#!/usr/bin/env python3
"""SPEC-M3-link-batch-v25 6.1 W1: the v25 worker is the archived v24 worker
plus a closed list of hunks, each labelled with its section 4.2 item.

The list lives in tests/v25-worker-delta.json.  Applying it, in order, to the
archived v24 worker must give sdk/v25-feature-worker.js byte for byte, so a
change outside the list is red here, and every listed hunk must still apply.
Every item 1-4 has a hunk.  (The shape of test_v24_feature_worker_delta.py.)
"""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "build/archive/e2-editor-v24-27615808-worker-41041fe7/sdk-worker.js"
BASE_SHA256 = "41041fe746b2355a1768bc774a10ac59802a8e359579618be405e3696f3b9461"
CANDIDATE = Path(os.environ.get("V25_W1_WORKER", ROOT / "sdk/v25-feature-worker.js"))
DELTA = json.loads((ROOT / "tests/v25-worker-delta.json").read_text())


def apply(lines, hunks):
    out, cursor = [], 0
    for hunk in hunks:
        index, count = hunk["v24Index"], hunk["v24Lines"]
        if index < cursor:
            raise AssertionError("hunks out of order")
        out += lines[cursor:index]
        if "".join(lines[index:index + count]) != hunk["old"]:
            raise AssertionError(f"hunk for item {hunk['item']} no longer matches the v24 worker")
        out.append(hunk["new"])
        cursor = index + count
    return "".join(out + lines[cursor:])


class WorkerDelta(unittest.TestCase):
    def test_base_is_the_archived_v24_worker(self):
        self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(), BASE_SHA256)

    def test_every_item_has_a_hunk(self):
        named = {hunk["item"].split()[0] for hunk in DELTA["hunks"]}
        self.assertEqual(named, {"1", "2", "3", "4"})

    def test_candidate_is_base_plus_the_list(self):
        lines = BASE.read_text().splitlines(keepends=True)
        self.assertEqual(apply(lines, DELTA["hunks"]), CANDIDATE.read_text())


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
