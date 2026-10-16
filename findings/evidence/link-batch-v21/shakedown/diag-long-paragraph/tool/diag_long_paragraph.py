#!/usr/bin/env python3
"""Long-paragraph crash diagnosis, browser cells (v21 shakedown, item 2 follow-up).  Recorded, not judged.

Every CELL is one fresh browser process: S-9 lock taken (waited for), pre-run checks, a new browser, one
page load, the empty template opened, ONE attempt, the after-state read, the browser closed, the lock
released.  The instruments are the shakedown's own, imported, not copied:

  v21_shakedown_common   S-1 mirror + identity, S-9 lock + pre-run checks, served(), close_browser()
  run_v21_shakedown_item2  Ctx (load/open/handle/ask), RecordingChrome, navigate, open_browser (Firefox)
  v21_page_hook          S-3: the page's own DocumentHandle (route sdk-*)
  v21_item2_observer     the ask channel (route worker-md) and the rq/rs log
  v21_clipboard          real clipboard + trusted Ctrl+V (route ctrlv-*)
  v21_engine_read        the editorGetStateV2 ask (is the worker alive?) and the product's save

Cell spec:  ROUTE:CORPUS:BYTES[:PAGE]
  ROUTE   sdk-md       DocumentHandle.pasteMarkdown(text) through the hook (the SDK route)
          worker-md    a raw {operation: pasteMarkdown} message to the page's worker (no SDK limit)
          worker-text  a raw {operation: insertText} message to the page's worker (works on v0224 too,
                       which has no S-3 hook)
          sdk-text     DocumentHandle.insertText(text) through the hook (plain text, the SDK route)
          ctrlv-text   real clipboard + trusted Ctrl+V into #sink after a click in the document
          ctrlv-textxK the same K times in a row (K pastes of BYTES each), each answered first
          open         open an ODT given with --odt NAME=PATH (cell open:NAME:0[:PAGE]) instead of the
                       empty template; the open itself is the attempt
          opentype     open as above, then one raw insertText "x" at the caret the open leaves
  CORPUS  see corpora.py (cjk, ascii, cjksplit<k>, cjkspace<k>)
  PAGE    v21 (default: the round's page, shell and e2-editor-v21, as the item-2 runner serves it)
          v0224 (dist/'s page and shell with e2-editor-v20, as item 1's d8red serves it)
          v21big (v21 with ONE change in the mirror's probe.js: the DEFAULT_PTHREAD_STACK_SIZE value
                  handed to _emscripten_thread_init, 65536 -> 1048576; a non-shipped loader, the
                  counterfactual for the stack hypothesis; probe.wasm untouched)

Chrome cells also record, through CDP auto-attach (recursive, flatten), every Runtime.exceptionThrown and
console error of the page AND of every worker target (the document worker and its pthreads), with the
stack frames, and Target.detachedFromTarget.  Firefox cells record what the page and SDK say.

  diag_long_paragraph.py --browser chrome --out DIR --label NAME [--repeat N] CELL [CELL ...]

Writes DIR/report-NAME.json (flushed after every cell) and DIR/docs-NAME/ (documents saved after an
answered attempt).  Never writes under dist/, never runs make.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import os
import re
import signal
import sys
import tempfile
import time
import traceback
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
TOOLS = REPO / "wasm_sdk_probe" / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE))
import corpora  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import run_merge_wasm_shakedown as mws  # noqa: E402
import run_v20_shakedown as v20  # noqa: E402
import run_v21_shakedown_item2 as item2  # noqa: E402
import v21_clipboard as clip  # noqa: E402
import v21_engine_read as er  # noqa: E402
import v21_item2_observer as obs2  # noqa: E402
import v21_page_hook as hook  # noqa: E402
import v21_shakedown_common as common  # noqa: E402

EMPTY = item2.EMPTY                    # v21-i2-empty.odt, round 1's empty template
PASTE_TIMEOUT = 240.0
WORKER_TIMEOUT = 90.0       # the raw routes have no SDK timeout; 240 s in chrome-s1-worker, 90 s after it
STACK_CALL = "__emscripten_thread_init(tb,!ENVIRONMENT_IS_WORKER,1,!ENVIRONMENT_IS_WEB,65536,false)"
STACK_BIG = "__emscripten_thread_init(tb,!ENVIRONMENT_IS_WORKER,1,!ENVIRONMENT_IS_WEB,1048576,false)"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# ------------------------------------------------------------------ Chrome with worker events

class DiagChrome(item2.RecordingChrome):
    """RecordingChrome that keeps the page's AND every worker's exceptions and console errors.

    Target.setAutoAttach (flatten) on the page reaches the page's dedicated worker (the url is in the
    event: run_e2_c_product_path.py induce_worker_failure, measured 2026-08-27); the same call on that
    worker's session reaches its nested workers (the wasm's pthreads).  Each attached session gets
    Runtime.enable.  No Debugger domain (it would change how wasm runs)."""

    KEEP = {"Target.attachedToTarget", "Target.detachedFromTarget", "Runtime.exceptionThrown",
            "Runtime.consoleAPICalled", "Log.entryAdded", "Inspector.targetCrashed"}

    def __init__(self):
        self.events: list[dict] = []          # what item2.navigate() keeps (then fed to _on_event)
        self.targets: dict[str, dict] = {}
        self.record: dict = {"exceptions": [], "consoleErrors": [], "detached": [], "attached": [],
                             "consoleCounts": collections.Counter(), "crashedPage": []}
        super().__init__("cold")

    def call(self, method, params=None, timeout=180, session_id=None):
        self.next_id += 1
        message_id = self.next_id
        message = {"id": message_id, "method": method, "params": params or {}}
        if session_id is not None:
            message["sessionId"] = session_id
        self.websocket.send(json.dumps(message))
        while True:
            response = json.loads(self.websocket.recv(timeout=timeout))
            if "id" not in response:
                if response.get("method") == "Page.javascriptDialogOpening":
                    item2.DIALOGS.append({"at": common.now_iso(), **{k: response["params"].get(k)
                                                                      for k in ("type", "message", "url")}})
                if response.get("method") == "Target.attachedToTarget":
                    self._enable_attached(response["params"])
                self._on_event(response)
                continue
            if response.get("id") != message_id:
                continue
            if "error" in response:
                raise RuntimeError(f"CDP {method}: {response['error']}")
            return response.get("result", {})

    def pump(self, seconds: float) -> None:
        """Read events for `seconds` (an evaluate every 0.25 s keeps the socket moving)."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                self.call("Runtime.evaluate", {"expression": "1", "returnByValue": True}, timeout=10)
            except Exception:  # noqa: BLE001 -- a page that cannot answer is recorded elsewhere
                pass
            time.sleep(0.25)
        self.absorb_navigation_events()

    def absorb_navigation_events(self) -> None:
        kept, self.events[:] = list(self.events), []
        for message in kept:
            self._on_event(message)

    def _enable_attached(self, params: dict) -> None:
        sid = params.get("sessionId")
        if not sid:
            return
        info = params.get("targetInfo") or {}
        self.targets[sid] = {"type": info.get("type"), "url": (info.get("url") or "")[-60:],
                             "parentSession": None}
        for method, args in (("Runtime.enable", {}),
                             ("Target.setAutoAttach", {"autoAttach": True, "flatten": True,
                                                       "waitForDebuggerOnStart": False}),
                             ("Runtime.runIfWaitingForDebugger", {})):
            self.next_id += 1
            self.websocket.send(json.dumps({"id": self.next_id, "method": method, "params": args,
                                            "sessionId": sid}))

    def _where(self, message: dict) -> dict:
        sid = message.get("sessionId")
        if sid is None:
            return {"target": "page"}
        info = self.targets.get(sid, {})
        return {"target": info.get("type") or "unknown", "url": info.get("url"), "session": sid[-8:]}

    def _on_event(self, message: dict) -> None:
        method = message.get("method")
        params = message.get("params") or {}
        rec = self.record
        if method == "Target.attachedToTarget":
            info = params.get("targetInfo") or {}
            rec["attached"].append({"at": common.now_iso(), "type": info.get("type"),
                                    "url": (info.get("url") or "")[-60:],
                                    "session": (params.get("sessionId") or "")[-8:],
                                    "via": self._where(message)["target"]})
        elif method == "Target.detachedFromTarget":
            sid = params.get("sessionId") or ""
            rec["detached"].append({"at": common.now_iso(), "session": sid[-8:],
                                    **{k: v for k, v in self.targets.get(sid, {}).items() if k != "parentSession"}})
        elif method == "Runtime.exceptionThrown":
            details = params.get("exceptionDetails") or {}
            exc = details.get("exception") or {}
            frames = ((details.get("stackTrace") or {}).get("callFrames") or [])
            rec["exceptions"].append({
                "at": common.now_iso(), **self._where(message),
                "text": str(details.get("text"))[:300],
                "description": str(exc.get("description") or "")[:6000],
                "className": exc.get("className"),
                "frames": [{"fn": f.get("functionName"), "url": (f.get("url") or "")[-50:],
                            "line": f.get("lineNumber"), "col": f.get("columnNumber")} for f in frames[:300]],
                "frameCount": len(frames)})
        elif method == "Runtime.consoleAPICalled":
            kind = params.get("type")
            where = self._where(message)
            rec["consoleCounts"][f"{where['target']}:{kind}"] += 1
            if kind in ("error", "warning", "assert") and len(rec["consoleErrors"]) < 60:
                args = params.get("args") or []
                text = " ".join(str(a.get("value") if "value" in a else a.get("description")) for a in args)
                rec["consoleErrors"].append({"at": common.now_iso(), **where, "type": kind, "text": text[:1500]})
        elif method == "Log.entryAdded":
            entry = params.get("entry") or {}
            if entry.get("level") in ("error", "warning") and len(rec["consoleErrors"]) < 60:
                rec["consoleErrors"].append({"at": common.now_iso(), **self._where(message), "type": f"log-{entry.get('level')}",
                                             "source": entry.get("source"), "text": str(entry.get("text"))[:1500]})
        elif method == "Inspector.targetCrashed":
            rec["crashedPage"].append({"at": common.now_iso(), **self._where(message)})

    def snapshot(self) -> dict:
        out = dict(self.record)
        out["consoleCounts"] = dict(self.record["consoleCounts"])
        return out


def open_browser(browser: str):
    if browser == "chrome":
        session = DiagChrome()
        session.call("Log.enable")
        session.call("Emulation.setDeviceMetricsOverride",
                     {"width": 1400, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
        session.call("Target.setAutoAttach", {"autoAttach": True, "flatten": True, "waitForDebuggerOnStart": False})
        return session
    return item2.open_browser("firefox")


# ------------------------------------------------------------------ mirrors

def build_page(page: str, scratch: Path, extra: dict[str, bytes]) -> dict:
    target = scratch / f"mirror-{page}"
    if page == "v21":
        return common.build_mirror(target, snippets=[v20.OBSERVER, obs2.SNIPPET, hook.SNIPPET], extra_files=extra)
    if page == "v0224":
        return common.build_mirror(target, page_profile="e2-editor-v20", shell_from_tree=False,
                                   source_page=(common.DIST / "e2-editor-app.js").read_text(encoding="utf-8"),
                                   snippets=[v20.OBSERVER, obs2.SNIPPET], extra_files=extra)
    if page == "v21big":
        shipped_worker = (common.DIST / "profiles/e2-editor-v21/sdk-worker.js").read_bytes()
        # The shipped worker as an "override" only so that profiles/e2-editor-v21/ is a REAL directory in the
        # mirror (pp.build_mirror symlinks everything else into dist/); its bytes are the shipped ones.
        identity = common.build_mirror(target, snippets=[v20.OBSERVER, obs2.SNIPPET, hook.SNIPPET],
                                       extra_files=extra, worker_override=shipped_worker)
        loader = target / "profiles/e2-editor-v21/probe.js"
        if loader.parent.is_symlink() or not loader.is_symlink():
            raise SystemExit(f"refusing: {loader} is not a symlink inside a real mirror directory")
        source = loader.resolve()
        if common.DIST.resolve() not in source.parents:
            raise SystemExit(f"refusing: {loader} does not point into dist/")
        text = source.read_text(encoding="utf-8")
        if text.count(STACK_CALL) != 1:
            raise SystemExit("the loader's thread-init call is not where the counterfactual expects it")
        patched = text.replace(STACK_CALL, STACK_BIG, 1)
        loader.unlink()                       # removes the symlink only; dist/ is never opened for writing
        loader.write_text(patched, encoding="utf-8")
        identity["counterfactual"] = {
            "file": "profiles/e2-editor-v21/probe.js", "shippedSha256": sha(text.encode("utf-8")),
            "servedSha256": sha(patched.encode("utf-8")), "replaced": STACK_CALL, "with": STACK_BIG,
            "probeWasmUntouched": (target / "profiles/e2-editor-v21/probe.wasm").is_symlink()}
        return identity
    raise SystemExit(f"unknown page {page}")


# ------------------------------------------------------------------ one cell

def paragraphs_of(odt: bytes) -> dict:
    """Paragraph count and lengths in the saved document's body (text:p / text:h, any depth)."""
    ns = {"office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
          "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(odt)).read("content.xml"))
    body = root.find("office:body/office:text", ns)
    lengths = []
    for el in body.iter():
        if el.tag in ("{%s}p" % ns["text"], "{%s}h" % ns["text"]):
            text = "".join(t for t in el.itertext())
            spaces = sum(int(s.get("{%s}c" % ns["text"], "1")) for s in el.iter("{%s}s" % ns["text"]))
            lengths.append(len(text) + spaces)
    text_all = "".join(body.itertext())
    return {"paragraphs": len(lengths), "lengths": lengths[:20], "longest": max(lengths) if lengths else 0,
            "totalChars": sum(lengths), "cjkChars": text_all.count(corpora.CJK)}


def page_status(ctx, page: str) -> dict:
    out = {}
    try:
        seen = mws.obs(ctx.session) or {}
        out["obs"] = {k: seen.get(k) for k in ("state", "workers", "documentHandle", "doc")}
    except Exception as error:  # noqa: BLE001
        out["obs"] = {"error": f"{type(error).__name__}: {error}"[:300]}
    try:
        out["pageState"] = pp.evaluate(ctx.session, pp.READ_STATE)
        if isinstance(out["pageState"], dict):
            out["pageState"] = {k: out["pageState"].get(k) for k in ("state", "label", "revision", "pending",
                                                                      "checkpoint", "doc", "toast")}
    except Exception as error:  # noqa: BLE001
        out["pageState"] = {"error": f"{type(error).__name__}: {error}"[:300]}
    if page != "v0224":
        try:
            state = hook.state(ctx.session, ctx.hlog)
            out["session"] = {k: state.get(k) for k in ("state", "revision", "dirty", "pending", "generation",
                                                         "checkpointError", "documentRevision")}
        except Exception as error:  # noqa: BLE001
            out["session"] = {"error": f"{type(error).__name__}: {error}"[:300]}
    try:
        out["notice"] = ctx.ev(item2.NOTICE)
    except Exception as error:  # noqa: BLE001
        out["notice"] = {"error": f"{type(error).__name__}: {error}"[:300]}
    return out


def browser_cpu(session, seconds: float = 2.0) -> dict:
    """CPU of the browser's own processes over `seconds` (a spinning engine thread shows as ~100 % of one
    core in the renderer; a parked one as ~0).  Added after the 45,056-byte cell timed out (bisect2)."""
    process = getattr(session, "process", None)
    if process is None:
        return {"sampled": False, "why": "no browser process handle"}
    tick = os.sysconf("SC_CLK_TCK")
    before, t0 = common._proc_table(), time.monotonic()
    time.sleep(seconds)
    after, t1 = common._proc_table(), time.monotonic()
    tree = common.process_tree(process.pid, after)
    rows = []
    for pid in tree:
        if pid in before and pid in after:
            pct = 100.0 * (after[pid]["ticks"] - before[pid]["ticks"]) / tick / (t1 - t0)
            rows.append({"pid": pid, "comm": after[pid]["comm"], "pct": round(pct, 1)})
    rows.sort(key=lambda r: -r["pct"])
    return {"sampled": True, "seconds": round(t1 - t0, 2), "processes": len(rows), "top": rows[:4]}


def handle_of(ctx, page: str):
    if page == "v0224":
        return er.document_handle(ctx.session)
    return ctx.handle()


def alive(ctx, page: str) -> dict:
    asked = er.ask_state(ctx.trace, handle_of(ctx, page), timeout=8.0)
    return {"answered": asked.get("answered"), "ok": asked.get("ok"), "roundTripMs": asked.get("roundTripMs"),
            "rev": (asked.get("result") or {}).get("rev")}


def ctrlv_once(ctx, url: str, expect_sha: str, timeout: float) -> dict:
    out = {"clipboard": clip.write_from_url(ctx.session, url)}
    out["clipboardIntact"] = out["clipboard"].get("sha256") == expect_sha
    ctx.focus_sink()
    out["focus"] = ctx.ev(item2.ACTIVE)
    mark = ctx.mark()
    t0 = time.monotonic()
    clip.press_ctrl_v(ctx.session, ctx.browser)
    rq = None
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and rq is None:
        ctx.ilog.drain()
        rq = next((e for e in ctx.ilog.all[mark:] if e.get("k") == "rq" and e.get("op") == "insertText"), None)
        time.sleep(0.1)
    out["insertTextRequested"] = rq is not None
    if rq is not None:
        rs = ctx.wait_rs(mark, lambda e: e.get("op") == "insertText", timeout)
        out["response"] = {k: (rs or {}).get(k) for k in ("ok", "code", "dispatched", "revision", "message")} if rs else None
        out["seconds"] = round(time.monotonic() - t0, 3)
    out["requests"] = [{"op": e.get("op")} for e in ctx.ilog.all[mark:] if e.get("k") == "rq"]
    return out


def run_cell(browser: str, page: str, base: str, docs: Path, spec: dict, files: dict) -> dict:
    rec: dict = {"spec": spec, "startedAt": common.now_iso()}
    session = None
    t_cell = time.monotonic()
    with common.browser_lock(f"diag_long_paragraph {browser} {spec['cell']}", wait_s=7200) as holder:
        rec["lock"] = {"since": holder.get("since")}
        pre = common.pre_run_checks()
        rec["preRun"] = {k: pre.get(k) for k in ("kwalletLocked", "chromeProcesses", "firefoxProcesses",
                                                  "oursRunning", "loadavg", "refuse")}
        if pre["refuse"]:
            rec["refused"] = pre["refuse"]
            return rec
        rec["foreignCpu"] = {k: common.foreign_cpu().get(k) for k in ("ok", "overLimit", "loadavg")}
        try:
            session = open_browser(browser)
            rec["browserVersion"] = getattr(session, "version", None)
            if spec["route"].startswith("ctrlv"):
                rec["clipboardGrant"] = clip.grant(session, browser, base.rsplit("/", 1)[0])
            ctx = item2.Ctx(session, browser, base, docs, {})
            rec["load"] = ctx.load()
            if browser == "chrome":
                session.absorb_navigation_events()
            route = spec["route"]
            t0 = time.monotonic()
            if route in ("open", "opentype"):
                # The document IS the attempt: open an ODT whose body already holds the long paragraph.
                try:
                    if page == "v0224":
                        opened = bool(mws.open_fixture(session, f"./{spec['file']}", spec["file"]).get("opened"))
                    else:
                        ctx.open(spec["file"])
                        opened = True
                except Exception as error:  # noqa: BLE001 -- the open's failure is the result here
                    opened = False
                    rec["openError"] = f"{type(error).__name__}: {error}"[:600]
                ctx.drain()
                rec["attempt"] = {"route": route, "opened": opened, "seconds": round(time.monotonic() - t0, 3)}
                if route == "opentype" and opened:
                    # Then one character at the caret the open leaves (the document's start), by a raw
                    # insertText (both pages): the paragraph is reformatted with its follows already there.
                    typed = obs2.ask(session, ctx.ilog, "insertText", {"documentHandle": handle_of(ctx, page),
                                                                       "text": "x"}, timeout=WORKER_TIMEOUT)
                    entry = typed.get("entry") or {}
                    rec["attempt"]["typed"] = {"answered": typed["answered"], "seconds": typed.get("seconds"),
                                               **{k: entry.get(k) for k in ("ok", "code", "revision", "message")}}
            elif page == "v0224":
                opened = mws.open_fixture(session, f"./{EMPTY}", EMPTY)
                ctx.drain()
                rec["open"] = {"opened": opened.get("opened")}
            else:
                rec["open"] = {k: v for k, v in ctx.open(EMPTY).items() if k != "capture"}
                rec["open"]["captureOk"] = ctx.capture.get("ok")
            if route not in ("open", "opentype"):
                rec["before"] = alive(ctx, page)
            url = "./" + spec["file"]
            t0 = time.monotonic()
            if route in ("open", "opentype"):
                pass
            elif route == "sdk-md" or route == "sdk-text":
                method = "pasteMarkdown" if route == "sdk-md" else "insertText"
                answer = hook.call(session, ctx.hlog, "document", method, text_url=url, timeout=PASTE_TIMEOUT)
                rec["attempt"] = {"route": route, "method": method,
                                  **{k: answer.get(k) for k in ("answered", "ok", "error", "ms", "waitedS")},
                                  "value": (answer.get("value") if not isinstance(answer.get("value"), dict)
                                            else {k: answer["value"].get(k) for k in ("revision", "completion", "ok")})}
            elif route in ("worker-md", "worker-text"):
                operation = "pasteMarkdown" if route == "worker-md" else "insertText"
                answer = obs2.ask(session, ctx.ilog, operation, {"documentHandle": handle_of(ctx, page)},
                                  text_url=url, timeout=WORKER_TIMEOUT)
                entry = answer.get("entry") or {}
                rec["attempt"] = {"route": route, "answered": answer["answered"], "posted": answer["posted"],
                                  "seconds": answer.get("seconds"),
                                  "response": {k: entry.get(k) for k in ("k", "ok", "code", "dispatched", "revision",
                                                                          "message", "error")}}
            elif route.startswith("ctrlv-text"):
                times = int(route[len("ctrlv-textx"):]) if route.startswith("ctrlv-textx") else 1
                caret = {}
                if page != "v0224":
                    caret = ctx.ask().get("caret") or {}
                rec["click"] = ctx.click_twips(caret.get("x", 1418) + 1,
                                               caret.get("y", 1418) + caret.get("height", 276) / 2)
                rec["attempt"] = {"route": route, "times": times, "pastes": []}
                for _ in range(times):
                    one = ctrlv_once(ctx, url, spec["sha256"], PASTE_TIMEOUT)
                    rec["attempt"]["pastes"].append(one)
                    if not (one.get("response") or {}).get("ok"):
                        break
            else:
                raise SystemExit(f"unknown route {route}")
            rec["attemptSeconds"] = round(time.monotonic() - t0, 3)
            if browser == "chrome":
                session.pump(4.0)
            else:
                time.sleep(4.0)
            rec["browserCpu"] = browser_cpu(session)
            rec["after"] = page_status(ctx, page)
            rec["alive"] = alive(ctx, page)
            if rec["alive"].get("answered"):
                raw = er.save(session, timeout=90)
                if raw:
                    path = docs / f"{spec['n']:03d}-{re.sub(r'[^A-Za-z0-9_.+-]', '_', spec['cell'])}.odt"
                    if path.exists():
                        raise SystemExit(f"refusing to overwrite {path}")
                    path.write_bytes(raw)
                    rec["saved"] = {"file": path.name, "sha256": sha(raw), "bytes": len(raw), **paragraphs_of(raw)}
                else:
                    rec["saved"] = {"saved": False}
        except Exception as error:  # noqa: BLE001
            rec["runnerError"] = f"{type(error).__name__}: {error}"[:1000]
            rec["traceback"] = traceback.format_exc()[-2500:]
        finally:
            if browser == "chrome" and session is not None:
                try:
                    session.pump(1.0)
                except Exception:  # noqa: BLE001
                    pass
                rec["cdp"] = session.snapshot()
            rec["javascriptDialogs"] = list(item2.DIALOGS)
            item2.DIALOGS.clear()
            if session is not None:
                rec["close"] = common.close_browser(session)
    rec["outcome"] = classify(rec)
    rec["cellSeconds"] = round(time.monotonic() - t_cell, 1)
    return rec


def classify(rec: dict) -> str:
    """A label for reading the report, from the fields above (the fields are the record)."""
    if rec.get("refused"):
        return "not-run"
    if rec.get("runnerError") and "attempt" not in rec:
        return "runner-error"
    attempt = rec.get("attempt") or {}
    oob = any("memory access out of bounds" in (e.get("description") or e.get("text") or "")
              for e in (rec.get("cdp") or {}).get("exceptions", []))
    # An uncaught exception on a pthread (the loader's own worker url) after a paste that answered ok:
    # seen at 43,520 bytes (edges), where the paste returned and the engine thread then aborted.
    pthread = any((e.get("url") or "").endswith("probe.js") for e in (rec.get("cdp") or {}).get("exceptions", []))
    # Without CDP (Firefox) the same shows as: the page in recoverable-error, or the engine answering the
    # state ask with ok:false (seen at 43,520 bytes in firefox-s7).
    after_alive = rec.get("alive") or {}
    page_error = ((rec.get("after") or {}).get("pageState") or {}).get("state") == "recoverable-error"
    late = "ok-then-crash" if (pthread or page_error or (after_alive.get("answered") and not after_alive.get("ok"))) else "ok"
    if attempt.get("route") in ("open", "opentype"):
        if oob or (pthread and attempt.get("typed") is None):
            return "crash"
        if not attempt.get("opened"):
            return "hang" if not (rec.get("alive") or {}).get("answered") else "open-failed"
        typed = attempt.get("typed")
        if typed is not None and not typed.get("ok"):
            return ("hang" if not (rec.get("alive") or {}).get("answered") else "no-reply") \
                if not typed.get("answered") else f"refused:{typed.get('code')}"
        return late
    if attempt.get("route", "").startswith("ctrlv"):
        last = (attempt.get("pastes") or [{}])[-1]
        if not last.get("insertTextRequested"):
            return "no-request"
        resp = last.get("response") or {}
        if resp.get("ok"):
            return late
        if resp.get("code") == "WORKER_CRASHED" or oob:
            return "crash"
        return "no-reply" if not resp else f"refused:{resp.get('code')}"
    if attempt.get("route") in ("worker-md", "worker-text"):
        resp = attempt.get("response") or {}
        if attempt.get("answered") and resp.get("ok"):
            return late
        if oob or pthread:
            return "crash"
        if not attempt.get("answered"):
            return "hang" if not (rec.get("alive") or {}).get("answered") else "no-reply"
        return f"refused:{resp.get('code')}"
    if attempt.get("answered") and attempt.get("ok"):
        return late
    code = (attempt.get("error") or {}).get("code") if isinstance(attempt.get("error"), dict) else None
    if code == "WORKER_CRASHED" or oob:
        return "crash"
    if code == "TIMEOUT" and not (rec.get("alive") or {}).get("answered"):
        return "hang"            # the SDK's request timeout, and the worker answers nothing afterwards
    return "no-reply" if not attempt.get("answered") else f"refused:{code}"


def parse_cell(text: str, n: int, odts: dict[str, Path]) -> dict:
    parts = text.split(":")
    if len(parts) not in (3, 4):
        raise SystemExit(f"bad cell {text}")
    route, corpus, size = parts[:3]
    page = parts[3] if len(parts) == 4 else "v21"
    if route in ("open", "opentype"):
        raw = odts[corpus].read_bytes()
        return {"cell": text, "n": n, "route": route, "corpus": corpus, "bytes": len(raw), "page": page,
                "file": f"v21-diag-{corpus}.odt", "sha256": sha(raw), "source": str(odts[corpus]), "raw": raw}
    raw = corpora.make(corpus, int(size))
    return {"cell": text, "n": n, "route": route, "corpus": corpus, "bytes": int(size), "page": page,
            "file": f"diag/{corpus}-{int(size)}.md", "sha256": sha(raw), "describe": corpora.describe(raw),
            "raw": raw}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--repeat", type=int, default=1, help="run the whole cell list N times (each cell fresh)")
    ap.add_argument("--odt", action="append", default=[],
                    help="NAME=PATH: a document for route `open` (cell open:NAME:0[:PAGE])")
    ap.add_argument("cells", nargs="+")
    args = ap.parse_args()
    odts = {k: Path(v) for k, v in (item.split("=", 1) for item in args.odt)}
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    args.out.mkdir(parents=True, exist_ok=True)
    report_path = args.out / f"report-{args.label}.json"
    if report_path.exists():
        raise SystemExit(f"refusing to overwrite {report_path}")
    docs = args.out / f"docs-{args.label}"
    docs.mkdir(parents=True, exist_ok=False)
    specs = []
    for k in range(args.repeat):
        for cell in args.cells:
            specs.append(parse_cell(cell, len(specs) + 1, odts))
    extra: dict[str, bytes] = {f"v21-i2-empty.odt": (item2.NATIVE / "tool/inputs/empty-template.odt").read_bytes()}
    for spec in specs:
        if extra.get(spec["file"], spec["raw"]) != spec["raw"]:
            raise SystemExit(f"two different inputs for {spec['file']}")
        extra[spec["file"]] = spec["raw"]
    report = {"tool": "diag_long_paragraph.py", "toolSha256": sha(Path(__file__).read_bytes()),
              "corporaSha256": sha((HERE / "corpora.py").read_bytes()), "counted": False, "judged": False,
              "browser": args.browser, "label": args.label, "argv": sys.argv[1:], "startedAt": common.now_iso(),
              "instruments": {n: sha((TOOLS / n).read_bytes()) for n in
                              ("v21_shakedown_common.py", "run_v21_shakedown_item2.py", "v21_page_hook.py",
                               "v21_item2_observer.py", "v21_clipboard.py", "v21_engine_read.py")},
              "identity": {}, "cells": []}

    def flush() -> None:
        report_path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))

    scratch = Path(tempfile.mkdtemp(prefix="diag-long-para-", dir=os.environ.get("DIAG_SCRATCH") or None))
    pages = sorted({s["page"] for s in specs})
    stack = []
    bases = {}
    try:
        for page in pages:
            identity = build_page(page, scratch, extra)
            report["identity"][page] = {k: v for k, v in identity.items() if k != "extraFiles"}
            report["identity"][page]["extraFiles"] = {k: v for k, v in identity["extraFiles"].items()}
            served = common.served(Path(identity["mirror"]))
            bases[page] = served.__enter__()
            stack.append(served)
        flush()
        for spec in specs:
            public = {k: v for k, v in spec.items() if k != "raw"}
            print(f"[{common.now_iso()}] cell {spec['n']}/{len(specs)} {spec['cell']}", flush=True)
            rec = run_cell(args.browser, spec["page"], bases[spec["page"]], docs, public, extra)
            report["cells"].append(rec)
            flush()
            print(f"    -> {rec.get('outcome')} attempt={rec.get('attemptSeconds')}s cell={rec.get('cellSeconds')}s",
                  flush=True)
            if rec.get("refused"):
                break
    finally:
        while stack:
            try:
                stack.pop().__exit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
        report["completedAt"] = common.now_iso()
        flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
