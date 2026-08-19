#!/usr/bin/env python3
"""Finding 062: in the PRODUCT's blank state, can that canvas hold pixels at all?

The SDK probe showed the engine returning a correct tile, ImageData building
from it, and putImageData painting it -- on both a detached and an attached
canvas -- at every height up to 34,847.  So the loss is page-side.  This asks
which page-side step, by painting the product's OWN canvas from the harness
while it is in the blank state:

  * if a synthetic block SHOWS, the canvas is fine and the product simply never
    put the tile there;
  * if it does not, the canvas the product is holding cannot take pixels at
    that size in that layout, and the tile was irrelevant.
"""

from __future__ import annotations

import base64
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from create_long_document import build as build_long           # noqa: E402
from r7_support import evaluate, wait_page                     # noqa: E402
from run_browser_probe import ChromeSession, free_port         # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate           # noqa: E402
from run_e2_c_product_path import (GEOMETRY, INSTALL,          # noqa: E402
                                   OPEN_BYTES, PROJECT, TOP_INK)

PAINT_A_BLOCK = """(() => {
const canvas = document.querySelector('#canvas');
const context = canvas.getContext('2d');
// A solid block across the top strip, painted by the HARNESS, not by the
// product: nothing about the tile or the engine is involved.
context.fillStyle = '#000000';
context.fillRect(0, 0, canvas.width, 50);
const back = context.getImageData(0, 0, canvas.width, 60).data;
let dark = 0;
for (let i = 0; i + 3 < back.length; i += 4)
  if (back[i+3] > 128 && back[i] < 100 && back[i+1] < 100 && back[i+2] < 100)
    dark += 1;
return { width: canvas.width, height: canvas.height, darkAfterFill: dark,
         expected: canvas.width * 50 };
})()"""


def main() -> int:
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(PROJECT / "dist")],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session = ChromeSession("cold")
        navigate(session, base)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            if (evaluate(session, READ_STATE) or {}).get("state") == "ready":
                break
            time.sleep(0.5)
        evaluate(session, INSTALL)

        for pages in (17, 35):
            payload = base64.b64encode(build_long(pages)).decode("ascii")
            evaluate(session, OPEN_BYTES.replace("ARG_B64", payload)
                     .replace("ARG_NAME", f"blank-{pages}.odt"))
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                state = evaluate(session, READ_STATE) or {}
                if state.get("doc") == f"blank-{pages}.odt" \
                        and state.get("state") == "ready":
                    break
                time.sleep(0.5)
            time.sleep(5.0)
            geometry = evaluate(session, GEOMETRY) or {}
            before = evaluate(session, TOP_INK) or {}
            painted = evaluate(session, PAINT_A_BLOCK) or {}
            print(f"pages={pages} canvas={geometry.get('width')}x"
                  f"{geometry.get('height')} "
                  f"productInkCols={before.get('columns')} "
                  f"harnessFill dark={painted.get('darkAfterFill')} "
                  f"of expected {painted.get('expected')}")
        return 0
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
