#!/usr/bin/env python3
"""SPEC-P-calc-headers 4.2: P-H1..P-H6 on the Calc page, Chrome and Firefox, on a private mirror of the live page sources with the
engine under test (the development profile build/ods/editor-v6/profile before the hand-test slot).  Real pointer and keys; the
viewport is scrolled by script only as setup.  Every check is recorded and the run goes on past a red one.

  check_calc_headers.py --out NEW_DIR --engine PROFILE_DIR [--browsers chrome,firefox] [--mutate NAME]

--mutate applies one of the spec's red cases to the mirrored page and exits 0 only if the checks it names turn red:
  header-left-plus-1    every column header drawn 1 px right            -> P-H1
  whole-endrow-visible  a whole column ends at row 41, not the sheet's end -> P-H2, P-H4
  hidden-1px            the hidden column D drawn as a 1 px header       -> P-H1
  shift-space-types     Shift+Space not caught: the space starts an entry -> P-H5
Without --mutate: exit 0 iff every check of every browser passes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from check_calc_sheet_view import Hands, wait
from create_calc_headers_fixture import create
from r7_support import evaluate, wait_page
from run_browser_probe import free_port
from run_e2_c_page_smoke import navigate
from v21_shakedown_common import browser_lock, close_browser, open_browser

PROJECT = Path(__file__).resolve().parents[1]
WINDOW = (1440, 1000)
ROOT = "window.__calcEditor"
ROWS, COLUMNS = 1048576, 16384
MUTATIONS = {
    "header-left-plus-1": ("ods-editor-app.js", 'if(axis==="column"){node.style.left=start;',
                           'if(axis==="column"){node.style.left=`${entry.startPx+1}px`;', ["P-H1"]),
    "whole-endrow-visible": ("spreadsheet-shell/calc-editor-session.js", "row: rows ? low : 0, endRow: rows ? high : SHEET_ROWS - 1,",
                             "row: rows ? low : 0, endRow: rows ? high : 40,", ["P-H2", "P-H4"]),
    "hidden-1px": ("ods-editor-app.js", 'headerData.columns.filter(e=>!e.hidden).map(e=>headerButton("column",e))',
                   'headerData.columns.map(e=>headerButton("column",e.hidden ? {...e,endPx:e.startPx+1} : e))', ["P-H1"]),
    "shift-space-types": ("ods-editor-app.js", 'const kind=event.ctrlKey ? "columns" : event.shiftKey ? "rows" : null;',
                          'const kind=event.ctrlKey ? "columns" : null;', ["P-H5"]),
}
DOM = """(()=>{const s=document.querySelector('#surface').getBoundingClientRect();
 const pick=(sel,axis)=>[...document.querySelectorAll(sel)].map(b=>{const r=b.getBoundingClientRect();
   return {index:+b.dataset.index,label:b.textContent,start:axis==='c'?r.left-s.left:r.top-s.top,size:axis==='c'?r.width:r.height,
     aria:b.getAttribute('aria-label'),tab:b.tabIndex,selected:b.getAttribute('aria-selected'),
     center:[r.left+r.width/2,r.top+r.height/2]};});
 const c=document.querySelector('#corner-header').getBoundingClientRect();
 return {columns:pick('#column-headers [role=columnheader]','c'),rows:pick('#row-headers [role=rowheader]','r'),
   corner:{selected:document.querySelector('#corner-header').getAttribute('aria-selected'),center:[c.left+c.width/2,c.top+c.height/2]},
   record:window.__calcEditor.headers,toast:document.querySelector('#toast').textContent,
   label:document.querySelector('#selection-label').textContent,
   scroll:[document.querySelector('#viewport').scrollLeft,document.querySelector('#viewport').scrollTop],
   view:(()=>{const v=document.querySelector('#viewport'),r=v.getBoundingClientRect();
     return [r.left+48,r.top+20,r.left+v.clientWidth,r.top+v.clientHeight];})()};})()"""
READ = "(async()=>{const d=window.__calcEditor.session.document,out=[];for(const [c,r] of ARGS){const {cell}=await d.readCell(c,r);out.push(cell);}return out;})()"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mirror(out, engine, mutate):
    root = PROJECT / "build/calc-headers" / out.name
    root.mkdir(parents=True, exist_ok=False)
    for directory in ("sdk", "viewer-shell", "spreadsheet-shell"):
        shutil.copytree(PROJECT / directory, root / directory)
    page = (PROJECT / "web/ods-editor-app.js").read_text(encoding="utf-8")
    for name in ("ods-editor-v5", "ods-editor-v6", "ods-editor-v7", "ods-editor-v8"):
        page = page.replace(f"./profiles/{name}/sdk-worker.js", "./profiles/under-test/sdk-worker.js")
    if "./profiles/under-test/sdk-worker.js" not in page:
        raise SystemExit("the page names no engine this tool knows")
    (root / "ods-editor-app.js").write_text(page, encoding="utf-8")
    shutil.copyfile(PROJECT / "web/ods-editor.html", root / "ods-editor.html")
    if mutate:
        name, old, new, _ = MUTATIONS[mutate]
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
        time.sleep(.4)

    def dom(self):
        return evaluate(self.session, DOM)

    def read(self, cells):
        return evaluate(self.session, READ.replace("ARGS", json.dumps(cells)))

    def headers_settled(self):
        """The newest header reply answers the current scroll position and the page has drawn it."""
        return wait(self.session, f"""(()=>{{const h={ROOT}.headers,v=document.querySelector('#viewport');
          return h && h.rectangle.x===Math.round(v.scrollLeft*15) && h.rectangle.y===Math.round(v.scrollTop*15)
            && document.querySelectorAll('#column-headers [role=columnheader]').length>0;}})()""", 20)

    def click(self, x, y, shift=False):
        if not shift:
            self.hands.click(x, y)
        elif self.hands.chrome:
            self.session.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "modifiers": 8})
            for kind in ("mousePressed", "mouseReleased"):
                self.session.call("Input.dispatchMouseEvent", {"type": kind, "x": x, "y": y, "button": "left", "clickCount": 1, "modifiers": 8})
        else:
            self.session.command("POST", "/actions", {"actions": [
                {"type": "key", "id": "keys", "actions": [{"type": "keyDown", "value": ""}, {"type": "pause", "duration": 0},
                                                          {"type": "pause", "duration": 0}, {"type": "pause", "duration": 0},
                                                          {"type": "keyUp", "value": ""}]},
                {"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"}, "actions": [
                    {"type": "pause", "duration": 0}, {"type": "pointerMove", "duration": 0, "origin": "viewport", "x": round(x), "y": round(y)},
                    {"type": "pointerDown", "button": 0}, {"type": "pointerUp", "button": 0}, {"type": "pause", "duration": 0}]}]})
            self.session.command("DELETE", "/actions")
        self.idle()

    def drag(self, start, end):
        steps = [(start[0] + (end[0] - start[0]) * i / 6, start[1] + (end[1] - start[1]) * i / 6) for i in range(1, 7)]
        if self.hands.chrome:
            self.session.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": start[0], "y": start[1]})
            self.session.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": start[0], "y": start[1], "button": "left", "clickCount": 1})
            for x, y in steps:
                self.session.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "button": "left", "buttons": 1})
                time.sleep(.15)
            self.session.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": end[0], "y": end[1], "button": "left", "clickCount": 1})
        else:
            moves = [{"type": "pointerMove", "duration": 150, "origin": "viewport", "x": round(x), "y": round(y)} for x, y in steps]
            self.session.command("POST", "/actions", {"actions": [{"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"},
                "actions": [{"type": "pointerMove", "duration": 0, "origin": "viewport", "x": round(start[0]), "y": round(start[1])},
                            {"type": "pointerDown", "button": 0}, *moves, {"type": "pointerUp", "button": 0}]}]})
        self.idle()
        time.sleep(.6)
        self.idle()

    def space(self, ctrl=False, shift=False):
        if self.hands.chrome:
            modifiers = (2 if ctrl else 0) | (8 if shift else 0)
            base = {"key": " ", "code": "Space", "windowsVirtualKeyCode": 32, "modifiers": modifiers}
            self.session.call("Input.dispatchKeyEvent", {"type": "keyDown", **base, **({} if ctrl else {"text": " "})})
            self.session.call("Input.dispatchKeyEvent", {"type": "keyUp", **base})
        else:
            held = ([""] if ctrl else []) + ([""] if shift else [])
            actions = [{"type": "keyDown", "value": k} for k in held] + [{"type": "keyDown", "value": " "}, {"type": "keyUp", "value": " "}]
            actions += [{"type": "keyUp", "value": k} for k in reversed(held)]
            self.session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keys", "actions": actions}]})
            self.session.command("DELETE", "/actions")
        self.idle()


def p_h1(run, where):
    """Each drawn header against the reply it was drawn from and against the engine's own cell geometry; hidden ones absent."""
    run.headers_settled()
    dom = run.dom()
    reply = dom["record"]["reply"]
    for axis, key in (("columns", "c"), ("rows", "r")):
        drawn = {e["index"]: e for e in dom[axis]}
        entries = {e["index"]: e for e in reply[axis]}
        visible = sorted(i for i, e in entries.items() if not e["hidden"])
        hidden = sorted(i for i, e in entries.items() if e["hidden"])
        geometry = run.read([[i, 0] if axis == "columns" else [0, i] for i in visible])
        cells = []
        for i, cell in zip(visible, geometry):
            e, d = entries[i], drawn.get(i)
            pos, size = (cell["xTwips"], cell["widthTwips"]) if axis == "columns" else (cell["yTwips"], cell["heightTwips"])
            ok = (d is not None and abs(d["start"] - e["startPx"]) < .6 and abs(d["size"] - (e["endPx"] - e["startPx"])) < .6
                  and d["label"] == e["label"] and pos == e["startPx"] * 15 and size + 1 == (e["endPx"] - e["startPx"]) * 15
                  and bool(d["aria"]) and d["tab"] == -1)
            cells.append({"index": i, "label": e["label"], "drawn": d and [round(d["start"], 2), round(d["size"], 2)],
                          "reply": [e["startPx"], e["endPx"]], "twips": [pos, size], "ok": ok})
        extra = sorted(set(drawn) - set(visible))
        run.check(f"P-H1/{where}/{axis}", cells and all(c["ok"] for c in cells) and not extra,
                  {"checked": len(cells), "red": [c for c in cells if not c["ok"]][:4], "drawnNotVisible": extra, "hiddenInReply": hidden})
        # P-H6, the per-instance half: every header element has a name and stays out of the Tab order.
        run.check(f"P-H6/{where}/{axis}", dom[axis] and all(d["aria"] and d["tab"] == -1 for d in dom[axis]),
                  {"elements": len(dom[axis])})
    return dom


def whole_ok(state, kind, low, high):
    s = state["selection"] or {}
    if kind == "columns":
        return (s.get("whole") == "columns" and s.get("column") == low and s.get("endColumn") == high and s.get("row") == 0
                and s.get("endRow") == ROWS - 1)
    if kind == "rows":
        return (s.get("whole") == "rows" and s.get("row") == low and s.get("endRow") == high and s.get("column") == 0
                and s.get("endColumn") == COLUMNS - 1)
    return s.get("whole") == "sheet" and s.get("endColumn") == COLUMNS - 1 and s.get("endRow") == ROWS - 1


def clickable(dom, header, axis):
    """Core returns two indices past each edge: only a header whose centre is in the uncovered viewport is under the pointer
    (a column header's centre along x, a row header's along y; the other coordinate is the strip's own)."""
    x, y = header["center"]
    left, top, right, bottom = dom["view"]
    return left <= x < right if axis == "columns" else top <= y < bottom


def p_h2(run, dom, where, limit=None):
    for axis, kind in (("columns", "columns"), ("rows", "rows")):
        targets = [h for h in dom[axis] if clickable(dom, h, axis)]
        run.check(f"P-H2/{where}/{axis}/targets", bool(targets), {"clickable": [h["label"] for h in targets], "drawn": len(dom[axis])})
        for header in targets:
            i = header["index"]
            run.click(*header["center"])
            state, after = run.state(), run.dom()
            mine = next((d for d in after[axis] if d["index"] == i), {})
            others = [d["index"] for d in after[axis] if d["index"] != i and d["selected"] == "true"]
            cell = state["cell"] or {}
            at = (cell.get("column"), cell.get("row")) == ((i, 0) if kind == "columns" else (0, i))
            label = f"{header['label']}:{header['label']}"
            run.check(f"P-H2/{where}/{axis}/{header['label']}",
                      whole_ok(state, kind, i, i) and at and after["label"].startswith(label) and mine.get("selected") == "true" and not others,
                      {"selection": {k: (state["selection"] or {}).get(k) for k in ("whole", "column", "row", "endColumn", "endRow")},
                       "cell": [cell.get("column"), cell.get("row")], "label": after["label"], "selected": mine.get("selected"), "others": others})
            run.check(f"P-H6/{where}/toast/{header['label']}", header["label"] in after["toast"], after["toast"])
    run.click(*dom["corner"]["center"])
    state, after = run.state(), run.dom()
    run.check(f"P-H2/{where}/corner", whole_ok(state, "sheet", 0, 0) and after["corner"]["selected"] == "true",
              {"selection": state["selection"] and {k: state["selection"].get(k) for k in ("whole", "endColumn", "endRow")},
               "corner": after["corner"]["selected"], "toast": after["toast"]})


def by_label(dom, axis, label):
    return next(d for d in dom[axis] if d["label"] == label)


def p_h3(run, dom):
    cases = [("columns", "C", "E", "shift"), ("columns", "E", "B", "shift"), ("columns", "B", "E", "drag"), ("columns", "E", "B", "drag"),
             ("rows", "2", "5", "shift"), ("rows", "5", "2", "drag")]
    for axis, a, b, how in cases:
        ha, hb = by_label(dom, axis, a), by_label(dom, axis, b)
        if how == "shift":
            run.click(*ha["center"])
            run.click(*hb["center"], shift=True)
        else:
            run.drag(ha["center"], hb["center"])
        state = run.state()
        low, high = sorted((ha["index"], hb["index"]))
        run.check(f"P-H3/{axis}/{a}-{b}/{how}", whole_ok(state, axis, low, high),
                  {k: (state["selection"] or {}).get(k) for k in ("whole", "column", "row", "endColumn", "endRow", "first", "last")})


def p_h4(run, dom):
    c = by_label(dom, "columns", "C")
    run.click(*c["center"])
    bold = evaluate(run.session, "(()=>{const r=document.querySelector('[data-format=\"bold\"]').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2];})()")
    run.click(*bold)
    state = run.state()
    cells = run.read([[2, 0], [2, 999]])
    pressed = evaluate(run.session, "document.querySelector('[data-format=\"bold\"]').getAttribute('aria-pressed')")
    undo = evaluate(run.session, "(()=>{const b=document.querySelector('#undo-button');const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,b.disabled,b.hidden];})()")
    run.click(undo[0], undo[1])
    back = run.read([[2, 0], [2, 999]])
    run.check("P-H4/bold-whole-column-C", whole_ok(state, "columns", 2, 2) and (state["rangeFormat"] or {}).get("bold") is True
              and pressed == "true" and all(x["bold"] for x in cells) and not any(x["bold"] for x in back),
              {"rangeBold": (state["rangeFormat"] or {}).get("bold"), "pressed": pressed, "bold": [x["bold"] for x in cells],
               "afterUndo": [x["bold"] for x in back], "undoButton": undo[2:]})


def p_h5(run, dom):
    b2 = [by_label(dom, "columns", "B"), by_label(dom, "rows", "2")]
    surface = evaluate(run.session, "(()=>{const r=document.querySelector('#surface').getBoundingClientRect();return [r.left,r.top];})()")
    cell_center = lambda: (surface[0] + b2[0]["start"] + b2[0]["size"] / 2, surface[1] + b2[1]["start"] + b2[1]["size"] / 2)  # noqa: E731
    before = run.read([[1, 1]])[0]["input"]
    for name, ctrl, shift, kind, low in (("ctrl-space", True, False, "columns", 1), ("ctrl-shift-space", True, True, "columns", 1),
                                         ("shift-space", False, True, "rows", 1)):
        run.click(*cell_center())
        run.space(ctrl=ctrl, shift=shift)
        time.sleep(.5)
        state = run.state()
        pending = evaluate(run.session, f"{ROOT}.inputState ? {ROOT}.inputState().pending : 'no-diagnostics'")
        after = run.read([[1, 1]])[0]["input"]
        run.check(f"P-H5/{name}", whole_ok(state, kind, low, low) and state["editing"] is None and pending is None and after == before,
                  {"selection": {k: (state["selection"] or {}).get(k) for k in ("whole", "column", "row", "endColumn", "endRow")},
                   "editing": state["editing"], "pending": pending, "b2": [before, after]})
        if state["editing"] is not None or pending:
            evaluate(run.session, f"{ROOT}.session.cancelEdit()")  # leave no entry behind for the next case
            run.idle()


def scenario(run):
    dom = p_h1(run, "top-left")
    p_h2(run, dom, "top-left")
    p_h3(run, dom)
    p_h4(run, dom)
    p_h5(run, dom)
    # Far away: AA and row 1000, scrolled by script (setup), then measured and clicked like the rest.
    evaluate(run.session, "(()=>{const v=document.querySelector('#viewport');v.scrollLeft=2100;v.scrollTop=16900;return true;})()")
    time.sleep(1.0)
    run.idle()
    far = p_h1(run, "aa-row-1000")
    labels = {"columns": [d["label"] for d in far["columns"]], "rows": [d["label"] for d in far["rows"]]}
    run.check("P-H1/aa-row-1000/reached", "AA" in labels["columns"] and "1000" in labels["rows"], labels)
    targets = {"columns": [d for d in far["columns"] if d["label"] == "AA"], "rows": [d for d in far["rows"] if d["label"] == "1000"]}
    p_h2(run, {**far, **targets}, "aa-row-1000")


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
    server = subprocess.Popen(["python3", str(PROJECT / "web/serve.py"), "--port", str(port), "--root", str(root)], stdout=log, stderr=subprocess.STDOUT)
    report = {"tool": {"path": "wasm_sdk_probe/tools/check_calc_headers.py", "sha256": sha(__file__), "argv": sys.argv[1:]},
              "engine": str(args.engine), "wasm": sha(args.engine / "probe.wasm"), "worker": sha(args.engine / "sdk-worker.js"),
              "page": {n: sha(root / n) for n in ("ods-editor-app.js", "ods-editor.html", "spreadsheet-shell/calc-editor-session.js",
                                                   "spreadsheet-shell/calc-document-sdk.js")},
              "mutate": args.mutate, "fixture": sha(fixture), "runs": []}
    try:
        wait_page(f"http://127.0.0.1:{port}/ods-editor.html")
        with browser_lock("calc-headers", wait_s=0):
            for browser in args.browsers.split(","):
                session = None
                record = {"browser": browser, "checks": [], "error": None}
                report["runs"].append(record)
                try:
                    session = open_browser(browser, WINDOW)
                    record["version"] = session.version
                    navigate(session, f"http://127.0.0.1:{port}/ods-editor.html?diagnostics=1")
                    session.set_file("#file-input", fixture)
                    wait(session, f"Boolean({ROOT}.state?.cell) && {ROOT}.state.headersSupported===true", 120)
                    scenario(Run(session, record))
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
        wanted = MUTATIONS[args.mutate][3]
        ok = all(not r["error"] for r in report["runs"]) and all(w in red for w in wanted)
        report["verdict"] = "MUTATION_RED" if ok else "MUTATION_NOT_RED"
    else:
        ok = bool(report["runs"]) and all(not r["error"] and r["checks"] and all(c["pass"] for c in r["checks"]) for r in report["runs"])
        report["verdict"] = "P_HOLDS" if ok else "P_RED"
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"verdict": report["verdict"], "redCriteria": red,
                      "runs": [{"browser": r["browser"], "error": r["error"], "passed": sum(c["pass"] for c in r["checks"]),
                                "checks": len(r["checks"]), "red": [c["id"] for c in r["checks"] if not c["pass"]][:12]} for r in report["runs"]]},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
