#!/usr/bin/env python3
"""Read a fourth-round run of tools/run_merge_native.sh (the probe records the
undo stack around every dispatch and key press) and say, for every press,
whether the document changed and whether the undo stack changed.

The question (finding 109's option B, 2026-10-06): can "the undo stack
changed" serve as the completion proof for a real key -- does it change
exactly when the document does?  A press where the two disagree is the
answer "no" for that shape.

"Document changed" is judged two ways, both reported: the block reduction of
tools/analyze_merge_native.py (what a merge or a key is meant to change) and
the raw bytes of content.xml (anything at all).  "Stack changed" = the
.uno:UndoCount payload or the .uno:Undo actions payload differs from the one
before the press.

The "b" arm is option B's whole sequence (select one unit as the barrier
does, Shift + the opposite arrow back, the user's own key).  For it the reader
also says whether the selection came back collapsed at the placed caret, and
whether its document equals the key arm's first press -- B must be Writer's key.

Usage: analyze_merge_undo.py ROUND_DIR [--json OUT]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "analyze_merge_native", Path(__file__).with_name("analyze_merge_native.py"))
_native = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_native)


def raw(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        return archive.read("content.xml")


def stack(undo: dict | None) -> tuple:
    undo = undo or {}
    return (undo.get("count"), undo.get("actions"))


def top(undo: dict | None) -> dict:
    try:
        actions = json.loads((undo or {}).get("actions") or "{}").get("actions") or []
    except json.JSONDecodeError:
        return {"unparsed": (undo or {}).get("actions")}
    return actions[0] if actions else {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("round_dir", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    docs = args.round_dir / "docs"
    arms = [json.loads(line) for line in (args.round_dir / "arms.jsonl").read_text().splitlines()
            if line.startswith("{") and '"case"' in line]
    if not arms:
        print("no arms", file=sys.stderr)
        return 1
    original = docs / "original.odt"
    out, disagreements, presses_seen = {}, 0, 0
    for arm in arms:
        if arm.get("fatal") or "undoBefore" not in arm:
            continue
        stem = docs / f"r{arm['round']}-{arm['case']}"
        steps = []
        if arm["arm"] == "select":
            if not arm.get("dispatched"):
                continue
            seq = [(1, stem.parent / f"{stem.name}-select.odt", arm.get("undoAfter"))]
        elif arm["arm"] == "b":
            seq = [(1, stem.parent / f"{stem.name}-b.odt", arm.get("undoAfter"))]
        else:
            seq = [(1, stem.parent / f"{stem.name}-key.odt", arm.get("undoAfter"))]
            seq += [(e["press"], stem.parent / f"{stem.name}-key{e['press']}.odt", e.get("undo"))
                    for e in arm.get("laterPresses") or []]
        prev_doc, prev_raw, prev_stack = _native.document(original), raw(original), stack(arm["undoBefore"])
        for press, path, undo in seq:
            doc, content = _native.document(path), raw(path)
            changed = doc != prev_doc
            raw_changed = content != prev_raw
            stack_changed = stack(undo) != prev_stack
            presses_seen += 1
            agree = stack_changed == raw_changed
            disagreements += not agree
            steps.append({"press": press, "documentChanged": changed, "contentXmlChanged": raw_changed,
                          "stackChanged": stack_changed, "agree": agree,
                          "count": (undo or {}).get("count"), "top": top(undo)})
            prev_doc, prev_raw, prev_stack = doc, content, stack(undo)
        if arm["arm"] == "b":
            restored = arm.get("restored") or {}
            placed = arm.get("placed") or {}
            key_doc = stem.parent / f"{stem.name}-key.odt"
            steps[0]["restoredCollapsed"] = restored.get("type") == 0
            steps[0]["restoredAtPlacedCaret"] = bool(placed.get("cursor")) and restored.get("cursor") == placed.get("cursor")
            steps[0]["equalsKey"] = key_doc.exists() and raw(stem.parent / f"{stem.name}-b.odt") == raw(key_doc)
            steps[0]["equalsKeyBlocks"] = key_doc.exists() and _native.document(
                stem.parent / f"{stem.name}-b.odt") == _native.document(key_doc)
            steps[0]["unit"] = (arm.get("unit") or {}).get("codePoints")
        key = f"{arm['case']} {arm['arm']}"
        out.setdefault(key, {"boundary": arm["boundary"], "result": (arm.get("result") or "")[:90],
                             "rounds": {}})["rounds"][arm["round"]] = steps

    for key in sorted(out):
        entry = out[key]
        print(f"{key:<12} {entry['boundary']}")
        for rnd, steps in sorted(entry["rounds"].items()):
            cells = []
            for s in steps:
                mark = "" if s["agree"] else "  <-- DISAGREE"
                if "equalsKey" in s:
                    mark += (f"  restore={'ok' if s['restoredCollapsed'] and s['restoredAtPlacedCaret'] else 'FAILED'}"
                             f" =key={'Y' if s['equalsKeyBlocks'] else 'NO'}"
                             f"{'' if s['equalsKey'] == s['equalsKeyBlocks'] else '(bytes ' + ('Y' if s['equalsKey'] else 'n') + ')'}")
                cells.append(f"p{s['press']}: doc={'Y' if s['contentXmlChanged'] else 'n'}"
                             f"{'' if s['documentChanged'] == s['contentXmlChanged'] else '(blocks ' + ('Y' if s['documentChanged'] else 'n') + ')'}"
                             f" stack={'Y' if s['stackChanged'] else 'n'}"
                             f" [{s['top'].get('comment', '')!s}]{mark}")
            print(f"    r{rnd} " + " | ".join(cells))
    print(f"\npresses: {presses_seen}, stack-vs-content.xml disagreements: {disagreements}")
    if args.json:
        args.json.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
