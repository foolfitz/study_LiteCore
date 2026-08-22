"""What the e2-editor-v4 profile claims, checked instead of asserted in prose.

The claims are cheap to state and expensive to lose, and this tree has lost one
of them before: E1-C extended v1 in place while the freeze test kept pinning
eight of ten actions, so for two shipped artifacts the freeze froze the wrong
set.  These tests are the successor identity's half of that lesson.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import build_e2_b_profile as v2  # noqa: E402
import build_e2_c_profile as v3  # noqa: E402
import build_e2_editor_v4_profile as v4  # noqa: E402


class InheritedVerbatim(unittest.TestCase):
    """Ids 1-15 are the claim; everything else v4 says rests on it."""

    def test_the_fifteen_inherited_actions_keep_their_wire_ids(self):
        old = v3.action_map()
        new = v4.action_map()
        for name, spec in old.items():
            self.assertIn(name, new, f"v4 dropped inherited action {name}")
            self.assertEqual(new[name]["id"], spec["id"],
                             f"v4 renumbered {name}")

    def test_the_new_actions_append_and_collide_with_nothing(self):
        new = v4.action_map()
        self.assertEqual(sorted(spec["id"] for spec in new.values()),
                         list(range(1, 22)))
        for name in v4.NEW_ACTIONS:
            self.assertGreaterEqual(new[name]["id"], 16)

    def test_the_ten_v1_actions_are_still_caret_only(self):
        new = v4.action_map()
        for name in v2.V1_ACTIONS:
            self.assertEqual(new[name]["gestures"], [v2.COLLAPSED],
                             f"{name} was widened without a measurement")


class WithheldRatherThanAbsent(unittest.TestCase):
    """The distinction the whole ship-dark design rests on.

    The engine sets EVERY entry to all-permitted on the first
    `set_action_gestures` call and intersects from there, so an action the
    worker never calls the setter for keeps that all-permitted default.  An
    action omitted from the manifest is therefore SHIPPED WIDE OPEN, not
    withheld -- the exact opposite of the intent, and silent.
    """

    def test_select_all_is_present_with_an_empty_gesture_list(self):
        new = v4.action_map()
        self.assertIn("select-all", new,
                      "select-all must be PRESENT with no gestures; omitting "
                      "it leaves the engine's all-permitted default standing")
        self.assertEqual(new["select-all"]["gestures"], [])

    def test_the_worker_still_pushes_a_mask_for_an_empty_gesture_list(self):
        """The manifest's half is useless if the worker's loop skips it."""
        worker = (Path(__file__).resolve().parents[1]
                  / "sdk" / "sdk-worker.js").read_text(encoding="utf-8")
        self.assertIn("!Array.isArray(spec?.gestures)", worker,
                      "the worker's skip condition must test for a MISSING "
                      "gestures field, not for an empty one -- an empty list "
                      "has to reach the engine as mask 0")

    def test_delete_selection_is_range_only_and_single_paragraph_only(self):
        spec = v4.action_map()["delete-selection"]
        self.assertNotIn(v2.COLLAPSED, spec["gestures"],
                         "a delete-selection that runs with no selection would "
                         "duplicate delete-backward and widen it by accident")
        self.assertNotIn(v2.RANGE_CROSS, spec["gestures"],
                         "cross-paragraph delete is not characterised")
        self.assertEqual(spec["gestures"], [v2.RANGE_SINGLE])


class ContractVersionDoesNotMove(unittest.TestCase):
    """ABI carries the break; the capability string must not.

    Moving the capability would make the profile unreachable through the
    worker's operation map, which is the defect SPEC E2-C 2.2 records.
    """

    def test_abi_version_is_four(self):
        self.assertEqual(v4.ABI_VERSION, 4)
        self.assertEqual(v3.ABI_VERSION, 3)

    def test_the_builder_is_a_separate_entry_point(self):
        self.assertIsNot(v4.main, v3.main)
        self.assertIsNot(v4.main, v2.main)


class TheGuardsFireWhenTheyShould(unittest.TestCase):
    """A check nobody has seen fail is a check nobody has tested."""

    def test_renumbering_an_inherited_action_is_refused(self):
        original = v4.NEW_ACTIONS["select-all"]
        try:
            v4.NEW_ACTIONS["set-bold"] = {"id": 21, "gestures": [],
                                          "limits": []}
            with self.assertRaises(SystemExit):
                v4.action_map()
        finally:
            v4.NEW_ACTIONS.pop("set-bold", None)
            v4.NEW_ACTIONS["select-all"] = original
        self.assertEqual(v4.action_map()["set-bold"]["id"], 7)

    def test_a_gap_in_the_id_range_is_refused(self):
        original = dict(v4.NEW_ACTIONS["select-all"])
        try:
            v4.NEW_ACTIONS["select-all"]["id"] = 22
            with self.assertRaises(SystemExit):
                v4.action_map()
        finally:
            v4.NEW_ACTIONS["select-all"] = original
        self.assertEqual(v4.action_map()["select-all"]["id"], 21)


if __name__ == "__main__":
    unittest.main()
