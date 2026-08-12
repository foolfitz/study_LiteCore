#!/usr/bin/env python3
"""Create the deterministic ODT-first E1 editing discovery corpus."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

from e1_support import sha256, write_json


MIMETYPE = "application/vnd.oasis.opendocument.text"
ZIP_TIME = (2026, 8, 4, 0, 0, 0)
NAMESPACES = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
    'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
    'office:version="1.3"'
)


def xml_document(body: str, extra_namespaces: str = "") -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content {NAMESPACES}{extra_namespaces}>
 <office:automatic-styles>
  <style:style style:name="E1Bold" style:family="text"><style:text-properties fo:font-weight="bold"/></style:style>
  <style:style style:name="E1Italic" style:family="text"><style:text-properties fo:font-style="italic"/></style:style>
 </office:automatic-styles>
 <office:body><office:text>{body}</office:text></office:body>
</office:document-content>
'''


STYLES_XML = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles {NAMESPACES}>
 <office:styles>
  <style:default-style style:family="paragraph"><style:paragraph-properties fo:margin-top="0cm" fo:margin-bottom="0.2cm"/></style:default-style>
  <style:style style:name="Heading_20_1" style:display-name="Heading 1" style:family="paragraph"><style:text-properties fo:font-size="18pt" fo:font-weight="bold"/></style:style>
 </office:styles>
</office:document-styles>
'''

MANIFEST_XML = f'''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="{MIMETYPE}" manifest:version="1.3"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
'''


PARAGRAPH_CONTENT_NAMESPACES = (
    ' xmlns:xlink="http://www.w3.org/1999/xlink"'
    ' xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"'
    ' xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"'
    ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
)

PARAGRAPH_CONTENT_STYLES = '''  <style:style style:name="Heading_20_2" style:display-name="Heading 2" style:family="paragraph" style:default-outline-level="2">
   <style:paragraph-properties fo:margin-top="0.35cm" fo:margin-bottom="0.15cm"/>
   <style:text-properties fo:font-size="16pt" fo:font-weight="bold"/>
  </style:style>
  <style:style style:name="Heading_20_3" style:display-name="Heading 3" style:family="paragraph" style:default-outline-level="3">
   <style:paragraph-properties fo:margin-top="0.3cm" fo:margin-bottom="0.15cm"/>
   <style:text-properties fo:font-size="14pt" fo:font-weight="bold"/>
  </style:style>
  <style:style style:name="Heading_20_6" style:display-name="Heading 6" style:family="paragraph" style:default-outline-level="6">
   <style:paragraph-properties fo:margin-top="0.2cm" fo:margin-bottom="0.1cm"/>
   <style:text-properties fo:font-size="11pt" fo:font-weight="bold"/>
  </style:style>
  <style:style style:name="Preformatted_20_Text" style:display-name="Preformatted Text" style:family="paragraph">
   <style:paragraph-properties fo:margin-top="0cm" fo:margin-bottom="0cm"/>
   <style:text-properties fo:font-family="monospace"/>
  </style:style>
  <style:style style:name="Quotations" style:display-name="Quotations" style:family="paragraph">
   <style:paragraph-properties fo:margin-left="1cm" fo:margin-right="1cm"/>
  </style:style>
  <style:style style:name="Title" style:display-name="Title" style:family="paragraph">
   <style:paragraph-properties fo:text-align="center" fo:margin-bottom="0.4cm"/>
   <style:text-properties fo:font-size="24pt" fo:font-weight="bold"/>
  </style:style>
  <style:style style:name="Subtitle" style:display-name="Subtitle" style:family="paragraph">
   <style:paragraph-properties fo:text-align="center" fo:margin-bottom="0.3cm"/>
   <style:text-properties fo:font-size="14pt" fo:font-style="italic"/>
  </style:style>
  <style:style style:name="Heading_20_4" style:display-name="Heading 4" style:family="paragraph" style:default-outline-level="4">
   <style:text-properties fo:font-size="12pt" fo:font-weight="bold"/>
  </style:style>
  <style:style style:name="Heading_20_5" style:display-name="Heading 5" style:family="paragraph" style:default-outline-level="5">
   <style:text-properties fo:font-size="11pt" fo:font-weight="bold"/>
  </style:style>
  <style:style style:name="Heading_20_7" style:display-name="Heading 7" style:family="paragraph" style:default-outline-level="7">
   <style:text-properties fo:font-size="10pt" fo:font-weight="bold"/>
  </style:style>
  <style:style style:name="Heading_20_10" style:display-name="Heading 10" style:family="paragraph" style:default-outline-level="10">
   <style:text-properties fo:font-size="10pt" fo:font-style="italic"/>
  </style:style>
  <style:style style:name="PCCjkBold" style:display-name="PC CJK Bold" style:family="text">
   <style:text-properties fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold"/>
  </style:style>
'''

# Only the picture.  The manifest deliberately does not list itself: ODF 1.3
# part 3 keeps /META-INF/ out of the file entries, no real producer writes such
# an entry, and the other six fixtures do not have one.  A fixture whose package
# shape differs from the rest of the corpus would be a confound in a measurement
# whose whole subject is what the serialiser does with ordinary documents.
PARAGRAPH_CONTENT_MANIFEST_ENTRIES = ''' <manifest:file-entry manifest:full-path="Pictures/pc-dot.png" manifest:media-type="image/png"/>
'''

# Keeping the complete PNG as bytes makes the image member independent of the
# host's image libraries and their encoder metadata.
PC_DOT_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xdac\xf8\xcf"
    b"\xc0\xf0\x1f\x00\x05\x00\x01\xffV\xc7/\r\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Finding 037's guard keys on the selection type, and the only shape ever
# measured as COMPLEX is an as-char embedded PNG.  That is one sample, and the
# guard's whole premise is that the shapes which hang are exactly the ones that
# report non-TEXT.  A shape that reports TEXT and hangs anyway would go straight
# through the guard -- so the anchoring modes and graphic kinds get pulled apart
# here and each one is asked for its selection type.
#
# Its own fixture, not more rows in paragraph-content: adding to that file would
# change its bytes, and every M2 and finding 035 measurement is evidence about
# the file with those bytes.
IMAGE_VARIANTS_NAMESPACES = PARAGRAPH_CONTENT_NAMESPACES

IMAGE_VARIANTS_MANIFEST_ENTRIES = (
    ' <manifest:file-entry manifest:full-path="Pictures/iv-dot.png"'
    ' manifest:media-type="image/png"/>\n'
    ' <manifest:file-entry manifest:full-path="Pictures/iv-dot.svg"'
    ' manifest:media-type="image/svg+xml"/>\n'
)

# Hand-written rather than produced by a library, for the same reason as the
# PNG: the bytes have to be a property of this file, not of whatever was
# installed on the machine that last regenerated the corpus.
IV_DOT_SVG = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"'
    b' viewBox="0 0 8 8"><rect width="8" height="8" fill="#336699"/></svg>\n'
)


def image_frame(name: str, anchor: str, href: str, mime: str) -> str:
    return (
        f'<draw:frame draw:name="{name}" text:anchor-type="{anchor}"'
        f' svg:width="0.08in" svg:height="0.08in">'
        f'<draw:image xlink:href="{href}" xlink:type="simple" xlink:show="embed"'
        f' xlink:actuate="onLoad" draw:mime-type="{mime}"/></draw:frame>')


FIXTURES = {
    "plain-grapheme": {
        "body": """
 <text:p>E1-PLAIN-START</text:p>
 <text:p>ASCII abc XYZ 0123456789</text:p>
 <text:p>臺灣中文游標測試</text:p>
 <text:p>emoji 😀 grapheme</text:p>
 <text:p>combining é boundary</text:p>
 <text:p>E1-PLAIN-END</text:p>
""",
        "anchors": ["E1-PLAIN-START", "臺灣中文游標測試", "emoji 😀 grapheme", "combining é boundary", "E1-PLAIN-END"],
        "minimum": {"paragraphs": 6, "headings": 0, "lists": 0, "tables": 0},
    },
    "multi-paragraph": {
        "body": """
 <text:p>E1-MULTI-START alpha</text:p>
 <text:p>第二段中文 beta</text:p>
 <text:p>第三段跨行 gamma</text:p>
 <text:p>第四段落 delta</text:p>
 <text:p>E1-MULTI-END omega</text:p>
""",
        "anchors": ["E1-MULTI-START alpha", "第二段中文 beta", "E1-MULTI-END omega"],
        "minimum": {"paragraphs": 5, "headings": 0, "lists": 0, "tables": 0},
    },
    "styled-list": {
        "body": """
 <text:h text:outline-level="1" text:style-name="Heading_20_1">E1-STYLED-HEADING</text:h>
 <text:p>Normal <text:span text:style-name="E1Bold">bold anchor</text:span> and <text:span text:style-name="E1Italic">italic anchor</text:span>.</text:p>
 <text:list><text:list-item><text:p>E1-LIST-ONE</text:p></text:list-item><text:list-item><text:p>E1-LIST-TWO</text:p></text:list-item></text:list>
 <text:p>E1-STYLED-END</text:p>
""",
        "anchors": ["E1-STYLED-HEADING", "bold anchor", "italic anchor", "E1-LIST-ONE", "E1-STYLED-END"],
        "minimum": {"paragraphs": 4, "headings": 1, "lists": 1, "tables": 0},
    },
    # Added 2026-08-11 for the format-barrier deadline work.  An empty paragraph
    # is not an exotic shape -- "press the list button on a blank line" is one of
    # the commonest editing gestures -- and .uno:EndOfParaSel has nothing to
    # select there by construction.  Every other fixture's paragraphs carry text,
    # which is why 375 judged dispatches never touched this.
    #
    # A new fixture rather than an edit to an existing one: the fixture sha256 is
    # recorded in every run's evidence, so editing one would detach the A3/A4/A5
    # verdicts from the documents they were measured on.
    "empty-paragraph": {
        # Two empty paragraphs, and the difference between them is the point:
        # mid-document, a selection that escapes lands on a neighbour; at the
        # document end there is no next paragraph to escape to, so it may
        # produce no selection at all.  Those are different failures.
        "body": """
 <text:p>E1-EMPTY-BEFORE</text:p>
 <text:p/>
 <text:p>E1-EMPTY-AFTER</text:p>
 <text:p/>
""",
        "anchors": ["E1-EMPTY-BEFORE", "E1-EMPTY-AFTER"],
        "minimum": {"paragraphs": 4, "headings": 0, "lists": 0, "tables": 0},
    },
    # Added 2026-08-11 for finding 035.  text/markdown turned out to express all
    # five closed actions with three prefixes ("- ", "1. ", "# ") and -- unlike
    # the HTML flavour -- to write CJK text with no font-run wrapper at all, so
    # it is a candidate for replacing the readback entirely.  That only holds if
    # the exporter escapes a paragraph whose *text* begins with those same
    # characters.  If it does not, an ordinary paragraph reads back as a list
    # item and the barrier reports a list that is not there: a false positive,
    # which is the direction that matters.
    #
    # The fixture pairs each look-alike with the real thing, because the
    # question is not "what does a plain paragraph produce" but "can the two be
    # told apart".  A check that cannot distinguish them is the shape this
    # project keeps having to retract.
    "markdown-syntax": {
        "body": """
 <text:p>MD-CONTROL ordinary paragraph</text:p>
 <text:p>- MD-DASH is a plain paragraph</text:p>
 <text:p>1. MD-NUMBER is a plain paragraph</text:p>
 <text:p># MD-HASH is a plain paragraph</text:p>
 <text:p>&gt; MD-QUOTE is a plain paragraph</text:p>
 <text:p>* MD-STAR is a plain paragraph</text:p>
 <text:list><text:list-item><text:p>MD-REAL-ITEM is a real list item</text:p></text:list-item></text:list>
 <text:h text:outline-level="1" text:style-name="Heading_20_1">MD-REAL-HEADING is a real heading</text:h>
""",
        "anchors": ["MD-CONTROL", "MD-DASH", "MD-NUMBER", "MD-HASH", "MD-QUOTE",
                    "MD-STAR", "MD-REAL-ITEM", "MD-REAL-HEADING"],
        "minimum": {"paragraphs": 7, "headings": 1, "lists": 1, "tables": 0},
    },
    "table-boundary": {
        "body": """
 <text:p>E1-TABLE-BEFORE</text:p>
 <table:table table:name="E1Table">
  <table:table-column table:number-columns-repeated="2"/>
  <table:table-row><table:table-cell><text:p>E1-CELL-A1</text:p></table:table-cell><table:table-cell><text:p>E1-CELL-B1</text:p></table:table-cell></table:table-row>
  <table:table-row><table:table-cell><text:p>E1-CELL-A2</text:p></table:table-cell><table:table-cell><text:p>E1-CELL-B2</text:p></table:table-cell></table:table-row>
 </table:table>
 <text:p>E1-TABLE-AFTER</text:p>
""",
        "anchors": ["E1-TABLE-BEFORE", "E1-CELL-A1", "E1-CELL-B2", "E1-TABLE-AFTER"],
        "minimum": {"paragraphs": 6, "headings": 0, "lists": 0, "tables": 1},
    },
    # The namespace, style and package additions stay on this fixture because
    # the older fixture bytes are evidence identifiers for published findings.
    #
    # PC-CJK-BOLD uses its own PCCjkBold rather than the shared E1Bold, and the
    # difference is not cosmetic.  E1Bold sets fo:font-weight only, which is the
    # *Western* weight: measured on 2026-08-12, the CJK run came back as
    # <font><span>...</span></font> with no <b> anywhere, i.e. the fixture did
    # not carry the thing it was named after.  A row like that reads as "CJK
    # bold produces no <b>" when it actually means "this document has no CJK
    # bold" -- the failure mode this corpus exists to make impossible.
    # style:font-weight-asian is the attribute that applies to CJK text.
    "paragraph-content": {
        "body": """
 <text:p>PC-PLAIN ordinary paragraph</text:p>
 <text:h text:outline-level="2" text:style-name="Heading_20_2">PC-H2 level two heading</text:h>
 <text:h text:outline-level="3" text:style-name="Heading_20_3">PC-H3 level three heading</text:h>
 <text:h text:outline-level="4" text:style-name="Heading_20_4">PC-H4 level four heading</text:h>
 <text:h text:outline-level="5" text:style-name="Heading_20_5">PC-H5 level five heading</text:h>
 <text:h text:outline-level="6" text:style-name="Heading_20_6">PC-H6 level six heading</text:h>
 <text:h text:outline-level="7" text:style-name="Heading_20_7">PC-H7 level seven heading</text:h>
 <text:h text:outline-level="10" text:style-name="Heading_20_10">PC-H10 level ten heading</text:h>
 <text:p text:style-name="Preformatted_20_Text">PC-PRE preformatted paragraph</text:p>
 <text:p text:style-name="Quotations">PC-QUOTE quotation paragraph</text:p>
 <text:p text:style-name="Title">PC-TITLE title paragraph</text:p>
 <text:p text:style-name="Subtitle">PC-SUBTITLE subtitle paragraph</text:p>
 <text:p>PC-LINK paragraph with a <text:a xlink:href="https://example.invalid/pc" xlink:type="simple">hyperlink</text:a></text:p>
 <text:p>PC-BOOKMARK paragraph with <text:bookmark-start text:name="pc-bookmark"/>bookmarked text<text:bookmark-end text:name="pc-bookmark"/></text:p>
 <text:p>PC-FOOTNOTE paragraph with a note<text:note text:id="pc-footnote" text:note-class="footnote"><text:note-citation>1</text:note-citation><text:note-body><text:p>Footnote body text.</text:p></text:note-body></text:note></text:p>
 <text:p>PC-COMMENT paragraph with a comment<office:annotation office:name="pc-comment"><dc:creator>E1 corpus</dc:creator><dc:date>2026-08-12T00:00:00Z</dc:date><text:p>Comment body text.</text:p></office:annotation></text:p>
 <text:p>PC-IMAGE paragraph with an inline image <draw:frame draw:name="pc-dot" text:anchor-type="as-char" svg:width="0.08in" svg:height="0.08in"><draw:image xlink:href="Pictures/pc-dot.png" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad" draw:mime-type="image/png"/></draw:frame></text:p>
 <text:p>PC-BREAK before the break<text:line-break/>after the break</text:p>
 <text:p>PC-CJK-BOLD 臺灣與 <text:span text:style-name="PCCjkBold">粗體中文</text:span> mixed with ASCII</text:p>
 <text:section text:name="pc-section"><text:p>PC-SECTION paragraph inside a section</text:p></text:section>
 <text:list><text:list-item><text:p>PC-LIST-ITEM paragraph inside a real list item</text:p></text:list-item></text:list>
""",
        "anchors": ["PC-PLAIN", "PC-H2", "PC-H3", "PC-H4", "PC-H5", "PC-H6",
                    "PC-H7", "PC-H10", "PC-PRE", "PC-QUOTE",
                    "PC-TITLE", "PC-SUBTITLE", "PC-LINK", "PC-BOOKMARK", "PC-FOOTNOTE",
                    "PC-COMMENT", "PC-IMAGE", "PC-BREAK", "PC-CJK-BOLD", "PC-SECTION",
                    "PC-LIST-ITEM"],
        # 16, not 20.  The first version wrote 20 by counting the 21 anchors,
        # but seven of those anchors are <text:h> and two of the paragraphs are
        # the footnote and comment bodies -- the file has 16 <text:p> and always
        # did.  Nothing caught it because validate_e1_corpus.py had no target
        # that ran it: the committed baseline still described five fixtures,
        # three fixtures after this one was added.  A gate nobody runs is not a
        # gate, so the corpus check is now wired into test-e1-a-static.
        "minimum": {"paragraphs": 16, "headings": 7, "lists": 1, "tables": 0},
        "extra_namespaces": PARAGRAPH_CONTENT_NAMESPACES,
        "extra_styles": PARAGRAPH_CONTENT_STYLES,
        "extra_manifest_entries": PARAGRAPH_CONTENT_MANIFEST_ENTRIES,
        "extra_members": (("Pictures/pc-dot.png", PC_DOT_PNG),),
    },
    # Finding 037.  One axis per row, so a difference in the answer is a
    # difference in one property:
    #
    #   IV-PLAIN      no frame at all -- the control that says the run worked
    #   IV-ASCHAR     as-char embedded PNG -- the shape already measured COMPLEX
    #   IV-SVG        same anchoring, vector graphic instead of a bitmap
    #   IV-LINKED     same anchoring, href to a file:// URL that resolves to
    #                 nothing -- the ordinary "the linked picture moved" case.
    #                 It must be an absolute URL: the first version pointed at a
    #                 relative name with xlink:show="embed" and no such member in
    #                 the package, and LibreOffice then refuses to load the whole
    #                 document (0.5 s, "source file could not be loaded").  That
    #                 is a broken file, not a linked picture, and it took the
    #                 other eight rows down with it.
    #   IV-CHAR       anchored to a character rather than being one
    #   IV-PARAGRAPH  anchored to the paragraph
    #   IV-TEXTBOX    an as-char frame with no image in it at all
    #   IV-LIST       an as-char image inside a real list item
    #   IV-TAIL       plain paragraph after them, so every row has a neighbour
    #                 to escape to
    #
    # IV-TEXTBOX is the one that decides how the finding should be worded: if a
    # frame with no graphic in it also reports COMPLEX, the trigger is the
    # frame, and calling this "the inline image bug" would be naming the wrong
    # thing.
    "image-variants": {
        "body": """
 <text:p>IV-PLAIN ordinary paragraph with no frame</text:p>
 <text:p>IV-ASCHAR as-char embedded png """ + image_frame(
            "iv-aschar", "as-char", "Pictures/iv-dot.png", "image/png") + """</text:p>
 <text:p>IV-SVG as-char embedded svg """ + image_frame(
            "iv-svg", "as-char", "Pictures/iv-dot.svg", "image/svg+xml") + """</text:p>
 <text:p>IV-LINKED as-char link to a file outside the package """ + image_frame(
            "iv-linked", "as-char", "file:///nonexistent/iv-linked.png", "image/png") + """</text:p>
 <text:p>IV-CHAR anchored to a character """ + image_frame(
            "iv-char", "char", "Pictures/iv-dot.png", "image/png") + """</text:p>
 <text:p>IV-PARAGRAPH anchored to the paragraph """ + image_frame(
            "iv-paragraph", "paragraph", "Pictures/iv-dot.png", "image/png") + """</text:p>
 <text:p>IV-TEXTBOX as-char frame with no image <draw:frame draw:name="iv-textbox" text:anchor-type="as-char" svg:width="0.4in" svg:height="0.16in"><draw:text-box><text:p>boxed</text:p></draw:text-box></draw:frame></text:p>
 <text:list><text:list-item><text:p>IV-LIST list item with an image """ + image_frame(
            "iv-list", "as-char", "Pictures/iv-dot.png", "image/png") + """</text:p></text:list-item></text:list>
 <text:p>IV-TAIL ordinary paragraph after the frames</text:p>
""",
        "anchors": ["IV-PLAIN", "IV-ASCHAR", "IV-SVG", "IV-LINKED", "IV-CHAR",
                    "IV-PARAGRAPH", "IV-TEXTBOX", "IV-LIST", "IV-TAIL"],
        "minimum": {"paragraphs": 8, "headings": 0, "lists": 1, "tables": 0},
        "extra_namespaces": IMAGE_VARIANTS_NAMESPACES,
        "extra_manifest_entries": IMAGE_VARIANTS_MANIFEST_ENTRIES,
        "extra_members": (("Pictures/iv-dot.png", PC_DOT_PNG),
                          ("Pictures/iv-dot.svg", IV_DOT_SVG)),
    },
    # Finding 012's open question, and it needs its own file to answer.
    #
    # 012 minimised its close hang to "an image frame as a direct child of
    # text:p" and stopped there -- it never tried a frame with no image in it.
    # Finding 037 then measured an as-char frame containing only a text box
    # reporting COMPLEX exactly like the image ones, so on that axis the trigger
    # is the frame.  image-variants cannot settle it for 012 because it carries
    # both, and it does need the close recovery.
    #
    # This file has frames and no images anywhere: no Pictures/ member, no
    # draw:image, nothing in the manifest but the two XML parts.  Open it and
    # close it.  A close that hangs says 012's trigger is the frame and its
    # minimisation needs redoing; a close that returns says the image is
    # required after all, and the "two entry points, one shared layer" reading
    # of 012-plus-037 has to be withdrawn.  Both answers change something,
    # which is the point.
    "frame-no-image": {
        "body": """
 <text:p>FNI-PLAIN ordinary paragraph before the frame</text:p>
 <text:p>FNI-TEXTBOX as-char frame holding text only <draw:frame draw:name="fni-textbox" text:anchor-type="as-char" svg:width="0.6in" svg:height="0.2in"><draw:text-box><text:p>boxed text</text:p></draw:text-box></draw:frame></text:p>
 <text:p>FNI-TAIL ordinary paragraph after the frame</text:p>
""",
        "anchors": ["FNI-PLAIN", "FNI-TEXTBOX", "FNI-TAIL"],
        "minimum": {"paragraphs": 4, "headings": 0, "lists": 0, "tables": 0},
        "extra_namespaces": IMAGE_VARIANTS_NAMESPACES,
    },
    # The other half of the same cut.  frame-no-image showed the close hang
    # needs a frame and not an image; it used as-char anchoring, so "as-char" and
    # "frame" were still varying together.  This file is identical except that
    # its one frame is anchored to the paragraph -- the anchoring 037 measured
    # behaving like plain text for selection purposes.
    #
    # If this closes promptly, as-char (or char) anchoring is part of the
    # trigger and 012's minimisation gets narrower again.  If it hangs, the
    # anchoring is irrelevant and any frame will do.
    "frame-paragraph-anchored": {
        "body": """
 <text:p>FPA-PLAIN ordinary paragraph before the frame</text:p>
 <text:p>FPA-FRAME paragraph-anchored frame holding text only <draw:frame draw:name="fpa-textbox" text:anchor-type="paragraph" svg:width="0.6in" svg:height="0.2in"><draw:text-box><text:p>boxed text</text:p></draw:text-box></draw:frame></text:p>
 <text:p>FPA-TAIL ordinary paragraph after the frame</text:p>
""",
        "anchors": ["FPA-PLAIN", "FPA-FRAME", "FPA-TAIL"],
        "minimum": {"paragraphs": 4, "headings": 0, "lists": 0, "tables": 0},
        "extra_namespaces": IMAGE_VARIANTS_NAMESPACES,
    },
}


def write_member(archive: zipfile.ZipFile, name: str, data: bytes, compress: int) -> None:
    info = zipfile.ZipInfo(name, ZIP_TIME)
    info.compress_type = compress
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def styles_document(extra_styles: str = "") -> str:
    if not extra_styles:
        return STYLES_XML
    return STYLES_XML.replace(" </office:styles>", f"{extra_styles} </office:styles>", 1)


def manifest_document(extra_entries: str = "") -> str:
    if not extra_entries:
        return MANIFEST_XML
    return MANIFEST_XML.replace("</manifest:manifest>", f"{extra_entries}</manifest:manifest>", 1)


def create_odt(
    path: Path,
    body: str,
    *,
    extra_namespaces: str = "",
    extra_styles: str = "",
    extra_manifest_entries: str = "",
    extra_members: tuple[tuple[str, bytes], ...] = (),
) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        write_member(archive, "mimetype", MIMETYPE.encode(), zipfile.ZIP_STORED)
        write_member(archive, "content.xml", xml_document(body, extra_namespaces).encode(), zipfile.ZIP_DEFLATED)
        write_member(archive, "styles.xml", styles_document(extra_styles).encode(), zipfile.ZIP_DEFLATED)
        write_member(
            archive,
            "META-INF/manifest.xml",
            manifest_document(extra_manifest_entries).encode(),
            zipfile.ZIP_DEFLATED,
        )
        for name, data in extra_members:
            write_member(archive, name, data, zipfile.ZIP_DEFLATED)


def frozen_valid(manifest_path: Path) -> bool:
    if not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for fixture in manifest.get("fixtures", []):
        path = manifest_path.parent / fixture["path"]
        if not path.is_file() or path.stat().st_size != fixture["bytes"] or sha256(path) != fixture["sha256"]:
            return False
    return bool(manifest.get("fixtures"))


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=project / "test-docs" / "e1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    manifest_path = output / "manifest.json"
    if not args.force and frozen_valid(manifest_path):
        print(json.dumps({"manifest": str(manifest_path), "status": "frozen-valid"}))
        return
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for identifier, definition in FIXTURES.items():
        path = output / f"{identifier}.odt"
        create_odt(
            path,
            definition["body"],
            extra_namespaces=definition.get("extra_namespaces", ""),
            extra_styles=definition.get("extra_styles", ""),
            extra_manifest_entries=definition.get("extra_manifest_entries", ""),
            extra_members=definition.get("extra_members", ()),
        )
        entries.append({
            "id": identifier,
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "anchors": definition["anchors"],
            "minimum": definition["minimum"],
            "source": "project-generated deterministic ODT",
        })
    source = project / "test-docs" / "t2-styled.odt"
    copied = output / "r7-t2-styled.odt"
    shutil.copyfile(source, copied)
    entries.append({
        "id": "r7-t2-styled",
        "path": copied.name,
        "bytes": copied.stat().st_size,
        "sha256": sha256(copied),
        "anchors": ["R1 樣式文件", "文件結尾：請確認表格、圖片、註解與標題樣式均保留。"],
        "minimum": {"paragraphs": 1, "headings": 1, "lists": 0, "tables": 1},
        "source": "wasm_sdk_probe/test-docs/t2-styled.odt exact copy",
    })
    write_json(manifest_path, {
        "schemaVersion": 1,
        "release": "E1-A-editing-discovery",
        "frozenDate": "2026-08-04",
        "mutationPolicy": "copy-only",
        "fixtures": entries,
    })
    print(json.dumps({"manifest": str(manifest_path), "fixtures": len(entries)}))


if __name__ == "__main__":
    main()
