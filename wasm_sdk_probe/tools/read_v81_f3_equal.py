#!/usr/bin/env python3
"""SPEC-M3-v27-finding-176 7.3 F3-81, reading 2: every check's outcome equals F3-80's except exactly the moves spec 8
declares -- and reading 1 (tools/read_v25_f3.py, unchanged, imported) is F3_RED with exactly the declared problems.

Derived from tools/read_v80_f3_equal.py (bound by F3-80's evidence; not edited).  The differences are a closed list:
this docstring; BASELINE = F3-80 (the clipboard run, findings/evidence/select-all-v26/f3-clipboard/run-01) instead of
F3-79; the names v80 -> v81 and f379 -> f380 in the code, the argument and the verdict; DECLARED and its pinned
reason (below); the report-level clauses; the reading-1 clause; their self-test mutations.  The per-cell comparison
is v80's line for line, with a declared move taken out of `moved` instead of reported.

Declared moves (spec 8 items 1, 3, 7; 7.3 F3-81), per browser, exactly:
  bulleting-a-blank-line-does-not-demand-a-rollback  PASS -> FAIL, and the FAIL is v27's, not a rollback:
      observed.state == "ready", observed.toast == "", observed.unverifiedSentence is None
  report: recoveryPairing.held  true -> false; report.ok false; report.verdict starts "the recovery pair disagrees"
`notice-action-recovers-the-session` is NOT a declared move: it stays NOT_ESTABLISHED (spec 8 item 2), so it is
judged by the ordinary equality.  Any other moved cell -- to PASS included -- is a finding: stop and look.

Reading 1 (spec 8 item 5): read_v25_f3.read on the same F3-81 reports must give F3_RED whose problems are exactly,
per browser, `<browser> bulleting-a-blank-line-does-not-demand-a-rollback [P]: v24 <x> -> v25 FAIL` and
`<browser> notice-action-recovers-the-session [recovery-pairing]: held False`.  Nothing else, nothing fewer.

  python3 tools/read_v81_f3_equal.py --v81 <f3 run dir>        (expects <dir>/{chrome,firefox}/report.json)
  python3 tools/read_v81_f3_equal.py --v81 <dir> --self-test   (mutations of the real input must each turn red)

Population (form two), per browser, generated from the BASELINE report: one cell per check id.  The two id sets must
be equal per browser; either report without checks is red.  Exit 0 iff F3_81_DECLARED_ONLY.
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

BASELINE = REPO / "findings/evidence/select-all-v26/f3-clipboard/run-01"
BROWSERS = ("chrome", "firefox")
BULLETING = "bulleting-a-blank-line-does-not-demand-a-rollback"
DECLARED = {BULLETING: ("PASS", "FAIL")}
PAIR_VERDICT = "the recovery pair disagrees"
READING1 = [re.compile(rf"^{b} {BULLETING} \[P\]: v24 [A-Z_]+ -> v25 FAIL$") for b in BROWSERS] + \
           [re.compile(rf"^{b} notice-action-recovers-the-session \[recovery-pairing\]: held False$") for b in BROWSERS]


def outcomes(report: dict) -> dict[str, str]:
    return {c["id"]: c.get("outcome") for c in report.get("checks", [])}


def declared_reason(report: dict) -> list[str]:
    cell = next((c for c in report.get("checks", []) if c["id"] == BULLETING), {})
    observed = cell.get("observed") or {}
    why = []
    if observed.get("state") != "ready":
        why.append(f"observed.state {observed.get('state')!r}")
    if observed.get("toast") != "":
        why.append(f"observed.toast {observed.get('toast')!r}")
    if observed.get("unverifiedSentence") is not None:
        why.append(f"observed.unverifiedSentence {observed.get('unverifiedSentence')!r}")
    return why


def read(baseline: dict[str, dict], v81: dict[str, dict]) -> dict:
    problems, moved, declared, counts = [], [], [], {}
    for browser in BROWSERS:
        base, new = outcomes(baseline.get(browser, {})), outcomes(v81.get(browser, {}))
        if not base or not new:
            problems.append(f"{browser}: {'baseline' if not base else 'v81'} report has no checks")
            continue
        if set(base) != set(new):
            problems.append(f"{browser}: id sets differ: only f3-80 {sorted(set(base) - set(new))}, "
                            f"only v81 {sorted(set(new) - set(base))}")
        same = 0
        for check in sorted(set(base) & set(new)):
            if check in DECLARED:
                want = DECLARED[check]
                if (base[check], new[check]) != want:
                    problems.append(f"{browser} {check}: declared {want[0]} -> {want[1]}, got f3-80 {base[check]} "
                                    f"-> v81 {new[check]}")
                else:
                    why = declared_reason(v81[browser])
                    declared.append({"browser": browser, "check": check, "f380": base[check], "v81": new[check],
                                     "reasonHolds": not why})
                    if why:
                        problems.append(f"{browser} {check}: the FAIL is not v27's: {'; '.join(why)}")
            elif base[check] == new[check]:
                same += 1
            else:
                moved.append({"browser": browser, "check": check, "f380": base[check], "v81": new[check]})
                problems.append(f"{browser} {check}: f3-80 {base[check]} -> v81 {new[check]}")
        counts[browser] = {"cells": len(set(base) | set(new)), "equal": same}
        was = (baseline.get(browser, {}).get("recoveryPairing") or {}).get("held")
        pairing = v81.get(browser, {}).get("recoveryPairing") or {}
        if was is not True or pairing.get("held") is not False:
            problems.append(f"{browser}: recoveryPairing.held declared true -> false, got {was!r} -> {pairing.get('held')!r}")
        if v81.get(browser, {}).get("ok") is not False:
            problems.append(f"{browser}: report ok declared false, got {v81.get(browser, {}).get('ok')!r}")
        if not str(v81.get(browser, {}).get("verdict") or "").startswith(PAIR_VERDICT):
            problems.append(f"{browser}: report verdict does not start {PAIR_VERDICT!r}")
    return {"verdict": "F3_81_DECLARED_ONLY" if not problems else "F3_81_MOVED",
            "baseline": str(BASELINE.relative_to(REPO)), "counts": counts, "declared": declared, "moved": moved,
            "problems": problems}


def read_one(baseline1: dict[str, dict], v81: dict[str, dict], dispositions: str) -> dict:
    """Reading 1, unchanged, and whether its problems are exactly the declared four."""
    result = reading1.read(baseline1, v81, dispositions)
    got = result["problems"]
    unmatched = [p for p in got if not any(r.match(p) for r in READING1)]
    missing = [r.pattern for r in READING1 if not any(r.match(p) for p in got)]
    exact = result["verdict"] == "F3_RED" and not unmatched and not missing and len(got) == len(READING1)
    return {"verdict": result["verdict"], "exactlyDeclared": exact, "problems": got,
            "unmatched": unmatched, "missing": missing}


def load(directory: Path) -> dict[str, dict]:
    return {b: json.loads((directory / b / "report.json").read_text(encoding="utf-8")) for b in BROWSERS}


def combined(baseline, baseline1, v81, dispositions):
    two, one = read(baseline, v81), read_one(baseline1, v81, dispositions)
    ok = two["verdict"] == "F3_81_DECLARED_ONLY" and one["exactlyDeclared"]
    return {"verdict": "F3_81_DECLARED_ONLY" if ok else "F3_81_MOVED", "reading2": two, "reading1": one}


def mutations(v81: dict[str, dict]):
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
        checks(r, "firefox").append({"id": "a-check-f3-80-never-had", "outcome": "PASS"})

    def empty(r):
        r["chrome"]["checks"] = []

    def bulleting_still_pass(r):
        cell(r, "chrome", BULLETING)["outcome"] = "PASS"

    def bulleting_fail_by_rollback(r):
        cell(r, "firefox", BULLETING)["observed"]["state"] = "recoverable-error"

    def bulleting_fail_with_toast(r):
        cell(r, "chrome", BULLETING)["observed"]["toast"] = "• 項目符號：動作已送出，但這一段是空的"

    def pairing_still_held(r):
        r["firefox"]["recoveryPairing"]["held"] = True

    def report_ok(r):
        r["chrome"]["ok"] = True

    out = []
    for fn in (pass_to_fail, ne_to_pass, missing, extra, empty, bulleting_still_pass, bulleting_fail_by_rollback,
               bulleting_fail_with_toast, pairing_still_held, report_ok):
        mutated = copy.deepcopy(v81)
        fn(mutated)
        out.append((fn.__name__, mutated))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--v81", type=Path, required=True, help="F3 run dir with chrome/ and firefox/ report.json")
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    baseline, v81 = load(args.baseline), load(args.v81)
    baseline1, dispositions = load(reading1.BASELINE), reading1.DISPOSITIONS.read_text(encoding="utf-8")
    if args.self_test:
        if combined(baseline, baseline1, v81, dispositions)["verdict"] != "F3_81_DECLARED_ONLY":
            print("self-test needs an input that holds", file=sys.stderr)
            return 2
        results = {name: combined(baseline, baseline1, mutated, dispositions)["verdict"]
                   for name, mutated in mutations(v81)}
        red = all(v != "F3_81_DECLARED_ONLY" for v in results.values())
        print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "mutations": results}, indent=1))
        return 0 if red else 1
    result = combined(baseline, baseline1, v81, dispositions)
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0 if result["verdict"] == "F3_81_DECLARED_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
