"""The blank-document generator (SPEC-M3-new-document section 3.3): the set it
makes, that it is deterministic, that the files state what their records say,
and that the reader tells a template that does not from one that does."""
from __future__ import annotations

import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

import make_new_document_templates as gen  # noqa: E402


class TheSet(unittest.TestCase):
    def test_thirty_triples_one_file_each(self):
        files = gen.generate()
        self.assertEqual(len(files), 30)
        self.assertEqual(len(gen.triples()), 30)
        self.assertIn("en-US_zh-TW_A4.odt", files)
        self.assertIn("en-US_zh-TW_Letter.odt", files)
        self.assertIn("en-US_ja-JP_A4.odt", files)
        self.assertIn("de-DE_zh-TW_Letter.odt", files)
        # No Asian tag but zh-TW is paired with a non-English western tag.
        self.assertNotIn("de-DE_ja-JP_A4.odt", files)

    def test_deterministic(self):
        a, b = gen.generate(), gen.generate()
        for name in a:
            self.assertEqual(a[name]["bytes"], b[name]["bytes"], name)
        self.assertEqual(gen.manifest_bytes(a), gen.manifest_bytes(b))

    def test_package_rules(self):
        data = gen.build("en-US", "zh-TW", "A4")
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
        self.assertEqual(infos[0].filename, "mimetype")
        self.assertEqual(infos[0].compress_type, zipfile.ZIP_STORED)
        self.assertEqual(infos[0].extra, b"")
        self.assertTrue(all(i.compress_type == zipfile.ZIP_STORED for i in infos))
        self.assertTrue(all(i.date_time == gen.EPOCH for i in infos))
        self.assertEqual([i.filename for i in infos],
                         ["mimetype", "META-INF/manifest.xml", "meta.xml", "styles.xml", "content.xml"])
        # The raw bytes: the mimetype entry's local header has no extra field and
        # the mimetype text starts right after the 30-byte header + name.
        self.assertEqual(data[30:38], b"mimetype")
        self.assertTrue(data[38:].startswith(gen.ODT.encode()))

    def test_every_file_states_its_record(self):
        for name, entry in gen.generate().items():
            described = gen.describe(entry["bytes"])
            self.assertEqual(gen.compare(entry["record"], described), [], name)
            self.assertTrue(described["standardStyle"], name)
            self.assertEqual(described["mimetype"], gen.ODT, name)
            self.assertEqual(sorted(described["fontFaceDecls"]),
                             sorted({gen.WESTERN_FONT, gen.ASIAN_FONT[entry["record"]["asian"]], gen.COMPLEX_FONT}), name)

    def test_font_names_are_the_shipped_ones(self):
        # fontTools read of the e10 TTC and the base pack, 2026-10-14 (spec section 2).
        shipped = {"Noto Sans CJK JP", "Noto Sans CJK KR", "Noto Sans CJK SC", "Noto Sans CJK TC", "Noto Sans CJK HK",
                   "Liberation Serif", "Liberation Sans", "Liberation Mono"}
        self.assertTrue(set(gen.ASIAN_FONT.values()) <= shipped)
        self.assertIn(gen.WESTERN_FONT, shipped)
        self.assertIn(gen.COMPLEX_FONT, shipped)

    def test_manifest_shape(self):
        files = gen.generate()
        man = json.loads(gen.manifest_bytes(files))
        self.assertEqual(set(man["files"]), set(files))
        for name, rec in man["files"].items():
            self.assertEqual(rec["sha256"], gen.sha256(files[name]["bytes"]))
            self.assertEqual(rec["bytes"], len(files[name]["bytes"]))
            self.assertEqual(name, gen.file_name(rec["western"], rec["asian"], rec["paper"]))
        self.assertEqual(man["generator"]["path"], "wasm_sdk_probe/tools/make_new_document_templates.py")


class TheReader(unittest.TestCase):
    def test_compare_goes_red_on_a_changed_field(self):
        entry = gen.generate()["en-US_zh-TW_A4.odt"]
        described = gen.describe(entry["bytes"])
        self.assertEqual(gen.compare(entry["record"], described), [])
        for field, value in (("asian", "zh-CN"), ("western", "en-GB"), ("paper", "Letter"), ("complex", None)):
            wrong = dict(described, **{field: value})
            self.assertTrue(gen.compare(entry["record"], wrong), field)
        wrong = dict(described, fonts=dict(described["fonts"], asian="Noto Sans CJK KR"))
        self.assertTrue(gen.compare(entry["record"], wrong))

    def test_paper_classification(self):
        self.assertEqual(gen.classify_paper(210.0, 297.0), "A4")
        self.assertEqual(gen.classify_paper(210.01, 297.0), "A4")       # LibreOffice writes 21.001cm
        self.assertEqual(gen.classify_paper(215.9, 279.4), "Letter")
        self.assertEqual(gen.classify_paper(gen.to_mm("8.5in"), gen.to_mm("11in")), "Letter")
        self.assertEqual(gen.classify_paper(200.0, 297.0), "other")
        self.assertIsNone(gen.classify_paper(None, 297.0))

    def test_a_style_less_template_describes_as_stating_nothing(self):
        rd = Path(__file__).resolve().parent.parent.parent / "findings" / "evidence" / "new-document" / \
            "probe-1-native-defaults" / "tool" / "input-template.odt"
        if not rd.is_file():
            self.skipTest("richdocuments' template is not checked in here")
        described = gen.describe(rd.read_bytes())
        self.assertIsNone(described["western"])
        self.assertIsNone(described["asian"])
        self.assertIsNone(described["paper"])
        record = gen.generate()["en-US_zh-TW_A4.odt"]["record"]
        self.assertTrue(gen.compare(record, described))

    def test_zero_bytes_do_not_describe(self):
        with self.assertRaises(zipfile.BadZipFile):
            gen.describe(b"")


if __name__ == "__main__":
    unittest.main()
