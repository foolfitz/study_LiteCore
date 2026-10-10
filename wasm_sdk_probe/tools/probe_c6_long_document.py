#!/usr/bin/env python3
"""SPEC-M3-production-ui §17, C6: is the last page of a long document drawn ON SCREEN?

Finding 062's browser ceiling: a canvas taller than 65,535 rows is not drawn below that row (Chrome) or
fails (Firefox).  The page before C′ puts the whole document on one canvas, so a document times a screen
past that height should show its last page blank.  This opens a document of an exact page count
(`create_long_document.build`, A4, every page starts with a heading and carries `LD-P{page}-L{line}` lines)
through the product's own file input, at a given devicePixelRatio and CSS window, waits, then scrolls
`#desk` so that the top of the LAST page is at the top of the view and reads the pixels on screen
(a screenshot, cropped to the desk) -- and, as the positive control of the instrument, the same at the
top of the document.  No product byte is changed; the page is dist/ as served, through a mirror.

  probe_c6_long_document.py --browser chrome --pages 40 --dpr 2 --window 1400x1000 --out REPORT.json

Ink = pixels darker than luma 128 inside the desk's rectangle.  A screenful of text is tens of thousands
of such pixels; the caret is about 60; a blank page is 0.  Reported raw; the verdict is C6's (spec §17.4).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe_111_overtake as p111  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
DIST = HERE / "dist"
TOASTS = """(() => { const root = document.documentElement, toast = document.querySelector('#toast');
  root.dataset.toastsC6 = '[]';
  new MutationObserver(() => { const t = JSON.parse(root.dataset.toastsC6);
    if (toast.textContent) t.push([toast.textContent, Math.round(performance.now())]);
    root.dataset.toastsC6 = JSON.stringify(t); }).observe(toast, { childList: true, characterData: true, subtree: true });
  return true; })()"""
READ_TOASTS = "(() => JSON.parse(document.documentElement.dataset.toastsC6 || '[]'))()"
VIEW = """(() => { const desk = document.querySelector('#desk'), paper = document.querySelector('#paper');
  const d = desk.getBoundingClientRect(), p = paper.getBoundingClientRect();
  return { innerWidth: window.innerWidth, devicePixelRatio: window.devicePixelRatio,
           desk: [d.left, d.top, d.width, d.height], paper: [p.left, p.top, p.width, p.height],
           scrollTop: desk.scrollTop, scrollHeight: desk.scrollHeight, clientHeight: desk.clientHeight }; })()"""
# Scroll so that document fraction ARG_F is at the top of the desk's view (paper-relative).
SCROLL_TO = """(() => { const desk = document.querySelector('#desk'), paper = document.querySelector('#paper');
  const offset = paper.getBoundingClientRect().top - desk.getBoundingClientRect().top + desk.scrollTop;
  desk.scrollTop = Math.round(offset + paper.getBoundingClientRect().height * ARG_F);
  return desk.scrollTop; })()"""


def ink(png: bytes, view: dict) -> dict:
    image = Image.open(io.BytesIO(png)).convert("L")
    scale = image.width / view["innerWidth"]
    left, top, width, height = view["desk"]
    box = (round(left * scale), round(top * scale), round((left + width) * scale), round((top + height) * scale))
    crop = image.crop(box)
    dark = sum(1 for value in crop.getdata() if value < 128)
    return {"dark": dark, "box": box, "scale": round(scale, 3), "image": [image.width, image.height]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--pages", type=int, required=True)
    ap.add_argument("--dpr", type=float, default=1.0)
    ap.add_argument("--window", default="1400x1000")
    ap.add_argument("--settle", type=float, default=10.0, help="seconds to wait after the session is quiet")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    window = tuple(int(v) for v in a.window.split("x"))
    if a.browser == "firefox":
        os.environ["MOZ_HEADLESS_WIDTH"] = str(round(window[0] * a.dpr))
        os.environ["MOZ_HEADLESS_HEIGHT"] = str(round(window[1] * a.dpr))
    mirror = Path(tempfile.mkdtemp(prefix="c6-")) / "root"
    pp.build_mirror(DIST, mirror, {})
    report = {"probe": "probe_c6_long_document.py", "browser": a.browser, "pages": a.pages, "dprRequested": a.dpr,
              "windowRequested": window, "settle": a.settle,
              "page": hashlib.sha256((DIST / "e2-editor-app.js").read_bytes()).hexdigest(),
              "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
              "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    port = pp.free_port()
    server = subprocess.Popen([sys.executable, str(HERE / "web" / "serve.py"), "--port", str(port), "--root", str(mirror)],
                              cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        pp.wait_page(base)
        if a.browser == "chrome":
            session = pp.ChromeSession("cold")
            session.call("Emulation.setDeviceMetricsOverride",
                         {"width": window[0], "height": window[1], "deviceScaleFactor": a.dpr, "mobile": False})
        else:
            session = pp.FirefoxSession("cold", extra_prefs={"layout.css.devPixelsPerPx": str(a.dpr)})
        report["version"] = getattr(session, "version", None)
        pp.navigate(session, base)
        pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        pp.evaluate(session, pp.INSTALL)
        pp.evaluate(session, TOASTS)
        name = f"c6-{a.pages:02d}p.odt"
        report["open"] = pp.open_long_document(session, a.pages, name)
        report["quiet"] = p111.quiet(session, 120)
        time.sleep(a.settle)
        report["geometry"] = pp.evaluate(session, pp.GEOMETRY)
        report["state"] = pp.evaluate(session, pp.READ_STATE)
        pp.evaluate(session, SCROLL_TO.replace("ARG_F", "0"))
        time.sleep(2.0)
        top_view = pp.evaluate(session, VIEW)
        report["top"] = {"view": top_view, "ink": ink(session.screenshot(), top_view)}
        last_page = (a.pages - 1) / a.pages
        report["lastPageFraction"] = last_page
        pp.evaluate(session, SCROLL_TO.replace("ARG_F", repr(last_page)))
        time.sleep(a.settle)
        bottom_view = pp.evaluate(session, VIEW)
        report["lastPage"] = {"view": bottom_view, "ink": ink(session.screenshot(), bottom_view)}
        report["toasts"] = pp.evaluate(session, READ_TOASTS)
        report["stateAtEnd"] = pp.evaluate(session, pp.READ_STATE)
        report["summary"] = {
            "canvas": [report["geometry"].get("width"), report["geometry"].get("height")],
            "topDark": report["top"]["ink"]["dark"], "lastPageDark": report["lastPage"]["ink"]["dark"],
            "toasts": [t for t, _ in report["toasts"]],
            "repaintFailedToast": any("重繪失敗" in t for t, _ in report["toasts"]),
            "stateAtEnd": (report["stateAtEnd"] or {}).get("state"),
            "scrolledTo": bottom_view["scrollTop"], "scrollHeight": bottom_view["scrollHeight"],
        }
    finally:
        report["completedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if session is not None:
            try:
                session.close()
            except Exception as error:  # noqa: BLE001
                report["closeError"] = str(error)
        server.terminate()
        server.wait(timeout=10)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps(report.get("summary"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
