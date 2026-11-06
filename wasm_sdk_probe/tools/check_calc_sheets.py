#!/usr/bin/env python3
"""SPEC-P-calc-sheets 4.2: P-T1..P-T9 on the Calc page, Chrome and Firefox, on a private mirror of the live page sources with the
frozen engine ods-editor-v6 (no engine change in this spec).  Real pointer and keys (CDP in Chrome, WebDriver actions in
Firefox).  Every check is recorded and the run goes on past a red one.  While another sheet is shown for a formula nothing is
read from the document: a read would ask the engine for a cell there; the revision says whether anything was written.

  check_calc_sheets.py --out NEW_DIR [--engine dist/profiles/ods-editor-v6] [--browsers chrome,firefox] [--mutate NAME]

--mutate applies one of the spec's red cases to the mirrored page and exits 0 only if the criteria it names turn red:
  never-quote      sheet names are never quoted                     -> P-T6
  browse-commits   a tab click with the caret in a slot commits     -> P-T5
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

import check_calc_structure as cs
from check_calc_sheet_view import wait
from create_calc_sheets_fixture import create
from r7_support import evaluate, wait_page
from run_browser_probe import free_port
from run_e2_c_page_smoke import navigate
from v21_shakedown_common import browser_lock, close_browser, open_browser

PROJECT = Path(__file__).resolve().parents[1]
ROOT = "window.__calcEditor"
MUTATIONS = {
    "never-quote": ("spreadsheet-shell/calc-editor-session.js",
                    """return /^[\\p{L}_][\\p{L}\\p{N}_]*$/u.test(name) ? name : `'${name.replaceAll("'", "''")}'`;""",
                    "return name;", ["P-T6"]),
    "browse-commits": ("ods-editor-app.js", "await viewPart(part,()=>session.browsePart(part));",
                       "await viewPart(part,()=>session.showPart(part));", ["P-T5"]),
}
cs.KEYS["Enter"] = ("Enter", "Enter", 13, "")
TABS = """[...document.querySelectorAll('#tab-strip button')].map(b=>({text:b.textContent,protected:b.dataset.protected??null,
  aria:b.getAttribute('aria-label'),lock:!!b.querySelector('.lock'),selected:b.getAttribute('aria-selected')}))"""
FIELDS = """({formula:document.querySelector('#formula-input').value,position:document.querySelector('#sheet-position').textContent,
  toast:document.querySelector('#toast').textContent,active:document.activeElement?.id ?? null,
  box:!document.querySelector('#reference-box').hidden})"""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mirror(out, engine, mutate):
    root = PROJECT / "build/calc-sheets" / out.name
    root.mkdir(parents=True, exist_ok=False)
    for directory in ("sdk", "viewer-shell", "spreadsheet-shell"):
        shutil.copytree(PROJECT / directory, root / directory)
    page = (PROJECT / "web/ods-editor-app.js").read_text(encoding="utf-8")
    for name in ("ods-editor-v6", "ods-editor-v7"):
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


class Run(cs.Run):
    def fields(self):
        return evaluate(self.session, FIELDS)

    def typed(self, text):
        self.hands.text(text)
        time.sleep(.3)
        self.idle()

    def drag(self, start, end):
        (x0, y0), (x1, y1) = start, end
        if self.hands.chrome:
            self.session.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x0, "y": y0})
            self.session.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x0, "y": y0, "button": "left", "clickCount": 1})
            for k in range(1, 6):
                self.session.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x0 + (x1 - x0) * k / 5,
                                  "y": y0 + (y1 - y0) * k / 5, "button": "left", "buttons": 1})
                time.sleep(.05)
            self.session.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x1, "y": y1, "button": "left", "clickCount": 1})
        else:
            moves = [{"type": "pointerMove", "duration": 50, "origin": "viewport", "x": round(x0 + (x1 - x0) * k / 5),
                      "y": round(y0 + (y1 - y0) * k / 5)} for k in range(1, 6)]
            self.session.command("POST", "/actions", {"actions": [{"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"},
                "actions": [{"type": "pointerMove", "duration": 0, "origin": "viewport", "x": round(x0), "y": round(y0)},
                            {"type": "pointerDown", "button": 0}, *moves, {"type": "pointerUp", "button": 0}]}]})
            self.session.command("DELETE", "/actions")
        time.sleep(.5)
        self.idle()

    def tab_only(self, text):
        """Click a tab and wait for the shown sheet to settle (the tab may keep a formula going)."""
        tab = next(t for t in self.dom()["tabs"] if t["text"].strip() == text)
        self.click(*tab["center"])
        time.sleep(1.0)
        self.idle()

    def cell(self, column, row):
        return self.read([[column, row]])[0]

    def start_formula(self, column_label, row_label, text):
        self.click(*self.cell_center(column_label, row_label))
        self.typed(text)
        wait(self.session, f"{ROOT}.state.editing!==null && {ROOT}.state.draft==={json.dumps(text)}", 15)

    def home(self):
        if self.state()["currentPart"] != 0:
            self.tab("編輯測試")


def p_t1(run):
    tabs = evaluate(run.session, TABS)
    locked = [t["text"] for t in tabs if t["lock"]]
    guarded = next((t for t in tabs if t["text"] == "保護測試"), {})
    run.check("P-T1/lock", locked == ["保護測試"] and "受保護" in (guarded.get("aria") or "") and len(tabs) == 9,
              {"locked": locked, "protectedTab": guarded, "tabs": len(tabs)})


def p_t2(run):
    first = run.fields()["position"]
    run.tab("另一張表")
    second = run.fields()["position"]
    run.home()
    run.check("P-T2/position", first == "工作表 1／9" and second == "工作表 2／9", {"atOpen": first, "afterTab2": second})


def name_box(run, text):
    # The address box is above the grid: click it, select its text, type, Enter.
    center = evaluate(run.session, "(()=>{const r=document.querySelector('#cell-address').getBoundingClientRect();"
                                   "return [r.left+r.width/2,r.top+r.height/2];})()")
    run.click(*center)
    evaluate(run.session, "document.querySelector('#cell-address').select(),true")
    run.typed(text)
    run.key("Enter")
    time.sleep(.8)
    run.idle()
    state = run.state()
    return {"part": state["currentPart"], "cell": [state["cell"]["column"], state["cell"]["row"]], "toast": run.fields()["toast"]}


def p_t3(run):
    other = name_box(run, "另一張表.A1")
    spaced = name_box(run, "'有 空白'.B1")
    excel = name_box(run, "另一張表!A1")
    missing = name_box(run, "不存在.A1")
    run.home()
    run.check("P-T3/name-box", other["part"] == 1 and other["cell"] == [0, 0] and spaced["part"] == 5 and spaced["cell"] == [1, 0]
              and excel["part"] == 1 and excel["cell"] == [0, 0] and missing["part"] == 1 and missing["cell"] == [0, 0]
              and "找不到" in missing["toast"], {"另一張表.A1": other, "'有 空白'.B1": spaced, "另一張表!A1": excel, "不存在.A1": missing})


def p_t4(run):
    run.start_formula("H", "1", "=")
    run.click(*run.cell_center("B", "1"))
    after_b1 = run.fields()
    run.typed("+")
    run.click(*run.cell_center("C", "1"))
    after_c1 = run.fields()
    run.key("Enter")
    h1 = run.cell(7, 0)
    run.check("P-T4/same-sheet", after_b1["formula"] == "=B1" and after_c1["formula"] == "=B1+C1" and h1.get("formula") == "=B1+C1"
              and h1.get("value") == 126, {"afterB1": after_b1, "afterC1": after_c1, "H1": {k: h1.get(k) for k in ("formula", "value", "text")}})


def p_t5(run):
    run.start_formula("H", "2", "=")
    revision = run.state()["revision"]
    run.tab_only("另一張表")
    state, browsing = run.state(), run.fields()
    run.click(*run.cell_center("A", "1"))
    pointed = run.fields()
    middle = run.state()
    run.key("Enter")
    time.sleep(.5)
    run.idle()
    back = run.state()
    h2 = run.cell(7, 1)
    run.check("P-T5/other-sheet", state["currentPart"] == 1 and state["editing"] is not None and browsing["formula"] == "="
              and state["revision"] == revision and pointed["formula"] == "=$另一張表.A1" and middle["revision"] == revision
              and back["currentPart"] == 0 and h2.get("text") == "第二表不應改動",
              {"browsing": {"part": state["currentPart"], "editing": state["editing"], "formula": browsing["formula"],
                            "revision": [revision, state["revision"]]}, "pointed": pointed, "afterEnter": back["currentPart"],
               "H2": {k: h2.get(k) for k in ("formula", "text")}})


def p_t6(run):
    run.start_formula("H", "3", "=")
    run.tab_only("有 空白")
    run.click(*run.cell_center("B", "1"))
    pointed = run.fields()
    run.key("Enter")
    time.sleep(.5)
    run.idle()
    h3 = run.cell(7, 2)
    run.check("P-T6/quoted", pointed["formula"] == "=$'有 空白'.B1" and h3.get("value") == 10,
              {"pointed": pointed["formula"], "H3": {k: h3.get(k) for k in ("formula", "value", "text")}})
    run.home()


def p_t7(run):
    run.start_formula("H", "7", "=SUM(")  # spec append 1: H4 is on the hidden row
    run.drag(run.cell_center("B", "1"), run.cell_center("C", "1"))
    dragged = run.fields()
    run.typed(")")
    run.key("Enter")
    h7 = run.cell(7, 6)
    run.check("P-T7/drag-range", dragged["formula"] == "=SUM(B1:C1" and h7.get("value") == 126,
              {"dragged": dragged, "H7": {k: h7.get(k) for k in ("formula", "value", "text")}})


def p_t8(run):
    run.start_formula("H", "5", "=")
    revision = run.state()["revision"]
    run.tab_only("另一張表")
    shown = run.state()["currentPart"]
    run.key("Escape")
    time.sleep(.8)
    run.idle()
    state = run.state()
    h5 = run.cell(7, 4)
    run.check("P-T8/escape", shown == 1 and state["currentPart"] == 0 and state["editing"] is None and state["revision"] == revision
              and h5.get("text") == "", {"shown": shown, "after": state["currentPart"], "editing": state["editing"],
                                         "revision": [revision, state["revision"]], "H5": h5.get("text")})


def p_t9(run):
    run.start_formula("H", "6", "5")
    run.click(*run.cell_center("B", "1"))
    time.sleep(.5)
    run.idle()
    state = run.state()
    h6 = run.cell(7, 5)
    run.check("P-T9/not-a-slot", h6.get("text") == "5" and [state["cell"]["column"], state["cell"]["row"]] == [1, 0],
              {"H6": h6.get("text"), "cell": [state["cell"]["column"], state["cell"]["row"]]})


def scenario(run):
    for step in (p_t1, p_t2, p_t3, p_t4, p_t5, p_t6, p_t7, p_t8, p_t9):
        try:
            step(run)
        except Exception as error:  # noqa: BLE001  one cell's crash is that cell's red; the next cell runs
            run.check(f"{step.__name__.upper().replace('_', '-')}/crash", False, repr(error))
            try:
                run.key("Escape")
                run.home()
            except Exception:  # noqa: BLE001
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--engine", type=Path, default=PROJECT / "dist/profiles/ods-editor-v6")
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
    report = {"tool": {"path": "wasm_sdk_probe/tools/check_calc_sheets.py", "sha256": sha(__file__), "argv": sys.argv[1:]},
              "engine": str(args.engine), "wasm": sha(args.engine / "probe.wasm"), "worker": sha(args.engine / "sdk-worker.js"),
              "page": {n: sha(root / n) for n in ("ods-editor-app.js", "ods-editor.html", "spreadsheet-shell/calc-editor-session.js",
                                                   "spreadsheet-shell/calc-document-sdk.js")},
              "mutate": args.mutate, "fixture": sha(fixture), "runs": []}
    try:
        wait_page(f"http://127.0.0.1:{port}/ods-editor.html")
        with browser_lock("calc-sheets", wait_s=0):
            for browser in args.browsers.split(","):
                session = None
                record = {"browser": browser, "checks": [], "error": None}
                report["runs"].append(record)
                try:
                    session = open_browser(browser, cs.WINDOW)
                    record["version"] = session.version
                    navigate(session, f"http://127.0.0.1:{port}/ods-editor.html?diagnostics=1")
                    session.set_file("#file-input", fixture)
                    wait(session, f"Boolean({ROOT}.state?.cell) && {ROOT}.state.headersSupported===true", 120)
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
