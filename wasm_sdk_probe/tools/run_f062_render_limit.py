#!/usr/bin/env python3
"""Finding 062: ask the ENGINE for a tile taller than the wall, and look at it.

The product path cannot say where the pixels are lost -- `render()` does not
throw and the page publishes no session handle -- and that question decides
whether the fix needs a link. So this drives the same artifact through the same
engine factory the product uses (`web/e2-editor-app.js:585`) from a page that
does nothing but report what came back.

The page and its document are written into a SYMLINK MIRROR of `dist/`, never
into `dist/` itself: that tree is the frozen artifact and the E2-B lesson is
that a hash-bound set is not something to grow a file beside. The mirror shares
every real file by symlink, so the engine, the worker and the wasm are byte for
byte the ones the product loads.

Usage: run_f062_render_limit.py [--out REPORT.json] [--browser chrome|firefox]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_long_document import build as build_long_document   # noqa: E402
from r7_support import evaluate, wait_page                      # noqa: E402
from run_browser_probe import (ChromeSession, FirefoxSession,   # noqa: E402
                               free_port)
from run_e2_c_product_path import PROJECT, build_mirror         # noqa: E402
from run_e2_c_page_smoke import navigate                        # noqa: E402

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>finding 062 -- render limit</title></head>
<body><pre id="log"></pre><div id="stage"></div>
<script type="module" src="./f062-render-limit-app.js"></script>
</body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"),
                        default="chrome")
    parser.add_argument("--pages", type=int, default=17)
    parser.add_argument("--heights",
                        default="31048,32590,32767,32768,32889,34847")
    parser.add_argument("--via-session", action="store_true",
                        help="open through NarrowEditorV2Session, the way the "
                             "product does, instead of the raw SDK")
    parser.add_argument("--width", type=int, default=725,
                        help="canvas width; the discriminator between a 2^15 "
                             "height limit and a byte-size ceiling")
    parser.add_argument("--second", action="store_true",
                        help="open and close a document first, the way the "
                             "product always has by the time it opens a long one")
    parser.add_argument("--preallocate", action="store_true",
                        help="allocate a canvas of the target size BEFORE the "
                             "render, the way layoutCanvas() does")
    parser.add_argument("--out", default=None)
    parser.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()

    scratch = Path(tempfile.mkdtemp(prefix="f062-render-limit-"))
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root, {})
    # Written into the MIRROR, not into dist: a path that dist does not have
    # cannot be delivered as an override (measured 2026-08-18 -- overrides for
    # absent paths are silently dropped and the page opens a 404).
    (root / "f062-render-limit.html").write_text(PAGE, encoding="utf-8")
    shutil.copyfile(PROJECT / "tools" / "f062_render_limit_app.js",
                    root / "f062-render-limit-app.js")
    (root / "f062-long.odt").write_bytes(build_long_document(args.pages))

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    report: dict = {"schemaVersion": 1, "release": "f062-render-limit",
                    "browser": args.browser, "pages": args.pages}
    try:
        base = (f"http://127.0.0.1:{port}/f062-render-limit.html"
                f"?heights={args.heights}&width={args.width}"
                + ("&preallocate=1" if args.preallocate else "")
                + ("&viaSession=1" if args.via_session else "")
                + ("&second=1" if args.second else ""))
        wait_page(f"http://127.0.0.1:{port}/f062-render-limit.html")
        session = (ChromeSession("cold") if args.browser == "chrome"
                   else FirefoxSession("cold"))
        navigate(session, base)
        deadline = time.monotonic() + args.timeout
        page = None
        while time.monotonic() < deadline:
            page = evaluate(session, "(() => globalThis.__f062 || null)()")
            if page and page.get("done"):
                break
            time.sleep(1.0)
        report["page"] = page
        report["log"] = evaluate(
            session, "(() => document.querySelector('#log').textContent)()")
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        shutil.rmtree(scratch, ignore_errors=True)

    page = report.get("page") or {}
    arms = page.get("arms") or []
    # The verdict this round exists for, stated so it cannot be read off a
    # feeling: an arm whose buffer is the size the request implies, and which
    # carries dark pixels, is a tile the ENGINE produced correctly.
    good = [a for a in arms if a.get("byteLengthMatchesRequest")
            and (a.get("darkPixels") or 0) > 0]
    empty = [a for a in arms if a.get("byteLengthMatchesRequest")
             and not (a.get("darkPixels") or 0)]
    short = [a for a in arms if a.get("byteLength") is not None
             and not a.get("byteLengthMatchesRequest")]
    threw = [a for a in arms if a.get("threw")]
    report["summary"] = {
        "tilesWithInk": [a["canvasHeightPx"] for a in good],
        "tilesCorrectlySizedButBlank": [a["canvasHeightPx"] for a in empty],
        "tilesShortOrOversized": [a["canvasHeightPx"] for a in short],
        "renderThrew": [a["canvasHeightPx"] for a in threw],
        "imageDataRefused": [a["canvasHeightPx"] for a in arms
                             if a.get("imageDataBuilt") is False],
        "detachedCanvasBlank": [a["canvasHeightPx"] for a in arms
                                if (a.get("detachedInkedColumns") or 0) < 40],
        "attachedCanvasBlank": [a["canvasHeightPx"] for a in arms
                                if (a.get("attachedInkedColumns") or 0) < 40],
    }
    report["ok"] = bool(arms) and page.get("error") is None
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False,
                                             indent=1) + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
