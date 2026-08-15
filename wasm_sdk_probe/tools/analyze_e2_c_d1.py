#!/usr/bin/env python3
"""Judge SPEC E2-C phase D1 against the frozen matrix.

Two halves, and both are needed.

The TYPED half is what the engine said: completion, `changed`, revision delta,
per action class.  That half alone is not enough -- all four inline formats
return `uno-command-result`, so a mapping that sent bold to italic would report
the action it was asked for.

The DOCUMENT half is what the saved ODT says at that action's own anchor.  For
the inline formats it is judged through a marker committed after the dispatch,
because the D1 pre-flight measured that a format at a collapsed caret leaves
`<office:body>` byte-identical: the effect lands on what is typed next.

Reads saved files only.  `--self-test` mutates a passing result and requires
every predicate to go red.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
MATRIX = PROJECT / "e2" / "validation-matrix-v1.json"

BODY_OPEN, BODY_CLOSE = b"<office:body>", b"</office:body>"

MOVE = {"move-character-left", "move-character-right"}
DELETE = {"delete-backward", "delete-forward"}
FORMAT = {"set-bold", "set-italic", "set-underline", "set-strikethrough"}
PARAGRAPH = {"set-list-none", "set-list-unordered", "set-list-ordered",
             "set-paragraph-heading", "set-paragraph-body"}

PROPERTY = {
    "set-bold": r'fo:font-weight="bold"',
    "set-italic": r'fo:font-style="italic"',
    "set-underline": r"style:text-underline-style",
    "set-strikethrough": r"style:text-line-through-style",
}


# ---------------------------------------------------------------- ODT reading

def content_of(odt: Path) -> str | None:
    if not odt.is_file():
        return None
    with zipfile.ZipFile(odt) as archive:
        return archive.read("content.xml").decode("utf-8")


def body_of(odt: Path) -> bytes | None:
    if not odt.is_file():
        return None
    with zipfile.ZipFile(odt) as archive:
        content = archive.read("content.xml")
    start, end = content.find(BODY_OPEN), content.find(BODY_CLOSE)
    return content[start:end + len(BODY_CLOSE)] if start >= 0 and end >= 0 else None


def blocks(content: str) -> list[tuple[str, str]]:
    """(tag, xml) for every top-level paragraph or heading, in document order."""
    return [(match.group(1), match.group(0)) for match in
            re.finditer(r"<text:(p|h)\b[^>]*>.*?</text:\1>", content, re.S)]


def text_of(xml: str) -> str:
    return re.sub(r"<[^>]+>", "", xml)


def block_with(content: str, anchor: str) -> tuple[str, str] | None:
    for tag, xml in blocks(content):
        if anchor in text_of(xml):
            return tag, xml
    return None


def in_list(content: str, anchor: str) -> bool:
    for match in re.finditer(r"<text:list\b.*?</text:list>", content, re.S):
        if anchor in text_of(match.group(0)):
            return True
    return False


def style_of_span(content: str, marker: str) -> str | None:
    """The text-properties of the span holding `marker`, if it is in one."""
    found = block_with(content, marker)
    if not found:
        return None
    span = re.search(r'<text:span text:style-name="([^"]+)">[^<]*'
                     + re.escape(marker), found[1])
    if not span:
        return ""            # present, but in no span at all
    style = re.search(r'<style:style style:name="%s"[^>]*>(.*?)</style:style>'
                      % re.escape(span.group(1)), content, re.S)
    return style.group(1) if style else ""


def paragraph_style(content: str, anchor: str) -> str | None:
    found = block_with(content, anchor)
    if not found:
        return None
    name = re.search(r'text:style-name="([^"]+)"', found[1])
    return name.group(1) if name else ""


# ------------------------------------------------------------------- oracles

def typed_problems(action: str, result: dict) -> list[str]:
    before, after = result.get("beforeRevision"), result.get("revision")
    completion = str(result.get("completion") or "")
    changed = result.get("changed")
    if action in MOVE:
        if after != before or changed is not False \
                or not completion.startswith("documented-callback-"):
            return [f"{action}: movement postcondition not met"]
    elif action in DELETE:
        if completion != "verified-selection-delete" or changed is not True \
                or after != before + 1:
            return [f"{action}: delete postcondition not met"]
    elif action in PARAGRAPH:
        if completion != "verified-format-readback" or changed is not None \
                or after != before + 1:
            return [f"{action}: route C postcondition not met"]
    else:
        if completion != "uno-command-result" or changed is not True \
                or after != before + 1:
            return [f"{action}: mutation postcondition not met"]
    return []


def document_problems(cell: dict, saved: Path, opened: str | None) -> list[str]:
    """What the saved ODT must show for this cell, at this cell's own anchor."""
    cid = cell["cell"]
    label = f"{cid}-round{cell['round']}"
    after = content_of(saved / f"{label}.odt")
    # The cell's OWN before-picture, not the document as it was opened: by the
    # time a cell runs, twenty other cells have edited the file, and judging
    # against the opened state charges this cell with all of them.
    before = content_of(saved / f"{label}-before-action.odt") or opened
    anchor = cell.get("anchor")
    out: list[str] = []

    if cid in ("d1-place-caret", "d1-move-character-left",
               "d1-move-character-right"):
        # A caret, and a caret that moved, leave no trace in the file.  Their
        # whole postcondition is the typed one, which is checked above.
        return out

    if after is None:
        return [f"{cid}: no saved document"]

    if cid == "d1-insert-text":
        marker = (cell.get("result") or {}).get("marker") or "D1INSERT"
        if after.count(marker) != 1:
            out.append(f"{cid}: marker appears {after.count(marker)} times, want 1")
        return out

    if cid.startswith("d1-set-"):
        action = cell["action"]
        marker = (cell.get("result") or {}).get("marker")
        wants = cid.endswith("-true")
        # Half one: the dispatch itself does not move the document.
        before_body = body_of(saved / f"{label}-before-action.odt")
        after_body = body_of(saved / f"{label}-after-action.odt")
        if before_body is None or after_body is None:
            out.append(f"{cid}: the before/after-action saves are missing")
        elif before_body != after_body:
            out.append(f"{cid}: the collapsed-caret dispatch changed <office:body>")
        # Half two: the marker typed afterwards carries (or lacks) the property.
        style = style_of_span(after, marker) if marker else None
        if style is None:
            out.append(f"{cid}: the marker {marker} is not in the document")
        else:
            carries = bool(re.search(PROPERTY[action], style))
            if carries != wants:
                out.append(f"{cid}: marker carries {PROPERTY[action]}={carries}, "
                           f"want {wants}")
        return out

    if cid in ("d1-list-unordered-collapsed", "d1-list-ordered-collapsed"):
        if not in_list(after, anchor):
            out.append(f"{cid}: {anchor} is not inside a list")
        return out

    if cid == "d1-list-none-collapsed":
        if in_list(after, anchor):
            out.append(f"{cid}: {anchor} is still inside a list")
        return out

    if cid in ("d1-heading-collapsed", "d1-heading-range-single"):
        style = paragraph_style(after, anchor)
        if style is None or "Heading" not in style:
            out.append(f"{cid}: {anchor} does not carry a heading style "
                       f"(style is {style!r})")
        return out

    if cid == "d1-heading-range-cross":
        for name in (anchor, "E2-D1-RANGE-TWO"):
            style = paragraph_style(after, name)
            if style is None or "Heading" not in style:
                out.append(f"{cid}: {name} does not carry a heading style "
                           f"(style is {style!r})")
        return out

    if cid == "d1-body-collapsed":
        found = block_with(after, anchor)
        if found is None:
            out.append(f"{cid}: {anchor} is gone")
        else:
            style = paragraph_style(after, anchor) or ""
            if found[0] == "h" or "Heading" in style:
                out.append(f"{cid}: {anchor} is still a heading")
        return out

    if cid == "d1-ordered-range-cross-both-already-numbered":
        for name in ("E2-D1-NUM-ONE", "E2-D1-NUM-TWO"):
            if not in_list(after, name):
                out.append(f"{cid}: {name} left the list")
        return out

    # The edit targets are identified by their TAIL token, not by the anchor the
    # caret was placed at: the caret lands near the start of the line, so the
    # edit damages the leading anchor.  Looking for the damaged anchor is how
    # the first version of this analyzer reported "the paragraph is gone" about
    # a paragraph that was right there, one character shorter.
    TAIL = {"d1-delete-backward": "ZZDELB", "d1-delete-forward": "ZZDELF",
            "d1-insert-paragraph-break": "ZZBRKP",
            "d1-insert-line-break": "ZZBRKL"}

    if cid in ("d1-delete-backward", "d1-delete-forward"):
        tail = TAIL[cid]
        found, original = block_with(after, tail), block_with(before or "", tail)
        if found is None:
            out.append(f"{cid}: no paragraph carries {tail} any more")
        elif original is None:
            out.append(f"{cid}: {tail} is not in this cell's before-picture")
        else:
            was, now = text_of(original[1]), text_of(found[1])
            if len(now) != len(was) - 1:
                out.append(f"{cid}: paragraph went from {len(was)} to {len(now)} "
                           f"characters, want exactly one fewer")
            elif not is_one_deletion(was, now):
                out.append(f"{cid}: the text is not the original minus one character")
        return out

    if cid == "d1-insert-paragraph-break":
        tail = TAIL[cid]
        after_blocks, opened_blocks = blocks(after), blocks(before or "")
        if block_with(after, tail) is None:
            out.append(f"{cid}: no paragraph carries {tail} any more")
        elif len(after_blocks) <= len(opened_blocks):
            out.append(f"{cid}: block count did not grow "
                       f"({len(opened_blocks)} -> {len(after_blocks)})")
        else:
            # Text is conserved by a break: the same characters, one more block.
            was = "".join(text_of(xml) for _, xml in opened_blocks)
            now = "".join(text_of(xml) for _, xml in after_blocks)
            if now != was:
                out.append(f"{cid}: the split changed the document text")
        return out

    if cid == "d1-insert-line-break":
        tail = TAIL[cid]
        found = block_with(after, tail)
        if found is None:
            out.append(f"{cid}: no paragraph carries {tail} any more")
        elif "<text:line-break/>" not in found[1]:
            out.append(f"{cid}: no <text:line-break/> in the paragraph")
        return out

    if cid == "d1-interleave-v1-after-v2":
        return out            # judged entirely on the typed steps, below

    if cid in ("d1-characterisation-range-inherited", "d1-undo", "d1-save"):
        return out

    return [f"{cid}: no document oracle is defined for this cell"]


def is_one_deletion(was: str, now: str) -> bool:
    for index in range(len(was)):
        if was[:index] + was[index + 1:] == now:
            return True
    return False


def judge_round(entry: dict, saved: Path, matrix: dict) -> dict:
    by_id = {cell["id"]: cell for cell in matrix["cells"]}
    opened = content_of(saved / f"round{entry['round']}-opened.odt")
    problems: list[str] = []
    per_cell: dict[str, dict] = {}
    for cell in entry["cells"]:
        cid = cell["cell"]
        spec = by_id.get(cid)
        found: list[str] = []
        if spec is None:
            found.append(f"{cid}: not a cell the frozen matrix declares")
        if cell.get("error"):
            found.append(f"{cid}: {cell['error'].get('code')}")
        elif cell.get("action") and cell.get("result"):
            found += typed_problems(cell["action"], cell["result"])

        if cid == "d1-interleave-v1-after-v2" and not cell.get("error"):
            for step in cell.get("steps", []):
                found += typed_problems(step["action"], {
                    "beforeRevision": step["revision"] - (
                        0 if step["action"] in MOVE else 1),
                    "revision": step["revision"],
                    "changed": step.get("changed"),
                    "completion": step.get("completion")})
        if cid == "d1-undo" and not cell.get("error"):
            result = cell.get("result") or {}
            if result.get("revision") == result.get("beforeRevision"):
                found.append("d1-undo: the revision did not move")
        if not cell.get("error"):
            found += document_problems(cell, saved, opened)

        # A cell the matrix marks NONE cannot fail the round (SPEC E2-C 2.5).
        if spec and spec.get("onFailure") == "NONE":
            per_cell[cid] = {"pass": True, "recorded": found, "disposition": "NONE"}
            continue
        per_cell[cid] = {"pass": not found, "problems": found}
        problems += found
    return {"round": entry["round"], "pass": not problems,
            "problems": problems, "cells": per_cell}


def projection(result: dict, matrix: dict) -> dict:
    include = set(matrix["comparisonProjection"]["include"])
    out: dict[str, dict] = {}
    for entry in result.get("rounds_", []):
        for cell in entry["cells"]:
            spec = next((c for c in matrix["cells"] if c["id"] == cell["cell"]), None)
            if spec and spec.get("onFailure") == "NONE":
                continue        # characterisation may legitimately differ
            item = cell.get("result") or {}
            row = {
                "cell": cell["cell"],
                "action": cell.get("action"),
                "completion": item.get("completion"),
                "changed": item.get("changed"),
                "revisionDelta": (item.get("revision", 0) - item.get("beforeRevision", 0)
                                  if item.get("revision") is not None else None),
                "code": (cell.get("error") or {}).get("code"),
            }
            out[f"{cell['cell']}#{entry['round']}"] = {
                key: value for key, value in row.items() if key in include}
    return out


def judge(result: dict, evidence: Path, matrix: dict) -> dict:
    saved = evidence / "saved"
    problems: list[str] = []
    if not result.get("complete") or result.get("error"):
        problems.append(f"run did not complete: {result.get('error')}")
    if (result.get("attribution") or {}).get("consistent") is not True:
        problems.append("attribution inconsistent")

    expected_rounds = matrix["thresholds"]["d1RoundsPerBrowser"]
    rounds = result.get("rounds_") or []
    if len(rounds) != expected_rounds:
        problems.append(f"{len(rounds)} rounds, the matrix requires "
                        f"{expected_rounds}")

    declared = {cell["id"] for cell in matrix["cells"] if cell["phase"] == "D1"}
    judged = [judge_round(entry, saved, matrix) for entry in rounds]
    for item in judged:
        problems += item["problems"]
        missing = sorted(declared - set(item["cells"]))
        if missing:
            problems.append(f"round {item['round']}: cells never run: {missing}")

    return {"pass": not problems, "problems": problems, "rounds": judged,
            "browser": result.get("browserName"),
            "artifact": result.get("artifact")}


SELF_TEST_MUTATIONS = [
    ("a movement that advanced the revision",
     lambda r: cell_of(r, "d1-move-character-left")["result"].update(
         {"revision": 99})),
    ("a delete with route C's completion",
     lambda r: cell_of(r, "d1-delete-backward")["result"].update(
         {"completion": "verified-format-readback", "changed": None})),
    ("a paragraph action with a v1 completion",
     lambda r: cell_of(r, "d1-heading-collapsed")["result"].update(
         {"completion": "uno-command-result", "changed": True})),
    ("a format marker that never got typed",
     lambda r: cell_of(r, "d1-set-bold-true")["result"].update(
         {"marker": "NOSUCHMARKER"})),
    ("a cell that errored",
     lambda r: cell_of(r, "d1-list-ordered-collapsed").update(
         {"error": {"code": "ANCHOR_NOT_FOUND"}})),
    ("a round removed",
     lambda r: r["rounds_"].pop()),
    ("a cell removed",
     lambda r: r["rounds_"][0]["cells"].remove(cell_of(r, "d1-save"))),
    ("a broken attribution",
     lambda r: r["attribution"].update({"consistent": False})),
    ("an incomplete run",
     lambda r: r.update({"complete": False})),
]


def cell_of(result: dict, cid: str) -> dict:
    for entry in result["rounds_"]:
        for cell in entry["cells"]:
            if cell["cell"] == cid:
                return cell
    raise KeyError(cid)


def self_test(evidence: Path) -> int:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    result = json.loads((evidence / "result.json").read_text(encoding="utf-8"))
    failures = []
    base = judge(result, evidence, matrix)
    # The check is "this mutation changes the verdict", not "this mutation makes
    # it fail".  A self-test that only works on green evidence stops working
    # exactly when the evidence is red -- which is when the analyzer's judgement
    # matters most, and is the state this phase is actually in.
    base_problems = set(base["problems"])
    for label, mutate in SELF_TEST_MUTATIONS:
        mutated = copy.deepcopy(result)
        try:
            mutate(mutated)
        except Exception as error:                          # noqa: BLE001
            failures.append(f"{label}: mutation could not be applied ({error})")
            continue
        after = judge(mutated, evidence, matrix)
        if after["pass"] or set(after["problems"]) == base_problems:
            failures.append(f"{label}: the analyzer's verdict did not change")
    print(json.dumps({"selfTest": len(SELF_TEST_MUTATIONS),
                      "baseVerdict": "pass" if base["pass"] else "fail",
                      "baseProblems": sorted(base_problems),
                      "failures": failures,
                      "pass": not failures}, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--projection", action="store_true",
                        help="print only the cross-browser comparison projection")
    args = parser.parse_args()

    if args.self_test:
        return self_test(args.evidence)

    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    result = json.loads((args.evidence / "result.json").read_text(encoding="utf-8"))
    if args.projection:
        print(json.dumps(projection(result, matrix), indent=2, ensure_ascii=False,
                         sort_keys=True))
        return 0
    verdict = judge(result, args.evidence, matrix)
    print(json.dumps(verdict, indent=2, ensure_ascii=False))
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
