#!/usr/bin/env python3
"""122-B reader (spec SPEC-M3-production-ui §15.8; fable's fourth ruling, condition 2).

Reads the six existing reports -- per browser `owner-gap80`, `owner-gap200`, `boundaries-gap200` -- and judges
them; it opens no browser.  Per report: bound to the candidate page and the counted probe (the diagnostic
lazy-shim reports cannot count), and to the slot's document / gap / chars.  Per browser:

  (a)  owner gap 80: every key's revisionMs < 2 x gap                       (per instance, §15.8)
  (b)  owner gap 80: median revisionMs < gap                                (aggregate over rows, §15.8)
  on-screen median < 70 (Chrome) / < 90 (Firefox), both gaps               (§15.2, §15.6)
  on-screen max < 150, both gaps                                            (§15.2, §15.6; ruling cond. 2)
  every key seen on screen and committed (n == chars)                       (otherwise median/max are undefined)
  (ii) allCurrentAfterLastKeyMs is not None, all three reports              (§15.6; ruling cond. 2)
  boundaries gap 200: median revisionMs <= 10 ms                            (§15.2)

Recorded, not gated (§15.8): per-key backlog b_i = max(0, revisionMs[i-1] - (key_i - key_{i-1})), the
first-five / last-five medians of revisionMs, and the (ii) times.

Median = the probe's own definition, sorted(xs)[len(xs) // 2] (the upper median for an even count), so the
numbers match each report's `summary` and the spec.  Everything gated is computed from `rows`, except (ii),
which the probe computes from `raw.blits` into `allCurrentAfterLastKeyMs`.

Exit 0 PASS (both browsers, every report bound, every cell met); 1 FAIL (bound, a cell missed);
2 REFUSED (a report missing, unreadable, or bound to something else) -- cells are still printed.

  judge.py [--dir DIR] [--report BROWSER:SLOT=PATH ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Re-pinned 2026-10-13 to the final page of finding 132 (SPEC-M3-held-key §5.3).  The previous pin, the C′ page, was
# 8909564eb2316afa6de7868a08b61d27219fabdf49f37326fee0dda2977bd401 (findings/evidence/c-prime/c2/ ran on it).
PAGE = "abe93f4575c7797db97462f1f0e3a71cf5fc4063205cd6d5877093ca1c248fcf"
RUNNER = "dbad93c0dcf27fbf"   # the probe writes the first 16 hex digits of its own sha256
BROWSERS = ("chrome", "firefox")
SLOTS = {  # slot: (document, gap, chars)
    "owner-gap80": ("owner", 80, 20),
    "owner-gap200": ("owner", 200, 10),
    "boundaries-gap200": ("boundaries", 200, 10),
}
ON_SCREEN_MEDIAN = {"chrome": 70.0, "firefox": 90.0}
ON_SCREEN_MAX = 150.0
BOUNDARIES_COMMIT_MEDIAN = 10.0


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--report", action="append", default=[], metavar="BROWSER:SLOT=PATH")
    a = ap.parse_args()
    paths = {(b, s): a.dir / f"p-candidate-{b}-{s}.json" for b in BROWSERS for s in SLOTS}
    for override in a.report:
        key, _, path = override.partition("=")
        b, _, s = key.partition(":")
        if (b, s) not in paths or not path:
            print(f"bad --report {override!r}")
            return 2
        paths[(b, s)] = Path(path)

    refused, failed = [], []

    def line(ok, browser, what, detail):
        print(f"  {'PASS' if ok else 'FAIL'}  {browser:7s} {what}: {detail}")
        if not ok:
            failed.append(f"{browser} {what}")

    for browser in BROWSERS:
        print(f"== {browser}")
        reports = {}
        for slot, (document, gap, chars) in SLOTS.items():
            path = paths[(browser, slot)]
            try:
                report = json.loads(path.read_text())
            except (OSError, ValueError) as error:
                print(f"  REFUSED {browser:7s} {slot}: cannot read {path}: {error}")
                refused.append(f"{browser} {slot}")
                continue
            binding = {"page": PAGE, "runner": RUNNER, "browser": browser,
                       "document": document, "gap": gap, "chars": chars}
            wrong = {k: report.get(k) for k, v in binding.items() if report.get(k) != v}
            if wrong:
                print(f"  REFUSED {browser:7s} {slot}: {path.name} is bound to {wrong}, not {binding}")
                refused.append(f"{browser} {slot}")
            reports[slot] = report
            rows = report.get("rows") or []
            commits = [r.get("revisionMs") for r in rows]
            screens = [r.get("onScreenMs") for r in rows]
            line(len(rows) == chars and None not in commits, browser, f"{slot} every key committed",
                 f"{sum(c is not None for c in commits)} of {chars}")
            line(len(rows) == chars and None not in screens, browser, f"{slot} every key on screen",
                 f"{sum(s is not None for s in screens)} of {chars}")
            commits = [c for c in commits if c is not None]
            screens = [s for s in screens if s is not None]
            if slot.startswith("owner") and screens:
                m, top = median(screens), max(screens)
                line(m < ON_SCREEN_MEDIAN[browser], browser, f"{slot} on-screen median",
                     f"{m} (needs < {ON_SCREEN_MEDIAN[browser]:g})")
                line(top < ON_SCREEN_MAX, browser, f"{slot} on-screen max", f"{top} (needs < {ON_SCREEN_MAX:g})")
            if slot == "owner-gap80" and commits:
                top, m = max(commits), median(commits)
                line(top < 2 * gap, browser, f"{slot} (a) every key's commit < 2 x gap",
                     f"max {top} (needs < {2 * gap})" + ("" if top < 2 * gap else
                     f"; keys at or over: {[r['i'] for r in rows if (r.get('revisionMs') or 0) >= 2 * gap]}"))
                line(m < gap, browser, f"{slot} (b) median commit < gap", f"{m} (needs < {gap})")
            if slot == "boundaries-gap200" and commits:
                m = median(commits)
                line(m <= BOUNDARIES_COMMIT_MEDIAN, browser, f"{slot} commit median",
                     f"{m} (needs <= {BOUNDARIES_COMMIT_MEDIAN:g})")
            current = report.get("allCurrentAfterLastKeyMs")
            line(current is not None, browser, f"{slot} (ii) every band current after the last key",
                 f"{current} ms (the time is recorded, not gated)" if current is not None else "None")
            canvas = (report.get("raw") or {}).get("canvasHeight")
            print(f"        {browser:7s} {slot}: canvas rows {canvas} (width unrecorded)")
        gap80 = reports.get("owner-gap80")
        if gap80:
            rows = gap80.get("rows") or []
            commits = [r.get("revisionMs") for r in rows]
            if rows and None not in commits:
                backlog = [0.0] + [round(max(0.0, rows[i - 1]["revisionMs"] - (rows[i]["key"] - rows[i - 1]["key"])), 1)
                                   for i in range(1, len(rows))]
                print(f"  RECORD  {browser:7s} owner-gap80 backlog b_i: {backlog}")
                print(f"  RECORD  {browser:7s} owner-gap80 first-five / last-five median commit: "
                      f"{median(commits[:5])} / {median(commits[-5:])}")

    if refused:
        print(f"REFUSED: {', '.join(refused)}" + (f"; also FAIL: {', '.join(failed)}" if failed else ""))
        return 2
    if failed:
        print(f"FAIL: {', '.join(failed)}")
        return 1
    print("PASS: both browsers, every cell")
    return 0


if __name__ == "__main__":
    sys.exit(main())
