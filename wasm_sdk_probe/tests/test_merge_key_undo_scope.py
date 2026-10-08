"""M1-1's per-object judgement (`check_merge_key_undo_scope.judge_rows`), offline, on the rows of the
committed green run (findings/evidence/v19/pre-link/m1-1/green.json) and mutations of them.

    python3 -m unittest tests.test_merge_key_undo_scope
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_merge_key_undo_scope as c  # noqa: E402

GREEN = json.loads((Path(__file__).resolve().parents[2]
                    / "findings/evidence/v19/pre-link/m1-1/green.json").read_text())
RULES = sorted({r["rule"] for r in GREEN["rows"]})


def judged(change=None, carriers=c.CARRIERS):
    rows = copy.deepcopy(GREEN["rows"])
    if change:
        change(rows)
    return c.judge_rows(rows, carriers, RULES, "5d77dc84")


def row(rows, rule, name):
    return next(r for r in rows if r["rule"] == rule and r["object"].endswith(f"/{name}.o"))


class JudgeRows(unittest.TestCase):
    def test_the_green_run(self):
        self.assertEqual(judged(), [])
        self.assertEqual(GREEN["failures"], [])

    def test_red_another_object_of_a_carrier(self):
        # codex B7: B grows into sdk_api.cpp of v19.
        failures = judged(lambda rows: row(rows, "E2_V19", "sdk_api").update(same=False))
        self.assertEqual(len(failures), 1)
        self.assertIn("E2_V19 build/e2/editor-v19/sdk_api.o", failures[0])

    def test_red_a_carrier_without_b(self):
        failures = judged(lambda rows: row(rows, "E2_V19", "probe_engine").update(same=True))
        self.assertEqual(failures, ["E2_V19: its probe_engine object does not differ from 5d77dc84 (B is not in it)"])

    def test_red_v19_unlisted(self):
        failures = judged(carriers=("E2_V15",))
        self.assertEqual(len(failures), 1)
        self.assertIn("E2_V19 build/e2/editor-v19/probe_engine.o", failures[0])

    def test_red_any_other_rule(self):
        failures = judged(lambda rows: row(rows, "E2_V8", "editor_api").update(same=False))
        self.assertEqual(len(failures), 1)
        self.assertIn("E2_V8", failures[0])


if __name__ == "__main__":
    unittest.main()
