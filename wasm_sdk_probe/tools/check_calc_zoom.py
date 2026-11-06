#!/usr/bin/env python3
"""SPEC-P-calc-zoom 4.2 with append 2: P-Z1..P-Z8 on the Calc page, Chrome and Firefox, on a private mirror of the live page
sources with the engine under test (the development profile build/ods/editor-v8/profile before the hand-test slot).  Real
pointer and keys; the only scripted moves are reads and centring the viewport on F100 before a zoom click (setup, not the act).

Order (append 2): P-Z1 and the first P-Z7 segment on the fresh document (zoom only, before anything is painted); then F100 is
painted #ff0000 with the page's own back-colour menu; then one click at a time 100 -> 75 -> 50 -> 75 -> ... -> 200, each click a
P-Z5 measurement and each first visit of a level P-Z2, P-Z3, P-Z4 and the second P-Z7 segment (revision = after painting); then
P-Z6 at 150 and P-Z8 at 75.  The levels are read from the page (ZOOM_PERCENTS), so a level added there is judged here.

Red box: the client-space bounding box of red pixels (R>200, G<60, B<60) in the visible tile canvases.  Active box: #active-cell's
getBoundingClientRect().

  check_calc_zoom.py --out NEW_DIR --engine PROFILE_DIR [--browsers chrome,firefox] [--mutate NAME]

--mutate point-15 keeps point()'s 15 (P-Z3 red off 100); no-op16 changes the tiles' scale without op 16 (P-Z3 or P-Z4 red at 75);
no-centre keeps the scroll position on zoom (P-Z5 red).  Without --mutate: exit 0 iff every check of every browser passes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import check_calc_structure as cs
from check_calc_sheet_view import wait
from create_calc_structure_fixture import create
from r7_support import evaluate, wait_page
from run_browser_probe import free_port
from run_e2_c_page_smoke import navigate
from v21_shakedown_common import browser_lock, close_browser, open_browser

PROJECT = Path(__file__).resolve().parents[1]
ROOT = "window.__calcEditor"
# name: (file in the mirror, old, new, criteria that must turn red, "all" or "any")
MUTATIONS = {
    "point-15": ("ods-editor-app.js", "function point(event){const rect=ui.surface.getBoundingClientRect(),t=tw();",
                 "function point(event){const rect=ui.surface.getBoundingClientRect(),t=15;", ["P-Z3"], "all"),
    "no-op16": ("spreadsheet-shell/calc-editor-session.js", "const {zoom}=await this.document.setZoom(384000/percent,{part});",
                "const zoom={widthTwips:this.document.widthTwips,heightTwips:this.document.heightTwips};", ["P-Z3", "P-Z4"], "any"),
    "no-centre": ("ods-editor-app.js",
                  "pendingView={scrollLeft:Math.max(0,Math.round(x-visibleWidth()/2)),scrollTop:Math.max(0,Math.round(y-visibleHeight()/2)),",
                  "pendingView={scrollLeft:ui.viewport.scrollLeft,scrollTop:ui.viewport.scrollTop,", ["P-Z5"], "all"),
}
cs.KEYS["Enter"] = ("Enter", "Enter", 13, "")
F100 = (5, 99)
LEVELS = "import('./spreadsheet-shell/calc-document-sdk.js').then(m=>[...m.ZOOM_PERCENTS])"
CONTROLS = """(()=>{const b=id=>{const n=document.getElementById(id),r=n.getBoundingClientRect();
  return {center:[r.left+r.width/2,r.top+r.height/2],disabled:n.disabled,visible:!n.hidden&&r.width>0,text:n.textContent};};
  return {out:b('zoom-out'),level:b('zoom-level'),in:b('zoom-in'),zoom:window.__calcEditor.zoom};})()"""
MEASURE = """(()=>{const s=window.__calcEditor.state,scale=(s.zoom/100).toFixed(4),v=document.querySelector('#viewport').getBoundingClientRect();
  const visible=[...document.querySelectorAll('#tiles canvas')].filter(c=>{const r=c.getBoundingClientRect();
    return r.right>v.left&&r.left<v.right&&r.bottom>v.top&&r.top<v.bottom;});
  let box=null;
  for(const c of visible){const r=c.getBoundingClientRect(),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
    const kx=r.width/c.width,ky=r.height/c.height;
    for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++){const i=(y*c.width+x)*4;
      if(d[i]>200&&d[i+1]<60&&d[i+2]<60&&d[i+3]>0){const px=r.left+x*kx,py=r.top+y*ky;
        if(!box)box=[px,py,px+kx,py+ky];
        else{box[0]=Math.min(box[0],px);box[1]=Math.min(box[1],py);box[2]=Math.max(box[2],px+kx);box[3]=Math.max(box[3],py+ky);}}}}
  const a=document.querySelector('#active-cell').getBoundingClientRect();
  const col=document.querySelector('#column-headers [data-index="5"]')?.getBoundingClientRect();
  const row=document.querySelector('#row-headers [data-index="99"]')?.getBoundingClientRect();
  return {box,active:[a.left,a.top,a.right,a.bottom],column:col?[col.left,col.right]:null,row:row?[row.top,row.bottom]:null,scale,
    tiles:visible.map(c=>({key:c.dataset.key,width:c.width,css:parseFloat(c.style.width)})),
    surface:parseFloat(document.querySelector('#surface').style.width),
    documentCss:window.__calcEditor.session.scheduler.documentCssSize.width,cell:[s.cell.column,s.cell.row],
    revision:s.revision,zoom:s.zoom};})()"""
CENTRE = """(()=>{const v=document.querySelector('#viewport'),s=document.querySelector('#surface').getBoundingClientRect();
  const left=window.__calcEditor.state.headersSupported?48:0,top=window.__calcEditor.state.headersSupported?20:0;
  const x=s.left+v.scrollLeft+(v.clientWidth-left)/2,y=s.top+v.scrollTop+(v.clientHeight-top)/2;
  const hit=(sel,lo,hi,p)=>{for(const n of document.querySelectorAll(sel)){const b=n.getBoundingClientRect();
    if(p>=b[lo]&&p<b[hi])return +n.dataset.index;}return null;};
  return {column:hit('#column-headers [role=columnheader]','left','right',x),row:hit('#row-headers [role=rowheader]','top','bottom',y),
    scrollLeft:v.scrollLeft,scrollTop:v.scrollTop};})()"""
# Setup, not the act: put F100's centre in the viewport's centre (the cell's rectangle at this zoom, from the active cell).
CENTRE_ON = """(()=>{const c=window.__calcEditor.state.cell,z=window.__calcEditor.state.zoom/100,t=15/z,v=document.querySelector('#viewport');
  const left=window.__calcEditor.state.headersSupported?48:0,top=window.__calcEditor.state.headersSupported?20:0;
  v.scrollLeft=Math.max(0,(c.xTwips+c.widthTwips/2)/t-(v.clientWidth-left)/2);
  v.scrollTop=Math.max(0,(c.yTwips+c.heightTwips/2)/t-(v.clientHeight-top)/2);return [v.scrollLeft,v.scrollTop];})()"""
CELL = ("(async()=>{const {cell}=await window.__calcEditor.session.document.readCell(%d,%d);"
        "return {text:cell.text,backColor:cell.backColor};})()")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mirror(out, engine, mutate):
    root = PROJECT / "build/calc-zoom" / out.name
    root.mkdir(parents=True, exist_ok=False)
    for directory in ("sdk", "viewer-shell", "spreadsheet-shell"):
        shutil.copytree(PROJECT / directory, root / directory)
    page = (PROJECT / "web/ods-editor-app.js").read_text(encoding="utf-8")
    for name in ("ods-editor-v7", "ods-editor-v8"):
        page = page.replace(f"./profiles/{name}/sdk-worker.js", "./profiles/under-test/sdk-worker.js")
    if "./profiles/under-test/sdk-worker.js" not in page:
        raise SystemExit("the page names no engine this tool knows")
    (root / "ods-editor-app.js").write_text(page, encoding="utf-8")
    shutil.copyfile(PROJECT / "web/ods-editor.html", root / "ods-editor.html")
    if mutate:
        name, old, new = MUTATIONS[mutate][:3]
        text = (root / name).read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise SystemExit(f"the mutation {mutate} does not apply ({text.count(old)} sites)")
        (root / name).write_text(text.replace(old, new), encoding="utf-8")
    (root / "reader-shell").mkdir()
    shutil.copyfile(PROJECT / "reader-shell/tile-scheduler.js", root / "reader-shell/tile-scheduler.js")
    (root / "profiles").mkdir()
    (root / "profiles/under-test").symlink_to(engine.resolve(), target_is_directory=True)
    (root / "profiles/resources").symlink_to(PROJECT / "dist/profiles/resources", target_is_directory=True)
    return root


class Run(cs.Run):
    def controls(self):
        return evaluate(self.session, CONTROLS)

    def settle(self, zoom):
        wait(self.session, f"{ROOT}.zoom==={zoom} && {ROOT}.headers?.zoom==={zoom} && !{ROOT}.state.busy", 60)
        self.idle()
        time.sleep(1.0)

    def press(self, button):
        """One click on a zoom control; returns the label after it settles."""
        before = self.controls()["zoom"]
        self.click(*self.controls()[button]["center"])
        wait(self.session, f"{ROOT}.zoom!=={before}", 30)
        after = self.controls()["zoom"]
        self.settle(after)
        return self.controls()["level"]["text"]

    def goto(self, address, column, row):
        center = evaluate(self.session, "(()=>{const r=document.querySelector('#cell-address').getBoundingClientRect();"
                                        "return [r.left+r.width/2,r.top+r.height/2];})()")
        self.click(*center)
        evaluate(self.session, "document.querySelector('#cell-address').select(),true")
        self.hands.text(address)
        self.key("Enter")
        wait(self.session, f"{ROOT}.state.cell?.column==={column} && {ROOT}.state.cell?.row==={row}", 30)
        self.idle()

    def measure(self):
        return evaluate(self.session, MEASURE)


def near(a, b, tolerance):
    return a is not None and b is not None and all(abs(x - y) <= tolerance for x, y in zip(a, b))


def p_z1_z7a(run, levels, record):
    c = run.controls()
    opened = run.state()
    labels_down, labels_up = [], []
    while not run.controls()["out"]["disabled"] and len(labels_down) < 10:
        labels_down.append(run.press("out"))
    while not run.controls()["in"]["disabled"] and len(labels_up) < 10:
        labels_up.append(run.press("in"))
    back = run.press("level")
    want_down = [f"{p}%" for p in sorted((p for p in levels if p < 100), reverse=True)]
    want_up = [f"{p}%" for p in levels[1:]]
    run.check("P-Z1/controls", all(c[k]["visible"] for k in ("out", "level", "in")) and c["level"]["text"] == "100%"
              and labels_down == want_down and labels_up == want_up and back == "100%",
              {"atOpen": c, "down": labels_down, "up": labels_up, "back": back, "levels": levels})
    after = run.state()
    unsaved = evaluate(run.session, f"{ROOT}.session.hasUnsavedEdits()")
    last_save = evaluate(run.session, f"{ROOT}.lastSave")
    run.check("P-Z7/zoom-only", after["revision"] == opened["revision"] and unsaved is False and last_save is None,
              {"revision": [opened["revision"], after["revision"]], "hasUnsavedEdits": unsaved, "lastSave": last_save})


def paint_f100(run):
    run.goto("F100", *F100)
    menu = evaluate(run.session, "(()=>{const r=document.querySelector('[data-color-menu=\"backColor\"]').getBoundingClientRect();"
                                 "return [r.left+r.width/2,r.top+r.height/2];})()")
    run.click(*menu)
    swatch = evaluate(run.session, "(()=>{const r=document.querySelector('[data-swatch=\"#ff0000\"]').getBoundingClientRect();"
                                   "return [r.left+r.width/2,r.top+r.height/2];})()")
    run.click(*swatch)
    time.sleep(.5)
    run.idle()
    cell = evaluate(run.session, CELL % F100)
    if cell.get("backColor") != "#ff0000":
        raise RuntimeError(f"F100 was not painted: {cell}")
    return run.state()["revision"]


def level_checks(run, zoom, painted):
    run.goto("F100", *F100)
    run.key("ArrowDown")
    wait(run.session, f"{ROOT}.state.cell?.row===100", 15)
    time.sleep(.8)
    m = run.measure()
    clicked = None
    if m["box"]:
        run.click((m["box"][0] + m["box"][2]) / 2, (m["box"][1] + m["box"][3]) / 2)
        time.sleep(.5)
        clicked = run.measure()
    scale = m["scale"]
    run.check(f"P-Z2/{zoom}", bool(m["tiles"]) and all(f":{scale}:" in t["key"] and t["width"] == -(-t["css"] // 1)
                                                       for t in m["tiles"])
              and abs(m["surface"] - -(-m["documentCss"] // 1)) <= 1,
              {"scale": scale, "tiles": len(m["tiles"]), "badTiles": [t for t in m["tiles"] if f":{scale}:" not in t["key"]
                                                                       or t["width"] != -(-t["css"] // 1)][:4],
               "surface": m["surface"], "documentCss": m["documentCss"]})
    run.check(f"P-Z3/{zoom}", clicked is not None and clicked["cell"] == list(F100) and near(clicked["box"], clicked["active"], 2),
              {"before": m["cell"], "after": clicked and clicked["cell"], "redBox": clicked and clicked["box"],
               "activeBox": clicked and clicked["active"]})
    a = (clicked or m)["active"]
    run.check(f"P-Z4/{zoom}", clicked is not None and near((clicked or m)["column"], [a[0], a[2]], 1)
              and near((clicked or m)["row"], [a[1], a[3]], 1),
              {"column": (clicked or m)["column"], "row": (clicked or m)["row"], "active": a})
    run.check(f"P-Z7/{zoom}", m["revision"] == painted, {"revision": m["revision"], "painted": painted})


def zoom_walk(run, levels, painted):
    """100 -> down to the lowest, then up to the highest, one click at a time; P-Z5 on every click."""
    seen = {100}
    level_checks(run, 100, painted)
    order = [("out", p) for p in sorted((p for p in levels if p < 100), reverse=True)]
    order += [("in", p) for p in levels[1:]]
    for button, target in order:
        run.goto("F100", *F100)
        evaluate(run.session, CENTRE_ON)
        time.sleep(1.0)
        run.idle()
        before = evaluate(run.session, CENTRE)
        label = run.press(button)
        after = evaluate(run.session, CENTRE)
        ok = (label == f"{target}%" and None not in (before["row"], after["row"], before["column"], after["column"])
              and abs(after["row"] - before["row"]) <= 1 and abs(after["column"] - before["column"]) <= 1)
        run.check(f"P-Z5/{button}-{target}", ok, {"label": label, "before": before, "after": after})
        if target not in seen:
            seen.add(target)
            level_checks(run, target, painted)


def p_z6(run):
    while run.controls()["zoom"] > 150:
        run.press("out")
    run.goto("F100", *F100)
    run.hands.text("縮放")
    wait(run.session, f"{ROOT}.state.editing==='inline'", 15)
    font = evaluate(run.session, "getComputedStyle(document.querySelector('#cell-editor')).fontSize")
    run.key("Enter")
    time.sleep(.5)
    run.idle()
    cell = evaluate(run.session, CELL % F100)
    run.check("P-Z6/type", run.controls()["zoom"] == 150 and font == "21px" and cell.get("text") == "縮放",
              {"zoom": run.controls()["zoom"], "fontSize": font, "F100": cell})


def p_z8(run):
    while run.controls()["zoom"] > 75:
        run.press("out")
    tabs = run.dom()["tabs"]
    run.click(*tabs[1]["center"])
    wait(run.session, f"{ROOT}.state.currentPart===1 && !{ROOT}.state.busy", 30)
    run.settle(75)
    run.click(*run.dom()["tabs"][0]["center"])
    wait(run.session, f"{ROOT}.state.currentPart===0 && !{ROOT}.state.busy", 30)
    run.settle(75)
    label = run.controls()["level"]["text"]
    run.goto("F100", *F100)
    run.key("ArrowDown")
    time.sleep(.8)
    m = run.measure()
    clicked = None
    if m["box"]:
        run.click((m["box"][0] + m["box"][2]) / 2, (m["box"][1] + m["box"][3]) / 2)
        time.sleep(.5)
        clicked = run.measure()
    run.check("P-Z8/sheets", label == "75%" and clicked is not None and clicked["cell"] == list(F100)
              and near(clicked["box"], clicked["active"], 2),
              {"label": label, "after": clicked and clicked["cell"], "redBox": clicked and clicked["box"],
               "activeBox": clicked and clicked["active"]})


def scenario(run, record):
    levels = evaluate(run.session, LEVELS)
    record["levels"] = levels
    try:
        p_z1_z7a(run, levels, record)
    except Exception as error:  # noqa: BLE001  one cell's crash is that cell's red; the next cell runs
        run.check("P-Z1/crash", False, repr(error))
    painted = paint_f100(run)
    for step in (lambda: zoom_walk(run, levels, painted), lambda: p_z6(run), lambda: p_z8(run)):
        try:
            step()
        except Exception as error:  # noqa: BLE001
            run.check("P-Z-step/crash", False, repr(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--mutate", choices=sorted(MUTATIONS))
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = mirror(out, args.engine, args.mutate)
    fixture = create(out / "fixture")
    port = free_port()
    log = (out / "server.txt").open("w")
    server = subprocess.Popen(["python3", str(PROJECT / "web/serve.py"), "--port", str(port), "--root", str(root)], stdout=log,
                              stderr=subprocess.STDOUT)
    report = {"tool": {"path": "wasm_sdk_probe/tools/check_calc_zoom.py", "sha256": sha(__file__), "argv": sys.argv[1:]},
              "engine": str(args.engine), "wasm": sha(args.engine / "probe.wasm"), "worker": sha(args.engine / "sdk-worker.js"),
              "page": {n: sha(root / n) for n in ("ods-editor-app.js", "ods-editor.html", "spreadsheet-shell/calc-editor-session.js",
                                                   "spreadsheet-shell/calc-document-sdk.js", "viewer-shell/ods-viewer-session.js")},
              "mutate": args.mutate, "fixture": sha(fixture), "runs": []}
    try:
        wait_page(f"http://127.0.0.1:{port}/ods-editor.html")
        with browser_lock("calc-zoom", wait_s=0):
            for browser in args.browsers.split(","):
                session = None
                record = {"browser": browser, "checks": [], "error": None}
                report["runs"].append(record)
                try:
                    session = open_browser(browser, cs.WINDOW)
                    record["version"] = session.version
                    navigate(session, f"http://127.0.0.1:{port}/ods-editor.html?diagnostics=1")
                    session.set_file("#file-input", fixture)
                    wait(session, f"Boolean({ROOT}.state?.cell) && {ROOT}.state.zoomSupported===true", 120)
                    wait(session, f"document.querySelectorAll('#row-headers [role=rowheader]').length>0 && {ROOT}.headers?.zoom===100", 30)
                    if not evaluate(session, f"{ROOT}.state.zoomSupported===true"):
                        raise RuntimeError("the engine under test has no cell-zoom capability")
                    scenario(Run(session, record), record)
                except Exception as error:  # noqa: BLE001  a crash is a result; keep the cells already read
                    record["error"] = repr(error)
                    if session:
                        (out / f"{browser}-failure.png").write_bytes(session.screenshot())
                finally:
                    if session:
                        (out / f"{browser}-last.png").write_bytes(session.screenshot())
                        record["cleanup"] = close_browser(session)
                    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()
    red = sorted({c["id"].split("/")[0] for r in report["runs"] for c in r["checks"] if not c["pass"]})
    if args.mutate:
        wanted, policy = MUTATIONS[args.mutate][3:]
        hit = [w in red for w in wanted]
        ok = all(not r["error"] for r in report["runs"]) and (all(hit) if policy == "all" else any(hit))
        report["verdict"] = "MUTATION_RED" if ok else "MUTATION_NOT_RED"
    else:
        ok = bool(report["runs"]) and all(not r["error"] and r["checks"] and all(c["pass"] for c in r["checks"]) for r in report["runs"])
        report["verdict"] = "P_HOLDS" if ok else "P_RED"
    report["redCriteria"] = red
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"verdict": report["verdict"], "redCriteria": red,
                      "runs": [{"browser": r["browser"], "version": r.get("version"), "error": r["error"],
                                "passed": sum(c["pass"] for c in r["checks"]), "checks": len(r["checks"]),
                                "red": [c["id"] for c in r["checks"] if not c["pass"]][:12]} for r in report["runs"]]},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
