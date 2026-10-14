import sys, io, json, time
sys.path.insert(0, "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
sys.path.insert(0, "/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/scroll-page-bubble")
from pathlib import Path
from run_browser_probe import FirefoxSession
from probe_m3_gate0_coep import firefox_profile
from r7_support import evaluate
from bubble_geometry import thumb_centre
from PIL import Image
S = Path(sys.argv[1]); prefs = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
tag = sys.argv[3] if len(sys.argv) > 3 else "default"
s = FirefoxSession("cold", profile_dir=firefox_profile(Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/scratch-m3-production-ui") / f"ffbar-{tag}-{time.monotonic_ns()}"), extra_prefs=prefs or None)
s.command("POST", "/window/rect", {"width": 1850, "height": 1080})
s.command("POST", "/url", {"url": "file://" + str(S / "page.html")})
time.sleep(1.0)
def geo():
    return evaluate(s, "(() => { const d = document.querySelector('#desk'); const r = d.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, right: r.right, ow: d.offsetWidth, cw: d.clientWidth, st: d.scrollTop, sh: d.scrollHeight, ch: d.clientHeight}; })()")
def shot(label):
    png = s.screenshot(); g = geo()
    (S / f"{tag}-{label}.png").write_bytes(png)
    im = Image.open(io.BytesIO(png)).convert("RGB"); px = im.load()
    cols = {x: sorted({px[x, y] for y in range(int(g["top"]), int(g["bottom"]))}, key=lambda c: sum(c))[:3] for x in range(int(g["right"]) - 12, int(g["right"]))}
    print(tag, label, "geo", g, "size", im.size)
    print("   darkest per column", {x: v[0] for x, v in cols.items()})
    print("   thumb", thumb_centre(png, {"top": g["top"], "bottom": g["bottom"], "right": g["right"]}))
evaluate(s, "(() => { document.querySelector('#desk').scrollTop = 4900; return 1; })()")
time.sleep(0.6)
shot("scrolled")
# hover the rail
g = geo(); x = int(g["right"] - 6); y = int((g["top"] + g["bottom"]) / 2)
s.command("POST", "/actions", {"actions": [{"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"}, "actions": [{"type": "pointerMove", "x": x, "y": y, "origin": "viewport"}]}]})
time.sleep(0.6)
shot("hovered")
# wheel scroll (real input) then shoot at 0.2 s
s.command("POST", "/actions", {"actions": [{"type": "wheel", "id": "wheel", "actions": [{"type": "scroll", "x": 900, "y": y, "deltaX": 0, "deltaY": 700, "origin": "viewport"}]}]})
s.command("DELETE", "/actions")
time.sleep(0.2)
shot("wheel-0.2s")
# CSS scrollbar-color on the desk (instrument-side, this static page only)
evaluate(s, "(() => { document.querySelector('#desk').style.scrollbarColor = '#888 #fff'; return 1; })()")
time.sleep(0.6)
shot("css-colored")
evaluate(s, "(() => { const d = document.querySelector('#desk'); d.style.scrollbarColor = ''; d.style.scrollbarWidth = 'thin'; return 1; })()")
time.sleep(0.6)
shot("css-thin")
s.close()
