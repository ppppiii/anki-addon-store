"""插件市场 (Anki Add-on Store) — 开源原生 Anki 插件浏览、分类与一键安装市场。"""

from __future__ import annotations

import os
from typing import Any, Dict

from aqt import gui_hooks, mw
from aqt.qt import QAction, QActionGroup, QMenu

from .core import i18n
from .ui.store_dialog import StoreDialog

ADDON = mw.addonManager.addonFromModule(__name__)
ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ADDON_DIR, "user_files", "cache")


def _load_cfg() -> Dict[str, Any]:
    try:
        return dict(mw.addonManager.getConfig(ADDON) or {})
    except Exception:
        return {}


def _save_cfg(cfg: Dict[str, Any]) -> None:
    try:
        mw.addonManager.writeConfig(ADDON, cfg)
    except Exception:
        pass


def _current_lang() -> str:
    cfg = _load_cfg()
    anki_loc = ""
    try:
        from anki.lang import current_lang as _cur_lang  # type: ignore

        anki_loc = str(_cur_lang or "")
    except Exception:
        anki_loc = ""
    return i18n.resolve_lang(str(cfg.get("language", "auto") or "auto"), anki_loc)


def open_store() -> None:
    dlg = StoreDialog(mw, mw, _load_cfg(), CACHE_DIR, lang=_current_lang())
    dlg.exec()


def _setup_menu() -> None:
    try:
        known = {i18n.STRINGS["menu_root"]["zh"], i18n.STRINGS["menu_root"]["en"]}
        for act in mw.form.menuTools.actions():
            if act.text() in known:
                return
        lang = _current_lang()
        menu = QMenu(i18n.tr("menu_root", lang), mw)

        act_open = QAction(i18n.tr("menu_open", lang), mw)
        act_open.triggered.connect(open_store)
        menu.addAction(act_open)
        menu.addSeparator()

        lang_menu = QMenu(i18n.tr("menu_lang", lang), mw)
        lang_group = QActionGroup(lang_menu)
        lang_group.setExclusive(True)
        lang_actions: Dict[str, QAction] = {}
        for code, key in (("auto", "lang_auto"), ("zh", "lang_zh"), ("en", "lang_en")):
            act = QAction(i18n.tr(key, lang), mw)
            act.setCheckable(True)
            act.triggered.connect(lambda _chk=False, c=code: _set_language(c))
            lang_group.addAction(act)
            lang_menu.addAction(act)
            lang_actions[code] = act
        menu.addMenu(lang_menu)

        def _sync_labels() -> None:
            cur = _current_lang()
            pref = str(_load_cfg().get("language", "auto") or "auto").strip().lower()
            if pref not in lang_actions:
                pref = "auto"
            menu.setTitle(i18n.tr("menu_root", cur))
            act_open.setText(i18n.tr("menu_open", cur))
            lang_menu.setTitle(i18n.tr("menu_lang", cur))
            lang_actions["auto"].setText(i18n.tr("lang_auto", cur))
            lang_actions["zh"].setText(i18n.tr("lang_zh", cur))
            lang_actions["en"].setText(i18n.tr("lang_en", cur))
            for code, act in lang_actions.items():
                act.setChecked(code == pref)

        def _set_language(code: str) -> None:
            cfg = _load_cfg()
            cfg["language"] = code
            _save_cfg(cfg)
            _sync_labels()

        _sync_labels()
        try:
            menu.aboutToShow.connect(_sync_labels)
        except Exception:
            pass
        mw.form.menuTools.addMenu(menu)
    except Exception:
        pass


gui_hooks.main_window_did_init.append(_setup_menu)

if getattr(mw, "form", None) is not None and getattr(mw.form, "menuTools", None) is not None:
    _setup_menu()
