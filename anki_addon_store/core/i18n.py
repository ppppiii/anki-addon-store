"""Bilingual (zh / en) localization for anki_addon_store (zero aqt/anki/PyQt deps)."""

from __future__ import annotations

from typing import Any, Dict

STRINGS: Dict[str, Dict[str, str]] = {
    # Menu & Shell
    "menu_root": {"zh": "插件市场", "en": "Add-on Store"},
    "menu_open": {"zh": "打开插件市场...", "en": "Open Add-on Store..."},
    "menu_lang": {"zh": "语言 / Language", "en": "Language"},
    "lang_auto": {"zh": "自动 (跟随 Anki)", "en": "Auto (Follow Anki)"},
    "lang_zh": {"zh": "中文", "en": "中文"},
    "lang_en": {"zh": "English", "en": "English"},
    "win_title": {"zh": "Anki 插件市场", "en": "Anki Add-on Store"},
    # Categories
    "cat_all": {"zh": "全部", "en": "All"},
    "cat_installed": {"zh": "已安装", "en": "Installed"},
    "cat_review": {"zh": "刷卡复习", "en": "Review"},
    "cat_editor": {"zh": "制卡编辑", "en": "Editor & Notes"},
    "cat_language": {"zh": "语言发音", "en": "Language & TTS"},
    "cat_stats": {"zh": "游戏化", "en": "Gamification"},
    "cat_ui": {"zh": "界面美化", "en": "UI & Themes"},
    "cat_scheduling": {"zh": "算法调度", "en": "Scheduling"},
    "cat_sync": {"zh": "同步导入", "en": "Sync & Import"},
    "cat_browser": {"zh": "卡片浏览", "en": "Card Browser"},
    "cat_media": {"zh": "媒体处理", "en": "Media"},
    "cat_tools": {"zh": "效率工具", "en": "Utilities"},
    # Toolbar & Filters
    "search_ph": {"zh": "搜索名称、ID 或关键词...", "en": "Search name, ID, or keyword..."},
    "flt_compat": {"zh": "兼容当前版本", "en": "Compatible"},
    "flt_active": {"zh": "近 1 年更新", "en": "Active 1y"},
    "sort_popular": {"zh": "按热门度", "en": "Most Popular"},
    "sort_rating": {"zh": "按好评率", "en": "Highest Rated"},
    "sort_updated": {"zh": "按最近更新", "en": "Recently Updated"},
    "sort_name": {"zh": "按名称", "en": "Name"},
    "sort_desc": {"zh": "降序 ↓", "en": "Desc ↓"},
    "sort_asc": {"zh": "升序 ↑", "en": "Asc ↑"},
    "btn_updates": {"zh": "检查更新", "en": "Check Updates"},
    "btn_refresh": {"zh": "刷新目录", "en": "Refresh"},
    "btn_load_more": {"zh": "加载更多 ({n})", "en": "Load More ({n})"},
    # Status & Badges
    "loading": {"zh": "加载插件目录...", "en": "Loading add-on catalog..."},
    "loading_detail": {"zh": "读取详情...", "en": "Loading details..."},
    "empty_results": {"zh": "无匹配插件", "en": "No matching add-ons"},
    "count_shown": {"zh": "显示 {shown} / {total}", "en": "{shown} of {total}"},
    "source_ankiweb": {"zh": "AnkiWeb 实时索引", "en": "AnkiWeb Live"},
    "source_static": {"zh": "GitHub 静态索引", "en": "GitHub Index"},
    "source_cache": {"zh": "本地缓存", "en": "Cached"},
    "source_stale_cache": {"zh": "离线缓存", "en": "Offline Cache"},
    "source_seed": {"zh": "内置快照", "en": "Bundled Index"},
    "status_refreshing": {"zh": "后台更新中...", "en": "Refreshing..."},
    "compat_compatible": {"zh": "兼容", "en": "Compatible"},
    "compat_likely": {"zh": "大概率兼容", "en": "Likely OK"},
    "compat_legacy": {"zh": "旧版插件", "en": "Legacy"},
    "compat_incompatible": {"zh": "版本受限", "en": "Version Cap"},
    "compat_unknown": {"zh": "未标版本", "en": "Unspecified"},
    "act_active": {"zh": "活跃", "en": "Active"},
    "act_aging": {"zh": "较久未更", "en": "Aging"},
    "act_stale": {"zh": "长期未更", "en": "Stale"},
    # Actions & Detail Drawer
    "btn_install": {"zh": "安装", "en": "Install"},
    "btn_installing": {"zh": "安装中...", "en": "Installing..."},
    "btn_enable": {"zh": "启用", "en": "Enable"},
    "btn_disable": {"zh": "禁用", "en": "Disable"},
    "btn_uninstall": {"zh": "卸载", "en": "Uninstall"},
    "btn_ankiweb": {"zh": "AnkiWeb 评论与主页", "en": "AnkiWeb & Reviews"},
    "btn_github": {"zh": "GitHub 仓库", "en": "GitHub"},
    "btn_support": {"zh": "支持主页", "en": "Support"},
    "lbl_installed": {"zh": "已安装", "en": "Installed"},
    "lbl_disabled": {"zh": "已禁用", "en": "Disabled"},
    "lbl_updated": {"zh": "更新", "en": "Updated"},
    "lbl_anki_ver": {"zh": "支持 Anki", "en": "Anki"},
    "lbl_size": {"zh": "体积", "en": "Size"},
    "lbl_code": {"zh": "代码", "en": "Code"},
    "lbl_reviews": {"zh": "评价", "en": "Ratings"},
    # Prompts & Notifications
    "confirm_uninstall": {"zh": "确定卸载「{name}」？", "en": "Uninstall '{name}'?"},
    "msg_restart": {"zh": "操作完成，重启 Anki 后生效。", "en": "Done. Restart Anki to apply."},
    "msg_install_fail": {"zh": "安装失败：{err}", "en": "Install failed: {err}"},
    "msg_load_fail": {"zh": "目录加载失败：{err}", "en": "Failed to load catalog: {err}"},
    "sec_reviews": {"zh": "用户评论 ({n})", "en": "Reviews ({n})"},
    "btn_write_review": {"zh": "去 AnkiWeb 写评论", "en": "Write Review on AnkiWeb"},
    "no_reviews": {"zh": "暂无评论", "en": "No reviews yet"},
    "author_reply": {"zh": "作者回复", "en": "Author reply"},
    "btn_retry": {"zh": "重试", "en": "Retry"},
    "detail_load_fail": {"zh": "详情加载失败：{err}", "en": "Failed to load details: {err}"},
    "rev_all": {"zh": "全部", "en": "All"},
    "rev_pos": {"zh": "赞 👍", "en": "Up 👍"},
    "rev_neg": {"zh": "踩 👎", "en": "Down 👎"},
}


def resolve_lang(cfg_lang: str = "auto", anki_locale: str = "") -> str:
    """Resolve UI language ('zh' or 'en') from config and Anki's locale."""
    raw = str(cfg_lang or "auto").strip().lower()
    if raw in ("zh", "zh_cn", "zh-cn", "cn"):
        return "zh"
    if raw in ("en", "en_us", "en-us"):
        return "en"
    loc = str(anki_locale or "").strip().lower()
    if loc and not loc.startswith("zh"):
        return "en"
    return "zh"


def tr(key: str, lang: str = "zh", **kwargs: Any) -> str:
    """Lookup and format a localized string."""
    entry = STRINGS.get(key)
    if not entry:
        return key
    tpl = entry.get(lang) or entry.get("zh") or key
    if kwargs:
        try:
            return tpl.format(**kwargs)
        except Exception:
            return tpl
    return tpl


def get_bundle(lang: str = "zh") -> Dict[str, str]:
    """Return flattened {key: localized_text} dictionary for injecting into JS frontend."""
    resolved = resolve_lang(lang)
    return {k: (v.get(resolved) or v.get("zh") or k) for k, v in STRINGS.items()}
