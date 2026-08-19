#!/usr/bin/env python3
"""A document that can REFUSE, for finding 059's missing negative arm.

Finding 059 settled which predicate replaces `success == true`: the barrier's
own postcondition, observed state against requested state.  Ten native arms
showed it agreeing nine times.  **Nothing has shown it disagreeing**, and a
predicate that has only ever been seen to agree is not yet a predicate -- the
intended refusal arm (`setViewReadOnly`) did not refuse, because core applied
the command anyway.

So this fixture carries places where an inline format has a reason not to take:

  * `F059-NEG-PLAIN-*` -- ordinary paragraphs, one per arm, so a PENDING
    attribute from one arm cannot reach the next one's marker.  These are the
    positive controls: if none of them comes back styled, the round measured
    nothing and no negative arm can be read from it.
  * a **protected section** holding `F059-NEG-PROTECTED` -- editing inside it
    is refused by Writer.  Whether the caret can even enter is itself a
    measurement: LibreOffice's default is that the cursor stays out of
    protected areas, in which case the arm reports that it could not aim rather
    than pretending it measured a refusal.

Exactly one line per paragraph, because the probe navigates by keystroke
(Ctrl+Home, Down x N, End) and a wrapped paragraph silently shifts every arm
after it.

Not part of any frozen corpus.  Regenerate at will.
"""
from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree

PLAIN_PARAGRAPHS = 8

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""

# Deliberately unstyled, including in declarations that are never used: the
# verdict is "is this marker's run styled", and any pre-existing bold anywhere
# makes a document-wide read unaskable.  The E1 corpus's unused `E1Bold` is the
# precedent this avoids.
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

# Long enough that the line is a line; short enough to stay unwrapped.
PADDING = "filler so the line is a line and nothing wraps"


def build(plain: int = PLAIN_PARAGRAPHS) -> bytes:
    body = "".join(
        f'   <text:p text:style-name="Standard">F059-NEG-PLAIN-{index:02d} '
        f'{PADDING}</text:p>\n'
        for index in range(plain))
    body += (
        '   <text:section text:name="F059NegProtected" text:protected="true">\n'
        '    <text:p text:style-name="Standard">F059-NEG-PROTECTED '
        f'{PADDING}</text:p>\n'
        '   </text:section>\n')
    # One more plain paragraph AFTER the section, so "the caret walked past the
    # protected section" and "the caret stopped at it" are distinguishable.
    body += ('   <text:p text:style-name="Standard">F059-NEG-AFTER '
             f'{PADDING}</text:p>\n')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"),
                         "application/vnd.oasis.opendocument.text",
                         compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/manifest.xml", MANIFEST)
        archive.writestr("styles.xml", STYLES)
        archive.writestr("content.xml", CONTENT_HEAD + body + CONTENT_TAIL)
    return buffer.getvalue()


def self_test() -> int:
    failures: list[str] = []

    def verify(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    raw = build()
    archive = zipfile.ZipFile(io.BytesIO(raw))
    content = archive.read("content.xml").decode("utf-8")
    styles = archive.read("styles.xml").decode("utf-8")

    verify("one paragraph per arm, plus the protected one and the one after",
           content.count("<text:p ") == PLAIN_PARAGRAPHS + 2,
           f"{content.count('<text:p ')} paragraphs")
    verify("every plain paragraph is uniquely identifiable",
           all(content.count(f"F059-NEG-PLAIN-{i:02d}") == 1
               for i in range(PLAIN_PARAGRAPHS)))
    verify("the section is declared protected",
           'text:protected="true"' in content
           and content.count("<text:section ") == 1)
    verify("the protected paragraph is INSIDE the section",
           content.index("<text:section ")
           < content.index("F059-NEG-PROTECTED")
           < content.index("</text:section>"))
    verify("there is a paragraph after the section",
           content.index("</text:section>") < content.index("F059-NEG-AFTER"))
    # The whole point: nothing may be styled before the probe runs.
    for attribute in ("fo:font-weight", "fo:font-style",
                      "style:text-underline-style", "style:text-line-through-style"):
        verify(f"no {attribute} anywhere, including unused declarations",
               attribute not in content and attribute not in styles)
    try:
        ElementTree.fromstring(content)
        verify("content.xml parses", True)
    except ElementTree.ParseError as error:
        verify("content.xml parses", False, str(error))
    verify("the mimetype entry is first and stored",
           archive.infolist()[0].filename == "mimetype"
           and archive.infolist()[0].compress_type == zipfile.ZIP_STORED)

    print(f"\nself-test: {11 - len(failures)}/11 checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    target = Path(args.out or (Path(__file__).resolve().parent.parent
                               / "test-docs" / "f059-negative-arm.odt"))
    target.write_bytes(build())
    print(f"{target}: {target.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
