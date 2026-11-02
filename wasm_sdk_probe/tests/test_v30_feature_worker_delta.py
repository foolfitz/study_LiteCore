#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 D1: the v30 worker is the archived v29 worker plus a closed list of hunks.

The list lives in tests/v30-worker-delta.json.  Applying it, in order, to the archived worker must give
sdk/v30-extend-gate-worker.js byte for byte, so a change outside the list is red here and every listed hunk must still
apply.  (Derived from test_v28_feature_worker_delta.py.)
"""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "build/archive/e2-editor-v29-e61e5890-worker-a5df83db/sdk-worker.js"
BASE_SHA256 = "a5df83dbd0bd4df6b67b81d000da141910b76252fbf2bb8636d9a312edfffcba"
CANDIDATE = Path(os.environ.get("V30_D1_WORKER", ROOT / "sdk/v30-extend-gate-worker.js"))
DELTA = json.loads((ROOT / "tests/v30-worker-delta.json").read_text())


def apply(lines, hunks):
    out, cursor = [], 0
    for hunk in hunks:
        index, count = hunk["baseIndex"], hunk["baseLines"]
        if index < cursor:
            raise AssertionError("hunks out of order")
        out += lines[cursor:index]
        if "".join(lines[index:index + count]) != hunk["old"]:
            raise AssertionError(f"hunk for item {hunk['item']} no longer matches the v29 worker")
        out.append(hunk["new"])
        cursor = index + count
    return "".join(out + lines[cursor:])


class WorkerDelta(unittest.TestCase):
    def test_base_is_the_archived_v29_worker(self):
        self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(), BASE_SHA256)

    def test_every_item_has_a_hunk(self):
        self.assertEqual({hunk["item"].split()[0] for hunk in DELTA["hunks"]}, {"1", "2"})

    def test_candidate_is_base_plus_the_list(self):
        lines = BASE.read_text().splitlines(keepends=True)
        self.assertEqual(apply(lines, DELTA["hunks"]), CANDIDATE.read_text())


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
