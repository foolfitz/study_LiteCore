#!/usr/bin/env python3
"""R0c (SPEC-M3-paragraph-merge 16.3): the E shape, native.

Reads rounds run with MERGE_ESHAPE=1 (the b arm is K1, .uno:Escape, K2,
.uno:Escape, key) and, per case and round, applies the engine's rules of 16.2
to say where v15 would stop, and checks the premises 16.3 makes kill
conditions:

  Escape #1: selection empty, no START/END, .uno:Undo payload unchanged, the
             caret did not move (same x as K1's caret, inside its line);
  K2:        point side (START after Shift+Left, END after Shift+Right)
             satisfies the 14.2 mapping against the origin caret whenever the
             selected text equals K1's byte for byte;
  Escape #2: selection empty, payload unchanged, a caret delivered after it
             equals the origin caret;
  the key:   where v15 would press it, content.xml equals the key arm's
             (paragraph text when the case typed first), and the follow text
             lands as after the key arm.

Decisions: nothing-selected, barrier (no separator: today's barrier, not the
E shape), refused-k1-anchor, refused-k1-fence, refused-k2-text,
refused-k2-anchor, merge, typed-merge, key-noop.  A decision differing between
rounds of one case is a STOP; so is a missing arm.  Exit 1 on any KILL or
STOP, or when merge, nothing-selected or a refusal never occurs.

Usage: check_merge_eshape.py [--json OUT] ROUND_DIR [ROUND_DIR ...]
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odt_paragraphs import first_difference, paragraph_texts  # noqa: E402

SEPARATORS = {10, 13, 0x2028, 0x2029}


def rect(payload: str | None) -> tuple[int, ...] | None:
    if not payload or payload == "EMPTY":
        return None
    try:
        values = tuple(int(v.strip()) for v in payload.split(";", 1)[0].split(","))
    except ValueError:
        return None
    return values if len(values) == 4 else None


def fence(caret: tuple[int, ...] | None, anchor: tuple[int, ...] | None) -> bool:
    return (caret is not None and anchor is not None and anchor[0] == caret[0]
            and anchor[1] <= caret[1] and caret[1] + caret[3] <= anchor[1] + anchor[3] + 1)


def content(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        return archive.read("content.xml")


def empty_selection(readback: dict) -> bool:
    return readback.get("type") == 0 and readback.get("rectangleCount") == 0


def judge(b: dict, key: dict, stem: Path, original: bytes, kills: list[str], where: str) -> str:
    if b.get("eshape") is not True or "restorePresses" in b:
        kills.append(f"{where}: b arm is not an E-shape arm")
        return "invalid"
    typed = bool(b.get("pretype"))
    origin = (b.get("typedAt") if typed else b.get("placed")) or {}
    p = rect(origin.get("cursor"))
    unit = b.get("unit") or {}
    if unit.get("type") == 0:
        if "esc1" in b or "k2" in b:
            kills.append(f"{where}: nothing selected but the shape went on")
        return "nothing-selected"
    if not any(cp in SEPARATORS for cp in unit.get("codePoints") or []):
        return "barrier"
    backward = bool(b.get("backward"))
    k1_anchor = rect(unit.get("selectionEnd" if backward else "selectionStart"))
    decision = None
    if k1_anchor is None:
        decision = "refused-k1-anchor"
    elif not fence(p, k1_anchor):
        decision = "refused-k1-fence"
    if decision is not None:
        return decision  # v15 sends nothing after K1 here; later steps are not its premises

    # Escape #1 -- sent by v15 only when K1 passed.
    esc1 = b.get("esc1") or {}
    unit_caret = rect(unit.get("cursor"))
    esc1_caret = rect(esc1.get("cursor"))
    if not empty_selection(esc1):
        kills.append(f"{where}: Escape #1 left a selection {esc1.get('rectangles')!r}")
    if esc1.get("selectionStart") or esc1.get("selectionEnd"):
        kills.append(f"{where}: Escape #1's flush sent START/END")
    if b.get("esc1Undo") != b.get("undoStart"):
        kills.append(f"{where}: Escape #1 changed the undo payload")
    if not (unit_caret and esc1_caret and esc1_caret[0] == unit_caret[0]
            and unit_caret[1] <= esc1_caret[1]
            and esc1_caret[1] + esc1_caret[3] <= unit_caret[1] + unit_caret[3]):
        kills.append(f"{where}: Escape #1 moved the caret {unit_caret} -> {esc1_caret}")

    k2 = b.get("k2") or {}
    if k2.get("text") != unit.get("text"):
        decision = "refused-k2-text"
    else:
        point = rect(k2.get("selectionStart" if not backward else "selectionEnd"))
        if point is None:
            decision = "refused-k2-anchor"
        elif not fence(p, point):
            kills.append(f"{where}: K2 selected K1's text but its point side {point} "
                         f"fails the fence against {p}")
            decision = "refused-k2-fence"

    if decision is not None:
        return decision  # refused at K2: v15 sends no Escape #2 and no key

    # Escape #2 -- sent by v15 only when K2 passed.
    esc2 = b.get("esc2") or {}
    if not empty_selection(esc2):
        kills.append(f"{where}: Escape #2 left a selection {esc2.get('rectangles')!r}")
    if b.get("esc2Undo") != b.get("undoStart"):
        kills.append(f"{where}: Escape #2 changed the undo payload")
    if esc2.get("cursor") != k2.get("cursor") and esc2.get("cursor") != origin.get("cursor"):
        kills.append(f"{where}: Escape #2 delivered a caret {esc2.get('cursor')!r} "
                     f"that is not the origin {origin.get('cursor')!r}")

    if b.get("saved") is not True or key.get("saved") is not True:
        kills.append(f"{where}: unsaved arm")
        return "invalid"
    b_doc, key_doc = Path(f"{stem}-b.odt"), Path(f"{stem}-key.odt")
    if typed:
        difference = first_difference(paragraph_texts(str(b_doc)), paragraph_texts(str(key_doc)))
        if difference:
            kills.append(f"{where}: typed case, E-shape document differs from the key arm: {difference}")
        decision = "typed-merge"
    else:
        key_content = content(key_doc)
        if key_content == original:
            decision = "key-noop"
            if content(b_doc) != original:
                kills.append(f"{where}: the key changed nothing but the E shape did")
        else:
            decision = "merge"
            if content(b_doc) != key_content:
                kills.append(f"{where}: E-shape content.xml != key arm")
    if b.get("followSaved") is True and key.get("followSaved") is True:
        difference = first_difference(paragraph_texts(f"{stem}-b-follow.odt"),
                                      paragraph_texts(f"{stem}-key-follow.odt"))
        if difference:
            kills.append(f"{where}: text typed after the key landed elsewhere: {difference}")
    return decision


def main(argv: list[str]) -> int:
    out = None
    if argv[:1] == ["--json"]:
        out, argv = Path(argv[1]), argv[2:]
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    kills: list[str] = []
    stops: list[str] = []
    decisions: dict[str, dict[str, str]] = {}
    for round_dir in map(Path, argv):
        lines = (round_dir / "arms.jsonl").read_text(encoding="utf-8").splitlines()
        arms: dict[tuple[str, int, str], dict] = {}
        for line in lines[1:]:
            arm = json.loads(line)
            arms[(arm["case"], arm["round"], arm["arm"])] = arm
        docs = round_dir / "docs"
        original = content(docs / "original.odt") if (docs / "original.odt").exists() else b""
        for (case, rnd, name), arm in sorted(arms.items()):
            if name != "b":
                continue
            where = f"{round_dir.name} {case} r{rnd}"
            key = arms.get((case, rnd, "key"))
            if key is None or "fatal" in arm or "fatal" in key:
                stops.append(f"{where}: missing or fatal arm")
                continue
            decision = judge(arm, key, docs / f"r{rnd}-{case}", original, kills, where)
            decisions.setdefault(f"{round_dir.name} {case}", {})[str(rnd)] = decision
    summary: dict[str, int] = {}
    per_case: dict[str, str] = {}
    for case, by_round in sorted(decisions.items()):
        values = set(by_round.values())
        if len(values) != 1:
            stops.append(f"{case}: decision differs between rounds {by_round}")
        per_case[case] = "/".join(sorted(values))
        for value in by_round.values():
            summary[value] = summary.get(value, 0) + 1
    if not summary.get("merge") or not summary.get("nothing-selected") or not any(
            k.startswith("refused") for k in summary):
        stops.append(f"vacuous: a decision class never occurred {summary}")
    if out:
        out.write_text(json.dumps({"summary": summary, "cases": per_case, "kills": kills,
                                   "stops": stops}, indent=1, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    print(json.dumps(summary))
    for case, value in per_case.items():
        print(f"  {case}: {value}")
    for kill in kills:
        print("KILL " + kill)
    for stop in stops:
        print("STOP " + stop)
    return 1 if kills or stops else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
