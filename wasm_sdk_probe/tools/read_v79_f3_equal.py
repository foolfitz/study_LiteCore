#!/usr/bin/env python3
"""SPEC-M3-shell-v79-finding-173 5.4 (F3-79, reading 2): every check's outcome equals v25 F3 run-02's.

The fix touches one disposition branch and the condition of one review sentence, so on the product-path
suite any other moved cell is a finding, not noise -- moving to PASS included (it is named and red like any
other move; a move is examined before anything else is decided).

  python3 tools/read_v79_f3_equal.py --v79 <f3 run dir>        (expects <dir>/{chrome,firefox}/report.json)
  python3 tools/read_v79_f3_equal.py --v79 <dir> --self-test   (mutations of the real input must each turn red)

Population (form two), per browser, generated from the BASELINE report -- v25 F3's verdict run, run-02
(read-02.json, F3_HOLDS): one cell per check id.  The two id sets must be equal per browser; either report
without checks is red.  Reading 1 (spec 16 / 16.1 against v24 T4) is tools/read_v25_f3.py, unchanged.
Exit 0 iff F3_79_EQUAL.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
BASELINE = REPO / "findings/evidence/link-batch-v25/f3/run-02"
BROWSERS = ("chrome", "firefox")


def outcomes(report: dict) -> dict[str, str]:
    return {c["id"]: c.get("outcome") for c in report.get("checks", [])}


def read(baseline: dict[str, dict], v79: dict[str, dict]) -> dict:
    problems, moved, counts = [], [], {}
    for browser in BROWSERS:
        base, new = outcomes(baseline.get(browser, {})), outcomes(v79.get(browser, {}))
        if not base or not new:
            problems.append(f"{browser}: {'baseline' if not base else 'v79'} report has no checks")
            continue
        if set(base) != set(new):
            problems.append(f"{browser}: id sets differ: only run-02 {sorted(set(base) - set(new))}, "
                            f"only v79 {sorted(set(new) - set(base))}")
        same = 0
        for check in sorted(set(base) & set(new)):
            if base[check] == new[check]:
                same += 1
            else:
                moved.append({"browser": browser, "check": check, "run02": base[check], "v79": new[check]})
                problems.append(f"{browser} {check}: run-02 {base[check]} -> v79 {new[check]}")
        counts[browser] = {"cells": len(set(base) | set(new)), "equal": same}
    return {"verdict": "F3_79_EQUAL" if not problems else "F3_79_MOVED", "baseline": str(BASELINE.relative_to(REPO)),
            "counts": counts, "moved": moved, "problems": problems}


def load(directory: Path) -> dict[str, dict]:
    return {b: json.loads((directory / b / "report.json").read_text(encoding="utf-8")) for b in BROWSERS}


def mutations(v79: dict[str, dict]):
    def checks(r, b):
        return r[b]["checks"]

    def pass_to_fail(r):
        next(c for c in checks(r, "chrome") if c.get("outcome") == "PASS")["outcome"] = "FAIL"

    def ne_to_pass(r):  # an improvement is a move too
        next(c for c in checks(r, "firefox") if c.get("outcome") == "NOT_ESTABLISHED")["outcome"] = "PASS"

    def missing(r):
        checks(r, "chrome").pop()

    def extra(r):
        checks(r, "firefox").append({"id": "a-check-run-02-never-had", "outcome": "PASS"})

    def empty(r):
        r["chrome"]["checks"] = []

    out = []
    for fn in (pass_to_fail, ne_to_pass, missing, extra, empty):
        mutated = copy.deepcopy(v79)
        fn(mutated)
        out.append((fn.__name__, mutated))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--v79", type=Path, required=True, help="F3 run dir with chrome/ and firefox/ report.json")
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    baseline, v79 = load(args.baseline), load(args.v79)
    if args.self_test:
        if read(baseline, v79)["verdict"] != "F3_79_EQUAL":
            print("self-test needs an equal input", file=sys.stderr)
            return 2
        results = {name: read(baseline, mutated)["verdict"] for name, mutated in mutations(v79)}
        red = all(v != "F3_79_EQUAL" for v in results.values())
        print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "mutations": results}, indent=1))
        return 0 if red else 1
    result = read(baseline, v79)
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0 if result["verdict"] == "F3_79_EQUAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
