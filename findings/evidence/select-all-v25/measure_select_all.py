#!/usr/bin/env python3
"""What select-all (action 21) does on v25 when its gesture is granted -- research measurement, NOT a gate check.

Work order `handoff/WORKORDER-v26-select-all.md`, deliverable 1, questions 2-3 (research note
`research/2026-10-29-select-all-route-on-v25.md`, part 1 answered question 1 by reading source).

HARNESS PATH, stated up front.  The shell client refuses `select-all` before any request
(`narrow-editor-v2-client.js` closed lists), so select-all is posted to the page's document worker DIRECTLY by
an observer in the HTML, with request ids >= 2,000,000,000; the SDK client ignores replies whose id it did not
issue (`document-sdk.js` `_handleMessage`), so the page never sees the reply -- but the engine's editor-state
events reach the page's session as they would for any action, so the page's own wash (drawOverlay) and the
page's later keys/buttons are the product's.  What the PAGE would do on Ctrl+A is not measured here: that path
does not exist yet (question 4, the spec).

Products (each a symlink mirror of dist/ with exactly the overrides named; identity checked file by file
before use, a product whose identity fails is not run):
  grant            dist/ as served (page 9cb6ea1f, generation 79, profile e2-editor-v25) + a SCRATCH
                   sdk-manifest.json whose `select-all` grants collapsed, range-single, range-cross
  grant-collapsed  the same with `select-all` granting collapsed only (research note detail 2: a second
                   select-all from a range needs both range bits)
  withheld         the manifest as shipped (`gestures: []`) -- control: the direct post must be refused
The scratch manifests keep `profile: "e2-editor-v25"` (the worker keys extend moves on that name); they exist
only in the mirror under wasm_sdk_probe/build/ and are deleted with it.  NOTHING UNDER dist/ IS WRITTEN.

Per run, fresh Chrome: open the fixture through the page's file input, attach to the document worker (CDP) and
record every engine JSON object it parses, click into the document (real mouse), harness-save the baseline,
read the document-start and document-end carets (harness move-document-start/-end, then back to start), then
the arm.  After the select-all: the reply, a later editorGetStateV2, getSelection (the engine's copy path, i.e.
what Ctrl+C would put on the clipboard), the wash rectangles the page drew (CanvasRenderingContext2D.fillRect
with the overlay's multiply/#b7d3f2 -- the draw calls, not pixels), the page's pill/toast/notice.

Arms:  look              select-all, record, save
       type              select-all, then the marker typed with REAL keys (page path), save
       backspace         select-all, then one REAL Backspace (page path), save
       delete-selection  select-all, then harness delete-selection, save
       bold              select-all, then a REAL click on the toolbar B (page path), save
       type-undo         select-all, type (real keys), then the page's undo button until the saved text
                         equals the baseline (at most 8), save after each
       partial-bold      CONTROL for the bold reading: the `partial` range, then the real B click -- only the
                         first paragraph may come back bold
       twice             select-all twice (the second from a range), getSelection after each
       table-cell        harness move-line-down into the first table row, then select-all three times
       geometric         2026-08-19's construction: instead of select-all, harness editorSelectRangeV2
                         (0,0)-(width-1,height-1).  On 08-19 (pre-ordered engine) it reported success and
                         selected nothing; shake-01 found it SELECTS on v25, so it is a reproduction attempt
                         and not the control.
       degenerate        POSITIVE CONTROL, "reported success, selected nothing" constructed: editorSelectRangeV2
                         (0,0)-(1,1), both ends in the top-left margin -- the predicate must not call it whole
       partial           POSITIVE CONTROL, a real range that is not the document: editorSelectRangeV2 from (0,0)
                         to the first line's middle at the right edge -- must not be called whole

  measure_select_all.py --out DIR [--plan full|shake|bold]

Added after run-01 (run-01 was produced without them; its report has no `bold` fields and no kept ODTs): the
saved documents are read for BOLD per paragraph (automatic paragraph style or bold span, resolved through
run_e2_c_product_path._styles_carrying), every run's final ODT is kept next to the report, and the
`partial-bold` arm and the `bold` plan exist.  run-01's `final.unchanged` compares TEXT only, so it says
nothing about whether bold was applied.
  measure_select_all.py --summarise REPORT          (re-derive the summary from a report; prints it)

--out must not exist.  Not a timing measurement: no desk gate.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "wasm_sdk_probe"
sys.path.insert(0, str(PROJECT / "tools"))
import run_e2_c_product_path as pp  # noqa: E402
import v21_input as real  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

_spec = importlib.util.spec_from_file_location("f1", ROOT / "findings/evidence/link-batch-v25/f1/diag_format_v25.py")
f1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(f1)

PROFILE = "e2-editor-v25"
ARCHIVE = PROJECT / "build/archive/e2-editor-v25-44cb15ea-worker-75557b22"
PAGE_SHA256 = "9cb6ea1f1d867c40284a917fcc89ec94175ec2ebf9fbd009334626f1e8685dd1"
MANIFEST_PATH = f"profiles/{PROFILE}/sdk-manifest.json"
BLANK = Path("/home/jiajun/Projects/Nextcloud_Apps/litecore/blank/en-US_zh-TW_A4.odt")
FIXTURES = {name: PROJECT / f"dist/e1-fixtures/{name}.odt"
            for name in ("list-contexts", "table-boundary", "frame-contexts", "endnote-frame", "frame-no-image")}
FIXTURES["blank"] = BLANK
GRANTS = {"grant": ["collapsed", "range-single", "range-cross"], "grant-collapsed": ["collapsed"], "withheld": None}
MARKER = "mkallq"
CLICK_AT = (0.30, 0.08)
HARNESS_ID = 2_000_000_000
NS = {"office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
      "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
      "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
      "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"}

OBSERVER = """<script>
(() => {
  const H = %d;
  const rec = window.__sa = {requests: [], responses: [], workers: [], raw: {}, wash: [], washTotal: 0, blobs: []};
  const snap = v => { try { return JSON.parse(JSON.stringify(v, (k, x) =>
    (x instanceof ArrayBuffer || ArrayBuffer.isView(x)) ? {bytes: x.byteLength} : x)); }
    catch (e) { return {unserialisable: String(e)}; } };
  const Native = window.Worker;
  window.Worker = class extends Native {
    constructor(url, options) { super(url, options); const w = rec.workers.push(this) - 1;
      this.addEventListener('message', ev => { const d = ev.data; if (d?.kind !== 'response') return;
        rec.responses.push({w, at: performance.now(), message: snap(d)});
        if (d.requestId >= H) rec.raw[d.requestId] = d; }); }
    postMessage(m, ...rest) { if (m?.kind === 'request')
      rec.requests.push({w: rec.workers.indexOf(this), at: performance.now(), message: snap(m)});
      return super.postMessage(m, ...rest); }
  };
  let next = H;
  rec.post = (operation, payload) => {
    const w = rec.workers.at(-1), requestId = next++;
    const pv = rec.requests.at(-1)?.message?.protocolVersion ?? 1;
    w.postMessage({protocolVersion: pv, kind: 'request', requestId, operation, payload});
    return requestId; };
  rec.reply = id => rec.raw[id] ? snap(rec.raw[id]) : null;
  rec.saved = id => { const b = rec.raw[id]?.result?.buffer; if (!b) return null; const u = new Uint8Array(b);
    let s = ''; for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode(...u.subarray(i, i + 8192));
    return btoa(s); };
  const fill = CanvasRenderingContext2D.prototype.fillRect;
  CanvasRenderingContext2D.prototype.fillRect = function (x, y, w, h) {
    if (this.globalCompositeOperation === 'multiply' && String(this.fillStyle).toLowerCase() === '#b7d3f2') {
      rec.washTotal += 1; rec.wash.push({i: rec.washTotal, t: performance.now(), x, y, w, h});
      if (rec.wash.length > 6000) rec.wash.splice(0, 3000); }
    return fill.call(this, x, y, w, h); };
  const create = URL.createObjectURL.bind(URL);
  URL.createObjectURL = blob => { if (blob instanceof Blob) rec.blobs.push(blob); return create(blob); };
  const click = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () { if (this.hasAttribute('download')) return; return click.call(this); };
})();
</script>""" % HARNESS_ID

RAW_INSTALL = """(() => {
  if (self.__saRaw) return 'already';
  const rec = self.__saRaw = []; const parse = JSON.parse; let n = 0;
  JSON.parse = function (text, reviver) {
    const v = parse.call(JSON, text, reviver);
    try {
      if (v && typeof v === 'object' && typeof v.type === 'string' && v.type !== 'tile') {
        const st = (v.state && typeof v.state === 'object') ? v.state : v; const s = st.selection;
        rec.push({n: n++, t: performance.now(), type: v.type, requestId: v.requestId ?? null,
          action: v.action ?? v.method ?? null, completion: v.completion ?? null, changed: v.changed ?? null,
          revision: v.revision ?? null, seqBefore: v.callbackSequenceBefore ?? null,
          seqAfter: v.callbackSequenceAfter ?? null, sourceSequence: st.sourceSequence ?? null,
          sel: s && typeof s === 'object' ? {observed: s.observed ?? null, collapsed: s.collapsed ?? null,
            rects: Array.isArray(s.rectangles) ? s.rectangles.length : null} : null});
        if (rec.length > 6000) rec.splice(0, 3000);
      }
    } catch (e) {}
    return v;
  };
  return 'installed';
})()"""

PAGE = """(() => ({pill: document.querySelector('#state-pill')?.dataset.state,
  latency: document.querySelector('#s-latency')?.textContent,
  toast: document.querySelector('#toast')?.textContent,
  revision: document.querySelector('#s-revision')?.textContent,
  notice: {show: document.querySelector('#notice')?.dataset.show ?? null,
           text: document.querySelector('#notice-text')?.textContent ?? null},
  shape: document.querySelector('#toolbar')?.dataset.selectionShape ?? null,
  canvas: {width: document.querySelector('#canvas')?.width, height: document.querySelector('#canvas')?.height},
  focus: document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : null,
  requests: window.__sa.requests.length, responses: window.__sa.responses.length,
  workers: window.__sa.workers.length, washTotal: window.__sa.washTotal}))()"""
OPEN_META = """(() => { const r = window.__sa, w = r.workers.length - 1;
  const q = r.requests.filter(e => e.w === w && e.message.operation === 'open').at(-1); if (!q) return null;
  const a = r.responses.find(e => e.w === w && e.message.requestId === q.message.requestId);
  const x = a?.message?.result || {};
  return {requestId: q.message.requestId, documentHandle: x.documentHandle, revision: x.revision,
          width: x.width, height: x.height}; })()"""


# ------------------------------------------------------------------ products

def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def scratch_manifest(grant: list[str] | None) -> bytes:
    shipped = (ARCHIVE / "sdk-manifest.json").read_bytes()
    if grant is None:
        return shipped
    manifest = json.loads(shipped)
    manifest["editorContract"]["actions"]["select-all"] = {
        "id": 21, "gestures": list(grant), "limits": ["scratch-measurement-not-shipped"]}
    return (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def overrides(product: str) -> dict[str, bytes]:
    html = common.inject((common.DIST / "e2-editor.html").read_text(encoding="utf-8"), [OBSERVER])
    out = {"e2-editor.html": html.encode("utf-8")}
    if GRANTS[product] is not None:
        out[MANIFEST_PATH] = scratch_manifest(GRANTS[product])
    return out


def identity(product: str, mirror: Path) -> dict:
    sums = dict(line.split()[::-1] for line in (ARCHIVE / "SHA256SUMS").read_text().splitlines() if line.strip())
    served = {f: sha256((mirror / "profiles" / PROFILE / f).read_bytes())
              for f in ("probe.wasm", "probe.js", "sdk-worker.js", "sdk-manifest.json")}
    shipped = json.loads((ARCHIVE / "sdk-manifest.json").read_bytes())
    mirrored = json.loads((mirror / MANIFEST_PATH).read_bytes())
    rest = lambda m: {**m, "editorContract": {**m["editorContract"], "actions": {
        k: v for k, v in m["editorContract"]["actions"].items() if k != "select-all"}}}
    page = (mirror / "e2-editor-app.js").read_bytes()
    checks = {
        "engineEqualsArchive": all(served[f] == sums.get(f) for f in ("probe.wasm", "probe.js", "sdk-worker.js")),
        "pageIsGeneration79": sha256(page) == PAGE_SHA256,
        "pagePointsAtProfile": f'workerUrl: "./profiles/{PROFILE}/sdk-worker.js"'.encode() in page,
        "shippedWithholdsSelectAll": shipped["editorContract"]["actions"]["select-all"]["gestures"] == [],
        "manifestDiffersOnlyInSelectAll": rest(mirrored) == rest(shipped),
        "selectAllGrant": mirrored["editorContract"]["actions"]["select-all"]["gestures"] == (GRANTS[product] or []),
    }
    if GRANTS[product] is None:
        checks["manifestIsShipped"] = served["sdk-manifest.json"] == sums.get("sdk-manifest.json")
    return {"product": product, "servedProfile": served, "page": sha256(page),
            "selectAll": mirrored["editorContract"]["actions"]["select-all"], "checks": checks,
            "ok": all(checks.values())}


# ------------------------------------------------------------------ the document's answer

def _text(node, skip=("note", "frame")) -> str:
    """Text of `node` without the subtrees whose local name is in `skip` (notes and frames are read apart)."""
    out = [node.text or ""]
    for child in node:
        if child.tag.split("}")[-1] not in skip:
            out.append(_text(child, skip))
        out.append(child.tail or "")
    return "".join(out)


def _bold_chars(node, bold: bool, spans: dict) -> tuple[int, int]:
    """(bold characters, all non-blank characters) under `node`; notes and frames skipped (read apart)."""
    def count(text: str) -> int:
        return len(text) if text.strip() else 0
    total = count(node.text or "")
    held = total if bold else 0
    for child in node:
        if child.tag.split("}")[-1] not in ("note", "frame"):
            inner = bold or (child.tag == f"{{{NS['text']}}}span"
                             and child.get(f"{{{NS['text']}}}style-name") in spans)
            a, b = _bold_chars(child, inner, spans)
            held, total = held + a, total + b
        tail = count(child.tail or "")
        total += tail
        held += tail if bold else 0
    return held, total


def bold_reading(content: str, body) -> list[dict]:
    """Per body paragraph (p/h, also in lists and table cells; NOT inside notes or frames): how many of its
    characters are bold by an AUTOMATIC style the save wrote -- the paragraph's own style or a span's.  Named
    styles (e.g. Heading_20_1, bold in styles.xml) do not count, so compare against the baseline."""
    spans, _ = pp._styles_carrying(content, "text", "set-bold")
    paragraphs, _ = pp._styles_carrying(content, "paragraph", "set-bold")
    hidden = {id(n) for apparatus in ("note", "frame")
              for top in body.iter(f"{{{NS['text' if apparatus == 'note' else 'draw']}}}{apparatus}")
              for n in top.iter()}
    out = []
    for node in body.iter():
        if node.tag not in (f"{{{NS['text']}}}p", f"{{{NS['text']}}}h") or id(node) in hidden:
            continue
        style = node.get(f"{{{NS['text']}}}style-name")
        held, total = _bold_chars(node, style in paragraphs, spans)
        if total:
            out.append({"text": _text(node)[:40], "style": style, "paragraphBold": style in paragraphs,
                        "bold": held, "chars": total})
    return out


def reading(raw: bytes) -> dict:
    content_raw = zipfile.ZipFile(io.BytesIO(raw)).read("content.xml")
    root = ET.fromstring(content_raw)
    body = root.find("office:body/office:text", NS)
    blocks = []
    for child in body if body is not None else []:
        tag = child.tag.split("}")[-1]
        if tag in ("p", "h"):
            blocks.append({"kind": tag, "text": _text(child)})
        elif tag == "list":
            for item in child.iter(f"{{{NS['text']}}}list-item"):
                for p in item:
                    if p.tag.split("}")[-1] in ("p", "h"):
                        blocks.append({"kind": "list-item", "text": _text(p)})
        elif tag == "table":
            cells = [" ".join(_text(p) for p in cell if p.tag.split("}")[-1] in ("p", "h"))
                     for cell in child.iter(f"{{{NS['table']}}}table-cell")]
            blocks.append({"kind": "table", "cells": cells})
    notes = [_text(n.find("text:note-body", NS), skip=("frame",)) if n.find("text:note-body", NS) is not None else ""
             for n in body.iter(f"{{{NS['text']}}}note")] if body is not None else []
    frames = len(list(body.iter(f"{{{NS['draw']}}}frame"))) if body is not None else 0
    anchors = []
    for block in blocks:
        for value in (block.get("cells") or [block.get("text")]):
            if value and value.strip():
                anchors.append(value.strip())
    bold = bold_reading(content_raw.decode("utf-8"), body) if body is not None else []
    return {"sha256": sha256(raw), "blocks": blocks, "notes": notes, "frames": frames, "anchors": anchors,
            "bold": bold}


def anchors_in_order(text: str, anchors: list[str]) -> dict:
    position, missing = 0, []
    for anchor in anchors:
        found = text.find(anchor, position)
        if found < 0:
            missing.append(anchor)
        else:
            position = found + len(anchor)
    return {"all": bool(anchors) and not missing, "missing": missing, "of": len(anchors)}


# ------------------------------------------------------------------ harness calls

def wait(session, predicate, limit):
    until, state = time.monotonic() + limit, None
    while time.monotonic() < until:
        state = evaluate(session, PAGE)
        if state and predicate(state):
            return state, True
        time.sleep(0.2)
    return state, False


def post(session, operation, payload, limit=30.0):
    rid = evaluate(session, f"window.__sa.post({json.dumps(operation)}, {json.dumps(payload)})")
    until = time.monotonic() + limit
    while time.monotonic() < until:
        reply = evaluate(session, f"window.__sa.reply({rid})")
        if reply is not None:
            return {"requestId": rid, "at": time.time(), **reply}
        time.sleep(0.1)
    return {"requestId": rid, "timeout": True}


def revision(session, doc):
    reply = post(session, "editorGetStateV2", {"documentHandle": doc["documentHandle"]})
    return (reply.get("result") or {}).get("revision"), reply


def action(session, doc, name):
    rev, _ = revision(session, doc)
    return post(session, "editorActionV2", {"documentHandle": doc["documentHandle"], "expectedRevision": rev,
                                            "action": name, "extendSelection": False, "enabled": False})


def harness_save(session, doc):
    reply = post(session, "save", {"documentHandle": doc["documentHandle"], "format": "odt"}, limit=60)
    b64 = evaluate(session, f"window.__sa.saved({reply['requestId']})") if reply.get("ok") else None
    if not b64:
        return {"reply": reply, "reading": None}
    raw = base64.b64decode(b64)
    return {"reply": {k: reply.get(k) for k in ("requestId", "ok", "error")}, "reading": reading(raw), "_bytes": raw}


def selection_of(state: dict | None) -> dict | None:
    s = (state or {}).get("selection")
    if not isinstance(s, dict):
        return None
    rects = s.get("rectangles") if isinstance(s.get("rectangles"), list) else []
    return {"observed": s.get("observed"), "collapsed": s.get("collapsed"), "start": s.get("start"),
            "end": s.get("end"), "rectangles": len(rects),
            "span": [min((r["y"] for r in rects), default=None),
                     max((r["y"] + r["height"] for r in rects), default=None)]}


def raw_since(session, mark):
    if not getattr(session, "_raw_sid", None):
        return None
    try:
        return f1.worker_eval(session, f"(self.__saRaw ?? []).filter(e => e.n >= {mark})")
    except Exception as error:  # noqa: BLE001
        return {"error": str(error)}


def raw_mark(session):
    if not getattr(session, "_raw_sid", None):
        return None
    try:
        return f1.worker_eval(session, "(self.__saRaw ?? []).at(-1)?.n ?? -1") + 1
    except Exception:  # noqa: BLE001
        return None


def observe(session, doc, label, send):
    """Send one selection request (a callable returning the reply); record everything the questions ask."""
    page_mark = evaluate(session, PAGE)
    wash_mark, rmark = page_mark["washTotal"], raw_mark(session)
    reply = send()
    time.sleep(1.2)
    state = post(session, "editorGetStateV2", {"documentHandle": doc["documentHandle"]})
    copy = post(session, "getSelection", {"documentHandle": doc["documentHandle"]})
    wash = evaluate(session, f"window.__sa.wash.filter(e => e.i > {wash_mark})")
    result = reply.get("result") or {}
    return {"label": label, "reply": {"ok": reply.get("ok"), "error": reply.get("error"),
                                      "completion": result.get("completion"), "changed": result.get("changed"),
                                      "revision": [result.get("beforeRevision"), result.get("revision")],
                                      "callbackSequence": [result.get("callbackSequenceBefore"),
                                                           result.get("callbackSequenceAfter")],
                                      "selection": selection_of(result.get("state"))},
            "state": {"ok": state.get("ok"), "sourceSequence": (state.get("result") or {}).get("sourceSequence"),
                      "selection": selection_of(state.get("result"))},
            "copy": {"ok": copy.get("ok"), "error": copy.get("error"),
                     "selectionType": (copy.get("result") or {}).get("selectionType"),
                     "text": (copy.get("result") or {}).get("text")},
            "wash": wash, "page": evaluate(session, PAGE), "raw": raw_since(session, rmark) if rmark is not None else None}


def page_rows(session, start):
    record = evaluate(session, "window.__sa")
    w = len(record["workers"]) - 1
    replies = {r["message"].get("requestId"): r["message"] for r in record["responses"] if r["w"] == w}
    out = []
    for q in record["requests"][start:]:
        m = q["message"]
        if q["w"] != w or m.get("requestId", 0) >= HARNESS_ID:
            continue
        reply = replies.get(m.get("requestId")) or {}
        error, result = reply.get("error") or {}, reply.get("result") or {}
        out.append({"operation": m.get("operation"), "action": (m.get("payload") or {}).get("action"),
                    "route": (m.get("payload") or {}).get("route"), "text": (m.get("payload") or {}).get("text"),
                    "replied": bool(reply), "ok": reply.get("ok"), "code": error.get("code"),
                    "message": error.get("message"), "revision": [result.get("beforeRevision"), result.get("revision")]})
    return out


def real_click_button(session, action_name):
    box = evaluate(session, pp.BUTTON_BOX.replace("ARG_SELECTOR", f'#toolbar button[data-action="{action_name}"]'))
    if not box:
        return False
    real.click(session, "chrome", box["x"], box["y"])
    return True


def settle_page(session, start, limit=30):
    def done(s):
        return s["requests"] > start and s["responses"] >= s["requests"] - 0 and s["pill"] in (
            "ready", "recoverable-error", "restart-required")
    state, ok = wait(session, done, limit)
    time.sleep(1.5)
    return evaluate(session, PAGE), ok


# ------------------------------------------------------------------ one run

def one(session, product, fixture, arm, base):
    out = {}
    navigate(session, base)
    _, ok = wait(session, lambda s: s["pill"] == "ready", 240)
    if not ok:
        return {"fatal": "page not ready"}
    if fixture != "list-contexts":
        workers = evaluate(session, PAGE)["workers"]
        raw = FIXTURES[fixture].read_bytes()
        evaluate(session, pp.OPEN_BYTES.replace("ARG_B64", base64.b64encode(raw).decode())
                 .replace("ARG_NAME", FIXTURES[fixture].name))
        _, ok = wait(session, lambda s: s["workers"] > workers and s["pill"] == "ready", 120)
        if not ok:
            return {"fatal": "fixture not opened"}
    time.sleep(1.5)
    sid, why = f1.attach_worker(session)
    session._raw_sid = sid
    out["rawInstall"] = f1.worker_eval(session, RAW_INSTALL) if sid else why
    doc = evaluate(session, OPEN_META)
    out["document"] = doc
    if not doc or doc.get("documentHandle") is None:
        out["fatal"] = "no open metadata"
        return out
    evaluate(session, real.SCROLL_TO_FRACTION.replace("ARG_F", repr(CLICK_AT[1])))
    time.sleep(0.25)
    rect = evaluate(session, real.PAPER_RECT)
    real.click(session, "chrome", rect["left"] + rect["width"] * CLICK_AT[0], rect["top"] + rect["height"] * CLICK_AT[1])
    _, out["clicked"] = wait(session, lambda s: "定位游標" in (s["latency"] or ""), 30)
    time.sleep(0.8)
    out["baseline"] = harness_save(session, doc)
    refs = {}
    for name in ("move-document-end", "move-document-start"):
        reply = action(session, doc, name)
        refs[name] = {"ok": reply.get("ok"), "error": reply.get("error"),
                      "caret": ((reply.get("result") or {}).get("state") or {}).get("caret")}
    out["references"] = refs
    time.sleep(0.5)
    evaluate(session, pp.CLEAR_TOAST)

    if arm in ("geometric", "degenerate", "partial", "partial-bold"):
        first = refs["move-document-start"]["caret"] or {}
        end = {"geometric": (int(doc["width"]) - 1, int(doc["height"]) - 1), "degenerate": (1, 1),
               "partial": (int(doc["width"]) - 1, int(first.get("y", 0)) + int(first.get("height", 0)) // 2)}[
            "partial" if arm == "partial-bold" else arm]
        coords = {"startXTwips": 0, "startYTwips": 0, "endXTwips": max(0, end[0]), "endYTwips": max(0, end[1])}
        out["presses"] = [observe(session, doc, arm, lambda: post(
            session, "editorSelectRangeV2", {"documentHandle": doc["documentHandle"], **coords}))]
        out["range"] = coords
    elif arm == "table-cell":
        reply = action(session, doc, "move-line-down")
        out["intoCell"] = {"ok": reply.get("ok"), "error": reply.get("error"),
                           "caret": ((reply.get("result") or {}).get("state") or {}).get("caret")}
        time.sleep(0.5)
        out["presses"] = [observe(session, doc, f"select-all-{n}", lambda: action(session, doc, "select-all"))
                          for n in (1, 2, 3)]
    else:
        out["presses"] = [observe(session, doc, "select-all-1", lambda: action(session, doc, "select-all"))]
        if arm == "twice":
            out["presses"].append(observe(session, doc, "select-all-2", lambda: action(session, doc, "select-all")))

    follow = {}
    if arm in ("type", "type-undo"):
        start = evaluate(session, PAGE)["requests"]
        for ch in MARKER:
            real.key(session, "chrome", ch)
            time.sleep(0.12)
        follow["page"], follow["settled"] = settle_page(session, start)
        follow["rows"] = page_rows(session, start)
    elif arm == "backspace":
        start = evaluate(session, PAGE)["requests"]
        real.key(session, "chrome", "Backspace")
        follow["page"], follow["settled"] = settle_page(session, start)
        follow["rows"] = page_rows(session, start)
    elif arm in ("bold", "partial-bold"):
        start = evaluate(session, PAGE)["requests"]
        follow["clicked"] = real_click_button(session, "set-bold")
        follow["page"], follow["settled"] = settle_page(session, start)
        follow["rows"] = page_rows(session, start)
    elif arm == "delete-selection":
        reply = action(session, doc, "delete-selection")
        result = reply.get("result") or {}
        follow["reply"] = {"ok": reply.get("ok"), "error": reply.get("error"), "completion": result.get("completion"),
                           "changed": result.get("changed"),
                           "revision": [result.get("beforeRevision"), result.get("revision")]}
        time.sleep(1.2)
        follow["page"] = evaluate(session, PAGE)
    out["follow"] = follow

    if arm == "type-undo":
        undos, baseline = [], (out["baseline"].get("reading") or {}).get("blocks")
        for n in range(1, 9):
            start = evaluate(session, PAGE)["requests"]
            clicked = real_click_button(session, "undo")
            page, settled = settle_page(session, start, 20)
            saved = harness_save(session, doc)
            blocks = (saved.get("reading") or {}).get("blocks")
            undos.append({"n": n, "clicked": clicked, "settled": settled, "page": page,
                          "rows": page_rows(session, start), "blocks": blocks,
                          "equalsBaseline": blocks == baseline})
            if blocks == baseline or not clicked:
                break
        out["undos"] = undos
    out["final"] = harness_save(session, doc)
    out["finalPage"] = evaluate(session, PAGE)
    return out


# ------------------------------------------------------------------ plan and summary

def plan(kind: str) -> list[tuple[str, str, str]]:
    if kind == "bold":
        return [("grant", fixture, "bold") for fixture in FIXTURES] + [
            ("grant", "list-contexts", "partial-bold"), ("grant", "table-boundary", "partial-bold")]
    if kind == "shake":
        return [("grant", "list-contexts", "degenerate"), ("grant", "list-contexts", "partial"),
                ("grant", "table-boundary", "type-undo")]
    runs = []
    for fixture in FIXTURES:
        for arm in ("look", "type", "backspace", "delete-selection", "bold", "type-undo"):
            runs.append(("grant", fixture, arm))
    runs += [("grant", "list-contexts", "twice"), ("grant", "table-boundary", "twice"),
             ("grant", "table-boundary", "table-cell"), ("grant", "frame-contexts", "table-cell"),
             ("grant", "list-contexts", "geometric"), ("grant", "table-boundary", "geometric"),
             ("grant", "list-contexts", "degenerate"), ("grant", "list-contexts", "partial"),
             ("grant-collapsed", "list-contexts", "twice"), ("withheld", "list-contexts", "look")]
    return runs


def press_summary(press: dict, anchors: list[str], notes: list[str]) -> dict:
    reply, copy = press.get("reply") or {}, press.get("copy") or {}
    text = copy.get("text") or ""
    order = anchors_in_order(text, anchors)
    wash = press.get("wash") or []
    canvas = (press.get("page") or {}).get("canvas") or {}
    rs, ss = reply.get("selection") or {}, (press.get("state") or {}).get("selection") or {}
    whole = (reply.get("ok") is True and rs.get("collapsed") is False and order["all"] and bool(wash))
    return {"label": press.get("label"), "ok": reply.get("ok"),
            "code": (reply.get("error") or {}).get("code"), "completion": reply.get("completion"),
            "changed": reply.get("changed"), "revision": reply.get("revision"),
            "replyCollapsed": rs.get("collapsed"), "replyRects": rs.get("rectangles"),
            "stateCollapsed": ss.get("collapsed"), "stateRects": ss.get("rectangles"),
            "replyEqualsLaterState": bool(rs) and rs == ss,
            "copyType": copy.get("selectionType"), "copyChars": len(text), "anchors": order,
            "notesInCopy": [bool(n.strip()) and n.strip() in text for n in notes],
            "washDraws": len(wash), "washMaxRects": max((sum(1 for w in wash if abs(w["t"] - x["t"]) < 3) for x in wash),
                                                       default=0),
            "canvas": canvas, "pill": (press.get("page") or {}).get("pill"),
            "notice": ((press.get("page") or {}).get("notice") or {}).get("show"),
            "whole": whole}


def summarise(report: dict) -> list[dict]:
    rows = []
    for run in report["runs"]:
        base = ((run.get("baseline") or {}).get("reading")) or {}
        final = ((run.get("final") or {}).get("reading")) or {}
        row = {"product": run["product"], "fixture": run["fixture"], "arm": run["arm"], "fatal": bool(run.get("fatal"))}
        if run.get("fatal"):
            row["why"] = run["fatal"].strip().splitlines()[-1]
            rows.append(row)
            continue
        row["presses"] = [press_summary(p, base.get("anchors") or [], base.get("notes") or [])
                          for p in run.get("presses") or []]
        follow = run.get("follow") or {}
        row["followRows"] = [{k: r.get(k) for k in ("operation", "action", "route", "ok", "code")}
                             for r in follow.get("rows") or []]
        if follow.get("reply"):
            row["followReply"] = {k: follow["reply"].get(k) for k in ("ok", "completion", "changed", "revision")}
            row["followReply"]["code"] = (follow["reply"].get("error") or {}).get("code")
        row["followPill"] = (follow.get("page") or {}).get("pill")
        row["followNotice"] = ((follow.get("page") or {}).get("notice") or {}).get("show")
        row["followToast"] = ((follow.get("page") or {}).get("toast") or "")[:120]
        row["baseline"] = {"blocks": len(base.get("blocks") or []), "notes": len(base.get("notes") or []),
                           "frames": base.get("frames")}
        row["final"] = {"blocks": final.get("blocks"), "notes": final.get("notes"), "frames": final.get("frames"),
                        "unchanged": final.get("blocks") == base.get("blocks") and final.get("notes") == base.get("notes")}
        if "bold" in final:
            row["final"]["bold"] = [[b["text"][:24], b["bold"], b["chars"]] for b in final["bold"]]
            row["baselineBold"] = [[b["text"][:24], b["bold"], b["chars"]] for b in base.get("bold") or []]
            row["allBold"] = bool(final["bold"]) and all(b["bold"] == b["chars"] for b in final["bold"])
        if run.get("undos") is not None:
            row["undosToBaseline"] = next((u["n"] for u in run["undos"] if u["equalsBaseline"]), None)
            row["undoRows"] = [[{k: r.get(k) for k in ("operation", "ok", "code")} for r in u["rows"]]
                               for u in run["undos"]]
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", choices=("full", "shake", "bold"), default="full")
    parser.add_argument("--summarise", type=Path)
    args = parser.parse_args()
    if args.summarise:
        print(json.dumps(summarise(json.loads(args.summarise.read_text())), indent=1, ensure_ascii=False))
        return
    if not args.out:
        raise SystemExit("--out is required")
    args.out.mkdir(parents=True, exist_ok=False)
    runs = plan(args.plan)
    report = {"argv": sys.argv, "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "fixtures": {k: {"path": str(v), "sha256": sha256(v.read_bytes())} for k, v in FIXTURES.items()},
              "identities": {}, "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="select-all-v25-", dir=PROJECT / "build"))
    try:
        with common.browser_lock("measure_select_all_v25"):
            report["preRun"] = common.pre_run_checks()
            for product in GRANTS:
                mine = [r for r in runs if r[0] == product]
                if not mine:
                    continue
                target = scratch / product
                pp.build_mirror(common.DIST, target, overrides(product))
                report["identities"][product] = identity(product, target)
                if not report["identities"][product]["ok"]:
                    print(product, "identity FAILED", report["identities"][product]["checks"], file=sys.stderr)
                    continue
                with common.served(target) as base:
                    for _, fixture, arm in mine:
                        run, session = {"product": product, "fixture": fixture, "arm": arm}, None
                        try:
                            session = common.open_browser("chrome")
                            run.update(one(session, product, fixture, arm, base))
                        except Exception:  # noqa: BLE001
                            run["fatal"] = traceback.format_exc()
                        finally:
                            if session is not None:
                                run["close"] = common.close_browser(session)
                        for key in ("baseline", "final"):
                            raw = (run.get(key) or {}).pop("_bytes", None)
                            if raw is not None and key == "final":
                                name = f"{len(report['runs']) + 1:02d}-{product}-{fixture}-{arm}.odt"
                                (args.out / name).write_bytes(raw)
                                run[key]["kept"] = name
                        for undo in run.get("undos") or []:
                            undo.pop("_bytes", None)
                        report["runs"].append(run)
                        (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
                        p = (run.get("presses") or [{}])[0].get("reply") or {}
                        print(product, fixture, arm, "fatal" if run.get("fatal") else
                              f"ok={p.get('ok')} sel={p.get('selection')}", file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["summary"] = summarise(report)
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
