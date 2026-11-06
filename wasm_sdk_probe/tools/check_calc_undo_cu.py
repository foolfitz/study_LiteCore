#!/usr/bin/env python3
"""SPEC-P-calc-undo 4.5 and 6: CU-1 to CU-7 and CU-9 on a mirror of the web/ Calc page with --engine mounted, Chrome and Firefox, real
keys and a real pointer, the saved ODS read back.  CU-8 (the regressions) is other tools'.

Each criterion starts from a freshly opened fixture (create_calc_range_format_fixture, three sheets) and compares the touched cells with
the zero-edit save of that same document: content and resolved automatic style (probe_calc_undo_native.sheet_state's reading, per sheet).
Every arm records what the page sent to its Worker, so "the file did not change" and "nothing was asked" are told apart.

Red case: --engine dist/profiles/ods-editor-v3 must be red on CU-1 and CU-2 (no button; Ctrl+Z sends nothing).  A missing button is a red
cell, never a crash.  This tool never compiles.
  check_calc_undo_cu.py --engine DIR --out DIR [--browsers chrome,firefox]
"""
import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
from check_calc_sheet_view import wait  # noqa: E402
from check_calc_style import ROOT, Run, WINDOW  # noqa: E402
from create_calc_range_format_fixture import create  # noqa: E402
import probe_calc_undo_native as nu  # noqa: E402
from r7_support import evaluate, run_in_page, wait_page  # noqa: E402
from run_browser_probe import free_port  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402
from v21_shakedown_common import browser_lock, close_browser, open_browser  # noqa: E402
from run_calc_editor_browser import key as box_key, select, type_text  # noqa: E402
import v21_input as real  # noqa: E402

WATCH = """(() => { if (window.__u) return; const u = window.__u = {keys: [], sent: []};
  addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key)) u.keys.push(e.key); }, true);
  const post = Worker.prototype.postMessage;
  Worker.prototype.postMessage = function (m, ...rest) { if (m?.kind === 'request') u.sent.push(m.operation); return post.call(this, m, ...rest); }; })()"""
SENT = "window.__u.sent.length"
BUTTON = """(() => { const b = document.querySelector(ARG); return Boolean(b && !b.hidden && !b.disabled && b.getBoundingClientRect().width > 0); })()"""
TOAST = "(() => { const t = document.querySelector('#toast'); return {text: t.textContent, error: t.classList.contains('error')}; })()"
VIEW = "[document.querySelector('#viewport').scrollLeft, document.querySelector('#viewport').scrollTop]"
FORMULA = "document.querySelector('#formula-input').value"


# --mutate field-guard: the page takes Ctrl+Z even from the formula bar.  CU-3 is green on v3 because v3 takes no Ctrl+Z at all, so its red
# has to come from a page that does take it (rule: a check is shown red before its green counts).
FIELD_GUARD = "    if(field || session.state.editing!==null || pendingEntry!==null)return;\n"


def mirror(out, engine, mutate=None):
    """check_calc_style.mirror's mirror, with ods-editor-v4's URL aliased too (the page loads v4 once it is switched)."""
    root = PROJECT / "build/calc-undo-cu" / out.name
    root.mkdir(parents=True, exist_ok=False)
    page = (PROJECT / "web/ods-editor-app.js").read_text(encoding="utf-8")
    for name in ("ods-editor-v2", "ods-editor-v3", "ods-editor-v4", "ods-editor-v5", "ods-editor-v6", "ods-editor-v7"):  # v5: SPEC-P-ms-formats; v6: 2026-11-05 (headers, structure); v7: 2026-11-06 (copy)
        page = page.replace(f"./profiles/{name}/sdk-worker.js", "./profiles/under-test/sdk-worker.js")
    if "./profiles/under-test/sdk-worker.js" not in page:
        raise SystemExit("the page names no profile this mirror knows")
    if mutate == "field-guard":
        if page.count(FIELD_GUARD) != 1:
            raise SystemExit("the field-guard mutation does not apply")
        page = page.replace(FIELD_GUARD, "")
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


def part_state(path, part):
    """probe_calc_undo_native.sheet_state for the sheet at index `part`."""
    with zipfile.ZipFile(path) as z:
        content = ET.fromstring(z.read("content.xml"))
    tables = content.findall(".//" + nu.T("table"))
    one = ET.Element("doc")
    one.extend(content.findall(".//{%s}automatic-styles" % nu.NS["o"]))
    body = ET.SubElement(one, "body")
    body.append(tables[part])
    scratch = path.with_suffix(f".part{part}.ods")
    with zipfile.ZipFile(scratch, "w") as z:
        z.writestr("content.xml", ET.tostring(one))
    try:
        return nu.sheet_state(scratch)
    finally:
        scratch.unlink()


def saved(run, out, name):
    evaluate(run.session, f"(() => {{ {ROOT}.lastSave = null; return true; }})()")  # two saves at one revision look alike otherwise
    run.press("#save-button")
    if not wait(run.session, f"{ROOT}.lastSave !== null && !{ROOT}.state.busy", 60):
        raise RuntimeError(f"save {name} did not settle")
    time.sleep(.5)
    encoded = evaluate(run.session, f"""(async()=>{{const b=new Uint8Array({ROOT}.lastExport);let s='';
      for(let i=0;i<b.length;i+=8192)s+=String.fromCharCode(...b.subarray(i,i+8192));return btoa(s);}})()""")
    path = out / f"{run.record['browser']}-{name}.ods"
    path.write_bytes(base64.b64decode(encoded))
    return path


def fresh(run):
    # An unsaved page holds the next navigation in beforeunload for CDP's 180 s (shakedown-01, after cu6): save first.
    if evaluate(run.session, f"Boolean(window.__calcEditor?.state?.dirty)"):
        run.fresh_saves = getattr(run, "fresh_saves", 0) + 1
        saved(run, run.out, f"before-navigate-{run.fresh_saves}")
    navigate(run.session, run.url)
    run.session.set_file("#file-input", run.fixture)
    if not wait(run.session, f"Boolean({ROOT}.state?.cell)", 120):
        raise RuntimeError("the fixture did not open")
    run.idle()
    run_in_page(run.session, WATCH)
    time.sleep(.2)


def key(run, name, mods=()):
    real.key(run.session, run.record["browser"], name, mods)
    time.sleep(.4)
    run.idle()


def commit(run, address, text):
    select(run.session, address)
    type_text(run.session, "#formula-input", text)
    box_key(run.session, "Enter")
    wait(run.session, f"!{ROOT}.state.busy && !{ROOT}.state.editing")
    run.idle()


def sent_since(run, mark):
    return evaluate(run.session, f"window.__u.sent.slice({mark})")


def button(run, which):
    """Press #undo-button or #redo-button if the page offers it; False when it does not."""
    selector = f"#{which}-button"
    if not evaluate(run.session, BUTTON.replace("ARG", json.dumps(selector))):
        return False
    run.press(selector)
    time.sleep(.4)
    run.idle()
    return True


def same(a, b, cells):
    return all(a.get(c) == b.get(c) for c in cells)


def cu1(run, out):
    fresh(run)
    base = part_state(saved(run, out, "cu1-zero"), 0)
    commit(run, "D9", "CU1")
    landed = run.state()["cell"].get("input") == "CU1" or part_state(saved(run, out, "cu1-input-written"), 0).get("3,8") is not None
    pressed = button(run, "undo")
    after = part_state(saved(run, out, "cu1-input-undone"), 0)
    run.check("CU-1/input", pressed and landed and same(after, base, ["3,8"]), {"button": pressed, "D9": (after.get("3,8") or {}).get("text")})
    select(run.session, "A1")
    run.idle()
    key(run, "b", ("ctrl",))
    bold = run.state()["cell"].get("bold") is True
    pressed = button(run, "undo")
    after = part_state(saved(run, out, "cu1-bold-undone"), 0)
    run.check("CU-1/cell-bold", pressed and bold and same(after, base, ["0,0"]), {"button": pressed, "boldBefore": bold, "A1": after.get("0,0")})
    select(run.session, "A1")
    key(run, "ArrowRight", ("shift",))
    key(run, "ArrowDown", ("shift",))
    multiple = run.state()["selection"].get("multiple") is True
    run.choose("backColor", "#ffe599")
    filled = run.state().get("rangeFormat", {}).get("backColor") == "#ffe599" if multiple else False
    pressed = button(run, "undo")
    after = part_state(saved(run, out, "cu1-fill-undone"), 0)
    run.check("CU-1/range-fill", pressed and filled and same(after, base, ["0,0", "1,0", "0,1", "1,1"]),
              {"button": pressed, "range": multiple, "filled": filled, "B2": after.get("1,1")})


def cu2(run, out):
    fresh(run)
    base = part_state(saved(run, out, "cu2-zero"), 0)
    commit(run, "D9", "CU2")
    mark = evaluate(run.session, SENT)
    key(run, "z", ("ctrl",))
    undone = part_state(saved(run, out, "cu2-ctrl-z"), 0)
    asked = sent_since(run, mark)
    run.check("CU-2/ctrl-z-input", same(undone, base, ["3,8"]), {"D9": (undone.get("3,8") or {}).get("text"), "sent": asked[:4]})
    key(run, "y", ("ctrl",))
    redone = part_state(saved(run, out, "cu2-ctrl-y"), 0)
    # A redo only counts after an undo that took the value away: on v3 the value never left (red-on-v3, first run).
    run.check("CU-2/ctrl-y-input", same(undone, base, ["3,8"]) and (redone.get("3,8") or {}).get("text") == "CU2", (redone.get("3,8") or {}).get("text"))
    select(run.session, "A1")
    run.idle()
    key(run, "b", ("ctrl",))
    key(run, "z", ("ctrl",))
    undone = part_state(saved(run, out, "cu2-bold-ctrl-z"), 0)
    bold_undone = same(undone, base, ["0,0"])
    run.check("CU-2/ctrl-z-bold", bold_undone, undone.get("0,0"))
    key(run, "z", ("ctrl", "shift"))
    redone = part_state(saved(run, out, "cu2-bold-ctrl-shift-z"), 0)
    weight = json.dumps(redone.get("0,0") or {})
    run.check("CU-2/ctrl-shift-z-bold", bold_undone and '"bold"' in weight, redone.get("0,0"))


def cu3(run, out):
    fresh(run)
    base = part_state(saved(run, out, "cu3-zero"), 0)
    select(run.session, "D9")
    type_text(run.session, "#formula-input", "abc")
    mark = evaluate(run.session, SENT)
    real.key(run.session, run.record["browser"], "z", ("ctrl",))
    time.sleep(.5)
    asked = sent_since(run, mark)
    focus = evaluate(run.session, "document.activeElement?.id")
    box_key(run.session, "Escape")
    run.idle()
    after = part_state(saved(run, out, "cu3-after"), 0)
    run.check("CU-3/field-keeps-its-undo", "undo" not in asked and focus == "formula-input" and same(after, base, list(base) + ["3,8"]),
              {"sent": asked, "focus": focus})


def cu4(run, out):
    fresh(run)
    base = part_state(saved(run, out, "cu4-zero"), 0)
    commit(run, "D9", "FIRST")
    select(run.session, "D10")
    type_text(run.session, "#formula-input", "DRAFT")
    mark = evaluate(run.session, SENT)
    pressed = button(run, "undo")
    asked = sent_since(run, mark)
    draft = evaluate(run.session, FORMULA)
    kept = part_state(saved(run, out, "cu4-draft-dropped"), 0)
    run.check("CU-4/draft-dropped", pressed and "undo" not in asked and draft == "" and (kept.get("3,8") or {}).get("text") == "FIRST"
              and kept.get("3,9") is None, {"button": pressed, "sent": asked[:4], "formula": draft, "toast": evaluate(run.session, TOAST)})
    pressed = button(run, "undo")
    after = part_state(saved(run, out, "cu4-second-press"), 0)
    run.check("CU-4/second-press-undoes-the-write", pressed and same(after, base, ["3,8", "3,9"]), (after.get("3,8") or {}).get("text"))


def cu5(run, out):
    fresh(run)
    answers = {}
    for which, sentence in (("undo", "沒有可以復原的動作。"), ("redo", "沒有可以重做的動作。")):
        pressed = button(run, which)
        toast = evaluate(run.session, TOAST)
        answers[which] = {"button": pressed, "toast": toast}
        run.check(f"CU-5/nothing-to-{which}", pressed and toast["text"] == sentence and not toast["error"]
                  and run.state().get("state") == "ready" and not run.state().get("uncertain"), answers[which])


def cu6(run, out):
    fresh(run)
    commit(run, "D9", "SIX")
    select(run.session, "A1")
    run.idle()
    key(run, "z", ("ctrl",))
    cell = run.state()["cell"]
    run.check("CU-6/follows-the-restored-cell", [cell.get("column"), cell.get("row")] == [3, 8] and evaluate(run.session, FORMULA) == "",
              {"cell": [cell.get("column"), cell.get("row")], "formula": evaluate(run.session, FORMULA)})
    select(run.session, "A1")
    run.idle()
    key(run, "b", ("ctrl",))
    on = evaluate(run.session, "document.querySelector('[data-format=bold]').getAttribute('aria-pressed')")
    key(run, "z", ("ctrl",))
    off = evaluate(run.session, "document.querySelector('[data-format=bold]').getAttribute('aria-pressed')")
    run.check("CU-6/bold-button-shows-the-restored-state", on == "true" and off == "false" and run.state()["cell"].get("bold") is False,
              {"before": on, "after": off})


def cu7(run, out):
    fresh(run)
    base = part_state(saved(run, out, "cu7-zero"), 0)
    commit(run, "D9", "SEVEN")
    written = part_state(saved(run, out, "cu7-saved"), 0)
    key(run, "z", ("ctrl",))
    after = part_state(saved(run, out, "cu7-undone-after-save"), 0)
    run.check("CU-7/undo-after-save", (written.get("3,8") or {}).get("text") == "SEVEN" and same(after, base, ["3,8"]),
              (after.get("3,8") or {}).get("text"))


def cu9(run, out):
    fresh(run)
    base = part_state(saved(run, out, "cu9-zero"), 1)
    select(run.session, "Z60")
    run.idle()
    view = evaluate(run.session, VIEW)
    run.press('.sheet-tab[data-part="1"]')
    run.idle()
    commit(run, "B2", "S2")
    written = (part_state(saved(run, out, "cu9-written"), 1).get("1,1") or {}).get("text")  # the write landed on the second sheet
    run.press('.sheet-tab[data-part="0"]')
    run.idle()
    back = evaluate(run.session, VIEW)
    pressed = button(run, "undo")
    state = run.state()
    cell = state["cell"]
    shown = [state.get("currentPart"), cell.get("column"), cell.get("row")]
    run.check("CU-9/shows-the-sheet-and-cell", pressed and shown == [1, 1, 1] and evaluate(run.session, FORMULA) == "",
              {"button": pressed, "shown": shown, "viewBeforeUndo": back})
    run.press('.sheet-tab[data-part="0"]')
    run.idle()
    time.sleep(.5)
    again = evaluate(run.session, VIEW)
    # Only after a switch: without one the view is trivially kept (red-on-v3-02).
    run.check("CU-9/the-sheet-left-keeps-its-view", shown == [1, 1, 1] and back == view and again == view,
              {"view": view, "back": back, "again": again})
    after = part_state(saved(run, out, "cu9-after"), 1)
    run.check("CU-9/the-file", written == "S2" and same(after, base, ["1,1"]), {"written": written, "after": after.get("1,1")})


ARMS = (cu1, cu2, cu3, cu4, cu5, cu6, cu7, cu9)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--mutate", choices=["field-guard"])
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = mirror(out, args.engine, args.mutate)
    fixture = create(out / "fixture")
    port = free_port()
    log = (out / "server.txt").open("w")
    server = subprocess.Popen(["python3", str(PROJECT / "web/serve.py"), "--port", str(port), "--root", str(root)], stdout=log,
                              stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/ods-editor.html?diagnostics=1"
    report = {"engine": str(args.engine.resolve()), "mutate": args.mutate, "runs": []}
    try:
        wait_page(url)
        with browser_lock("calc-undo-cu", wait_s=600):
            for browser in args.browsers.split(","):
                session, record = None, {"browser": browser, "checks": [], "fatal": {}}
                report["runs"].append(record)
                try:
                    session = open_browser(browser, WINDOW)
                    record["version"] = session.version
                    run = Run(session, record, url, fixture)
                    run.out = out
                    for arm in ARMS:
                        try:
                            arm(run, out)
                        except Exception as error:  # noqa: BLE001  one arm's failure is recorded, the next arm still runs
                            record["fatal"][arm.__name__] = repr(error)
                            try:
                                (out / f"{browser}-{arm.__name__}-fatal.png").write_bytes(session.screenshot())
                            except Exception as shot:  # noqa: BLE001  a page held by a dialog cannot be shot either (shakedown-01)
                                record["fatal"][arm.__name__ + "/screenshot"] = repr(shot)
                finally:
                    if session:
                        record["cleanup"] = close_browser(session)
                    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()
        shutil.rmtree(root, ignore_errors=True)
    checks = [c for r in report["runs"] for c in r["checks"]]
    report["verdict"] = "CU_HOLDS" if checks and all(c["pass"] for c in checks) and not any(r["fatal"] for r in report["runs"]) else "CU_RED"
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(report["verdict"], [(r["browser"], [c["id"] for c in r["checks"] if not c["pass"]], list(r["fatal"])) for r in report["runs"]])
    return 0 if report["verdict"] == "CU_HOLDS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
