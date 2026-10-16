"""tools/v21_item2_fixtures.py: the item-2 corpora and the M10 fixture are what the arms pinned.

Red cases: a pin moved by one hex digit, a generator whose tail byte changes, an M6 corpus one byte short,
a fixture whose frame is written after the paragraphs (the dry-run shape native Writer dropped) -- each
must be reported, and the real generator must report nothing.
"""
import importlib.util
import io
import sys
import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
TOOL = Path(__file__).resolve().parent.parent / "tools" / "v21_item2_fixtures.py"


def load():
    spec = importlib.util.spec_from_file_location("v21_item2_fixtures_under_test", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
DRAW_NS = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"


def frame_first(odt: bytes) -> bool:
    with zipfile.ZipFile(io.BytesIO(odt)) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    text = root.find(f"{{{OFFICE_NS}}}body/{{{OFFICE_NS}}}text")
    first = list(text)[0]
    return first.tag == f"{{{DRAW_NS}}}frame" and first.get(f"{{{TEXT_NS}}}anchor-type") == "page"


class Generator(unittest.TestCase):
    def setUp(self):
        self.fx = load()

    def test_real_generator_matches_every_pin(self):
        self.assertEqual(self.fx.check(), [])

    def test_sizes_are_exact(self):
        for n in (0, 1, 2, 3, 16384, 16385, 65536, 65537):
            self.assertEqual(len(self.fx.size_corpus(n)), n)
        data, sections = self.fx.m6_corpus(65536)
        self.assertEqual((len(data), sections), (65536, 286))
        data, sections = self.fx.m6_corpus(16384)
        self.assertEqual((len(data), sections), (16384, 74))
        data.decode("utf-8")  # valid UTF-8

    def test_m10_fixture_is_an_odt_with_the_frame_first(self):
        odt = self.fx.m10_selectables()
        with zipfile.ZipFile(io.BytesIO(odt)) as archive:
            infos = archive.infolist()
            self.assertEqual(infos[0].filename, "mimetype")
            self.assertEqual(infos[0].compress_type, zipfile.ZIP_STORED)
            self.assertIsNone(archive.testzip())
            self.assertTrue(archive.read(self.fx.M10_PICTURE).startswith(b"\x89PNG"))
            ET.fromstring(archive.read("content.xml"))
            ET.fromstring(archive.read("styles.xml"))
        self.assertTrue(frame_first(odt))
        self.assertEqual(odt, self.fx.m10_selectables(), "not deterministic")

    # ---- red cases ----
    def test_red_a_moved_pin_is_reported(self):
        pins = dict(self.fx.PINNED)
        name = "size-65537.md"
        pins[name] = pins[name][:-1] + ("0" if pins[name][-1] != "0" else "1")
        problems = self.fx.check(pins)
        self.assertEqual(len(problems), 1)
        self.assertIn(name, problems[0])

    def test_red_a_changed_tail_is_reported(self):
        self.fx.SIZE_TAIL = "b"
        problems = self.fx.check()
        for name in ("size-65536.md", "size-65537.md", "size-16384.md", "size-16385.md"):
            self.assertTrue(any(p.startswith(name) for p in problems), name)
        self.assertFalse(any(p.startswith("m6-") or p.startswith("m10-") for p in problems))

    def test_red_a_short_m6_corpus_is_refused(self):
        original = self.fx.m6_corpus

        def short(limit):
            data, sections = original(limit)
            return data[:-1], sections
        self.fx.m6_corpus = short
        problems = self.fx.check()
        self.assertTrue(any(p.startswith("m6-65536.md") for p in problems))

    def test_red_frame_after_the_paragraphs_is_detected(self):
        odt = self.fx.m10_selectables()
        with zipfile.ZipFile(io.BytesIO(odt)) as archive:
            content = archive.read("content.xml").decode("utf-8")
        start = content.index("  <draw:frame draw:style-name=\"frText\"")
        end = content.index("</draw:frame>\n", start) + len("</draw:frame>\n")
        frame = content[start:end]
        moved = content[:start] + content[end:]
        moved = moved.replace(" </office:text>", frame + " </office:text>")
        buffer = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(odt)) as src, zipfile.ZipFile(buffer, "w") as dst:
            for info in src.infolist():
                data = moved.encode("utf-8") if info.filename == "content.xml" else src.read(info)
                dst.writestr(info, data)
        self.assertFalse(frame_first(buffer.getvalue()))


if __name__ == "__main__":
    unittest.main()
