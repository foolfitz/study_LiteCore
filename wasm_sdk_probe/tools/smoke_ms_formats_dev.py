#!/usr/bin/env python3
"""Microsoft formats, post-link smoke on the DEVELOPMENT profiles (specs/SPEC-P-ms-formats.md 6.2, before the pages change), Chrome.

Not the W criteria: the pages are still generation 88 / the v4 Calc page, which save in ODF only.  This is the first look at the
linked engines through the shipped pages, on a mirror of dist/ in which

  - ods-editor-app.js loads ./profiles/ods-editor-v5/ (a symlink to build/ods/editor-v5/profile);
  - e2-editor-app.js loads ./profiles/e2-editor-v33/ (build/e2/editor-v33/profile) and pins that wasm's sha256 prefix in place of
    v32's (the page refuses any other build, PAGE_BUILD_MISMATCH);

and every other file is a symlink to dist/.  With --baseline the mirror is dist/ unchanged (v32 / v4): the red case.

Per corpus DOCX / XLSX (M0's list), under its TRUE name, through the page's own host contract (as run_msformat_wasm.py):
  opened        the page reaches ready;
  odf           the page's save button (ODF), dumped natively, equals M0's native ODF round trip;
  xlsx          Calc only: `__calcEditor.session.document.save({format: "xlsx"})` (the Writer page exposes no session), the bytes are
                OOXML (zip with [Content_Types].xml, no mimetype) and their dump equals M0's own-format round trip.
Plus refused names (`.doc`, `.docm` to Writer; `.xls`, `.xlsm` to Calc): the page must not reach ready.
Observations, not verdicts.
  smoke_ms_formats_dev.py --native-m0 DIR --harness FILE --out DIR [--baseline] [--only NAME]
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
from r7_support import evaluate, wait_page                    # noqa: E402
from run_browser_probe import free_port                       # noqa: E402
from run_e2_c_page_smoke import navigate                      # noqa: E402
from v21_shakedown_common import browser_lock, close_browser, open_browser  # noqa: E402
import run_msformat_native as m0                              # noqa: E402
import run_msformat_wasm as m1                                # noqa: E402

DEV = {"writer": PROJECT / "build/e2/editor-v33/profile", "calc": PROJECT / "build/ods/editor-v5/profile"}
PAGES = {"docx": "e2-editor.html", "xlsx": "ods-editor.html?diagnostics=1"}
KIND = {"docx": "odt", "xlsx": "ods"}
REFUSED = [("Report.doc", "docx"), ("Report.docm", "docx"), ("Book.xls", "xlsx"), ("Book.xlsm", "xlsx")]


def mirror(root, baseline):
    dist = PROJECT / "dist"
    if baseline:
        return dist, {}
    root.mkdir(parents=True)
    for entry in dist.iterdir():
        if entry.name in ("e2-editor-app.js", "ods-editor-app.js", "profiles"):
            continue
        (root / entry.name).symlink_to(entry)
    (root / "profiles").mkdir()
    for entry in (dist / "profiles").iterdir():
        (root / "profiles" / entry.name).symlink_to(entry)
    (root / "profiles/e2-editor-v33").symlink_to(DEV["writer"], target_is_directory=True)
    (root / "profiles/ods-editor-v5").symlink_to(DEV["calc"], target_is_directory=True)
    wasm = hashlib.sha256((DEV["writer"] / "probe.wasm").read_bytes()).hexdigest()
    writer = (dist / "e2-editor-app.js").read_text()
    edits = [('workerUrl: "./profiles/e2-editor-v32/sdk-worker.js"', 'workerUrl: "./profiles/e2-editor-v33/sdk-worker.js"'),
             ('const PINNED_WASM_SHA256 = "54e500931de0ee28";', f'const PINNED_WASM_SHA256 = "{wasm[:16]}";')]
    for old, new in edits:
        if writer.count(old) != 1:
            raise SystemExit(f"the Writer page moved: {old!r} occurs {writer.count(old)} times")
        writer = writer.replace(old, new)
    (root / "e2-editor-app.js").write_text(writer)
    calc = (dist / "ods-editor-app.js").read_text()
    old = 'workerUrl:"./profiles/ods-editor-v4/sdk-worker.js"'
    if calc.count(old) != 1:
        raise SystemExit("the Calc page moved")
    (root / "ods-editor-app.js").write_text(calc.replace(old, 'workerUrl:"./profiles/ods-editor-v5/sdk-worker.js"'))
    return root, {"writerWasmSha256": wasm, "writerManifestWasm": json.loads((DEV["writer"] / "sdk-manifest.json").read_text())["editorContract"]["wasmSha256"]}


def ooxml(data):
    try:
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    except zipfile.BadZipFile:
        return False
    return "[Content_Types].xml" in names and "mimetype" not in names


def fetch_b64(session, expression_length, expression_slice):
    length = evaluate(session, expression_length)
    return base64.b64decode("".join(evaluate(session, expression_slice % (i, i + 500000)) for i in range(0, length, 500000)))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--native-m0", type=Path, required=True)
    parser.add_argument("--harness", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--only")
    parser.add_argument("--keep", action="store_true", help="keep the saved documents (for a diagnosis; never for evidence)")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    native = json.loads((args.native_m0 / "report.json").read_text())
    native_dirs = {f["name"]: args.native_m0 / f"{i:02d}-{f['name']}" for i, f in enumerate(native["files"])}
    items = [i for i in m0.corpus() if i["suffix"] in PAGES and i["name"] in native_dirs and (not args.only or i["name"] == args.only)]
    if not items:
        raise SystemExit("empty corpus")
    root, identity = mirror(PROJECT / "build/ms-formats-smoke" / out.name, args.baseline)
    report = {"schema": 1, "baseline": args.baseline, "root": str(root), **identity, "files": [], "refused": []}
    port = free_port()
    log = (out / "server.txt").open("w")
    server = subprocess.Popen([sys.executable, str(PROJECT / "web/serve.py"), "--port", str(port), "--root", str(root)],
                              stdout=log, stderr=subprocess.STDOUT)

    def session_for(name, data):
        session = open_browser("chrome", (1440, 1000))
        session.call("Page.addScriptToEvaluateOnNewDocument",
                     {"source": m1.HOST % (json.dumps(base64.b64encode(data).decode()), json.dumps(name))})
        return session

    try:
        wait_page(f"http://127.0.0.1:{port}/e2-editor.html")
        with browser_lock("ms-formats-smoke", wait_s=0):
            for index, item in enumerate(items):
                kind = KIND[item["suffix"]]
                base = out / f"{index:02d}-{item['name']}"
                base.mkdir()
                entry = {"name": item["name"], "sha256": item["sha256"], "page": PAGES[item["suffix"]]}
                report["files"].append(entry)
                session = None
                try:
                    session = session_for(item["name"], item["path"].read_bytes())
                    started = time.monotonic()
                    navigate(session, f"http://127.0.0.1:{port}/{PAGES[item['suffix']]}")
                    ready = m1.wait_for(session, m1.READY[kind], 240)
                    entry["readySeconds"] = round(time.monotonic() - started, 2) if ready else None
                    entry["ready"] = ready
                    (base / "opened.png").write_bytes(session.screenshot())
                    entry["opened"] = bool(ready) and (ready.get("state") == "ready" if kind == "odt"
                                                       else bool((ready.get("state") or {}).get("cell")))
                    if entry["opened"]:
                        evaluate(session, m1.SAVE[kind])
                        saved = m1.wait_for(session, "globalThis.__msHost.saves.length>0&&globalThis.__msHost.saves[0].b64.length", 180)
                        if saved:
                            data = fetch_b64(session, "globalThis.__msHost.saves[0].b64.length",
                                             "globalThis.__msHost.saves[0].b64.slice(%d,%d)")
                            target = base / f"saved.{kind}"
                            target.write_bytes(data)
                            dumped = m1.native_dump(args.harness.resolve(), target, base / "odf-dump")
                            entry["odf"] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "dumpExit": dumped.get("exit"),
                                            "vsNative": m0.compare(m0.dump(base / "odf-dump/out/source.dump.txt"),
                                                                   m0.dump(native_dirs[item["name"]] / f"true-name/out/saved.{kind}.dump.txt"))}
                            if not args.keep:
                                target.unlink()
                        if kind == "ods":
                            evaluate(session, "(async()=>{const b=await __calcEditor.session.document.save({format:'xlsx'});"
                                              "const u=new Uint8Array(b);let s='';for(let i=0;i<u.length;i+=0x8000)"
                                              "s+=String.fromCharCode(...u.subarray(i,i+0x8000));globalThis.__msX=btoa(s);return true})()"
                                              ".catch(e=>{globalThis.__msXError=String(e&&e.code||'')+': '+String(e&&e.message||e);return false})")
                            error = evaluate(session, "globalThis.__msXError||null")
                            if error:
                                entry["xlsx"] = {"error": error}
                            else:
                                data = fetch_b64(session, "globalThis.__msX.length", "globalThis.__msX.slice(%d,%d)")
                                target = base / "saved.xlsx"
                                target.write_bytes(data)
                                dumped = m1.native_dump(args.harness.resolve(), target, base / "xlsx-dump")
                                entry["xlsx"] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "ooxml": ooxml(data),
                                                 "dumpExit": dumped.get("exit"),
                                                 "filter": ((dumped.get("report") or {}).get("source") or {}).get("filter"),
                                                 "vsNative": m0.compare(m0.dump(base / "xlsx-dump/out/source.dump.txt"),
                                                                        m0.dump(native_dirs[item["name"]] / "true-name/out/saved.xlsx.dump.txt"))}
                                if not args.keep:
                                    target.unlink()
                    entry["toast"] = evaluate(session, "document.querySelector('#toast')&&document.querySelector('#toast').textContent")
                except Exception as error:  # noqa: BLE001
                    entry["error"] = repr(error)
                finally:
                    if session:
                        close_browser(session)
                    for leftover in base.glob("*-dump"):
                        shutil.rmtree(leftover / "profile", ignore_errors=True)
                    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
                print(item["name"], "opened", entry.get("opened"), "odf", (entry.get("odf") or {}).get("vsNative", {}).get("equal"),
                      "xlsx", {k: v for k, v in (entry.get("xlsx") or {}).items() if k in ("ooxml", "error")},
                      (entry.get("xlsx") or {}).get("vsNative", {}).get("equal"), entry.get("error"), flush=True)
            sample = {"docx": PROJECT / "test-docs/r7-compat/l1-plain.docx", "xlsx": m0.LO / "sc/qa/unit/data/xlsx/formats.xlsx"}
            for name, suffix in REFUSED:
                kind = KIND[suffix]
                session = session_for(name, sample[suffix].read_bytes())
                try:
                    navigate(session, f"http://127.0.0.1:{port}/{PAGES[suffix]}")
                    ready = m1.wait_for(session, m1.READY[kind], 120)
                    opened = bool(ready) and (ready.get("state") == "ready" if kind == "odt" else bool((ready.get("state") or {}).get("cell")))
                    report["refused"].append({"name": name, "opened": opened, "ready": ready})
                    print("refused-name", name, "opened", opened, (ready or {}).get("toast"), flush=True)
                finally:
                    close_browser(session)
                    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
