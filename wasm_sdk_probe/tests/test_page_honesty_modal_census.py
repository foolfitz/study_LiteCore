"""The visible Markdown entry opens a modal; its click does not edit the document.

Use the committed, unchanged-runner witness from host 0.2.33. Other controls,
including a future control added by the page, must retain census coverage and
mutation checks. Read-only disabling of the entry remains mandatory.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "wasm_sdk_probe/tools"))
import check_m3_page_honesty as honesty


class ModalCensus(unittest.TestCase):
    def setUp(self):
        witness = ROOT / "findings/evidence/m3-page-honesty/shakedown/2026-10-24T190507+0000.json"
        self.writable = json.loads(witness.read_text())["runs"][0]

    def test_existing_modal_witness_is_not_an_edit_failure(self):
        self.assertEqual(honesty.score_arm(self.writable), [])

    def test_census_can_omit_the_named_modal_entry(self):
        run = copy.deepcopy(self.writable)
        run["census"] = [row for row in run["census"] if row["item"] != "paste-markdown"]
        self.assertEqual(honesty.score_arm(run), [])

    def test_a_future_mutating_control_still_has_to_advance(self):
        run = copy.deepcopy(self.writable)
        run["controlsAtCensus"].append({"action": "future-edit-action", "mutates": "1", "hidden": False})
        row = {"item": "future-edit-action", "revisionBefore": 9, "revisionAfter": 9, "latency": "ready"}
        run["census"].append(row)
        self.assertTrue(any("future-edit-action did not advance" in p for p in honesty.score_arm(run)))
        row["revisionAfter"] = 10
        self.assertFalse(any("future-edit-action" in p for p in honesty.score_arm(run)))

    def test_an_uncovered_edit_button_still_fails(self):
        run = copy.deepcopy(self.writable)
        run["census"] = [row for row in run["census"] if row["item"] != "set-italic"]
        self.assertTrue(any("V2 census:" in p and "set-italic" in p for p in honesty.score_arm(run)))

    def test_readonly_disabling_of_markdown_still_has_to_hold(self):
        prior = ROOT / "findings/evidence/m3-page-honesty/runs/2026-10-18T175135+0000.json"
        run = next(r for r in json.loads(prior.read_text())["runs"] if r["arm"] == "Vro")
        self.assertEqual(honesty.score_arm(run), [])
        button = next(c for c in run["controls"] if c["action"] == "paste-markdown")
        button["disabled"] = False
        self.assertTrue(any("V7 paste-markdown:" in p for p in honesty.score_arm(run)))


if __name__ == "__main__":
    unittest.main()
