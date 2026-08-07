from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from validate_r7_compatibility_corpus import validate_manifest  # noqa: E402
from run_r7_compatibility import (  # noqa: E402
    collect_browser_summary,
    firefox_batches,
    full_batches,
)


class R7CompatibilityCorpusTest(unittest.TestCase):
    def test_frozen_project_manifest_passes(self) -> None:
        project = Path(__file__).resolve().parent.parent
        manifest = project / "test-docs" / "r7-compat" / "manifest.json"
        if not manifest.is_file():
            self.skipTest("R7-C corpus has not been generated yet")
        result = validate_manifest(manifest)
        self.assertTrue(result["pass"], result)
        self.assertGreaterEqual(len(result["documents"]), 28)

    def test_invalid_schema_does_not_rewrite_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r7-c-validator-") as temporary:
            path = Path(temporary) / "manifest.json"
            original = {"schemaVersion": 99, "release": "wrong", "documents": []}
            path.write_text(json.dumps(original), encoding="utf-8")
            result = validate_manifest(path)
            self.assertFalse(result["pass"])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)

    def test_full_batches_cover_each_selected_document_once(self) -> None:
        documents = [
            {"id": "l0-control", "tier": "L0"},
            {"id": "l1-hyperlink-font-odt", "tier": "L1"},
            {"id": "l2-a", "tier": "L2"},
            {"id": "l2-b", "tier": "L2"},
            {"id": "l3-a", "tier": "L3"},
            {"id": "l4-a", "tier": "L4"},
        ]
        batches = full_batches(documents, 3)
        self.assertEqual([len(batch) for batch in batches], [3, 2])
        self.assertEqual(
            [item["id"] for batch in batches for item in batch],
            ["l1-hyperlink-font-odt", "l2-a", "l2-b", "l3-a", "l4-a"],
        )

    def test_firefox_batches_respect_worker_budget_and_exact_coverage(self) -> None:
        documents = [
            {"id": "l0-t1", "tier": "L0"},
            {"id": "l0-t2", "tier": "L0"},
            {"id": "l0-t3", "tier": "L0"},
            {"id": "l1-plain-odt", "tier": "L1"},
            {"id": "l1-plain-docx", "tier": "L1"},
            {"id": "l1-review-odt", "tier": "L1"},
        ]
        batches = firefox_batches(documents, "repeat")
        self.assertEqual([len(batch) for batch in batches], [2, 3, 1])
        self.assertEqual(
            [item["id"] for batch in batches for item in batch],
            [item["id"] for item in documents],
        )
        for batch in batches:
            worker_count = sum(
                2 if item["id"] == "l0-t2" else 1 for item in batch
            )
            self.assertLessEqual(worker_count, 3)

    def test_browser_summary_requires_the_complete_formal_matrix(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r7-c-summary-") as temporary:
            root = Path(temporary)
            for group, run in (("repeat", 1), ("repeat", 2), ("repeat", 3), ("full", 1)):
                path = root / group / f"run-{run}" / "result.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"pass": True}), encoding="utf-8")
            self.assertTrue(collect_browser_summary("firefox", root)["pass"])
            (root / "full" / "run-1" / "result.json").unlink()
            self.assertFalse(collect_browser_summary("firefox", root)["pass"])


if __name__ == "__main__":
    unittest.main()
