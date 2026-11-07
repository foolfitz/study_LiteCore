#!/usr/bin/env python3
"""SPEC-P-calc-structure 4.2: P-S1..P-S7 on the Calc page, Chrome and Firefox, on a private mirror of the live page sources with the
engine under test (the development profile build/ods/editor-v6/profile before the hand-test slot).  Real pointer and keys (a right
click, Shift+F10, Ctrl+minus / Ctrl+plus, the menu's arrows and Escape).  Each change is undone with the toolbar's undo before the
next cell, and the undo is read back too.  Every check is recorded and the run goes on past a red one.  P-S8 is
check_calc_headers.py on the same profile, run on its own.

  check_calc_structure.py --out NEW_DIR --engine PROFILE_DIR [--browsers chrome,firefox] [--mutate NAME]

--mutate applies one of the spec's red cases to the mirrored page and exits 0 only if the criteria it names turn red:
  above-index-plus-1   an insert above goes one row/column further down  -> P-S1
  count-one            the count is always 1                             -> P-S3
  no-reason-title      a disabled item has no title                      -> P-S6
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
from create_calc_structure_fixture import create
from r7_support import evaluate, wait_page
from run_browser_probe import free_port
from run_e2_c_page_smoke import navigate
from v21_shakedown_common import browser_lock, close_browser, open_browser

PROJECT = Path(__file__).resolve().parents[1]
WINDOW = (1440, 1000)
ROOT = "window.__calcEditor"
MUTATIONS = {
    "above-index-plus-1": ("spreadsheet-shell/calc-editor-session.js",
                           'const index=action==="insert" && where==="after" ? high+1 : low;',
                           'const index=action==="insert" && where==="after" ? high+1 : action==="insert" ? low+1 : low;', ["P-S1"]),
    "count-one": ("spreadsheet-shell/calc-editor-session.js", "const count=high-low+1;", "const count=1;", ["P-S3"]),
    "no-reason-title": ("ods-editor-app.js", "node.title=reason ?? label;", 'node.title=reason ? "" : label;', ["P-S6"]),
}
DOM = """(()=>{const pick=sel=>[...document.querySelectorAll(sel)].map(b=>{const r=b.getBoundingClientRect();
   return {index:+b.dataset.index,label:b.textContent,center:[r.left+r.width/2,r.top+r.height/2]};});
 const m=document.querySelector('#structure-menu');
 return {columns:pick('#column-headers [role=columnheader]'),rows:pick('#row-headers [role=rowheader]'),
   menu:{hidden:m.hidden,items:[...m.querySelectorAll('[role=menuitem]')].map(b=>{const r=b.getBoundingClientRect();
     return {id:b.dataset.structure,disabled:b.getAttribute('aria-disabled'),title:b.title,label:b.textContent,
       center:[r.left+r.width/2,r.top+r.height/2]};}),focused:document.activeElement?.dataset?.structure ?? null},
   active:document.activeElement?.id ?? null,toast:document.querySelector('#toast').textContent,
   tabs:[...document.querySelectorAll('#tab-strip button')].map(b=>{const r=b.getBoundingClientRect();
     return {text:b.textContent,center:[r.left+r.width/2,r.top+r.height/2]};}),
   surface:(()=>{const r=document.querySelector('#surface').getBoundingClientRect();return [r.left,r.top];})(),
   undo:(()=>{const b=document.querySelector('#undo-button'),r=b.getBoundingClientRect();
     return {center:[r.left+r.width/2,r.top+r.height/2],disabled:b.disabled,hidden:b.hidden};})()};})()"""
# Each read is caught: a read that fails is that check's red (with its code), not a crash of the cell.
READ = ("(async()=>{const d=window.__calcEditor.session.document,out=[];for(const [c,r] of ARGS){try{const {cell}=await d.readCell(c,r);"
        "out.push(cell);}catch(e){out.push({text:null,error:e.code||String(e)});}}return out;})()")
# Chrome CDP key, code, Windows virtual key; WebDriver value.
KEYS = {"F10": ("F10", "F10", 121, ""), "Escape": ("Escape", "Escape", 27, ""),
        "ArrowDown": ("ArrowDown", "ArrowDown", 40, ""), "-": ("-", "Minus", 189, "-"), "+": ("+", "Equal", 187, "+")}
MODS = {"ctrl": (2, ""), "shift": (8, "")}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mirror(out, engine, mutate):
    root = PROJECT / "build/calc-structure" / out.name
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

    def texts(self, cells):
        return [c["text"] for c in self.read(cells)]

    def click(self, x, y):
        self.hands.click(x, y)
        self.idle()

    def right_click(self, x, y):
        if self.hands.chrome:
            self.session.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
            for kind in ("mousePressed", "mouseReleased"):
                self.session.call("Input.dispatchMouseEvent", {"type": kind, "x": x, "y": y, "button": "right", "clickCount": 1})
        else:
            self.session.command("POST", "/actions", {"actions": [{"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"},
                "actions": [{"type": "pointerMove", "duration": 0, "origin": "viewport", "x": round(x), "y": round(y)},
                            {"type": "pointerDown", "button": 2}, {"type": "pointerUp", "button": 2}]}]})
            self.session.command("DELETE", "/actions")
        wait(self.session, "!document.querySelector('#structure-menu').hidden", 15)
        self.idle()

    def key(self, name, mods=()):
        if self.hands.chrome:
            key, code, vk = KEYS[name][:3]
            bits = sum(MODS[m][0] for m in mods)
            base = {"key": key, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk, "modifiers": bits}
            self.session.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", **base})
            self.session.call("Input.dispatchKeyEvent", {"type": "keyUp", **base})
        else:
            held = [MODS[m][1] for m in mods]
            actions = [{"type": "keyDown", "value": k} for k in held]
            actions += [{"type": "keyDown", "value": KEYS[name][3]}, {"type": "keyUp", "value": KEYS[name][3]}]
            actions += [{"type": "keyUp", "value": k} for k in reversed(held)]
            self.session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keys", "actions": actions}]})
            self.session.command("DELETE", "/actions")
        self.idle()

    def item(self, ident):
        """Click a menu item, then wait for the change (or the refusal) to settle."""
        menu = self.dom()["menu"]
        node = next((i for i in menu["items"] if i["id"] == ident), None)
        if node is None:
            return None
        self.click(*node["center"])
        time.sleep(.5)
        self.idle()
        return node

    def undo(self):
        u = self.dom()["undo"]
        self.click(*u["center"])
        time.sleep(.5)
        self.idle()

    def header(self, axis, label):
        return next(h for h in self.dom()[axis] if h["label"] == label)

    def cell_center(self, column_label, row_label):
        dom = self.dom()
        c = next(h for h in dom["columns"] if h["label"] == column_label)
        r = next(h for h in dom["rows"] if h["label"] == row_label)
        return c["center"][0], r["center"][1]

    def tab(self, text):
        t = next(t for t in self.dom()["tabs"] if t["text"].strip() == text)
        self.click(*t["center"])
        time.sleep(1.0)
        self.idle()


def selection(state):
    s = state["selection"] or {}
    return {k: s.get(k) for k in ("whole", "column", "row", "endColumn", "endRow")}


def menu_ids(dom):
    return [i["id"] for i in dom["menu"]["items"]]


ROW_ITEMS = ["rows-insert-before", "rows-insert-after", "rows-delete"]
COLUMN_ITEMS = ["columns-insert-before", "columns-insert-after", "columns-delete"]


def p_s1(run):
    run.right_click(*run.header("rows", "3")["center"])
    dom = run.dom()
    run.check("P-S1/menu", not dom["menu"]["hidden"] and menu_ids(dom) == ROW_ITEMS and dom["menu"]["focused"] == ROW_ITEMS[0],
              {"items": menu_ids(dom), "focused": dom["menu"]["focused"], "hidden": dom["menu"]["hidden"]})
    run.item("rows-insert-before")
    state, dom = run.state(), run.dom()
    after = run.texts([[0, 2], [0, 3]])
    labels_ok = all(h["label"] == str(h["index"] + 1) for h in dom["rows"])
    run.check("P-S1/inserted-above-3", after == ["", "合併格"] and selection(state) == {"whole": "rows", "column": 0, "row": 2,
              "endColumn": 16383, "endRow": 2} and labels_ok and "第 3 列上方插入 1 列" in dom["toast"],
              {"A3,A4": after, "selection": selection(state), "rowLabelsContiguous": labels_ok, "toast": dom["toast"]})
    run.undo()
    back = run.texts([[0, 2], [0, 4]])
    run.check("P-S1/undo", back == ["合併格", "隱藏列之後"], {"A3,A5": back})


def p_s2(run):
    run.right_click(*run.header("columns", "C")["center"])
    dom = run.dom()
    run.check("P-S2/menu", menu_ids(dom) == COLUMN_ITEMS and dom["menu"]["focused"] == COLUMN_ITEMS[0], {"items": menu_ids(dom)})
    run.item("columns-insert-after")
    state, dom = run.state(), run.dom()
    after = run.texts([[3, 0], [5, 0], [2, 0]])
    # Spec append 1: the same indices stay selected -- whole column C.  E is the hidden column now (old D).
    run.check("P-S2/inserted-right-of-C", after == ["", "隱藏欄之後", "84"] and selection(state) == {"whole": "columns",
              "column": 2, "row": 0, "endColumn": 2, "endRow": 1048575} and "C 欄右方插入 1 欄" in dom["toast"],
              {"D1,F1,C1": after, "selection": selection(state), "toast": dom["toast"]})
    run.undo()
    back = run.texts([[4, 0], [5, 0]])
    run.check("P-S2/undo", back == ["隱藏欄之後", ""], {"E1,F1": back})


def p_s3(run):
    a, b = run.header("rows", "2"), run.header("rows", "3")
    run.click(*a["center"])
    # Shift-click is the multi-row selection the headers spec measured (P-H3); the right click lands inside it.
    shift_click(run, *b["center"])
    run.right_click(*run.header("rows", "2")["center"])
    run.item("rows-delete")
    state, dom = run.state(), run.dom()
    # Two rows gone: the hidden row (old 4) is row 2 now, so row 2 has no header; A3 is the old A5.
    after = run.texts([[0, 2], [0, 0]])
    labels = [h["label"] for h in dom["rows"]]
    run.check("P-S3/deleted-2-3", after == ["隱藏列之後", "原始中文 Alpha"] and "2" not in labels and "3" in labels
              and selection(state) == {"whole": "rows", "column": 0, "row": 1, "endColumn": 16383, "endRow": 2}
              and "第 2 到 3 列" in dom["toast"],
              {"A3,A1": after, "rowLabels": labels[:6], "selection": selection(state), "toast": dom["toast"]})
    run.undo()
    back = run.texts([[0, 1], [0, 2]])
    run.check("P-S3/undo", back == ["鄰格必須保留", "合併格"], {"A2,A3": back})


def shift_click(run, x, y):
    if run.hands.chrome:
        run.session.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "modifiers": 8})
        for kind in ("mousePressed", "mouseReleased"):
            run.session.call("Input.dispatchMouseEvent", {"type": kind, "x": x, "y": y, "button": "left", "clickCount": 1, "modifiers": 8})
    else:
        run.session.command("POST", "/actions", {"actions": [
            {"type": "key", "id": "keys", "actions": [{"type": "keyDown", "value": ""}, {"type": "pause", "duration": 0},
                                                      {"type": "pause", "duration": 0}, {"type": "pause", "duration": 0},
                                                      {"type": "keyUp", "value": ""}]},
            {"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"}, "actions": [
                {"type": "pause", "duration": 0}, {"type": "pointerMove", "duration": 0, "origin": "viewport", "x": round(x), "y": round(y)},
                {"type": "pointerDown", "button": 0}, {"type": "pointerUp", "button": 0}, {"type": "pause", "duration": 0}]}]})
        run.session.command("DELETE", "/actions")
    run.idle()


def p_s4(run):
    run.right_click(*run.cell_center("B", "2"))
    dom = run.dom()
    state = run.state()
    run.check("P-S4/menu", menu_ids(dom) == ROW_ITEMS + COLUMN_ITEMS and (state["cell"]["column"], state["cell"]["row"]) == (1, 1),
              {"items": menu_ids(dom), "cell": [state["cell"]["column"], state["cell"]["row"]]})
    run.item("columns-insert-before")
    after = run.texts([[1, 1], [2, 1]])
    run.check("P-S4/inserted-left-of-B", after == ["", "格式測試"], {"B2,C2": after, "toast": run.dom()["toast"]})
    run.undo()
    back = run.texts([[1, 1], [2, 1]])
    run.check("P-S4/undo", back == ["格式測試", "待清除"], {"B2,C2": back})


def p_s5(run):
    run.click(*run.header("columns", "C")["center"])
    run.key("-", ("ctrl",))
    time.sleep(.5); run.idle()
    # C gone: the hidden column (old D) is C now, so C has no header; D1 is the old E1.
    after = run.texts([[3, 0]])
    labels = [h["label"] for h in run.dom()["columns"]]
    run.check("P-S5/ctrl-minus-deletes-C", after == ["隱藏欄之後"] and "C" not in labels and "D" in labels,
              {"D1": after, "columnLabels": labels[:6], "toast": run.dom()["toast"]})
    run.undo()
    run.click(*run.header("rows", "2")["center"])
    run.key("+", ("ctrl", "shift") if run.hands.chrome else ("ctrl",))
    time.sleep(.5); run.idle()
    after = run.texts([[0, 1], [0, 2]])
    run.check("P-S5/ctrl-plus-inserts-above-2", after == ["", "鄰格必須保留"], {"A2,A3": after, "toast": run.dom()["toast"]})
    run.undo()
    run.click(*run.cell_center("B", "2"))
    revision = run.state()["revision"]
    run.key("-", ("ctrl",))
    run.key("+", ("ctrl", "shift") if run.hands.chrome else ("ctrl",))
    time.sleep(.5); run.idle()
    state, dom = run.state(), run.dom()
    texts = run.texts([[1, 1], [0, 1]])
    run.check("P-S5/partial-selection-changes-nothing", state["revision"] == revision and texts == ["格式測試", "鄰格必須保留"]
              and "右鍵選單" in dom["toast"], {"revision": [revision, state["revision"]], "B2,A2": texts, "toast": dom["toast"]})


def p_s6(run):
    # A whole column selected: the row items in the cell menu are disabled and say why.
    run.click(*run.header("columns", "C")["center"])
    run.right_click(*run.cell_center("C", "2"))
    dom = run.dom()
    rows = [i for i in dom["menu"]["items"] if i["id"] in ROW_ITEMS]
    run.check("P-S6/whole-column-disables-row-items", len(rows) == 3 and all(i["disabled"] == "true" and i["title"] for i in rows),
              {"rows": [(i["id"], i["disabled"], i["title"]) for i in rows]})
    run.key("Escape")
    # The protected sheet: every item disabled with a reason; choosing one changes nothing.
    run.tab("保護測試")
    revision = run.state()["revision"]
    run.right_click(*run.cell_center("A", "1"))
    dom = run.dom()
    items = dom["menu"]["items"]
    ok = len(items) == 6 and all(i["disabled"] == "true" and i["title"] for i in items)
    run.item("rows-insert-before")
    state = run.state()
    text = run.texts([[0, 0]])
    run.check("P-S6/protected-sheet", ok and state["revision"] == revision and text == ["鎖定內容"],
              {"items": [(i["id"], i["disabled"], i["title"]) for i in items], "revision": [revision, state["revision"]], "A1": text,
               "toast": run.dom()["toast"]})
    # The core refuses (text in the last row): the reason is shown, nothing changes, the page keeps its session.
    run.tab("邊界測試")
    evaluate(run.session, f"window.__keptSession={ROOT}.session,true")
    revision = run.state()["revision"]
    run.right_click(*run.cell_center("A", "1"))
    run.item("rows-insert-before")
    state, dom = run.state(), run.dom()
    same = evaluate(run.session, f"window.__keptSession==={ROOT}.session")
    text = run.texts([[0, 0]])
    run.check("P-S6/core-refusal", "LibreOffice 拒絕" in dom["toast"] and state["revision"] == revision and text == ["邊界"]
              and same is True and state["uncertain"] is False,
              {"toast": dom["toast"], "revision": [revision, state["revision"]], "A1": text, "sameSession": same,
               "uncertain": state["uncertain"]})
    run.tab("編輯測試")


def p_s7(run):
    run.click(*run.cell_center("B", "2"))
    run.key("F10", ("shift",))
    wait(run.session, "!document.querySelector('#structure-menu').hidden", 10)
    first = run.dom()
    run.key("ArrowDown")
    second = run.dom()
    run.key("Escape")
    closed = run.dom()
    run.check("P-S7/keyboard", not first["menu"]["hidden"] and first["menu"]["focused"] == ROW_ITEMS[0]
              and second["menu"]["focused"] == ROW_ITEMS[1] and closed["menu"]["hidden"] and closed["active"] == "cell-editor",
              {"opened": not first["menu"]["hidden"], "focused": [first["menu"]["focused"], second["menu"]["focused"]],
               "closed": closed["menu"]["hidden"], "active": closed["active"]})


def scenario(run):
    for step in (p_s1, p_s2, p_s3, p_s4, p_s5, p_s6, p_s7):
        try:
            step(run)
        except Exception as error:  # noqa: BLE001  one cell's crash is that cell's red; the next cell runs
            run.check(f"{step.__name__.upper().replace('_', '-')}/crash", False, repr(error))
            evaluate(run.session, "document.querySelector('#structure-menu').hidden=true")


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
    report = {"tool": {"path": "wasm_sdk_probe/tools/check_calc_structure.py", "sha256": sha(__file__), "argv": sys.argv[1:]},
              "engine": str(args.engine), "wasm": sha(args.engine / "probe.wasm"), "worker": sha(args.engine / "sdk-worker.js"),
              "page": {n: sha(root / n) for n in ("ods-editor-app.js", "ods-editor.html", "spreadsheet-shell/calc-editor-session.js",
                                                   "spreadsheet-shell/calc-document-sdk.js")},
              "mutate": args.mutate, "fixture": sha(fixture), "runs": []}
    try:
        wait_page(f"http://127.0.0.1:{port}/ods-editor.html")
        with browser_lock("calc-structure", wait_s=0):
            for browser in args.browsers.split(","):
                session = None
                record = {"browser": browser, "checks": [], "error": None}
                report["runs"].append(record)
                try:
                    session = open_browser(browser, WINDOW)
                    record["version"] = session.version
                    navigate(session, f"http://127.0.0.1:{port}/ods-editor.html?diagnostics=1")
                    session.set_file("#file-input", fixture)
                    wait(session, f"Boolean({ROOT}.state?.cell) && {ROOT}.state.structureSupported===true", 120)
                    wait(session, "document.querySelectorAll('#row-headers [role=rowheader]').length>0", 30)
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
    report["redCriteria"] = red
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"verdict": report["verdict"], "redCriteria": red,
                      "runs": [{"browser": r["browser"], "error": r["error"], "passed": sum(c["pass"] for c in r["checks"]),
                                "checks": len(r["checks"]), "red": [c["id"] for c in r["checks"] if not c["pass"]][:12]}
                               for r in report["runs"]]}, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
