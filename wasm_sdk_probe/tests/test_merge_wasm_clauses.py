"""The merge WASM runner's clauses (SPEC-M3-paragraph-merge 22.1), offline.

The comparator red cases spec 10.2 asks for (one per assertion) and the two
the review of 5555e554 found missing: the marker check that inverted when the
marker was lost (B3), and "not changed" said after the key went out.  Built
from the native R0c data, so a clause is tested against the references it
will meet in a run.

    python3 -m unittest tests.test_merge_wasm_clauses
"""
from __future__ import annotations

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
        self.assertEqual(counts, {"M2-1": 31, "M2-3": 5, "barrier": 1})

    def test_an_unknown_decision_stops(self):
        with self.assertRaises(SystemExit):
            m.expectation("something-new")


if __name__ == "__main__":
    unittest.main()
