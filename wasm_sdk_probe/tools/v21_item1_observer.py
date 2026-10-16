#!/usr/bin/env python3
"""The item-1 observer snippet (ARMS.md S-2; ARMS-item1.md §2.2 (a)-(d)) and the D11a host shim.

SNIPPET is one `<script>` block, injected by S-1 AFTER v20's OBSERVER and before the page's module.  It
never edits v20's observer: it wraps `window.Worker` once more (v20's wrapper inside), and wraps the
instance's `postMessage` that v20 installed.  Everything it sees goes into its own DOM node
`#v21-i1` (Firefox evaluates the runner's scripts in a Marionette sandbox, so DOM, not globals):

  kd / kdp / ku / bi   keydown (capture: key, ctrl, meta, shift, alt, repeat, focus), the same keydown's
                       `defaultPrevented` after the page's sink listener (window, bubble), keyup, and the
                       sink's beforeinput inputType
  st                   a state-line change: pill state, #s-pending, #s-revision, #s-generation,
                       #s-checkpoint, #s-latency, #s-doc, #page-status (text, hidden)
  rq / rs              every request (op, action, requestId) and its response (ok, completion, code,
                       caret, revision, beforeRevision, changed, boundaryNoop, state.selection summary)
  ask7post / ask7      D7: 500 ms after a successful move-document-* response, ONE editorGetStateV2 is
                       posted (requestIds from 0x7E000000) and its answer logged
  askx                 the answer to ANY ask (v20's channel or D7's): caret, selection summary,
                       selectionType, selectionText (first 400 chars), revision
  frame                D10: one animation frame after #s-latency starts with a document move's label:
                       the desk/paper geometry and #page-status (text, hidden)

drain(session) reads the node in chunks and acknowledges (the v20 shape: no CDP frame over 1 MiB).
"""
from __future__ import annotations

import json

import run_e2_c_product_path as pp

SNIPPET = r"""<script>
(() => {
  const Inner = window.Worker;
  const log = [];
  let seq = 0, gens = 0, queued = false;
  const node = document.createElement("script");
  node.type = "application/json"; node.id = "v21-i1";
  const now = () => Math.round(performance.now() * 10) / 10;
  const flush = () => {
    queued = false;
    const cut = Number(node.dataset.cut ?? -1);
    while (log.length && log[0].s <= cut) log.shift();
    if (log.length > 8000) log.splice(0, log.length - 8000);
    node.textContent = JSON.stringify(log);
  };
  const put = (e) => { e.s = seq++; e.t = now(); log.push(e); if (!queued) { queued = true; setTimeout(flush, 0); } };
  const MOVE_LABELS = ["移到文件結尾", "移到文件開頭"];
  const ASK7 = 0x7E000000;
  let ask7n = 0;
  const selOf = (s) => (s && typeof s === "object")
    ? { collapsed: s.collapsed ?? null, n: Array.isArray(s.rectangles) ? s.rectangles.length : null, observed: s.observed ?? null }
    : null;
  function Wrapped(url, options) {
    const worker = new Inner(url, options);
    if (!(options && options.name === "oxoffice-document-engine")) return worker;
    const g = ++gens;
    const requests = new Map();
    let protocol = null, handle = null;
    const post = worker.postMessage;          // v20's instance wrapper (it calls the native post)
    worker.postMessage = (message, transfer) => {
      if (message && message.kind === "request") {
        if (message.protocolVersion !== undefined && message.requestId < 0x7E000000) protocol = message.protocolVersion;
        if (message.payload && message.payload.documentHandle !== undefined && message.requestId < 0x7E000000)
          handle = message.payload.documentHandle;
        const prior = requests.get(message.requestId) || {};
        requests.set(message.requestId, { ...prior, op: message.operation, action: message.payload?.action ?? null, t: now() });
        if (message.operation !== "paint" && message.operation !== "pageRectangles")
          put({ k: "rq", g, rq: message.requestId, op: message.operation, action: message.payload?.action ?? null,
                ask: message.requestId >= 0x7E000000 });
      }
      return post.call(worker, message, transfer);
    };
    worker.addEventListener("message", (event) => {
      const d = event.data;
      if (!d || d.kind !== "response") return;
      const rq = requests.get(d.requestId);
      if (!rq) return;
      requests.delete(d.requestId);
      const v = d.ok ? d.result : d.error;
      if (d.requestId >= 0x7E000000) {
        const r = (d.ok && v && typeof v === "object") ? v : {};
        put({ k: rq.ask7 ? "ask7" : "askx", g, rq: d.requestId, forRq: rq.forRq ?? null, tPosted: rq.t, ok: d.ok,
              code: d.ok ? null : (v && v.code) ?? null, caret: r.caret ?? null, sel: selOf(r.selection),
              selectionType: r.selectionType ?? null,
              selectionText: typeof r.selectionText === "string" ? r.selectionText.slice(0, 400) : null,
              rev: r.revision ?? null });
        return;
      }
      if (rq.op === "paint" || rq.op === "pageRectangles") return;
      const o = (v && typeof v === "object") ? v : {};
      put({ k: "rs", g, rq: d.requestId, op: rq.op, action: rq.action, tRq: rq.t, ok: d.ok,
            completion: o.completion ?? null, code: d.ok ? null : (o.code ?? null),
            message: d.ok ? null : String(o.message ?? "").slice(0, 200),
            caret: o.state?.caret ?? o.caret ?? null, sel: selOf(o.state?.selection), rev: o.revision ?? null,
            beforeRev: o.beforeRevision ?? null, changed: o.changed ?? null,
            waitedMs: o.boundaryNoop?.waitedMs ?? null,
            mergeStage: (o.mergeKey ?? o.details?.mergeKey)?.stage ?? null });
      if (d.ok && rq.op === "editorActionV2" && /^move-document-/.test(rq.action || "")) {
        const forRq = d.requestId;
        setTimeout(() => {
          const id = ASK7 + (ask7n++);
          requests.set(id, { op: "editorGetStateV2", ask7: true, forRq, t: now() });
          put({ k: "ask7post", g, rq: id, forRq });
          post.call(worker, { protocolVersion: protocol, kind: "request", requestId: id, operation: "editorGetStateV2",
                              payload: { documentHandle: handle } });
        }, 500);
      }
    });
    return worker;
  }
  Wrapped.prototype = Inner.prototype;
  window.Worker = Wrapped;

  const sinkId = (el) => el ? (el.id || el.tagName) : null;
  window.addEventListener("keydown", (e) => {
    e.__v21 = seq;
    put({ k: "kd", key: e.key, ctrl: e.ctrlKey, meta: e.metaKey, shift: e.shiftKey, alt: e.altKey, repeat: e.repeat,
          focus: sinkId(document.activeElement) });
  }, true);
  window.addEventListener("keydown", (e) => put({ k: "kdp", of: e.__v21 ?? null, key: e.key, prevented: e.defaultPrevented }));
  window.addEventListener("keyup", (e) => put({ k: "ku", key: e.key, ctrl: e.ctrlKey }), true);
  document.addEventListener("DOMContentLoaded", () => {
    document.head.appendChild(node); flush();
    const $ = (s) => document.querySelector(s);
    const sink = $("#sink");
    if (sink) sink.addEventListener("beforeinput", (e) => put({ k: "bi", type: e.inputType, data: e.data ?? null }), true);
    const read = () => {
      const pill = $("#state-pill"), ps = $("#page-status");
      return { state: pill ? pill.dataset.state : null, pending: $("#s-pending")?.textContent ?? null,
               rev: $("#s-revision")?.textContent ?? null, gen: $("#s-generation")?.textContent ?? null,
               checkpoint: $("#s-checkpoint")?.textContent ?? null, latency: $("#s-latency")?.textContent ?? null,
               doc: $("#s-doc")?.textContent ?? null, ps: ps ? ps.textContent : null, psHidden: ps ? ps.hidden : null };
    };
    const geometry = () => {
      const desk = $("#desk"), paper = $("#paper");
      if (!desk || !paper) return null;
      const d = desk.getBoundingClientRect(), p = paper.getBoundingClientRect();
      return { scrollTop: desk.scrollTop, clientHeight: desk.clientHeight, scrollHeight: desk.scrollHeight,
               deskTop: d.top, deskBottom: d.bottom, paperTop: p.top, paperBottom: p.bottom,
               paperHeight: p.height, paperWidth: p.width };
    };
    let last = "", lastLatency = null;
    const tick = () => {
      const r = read();
      const key = JSON.stringify(r);
      if (key === last) return;
      last = key;
      put({ k: "st", ...r });
      if (r.latency !== lastLatency) {
        lastLatency = r.latency;
        if (r.latency && MOVE_LABELS.some((label) => r.latency.startsWith(label)))
          requestAnimationFrame(() => { const ps = $("#page-status");
            put({ k: "frame", latency: r.latency, geo: geometry(), ps: ps ? ps.textContent : null, psHidden: ps ? ps.hidden : null }); });
      }
    };
    new MutationObserver(tick).observe(document.body, { attributes: true, childList: true, characterData: true, subtree: true });
    tick();
  });
})();
</script>
"""

READ_LEN = "(() => { const n = document.getElementById('v21-i1'); return n ? n.textContent.length : -1; })()"
READ_SLICE = "(() => { const n = document.getElementById('v21-i1'); return n ? n.textContent.slice(ARG_A, ARG_B) : null; })()"
CUT = "(() => {{ const n = document.getElementById('v21-i1'); if (n) n.dataset.cut = '{0}'; return true; }})()"
CHUNK = 400000


class Log:
    """The snippet's node, drained and kept whole (the v20 shape: chunked reads, an acknowledged cut)."""

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


def host_shim(fixture_url: str, name: str) -> str:
    """D11a (ARMS-item1.md §3 D11, ruling D-2 A): `globalThis.liteCoreHost` before the page's module.
    load() returns the fixture view-only; save() is counted; watchUnsaved keeps the page's own
    hasUnsavedWork, which the runner asks through the `v21-unsaved` event (answer in #v21-host)."""
    return ("<script>\n(() => {\n"
            "  const node = document.createElement('script'); node.type = 'application/json'; node.id = 'v21-host';\n"
            "  const state = { saves: 0, loads: 0, watch: false, unsaved: [] };\n"
            "  const write = () => { node.textContent = JSON.stringify(state); };\n"
            "  let ask = null;\n"
            "  globalThis.liteCoreHost = {\n"
            f"    async load() {{ state.loads += 1; write(); const r = await fetch({json.dumps(fixture_url)}, {{ cache: 'no-cache' }});\n"
            f"      return {{ bytes: await r.arrayBuffer(), name: {json.dumps(name)}, readOnly: true }}; }},\n"
            "    async save() { state.saves += 1; write(); return { ok: true }; },\n"
            "    watchUnsaved(fn) { ask = fn; state.watch = true; write(); },\n"
            "  };\n"
            "  document.documentElement.addEventListener('v21-unsaved', () => {\n"
            "    let value; try { value = ask ? ask() : null; } catch (error) { value = 'throw: ' + String(error); }\n"
            "    state.unsaved.push({ t: Math.round(performance.now()), value }); write(); });\n"
            "  document.addEventListener('DOMContentLoaded', () => { document.head.appendChild(node); write(); });\n"
            "})();\n</script>\n")


READ_HOST = "(() => { const n = document.getElementById('v21-host'); return n ? JSON.parse(n.textContent || 'null') : null; })()"
ASK_UNSAVED = "document.documentElement.dispatchEvent(new Event('v21-unsaved'));"
# D11b (ruling D-12 A): the page's own guardLeave answers a cancelable beforeunload; the answer goes to DOM.
BEFOREUNLOAD = ("(() => { const e = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(e);"
                " document.documentElement.dataset.v21Unsaved = String(e.defaultPrevented); })();")
READ_BEFOREUNLOAD = "(() => document.documentElement.dataset.v21Unsaved ?? null)()"
