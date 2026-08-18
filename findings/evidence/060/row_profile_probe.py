#!/usr/bin/env python3
"""Is the caret DRAWN at all, or is the 058 check's fixed band just mis-aimed?

The product-path round reported darkWithCaret == darkAfterItMovedAway == 2051,
which two different things produce:

  H1  the caret is drawn, but both click fractions land on the same line, so it
      never leaves the sampled band -- a harness fragility
  H2  the caret is not drawn at all -- a regression of finding 058's fix

The band count cannot tell them apart. A per-row profile of the whole canvas
can: click A, profile; click B, profile; diff. A caret that is drawn and moves
shows up as a narrow run of rows that gains ink and another that loses it.
Nothing changing anywhere is H2.
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

PROFILE = """(() => {
const canvas = document.querySelector('#canvas');
const ctx = canvas.getContext('2d');
const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
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
return { width: canvas.width, height: canvas.height,
         cssWidth: canvas.style.width, dpr: globalThis.devicePixelRatio, rows };
})()"""


def click(session, fx, fy):
    evaluate(session, POINT_AT.replace("ARG_X", fx).replace("ARG_Y", fy))
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if state and "定位游標" in (state.get("latency") or ""):
            return state
        time.sleep(0.3)
    return None


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "dist"
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session = ChromeSession("caret-profile")
        navigate(session, base)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            state = evaluate(session, READ_STATE)
            if state and state.get("state") == "ready":
                break
            time.sleep(0.5)
        else:
            print("page never became ready")
            return 1

        out = {}
        for label, (fx, fy) in (("A", ("0.35", "0.28")),
                                ("B", ("0.35", "0.42"))):
            click(session, fx, fy)
            time.sleep(1.0)
            out[label] = evaluate(session, PROFILE)
        Path(sys.argv[2]).write_text(json.dumps(out)) if len(sys.argv) > 2 else None

        a, b = out["A"], out["B"]
        print(json.dumps({k: a[k] for k in ("width", "height", "cssWidth", "dpr")}))
        rows_a, rows_b = a["rows"], b["rows"]
        diffs = [(y, rows_a[y], rows_b[y]) for y in range(min(len(rows_a), len(rows_b)))
                 if rows_a[y] != rows_b[y]]
        print(f"rows that changed between click A and click B: {len(diffs)}")
        for y, va, vb in diffs[:60]:
            print(f"  row {y:5d}  A={va:5d}  B={vb:5d}  delta={vb - va:+d}")
        print(f"total ink A={sum(rows_a)}  B={sum(rows_b)}")
        # Where the two click fractions actually land, in canvas rows.
        for label, fy in (("A", 0.28), ("B", 0.42)):
            print(f"click {label} targets canvas row {int(a['height'] * fy)}")
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
