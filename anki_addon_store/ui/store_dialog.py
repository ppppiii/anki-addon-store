"""AnkiWebView dialog hosting the bilingual Add-on Store UI."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from aqt.qt import QDialog, QMessageBox, QVBoxLayout
from aqt.theme import theme_manager
from aqt.utils import openLink, showInfo, showWarning
from aqt.webview import AnkiWebView

from .. import addon_bridge
from ..core import catalog, classifier, i18n

_WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class StoreDialog(QDialog):
    """Browse, filter, preview, install, toggle, and uninstall AnkiWeb add-ons."""

    def __init__(
        self,
        parent: Any,
        mw: Any,
        cfg: Dict[str, Any],
        cache_dir: str,
        lang: str = "zh",
    ) -> None:
        super().__init__(parent)
        self._mw = mw
        self._cfg = dict(cfg)
        self._cache_dir = cache_dir
        self._lang = lang
        self._catalog_items: List[Dict[str, Any]] = []
        self._source: str = ""
        self._page_ready: bool = False
        self._bg_loading: bool = False
        self._current_pv = addon_bridge.get_current_point_version()
        self._last_query: Dict[str, Any] = {
            "query": "",
            "category": "all",
            "compat_only": False,
            "active_only": False,
            "sort_by": "popular",
            "sort_dir": "desc",
            "limit": 60,
        }

        self.setWindowTitle(i18n.tr("win_title", self._lang))
        self.resize(1060, 720)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.web = AnkiWebView(parent=self)
        self.web.set_bridge_command(self._on_bridge_cmd, self)
        self.web.loadFinished.connect(self._on_page_loaded)
        lay.addWidget(self.web)

        self._bootstrap_local_catalog()
        self._render_shell()

    def _bootstrap_local_catalog(self) -> None:
        ttl = int(self._cfg.get("cache_ttl_hours", 12) or 12)
        cached = catalog.load_cached_catalog(self._cache_dir, cache_ttl_hours=ttl)
        if cached and cached.get("items"):
            self._catalog_items = list(cached["items"])
            self._source = str(cached.get("source") or "cache")
            if not cached.get("fresh"):
                self._load_catalog_async(force_refresh=False)
            return

        seed = catalog.load_seed_catalog()
        if seed and seed.get("items"):
            self._catalog_items = list(seed["items"])
            self._source = "seed"
        self._load_catalog_async(force_refresh=False)

    def _render_shell(self) -> None:
        with open(os.path.join(_WEB_DIR, "store.html"), "r", encoding="utf-8") as fh:
            body_html = fh.read()
        with open(os.path.join(_WEB_DIR, "store.css"), "r", encoding="utf-8") as fh:
            css_text = fh.read()
        with open(os.path.join(_WEB_DIR, "store.js"), "r", encoding="utf-8") as fh:
            js_text = fh.read()

        full_body = f"<style>{css_text}</style>\n{body_html}\n<script>{js_text}</script>"
        self.web.stdHtml(full_body, context=self, default_css=False)

    def _on_page_loaded(self, _ok: bool = True) -> None:
        self._page_ready = True
        self._push_js(
            {
                "type": "init",
                "lang": self._lang,
                "night": bool(getattr(theme_manager, "night_mode", False)),
                "i18n": i18n.get_bundle(self._lang),
            }
        )
        if self._catalog_items:
            warn = i18n.tr("status_refreshing", self._lang) if self._bg_loading else ""
            self._send_filtered(warning=warn)
        elif self._bg_loading:
            self._push_js({"type": "status", "message": i18n.tr("loading", self._lang)})

    def _push_js(self, payload: Dict[str, Any]) -> None:
        if not self._page_ready:
            return
        try:
            self.web.eval(f"window.__storeReceive({json.dumps(payload, ensure_ascii=False)});")
        except Exception:
            pass

    def _compute_counts(self, installed_map: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {"all": len(self._catalog_items), "installed": 0}
        for cat in classifier.CATEGORY_ORDER:
            counts[cat] = 0
        for it in self._catalog_items:
            if str(it.get("id") or "") in installed_map:
                counts["installed"] += 1
            cat = str(it.get("category") or "tools")
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def _send_filtered(self, warning: str = "") -> None:
        if not self._page_ready:
            return
        installed_map = addon_bridge.list_installed_addons(self._mw.addonManager)
        filtered = catalog.filter_and_sort(
            self._catalog_items,
            query=self._last_query.get("query", ""),
            category=self._last_query.get("category", "all"),
            compat_only=bool(self._last_query.get("compat_only", False)),
            active_only=bool(self._last_query.get("active_only", False)),
            sort_by=self._last_query.get("sort_by", "popular"),
            sort_dir=self._last_query.get("sort_dir", "desc"),
            installed_ids=installed_map,
            current_pv=self._current_pv,
        )
        limit = max(60, int(self._last_query.get("limit", 60) or 60))
        self._push_js(
            {
                "type": "catalog",
                "items": filtered[:limit],
                "total": len(filtered),
                "counts": self._compute_counts(installed_map),
                "source": self._source,
                "warning": warning,
            }
        )

    def _load_catalog_async(self, force_refresh: bool = False) -> None:
        self._bg_loading = True
        cat_url = str(self._cfg.get("catalog_url") or "")
        ttl = int(self._cfg.get("cache_ttl_hours", 12) or 12)

        def _bg() -> Dict[str, Any]:
            return catalog.fetch_catalog(
                catalog_url=cat_url,
                cache_dir=self._cache_dir,
                cache_ttl_hours=ttl,
                force_refresh=force_refresh,
            )

        def _done(fut: Any) -> None:
            self._bg_loading = False
            try:
                res = fut.result()
            except Exception as exc:
                if not self._catalog_items:
                    self._push_js(
                        {
                            "type": "status",
                            "message": i18n.tr("msg_load_fail", self._lang, err=exc),
                        }
                    )
                else:
                    self._push_js({"type": "status", "message": ""})
                return
            self._catalog_items = list(res.get("items") or [])
            self._source = str(res.get("source") or "")
            self._send_filtered(warning=str(res.get("warning") or ""))

        self._mw.taskman.run_in_background(_bg, _done)

    def _load_detail_async(self, addon_id: int, force: bool = False) -> None:
        def _bg() -> Dict[str, Any]:
            return addon_bridge.fetch_addon_detail(
                addon_id, cache_dir=self._cache_dir, force=force
            )

        def _done(fut: Any) -> None:
            try:
                detail = fut.result()
                self._push_js({"type": "detail", "id": addon_id, "detail": detail})
            except Exception as exc:
                self._push_js({"type": "detail_error", "id": addon_id, "error": str(exc)})

        self._mw.taskman.run_in_background(_bg, _done)

    def _on_bridge_cmd(self, cmd: str) -> Any:
        if not isinstance(cmd, str) or not cmd.startswith("store:"):
            return False
        try:
            payload = json.loads(cmd[6:])
        except Exception:
            return True

        action = payload.get("action")
        if action == "refresh_catalog":
            self._load_catalog_async(force_refresh=True)
        elif action == "query":
            self._last_query = {
                "query": str(payload.get("query") or ""),
                "category": str(payload.get("category") or "all"),
                "compat_only": bool(payload.get("compat_only", False)),
                "active_only": bool(payload.get("active_only", False)),
                "sort_by": str(payload.get("sort_by") or "popular"),
                "sort_dir": str(payload.get("sort_dir") or "desc"),
                "limit": max(60, int(payload.get("limit", 60) or 60)),
            }
            self._send_filtered()
        elif action == "fetch_detail":
            self._load_detail_async(int(payload["id"]), force=bool(payload.get("force", False)))
        elif action == "install":
            aid = int(payload["id"])
            addon_bridge.install_addon(
                self,
                self._mw.addonManager,
                aid,
                lambda res: self._on_install_done(res),
            )
        elif action == "toggle":
            mod_id = str(payload["id"])
            addon_bridge.toggle_addon(self._mw.addonManager, mod_id)
            self._send_filtered(warning=i18n.tr("msg_restart", self._lang))
        elif action == "uninstall":
            mod_id = str(payload["id"])
            title = str(payload.get("title") or mod_id)
            ans = QMessageBox.question(
                self,
                i18n.tr("btn_uninstall", self._lang),
                i18n.tr("confirm_uninstall", self._lang, name=title),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans == QMessageBox.StandardButton.Yes:
                addon_bridge.delete_addon(self._mw.addonManager, mod_id)
                self._send_filtered(warning=i18n.tr("msg_restart", self._lang))
        elif action == "check_updates":
            try:
                addon_bridge.check_updates(self, self._mw.addonManager)
            except Exception as exc:
                showWarning(str(exc), parent=self)
        elif action == "open_url":
            url = str(payload.get("url") or "")
            if url.startswith(("https://", "http://")):
                openLink(url)
        return True

    def _on_install_done(self, res: Dict[str, Any]) -> None:
        self._push_js({"type": "install_done", **res})
        if res.get("ok"):
            showInfo(i18n.tr("msg_restart", self._lang), parent=self)
        else:
            showWarning(i18n.tr("msg_install_fail", self._lang, err=res.get("error", "")), parent=self)
