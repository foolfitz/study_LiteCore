#!/usr/bin/env python3
"""One short, plain paragraph per arm, for the finding 059 predicate probe.

The probe needs each arm to own a paragraph, for two reasons:

  * an inline format on a collapsed caret is a PENDING attribute, so two arms
    sharing a paragraph would let one arm's pending bold reach the next arm's
    marker;
  * the caret is placed by keystroke (Ctrl+Home, then Down x N, then End) rather
    than by clicking a guessed y, so every paragraph must be exactly one line --
    a wrapped paragraph makes Down move within it and the arms silently shift.

Deliberately unstyled: no bold, italic, underline or strikethrough anywhere in
the document, including in unused style declarations. The E1 corpus declares an
`E1Bold` it never uses and carries a bold heading style, and a document-wide
grep for `fo:font-weight` passes there whatever the probe did.

Not part of any frozen corpus. Regenerate at will.
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

PARAGRAPHS = 14

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""

STYLES = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.2">
 <office:styles>
  <style:style style:name="Standard" style:family="paragraph" style:class="text"/>
 </office:styles>
</office:document-styles>
"""

CONTENT_HEAD = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.2">
 <office:body>
  <office:text>
"""

CONTENT_TAIL = """  </office:text>
 </office:body>
</office:document-content>
"""


def build(paragraphs: int = PARAGRAPHS) -> bytes:
    import io
    body = "".join(
        f'   <text:p text:style-name="Standard">F059-P{index:02d}</text:p>\n'
        for index in range(paragraphs))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        # Stored, first, uncompressed: the ODF package rule.
        archive.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/vnd.oasis.opendocument.text",
            compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/manifest.xml", MANIFEST)
        archive.writestr("styles.xml", STYLES)
        archive.writestr("content.xml", CONTENT_HEAD + body + CONTENT_TAIL)
    return buffer.getvalue()


def self_test() -> int:
    """It has to be possible for this fixture to be wrong."""
    failures = []

    def verify(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    import io
    raw = build()
    archive = zipfile.ZipFile(io.BytesIO(raw))
    content = archive.read("content.xml").decode("utf-8")
    styles = archive.read("styles.xml").decode("utf-8")

    verify("one paragraph per arm and then some",
           content.count("<text:p ") == PARAGRAPHS,
           f"{content.count('<text:p ')} paragraphs")
    verify("every paragraph is uniquely identifiable",
           all(f"F059-P{i:02d}" in content for i in range(PARAGRAPHS)))
    # The point of the fixture: the probe's document-side verdict is "is this
    # marker's run styled", and any pre-existing styling makes that unaskable.
    for attribute in ("fo:font-weight", "fo:font-style",
                      "style:text-underline-style", "style:text-line-through-style"):
        verify(f"no {attribute} anywhere in the document",
               attribute not in content and attribute not in styles)
    verify("the mimetype entry is stored, not deflated",
           archive.getinfo("mimetype").compress_type == zipfile.ZIP_STORED)
    print(f"\nself-test: {7 - len(failures)}/7 checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parent.parent
                        / "test-docs" / "f059-predicate-paragraphs.odt")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    args.out.write_bytes(build())
    print(f"wrote {args.out} ({PARAGRAPHS} paragraphs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
