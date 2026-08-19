#!/usr/bin/env python3
"""Documents of an EXACT page count, for measuring where the editor stops.

The checklist row `edit-a-real-length-document` is the only one still marked
`missing`, and the reason nothing has measured it is that "a twenty page
document" was never a thing this tree could produce on demand.

Page count is made exact rather than estimated: every page after the first
starts with a heading carrying `fo:break-before="page"`, so the layout cannot
decide to fit two of them on one sheet whatever the font metrics turn out to
be.  Each page still carries real text, because the thing being measured --
render cost and canvas height -- is not the same on an empty page as on a full
one.

Markers, and what each is for:

  * `LD-P{page}-L{line}` on every line, so a caret or an edit can be aimed at a
    named place and the verdict can say WHICH page it was reading;
  * `LD-TOP` on the first line and `LD-BOTTOM` on the last, so "the bottom of
    the document is still being drawn" is a question about a specific string
    rather than about a general impression;
  * `LD-PAGE-{n}` on each heading.

Not part of any frozen corpus, and deliberately not written into `dist/`: the
runner builds the bytes in memory and hands them to the product's own file
input, which is also the more faithful path -- a user's document does not
arrive from the server that served the page.
"""
from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree

LINES_PER_PAGE = 18

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""

# The page geometry is DECLARED, and that is not a detail.  Without a
# page-layout and a master page the build lays the document out on a sheet with
# an aspect ratio of 2.52 -- two and a half times as tall as it is wide -- and a
# "page" then holds about 83 lines.  Measured 2026-08-19, by an edit that added
# 3,336 characters to a two-page document and did not add a page: the text fit,
# because the pages were nothing like A4 and half of the second one was empty.
# A corpus whose page is not a page cannot measure where a page count breaks
# anything.
STYLES = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.2">
 <office:styles>
  <style:style style:name="Standard" style:family="paragraph" style:class="text"/>
  <style:style style:name="Heading_20_1" style:display-name="Heading 1" style:family="paragraph" style:parent-style-name="Standard">
   <style:text-properties fo:font-size="16pt"/>
  </style:style>
 </office:styles>
 <office:automatic-styles>
  <style:page-layout style:name="LDPage">
   <style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" fo:margin-top="2cm" fo:margin-bottom="2cm" fo:margin-left="2cm" fo:margin-right="2cm"/>
  </style:page-layout>
 </office:automatic-styles>
 <office:master-styles>
  <style:master-page style:name="Standard" style:page-layout-name="LDPage"/>
 </office:master-styles>
</office:document-styles>
"""

CONTENT_HEAD = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.2">
 <office:automatic-styles>
  <style:style style:name="LDBreak" style:family="paragraph" style:parent-style-name="Heading_20_1">
   <style:paragraph-properties fo:break-before="page"/>
  </style:style>
 </office:automatic-styles>
 <office:body>
  <office:text>
"""

CONTENT_TAIL = """  </office:text>
 </office:body>
</office:document-content>
"""

# Long enough that a click lands on the line rather than past its end (finding
# 052's shape), and long enough that a page of them costs something to render.
FILLER = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do "
          "eiusmod tempor incididunt ut labore")


def build(pages: int = 1, lines_per_page: int = LINES_PER_PAGE) -> bytes:
    if pages < 1:
        raise ValueError("a document has at least one page")
    body: list[str] = []
    for page in range(1, pages + 1):
        style = "Heading_20_1" if page == 1 else "LDBreak"
        body.append(f'   <text:h text:style-name="{style}" '
                    f'text:outline-level="1">LD-PAGE-{page:02d}</text:h>\n')
        for line in range(1, lines_per_page + 1):
            marks = [f"LD-P{page:02d}-L{line:02d}"]
            if page == 1 and line == 1:
                marks.append("LD-TOP")
            if page == pages and line == lines_per_page:
                marks.append("LD-BOTTOM")
            body.append('   <text:p text:style-name="Standard">'
                        f'{" ".join(marks)} {FILLER}</text:p>\n')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        # Stored, first, uncompressed: the ODF package rule.
        archive.writestr(zipfile.ZipInfo("mimetype"),
                         "application/vnd.oasis.opendocument.text",
                         compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/manifest.xml", MANIFEST)
        archive.writestr("styles.xml", STYLES)
        archive.writestr("content.xml",
                         CONTENT_HEAD + "".join(body) + CONTENT_TAIL)
    return buffer.getvalue()


def self_test() -> int:
    """It has to be possible for this generator to be wrong."""
    failures: list[str] = []

    def verify(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    one = zipfile.ZipFile(io.BytesIO(build(1)))
    ten = zipfile.ZipFile(io.BytesIO(build(10)))
    one_xml = one.read("content.xml").decode("utf-8")
    ten_xml = ten.read("content.xml").decode("utf-8")

    verify("a one-page document has no page break",
           'text:style-name="LDBreak"' not in one_xml)
    verify("a ten-page document has exactly nine",
           ten_xml.count('text:style-name="LDBreak"') == 9,
           f"{ten_xml.count('text:style-name=\"LDBreak\"')} breaks")
    verify("every page is named once",
           all(ten_xml.count(f"LD-PAGE-{page:02d}") == 1
               for page in range(1, 11)))
    verify("every line is named once",
           all(ten_xml.count(f"LD-P{page:02d}-L{line:02d}") == 1
               for page in (1, 5, 10) for line in (1, LINES_PER_PAGE)))
    verify("the top marker is on the first line and appears once",
           ten_xml.count("LD-TOP") == 1
           and ten_xml.index("LD-TOP") < ten_xml.index("LD-P01-L02"))
    verify("the bottom marker is on the last line and appears once",
           ten_xml.count("LD-BOTTOM") == 1
           and ten_xml.index("LD-BOTTOM")
           > ten_xml.index(f"LD-P10-L{LINES_PER_PAGE - 1:02d}"))
    verify("the bottom marker is NOT in a shorter document",
           "LD-BOTTOM" in one_xml
           and "LD-P10" not in one_xml)
    verify("content.xml parses",
           _parses(one_xml) and _parses(ten_xml))
    verify("the mimetype entry is first and stored",
           ten.infolist()[0].filename == "mimetype"
           and ten.infolist()[0].compress_type == zipfile.ZIP_STORED)
    verify("the package carries what the manifest declares",
           set(ten.namelist()) == {"mimetype", "META-INF/manifest.xml",
                                   "styles.xml", "content.xml"})
    # The reason the generator exists: page count must be a parameter, not an
    # emergent property. A version that ignored `pages` would pass every check
    # above except this one.
    verify("page count scales with the argument",
           len(build(20)) > len(build(10)) > len(build(1))
           and zipfile.ZipFile(io.BytesIO(build(20))).read("content.xml")
           .decode("utf-8").count('text:style-name="LDBreak"') == 19)
    try:
        build(0)
        verify("zero pages is refused", False, "it was accepted")
    except ValueError:
        verify("zero pages is refused", True)

    print(f"\nself-test: {12 - len(failures)}/12 checks moved the verdict")
    return 1 if failures else 0


def _parses(xml: str) -> bool:
    try:
        ElementTree.fromstring(xml)
        return True
    except ElementTree.ParseError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--lines-per-page", type=int, default=LINES_PER_PAGE)
    parser.add_argument("--out", default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    raw = build(args.pages, args.lines_per_page)
    if args.out:
        Path(args.out).write_bytes(raw)
        print(f"{args.out}: {args.pages} pages, {len(raw)} bytes")
    else:
        print(f"{args.pages} pages, {len(raw)} bytes (use --out to write it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
