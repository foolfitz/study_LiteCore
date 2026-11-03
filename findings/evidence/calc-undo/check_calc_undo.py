#!/usr/bin/env python3
"""Does the Calc page have undo?  The owner asked on 2026-11-03.  A probe, not a gate: every arm is recorded.

On a mirror of the live Calc page with the frozen ods-editor-v3 engine, real keys and a real pointer; the saved ODS is the answer.

  U1  what the page offers: any control named undo or redo.
  U2  a committed value, Ctrl+Z, the file.
  U3  Ctrl+B, which must land first, so a dead Ctrl+Z cannot be a key that never arrived; then Ctrl+Z, the file.
  U4  mid-edit: three letters in the cell editor, Ctrl+Z.  That is the browser's own undo of a text field, not the document's, and it is read apart.
      Chrome's CDP key fires no editing command by itself, so Chrome is also pressed with `commands: ["undo"]`.
  U5  the worker: an `undo` request posted straight at it, past the page.  Tells "the page has no button" from "the engine refuses".

Every arm records whether the page saw the key and what went to the Worker.

Changed after run-02 (kept): the letters there never reached a cell, the grid had no focus, so U2 read A1 and U4 an empty editor.  The arms now go
the way run_calc_editor_browser.py does, the address box and the formula bar, and U2 first checks the value landed.  U3 reads the weight from the
file.  U5's request carries protocolVersion.
  check_calc_undo.py --out DIR [--browsers chrome,firefox]
"""
import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

SDK = Path(__file__).resolve().parents[3] / "wasm_sdk_probe"
sys.path.insert(0, str(SDK / "tools"))
from check_calc_sheet_view import wait  # noqa: E402
from check_calc_style import ROOT, Run, WINDOW, mirror  # noqa: E402
from create_calc_range_format_fixture import create  # noqa: E402
import probe_calc_style_native as native  # noqa: E402
from probe_calc_style_native import cell_style  # noqa: E402
from r7_support import evaluate, run_in_page, wait_page  # noqa: E402
from run_browser_probe import free_port  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402
from v21_shakedown_common import browser_lock, close_browser, open_browser  # noqa: E402
from run_calc_editor_browser import key as box_key, select, type_text  # noqa: E402
import zipfile  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402
import v21_input as real  # noqa: E402

ENGINE = SDK / "dist/profiles/ods-editor-v3"
WATCH = """(() => { if (window.__u) return; const u = window.__u = {keys: [], sent: [], replies: []};
  addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') u.keys.push({target: e.target.id || e.target.tagName}); }, true);
  const post = Worker.prototype.postMessage;
  Worker.prototype.postMessage = function (m, ...rest) { if (m?.kind === 'request') { u.sent.push(m.operation); u.worker = this; u.handle = m.payload?.documentHandle ?? u.handle; } return post.call(this, m, ...rest); };
  const on = Worker.prototype.addEventListener; })()"""
CONTROLS = """[...document.querySelectorAll('button,[role=button],[role=menuitem]')].map(b => [b.id, b.title, b.getAttribute('aria-label'), b.dataset.tip, b.textContent.trim()].filter(Boolean).join(' | ')).filter(t => /undo|redo|復原|取消復原|重做|還原/i.test(t))"""
FORWARD = """(async () => { const u = window.__u, id = 'undo-probe-' + Date.now();
  const answer = new Promise(done => { const on = e => { if (e.data?.requestId === id) { u.worker.removeEventListener('message', on); done(e.data); } }; u.worker.addEventListener('message', on); setTimeout(() => done({timeout: true}), 8000); });
  u.worker.postMessage({protocolVersion: 1, kind: 'request', requestId: id, operation: 'undo', payload: {documentHandle: u.handle, expectedRevision: 0}});
  const a = await answer; window.__undoAnswer = JSON.parse(JSON.stringify({ok: a.ok, timeout: a.timeout, error: a.error ?? null, result: a.result ?? null, keys: Object.keys(a)})); })()"""


def text_of(path, part, column, row):
    _, cells = native.native.cells_from_xml(path)  # the reader probe_calc_style_native imports as `native`
    cell = cells.get((part, column, row))
    return None if cell is None else "".join(cell.itertext())


def bold_of(path, column, row):
    """fo:font-weight of the cell's automatic style, or None."""
    ns = {"s": "urn:oasis:names:tc:opendocument:xmlns:style:1.0", "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"}
    _, cells = native.native.cells_from_xml(path)
    name = cells[(0, column, row)].get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}style-name")
    root = ET.fromstring(zipfile.ZipFile(path).read("content.xml"))
    for style in root.iter("{%s}style" % ns["s"]):
        if style.get("{%s}name" % ns["s"]) == name:
            text = style.find("s:text-properties", ns)
            return None if text is None else text.get("{%s}font-weight" % ns["fo"])
    return None


def saved(run, out, name):
    before = evaluate(run.session, f"{ROOT}.saveCount ?? 0")
    run.press("#save-button")
    wait(run.session, f"{ROOT}.lastSave && !{ROOT}.state.busy", 60)
    time.sleep(.5)
    encoded = evaluate(run.session, f"""(async()=>{{const b=new Uint8Array({ROOT}.lastExport);let s='';
      for(let i=0;i<b.length;i+=8192)s+=String.fromCharCode(...b.subarray(i,i+8192));return btoa(s);}})()""")
    path = out / f"{name}.ods"
    path.write_bytes(base64.b64decode(encoded))
    return path


def fresh(run, fixture):
    navigate(run.session, run.url)
    run.session.set_file("#file-input", fixture)
    wait(run.session, f"Boolean({ROOT}.state?.cell)", 120)
    run.idle()
    run_in_page(run.session, WATCH)
    time.sleep(.2)


def press(run, name, mods=()):
    real.key(run.session, run.record["browser"], name, mods)
    time.sleep(.3)
    run.idle()


def to_blank(run):
    """D9: well below the fixture's cells."""
    for _ in range(8):
        press(run, "ArrowDown")
    for _ in range(3):
        press(run, "ArrowRight")
    return run.state()["cell"]


def watched(run):
    return evaluate(run.session, "(() => ({keys: window.__u.keys.length, sent: window.__u.sent.slice()}))()")


def scenario(run, out, fixture, browser):
    fresh(run, fixture)
    run.record["cells"] = {"U1/controls": evaluate(run.session, CONTROLS)}
    (out / f"{browser}-toolbar.png").write_bytes(run.session.screenshot())
    cells = run.record["cells"]

    session, idle = run.session, f"!{ROOT}.state.busy && !{ROOT}.state.editing"
    select(session, "D9")
    type_text(session, "#formula-input", "UNDOME")
    box_key(session, "Enter")
    wait(session, idle)
    run.idle()
    landed = run.state()["cell"].get("input")
    typed = saved(run, out, f"{browser}-u2-typed")
    mark = watched(run)
    press(run, "z", ("ctrl",))
    time.sleep(1)
    after = watched(run)
    undone = saved(run, out, f"{browser}-u2-after-ctrl-z")
    cells["U2/value"] = {"pageSaysD9": landed, "typed": text_of(typed, 0, 3, 8), "afterCtrlZ": text_of(undone, 0, 3, 8), "pageSawKey": after["keys"] - mark["keys"],
                         "sentToWorker": after["sent"][len(mark["sent"]):]}

    fresh(run, fixture)
    select(session, "A1")
    run.idle()
    press(run, "b", ("ctrl",))
    time.sleep(.5)
    state = run.state()["cell"]
    bold = saved(run, out, f"{browser}-u3-bold")
    mark = watched(run)
    press(run, "z", ("ctrl",))
    time.sleep(1)
    after = watched(run)
    undone = saved(run, out, f"{browser}-u3-after-ctrl-z")
    cells["U3/format"] = {"pageSaysBold": state.get("bold"), "weightInFile": bold_of(bold, 0, 0), "weightAfterCtrlZ": bold_of(undone, 0, 0),
                          "pageSawKey": after["keys"] - mark["keys"], "sentToWorker": after["sent"][len(mark["sent"]):]}

    fresh(run, fixture)
    select(session, "D9")
    type_text(session, "#formula-input", "abc")
    value = "document.querySelector('#formula-input').value"
    typing = evaluate(session, value)
    real.key(session, browser, "z", ("ctrl",))
    time.sleep(.5)
    cells["U4/mid-edit"] = {"typed": typing, "afterCtrlZ": evaluate(session, value), "focus": evaluate(session, "document.activeElement?.id")}
    if browser == "chrome":
        for kind, extra in (("rawKeyDown", {"commands": ["undo"]}), ("keyUp", {})):
            session.call("Input.dispatchKeyEvent", {"type": kind, "key": "z", "code": "KeyZ", "windowsVirtualKeyCode": 90, "modifiers": 2, **extra})
        time.sleep(.5)
        cells["U4/mid-edit"]["afterCdpUndoCommand"] = evaluate(session, value)
    box_key(session, "Escape")
    run.idle()

    fresh(run, fixture)
    press(run, "b", ("ctrl",))
    run_in_page(run.session, FORWARD)
    wait(run.session, "window.__undoAnswer !== undefined", 15)
    cells["U5/worker"] = evaluate(run.session, "window.__undoAnswer")
    run.record["pill"] = run.state().get("state")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browsers", default="chrome,firefox")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = mirror(out, ENGINE)
    fixture = create(out / "fixture")
    port = free_port()
    log = (out / "server.txt").open("w")
    server = subprocess.Popen(["python3", str(SDK / "web/serve.py"), "--port", str(port), "--root", str(root)], stdout=log, stderr=subprocess.STDOUT)
    report = {"runs": []}
    url = f"http://127.0.0.1:{port}/ods-editor.html?diagnostics=1"
    try:
        wait_page(url)
        with browser_lock("calc-undo", wait_s=600):
            for browser in args.browsers.split(","):
                session, record = None, {"browser": browser, "checks": [], "error": None}
                report["runs"].append(record)
                try:
                    session = open_browser(browser, WINDOW)
                    record["version"] = session.version
                    scenario(Run(session, record, url, fixture), out, fixture, browser)
                except Exception as error:  # noqa: BLE001  keep what was read
                    record["error"] = repr(error)
                    if session:
                        (out / f"{browser}-failure.png").write_bytes(session.screenshot())
                finally:
                    if session:
                        record["cleanup"] = close_browser(session)
                    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()
        shutil.rmtree(root, ignore_errors=True)
    print(json.dumps(report, ensure_ascii=False, indent=1)[:3000])


if __name__ == "__main__":
    main()
