#!/usr/bin/env python3
"""W2 of task 2026-10-14k: every `定位游標` latency record of a succeeded click, per browser, from a 129-B round.

Usage: extract_click_latency.py ROUND_DIR [REFERENCE_ROUND_DIR ...]

Reads ROUND_DIR/arms-{chrome,firefox}.jsonl (read-only).  For each arm that has a `timing.latencyRecords` list, each
record is [ms_since_keydown, page_latency_text].  A `定位游標` record is the page's own latency pill for the caret
placement the arrow-key path makes.  It is a *succeeded* click when the text reads `定位游標 <n> ms`; a failed click
reads `定位游標 失敗` and is counted apart (it is not judged by the clause, the toast clauses judge it).
The measured value is the first element (ms from the keydown to the record, one decimal) -- the same quantity the
task's reference numbers (v67: Chrome 26.1-31.7 median 27.95, Firefox 27.8-32.0 median 29.15) were taken from; the
integer `<n>` in the text is printed beside it as a cross-check.

Clause (task 10-14k, criterion C2 added before the run): in each browser every succeeded record is < 100 ms and the
median is <= 40 ms.  The script exits 1 if the first ROUND_DIR does not satisfy it, and also if it finds nothing to
judge (a clause over zero records would be vacuously true).  References are printed, not judged.
"""
import json
import re
import statistics
import sys
from pathlib import Path

PREFIX = "定位游標"
OK = re.compile(r"^定位游標 (\d+) ms$")
MAX_MS = 100.0
MAX_MEDIAN_MS = 40.0
EXPECTED_SUCCEEDED = 54  # the 54 `m4` click-and-move arms of 129-B, one click each


def collect(round_dir: Path, browser: str) -> dict:
    ok, failed, other = [], [], []
    arms_with_records = arms_total = 0
    kinds = {}
    for line in (round_dir / f"arms-{browser}.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        arm = json.loads(line)
        arms_total += 1
        records = (arm.get("timing") or {}).get("latencyRecords") or []
        mine = [r for r in records if (r[1] or "").startswith(PREFIX)]
        if mine:
            arms_with_records += 1
        for ms, text in mine:
            m = OK.match(text)
            if m:
                ok.append((ms, int(m.group(1)), arm["arm"]))
                kinds[arm.get("kind")] = kinds.get(arm.get("kind"), 0) + 1
            elif "失敗" in text:
                failed.append((ms, text, arm["arm"]))
            else:
                other.append((ms, text, arm["arm"]))
    return dict(ok=ok, failed=failed, other=other, arms_total=arms_total, arms_with_records=arms_with_records,
                kinds=kinds)


def summary(c: dict) -> dict:
    v = [x[0] for x in c["ok"]]
    t = [x[1] for x in c["ok"]]
    if not v:
        return dict(count=0, over_100=[], median=None)
    slow = sorted(c["ok"], key=lambda x: -x[0])[:3]
    return dict(count=len(v), min=min(v), max=max(v), median=statistics.median(v),
                text_min=min(t), text_max=max(t), text_median=statistics.median(t),
                over_100=[x[2] for x in c["ok"] if x[0] >= MAX_MS], slowest=[(x[0], x[2]) for x in slow])


def main(argv: list) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    main_round = Path(argv[1])
    verdict_ok = True
    for rnd in [main_round] + [Path(a) for a in argv[2:]]:
        judged = rnd == main_round
        print(f"## {rnd.name}{'  (judged)' if judged else '  (reference, not judged)'}")
        for browser in ("chrome", "firefox"):
            c = collect(rnd, browser)
            s = summary(c)
            print(f"{browser}: arms in file {c['arms_total']}, arms with a {PREFIX} record {c['arms_with_records']}, "
                  f"succeeded {s['count']} (by kind {c['kinds']}), failed {len(c['failed'])}, unrecognised {len(c['other'])}")
            if s["count"]:
                print(f"  record (ms since keydown): count {s['count']}  min {s['min']}  max {s['max']}  median {s['median']}")
                print(f"  page text (integer ms):    min {s['text_min']}  max {s['text_max']}  median {s['text_median']}")
                print(f"  slowest three: {s['slowest']}")
            for f in c["failed"]:
                print(f"  failed record: {f}")
            for f in c["other"]:
                print(f"  unrecognised record: {f}")
            if judged:
                good = (s["count"] > 0 and not s["over_100"] and s["median"] <= MAX_MEDIAN_MS)  # zero records: FAIL
                complete = s["count"] == EXPECTED_SUCCEEDED
                print(f"  clause: all < {MAX_MS:.0f} ms: {not s['over_100'] and s['count'] > 0}; "
                      f"median <= {MAX_MEDIAN_MS:.0f} ms: {s['count'] > 0 and s['median'] <= MAX_MEDIAN_MS}; "
                      f"count == {EXPECTED_SUCCEEDED}: {complete}  ->  {'PASS' if good else 'FAIL'}")
                verdict_ok = verdict_ok and good
                if c["failed"] or c["other"] or not complete:
                    print(f"  NOTE: {len(c['failed'])} failed and {len(c['other'])} unrecognised {PREFIX} records, "
                          f"{s['count']} of {EXPECTED_SUCCEEDED} expected clicks succeeded; the clause above judges the "
                          f"succeeded ones only, the failed ones belong to the toast and toolbar clauses")
        print()
    print(f"W2 {'PASS' if verdict_ok else 'FAIL'}")
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
