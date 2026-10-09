"""Drag-select inside a paragraph, then press Backspace (or Delete): what does the product do?

Standalone page from dist/ (or another page source via --page FILE as a mirror override), boundaries.odt,
a drag through the page's own pointer handler (pp.DRAG) inside "M01 plain alpha", then one real key.
Records: the toolbar's selection shape before the key, the toasts, state, generation, revision, the
saved first paragraph.  No product byte changed.
"""
import base64, io, json, subprocess, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
import odt_paragraphs
import run_e2_c_product_path as pp
import probe_111_overtake as p111
p111.CDP_KEYS["Delete"] = ("Delete", "Delete", 46)   # the 111 probe never pressed Delete
p111.WD["Delete"] = "\ue017"
HERE = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
browser, key = sys.argv[1], sys.argv[2]
page = Path(sys.argv[3]) if len(sys.argv) > 3 else None
mirror = Path(tempfile.mkdtemp(prefix="seldel-")) / "root"
overrides = {"e2-editor-app.js": page.read_bytes()} if page else {}
pp.build_mirror(HERE / "dist", mirror, overrides)
(mirror / "f.odt").write_bytes((HERE / "test-docs/merge/odt/boundaries.odt").read_bytes())
SHAPE = "(() => document.querySelector('#toolbar')?.dataset.selectionShape ?? null)()"
GEN = "(() => document.querySelector('#s-generation').textContent)()"
out = {"browser": browser, "key": key, "page": str(page) if page else "dist"}
port = pp.free_port()
server = subprocess.Popen([sys.executable, str(HERE / "web/serve.py"), "--port", str(port), "--root", str(mirror)],
                          cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
session = None
try:
    base = f"http://127.0.0.1:{port}/e2-editor.html"; pp.wait_page(base)
    session = (pp.ChromeSession if browser == "chrome" else pp.FirefoxSession)("cold")
    out["version"] = getattr(session, "version", None)
    pp.navigate(session, base); pp.wait_for(session, lambda s: s.get("state") == "ready", 300); pp.evaluate(session, pp.INSTALL)
    pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./f.odt").replace("ARG_NAME", "f.odt"))
    pp.wait_for(session, lambda s: (s.get("doc") or "") == "f.odt" and s.get("state") == "ready", 120); p111.quiet(session)
    # Drag across "plain" in "M01 plain alpha" (the line's caret end is x 0.2366 at y 0.0451).
    pp.evaluate(session, pp.DRAG.replace("ARG_X1", "0.150").replace("ARG_Y1", "0.045065")
                .replace("ARG_X2", "0.195").replace("ARG_Y2", "0.045065"))
    time.sleep(1.5); p111.quiet(session)
    out["shapeBeforeKey"] = pp.evaluate(session, SHAPE)
    out["before"] = {k: (pp.evaluate(session, pp.READ_STATE) or {}).get(k) for k in ("state", "revision", "latency")}
    out["genBefore"] = pp.evaluate(session, GEN)
    pp.evaluate(session, "(() => { window.__pp && (window.__pp.toasts.length = 0); return true; })()")
    p111.burst(session, browser, [key], 0)
    time.sleep(4.0); p111.quiet(session, 20)
    st = pp.evaluate(session, pp.READ_STATE) or {}
    out["after"] = {k: st.get(k) for k in ("state", "revision", "latency", "toast")}
    out["genAfter"] = pp.evaluate(session, GEN)
    out["toasts"] = pp.evaluate(session, pp.READ_TOASTS)
    idx = pp.evaluate(session, pp.SAVE_COUNT) or 0
    pp.evaluate(session, pp.PRESS.replace("ARG_ACTION", "save"))
    if pp.wait_saves(session, idx + 1, 30):
        raw = base64.b64decode(pp.evaluate(session, pp.READ_SAVE.replace("ARG_INDEX", str(idx)))["b64"])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            out["firstParagraph"] = odt_paragraphs.paragraph_texts_from_xml(z.read("content.xml"))[0]
finally:
    if session: session.close()
    server.terminate(); server.wait(timeout=10)
print(json.dumps(out, ensure_ascii=False))
