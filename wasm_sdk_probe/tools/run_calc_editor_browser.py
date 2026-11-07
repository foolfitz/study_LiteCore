#!/usr/bin/env python3
"""Exercise the real cell editor on an isolated mirror and browser profile."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from create_calc_edit_fixture import create
from r7_support import evaluate, wait_page
from run_browser_probe import ChromeSession, FirefoxSession, free_port
from run_e2_c_page_smoke import navigate
from v21_shakedown_common import browser_lock, close_browser, open_browser
from run_calc_cell_native import cells_from_xml, NAMES

PROJECT = Path(__file__).resolve().parents[1]


def mirror(out, profile):
    root = PROJECT / "build/calc-editor-browser" / out.name
    root.mkdir(parents=True, exist_ok=False)
    for name in ("ods-editor.html", "ods-editor-app.js"):
        shutil.copyfile(PROJECT / "web" / name, root / name)
    # This generic mirror deliberately aliases its selected engine as v1.
    # Keep that private URL valid after the product switches to a successor;
    # successor-specific wrappers rename both the alias and URL together.
    app=root/"ods-editor-app.js"
    source=app.read_text()
    # ods-editor-v4 added 2026-11-03 when the page moved to it (SPEC-P-calc-undo); a page URL this list lacks loads nothing.
    # ods-editor-v5 added the same day for the same reason (SPEC-P-ms-formats); ods-editor-v6 2026-11-05 (headers, structure);
    # ods-editor-v7 2026-11-06 (copy); ods-editor-v8 2026-11-07 (copy text/html, zoom).
    for live in ('"./profiles/ods-editor-v2/sdk-worker.js"','"./profiles/ods-editor-v3/sdk-worker.js"','"./profiles/ods-editor-v4/sdk-worker.js"',
                 '"./profiles/ods-editor-v5/sdk-worker.js"','"./profiles/ods-editor-v6/sdk-worker.js"','"./profiles/ods-editor-v7/sdk-worker.js"',
                 '"./profiles/ods-editor-v8/sdk-worker.js"'):
        source=source.replace(live,'"./profiles/ods-editor-v1/sdk-worker.js"')
    app.write_text(source)
    for directory in ("sdk", "viewer-shell", "spreadsheet-shell"):
        shutil.copytree(PROJECT / directory, root / directory)
    (root / "reader-shell").mkdir()
    shutil.copyfile(PROJECT / "reader-shell/tile-scheduler.js", root / "reader-shell/tile-scheduler.js")
    (root / "profiles").mkdir()
    (root / "profiles/ods-editor-v1").symlink_to(profile.resolve(), target_is_directory=True)
    (root / "profiles/resources").symlink_to(PROJECT / "dist/profiles/resources", target_is_directory=True)
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in root.rglob("*") if p.is_file()}
    (out / "mirror-sources.json").write_text(json.dumps({"root": str(root), "sha256": hashes}, indent=2) + "\n")
    return root


def wait(session, expression, timeout=120):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = evaluate(session, expression)
        if last:
            return last
        time.sleep(.1)
    raise RuntimeError(f"condition did not become true: {expression}; last {last}")


def key(session, name):
    codes = {"Enter": (13, "\ue007"), "Escape": (27, "\ue00c"), "Backspace": (8, "\ue003")}
    code, webdriver = codes[name]
    if isinstance(session, ChromeSession):
        session.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": name, "code": name, "windowsVirtualKeyCode": code})
        session.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": name, "code": name, "windowsVirtualKeyCode": code})
    else:
        element = session.command("GET", "/element/active")["element-6066-11e4-a52e-4f735466cecf"]
        session.command("POST", f"/element/{element}/value", {"text": webdriver})


def type_text(session, selector, text):
    wait(session, f"!document.querySelector({json.dumps(selector)}).disabled")
    evaluate(session, f"(()=>{{const n=document.querySelector({json.dumps(selector)});n.focus();n.select();return true;}})()")
    key(session, "Backspace")
    if text:
        if isinstance(session, ChromeSession):
            session.call("Input.insertText", {"text": text})
        else:
            element = session.command("GET", "/element/active")["element-6066-11e4-a52e-4f735466cecf"]
            session.command("POST", f"/element/{element}/value", {"text": text})


def select(session, address):
    type_text(session, "#cell-address", address)
    key(session, "Enter")
    wait(session, f"window.__calcEditor.state.cell && !window.__calcEditor.state.busy && document.querySelector('#cell-address').value === {json.dumps(address)}")


def double_click(session, x, y):
    if isinstance(session, ChromeSession):
        for count in (1, 2):
            for kind in ("mousePressed", "mouseReleased"):
                session.call("Input.dispatchMouseEvent", {"type": kind, "x": x, "y": y, "button": "left", "clickCount": count})
            time.sleep(.08)
    else:
        session.command("POST", "/actions", {"actions": [{"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"}, "actions": [
            {"type": "pointerMove", "duration": 0, "origin": "viewport", "x": round(x), "y": round(y)},
            {"type": "pointerDown", "button": 0}, {"type": "pointerUp", "button": 0}, {"type": "pause", "duration": 80},
            {"type": "pointerDown", "button": 0}, {"type": "pointerUp", "button": 0}]}]})


def exercise(session, out, run):
    def check(name, passed, actual):
        run["checks"].append({"id": name, "pass": bool(passed), "actual": actual})
        if not passed:
            raise RuntimeError(f"{name} failed: {actual!r}")

    def state():
        return evaluate(session, "window.__calcEditor.state")

    def commit_formula(address, text):
        select(session, address)
        type_text(session, "#formula-input", text)
        key(session, "Enter")
        wait(session, "!window.__calcEditor.state.busy && !window.__calcEditor.state.editing")
        snapshot = state()
        check("formula-input/" + address, snapshot["cell"]["input"] == text, snapshot["cell"])
        return snapshot

    prefix = f"{run['browser']}-r{run['repeat']}"
    wait(session, "document.querySelectorAll('#tiles canvas').length > 0 && !window.__calcEditor.state.busy")
    point = evaluate(session, "(()=>{const b=document.querySelector('#surface').getBoundingClientRect();return {x:b.left+40,y:b.top+9};})()")
    double_click(session, point["x"], point["y"])
    wait(session, "window.__calcEditor.state.editing === 'inline'")
    geometry = evaluate(session, "(()=>{const a=document.querySelector('#cell-editor').getBoundingClientRect();const b=document.querySelector('#selection').getBoundingClientRect();return {dx:a.x-b.x,dy:a.y-b.y,focus:document.activeElement.id};})()")
    check("double-click-in-place", abs(geometry["dx"]) <= 1 and abs(geometry["dy"]) <= 1 and geometry["focus"] == "cell-editor", geometry)
    (out / f"{prefix}-inline.png").write_bytes(session.screenshot())
    type_text(session, "#cell-editor", "原地輸入 中文123")
    key(session, "Enter")
    wait(session, "!window.__calcEditor.state.busy && !window.__calcEditor.state.editing")
    check("inline-input", state()["cell"]["input"] == "原地輸入 中文123", state()["cell"])
    commit_formula("B1", "21")
    snapshot = commit_formula("C1", "=B1*3")
    check("formula-recalculates", snapshot["cell"]["value"] == 63 and snapshot["cell"]["text"] == "63", snapshot["cell"])
    revision = state()["revision"]
    type_text(session, "#formula-input", "=1+999")
    key(session, "Escape")
    check("escape-no-mutation", state()["revision"] == revision and state()["draft"] == "=B1*3", state())
    commit_formula("C2", "")
    literal = commit_formula("F2", "'=B1*9")
    check("literal-stays-text", literal["cell"]["cellType"] == 2 and literal["cell"]["text"] == "=B1*9", literal["cell"])
    commit_formula("E2", '第一行\n第二行 "引號"')
    select(session, "B2")
    manifest = json.loads((out / "fixture/manifest.json").read_text())
    for format in manifest["formats"]:
        for enabled in (True, False, True):
            session.click(f'[data-format="{format}"]')
            wait(session, "!window.__calcEditor.state.busy")
            check(f"{format}/{enabled}", state()["cell"][format] is enabled, state()["cell"])
    (out / f"{prefix}-formatted.png").write_bytes(session.screenshot())
    session.click('[data-part="1"]')
    wait(session, "window.__calcEditor.state.currentPart === 1 && !window.__calcEditor.state.busy")
    check("other-sheet-preserved", state()["cell"]["input"] == "第二表不應改動", state()["cell"])
    session.click('[data-part="2"]')
    wait(session, "window.__calcEditor.state.currentPart === 2 && !window.__calcEditor.state.busy")
    protection = evaluate(session, "({input:window.__calcEditor.state.cell.input,disabled:document.querySelector('#formula-input').disabled,formatDisabled:document.querySelector('[data-format]').disabled})")
    check("protected-cell-disabled", protection["disabled"] and protection["formatDisabled"] and protection["input"] == "鎖定內容", protection)
    commit_formula("B1", "Unlocked updated")
    select(session, "A1")
    check("protected-selection-still-allows-save", evaluate(session, "!document.querySelector('#save-button').disabled"), state())
    session.click("#save-button")
    wait(session, "window.__calcEditor.lastSave && !window.__calcEditor.state.saving")
    encoded = evaluate(session, "btoa(Array.from(new Uint8Array(window.__calcEditor.lastExport),n=>String.fromCharCode(n)).join(''))")
    downloaded = Path(run["downloadDirectory"]) / "cell-editing.ods"
    deadline = time.monotonic() + 30
    while not downloaded.is_file() and time.monotonic() < deadline:
        time.sleep(.1)
    actual_download = downloaded.read_bytes() if downloaded.is_file() else b""
    expected_export = base64.b64decode(encoded)
    check("browser-downloaded-real-file", bool(actual_download) and actual_download == expected_export,
          {"file": str(downloaded), "bytes": len(actual_download), "sha256": hashlib.sha256(actual_download).hexdigest()})
    saved = out / f"{prefix}-saved.ods"; saved.write_bytes(actual_download)
    check("save-cleans-only-after-export", not state()["dirty"], state())
    content, cells = cells_from_xml(saved)
    formula = cells[(0, 2, 0)]
    check("saved-xml-formula", formula.get(f"{{{NAMES['t']}}}formula") == "of:=[.B1]*3" and formula.get(f"{{{NAMES['o']}}}value") == "63", dict(formula.attrib))
    styled = cells[(0, 1, 1)]; style = styled.get(f"{{{NAMES['t']}}}style-name")
    attributes = content.find(f".//s:style[@s:name='{style}']/s:text-properties", NAMES)
    check("saved-xml-formats", attributes is not None and attributes.get(f"{{{NAMES['f']}}}font-weight") == "bold" and attributes.get(f"{{{NAMES['f']}}}font-style") == "italic" and attributes.get(f"{{{NAMES['s']}}}text-underline-style") == "solid", attributes.attrib if attributes is not None else None)
    session.set_file("#file-input", saved)
    wait(session, f"window.__calcEditor.state?.fileName === {json.dumps(saved.name)} && Boolean(window.__calcEditor.state.cell)")
    # Calc persists the active sheet. The saved file was on protection sheet 2;
    # explicitly return to sheet 0 before reading the edited C1/B2/A2.
    session.click('[data-part="0"]')
    wait(session, "window.__calcEditor.state.currentPart === 0 && !window.__calcEditor.state.busy")
    select(session, "C1")
    check("reopen-formula", state()["cell"]["input"] == "=B1*3" and state()["cell"]["value"] == 63, state()["cell"])
    select(session, "B2")
    check("reopen-formats", all(state()["cell"][key] for key in manifest["formats"]), state()["cell"])
    select(session, "A2")
    check("neighbor-preserved", state()["cell"]["input"] == "鄰格必須保留", state()["cell"])
    (out / f"{prefix}-reopened.png").write_bytes(session.screenshot())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--profile", type=Path, default=PROJECT / "build/ods/editor-v1/profile")
    ap.add_argument("--browsers", default="chrome,firefox")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--smoke-only", action="store_true")
    args = ap.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    root = mirror(out, args.profile)
    fixture = create(out / "fixture")
    port = free_port()
    log = (out / "server.txt").open("w")
    server = subprocess.Popen(["python3", str(PROJECT / "web/serve.py"), "--port", str(port), "--root", str(root)], stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/ods-editor.html?diagnostics=1"
    report = {"url": url, "profile": str(args.profile), "smokeOnly": args.smoke_only, "runs": []}
    try:
        wait_page(url)
        with browser_lock("calc-editor", wait_s=0):
            for browser in args.browsers.split(","):
                for repeat in range(1, args.repeats + 1):
                    session = None
                    run = {"browser": browser, "repeat": repeat, "checks": [], "error": None}
                    report["runs"].append(run)
                    try:
                        download_dir = out / f"downloads-{browser}-r{repeat}"; download_dir.mkdir()
                        run["downloadDirectory"] = str(download_dir)
                        session = open_browser(browser, (1440, 1000), firefox_prefs={
                            "browser.download.dir": str(download_dir), "browser.download.folderList": 2,
                            "browser.download.useDownloadDir": True,
                            "browser.helperApps.neverAsk.saveToDisk": "application/vnd.oasis.opendocument.spreadsheet"})
                        if isinstance(session, ChromeSession):
                            session.call("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(download_dir)})
                        run["version"] = session.version
                        navigate(session, url)
                        session.set_file("#file-input", fixture)
                        wait(session, "Boolean(window.__calcEditor?.state?.cell || document.querySelector('#toast.error'))")
                        run["opened"] = evaluate(session, "window.__calcEditor.state")
                        run["toast"] = evaluate(session, "document.querySelector('#toast').textContent")
                        run["events"] = evaluate(session, "window.__calcEditor.events.slice(-15)")
                        run["checks"].append({"id": "opened-cell", "pass": bool(run["opened"].get("cell"))})
                        (out / f"{browser}-r{repeat}-opened.png").write_bytes(session.screenshot())
                        if not args.smoke_only and run["opened"].get("cell"):
                            exercise(session, out, run)
                    except Exception as error:
                        run["error"] = repr(error)
                        if session:
                            try:
                                run["failureState"] = evaluate(session, "window.__calcEditor?.state")
                                run["failureToast"] = evaluate(session, "document.querySelector('#toast')?.textContent")
                                (out / f"{browser}-r{repeat}-failure.png").write_bytes(session.screenshot())
                            except Exception:
                                pass
                    finally:
                        if session:
                            run["cleanup"] = close_browser(session)
                        (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    finally:
        server.terminate(); server.wait(timeout=10); log.close()
    ok = bool(report["runs"]) and all(not r["error"] and all(c["pass"] for c in r["checks"]) for r in report["runs"])
    print(json.dumps({"pass": ok, "runs": [{"browser": r["browser"], "passed": sum(c["pass"] for c in r["checks"]), "checks": len(r["checks"]), "error": r["error"], "toast": r.get("toast")} for r in report["runs"]]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
