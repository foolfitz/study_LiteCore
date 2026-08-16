#!/usr/bin/env python3
"""Top half of a line versus bottom half of the SAME line.

Predictions: scratchpad/PREDICTION-051.md, written first.
Each click is resolved before the next is sent; the shell serialises them.
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
OK_FIND = """    el.s.latency.textContent = `${label} ${Math.round(performance.now() - started)} ms`;"""
OK_ADD = """    el.s.latency.textContent = `${label} ${Math.round(performance.now() - started)} ms`;
    globalThis.__diag = { label, ok: true, result: result ?? null };"""

# The candidate fix, applied to the mirror only.
FIX_FIND = """  return Math.abs(yTwips - caret.y) <= Math.max(caret.height / 2, 1);"""
FIX_ADD = """  const slack = Math.max(caret.height / 2, 1);
  return yTwips >= caret.y - slack && yTwips <= caret.y + caret.height;"""

browser = sys.argv[1] if len(sys.argv) > 1 else "chrome"
fixed = "--fixed" in sys.argv
scratch = Path("/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/"
               "7a4f2519-cbb2-4716-8ac9-dd487bf33ea8/scratchpad/"
               f"mirror-halves-{'fixed' if fixed else 'asis'}")
subprocess.run(["rm", "-rf", str(scratch)], check=True)

app = (PROJECT / "dist" / "e2-editor-app.js").read_text(encoding="utf-8")
assert app.count(FIND) == 1 and app.count(OK_FIND) == 1
overrides = {"e2-editor-app.js": app.replace(FIND, ADD).replace(OK_FIND, OK_ADD).encode()}
if fixed:
    shell = (PROJECT / "dist" / "editor-shell" / "editor-session.js").read_text(encoding="utf-8")
    assert shell.count(FIX_FIND) == 1, shell.count(FIX_FIND)
    overrides["editor-shell/editor-session.js"] = shell.replace(FIX_FIND, FIX_ADD).encode()
build_mirror(PROJECT / "dist", scratch, overrides)

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
    print(f"[{browser}{' FIXED' if fixed else ''}] open after "
          f"{round(time.monotonic()-t0,2)} s")
    for label, frac in [("top-half", 0.092), ("bottom-half", 0.106),
                        ("top-half-again", 0.092), ("bottom-half-again", 0.106)]:
        evaluate(session, "(() => { globalThis.__diag = null; return 1; })()")
        started = time.monotonic()
        evaluate(session, POINT_AT.replace("ARG_X", "0.40").replace("ARG_Y", str(frac)))
        diag = None
        while time.monotonic() - started < 45:
            diag = evaluate(session, "(() => globalThis.__diag || null)()")
            if diag:
                break
            time.sleep(0.25)
        wall = round(time.monotonic() - started, 1)
        row = {"label": label, "yFraction": frac, "wallSeconds": wall,
               "ok": bool(diag and diag.get("ok")),
               "code": (diag or {}).get("code"),
               "details": (diag or {}).get("details"),
               "result": (diag or {}).get("result")}
        rows.append(row)
        print(f"  {label:<18} y={frac}  wall={wall:<6}s  ok={row['ok']}  "
              f"{row['code'] or ''} {json.dumps(row['details'] or row['result'] or {}, ensure_ascii=False)[:160]}")
finally:
    if session:
        session.close()
    server.terminate()
    out = Path(sys.argv[-1]) if sys.argv[-1].endswith(".json") else None
    if out:
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
