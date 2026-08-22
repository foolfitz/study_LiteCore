#!/usr/bin/env python3
"""The oracle for "did an inline format actually take", exercised on ODF.

Why a marker at all: the validation matrix amended its own D1 cells on
2026-08-15, BEFORE D1 ran, on the strength of a pre-flight probe --

    at a collapsed caret an inline format leaves <office:body> byte-identical
    and shows up only in text committed afterwards

-- so an oracle that diffs the saved document against the paragraph it aimed
at passes on a no-op.  These cases pin the reading of a marker's own span.

The `none` cases are the ones that matter most.  ODF does not spell underline
and strike as booleans; it spells them as a line STYLE whose "off" value is the
literal string "none".  An oracle that asked whether the attribute is PRESENT
would read an explicitly-turned-off underline as underlined -- and that is the
direction relink 2 shipped and nothing has yet driven.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from run_e2_c_product_path import inline_styles_of  # noqa: E402

HEAD = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0">
<office:automatic-styles>
%s
</office:automatic-styles>
<office:body><office:text>
%s
</office:text></office:body></office:document-content>"""


def style(name: str, properties: str, parent: str = "") -> str:
    parent = f' style:parent-style-name="{parent}"' if parent else ""
    return (f'<style:style style:name="{name}" style:family="text"{parent}>'
            f'<style:text-properties {properties}/></style:style>')


def paragraph_style(name: str, properties: str, parent: str = "Standard") -> str:
    """An automatic PARAGRAPH style carrying character properties.

    This is what LibreOffice writes when a paragraph is uniformly formatted --
    no span at all -- and reading it is finding 065's whole story.
    """
    return (f'<style:style style:name="{name}" style:family="paragraph"'
            f' style:parent-style-name="{parent}">'
            f'<style:paragraph-properties style:writing-mode="lr-tb"/>'
            f'<style:text-properties {properties}/></style:style>')


def document(styles: str, body: str) -> dict:
    return {"content": HEAD % (styles, body)}


class InlineStylesOf(unittest.TestCase):

    def test_all_four_on(self):
        report = document(
            style("T1", 'fo:font-weight="bold" fo:font-style="italic"'
                        ' style:text-underline-style="solid"'
                        ' style:text-line-through-style="solid"'),
            '<text:p><text:span text:style-name="T1">MARK</text:span></text:p>')
        got = inline_styles_of(report, "MARK")
        self.assertTrue(got["found"])
        self.assertEqual(got["carrier"], "span")
        for name in ("bold", "italic", "underline", "strikethrough"):
            self.assertTrue(got[name], name)

    def test_underline_and_strike_explicitly_none_are_off(self):
        """The case a presence test would get backwards."""
        report = document(
            style("T2", 'style:text-underline-style="none"'
                        ' style:text-line-through-style="none"'),
            '<text:p><text:span text:style-name="T2">MARK</text:span></text:p>')
        got = inline_styles_of(report, "MARK")
        self.assertTrue(got["found"])
        self.assertFalse(got["underline"])
        self.assertFalse(got["strikethrough"])

    def test_font_weight_normal_is_not_bold(self):
        report = document(
            style("T3", 'fo:font-weight="normal" fo:font-style="normal"'),
            '<text:p><text:span text:style-name="T3">MARK</text:span></text:p>')
        got = inline_styles_of(report, "MARK")
        self.assertFalse(got["bold"])
        self.assertFalse(got["italic"])

    def test_text_with_no_span_carries_no_inline_format(self):
        """What a working `clear-format` produces, and it must not read as 'lost'."""
        report = document("", "<text:p>plain MARK here</text:p>")
        got = inline_styles_of(report, "MARK")
        self.assertTrue(got["found"])
        self.assertEqual(got["carrier"], "paragraph")
        for name in ("bold", "italic", "underline", "strikethrough"):
            self.assertFalse(got[name], name)

    # --------------------------------------------- the paragraph carrier
    #
    # Added 2026-08-22, after an OPERATOR saw bold on the canvas while this
    # function reported `bold: false` on the document they had just saved.
    # It stopped at "not in a span, therefore not formatted", and ODF does not
    # work that way: a uniformly formatted paragraph carries its character
    # properties on its own automatic style and emits no span.
    #
    # THREE of the four fail against the pre-fix function (two failures and
    # one KeyError on the new field). The fourth --
    # `test_a_paragraph_style_that_turns_it_off_reads_off` -- passes both
    # ways, because the old code returned no properties at all and
    # "no properties" and "explicitly off" both read as off. It is kept
    # anyway: it pins the direction that WOULD break under a naive
    # presence test, and it is honest about not being a discriminator.

    def test_bold_on_the_paragraph_style_is_bold(self):
        """The operator's own file, reduced: <text:p P1>MARK</text:p>."""
        report = document(
            paragraph_style("P1", 'fo:font-weight="bold"'
                                  ' style:font-weight-asian="bold"'),
            '<text:p text:style-name="P1"><text:s/>MARK</text:p>')
        got = inline_styles_of(report, "MARK")
        self.assertTrue(got["found"])
        self.assertEqual(got["carrier"], "paragraph")
        self.assertEqual(got["styleName"], "P1")
        self.assertTrue(got["fromParagraphStyle"])
        self.assertTrue(got["bold"])

    def test_every_format_on_the_paragraph_style_is_read(self):
        report = document(
            paragraph_style("P2", 'fo:font-weight="bold" fo:font-style="italic"'
                                  ' style:text-underline-style="solid"'
                                  ' style:text-line-through-style="solid"'),
            '<text:p text:style-name="P2">MARK</text:p>')
        got = inline_styles_of(report, "MARK")
        for name in ("bold", "italic", "underline", "strikethrough"):
            self.assertTrue(got[name], name)

    def test_a_paragraph_style_that_turns_it_off_reads_off(self):
        """The direction the presence trap gets backwards, at paragraph level."""
        report = document(
            paragraph_style("P3", 'fo:font-weight="normal"'
                                  ' style:text-underline-style="none"'),
            '<text:p text:style-name="P3">MARK</text:p>')
        got = inline_styles_of(report, "MARK")
        self.assertTrue(got["found"])
        self.assertFalse(got["bold"])
        self.assertFalse(got["underline"])

    def test_a_span_still_wins_over_its_paragraph(self):
        """The span is nearer the text; a paragraph-level default must not mask it."""
        report = document(
            paragraph_style("P4", 'fo:font-weight="normal"')
            + style("T9", 'fo:font-weight="bold"'),
            '<text:p text:style-name="P4">'
            '<text:span text:style-name="T9">MARK</text:span></text:p>')
        got = inline_styles_of(report, "MARK")
        self.assertEqual(got["carrier"], "span")
        self.assertFalse(got["fromParagraphStyle"])
        self.assertTrue(got["bold"])

    def test_a_marker_that_is_not_there_is_not_found(self):
        report = document("", "<text:p>nothing to see</text:p>")
        self.assertFalse(inline_styles_of(report, "MARK")["found"])

    def test_the_right_span_is_read_when_several_exist(self):
        """Two markers, two styles: each must read its own."""
        report = document(
            style("T1", 'fo:font-weight="bold"')
            + style("T2", 'fo:font-style="italic"'),
            '<text:p><text:span text:style-name="T1">ONMARK</text:span>'
            '<text:span text:style-name="T2">OFFMARK</text:span></text:p>')
        on = inline_styles_of(report, "ONMARK")
        off = inline_styles_of(report, "OFFMARK")
        self.assertTrue(on["bold"])
        self.assertFalse(on["italic"])
        self.assertFalse(off["bold"])
        self.assertTrue(off["italic"])

    def test_a_parent_style_is_inherited_and_the_child_wins(self):
        report = document(
            style("Base", 'fo:font-weight="bold" fo:font-style="italic"')
            + style("T4", 'fo:font-weight="normal"', parent="Base"),
            '<text:p><text:span text:style-name="T4">MARK</text:span></text:p>')
        got = inline_styles_of(report, "MARK")
        self.assertFalse(got["bold"], "the child's normal must beat the parent")
        self.assertTrue(got["italic"], "the parent's italic must be inherited")

    def test_a_style_cycle_does_not_hang(self):
        report = document(
            style("A", 'fo:font-weight="bold"', parent="B")
            + style("B", 'fo:font-style="italic"', parent="A"),
            '<text:p><text:span text:style-name="A">MARK</text:span></text:p>')
        got = inline_styles_of(report, "MARK")
        self.assertTrue(got["found"])

    def test_unparseable_content_is_not_found_rather_than_raising(self):
        self.assertFalse(inline_styles_of({"content": "<not xml"}, "MARK")["found"])
        self.assertFalse(inline_styles_of({}, "MARK")["found"])


if __name__ == "__main__":
    unittest.main()
