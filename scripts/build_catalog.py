"""Build static catalog.json and catalog.json.gz from AnkiWeb's official add-on list."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
import types
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.join(REPO_ROOT, "anki_addon_store")

if "anki_addon_store" not in sys.modules:
    pkg = types.ModuleType("anki_addon_store")
    pkg.__path__ = [PKG_DIR]
    sys.modules["anki_addon_store"] = pkg
if "anki_addon_store.core" not in sys.modules:
    core_pkg = types.ModuleType("anki_addon_store.core")
    core_pkg.__path__ = [os.path.join(PKG_DIR, "core")]
    sys.modules["anki_addon_store.core"] = core_pkg

from anki_addon_store.core import ankiweb_proto, classifier  # noqa: E402

ANKIWEB_LIST_URL = "https://ankiweb.net/svc/shared/list-addons?search="


def main() -> None:
    ap = argparse.ArgumentParser(description="Build static catalog.json(.gz) for anki-addon-store")
    ap.add_argument("--out-dir", default=os.path.join(REPO_ROOT, "data"))
    args = ap.parse_args()

    req = urllib.request.Request(
        ANKIWEB_LIST_URL,
        headers={"User-Agent": "anki-addon-store-catalog-builder/1.0 (+https://github.com)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()

    decoded = ankiweb_proto.decode_list_addons(raw)
    if not decoded:
        raise RuntimeError("Decoded 0 add-ons from AnkiWeb")
    enriched = classifier.enrich_items(decoded)

    payload = {
        "schema_version": 1,
        "generated_at": int(time.time()),
        "count": len(enriched),
        "items": enriched,
    }
    os.makedirs(args.out_dir, exist_ok=True)
    json_path = os.path.join(args.out_dir, "catalog.json")
    gz_path = os.path.join(args.out_dir, "catalog.json.gz")

    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with open(json_path, "wb") as fh:
        fh.write(serialized)
    with gzip.open(gz_path, "wb", compresslevel=9) as fh:
        fh.write(serialized)

    print(
        f"Built {len(enriched)} add-ons -> {json_path} ({len(serialized) / 1024:.1f} KB), "
        f"{gz_path} ({os.path.getsize(gz_path) / 1024:.1f} KB)"
    )


if __name__ == "__main__":
    main()
