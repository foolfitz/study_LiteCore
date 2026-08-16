#!/usr/bin/env python3
"""What twips does the product page compute, and where does the engine put the
caret?

The page throws EDITOR_CARET_NOT_PLACED with details {xTwips, yTwips, caret,
sequenceAdvanced} and then drops them on the floor -- `describeError` keeps the
code and the message only.  So this serves a MIRROR of dist with one diagnostic
line added to the page's error path (dist itself is untouched, symlinks
everywhere else) and reads the details back.
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

FIND = """    el.s.latency.textContent = `${label} 失敗`;"""
ADD = """    el.s.latency.textContent = `${label} 失敗`;
    globalThis.__diag = { label, code: error?.code, message: error?.message,
                          details: error?.details ?? null };"""

# And a second patch: report the geometry the page used.
FIND2 = """function pointToTwips(event) {"""
ADD2 = """function pointToTwips(event) {
  globalThis.__geom = { widthTwips: session?.document?.widthTwips,
                        heightTwips: session?.document?.heightTwips,
                        box: el.canvas.getBoundingClientRect().toJSON(),
                        clientX: event.clientX, clientY: event.clientY };"""

browser = sys.argv[1] if len(sys.argv) > 1 else "chrome"
scratch = Path("/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/"
               "7a4f2519-cbb2-4716-8ac9-dd487bf33ea8/scratchpad/mirror-diag")
if scratch.exists():
    subprocess.run(["rm", "-rf", str(scratch)], check=True)

source = (PROJECT / "dist" / "e2-editor-app.js").read_text(encoding="utf-8")
assert source.count(FIND) == 1, source.count(FIND)
assert source.count(FIND2) == 1
patched = source.replace(FIND, ADD).replace(FIND2, ADD2)
build_mirror(PROJECT / "dist", scratch, {"e2-editor-app.js": patched.encode()})

port = free_port()
server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"),
                           "--port", str(port), "--root", str(scratch)],
                          cwd=PROJECT, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)
session = None
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
    for (x, y) in [(0.40, 0.10), (0.40, 0.30)]:
        evaluate(session, "(() => { globalThis.__diag = null; return 1; })()")
        evaluate(session, POINT_AT.replace("ARG_X", str(x)).replace("ARG_Y", str(y)))
        started = time.monotonic()
        diag = None
        while time.monotonic() - started < 60:
            diag = evaluate(session, "(() => globalThis.__diag || null)()")
            if diag:
                break
            time.sleep(0.5)
        print(f"\n=== click at fraction ({x}, {y}) after "
              f"{round(time.monotonic()-started,1)} s")
        print("geom:", json.dumps(evaluate(session, "(() => globalThis.__geom)()"),
                                  ensure_ascii=False))
        print("diag:", json.dumps(diag, ensure_ascii=False))
finally:
    if session:
        session.close()
    server.terminate()
