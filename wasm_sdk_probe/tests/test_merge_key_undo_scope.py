"""M1-1's per-object judgement (`check_merge_key_undo_scope.judge_rows`), offline, on the rows of the
committed green run (findings/evidence/v19/pre-link/m1-1/green.json) and mutations of them; and, for the
per-carrier object sets (ruling 6 condition 50, 2026-10-14), on the rows of the committed v20 runs under
findings/evidence/link-batch/v20-part3/m1-1/ (green-1 and red cases 1-4) and the witness's.

green-2 (`--base 82af92ca^`) is NOT here: it is red (E2_V15 and E2_V19 probe_engine differ from that base), see
that directory's README.  Nothing below asserts it as expected.

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

EVIDENCE = Path(__file__).resolve().parents[2] / "findings/evidence"
GREEN = json.loads((EVIDENCE / "v19/pre-link/m1-1/green.json").read_text())
V20_DIR = EVIDENCE / "link-batch/v20-part3"
V20_SET = ("probe_engine", "sdk_api", "editor_api")
V20_CARRIERS = {"E2_V15": ("probe_engine",), "E2_V19": ("probe_engine",), "E2_V20": V20_SET}


def rules_of(doc):
    return sorted({r["rule"] for r in doc["rows"]})


def committed(directory, name):
    return json.loads((V20_DIR / directory / f"{name}.json").read_text())
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


class PerCarrierObjectSets(unittest.TestCase):
    """Ruling 6 condition 50 as amended: `--carrier RULE=obj,...`.  The rows are the committed runs' own."""

    def judged(self, doc, carriers, base):
        return c.judge_rows(copy.deepcopy(doc["rows"]), carriers, rules_of(doc), base)

    def test_the_default_shape_is_unchanged(self):
        self.assertEqual(c.carrier_map(c.CARRIERS), {"E2_V15": ("probe_engine",), "E2_V19": ("probe_engine",)})
        self.assertEqual(c.parse_carrier("E2_V19"), ("E2_V19", ("probe_engine",)))
        self.assertEqual(c.parse_carrier("E2_V20=probe_engine,sdk_api,editor_api"), ("E2_V20", V20_SET))

    def test_a_malformed_carrier_is_refused(self):
        for bad in ("E2_V20=", "E2_V20=probe_engine,", "E2_V20=probe_engine.o", "=probe_engine",
                    "E2_V20=build/e2/probe_engine"):
            with self.subTest(bad):
                with self.assertRaises(SystemExit):
                    c.parse_carrier(bad)

    def test_the_witness_is_reproduced_offline(self):
        # The unchanged tool's red run on the tree with the block applied: default carriers, three E2_V20 objects.
        witness = json.loads((V20_DIR / "m1-1-witness/m1-1-base-5d77dc84.json").read_text())
        failures = self.judged(witness, c.CARRIERS, "5d77dc84")
        self.assertEqual(failures, witness["failures"])
        self.assertEqual([f.split(":")[0] for f in failures],
                         [f"E2_V20 build/e2/editor-v20/{n}.o" for n in ("sdk_api", "probe_engine", "editor_api")])

    def test_green_1_base_5d77dc84(self):
        doc = committed("m1-1", "green-1-base-5d77dc84")
        self.assertEqual(doc["failures"], [])
        self.assertEqual(self.judged(doc, V20_CARRIERS, "5d77dc84"), [])
        differing = sorted((r["rule"], r["object"].rsplit("/", 1)[1]) for r in doc["rows"] if not r["same"])
        self.assertEqual(differing, sorted([("E2_V15", "probe_engine.o"), ("E2_V19", "probe_engine.o"),
                                            ("E2_V20", "probe_engine.o"), ("E2_V20", "sdk_api.o"),
                                            ("E2_V20", "editor_api.o")]))

    def test_the_default_carriers_alone_are_red_on_green_1_rows(self):
        # The same rows the repair accepts: the old rule cannot express v20.
        doc = committed("m1-1", "green-1-base-5d77dc84")
        self.assertEqual(len(self.judged(doc, c.CARRIERS, "5d77dc84")), 3)

    def test_red_1_v20_engine_only(self):
        doc = committed("m1-1", "red-1-v20-engine-only")
        failures = self.judged(doc, {**V20_CARRIERS, "E2_V20": ("probe_engine",)}, "5d77dc84")
        self.assertEqual(failures, doc["failures"])
        self.assertEqual([f.split(":")[0] for f in failures],
                         ["E2_V20 build/e2/editor-v20/sdk_api.o", "E2_V20 build/e2/editor-v20/editor_api.o"])

    def test_red_2_v20_without_editor_api(self):
        doc = committed("m1-1", "red-2-v20-engine-sdk-api")
        failures = self.judged(doc, {**V20_CARRIERS, "E2_V20": ("probe_engine", "sdk_api")}, "5d77dc84")
        self.assertEqual(failures, doc["failures"])
        self.assertEqual([f.split(":")[0] for f in failures], ["E2_V20 build/e2/editor-v20/editor_api.o"])

    def test_red_3_a_declared_object_that_did_not_move(self):
        doc = committed("m1-1", "red-3-v20-declared-unmoved")
        failures = self.judged(doc, {**V20_CARRIERS, "E2_V20": (*V20_SET, "unoembind_stub")}, "5d77dc84")
        self.assertEqual(failures, doc["failures"])
        self.assertEqual(failures, ["E2_V20: its unoembind_stub object does not differ from 5d77dc84 "
                                    "(declared to differ, did not move)"])

    def test_red_4_the_define_injected_into_v19(self):
        doc = committed("m1-1", "red-4-inject-v19-define")
        failures = self.judged(doc, V20_CARRIERS, "5d77dc84")
        self.assertEqual(failures, doc["failures"])
        self.assertEqual([f.split(":")[0] for f in failures],
                         ["E2_V19 build/e2/editor-v19/sdk_api.o", "E2_V19 build/e2/editor-v19/editor_api.o"])

    def test_mutations_of_the_green_rows(self):
        doc = committed("m1-1", "green-1-base-5d77dc84")

        def mutated(rule, name, **change):
            rows = copy.deepcopy(doc["rows"])
            row(rows, rule, name).update(change)
            return c.judge_rows(rows, V20_CARRIERS, rules_of(doc), "5d77dc84")

        # a declared object that stopped differing, one per declared object
        for name in V20_SET:
            with self.subTest(declared_but_same=name):
                failures = mutated("E2_V20", name, same=True)
                self.assertEqual(len(failures), 1)
                self.assertIn(f"E2_V20: its {name} object does not differ", failures[0])
        # an undeclared object of a carrier that started differing, and of a rule that is not a carrier
        self.assertEqual(len(mutated("E2_V20", "unoembind_stub", same=False)), 1)
        self.assertEqual(len(mutated("E2_V19", "editor_api", same=False)), 1)
        self.assertEqual(len(mutated("E2_V8", "sdk_api", same=False)), 1)
        # a carrier object that does not preprocess
        self.assertTrue(mutated("E2_V20", "sdk_api", unbuildable=True))

    def test_a_declared_name_that_is_not_an_object_of_the_rule_is_red(self):
        doc = committed("m1-1", "green-1-base-5d77dc84")
        failures = c.judge_rows(copy.deepcopy(doc["rows"]), {**V20_CARRIERS, "E2_V20": (*V20_SET, "no_such_unit")},
                                rules_of(doc), "5d77dc84")
        self.assertEqual(len(failures), 1)
        self.assertIn("no_such_unit", failures[0])


if __name__ == "__main__":
    unittest.main()
