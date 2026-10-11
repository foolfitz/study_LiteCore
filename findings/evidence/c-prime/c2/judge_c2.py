#!/usr/bin/env python3
"""C2 reader (spec SPEC-M3-production-ui §17.4 C2): ratio 2 wide, both browsers, on the C′ page.

A copy of ../../typing-latency/judge_p2.py (the P2 reader, itself judge.py with the page constant changed), made
2026-10-11.  Changed, every hard-coded expectation re-read (rule ee): the slots are owner gap 80 and gap 200 only;
the binding adds dprRequested 2.0 and windowRequested [1400, 1000] and the runner is the non-diagnostic sizing
wrapper `tools/probe_typing_latency_view.py` over the counted probe; (ii) is RECORDED, not gated, because C3
replaces §15.6 (ii) on the C′ page; the boundaries commit cell is dropped (a ratio-1 cell, P2's).  PAGE is a
placeholder until the C′ page exists, so every report is REFUSED until then.  --page / --runner / --window /
--slots override the binding for red-case runs on older reports only; each override is printed.

The P2 reader's notes follow; they describe the cells this copy kept.

122-B reader (spec SPEC-M3-production-ui §15.8; fable's fourth ruling, condition 2).

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

PAGE = "8909564eb2316afa6de7868a08b61d27219fabdf49f37326fee0dda2977bd401"
RUNNER = "probe_typing_latency_view.py 1412e4c863de6fcb over probe dbad93c0dcf27fbf"
DPR = 2.0
WINDOW = [1400, 1000]
BROWSERS = ("chrome", "firefox")
SLOTS = {  # slot: (document, gap, chars)
    "owner-gap80": ("owner", 80, 20),
    "owner-gap200": ("owner", 200, 10),
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
    ap.add_argument("--page", default=PAGE)
    ap.add_argument("--runner", default=RUNNER)
    ap.add_argument("--window", default=None, help="WxH or none (red cases on ratio-2-narrow reports)")
    ap.add_argument("--slots", default=",".join(SLOTS))
    ap.add_argument("--browsers", default=",".join(BROWSERS), help="red-case runs on one-browser reports only")
    a = ap.parse_args()
    window = WINDOW if a.window is None else (None if a.window == "none" else [int(v) for v in a.window.split("x")])
    # Every override is said, and a PASS under one says it is not C2's verdict (codex review 2026-10-11: a
    # --slots that dropped the gap-80 cells printed "PASS: both browsers, every cell").
    overridden = []
    for name, value, default in (("page", a.page, PAGE), ("runner", a.runner, RUNNER), ("window", window, WINDOW),
                                 ("slots", a.slots, ",".join(SLOTS)), ("browsers", a.browsers, ",".join(BROWSERS))):
        if value != default:
            overridden.append(name)
            print(f"OVERRIDE {name} = {value!r} (red-case run; the counted binding is {default!r})")
    slots = {s: SLOTS[s] for s in a.slots.split(",")}
    browsers = tuple(a.browsers.split(","))
    paths = {(b, s): a.dir / f"c2-candidate-{b}-{s}.json" for b in BROWSERS for s in slots}
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

    for browser in browsers:
        print(f"== {browser}")
        reports = {}
        for slot, (document, gap, chars) in slots.items():
            path = paths[(browser, slot)]
            try:
                report = json.loads(path.read_text())
            except (OSError, ValueError) as error:
                print(f"  REFUSED {browser:7s} {slot}: cannot read {path}: {error}")
                refused.append(f"{browser} {slot}")
                continue
            binding = {"page": a.page, "runner": a.runner, "browser": browser,
                       "document": document, "gap": gap, "chars": chars,
                       "dprRequested": DPR, "windowRequested": window}
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
            current = report.get("allCurrentAfterLastKeyMs")
            print(f"  RECORD  {browser:7s} {slot} (ii) whole canvas current after the last key: {current} ms (C3 gates this on C′)")
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
    if overridden:
        print(f"PASS under OVERRIDE ({', '.join(overridden)}): every cell judged passed -- not C2's verdict")
        return 0
    print("PASS: both browsers, every cell")
    return 0


if __name__ == "__main__":
    sys.exit(main())
