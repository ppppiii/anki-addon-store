"""Deterministic add-on category classifier and curated metadata enrichment."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence

CATEGORY_ORDER: List[str] = [
    "review",
    "editor",
    "language",
    "stats",
    "ui",
    "scheduling",
    "sync",
    "browser",
    "media",
    "tools",
]

_CATEGORY_KEYWORDS: Dict[str, Sequence[str]] = {
    "language": (
        "tts", "speech", "audio", "voice", "pronunciation", "japanese", "kanji",
        "furigana", "chinese", "pinyin", "hanzi", "korean", "german", "french",
        "spanish", "arabic", "russian", "dict", "dictionary", "translate", "vocab",
        "yomichan", "yomitan", "migaku", "forvo", "ipa", "language", "subtitle",
    ),
    "editor": (
        "editor", "cloze", "occlusion", "field", "html", "markdown", "latex",
        "mathjax", "mermaid", "syntax", "highlight", "table", "paste", "markdown",
        "format", "batch edit", "bulk", "template", "note type", "notetype",
        "image occlusion", "sticky", "frozen", "duplicate", "symbol", "popup",
    ),
    "review": (
        "review", "reviewer", "button", "shortcut", "hotkey", "gamepad", "controller",
        "timer", "countdown", "pomodoro", "focus", "pass/fail", "again", "easy",
        "answer", "flip", "typing", "type in", "hint", "scratchpad", "whiteboard",
        "playback", "speed", "auto advance", "zoom",
    ),
    "stats": (
        "heatmap", "stat", "stats", "chart", "graph", "simulator", "retention",
        "streak", "gamif", "game", "gaming", "pet", "quest", "play", "rpg",
        "pokemon", "ankimon", "leaderboard", "progress", "habit", "life drain",
        "xp", "level", "badge", "goal", "analytics",
    ),
    "ui": (
        "theme", "dark", "night", "css", "background", "wallpaper", "font",
        "redesign", "modern", "minimal", "icon", "deck browser", "sidebar",
        "toolbar", "window", "fullscreen", "color", "colour", "style", "onigiri",
        "synapse", "prettify",
    ),
    "scheduling": (
        "fsrs", "sm2", "sm-2", "scheduler", "schedule", "reschedule", "ease",
        "interval", "bury", "suspend", "leech", "sibling", "postpone", "advance",
        "fuzz", "overload", "load balancer", "filtered deck", "custom study",
        "due", "retention",
    ),
    "sync": (
        "sync", "ankiconnect", "ankihub", "backup", "export", "import", "csv",
        "json", "apkg", "obsidian", "notion", "quizlet", "memrise", "supermemo",
        "crowdanki", "git", "webdav", "api", "server", "remote",
    ),
    "browser": (
        "browser", "search", "filter", "tag", "tags", "flag", "deck", "decks",
        "column", "find", "replace", "sort", "preview", "sidebar", "reposition",
    ),
    "media": (
        "image", "img", "svg", "video", "gif", "mp3", "ogg", "compress",
        "resize", "screenshot", "pdf", "media", "recorder", "mic", "camera",
    ),
}

_WORD_RE = re.compile(r"[a-z0-9_/+.-]+")


def load_curated_overrides(path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """Load bundled curated_overrides.json."""
    target = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "curated_overrides.json")
    if not os.path.isfile(target):
        return {}
    with open(target, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def classify_text(title: str, tags: Sequence[str] = ()) -> str:
    """Assign a deterministic category based on title and optional tags."""
    haystack = " ".join([str(title or ""), *[str(t) for t in tags]]).lower()
    if not haystack.strip():
        return "tools"
    tokens = set(_WORD_RE.findall(haystack))

    best_cat = "tools"
    best_score = 0
    for cat in CATEGORY_ORDER:
        kws = _CATEGORY_KEYWORDS.get(cat, ())
        score = 0
        for kw in kws:
            if " " in kw or "-" in kw or "/" in kw:
                if kw in haystack:
                    score += 2
            elif kw in tokens:
                score += 2
            elif len(kw) >= 6 and kw in haystack:
                score += 1
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat


def compute_rating_metrics(likes: int, dislikes: int) -> Dict[str, Any]:
    """Compute net score and positive rating percentage."""
    up = max(0, int(likes or 0))
    down = max(0, int(dislikes or 0))
    total = up + down
    pct = int(round((up * 100.0) / total)) if total > 0 else None
    return {
        "net_score": up - down,
        "rating_pct": pct,
    }


def enrich_items(
    items: Sequence[Dict[str, Any]],
    overrides: Optional[Dict[str, Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """Attach category, curated bilingual summaries, and rating metrics to items."""
    ov_map = overrides if overrides is not None else load_curated_overrides()
    enriched: List[Dict[str, Any]] = []
    for raw in items:
        item = dict(raw)
        sid = str(item.get("id") or "")
        ov = ov_map.get(sid) or {}
        tags = list(item.get("tags") or [])
        cat = str(ov.get("category") or item.get("category") or "").strip()
        if cat not in CATEGORY_ORDER:
            cat = classify_text(str(item.get("title") or ""), tags)
        item["category"] = cat
        item["summary_en"] = str(ov.get("summary_en") or item.get("summary_en") or "")
        item["summary_zh"] = str(ov.get("summary_zh") or item.get("summary_zh") or "")
        metrics = compute_rating_metrics(item.get("likes", 0), item.get("dislikes", 0))
        item["net_score"] = metrics["net_score"]
        item["rating_pct"] = metrics["rating_pct"]
        enriched.append(item)
    return enriched
