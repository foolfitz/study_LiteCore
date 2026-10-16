#!/usr/bin/env python3
"""SPEC-M3-link-batch §17.4's hand reading, printed from the raw report: for every run of a production-UI report, the
busy spans of at least 1,000 ms (busy until the next sample that is not busy), with rev and gen at both ends.

Not a judge: it prints facts and applies no rule.  The §17.4 rule is read off its output by the reader: every counted
Rbs/Rdel run needs one span >= 2,000 ms whose rev is equal at its start and end; a run without one is NOT_ESTABLISHED
for that arm.  The span function is witness-c-0.2.23/read_witness.py's busy_intervals, copied unchanged.
Run: python3 -I r_arm_spans.py REPORT.json [REPORT.json ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def busy_intervals(timeline: list[dict], at_least_ms: int = 1000) -> list[dict]:
    """Spans where state was busy until the next sample that was ready, longer than at_least_ms."""
    out = []
    for i, s in enumerate(timeline[:-1]):
        if s["state"] != "busy":
            continue
        nxt = next((x for x in timeline[i + 1:] if x["state"] != "busy"), None)
        if nxt and nxt["t"] - s["t"] >= at_least_ms:
            out.append({"from": s["t"], "to": nxt["t"], "ms": nxt["t"] - s["t"], "rev": f"{s['rev']}->{nxt['rev']}",
                        "gen": f"{s['gen']}->{nxt['gen']}", "endState": nxt["state"]})
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for arg in sys.argv[1:]:
        report = json.loads(Path(arg).read_text())
        st = report["static"]
        print(f"report {arg}: runner {report.get('runnerSha256', '')[:16]} counted {report.get('counted')} "
              f"servedPage {st['servedPage'][:16]} buildId {st['buildId']} runs {len(report['runs'])}")
        seen: dict[tuple[str, str], int] = {}
        for run in report["runs"]:
            key = (run["arm"], run["browser"])
            seen[key] = seen.get(key, 0) + 1
            tl = run.get("timeline") or []
            spans = busy_intervals(tl)
            longest = max((s["ms"] for s in spans), default=None)
            print(f"  {run['arm']:5} {run['browser']:8} #{seen[key]}  samples {len(tl):3}  "
                  f"rev {tl[0]['rev'] if tl else None}..{tl[-1]['rev'] if tl else None}  busy>=1s {spans}  longest {longest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
