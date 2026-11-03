#!/usr/bin/env python3
"""Microsoft formats, WASM measurement M1 (specs/SPEC-P-ms-formats.md): the M0 corpus through the SHIPPED pages and frozen
profiles (dist/: Writer e2-editor-v32, Calc ods-editor-v4), no link, Chrome.

The shipped engine's open boundary accepts only `.odt` / `.ods` names (finding 013), so every file is handed over under its
ODF name.  This is a measurement, not a product path (finding 013 forbids claiming support that way).  M0's odf-name arm says
what that changes natively: for DOCX, DOC and XLSX type detection picks the same filter under either name; for XLS it picks
the template variant ("MS Excel 97 Vorlage/Template") with the same content.

The file reaches the page through the page's own host contract (`globalThis.liteCoreHost`, the one Nextcloud fills), set by
Page.addScriptToEvaluateOnNewDocument: load() gives the corpus bytes, save() keeps the bytes the page saves.  So the open and
the save are the product's (the page's toolbar save button), only the host is fake.  Firefox's WebDriver has no init script;
this tool is Chrome only, and says so in its report.

Per file: time from navigation to ready (Writer: the state pill `ready`; Calc: a selected cell), the page's toast, a
screenshot, then the save button, the saved ODF bytes, and those bytes dumped by the native harness (tools/msformat_native.cpp,
no saves) and compared with M0's native ODF round trip of the same file (`saved.<odf>.dump.txt`): equal dumps mean the WASM
import kept what the native import kept, as far as text and cell formulas go.  Observations, not verdicts.

  run_msformat_wasm.py --native-m0 DIR --harness build/msformat-native/msformat-native --out DIR [--only NAME]
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
from r7_support import evaluate, wait_page                    # noqa: E402
from run_browser_probe import free_port                       # noqa: E402
from run_e2_c_page_smoke import navigate                      # noqa: E402
from v21_shakedown_common import browser_lock, close_browser, open_browser  # noqa: E402
import run_msformat_native as m0                              # noqa: E402

PAGES = {"odt": "e2-editor.html", "ods": "ods-editor.html?diagnostics=1"}
READY = {
    "odt": "(()=>{const p=document.querySelector('#state-pill');const t=document.querySelector('#toast');"
           "return p&&(p.dataset.state==='ready'||p.dataset.state==='stopped'||p.dataset.state==='recoverable-error'"
           "||(t&&t.classList.contains('error')))?{state:p.dataset.state,toast:t&&t.textContent}:null})()",
    "ods": "(()=>{const s=window.__calcEditor&&window.__calcEditor.state;const t=document.querySelector('#toast');"
           "return (s&&s.cell)||(t&&t.classList.contains('error'))?{state:s,toast:t&&t.textContent}:null})()",
}
SAVE = {"odt": "document.querySelector('[data-action=\"save\"]').click(),true",
        "ods": "document.querySelector('#save-button').click(),true"}

HOST = """
(() => {
  const b64 = %s, name = %s;
  const bytes = () => { const s = atob(b64); const u = new Uint8Array(s.length);
                        for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return u.buffer; };
  const encode = (buffer) => { const u = new Uint8Array(buffer); let s = '';
                               for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode(...u.subarray(i, i + 0x8000));
                               return btoa(s); };
  globalThis.__msHost = { loads: 0, saves: [] };
  globalThis.liteCoreHost = {
    async load() { globalThis.__msHost.loads++; return { bytes: bytes(), name, readOnly: false }; },
    async save(buffer, options = {}) {
      const data = buffer instanceof ArrayBuffer ? buffer : buffer.buffer;
      globalThis.__msHost.saves.push({ at: performance.now(), size: data.byteLength, name: options.name,
                                       trigger: options.trigger, b64: encode(data) });
      return { name: options.name || name, target: 'original' };
    },
    watchUnsaved() {},
  };
})();
"""


def wait_for(session, expression, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = evaluate(session, expression)
        except Exception:  # noqa: BLE001 -- the page may be mid-navigation
            value = None
        if value:
            return value
        time.sleep(0.2)
    return None  # a timeout is reported as such, never as a truthy result (memory 2026-11-03)


def native_dump(harness, saved, work):
    work.mkdir(parents=True)
    (work / "out").mkdir()
    argv = [str(harness), str(m0.PROGRAM), (work / "profile").as_uri(), str(saved), str(work / "out"), ""]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        report = json.loads(done.stdout) if done.stdout.strip().startswith("{") else None
        return {"exit": done.returncode, "report": report}
    except subprocess.TimeoutExpired:
        return {"exit": "timeout"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--native-m0", type=Path, required=True)
    parser.add_argument("--harness", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--only")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    native = json.loads((args.native_m0 / "report.json").read_text())
    native_dirs = {f["name"]: args.native_m0 / f"{i:02d}-{f['name']}" for i, f in enumerate(native["files"])}
    items = [i for i in m0.corpus() if (not args.only or i["name"] == args.only) and i["name"] in native_dirs]
    if not items:
        raise SystemExit("empty corpus")
    dist = PROJECT / "dist"
    report = {"schema": 1, "browser": "chrome", "firefox": "not run: WebDriver classic has no init script",
              "pages": {k: hashlib.sha256((dist / v.split('?')[0]).read_bytes()).hexdigest() for k, v in PAGES.items()},
              "nativeM0": str(args.native_m0.resolve()), "files": []}
    port = free_port()
    log = (out / "server.txt").open("w")
    server = subprocess.Popen([sys.executable, str(PROJECT / "web/serve.py"), "--port", str(port)],
                              stdout=log, stderr=subprocess.STDOUT)
    try:
        wait_page(f"http://127.0.0.1:{port}/e2-editor.html")
        with browser_lock("msformat-wasm", wait_s=0):
            for index, item in enumerate(items):
                odf = m0.ODF[item["suffix"]]
                name = f"{Path(item['name']).stem}.{odf}"
                base = out / f"{index:02d}-{item['name']}"
                base.mkdir()
                entry = {"name": item["name"], "sha256": item["sha256"], "inputName": name, "page": PAGES[odf]}
                report["files"].append(entry)
                session = None
                try:
                    session = open_browser("chrome", (1440, 1000))
                    entry["version"] = session.version
                    source = HOST % (json.dumps(base64.b64encode(item["path"].read_bytes()).decode()), json.dumps(name))
                    session.call("Page.addScriptToEvaluateOnNewDocument", {"source": source})
                    started = time.monotonic()
                    navigate(session, f"http://127.0.0.1:{port}/{PAGES[odf]}")
                    ready = wait_for(session, READY[odf], 240)
                    entry["readySeconds"] = round(time.monotonic() - started, 2) if ready else None
                    entry["ready"] = ready
                    entry["hostLoads"] = evaluate(session, "globalThis.__msHost && globalThis.__msHost.loads")
                    (base / "opened.png").write_bytes(session.screenshot())
                    opened = bool(ready) and (ready.get("state") == "ready" if odf == "odt" else bool((ready.get("state") or {}).get("cell")))
                    entry["opened"] = opened
                    if opened:
                        evaluate(session, SAVE[odf])
                        started = time.monotonic()
                        # The saved bytes come back in slices: one CDP frame is capped at 1 MiB by the websocket client, and
                        # an ODT with embedded fonts is 9 MB (the first run of this tool died on it).
                        saved = wait_for(session, "globalThis.__msHost.saves.length>0&&{name:globalThis.__msHost.saves[0].name,"
                                                  "length:globalThis.__msHost.saves[0].b64.length}", 180)
                        entry["saveSeconds"] = round(time.monotonic() - started, 2) if saved else None
                        if saved:
                            text = "".join(evaluate(session, f"globalThis.__msHost.saves[0].b64.slice({i},{i + 500000})")
                                           for i in range(0, saved["length"], 500000))
                            data = base64.b64decode(text)
                            target = base / f"wasm-saved.{odf}"
                            target.write_bytes(data)
                            entry["saved"] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "name": saved.get("name")}
                            dumped = native_dump(args.harness.resolve(), target, base / "dump")
                            entry["dump"] = {k: v for k, v in dumped.items() if k != "report"}
                            entry["dump"]["filter"] = ((dumped.get("report") or {}).get("source") or {}).get("filter")
                            reference = native_dirs[item["name"]] / f"true-name/out/saved.{odf}.dump.txt"
                            entry["vsNativeOdfRoundTrip"] = m0.compare(m0.dump(base / "dump/out/source.dump.txt"), m0.dump(reference))
                            # Lean evidence, as M0's: the saved bytes by sha256 (above), the dump gzipped, no profile.
                            target.unlink()
                            import shutil
                            shutil.rmtree(base / "dump/profile", ignore_errors=True)
                            for path in sorted((base / "dump/out").iterdir()):  # listed before any .gz is written
                                if path.name.endswith(".dump.txt"):
                                    path.with_name(path.name + ".gz").write_bytes(gzip.compress(path.read_bytes(), mtime=0))
                                path.unlink()
                    entry["toastAfter"] = evaluate(session, "document.querySelector('#toast')&&document.querySelector('#toast').textContent")
                except Exception as error:  # noqa: BLE001
                    entry["error"] = repr(error)
                    if session:
                        try:
                            (base / "failure.png").write_bytes(session.screenshot())
                        except Exception:  # noqa: BLE001
                            pass
                finally:
                    if session:
                        entry["cleanup"] = close_browser(session)
                    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
                cmp = entry.get("vsNativeOdfRoundTrip", {})
                print(f"{item['name']}: opened={entry.get('opened')} ready={entry.get('readySeconds')}s "
                      f"save={entry.get('saveSeconds')}s sameAsNative={cmp.get('equal')} error={entry.get('error')}", flush=True)
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
