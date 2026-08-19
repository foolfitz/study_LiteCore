#!/usr/bin/env python3
"""How tall a canvas can this browser actually paint?

The long-document cell needs this number and must not cite it from the web.
32,767 is the figure everyone repeats; whether THIS build of THIS browser on
THIS machine agrees is a measurement, and the prediction file says so.

"Usable" is not "the assignment was accepted".  A canvas can take its width and
height, hand back a 2d context, and then silently paint nothing -- which is the
failure mode that matters here, because it is exactly what the product would do
to a user with a long document.  So each trial paints the BOTTOM-most pixel and
reads it back: the last row is the first thing an over-tall canvas loses.

Bisection, not a scan: the answer is monotone (if a canvas of height H works,
every smaller one does), and a scan over five orders of magnitude would take
longer than the browser it is measuring.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page                      # noqa: E402
from run_browser_probe import (ChromeSession, FirefoxSession,   # noqa: E402
                               free_port)
from run_e2_c_page_smoke import navigate                        # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

TRIAL = """(() => {
const canvas = document.createElement('canvas');
canvas.width = ARG_W;
canvas.height = ARG_H;
if (canvas.width !== ARG_W || canvas.height !== ARG_H)
  return { usable: false, why: 'dimensions refused',
           width: canvas.width, height: canvas.height };
let context = null;
try { context = canvas.getContext('2d'); }
catch (error) { return { usable: false, why: 'getContext threw: ' + error.name }; }
if (!context) return { usable: false, why: 'no 2d context' };
try {
  context.fillStyle = '#000000';
  // The BOTTOM row: an over-tall canvas keeps its dimensions and loses its
  // pixels, and it loses the far end first.
  context.fillRect(0, ARG_H - 1, 1, 1);
  const data = context.getImageData(0, ARG_H - 1, 1, 1).data;
  return { usable: data[3] > 0,
           why: data[3] > 0 ? '' : 'the bottom pixel did not take',
           alpha: data[3] };
} catch (error) {
  return { usable: false, why: 'paint threw: ' + error.name };
}
})()"""


def trial(session, width: int, height: int) -> dict:
    result = evaluate(session, TRIAL.replace("ARG_W", str(width))
                      .replace("ARG_H", str(height)))
    return result or {"usable": False, "why": "the browser did not answer"}


def tallest(session, width: int, ceiling: int = 200000) -> dict:
    """The tallest usable canvas at this width, and the first failing height."""
    if not trial(session, width, 1)["usable"]:
        return {"width": width, "tallest": None,
                "why": "a canvas one pixel tall is already unusable"}
    low, high = 1, ceiling
    if trial(session, width, ceiling)["usable"]:
        return {"width": width, "tallest": ceiling, "firstFailure": None,
                "why": f"nothing failed below {ceiling}"}
    first_failure = trial(session, width, ceiling)
    while high - low > 1:
        middle = (low + high) // 2
        outcome = trial(session, width, middle)
        if outcome["usable"]:
            low = middle
        else:
            high = middle
            first_failure = outcome
    return {"width": width, "tallest": low, "firstFailureHeight": high,
            "firstFailureWhy": first_failure.get("why"),
            "area": width * low}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox", "both"),
                        default="both")
    parser.add_argument("--widths", default="725,1450,2175,2400",
                        help="the backing widths layoutCanvas can produce")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    widths = [int(value) for value in args.widths.split(",")]
    browsers = (["chrome", "firefox"] if args.browser == "both"
                else [args.browser])

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(PROJECT / "dist")],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report: dict = {"schemaVersion": 1, "release": "canvas-limit",
                    "widths": widths, "browsers": {}}
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        for name in browsers:
            session = None
            try:
                session = (ChromeSession("cold") if name == "chrome"
                           else FirefoxSession("cold"))
                # Any document will do; the canvases are created detached.
                navigate(session, base)
                time.sleep(2.0)
                entry = {"version": getattr(session, "version", "unknown"),
                         "devicePixelRatio": evaluate(
                             session, "(() => globalThis.devicePixelRatio)()"),
                         "byWidth": []}
                for width in widths:
                    measured = tallest(session, width)
                    entry["byWidth"].append(measured)
                    print(f"{name} {width}px wide -> tallest usable "
                          f"{measured.get('tallest')} "
                          f"(first failure {measured.get('firstFailureHeight')}: "
                          f"{measured.get('firstFailureWhy')})")
                report["browsers"][name] = entry
            except Exception as error:               # noqa: BLE001 -- reported
                report["browsers"][name] = {"error": f"{type(error).__name__}: {error}"}
                print(f"{name}: {type(error).__name__}: {error}")
            finally:
                if session is not None:
                    session.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False,
                                             indent=1) + "\n",
                                  encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
