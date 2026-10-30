#!/usr/bin/env python3
"""SPEC-M3-v27-finding-176 7.2 W1: the v27 worker is the archived v26 worker
plus a closed list of hunks, each labelled with its section 4.2 item.

The list lives in tests/v27-worker-delta.json.  Applying it, in order, to the
archived v26 worker must give sdk/v27-first-block-worker.js byte for byte, so a
change outside the list is red here, and every listed hunk must still apply.
Every item 1-3 has a hunk.  (Derived from test_v25_feature_worker_delta.py.)
"""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "build/archive/e2-editor-v26-44cb15ea-worker-95d6e7ae/sdk-worker.js"
BASE_SHA256 = "95d6e7ae375e60ef58de3e1bbeb838f0d4922a0d4737287b262c23f595aed964"
CANDIDATE = Path(os.environ.get("V27_W1_WORKER", ROOT / "sdk/v27-first-block-worker.js"))
DELTA = json.loads((ROOT / "tests/v27-worker-delta.json").read_text())


def apply(lines, hunks):
    out, cursor = [], 0
    for hunk in hunks:
        index, count = hunk["v26Index"], hunk["v26Lines"]
        if index < cursor:
            raise AssertionError("hunks out of order")
        out += lines[cursor:index]
        if "".join(lines[index:index + count]) != hunk["old"]:
            raise AssertionError(f"hunk for item {hunk['item']} no longer matches the v26 worker")
        out.append(hunk["new"])
        cursor = index + count
    return "".join(out + lines[cursor:])


class WorkerDelta(unittest.TestCase):
    def test_base_is_the_archived_v26_worker(self):
        self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(), BASE_SHA256)

    def test_every_item_has_a_hunk(self):
        named = {hunk["item"].split()[0] for hunk in DELTA["hunks"]}
        self.assertEqual(named, {"1", "2", "3"})

    def test_candidate_is_base_plus_the_list(self):
        lines = BASE.read_text().splitlines(keepends=True)
        self.assertEqual(apply(lines, DELTA["hunks"]), CANDIDATE.read_text())


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
