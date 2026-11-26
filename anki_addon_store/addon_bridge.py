"""Anki AddonManager & item-info bridge (cleanly testable without live Anki/Qt)."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Dict, Optional

from .core import ankiweb_proto, catalog

ANKIWEB_ITEM_INFO_URL = "https://ankiweb.net/svc/shared/item-info?sharedId={id}"
DETAIL_CACHE_TTL_SEC = 24 * 3600


def get_current_point_version() -> int:
    """Return current Anki point version integer (e.g. 260904 for 26.09.4)."""
    ver_str = ""
    try:
        from anki.buildinfo import version as _anki_ver  # type: ignore

        ver_str = str(_anki_ver or "")
    except Exception:
        try:
            from aqt import mw  # type: ignore

            ver_str = str(getattr(mw, "appVersion", "") or "")
        except Exception:
            ver_str = ""
    return ankiweb_proto.parse_version_to_point(ver_str)


def list_installed_addons(mgr: Any) -> Dict[str, Dict[str, Any]]:
    """Return {module_or_id: {module_id, name, enabled}} from AddonManager."""
    out: Dict[str, Dict[str, Any]] = {}
    if mgr is None:
        return out
    for mod in mgr.allAddons():
        mid = str(mod)
        try:
            enabled = bool(mgr.isEnabled(mid))
        except Exception:
            enabled = True
        try:
            name = str(mgr.addonName(mid) or mid)
        except Exception:
            name = mid
        out[mid] = {
            "module_id": mid,
            "name": name,
            "enabled": enabled,
        }
    return out


def install_addon(
    parent: Any,
    mgr: Any,
    addon_id: int,
    on_done: Callable[[Dict[str, Any]], None],
) -> None:
    """Install an AnkiWeb add-on natively via aqt.addons.download_addons."""
    try:
        from aqt.addons import download_addons  # type: ignore
    except Exception as exc:
        on_done({"ok": False, "error": str(exc)})
        return

    def _finished(log: Any = None) -> None:
        err = ""
        if log is not None:
            errs = getattr(log, "errors", None)
            if errs:
                err = "; ".join(str(e) for e in errs)
        if err:
            on_done({"ok": False, "error": err})
        else:
            on_done({"ok": True, "id": int(addon_id)})

    try:
        download_addons(parent, mgr, [int(addon_id)], _finished)
    except Exception as exc:
        on_done({"ok": False, "error": str(exc)})


def toggle_addon(mgr: Any, module_id: str) -> bool:
    """Toggle enabled state of an installed add-on and return new enabled state."""
    mgr.toggleEnabled(str(module_id))
    return bool(mgr.isEnabled(str(module_id)))


def delete_addon(mgr: Any, module_id: str) -> None:
    """Delete an installed add-on via AddonManager."""
    mgr.deleteAddon(str(module_id))


def check_updates(parent: Any, mgr: Any) -> None:
    """Trigger Anki's native add-on update checker."""
    from aqt import addons as aqt_addons  # type: ignore

    if hasattr(aqt_addons, "check_and_install_addon_updates"):
        try:
            aqt_addons.check_and_install_addon_updates(mgr, parent)
            return
        except TypeError:
            aqt_addons.check_and_install_addon_updates(mgr)
            return
    dlg = aqt_addons.AddonsDialog(mgr)
    if hasattr(dlg, "onCheckForUpdates"):
        dlg.onCheckForUpdates()


DETAIL_SCHEMA_VERSION = 2


def fetch_addon_detail(
    addon_id: int,
    cache_dir: str = "",
    force: bool = False,
    http_get: Callable[[str], bytes] = catalog.default_http_get,
    now_ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Fetch and cache full detail info for a single AnkiWeb add-on."""
    aid = int(addon_id)
    now = int(now_ts if now_ts is not None else time.time())
    detail_path = os.path.join(cache_dir, "details", f"{aid}.json") if cache_dir else ""

    if detail_path and not force and os.path.isfile(detail_path):
        try:
            with open(detail_path, "r", encoding="utf-8") as fh:
                cached = json.load(fh)
            if (
                isinstance(cached, dict)
                and cached.get("detail_schema_version") == DETAIL_SCHEMA_VERSION
                and "reviews" in cached
                and now - int(cached.get("fetched_at") or 0) <= DETAIL_CACHE_TTL_SEC
            ):
                return cached
        except Exception:
            pass

    url = ANKIWEB_ITEM_INFO_URL.format(id=aid)
    raw = http_get(url)
    detail = ankiweb_proto.decode_item_info(raw, addon_id=aid)
    detail["detail_schema_version"] = DETAIL_SCHEMA_VERSION
    detail["fetched_at"] = now
    detail["ankiweb_url"] = f"https://ankiweb.net/shared/info/{aid}"

    if detail_path:
        os.makedirs(os.path.dirname(detail_path), exist_ok=True)
        tmp = f"{detail_path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(detail, fh, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, detail_path)

    return detail
