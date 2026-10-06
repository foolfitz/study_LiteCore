#!/usr/bin/env python3
"""Read a run of tools/run_merge_native.sh and say, per case, what the
one-unit selection looked like and whether deleting it gave the user's own
key's document.

Each saved ODT is reduced to a list of blocks (paragraph or heading with its
resolved style, outline level, list membership and list type, break-before,
the indents its automatic style sets, and whether a heading is counted;
tables and sections as nested blocks; line breaks, tabs, frames and bookmarks
as markers in the text).  Two documents are "the same" when those lists are
equal.

The indents, the heading's is-list-header and the bookmarks were added on
2026-10-06 for the second round: Writer's own Backspace at an indented
paragraph's start removes the indent instead of merging (SwWrtShell::
TryRemoveIndent), and at a heading's start marks it not counted (NumOrNoNum);
neither shows in a style name or in the text, so the first reduction could
not see what the key did.  Soft page breaks are layout and are dropped.

When the key arm pressed its key more than once (the probe's PRESSES), the
summary also says after how many presses the key's document equals the select
arm's ("keyPressesToMatchSelect", null when none of the recorded presses did).

Usage: analyze_merge_native.py ROUND_DIR [--json OUT] [--control CASE]
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
}


def q(prefix: str, name: str) -> str:
    return f"{{{NS[prefix]}}}{name}"


class Styles:
    """Automatic paragraph styles resolved to what matters for a merge."""

    def __init__(self, root: ET.Element):
        self.paragraph: dict[str, dict[str, str]] = {}
        self.lists: dict[str, str] = {}
        for auto in root.iter(q("office", "automatic-styles")):
            for style in auto.findall(q("style", "style")):
                if style.get(q("style", "family")) != "paragraph":
                    continue
                props = style.find(q("style", "paragraph-properties"))
                get = (lambda k: props.get(q("fo", k)) if props is not None else None)
                self.paragraph[style.get(q("style", "name"))] = {
                    "parent": style.get(q("style", "parent-style-name")) or "",
                    "breakBefore": get("break-before") or "",
                    "listStyle": style.get(q("style", "list-style-name")) or "",
                    "indents": {k: v for k in ("text-indent", "margin-left") if (v := get(k)) is not None},
                }
            for lst in auto.findall(q("text", "list-style")):
                self.lists[lst.get(q("style", "name"))] = self.list_kind(lst)

    @staticmethod
    def list_kind(lst: ET.Element) -> str:
        for child in lst:
            if child.get(q("text", "level")) == "1":
                if child.tag == q("text", "list-level-style-bullet"):
                    return "bullet"
                if child.tag == q("text", "list-level-style-number"):
                    return "number:" + (child.get(q("style", "num-format")) or "")
        return "?"

    def paragraph_style(self, name: str | None) -> tuple[str, str, dict[str, str]]:
        if not name:
            return "", "", {}
        auto = self.paragraph.get(name)
        if auto is None:
            return name, "", {}
        return auto["parent"], auto["breakBefore"], auto["indents"]

    def list_type(self, name: str | None) -> str:
        if not name:
            return ""
        return self.lists.get(name, name)


def inline_text(element: ET.Element) -> str:
    out = [element.text or ""]
    for child in element:
        tag = child.tag
        if tag == q("text", "line-break"):
            out.append("⏎")
        elif tag == q("text", "tab"):
            out.append("⇥")
        elif tag == q("text", "s"):
            out.append(" " * int(child.get(q("text", "c")) or 1))
        elif tag == q("draw", "frame"):
            out.append(f"[frame:{child.get(q('text', 'anchor-type'))}:{child.get(q('draw', 'name'))}]")
        elif tag == q("text", "bookmark"):
            out.append(f"[bm:{child.get(q('text', 'name'))}]")
        elif tag == q("text", "bookmark-start"):
            out.append(f"[bm<:{child.get(q('text', 'name'))}]")
        elif tag == q("text", "bookmark-end"):
            out.append(f"[bm>:{child.get(q('text', 'name'))}]")
        elif tag == q("text", "soft-page-break"):
            pass
        else:
            out.append(inline_text(child))
        out.append(child.tail or "")
    return "".join(out)


def blocks(parent: ET.Element, styles: Styles, lists: tuple[str, ...] = ()) -> list:
    out = []
    for child in parent:
        tag = child.tag
        if tag in (q("text", "p"), q("text", "h")):
            style, brk, indents = styles.paragraph_style(child.get(q("text", "style-name")))
            block = {"kind": "h" if tag == q("text", "h") else "p", "style": style, "text": inline_text(child)}
            if tag == q("text", "h"):
                block["outline"] = child.get(q("text", "outline-level"))
                if child.get(q("text", "is-list-header")):
                    block["listHeader"] = child.get(q("text", "is-list-header"))
            if brk:
                block["breakBefore"] = brk
            if indents:
                block["indents"] = indents
            if lists:
                block["list"] = list(lists)
            out.append(block)
        elif tag == q("text", "list"):
            kind = styles.list_type(child.get(q("text", "style-name")))
            for item in child:
                header = item.tag == q("text", "list-header")
                out.extend(blocks(item, styles, lists + ((kind + (":header" if header else "")),)))
        elif tag == q("table", "table"):
            rows = []
            for row in child.iter(q("table", "table-row")):
                rows.append([blocks(cell, styles) for cell in row.findall(q("table", "table-cell"))])
            out.append({"kind": "table", "name": child.get(q("table", "name")), "rows": rows})
        elif tag == q("text", "section"):
            out.append({"kind": "section", "name": child.get(q("text", "name")), "blocks": blocks(child, styles, lists)})
        elif tag in (q("text", "sequence-decls"), q("text", "variable-decls"), q("office", "forms"),
                     q("text", "tracked-changes"), q("text", "soft-page-break")):
            pass
        else:
            out.append({"kind": "other", "tag": tag.split("}")[-1]})
    return out


def document(path: Path) -> list:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    text = root.find(f".//{q('office', 'text')}")
    return blocks(text, Styles(root))


def flatten(items: list, prefix: str = "") -> list[str]:
    """One line per block, for a readable diff."""
    lines = []
    for block in items:
        if block["kind"] == "table":
            lines.append(f"{prefix}TABLE {block['name']}")
            for r, row in enumerate(block["rows"]):
                for c, cell in enumerate(row):
                    lines += flatten(cell, f"{prefix}  [{r},{c}] ")
        elif block["kind"] == "section":
            lines.append(f"{prefix}SECTION {block['name']}")
            lines += flatten(block["blocks"], prefix + "  ")
        else:
            extra = "".join(f" {k}={block[k]}" for k in ("outline", "listHeader", "breakBefore", "indents", "list")
                            if k in block)
            lines.append(f"{prefix}{block['kind']} [{block.get('style')}]{extra} {block.get('text')!r}")
    return lines


def diff(a: list, b: list) -> list[str]:
    fa, fb = flatten(a), flatten(b)
    out = []
    for line in fa:
        if line not in fb:
            out.append("- " + line)
    for line in fb:
        if line not in fa:
            out.append("+ " + line)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("round_dir", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--control", default="C01",
                        help="case whose key arm must change the document (a plain Delete at a paragraph's end)")
    args = parser.parse_args()
    docs = args.round_dir / "docs"
    arms = [json.loads(line) for line in (args.round_dir / "arms.jsonl").read_text().splitlines()
            if line.startswith("{") and '"case"' in line]
    if not arms:
        print("no arms in arms.jsonl", file=sys.stderr)
        return 1
    original = document(docs / "original.odt")
    # Positive control: Writer's own Delete at the end of a plain paragraph
    # merges.  If that left the document unchanged, nothing here could change
    # it (a stale lock once made every load read-only, and every arm "same").
    control = docs / f"r1-{args.control}-key.odt"
    if not control.exists() or document(control) == original:
        print(f"POSITIVE CONTROL FAILED: the key arm of {args.control} is missing or changed nothing;"
              " the document was not editable", file=sys.stderr)
        return 1
    by_case: dict[str, list] = defaultdict(list)
    for arm in arms:
        by_case[arm["case"]].append(arm)

    summary = {}
    for case, entries in by_case.items():
        rounds = sorted({e["round"] for e in entries})
        boundary = entries[0]["boundary"]
        signatures, verdicts, undo, results, placed_ok = set(), [], [], set(), True
        presses_to_match: list = []
        detail = None
        for r in rounds:
            sel = next(e for e in entries if e["round"] == r and e["arm"] == "select")
            key = next(e for e in entries if e["round"] == r and e["arm"] == "key")
            for e in (sel, key):
                if (e.get("placed") or {}).get("type") != 0:
                    placed_ok = False
            # The probe's own self-check: caret-to-edge text equals the anchor.
            if sel.get("placementOk") is not True:
                placed_ok = False
            unit = sel.get("unit") or {}
            signatures.add((unit.get("type"), tuple(unit.get("codePoints") or ()), unit.get("rectangleCount")))
            stem = docs / f"r{r}-{case}"
            key_doc = document(Path(f"{stem}-key.odt"))
            if sel.get("dispatched"):
                results.add(sel.get("result", "")[:160])
                sel_doc = document(Path(f"{stem}-select.odt"))
                same = sel_doc == key_doc
                verdicts.append("same" if same else "differs")
                undo.append(document(Path(f"{stem}-select-undo.odt")) == original)
                later = sorted(int(e["press"]) for e in key.get("laterPresses") or [])
                if later:
                    match = 1 if same else None
                    for n in later:
                        if match is None and document(Path(f"{stem}-key{n}.odt")) == sel_doc:
                            match = n
                    presses_to_match.append(match)
                if not same and detail is None:
                    detail = {"select-vs-key": diff(key_doc, sel_doc)}
            else:
                verdicts.append("not dispatched; key " + ("changed nothing" if key_doc == original else "CHANGED the document"))
                if key_doc != original and detail is None:
                    detail = {"key-vs-original": diff(original, key_doc)}
            if detail is None and key_doc == original and sel.get("dispatched"):
                detail = {"note": "the key changed nothing"}
        summary[case] = {
            "boundary": boundary, "backward": entries[0]["backward"], "rounds": len(rounds),
            "caretCollapsedBeforeEveryArm": placed_ok,
            "unitSignatures": [{"type": t, "codePoints": list(cp), "rectangles": rc} for t, cp, rc in sorted(signatures, key=str)],
            "selectVsKey": verdicts, "undoRestores": undo, "commandResults": sorted(results), "detail": detail,
        }
        if presses_to_match:
            summary[case]["keyPressesToMatchSelect"] = presses_to_match

    for case in sorted(summary):
        s = summary[case]
        sig = "; ".join(f"type {x['type']} cp {x['codePoints']} rects {x['rectangles']}" for x in s["unitSignatures"])
        verdict = sorted(set(s["selectVsKey"]))
        print(f"{case} {'⌫' if s['backward'] else '⌦'} {s['boundary']:<32} unit[{sig}]  {verdict}"
              f"  undo={sorted(set(s['undoRestores']))}{'' if s['caretCollapsedBeforeEveryArm'] else '  PLACEMENT-NOT-COLLAPSED'}"
              + (f"  presses-to-match={s['keyPressesToMatchSelect']}" if "keyPressesToMatchSelect" in s else ""))
        if s["detail"] and "note" not in s["detail"]:
            for k, lines in s["detail"].items():
                for line in lines[:8]:
                    print(f"      {k}: {line}")
    if args.json:
        args.json.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
