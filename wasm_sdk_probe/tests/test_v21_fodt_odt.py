"""Red cases for S-6 (`tools/fodt_to_odt.py`) and S-7 (`tools/v21_odt_adapter.py`).

ARMS.md S-6, S-7; ARMS-item1.md §2.5 (proofs (i)-(iii)), §2.7, §8 D-4 (every top-level child placed,
an unknown one refused).  D1's own four red cases are `tools/v21_item1_marker.py --self-test`, run
here too.

  python3 -m unittest tests/test_v21_fodt_odt.py
"""
from __future__ import annotations

import hashlib
import io
import sys
import unittest
import zipfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
import fodt_to_odt as f  # noqa: E402
import v21_item1_marker as marker  # noqa: E402
import v21_odt_adapter as a  # noqa: E402

FIXTURES = marker.FIXTURES
COMMITTED = HERE.parent / "findings/evidence/link-batch-v21/shakedown/fixtures"
HEADER = (FIXTURES / "header-footer.fodt").read_bytes()


class ConverterTest(unittest.TestCase):
    def test_every_fixture_and_native_document_proves_i_and_ii(self):
        self.assertEqual(marker.cross_container(), [])
        for path in sorted(FIXTURES.glob("*.fodt")):
            raw = path.read_bytes()
            out = f.convert(raw)
            self.assertEqual(f.verify(raw, out), [], path.name)
            self.assertEqual(out, f.convert(raw), f"{path.name}: not deterministic")

    def test_an_unknown_top_level_child_is_refused(self):
        for extra in (b"<office:forms/>", b'<x:y xmlns:x="urn:x"/>'):
            raw = HEADER.replace(b"<office:body>", extra + b"<office:body>", 1)
            with self.assertRaises(f.ConversionError, msg=extra):
                f.convert(raw)

    def test_a_duplicated_top_level_child_is_refused(self):
        raw = HEADER.replace(b"<office:body>", b"<office:master-styles/><office:body>", 1)
        with self.assertRaises(f.ConversionError):
            f.convert(raw)

    def test_a_root_that_is_not_office_document_is_refused(self):
        with self.assertRaises(f.ConversionError):
            f.convert(b'<?xml version="1.0"?><office:document-content xmlns:office="%s"/>' % f.OFFICE.encode())

    def test_proof_ii_goes_red_when_the_converter_drops_a_slice(self):
        raw = HEADER
        broken = dict(f.PLACEMENT)
        broken["master-styles"] = ()
        with mock.patch.dict(f.PLACEMENT, broken):
            out = f.convert(raw)
        problems = f.verify(raw, out)
        self.assertTrue(any("master-styles" in p for p in problems), problems)
        # ...and proof (i) on the header fixture sees it too
        self.assertNotEqual(marker.paragraphs_of(out), marker.read_marker.paragraphs(raw))

    def test_page_layout_goes_to_styles_only(self):
        out = f.convert(HEADER)
        with zipfile.ZipFile(io.BytesIO(out)) as z:
            self.assertNotIn(b"page-layout", z.read("content.xml"))
            self.assertIn(b"page-layout", z.read("styles.xml"))
            self.assertEqual(z.namelist()[0], "mimetype")
            self.assertEqual(z.getinfo("mimetype").compress_type, zipfile.ZIP_STORED)

    def test_the_committed_outputs_are_the_converter_s(self):
        sums = (COMMITTED / "SHA256SUMS").read_text().split("\n")
        rows = [line.split("  ") for line in sums if line.strip()]
        self.assertEqual(len(rows), 10)
        for digest, name in rows:
            out = f.convert((FIXTURES / name.replace(".odt", ".fodt")).read_bytes())
            self.assertEqual(hashlib.sha256(out).hexdigest(), digest, name)
            self.assertEqual((COMMITTED / name).read_bytes(), out, name)


class AdapterTest(unittest.TestCase):
    def test_errors_carry_their_payload(self):
        with self.assertRaisesRegex(a.AdapterError, "not a zip|does not parse"):
            a.flat_document(b"PK\x03\x04garbage")
        with self.assertRaisesRegex(a.AdapterError, "does not parse"):
            a.flat_document(b"<office:document")
        with self.assertRaisesRegex(a.AdapterError, "not office:document"):
            a.flat_document(b'<x xmlns="urn:x"/>')

    def test_an_automatic_style_that_differs_between_parts_is_refused(self):
        out = f.convert((FIXTURES / "indent.fodt").read_bytes())
        members = {}
        with zipfile.ZipFile(io.BytesIO(out)) as z:
            for name in z.namelist():
                members[name] = z.read(name)
        members["styles.xml"] = members["styles.xml"].replace(b'fo:text-indent="1cm"', b'fo:text-indent="2cm"', 1)
        self.assertIn(b"2cm", members["styles.xml"])
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            for name, data in members.items():
                z.writestr(name, data)
        with self.assertRaisesRegex(a.AdapterError, "differs between"):
            a.flat_document(buffer.getvalue())

    def test_pictures_are_exposed(self):
        out = f.convert(HEADER)
        members = {}
        with zipfile.ZipFile(io.BytesIO(out)) as z:
            for name in z.namelist():
                members[name] = z.read(name)
        members["Pictures/x.png"] = b"\x89PNG"
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            for name, data in members.items():
                z.writestr(name, data)
        self.assertEqual(a.pictures(buffer.getvalue()), {"Pictures/x.png": b"\x89PNG"})
        self.assertEqual(a.pictures(HEADER), {})


class D1RedCasesTest(unittest.TestCase):
    def test_the_four_red_cases(self):
        self.assertEqual(marker.self_test(verbose=False), 0)


if __name__ == "__main__":
    unittest.main()
