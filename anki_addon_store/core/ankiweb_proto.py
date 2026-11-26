"""Pure-Python AnkiWeb protobuf decoder, HTML sanitizer, and version/activity evaluators."""

from __future__ import annotations

import html
import re
import time
from typing import Any, Dict, List, Optional, Tuple

_GITHUB_URL_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
_STRIP_TAG_BLOCK_RE = re.compile(
    r"<\s*(script|style|iframe|object|embed|form)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_STRIP_SINGLE_TAG_RE = re.compile(
    r"<\s*/?\s*(script|style|iframe|object|embed|form)\b[^>]*>",
    re.IGNORECASE,
)
_ON_EVENT_RE = re.compile(
    r"""\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""",
    re.IGNORECASE,
)
_JS_URI_RE = re.compile(
    r"""(href|src)\s*=\s*(?:"\s*(?:javascript|vbscript|data:text/html)[^"]*"|'\s*(?:javascript|vbscript|data:text/html)[^']*')""",
    re.IGNORECASE,
)


def read_varint(buf: bytes, idx: int) -> Tuple[int, int]:
    """Decode an unsigned base-128 varint from buf starting at idx."""
    shift = 0
    val = 0
    n = len(buf)
    while idx < n:
        b = buf[idx]
        idx += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, idx
        shift += 7
    raise ValueError("Truncated varint")


def to_signed64(val: int) -> int:
    """Convert unsigned 64-bit varint representation to signed integer."""
    if val >= (1 << 63):
        return val - (1 << 64)
    return val


def decode_fields(buf: bytes) -> List[Tuple[int, str, Any]]:
    """Decode top-level protobuf fields into [(field_num, wire_kind, value), ...]."""
    out: List[Tuple[int, str, Any]] = []
    idx = 0
    n = len(buf)
    while idx < n:
        tag, idx = read_varint(buf, idx)
        fnum = tag >> 3
        wtype = tag & 0x07
        if wtype == 0:
            v, idx = read_varint(buf, idx)
            out.append((fnum, "varint", v))
        elif wtype == 2:
            ln, idx = read_varint(buf, idx)
            out.append((fnum, "bytes", buf[idx : idx + ln]))
            idx += ln
        elif wtype == 5:
            out.append((fnum, "fixed32", buf[idx : idx + 4]))
            idx += 4
        elif wtype == 1:
            out.append((fnum, "fixed64", buf[idx : idx + 8]))
            idx += 8
        else:
            break
    return out


def encode_varint(val: int) -> bytes:
    """Encode signed/unsigned integer as protobuf varint (used by tests & tools)."""
    if val < 0:
        val = (1 << 64) + val
    parts = bytearray()
    while True:
        b = val & 0x7F
        val >>= 7
        if val:
            parts.append(b | 0x80)
        else:
            parts.append(b)
            break
    return bytes(parts)


def encode_field_varint(fnum: int, val: int) -> bytes:
    return encode_varint((fnum << 3) | 0) + encode_varint(val)


def encode_field_bytes(fnum: int, data: bytes) -> bytes:
    return encode_varint((fnum << 3) | 2) + encode_varint(len(data)) + data


def format_point_version(pv: int) -> str:
    """Format an Anki point version integer (e.g. 54 -> '2.1.54', 250205 -> '25.02.5')."""
    if not pv:
        return ""
    neg = pv < 0
    apv = abs(int(pv))
    if apv < 1000:
        s = f"2.1.{apv}"
    else:
        yy = apv // 10000
        mm = (apv // 100) % 100
        pp = apv % 100
        s = f"{yy}.{mm:02d}" if pp == 0 else f"{yy}.{mm:02d}.{pp}"
    return f"-{s}" if neg else f"{s}~"


def parse_version_to_point(ver_str: str) -> int:
    """Parse Anki version string like '26.09.4', '23.10', or '2.1.66' to point version."""
    s = (ver_str or "").strip().lstrip("-").rstrip("~+").strip()
    if not s:
        return 0
    parts = []
    for tok in s.split("."):
        m = re.match(r"^(\d+)", tok)
        if not m:
            break
        parts.append(int(m.group(1)))
    if not parts:
        return 0
    if len(parts) >= 3 and parts[0] == 2 and parts[1] == 1:
        return parts[2]
    yy = parts[0]
    mm = parts[1] if len(parts) > 1 else 0
    pp = parts[2] if len(parts) > 2 else 0
    return yy * 10000 + mm * 100 + pp


def evaluate_compatibility(max_pv: int, current_pv: int) -> str:
    """Classify compatibility against current_pv: compatible/likely/legacy/incompatible/unknown."""
    pv = int(max_pv or 0)
    if pv == 0:
        return "unknown"
    if pv < 0:
        cap = abs(pv)
        if current_pv <= 0 or cap >= current_pv:
            return "compatible"
        return "incompatible"
    if current_pv > 0 and pv >= current_pv:
        return "compatible"
    if pv >= 231000:
        return "compatible"
    if pv >= 50:
        return "likely"
    return "legacy"


def evaluate_activity(modified_ts: int, now_ts: Optional[int] = None) -> str:
    """Classify maintenance recency: active (<=1y), aging (<=3y), stale (>3y)."""
    ts = int(modified_ts or 0)
    if ts <= 0:
        return "stale"
    now = int(now_ts if now_ts is not None else time.time())
    age_days = max(0.0, (now - ts) / 86400.0)
    if age_days <= 365:
        return "active"
    if age_days <= 1095:
        return "aging"
    return "stale"


def decode_list_addons(raw: bytes) -> List[Dict[str, Any]]:
    """Decode /svc/shared/list-addons protobuf response into plain add-on dicts."""
    items: List[Dict[str, Any]] = []
    for fnum, wkind, val in decode_fields(raw):
        if fnum != 1 or wkind != "bytes":
            continue
        entry: Dict[str, Any] = {
            "id": 0,
            "title": "",
            "likes": 0,
            "dislikes": 0,
            "modified": 0,
            "max_pv": 0,
        }
        for sf, sw, sv in decode_fields(val):
            if sf == 1 and sw == "varint":
                entry["id"] = int(sv)
            elif sf == 2 and sw == "bytes":
                entry["title"] = sv.decode("utf-8", "replace").strip()
            elif sf == 3 and sw == "varint":
                entry["likes"] = int(sv)
            elif sf == 4 and sw == "varint":
                entry["dislikes"] = int(sv)
            elif sf == 5 and sw == "varint":
                entry["modified"] = int(sv)
            elif sf == 6 and sw == "varint":
                entry["max_pv"] = to_signed64(int(sv))
        if entry["id"] > 0:
            entry["max_version"] = format_point_version(entry["max_pv"])
            items.append(entry)
    return items


def sanitize_html(raw_html: str) -> str:
    """Strip unsafe scripts, event handlers, and javascript: URIs from AnkiWeb HTML."""
    s = raw_html or ""
    s = _STRIP_TAG_BLOCK_RE.sub("", s)
    s = _STRIP_SINGLE_TAG_RE.sub("", s)
    s = _ON_EVENT_RE.sub("", s)
    s = _JS_URI_RE.sub(r'\1="#"', s)
    return s


def extract_github_url(support_url: str, desc_html: str) -> str:
    """Find first valid GitHub repository URL from support_url or description HTML."""
    for src in (support_url or "", html.unescape(desc_html or "")):
        m = _GITHUB_URL_RE.search(src)
        if m:
            repo = m.group(1).rstrip(").,;\"'<>")
            if "/" in repo:
                parts = repo.split("/", 2)
                return f"https://github.com/{parts[0]}/{parts[1]}"
    return ""


def decode_item_info(raw: bytes, addon_id: int = 0) -> Dict[str, Any]:
    """Decode /svc/shared/item-info protobuf payload into a sanitized detail dict."""
    outer = decode_fields(raw)
    inner_bytes = b""
    for fnum, wkind, val in outer:
        if fnum == 1 and wkind == "bytes":
            inner_bytes = val
            break
    if not inner_bytes:
        raise ValueError("Invalid item-info response")

    detail: Dict[str, Any] = {
        "id": int(addon_id),
        "title": "",
        "likes": 0,
        "dislikes": 0,
        "tags": [],
        "size_bytes": 0,
        "modified": 0,
        "description_html": "",
        "support_url": "",
        "branches": [],
        "reviews": [],
    }
    for sf, sw, sv in decode_fields(inner_bytes):
        if sf == 1 and sw == "bytes":
            rev: Dict[str, Any] = {
                "created": 0,
                "positive": False,
                "text": "",
                "author_reply": "",
                "reply_created": 0,
            }
            for rf, rw, rv in decode_fields(sv):
                if rf == 1 and rw == "varint":
                    rev["created"] = int(rv)
                elif rf == 2 and rw == "varint":
                    rev["positive"] = bool(int(rv) == 1)
                elif rf == 4 and rw == "bytes":
                    rev["text"] = rv.decode("utf-8", "replace").strip()
                elif rf == 5 and rw == "bytes":
                    rev["author_reply"] = rv.decode("utf-8", "replace").strip()
                elif rf == 6 and rw == "varint":
                    rev["reply_created"] = int(rv)
            if rev["text"]:
                detail["reviews"].append(rev)
        elif sf == 2 and sw == "varint" and detail["likes"] == 0:
            detail["likes"] = int(sv)
        elif sf == 3 and sw == "varint" and detail["dislikes"] == 0:
            detail["dislikes"] = int(sv)
        elif sf == 5 and sw == "bytes":
            detail["title"] = sv.decode("utf-8", "replace").strip()
        elif sf == 6 and sw == "bytes":
            raw_tags = sv.decode("utf-8", "replace").strip()
            detail["tags"] = [t for t in raw_tags.split() if t]
        elif sf == 7 and sw == "varint":
            detail["size_bytes"] = int(sv)
        elif sf == 8 and sw == "varint":
            detail["modified"] = int(sv)
        elif sf == 9 and sw == "bytes":
            detail["description_html"] = sanitize_html(sv.decode("utf-8", "replace"))
        elif sf in (10, 12) and sw == "bytes":
            detail["support_url"] = sv.decode("utf-8", "replace").strip()
        elif sf == 11 and sw == "bytes":
            direct_br = {"version_range": "", "modified": 0}
            for bf, bw, bv in decode_fields(sv):
                if bf == 1 and bw == "bytes":
                    direct_br["version_range"] = bv.decode("utf-8", "replace").strip()
                elif bf == 2 and bw == "varint":
                    direct_br["modified"] = int(bv)
                elif bf == 3 and bw == "bytes":
                    sub_br = {"version_range": "", "modified": 0}
                    for sbf, sbw, sbv in decode_fields(bv):
                        if sbf == 1 and sbw == "bytes":
                            sub_br["version_range"] = sbv.decode("utf-8", "replace").strip()
                        elif sbf == 2 and sbw == "varint":
                            sub_br["modified"] = int(sbv)
                    if sub_br["version_range"]:
                        detail["branches"].append(sub_br)
            if direct_br["version_range"]:
                detail["branches"].append(direct_br)
        elif sf == 18 and sw == "varint":
            detail["likes"] = int(sv)
        elif sf == 19 and sw == "varint":
            detail["dislikes"] = int(sv)

    detail["github_url"] = extract_github_url(detail["support_url"], detail["description_html"])
    return detail
