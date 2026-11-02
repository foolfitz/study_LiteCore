#!/usr/bin/env python3
"""SPEC-P-demo-batch-3 P2: text colour, cell fill and horizontal alignment on the Calc page.

The owner's path on a private mirror of the live sources: real pointer on the toolbar and the palette, real keys.  Three witnesses
for one claim, because each can be wrong alone: the page's state (what the engine answered), the pixels of the tile under the cell
(what was painted), and the saved ODS (what the document holds).  Every check is recorded and the run goes on past a red one.

  check_calc_style.py --out DIR --engine DIR [--browsers chrome,firefox]

--engine is the profile directory holding the v3 engine: dist/profiles/ods-editor-v3, or build/ods/editor-v3/profile before it is
frozen.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

from check_calc_sheet_view import Hands, RECT, wait
from create_calc_range_format_fixture import create
from probe_calc_style_native import cell_style
from r7_support import evaluate, wait_page
from run_browser_probe import free_port
from run_e2_c_page_smoke import navigate
from v21_shakedown_common import browser_lock, close_browser, open_browser

PROJECT = Path(__file__).resolve().parents[1]
WINDOW = (1440, 1000)
ROOT = "window.__calcEditor"
PAINT = """(()=>{const [x,y,w,h]=ARGS,out={fill:null,ink:0,left:null,right:null,red:0};
 const canvases=[...document.querySelectorAll('#tiles canvas')];
 const at=(px,py)=>{for(const c of canvases){const r=c.getBoundingClientRect();
   if(px>=r.left&&px<r.right&&py>=r.top&&py<r.bottom){const s=c.width/r.width;
     return c.getContext('2d').getImageData(Math.floor((px-r.left)*s),Math.floor((py-r.top)*s),1,1).data;}}return null;};
 const s=document.querySelector('#surface').getBoundingClientRect();
 const corner=at(s.left+x+3,s.top+y+3);out.fill=corner?[corner[0],corner[1],corner[2]]:null;
 for(let py=s.top+y+1;py<s.top+y+h-1;py+=1)for(let px=s.left+x+1;px<s.left+x+w-1;px+=1){const p=at(px,py);if(!p)continue;
   const same=corner&&Math.abs(p[0]-corner[0])+Math.abs(p[1]-corner[1])+Math.abs(p[2]-corner[2])<40;
   if(!same){out.ink++;out.left=out.left===null?px-s.left-x:Math.min(out.left,px-s.left-x);out.right=Math.max(out.right??0,px-s.left-x);
     if(p[0]>150&&p[1]<90&&p[2]<90)out.red++;}}
 return out;})()"""


def mirror(out, engine):
    root = PROJECT / "build/calc-style" / out.name
    root.mkdir(parents=True, exist_ok=False)
    page = (PROJECT / "web/ods-editor-app.js").read_text(encoding="utf-8")
    for name in ("ods-editor-v2", "ods-editor-v3"):
        page = page.replace(f"./profiles/{name}/sdk-worker.js", "./profiles/under-test/sdk-worker.js")
    (root / "ods-editor-app.js").write_text(page, encoding="utf-8")
    shutil.copyfile(PROJECT / "web/ods-editor.html", root / "ods-editor.html")
    for directory in ("sdk", "viewer-shell", "spreadsheet-shell"):
        shutil.copytree(PROJECT / directory, root / directory)
    (root / "reader-shell").mkdir()
    shutil.copyfile(PROJECT / "reader-shell/tile-scheduler.js", root / "reader-shell/tile-scheduler.js")
    (root / "profiles").mkdir()
    (root / "profiles/under-test").symlink_to(engine.resolve(), target_is_directory=True)
    (root / "profiles/resources").symlink_to(PROJECT / "dist/profiles/resources", target_is_directory=True)
    return root


class Run:
    def __init__(self, session, record):
        self.session, self.record, self.hands = session, record, Hands(session)

    def check(self, name, passed, actual):
        self.record["checks"].append({"id": name, "pass": bool(passed), "actual": actual})

    def state(self):
        return evaluate(self.session, f"{ROOT}.state")

    def idle(self):
        time.sleep(.2)
        wait(self.session, f"{ROOT}.state && !{ROOT}.state.busy && !{ROOT}.state.selectionPending && {ROOT}.state.state==='ready'", 30)
        time.sleep(.5)

    def press(self, selector):
        self.hands.click(*evaluate(self.session, RECT % json.dumps(selector)))

    def cell_px(self, cell=None):
        cell = cell or self.state()["cell"]
        return [round(cell[k] / 15) for k in ("xTwips", "yTwips", "widthTwips", "heightTwips")]

    def paint(self, cell=None):
        return evaluate(self.session, PAINT.replace("ARGS", json.dumps(self.cell_px(cell))))

    def choose(self, key, color):
        self.press(f'[data-color-menu="{key}"]')
        wait(self.session, "!document.querySelector('#color-popover').hidden", 5)
        self.press(f'[data-swatch="{color}"]' if color.startswith("#") else "#color-clear")
        self.idle()

    def select_click(self, x_px, y_px):
        box = evaluate(self.session, "(()=>{const r=document.querySelector('#surface').getBoundingClientRect();return [r.left,r.top];})()")
        self.hands.click(box[0] + x_px, box[1] + y_px)
        self.idle()


def scenario(run, out, name):
    session = run.session
    run.idle()
    state = run.state()
    run.check("setup/styling-offered", state.get("rangeStylingSupported") is True and not evaluate(
        session, "document.querySelector('[data-align=\"center\"]').hidden"), state.get("rangeStylingSupported"))
    run.check("setup/a1", [state["cell"]["column"], state["cell"]["row"]] == [0, 0], state["cell"])
    plain = run.paint()

    run.choose("textColor", "#cc0000")
    s, painted = run.state(), run.paint()
    run.check("P2/text-colour/state", s["cell"]["textColor"] == "#cc0000", s["cell"].get("textColor"))
    run.check("P2/text-colour/painted", painted["red"] > 0 and plain["red"] == 0, {"before": plain, "after": painted})
    run.check("P2/text-colour/bar-remembers", evaluate(
        session, "document.querySelector('[data-color=\"textColor\"] .swatch-bar').style.getPropertyValue('--swatch')") == "#cc0000", None)

    run.choose("backColor", "#ffe599")
    s, painted = run.state(), run.paint()
    run.check("P2/fill/state", s["cell"]["backColor"] == "#ffe599", s["cell"].get("backColor"))
    run.check("P2/fill/painted", painted["fill"] == [0xff, 0xe5, 0x99], painted["fill"])

    # The main button applies the last colour, on another cell.
    a1 = run.cell_px()
    run.select_click(a1[0] + a1[2] + 20, a1[1] + 4)
    other = run.state()["cell"]
    run.check("setup/b1", [other["column"], other["row"]] == [1, 0], [other["column"], other["row"]])
    run.press('[data-color="backColor"]')
    run.idle()
    run.check("P2/main-button-reuses-the-colour", run.state()["cell"]["backColor"] == "#ffe599", run.state()["cell"].get("backColor"))
    run.choose("backColor", "none")
    s, painted = run.state(), run.paint()
    run.check("P2/fill/none", s["cell"]["backColor"] == "none" and painted["fill"] == [255, 255, 255], painted["fill"])

    # Alignment moves the ink, in the order the words say.
    run.select_click(a1[0] + 4, a1[1] + 4)
    edges = {}
    for align in ("left", "center", "right", "block"):
        run.press(f'[data-align="{align}"]')
        run.idle()
        s = run.state()
        run.check(f"P2/align-{align}/state", s["cell"]["horizontalAlign"] == align, s["cell"].get("horizontalAlign"))
        run.check(f"P2/align-{align}/pressed", evaluate(session, f"document.querySelector('[data-align=\"{align}\"]').getAttribute('aria-pressed')") == "true", None)
        edges[align] = run.paint()
    run.check("P2/align/ink-moves", edges["left"]["left"] < edges["center"]["left"] < edges["right"]["left"],
              {k: v["left"] for k, v in edges.items()})
    run.press('[data-align="right"]')
    run.idle()
    run.press('[data-align="right"]')
    run.idle()
    run.check("P2/align/second-press-gives-it-back", run.state()["cell"]["horizontalAlign"] == "standard", run.state()["cell"].get("horizontalAlign"))

    # A range, whole, and a mixed read.
    run.hands.click(*evaluate(session, RECT % json.dumps("#viewport")))
    run.select_click(a1[0] + 4, a1[1] + 4)
    session.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", "key": "ArrowRight", "code": "ArrowRight", "windowsVirtualKeyCode": 39, "modifiers": 8}) if run.hands.chrome else \
        session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keys", "actions": [
            {"type": "keyDown", "value": ""}, {"type": "keyDown", "value": ""}, {"type": "keyUp", "value": ""}, {"type": "keyUp", "value": ""}]}]})
    if run.hands.chrome:
        session.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "ArrowRight", "code": "ArrowRight", "windowsVirtualKeyCode": 39, "modifiers": 8})
    run.idle()
    s = run.state()
    run.check("setup/range", s["selection"]["multiple"] is True and [s["selection"]["endColumn"], s["selection"]["endRow"]] == [1, 0], s["selection"])
    run.check("P2/range/mixed-read", s["rangeFormat"]["textColor"] is None, s["rangeFormat"])
    run.choose("backColor", "#b6d7a8")
    s = run.state()
    run.check("P2/range/whole", s["rangeFormat"]["backColor"] == "#b6d7a8", s["rangeFormat"])
    (out / f"{name}-styled.png").write_bytes(session.screenshot())

    run.press("#save-button")
    wait(session, f"{ROOT}.lastSave && !{ROOT}.state.busy", 60)
    encoded = evaluate(session, f"""(async()=>{{const b=new Uint8Array({ROOT}.lastExport);let s='';
      for(let i=0;i<b.length;i+=8192)s+=String.fromCharCode(...b.subarray(i,i+8192));return btoa(s);}})()""")
    saved = out / f"{name}-saved.ods"
    saved.write_bytes(base64.b64decode(encoded))
    a, b, c = (cell_style(saved, 0, col, 0) for col in (0, 1, 2))
    run.check("P2/saved", a.get("color") == "#cc0000" and a.get("background") == "#b6d7a8" and b.get("background") == "#b6d7a8"
              and "background" not in c, {"a1": a, "b1": b, "c1": c})

    # The protected sheet: nothing to press.
    run.press('#tab-strip [data-part="2"]')
    wait(session, f"{ROOT}.state.currentPart===2", 30)
    run.idle()
    run.check("P2/protected-disabled", evaluate(session, "document.querySelector('[data-align=\"center\"]').disabled") is True
              and evaluate(session, "document.querySelector('[data-color=\"backColor\"]').disabled") is True, run.state()["cell"].get("writable"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = mirror(out, args.engine)
    fixture = create(out / "fixture")
    port = free_port()
    log = (out / "server.txt").open("w")
    server = subprocess.Popen(["python3", str(PROJECT / "web/serve.py"), "--port", str(port), "--root", str(root)], stdout=log, stderr=subprocess.STDOUT)
    report = {"tool": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "engine": str(args.engine),
              "wasm": hashlib.sha256((args.engine / "probe.wasm").read_bytes()).hexdigest(), "runs": []}
    try:
        wait_page(f"http://127.0.0.1:{port}/ods-editor.html")
        with browser_lock("calc-style", wait_s=0):
            for browser in args.browsers.split(","):
                session = None
                record = {"browser": browser, "checks": [], "error": None}
                report["runs"].append(record)
                try:
                    session = open_browser(browser, WINDOW)
                    record["version"] = session.version
                    navigate(session, f"http://127.0.0.1:{port}/ods-editor.html?diagnostics=1")
                    session.set_file("#file-input", fixture)
                    wait(session, f"Boolean({ROOT}.state?.cell)", 120)
                    scenario(Run(session, record), out, browser)
                except Exception as error:  # noqa: BLE001  a crash is a result; keep the cells already read
                    record["error"] = repr(error)
                    if session:
                        (out / f"{browser}-failure.png").write_bytes(session.screenshot())
                finally:
                    if session:
                        record["cleanup"] = close_browser(session)
                    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()
    ok = bool(report["runs"]) and all(not r["error"] and r["checks"] and all(c["pass"] for c in r["checks"]) for r in report["runs"])
    print(json.dumps({"pass": ok, "runs": [{"browser": r["browser"], "error": r["error"], "passed": sum(c["pass"] for c in r["checks"]),
                                            "checks": len(r["checks"]), "red": [c["id"] for c in r["checks"] if not c["pass"]]} for r in report["runs"]]},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
