#!/usr/bin/env python3
"""Task 10-14q: read N1 off probe_10_14q.py reports.  The clauses are the brief's, pinned
before any run; numbers come from the reports' own fields.

  python3 -I judge_n1.py --dir DIR [--dir DIR ...] [--red-check DIR]

N1 (no host, the dist mirror with the 144 page), per report, both browsers:
  burst-1s at the document start:   (a) exactly 1 engine delete request; (b) ready < 2,500 ms.
  burst-1s-in-text (unflagged):      (c) every press deletes: 18 requests, 18 verified deletes.
  hold-2s-in-text (flagged repeats): (d) deletes after the key-up <= 2;
                                     (e) `beforeinput` events == verified deletes (132-B's clause (c):
                                         no synthetic re-dispatch, no press lost);
                                     (f) the engine was kept busy: >= 20 deletes during the hold.
--red-check DIR: the same clauses on a report made on the 0.2.21 page, which must fail (d) and (e).
Exit 1 on any red (or a red check that is not red).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def judge(report: dict, lines: list[str]) -> bool:
    ok = True
    for run in report["runs"]:
        s = run.get("summary") or {}
        tag = f"N1 {report['browser']} {run['arm']}"
        if run.get("fatal"):
            lines.append(f"{tag}: FAIL fatal {run['fatal'].strip().splitlines()[-1]}")
            ok = False
            continue
        responses = [x for x in s.get("editorResponses", []) if (x.get("op") or "").startswith("editor")]
        requests = [x for x in s.get("nonPaintRequests", []) if (x.get("op") or "").startswith("editor")]
        ready = s.get("readyAgainMs") or []
        if run["arm"] == "burst-1s":
            a = len(requests) == 1 and len(responses) == 1
            b = bool(ready) and ready[-1] < 2500
            lines.append(f"{tag}: (a) requests {len(requests)} -> {'PASS' if a else 'FAIL'}; (b) ready at {ready} ms -> {'PASS' if b else 'FAIL'}; "
                         f"generations {s.get('generations')} toasts {s.get('toasts')}")
            ok &= a and b
        elif run["arm"] == "burst-1s-in-text":
            c = len(requests) == s["keydowns"] and s.get("verifiedDeletes") == s["keydowns"]
            lines.append(f"{tag}: (c) keydowns {s['keydowns']} requests {len(requests)} verified deletes {s.get('verifiedDeletes')} -> {'PASS' if c else 'FAIL'}")
            ok &= c
        elif run["arm"] == "hold-2s-in-text":
            d = s.get("deletesAfterRelease") is not None and s["deletesAfterRelease"] <= 2
            e = s.get("beforeinputs") == s.get("verifiedDeletes")
            during = (s.get("verifiedDeletes") or 0) - (s.get("deletesAfterRelease") or 0)
            f = during >= 20
            lines.append(f"{tag}: keydowns {s['keydowns']} (flagged {s.get('repeatsFlagged')}) release at {s.get('releaseMs')} ms; "
                         f"(d) deletes after release {s.get('deletesAfterRelease')} (last +{s.get('lastDeleteAfterReleaseMs')} ms) -> {'PASS' if d else 'FAIL'}; "
                         f"(e) beforeinputs {s.get('beforeinputs')} == deletes {s.get('verifiedDeletes')} -> {'PASS' if e else 'FAIL'}; "
                         f"(f) {during} deletes during the hold -> {'PASS' if f else 'FAIL'}; generations {s.get('generations')} toasts {s.get('toasts')}")
            ok &= d and e and f
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path, action="append", default=[])
    parser.add_argument("--red-check", type=Path, default=None)
    args = parser.parse_args()
    lines: list[str] = []
    ok = True
    for d in args.dir:
        for path in sorted(d.glob("report-*.json")):
            ok &= judge(json.loads(path.read_text()), lines)
    if args.red_check is not None:
        red_lines: list[str] = []
        red_ok = True
        for path in sorted(args.red_check.glob("report-*.json")):
            red_ok &= judge(json.loads(path.read_text()), red_lines)
        print("\n".join("RED-CHECK " + line for line in red_lines))
        print(f"RED-CHECK verdict: red={not red_ok} -> {'self-test PASS' if not red_ok else 'self-test FAIL'}")
        if red_ok:
            ok = False
    print("\n".join(lines))
    print("VERDICT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
