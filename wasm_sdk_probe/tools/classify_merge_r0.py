#!/usr/bin/env python3
"""Classify R0's native reference rounds into the lists the WASM criteria run
(SPEC-M3-paragraph-merge 4.2 as corrected in 10.2).

Every case of every input's case file must be present in every round with all
three arms (select, b, key), without a fatal, with its placement check passed
and its saves written.  Then, per case, from the b arm's unit and the arms'
saved documents:

  nothing-selected   the one-unit selection selected nothing (document ends)
  barrier            the unit holds no paragraph/line separator (10, 13,
                     U+2028, U+2029): today's selection barrier, not B
  restore-refused    a B unit whose restore did not come back to the caret
  key-noop           a B unit, restore back, and Writer's own key changed
                     nothing (the b arm must not have changed anything either)
  merge              a B unit, restore back, the key changed the document, and
                     the b arm's content.xml is byte-identical to the key arm's
  typed-merge        as merge, for a case that types before the key; compared
                     by paragraph text (typed text carries a per-session rsid)

STOP (exit 1) if: an arm is missing, fatal, misplaced or unsaved; a case's
class or restore press count differs between rounds; a B unit came back and
its b arm differs from the key arm (bytes, or paragraph text when typed); with
MERGE_FOLLOW_TEXT, the text typed after the b arm lands elsewhere than after
the key arm; or any class is empty across all inputs.

Usage: classify_merge_r0.py --out R0.json ROUND_DIR CASES_TSV [ROUND_DIR CASES_TSV ...]
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odt_paragraphs import first_difference, paragraph_texts  # noqa: E402

SEPARATORS = {10, 13, 0x2028, 0x2029}
ARMS = ("select", "b", "key")
CLASSES = ("nothing-selected", "barrier", "restore-refused", "key-noop", "merge", "typed-merge")


def content(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        return archive.read("content.xml")


def case_ids(tsv: Path) -> list[str]:
    ids = []
    for line in tsv.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            ids.append(line.split("\t", 1)[0])
    return ids


def top_comment(undo: dict | None) -> str | None:
    if not undo:
        return None
    try:
        actions = json.loads(undo.get("actions", "")).get("actions")
    except (ValueError, AttributeError):
        return None
    if not isinstance(actions, list) or not actions:
        return None
    return actions[0].get("comment")


def classify_round(arms: dict, docs: Path, rnd: int, case: str, original: bytes,
                   follow: bool, stops: list[str]) -> dict | None:
    where = f"{case} round {rnd}"
    for name in ARMS:
        arm = arms.get(name)
        if arm is None:
            stops.append(f"{where}: arm {name} missing")
            return None
        if "fatal" in arm:
            stops.append(f"{where}: arm {name} fatal {arm['fatal']}")
            return None
        if arm.get("placementOk") is not True:
            stops.append(f"{where}: arm {name} placement check failed")
            return None
    b, key, select = arms["b"], arms["key"], arms["select"]
    if b.get("saved") is not True or key.get("saved") is not True:
        stops.append(f"{where}: b or key arm not saved")
        return None
    if (select.get("unit") or {}).get("codePoints") != (b.get("unit") or {}).get("codePoints"):
        stops.append(f"{where}: select and b arms selected different units")
        return None
    unit = b.get("unit") or {}
    typed = bool(b.get("pretype"))
    stem = docs / f"r{rnd}-{case}"
    result = {"unit": unit.get("codePoints"), "restorePresses": b.get("restorePresses", 0),
              "comment": top_comment(key.get("undoAfter")), "typed": typed}
    if unit.get("type") == 0:
        result["class"] = "nothing-selected"
        return result
    if not any(cp in SEPARATORS for cp in unit.get("codePoints") or []):
        result["class"] = "barrier"
        return result
    origin = (b.get("typedAt") if typed else b.get("placed")) or {}
    restored = b.get("restored") or {}
    if not (restored.get("type") == 0 and origin.get("cursor") and
            restored.get("cursor") == origin.get("cursor")):
        result["class"] = "restore-refused"
        return result
    if typed:
        difference = first_difference(paragraph_texts(str(stem) + "-b.odt"),
                                      paragraph_texts(str(stem) + "-key.odt"))
        if difference:
            stops.append(f"{where}: typed case, b arm differs from key arm: {difference}")
            return None
        result["class"] = "typed-merge"
    else:
        key_content = content(Path(str(stem) + "-key.odt"))
        b_content = content(Path(str(stem) + "-b.odt"))
        if key_content == original:
            if b_content != original:
                stops.append(f"{where}: key changed nothing but the b arm changed the document")
                return None
            result["class"] = "key-noop"
            return result
        if b_content != key_content:
            stops.append(f"{where}: restore came back but b arm content.xml != key arm")
            return None
        result["class"] = "merge"
    if follow:
        if b.get("followSaved") is not True or key.get("followSaved") is not True:
            stops.append(f"{where}: follow text not saved")
            return None
        difference = first_difference(paragraph_texts(str(stem) + "-b-follow.odt"),
                                      paragraph_texts(str(stem) + "-key-follow.odt"))
        if difference:
            stops.append(f"{where}: text typed after the b arm landed elsewhere: {difference}")
            return None
    return result


def main(argv: list[str]) -> int:
    if len(argv) < 4 or argv[0] != "--out" or (len(argv) - 2) % 2:
        print(__doc__, file=sys.stderr)
        return 2
    out = Path(argv[1])
    pairs = [(Path(argv[i]), Path(argv[i + 1])) for i in range(2, len(argv), 2)]
    stops: list[str] = []
    report = {"inputs": [], "cases": [], "classes": {c: [] for c in CLASSES}, "stops": stops}
    for round_dir, tsv in pairs:
        ids = case_ids(tsv)
        lines = (round_dir / "arms.jsonl").read_text(encoding="utf-8").splitlines()
        if not lines or json.loads(lines[0]).get("original") is not True:
            stops.append(f"{round_dir}: no original.odt")
            continue
        original = content(round_dir / "docs" / "original.odt")
        follow = (round_dir / "follow-text.txt").exists()
        by_case: dict[str, dict[int, dict]] = {}
        for line in lines[1:]:
            arm = json.loads(line)
            by_case.setdefault(arm.get("case"), {}).setdefault(arm.get("round"), {})[arm.get("arm")] = arm
        rounds = sorted({r for per in by_case.values() for r in per})
        if rounds != [1, 2, 3]:
            stops.append(f"{round_dir}: rounds {rounds}, want [1, 2, 3]")
        unknown = set(by_case) - set(ids)
        if unknown:
            stops.append(f"{round_dir}: arms for cases not in {tsv.name}: {sorted(unknown)}")
        report["inputs"].append({
            "roundDir": str(round_dir), "cases": str(tsv), "caseCount": len(ids),
            "casesSha256": hashlib.sha256(tsv.read_bytes()).hexdigest(),
            "inputsSha256": (round_dir / "inputs.sha256").read_text(encoding="utf-8").strip().splitlines(),
            "followText": follow,
        })
        for case in ids:
            per_round = [classify_round(by_case.get(case, {}).get(r, {}), round_dir / "docs", r, case,
                                        original, follow, stops) for r in (1, 2, 3)]
            if any(r is None for r in per_round):
                continue
            classes = {r["class"] for r in per_round}
            presses = {r["restorePresses"] for r in per_round}
            comments = {r["comment"] for r in per_round}
            if len(classes) != 1:
                stops.append(f"{case}: class differs between rounds: {sorted(classes)}")
                continue
            if len(presses) != 1:
                stops.append(f"{case}: restore presses differ between rounds: {sorted(presses)}")
                continue
            klass = classes.pop()
            entry = {"fixture": round_dir.name, "roundDir": str(round_dir), "case": case,
                     "class": klass, "restorePresses": presses.pop(),
                     "unit": per_round[0]["unit"], "typed": per_round[0]["typed"],
                     "comment": comments.pop() if len(comments) == 1 else sorted(map(str, comments))}
            report["cases"].append(entry)
            report["classes"][klass].append(f"{round_dir.name}:{case}")
    for klass in CLASSES:
        if not report["classes"][klass]:
            stops.append(f"class {klass} is empty across all inputs")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for klass in CLASSES:
        print(f"{klass}: {len(report['classes'][klass])}")
    for stop in stops:
        print("STOP " + stop)
    return 1 if stops else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
