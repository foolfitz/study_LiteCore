#!/usr/bin/env python3
"""SPEC-M3-link-batch-v24 6.1 W1: the v24 worker is the archived v23 worker
plus a closed list of hunks, each labelled with its section 4.2 item.

The list lives in tests/v24-worker-delta.json.  Applying it, in order, to the
archived v23 worker must give sdk/v24-feature-worker.js byte for byte, so a
change outside the list is red here, and every listed hunk must still apply
(a hunk that no longer matches is red too).  Every item 1-6 has a hunk.
"""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/sdk-worker.js"
BASE_SHA256 = "3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5"
CANDIDATE = Path(os.environ.get("V24_W1_WORKER", ROOT / "sdk/v24-feature-worker.js"))
DELTA = json.loads((ROOT / "tests/v24-worker-delta.json").read_text())


def apply(lines, hunks):
    out, cursor = [], 0
    for hunk in hunks:
        index, count = hunk["v23Index"], hunk["v23Lines"]
        if index < cursor:
            raise AssertionError("hunks out of order")
        out += lines[cursor:index]
        if "".join(lines[index:index + count]) != hunk["old"]:
            raise AssertionError(f"hunk for item {hunk['item']} no longer matches the v23 worker")
        out.append(hunk["new"])
        cursor = index + count
    return "".join(out + lines[cursor:])


class WorkerDelta(unittest.TestCase):
    def test_base_is_the_archived_v23_worker(self):
        self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(), BASE_SHA256)

    def test_every_item_has_a_hunk(self):
        named = {part for hunk in DELTA["hunks"] for part in hunk["item"].split()[0].split("+")}
        self.assertEqual(named, {"1", "2", "3", "4", "5", "6"})

    def test_candidate_is_base_plus_the_list(self):
        lines = BASE.read_text().splitlines(keepends=True)
        self.assertEqual(apply(lines, DELTA["hunks"]), CANDIDATE.read_text())


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
