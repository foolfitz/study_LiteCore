#!/usr/bin/env python3
"""Checks for the corpus content-axis inventory (task 034).

This tool is meant to gate future GO verdicts, which makes it the same kind of
thing as a validator -- and this project has already shipped two validators that
could not fail: `validate_e1_corpus.py` never ran at all, and a substring check
passed happily against `if (false && ...)`.  So the tests here are mostly
mutation tests: build a document that HAS the construct, build one that does
not, and require the tool to tell them apart.  A test that only asserts the
happy case would pass against a function that returns zeros.
"""

from __future__ import annotations

import io
import sys
import unittest
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

from inventory_corpus_axes import blind_spots, inventory, roll_up  # noqa: E402

CONTENT_HEAD = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<office:document-content'
    ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
    ' xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"'
    ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    ' xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
    ' xmlns:xlink="http://www.w3.org/1999/xlink">'
    "<office:body><office:text>"
)
CONTENT_TAIL = "</office:text></office:body></office:document-content>"

FRAME = (
    '<draw:frame text:anchor-type="as-char"><draw:image xlink:href="Pictures/a.png"/>'
    "</draw:frame>"
)
FOOTNOTE_WITH_FRAME = (
    '<text:note text:note-class="footnote">'
    "<text:note-citation>1</text:note-citation>"
    f"<text:note-body><text:p>note {FRAME}</text:p></text:note-body>"
    "</text:note>"
)
FOOTNOTE_WITHOUT_FRAME = (
    '<text:note text:note-class="footnote">'
    "<text:note-citation>1</text:note-citation>"
    "<text:note-body><text:p>note</text:p></text:note-body>"
    "</text:note>"
)


def odt(body: str, styles: str | None = None) -> Path:
    """A minimal package the inventory can read, written to a temp file."""
    import tempfile

    handle = tempfile.NamedTemporaryFile(suffix=".odt", delete=False)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("content.xml", CONTENT_HEAD + body + CONTENT_TAIL)
        if styles is not None:
            archive.writestr("styles.xml", CONTENT_HEAD + styles + CONTENT_TAIL)
    handle.write(buffer.getvalue())
    handle.close()
    return Path(handle.name)


class ContentAxisInventoryTest(unittest.TestCase):
    def test_counts_frames_by_anchor_type(self) -> None:
        """The one attribute that separates finding 012 firing from not firing."""
        as_char = inventory(odt(f"<text:p>a {FRAME}</text:p>"))
        paragraph = inventory(odt(
            '<text:p>a <draw:frame text:anchor-type="paragraph">'
            '<draw:image xlink:href="Pictures/a.png"/></draw:frame></text:p>'))
        self.assertEqual(as_char["axes"]["frame-as-char"], 1)
        self.assertEqual(as_char["axes"]["frame-paragraph"], 0)
        self.assertEqual(paragraph["axes"]["frame-as-char"], 0)
        self.assertEqual(paragraph["axes"]["frame-paragraph"], 1)

    def test_separates_a_frame_in_a_note_from_a_frame_and_a_note(self) -> None:
        """Finding 038 is a composite, and this is the distinction that matters.

        Both documents contain a footnote AND an as-char frame.  Only one of
        them contains an as-char frame INSIDE the footnote.  An inventory that
        cannot tell these apart would have called E1-C's corpus covered.
        """
        together = inventory(odt(f"<text:p>x{FOOTNOTE_WITH_FRAME}</text:p>"))
        apart = inventory(odt(
            f"<text:p>x{FOOTNOTE_WITHOUT_FRAME}</text:p><text:p>y {FRAME}</text:p>"))
        for entry in (together, apart):
            self.assertEqual(entry["axes"]["footnote"], 1)
            self.assertEqual(entry["axes"]["frame-as-char"], 1)
        self.assertEqual(together["composites"]["footnote"]["frame-as-char"], 1)
        self.assertEqual(apart["composites"]["footnote"]["frame-as-char"], 0)

    def test_endnote_is_not_counted_as_a_footnote(self) -> None:
        entry = inventory(odt(
            '<text:p><text:note text:note-class="endnote">'
            "<text:note-body><text:p>e</text:p></text:note-body></text:note></text:p>"))
        self.assertEqual(entry["axes"]["endnote"], 1)
        self.assertEqual(entry["axes"]["footnote"], 0)

    def test_reads_styles_xml_so_headers_are_visible(self) -> None:
        """Headers and footers live in styles.xml; a content-only reader misses them."""
        entry = inventory(
            odt("<text:p>body</text:p>", styles=f"<style:header><text:p>h {FRAME}</text:p>"
                "</style:header>"))
        self.assertEqual(entry["axes"]["header-footer"], 1)
        self.assertEqual(entry["composites"]["header-footer"]["frame-as-char"], 1)

    def test_counts_han_text(self) -> None:
        """Finding 035 was a CJK paragraph; an all-Latin corpus cannot show it."""
        self.assertGreater(inventory(odt("<text:p>中文字</text:p>"))["scripts"]["han"], 0)
        self.assertEqual(inventory(odt("<text:p>latin</text:p>"))["scripts"]["han"], 0)

    def test_blind_spots_do_not_double_report_a_missing_container(self) -> None:
        """No footnote at all is `absentAxes`, not thirty empty footnote cells.

        Reporting both would bury the one real signal under noise, which is the
        failure mode that made the missing axis invisible in the first place.
        """
        rollup = roll_up([inventory(odt(f"<text:p>a {FRAME}</text:p>"))])
        gaps = blind_spots(rollup)
        self.assertIn("footnote", gaps["absentAxes"])
        self.assertNotIn("footnote/frame-as-char", gaps["emptyComposites"])

    def test_blind_spots_report_a_cell_both_of_whose_axes_are_present(self) -> None:
        rollup = roll_up([inventory(odt(
            f"<text:p>x{FOOTNOTE_WITHOUT_FRAME}</text:p><text:p>y {FRAME}</text:p>"))])
        gaps = blind_spots(rollup)
        self.assertNotIn("footnote", gaps["absentAxes"])
        self.assertNotIn("frame-as-char", gaps["absentAxes"])
        self.assertIn("footnote/frame-as-char", gaps["emptyComposites"])


class ShippedCorpusTest(unittest.TestCase):
    """The claims SPEC-E1-C 9.1 makes in prose, restated as assertions.

    9.1 narrows E1_GO_ODT_EDITOR on the strength of two facts about the C3
    corpus.  They were true when someone checked them by hand on 2026-08-12.
    Here they are checked every run.
    """

    C3 = [
        "l0-t1-plain-zh.odt", "l0-t2-styled.odt", "l0-t3-long.odt",
        "l1-review.odt", "l4-stress-100.odt",
    ]

    def rollup(self) -> dict:
        corpus = PROJECT / "test-docs" / "r7-compat"
        entries = [inventory(corpus / name) for name in self.C3]
        return roll_up(entries)

    def test_c3_has_no_notes_at_all(self) -> None:
        rollup = self.rollup()
        self.assertEqual(rollup["axes"]["footnote"], 0)
        self.assertEqual(rollup["axes"]["endnote"], 0)

    def test_c3_does_carry_as_char_frames(self) -> None:
        """The other half of 9.1: the corpus is not innocent of frames."""
        self.assertGreater(self.rollup()["axes"]["frame-as-char"], 0)

    def test_c3_carries_no_lists(self) -> None:
        """Not in any spec yet -- found by this tool on its first run.

        The five documents E1_GO_ODT_EDITOR rests on contain no `text:list`.
        That matters the moment list actions are promoted into the shipped
        contract: the verdict's own corpus could not exercise them.
        """
        rollup = self.rollup()
        self.assertEqual(rollup["axes"]["list"], 0)
        self.assertEqual(rollup["axes"]["list-item"], 0)


if __name__ == "__main__":
    unittest.main()
