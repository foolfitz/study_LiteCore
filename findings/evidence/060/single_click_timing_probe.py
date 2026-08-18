#!/usr/bin/env python3
"""After the FIRST click, is the caret drawn late, or not at all?

The clean-vs-no-caret isolation showed an 8-row, 1px stroke after the second
click and nothing after the first. Two candidates:

  timing    the caret is painted, just later than the 1.0 s the check waits
  ordering  the first gesture's caret is never painted; the next paint draws it

This samples the same band repeatedly after ONE click, with no second click, so
the two are separable: under `timing` the stroke appears on its own.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
sys.path.insert(0, str(PROJECT / "tools"))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from run_e2_c_product_path import POINT_AT  # noqa: E402

# The whole canvas, as a count and as the set of rows carrying a 1px stroke.
INK = """(() => {
const canvas = document.querySelector('#canvas');
const data = canvas.getContext('2d')
  .getImageData(0, 0, canvas.width, canvas.height).data;
const rows = [];
for (let y = 0; y < canvas.height; y += 1) {
  let dark = 0;
  const base = y * canvas.width * 4;
  for (let x = 0; x < canvas.width; x += 1) {
    const i = base + x * 4;
    if (data[i] < 100 && data[i+1] < 100 && data[i+2] < 100) dark += 1;
  }
  rows.push(dark);
}
return rows;
})()"""


def main():
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(PROJECT / "dist")],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session = ChromeSession("caret-timing")
        navigate(session, base)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            state = evaluate(session, READ_STATE)
            if state and state.get("state") == "ready":
                break
            time.sleep(0.5)

        before = evaluate(session, INK)
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            state = evaluate(session, READ_STATE)
            if state and "定位游標" in (state.get("latency") or ""):
                break
            time.sleep(0.3)
        print("status after click:", (state or {}).get("latency"))

        for wait in (1.0, 2.0, 3.0, 6.0):
            time.sleep(wait)
            after = evaluate(session, INK)
            gained = [(y, before[y], after[y])
                      for y in range(min(len(before), len(after)))
                      if after[y] > before[y]]
            total = sum(after) - sum(before)
            print(f"t≈{sum((1.0, 2.0, 3.0, 6.0)[:(1.0, 2.0, 3.0, 6.0).index(wait)+1]):4.1f}s "
                  f"rows gaining ink: {len(gained)}  total delta: {total:+d}  "
                  f"{[y for y, _, _ in gained][:12]}")
        return 0
    finally:
        if session:
            try:
                session.close()
            except Exception:
                pass
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    sys.exit(main())
