#!/usr/bin/env python3
"""SPEC E2-C phase D3: score the list cells against predictions written first.

The page judges nothing.  This reads the saved documents and applies the eight
predictions registered in
`findings/evidence/sdk-e2/e2-c-validation/d3-lists/PREDICTION.md` before the
harness existed, plus one check no cell may fail: nothing may be lost.

Two rules this file exists to enforce, both learned the expensive way:

  * A cell that did not dispatch does not get a verdict.  The first execution of
    this phase reported `verified-format-readback` for three cells that had
    acted on a heading four paragraphs from their anchor (finding 048), and a
    scorer that reads only completion codes would have called them passes.
    Every cell must show its caret on its own anchor.
  * The prediction is scored as written, not as it turned out.  L2 and L5 are
    recorded as FAILED predictions with acceptable behaviour, because "we would
    have accepted that too" is a thing to decide before the round, not after.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

import xml.etree.ElementTree as ET

NS = {"office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
      "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
      "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0"}
PROJECT = Path(__file__).resolve().parent.parent
# Half the corpus's 390-twip line pitch: the harness's own gate, repeated here
# so the offline scorer does not have to trust the page's boolean.
CARET_TOLERANCE_TWIPS = 195

FIXTURES = {"list-contexts": PROJECT / "test-docs" / "e1" / "list-contexts.odt",
            "list-split": PROJECT / "test-docs" / "e2" / "list-split.odt"}


def qname(element) -> str:
    return element.tag.split("}")[-1]


def list_style_kinds(archive: zipfile.ZipFile) -> dict[str, str]:
    """style name -> "bullet" | "number", from both content.xml and styles.xml.

    A list created by the action gets an automatic style in content.xml; the
    corpus's own lists are defined in styles.xml.  Reading only one of the two
    would leave half the lists unclassifiable, and "unclassifiable" is exactly
    what a bullet list masquerading as a numbered one would look like.
    """
    kinds: dict[str, str] = {}
    for name in ("content.xml", "styles.xml"):
        try:
            blob = archive.read(name).decode("utf-8")
        except KeyError:
            continue
        for match in re.finditer(
                r'<text:list-style[^>]*style:name="([^"]+)"(.*?)</text:list-style>',
                blob, re.S):
            levels = set(re.findall(r"<text:list-level-style-(\w+)", match.group(2)))
            if "bullet" in levels:
                kinds[match.group(1)] = "bullet"
            elif "number" in levels:
                kinds[match.group(1)] = "number"
    return kinds


def outline(path: Path) -> list[dict]:
    """The body as a flat list of blocks, with list membership made explicit."""
    with zipfile.ZipFile(path) as archive:
        kinds = list_style_kinds(archive)
        root = ET.fromstring(archive.read("content.xml"))
    body = root.find("office:body/office:text", NS)
    blocks: list[dict] = []
    for child in (body if body is not None else []):
        tag = qname(child)
        if tag in ("p", "h"):
            blocks.append({"kind": tag, "text": "".join(child.itertext()).strip()})
        elif tag == "list":
            style = child.get(f"{{{NS['style']}}}name") \
                or child.get(f"{{{NS['text']}}}style-name")
            items = ["".join(item.itertext()).strip()
                     for item in child if qname(item) == "list-item"]
            blocks.append({
                "kind": "list", "style": style, "listKind": kinds.get(style),
                "items": items,
                "continueNumbering":
                    child.get(f"{{{NS['text']}}}continue-numbering") == "true",
            })
    return blocks


def texts(blocks: list[dict]) -> list[str]:
    """Every non-empty run of text, in order, regardless of structure."""
    out: list[str] = []
    for block in blocks:
        if block["kind"] == "list":
            out.extend(t for t in block["items"] if t)
        elif block["text"]:
            out.append(block["text"])
    return out


def find_list_holding(blocks: list[dict], text: str) -> dict | None:
    for block in blocks:
        if block["kind"] == "list" and text in block["items"]:
            return block
    return None


def is_plain(blocks: list[dict], text: str) -> bool:
    return any(block["kind"] in ("p", "h") and block["text"] == text
               for block in blocks)


def count_lists(blocks: list[dict]) -> int:
    return sum(1 for block in blocks if block["kind"] == "list")


# The eight predictions, as predicates over the after-picture.  Each returns
# (held, observation).  `before` is the fixture on disk -- byte for byte what
# the document looked like, which is why this phase takes no before-save.
def p_l1(before, after):
    holder = find_list_holding(after, "E1-LC-ISOLATED 前後都不是清單的段落")
    held = bool(holder) and holder["listKind"] == "bullet" \
        and len(holder["items"]) == 1 \
        and is_plain(after, "E1-LC-HEADING") and is_plain(after, "E1-LC-SPACER")
    return held, ("a new one-item bullet list, neighbours untouched" if held
                  else f"holder={holder}")


def p_l2(before, after):
    holder = find_list_holding(after, "E1-LC-END")
    if not holder:
        return False, "E1-LC-END is not in a list"
    new_list = len(holder["items"]) == 1
    return (holder["listKind"] == "number" and new_list,
            f"numbered={holder['listKind'] == 'number'}, "
            f"items={holder['items']} -- predicted a NEW list, "
            f"{'got one' if new_list else 'it merged with the numbered list above'}")


def p_l3(before, after):
    left = is_plain(after, "E1-LC-BULLET-TWO 中文項目")
    holder = find_list_holding(after, "E1-LC-BULLET-ONE")
    stayed = bool(holder) and holder["listKind"] == "bullet" \
        and holder["items"] == ["E1-LC-BULLET-ONE"]
    return left and stayed, f"left={left}, one-stayed-bullet={stayed}"


def p_l4(before, after):
    left = is_plain(after, "E1-LC-NUMBER-TWO")
    holder = find_list_holding(after, "E1-LC-NUMBER-ONE")
    stayed = bool(holder) and holder["listKind"] == "number" \
        and holder["items"] == ["E1-LC-NUMBER-ONE"]
    return left and stayed, f"left={left}, one-stayed-numbered={stayed}"


def p_l5(before, after):
    holder = find_list_holding(after, "E1-LC-BULLET-ONE")
    converted = bool(holder) and holder["listKind"] == "number"
    no_third = count_lists(after) == count_lists(before)
    return (converted and no_third,
            f"converted={converted}, lists {count_lists(before)}->"
            f"{count_lists(after)} -- predicted no third list")


def p_l6(before, after, control=None):
    if control is None:
        return None, "no no-action control in this run; idempotence unmeasurable"
    return after == control, ("body identical to a no-action save" if after == control
                              else "the repeat dispatch changed the document")


def p_l7(before, after):
    one = find_list_holding(after, "E2-LS-ONE")
    three = find_list_holding(after, "E2-LS-THREE")
    split = bool(one) and bool(three) and one is not three
    mid_plain = is_plain(after, "E2-LS-MID 中間那一項")
    kept = sorted(texts(before)) == sorted(texts(after))
    return (split and mid_plain and kept,
            f"split={split}, mid-plain={mid_plain}, nothing-lost={kept}, "
            f"continue-numbering={three['continueNumbering'] if three else None}")


def p_l8(before, after):
    holder = find_list_holding(after, "E1-LC-BETWEEN")
    merged = bool(holder) and holder["listKind"] == "bullet" \
        and holder["items"] == ["E1-LC-BULLET-ONE", "E1-LC-BULLET-TWO 中文項目",
                                "E1-LC-BETWEEN"]
    numbered = find_list_holding(after, "E1-LC-NUMBER-ONE")
    separate = bool(numbered) and numbered is not holder \
        and numbered["items"] == ["E1-LC-NUMBER-ONE", "E1-LC-NUMBER-TWO"]
    return merged and separate, f"merged-with-bullets={merged}, numbered-separate={separate}"


PREDICTIONS = {
    "L1": ("list-contexts", p_l1),
    "L2": ("list-contexts", p_l2),
    "L3": ("list-contexts", p_l3),
    "L4": ("list-contexts", p_l4),
    "L5": ("list-contexts", p_l5),
    "L6": ("list-contexts", p_l6),
    "L7": ("list-split", p_l7),
    "L8": ("list-contexts", p_l8),
}


def body_bytes(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        blob = archive.read("content.xml")
    return blob[blob.index(b"<office:body"):]


def score(evidence: Path) -> dict:
    metrics = json.loads((evidence / "result.json").read_text(encoding="utf-8"))
    metrics = metrics.get("metrics", metrics)
    cells = metrics.get("cells") or {}
    saved = evidence / "saved"
    control = saved / "L6C-after.odt"
    results: dict[str, dict] = {}
    problems: list[str] = []

    for name, (fixture, predicate) in PREDICTIONS.items():
        record = cells.get(name)
        entry: dict = {"cell": name}
        if not record:
            entry.update(dispatched=False, predictionHeld=None,
                         observation="cell not in this run")
            results[name] = entry
            continue

        # Did it act where it said it did?  Recomputed from the recorded caret
        # rather than trusting the page's own boolean.
        caret = record.get("caretAfter") or {}
        asked = record.get("y")
        placed = (caret.get("y") is not None and asked is not None
                  and abs(asked - caret["y"]) <= CARET_TOLERANCE_TWIPS)
        entry["caretAtAnchor"] = placed
        entry["completion"] = (record.get("result") or {}).get("completion") \
            or (record.get("error") or {}).get("code")
        after = saved / f"{name}-after.odt"
        if not placed or not after.is_file():
            if caret.get("y") is None:
                why = ("this run recorded no caret, so where it acted is "
                       "unknown -- runs before the gate existed look like this")
            elif not placed:
                why = (f"the caret was not on this cell's anchor: asked "
                       f"{asked}, caret at {caret['y']}")
            else:
                why = "no saved document"
            entry.update(dispatched=False, predictionHeld=None, observation=why)
            problems.append(f"{name}: no verdict -- {entry['observation']}")
            results[name] = entry
            continue

        before_blocks = outline(FIXTURES[fixture])
        after_blocks = outline(after)
        if name == "L6":
            held, observation = predicate(
                body_bytes(FIXTURES[fixture]), body_bytes(after),
                body_bytes(control) if control.is_file() else None)
        else:
            held, observation = predicate(before_blocks, after_blocks)
        entry.update(dispatched=True, predictionHeld=held, observation=observation)

        # The stop condition, applied to every cell regardless of its own
        # prediction: SPEC E2-000 section 10 stops E2 if a list switch loses
        # structure silently.  Text going missing is the visible half of that.
        lost = sorted(set(texts(before_blocks)) - set(texts(after_blocks)))
        entry["textLost"] = lost
        if lost:
            problems.append(f"{name}: text lost: {lost}")
        results[name] = entry

    held = [k for k, v in results.items() if v.get("predictionHeld") is True]
    failed = [k for k, v in results.items() if v.get("predictionHeld") is False]
    unscored = [k for k, v in results.items() if v.get("predictionHeld") is None]
    return {
        "phase": "D3",
        "browser": metrics.get("browserName"),
        "artifact": (metrics.get("artifact") or {}).get("wasmSha256"),
        "cells": results,
        "predictionsHeld": held,
        "predictionsFailed": failed,
        "unscored": unscored,
        "problems": problems,
    }


def self_test() -> int:
    """Every predicate must be able to say no, and the caret gate must bite."""
    failures: list[str] = []

    def check(label, condition):
        if not condition:
            failures.append(label)

    bullet = {"kind": "list", "style": "B", "listKind": "bullet",
              "items": ["E1-LC-BULLET-ONE", "E1-LC-BULLET-TWO 中文項目"],
              "continueNumbering": False}
    number = {"kind": "list", "style": "N", "listKind": "number",
              "items": ["E1-LC-NUMBER-ONE", "E1-LC-NUMBER-TWO"],
              "continueNumbering": False}
    before = [{"kind": "h", "text": "E1-LC-HEADING"},
              {"kind": "p", "text": "E1-LC-ISOLATED 前後都不是清單的段落"},
              {"kind": "p", "text": "E1-LC-SPACER"}, bullet,
              {"kind": "p", "text": "E1-LC-BETWEEN"}, number,
              {"kind": "p", "text": "E1-LC-END"}]

    # L1 holds on the shape it predicted and fails when the new list is numbered.
    good = [before[0], {"kind": "list", "style": "L1", "listKind": "bullet",
                        "items": ["E1-LC-ISOLATED 前後都不是清單的段落"],
                        "continueNumbering": False}] + before[2:]
    check("L1 accepts its own shape", p_l1(before, good)[0])
    wrong = [dict(block, listKind="number") if block.get("style") == "L1" else block
             for block in good]
    check("L1 rejects a numbered list", not p_l1(before, wrong)[0])

    # L5's "no third list" clause must be what decides it: a converted paragraph
    # is not enough on its own.
    third = [before[0], before[1], before[2],
             {"kind": "list", "style": "L1", "listKind": "number",
              "items": ["E1-LC-BULLET-ONE"], "continueNumbering": False},
             {"kind": "list", "style": "B", "listKind": "bullet",
              "items": ["E1-LC-BULLET-TWO 中文項目"], "continueNumbering": False},
             before[4], before[5], before[6]]
    held, observation = p_l5(before, third)
    check("L5 fails when a third list appears", not held)
    check("L5 says why", "3" in observation)

    # L7's stop condition: losing an item must fail even if the split happened.
    split_ok = [{"kind": "p", "text": "E2-LS-BEFORE"},
                {"kind": "list", "style": "N", "listKind": "number",
                 "items": ["E2-LS-ONE"], "continueNumbering": False},
                {"kind": "p", "text": "E2-LS-MID 中間那一項"},
                {"kind": "list", "style": "N", "listKind": "number",
                 "items": ["E2-LS-THREE"], "continueNumbering": True}]
    origin = [{"kind": "p", "text": "E2-LS-BEFORE"},
              {"kind": "list", "style": "N", "listKind": "number",
               "items": ["E2-LS-ONE", "E2-LS-MID 中間那一項", "E2-LS-THREE"],
               "continueNumbering": False}]
    check("L7 accepts a clean split", p_l7(origin, split_ok)[0])
    lost = [block for block in split_ok if block.get("items") != ["E2-LS-THREE"]]
    check("L7 fails when an item vanishes", not p_l7(origin, lost)[0])

    # L6 without a control must be unscored, not a pass.
    held, _ = p_l6(b"x", b"x", None)
    check("L6 is unscored without a control", held is None)
    check("L6 fails when the body moved", p_l6(b"x", b"y", b"x")[0] is False)

    # L8's two halves are separate claims.
    merged = [before[0], before[1], before[2],
              {"kind": "list", "style": "B", "listKind": "bullet",
               "items": ["E1-LC-BULLET-ONE", "E1-LC-BULLET-TWO 中文項目",
                         "E1-LC-BETWEEN"], "continueNumbering": False},
              number, before[6]]
    check("L8 accepts the merge", p_l8(before, merged)[0])
    swallowed = [before[0], before[1], before[2],
                 {"kind": "list", "style": "B", "listKind": "bullet",
                  "items": ["E1-LC-BULLET-ONE", "E1-LC-BULLET-TWO 中文項目",
                            "E1-LC-BETWEEN", "E1-LC-NUMBER-ONE",
                            "E1-LC-NUMBER-TWO"], "continueNumbering": False},
                 before[6]]
    check("L8 fails when the numbered list is swallowed", not p_l8(before, swallowed)[0])

    # And the caret gate: a cell whose caret is a line away gets no verdict.
    check("the gate rejects a caret one line off",
          abs(1950 - 1418) > CARET_TOLERANCE_TWIPS)
    check("the gate accepts the measured landings",
          abs(3120 - 3238) <= CARET_TOLERANCE_TWIPS)

    print(json.dumps({"selfTest": "d3", "checks": 13,
                      "failures": failures}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.evidence:
        parser.error("an evidence directory is required")
    report = score(args.evidence)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["problems"] else 1


if __name__ == "__main__":
    sys.exit(main())
