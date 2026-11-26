"""Offline unit tests for anki_addon_store pure core, i18n, catalog, and bridge."""

from __future__ import annotations

import ast
import gzip
import json
import os
import string
import sys
import tempfile
import time
import types
import unittest

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

from anki_addon_store import addon_bridge  # noqa: E402
from anki_addon_store.core import ankiweb_proto, catalog, classifier, i18n  # noqa: E402


def _make_list_payload(entries: list[dict]) -> bytes:
    buf = bytearray()
    for e in entries:
        item = bytearray()
        item.extend(ankiweb_proto.encode_field_varint(1, e["id"]))
        item.extend(ankiweb_proto.encode_field_bytes(2, e["title"].encode("utf-8")))
        item.extend(ankiweb_proto.encode_field_varint(3, e["likes"]))
        item.extend(ankiweb_proto.encode_field_varint(4, e["dislikes"]))
        item.extend(ankiweb_proto.encode_field_varint(5, e["modified"]))
        item.extend(ankiweb_proto.encode_field_varint(6, e["max_pv"]))
        buf.extend(ankiweb_proto.encode_field_bytes(1, bytes(item)))
    return bytes(buf)


def _make_item_info_payload(info: dict) -> bytes:
    inner = bytearray()
    for rev in info.get("reviews", []):
        r = bytearray()
        r.extend(ankiweb_proto.encode_field_varint(1, rev["created"]))
        if rev.get("positive"):
            r.extend(ankiweb_proto.encode_field_varint(2, 1))
        r.extend(ankiweb_proto.encode_field_bytes(4, rev["text"].encode("utf-8")))
        if rev.get("author_reply"):
            r.extend(ankiweb_proto.encode_field_bytes(5, rev["author_reply"].encode("utf-8")))
            r.extend(ankiweb_proto.encode_field_varint(6, rev.get("reply_created", 0)))
        inner.extend(ankiweb_proto.encode_field_bytes(1, bytes(r)))
    inner.extend(ankiweb_proto.encode_field_bytes(5, info["title"].encode("utf-8")))
    inner.extend(ankiweb_proto.encode_field_bytes(6, info["tags"].encode("utf-8")))
    inner.extend(ankiweb_proto.encode_field_varint(7, info["size_bytes"]))
    inner.extend(ankiweb_proto.encode_field_varint(8, info["modified"]))
    inner.extend(ankiweb_proto.encode_field_bytes(9, info["desc_html"].encode("utf-8")))
    if info.get("support_url"):
        inner.extend(ankiweb_proto.encode_field_bytes(12, info["support_url"].encode("utf-8")))
    branches_outer = bytearray()
    for br in info.get("branches", []):
        b = ankiweb_proto.encode_field_bytes(1, br["range"].encode("utf-8")) + ankiweb_proto.encode_field_varint(2, br["mod"])
        branches_outer.extend(ankiweb_proto.encode_field_bytes(3, b))
    if branches_outer:
        inner.extend(ankiweb_proto.encode_field_bytes(11, bytes(branches_outer)))
    inner.extend(ankiweb_proto.encode_field_varint(18, info["likes"]))
    inner.extend(ankiweb_proto.encode_field_varint(19, info["dislikes"]))
    return ankiweb_proto.encode_field_bytes(1, bytes(inner))


class SyntaxAndPurityTests(unittest.TestCase):
    def test_all_python_files_parse_cleanly(self):
        py_files = []
        for dirpath, _dirs, names in os.walk(PKG_DIR):
            for name in names:
                if name.endswith(".py"):
                    py_files.append(os.path.join(dirpath, name))
        self.assertGreaterEqual(len(py_files), 8)
        for path in py_files:
            with open(path, "r", encoding="utf-8") as fh:
                ast.parse(fh.read(), filename=path)

    def test_core_never_imports_anki_or_qt(self):
        core_dir = os.path.join(PKG_DIR, "core")
        for name in os.listdir(core_dir):
            if not name.endswith(".py"):
                continue
            path = os.path.join(core_dir, name)
            with open(path, "r", encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(alias.name.startswith(("aqt", "anki", "PyQt")))
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertFalse(node.module.startswith(("aqt", "anki", "PyQt")))


class ProtoAndVersionTests(unittest.TestCase):
    def test_decode_list_addons_and_negative_point_version(self):
        raw = _make_list_payload([
            {"id": 1771074083, "title": "Review Heatmap", "likes": 2290, "dislikes": 42, "modified": 1790000000, "max_pv": 250205},
            {"id": 999, "title": "Old Addon", "likes": 10, "dislikes": 5, "modified": 1600000000, "max_pv": -215000},
        ])
        items = ankiweb_proto.decode_list_addons(raw)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["max_version"], "25.02.5~")
        self.assertEqual(items[1]["max_pv"], -215000)
        self.assertEqual(items[1]["max_version"], "-21.50")

    def test_decode_item_info_sanitizes_html_and_extracts_github(self):
        raw = _make_item_info_payload({
            "likes": 100,
            "dislikes": 2,
            "title": "Demo Addon",
            "tags": "sync fsrs",
            "size_bytes": 12345,
            "modified": 1795000000,
            "desc_html": '<p>Hi</p><script>alert(1)</script><a href="javascript:evil()" onclick="x()">bad</a><a href="https://github.com/user/demo-repo/issues">repo</a>',
            "support_url": "https://forums.ankiweb.net/t/demo/1",
            "branches": [{"range": "23.10-26.09+", "mod": 1795000000}],
            "reviews": [
                {"created": 1795000001, "positive": True, "text": "Great!", "author_reply": "Thanks!", "reply_created": 1795000100},
                {"created": 1795000002, "positive": False, "text": "Broken on 26.09"},
            ],
        })
        detail = ankiweb_proto.decode_item_info(raw, addon_id=42)
        self.assertEqual(detail["id"], 42)
        self.assertEqual(detail["likes"], 100)
        self.assertEqual(detail["dislikes"], 2)
        self.assertEqual(detail["tags"], ["sync", "fsrs"])
        self.assertEqual(detail["support_url"], "https://forums.ankiweb.net/t/demo/1")
        self.assertEqual(detail["branches"][0]["version_range"], "23.10-26.09+")
        self.assertEqual(len(detail["reviews"]), 2)
        self.assertTrue(detail["reviews"][0]["positive"])
        self.assertEqual(detail["reviews"][0]["author_reply"], "Thanks!")
        self.assertFalse(detail["reviews"][1]["positive"])
        self.assertEqual(detail["github_url"], "https://github.com/user/demo-repo")
        self.assertNotIn("<script", detail["description_html"].lower())
        self.assertNotIn("onclick", detail["description_html"].lower())
        self.assertNotIn("javascript:", detail["description_html"].lower())

    def test_version_and_compatibility(self):
        self.assertEqual(ankiweb_proto.parse_version_to_point("26.09.4"), 260904)
        self.assertEqual(ankiweb_proto.parse_version_to_point("23.10"), 231000)
        self.assertEqual(ankiweb_proto.parse_version_to_point("2.1.66"), 66)
        self.assertEqual(ankiweb_proto.evaluate_compatibility(260903, 260904), "compatible")
        self.assertEqual(ankiweb_proto.evaluate_compatibility(54, 260904), "likely")
        self.assertEqual(ankiweb_proto.evaluate_compatibility(45, 260904), "legacy")
        self.assertEqual(ankiweb_proto.evaluate_compatibility(-231000, 260904), "incompatible")
        self.assertEqual(ankiweb_proto.evaluate_compatibility(-260904, 260904), "compatible")


class ClassifierAndCatalogTests(unittest.TestCase):
    def test_classifier_and_curated_overrides(self):
        items = classifier.enrich_items([
            {"id": 1771074083, "title": "Review Heatmap", "likes": 2000, "dislikes": 40, "modified": 1790000000, "max_pv": 54},
            {"id": 12345, "title": "HyperTTS Speech Pronunciation", "likes": 50, "dislikes": 5, "modified": 1790000000, "max_pv": 250200},
            {"id": 54321, "title": "Random Widget", "likes": 1, "dislikes": 0, "modified": 1790000000, "max_pv": 250200},
            {"id": 99999, "title": "Cristal Memoria | Science Based Anki Addictive Game", "likes": 400, "dislikes": 10, "modified": 1790000000, "max_pv": 260801},
        ])
        self.assertEqual(items[0]["category"], "stats")
        self.assertTrue(items[0]["summary_zh"])
        self.assertEqual(items[1]["category"], "language")
        self.assertEqual(items[2]["category"], "tools")
        self.assertEqual(items[3]["category"], "stats")
        self.assertEqual(items[0]["net_score"], 1960)

    def test_hybrid_catalog_static_fallback_and_cache(self):
        now = 1795656000
        proto_raw = _make_list_payload([
            {"id": 1771074083, "title": "Review Heatmap", "likes": 200, "dislikes": 5, "modified": now - 10 * 86400, "max_pv": 250200},
            {"id": 2055492159, "title": "AnkiConnect", "likes": 500, "dislikes": 10, "modified": now - 1500 * 86400, "max_pv": -215000},
        ])
        static_gz = gzip.compress(json.dumps({"items": [{"id": 1, "title": "Static One", "likes": 9, "dislikes": 1, "modified": now, "max_pv": 260900}]}).encode("utf-8"))

        with tempfile.TemporaryDirectory() as tmp:
            # 1. Static .json.gz works
            res1 = catalog.fetch_catalog(
                catalog_url="https://example.com/catalog.json.gz",
                cache_dir=tmp,
                http_get=lambda _u: static_gz,
                now_ts=now,
            )
            self.assertEqual(res1["source"], "static")
            self.assertEqual(len(res1["items"]), 1)

            # 2. Cache hit without network
            res2 = catalog.fetch_catalog(
                catalog_url="https://example.com/catalog.json.gz",
                cache_dir=tmp,
                http_get=lambda _u: (_ for _ in ()).throw(RuntimeError("offline")),
                now_ts=now + 60,
            )
            self.assertEqual(res2["source"], "cache")

            # 3. Force refresh with broken static URL -> falls back cleanly to AnkiWeb protobuf
            def _fake_http(u: str) -> bytes:
                if "example.com" in u:
                    raise RuntimeError("404")
                return proto_raw

            res3 = catalog.fetch_catalog(
                catalog_url="https://example.com/catalog.json.gz",
                cache_dir=tmp,
                force_refresh=True,
                http_get=_fake_http,
                now_ts=now + 120,
            )
            self.assertEqual(res3["source"], "ankiweb")
            self.assertEqual(len(res3["items"]), 2)

            filtered = catalog.filter_and_sort(
                res3["items"],
                query="heat",
                compat_only=True,
                active_only=True,
                installed_ids={"1771074083": {"module_id": "1771074083", "enabled": True}},
                current_pv=260904,
                now_ts=now,
            )
            self.assertEqual(len(filtered), 1)
            self.assertTrue(filtered[0]["installed"])

    def test_bundled_seed_catalog_loads(self):
        seed = catalog.load_seed_catalog()
        self.assertIsNotNone(seed)
        self.assertEqual(seed["source"], "seed")
        self.assertGreater(len(seed["items"]), 1000)

    def test_sort_asc_and_desc_across_modes(self):
        items = classifier.enrich_items([
            {"id": 1, "title": "Bravo", "likes": 100, "dislikes": 0, "modified": 200, "max_pv": 260900},
            {"id": 2, "title": "Alpha", "likes": 10, "dislikes": 10, "modified": 300, "max_pv": 260900},
            {"id": 3, "title": "Charlie", "likes": 0, "dislikes": 0, "modified": 100, "max_pv": 260900},
        ])
        self.assertEqual([x["title"] for x in catalog.filter_and_sort(items, sort_by="popular", sort_dir="desc")], ["Bravo", "Alpha", "Charlie"])
        self.assertEqual([x["title"] for x in catalog.filter_and_sort(items, sort_by="popular", sort_dir="asc")], ["Charlie", "Alpha", "Bravo"])
        self.assertEqual([x["title"] for x in catalog.filter_and_sort(items, sort_by="updated", sort_dir="asc")], ["Charlie", "Bravo", "Alpha"])
        self.assertEqual([x["title"] for x in catalog.filter_and_sort(items, sort_by="name", sort_dir="asc")], ["Alpha", "Bravo", "Charlie"])
        self.assertEqual([x["title"] for x in catalog.filter_and_sort(items, sort_by="name", sort_dir="desc")], ["Charlie", "Bravo", "Alpha"])
        # Rating keeps unrated (Charlie) at end in both directions
        self.assertEqual([x["title"] for x in catalog.filter_and_sort(items, sort_by="rating", sort_dir="desc")], ["Bravo", "Alpha", "Charlie"])
        self.assertEqual([x["title"] for x in catalog.filter_and_sort(items, sort_by="rating", sort_dir="asc")], ["Alpha", "Bravo", "Charlie"])


class I18nAndBridgeTests(unittest.TestCase):
    def test_i18n_strings_complete_and_matching_placeholders(self):
        self.assertEqual(i18n.resolve_lang("auto", "zh_CN"), "zh")
        self.assertEqual(i18n.resolve_lang("auto", "en_US"), "en")
        self.assertEqual(i18n.resolve_lang("en", "zh_CN"), "en")
        fmt = string.Formatter()
        for key, entry in i18n.STRINGS.items():
            self.assertTrue(entry.get("zh", "").strip(), f"{key} zh empty")
            self.assertTrue(entry.get("en", "").strip(), f"{key} en empty")
            zh_f = {f for _, f, _, _ in fmt.parse(entry["zh"]) if f is not None}
            en_f = {f for _, f, _, _ in fmt.parse(entry["en"]) if f is not None}
            self.assertEqual(zh_f, en_f, f"{key} mismatch")

    def test_fake_addon_manager_bridge(self):
        class FakeMgr:
            def __init__(self):
                self.addons = {"1771074083": {"name": "Review Heatmap", "enabled": True}}

            def allAddons(self):
                return list(self.addons.keys())

            def isEnabled(self, mid):
                return self.addons[mid]["enabled"]

            def addonName(self, mid):
                return self.addons[mid]["name"]

            def toggleEnabled(self, mid):
                self.addons[mid]["enabled"] = not self.addons[mid]["enabled"]

            def deleteAddon(self, mid):
                self.addons.pop(mid, None)

        mgr = FakeMgr()
        inst = addon_bridge.list_installed_addons(mgr)
        self.assertTrue(inst["1771074083"]["enabled"])
        self.assertFalse(addon_bridge.toggle_addon(mgr, "1771074083"))
        addon_bridge.delete_addon(mgr, "1771074083")
        self.assertEqual(addon_bridge.list_installed_addons(mgr), {})

    def test_detail_cache_invalidates_old_schema_without_reviews(self):
        raw = _make_item_info_payload({
            "likes": 5,
            "dislikes": 0,
            "title": "Heatmap",
            "tags": "stats",
            "size_bytes": 1000,
            "modified": 1795000000,
            "desc_html": "<p>Desc</p>",
            "reviews": [{"created": 1795000001, "positive": True, "text": "Awesome"}],
        })
        now = 1795656000
        with tempfile.TemporaryDirectory() as tmp:
            det_dir = os.path.join(tmp, "details")
            os.makedirs(det_dir, exist_ok=True)
            with open(os.path.join(det_dir, "1771074083.json"), "w", encoding="utf-8") as fh:
                json.dump({"id": 1771074083, "fetched_at": now - 10, "title": "Old Cached"}, fh)

            calls = {"n": 0}
            def _http(_u: str) -> bytes:
                calls["n"] += 1
                return raw

            res1 = addon_bridge.fetch_addon_detail(1771074083, cache_dir=tmp, http_get=_http, now_ts=now)
            self.assertEqual(calls["n"], 1)
            self.assertEqual(len(res1["reviews"]), 1)

            res2 = addon_bridge.fetch_addon_detail(1771074083, cache_dir=tmp, http_get=_http, now_ts=now + 60)
            self.assertEqual(calls["n"], 1)
            self.assertEqual(res2["reviews"][0]["text"], "Awesome")


if __name__ == "__main__":
    unittest.main()
