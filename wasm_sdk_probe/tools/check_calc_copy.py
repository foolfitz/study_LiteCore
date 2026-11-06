#!/usr/bin/env python3
"""SPEC-P-calc-copy 4.2: P-C1..P-C5 on the Calc page, Chrome and Firefox, on a private mirror of the live page sources with the
engine under test (the development profile build/ods/editor-v7/profile before the hand-test slot).  Real pointer and keys.

The clipboard is read back with navigator.clipboard.readText(): Chrome is granted clipboard permission over CDP, Firefox runs
with dom.events.testing.asyncClipboard (tools/v21_clipboard.py's shape).  Both relax the user-activation rule the page's
writeText meets in a real browser, so this cannot show that the activation of a Ctrl+C survives the engine round trip --
a named limit of this instrument; the owner's hand test is the observer for it.

  check_calc_copy.py --out NEW_DIR --engine PROFILE_DIR [--browsers chrome,firefox] [--mutate anchor-only]

--mutate anchor-only copies the active cell whatever the selection; it must turn P-C1 red.
Without --mutate: exit 0 iff every check of every browser passes.

2026-11-07, SPEC-P-calc-copy 9.2 (ods-editor-v8): --html adds P-H1..P-H3 after P-C1..P-C5, reading the clipboard back with
navigator.clipboard.read() (both browsers' versions are in the report), and P-H4: the text/html each browser read back in P-H1
is saved beside the report and pasted at L20 by the native harness (check_calc_copy_native.py --paste-html, --native-harness).
--mutate plain-only drops the page's ClipboardItem write; it must turn P-H1 red.
  check_calc_copy.py --html --out NEW_DIR --engine build/ods/editor-v8/profile --native-harness BUILD/v8/calc-undo-native
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
from check_calc_copy_native import WANT_H1, cell_table
from check_calc_sheet_view import wait
from create_calc_structure_fixture import create
from r7_support import evaluate, wait_page
from run_browser_probe import free_port
from run_e2_c_page_smoke import navigate
from v21_clipboard import FIREFOX_PREFS, grant
from v21_shakedown_common import browser_lock, close_browser, open_browser

PROJECT = Path(__file__).resolve().parents[1]
ROOT = "window.__calcEditor"
MUTATIONS = {"anchor-only": ("spreadsheet-shell/calc-editor-session.js", "const range=this._selection ?? rectangle(this._cell);",
                             "const range=rectangle(this._cell);", ["P-C1"]),
             "plain-only": ("ods-editor-app.js",
                            'if(typeof result.htmlText==="string" && typeof globalThis.ClipboardItem==="function" && navigator.clipboard?.write) {',
                            "if(false) {", ["P-H1"])}
cs.KEYS["c"] = ("c", "KeyC", 67, "c")
WANT_C1 = "42\t84\n格式測試\t待清除\n"
CLIP = "navigator.clipboard.readText()"
READ = """(async()=>{const items=await navigator.clipboard.read();const out={types:[],plain:null,html:null};
  for(const item of items){out.types.push(...item.types);
    if(item.types.includes('text/plain'))out.plain=await (await item.getType('text/plain')).text();
    if(item.types.includes('text/html'))out.html=await (await item.getType('text/html')).text();}
  return out;})()"""
ENGINE_HTML = """(async()=>{const r=await %s.session.copySelection();const h=r.htmlText||'';
  return {bytes:new TextEncoder().encode(h).length,style:h.includes('<style'),origin:h.includes('google-sheets-html-origin')};})()""" % ROOT


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mirror(out, engine, mutate):
    root = PROJECT / "build/calc-copy" / out.name
    root.mkdir(parents=True, exist_ok=False)
    for directory in ("sdk", "viewer-shell", "spreadsheet-shell"):
        shutil.copytree(PROJECT / directory, root / directory)
    page = (PROJECT / "web/ods-editor-app.js").read_text(encoding="utf-8")
    for name in ("ods-editor-v6", "ods-editor-v7", "ods-editor-v8"):
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
    def clipboard(self):
        try:
            return evaluate(self.session, CLIP)
        except Exception as error:  # noqa: BLE001  a failed read is that check's red, with its reason
            return f"<read failed: {type(error).__name__}: {error}>"

    def copy(self):
        evaluate(self.session, "document.querySelector('#toast').textContent='',true")
        self.key("c", ("ctrl",))
        time.sleep(1.0)
        self.idle()
        return self.clipboard(), evaluate(self.session, "document.querySelector('#toast').textContent")

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


def p_c1_c3(run):
    opened = run.state()["revision"]
    undo_at_open = run.dom()["undo"]["disabled"]  # spec append 1: recorded, not judged (the page never disables it by depth)
    run.drag(run.cell_center("B", "1"), run.cell_center("C", "2"))
    clip, toast = run.copy()
    run.check("P-C1/rectangle", clip == WANT_C1 and "B1:C2" in toast, {"clipboard": clip, "toast": toast})
    state = run.state()
    unsaved = evaluate(run.session, f"{ROOT}.session.hasUnsavedEdits()")
    # Spec append 1: the copy left no undo step -- one undo finds nothing, and nothing moves.
    evaluate(run.session, "document.querySelector('#toast').textContent='',true")
    run.undo()
    after_undo, undo_toast = run.state()["revision"], evaluate(run.session, "document.querySelector('#toast').textContent")
    run.check("P-C3/clean", unsaved is False and state["revision"] == opened and undo_toast == "沒有可以復原的動作。"
              and after_undo == opened,
              {"hasUnsavedEdits": unsaved, "revision": [opened, state["revision"], after_undo], "undoToast": undo_toast,
               "undoDisabledAtOpen": undo_at_open})


def p_c2(run):
    run.click(*run.header("columns", "A")["center"])
    clip, toast = run.copy()
    lines = (clip or "").split("\n")
    run.check("P-C2/column", clip.endswith("\n") and len(lines) - 1 == 1000 and lines[0] == "原始中文 Alpha"
              and lines[999] == "第 1000 列" and "A 欄" in toast,
              {"lines": len(lines) - 1, "first": lines[0], "line1000": lines[999] if len(lines) > 999 else None, "toast": toast})
    run.click(*run.header("rows", "2")["center"])
    clip, toast = run.copy()
    run.check("P-C2/row", (clip or "").startswith("鄰格必須保留\t格式測試\t待清除") and "第 2 列" in toast,
              {"start": (clip or "")[:40], "toast": toast})


def p_c4(run):
    run.click(*run.cell_center("B", "1"))
    center = evaluate(run.session, "(()=>{const r=document.querySelector('#formula-input').getBoundingClientRect();"
                                   "return [r.left+r.width/2,r.top+r.height/2];})()")
    run.click(*center)
    evaluate(run.session, "document.querySelector('#formula-input').select(),true")
    clip, toast = run.copy()
    run.check("P-C4/field", clip == "42", {"clipboard": clip, "toast": toast})
    run.key("Escape")


def p_c5(run):
    evaluate(run.session, "navigator.clipboard.writeText('標記-P-C5')")
    time.sleep(.3)
    run.drag(run.cell_center("L", "10"), run.cell_center("M", "11"))
    clip, toast = run.copy()
    run.check("P-C5/empty", clip == "標記-P-C5" and "沒有可以複製的文字" in toast, {"clipboard": clip, "toast": toast})


def items(run):
    try:
        return evaluate(run.session, READ)
    except Exception as error:  # noqa: BLE001  a failed read is that check's red, with its reason
        return {"types": [], "plain": None, "html": None, "error": f"{type(error).__name__}: {error}"}


def copy_items(run):
    evaluate(run.session, "document.querySelector('#toast').textContent='',true")
    run.key("c", ("ctrl",))
    time.sleep(1.0)
    run.idle()
    return items(run), evaluate(run.session, "document.querySelector('#toast').textContent"), evaluate(run.session, f"{ROOT}.lastCopy")


def p_h1(run):
    run.drag(run.cell_center("B", "1"), run.cell_center("C", "2"))
    clip, toast, last = copy_items(run)
    table = cell_table(clip.get("html"))
    saved = run.out / f"{run.record['browser']}-P-H1.html"
    saved.write_text(clip.get("html") or "", encoding="utf-8")
    run.record["P-H1-html"] = str(saved)
    browser_html = clip.get("html") or ""
    run.record["P-H1-registration"] = {"browserBytes": len(browser_html.encode()), "browserStyle": "<style" in browser_html,
                                       "browserOrigin": "google-sheets-html-origin" in browser_html,
                                       "engine": evaluate(run.session, ENGINE_HTML)}
    run.check("P-H1/both-formats", "text/plain" in clip["types"] and "text/html" in clip["types"] and clip["plain"] == WANT_C1
              and table["tables"] == 1 and table["rows"] == WANT_H1 and (last or {}).get("formats") == ["text/plain", "text/html"],
              {"types": clip["types"], "plain": clip["plain"], "table": table, "lastCopy": last, "toast": toast,
               "error": clip.get("error")})


def p_h2(run):
    run.click(*run.header("columns", "A")["center"])
    clip, toast, last = copy_items(run)
    rows = cell_table(clip.get("html"))["rows"]
    run.check("P-H2/column", len(rows) == 999 and rows[:1] == [["原始中文 Alpha"]] and "A 欄" in toast,
              {"rows": len(rows), "first": rows[:1], "types": clip["types"], "lastCopy": last, "toast": toast})


def p_h3(run):
    removed = evaluate(run.session, "(delete globalThis.ClipboardItem, typeof globalThis.ClipboardItem)")
    run.drag(run.cell_center("B", "1"), run.cell_center("C", "2"))
    clip, toast, last = copy_items(run)
    run.check("P-H3/fallback", removed == "undefined" and clip["types"] == ["text/plain"] and clip["plain"] == WANT_C1
              and "B1:C2" in toast and (last or {}).get("formats") == ["text/plain"],
              {"ClipboardItem": removed, "types": clip["types"], "plain": clip["plain"], "lastCopy": last, "toast": toast})


def scenario(run, html=False):
    for step in (p_c1_c3, p_c2, p_c4, p_c5) + ((p_h1, p_h2, p_h3) if html else ()):
        try:
            step(run)
        except Exception as error:  # noqa: BLE001  one cell's crash is that cell's red; the next cell runs
            run.check(f"{step.__name__.upper().replace('_', '-')}/crash", False, repr(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--mutate", choices=sorted(MUTATIONS))
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--native-harness", type=Path)
    args = parser.parse_args()
    if args.html and not args.native_harness:
        parser.error("--html needs --native-harness (P-H4)")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = mirror(out, args.engine, args.mutate)
    fixture = create(out / "fixture")
    port = free_port()
    log = (out / "server.txt").open("w")
    server = subprocess.Popen(["python3", str(PROJECT / "web/serve.py"), "--port", str(port), "--root", str(root)], stdout=log,
                              stderr=subprocess.STDOUT)
    report = {"tool": {"path": "wasm_sdk_probe/tools/check_calc_copy.py", "sha256": sha(__file__), "argv": sys.argv[1:]},
              "engine": str(args.engine), "wasm": sha(args.engine / "probe.wasm"), "worker": sha(args.engine / "sdk-worker.js"),
              "page": {n: sha(root / n) for n in ("ods-editor-app.js", "ods-editor.html", "spreadsheet-shell/calc-editor-session.js",
                                                   "spreadsheet-shell/calc-document-sdk.js")},
              "mutate": args.mutate, "html": args.html, "fixture": sha(fixture), "runs": []}
    try:
        wait_page(f"http://127.0.0.1:{port}/ods-editor.html")
        with browser_lock("calc-copy", wait_s=0):
            for browser in args.browsers.split(","):
                session = None
                record = {"browser": browser, "checks": [], "error": None}
                report["runs"].append(record)
                try:
                    session = open_browser(browser, cs.WINDOW, firefox_prefs=FIREFOX_PREFS if browser == "firefox" else None)
                    record["version"] = session.version
                    record["clipboardGrant"] = grant(session, browser, f"http://127.0.0.1:{port}")
                    if browser == "chrome":  # readText needs a focused document (check_v26_select_all.py's copy arm)
                        session.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
                    navigate(session, f"http://127.0.0.1:{port}/ods-editor.html?diagnostics=1")
                    session.set_file("#file-input", fixture)
                    wait(session, f"Boolean({ROOT}.state?.cell) && {ROOT}.state.copySupported===true", 120)
                    wait(session, "document.querySelectorAll('#row-headers [role=rowheader]').length>0", 30)
                    if not evaluate(session, f"{ROOT}.state.copySupported===true"):
                        raise RuntimeError("the engine under test has no cell-copy capability")
                    run = Run(session, record)
                    run.out, run.record = out, record
                    scenario(run, args.html)
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
    if args.html:  # P-H4: what each browser read back, pasted by the native core (no browser involved)
        for r in report["runs"]:
            saved = r.get("P-H1-html")
            paste_out = out / f"{r['browser']}-P-H4"
            proc = subprocess.run(["python3", str(PROJECT / "tools/check_calc_copy_native.py"), "--paste-html", str(saved or "/dev/null"),
                                   "--harness", str(args.native_harness), "--out", str(paste_out)], capture_output=True, text=True,
                                  timeout=300) if saved else None
            detail = json.loads((paste_out / "report.json").read_text())["P-H4"] if saved and (paste_out / "report.json").exists() else None
            r["checks"].append({"id": "P-H4/paste-back", "pass": bool(proc and proc.returncode == 0 and detail and detail["ok"]),
                                "detail": {"exit": proc.returncode if proc else None, "L20": detail and detail["L20"],
                                           "target": detail and detail["target"], "stderr": proc.stderr[-400:] if proc else None}})
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
