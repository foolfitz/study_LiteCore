#!/usr/bin/env python3
"""SPEC-M3-select-all-v26 append 2 (F3-80, reading 3): the three Chrome cells finding 175 blinded, read by count.

A new reader, not a derivation (fable ruling B modified, findings/evidence/select-all-v26/f3/RULING-fable-2026-10-30.md).
The bound runner (tools/run_e2_c_product_path.py, not edited) takes the engine's selected text from the copy
toast's "U+XXXX" list; generation 80 (finding 175) prints `已複製 N 字` instead, so three Chrome cells lost their
observable and moved: read-01 is F3_RED and equal-01 is F3_80_MOVED with exactly those three.  Those two records
stay as they are.  This reader decides whether the move is ONLY that: each cell's own predicate with the toast's
count in place of the text, every expected value taken from the F3-79 report (the baseline), never from
generation 80.  It reads committed reports only -- no browser, nothing written.

  python3 tools/read_v80_f3_append2.py               > ../findings/evidence/select-all-v26/f3/append2-read-01.json
  python3 tools/read_v80_f3_append2.py --self-test   > ../findings/evidence/select-all-v26/f3/append2-self-test.json

Inputs (pinned): the F3-79 Chrome report; the two generation-80 Chrome reports (F3-80 run-01, and the suite F4-80's
runner executed before its arms); read-01.json; equal-01.json.  Conditions A-F and B'/C' are spec append 2's.
Exit 0 iff F3_80_HOLDS_UNDER_APPEND_2 (or, with --self-test, iff every mutation is red and the real input is not).
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
EV = REPO / "findings/evidence"
BASELINE = EV / "shell-v79-173/f3/run-01/chrome/report.json"
GEN80 = {"f3-80": EV / "select-all-v26/f3/run-01/chrome/report.json",
         "f4-80": EV / "select-all-v26/f4/chrome/report.json"}
READ01 = EV / "select-all-v26/f3/read-01.json"
EQUAL01 = EV / "select-all-v26/f3/equal-01.json"

ABORT, INLINE, AGREE = ("an-aborted-gesture-stops-selecting", "an-inline-format-reaches-a-selection",
                        "the-page-agrees-with-the-engine-about-the-selection")
# Spec append 2's closed list, as the two original readers word it.
READ01_PROBLEMS = [
    f"chrome {ABORT} [no-regression]: v24 PASS -> v25 NOT_ESTABLISHED",
    f"chrome {INLINE} [P]: v24 FAIL -> v25 FAIL",
    f"chrome {AGREE} [no-regression]: v24 PASS -> v25 NOT_ESTABLISHED",
]
EQUAL01_MOVED = [
    {"browser": "chrome", "check": ABORT, "f379": "PASS", "v80": "NOT_ESTABLISHED"},
    {"browser": "chrome", "check": INLINE, "f379": "PASS", "v80": "FAIL"},
    {"browser": "chrome", "check": AGREE, "f379": "PASS", "v80": "NOT_ESTABLISHED"},
]
EQUAL01_COUNTS = {"chrome": {"cells": 46, "equal": 43}, "firefox": {"cells": 46, "equal": 46}}
AIM_KEYS = ("x1", "y", "band", "scanWidth")


def squeeze(value: str) -> str:
    return re.sub(r"\s+", "", value)   # the runner's own (run_e2_c_product_path.py, the inline-format check)


def count(toast) -> int | None:
    match = re.fullmatch(r"已複製 (\d+) 字", toast or "")
    return int(match.group(1)) if match else None


def cells(report: dict) -> dict[str, dict]:
    return {c["id"]: c for c in report.get("checks", [])}


def read_abort(new: dict, base: dict, problems: list, where: str) -> dict:
    o, b = new.get("observed") or {}, base.get("observed") or {}
    arms = [("control", o.get("control") or {}, b.get("control") or {}),
            ("reference", o.get("reference") or {}, b.get("reference") or {})]
    arms += [(a.get("kind"), a, ba) for a, ba in zip(o.get("arms") or [], b.get("arms") or [])]
    numbers = {name: count(arm.get("copyToast")) for name, arm, _ in arms}
    expected = {name: len(barm.get("selectedText") or "") for name, _, barm in arms}

    def need(ok, why):
        if not ok:
            problems.append(f"{where} {ABORT}: {why}")
    need(new.get("outcome") == "NOT_ESTABLISHED", f"outcome {new.get('outcome')}, not NOT_ESTABLISHED")
    need([name for name, _, _ in arms] == ["control", "reference", "pointercancel", "blur"],
         f"arms {[name for name, _, _ in arms]}")
    need(all(isinstance(n, int) for n in numbers.values()), f"a toast is not 已複製 N 字: {numbers}")
    c, r = numbers.get("control"), numbers.get("reference")
    need((o.get("control") or {}).get("aRangeIsSelectedAfterAbortAndMove") is True, "control did not extend")
    need((o.get("reference") or {}).get("aRangeIsSelectedAfterAbortAndMove") is True, "reference did not extend")
    need(isinstance(r, int) and r > 0 and r != c, f"not resolvable: control {c}, reference {r}")
    for name, arm, _ in arms[2:]:
        need(arm.get("aRangeIsSelectedBefore") is False, f"{name} had a range before")
        need(numbers.get(name) == r, f"{name} {numbers.get(name)} != reference {r}")
    aims = {name: {k: (arm.get("aim") or {}).get(k) for k in AIM_KEYS} for name, arm, _ in arms}
    need(len({json.dumps(a, sort_keys=True) for a in aims.values()}) == 1, f"aims differ across arms: {aims}")
    fractions = {name: (arm.get("aim") or {}).get("abortAtFraction") for name, arm, _ in arms}
    need(fractions["control"] == fractions.get("pointercancel") == fractions.get("blur"),
         f"abortAtFraction differs: {fractions}")
    for name, arm, barm in arms:
        need(arm.get("aim") == barm.get("aim"), f"{name} aim differs from F3-79's")
        need(numbers.get(name) == expected[name], f"{name} count {numbers.get(name)} != F3-79 text length {expected[name]}")
        need(expected[name] > 0 and "U+" in (barm.get("copyToast") or ""), f"{name}: F3-79 had no U+ text (vacuous)")
        need("U+" not in (arm.get("copyToast") or ""), f"{name}: the generation-80 toast still carries U+")
    return {"counts": numbers, "f379TextLengths": expected, "f379Texts": {n: ba.get("selectedText") for n, _, ba in arms},
            "aim": aims.get("control"), "abortAtFraction": fractions}


def read_inline(new: dict, base: dict, problems: list, where: str) -> dict:
    o, b = new.get("observed") or {}, base.get("observed") or {}
    selected = b.get("selectedText") or ""
    before, after = o.get("boldBefore") or "", o.get("boldAfter") or ""

    def need(ok, why):
        if not ok:
            problems.append(f"{where} {INLINE}: {why}")
    need(new.get("outcome") == "FAIL", f"outcome {new.get('outcome')}, not FAIL")
    need(bool(selected), "F3-79's selectedText is empty (vacuous)")
    need(o.get("savedIsOdt") is True, "the save is not an ODT")
    need((o.get("buttonAfterDrag") or {}).get("disabled") is False, "the bold button was disabled after the drag")
    need(bool(selected) and squeeze(selected) not in squeeze(before), "the selection was bold before")
    need(bool(selected) and squeeze(selected) in squeeze(after), "the selection is not bold after")
    need(bool(selected) and squeeze(after).replace(squeeze(selected), "", 1) == squeeze(before),
         "something other than the selection became bold")
    need(o.get("drag") == b.get("drag"), f"drag {o.get('drag')} differs from F3-79's {b.get('drag')}")
    return {"f379Selected": selected, "boldBeforeLength": len(squeeze(before)),
            "boldAfterLength": len(squeeze(after)), "drag": o.get("drag")}


def read_agree(new: dict, base: dict, problems: list, where: str) -> dict:
    o, b = new.get("observed") or {}, base.get("observed") or {}
    n, after = count(o.get("copyToast")), o.get("pageAfter") or {}

    def need(ok, why):
        if not ok:
            problems.append(f"{where} {AGREE}: {why}")
    need(new.get("outcome") == "NOT_ESTABLISHED", f"outcome {new.get('outcome')}, not NOT_ESTABLISHED")
    need(isinstance(n, int) and n > 0, f"the toast is not 已複製 N 字 with N > 0: {o.get('copyToast')!r}")
    need(n == b.get("engineCodePoints"), f"count {n} != F3-79 engineCodePoints {b.get('engineCodePoints')}")
    need((b.get("engineCodePoints") or 0) > 0 and "U+" in (b.get("copyToast") or ""), "F3-79 had no U+ text (vacuous)")
    need("U+" not in (o.get("copyToast") or ""), "the generation-80 toast still carries U+")
    need(o.get("pageSaysARange") is True, "the page does not say a range")
    need(after.get("shape") in ("range-single", "range-cross"), f"page shape {after.get('shape')}")
    need(after.get("unreadable") is not True, "the page's shape is unreadable")
    need(o.get("drag") == b.get("drag"), f"drag {o.get('drag')} differs from F3-79's {b.get('drag')}")
    return {"count": n, "f379EngineCodePoints": b.get("engineCodePoints"), "pageAfter": after, "drag": o.get("drag")}


def read(inputs: dict) -> dict:
    problems, per_run = [], {}
    base = cells(inputs["baseline"])
    for name, report in inputs["gen80"].items():
        new = cells(report)
        missing = [c for c in (ABORT, INLINE, AGREE) if c not in new or c not in base]
        if missing:
            problems.append(f"{name}: cells missing: {missing}")
            continue
        per_run[name] = {"abort": read_abort(new[ABORT], base[ABORT], problems, name),
                         "inline": read_inline(new[INLINE], base[INLINE], problems, name),
                         "agree": read_agree(new[AGREE], base[AGREE], problems, name)}
    numbers = {name: {"abort": r["abort"]["counts"], "inline": [r["inline"]["boldBeforeLength"], r["inline"]["boldAfterLength"]],
                      "agree": r["agree"]["count"]} for name, r in per_run.items()}
    if len({json.dumps(v, sort_keys=True) for v in numbers.values()}) != 1 or len(numbers) != len(inputs["gen80"]):
        problems.append(f"the generation-80 runs disagree: {numbers}")
    r1, e1 = inputs["read01"], inputs["equal01"]
    if r1.get("verdict") != "F3_RED" or r1.get("problems") != READ01_PROBLEMS:
        problems.append(f"read-01 is not F3_RED with exactly the three problems: {r1.get('verdict')} {r1.get('problems')}")
    if e1.get("verdict") != "F3_80_MOVED" or e1.get("moved") != EQUAL01_MOVED or e1.get("counts") != EQUAL01_COUNTS:
        problems.append(f"equal-01 is not F3_80_MOVED with exactly the three moves: {e1.get('verdict')} "
                        f"{e1.get('moved')} {e1.get('counts')}")
    return {"verdict": "F3_80_HOLDS_UNDER_APPEND_2" if not problems else "F3_80_APPEND_2_RED",
            "spec": "specs/SPEC-M3-select-all-v26.md append 2",
            "inputs": {"baseline": str(BASELINE.relative_to(REPO)),
                       "gen80": {k: str(v.relative_to(REPO)) for k, v in GEN80.items()},
                       "read01": str(READ01.relative_to(REPO)), "equal01": str(EQUAL01.relative_to(REPO))},
            "runs": per_run, "problems": problems}


def load() -> dict:
    def j(path):
        return json.loads(path.read_text(encoding="utf-8"))
    return {"baseline": j(BASELINE), "gen80": {k: j(v) for k, v in GEN80.items()}, "read01": j(READ01), "equal01": j(EQUAL01)}


def mutations(inputs: dict):
    def obs(i, run, cell):
        return cells(i["gen80"][run])[cell]["observed"]

    def arm(i, run, kind):
        return next(a for a in obs(i, run, ABORT)["arms"] if a["kind"] == kind)

    def m1(i): arm(i, "f3-80", "blur")["copyToast"] = "已複製 13 字"
    def m2(i): obs(i, "f3-80", ABORT)["control"]["copyToast"] = "已複製 12 字"
    def m3(i): obs(i, "f3-80", AGREE)["copyToast"] = "已複製 0 字"
    def m4(i): obs(i, "f3-80", AGREE)["pageSaysARange"] = False
    def m5(i): obs(i, "f3-80", INLINE)["boldAfter"] = obs(i, "f3-80", INLINE)["boldAfter"].replace("KITAL", "", 1)
    def m6(i): obs(i, "f3-80", INLINE)["savedIsOdt"] = False
    def m7(i): cells(i["baseline"])[INLINE]["observed"]["selectedText"] = ""
    def m8(i): i["read01"]["problems"].append("chrome a-fourth-cell [no-regression]: v24 PASS -> v25 FAIL")
    def m9(i): i["read01"]["problems"].pop()
    def m10(i): i["equal01"]["moved"].append({"browser": "chrome", "check": "a-fourth-cell", "f379": "PASS", "v80": "FAIL"})
    def m11(i): arm(i, "f3-80", "blur")["aim"]["x1"] = "0.20000"
    def m12(i): arm(i, "f4-80", "blur")["copyToast"] = "已複製 11 字"
    def m13(i): obs(i, "f3-80", AGREE)["copyToast"] = "已複製 U+004B,U+0049,U+0054,U+0041,U+004C 字"
    def m14(i): obs(i, "f3-80", INLINE)["drag"]["x1"] = "0.14000"

    for fn in (m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13, m14):
        mutated = copy.deepcopy(inputs)
        fn(mutated)
        yield fn.__name__, mutated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    inputs = load()
    if args.self_test:
        base = read(inputs)["verdict"]
        results = {name: read(mutated)["verdict"] for name, mutated in mutations(inputs)}
        red = base == "F3_80_HOLDS_UNDER_APPEND_2" and all(v == "F3_80_APPEND_2_RED" for v in results.values())
        print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "base": base, "mutations": results},
                         indent=1))
        return 0 if red else 1
    result = read(inputs)
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0 if result["verdict"] == "F3_80_HOLDS_UNDER_APPEND_2" else 1


if __name__ == "__main__":
    sys.exit(main())
