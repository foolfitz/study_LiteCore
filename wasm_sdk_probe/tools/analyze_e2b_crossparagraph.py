#!/usr/bin/env python3
"""SPEC E2-B 9.7 check 3: judge the undo from the saved documents.

Separate from the probe on purpose, same as the e2b-gate pair: the probe drives
LOK and keeps files, this reads only those files.

Check 3 asks whether a cross-paragraph format dispatch is a SINGLE undo step.
That is a question about the document, so it is answered from the document --
not from whether `.uno:Undo` returned.  The probe saves four states per arm:
before the dispatch, after it, after one undo, after two.

The paragraph signature is the same one the e2b-gate analyzer uses, and for the
same reasons: automatic style names renumber, so they are folded to `(auto)`,
and bullet-versus-number lives on the list style, not on the paragraph.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
AUTOMATIC_NAME = re.compile(r"^(P|L|T|Sect|fr|Mfr)\d+$")


def opaque(name: str | None) -> str | None:
    if name is None:
        return None
    return "(auto)" if AUTOMATIC_NAME.match(name) else name


def list_kinds(root) -> dict[str, str]:
    kinds: dict[str, str] = {}
    automatic = root.find(f"{{{OFFICE_NS}}}automatic-styles")
    if automatic is None:
        return kinds
    for style in automatic.findall(f"{{{TEXT_NS}}}list-style"):
        name = style.get(f"{{{STYLE_NS}}}name")
        for level in style:
            tag = level.tag.split("}")[1]
            if tag.startswith("list-level-style-"):
                kinds[name] = tag.rsplit("-", 1)[-1]
                break
    return kinds


def paragraphs(odt: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(odt) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    body = root.find(f"{{{OFFICE_NS}}}body/{{{OFFICE_NS}}}text")
    kinds = list_kinds(root)
    rows: list[dict[str, Any]] = []

    def walk(node, in_list: str | None) -> None:
        for child in node:
            tag = child.tag.split("}")[1]
            if tag in ("p", "h"):
                rows.append({
                    "kind": tag,
                    "style": opaque(child.get(f"{{{TEXT_NS}}}style-name")),
                    "outline": child.get(f"{{{TEXT_NS}}}outline-level"),
                    "list": in_list,
                    "text": "".join(child.itertext()),
                })
            elif tag == "list":
                walk(child, kinds.get(child.get(f"{{{TEXT_NS}}}style-name"), "list"))
            elif tag in ("list-item", "list-header"):
                walk(child, in_list)

    walk(body, None)
    return rows


def signature(row: dict[str, Any]) -> tuple:
    return (row["kind"], row["style"], row["outline"], row["list"], row["text"])


def changed(before: list[dict], after: list[dict]) -> list[str]:
    if len(before) != len(after):
        return [f"paragraph count {len(before)} -> {len(after)}"]
    return [b["text"][:30] for b, a in zip(before, after)
            if signature(b) != signature(a)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("saved", type=Path, help="directory of saved ODTs")
    args = parser.parse_args()

    verdicts = []
    for before in sorted(args.saved.glob("*-before.odt")):
        stem = before.name[: -len("-before.odt")]
        states = {name: args.saved / f"{stem}-{name}.odt"
                  for name in ("after", "undo", "undo2")}
        missing = [n for n, p in states.items() if not p.exists()]
        if missing:
            verdicts.append({"arm": stem, "void": f"missing saves: {missing}"})
            continue
        base = paragraphs(before)
        row = {
            "arm": stem,
            "dispatchChanged": changed(base, paragraphs(states["after"])),
            "afterOneUndo": changed(base, paragraphs(states["undo"])),
            "afterTwoUndos": changed(base, paragraphs(states["undo2"])),
        }
        row["dispatchApplied"] = bool(row["dispatchChanged"])
        row["singleStepUndo"] = (row["dispatchApplied"]
                                 and row["afterOneUndo"] == [])
        verdicts.append(row)

    print(json.dumps({"verdicts": verdicts}, indent=2, ensure_ascii=False))
    (args.saved.parent / "undo-verdict.json").write_text(
        json.dumps({"verdicts": verdicts}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    ok = all(v.get("singleStepUndo") for v in verdicts)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
