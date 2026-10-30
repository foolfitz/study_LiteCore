#!/usr/bin/env python3
"""SPEC-M3-v28-last-line-fallback 7.3 F3-82, reading 2: every check's outcome equals F3-81's, with NO declared move
(spec 8 item 1) -- and reading 1 (tools/read_v25_f3.py, unchanged, imported) is F3_RED with exactly F3-81's four
problems.

Derived from tools/read_v81_f3_equal.py (bound by F3-81's evidence; not edited).  The differences are a closed list:
this docstring; BASELINE = F3-81 (findings/evidence/v27-176/f3-81/run-01) instead of F3-80; the names v81 -> v82 and
f380 -> f381 in the code, the argument and the verdict; DECLARED is empty, so `declared_reason` and the declared
branch are gone; the report-level clauses compare with the baseline's values (`recoveryPairing.held`, `ok`, and the
verdict's PAIR_VERDICT prefix, all as F3-81 recorded them) instead of a declared true -> false; the self-test
mutations (v81's five generic ones, plus: the bulleting cell back to PASS, the pairing held, report ok true).
READING1 and `read_one` are v81's: F3-81's reading 1 is exactly those four problems (f3-81/README.md).

The bulleting cell (`bulleting-a-blank-line-does-not-demand-a-rollback`) is a blank line in the MIDDLE of the
document (046's cell): `.uno:SelectText` reads text there, so v28's fallback does not run (spec 6, 8 item 1).  Any
moved cell -- to PASS included -- is a finding: stop and look.

  python3 tools/read_v82_f3_equal.py --v82 <f3 run dir>        (expects <dir>/{chrome,firefox}/report.json)
  python3 tools/read_v82_f3_equal.py --v82 <dir> --self-test   (mutations of the real input must each turn red)

Population (form two), per browser, generated from the BASELINE report: one cell per check id.  The two id sets must
be equal per browser; either report without checks is red.  Exit 0 iff F3_82_EQUAL.
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
sys.path.insert(0, str(PROJECT / "tools"))
import read_v25_f3 as reading1  # noqa: E402

BASELINE = REPO / "findings/evidence/v27-176/f3-81/run-01"
BROWSERS = ("chrome", "firefox")
BULLETING = "bulleting-a-blank-line-does-not-demand-a-rollback"
PAIR_VERDICT = "the recovery pair disagrees"
READING1 = [re.compile(rf"^{b} {BULLETING} \[P\]: v24 [A-Z_]+ -> v25 FAIL$") for b in BROWSERS] + \
           [re.compile(rf"^{b} notice-action-recovers-the-session \[recovery-pairing\]: held False$") for b in BROWSERS]


def outcomes(report: dict) -> dict[str, str]:
    return {c["id"]: c.get("outcome") for c in report.get("checks", [])}


def read(baseline: dict[str, dict], v82: dict[str, dict]) -> dict:
    problems, moved, counts = [], [], {}
    for browser in BROWSERS:
        base, new = outcomes(baseline.get(browser, {})), outcomes(v82.get(browser, {}))
        if not base or not new:
            problems.append(f"{browser}: {'baseline' if not base else 'v82'} report has no checks")
            continue
        if set(base) != set(new):
            problems.append(f"{browser}: id sets differ: only f3-81 {sorted(set(base) - set(new))}, "
                            f"only v82 {sorted(set(new) - set(base))}")
        same = 0
        for check in sorted(set(base) & set(new)):
            if base[check] == new[check]:
                same += 1
            else:
                moved.append({"browser": browser, "check": check, "f381": base[check], "v82": new[check]})
                problems.append(f"{browser} {check}: f3-81 {base[check]} -> v82 {new[check]}")
        counts[browser] = {"cells": len(set(base) | set(new)), "equal": same}
        old, now = baseline.get(browser, {}), v82.get(browser, {})
        was = (old.get("recoveryPairing") or {}).get("held")
        held = (now.get("recoveryPairing") or {}).get("held")
        if held != was:
            problems.append(f"{browser}: recoveryPairing.held f3-81 {was!r} -> v82 {held!r}")
        if now.get("ok") != old.get("ok"):
            problems.append(f"{browser}: report ok f3-81 {old.get('ok')!r} -> v82 {now.get('ok')!r}")
        if str(old.get("verdict") or "").startswith(PAIR_VERDICT) != str(now.get("verdict") or "").startswith(PAIR_VERDICT):
            problems.append(f"{browser}: report verdict prefix {PAIR_VERDICT!r} moved")
    return {"verdict": "F3_82_EQUAL" if not problems else "F3_82_MOVED",
            "baseline": str(BASELINE.relative_to(REPO)), "counts": counts, "moved": moved, "problems": problems}


def read_one(baseline1: dict[str, dict], v82: dict[str, dict], dispositions: str) -> dict:
    """Reading 1, unchanged, and whether its problems are exactly F3-81's four."""
    result = reading1.read(baseline1, v82, dispositions)
    got = result["problems"]
    unmatched = [p for p in got if not any(r.match(p) for r in READING1)]
    missing = [r.pattern for r in READING1 if not any(r.match(p) for p in got)]
    exact = result["verdict"] == "F3_RED" and not unmatched and not missing and len(got) == len(READING1)
    return {"verdict": result["verdict"], "exactlyAsF381": exact, "problems": got,
            "unmatched": unmatched, "missing": missing}


def load(directory: Path) -> dict[str, dict]:
    return {b: json.loads((directory / b / "report.json").read_text(encoding="utf-8")) for b in BROWSERS}


def combined(baseline, baseline1, v82, dispositions):
    two, one = read(baseline, v82), read_one(baseline1, v82, dispositions)
    ok = two["verdict"] == "F3_82_EQUAL" and one["exactlyAsF381"]
    return {"verdict": "F3_82_EQUAL" if ok else "F3_82_MOVED", "reading2": two, "reading1": one}


def mutations(v82: dict[str, dict]):
    def checks(r, b):
        return r[b]["checks"]

    def cell(r, b, cid):
        return next(c for c in checks(r, b) if c["id"] == cid)

    def pass_to_fail(r):
        next(c for c in checks(r, "chrome") if c.get("outcome") == "PASS")["outcome"] = "FAIL"

    def ne_to_pass(r):  # an improvement is a move too
        next(c for c in checks(r, "firefox") if c.get("outcome") == "NOT_ESTABLISHED")["outcome"] = "PASS"

    def missing(r):
        checks(r, "chrome").pop()

    def extra(r):
        checks(r, "firefox").append({"id": "a-check-f3-81-never-had", "outcome": "PASS"})

    def empty(r):
        r["chrome"]["checks"] = []

    def bulleting_back_to_pass(r):
        cell(r, "chrome", BULLETING)["outcome"] = "PASS"

    def pairing_held(r):
        r["firefox"]["recoveryPairing"]["held"] = True

    def report_ok(r):
        r["chrome"]["ok"] = True

    out = []
    for fn in (pass_to_fail, ne_to_pass, missing, extra, empty, bulleting_back_to_pass, pairing_held, report_ok):
        mutated = copy.deepcopy(v82)
        fn(mutated)
        out.append((fn.__name__, mutated))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--v82", type=Path, required=True, help="F3 run dir with chrome/ and firefox/ report.json")
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    baseline, v82 = load(args.baseline), load(args.v82)
    baseline1, dispositions = load(reading1.BASELINE), reading1.DISPOSITIONS.read_text(encoding="utf-8")
    if args.self_test:
        if combined(baseline, baseline1, v82, dispositions)["verdict"] != "F3_82_EQUAL":
            print("self-test needs an input that holds", file=sys.stderr)
            return 2
        results = {name: combined(baseline, baseline1, mutated, dispositions)["verdict"]
                   for name, mutated in mutations(v82)}
        red = all(v != "F3_82_EQUAL" for v in results.values())
        print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "mutations": results}, indent=1))
        return 0 if red else 1
    result = combined(baseline, baseline1, v82, dispositions)
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0 if result["verdict"] == "F3_82_EQUAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
