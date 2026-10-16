"""tools/v21_item2_population.py: the populations are closed by their sources, and the tool refuses what no
rule places.

Real sources: M1 29 items, all with a native reference; M3 35 items (28 on the dialog and SDK routes, 7 on
the raw-bytes route) and X14 excluded by spec §12.2 (b); M4 38 collapsed, 14 range, 5 protected, 9
excluded; M5 19.  Red cases: an unknown verdict, an empty fixture, a PASS item without a native reference,
a script with Ctrl+Home after other steps, an unknown step, a click on an unrecorded point -- each must
raise PopulationError, never shrink the population quietly.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
