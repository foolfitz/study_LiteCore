#!/usr/bin/env python3
"""SPEC-P-ms-formats 6.2: W1-W3 on the development profiles, Chrome or Firefox, through the pages' own file input and buttons.

The mirror (build/ms-formats-w/<out name>/) is dist/ with the two pages and their import graph taken from the SOURCE tree (web/'s
e2-editor.html, e2-editor-app.js, ods-editor.html, ods-editor-app.js; sdk/, editor-shell/, editor-shell-v2/, input/, reader-shell/,
spreadsheet-shell/, viewer-shell/), and profiles/ = dist/profiles plus e2-editor-v33 -> build/e2/editor-v33/profile and ods-editor-v5 ->
build/ods/editor-v5/profile.  The Writer page is pointed at v33 (worker URL and its wasm pin), the Calc page at v5.  With --baseline the
same page sources stay on e2-editor-v32 / ods-editor-v4: the red case (spec 6.2: the true names are refused at the C ABI there).

No host: the page opens what its file input is given (the TRUE name) and a save is a real browser download (Chrome
Page.setDownloadBehavior, Firefox's download prefs), read from disk -- the bytes, name and type the page hands the user.  One browser per
file.  Per corpus DOCX / XLSX (run_msformat_native.corpus(), M0's list):

  opened   the page says it opened the file (Writer: the toast 「已開啟 <name>」 and the pill ready; Calc: state ready, fileName = name);
  W1       the save button: one download named as the page names it (Writer <stem>-v2.<fmt>, Calc <name>), OOXML ([Content_Types].xml,
           no mimetype); dumped by M0's native harness, equal to M0's own-format round trip of the same file
           (true-name/out/saved.<fmt>.dump.txt) -- or, spec 10.4, different only in external-link targets (L-external-links);
  W2       Save As: the dialog offers ODF first and checked and the original second; confirmed, one download <stem>.odt / .ods whose first
           member is `mimetype` with the right value; dumped, equal to M0's ODF round trip (saved.odt / saved.ods).  The file whose
           ODS cannot be reopened (finding 184) is NOT_ESTABLISHED: its bytes are checked, never dumped.
  truncated  the one file M0 could not open: the page must say why with a code, and then open a good file.
  W3       names outside the table (.doc .docm .rtf to Writer, .xls .xlsm to Calc, a good file's bytes): not opened, the toast carries
           INVALID_ARGUMENT, and the same page then opens a good file under its true name.

  run_ms_formats_w.py --browser chrome|firefox --native-m0 DIR --harness FILE --out DIR [--baseline] [--only NAME]
Writes only under --out and build/ms-formats-w/.  Observations; the verdict is read by --read on the report (W_HOLDS / W_RED / ...).

Spec 11.3 (fable's ruling, 2026-11-03) replaces W3's reading and the recovery reading: a Calc open fails only when the page's own state
record (`__calcEditor.state`) is `error` FOR THIS FILE (fileName equal), and W3's code is read there (`error.code`); a later open of the good
file counts only when the page's state names that file and is ready.  Run 01 (findings/evidence/ms-formats/w/) was read the old way and is
kept as the witness.
  --part refused                     only the refused names (spec 11.3 R1's live red case)
  --red-recovery-refused             the good file for "then open a good file" carries a refused name too: W3 must read red (R1)
  --self-test REPORT                 R2: three mutations of a green report, each must turn W3 red; runs nothing
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
from check_calc_sheet_view import Hands, RECT, wait            # noqa: E402
from r7_support import evaluate, wait_page                     # noqa: E402
from run_browser_probe import ChromeSession, free_port         # noqa: E402
from run_e2_c_page_smoke import navigate                       # noqa: E402
from v21_shakedown_common import browser_lock, close_browser, open_browser  # noqa: E402
import run_msformat_native as m0                               # noqa: E402
import run_msformat_wasm as m1                                 # noqa: E402

DEV = {"writer": PROJECT / "build/e2/editor-v33/profile", "calc": PROJECT / "build/ods/editor-v5/profile"}
SOURCES = ["sdk", "editor-shell", "editor-shell-v2", "input", "reader-shell", "spreadsheet-shell", "viewer-shell"]
PAGE_FILES = ["e2-editor.html", "e2-editor-app.js", "ods-editor.html", "ods-editor-app.js"]
KIND = {"docx": "writer", "xlsx": "calc"}
ODF = {"docx": ("odt", "application/vnd.oasis.opendocument.text"),
       "xlsx": ("ods", "application/vnd.oasis.opendocument.spreadsheet")}
MIMES = ["application/vnd.oasis.opendocument.text", "application/vnd.oasis.opendocument.spreadsheet",
         "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"]
PAGE = {"writer": "e2-editor.html", "calc": "ods-editor.html?diagnostics=1"}
FILE_INPUT = {"writer": "#file", "calc": "#file-input"}
SAVE = {"writer": '[data-action="save"]', "calc": "#save-button"}
SAVE_AS = {"writer": "#save-as", "calc": "#save-as-button"}
REFUSED = [("Report.doc", "docx"), ("Report.docm", "docx"), ("Report.rtf", "docx"), ("Book.xls", "xlsx"), ("Book.xlsm", "xlsx")]
SAMPLE = {"docx": PROJECT / "test-docs/r7-compat/l1-plain.docx", "xlsx": m0.LO / "sc/qa/unit/data/xlsx/formats.xlsx"}
NOT_ESTABLISHED_W2 = {"forum-mso-en4-134670.xlsx": "finding 184: the ODS it becomes does not finish loading (L-ods-reload-cliff)"}

TOAST = ("(()=>{const t=document.querySelector('#toast');return t?{text:t.textContent,"
         "bad:t.classList.contains('bad')||t.classList.contains('error')}:null})()")
WRITER_OPEN = ("(()=>{const p=document.querySelector('#state-pill'),d=document.querySelector('#s-doc');"
               "return {state:p&&p.dataset.state,doc:d&&d.textContent}})()")
CALC_STATE = ("(()=>{const s=window.__calcEditor&&window.__calcEditor.state;"
              "return s?{state:s.state,fileName:s.fileName,busy:s.busy,error:s.error||null}:null})()")
REFUSED_KIND = {"doc": "writer", "docm": "writer", "rtf": "writer", "xls": "calc", "xlsm": "calc"}
DIALOG = ("(()=>{const d=document.querySelector('#save-as-dialog');const r=[...document.querySelectorAll("
          "'#save-as-formats input[name=\"save-as-format\"]')];return {open:!!(d&&d.open),"
          "name:(document.querySelector('#save-as-name')||{}).value,suffix:(document.querySelector('#save-as-suffix')||{}).textContent,"
          "choices:r.map(x=>({value:x.value,checked:x.checked,label:x.parentElement.textContent})),"
          "message:(document.querySelector('#save-as-message')||{}).textContent}})()")
BUTTON = ("(()=>{const b=document.querySelector(%s);return b?{hidden:b.hidden,disabled:b.disabled,"
          "width:b.getBoundingClientRect().width}:null})()")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mirror(root, baseline):
    """dist/ with the pages and their modules from the tree; the development profiles aliased."""
    dist = PROJECT / "dist"
    root.mkdir(parents=True, exist_ok=False)
    taken = set(PAGE_FILES) | set(SOURCES) | {"profiles"}
    for entry in dist.iterdir():
        if entry.name not in taken:
            (root / entry.name).symlink_to(entry)
    for directory in SOURCES:
        shutil.copytree(PROJECT / directory, root / directory, ignore=shutil.ignore_patterns("tests", "*.test.*"))
    (root / "profiles").mkdir()
    for entry in (dist / "profiles").iterdir():
        (root / "profiles" / entry.name).symlink_to(entry)
    identity = {"baseline": baseline, "served": {}}
    pin = None
    if not baseline:
        (root / "profiles/e2-editor-v33").symlink_to(DEV["writer"], target_is_directory=True)
        (root / "profiles/ods-editor-v5").symlink_to(DEV["calc"], target_is_directory=True)
        pin = sha(DEV["writer"] / "probe.wasm")
        identity["writerWasmSha256"] = pin
        identity["calcWasmSha256"] = sha(DEV["calc"] / "probe.wasm")
        identity["writerWorkerSha256"] = sha(DEV["writer"] / "sdk-worker.js")
        identity["calcWorkerSha256"] = sha(DEV["calc"] / "sdk-worker.js")
    for name in PAGE_FILES:
        text = (PROJECT / "web" / name).read_text(encoding="utf-8")
        if not baseline and name == "e2-editor-app.js":
            for old, new in [('workerUrl: "./profiles/e2-editor-v32/sdk-worker.js"', 'workerUrl: "./profiles/e2-editor-v33/sdk-worker.js"'),
                             ('const PINNED_WASM_SHA256 = "54e500931de0ee28";', f'const PINNED_WASM_SHA256 = "{pin[:16]}";')]:
                if text.count(old) != 1:
                    raise SystemExit(f"the Writer page moved: {old!r} occurs {text.count(old)} times")
                text = text.replace(old, new)
        if not baseline and name == "ods-editor-app.js":
            old = 'workerUrl:"./profiles/ods-editor-v4/sdk-worker.js"'
            if text.count(old) != 1:
                raise SystemExit("the Calc page moved")
            text = text.replace(old, 'workerUrl:"./profiles/ods-editor-v5/sdk-worker.js"')
        (root / name).write_text(text, encoding="utf-8")
    for path in sorted([*(root / n for n in PAGE_FILES), *(p for d in SOURCES for p in (root / d).rglob("*.js"))]):
        identity["served"][str(path.relative_to(root))] = sha(path)
    for name in PAGE_FILES:
        identity["served"][f"source:web/{name}"] = sha(PROJECT / "web" / name)
    return identity


def ooxml(data):
    try:
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    except zipfile.BadZipFile:
        return False
    return "[Content_Types].xml" in names and "mimetype" not in names


def odf(data, mime):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        first = archive.infolist()[0]
        return first.filename == "mimetype" and archive.read(first).decode("ascii", "replace") == mime
    except (zipfile.BadZipFile, IndexError):
        return False


EXTERNAL = re.compile(r"^(?P<cell>[A-Z]+[0-9]+)\t='file:///(?P<path>[^']*)'(?P<rest>#.*)$")


def external_links_only(first, second):
    """Spec 10.4: the two dumps differ ONLY in external-link targets (L-external-links): same line count, every differing line on
    both sides an external reference `'file:///...'#...`, paired 1:1 by cell, the same file name and the same #part."""
    if first is None or second is None or len(first) != len(second):
        return False
    pairs = [(a, b) for a, b in zip(first, second) if a != b]
    if not pairs:
        return False
    for a, b in pairs:
        ma, mb = EXTERNAL.match(a), EXTERNAL.match(b)
        if not ma or not mb or ma["cell"] != mb["cell"] or ma["rest"] != mb["rest"]:
            return False
        if ma["path"].rsplit("/", 1)[-1] != mb["path"].rsplit("/", 1)[-1]:
            return False
    return True


def wait_download(directory, name, timeout=120):
    target = directory / name
    deadline = time.monotonic() + timeout
    last = -1
    while time.monotonic() < deadline:
        partial = [p for p in directory.iterdir() if p.suffix in (".crdownload", ".part") or p.name.startswith(".")]
        if target.exists() and not partial:
            size = target.stat().st_size
            if size > 0 and size == last:
                return target
            last = size
        time.sleep(.3)
    return None


class Page:
    def __init__(self, browser, downloads, port):
        self.browser, self.downloads, self.port = browser, downloads, port
        prefs = None
        if browser == "firefox":
            prefs = {"browser.download.folderList": 2, "browser.download.dir": str(downloads),
                     "browser.download.useDownloadDir": True, "browser.download.manager.showWhenStarting": False,
                     "browser.helperApps.neverAsk.saveToDisk": ",".join(MIMES),
                     "browser.download.always_ask_before_handling_new_types": False,
                     "browser.download.start_downloads_in_tmp_dir": False, "browser.download.alwaysOpenPanel": False}
        self.session = open_browser(browser, (1440, 1000), firefox_prefs=prefs)
        if isinstance(self.session, ChromeSession):
            self.session.call("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(downloads)})
        self.hands = Hands(self.session)

    def go(self, kind):
        navigate(self.session, f"http://127.0.0.1:{self.port}/{PAGE[kind]}")
        if kind == "writer":  # the page opens its bundled sample first; wait for it, so a later toast is ours
            return wait(self.session, f"(()=>{{const s={WRITER_OPEN};return s.state==='ready'&&s}})()", 180)
        return wait(self.session, "document.readyState==='complete'&&!!document.querySelector('#file-input')", 60)

    def press(self, selector):
        self.hands.click(*evaluate(self.session, RECT % json.dumps(selector)))

    def open(self, kind, path, timeout=240):
        """Give the file input `path`; wait until the page says it opened it, or says why not."""
        name = path.name
        before = evaluate(self.session, TOAST) or {}
        evaluate(self.session, "(()=>{const t=document.querySelector('#toast');if(t){t.textContent='';"
                               "t.classList.remove('bad','error');}return true})()")
        self.session.set_file(FILE_INPUT[kind], path)
        if kind == "writer":
            expr = (f"(()=>{{const t={TOAST},s={WRITER_OPEN};if(t&&t.text==={json.dumps('已開啟 ' + name)}&&s.state==='ready')"
                    f"return {{opened:true,toast:t,state:s}};if(t&&t.bad)return {{opened:false,toast:t,state:s}};return null}})()")
        else:
            # Spec 11.3 G1: a failure is THIS file's session in `error`; a toast alone is not (a closing session re-shows its error).
            expr = (f"(()=>{{const t={TOAST},s={CALC_STATE};if(s&&s.state==='ready'&&s.fileName==={json.dumps(name)}&&!s.busy)"
                    f"return {{opened:true,toast:t,state:s}};if(s&&s.state==='error'&&s.fileName==={json.dumps(name)})"
                    f"return {{opened:false,toast:t,state:s}};return null}})()")
        result = wait(self.session, expr, timeout)
        if result and kind == "calc" and not result.get("opened"):
            time.sleep(.5)  # the notice is written by the same render; read it again after it settles
            result["toast"] = evaluate(self.session, TOAST)
        return result or {"opened": False, "timeout": True, "toast": evaluate(self.session, TOAST), "toastBefore": before,
                          "state": evaluate(self.session, WRITER_OPEN if kind == "writer" else CALC_STATE)}

    def close(self):
        return close_browser(self.session)


def native(harness, data, suffix, work):
    work.mkdir(parents=True)
    saved = work / f"saved.{suffix}"
    saved.write_bytes(data)
    dumped = m1.native_dump(harness, saved, work / "dump")
    lines = m0.dump(work / "dump/out/source.dump.txt")
    shutil.rmtree(work / "dump/profile", ignore_errors=True)
    saved.unlink()
    for text in (work / "dump/out").glob("*.txt"):  # lean evidence, as M0's: m0.dump() reads the .gz
        text.with_name(text.name + ".gz").write_bytes(gzip.compress(text.read_bytes(), mtime=0))
        text.unlink()
    return dumped, lines


def one_file(page, item, native_dir, harness, base, files_dir):
    kind, suffix = KIND[item["suffix"]], item["suffix"]
    odf_suffix, odf_mime = ODF[suffix]
    stem = item["name"].rsplit(".", 1)[0]
    entry = {"name": item["name"], "sha256": item["sha256"], "kind": kind}
    copy = files_dir / item["name"]
    shutil.copyfile(item["path"], copy)
    page.go(kind)
    entry["open"] = page.open(kind, copy)
    entry["opened"] = entry["open"].get("opened") is True
    m0_source = m0.dump(native_dir / "true-name/out/source.dump.txt")
    entry["m0Opened"] = m0_source is not None
    if not entry["opened"]:
        return entry
    # W1: the save button.
    downloads = page.downloads
    w1_name = f"{stem}-v2.{suffix}" if kind == "writer" else item["name"]
    page.press(SAVE[kind])
    got = wait_download(downloads, w1_name)
    w1 = entry["w1"] = {"download": w1_name, "arrived": bool(got), "downloads": sorted(p.name for p in downloads.iterdir())}
    if got:
        data = got.read_bytes()
        w1.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), ooxml=ooxml(data))
        dumped, lines = native(harness, data, suffix, base / "w1")
        reference = m0.dump(native_dir / f"true-name/out/saved.{suffix}.dump.txt")
        w1.update(dumpExit=dumped.get("exit"), filter=((dumped.get("report") or {}).get("source") or {}).get("filter"),
                  vsNative=m0.compare(lines, reference), externalLinksOnly=external_links_only(lines, reference))
        got.unlink()
    # W2: Save As, the page's dialog.
    button = evaluate(page.session, BUTTON % json.dumps(SAVE_AS[kind]))
    w2 = entry["w2"] = {"button": button}
    if button and not button["hidden"] and not button["disabled"]:
        page.press(SAVE_AS[kind])
        dialog = wait(page.session, f"(()=>{{const d={DIALOG};return d.open&&d}})()", 10)
        w2["dialog"] = dialog
        if dialog:
            page.press("#save-as-confirm")
            w2_name = f"{stem}.{odf_suffix}"
            got = wait_download(downloads, w2_name)
            w2.update(download=w2_name, arrived=bool(got), after=evaluate(page.session, DIALOG), toast=evaluate(page.session, TOAST))
            if got:
                data = got.read_bytes()
                w2.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), odf=odf(data, odf_mime))
                if item["name"] in NOT_ESTABLISHED_W2:
                    w2["notEstablished"] = NOT_ESTABLISHED_W2[item["name"]]
                else:
                    dumped, lines = native(harness, data, odf_suffix, base / "w2")
                    w2.update(dumpExit=dumped.get("exit"),
                              vsNative=m0.compare(lines, m0.dump(native_dir / f"true-name/out/saved.{odf_suffix}.dump.txt")))
                got.unlink()
    entry["toast"] = evaluate(page.session, TOAST)
    return entry


def recovered(kind, record, name):
    """Spec 11.3 G2: the page's own state names the good file and is ready."""
    rec = record.get("recovery") or {}
    state = rec.get("state") or {}
    if kind == "writer":
        ok = (rec.get("opened") is True and state.get("state") == "ready" and state.get("doc") == name
              and (rec.get("toast") or {}).get("text") == f"已開啟 {name}")
    else:
        ok = state.get("state") == "ready" and state.get("fileName") == name and not state.get("busy")
    return ok, (None if ok else f"recovery not {name} ready: {json.dumps({'opened': rec.get('opened'), 'state': state, 'timeout': rec.get('timeout')}, ensure_ascii=False)}")


def refused_holds(record):
    """Spec 11.3 G1 (Calc) and 10.4 (Writer) for one refused name, and G2 for the open after it; every failed condition named."""
    name = record["name"]
    kind = REFUSED_KIND[name.rsplit(".", 1)[1].lower()]
    opened = record.get("open") or {}
    toast, state = opened.get("toast") or {}, opened.get("state") or {}
    why = []
    if record.get("error"):
        why.append(f"error {record['error']}")
    if opened.get("opened") is not False:
        why.append("opened (or no answer)")
    if not toast.get("bad"):
        why.append("toast not in error style")
    if kind == "writer":
        if "INVALID_ARGUMENT" not in (toast.get("text") or ""):
            why.append("toast names no INVALID_ARGUMENT")
    else:
        if state.get("state") != "error" or state.get("fileName") != name:
            why.append(f"page state is not error for {name}: {state.get('state')} {state.get('fileName')}")
        code = (state.get("error") or {}).get("code") if isinstance(state.get("error"), dict) else None
        if code != "INVALID_ARGUMENT":
            why.append("error.code missing" if code is None else f"error.code {code}")
    sample = record.get("recoveryName") or SAMPLE["docx" if kind == "writer" else "xlsx"].name
    ok, reason = recovered(kind, record, sample)
    if not ok:
        why.append(reason)
    return not why, [f"{name}: {w}" for w in why]


def read(report):
    """The verdict, from the report alone."""
    if report.get("part") == "refused":
        results = [refused_holds(r) for r in report["refused"]]
        w3 = bool(results) and all(ok for ok, _ in results)
        return {"part": "refused", "W3": w3, "problems": [p for _, ps in results for p in ps],
                "redRecovery": report.get("redRecovery", False), "verdict": "W3_HOLDS" if w3 else "W3_RED"}
    files = report["files"]
    problems = []
    if not files:
        problems.append("no files")
    good = [f for f in files if f.get("m0Opened")]
    bad = [f for f in files if not f.get("m0Opened")]
    w1 = w2 = True
    for f in good:
        if not f.get("opened"):
            problems.append(f"{f['name']}: not opened ({(f.get('open') or {}).get('toast')})")
            w1 = w2 = False
            continue
        a = f.get("w1") or {}
        eq = (a.get("vsNative") or {}).get("equal") is True
        if not (a.get("arrived") and a.get("ooxml") and (eq or a.get("externalLinksOnly"))):
            w1 = False
            problems.append(f"{f['name']}: W1 {json.dumps({k: a.get(k) for k in ('arrived', 'ooxml', 'externalLinksOnly')})} "
                            f"{json.dumps(a.get('vsNative'), ensure_ascii=False)[:300]}")
        b = f.get("w2") or {}
        d = b.get("dialog") or {}
        choices = d.get("choices") or []
        offered = (len(choices) == 2 and choices[0]["value"] == ODF[f["name"].rsplit(".", 1)[1]][0] and choices[0]["checked"]
                   and choices[1]["value"] == f["name"].rsplit(".", 1)[1] and not choices[1]["checked"])
        ok = b.get("arrived") and b.get("odf") and offered and (b.get("notEstablished") or (b.get("vsNative") or {}).get("equal") is True)
        if not ok:
            w2 = False
            problems.append(f"{f['name']}: W2 offered={offered} {json.dumps({k: b.get(k) for k in ('arrived', 'odf')})} "
                            f"{json.dumps(b.get('vsNative'), ensure_ascii=False)[:300]} button={b.get('button')}")
    truncated = bool(bad)
    for f in bad:
        sample = f.get("recoveryName") or SAMPLE[f["name"].rsplit(".", 1)[1]].name
        ok, reason = recovered(f.get("kind") or KIND[f["name"].rsplit(".", 1)[1]], f, sample)
        if not (not f.get("opened") and (f.get("open") or {}).get("toast", {}).get("bad")
                and re.match(r"^[A-Z][A-Z0-9_]+：", ((f.get("open") or {}).get("toast") or {}).get("text") or "") and ok):
            truncated = False
            problems.append(f"{f['name']}: truncated clause {reason or (f.get('open') or {}).get('toast')}")
    results = [refused_holds(r) for r in report["refused"]]
    w3 = bool(results) and all(ok for ok, _ in results)
    for _, why in results:
        problems.extend(why)
    opened = sum(1 for f in good if f.get("opened"))
    verdict = {"files": len(files), "comparable": len(good), "opened": opened, "W1": w1 and bool(good), "W2": w2 and bool(good),
               "truncated": truncated, "W3": w3,
               "notEstablished": sorted(f["name"] for f in good if (f.get("w2") or {}).get("notEstablished")),
               "externalLinksOnly": sorted(f["name"] for f in good if (f.get("w1") or {}).get("externalLinksOnly")),
               "problems": problems}
    if report["identity"]["baseline"]:
        verdict["verdict"] = "W_RED" if opened == 0 and not verdict["W1"] and not verdict["W2"] else "W_RED_CASE_FAILED"
    else:
        verdict["verdict"] = "W_HOLDS" if all(verdict[k] for k in ("W1", "W2", "truncated", "W3")) else "W_DOES_NOT_HOLD"
    return verdict


def self_test(report):
    """Spec 11.3 R2: the green report, then three mutations of it in memory; each must turn W3 red."""
    import copy
    base = read(report)
    out = {"base": {k: base[k] for k in ("W3", "verdict")}, "mutations": {}}
    calc = lambda r: REFUSED_KIND[r["name"].rsplit(".", 1)[1].lower()] == "calc"

    def code(rep):
        for r in rep["refused"]:
            if calc(r) and isinstance((r["open"].get("state") or {}).get("error"), dict):
                r["open"]["state"]["error"]["code"] = "OPEN_FAILED"

    def opening(rep):
        for r in rep["refused"]:
            if calc(r):
                r["recovery"]["state"]["state"] = "opening"

    def no_code(rep):
        for r in rep["refused"]:
            if not calc(r):
                r["open"]["toast"]["text"] = (r["open"]["toast"]["text"] or "").replace("INVALID_ARGUMENT：", "")

    for name, mutate in (("calc-code-OPEN_FAILED", code), ("calc-recovery-opening", opening), ("writer-toast-without-code", no_code)):
        mutated = copy.deepcopy(report)
        mutate(mutated)
        verdict = read(mutated)
        out["mutations"][name] = {"W3": verdict["W3"], "verdict": verdict["verdict"], "problems": verdict["problems"][:6]}
    out["pass"] = base["verdict"] == "W_HOLDS" and all(m["W3"] is False and m["verdict"] != "W_HOLDS" for m in out["mutations"].values())
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["pass"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--browser", choices=["chrome", "firefox"])
    parser.add_argument("--native-m0", type=Path)
    parser.add_argument("--harness", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--only")
    parser.add_argument("--read", type=Path, help="read a report.json and print its verdict; runs nothing")
    parser.add_argument("--part", choices=["all", "refused"], default="all")
    parser.add_argument("--red-recovery-refused", action="store_true")
    parser.add_argument("--self-test", type=Path, help="R2 on a green report.json; runs nothing")
    args = parser.parse_args()
    if args.self_test:
        return self_test(json.loads(args.self_test.read_text()))
    if args.read:
        report = json.loads(args.read.read_text())
        verdict = read(report)
        print(json.dumps(verdict, ensure_ascii=False, indent=1))
        return 0 if verdict["verdict"] in ("W_HOLDS", "W_RED") else 1
    if not (args.browser and args.native_m0 and args.harness and args.out):
        parser.error("--browser, --native-m0, --harness and --out are required to run")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    native_m0 = json.loads((args.native_m0 / "report.json").read_text())
    native_dirs = {f["name"]: args.native_m0 / f"{i:02d}-{f['name']}" for i, f in enumerate(native_m0["files"])}
    items = [i for i in m0.corpus() if i["suffix"] in KIND and i["name"] in native_dirs and (not args.only or i["name"] == args.only)]
    if args.part == "refused":
        items = []
    elif not items:
        raise SystemExit("empty corpus")
    work = PROJECT / "build/ms-formats-w" / f"{out.parent.name}-{out.name}"
    root = work / "root"
    identity = mirror(root, args.baseline)
    files_dir, downloads_root = work / "files", work / "downloads"
    files_dir.mkdir()
    downloads_root.mkdir()
    report = {"schema": 1, "tool": "run_ms_formats_w.py", "toolSha256": sha(__file__), "browser": args.browser, "identity": identity,
              "harness": str(args.harness), "harnessSha256": sha(args.harness), "nativeM0": str(args.native_m0),
              "work": str(work), "files": [], "refused": [], "part": args.part, "redRecovery": args.red_recovery_refused}
    port = free_port()
    log = (out / "server.txt").open("w")
    server = subprocess.Popen([sys.executable, str(PROJECT / "web/serve.py"), "--port", str(port), "--root", str(root)],
                              stdout=log, stderr=subprocess.STDOUT)
    write = lambda: (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    try:
        wait_page(f"http://127.0.0.1:{port}/e2-editor.html")
        with browser_lock("run_ms_formats_w", wait_s=0):
            for index, item in enumerate(items):
                base = out / f"{index:02d}-{item['name']}"
                base.mkdir()
                downloads = downloads_root / f"{index:02d}"
                downloads.mkdir()
                page = None
                started = time.monotonic()
                try:
                    page = Page(args.browser, downloads, port)
                    entry = one_file(page, item, native_dirs[item["name"]], args.harness.resolve(), base, files_dir)
                    if not entry["m0Opened"]:
                        sample = files_dir / SAMPLE[item["suffix"]].name
                        shutil.copyfile(SAMPLE[item["suffix"]], sample)
                        entry["recoveryName"] = sample.name
                        entry["recovery"] = page.open(KIND[item["suffix"]], sample)
                    shots = work / "shots"  # outside the evidence: a picture per file is megabytes and is never read by the verdict
                    shots.mkdir(exist_ok=True)
                    (shots / f"{index:02d}-{item['name']}.png").write_bytes(page.session.screenshot())
                except Exception as error:  # noqa: BLE001
                    entry = {"name": item["name"], "error": repr(error)}
                finally:
                    if page:
                        entry["close"] = page.close()
                entry["seconds"] = round(time.monotonic() - started, 1)
                report["files"].append(entry)
                write()
                print(item["name"], "opened", entry.get("opened"),
                      "W1", (entry.get("w1") or {}).get("ooxml"), ((entry.get("w1") or {}).get("vsNative") or {}).get("equal"),
                      "W2", (entry.get("w2") or {}).get("odf"), ((entry.get("w2") or {}).get("vsNative") or {}).get("equal"),
                      entry.get("error") or "", flush=True)
            if not args.only:
                for index, (name, suffix) in enumerate(REFUSED):
                    downloads = downloads_root / f"refused-{index}"
                    downloads.mkdir()
                    page = Page(args.browser, downloads, port)
                    record = {"name": name}
                    try:
                        kind = KIND[suffix]
                        disguised = files_dir / name
                        shutil.copyfile(SAMPLE[suffix], disguised)
                        page.go(kind)
                        record["open"] = page.open(kind, disguised, timeout=120)
                        sample = files_dir / SAMPLE[suffix].name
                        if args.red_recovery_refused:  # R1: the "good" file under a refused name, so the open after must fail
                            sample = files_dir / (SAMPLE[suffix].stem + ".red." + name.rsplit(".", 1)[1])
                        shutil.copyfile(SAMPLE[suffix], sample)
                        record["recoveryName"] = sample.name
                        record["recovery"] = page.open(kind, sample, timeout=120 if args.red_recovery_refused else 240)
                    except Exception as error:  # noqa: BLE001
                        record["error"] = repr(error)
                    finally:
                        record["close"] = page.close()
                    report["refused"].append(record)
                    write()
                    print("refused", name, "opened", (record.get("open") or {}).get("opened"),
                          ((record.get("open") or {}).get("toast") or {}).get("text"), "then", (record.get("recovery") or {}).get("opened"),
                          flush=True)
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()
        write()
    if not args.only:
        verdict = read(report)
        (out / "verdict.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=1) + "\n")
        print(json.dumps({k: v for k, v in verdict.items() if k != "problems"}, ensure_ascii=False), flush=True)
        for problem in verdict["problems"]:
            print("  ", problem)
    return 0


if __name__ == "__main__":
    sys.exit(main())
