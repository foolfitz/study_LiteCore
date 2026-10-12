#!/usr/bin/env python3
"""SPEC-M3-held-key §5.2, criterion 132-B: judge probe reports of a held Backspace.

  judge_132b.py --page SHA256 REPORT.json [REPORT.json ...]
  judge_132b.py --self-test BASELINE.json

Reads what `probe_hand_test_0212.py --arms hold-high,hold-low,wash-control` wrote (each hold's
`hold_summary`, each single press's, `persistent`, `washControl`).  Every hold must pass:

  (a) tail      deletesAfterRelease <= 2
  (b) screen    deletesShownAtRelease >= deletesDoneAtRelease - 2
  (c) no stall  deleted >= 20, beforeinputs == deleted, otherLatency == []
  (d) no blue   no wash during the hold, none on any single press
  (e) no ghost  persistent.differing == 0

and per browser: at least 3 holds in each of hold-high and hold-low, and the positive control
(wash-control: the user's own range washed at least once).  Per report: the page served at the start
(`static`) and at the end (`staticAfter`) is --page.  Exit 0 only when every cell passes in both
Chrome and Firefox.  Also prints the named numbers (§5.2: recorded, not thresholds).

--self-test: the baseline must come out red where §6 says (a) and (d) on every hold, (b) on every
low hold); a synthetic report made from it with every cell passing must come out green; and each
criterion broken alone in that synthetic report must turn exactly that criterion red.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ARMS = (("holdHigh", "hold-high"), ("holdLow", "hold-low"))
BROWSERS = ("chrome", "firefox")
MIN_ROUNDS = 3


def judge_hold(rnd: dict[str, Any]) -> dict[str, list[str]]:
    """The criteria that fail for one hold, each with why."""
    h = rnd.get("hold") or {}
    out: dict[str, list[str]] = {}
    def fail(key: str, why: str) -> None:
        out.setdefault(key, []).append(why)
    if "error" in h:
        fail("c", f"no hold summary: {h['error']}")
        return out
    if h.get("deletesAfterRelease") is None or h["deletesAfterRelease"] > 2:
        fail("a", f"deletesAfterRelease {h.get('deletesAfterRelease')}")
    done, shown = h.get("deletesDoneAtRelease"), h.get("deletesShownAtRelease")
    if done is None or shown is None or shown < done - 2:
        fail("b", f"shown {shown} vs done {done} at release")
    if (h.get("deleted") or 0) < 20:
        fail("c", f"deleted {h.get('deleted')}")
    if h.get("beforeinputs") != h.get("deleted"):
        fail("c", f"beforeinputs {h.get('beforeinputs')} != deleted {h.get('deleted')}")
    if h.get("otherLatency"):
        fail("c", f"otherLatency {h['otherLatency']}")
    washes = len(h.get("washes") or []) + sum(len(s.get("washes") or []) for s in rnd.get("singles") or [])
    if washes:
        fail("d", f"{len(h.get('washes') or [])} washes in the hold, "
                  f"{[len(s.get('washes') or []) for s in rnd.get('singles') or []]} on the single presses")
    differing = (rnd.get("persistent") or {}).get("differing")
    if differing != 0:
        fail("e", f"persistent.differing {differing}")
    return out


def judge(reports: list[dict[str, Any]], page: str) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True
    seen: dict[str, dict[str, Any]] = {}
    for n, report in enumerate(reports):
        for when in ("static", "staticAfter"):
            served = (report.get(when) or {}).get("servedPage")
            if served != page:
                ok = False
                lines.append(f"report {n}: {when}.servedPage {served} != {page}  FAIL")
        for run in report.get("runs", []):
            browser = run.get("browser")
            entry = seen.setdefault(browser, {"holds": {arm: 0 for arm, _ in ARMS}, "control": [],
                                              "deleted": [], "lastAfterRelease": [], "freshAfterRelease": []})
            if run.get("fatal"):
                ok = False
                lines.append(f"{browser}: fatal in the run  FAIL")
            for arm, label in ARMS:
                for i, rnd in enumerate((run.get(arm) or {}).get("rounds", [])):
                    entry["holds"][arm] += 1
                    failed = judge_hold(rnd)
                    h = rnd.get("hold") or {}
                    entry["deleted"].append(h.get("deleted"))
                    entry["lastAfterRelease"].append(h.get("lastDeleteAfterReleaseMs"))
                    entry["freshAfterRelease"].append(h.get("caretBandFreshAfterReleaseMs"))
                    verdict = "PASS" if not failed else "FAIL " + " ".join(sorted(failed))
                    lines.append(f"{browser} {label} round {i}: {verdict}"
                                 + "".join(f"\n    ({k}) {'; '.join(v)}" for k, v in sorted(failed.items())))
                    ok = ok and not failed
            control = run.get("washControl")
            if control is not None:
                entry["control"].append(control.get("selFills", 0))
    for browser in BROWSERS:
        entry = seen.get(browser)
        if entry is None:
            ok = False
            lines.append(f"{browser}: no run  FAIL")
            continue
        for arm, label in ARMS:
            if entry["holds"][arm] < MIN_ROUNDS:
                ok = False
                lines.append(f"{browser} {label}: {entry['holds'][arm]} holds < {MIN_ROUNDS}  FAIL")
        if not entry["control"]:
            ok = False
            lines.append(f"{browser} wash-control: not run  NOT_ESTABLISHED")
        elif min(entry["control"]) < 1:
            ok = False
            lines.append(f"{browser} wash-control: selection fills {entry['control']}  FAIL")
        else:
            lines.append(f"{browser} wash-control: selection fills {entry['control']}  PASS")
        lines.append(f"{browser} named numbers: deleted per hold {entry['deleted']}; last delete after release ms "
                     f"{entry['lastAfterRelease']}; caret band fresh after release ms {entry['freshAfterRelease']}")
    lines.append("132-B " + ("PASS" if ok else "FAIL"))
    return ok, lines


def self_test(baseline_path: Path) -> int:
    baseline = json.loads(baseline_path.read_text())
    page = baseline["static"]["servedPage"]
    problems: list[str] = []
    # 1. The baseline is red where §6 says.
    base = copy.deepcopy(baseline)
    base.setdefault("staticAfter", base["static"])
    for run in base["runs"]:
        for arm, _ in ARMS:
            for rnd in run[arm]["rounds"]:
                failed = judge_hold(rnd)
                want = {"a", "d"} | ({"b"} if arm == "holdLow" else set())
                if set(failed) != want:
                    problems.append(f"baseline {run['browser']} {arm}: failed {sorted(failed)}, expected {sorted(want)}")
    ok, _ = judge([base], page)
    if ok:
        problems.append("baseline judged PASS")
    # 2. A synthetic report with every cell passing is green.
    good = copy.deepcopy(base)
    for run in good["runs"]:
        run["washControl"] = {"selFills": 1}
        for arm, _ in ARMS:
            rounds = run[arm]["rounds"]
            rounds.append(copy.deepcopy(rounds[-1]))
            for rnd in rounds:
                h = rnd["hold"]
                h.update(deletesAfterRelease=1, deletesShownAtRelease=h["deletesDoneAtRelease"], deleted=25,
                         beforeinputs=25, otherLatency=[], washes=[])
                for single in rnd["singles"]:
                    single["washes"] = []
    ok, lines = judge([good], page)
    if not ok:
        problems.append("synthetic all-pass judged FAIL:\n  " + "\n  ".join(lines))
    # 3. Each criterion broken alone turns exactly it red.
    breaks = {
        "a": lambda r: r["hold"].update(deletesAfterRelease=3),
        "b": lambda r: r["hold"].update(deletesShownAtRelease=r["hold"]["deletesDoneAtRelease"] - 3),
        "c": lambda r: r["hold"].update(deleted=19, beforeinputs=19),
        "d": lambda r: r["singles"][0].update(washes=[{"t": 0}]),
        "e": lambda r: r.update(persistent={"differing": 7}),
    }
    for key, breaker in breaks.items():
        bad = copy.deepcopy(good)
        rnd = bad["runs"][1]["holdLow"]["rounds"][2]
        breaker(rnd)
        failed = judge_hold(rnd)
        ok, _ = judge([bad], page)
        if set(failed) != {key} or ok:
            problems.append(f"breaking ({key}) alone: failed {sorted(failed)}, report PASS={ok}")
    # 4. Other pages, a missing browser, too few rounds, no control.
    for name, mutate in {
        "another page": lambda r: r["static"].update(servedPage="0" * 64),
        "page changed during the run": lambda r: r.update(staticAfter={"servedPage": "0" * 64}),
        "Firefox missing": lambda r: r.update(runs=r["runs"][:1]),
        "two rounds": lambda r: r["runs"][0]["holdHigh"]["rounds"].pop(),
        "no control": lambda r: r["runs"][0].pop("washControl"),
    }.items():
        bad = copy.deepcopy(good)
        mutate(bad)
        if judge([bad], page)[0]:
            problems.append(f"{name}: judged PASS")
    print("self-test", "OK" if not problems else "FAILED")
    for problem in problems:
        print(" ", problem)
    return 0 if not problems else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", help="sha256 of the candidate page every report must have been served")
    parser.add_argument("--self-test", type=Path, help="the baseline report")
    parser.add_argument("reports", nargs="*", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.self_test)
    if not args.page or not args.reports:
        parser.error("--page and at least one report")
    ok, lines = judge([json.loads(p.read_text()) for p in args.reports], args.page)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
