#!/usr/bin/env python3
"""Where do ten seconds go when a 40-line text is pasted (task 2026-10-14f)?

The owner hand-tested host 0.2.19: a new document from Files, Ctrl+V of a
40-line Markdown text (about 540 characters), and 「他過好久才跑完」 -- about
ten-plus seconds, in both browsers, with the 處理中 pill lit the whole time.

This drives the owner's own path and timestamps every phase on the page's own
clock (performance.now()), changing no product byte: an instrumentation script
is appended to the page AFTER the editor is ready (run_in_page, both browsers
the same way) and records

  keydown / paste / beforeinput      the key and what the browser made of it
  req / res                          every Worker request and its reply (insertText, editorGetStateV2, paint, ...)
  evt                                every Worker event (document-invalidated, editor-state, ...)
  dom                                #state-pill, #state-shown, #s-revision, #s-pending, #s-latency, #toast, #litecore-host-saved
  blit                               every putImageData (the page's only blit)
  resource / longtask                fetches (the host's GET/PUT) and main-thread stalls (Chrome)

The clipboard is real: Chrome gets clipboard permission through CDP and the text
is written with navigator.clipboard.writeText, then a trusted Ctrl+V is
dispatched; Firefox runs with dom.events.testing.asyncClipboard so the same
API writes its headless clipboard, and WebDriver key actions press Ctrl+V.  If
a browser produces no `paste`/`insertFromPaste`, the arm says so and is not
replaced by a synthetic insert.

Arms (the text is never written to any report; only its shape is):
  owner    the owner's text, build/paste-repro/owner-paste.txt (git-ignored)
  single   the same text with every newline replaced by a space (one paragraph)
  ascii    40 lines of ASCII, 14 characters each
  ascii80  80 lines of ASCII (linearity in the paragraph count)
  cjk1     one line of 40 CJK characters (CJK without paragraphs)

Modes:
  host     the ddev host 0.2.19: Files -> + New -> the litecore entry -> the editor (the owner's path);
           waits afterwards for the autosave and reads the saved file's paragraph count
  nohost   the same page and profile bytes the host serves (its engine package, decompressed
           into a mirror) or dist/, served locally by web/serve.py; the blank A4 template opened
           through the page's own file input; no host, so no autosave

  probe_paste_latency.py --mode host --browser chrome --arms owner,single,ascii
  probe_paste_latency.py --mode nohost --root host-engine|dist --browser firefox --arms owner
  probe_paste_latency.py --summarize REPORT.json...

Never run beside another M3 runner.  On the ddev instance the files live in a
folder of this probe's own and are deleted afterwards.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import time
import traceback
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_m3_locks import LockChrome, login  # noqa: E402
from check_m3_new_document import create_from_menu, first_line, preflight  # noqa: E402
from check_m3_production_ui import HOST, click, quiet, state  # noqa: E402
from check_m3_skeleton_open import DEFAULT_DDEV, Instance  # noqa: E402
from odt_paragraphs import paragraph_texts_from_xml  # noqa: E402
from probe_m3_gate0_coep import firefox_profile, sha256_file, utc_now  # noqa: E402
from probe_m3_lock_semantics import Client  # noqa: E402
from r7_support import evaluate, run_in_page, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
REPO = PROJECT.parent
HOST_APP = Path.home() / "Projects" / "Nextcloud_Apps" / "litecore"
OWNER_TEXT = PROJECT / "build" / "paste-repro" / "owner-paste.txt"
SCRATCH = PROJECT / "build" / "paste-repro"                 # snap Firefox cannot see /tmp
EVIDENCE = REPO / "findings" / "evidence" / "paste-latency"
FOLDER = "貼上 測試資料夾"                                    # this probe's own folder on the instance
ROUTE = "/e2-editor.html"
BLANK = HOST_APP / "blank" / "en-US_zh-TW_A4.odt"           # what "+ New" gives the owner (TW arm)

INSTRUMENT = r"""(() => {
  if (window.__pl) return;
  const T = () => Math.round(performance.now() * 10) / 10;
  const pl = window.__pl = { installedAt: T(), dateNow: Date.now(), timeOrigin: performance.timeOrigin,
                             events: [], blits: 0, lastBlit: null, worker: false, dropped: 0 };
  const push = (type, extra) => {
    if (pl.events.length >= 40000) { pl.dropped += 1; return; }
    pl.events.push(Object.assign({ t: T(), type }, extra));
  };
  document.addEventListener('keydown', (e) => push('keydown', { key: e.key, ctrl: e.ctrlKey, trusted: e.isTrusted,
    target: e.target && e.target.id }), true);
  document.addEventListener('keyup', (e) => push('keyup', { key: e.key }), true);
  document.addEventListener('paste', (e) => { let len = null;
    try { len = (e.clipboardData.getData('text/plain') || '').length; } catch (err) { len = 'err'; }
    push('paste', { len, trusted: e.isTrusted, target: e.target && e.target.id }); }, true);
  document.addEventListener('beforeinput', (e) => push('beforeinput', { inputType: e.inputType,
    len: typeof e.data === 'string' ? e.data.length : null, hasDataTransfer: !!e.dataTransfer, trusted: e.isTrusted }), true);
  document.addEventListener('input', (e) => push('input', { inputType: e.inputType }), true);
  // Worker traffic: the SDK posts through Worker.prototype.postMessage (document-sdk.js _post) and
  // listens on the instance; the instance is learnt from the first request after this hook.
  const ops = new Map(), seen = new WeakSet();
  const proto = Worker.prototype, post = proto.postMessage;
  proto.postMessage = function (m, ...rest) {
    if (!seen.has(this)) {
      seen.add(this); pl.worker = true;
      this.addEventListener('message', (e) => {
        const d = e.data; if (!d || typeof d !== 'object') return;
        if (d.kind === 'response') {
          const op = ops.get(d.requestId); ops.delete(d.requestId);
          const r = d.result || {};
          push('res', { id: d.requestId, op, ok: d.ok, rev: r.revision, method: r.method,
                        err: d.ok ? undefined : (d.error && d.error.code) });
        } else if (d.kind === 'event') {
          push('evt', { ev: d.event, rev: d.revision, ss: d.sourceSequence,
                        stateSs: d.state && d.state.sourceSequence, source: d.source && (d.source.callback || d.source.id) });
        } else push('msg', { kind: d.kind });
      });
    }
    if (m && m.kind === 'request') {
      ops.set(m.requestId, m.operation);
      push('req', { id: m.requestId, op: m.operation,
                    len: m.operation === 'insertText' ? String((m.payload && m.payload.text) || '').length : undefined });
    } else if (m && m.kind) push('out', { kind: m.kind, id: m.requestId });
    return post.call(this, m, ...rest);
  };
  const watch = (sel, what) => { const n = document.querySelector(sel); if (!n) { push('nowatch', { sel }); return; }
    let last = null;
    new MutationObserver(() => {
      const value = what === 'pill' ? n.dataset.state : what === 'shown' ? n.dataset.state + '/' + n.textContent : n.textContent;
      if (value === last) return; last = value; push('dom', { what, value }); })
      .observe(n, { attributes: true, childList: true, characterData: true, subtree: true }); };
  watch('#state-pill', 'pill'); watch('#state-shown', 'shown'); watch('#s-revision', 'revision');
  watch('#s-pending', 'pending'); watch('#s-latency', 'latency'); watch('#toast', 'toast');
  watch('#litecore-host-saved', 'hostSaved'); watch('#litecore-host-unsaved', 'hostUnsaved');
  const cp = CanvasRenderingContext2D.prototype, put = cp.putImageData;
  cp.putImageData = function (img, dx, dy, ...r) {
    pl.blits += 1; pl.lastBlit = T(); push('blit', { dy, h: img.height });
    return put.call(this, img, dx, dy, ...r); };
  try { new PerformanceObserver((l) => { for (const e of l.getEntries())
      push('resource', { name: e.name.replace(/^https?:\/\/[^/]+/, '').slice(0, 160), init: e.initiatorType,
                         start: Math.round(e.startTime * 10) / 10, end: Math.round(e.responseEnd * 10) / 10 }); })
    .observe({ type: 'resource', buffered: false }); } catch (e) { push('noobserver', { what: 'resource', error: String(e) }); }
  try { new PerformanceObserver((l) => { for (const e of l.getEntries())
      push('longtask', { start: Math.round(e.startTime * 10) / 10, dur: Math.round(e.duration * 10) / 10 }); })
    .observe({ type: 'longtask', buffered: false }); } catch (e) { push('noobserver', { what: 'longtask', error: String(e) }); }
  document.addEventListener('pl-read', () => { document.documentElement.dataset.pl = JSON.stringify(pl); });
  document.addEventListener('pl-mark', (e) => { push('mark', { label: e.detail }); });
})();"""

READ_LOG = "(() => { document.dispatchEvent(new CustomEvent('pl-read')); return document.documentElement.dataset.pl || null; })()"
MARK = "(() => { document.dispatchEvent(new CustomEvent('pl-mark', { detail: ARG })); return true; })()"
INSTALLED = "(() => !!document.documentElement.dataset.pl || (() => { document.dispatchEvent(new CustomEvent('pl-read')); return !!document.documentElement.dataset.pl; })())()"
FOCUS = "(() => ({ hasFocus: document.hasFocus(), active: document.activeElement && document.activeElement.id, visibility: document.visibilityState }))()"
CLIPBOARD_SET = """(() => { const text = ARG; document.documentElement.dataset.plclip = '';
  navigator.clipboard.writeText(text).then(() => navigator.clipboard.readText())
    .then((back) => { document.documentElement.dataset.plclip = JSON.stringify({ ok: true, len: back.length, same: back === text,
                        sameModuloCRLF: back.replace(/\\r\\n/g, '\\n') === text }); },
          (e) => { document.documentElement.dataset.plclip = JSON.stringify({ ok: false, error: String(e) }); });
  return true; })()"""
CLIPBOARD_READ = "(() => document.documentElement.dataset.plclip || null)()"
PARAGRAPH_SHAPE = """(() => { const a = document.querySelector('#a11y-para'); const d = document.querySelector('#a11y-doc');
  return { offers: d ? d.dataset.offers : null, caretTextLength: a && a.textContent ? a.textContent.length : 0 }; })()"""

CJK_RANGES = ((0x3000, 0x303F), (0x3040, 0x30FF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF),
              (0xFF00, 0xFFEF), (0x20000, 0x2FA1F))


def is_cjk(ch: str) -> bool:
    return any(a <= ord(ch) <= b for a, b in CJK_RANGES)


def shape(text: str) -> dict[str, Any]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return {"chars": len(text), "newlines": text.count("\n"), "lines": len(lines),
            "cjk": sum(1 for c in text if is_cjk(c)), "ascii": sum(1 for c in text if ord(c) < 128 and c != "\n"),
            "bytesUtf8": len(text.encode("utf-8")), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "lineLengths": {"min": min((len(l) for l in lines), default=0), "max": max((len(l) for l in lines), default=0)},
            "trailingNewline": text.endswith("\n")}


def arm_text(arm: str) -> str:
    if arm in ("owner", "single"):
        owner = OWNER_TEXT.read_text(encoding="utf-8")
        return owner if arm == "owner" else owner.replace("\n", " ").strip()
    if arm == "ascii":
        return "".join(f"para {i:02d} abcdef\n" for i in range(1, 41))
    if arm == "ascii80":
        return "".join(f"para {i:02d} abcdef\n" for i in range(1, 81))
    if arm == "cjk1":
        return "".join(chr(0x4E00 + (i * 7919) % 0x51A5) for i in range(40))
    raise SystemExit(f"unknown arm {arm}")


# ------------------------------------------------------------------ browsers

def new_session(kind: str, scratch: Path, cold: bool = True):
    if kind == "chrome":
        session = LockChrome("cold" if cold else "warm")
        session.call("Network.disable")
        session.call("Emulation.setDeviceMetricsOverride", {"width": 1850, "height": 980, "deviceScaleFactor": 1, "mobile": False})
        return session
    scratch.mkdir(parents=True, exist_ok=True)
    session = FirefoxSession("cold" if cold else "warm", profile_dir=firefox_profile(scratch / f"ff-{time.monotonic_ns()}"),
                             extra_prefs={"dom.events.testing.asyncClipboard": True})
    session.command("POST", "/window/rect", {"width": 1850, "height": 1080})
    return session


def set_clipboard(session, kind: str, origin: str, text: str) -> dict[str, Any]:
    record: dict[str, Any] = {}
    if kind == "chrome":
        try:
            session.call("Browser.grantPermissions", {"origin": origin, "permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]})
            record["granted"] = True
        except RuntimeError as error:
            record["granted"] = str(error)
        try:
            session.call("Page.bringToFront")
        except RuntimeError as error:
            record["bringToFront"] = str(error)
    record["focus"] = evaluate(session, FOCUS)
    run_in_page(session, CLIPBOARD_SET.replace("ARG", json.dumps(text)))
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        raw = evaluate(session, CLIPBOARD_READ)
        if raw:
            record["clipboard"] = json.loads(raw)
            return record
        time.sleep(0.1)
    record["clipboard"] = {"ok": False, "error": "no answer in 10 s"}
    return record


def press_ctrl_v(session, kind: str) -> None:
    if kind == "chrome":
        ctrl = {"key": "Control", "code": "ControlLeft", "windowsVirtualKeyCode": 17, "nativeVirtualKeyCode": 17, "modifiers": 2}
        v = {"key": "v", "code": "KeyV", "windowsVirtualKeyCode": 86, "nativeVirtualKeyCode": 86, "modifiers": 2}
        session.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", **ctrl})
        session.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", **v})
        session.call("Input.dispatchKeyEvent", {"type": "keyUp", **v})
        session.call("Input.dispatchKeyEvent", {"type": "keyUp", **ctrl})
        return
    actions = [{"type": "keyDown", "value": ""}, {"type": "keyDown", "value": "v"},
               {"type": "keyUp", "value": "v"}, {"type": "keyUp", "value": ""}]
    session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": actions}]})
    session.command("DELETE", "/actions")


def read_log(session) -> dict[str, Any]:
    raw = evaluate(session, READ_LOG)
    return json.loads(raw) if raw else {"error": "no log"}


def wait_settled(session, revision_before: str | None, limit: float = 150) -> dict[str, Any]:
    """Until the revision moved past `revision_before` and the session has been
    ready with an empty queue for half a second; or the limit."""
    deadline = time.monotonic() + limit
    moved_at = None
    seen: dict[str, Any] = {}
    while time.monotonic() < deadline:
        seen = state(session)
        if moved_at is None and seen.get("revision") not in (None, revision_before):
            moved_at = time.monotonic()
        if moved_at is not None and seen.get("state") == "ready" and str(seen.get("pending")) == "0":
            settled = quiet(session, max(1.0, deadline - time.monotonic()))
            return {**settled, "secondsToRevision": round(moved_at - (deadline - limit), 2)}
        time.sleep(0.1)
    return {**seen, "timedOut": True}


# Where the user clicks before pasting, as fractions of #paper (POINT_AT).
# `first-line` is the N4 runner's point (waited for, as the runners do);
# `page-middle` is the middle of the blank page, NOT waited for: a user clicks
# and pastes a second later, whatever the engine is still doing with the click.
CLICKS = {"first-line": None, "page-middle": ("0.5", "0.5"), "below-first-line": ("0.3", "0.25")}


def place(session, where: str, record: dict[str, Any]) -> None:
    at = CLICKS[where] or first_line("A4")
    record["clickWhere"] = where
    record["clickAt"] = at
    if CLICKS[where] is None:
        record["click"] = click(session, at)
        return
    record["stateBeforeClick"] = state(session)
    evaluate(session, MARK.replace("ARG", json.dumps("click")))
    evaluate(session, pp.POINT_AT.replace("ARG_X", at[0]).replace("ARG_Y", at[1]))
    record["click"] = {"dispatched": True, "waited": False}
    time.sleep(1.0)
    record["stateAfterClickSecond"] = state(session)


def paste_and_measure(session, kind: str, origin: str, text: str, record: dict[str, Any], where: str) -> None:
    if CLICKS[where] is None:
        record["settledBefore"] = quiet(session, 60)
    else:
        record["settledBefore"] = state(session)
    record["revisionBefore"] = record["settledBefore"].get("revision")
    record["clipboardSet"] = set_clipboard(session, kind, origin, text)
    time.sleep(0.3)
    evaluate(session, MARK.replace("ARG", json.dumps("before-ctrl-v")))
    started = time.monotonic()
    press_ctrl_v(session, kind)
    record["settled"] = wait_settled(session, record["revisionBefore"])
    record["secondsToSettled"] = round(time.monotonic() - started, 2)
    # Let the render passes that follow the settle finish.
    time.sleep(4.0)
    record["stateAfter"] = state(session)
    record["focusAfter"] = evaluate(session, FOCUS)
    record["a11y"] = evaluate(session, PARAGRAPH_SHAPE)
    evaluate(session, MARK.replace("ARG", json.dumps("read")))
    record["log"] = read_log(session)


# ------------------------------------------------------------------ host mode

def file_shape(client: Client, path: str) -> dict[str, Any]:
    request_path = client.dav_path(path)
    import urllib.request
    import urllib.error
    request = urllib.request.Request(client.base + request_path, method="GET",
                                     headers={"X-Requested-With": "XMLHttpRequest", "Authorization": client.auth})
    try:
        with urllib.request.urlopen(request, context=client.tls, timeout=60) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    facts: dict[str, Any] = {"getStatus": status, "bytes": len(raw) if status == 200 else 0,
                             "sha256": hashlib.sha256(raw).hexdigest() if status == 200 else None}
    if status == 200:
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                paragraphs = paragraph_texts_from_xml(zf.read("content.xml"))
            facts["paragraphs"] = len(paragraphs)
            facts["paragraphLengths"] = [len(p) for p in paragraphs]
            facts["paragraphCjk"] = sum(1 for p in paragraphs for c in p if is_cjk(c))
        except Exception as error:  # noqa: BLE001
            facts["readError"] = f"{type(error).__name__}: {error}"
    return facts


def wait_autosave(session, limit: float = 50) -> dict[str, Any]:
    before = len((evaluate(session, HOST) or {}).get("saves") or [])
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        host = evaluate(session, HOST) or {}
        saves = host.get("saves") or []
        if len(saves) > before and saves[-1].get("settled") is True:
            time.sleep(0.5)
            return {"waited": True, "host": evaluate(session, HOST)}
        time.sleep(0.5)
    return {"waited": False, "timedOut": True, "host": evaluate(session, HOST)}


def run_host_arm(arm: str, kind: str, instance: Instance, admin: Client, scratch: Path, session, where: str) -> dict[str, Any]:
    text = arm_text(arm)
    name = f"貼上 測試-{arm}-{kind}-{time.strftime('%H%M%SZ', time.gmtime())}.odt"
    record: dict[str, Any] = {"arm": arm, "browser": kind, "mode": "host", "name": name, "folder": FOLDER, "click": where,
                              "text": shape(text), "startedAt": utc_now()}
    path = f"{FOLDER}/{name}"
    try:
        create = record["create"] = {}
        create_from_menu(session, kind, instance.base, FOLDER, name, create)
        record["createdFile"] = file_shape(admin, path)
        record["hostAtOpen"] = evaluate(session, HOST)
        run_in_page(session, INSTRUMENT)
        record["instrumented"] = evaluate(session, INSTALLED)
        place(session, where, record)
        paste_and_measure(session, kind, instance.base, text, record, where)
        record["autosave"] = wait_autosave(session)
        record["logAfterAutosave"] = read_log(session)
        record["savedFile"] = file_shape(admin, path)
    except Exception:  # noqa: BLE001 -- a run that dies is recorded, not lost
        record["fatal"] = traceback.format_exc()
        try:
            record["logAtFatal"] = read_log(session)
        except Exception:  # noqa: BLE001
            pass
    record["completedAt"] = utc_now()
    return record


# ------------------------------------------------------------------ no-host mode

def decompress_host_engine(target: Path) -> dict[str, Any]:
    """The host's engine package (gz/zst only on disk) decompressed into a mirror
    tree with the paths the page references."""
    source = HOST_APP / "engine" / "files"
    if target.exists():
        shutil.rmtree(target)
    files: dict[str, str] = {}
    for compressed in sorted(source.rglob("*.zst")):
        relative = compressed.relative_to(source).with_suffix("")
        out = target / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["zstd", "-d", "-q", "-f", str(compressed), "-o", str(out)], check=True)
        files[str(relative)] = sha256_file(out)
    manifest = json.loads((HOST_APP / "engine" / "MANIFEST.json").read_text())
    mismatched = {n: (files.get(n), f.get("sha256")) for n, f in manifest.get("files", {}).items()
                  if files.get(n) != f.get("sha256")}
    return {"files": len(files), "buildId": manifest.get("buildId"), "mismatched": mismatched,
            "page": files.get("e2-editor-app.js"), "profile": pp.product_profile(target)}


def run_nohost_arm(arm: str, kind: str, root_name: str, root: Path, scratch: Path, where: str) -> dict[str, Any]:
    text = arm_text(arm)
    record: dict[str, Any] = {"arm": arm, "browser": kind, "mode": "nohost", "root": root_name, "text": shape(text), "clickWhere": where,
                              "page": sha256_file(root / "e2-editor-app.js"), "profile": pp.product_profile(root),
                              "shellSession": sha256_file(root / "editor-shell-v2" / "narrow-editor-v2-session.js"),
                              "blank": {"path": str(BLANK), "sha256": sha256_file(BLANK)}, "startedAt": utc_now()}
    shutil.copyfile(BLANK, root / "blank.odt")
    port = free_port()
    server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port), "--root", str(root)],
                              cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session = new_session(kind, scratch)
        record["version"] = session.version
        navigate(session, base)
        pp.wait_for(session, lambda s: s.get("state") == "ready", 300)
        pp.evaluate(session, pp.OPEN_FILE.replace("ARG_URL", "./blank.odt").replace("ARG_NAME", "新文件.odt"))
        pp.wait_for(session, lambda s: (s.get("doc") or "") == "新文件.odt" and s.get("state") == "ready", 180)
        record["opened"] = quiet(session, 60)
        run_in_page(session, INSTRUMENT)
        record["instrumented"] = evaluate(session, INSTALLED)
        place(session, where, record)
        paste_and_measure(session, kind, f"http://127.0.0.1:{port}", text, record, where)
    except Exception:  # noqa: BLE001
        record["fatal"] = traceback.format_exc()
        if session is not None:
            try:
                record["logAtFatal"] = read_log(session)
            except Exception:  # noqa: BLE001
                pass
    finally:
        if session is not None:
            session.close()
        server.terminate()
        server.wait(timeout=10)
        (root / "blank.odt").unlink(missing_ok=True)
    record["completedAt"] = utc_now()
    return record


# ------------------------------------------------------------------ phases

def phases(record: dict[str, Any]) -> dict[str, Any]:
    """The phase table of one arm, from the page's own timestamps.  Every value
    is milliseconds after the Ctrl+V keydown ('v' with ctrl), or null."""
    log = record.get("logAfterAutosave") or record.get("log") or record.get("logAtFatal") or {}
    events = log.get("events") or []
    if not events:
        return {"error": "no events"}
    marks = [e for e in events if e["type"] == "mark" and e.get("label") == "before-ctrl-v"]
    t_mark = marks[-1]["t"] if marks else None
    after = lambda t0: [e for e in events if t0 is not None and e["t"] >= t0]  # noqa: E731
    keys = [e for e in after(t_mark) if e["type"] == "keydown" and e.get("key") in ("v", "V") and e.get("ctrl")]
    if not keys:
        keys = [e for e in after(t_mark) if e["type"] == "keydown" and e.get("key") == "Control"]
    t_key = keys[0]["t"] if keys else None
    if t_key is None:
        return {"error": "no Ctrl+V keydown recorded", "eventsAfterMark": len(after(t_mark)),
                "keydowns": [e for e in events if e["type"] == "keydown"][-5:]}
    rel = lambda t: None if t is None else round(t - t_key, 1)  # noqa: E731
    first = lambda pred, t0=t_key: next((e for e in after(t0) if pred(e)), None)  # noqa: E731
    click_marks = [e for e in events if e["type"] == "mark" and e.get("label") == "click"]
    t_click = click_marks[-1]["t"] if click_marks else None
    latency_after = [e for e in after(t_click if t_click is not None else t_key) if e["type"] == "dom" and e.get("what") == "latency"]
    toasts_after = [e for e in after(t_click if t_click is not None else t_key) if e["type"] == "dom" and e.get("what") == "toast"]
    pill_after_click = first(lambda e: e["type"] == "dom" and e.get("what") == "pill" and e.get("value") == "busy", t_click) if t_click is not None else None
    paste = first(lambda e: e["type"] == "paste")
    before_input = first(lambda e: e["type"] == "beforeinput" and e.get("inputType") == "insertFromPaste")
    req_insert = first(lambda e: e["type"] == "req" and e.get("op") == "insertText")
    get_states_between = [e for e in after(t_click) if e["type"] == "req" and e.get("op") == "editorGetStateV2"
                          and (req_insert is None or e["t"] < req_insert["t"])] if t_click is not None else []
    clicks_between = [e for e in after(t_click) if e["type"] == "req" and e.get("op") == "click"
                      and (req_insert is None or e["t"] < req_insert["t"])] if t_click is not None else []
    res_insert = first(lambda e: e["type"] == "res" and e.get("id") == req_insert["id"]) if req_insert else None
    # The drain's own getState is the first one REQUESTED after the insert (by
    # id): the request is posted from the microtask that follows the SDK's
    # message listener, before this probe's listener logs the insert's reply.
    req_state = first(lambda e: e["type"] == "req" and e.get("op") == "editorGetStateV2" and e.get("id", 0) > req_insert["id"],
                      req_insert["t"]) if req_insert else None
    res_state = first(lambda e: e["type"] == "res" and e.get("id") == req_state["id"]) if req_state else None
    pill_busy = first(lambda e: e["type"] == "dom" and e.get("what") == "pill" and e.get("value") == "busy")
    # The first `ready` AFTER THE KEY: with a click still in flight the pill was
    # busy before the key, and the first busy after the key may be the autosave's.
    pill_ready = first(lambda e: e["type"] == "dom" and e.get("what") == "pill" and e.get("value") == "ready")
    shown_busy = first(lambda e: e["type"] == "dom" and e.get("what") == "shown" and str(e.get("value", "")).startswith("busy"),
                       t_click if t_click is not None else t_key)
    shown_ready = first(lambda e: e["type"] == "dom" and e.get("what") == "shown" and str(e.get("value", "")).startswith("ready"))
    revision = first(lambda e: e["type"] == "dom" and e.get("what") == "revision")
    first_state_evt = first(lambda e: e["type"] == "evt" and e.get("ev") == "editor-state", req_insert["t"]) if req_insert else None
    invalidations = [e for e in after(req_insert["t"]) if e["type"] == "evt" and e.get("ev") == "document-invalidated"] if req_insert else []
    inval_before_res = [e for e in invalidations if res_insert and e["t"] <= res_insert["t"]]
    first_paint_req = first(lambda e: e["type"] == "req" and e.get("op") == "paint", res_insert["t"]) if res_insert else None
    paint_reqs = [e for e in after(res_insert["t"]) if e["type"] == "req" and e.get("op") == "paint"] if res_insert else []
    blits = [e for e in after(t_key) if e["type"] == "blit"]
    readmark = [e for e in events if e["type"] == "mark" and e.get("label") == "read"]
    t_read = readmark[0]["t"] if readmark else None
    blits_before_read = [e for e in blits if t_read is None or e["t"] <= t_read]
    longtasks = [e for e in after(t_key) if e["type"] == "longtask" and (t_read is None or e["t"] <= t_read)]
    resources = [e for e in after(t_key) if e["type"] == "resource"]
    other_reqs = {}
    for e in after(t_key):
        if e["type"] == "req" and (t_read is None or e["t"] <= t_read):
            other_reqs[e["op"]] = other_reqs.get(e["op"], 0) + 1
    out = {
        "keyAt": t_key,
        "clickBeforeKeyMs": None if t_click is None else round(t_key - t_click, 1),
        "pillBusyAfterClick": None if pill_after_click is None else round(pill_after_click["t"] - t_click, 1),
        "clickRequestsBeforeInsert": len(clicks_between),
        "getStateRequestsBeforeInsert": len(get_states_between),
        "latencyTextAfter": [{"at": rel(e["t"]), "value": e.get("value")} for e in latency_after][:10],
        "toastsAfter": [{"at": rel(e["t"]), "value": e.get("value")} for e in toasts_after][:10],
        "pasteEvent": rel(paste["t"]) if paste else None,
        "pasteLen": paste.get("len") if paste else None,
        "beforeinputInsertFromPaste": rel(before_input["t"]) if before_input else None,
        "beforeinputLen": before_input.get("len") if before_input else None,
        "insertTextRequest": rel(req_insert["t"]) if req_insert else None,
        "insertTextLen": req_insert.get("len") if req_insert else None,
        "insertTextResponse": rel(res_insert["t"]) if res_insert else None,
        "insertTextOk": res_insert.get("ok") if res_insert else None,
        "insertTextMethod": res_insert.get("method") if res_insert else None,
        "insertTextError": res_insert.get("err") if res_insert else None,
        "engineInsertMs": None if not (req_insert and res_insert) else round(res_insert["t"] - req_insert["t"], 1),
        "getStateRequest": rel(req_state["t"]) if req_state else None,
        "getStateResponse": rel(res_state["t"]) if res_state else None,
        "getStateMs": None if not (req_state and res_state) else round(res_state["t"] - req_state["t"], 1),
        "pillBusy": rel(pill_busy["t"]) if pill_busy else None,
        "pillReady": rel(pill_ready["t"]) if pill_ready else None,
        "shownBusy": rel(shown_busy["t"]) if shown_busy else None,
        "shownReady": rel(shown_ready["t"]) if shown_ready else None,
        "revisionShown": rel(revision["t"]) if revision else None,
        "revisionValue": revision.get("value") if revision else None,
        "firstEditorStateEvent": rel(first_state_evt["t"]) if first_state_evt else None,
        "invalidations": len(invalidations),
        "invalidationsBeforeInsertResponse": len(inval_before_res),
        "firstInvalidation": rel(invalidations[0]["t"]) if invalidations else None,
        "lastInvalidation": rel(invalidations[-1]["t"]) if invalidations else None,
        "firstPaintRequestAfterInsert": rel(first_paint_req["t"]) if first_paint_req else None,
        "paintRequestsAfterInsert": len(paint_reqs),
        "firstBlitAfterInsert": rel(next((e["t"] for e in blits if res_insert and e["t"] >= res_insert["t"]), None)) if res_insert else None,
        "lastBlit": rel(blits_before_read[-1]["t"]) if blits_before_read else None,
        "blits": len(blits_before_read),
        "longTasks": [{"start": rel(e["start"]), "dur": e["dur"]} for e in longtasks][:40],
        "longTaskTotalMs": round(sum(e["dur"] for e in longtasks), 1),
        "requestsByOperation": other_reqs,
        "resources": [{"name": e["name"], "init": e["init"], "start": rel(e["start"]), "end": rel(e["end"])} for e in resources][:40],
        "secondsToSettled": record.get("secondsToSettled"),
        "settledTimedOut": (record.get("settled") or {}).get("timedOut", False),
    }
    host = ((record.get("autosave") or {}).get("host") or {})
    if host.get("saves"):
        # The host's clock: Date.now() - out.started; the page log has dateNow at installedAt.
        epoch = (log.get("dateNow") or 0) - (log.get("installedAt") or 0)     # Date.now() at performance.now() == 0
        to_page = lambda at: None if at is None else round(host["started"] + at - epoch - t_key, 1)  # noqa: E731
        out["saves"] = [{"trigger": s.get("trigger"), "at": to_page(s.get("at")), "settled": s.get("settled"),
                         "outcome": s.get("outcome"), "status": s.get("status"), "bytes": s.get("bytes"),
                         "attempts": [{"waited": a.get("waited"), "checkAt": to_page((a.get("check") or {}).get("at")),
                                       "checkMs": (a.get("check") or {}).get("ms"), "putAt": to_page(a.get("at")),
                                       "respondedAt": to_page(a.get("respondedAt")), "status": a.get("status")}
                                      for a in s.get("attempts") or []]}
                        for s in host["saves"]]
    return out


def summarize(reports: list[Path]) -> None:
    for path in reports:
        report = json.loads(path.read_text())
        for run in report.get("runs") or []:
            p = phases(run)
            if "error" in p:
                print(f"{path.name} {run.get('mode')}/{run.get('browser')}/{run.get('arm')}: {p}")
                continue
            print(f"{path.name} {run.get('mode')}/{run.get('browser')}/{run.get('arm')} "
                  f"lines={run['text']['lines']} chars={run['text']['chars']}: "
                  f"click={run.get('clickWhere')} clickBeforeKey={p['clickBeforeKeyMs']} getStatesBeforeInsert={p['getStateRequestsBeforeInsert']} "
                  f"paste={p['pasteEvent']} beforeinput={p['beforeinputInsertFromPaste']} req={p['insertTextRequest']} "
                  f"res={p['insertTextResponse']} (engine {p['engineInsertMs']} ms) getState={p['getStateResponse']} "
                  f"(+{p['getStateMs']}) pillReady={p['pillReady']} shownBusy={p['shownBusy']} firstBlit={p['firstBlitAfterInsert']} "
                  f"lastBlit={p['lastBlit']} inval={p['invalidations']} ({p['invalidationsBeforeInsertResponse']} before res) "
                  f"saves={[(s['trigger'], s['at']) for s in p.get('saves', [])]} latency={p['latencyTextAfter'][-1:]} toasts={p['toastsAfter'][-2:]}")


# ------------------------------------------------------------------ main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=("host", "nohost"))
    parser.add_argument("--root", choices=("host-engine", "dist", "dir"), default="host-engine")
    parser.add_argument("--root-dir", type=Path, help="with --root dir: a prepared page tree (e.g. a dist mirror with a repointed page)")
    parser.add_argument("--browser", choices=("chrome", "firefox"))
    parser.add_argument("--arms", default="owner,single,ascii")
    parser.add_argument("--click", choices=sorted(CLICKS), default="first-line")
    parser.add_argument("--ddev-root", type=Path, default=DEFAULT_DDEV)
    parser.add_argument("--label", default="run")
    parser.add_argument("--summarize", nargs="*", type=Path)
    args = parser.parse_args()
    if args.summarize is not None:
        summarize(args.summarize)
        return 0
    if not args.mode or not args.browser:
        parser.error("--mode and --browser are required for a run")
    arms = [a for a in args.arms.split(",") if a]
    for arm in arms:
        arm_text(arm)   # fail early on a missing owner text
    SCRATCH.mkdir(parents=True, exist_ok=True)
    flight = preflight()
    flight["otherRunners"] = [line for line in flight["otherRunners"] if "probe_paste_latency" not in line]
    report: dict[str, Any] = {
        "probe": "probe_paste_latency.py", "runner": {"sha256": sha256_file(Path(__file__))}, "label": args.label,
        "mode": args.mode, "browser": args.browser, "arms": arms, "click": args.click, "startedAt": utc_now(), "preflight": flight,
        "ownerText": shape(OWNER_TEXT.read_text(encoding="utf-8")) if OWNER_TEXT.is_file() else None,
        "runs": [],
    }
    if flight["otherRunners"]:
        print(f"other runners are running: {flight['otherRunners']}", file=sys.stderr)
        return 2
    out_dir = EVIDENCE / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        if args.mode == "host":
            instance = Instance(args.ddev_root)
            log: list[dict[str, Any]] = []
            admin = Client(instance.base, "admin", instance.password, log)
            git = lambda *a: subprocess.run(["git", *a], cwd=args.ddev_root, capture_output=True, text=True).stdout.strip()  # noqa: E731
            manifest = json.loads((args.ddev_root / "engine" / "MANIFEST.json").read_text())
            report["host"] = {"commit": git("rev-parse", "--short", "HEAD"), "dirty": git("status", "--porcelain").splitlines(),
                              "buildId": manifest.get("buildId"),
                              "servedPage": ((manifest.get("files") or {}).get("e2-editor-app.js") or {}).get("sha256"),
                              "profile": sorted({n.split("/")[1] for n in manifest.get("files", {}) if n.startswith("profiles/e2-editor")}),
                              "base": instance.base}
            report["mkcol"] = admin.call("mkcol", "MKCOL", admin.dav_path(FOLDER))["status"]
            session = None
            try:
                session = new_session(args.browser, SCRATCH / f"host-{args.browser}")
                report["version"] = session.version
                report["login"] = login(session, instance.base, "admin", instance.password)
                for arm in arms:
                    report["runs"].append(run_host_arm(arm, args.browser, instance, admin, SCRATCH, session, args.click))
            finally:
                if session is not None:
                    session.close()
            # Tidy: the files this probe made (a file still under its session's lock answers 423; retried briefly).
            cleanup: dict[str, Any] = {}
            for run in report["runs"]:
                status = None
                for _ in range(20):
                    status = admin.call("cleanup", "DELETE", admin.dav_path(f"{FOLDER}/{run['name']}"))["status"]
                    if status != 423:
                        break
                    time.sleep(3)
                cleanup[run["name"]] = status
            remaining = admin.call("cleanup-list", "PROPFIND", admin.dav_path(FOLDER), None, {"Depth": "1"})
            if remaining["status"] == 207 and remaining["body"] and remaining["body"].count("<d:href>") <= 1:
                cleanup[FOLDER] = admin.call("cleanup-folder", "DELETE", admin.dav_path(FOLDER))["status"]
            report["cleanup"] = cleanup
            report["log"] = [e for e in log if e["step"] not in ("cleanup-list",)]
        else:
            if args.root == "host-engine":
                root = SCRATCH / "mirror-host-engine"
                report["mirror"] = decompress_host_engine(root)
            elif args.root == "dist":
                root = PROJECT / "dist"
                report["mirror"] = {"root": "dist", "page": sha256_file(root / "e2-editor-app.js"), "profile": pp.product_profile(root)}
            else:
                root = args.root_dir.resolve()
                report["mirror"] = {"root": str(root), "page": sha256_file(root / "e2-editor-app.js"), "profile": pp.product_profile(root),
                                    "shell": {n: sha256_file(root / "editor-shell-v2" / n) for n in ("narrow-editor-v2-session.js", "narrow-editor-v2-client.js", "paragraph-editor-client.js")}}
            for arm in arms:
                report["runs"].append(run_nohost_arm(arm, args.browser, args.root, root, SCRATCH / f"nohost-{args.browser}", args.click))
    finally:
        report["completedAt"] = utc_now()
        for run in report["runs"]:
            run["phases"] = phases(run)
        stamp = report["startedAt"].replace(":", "").replace("+0000", "Z")
        root_name = args.root if args.mode == "nohost" else "ddev"
        if args.mode == "nohost" and args.root == "dir":
            root_name = "dir-" + args.root_dir.name
        out = out_dir / f"{args.mode}-{root_name}-{args.browser}-{args.click}-{args.label}-{stamp}.json"
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
        print(json.dumps({"report": str(out)}, ensure_ascii=False))
    summarize([out])
    return 0


if __name__ == "__main__":
    sys.exit(main())
