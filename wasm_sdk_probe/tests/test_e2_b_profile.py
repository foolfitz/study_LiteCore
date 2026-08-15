"""SPEC E2-B 5.8: the v2 product profile builder must fail closed.

The refusals are the point of this file.  A builder that only ever succeeds
would let the one artifact that exports the diagnostic ABI -- e2-combination,
which is also the only other artifact carrying route C -- be packaged as the
product, and the mistake would surface at validation time, after evidence had
been produced against it.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import build_e2_b_profile as builder  # noqa: E402

PRODUCT_SYMBOLS = [
    "_oxsdk_editor_action",
    "_oxsdk_editor_get_state",
    "_oxsdk_editor_select_range",
    "_oxsdk_editor_abi_version",
    "_oxsdk_editor_set_action_gestures",
]


def exports_file(directory: Path, symbols: list[str]) -> Path:
    path = directory / "exports.txt"
    path.write_text("\n".join(symbols) + "\n", encoding="utf-8")
    return path


class RefusalTest(unittest.TestCase):
    def test_clean_inventory_has_no_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = exports_file(Path(tmp), PRODUCT_SYMBOLS)
            self.assertEqual(builder.refuse_non_product(path), [])

    def test_a_discovery_symbol_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = exports_file(Path(tmp),
                                PRODUCT_SYMBOLS + ["_oxsdk_editor_discovery_action"])
            problems = builder.refuse_non_product(path)
            self.assertTrue(any("diagnostic ABI" in p for p in problems), problems)

    def test_each_missing_product_symbol_is_refused(self):
        # One at a time: dropping all five and seeing a refusal would only
        # prove that at least one is checked.
        for missing in PRODUCT_SYMBOLS:
            with self.subTest(missing=missing):
                with tempfile.TemporaryDirectory() as tmp:
                    kept = [s for s in PRODUCT_SYMBOLS if s != missing]
                    path = exports_file(Path(tmp), kept)
                    problems = builder.refuse_non_product(path)
                    self.assertTrue(any(missing in p for p in problems), problems)

    def test_a_missing_inventory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            problems = builder.refuse_non_product(Path(tmp) / "absent.txt")
            self.assertTrue(problems)


class ActionMapTest(unittest.TestCase):
    def test_disposition_a_withholds_the_crossing_gesture(self):
        actions = builder.action_map(cross_paragraph=False)
        for name in builder.V2_PARAGRAPH_ACTIONS:
            self.assertNotIn(builder.RANGE_CROSS, actions[name]["gestures"], name)

    def test_disposition_b_offers_it(self):
        actions = builder.action_map(cross_paragraph=True)
        for name in builder.V2_PARAGRAPH_ACTIONS:
            self.assertIn(builder.RANGE_CROSS, actions[name]["gestures"], name)

    def test_v1_actions_stay_caret_only_under_both_dispositions(self):
        # Range dispatch was characterised for the five paragraph actions.
        # Declaring it for delete or insert would be the manifest claiming
        # coverage the evidence does not have.
        for cross in (False, True):
            actions = builder.action_map(cross_paragraph=cross)
            for name in builder.V1_ACTIONS:
                self.assertEqual(actions[name]["gestures"],
                                 [builder.COLLAPSED], (name, cross))

    def test_wire_ids_are_stable_across_dispositions(self):
        a = builder.action_map(cross_paragraph=False)
        b = builder.action_map(cross_paragraph=True)
        self.assertEqual({k: v["id"] for k, v in a.items()},
                         {k: v["id"] for k, v in b.items()})

    def test_v1_wire_ids_are_one_to_ten_in_order(self):
        actions = builder.action_map(cross_paragraph=True)
        self.assertEqual([actions[n]["id"] for n in builder.V1_ACTIONS],
                         list(range(1, 11)))

    def test_paragraph_wire_ids_are_eleven_to_fifteen(self):
        actions = builder.action_map(cross_paragraph=True)
        self.assertEqual(
            sorted(actions[n]["id"] for n in builder.V2_PARAGRAPH_ACTIONS),
            [11, 12, 13, 14, 15])

    def test_heading_carries_its_narrowings(self):
        actions = builder.action_map(cross_paragraph=True)
        self.assertIn("heading-level-1-only",
                      actions["set-paragraph-heading"]["limits"])


if __name__ == "__main__":
    unittest.main()
