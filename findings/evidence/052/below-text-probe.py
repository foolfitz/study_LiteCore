#!/usr/bin/env python3
"""A click below the last line, in the two orders that matter.

fresh: the first click of the session lands below the text.  The caret is at the
       top of the document, so the engine's clamp MOVES it.
again: a second click below the text, with the caret already on the clamped
       line.  Nothing moves, and nothing can distinguish that from a swallowed
       click.
"""
import json, subprocess, sys, time
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
    globalThis.__diag = { ok: true, caret: result?.state?.caret ?? null,
                          confirmedBy: result?.caretConfirmedBy ?? null,
                          onClickedLine: result?.caretOnClickedLine ?? null };"""

browser = sys.argv[1] if len(sys.argv) > 1 else "chrome"
out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
scratch = Path(f"/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/7a4f2519-cbb2-4716-8ac9-dd487bf33ea8/scratchpad/mirror-below-{browser}")
subprocess.run(["rm", "-rf", str(scratch)], check=True)
app = (PROJECT / "dist" / "e2-editor-app.js").read_text(encoding="utf-8")
build_mirror(PROJECT / "dist", scratch,
             {"e2-editor-app.js": app.replace(FIND_FAIL, ADD_FAIL).replace(FIND_OK, ADD_OK).encode()})
port = free_port()
server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"),
                           "--port", str(port), "--root", str(scratch)], cwd=PROJECT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
session = None
rows = []
try:
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session = (ChromeSession if browser == "chrome" else FirefoxSession)("cold")
    navigate(session, base)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 240:
        st = evaluate(session, READ_STATE)
        if st and st.get("state") == "ready" and st.get("doc") not in (None, "—"):
            break
        time.sleep(0.2)
    for label, frac in [("first click, below the text", 0.45),
                        ("again, below the text", 0.50),
                        ("back into the text", 0.14),
                        ("below the text once more", 0.55)]:
        evaluate(session, "(() => { globalThis.__diag = null; return 1; })()")
        started = time.monotonic()
        evaluate(session, POINT_AT.replace("ARG_X", "0.40").replace("ARG_Y", str(frac)))
        diag = None
        while time.monotonic() - started < 40:
            diag = evaluate(session, "(() => globalThis.__diag || null)()")
            if diag: break
            time.sleep(0.2)
        took = round((time.monotonic() - started) * 1000)
        rows.append({"label": label, "yFraction": frac, "tookMs": took,
                     "ok": bool(diag and diag.get("ok")), "diag": diag})
        print(f"  {label:<28} y={frac}  {took:>6} ms  ok={rows[-1]['ok']}  "
              f"{(diag or {}).get('confirmedBy') or (diag or {}).get('code')}")
finally:
    if session: session.close()
    server.terminate()
    if out: out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
