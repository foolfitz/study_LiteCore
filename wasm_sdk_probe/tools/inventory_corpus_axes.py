#!/usr/bin/env python3
"""Task 034: what ODF constructs each fixture actually contains, computed.

Four findings in a row -- 034, 035, 037, 038 -- were the same failure, and it
was never "the matrix had a cell we skipped".  It was "the matrix had no axis
for this, and nobody could see the axis was missing".  037 needed an as-char
`draw:frame`; 038 needed an as-char `draw:frame` *inside a footnote body*, and
E1-C's five-document corpus carried 105 as-char frames and not one `text:note`,
so that combination could not appear no matter how many times the suite ran.

The distinguishing feature of that class of gap is that it is invisible from
the test list.  It is not invisible from the *bytes*.  This reads the bytes.

Two things come out:

  axes         per fixture, how many of each named construct it holds -- read
               out of content.xml and styles.xml, never declared by hand
  composites   the co-occurrence grid: for each container (footnote, endnote,
               table cell, text box, header/footer, section) crossed with each
               content construct, how many of that construct live inside that
               container.  Every one of 034/035/037/038 is a cell in this grid.

A suite (E1-C's C3, E1-A's frozen five, ...) is scored by rolling its fixtures
up and listing the cells that stay at zero.  Those empty cells are the suite's
blind spots, stated in advance instead of discovered by a hang.

This does not decide what a suite *ought* to cover -- that is a judgement, and
it belongs in the spec.  It decides what a suite *does* cover, so the judgement
has something true underneath it.  SPEC-E1-C 9.1 asserts by hand that none of
the five C3 documents contains a `text:note`; run this and that sentence stops
being a thing someone checked once.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

NS = {
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
}


def qname(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def attribute(element: ElementTree.Element, prefix: str, local: str) -> str | None:
    return element.get(qname(prefix, local))


# Containers: constructs that hold other content.  The 038 family lives in the
# gap between "the corpus has X" and "the corpus has X *inside* Y".
CONTAINERS: dict[str, Any] = {
    "footnote": lambda e: e.tag == qname("text", "note")
    and attribute(e, "text", "note-class") == "footnote",
    "endnote": lambda e: e.tag == qname("text", "note")
    and attribute(e, "text", "note-class") == "endnote",
    "table-cell": lambda e: e.tag == qname("table", "table-cell"),
    "text-box": lambda e: e.tag == qname("draw", "text-box"),
    "header-footer": lambda e: e.tag in {qname("style", "header"), qname("style", "footer")},
    "section": lambda e: e.tag == qname("text", "section"),
    "list-item": lambda e: e.tag == qname("text", "list-item"),
    "annotation": lambda e: e.tag == qname("office", "annotation"),
    "tracked-change": lambda e: e.tag == qname("text", "tracked-changes"),
}

# Content constructs.  Frames are split by anchor type because that one
# attribute is the whole difference between finding 012 firing and not:
# frame-paragraph-anchored closes in 11 ms, frame-char-anchored needs recovery.
CONTENT: dict[str, Any] = {
    "frame-as-char": lambda e: e.tag == qname("draw", "frame")
    and attribute(e, "text", "anchor-type") == "as-char",
    "frame-char": lambda e: e.tag == qname("draw", "frame")
    and attribute(e, "text", "anchor-type") == "char",
    "frame-paragraph": lambda e: e.tag == qname("draw", "frame")
    and attribute(e, "text", "anchor-type") == "paragraph",
    "frame-page": lambda e: e.tag == qname("draw", "frame")
    and attribute(e, "text", "anchor-type") == "page",
    "frame-other-anchor": lambda e: e.tag == qname("draw", "frame")
    and attribute(e, "text", "anchor-type") not in {"as-char", "char", "paragraph", "page"},
    "image": lambda e: e.tag == qname("draw", "image"),
    "ole-object": lambda e: e.tag in {qname("draw", "object"), qname("draw", "object-ole")},
    "heading": lambda e: e.tag == qname("text", "h"),
    "list": lambda e: e.tag == qname("text", "list"),
    "table": lambda e: e.tag == qname("table", "table"),
    "note-citation": lambda e: e.tag == qname("text", "note-citation"),
    "hyperlink": lambda e: e.tag == qname("text", "a"),
    "bookmark": lambda e: e.tag in {
        qname("text", "bookmark"), qname("text", "bookmark-start")},
    "line-break": lambda e: e.tag == qname("text", "line-break"),
    "tab": lambda e: e.tag == qname("text", "tab"),
    "soft-page-break": lambda e: e.tag == qname("text", "soft-page-break"),
    "change-mark": lambda e: e.tag in {
        qname("text", "change"), qname("text", "change-start")},
}

PARAGRAPH_TAGS = {qname("text", "p"), qname("text", "h")}

# Axes that need to know where the element sits, not just what it is.
#
# `text:anchor-type="as-char"` on a frame that is NOT inside a paragraph does
# not mean what it says: as-char anchoring is a position in a text flow, and at
# body level there is none.  Counting the attribute alone gave a badly wrong
# answer the first time this tool was used for a coverage claim --
# l4-stress-100 carries 100 as-char-attributed frames directly under
# office:text and closes in 4 ms, while l0-t2-styled's single one inside a
# text:p needs the 10.8 s close recovery of finding 012.  On the attribute
# alone the corpus looked like it had 101 samples of the construct behind
# findings 012/037/038.  It has one.
#
# Kept as their own axes rather than as a `paragraph` container in the
# co-occurrence grid: nearly every construct in a text document is inside a
# paragraph, so that container would add a full row of noise to hide one signal.
CONTEXTUAL_CONTENT: dict[str, Any] = {
    "frame-as-char-in-paragraph": lambda e, ancestors: (
        e.tag == qname("draw", "frame")
        and attribute(e, "text", "anchor-type") == "as-char"
        and any(a.tag in PARAGRAPH_TAGS for a in ancestors)),
    "frame-as-char-body-level": lambda e, ancestors: (
        e.tag == qname("draw", "frame")
        and attribute(e, "text", "anchor-type") == "as-char"
        and not any(a.tag in PARAGRAPH_TAGS for a in ancestors)),
}

# Script axes, counted over text rather than elements.  035 was a CJK paragraph
# failing closed; a corpus that is all Latin cannot show that.
SCRIPT_RANGES = {
    "han": lambda ch: "CJK" in unicodedata.name(ch, ""),
    "hiragana-katakana": lambda ch: unicodedata.name(ch, "").startswith(
        ("HIRAGANA", "KATAKANA")),
    "hangul": lambda ch: unicodedata.name(ch, "").startswith("HANGUL"),
    "arabic-hebrew": lambda ch: unicodedata.name(ch, "").startswith(("ARABIC", "HEBREW")),
    "combining-mark": lambda ch: unicodedata.combining(ch) != 0,
}


def parse_members(path: Path) -> list[ElementTree.Element]:
    """content.xml and styles.xml as roots; styles.xml carries headers/footers."""
    roots = []
    with zipfile.ZipFile(path) as archive:
        members = set(archive.namelist())
        for name in ("content.xml", "styles.xml"):
            if name not in members:
                continue
            roots.append(ElementTree.fromstring(archive.read(name)))
    return roots


def walk(root: ElementTree.Element) -> list[tuple[ElementTree.Element, list[ElementTree.Element]]]:
    """Every element with its ancestor chain, so containment is answerable."""
    output: list[tuple[ElementTree.Element, list[ElementTree.Element]]] = []
    stack: list[tuple[ElementTree.Element, list[ElementTree.Element]]] = [(root, [])]
    while stack:
        element, ancestors = stack.pop()
        output.append((element, ancestors))
        chain = ancestors + [element]
        for child in element:
            stack.append((child, chain))
    return output


def inventory(path: Path) -> dict[str, Any]:
    axes = ({name: 0 for name in CONTAINERS} | {name: 0 for name in CONTENT}
            | {name: 0 for name in CONTEXTUAL_CONTENT})
    composites = {
        container: {content: 0 for content in CONTENT} for container in CONTAINERS
    }
    scripts = {name: 0 for name in SCRIPT_RANGES}
    text_length = 0

    for root in parse_members(path):
        for element, ancestors in walk(root):
            for name, predicate in CONTAINERS.items():
                if predicate(element):
                    axes[name] += 1
            enclosing = {
                name for name, predicate in CONTAINERS.items()
                if any(predicate(ancestor) for ancestor in ancestors)
            }
            for name, predicate in CONTENT.items():
                if not predicate(element):
                    continue
                axes[name] += 1
                for container in enclosing:
                    composites[container][name] += 1
            for name, predicate in CONTEXTUAL_CONTENT.items():
                if predicate(element, ancestors):
                    axes[name] += 1
            for chunk in (element.text, element.tail):
                if not chunk:
                    continue
                text_length += len(chunk)
                for character in chunk:
                    for name, predicate in SCRIPT_RANGES.items():
                        if predicate(character):
                            scripts[name] += 1

    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "axes": axes,
        "composites": composites,
        "scripts": scripts,
        "textLength": text_length,
    }


def roll_up(entries: list[dict[str, Any]]) -> dict[str, Any]:
    axes = ({name: 0 for name in CONTAINERS} | {name: 0 for name in CONTENT}
            | {name: 0 for name in CONTEXTUAL_CONTENT})
    composites = {
        container: {content: 0 for content in CONTENT} for container in CONTAINERS
    }
    scripts = {name: 0 for name in SCRIPT_RANGES}
    for entry in entries:
        for name, value in entry["axes"].items():
            axes[name] += value
        for container, row in entry["composites"].items():
            for content, value in row.items():
                composites[container][content] += value
        for name, value in entry["scripts"].items():
            scripts[name] += value
    return {"axes": axes, "composites": composites, "scripts": scripts}


def blind_spots(rollup: dict[str, Any]) -> dict[str, Any]:
    """What a suite provably cannot exercise, because it is not in the bytes."""
    return {
        "absentAxes": sorted(name for name, value in rollup["axes"].items() if value == 0),
        "absentScripts": sorted(
            name for name, value in rollup["scripts"].items() if value == 0),
        # Only report a cell when the suite HAS the container -- "no frames in a
        # footnote" is a different statement when there are no footnotes at all,
        # and the second is already covered by absentAxes.  Conflating them is
        # how "we tested frames and we tested notes" came to sound like cover.
        "emptyComposites": sorted(
            f"{container}/{content}"
            for container, row in rollup["composites"].items()
            if rollup["axes"][container] > 0
            for content, value in row.items()
            if value == 0 and rollup["axes"][content] > 0
        ),
    }


def load_suites(path: Path | None) -> dict[str, list[str]]:
    if path is None or not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("suites", {})


def resolve(project: Path, reference: str) -> Path:
    return (project / reference).resolve()


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus", type=Path, action="append",
        help="directory of documents to inventory; repeatable "
             "(default: test-docs/e1 and test-docs/r7-compat)")
    parser.add_argument(
        "--suites", type=Path, default=project / "e1" / "content-axis-suites.json",
        help="named fixture sets to roll up and score")
    parser.add_argument(
        "--output", type=Path,
        default=project.parent / "findings" / "evidence" / "sdk-e1" / "baseline"
        / "content-axes.json")
    parser.add_argument(
        "--check", action="store_true",
        help="exit non-zero if a suite's declared expectations do not hold")
    args = parser.parse_args()

    corpora = args.corpus or [project / "test-docs" / "e1",
                              project / "test-docs" / "r7-compat"]
    entries: dict[str, dict[str, Any]] = {}
    unreadable: list[dict[str, str]] = []
    for directory in corpora:
        for path in sorted(Path(directory).glob("*.odt")):
            try:
                entries[path.name] = inventory(path)
            except (zipfile.BadZipFile, ElementTree.ParseError, KeyError) as error:
                # The L3 corpus is deliberately corrupt.  Say so and move on;
                # silently dropping them would make the corpus look smaller
                # than it is.
                unreadable.append({"path": str(path), "reason": type(error).__name__})

    suites = load_suites(args.suites if args.suites.is_file() else None)
    scored: dict[str, Any] = {}
    failures: list[str] = []
    for name, definition in suites.items():
        members = definition["fixtures"] if isinstance(definition, dict) else definition
        missing = [item for item in members if item not in entries]
        selected = [entries[item] for item in members if item in entries]
        rollup = roll_up(selected)
        gaps = blind_spots(rollup)
        expectations = definition.get("expect", {}) if isinstance(definition, dict) else {}
        checked = {}
        for axis, expected in expectations.items():
            actual = rollup["axes"].get(axis)
            if actual is None:
                composite = re.fullmatch(r"([\w-]+)/([\w-]+)", axis)
                actual = (rollup["composites"].get(composite.group(1), {})
                          .get(composite.group(2)) if composite else None)
            held = (actual == 0) if expected == "absent" else (
                (actual or 0) > 0 if expected == "present" else actual == expected)
            checked[axis] = {"expect": expected, "actual": actual, "held": held}
            if not held:
                failures.append(f"{name}: {axis} expected {expected}, measured {actual}")
        if missing:
            failures.append(f"{name}: fixtures not found: {', '.join(missing)}")
        scored[name] = {
            "fixtures": members,
            "missingFixtures": missing,
            "rollup": rollup,
            "blindSpots": gaps,
            "expectations": checked,
        }

    result = {
        "schemaVersion": 1,
        "release": "content-axis-inventory",
        "corpora": [str(item) for item in corpora],
        "fixtureCount": len(entries),
        "unreadable": unreadable,
        "fixtures": entries,
        "suites": scored,
        "pass": not failures,
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "fixtures": len(entries),
        "unreadable": len(unreadable),
        "suites": {name: {"absentAxes": len(item["blindSpots"]["absentAxes"]),
                          "emptyComposites": len(item["blindSpots"]["emptyComposites"])}
                   for name, item in scored.items()},
        "pass": result["pass"],
        "failures": failures,
    }, ensure_ascii=False, indent=2))
    if args.check and failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
