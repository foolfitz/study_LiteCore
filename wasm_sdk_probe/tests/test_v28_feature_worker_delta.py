#!/usr/bin/env python3
"""SPEC-M3-v28-last-line-fallback 7.2 W1: the v28 worker is the archived v27 worker
plus a closed list of hunks, each labelled with its section 4.2 item.

The list lives in tests/v28-worker-delta.json.  Applying it, in order, to the
archived v27 worker must give sdk/v28-last-block-worker.js byte for byte, so a
change outside the list is red here, and every listed hunk must still apply.
Every item 1-3 has a hunk.  (Derived from test_v27_feature_worker_delta.py.)
"""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "build/archive/e2-editor-v27-c089dfd6-worker-8152448a/sdk-worker.js"
BASE_SHA256 = "8152448ab83bc323edfa6982a1db08c4367b15b4c99978eeb1b39b3ef41a669d"
CANDIDATE = Path(os.environ.get("V28_W1_WORKER", ROOT / "sdk/v28-last-block-worker.js"))
DELTA = json.loads((ROOT / "tests/v28-worker-delta.json").read_text())


def apply(lines, hunks):
    out, cursor = [], 0
    for hunk in hunks:
        index, count = hunk["v27Index"], hunk["v27Lines"]
        if index < cursor:
            raise AssertionError("hunks out of order")
        out += lines[cursor:index]
        if "".join(lines[index:index + count]) != hunk["old"]:
            raise AssertionError(f"hunk for item {hunk['item']} no longer matches the v27 worker")
        out.append(hunk["new"])
        cursor = index + count
    return "".join(out + lines[cursor:])


class WorkerDelta(unittest.TestCase):
    def test_base_is_the_archived_v27_worker(self):
        self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(), BASE_SHA256)

    def test_every_item_has_a_hunk(self):
        named = {hunk["item"].split()[0] for hunk in DELTA["hunks"]}
        self.assertEqual(named, {"1", "2", "3"})

    def test_candidate_is_base_plus_the_list(self):
        lines = BASE.read_text().splitlines(keepends=True)
        self.assertEqual(apply(lines, DELTA["hunks"]), CANDIDATE.read_text())


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
