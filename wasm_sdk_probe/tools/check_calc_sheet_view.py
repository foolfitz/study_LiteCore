#!/usr/bin/env python3
"""SPEC-P-demo-batch-1 section 2: each sheet keeps its own view.

The owner's path, on a private mirror of the live sources: real pointer on the
tab, real wheel on the viewport, real keys.  Every check is recorded and the run
goes on past a red one, so a red run shows the whole symptom and not its first
line.  The page state is read from the page's own record and from the viewport;
a screenshot after the return to sheet 1 stays with the report for a human.

  check_calc_sheet_view.py --out DIR [--browsers chrome,firefox] [--pages editor,viewer]
"""
import argparse
import base64
import hashlib
import io
import json
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from create_calc_sheet_view_fixture import create, SHEETS
from r7_support import evaluate, wait_page
from run_browser_probe import ChromeSession, free_port
from run_e2_c_page_smoke import navigate
from v21_shakedown_common import browser_lock, close_browser, open_browser

PROJECT = Path(__file__).resolve().parents[1]
WINDOW = (1440, 1000)
GLOBAL = {"editor": "window.__calcEditor", "viewer": "window.__odsViewer"}
PAGE = {"editor": "ods-editor.html", "viewer": "ods-viewer.html"}
ROW_SLACK_PX = 40
TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
KEYS = {"ArrowDown": (40, ""), "Enter": (13, "")}


def mirror(out):
    """The live sources; the engines stay the frozen profiles under dist/."""
    root = PROJECT / "build/calc-sheet-view" / out.name
    root.mkdir(parents=True, exist_ok=False)
    for name in ("ods-editor.html", "ods-editor-app.js", "ods-viewer.html", "ods-viewer-app.js"):
        shutil.copyfile(PROJECT / "web" / name, root / name)
    for directory in ("sdk", "viewer-shell", "spreadsheet-shell"):
        shutil.copytree(PROJECT / directory, root / directory)
    (root / "reader-shell").mkdir()
    shutil.copyfile(PROJECT / "reader-shell/tile-scheduler.js", root / "reader-shell/tile-scheduler.js")
    (root / "profiles").mkdir()
    for name in ("ods-editor-v2", "ods-editor-v3", "ods-editor-v4", "ods-editor-v5", "ods-editor-v6", "ods-viewer-v3", "resources"):  # v4, v5: 2026-11-03; v6: 2026-11-05
        (root / "profiles" / name).symlink_to(PROJECT / "dist/profiles" / name, target_is_directory=True)
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()
              and "profiles" not in p.relative_to(root).parts}
    (out / "mirror-sources.json").write_text(json.dumps({"root": str(root), "sha256": hashes}, indent=2) + "\n")
    return root


class Hands:
    """Real input.  Chrome through CDP, Firefox through WebDriver actions."""

    def __init__(self, session):
        self.session, self.chrome = session, isinstance(session, ChromeSession)

    def click(self, x, y):
        if self.chrome:
            self.session.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
            for kind in ("mousePressed", "mouseReleased"):
                self.session.call("Input.dispatchMouseEvent",
                                  {"type": kind, "x": x, "y": y, "button": "left", "clickCount": 1})
        else:
            self.session.command("POST", "/actions", {"actions": [{
                "type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"}, "actions": [
                    {"type": "pointerMove", "duration": 0, "origin": "viewport", "x": round(x), "y": round(y)},
                    {"type": "pointerDown", "button": 0}, {"type": "pointerUp", "button": 0}]}]})

    def wheel(self, x, y, dx, dy):
        if self.chrome:
            self.session.call("Input.dispatchMouseEvent",
                              {"type": "mouseWheel", "x": x, "y": y, "deltaX": dx, "deltaY": dy})
        else:
            self.session.command("POST", "/actions", {"actions": [{
                "type": "wheel", "id": "wheel", "actions": [
                    {"type": "scroll", "x": round(x), "y": round(y), "deltaX": dx, "deltaY": dy,
                     "duration": 0, "origin": "viewport"}]}]})

    def key(self, name):
        code, webdriver = KEYS[name]
        if self.chrome:
            for kind in ("rawKeyDown", "keyUp"):
                self.session.call("Input.dispatchKeyEvent",
                                  {"type": kind, "key": name, "code": name, "windowsVirtualKeyCode": code})
        else:
            self.session.command("POST", "/actions", {"actions": [{
                "type": "key", "id": "keys", "actions": [
                    {"type": "keyDown", "value": webdriver}, {"type": "keyUp", "value": webdriver}]}]})

    def text(self, value):
        if self.chrome:
            self.session.call("Input.insertText", {"text": value})
        else:
            active = self.session.command("GET", "/element/active")
            element = next(iter(active.values()))
            self.session.command("POST", f"/element/{element}/value", {"text": value})


def wait(session, expression, timeout=60):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = evaluate(session, expression)
        if last:
            return last
        time.sleep(.1)
    return last


VIEW = ("(()=>{const v=document.querySelector('#viewport');return {scrollTop:v.scrollTop,"
        "scrollLeft:v.scrollLeft,scrollHeight:v.scrollHeight,clientHeight:v.clientHeight,"
        "scrollWidth:v.scrollWidth,clientWidth:v.clientWidth};})()")
RECT = "(()=>{const r=document.querySelector(%s).getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];})()"
TILES = """(()=>{const v=document.querySelector('#viewport').getBoundingClientRect();
 const visible=[...document.querySelectorAll('#tiles canvas')].filter(c=>{const r=c.getBoundingClientRect();
  return r.right>v.left&&r.left<v.right&&r.bottom>v.top&&r.top<v.bottom;});
 let ink=0;for(const c of visible){const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
  for(let i=0;i<d.length;i+=4)if(d[i+3]>0&&d[i]<128)ink++;}
 return {count:visible.length,keys:visible.map(c=>c.dataset.key),ink};})()"""


def settle_scroll(session):
    last, stable = None, 0
    for _ in range(60):
        view = evaluate(session, VIEW)
        stable = stable + 1 if view == last else 0
        if stable >= 3:
            return view
        last = view
        time.sleep(.1)
    return last


class Run:
    def __init__(self, session, page, record):
        self.session, self.page, self.record = session, page, record
        self.hands = Hands(session)
        self.root = GLOBAL[page]

    def check(self, name, passed, actual):
        self.record["checks"].append({"id": name, "pass": bool(passed), "actual": actual})

    def state(self):
        return evaluate(self.session, f"{self.root}.state")

    def idle(self):
        if self.page == "editor":
            wait(self.session, f"{self.root}.state && !{self.root}.state.busy && !{self.root}.state.selectionPending")

    def cell(self):
        cell = self.state().get("cell") if self.page == "editor" else None
        return [cell["column"], cell["row"]] if cell else None

    def centre(self):
        return evaluate(self.session, RECT % json.dumps("#viewport"))

    def tab(self, part):
        selector = f'#tab-strip [data-part="{part}"]'
        self.hands.click(*evaluate(self.session, RECT % json.dumps(selector)))
        wait(self.session, f"{self.root}.state.currentPart==={part}", 30)
        self.idle()
        view = settle_scroll(self.session)
        return view

    def scroll(self, dx, dy):
        self.hands.wheel(*self.centre(), dx, dy)
        return settle_scroll(self.session)

    def painted(self, part, step):
        """C3: tiles of this sheet, in the window, with ink.  Waits for the paint."""
        deadline, tiles = time.monotonic() + 30, None
        while time.monotonic() < deadline:
            tiles = evaluate(self.session, TILES)
            if tiles["count"] and tiles["ink"] and all(k.split(":")[2] == str(part) for k in tiles["keys"]):
                break
            time.sleep(.2)
        self.check(f"C3/{step}", tiles and tiles["count"] and tiles["ink"]
                   and all(k.split(":")[2] == str(part) for k in tiles["keys"]),
                   {"part": self.state().get("currentPart"), **(tiles or {})})

    def first_visit(self, part, step, view):
        self.check(f"C1/{step}", view["scrollTop"] == 0 and view["scrollLeft"] == 0
                   and (self.page == "viewer" or self.cell() == [0, 0]),
                   {"view": view, "cell": self.cell(), "part": self.state().get("currentPart")})
        self.painted(part, step)

    def returned(self, part, step, view, left):
        self.check(f"C2/{step}", view["scrollTop"] == left["scrollTop"] and view["scrollLeft"] == left["scrollLeft"]
                   and (self.page == "viewer" or self.cell() == left["cell"]),
                   {"view": view, "cell": self.cell(), "left": left, "part": self.state().get("currentPart")})
        self.painted(part, step)


def cells_of(data):
    """{(sheet index, row, column): text}, the repeats expanded."""
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("content.xml"))
    out = {}
    for sheet, table in enumerate(root.iter(TABLE + "table")):
        row_index = 0
        for row in table.iter(TABLE + "table-row"):
            rows = int(row.get(TABLE + "number-rows-repeated", "1"))
            column = 0
            for cell in row:
                if not cell.tag.endswith("table-cell"):
                    continue
                columns = int(cell.get(TABLE + "number-columns-repeated", "1"))
                text = "\n".join("".join(p.itertext()) for p in cell.iter(TEXT + "p"))
                if text:
                    for r in range(rows):
                        for c in range(columns):
                            out[(sheet, row_index + r, column + c)] = text
                column += columns
            row_index += rows
    return out


def editor(run, out, name, source):
    session = run.session
    first = dict(run.scroll(600, 2500))
    run.check("setup/sheet1-scrolled", first["scrollTop"] > 1000 and first["scrollLeft"] > 100, first)
    run.hands.click(*run.centre())
    run.idle()
    left1 = {**settle_scroll(session), "cell": run.cell()}
    run.check("setup/cell-on-sheet1", left1["cell"] and left1["cell"][1] > 20, left1)
    run.first_visit(1, "first-visit-sheet2", run.tab(1))

    run.scroll(0, 1500)
    run.hands.click(*run.centre())
    run.idle()
    left2 = {**settle_scroll(session), "cell": run.cell()}
    run.check("setup/cell-on-sheet2", left2["cell"] and left2["cell"][1] > 20, left2)
    run.first_visit(2, "first-visit-short-sheet3", run.tab(2))

    run.returned(0, "back-to-sheet1", run.tab(0), left1)
    time.sleep(.5)
    (out / f"{name}-back-to-sheet1.png").write_bytes(session.screenshot())

    run.hands.key("ArrowDown")
    wait(session, f"{run.root}.state.cell?.row==={left1['cell'][1] + 1} && !{run.root}.state.busy", 15)
    view = settle_scroll(session)
    run.check("C4/arrow-from-restored-cell",
              run.cell() == [left1["cell"][0], left1["cell"][1] + 1]
              and abs(view["scrollTop"] - left1["scrollTop"]) <= ROW_SLACK_PX,
              {"cell": run.cell(), "view": view, "left": left1})

    run.returned(1, "back-to-sheet2", run.tab(1), left2)
    target = left2["cell"]
    run.hands.text("VIEW-MARK")
    wait(session, f"{run.root}.state.editing || {run.root}.state.draft==='VIEW-MARK'", 15)
    run.hands.key("Enter")
    wait(session, f"!{run.root}.state.editing && !{run.root}.state.busy", 30)
    run.hands.click(*evaluate(session, RECT % json.dumps("#save-button")))
    wait(session, f"{run.root}.lastSave && !{run.root}.state.busy", 60)
    encoded = evaluate(session, f"""(async()=>{{const b=new Uint8Array({run.root}.lastExport);let s='';
      for(let i=0;i<b.length;i+=8192)s+=String.fromCharCode(...b.subarray(i,i+8192));return btoa(s);}})()""")
    saved = base64.b64decode(encoded) if encoded else None
    if saved:
        (out / f"{name}-saved.ods").write_bytes(saved)
    before, after = cells_of(source.read_bytes()), cells_of(saved) if saved else {}
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    run.check("C5/only-that-cell", changed == [(1, target[1], target[0])]
              and after.get((1, target[1], target[0])) == "VIEW-MARK",
              {"changed": changed[:8], "changedCount": len(changed), "target": [1, target[1], target[0]]})


def viewer(run, out, name):
    session = run.session
    left1 = dict(run.scroll(600, 2500))
    run.check("setup/sheet1-scrolled", left1["scrollTop"] > 1000 and left1["scrollLeft"] > 100, left1)
    run.first_visit(1, "first-visit-sheet2", run.tab(1))
    left2 = dict(run.scroll(0, 1500))
    run.check("setup/sheet2-scrolled", left2["scrollTop"] > 500, left2)
    run.first_visit(2, "first-visit-short-sheet3", run.tab(2))
    run.returned(0, "back-to-sheet1", run.tab(0), left1)
    time.sleep(.5)
    (out / f"{name}-back-to-sheet1.png").write_bytes(session.screenshot())
    run.returned(1, "back-to-sheet2", run.tab(1), left2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--pages", default="editor,viewer")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = mirror(out)
    fixture = create(out / "fixture")
    port = free_port()
    log = (out / "server.txt").open("w")
    server = subprocess.Popen(["python3", str(PROJECT / "web/serve.py"), "--port", str(port), "--root", str(root)],
                              stdout=log, stderr=subprocess.STDOUT)
    report = {"tool": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "fixture": hashlib.sha256(fixture.read_bytes()).hexdigest(),
              "sheets": [list(s) for s in SHEETS], "runs": []}
    try:
        wait_page(f"http://127.0.0.1:{port}/{PAGE['editor']}")
        with browser_lock("calc-sheet-view", wait_s=0):
            for browser in args.browsers.split(","):
                for page in args.pages.split(","):
                    name, session = f"{browser}-{page}", None
                    record = {"browser": browser, "page": page, "checks": [], "error": None}
                    report["runs"].append(record)
                    try:
                        session = open_browser(browser, WINDOW)
                        record["version"] = session.version
                        navigate(session, f"http://127.0.0.1:{port}/{PAGE[page]}?diagnostics=1")
                        session.set_file("#file-input", fixture)
                        run = Run(session, page, record)
                        wait(session, f"{run.root}.state?.state==='ready' && {run.root}.state?.parts>0"
                             if page == "viewer" else f"Boolean({run.root}.state?.cell)", 120)
                        run.painted(0, "opened")
                        if page == "editor":
                            editor(run, out, name, fixture)
                        else:
                            viewer(run, out, name)
                    except Exception as error:  # noqa: BLE001  a crash is a result; keep the cells already read
                        record["error"] = repr(error)
                        if session:
                            try:
                                (out / f"{name}-failure.png").write_bytes(session.screenshot())
                            except Exception:  # noqa: BLE001
                                pass
                    finally:
                        if session:
                            record["cleanup"] = close_browser(session)
                        (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()
    ok = bool(report["runs"]) and all(not r["error"] and r["checks"] and all(c["pass"] for c in r["checks"])
                                      for r in report["runs"])
    print(json.dumps({"pass": ok, "runs": [{
        "browser": r["browser"], "page": r["page"], "error": r["error"],
        "passed": sum(c["pass"] for c in r["checks"]), "checks": len(r["checks"]),
        "red": [c["id"] for c in r["checks"] if not c["pass"]]} for r in report["runs"]]}, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
