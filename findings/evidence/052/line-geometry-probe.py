#!/usr/bin/env python3
"""Does any line box in the corpus reach into the next line's box?

Codex's adversarial review claims the corrected caretIsOnLine can accept a
caret one line ABOVE the clicked line, when a caret rectangle is taller than the
distance to the next line's top.  Whether that geometry occurs is a
measurement, not an argument: this walks a column of clicks down the product
page and records (caret.y, caret.height) for each distinct line, then compares
each box's bottom against the next box's top.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
sys.path.insert(0, str(PROJECT / "tools"))
from r7_support import evaluate, wait_page  # noqa
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa
from run_e2_c_page_smoke import READ_STATE, navigate, POINT_AT  # noqa
from run_e2_c_product_path import build_mirror  # noqa

FIND_FAIL = """    el.s.latency.textContent = `${label} 失敗`;"""
ADD_FAIL = """    el.s.latency.textContent = `${label} 失敗`;
    globalThis.__diag = { ok: false, code: error?.code, details: error?.details ?? null };"""
FIND_OK = """    el.s.latency.textContent = `${label} ${Math.round(performance.now() - started)} ms`;"""
ADD_OK = """    el.s.latency.textContent = `${label} ${Math.round(performance.now() - started)} ms`;
    globalThis.__diag = { ok: true, caret: result?.state?.caret ?? null };"""

browser = sys.argv[1] if len(sys.argv) > 1 else "chrome"
out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
scratch = Path("/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/"
               "7a4f2519-cbb2-4716-8ac9-dd487bf33ea8/scratchpad/mirror-geometry")
subprocess.run(["rm", "-rf", str(scratch)], check=True)
app = (PROJECT / "dist" / "e2-editor-app.js").read_text(encoding="utf-8")
assert app.count(FIND_FAIL) == 1 and app.count(FIND_OK) == 1
build_mirror(PROJECT / "dist", scratch,
             {"e2-editor-app.js": app.replace(FIND_FAIL, ADD_FAIL)
              .replace(FIND_OK, ADD_OK).encode()})

port = free_port()
server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"),
                           "--port", str(port), "--root", str(scratch)],
                          cwd=PROJECT, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)
session = None
rows = []
try:
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session = (ChromeSession if browser == "chrome" else FirefoxSession)("cold")
    navigate(session, base)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 240:
        state = evaluate(session, READ_STATE)
        if state and state.get("state") == "ready" and state.get("doc") not in (None, "—"):
            break
        time.sleep(0.2)
    print(f"[{browser}] open after {round(time.monotonic()-t0,2)} s")
    # 60 clicks down the page: fine enough to land on every line at least once.
    for i in range(26):
        frac = 0.03 + i * 0.018
        if frac > 0.95:
            break
        evaluate(session, "(() => { globalThis.__diag = null; return 1; })()")
        started = time.monotonic()
        evaluate(session, POINT_AT.replace("ARG_X", "0.40").replace("ARG_Y", str(round(frac, 4))))
        diag = None
        while time.monotonic() - started < 40:
            diag = evaluate(session, "(() => globalThis.__diag || null)()")
            if diag:
                break
            time.sleep(0.2)
        rows.append({"yFraction": round(frac, 4), "ok": bool(diag and diag.get("ok")),
                     "caret": (diag or {}).get("caret"),
                     "tookMs": round((time.monotonic() - started) * 1000)})
finally:
    if session:
        session.close()
    server.terminate()

boxes = []
for row in rows:
    caret = row.get("caret")
    if not caret:
        continue
    if not boxes or boxes[-1]["y"] != caret["y"]:
        boxes.append({"y": caret["y"], "height": caret["height"]})
boxes.sort(key=lambda b: b["y"])
print(f"\ndistinct line boxes: {len(boxes)}")
overlaps = []
for a, b in zip(boxes, boxes[1:]):
    pitch = b["y"] - a["y"]
    bottom = a["y"] + a["height"]
    overlap = bottom - b["y"]
    print(f"  y={a['y']:<6} h={a['height']:<5} bottom={bottom:<6} "
          f"next top={b['y']:<6} pitch={pitch:<5} overlap={overlap}")
    if overlap > 0:
        overlaps.append({"box": a, "next": b, "overlap": overlap})
print(f"\nboxes whose bottom reaches into the next line: {len(overlaps)}")
refused = [r for r in rows if not r["ok"]]
print(f"clicks refused: {len(refused)} of {len(rows)}")
if out:
    out.write_text(json.dumps({"browser": browser, "clicks": rows, "boxes": boxes,
                               "overlaps": overlaps}, ensure_ascii=False, indent=1))
