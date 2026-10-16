#!/usr/bin/env python3
"""The item-2 observer snippet (ARMS.md S-2; ARMS-item2.md I-2): one `<script>` block, injected by S-1 AFTER
v20's OBSERVER (and after item 1's snippet when both are present), before the page's module.  It never
edits another snippet: it wraps `window.Worker` once more and the instance's `postMessage` the inner
wrappers installed.  Everything goes into its own DOM node `#v21-i2` (Firefox: DOM, not globals).

Entries (`k`):
  rq      every request the page (or this snippet) posts: op, requestId, action; for pasteMarkdown the
          UTF-16 length and UTF-8 bytes of payload.text, for the raw-bytes carrier the buffer's length
          -- never the text; `rewritten: true` when the save rewrite changed it
  rs      every response: op, requestId, ok, and for a failure code, dispatched, operation, revision,
          message (300 chars); for a success revision and completion
  pill    #state-pill's data-state changes (the session's real state; only the shown word waits 700 ms,
          web/e2-editor-app.js:929-960), on the page clock
  ui      #notice data-show, #markdown-dialog open, #markdown-message text and hidden, #s-checkpoint text
  ask     an ask this snippet posted (URL-fed text or bytes), and `askError` when it could not
  rewrite the save-rewrite window opened or closed

The ask channel (`ask()` below): a raw worker message {operation, payload} with requestIds from ASK_BASE
(the SDK drops replies it has no entry for, sdk/document-sdk.js:334-336).  `textUrl`: the page realm
fetches it and decodes it with TextDecoder("utf-8", {fatal: true}) into payload.text (R-worker: the
shipped `pasteMarkdown`, which bypasses the SDK's limit L).  `bytesUrl`: the bytes go as payload.buffer
(transferred) -- only the S-10 raw-bytes carrier accepts that.

The save rewrite (M9-inject, DM-16 A): while armed, every `save` request leaving the page has
payload.format replaced by "x-induced"; the export refuses it before queueing (src/sdk_api.cpp:126-137).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r7_support  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

NODE_ID = "v21-i2"
ASK_BASE = 0x7D000000          # v20's asks use 0x7F000000, item 1's D7 0x7E000000
REWRITE_FORMAT = "x-induced"

SNIPPET = r"""<script>
(() => {
  const Inner = window.Worker;
  const log = [];
  let seq = 0, queued = false, current = null, protocolVersion = null, asks = 0, rewrite = false;
  const node = document.createElement("script");
  node.type = "application/json"; node.id = "v21-i2";
  const now = () => Math.round(performance.now() * 10) / 10;
  const flush = () => {
    queued = false;
    const cut = Number(node.dataset.cut ?? -1);
    for (let i = log.length - 1; i >= 0; i -= 1) if (log[i].s <= cut) log.splice(i, 1);
    node.textContent = JSON.stringify(log);
  };
  const push = (entry) => { entry.s = seq; seq += 1; entry.t = now(); log.push(entry);
                            if (!queued) { queued = true; setTimeout(flush, 0); } };
  const utf8 = (text) => (typeof text === "string" ? new TextEncoder().encode(text).byteLength : null);
  function Wrapped(url, options) {
    const worker = new Inner(url, options);
    if (!(options && options.name === "oxoffice-document-engine")) return worker;
    const requests = new Map();
    current = { worker, requests };
    const post = worker.postMessage.bind(worker);
    worker.postMessage = (message, transfer) => {
      if (message && message.kind === "request") {
        if (message.protocolVersion !== undefined && !(message.requestId >= 0x7D000000)) protocolVersion = message.protocolVersion;
        let rewritten = false;
        if (rewrite && message.operation === "save" && message.payload) {
          message = { ...message, payload: { ...message.payload, format: "x-induced" } };
          rewritten = true;
        }
        const p = message.payload || {};
        const entry = { k: "rq", rq: message.requestId, op: message.operation, action: p.action ?? null };
        if (typeof p.text === "string") { entry.utf16 = p.text.length; entry.utf8 = utf8(p.text); }
        if (p.buffer instanceof ArrayBuffer) entry.bufferBytes = p.buffer.byteLength;
        if (rewritten) entry.rewritten = true;
        requests.set(message.requestId, { op: message.operation, action: p.action ?? null });
        push(entry);
      }
      return post(message, transfer);
    };
    worker.addEventListener("message", (event) => {
      const data = event.data;
      if (!data || data.kind !== "response") return;
      const known = requests.get(data.requestId) ?? {};
      requests.delete(data.requestId);
      const value = data.ok ? data.result : data.error;
      const entry = { k: "rs", rq: data.requestId, op: known.op ?? null, action: known.action ?? null, ok: data.ok };
      if (value && typeof value === "object") {
        if (data.ok) {
          entry.revision = value.revision ?? null; entry.completion = value.completion ?? null;
          if (typeof value.documentHandle === "number") entry.documentHandle = value.documentHandle;
        } else {
          entry.code = value.code ?? null; entry.dispatched = typeof value.dispatched === "boolean" ? value.dispatched : null;
          entry.operation = value.operation ?? null; entry.revision = value.revision ?? null;
          entry.limitBytes = value.limitBytes ?? null;
          entry.message = String(value.message ?? "").slice(0, 300);
        }
      }
      push(entry);
    });
    return worker;
  }
  Wrapped.prototype = Inner.prototype;
  window.Worker = Wrapped;
  document.documentElement.addEventListener("v21-i2-ask", () => {
    void (async () => {
      let ask = null;
      try {
        ask = JSON.parse(document.documentElement.dataset.v21i2ask || "null");
        if (!ask || !current) { push({ k: "askError", id: ask && ask.requestId, error: ask ? "no worker" : "no request" }); return; }
        const payload = { ...(ask.payload || {}) };
        const transfer = [];
        if (ask.textUrl) {
          const buffer = await (await fetch(ask.textUrl, { cache: "no-cache" })).arrayBuffer();
          payload.text = new TextDecoder("utf-8", { fatal: true }).decode(buffer);
        }
        if (ask.bytesUrl) {
          payload.buffer = await (await fetch(ask.bytesUrl, { cache: "no-cache" })).arrayBuffer();
          transfer.push(payload.buffer);
        }
        asks += 1;
        push({ k: "ask", rq: ask.requestId, op: ask.operation });
        current.worker.postMessage({ protocolVersion, kind: "request", requestId: ask.requestId,
                                     operation: ask.operation, payload }, transfer);
      } catch (error) { push({ k: "askError", id: ask && ask.requestId, error: String(error).slice(0, 300) }); }
    })();
  });
  document.documentElement.addEventListener("v21-i2-rewrite", () => {
    rewrite = document.documentElement.dataset.v21i2rewrite === "on";
    push({ k: "rewrite", on: rewrite });
  });
  const watch = () => {
    const pill = document.querySelector("#state-pill");
    if (pill) new MutationObserver(() => push({ k: "pill", state: pill.dataset.state ?? null }))
      .observe(pill, { attributes: true, attributeFilter: ["data-state"] });
    const notice = document.querySelector("#notice");
    if (notice) new MutationObserver(() => push({ k: "ui", what: "notice", show: notice.dataset.show ?? null }))
      .observe(notice, { attributes: true, attributeFilter: ["data-show"] });
    const dialog = document.querySelector("#markdown-dialog");
    if (dialog) new MutationObserver(() => push({ k: "ui", what: "dialog", open: dialog.open }))
      .observe(dialog, { attributes: true, attributeFilter: ["open"] });
    const message = document.querySelector("#markdown-message");
    if (message) new MutationObserver(() => push({ k: "ui", what: "message", hidden: message.hidden,
                                                   text: (message.textContent || "").slice(0, 200) }))
      .observe(message, { attributes: true, childList: true, characterData: true, subtree: true });
    const checkpoint = document.querySelector("#s-checkpoint");
    if (checkpoint) new MutationObserver(() => push({ k: "ui", what: "checkpoint", text: checkpoint.textContent }))
      .observe(checkpoint, { childList: true, characterData: true, subtree: true });
  };
  document.addEventListener("DOMContentLoaded", () => { document.head.appendChild(node); flush(); watch(); });
})();
</script>"""

READ_LEN = "(() => { const n = document.getElementById('v21-i2'); return n ? n.textContent.length : -1; })()"
READ_SLICE = "(() => { const n = document.getElementById('v21-i2'); return n ? n.textContent.slice(ARG_A, ARG_B) : null; })()"
CUT = "(() => {{ const n = document.getElementById('v21-i2'); if (n) n.dataset.cut = '{0}'; return true; }})()"
CHUNK = 400000
ASK = ("document.documentElement.dataset.v21i2ask = ARG_JSON;"
       " document.documentElement.dispatchEvent(new Event('v21-i2-ask'));")
REWRITE = ("document.documentElement.dataset.v21i2rewrite = ARG_STATE;"
           " document.documentElement.dispatchEvent(new Event('v21-i2-rewrite'));")


class Log:
    """`#v21-i2`, drained in chunks with an acknowledged cut (no CDP frame over 1 MiB), kept whole."""

    def __init__(self, session):
        self.session = session
        self.last = -1
        self.all: list[dict] = []

    def reset(self) -> None:
        self.last = -1

    def drain(self) -> list[dict]:
        length = pp.evaluate(self.session, READ_LEN)
        if not isinstance(length, int) or length <= 0:
            return []
        parts = [pp.evaluate(self.session, READ_SLICE.replace("ARG_A", str(a)).replace("ARG_B", str(a + CHUNK)))
                 for a in range(0, length, CHUNK)]
        raw = "".join(p for p in parts if isinstance(p, str))
        try:
            entries = [e for e in (json.loads(raw) if raw else []) if e.get("s", -1) > self.last]
        except json.JSONDecodeError:
            return []
        if entries:
            self.last = max(e["s"] for e in entries)
            pp.evaluate(self.session, CUT.format(self.last))
            self.all += entries
        return entries

    def wait(self, predicate, timeout: float) -> dict | None:
        deadline = time.monotonic() + timeout
        for entry in self.all:
            if predicate(entry):
                return entry
        while time.monotonic() < deadline:
            for entry in self.drain():
                if predicate(entry):
                    return entry
            time.sleep(0.1)
        return None


_ASKS = {"n": 0}


def ask(session, log: Log, operation: str, payload: dict, text_url: str | None = None,
        bytes_url: str | None = None, timeout: float = 60.0) -> dict:
    """A raw worker request; waits for its response entry."""
    _ASKS["n"] += 1
    rq = ASK_BASE + (int(time.time() * 10) % 0x00FFFF) * 64 + _ASKS["n"] % 64
    request = {"requestId": rq, "operation": operation, "payload": payload}
    if text_url:
        request["textUrl"] = text_url
    if bytes_url:
        request["bytesUrl"] = bytes_url
    sent = time.monotonic()
    r7_support.run_in_page(session, ASK.replace("ARG_JSON", json.dumps(json.dumps(request))))
    entry = log.wait(lambda e: (e.get("k") == "rs" and e.get("rq") == rq)
                     or (e.get("k") == "askError" and e.get("id") == rq), timeout)
    return {"requestId": rq, "answered": entry is not None and entry.get("k") == "rs", "entry": entry,
            "posted": any(e.get("k") == "ask" and e.get("rq") == rq for e in log.all),
            "seconds": round(time.monotonic() - sent, 3)}


def set_rewrite(session, on: bool) -> None:
    r7_support.run_in_page(session, REWRITE.replace("ARG_STATE", json.dumps("on" if on else "off")))
