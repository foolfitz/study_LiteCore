"""tools/v21_item2_population.py: the populations are closed by their sources, and the tool refuses what no
rule places.

Real sources: M1 29 items, all with a native reference; M3 35 items (28 on the dialog and SDK routes, 7 on
the raw-bytes route) and X14 excluded by spec §12.2 (b); M4 38 collapsed, 14 range, 5 protected, 9
excluded by named rules; M5 19.  Red cases: an unknown verdict, an empty fixture, a PASS item without a
native reference, a script with Ctrl+Home after other steps, an unknown step -- and, for the population
clauses of ARMS-item2.md: three native runs that disagree (M1), native M8 texts that disagree (M2), corpus
bytes that are not the fixture's (M3's "the item's bytes sha must match the fixture's"), an injection-only
item whose bytes are not PASS without the injection (spec 12.2 (b) excludes only X14's shape), an M5 item
that only R-bytes can carry, no M3/M5 item at all, a round-1 collapsed arm whose one Undo did not restore,
a round-2 arm that no rule places, a click on an unrecorded point, an empty M4 class (M4: "zero instances
in any class"); and the tool's own guards: L not stated exactly once, a native reference without three runs,
a converted fixture that fails S-6's proof or the comparator -- each must raise PopulationError, never shrink
the population quietly.  The one raise no test reaches alone is "the M0 fixture has no items": with it
removed, the empty fixture still raises "an empty population" (the same case, guarded twice).
"""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import v21_item2_population as pop  # noqa: E402


class Population(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = pop.build()
        cls.expected = json.loads(pop.EXPECTED.read_text(encoding="utf-8"))

    def test_counts(self):
        c = self.built["counts"]
        self.assertEqual((c["M1"], c["M1withReference"]), (29, 29))
        self.assertEqual((c["M3items"], c["M3routes"], c["M3excluded"]),
                         (35, {"dialog": 28, "sdk": 28, "bytes": 7}, 1))
        self.assertEqual(c["M4"], {"collapsed": 38, "range": 14, "protected": 5})
        self.assertEqual((c["M4excluded"], c["M5"]), (9, 19))

    def test_raw_byte_items_are_exactly_the_undecodable_ones(self):
        raw = sorted(i["path"] for i in self.built["M3"]["items"] if i["routes"] == ["bytes"])
        self.assertEqual(raw, ["m0/X05-invalid-utf8-latin1-byte.md", "m0/X06-invalid-utf8-truncated.md",
                               "m0/X07-invalid-utf8-label-mismatch.md", "m0/X15-invalid-utf8-overlong.md",
                               "m0/X16-invalid-utf8-surrogate.md", "m0/X17-invalid-utf8-above-10ffff.md",
                               "round-1/M8-utf16le.bin"])

    def test_layers_and_size_arms(self):
        by = {i["path"]: i for i in self.built["M3"]["items"]}
        self.assertEqual(by["round-1/M13.md"]["layerOnDialogAndSdk"], "sdk")
        self.assertEqual(by["round-1/M14b.md"]["layerOnDialogAndSdk"], "sdk")
        self.assertEqual(by["round-2/S01-inline-http.md"]["layerOnDialogAndSdk"], "engine")
        arms = {a["arm"]: a for a in self.built["M3"]["sizeArms"]}
        self.assertEqual(arms["SDK-L+1"]["refusingLayer"], "sdk")
        self.assertEqual(arms["ENG-65537"]["refusingLayer"], "engine")
        self.assertIsNone(arms["ENG-65536"]["refusingLayer"])
        self.assertEqual(self.built["M3"]["limitL"], 65536)

    def test_m2_expected_texts(self):
        self.assertEqual(self.built["M2"]["expectedTexts"], ["標題", "粗體中文", "第一項", "第二項", "第三項", ""])

    def test_m5_targets(self):
        by = {i["path"]: i for i in self.built["M5"]}
        self.assertEqual(by["round-1/M11.md"]["originsNamed"], ["http://127.0.0.1:9"])
        self.assertEqual(by["m0/X08-angle-generic.md"]["targets"], [])
        self.assertIn("m0/X03-nul-suffixed-reference.md", by)

    def test_output_is_deterministic(self):
        self.assertEqual(json.dumps(pop.build(), sort_keys=True), json.dumps(self.built, sort_keys=True))

    # ---- red cases ----
    def test_red_unknown_verdict(self):
        bad = copy.deepcopy(self.expected)
        bad["items"][0]["verdict"] = "MAYBE"
        with self.assertRaises(pop.PopulationError):
            pop.m1_m2_m3_m5(bad, 65536)

    def test_red_empty_fixture(self):
        bad = copy.deepcopy(self.expected)
        bad["items"] = []
        with self.assertRaises(pop.PopulationError):
            pop.m1_m2_m3_m5(bad, 65536)

    def test_red_pass_item_without_reference(self):
        with self.assertRaises(pop.PopulationError):
            pop.reference("m0/X99-nowhere.md")

    def test_red_scripts(self):
        with self.assertRaises(pop.PopulationError):
            pop.native_script_to_product("k1024,k9220")
        with self.assertRaises(pop.PopulationError):
            pop.native_script_to_product("q42")
        with self.assertRaises(pop.PopulationError):
            pop.native_script_to_product("k%d" % (1027 | pop.MOD1))
        keys, extend, clicks = pop.native_script_to_product("k9220x3,k1024,k1027x2,k%dx6" % (1027 | pop.SHIFT))
        self.assertEqual((keys, extend, clicks), (["ArrowDown", "ArrowRight", "ArrowRight"], ["ArrowRight"] * 6, []))

    # ---- red cases for the population clauses of ARMS-item2.md ----
    def _summary(self, arm: str) -> dict:
        return json.loads((pop.NATIVE / "round-2/out" / arm / "run1/summary.json").read_text(encoding="utf-8"))

    def test_m4_excluded_by_named_rules(self):
        # ARMS-item2 M4 "excluded, with the rule that excludes them" (the arm names as round 2 wrote them).
        rules = {Path(e["native"]).name: e["rule"].split(":")[0].split(" (")[0] for e in self.built["M4"]["excluded"]}
        self.assertEqual(rules, {
            "T2-input-M1": "native one Undo does not restore", "T2-input-M2": "native one Undo does not restore",
            "T2-input-plain-M2": "not a Markdown paste", "T2-viewro-M2": "LOK setViewReadOnly, which the product never calls",
            "T2-ctl-typekey": "a control without a paste", "T2-viewro-typekey": "a control without a paste",
            "T2-filero-M2": "a file mode 0444", "T2-ctl-normal-M2": "a duplicate of round 1's P4-M2",
            "T2-ref-empty-M13": "the item is not M0-PASS"})
        self.assertEqual([i["rule"][:9] for i in self.built["excluded"]], ["spec 12.2"])

    def test_red_native_runs_disagree(self):
        with mock.patch.object(pop.cmp, "signature_sha256", side_effect=["a" * 64, "b" * 64, "a" * 64]):
            with self.assertRaises(pop.PopulationError):
                pop.reference("round-1/M1.md")

    def test_red_m2_native_texts_disagree(self):
        answers = iter([["標題"], ["標題"], ["標"]])
        with mock.patch.object(pop.cmp, "paragraph_texts", side_effect=lambda raw: next(answers)):
            with self.assertRaises(pop.PopulationError):
                pop.m1_m2_m3_m5(copy.deepcopy(self.expected), 65536)

    def test_red_bytes_not_the_fixtures(self):
        bad = copy.deepcopy(self.expected)
        bad["items"][0]["sha256"] = "0" * 64
        with self.assertRaises(pop.PopulationError):
            pop.m1_m2_m3_m5(bad, 65536)

    def test_red_injection_only_item_not_pass_without_it(self):
        bad = copy.deepcopy(self.expected)
        x14 = next(i for i in bad["items"] if i.get("inject"))
        x14["verdictWithoutInjection"] = "NUL"
        with self.assertRaises(pop.PopulationError):
            pop.m1_m2_m3_m5(bad, 65536)

    def test_red_m5_item_only_bytes_can_carry(self):
        bad = copy.deepcopy(self.expected)
        next(i for i in bad["items"] if i["path"] == "m0/X05-invalid-utf8-latin1-byte.md")["verdict"] = "REMOTE"
        with self.assertRaises(pop.PopulationError):
            pop.m1_m2_m3_m5(bad, 65536)

    def test_red_no_m3_or_m5_item(self):
        bad = copy.deepcopy(self.expected)
        bad["items"] = [i for i in bad["items"] if i["verdict"] == "PASS"]
        with self.assertRaises(pop.PopulationError):
            pop.m1_m2_m3_m5(bad, 65536)

    def test_red_round1_undo_did_not_restore(self):
        pop.round1_collapsed("P4-M2", {"undoStepsToRestore": 1})
        with self.assertRaises(pop.PopulationError):
            pop.round1_collapsed("P4-M2", {"undoStepsToRestore": 2})

    def test_red_round2_no_rule_places_it(self):
        summary = self._summary("T1-P8-M1")
        self.assertEqual(pop.round2_class("T1-P8-M1", summary), "collapsed")
        summary["undoStepsToRestore"] = None
        summary["undo"] = {"countBefore": 0, "countAfter": 1, "payloadChanged": True}
        with self.assertRaises(pop.PopulationError):
            pop.round2_class("T1-P8-M1", summary)

    def test_red_click_on_an_unrecorded_point(self):
        summary = self._summary("T1-P10-M1")
        self.assertEqual(len(pop.click_points("T1-P10-M1", ["body", "hdr"], summary)), 2)
        with self.assertRaises(pop.PopulationError):
            pop.click_points("T1-P10-M1", ["nowhere"], summary)

    def test_red_limit_not_stated_once(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            for text in ("export const OTHER = 1;\n", "export const MARKDOWN_PASTE_LIMIT_BYTES = 1;\n" * 2):
                fake = Path(tmp) / "document-sdk.js"
                fake.write_text(text, encoding="utf-8")
                with mock.patch.object(pop, "SDK_SOURCE", fake), self.assertRaises(pop.PopulationError):
                    pop.sdk_limit()

    def test_red_not_three_native_runs(self):
        real = pop.runs_of
        with mock.patch.object(pop, "runs_of", side_effect=lambda folder: real(folder)[:2]):
            with self.assertRaises(pop.PopulationError):
                pop.reference("round-1/M1.md")

    def test_red_converted_fixture_not_proved(self):
        fodt = pop.NATIVE / "tool/inputs/positions.fodt"
        self.assertTrue(pop.fixture_entry(fodt)["odtSha256"])
        with mock.patch.object(pop.fodt_to_odt, "verify", return_value=["a dropped child"]), self.assertRaises(pop.PopulationError):
            pop.fixture_entry(fodt)
        with mock.patch.object(pop.cmp, "compare", return_value={"same": False}), self.assertRaises(pop.PopulationError):
            pop.fixture_entry(fodt)

    def test_red_empty_m4_class(self):
        instances = [i for i in self.built["M4"]["instances"] if i["class"] != "protected"]
        with self.assertRaises(pop.PopulationError):
            pop.class_counts(instances)


if __name__ == "__main__":
    unittest.main()
