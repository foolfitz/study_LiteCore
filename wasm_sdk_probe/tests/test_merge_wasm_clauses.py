"""The merge WASM runner's clauses (SPEC-M3-paragraph-merge 22.1), offline.

The comparator red cases spec 10.2 asks for (one per assertion) and the two
the review of 5555e554 found missing: the marker check that inverted when the
marker was lost (B3), and "not changed" said after the key went out.  Built
from the native R0c data, so a clause is tested against the references it
will meet in a run.

    python3 -m unittest tests.test_merge_wasm_clauses
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_merge_wasm_shakedown as m  # noqa: E402

CASES = m.tool_cases(frame_cell=False)
DOCS = m.EVIDENCE / "r0c/round-20261006T144628Z/docs"


def observed_merge(case: str, *, key_doc: Path | None = None, comment: str | None = None,
                   presses: int = 0) -> dict:
    """What the runner records for a correct merge, built from the native arms."""
    spec = CASES[case]
    key_doc = key_doc or spec["key"]
    return {"outcome": "verified-key-undo",
            "keyUndo": {"comment": spec["nativeComment"] if comment is None else comment,
                        "restorePresses": presses},
            "generation": ["1", "1"], "toasts": [],
            "afterKeyDocument": m.compare(key_doc.read_bytes(), spec["key"], False),
            "followDocument": m.compare(spec["follow"].read_bytes(), spec["follow"], False)}


def verdict(clauses: dict) -> bool:
    return all(v for v in clauses.values() if v is not None)


class MergeClauses(unittest.TestCase):
    def test_the_native_key_arm_passes(self):
        for case in ("C01", "C03", "I02", "C11", "Y01"):
            clauses = m.merge_clauses(observed_merge(case), CASES[case])
            self.assertTrue(verdict(clauses), (case, clauses))
            if CASES[case]["decision"] == "typed-merge":
                self.assertIsNone(clauses["afterKeyBytes"], "spec 12: typed text compares by text")
            else:
                self.assertTrue(clauses["afterKeyBytes"], case)

    def test_red_the_select_arm_is_not_the_key(self):
        # 10.2: C03's native select-arm document as what the page saved.
        clauses = m.merge_clauses(observed_merge("C03", key_doc=DOCS / "r1-C03-select.odt"),
                                  CASES["C03"])
        self.assertFalse(clauses["afterKeyText"])
        self.assertFalse(clauses["afterKeyBytes"])
        self.assertFalse(verdict(clauses))

    def test_red_a_different_undo_comment(self):
        clauses = m.merge_clauses(observed_merge("C11", comment="Delete paragraph"), CASES["C11"])
        self.assertFalse(clauses["comment"])
        self.assertFalse(verdict(clauses))

    def test_red_a_restore_press(self):
        # 22.1: the E shape has none; a 2 is the replaced prescription back.
        clauses = m.merge_clauses(observed_merge("I02", presses=2), CASES["I02"])
        self.assertFalse(clauses["restorePresses"])
        self.assertFalse(verdict(clauses))


def observed_refusal(case: str, toasts: list[str], *, generation=("1", "2"),
                     checkpoint="有（r2）") -> dict:
    spec = CASES[case]
    _, stage, posted = spec["expected"]
    return {"outcome": "refused", "stage": stage, "keyPosted": posted,
            "generation": list(generation),
            "toastWindow": {"closed": True, "generation": generation[1], "toasts": toasts},
            "beforeKey": {"revision": "2"}, "afterKey": {"checkpoint": checkpoint}}


class RefusalClauses(unittest.TestCase):
    def setUp(self):
        self.original = m.odt_parts(CASES["C17"]["original"].read_bytes())["paragraphs"]
        target = m.native_cases("boundaries")["C01"]["search"]
        self.expected = [p + m.MARKER if p == target else p for p in self.original]
        self.reopen = ["這裡目前還不能這樣刪除。文件沒有被改動，正在重新載入…",
                       "這裡目前還不能這樣刪除。文件沒有被改動，已重新載入。"]

    def test_a_kept_marker_passes(self):
        clauses = m.refusal_clauses(observed_refusal("C17", self.reopen), CASES["C17"],
                                    self.expected, self.expected)
        self.assertTrue(verdict(clauses), clauses)

    def test_red_a_lost_marker(self):
        # B3: the page reopened the original without the marker.
        clauses = m.refusal_clauses(observed_refusal("C17", self.reopen), CASES["C17"],
                                    self.expected, list(self.original))
        self.assertFalse(clauses["reopenedText"])
        self.assertFalse(clauses["markerSurvived"])

    def test_red_not_changed_after_the_key_went_out(self):
        said = ["這一下刪除送出了，但沒能確認它做了什麼，正在重新載入…",
                "文件沒有被改動，已重新載入。"]
        clauses = m.refusal_clauses(observed_refusal("C15", said), CASES["C15"],
                                    self.expected, self.expected)
        self.assertFalse(clauses["noUnchanged"])

    def test_red_a_third_toast(self):
        toasts = [self.reopen[0], "重繪失敗：ENGINE_DISPOSED：engine is disposed", self.reopen[1]]
        clauses = m.refusal_clauses(observed_refusal("C17", toasts), CASES["C17"],
                                    self.expected, self.expected)
        self.assertFalse(clauses["onlyTheReopenToasts"])

    def test_red_a_repeated_reopen_sentence(self):
        # The count, not only the wording: a duplicated sentence (two repaint
        # loops at once, review N4) is a toast the user did not need.
        toasts = [self.reopen[0], self.reopen[1], self.reopen[1]]
        clauses = m.refusal_clauses(observed_refusal("C17", toasts), CASES["C17"],
                                    self.expected, self.expected)
        self.assertFalse(clauses["onlyTheReopenToasts"])

    def test_red_no_reopen(self):
        clauses = m.refusal_clauses(observed_refusal("C17", self.reopen, generation=("1", "1")),
                                    CASES["C17"], self.expected, self.expected)
        self.assertFalse(clauses["generation"])


ROOT = (b'<office:document-content xmlns:b="u2" xmlns:a="u1" office:version="1.4">'
        b'<office:body><office:text><office:forms form:automatic-focus="false" '
        b'form:apply-design-mode="false"/><text:p>ab<text:soft-page-break/>cd</text:p>'
        b'</office:text></office:body></office:document-content>')


class Reduction(unittest.TestCase):
    """Spec 24: M2-0's three operations, and nothing they should not do."""

    def test_the_three_differences_reduce_away(self):
        other = (ROOT.replace(b'xmlns:b="u2" xmlns:a="u1"', b'xmlns:a="u1" xmlns:b="u2"')
                 .replace(b'<office:forms form:automatic-focus="false" '
                          b'form:apply-design-mode="false"/>', b"")
                 .replace(b"ab<text:soft-page-break/>cd", b"abc<text:soft-page-break/>d"))
        self.assertNotEqual(ROOT, other)
        self.assertEqual(m.reduce_content(ROOT), m.reduce_content(other))

    def test_red_a_namespace_value_text_or_attribute_still_differs(self):
        for changed in (ROOT.replace(b'"u2"', b'"u3"'), ROOT.replace(b"cd</text:p>", b"cx</text:p>"),
                        ROOT.replace(b'office:version="1.4"', b'office:version="1.3"'),
                        ROOT.replace(b"<text:p>", b'<text:p text:style-name="P1">')):
            self.assertNotEqual(m.reduce_content(ROOT), m.reduce_content(changed))

    def test_no_case_collapses(self):
        # 10.2: the reduction is refused if it makes any case's native
        # before-key and key-arm documents equal.
        self.assertEqual(m.reduction_collapses(), [])

    def test_no_root_is_an_error(self):
        with self.assertRaises(ValueError):
            m.reduce_content(b"<office:document-styles/>")


class List(unittest.TestCase):
    def test_the_list_is_the_tool_closed_population(self):
        counts = {}
        for spec in CASES.values():
            counts[spec["criterion"]] = counts.get(spec["criterion"], 0) + 1
        self.assertEqual(counts, {"M2-1": 20, "M2-3": 5, "barrier": 1})   # spec 25

    def test_an_unknown_decision_stops(self):
        with self.assertRaises(SystemExit):
            m.expectation("something-new")


class Schedules(unittest.TestCase):
    """Spec 30.2: a criterion run's cases and rounds come from the tool list alone."""

    def test_each_mode(self):
        self.assertEqual(m.mode_schedule("counted", CASES), (list(CASES), 3))
        self.assertEqual(m.mode_schedule("m2-1b", CASES), (["Y01", "Y02"], 10))
        self.assertEqual(m.mode_schedule("m2-1-red", CASES), (["C01", "C02", "C03"], 1))
        self.assertEqual(m.mode_schedule("m2-4", CASES), ([], 1))

    def test_red_no_typed_merge_case_stops(self):
        without = {c: s for c, s in CASES.items() if s["decision"] != "typed-merge"}
        with self.assertRaises(SystemExit):
            m.mode_schedule("m2-1b", without)

    def test_nothing_is_bound_before_v56(self):
        # Spec 7 / 30.1: the binding is written after shell generation v56 is frozen; until then no report may
        # say "counted": true.  When BINDING is set this test is updated with it, in the same commit.
        self.assertIsNone(m.BINDING)


LIMIT = m.limit_reference() if m.LIMIT_ROUND.is_dir() else None


@unittest.skipIf(LIMIT is None, "R0 run 4's documents are not under build/")
class LimitClauses(unittest.TestCase):
    """Spec 30.2 M2-4, built from R0 run 4's own documents."""

    def observed(self, *, presses=None, final=None, toasts=None, generation=("1", "1"), control=False):
        if presses is None:
            presses = [{"press": n, "ok": True, "completion": "verified-key-undo", "comment": "Delete paragraph",
                        "restorePresses": 0, "actionsAfter": min(n, m.LIMIT_STEPS),
                        "keyToUndoMs": 40, "keyToResponseMs": 140.5}
                       for n in range(1, m.LIMIT_PRESSES + 1)]
        final = LIMIT["final"] if final is None else final
        return {"presses": presses, "generation": list(generation), "toasts": [] if toasts is None else toasts,
                "control": control, "finalDocument": m.compare(final.read_bytes(), LIMIT["final"], False)}

    def test_the_reference(self):
        self.assertEqual(LIMIT["caret"], [1791, 1418, 0, 276])
        self.assertEqual(LIMIT["fixtureSha256"][:8], "09b5ced0")

    def test_the_native_run_passes(self):
        clauses = m.limit_clauses(self.observed())
        self.assertTrue(verdict(clauses), clauses)

    def test_red_stopped_early(self):
        presses = self.observed()["presses"][:50]
        presses[-1] = {**presses[-1], "ok": False, "completion": None}
        clauses = m.limit_clauses(self.observed(presses=presses))
        self.assertFalse(clauses["presses"])
        self.assertFalse(clauses["everyPressVerified"])

    def test_red_the_limit_never_reached(self):
        presses = [{**p, "actionsAfter": min(p["actionsAfter"], 99)} for p in self.observed()["presses"]]
        self.assertFalse(m.limit_clauses(self.observed(presses=presses))["limitReached"])

    def test_red_the_count_falls_after_the_limit(self):
        presses = self.observed()["presses"]
        presses[102] = {**presses[102], "actionsAfter": 99}
        self.assertFalse(m.limit_clauses(self.observed(presses=presses))["limitReached"])

    def test_red_one_other_comment(self):
        presses = self.observed()["presses"]
        presses[103] = {**presses[103], "comment": "Delete “b”"}
        self.assertFalse(m.limit_clauses(self.observed(presses=presses))["comment"])

    def test_red_the_document_after_104_presses(self):
        doc = m.LIMIT_ROUND / "docs" / f"r1-{m.LIMIT_CASE}-key104.odt"
        clauses = m.limit_clauses(self.observed(final=doc))
        self.assertFalse(clauses["finalBytes"])
        self.assertFalse(clauses["finalText"])

    def test_red_a_toast_and_a_reopen(self):
        clauses = m.limit_clauses(self.observed(toasts=["已重新載入"], generation=("1", "2")))
        self.assertFalse(clauses["noToast"])
        self.assertFalse(clauses["generation"])

    def test_the_control_leaves_the_instrument_clauses_open(self):
        presses = [{"press": n, "settledBefore": True} for n in range(1, m.LIMIT_PRESSES + 1)]
        clauses = m.limit_clauses(self.observed(presses=presses, control=True))
        self.assertEqual({k for k, v in clauses.items() if v is None},
                         {"everyPressVerified", "comment", "restorePresses", "limitReached", "latency"})
        self.assertTrue(verdict(clauses), clauses)

    # Spec 31.2: every press under LATENCY_BOUND_MS, the runner's and the engine's number both.
    def test_red_one_press_at_the_bound(self):
        for field in ("keyToUndoMs", "keyToResponseMs"):
            presses = self.observed()["presses"]
            presses[54] = {**presses[54], field: m.LATENCY_BOUND_MS}
            self.assertFalse(m.limit_clauses(self.observed(presses=presses))["latency"], field)

    def test_red_a_missing_number(self):
        for field in ("keyToUndoMs", "keyToResponseMs"):
            presses = self.observed()["presses"]
            presses[0] = {**presses[0], field: None}
            self.assertFalse(m.limit_clauses(self.observed(presses=presses))["latency"], field)

    def test_red_the_v18_reports(self):
        # The five reports spec 31.2 names as its red cases; two of them say `pass: true` under the old clauses.
        v18 = m.HERE.parent / "findings/evidence/v18"
        for name in ("m2-shakedown/m2-4-chrome.json", "m2-shakedown/m2-4-firefox.json",
                     "diag-117/m2-4-chrome.json", "finding-118/p4-m2-4-fixed-chrome.json",
                     "finding-118/p4-m2-4-fixed-firefox.json"):
            presses = json.loads((v18 / name).read_text())["cases"][0]["presses"]
            self.assertEqual(len(presses), m.LIMIT_PRESSES, name)
            self.assertFalse(m.limit_clauses(self.observed(presses=presses))["latency"], name)


class Binding(unittest.TestCase):
    """Spec 7 / 30.2: what makes a report counted; the red case runs v8 and the same page source."""

    BINDING = {"wasmSha256": "w19", "workerSha256": "k19", "sessionSha256": "s", "pageSha256": "p19",
               "pageSourceSha256": "src", "eshapeSha256": "e"}

    def test_the_candidate(self):
        self.assertTrue(m.is_counted("counted", dict(self.BINDING), self.BINDING))
        self.assertTrue(m.is_counted("m2-4", dict(self.BINDING), self.BINDING))

    def test_red_any_value_differs_on_the_candidate(self):
        for key in self.BINDING:
            self.assertFalse(m.is_counted("m2-1b", {**self.BINDING, key: "other"}, self.BINDING), key)

    def test_the_red_case_on_v8(self):
        v8 = {**self.BINDING, "wasmSha256": "w8", "workerSha256": "k8", "pageSha256": "p8"}
        self.assertTrue(m.is_counted("m2-1-red", v8, self.BINDING))
        for key in ("sessionSha256", "pageSourceSha256", "eshapeSha256"):
            self.assertFalse(m.is_counted("m2-1-red", {**v8, key: "other"}, self.BINDING), key)
        self.assertFalse(m.is_counted("m2-1-red", {k: v for k, v in v8.items() if k != "eshapeSha256"},
                                      self.BINDING))

    def test_nothing_counts_unbound_or_in_a_shakedown(self):
        self.assertFalse(m.is_counted("counted", dict(self.BINDING), None))
        self.assertFalse(m.is_counted("shakedown", dict(self.BINDING), self.BINDING))


class Teardown(unittest.TestCase):
    """Handoff 10-08d Next 2: the browser is closed even when the last observer read fails."""

    class Session:
        def __init__(self):
            self.closed = 0

        def evaluate(self, *_):
            raise ConnectionError("CDP dropped")

        def close(self):
            self.closed += 1

    def test_the_browser_is_closed_when_the_read_fails(self):
        session, report = self.Session(), {}
        original = m.obs
        m.obs = lambda s: (_ for _ in ()).throw(ConnectionError("CDP dropped"))
        try:
            m.teardown(session, report)
        finally:
            m.obs = original
        self.assertEqual(session.closed, 1)
        self.assertEqual(report["observerAtEnd"], {"error": "ConnectionError: CDP dropped"})

    def test_a_normal_end(self):
        session, report = self.Session(), {}
        original = m.obs
        m.obs = lambda s: {"responses": [1], "responsesSeen": 1}
        try:
            m.teardown(session, report)
        finally:
            m.obs = original
        self.assertEqual(session.closed, 1)
        self.assertEqual(report["observerAtEnd"], {"responsesSeen": 1})

    def test_no_session(self):
        report = {}
        m.teardown(None, report)
        self.assertEqual(report, {})


if __name__ == "__main__":
    unittest.main()
