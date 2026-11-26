"""Hybrid catalog loader (GitHub static catalog + AnkiWeb live fallback + disk cache)."""

from __future__ import annotations

import gzip
import json
import os
import ssl
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import ankiweb_proto, classifier

ANKIWEB_LIST_URL = "https://ankiweb.net/svc/shared/list-addons?search="
DEFAULT_TIMEOUT = 15


def default_http_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    """Fetch raw bytes resiliently against proxy/TLS unexpected EOFs with retries."""
    headers = {
        "User-Agent": "anki-addon-store/1.0 (+https://github.com)",
        "Connection": "close",
    }
    ctx = ssl.create_default_context()
    ctx.options |= getattr(ssl, "OP_IGNORE_UNEXPECTED_EOF", 0)
    last_err: Optional[Exception] = None

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read()
        except Exception as exc:
            last_err = exc
        try:
            import requests  # type: ignore

            resp = requests.get(url, timeout=timeout, headers=headers)
            resp.raise_for_status()
            return bytes(resp.content)
        except ImportError:
            pass
        except Exception as exc:
            last_err = exc
        if attempt < 2:
            time.sleep(0.3 * (attempt + 1))

    raise last_err or RuntimeError("HTTP request failed")


def load_seed_catalog(seed_path: str = "") -> Optional[Dict[str, Any]]:
    """Load bundled seed_catalog.json.gz for instant zero-latency startup."""
    target = seed_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_catalog.json.gz")
    if not os.path.isfile(target):
        return None
    try:
        with gzip.open(target, "rb") as fh:
            parsed = json.loads(fh.read().decode("utf-8"))
        raw_items = parsed.get("items") if isinstance(parsed, dict) else parsed
        if not isinstance(raw_items, list) or not raw_items:
            return None
        return {
            "source": "seed",
            "fetched_at": int(parsed.get("generated_at") or 0) if isinstance(parsed, dict) else 0,
            "items": classifier.enrich_items(raw_items),
        }
    except Exception:
        return None


def load_cached_catalog(
    cache_dir: str,
    cache_ttl_hours: int = 12,
    now_ts: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Load local catalog_cache.json if present; marks whether it is still fresh."""
    if not cache_dir:
        return None
    cache_file = os.path.join(cache_dir, "catalog_cache.json")
    cached = _load_cache(cache_file)
    if not cached or not cached.get("items"):
        return None
    now = int(now_ts if now_ts is not None else time.time())
    age_sec = max(0, now - int(cached.get("fetched_at") or 0))
    fresh = age_sec <= max(1, int(cache_ttl_hours or 12)) * 3600
    return {
        "source": "cache" if fresh else "stale_cache",
        "fresh": fresh,
        "fetched_at": int(cached.get("fetched_at") or 0),
        "items": classifier.enrich_items(cached["items"]),
    }


def _load_cache(cache_file: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(cache_file):
        return None
    try:
        with open(cache_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data
    except Exception:
        return None
    return None


def _save_cache(cache_file: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(cache_file)), exist_ok=True)
    tmp = f"{cache_file}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, cache_file)


def _decode_static_catalog(raw: bytes) -> List[Dict[str, Any]]:
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    parsed = json.loads(raw.decode("utf-8"))
    if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
        return list(parsed["items"])
    if isinstance(parsed, list):
        return list(parsed)
    raise ValueError("Invalid static catalog JSON format")


def fetch_catalog(
    catalog_url: str = "",
    cache_dir: str = "",
    cache_ttl_hours: int = 12,
    force_refresh: bool = False,
    http_get: Callable[[str], bytes] = default_http_get,
    now_ts: Optional[int] = None,
) -> Dict[str, Any]:
    """Load add-on catalog from cache, static URL, or live AnkiWeb protobuf endpoint."""
    now = int(now_ts if now_ts is not None else time.time())
    cache_file = os.path.join(cache_dir, "catalog_cache.json") if cache_dir else ""

    cached = _load_cache(cache_file) if cache_file else None
    if cached and not force_refresh:
        age_sec = max(0, now - int(cached.get("fetched_at") or 0))
        if age_sec <= max(1, int(cache_ttl_hours or 12)) * 3600 and cached["items"]:
            return {
                "source": "cache",
                "fetched_at": int(cached.get("fetched_at") or now),
                "items": classifier.enrich_items(cached["items"]),
            }

    errors: List[str] = []
    if catalog_url and catalog_url.strip():
        try:
            raw = http_get(catalog_url.strip())
            items = classifier.enrich_items(_decode_static_catalog(raw))
            if items:
                payload = {"source": "static", "fetched_at": now, "items": items}
                if cache_file:
                    _save_cache(cache_file, payload)
                return payload
        except Exception as exc:
            errors.append(f"static: {exc}")

    try:
        raw_proto = http_get(ANKIWEB_LIST_URL)
        decoded = ankiweb_proto.decode_list_addons(raw_proto)
        items = classifier.enrich_items(decoded)
        if not items:
            raise ValueError("Empty list from AnkiWeb")
        payload = {"source": "ankiweb", "fetched_at": now, "items": items}
        if cache_file:
            _save_cache(cache_file, payload)
        return payload
    except Exception as exc:
        errors.append(f"ankiweb: {exc}")

    if cached and cached.get("items"):
        return {
            "source": "stale_cache",
            "fetched_at": int(cached.get("fetched_at") or 0),
            "items": classifier.enrich_items(cached["items"]),
            "warning": "; ".join(errors),
        }
    seed = load_seed_catalog()
    if seed is not None:
        seed["warning"] = "; ".join(errors)
        return seed
    raise RuntimeError("; ".join(errors))


def filter_and_sort(
    items: Sequence[Dict[str, Any]],
    query: str = "",
    category: str = "all",
    compat_only: bool = False,
    active_only: bool = False,
    installed_only: bool = False,
    sort_by: str = "popular",
    sort_dir: str = "desc",
    installed_ids: Optional[Dict[str, Dict[str, Any]]] = None,
    current_pv: int = 0,
    now_ts: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Filter, annotate, and sort catalog items for display."""
    q = (query or "").strip().lower()
    cat = (category or "all").strip().lower()
    inst = installed_ids or {}
    now = int(now_ts if now_ts is not None else time.time())

    out: List[Dict[str, Any]] = []
    for raw in items:
        sid = str(raw.get("id") or "")
        compat = ankiweb_proto.evaluate_compatibility(int(raw.get("max_pv") or 0), current_pv)
        activity = ankiweb_proto.evaluate_activity(int(raw.get("modified") or 0), now_ts=now)
        is_inst = sid in inst

        if installed_only and not is_inst:
            continue
        if cat not in ("all", "installed") and raw.get("category") != cat:
            continue
        if cat == "installed" and not is_inst:
            continue
        if compat_only and compat not in ("compatible", "likely"):
            continue
        if active_only and activity != "active":
            continue
        if q:
            hay = " ".join(
                [
                    sid,
                    str(raw.get("title") or ""),
                    str(raw.get("summary_en") or ""),
                    str(raw.get("summary_zh") or ""),
                    " ".join(str(t) for t in raw.get("tags") or []),
                ]
            ).lower()
            if not all(tok in hay for tok in q.split()):
                continue

        enriched = dict(raw)
        enriched["compat"] = compat
        enriched["activity"] = activity
        enriched["installed"] = is_inst
        enriched["enabled"] = bool(inst[sid].get("enabled", True)) if is_inst else False
        out.append(enriched)

    reverse = str(sort_dir or "desc").strip().lower() != "asc"
    if sort_by == "rating":
        rated = [x for x in out if x.get("rating_pct") is not None]
        unrated = [x for x in out if x.get("rating_pct") is None]
        rated.sort(key=lambda x: (int(x["rating_pct"]), int(x.get("net_score") or 0)), reverse=reverse)
        unrated.sort(key=lambda x: int(x.get("net_score") or 0), reverse=reverse)
        out = rated + unrated
    elif sort_by == "updated":
        out.sort(key=lambda x: (int(x.get("modified") or 0), int(x.get("net_score") or 0)), reverse=reverse)
    elif sort_by == "name":
        out.sort(key=lambda x: str(x.get("title") or "").lower(), reverse=reverse)
    else:  # popular
        out.sort(key=lambda x: (int(x.get("net_score") or 0), int(x.get("likes") or 0)), reverse=reverse)

    return out
