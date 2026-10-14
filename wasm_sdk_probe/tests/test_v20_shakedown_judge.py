"""The v20 shakedown judge's red cases (findings/evidence/link-batch/v20-shakedown/ARMS.md), offline.

Every mutation in `judge_v20_shakedown.mutations()` must turn its arm's verdict to the named one,
the synthetic PASS set must pass, P2-c's reader must read a lone size change as ESTABLISHED and an
empty trace as "not run", and the runner's span rule must agree with the native mixed-page string.

The §34.3 review (2026-10-14, `v20-shakedown/review/DISPOSITION.md`) added: the exit rule's own red
cases (a duplicate cell in either order, no expected page), E2's required six instances, P2's
`parts`, and the runner predicates the judge reads as booleans (`c1_clauses`, `reference_caret`,
`at_2s`), made red at the predicate.

    python3 -m unittest tests.test_v20_shakedown_judge
"""
from __future__ import annotations

import copy
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import judge_v20_shakedown as judge  # noqa: E402
import run_v20_shakedown as runner  # noqa: E402

PAGE = judge.SYNTHETIC_PAGE


def base_reports() -> list[dict]:
    return [judge.synthetic_report("chrome"), judge.synthetic_report("firefox")]


class SelfTest(unittest.TestCase):
    def test_every_red_case_goes_red(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = judge.self_test(verbose=True)
        self.assertEqual(code, 0, buffer.getvalue())

    def test_synthetic_set_passes_and_a_missing_browser_fails(self):
        code, lines = judge.judge_reports(base_reports(), PAGE)
        self.assertEqual(code, 0, lines[-1])
        code, lines = judge.judge_reports([judge.synthetic_report("chrome")], PAGE)
        self.assertEqual(code, 1)
        self.assertTrue(any(line.startswith("[firefox] p1-60: MISSING") for line in lines))

    def test_a_report_about_another_page_is_not_read(self):
        code, lines = judge.judge_reports(base_reports(), expect_page="0" * 64)
        self.assertEqual(code, 1)
        # Nothing of either report is judged: every bracketed line is the refusal or a MISSING cell.
        self.assertTrue(all(("is not read" in line or line.endswith(": MISSING"))
                            for line in lines if line.startswith("[")), lines)
        self.assertEqual(sum(1 for line in lines if "is not read" in line), 2)

    def test_an_arm_without_a_rule_fails(self):
        base = base_reports()
        base[0]["results"]["made-up-arm"] = {"ok": True}
        code, lines = judge.judge_reports(base, PAGE)
        self.assertEqual(code, 1)
        self.assertTrue(any("made-up-arm: no rule for an arm the runner declares" in line for line in lines))

    def test_parse_rects_refuses_a_torn_string(self):
        self.assertIsNone(runner.parse_rects("284, 284, 11906; 284, 17406, 16838, 11906"))
        self.assertEqual(runner.parse_rects(""), [])
        self.assertEqual(len(runner.parse_rects("284, 284, 11906, 16838; 284, 17406, 16838, 11906")), 2)

    def test_region_of_measures_the_view_on_paper(self):
        geometry = {"deskTop": 100.0, "deskBottom": 900.0, "paperTop": -500.0, "paperBottom": 10000.0,
                    "paperHeight": 10500.0}
        region = runner.region_of(geometry, 12474, 1027604)
        self.assertEqual(region["x"], 0)
        self.assertEqual(region["width"], 12474)
        self.assertAlmostEqual(region["y"], 600 * 1027604 / 10500, places=3)
        self.assertAlmostEqual(region["height"], 800 * 1027604 / 10500, places=3)
        self.assertIsNone(runner.region_of({**geometry, "deskBottom": 50.0}, 12474, 1027604))


class ReviewRedCases(unittest.TestCase):
    """§34.3 review, 2026-10-14: each case read PASS (or was unexercised) on the judge before the review."""

    def test_no_expected_page_is_not_a_verdict(self):
        code, lines = judge.judge_reports(base_reports(), None)
        self.assertEqual(code, 1)
        self.assertTrue(lines[0].startswith("VERDICT NOT GIVEN"), lines)

    def test_a_duplicate_cell_fails_in_either_order(self):
        bad, rerun = base_reports()[0], base_reports()[0]
        bad["results"]["p1-60"]["positions"][5]["text"] = "第 7 頁，共 60 頁"
        rerun["results"] = {"p1-60": rerun["results"]["p1-60"]}
        for order in ([bad, rerun], [rerun, bad]):
            code, lines = judge.judge_reports(order + [judge.synthetic_report("firefox")], PAGE)
            self.assertEqual(code, 1, lines[-1])
            self.assertTrue(any(line.startswith("[chrome] p1-60: DUPLICATE") for line in lines), lines)

    def test_e2_needs_all_six_instances(self):
        for name, mutate in (("hold raised", lambda e2: e2.update(hold={"error": "TimeoutError"})),
                             ("killed after two", lambda e2: e2.update(cases=e2["cases"][:2], hold=None)),
                             ("hold with no merge", lambda e2: e2["hold"].update(merges=0))):
            base = base_reports()
            mutate(base[0]["results"]["e2"])
            code, lines = judge.judge_reports(base, PAGE)
            self.assertEqual(code, 1, name)
            self.assertTrue(any(line.startswith("[chrome] e2: FAIL") for line in lines), (name, lines))
            self.assertTrue(any("instances judged" in line for line in lines), (name, lines))

    def test_p2_parts_must_equal_m(self):
        base = base_reports()
        base[0]["results"]["p2"]["remove"]["partsAt2s"] = None
        code, lines = judge.judge_reports(base, PAGE)
        self.assertEqual(code, 1)
        self.assertTrue(any("remove: parts None != expected 60" in line for line in lines), lines)

    def test_c1_clauses_read_the_fresh_selection_type_and_refuse_absent_values(self):
        answer = {"ok": True, "completion": "verified-boundary-noop", "changed": False, "rev": 0, "beforeRev": 0,
                  "boundaryNoop": {"waitedMs": 2251}}
        asked = {"answered": True, "ok": True,
                 "result": {"sel": {"collapsed": True, "n": 0, "observed": True}, "selectionType": "none"}}
        self.assertTrue(all(runner.c1_clauses(answer, asked, "1", "1", []).values()))
        fresh_text = {**asked, "result": {**asked["result"], "selectionType": "text"}}
        self.assertFalse(runner.c1_clauses(answer, fresh_text, "1", "1", [])["noSelectionAt500ms"])
        n_absent = {**asked, "result": {"sel": {"collapsed": True, "n": None}, "selectionType": "none"}}
        self.assertFalse(runner.c1_clauses(answer, n_absent, "1", "1", [])["noSelectionAt500ms"])
        self.assertFalse(runner.c1_clauses({**answer, "rev": None, "beforeRev": None}, asked, "1", "1", [])["revisionUnchanged"])
        self.assertFalse(runner.c1_clauses(answer, asked, "1", "1", ["任何一則提示"])["noToast"])
        self.assertFalse(runner.c1_clauses(answer, asked, "1", "2", [])["generationStays1"])

    def test_e2_reference_is_ordered_by_the_observer_sequence(self):
        a, b = {"x": 2684, "y": 7266, "width": 0, "height": 276}, {"x": 3000, "y": 7266, "width": 0, "height": 276}
        trace = [{"k": "ev", "s": 0, "g": 1, "t": 100.0, "caret": a, "seq": 10},
                 {"k": "rq", "s": 1, "g": 1, "t": 101.0, "rq": 5},
                 {"k": "ev", "s": 2, "g": 1, "t": 101.0, "caret": b, "seq": 11}]
        self.assertEqual(runner.reference_caret(trace, trace[1])["caret"], a)
        # Another generation's push is never the reference, whatever its order.
        self.assertIsNone(runner.reference_caret([{**trace[0], "g": 2}, trace[1]], trace[1]))

    def test_p2_at_2s_keeps_the_reply_parts_in_the_fallback(self):
        g = {"text": "第 60 頁，共 61 頁", "hidden": False}
        fallback = runner.at_2s(None, {"count": 61, "parts": 60}, g, 61)
        self.assertEqual((fallback["countAt2s"], fallback["partsAt2s"], fallback["pass"]), (61, 60, False))
        direct = runner.at_2s({"rects": "; ".join(["284, 284, 11906, 16838"] * 61), "parts": 61},
                              {"count": 1, "parts": 1}, g, 61)
        self.assertEqual((direct["countAt2s"], direct["partsAt2s"], direct["pass"]), (61, 61, True))


if __name__ == "__main__":
    unittest.main()
