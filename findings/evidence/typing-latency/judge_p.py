#!/usr/bin/env python3
"""Release P reader: P1 and 123-B (spec SPEC-M3-production-ui §16.2; fable's fifth ruling, A1).

Reads four existing reports written by r2-blit-bytes/blit_bytes_probe.py -- per browser `p1` and `123b` -- and
judges them; it opens no browser.  Per report: bound to the page named by --page (required: the candidate page
does not exist when this is written, and the red cases run on the shipped one), to the wrapper and the probe it
wraps (the report's `runner` prefix), to page choice `current`, no `--skip-stale`, and to the slot's document /
gap / chars / requested ratio / requested window, and the ratio the page actually saw (`raw.dpr`).

  P1   (ratio 1, owner, gap 600 x 10)  for EVERY typed key: the bytes the page passed to putImageData from that
       key's keydown to the next one's (the last: to the wrapper's final snapshot), new bands' first blits
       excluded, are <= 2 % of the canvas's bytes (width x height x 4); and n == chars.  The wrapper counts a
       7-argument putImageData as its dirty rectangle only, a 3-argument one as the whole image; "first blit" =
       the first putImageData of an ImageData (the wrapper's `fresh`).  Computed from raw.r2.keys / raw.r2.final,
       not from the wrapper's own r2PerKey.
  123-B (ratio 2, window 800x1000 Chrome / 797x1000 Firefox (§16.8), owner, gap 600 x 3)
       no toast containing TILE_NOT_PAINTED in raw.r2.toasts, which must hold at least one toast (the recorder
       ran); allCurrentAfterLastKeyMs is not None; a new image blitted after the last key whose rows reach the
       canvas bottom (raw.blits: [t, y, rows, revision]); n == chars.

Recorded, not gated: per key stale bytes and calls, dirty-rect calls, clearRect calls and bytes, the canvas size,
the last band's rows as blitted, and the toasts.

Exit 0 PASS (both browsers, every report bound, every cell met); 1 FAIL (bound, a cell missed);
2 REFUSED (a report missing, unreadable, or bound to something else) -- cells are still printed.

  judge_p.py --page SHA256 [--dir DIR] [--prefix PREFIX] [--report BROWSER:SLOT=PATH ...]
  default report paths: DIR/PREFIX-BROWSER-SLOT.json, DIR = ./p-release, PREFIX = candidate
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# The wrapper writes "DIAGNOSTIC r2-blit-bytes/blit_bytes_probe.py <its sha256[:16]> over probe <probe sha256[:16]>"
# ("DIAGNOSTIC" is its historical first word; spec §16.2 makes it P1's and 123-B's instrument).
RUNNER = "DIAGNOSTIC r2-blit-bytes/blit_bytes_probe.py 3dad37cbb03a769c over probe dbad93c0dcf27fbf "
BROWSERS = ("chrome", "firefox")
SLOTS = {  # slot: (document, gap, chars, dprRequested, windowRequested by browser, devicePixelRatio seen)
    "p1": ("owner", 600, 10, None, {"chrome": None, "firefox": None}, 1),
    # §16.8: the window that gives both browsers the canvas 1490 x 36,847 (a 19-row last band on the shipped page).
    "123b": ("owner", 600, 3, 2.0, {"chrome": [800, 1000], "firefox": [797, 1000]}, 2),
}
P1_MAX_FRACTION = 0.02


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--page", required=True, help="sha256 of the page the reports must have been served")
    ap.add_argument("--dir", type=Path, default=Path(__file__).resolve().parent / "p-release")
    ap.add_argument("--prefix", default="candidate")
    ap.add_argument("--report", action="append", default=[], metavar="BROWSER:SLOT=PATH")
    a = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{64}", a.page):
        print(f"--page must be a full sha256, not {a.page!r}")
        return 2
    paths = {(b, s): a.dir / f"{a.prefix}-{b}-{s}.json" for b in BROWSERS for s in SLOTS}
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
        for slot, (document, gap, chars, dpr_requested, windows, dpr_seen) in SLOTS.items():
            window_requested = windows[browser]
            path = paths[(browser, slot)]
            try:
                report = json.loads(path.read_text())
            except (OSError, ValueError) as error:
                print(f"  REFUSED {browser:7s} {slot}: cannot read {path}: {error}")
                refused.append(f"{browser} {slot}")
                continue
            raw = report.get("raw") or {}
            r2 = raw.get("r2") or {}
            binding = {"page": a.page, "browser": browser, "document": document, "gap": gap, "chars": chars,
                       "pageChoice": "current", "skipStale": False, "dprRequested": dpr_requested,
                       "windowRequested": window_requested}
            wrong = {k: report.get(k) for k, v in binding.items() if report.get(k) != v}
            runner = report.get("runner")
            if not (isinstance(runner, str) and runner.startswith(RUNNER)):
                wrong["runner"] = runner if not isinstance(runner, str) else runner[:len(RUNNER) + 8]
            if raw.get("dpr") != dpr_seen:
                wrong["raw.dpr"] = raw.get("dpr")
            if wrong:
                print(f"  REFUSED {browser:7s} {slot}: {path.name} is bound to {wrong}, not "
                      f"{ {**binding, 'runner': RUNNER + '...', 'raw.dpr': dpr_seen} }")
                refused.append(f"{browser} {slot}")
            width, height = raw.get("canvasWidth") or 0, raw.get("canvasHeight") or 0
            canvas_bytes = width * height * 4
            print(f"        {browser:7s} {slot}: canvas {width} x {height} ({canvas_bytes} bytes)")

            if slot == "p1":
                letters = [k for k in r2.get("keys") or [] if isinstance(k[0], str) and len(k[0]) == 1]
                final = r2.get("final")
                fractions = []
                for i, (key, _t, counters) in enumerate(letters):
                    after = letters[i + 1][2] if i + 1 < len(letters) else final
                    if not after or not canvas_bytes:
                        fractions.append(None)
                        continue
                    stale = after["staleBytes"] - counters["staleBytes"]
                    fractions.append(stale / canvas_bytes)
                    print(f"  RECORD  {browser:7s} p1 key {i} {key!r}: stale bytes {stale}"
                          f" ({stale / canvas_bytes:.6%} of the canvas), stale calls"
                          f" {after['staleCalls'] - counters['staleCalls']}, dirty-rect calls"
                          f" {after.get('dirtyCalls', 0) - counters.get('dirtyCalls', 0)}, clearRect calls"
                          f" {after.get('clearCalls', 0) - counters.get('clearCalls', 0)}"
                          f" ({after.get('clearBytes', 0) - counters.get('clearBytes', 0)} bytes), new-band blits"
                          f" {after['freshCalls'] - counters['freshCalls']}")
                line(len(letters) == chars and None not in fractions, browser, "p1 every key typed and measured",
                     f"{sum(f is not None for f in fractions)} of {chars} (keys seen {len(letters)})")
                measured = [f for f in fractions if f is not None]
                if measured:
                    over = [i for i, f in enumerate(fractions) if f is not None and f > P1_MAX_FRACTION]
                    line(not over, browser, "p1 every key's re-blitted bytes <= 2 % of the canvas",
                         f"max {max(measured):.6%}" + (f"; keys over: {over}" if over else ""))

            if slot == "123b":
                keys = [t for k, t in raw.get("keys") or [] if isinstance(k, str) and len(k) == 1]
                line(len(keys) == chars, browser, "123b every key typed", f"{len(keys)} of {chars}")
                toasts = r2.get("toasts")
                if not isinstance(toasts, list):
                    toasts = None
                for t, text in toasts or []:
                    print(f"  RECORD  {browser:7s} 123b toast at {t} ms: {text}")
                bad = [text for _t, text in toasts or [] if "TILE_NOT_PAINTED" in str(text)]
                line(bool(toasts) and not bad, browser, "123b no TILE_NOT_PAINTED toast",
                     "no toast recorded (recorder did not run)" if not toasts else
                     f"{len(bad)} of {len(toasts)} toasts" if bad else f"0 of {len(toasts)} toasts")
                current = report.get("allCurrentAfterLastKeyMs")
                line(current is not None, browser, "123b every band current after the last key",
                     f"{current} ms (the time is recorded, not gated)" if current is not None else "None")
                blits = raw.get("blits") or []
                last_key = keys[-1] if keys else None
                bottom = [(t, y, rows) for t, y, rows, _rev in blits
                          if last_key is not None and height and t >= last_key and y + rows >= height]
                line(bool(bottom), browser, "123b the last band blitted after the last key",
                     f"at y {bottom[0][1]}, {bottom[0][2]} rows, {round(bottom[0][0] - last_key, 1)} ms after"
                     if bottom else "never")
                if blits and height:
                    last = max(blits, key=lambda b: b[1])
                    print(f"  RECORD  {browser:7s} 123b lowest band ever blitted new: y {last[1]}, {last[2]} rows"
                          f" (canvas bottom {height})")

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
