"""Does opening a document through the page's file input re-enable an input sink a previous session left disabled?"""
import json, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
import run_e2_c_product_path as pp
import probe_111_overtake as p111
HERE = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
FIX = HERE / "test-docs/merge/odt/boundaries.odt"
mirror = Path(tempfile.mkdtemp(prefix="sink-")) / "root"
pp.build_mirror(HERE / "dist", mirror, {})
(mirror / "f.odt").write_bytes(FIX.read_bytes())
SINK = "(() => { const s = document.querySelector('#sink'); return { disabled: s.disabled, focused: document.activeElement === s }; })()"
out = {"browser": sys.argv[1], "arms": []}
port = pp.free_port()
server = subprocess.Popen([sys.executable, str(HERE / "web/serve.py"), "--port", str(port), "--root", str(mirror)], cwd=HERE,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
session = None
try:
    base = f"http://127.0.0.1:{port}/e2-editor.html"; pp.wait_page(base)
    for arm in ("control", "residue"):
        # A browser per arm: the control arm leaves an unsaved Q, and navigating away
        # from it stops at the page's own leave prompt in Chrome (handoff rule jj).
        if session: session.close()
        session = (pp.ChromeSession if sys.argv[1] == "chrome" else pp.FirefoxSession)("cold")
        out["version"] = getattr(session, "version", None)
        pp.navigate(session, base); pp.wait_for(session, lambda s: s.get("state") == "ready", 300); pp.evaluate(session, pp.INSTALL)
        rec = {"arm": arm}
        for k, name in enumerate(("first.odt", "second.odt")):
            if k == 1 and arm == "residue":
                pp.evaluate(session, "(() => { document.querySelector('#sink').disabled = true; return true; })()")
                rec["sinkBeforeSecondOpen"] = pp.evaluate(session, SINK)
            pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./f.odt").replace("ARG_NAME", name))
            pp.wait_for(session, lambda s: (s.get("doc") or "") == name and s.get("state") == "ready", 120)
            p111.quiet(session)
        before = (pp.evaluate(session, pp.READ_STATE) or {}).get("latency")
        pp.evaluate(session, pp.POINT_AT.replace("ARG_X", "0.236572").replace("ARG_Y", "0.045065"))
        pp.wait_for(session, lambda s: "定位游標" in (s.get("latency") or "") and s.get("latency") != before, 30)
        p111.quiet(session)
        rec["sinkAfterOpenAndClick"] = pp.evaluate(session, SINK)
        r0 = (pp.evaluate(session, pp.READ_STATE) or {}).get("revision")
        p111.burst(session, sys.argv[1], ["Q"], 0); p111.quiet(session, 15)
        rec["typingQ"] = [r0, (pp.evaluate(session, pp.READ_STATE) or {}).get("revision")]
        out["arms"].append(rec)
finally:
    if session: session.close()
    server.terminate(); server.wait(timeout=10)
print(json.dumps(out, ensure_ascii=False))
