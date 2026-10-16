"""tools/v21_item2_compare.py: the item-2 comparator's red cases (ARMS-item2.md I-7, spec §9.12), on committed
native documents (round 1's P1-M10 with an embedded PNG, P1-M8 with CJK and a list).

Positive: the same document as FODT, as an ODT whose image stays inline, and as an ODT whose image is a
Pictures/ member compares SAME (cross-container equality).  Red: styles.xml removed -> an error, not a
difference and not SAME; one byte of the picture changed -> DIFFERENT (the reader alone calls it equal: the
round-2 signature ignores image data); the picture member missing -> an error; one paragraph's text
changed -> DIFFERENT.
"""
import base64
import gzip
import io
import re
import sys
import unittest
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import fodt_to_odt  # noqa: E402
import v21_item2_compare as cmp  # noqa: E402
import v21_odt_adapter as s7  # noqa: E402

NATIVE = Path(__file__).resolve().parent.parent.parent / "findings/evidence/link-batch-v21/native/markdown-paste/out"
IMAGE = re.compile(rb"(<draw:image[^>]*?)>\s*<office:binary-data>([^<]*)</office:binary-data>\s*</draw:image>")


def members(odt: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(odt)) as archive:
        return {i.filename: archive.read(i.filename) for i in archive.infolist()}


def rebuild(parts: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in parts.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return buffer.getvalue()


def pictures_odt(fodt: bytes) -> bytes:
    """The flat document as an ODT whose embedded images are Pictures/ members (the shape a save writes)."""
    parts = members(fodt_to_odt.convert(fodt))
    found = []

    def move(match):
        found.append(base64.b64decode(match.group(2)))
        return match.group(1) + b' xlink:href="Pictures/img%d.png" xlink:type="simple"/>' % len(found)
    parts["content.xml"] = IMAGE.sub(move, parts["content.xml"])
    for i, data in enumerate(found, 1):
        parts[f"Pictures/img{i}.png"] = data
    assert found, "the fixture has no embedded image"
    return rebuild(parts)


class Comparator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m10 = gzip.decompress((NATIVE / "P1-M10/run1/after.fodt.gz").read_bytes())
        cls.m10_odt = pictures_odt(cls.m10)
        cls.m8 = gzip.decompress((NATIVE / "P1-M8/run1/after.fodt.gz").read_bytes())

    def test_cross_container_equality(self):
        self.assertTrue(cmp.compare(self.m10, self.m10_odt)["same"])
        self.assertTrue(cmp.compare(self.m10, fodt_to_odt.convert(self.m10))["same"])
        self.assertTrue(cmp.compare(self.m10, gzip.compress(self.m10))["same"])
        self.assertTrue(cmp.compare(self.m8, fodt_to_odt.convert(self.m8))["same"])

    def test_image_data_is_in_the_signature(self):
        data = cmp.signature(self.m10_odt)["imageData"]
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0].startswith("sha256:"))

    def test_paragraph_texts(self):
        self.assertEqual(cmp.paragraph_texts(self.m8), ["標題", "粗體中文", "第一項", "第二項", "第三項", ""])

    # ---- red cases ----
    def test_red_missing_styles_is_an_error(self):
        parts = members(self.m10_odt)
        del parts["styles.xml"]
        with self.assertRaises(s7.AdapterError):
            cmp.compare(self.m10, rebuild(parts))

    def test_red_broken_picture_is_different(self):
        parts = members(self.m10_odt)
        picture = bytearray(parts["Pictures/img1.png"])
        picture[-20] ^= 0xFF
        parts["Pictures/img1.png"] = bytes(picture)
        broken = rebuild(parts)
        result = cmp.compare(self.m10, broken)
        self.assertFalse(result["same"])
        self.assertIn("imageData", result["firstDifference"])
        # The committed reader alone does not see it -- the reason the data hash exists.
        self.assertEqual(cmp.md.signature(cmp.summary(self.m10)), cmp.md.signature(cmp.summary(broken)))

    def test_red_missing_picture_is_an_error(self):
        parts = members(self.m10_odt)
        del parts["Pictures/img1.png"]
        with self.assertRaises(cmp.ComparatorError):
            cmp.compare(self.m10, rebuild(parts))

    def test_red_changed_text_is_different(self):
        changed = self.m8.replace("第二項".encode(), "第二條".encode(), 1)
        self.assertNotEqual(changed, self.m8)
        self.assertFalse(cmp.compare(self.m8, changed)["same"])


if __name__ == "__main__":
    unittest.main()
