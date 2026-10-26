#!/usr/bin/env python3
"""The paragraph text sequence of an ODF text document (SPEC-M3-paragraph-merge
section 12).

Typed text carries a per-session rsid (SwDoc::UpdateRsid) and WASM types by
paste where the native probe types by keys, so a document with typed text in
it can never be byte-identical across sessions or platforms.  What those
comparisons are for is where the text landed -- which paragraph, which
position -- and that is what this returns: one string per text:p / text:h, in
document order, spans unwrapped, text:s expanded, text:tab as U+0009 and
text:line-break as U+2028.  Paragraphs nested in notes, frames and annotations
are listed on their own, after the paragraph that holds them, and are not
folded into its text.

Usage:
  odt_paragraphs.py FILE.odt            print the sequence as JSON
  odt_paragraphs.py --diff A.odt B.odt  exit 1 if the sequences differ
  odt_paragraphs.py --self-test         the comparator's own red cases
"""
from __future__ import annotations

import json
import sys
import zipfile
import xml.etree.ElementTree as ET

TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
DRAW = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
PARAGRAPHS = {f"{{{TEXT}}}p", f"{{{TEXT}}}h"}
# Children whose own paragraphs are listed separately, never inlined.
CONTAINERS = {f"{{{TEXT}}}note", f"{{{DRAW}}}frame", f"{{{OFFICE}}}annotation"}


def _inline(element: ET.Element, out: list[str]) -> None:
    if element.text:
        out.append(element.text)
    for child in element:
        tag = child.tag
        if tag in CONTAINERS:
            pass
        elif tag == f"{{{TEXT}}}s":
            out.append(" " * int(child.get(f"{{{TEXT}}}c", "1")))
        elif tag == f"{{{TEXT}}}tab":
            out.append("\t")
        elif tag == f"{{{TEXT}}}line-break":
            out.append(" ")
        else:
            _inline(child, out)
        if child.tail:
            out.append(child.tail)


def paragraph_texts_from_xml(content: bytes) -> list[str]:
    root = ET.fromstring(content)
    body = root.find(f"{{{OFFICE}}}body")
    if body is None:
        raise ValueError("content.xml has no office:body")
    texts = []
    for element in body.iter():
        if element.tag in PARAGRAPHS:
            parts: list[str] = []
            _inline(element, parts)
            texts.append("".join(parts))
    return texts


def paragraph_texts(path: str) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return paragraph_texts_from_xml(archive.read("content.xml"))


def first_difference(a: list[str], b: list[str]) -> str | None:
    for index, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f"paragraph {index}: {x!r} != {y!r}"
    if len(a) != len(b):
        return f"paragraph count {len(a)} != {len(b)}"
    return None


def _doc(body: str) -> bytes:
    return (f'<office:document-content xmlns:office="{OFFICE}" xmlns:text="{TEXT}" '
            f'xmlns:draw="{DRAW}"><office:body><office:text>{body}'
            '</office:text></office:body></office:document-content>').encode()


def self_test() -> int:
    base = _doc('<text:p>ab<text:span>cZ</text:span>d<text:line-break/>e</text:p><text:h>f<text:s text:c="2"/>g</text:h>')
    same_other_markup = _doc('<text:p>abc<text:span text:style-name="T1">Z</text:span>d<text:line-break/>e</text:p><text:h>f  g</text:h>')
    moved = _doc('<text:p>abZcd<text:line-break/>e</text:p><text:h>f  g</text:h>')
    split = _doc('<text:p>abcZ</text:p><text:p>d<text:line-break/>e</text:p><text:h>f  g</text:h>')
    line_break_lost = _doc('<text:p>abcZde</text:p><text:h>f  g</text:h>')
    t = paragraph_texts_from_xml
    checks = [
        ("same text, other markup, is equal", first_difference(t(base), t(same_other_markup)) is None),
        ("a character moved inside its paragraph is red", first_difference(t(base), t(moved)) is not None),
        ("a paragraph split in two is red", first_difference(t(base), t(split)) is not None),
        ("a lost line break is red", first_difference(t(base), t(line_break_lost)) is not None),
    ]
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
    return 0 if all(ok for _, ok in checks) else 1


def main(argv: list[str]) -> int:
    if argv[:1] == ["--self-test"]:
        return self_test()
    if argv[:1] == ["--diff"] and len(argv) == 3:
        difference = first_difference(paragraph_texts(argv[1]), paragraph_texts(argv[2]))
        print(difference or "equal")
        return 1 if difference else 0
    if len(argv) == 1:
        print(json.dumps(paragraph_texts(argv[0]), ensure_ascii=False, indent=1))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
