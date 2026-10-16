#!/usr/bin/env python3
"""S-3: the page-realm module hook -- the page's OWN session, client and DocumentHandle, reached without
changing a byte of the page or the shell.

Arms: findings/evidence/link-batch-v21/shakedown/ARMS.md S-3; ARMS-item2.md I-3 and §9 DM-1 (ruling A);
ARMS-item1.md §8 D-7 (superseded by this; item 1 uses it for D11c and D12).

How it reaches the page's objects.  SNIPPET is a `<script type="module">` that S-1 injects before the
page's module.  It imports `./editor-shell-v2/narrow-editor-v2-session.js` and
`./editor-shell-v2/paragraph-editor-session.js` by the URLs the page's own module graph uses
(web/e2-editor-app.js:30-31 imports the first; narrow-editor-v2-session.js:37 imports the second), so the
document's module map hands it the SAME module instances, and module scripts run in document order, so
the hook runs before the page creates its session.  It replaces a few methods of
`NarrowEditorV2Session.prototype` with pass-through wrappers that remember `this` (the page's session):
the page calls `offersPasteMarkdown()` on every state update (web/e2-editor-app.js:1023, :1208-1212).
The wrappers return exactly what the original returns and rethrow exactly what it throws.

What it offers (everything goes through DOM nodes: Firefox evaluates the runner's scripts in a Marionette
sandbox, so the runner never touches page globals):

  - log entries in `#v21-hook` (drained like v20's trace):
      capture   the hook saw a session object (n = how many distinct ones so far)
      paste     every `session.pasteMarkdown(text)` the PAGE makes (the dialog route): utf16/utf8 lengths
                (never the text), then ok + revision, or the rejection's code, message (300 chars),
                recovery, dispatched, details.{dispatched, limitBytes, utf8Bytes, operation}
      call      the answer to a runner request (below)
      error     the hook could not install (the import failed, a method to wrap is missing)
  - requests (`call()` below): target "session" | "document" | "editor" | "hook", a method name, JSON
    args; optionally `textUrl` -- the page realm fetches it and decodes it with
    TextDecoder("utf-8", {fatal: true}), so no CDP frame carries a 64 KiB text -- inserted as argument
    `textIndex`.  "document" is `session.document` (the page's DocumentHandle: the direct-SDK route,
    which bypasses the page's shape check and the session's queue); "editor" is `session.editor` (the
    page's client).  "hook"/"state" reads the session: revision, state, dirty, hasUnsavedEdits(),
    hasCheckpoint, checkpointError, enqueueCount, pending, generation, the document handle and revision,
    and `#s-revision` for the positive control.  Rejections carry `recoveryFor(error)` computed with the
    shell's own function (DM-8 A).

Positive control (every page load): `capture_check()` -- the node exists, a session was captured, and
the captured session's revision equals the page's `#s-revision`.  A load where it fails makes every arm
that needs the hook NOT_ESTABLISHED (ARMS-item2.md §9 DM-1).

Python interface (stable; item 1 imports it):

  SNIPPET                                    the <script type="module"> block for S-1's `snippets`
  HookLog(session)                           .drain() -> new entries; .all; .reset() after a navigation
  call(session, log, target, method, args=(), text_url=None, text_index=0, timeout=30.0) -> dict
      -> {"answered": bool, "ok": bool, "value": ..., "error": {...}, "ms": float, "entry": {...}}
  state(session, log, timeout=5.0) -> dict   the "hook"/"state" read (value of the call)
  capture_check(session, log, timeout=15.0) -> dict   {"present", "captured", "revisionMatchesPage", "ok", ...}
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r7_support  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

NODE_ID = "v21-hook"
WRAPPED = ("offersPasteMarkdown", "open", "pasteMarkdown", "action", "undo")

# The hook's logic, as one function the snippet calls with the real classes and a node test calls with
# fakes (tests/test_v21_page_hook.py).  Plain JS, no imports.
CORE_JS = r"""
function v21InstallPageHook(env) {
  const doc = env.document;
  const now = env.now;
  const log = [];
  let seq = 0, queued = false;
  const node = doc.createElement("script");
  node.type = "application/json"; node.id = "v21-hook";
  const flush = () => {
    queued = false;
    const cut = Number(node.dataset.cut ?? -1);
    for (let i = log.length - 1; i >= 0; i -= 1) if (log[i].s <= cut) log.splice(i, 1);
    node.textContent = JSON.stringify(log);
  };
  const later = () => { if (!queued) { queued = true; env.defer(flush); } };
  const push = (entry) => { entry.s = seq; seq += 1; entry.t = now(); log.push(entry); later(); };
  const hook = { session: null, sessions: 0 };
  const capture = (self) => {
    if (self && hook.session !== self) { hook.session = self; hook.sessions += 1; push({ k: "capture", n: hook.sessions }); }
  };
  const utf8 = (text) => (typeof text === "string" ? new TextEncoder().encode(text).byteLength : null);
  const safe = (fn) => { try { return fn(); } catch (error) { return { threw: String(error && error.message || error).slice(0, 200) }; } };
  const errorOf = (error) => {
    const details = (error && typeof error.details === "object" && error.details) || {};
    return {
      code: error && error.code !== undefined ? error.code : null,
      name: error && error.name ? String(error.name) : null,
      message: String(error && error.message !== undefined ? error.message : error).slice(0, 300),
      recovery: error && error.recovery !== undefined ? error.recovery : null,
      dispatched: error && typeof error.dispatched === "boolean" ? error.dispatched
        : (typeof details.dispatched === "boolean" ? details.dispatched : null),
      details: { dispatched: details.dispatched ?? null, limitBytes: details.limitBytes ?? null,
                 utf8Bytes: details.utf8Bytes ?? null, operation: details.operation ?? null,
                 code: details.code ?? null },
      recoveryFor: env.recoveryFor ? safe(() => env.recoveryFor(error)) : null,
    };
  };
  const summarize = (value) => {
    let budget = 8000;
    const seen = new WeakSet();
    const walk = (v, depth) => {
      if (budget <= 0) return "(cut)";
      if (v === null || v === undefined || typeof v === "number" || typeof v === "boolean") return v ?? null;
      if (typeof v === "string") { budget -= Math.min(v.length, 400); return v.length > 400 ? v.slice(0, 400) + "...(" + v.length + ")" : v; }
      if (v instanceof ArrayBuffer) return { arrayBuffer: v.byteLength };
      if (ArrayBuffer.isView(v)) return { typedArray: v.byteLength };
      if (typeof v === "function") return "(function)";
      if (typeof v !== "object" || depth > 6) return String(v).slice(0, 80);
      if (seen.has(v)) return "(cycle)";
      seen.add(v);
      if (Array.isArray(v)) return v.slice(0, 50).map((x) => walk(x, depth + 1));
      const out = {};
      for (const key of Object.keys(v).slice(0, 60)) { budget -= key.length; out[key] = walk(v[key], depth + 1); }
      return out;
    };
    return walk(value, 0);
  };
  const proto = env.Session && env.Session.prototype;
  if (!proto) { push({ k: "error", what: "no session class" }); }
  for (const name of env.wrap) {
    const base = proto && proto[name];
    if (typeof base !== "function") { push({ k: "error", what: "nothing to wrap: " + name }); continue; }
    proto[name] = function (...args) {
      capture(this);
      if (name !== "pasteMarkdown") return base.apply(this, args);
      const entry = { k: "paste", route: "session", utf16: typeof args[0] === "string" ? args[0].length : null, utf8: utf8(args[0]) };
      let result;
      try { result = base.apply(this, args); }
      catch (error) { push(Object.assign(entry, { ok: false, error: errorOf(error) })); throw error; }
      if (!result || typeof result.then !== "function") { push(Object.assign(entry, { ok: true, value: summarize(result) })); return result; }
      return result.then(
        (value) => { push(Object.assign(entry, { ok: true, revision: value && value.revision !== undefined ? value.revision : null })); return value; },
        (error) => { push(Object.assign(entry, { ok: false, error: errorOf(error) })); throw error; });
    };
  }
  const stateOf = () => {
    const s = hook.session;
    const pageRevision = safe(() => { const n = doc.querySelector("#s-revision"); return n ? n.textContent : null; });
    if (!s) return { captured: false, pageRevision };
    const snap = (s.state && s.state.snapshot) || {};
    const checkpointError = snap.checkpointError;
    return {
      captured: true, sessions: hook.sessions, revision: snap.revision ?? null, state: snap.state ?? null,
      dirty: snap.dirty ?? null, hasUnsavedEdits: safe(() => s.hasUnsavedEdits()),
      hasCheckpoint: snap.hasCheckpoint ?? null,
      checkpointError: checkpointError ? (checkpointError.code ?? String(checkpointError)) : null,
      enqueueCount: s.enqueueCount ?? null, pending: snap.pending ?? null, generation: snap.generation ?? null,
      documentHandle: s.document ? (s.document.handle ?? null) : null,
      documentRevision: s.document ? (s.document.revision ?? null) : null,
      pageRevision,
    };
  };
  const targetOf = (name) => {
    const s = hook.session;
    if (name === "session") return s;
    if (name === "document") return s && s.document;
    if (name === "editor") return s && s.editor;
    return null;
  };
  const handle = async (request) => {
    const out = { k: "call", id: request.id, target: request.target, method: request.method };
    try {
      if (request.target === "hook" && request.method === "state") { push(Object.assign(out, { ok: true, value: stateOf() })); return; }
      if (!hook.session) { push(Object.assign(out, { ok: false, error: { code: "HOOK_NOT_CAPTURED" } })); return; }
      const target = targetOf(request.target);
      if (!target || typeof target[request.method] !== "function") {
        push(Object.assign(out, { ok: false, error: { code: "HOOK_NO_METHOD" } })); return;
      }
      const args = Array.isArray(request.args) ? request.args.slice() : [];
      if (request.textUrl) {
        const response = await env.fetch(request.textUrl, { cache: "no-cache" });
        const buffer = await response.arrayBuffer();
        out.textBytes = buffer.byteLength;
        args.splice(request.textIndex || 0, 0, new TextDecoder("utf-8", { fatal: true }).decode(buffer));
      }
      const started = now();
      const value = await target[request.method](...args);
      push(Object.assign(out, { ok: true, ms: Math.round((now() - started) * 10) / 10, value: summarize(value) }));
    } catch (error) {
      push(Object.assign(out, { ok: false, error: errorOf(error) }));
    }
  };
  doc.documentElement.addEventListener("v21-hook", () => {
    let request = null;
    try { request = JSON.parse(doc.documentElement.dataset.v21hookReq || "null"); }
    catch (error) { push({ k: "error", what: "bad request: " + String(error) }); return; }
    if (request) void handle(request);
  });
  const attach = () => { (doc.head || doc.documentElement).appendChild(node); flush(); };
  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", attach); else attach();
  push({ k: "installed", wrapped: env.wrap.filter((name) => proto && typeof proto[name] === "function") });
  return { hook, stateOf, handle, push };
}
"""

SNIPPET = ("""<script type="module">
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";
import { recoveryFor } from "./editor-shell-v2/paragraph-editor-session.js";
""" + CORE_JS + """
try {
  v21InstallPageHook({ Session: NarrowEditorV2Session, recoveryFor, document, wrap: %s,
                       now: () => performance.now(), defer: (fn) => setTimeout(fn, 0),
                       fetch: (url, options) => fetch(url, options) });
} catch (error) {
  const n = document.createElement("script"); n.type = "application/json"; n.id = "v21-hook";
  n.textContent = JSON.stringify([{ s: 0, k: "error", what: "install threw: " + String(error) }]);
  document.head.appendChild(n);
}
</script>""") % json.dumps(list(WRAPPED))

READ = "(() => { const n = document.getElementById('v21-hook'); return n ? n.textContent : null; })()"
CUT = "(() => {{ const n = document.getElementById('v21-hook'); if (n) n.dataset.cut = '{0}'; return true; }})()"
PRESENT = "(() => !!document.getElementById('v21-hook'))()"
REQUEST = ("document.documentElement.dataset.v21hookReq = ARG_JSON;"
           " document.documentElement.dispatchEvent(new Event('v21-hook'));")


class HookLog:
    """The hook's node, drained (acknowledged cut) and kept whole for the run."""

    def __init__(self, session):
        self.session = session
        self.last = -1
        self.all: list[dict] = []

    def reset(self) -> None:
        self.last = -1

    def drain(self) -> list[dict]:
        raw = pp.evaluate(self.session, READ)
        if not raw:
            return []
        try:
            entries = [e for e in json.loads(raw) if e.get("s", -1) > self.last]
        except json.JSONDecodeError:
            return []
        if entries:
            self.last = max(e["s"] for e in entries)
            pp.evaluate(self.session, CUT.format(self.last))
            self.all += entries
        return entries


_IDS = {"n": 0}


def call(session, log: HookLog, target: str, method: str, args=(), text_url: str | None = None,
         text_index: int = 0, timeout: float = 30.0) -> dict:
    """One request to the page realm; waits for its `call` entry."""
    _IDS["n"] += 1
    rid = f"h{int(time.time() * 1000) % 100000000}-{_IDS['n']}"
    request = {"id": rid, "target": target, "method": method, "args": list(args)}
    if text_url is not None:
        request["textUrl"] = text_url
        request["textIndex"] = text_index
    sent = time.monotonic()
    r7_support.run_in_page(session, REQUEST.replace("ARG_JSON", json.dumps(json.dumps(request))))
    deadline = sent + timeout
    while time.monotonic() < deadline:
        for entry in log.drain():
            if entry.get("k") == "call" and entry.get("id") == rid:
                return {"answered": True, "ok": entry.get("ok"), "value": entry.get("value"),
                        "error": entry.get("error"), "ms": entry.get("ms"), "entry": entry,
                        "waitedS": round(time.monotonic() - sent, 3)}
        for entry in log.all:
            if entry.get("k") == "call" and entry.get("id") == rid:
                return {"answered": True, "ok": entry.get("ok"), "value": entry.get("value"),
                        "error": entry.get("error"), "ms": entry.get("ms"), "entry": entry,
                        "waitedS": round(time.monotonic() - sent, 3)}
        time.sleep(0.1)
    return {"answered": False, "ok": None, "request": request, "waitedS": round(time.monotonic() - sent, 3)}


def state(session, log: HookLog, timeout: float = 5.0) -> dict:
    answer = call(session, log, "hook", "state", timeout=timeout)
    return answer.get("value") if answer.get("answered") and answer.get("ok") else {"captured": None, "answer": answer}


def capture_check(session, log: HookLog, timeout: float = 15.0) -> dict:
    """The per-load positive control: present, captured, and the captured session is the page's."""
    deadline = time.monotonic() + timeout
    present = bool(pp.evaluate(session, PRESENT))
    read = {}
    while time.monotonic() < deadline:
        present = bool(pp.evaluate(session, PRESENT))
        if present:
            read = state(session, log)
            if read.get("captured") and str(read.get("revision")) == str(read.get("pageRevision")):
                break
        time.sleep(0.25)
    errors = [e for e in log.all if e.get("k") == "error"]
    ok = (present and read.get("captured") is True
          and str(read.get("revision")) == str(read.get("pageRevision")) and not errors)
    return {"present": present, "captured": read.get("captured"), "revision": read.get("revision"),
            "pageRevision": read.get("pageRevision"),
            "revisionMatchesPage": str(read.get("revision")) == str(read.get("pageRevision")),
            "installErrors": errors, "ok": ok}
