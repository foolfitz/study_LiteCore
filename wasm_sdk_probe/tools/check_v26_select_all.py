#!/usr/bin/env python3
"""S1 (SPEC-M3-select-all-v26 5.4): Ctrl/Cmd+A on the user's path -- the PAGE sends select-all on a real key.

Derived from findings/evidence/select-all-v25/measure_select_all.py (imported for its document reading and its
harness reads; not edited).  There the harness POSTED select-all; here every input is real (tools/v21_input.py:
Chrome CDP, Firefox WebDriver actions) and the harness only READS -- getSelection (the engine's copy path),
editorGetStateV2, save.  Reference carets come from real Ctrl+End / Ctrl+Home.

Products: tools/v80_f_products.py (after, before, unoffered, fake, v25-worker), identity checked per mirror.
Documents: measure_select_all's six (list-contexts, table-boundary, frame-contexts, endnote-frame, frame-no-image,
the host's blank template) and a three-page document (run_e2_c_product_path.open_long_document).

Every arm is judged by a CLAUSE TABLE (CLAUSES below: id -> predicate over the recorded run -> a mutation of the
record that must make the predicate false).  `--self-test REPORT` applies each clause's mutation to a run that
holds it and requires the verdict to turn red; a clause id with no mutation is itself red (the table is the
population: spec 5.4, tool-closed).  Counterexamples (before, unoffered, fake, v25-worker) have clause tables of
their own: what makes them red FOR THE RIGHT REASON.

Observer (in the HTML): every Worker request/reply; the harness post/reply/save API measure_select_all uses; the
overlay's wash draws; a document-level keydown listener (bubble phase) recording whether Ctrl/Cmd+A was
default-prevented; the page's `beforeunload` listener, kept so `unsaved()` can ask it whether it would guard a
leave -- the page's own hasUnsavedWork(), as the user meets it.

  check_v26_select_all.py --out DIR [--plan full|shake] [--browsers chrome,firefox]
  check_v26_select_all.py --self-test REPORT

Verdict S1_HOLDS iff every identity holds, every planned run exists, every after run PASSes every clause, and every
counterexample run is red for the right reason.  --out must not exist.  Nothing under dist/ is written.
Not a timing measurement: no desk gate.
"""
from __future__ import annotations

import argparse
import base64
import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import traceback

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
sys.path.insert(0, str(PROJECT / "tools"))
import run_e2_c_product_path as pp  # noqa: E402
import v21_input as real  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v80_f_products as products  # noqa: E402
from r7_support import evaluate  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "measure_select_all", ROOT / "findings/evidence/select-all-v25/measure_select_all.py")
msa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(msa)

MARKER = "mkallq"
CLICK_AT = (0.30, 0.08)
LONG = "long-3"
TEXT_FIXTURES = ("list-contexts", "table-boundary", "endnote-frame")
FRAME_FIXTURES = ("frame-contexts", "frame-no-image")
NOTHING, CLICK_FIRST, COPIED = "沒有選到任何內容", "請先點一下文件", "已複製"

OBSERVER = """<script>
(() => {
  const H = 2000000000;
  const rec = window.__sa = {requests: [], responses: [], workers: [], raw: {}, wash: [], washTotal: 0, keys: [],
                             unload: null};
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
      rec.washTotal += 1; rec.wash.push({i: rec.washTotal, t: performance.now()});
      if (rec.wash.length > 6000) rec.wash.splice(0, 3000); }
    return fill.call(this, x, y, w, h); };
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && typeof e.key === 'string' && e.key.toLowerCase() === 'a')
      rec.keys.push({prevented: e.defaultPrevented, repeat: e.repeat, at: performance.now()});
  });
  const add = window.addEventListener.bind(window);
  window.addEventListener = function (type, fn, opts) { if (type === 'beforeunload') rec.unload = fn; return add(type, fn, opts); };
  rec.unsaved = () => { if (!rec.unload) return null; let guarded = false;
    rec.unload({preventDefault() { guarded = true; }, set returnValue(v) {}}); return guarded; };
  const click = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () { if (this.hasAttribute('download')) return; return click.call(this); };
})();
</script>"""

PAGE = """(() => ({pill: document.querySelector('#state-pill')?.dataset.state,
  latency: document.querySelector('#s-latency')?.textContent,
  toast: document.querySelector('#toast')?.textContent,
  toastBad: document.querySelector('#toast')?.classList.contains('bad') ?? null,
  notice: {show: document.querySelector('#notice')?.dataset.show ?? null,
           text: document.querySelector('#notice-text')?.textContent ?? null},
  shape: document.querySelector('#toolbar')?.dataset.selectionShape ?? null,
  unreadable: document.querySelector('#toolbar')?.dataset.selectionUnreadable ?? null,
  requests: window.__sa.requests.length, responses: window.__sa.responses.length,
  workers: window.__sa.workers.length, washTotal: window.__sa.washTotal, keys: window.__sa.keys.length,
  unsaved: window.__sa.unsaved(), fakeRewrites: window.__fakeRewrites ?? 0}))()"""
CLEAR_TOAST = "(() => { const t = document.querySelector('#toast'); if (t) { t.textContent = ''; t.classList.remove('bad'); } })()"


# ------------------------------------------------------------------ helpers

def page(session):
    return evaluate(session, PAGE)


def wait(session, predicate, limit):
    until, state = time.monotonic() + limit, None
    while time.monotonic() < until:
        state = page(session)
        if state and predicate(state):
            return state, True
        time.sleep(0.2)
    return state, False


def page_actions(session, start, action=None):
    """The page's own editorActionV2 requests from index `start` (current worker), each with its reply."""
    record = evaluate(session, "window.__sa")
    w = len(record["workers"]) - 1
    replies = {r["message"].get("requestId"): r["message"] for r in record["responses"] if r["w"] == w}
    out = []
    for q in record["requests"][start:]:
        m = q["message"]
        if q["w"] != w or m.get("requestId", 0) >= msa.HARNESS_ID:
            continue
        payload = m.get("payload") or {}
        if action is not None and payload.get("action") != action:
            continue
        reply = replies.get(m.get("requestId"))
        out.append({"operation": m.get("operation"), "action": payload.get("action"), "route": payload.get("route"),
                    "extend": payload.get("extendSelection"), "replied": reply is not None,
                    "ok": (reply or {}).get("ok"), "code": ((reply or {}).get("error") or {}).get("code"),
                    "result": (reply or {}).get("result")})
    return out


def press(session, browser, key, mods=()):
    real.key(session, browser, key, mods)


def settle(session, start, limit=30):
    def done(s):
        return s["requests"] > start and s["responses"] >= s["requests"] and s["pill"] in (
            "ready", "recoverable-error", "restart-required")
    _, ok = wait(session, done, limit)
    time.sleep(1.2)
    return page(session), ok


def reference(session, browser, doc, mods):
    start = page(session)["requests"]
    press(session, browser, "End", mods)
    settle(session, start, 20)
    end = (page_actions(session, start, "move-document-end") or [{}])[-1]
    start = page(session)["requests"]
    press(session, browser, "Home", mods)
    settle(session, start, 20)
    begin = (page_actions(session, start, "move-document-start") or [{}])[-1]
    caret = lambda r: ((r.get("result") or {}).get("state") or {}).get("caret")
    return {"start": caret(begin), "end": caret(end), "startOk": begin.get("ok"), "endOk": end.get("ok")}


def read_selection(session, doc):
    state = msa.post(session, "editorGetStateV2", {"documentHandle": doc["documentHandle"]})
    copy_ = msa.post(session, "getSelection", {"documentHandle": doc["documentHandle"]})
    return {"state": msa.selection_of(state.get("result")),
            "copyType": (copy_.get("result") or {}).get("selectionType"),
            "copyText": (copy_.get("result") or {}).get("text") or ""}


def select_all(session, browser, doc, mods=("ctrl",)):
    before = page(session)
    start, wash0, keys0 = before["requests"], before["washTotal"], before["keys"]
    evaluate(session, CLEAR_TOAST)
    press(session, browser, "a", mods)
    _, ok = wait(session, lambda s: s["responses"] >= s["requests"] and s["requests"] > start, 15)
    time.sleep(1.2)
    after = page(session)
    sent = page_actions(session, start, "select-all")
    keys = evaluate(session, f"window.__sa.keys.slice({keys0})")
    return {"sent": sent, "page": after, "washDraws": after["washTotal"] - wash0, "keys": keys,
            "settled": ok, **read_selection(session, doc)}


# ------------------------------------------------------------------ one run

def open_doc(session, fixture):
    workers = page(session)["workers"]
    if fixture == LONG:
        pp.open_long_document(session, 3, "long-3.odt")
    elif fixture != "list-contexts":
        raw = msa.FIXTURES[fixture].read_bytes()
        evaluate(session, pp.OPEN_BYTES.replace("ARG_B64", base64.b64encode(raw).decode())
                 .replace("ARG_NAME", msa.FIXTURES[fixture].name))
    if fixture != "list-contexts":
        _, ok = wait(session, lambda s: s["workers"] > workers and s["pill"] == "ready", 300)
        if not ok:
            return False
    time.sleep(1.5)
    return True


def one(session, browser, product, fixture, arm, base, port):
    out = {}
    if arm == "copy" and browser == "chrome":
        session.call("Browser.grantPermissions", {"origin": f"http://127.0.0.1:{port}",
                                                  "permissions": ["clipboardReadWrite", "clipboardSanitizedWrite"]})
        session.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
    navigate(session, base)
    _, ok = wait(session, lambda s: s["pill"] == "ready", 240)
    if not ok or not open_doc(session, fixture):
        return {"fatal": "document not ready"}
    doc = evaluate(session, msa.OPEN_META)
    out["document"] = doc
    if not doc or doc.get("documentHandle") is None:
        return {**out, "fatal": "no open metadata"}
    out["baseline"] = msa.harness_save(session, doc)
    out["baseline"].pop("_bytes", None)
    if arm == "unobserved":
        evaluate(session, "document.querySelector('#sink').focus()")
        out["unsavedBefore"] = page(session)["unsaved"]
        out["press"] = select_all(session, browser, doc)
    else:
        evaluate(session, real.SCROLL_TO_FRACTION.replace("ARG_F", repr(CLICK_AT[1])))
        time.sleep(0.25)
        rect = evaluate(session, real.PAPER_RECT)
        real.click(session, browser, rect["left"] + rect["width"] * CLICK_AT[0], rect["top"] + rect["height"] * CLICK_AT[1])
        _, out["clicked"] = wait(session, lambda s: "定位游標" in (s["latency"] or ""), 30)
        time.sleep(0.8)
        out["unsavedBefore"] = page(session)["unsaved"]
        if arm != "extend":
            out["reference"] = reference(session, browser, doc, ("ctrl",))
        if arm == "extend":
            start = page(session)["requests"]
            press(session, browser, "ArrowDown", ("shift",))
            settle(session, start, 20)
            out["extend"] = {"sent": page_actions(session, start), **read_selection(session, doc)}
        elif arm == "table-cell":
            start = page(session)["requests"]
            press(session, browser, "ArrowDown")
            settle(session, start, 20)
            out["intoCell"] = page_actions(session, start)
            out["presses"] = [select_all(session, browser, doc) for _ in range(3)]
            if fixture == "frame-contexts":
                start = page(session)["requests"]
                press(session, browser, "Backspace")
                settle(session, start)
        else:
            out["press"] = select_all(session, browser, doc, ("meta",) if arm == "mac" else ("ctrl",))
    follow = {}
    if arm in ("type", "undo"):
        start = page(session)["requests"]
        for ch in MARKER:
            press(session, browser, ch)
            time.sleep(0.12)
        follow["page"], follow["settled"] = settle(session, start)
        follow["rows"] = page_actions(session, start)
    elif arm == "backspace":
        start = page(session)["requests"]
        press(session, browser, "Backspace")
        follow["page"], follow["settled"] = settle(session, start)
        follow["rows"] = page_actions(session, start)
    elif arm == "bold":
        start = page(session)["requests"]
        press(session, browser, "b", ("ctrl",))
        follow["page"], follow["settled"] = settle(session, start)
        follow["rows"] = page_actions(session, start)
    elif arm == "enter":
        start = page(session)["requests"]
        press(session, browser, "Enter")
        follow["page"], follow["settled"] = settle(session, start, 20)
        follow["rows"] = page_actions(session, start)
    elif arm == "copy":
        evaluate(session, CLEAR_TOAST)
        press(session, browser, "c", ("ctrl",))
        time.sleep(2.0)
        follow["page"] = page(session)
        try:
            follow["clipboard"] = evaluate(session, "navigator.clipboard.readText()")
        except Exception as error:  # noqa: BLE001
            follow["clipboard"] = None
            follow["clipboardError"] = f"{type(error).__name__}: {error}"
    out["follow"] = follow
    if arm == "undo":
        base_blocks = (out["baseline"].get("reading") or {}).get("blocks")
        undos = []
        for n in (1, 2):
            start = page(session)["requests"]
            press(session, browser, "z", ("ctrl",))
            settle(session, start, 20)
            saved = msa.harness_save(session, doc)
            blocks = (saved.get("reading") or {}).get("blocks")
            undos.append({"n": n, "equalsBaseline": blocks == base_blocks})
            if blocks == base_blocks:
                break
        out["undos"] = undos
    final = msa.harness_save(session, doc)
    final.pop("_bytes", None)
    out["final"] = final
    out["finalPage"] = page(session)
    return out


# ------------------------------------------------------------------ clauses

def _xy(rect):
    return (rect or {}).get("x"), (rect or {}).get("y")


def _blocks(run, key):
    return ((run.get(key) or {}).get("reading") or {}).get("blocks")


def _reply_sel(p):
    sent = (p or {}).get("sent") or []
    return (((sent[-1] if sent else {}).get("result") or {}).get("state") or {}).get("selection") or {}


def _whole(run, p):
    """The document's ends and content, for the fixture class."""
    fixture = run["fixture"]
    ref = run.get("reference") or {}
    sel = _reply_sel(p)
    ends = _xy(sel.get("start")) == _xy(ref.get("start")) and _xy(sel.get("end")) == _xy(ref.get("end")) \
        and None not in _xy(ref.get("start"))
    if fixture in FRAME_FIXTURES:
        content = p.get("copyType") == "complex"
    else:
        anchors = ((run.get("baseline") or {}).get("reading") or {}).get("anchors") or []
        content = msa.anchors_in_order(p.get("copyText") or "", anchors)["all"]
    return ends and content


def _set(path_fn, value):
    def mutate(run):
        holder, key = path_fn(run)
        holder[key] = value
    return mutate


SELECT = [  # an after `select` / `mac` run on a document with text
    ("S.one-request", lambda r: len(r["press"]["sent"]) == 1 and r["press"]["sent"][0]["replied"],
     lambda r: r["press"]["sent"].append(dict(r["press"]["sent"][0]))),
    ("S.reply-ok", lambda r: r["press"]["sent"][0]["ok"] is True,
     _set(lambda r: (r["press"]["sent"][0], "ok"), False)),
    ("S.range", lambda r: _reply_sel(r["press"]).get("collapsed") is False,
     _set(lambda r: (r["press"]["sent"][0]["result"]["state"]["selection"], "collapsed"), True)),
    ("S.whole", lambda r: _whole(r, r["press"]),
     _set(lambda r: (r["press"]["sent"][0]["result"]["state"]["selection"], "end"), {"x": -1, "y": -1})),
    ("S.shape", lambda r: r["press"]["page"]["shape"] not in (None, "collapsed"),
     _set(lambda r: (r["press"]["page"], "shape"), "collapsed")),
    ("S.wash", lambda r: r["press"]["washDraws"] > 0, _set(lambda r: (r["press"], "washDraws"), 0)),
    ("S.prevented", lambda r: bool(r["press"]["keys"]) and r["press"]["keys"][0]["prevented"] is True,
     _set(lambda r: (r["press"]["keys"][0], "prevented"), False)),
    ("S.ready", lambda r: r["press"]["page"]["pill"] == "ready", _set(lambda r: (r["press"]["page"], "pill"), "busy")),
    ("S.no-notice", lambda r: r["press"]["page"]["notice"]["show"] != "1",
     _set(lambda r: (r["press"]["page"]["notice"], "show"), "1")),
    ("S.no-nothing-toast", lambda r: NOTHING not in (r["press"]["page"]["toast"] or ""),
     _set(lambda r: (r["press"]["page"], "toast"), NOTHING)),
    ("S.clean", lambda r: r.get("unsavedBefore") is False and r["press"]["page"]["unsaved"] is False,
     _set(lambda r: (r["press"]["page"], "unsaved"), True)),
]
BLANK_SELECT = [
    ("B.one-request", SELECT[0][1], SELECT[0][2]),
    ("B.reply-ok", SELECT[1][1], SELECT[1][2]),
    ("B.collapsed", lambda r: _reply_sel(r["press"]).get("collapsed") is True,
     _set(lambda r: (r["press"]["sent"][0]["result"]["state"]["selection"], "collapsed"), False)),
    ("B.nothing-toast", lambda r: NOTHING in (r["press"]["page"]["toast"] or ""),
     _set(lambda r: (r["press"]["page"], "toast"), "")),
    ("B.ready", SELECT[7][1], SELECT[7][2]),
    ("B.clean", SELECT[10][1], SELECT[10][2]),
]


def _rows(r, operation=None, action=None):
    return [x for x in (r.get("follow") or {}).get("rows") or []
            if (operation is None or x["operation"] == operation) and (action is None or x.get("action") == action)]


FOLLOW = {
    "type": [("T.inserts-ok", lambda r: bool(_rows(r, "insertText")) and all(x["ok"] is True for x in _rows(r, "insertText")),
              lambda r: _rows(r, "insertText")[0].__setitem__("ok", False)),
             ("T.saved-marker-only", lambda r: _blocks(r, "final") is not None and len(_blocks(r, "final")) == 1
              and (_blocks(r, "final")[0].get("text") or "") == MARKER,
              lambda r: r["final"]["reading"]["blocks"].append({"kind": "p", "text": "x"}))],
    "backspace": [("K.sent", lambda r: [x["action"] for x in _rows(r, "editorActionV2")]
                   == (["delete-backward"] if r["fixture"] == "blank" else ["delete-selection"])
                   and all(x["ok"] is True for x in _rows(r, "editorActionV2")),
                   lambda r: _rows(r, "editorActionV2")[0].__setitem__("ok", False)),
                  ("K.saved", lambda r: (_blocks(r, "final") == _blocks(r, "baseline")) if r["fixture"] == "blank"
                   else (_blocks(r, "final") is not None and len(_blocks(r, "final")) == 1
                         and not (_blocks(r, "final")[0].get("text") or "").strip()),
                   lambda r: r["final"]["reading"]["blocks"].append({"kind": "p", "text": "left over"}))],
    "bold": [("D.all-bold", lambda r: r["fixture"] == "blank" or (
                bool(((r["final"].get("reading") or {}).get("bold")))
                and all(b["bold"] == b["chars"] for b in r["final"]["reading"]["bold"])),
              lambda r: r["final"]["reading"]["bold"].__setitem__(0, {**r["final"]["reading"]["bold"][0], "bold": 0}))],
    "undo": [("U.restored", lambda r: any(u["equalsBaseline"] for u in r.get("undos") or [])
              and len(r["undos"]) <= (1 if r["fixture"] == "blank" else 2),
              lambda r: [u.__setitem__("equalsBaseline", False) for u in r["undos"]])],
    "copy": [("C.toast", lambda r: (COPIED in (r["follow"]["page"]["toast"] or "")) == (r["fixture"] not in FRAME_FIXTURES),
              _set(lambda r: (r["follow"]["page"], "toast"), "")),
             ("C.content", lambda r: (msa.anchors_in_order(r["follow"].get("clipboard") or "",
                                                           r["baseline"]["reading"]["anchors"])["all"])
              if r["fixture"] not in FRAME_FIXTURES else _blocks(r, "final") == _blocks(r, "baseline"),
              lambda r: (r["follow"].__setitem__("clipboard", "") if r["fixture"] not in FRAME_FIXTURES
                         else r["final"]["reading"]["blocks"].append({"kind": "p", "text": "x"})))],
    "enter": [("E.unchanged", lambda r: _blocks(r, "final") == _blocks(r, "baseline"),
               lambda r: r["final"]["reading"]["blocks"].append({"kind": "p", "text": ""})),
              ("E.ready", lambda r: r["follow"]["page"]["pill"] == "ready",
               _set(lambda r: (r["follow"]["page"], "pill"), "recoverable-error")),
              ("E.no-notice", lambda r: r["follow"]["page"]["notice"]["show"] != "1",
               _set(lambda r: (r["follow"]["page"]["notice"], "show"), "1"))],
}


def _toast_count_ok(r):
    """Append 1 (finding 175): the copy toast is 「已複製 N 字」 and N is the clipboard text's code-point count."""
    if r["fixture"] in FRAME_FIXTURES:
        return True   # no success toast there; C.toast judges that a failure is said instead
    match = re.fullmatch(r"已複製 (\d+) 字", r["follow"]["page"]["toast"] or "")
    return bool(match) and int(match.group(1)) == len(r["follow"].get("clipboard") or "")


def _bump_toast_count(r):
    found = re.search(r"\d+", r["follow"]["page"]["toast"] or "")
    r["follow"]["page"]["toast"] = f"已複製 {int(found.group(0)) + 1 if found else 1} 字"


FOLLOW["copy"].append(("C.count", _toast_count_ok, _bump_toast_count))


def _lengths(r):
    return [len(p.get("copyText") or "") for p in r["presses"]]


def _rects(r):
    return [_reply_sel(p).get("rectangles") for p in r["presses"]]


TABLE_CELL = [
    ("TC.three-ok", lambda r: len(r["presses"]) == 3 and all(len(p["sent"]) == 1 and p["sent"][0]["ok"] is True
                                                             for p in r["presses"]),
     lambda r: r["presses"][1]["sent"][0].__setitem__("ok", False)),
    ("TC.grows", lambda r: (all(a < b for a, b in zip(_lengths(r), _lengths(r)[1:])) if r["fixture"] == "table-boundary"
                            else all(len(a or []) <= len(b or []) for a, b in zip(_rects(r), _rects(r)[1:]))),
     lambda r: (r["presses"][2].__setitem__("copyText", "") if r["fixture"] == "table-boundary"
                else r["presses"][2]["sent"][0]["result"]["state"]["selection"].__setitem__("rectangles", []))),
    ("TC.shapes", lambda r: all(p["page"]["shape"] not in (None, "collapsed") for p in r["presses"]),
     _set(lambda r: (r["presses"][0]["page"], "shape"), "collapsed")),
    ("TC.third", lambda r: (_whole(r, r["presses"][2]) if r["fixture"] == "table-boundary"
                            else (_blocks(r, "final") is not None and len(_blocks(r, "final")) == 1
                                  and not (_blocks(r, "final")[0].get("text") or "").strip())),
     lambda r: (r["presses"][2].__setitem__("copyText", "") if r["fixture"] == "table-boundary"
                else r["final"]["reading"]["blocks"].append({"kind": "p", "text": "x"}))),
]
UNOBSERVED = [
    ("UO.outcome", lambda r: bool(r["press"]["sent"]) and (
        (r["press"]["sent"][0]["ok"] is True and _reply_sel(r["press"]).get("collapsed") is False
         and msa.anchors_in_order(r["press"].get("copyText") or "", r["baseline"]["reading"]["anchors"])["all"])
        or (r["press"]["sent"][0]["ok"] is False and CLICK_FIRST in (r["press"]["page"]["toast"] or ""))),
     lambda r: (r["press"]["sent"][0].__setitem__("ok", None))),
    ("UO.unchanged", lambda r: _blocks(r, "final") == _blocks(r, "baseline"),
     lambda r: r["final"]["reading"]["blocks"].append({"kind": "p", "text": "x"})),
    ("UO.ready", lambda r: r["press"]["page"]["pill"] == "ready", _set(lambda r: (r["press"]["page"], "pill"), "busy")),
]
EXTEND = [
    ("X.reply-ok", lambda r: any(x["action"] == "move-line-down" and x["extend"] is True and x["ok"] is True
                                 for x in r["extend"]["sent"]),
     lambda r: [x.__setitem__("ok", False) for x in r["extend"]["sent"]]),
    ("X.range", lambda r: (r["extend"]["state"] or {}).get("collapsed") is False,
     _set(lambda r: (r["extend"]["state"], "collapsed"), True)),
]
# Counterexamples: red FOR THE RIGHT REASON.
COUNTER = {
    "before": [("R.before-nothing-sent", lambda r: r["press"]["sent"] == [],
                lambda r: r["press"]["sent"].append({"action": "select-all", "ok": True})),
               ("R.before-collapsed", lambda r: (r["press"]["state"] or {}).get("collapsed") is True,
                _set(lambda r: (r["press"]["state"], "collapsed"), False))],
    "unoffered": [("R.unoffered-nothing-sent", lambda r: r["press"]["sent"] == [],
                   lambda r: r["press"]["sent"].append({"action": "select-all", "ok": True})),
                  ("R.unoffered-not-prevented", lambda r: bool(r["press"]["keys"]) and r["press"]["keys"][0]["prevented"] is False,
                   _set(lambda r: (r["press"]["keys"][0], "prevented"), True)),
                  ("R.unoffered-collapsed", lambda r: (r["press"]["state"] or {}).get("collapsed") is True,
                   _set(lambda r: (r["press"]["state"], "collapsed"), False))],
    "fake": [("R.fake-rewritten", lambda r: r["press"]["page"]["fakeRewrites"] >= 1,
              _set(lambda r: (r["press"]["page"], "fakeRewrites"), 0)),
             ("R.fake-says-nothing", lambda r: NOTHING in (r["press"]["page"]["toast"] or ""),
              _set(lambda r: (r["press"]["page"], "toast"), "")),
             ("R.fake-shape-collapsed", lambda r: r["press"]["page"]["shape"] == "collapsed",
              _set(lambda r: (r["press"]["page"], "shape"), "range-cross"))],
    "v25-worker": [("R.extend-refused", lambda r: not any(x["action"] == "move-line-down" and x["ok"] is True
                                                          for x in r["extend"]["sent"])
                    or (r["extend"]["state"] or {}).get("collapsed") is True,
                    lambda r: (r["extend"]["sent"].append({"action": "move-line-down", "ok": True, "extend": True}),
                               r["extend"]["state"].__setitem__("collapsed", False)))],
}


def clauses_for(run):
    product, fixture, arm = run["product"], run["fixture"], run["arm"]
    if product != "after":
        return COUNTER[product]
    if arm in ("select", "mac") or arm in FOLLOW:
        base = BLANK_SELECT if fixture == "blank" else SELECT
        return base + FOLLOW.get(arm, [])
    return {"table-cell": TABLE_CELL, "unobserved": UNOBSERVED, "extend": EXTEND}[arm]


def judge(run):
    if run.get("fatal"):
        return "NE", ["fatal: " + run["fatal"].strip().splitlines()[-1]]
    failed = []
    for cid, predicate, _ in clauses_for(run):
        try:
            if not predicate(run):
                failed.append(cid)
        except Exception as error:  # noqa: BLE001 -- an unreadable record fails its clause
            failed.append(f"{cid} ({type(error).__name__}: {error})")
    return ("PASS" if not failed else "FAIL"), failed


# ------------------------------------------------------------------ plan and verdict

def plan(kind: str, browsers: list[str]) -> list[tuple]:
    if kind == "shake":
        return [("after", "list-contexts", "select", "chrome", 1), ("after", "blank", "select", "chrome", 1),
                ("after", "frame-no-image", "select", "chrome", 1), ("after", "list-contexts", "copy", "chrome", 1),
                ("after", "table-boundary", "table-cell", "chrome", 1), ("after", "list-contexts", "extend", "chrome", 1),
                ("after", "list-contexts", "unobserved", "chrome", 1), ("after", "list-contexts", "type", "firefox", 1),
                ("before", "list-contexts", "select", "chrome", 1), ("fake", "list-contexts", "select", "chrome", 1),
                ("v25-worker", "list-contexts", "extend", "chrome", 1)]
    runs = []
    for browser in browsers:
        for fixture in (*msa.FIXTURES, LONG):
            for n in range(1, (3 if fixture in ("list-contexts", "table-boundary") else 1) + 1):
                runs.append(("after", fixture, "select", browser, n))
        for fixture in msa.FIXTURES:
            for arm in ("type", "backspace", "bold", "undo"):
                runs.append(("after", fixture, arm, browser, 1))
        if browser == "chrome":
            for fixture in msa.FIXTURES:
                if fixture != "blank":
                    runs.append(("after", fixture, "copy", browser, 1))
        runs += [("after", "list-contexts", "enter", browser, 1), ("after", "list-contexts", "mac", browser, 1),
                 ("after", "table-boundary", "table-cell", browser, 1), ("after", "frame-contexts", "table-cell", browser, 1),
                 ("after", "list-contexts", "unobserved", browser, 1), ("after", "list-contexts", "extend", browser, 1),
                 ("before", "list-contexts", "select", browser, 1), ("unoffered", "list-contexts", "select", browser, 1),
                 ("fake", "list-contexts", "select", browser, 1), ("v25-worker", "list-contexts", "extend", browser, 1)]
    return runs


def verdict(report):
    problems = [f"{name}: identity failed" for name, i in report["identities"].items() if not i.get("ok")]
    planned = {tuple(x) for x in report["plan"]}
    seen = {(r["product"], r["fixture"], r["arm"], r["browser"], r["repetition"]) for r in report["runs"]}
    if planned - seen:
        problems.append(f"{len(planned - seen)} planned runs missing")
    for r in report["runs"]:
        r["outcome"], r["failed"] = judge(r)
        if r["outcome"] != "PASS":
            what = "PASS" if r["product"] == "after" else "red for the right reason"
            problems.append(f"{r['product']}/{r['fixture']}/{r['arm']}/{r['browser']}#{r['repetition']}: not {what}: "
                            f"{r['failed']}")
    return ("S1_HOLDS" if not problems else "S1_RED"), problems


def self_test(path: Path) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    base, problems = verdict(copy.deepcopy(report))
    if base != "S1_HOLDS":
        print(f"self-test needs a holding report; this one is {base}: {problems[:3]}", file=sys.stderr)
        return 2
    results, covered = {}, set()
    for i, run in enumerate(report["runs"]):
        for cid, _, mutate in clauses_for(run):
            if cid in covered:
                continue
            mutated = copy.deepcopy(report)
            if mutate is None:
                results[cid] = {"verdict": "NO_MUTATION"}
                covered.add(cid)
                continue
            mutate(mutated["runs"][i])
            got, _ = verdict(mutated)
            results[cid] = {"verdict": got, "run": i}
            covered.add(cid)
    for extra, mutate in (("identity-failed", lambda r: next(iter(r["identities"].values())).__setitem__("ok", False)),
                          ("run-missing", lambda r: r["runs"].pop())):
        mutated = copy.deepcopy(report)
        mutate(mutated)
        results[extra] = {"verdict": verdict(mutated)[0]}
    red = all(v["verdict"] == "S1_RED" for v in results.values())
    print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "clauses": len(covered),
                      "mutations": results}, indent=1, ensure_ascii=False))
    return 0 if red else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", choices=("full", "shake"), default="full")
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--self-test", type=Path, metavar="REPORT")
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.self_test)
    if not args.out:
        parser.error("--out is required")
    args.out.mkdir(parents=True, exist_ok=False)
    browsers = [x for x in args.browsers.split(",") if x]
    runs = plan(args.plan, browsers)
    report = {"argv": sys.argv, "tool": "check_v26_select_all", "plan": [list(r) for r in runs],
              "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "identities": {}, "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="s1-select-all-", dir=PROJECT / "build"))
    try:
        with common.browser_lock("check_v26_select_all"):
            report["preRun"] = common.pre_run_checks()
            if report["preRun"]["refuse"]:
                raise SystemExit(f"pre-run refused: {report['preRun']['refuse']}")
            for product in products.NAMES:
                mine = [r for r in runs if r[0] == product]
                if not mine:
                    continue
                mirror = scratch / product
                pp.build_mirror(common.DIST, mirror, products.overrides(product, [OBSERVER]))
                report["identities"][product] = products.identity(product, mirror)
                if not report["identities"][product]["ok"]:
                    print(product, "identity FAILED, not run", file=sys.stderr, flush=True)
                    continue
                with common.served(mirror) as base:
                    port = int(base.split(":")[2].split("/")[0])
                    for _, fixture, arm, browser, n in mine:
                        run, session = {"product": product, "fixture": fixture, "arm": arm, "browser": browser,
                                        "repetition": n}, None
                        try:
                            session = common.open_browser(browser)
                            run.update(one(session, browser, product, fixture, arm, base, port))
                        except Exception:  # noqa: BLE001 -- recorded
                            run["fatal"] = traceback.format_exc()
                        finally:
                            if session is not None:
                                run["cleanup"] = common.close_browser(session)
                        report["runs"].append(run)
                        outcome, failed = judge(copy.deepcopy(run))
                        print(product, fixture, arm, browser, n, outcome, failed[:4], file=sys.stderr, flush=True)
                        (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                                                              encoding="utf-8")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report["finishedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["verdict"], report["problems"] = verdict(report)
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], report["problems"][:10], file=sys.stderr)
    return 0 if report["verdict"] == "S1_HOLDS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
