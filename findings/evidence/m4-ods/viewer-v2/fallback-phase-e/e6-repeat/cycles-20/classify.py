#!/usr/bin/env python3
"""RULING-fable-1 section 3, as code (written before any 20-cycle run).

Per run, the reopen arm's steps Delta_n = open.begin[n+1] - open.begin[n], n = 1..19.
  tight    no step >= 4,000,000          informative segment: Delta_2..Delta_19
  slack@k  first step >= 4,000,000 is k  informative segment: Delta_2..Delta_(k-1); slack@2 is UNINFORMATIVE
A segment counts when it has >= 10 steps.  On a counting segment, the steps after Delta_2 (Delta_3..):
  R-other       any step > 65,536 outside [4,100,000, 4,300,000], or steps that grow step over step
  R-linear      every step is 8,192, a single 0 tolerated
  R-saturating  0 and staying 0 for >= 5 consecutive steps
  unclassified  none of the above (listed, not forced)
Yield rule: fewer than two counting segments on a link after its six runs -> record the yield, stop.

  classify.py REPORT.json ...      one line per run, then a per-profile summary
  classify.py --selftest
"""
from __future__ import annotations

import json
import sys

SLACK, SMALL, TILE_LO, TILE_HI, MIN_SEGMENT = 4_000_000, 65_536, 4_100_000, 4_300_000, 10


def classify_steps(steps: list[int]) -> dict:
    """steps[0] is Delta_1."""
    k = next((n for n, s in enumerate(steps, start=1) if n >= 2 and s >= SLACK), None)
    if k == 2:
        return {"shape": "slack@2", "class": "uninformative", "segment": []}
    segment = steps[1:(k - 1 if k else len(steps))]          # Delta_2 .. Delta_(k-1)
    shape = f"slack@{k}" if k else "tight"
    if len(segment) < MIN_SEGMENT:
        return {"shape": shape, "class": "short", "segment": segment}
    tail = segment[1:]                                          # Delta_3 ..
    if any(s > SMALL and not TILE_LO <= s <= TILE_HI for s in tail) or \
       any(b > a > 0 for a, b in zip(tail, tail[1:]) if a != 8192 or b != 8192):
        cls = "R-other"
    elif all(s == 8192 for s in tail if s != 0) and tail.count(0) <= 1:
        cls = "R-linear"
    else:
        run = best = 0
        for s in tail:
            run = run + 1 if s == 0 else 0
            best = max(best, run)
        cls = "R-saturating" if best >= 5 else "unclassified"
    return {"shape": shape, "class": cls, "segment": segment}


def steps_of(report: dict) -> list[int]:
    entry = next(e for e in report["entries"] if e["path"].endswith("one-cell-a1.ods"))
    begins = [c.get("openBegin") for c in entry["reopen"]["cycles"]]
    return [b - a for a, b in zip(begins, begins[1:])]


def selftest() -> int:
    flat = [9_736_192, 4_194_304] + [0] * 17
    cases = {
        "slack@2 is uninformative": (flat, "uninformative"),
        "tight, 8 KB every step": ([9_736_192, 28_672] + [8192] * 17, "R-linear"),
        "tight, 8 KB with one 0": ([9_736_192, 28_672] + [8192] * 8 + [0] + [8192] * 8, "R-linear"),
        "tight, settles to 0": ([9_736_192, 28_672, 8192, 8192] + [0] * 15, "R-saturating"),
        "tight, a 1 MB step": ([9_736_192, 28_672] + [8192] * 8 + [1_000_000] + [8192] * 8, "R-other"),
        "tight, growing steps": ([9_736_192, 28_672] + [8192 * n for n in range(1, 18)], "R-other"),
        "slack@6 is short": ([9_736_192, 28_672, 8192, 8192, 8192, 4_186_112] + [0] * 13, "short"),
    }
    ok = True
    for name, (steps, want) in cases.items():
        got = classify_steps(steps)["class"]
        ok &= got == want
        print(f"{'PASS' if got == want else 'FAIL'} {name}: {got} (want {want})")
    print("selftest PASS" if ok else "selftest FAIL")
    return 0 if ok else 1


def main(paths: list[str]) -> int:
    if paths == ["--selftest"]:
        return selftest()
    summary: dict[str, dict] = {}
    for path in sorted(paths):
        report = json.load(open(path, encoding="utf-8"))
        result = classify_steps(steps_of(report))
        profile = report["profile"]
        s = summary.setdefault(profile, {"runs": 0, "counting": 0, "classes": {}})
        s["runs"] += 1
        s["counting"] += result["class"] not in ("uninformative", "short")
        s["classes"][result["class"]] = s["classes"].get(result["class"], 0) + 1
        print(f"{profile} {path.rsplit('/', 1)[-1]} {result['shape']} {result['class']} steps={steps_of(report)}")
    for profile, s in summary.items():
        yield_note = "" if s["counting"] >= 2 else "  (yield rule: fewer than two counting segments -- record and stop)"
        print(f"SUMMARY {profile}: {s['runs']} runs, {s['counting']} counting segments, {s['classes']}{yield_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
