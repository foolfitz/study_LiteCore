#!/usr/bin/env python3
"""Diagnostic for the v21 shakedown: typing and arrows around a document move.  RECORDED, NEVER JUDGED.

Why (findings/evidence/link-batch-v21/shakedown/smoke/item1/README.md, "Observations" and "Product red"):
  1. In a dirty document the first Ctrl+End sends a checkpoint `save` first, and the move then completes
     `verified-move-readback` with the OLD caret; an engine ask later shows the caret at the end.  Spec
     SPEC-M3-link-batch-v21.md §9.1 names the consequence L-142-readback-overtaken (typing goes through
     a sync command that may run before Writer's GoToEndOfDoc).  Does it happen to typing?
  2. The move keys take the click-then-move path (`moveFromPoint`) while a delete is in flight, because
     the delete barrier's one-character range reads as the user's (web/e2-editor-app.js: the arrows'
     keydown path and `sendDocumentMove`; neither checks `deletesInFlight`).  Do arrows show it too?

Variants (`--variants`, comma-separated; every round is a fresh load and open):
  v1   plain3, dirty: real Z at the start (reply awaited), real Ctrl+End, real Q 30 ms after its keydown
  v2   as v1, but Q 50 ms after the move's reply arrives (polled from the observer's node)
  v3   as v1 without the Z: clean, no checkpoint (the control)
  v4   as v1 on long60 (create_long_document.build(60), as the item-1 runner builds it)
  v5   the Markdown dialog: paste `# a` with the clipboard instrument (D6's route), click 插入, then one
       real Z 0 ms (v5-0) or 300 ms (v5-300) after the dialog closes; added control v5-late (delayMs -1):
       Z once the page is quiet (ready, nothing pending, 0.5 s) plus 1 s.  Every v5 round then types Y
       (no click) and, after a real click at the engine's caret, X: does typing come back, and when?
       Added control v5-no-dialog (delayMs -2): the clipboard instrument's steps, no dialog, then Z, Y, X.
  v6   plain3, caret at «Bravo|» (k1024,k1027x5): Backspace @0, ArrowRight @20, Delete @40, on the v21
       page AND on the 0.2.24 page (dist/'s page, shell and v20 profile, as the item-1 runner's d8red)
  v6e  (added) as v6 with D8 (e)'s exact shape, ArrowRight in Ctrl+End's place: Backspace @0,
       Backspace @20, ArrowRight @40, Delete @60; both pages

Reused, not copied: the item-1 runner's `Pages` (S-1 mirrors), `Ctx` (load/open/start/ask/quiet/save,
the observer log), `run_script` and `element_center`; v21_input (keys), v21_clipboard (the dialog's
paste), v21_shakedown_common (S-9 lock, pre-run checks, foreign-CPU sample), v21_item1_marker
(paragraphs via the S-7 adapter).  New here: timed key sequences (Firefox: ONE WebDriver chain with
pauses, so a 20/30 ms gap is not eaten by per-press HTTP round trips), a reply-triggered key (v2), and a
small in-page recorder for v5 (dialog close, sink disabled/readOnly, focus, keypress, beforeinput).

  diag_v21_dirty_move.py --browser chrome --variants v1,v2,v3,v4,v5,v6 --rounds 3 --out DIR --wait-lock 7200
  diag_v21_dirty_move.py --table DIR        markdown tables from every report in DIR (no browser)

Every report says `"recordedNotJudged": true, "counted": false`.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r7_support  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import run_v20_shakedown as v20  # noqa: E402
import run_v21_shakedown_item1 as item1  # noqa: E402
import v21_clipboard as clip  # noqa: E402
import v21_input as inp  # noqa: E402
import v21_item1_marker as marker  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
from create_long_document import build as build_long_document  # noqa: E402

VARIANTS = ("v1", "v2", "v3", "v4", "v5", "v6", "v6e")
V21_PAGE_PREFIX = "3d5112161b23b060"
LOG_KINDS = ("kd", "kdp", "rq", "rs", "bi", "ask7post", "ask7", "askx")
PLACEMENT_BRAVO = "k1024,k1027x5"
V6_KEYS = [(0, "Backspace", ()), (20, "ArrowRight", ()), (40, "Delete", ())]
# Added: D8 (e)'s exact shape with ArrowRight in Ctrl+End's place (item-1 runner D8_SEQUENCES["e"]).
V6E_KEYS = [(0, "Backspace", ()), (20, "Backspace", ()), (40, "ArrowRight", ()), (60, "Delete", ())]
KEYS_OF = {"v6": V6_KEYS, "v6e": V6E_KEYS}
V5_TEXT = "# a"
StepError = item1.StepError


# ------------------------------------------------------------------ new instruments (small)

def timed_keys(ctx: item1.Ctx, steps: list[tuple[int, str, tuple]]) -> dict:
    """Real presses at offsets (ms).  Chrome: CDP presses on the monotonic clock (v21_input.schedule).
    Firefox: one WebDriver action chain with `pause` actions between the presses.  The page's own
    keydown times (the observer's `kd`) are what the report's gaps are computed from."""
    if ctx.browser == "chrome":
        sent = inp.schedule([(t, (lambda n=n, m=m: inp.key(ctx.session, "chrome", n, m))) for t, n, m in steps])
        return {"how": "cdp-schedule", "plannedMs": [t for t, _, _ in steps], "sentMs": sent}
    actions, previous = [], 0
    for t, name, mods in steps:
        if t > previous:
            actions.append({"type": "pause", "duration": t - previous})
        actions += inp._wd_press_actions(name, mods)  # noqa: SLF001  (the instrument's own press shape)
        previous = t
    t0 = time.monotonic()
    inp._wd_perform(ctx.session, actions)  # noqa: SLF001
    return {"how": "webdriver-chain-with-pauses", "plannedMs": [t for t, _, _ in steps],
            "chainMs": round((time.monotonic() - t0) * 1000, 1)}


PEEK_MOVE_REPLY = (
    "(() => { const n = document.getElementById('v21-i1'); if (!n) return null; let log;"
    " try { log = JSON.parse(n.textContent || '[]'); } catch (e) { return null; }"
    " const hit = log.find((e) => e.k === 'rs' && e.op === 'editorActionV2' && e.action === 'move-document-end'"
    " && e.s > ARG_LAST); return hit ? { t: hit.t, now: Math.round(performance.now() * 10) / 10 } : null; })()")


def key_after_move_reply(ctx: item1.Ctx, last_seq: int, name: str, after_ms: float, limit: float = 30.0) -> dict:
    """Poll the observer's node for the move's reply; press `name` `after_ms` after it (page clock)."""
    deadline = time.monotonic() + limit
    probe = PEEK_MOVE_REPLY.replace("ARG_LAST", str(last_seq))
    while time.monotonic() < deadline:
        hit = pp.evaluate(ctx.session, probe)
        if hit:
            lag = hit["now"] - hit["t"]
            usable = 0 <= lag < 1000
            wait = max(0.0, after_ms - lag) if usable else after_ms
            time.sleep(wait / 1000)
            inp.key(ctx.session, ctx.browser, name)
            return {"replyT": hit["t"], "seenLagMs": round(lag, 1), "lagUsable": usable, "sleptMs": round(wait, 1)}
        time.sleep(0.002)
    raise StepError(f"no move-document-end reply within {limit} s")


RECORDER = r"""(() => {
  if (document.getElementById('diag-dm')) return;
  const node = document.createElement('script'); node.type = 'application/json'; node.id = 'diag-dm';
  document.head.appendChild(node);
  const log = [];
  const now = () => Math.round(performance.now() * 10) / 10;
  const sink = document.querySelector('#sink'), dialog = document.querySelector('#markdown-dialog');
  const idOf = (el) => el ? (el.id || el.tagName) : null;
  const snap = () => ({ sinkDisabled: sink ? sink.disabled : null, sinkReadOnly: sink ? sink.readOnly : null,
                        active: idOf(document.activeElement), dialogOpen: dialog ? dialog.open : null,
                        hasFocus: document.hasFocus() });
  const put = (e) => { log.push({ t: now(), ...e, ...snap() }); node.textContent = JSON.stringify(log); };
  if (dialog) new MutationObserver((rs) => { for (const r of rs) put({ k: 'mut', target: 'dialog', attr: r.attributeName }); })
    .observe(dialog, { attributes: true, attributeFilter: ['open'] });
  if (sink) new MutationObserver((rs) => { for (const r of rs) put({ k: 'mut', target: 'sink', attr: r.attributeName }); })
    .observe(sink, { attributes: true, attributeFilter: ['disabled', 'readonly'] });
  window.addEventListener('keydown', (e) => put({ k: 'kd', key: e.key, target: idOf(e.target) }), true);
  window.addEventListener('keypress', (e) => put({ k: 'kp', key: e.key, target: idOf(e.target) }), true);
  window.addEventListener('keypress', (e) => put({ k: 'kpp', key: e.key, prevented: e.defaultPrevented }));
  document.addEventListener('focusin', (e) => put({ k: 'focusin', target: idOf(e.target) }), true);
  window.addEventListener('beforeinput', (e) => put({ k: 'bi', type: e.inputType, data: e.data ?? null, target: idOf(e.target) }), true);
  window.addEventListener('input', (e) => put({ k: 'in', type: e.inputType, data: e.data ?? null, target: idOf(e.target) }), true);
  put({ k: 'installed' });
})();"""
READ_RECORDER = "(() => { const n = document.getElementById('diag-dm'); return n ? JSON.parse(n.textContent || '[]') : null; })()"
AFTER_Z = ("(() => { const s = document.querySelector('#sink'), m = document.querySelector('#markdown-text');"
           " const a = document.activeElement; return { sinkValue: s ? s.value : null, markdownValue: m ? m.value : null,"
           " active: a ? (a.id || a.tagName) : null }; })()")
LATE = -1        # v5's added control: Z once the page is quiet (ready, nothing pending) plus 1 s
NO_DIALOG = -2   # v5's added control: the clipboard instrument's steps, no dialog, then Z
DELAY_LABEL = {LATE: "late", NO_DIALOG: "no-dialog"}


# ------------------------------------------------------------------ reading what was recorded

def paragraphs(raw: bytes) -> list[str]:
    return [t for _, _, t in marker.paragraphs_of(raw)]


def hits(texts: list[str], ch: str) -> list[dict]:
    return [{"para": i, "offset": off, "text": t[:70]} for i, t in enumerate(texts) for off, c in enumerate(t) if c == ch]


def q_class(texts: list[str], dirty: bool) -> str:
    q = hits(texts, "Q")
    if len(q) != 1:
        return f"{len(q)} Q in the saved document"
    h = q[0]
    if h["para"] == len(texts) - 1 and h["offset"] == len(texts[-1]) - 1:
        return "document end"
    if h["para"] == 0 and texts[0][:h["offset"]] == ("Z" if dirty else ""):
        return "pre-move caret"
    return f"elsewhere: para {h['para']} offset {h['offset']}"


def first(log: list[dict], pred) -> dict | None:
    return next((e for e in log if pred(e)), None)


def timeline(log: list[dict], t0: float | None) -> list[str]:
    """Compact request/response order relative to `t0` (the first key's keydown, page clock)."""
    out = []
    for e in log:
        if e.get("k") not in ("kd", "rq", "rs", "bi"):
            continue
        dt = (e.get("t", 0) - t0) if t0 is not None else e.get("t", 0)
        if e["k"] == "kd":
            if e.get("key") in ("Control", "Shift"):
                continue
            what = f"KEY {'Ctrl+' if e.get('ctrl') else ''}{e.get('key')}"
        elif e["k"] == "bi":
            what = f"beforeinput {e.get('type')} {e.get('data')!r}"
        elif e["k"] == "rq":
            if e.get("ask"):
                continue
            what = f"rq {e.get('action') or e.get('op')}"
        else:
            if e.get("rq", 0) >= 0x7E000000:
                continue
            caret = e.get("caret") or {}
            what = (f"rs {e.get('action') or e.get('op')} {e.get('completion') or ('ok' if e.get('ok') else e.get('code'))}"
                    + (f" caret {caret.get('x')},{caret.get('y')}" if caret else ""))
        out.append(f"{dt:+8.1f} {what}")
    return out


def caret_str(c) -> str | None:
    return f"{c.get('x')},{c.get('y')}" if isinstance(c, dict) else None


def summarise_move(rec: dict, dirty: bool) -> dict:
    log = rec.get("log", [])
    end_kd = first(log, lambda e: e.get("k") == "kd" and e.get("key") == "End")
    q_kd = first(log, lambda e: e.get("k") == "kd" and e.get("key") == "Q")
    move = first(log, lambda e: e.get("k") == "rs" and e.get("action") == "move-document-end")
    ask7 = first(log, lambda e: e.get("k") == "ask7" and move is not None and e.get("forRq") == move.get("rq"))
    ins = first(log, lambda e: e.get("k") == "rs" and e.get("op") == "insertText")
    texts = rec.get("savedTexts") or []
    t0 = end_kd.get("t") if end_kd else None
    return {
        "qClass": q_class(texts, dirty) if texts else "no saved document",
        "qHits": hits(texts, "Q"), "zHits": hits(texts, "Z"),
        "gapEndKdToQKdMs": round(q_kd["t"] - end_kd["t"], 1) if end_kd and q_kd else None,
        "gapMoveReplyToQKdMs": round(q_kd["t"] - move["t"], 1) if move and q_kd else None,
        "moveCompletion": move and move.get("completion"), "moveRoundTripMs": move and round(move["t"] - move["tRq"], 1),
        "moveReplyCaret": caret_str(move and move.get("caret")),
        "ask7Caret": caret_str(ask7 and ask7.get("caret")), "ask7AfterReplyMs": ask7 and move and round(ask7["tPosted"] - move["t"], 1),
        "insertTextCompletion": ins and (ins.get("completion") or ("ok" if ins.get("ok") else ins.get("code"))),
        "insertTextCaret": caret_str(ins and ins.get("caret")),
        "qBeforeinput": [e.get("type") for e in log if e.get("k") == "bi"],
        "order": [e.get("action") or e.get("op") for e in log if e.get("k") == "rq" and not e.get("ask")],
        "timeline": timeline(log, t0),
    }


def expected_in_order(text: str, caret: int, keys: list[str]) -> str:
    """The P2 text if each key were applied in order on a caret (no range)."""
    for key in keys:
        if key == "Backspace" and caret > 0:
            text, caret = text[:caret - 1] + text[caret:], caret - 1
        elif key == "Delete" and caret < len(text):
            text = text[:caret] + text[caret + 1:]
        elif key == "ArrowRight":
            caret = min(len(text), caret + 1)
        elif key == "ArrowLeft":
            caret = max(0, caret - 1)
    return text


def summarise_v6(rec: dict, keys: list) -> dict:
    log = rec.get("log", [])
    kds = [e for e in log if e.get("k") == "kd" and e.get("key") in ("Backspace", "ArrowRight", "Delete")]
    t0 = kds[0]["t"] if kds else None
    reqs = [e for e in log if e.get("k") == "rq" and not e.get("ask")]
    labels = [e.get("action") or e.get("op") for e in reqs]
    first_delete = next((i for i, a in enumerate(labels) if str(a).startswith("delete")), None)
    move_i = next((i for i, a in enumerate(labels) if a == "move-character-right"), None)
    between = labels[first_delete + 1:move_i] if first_delete is not None and move_i is not None else []
    click_i = next((i for i, a in enumerate(between) if a in ("click", "editorPlaceCaretV2")), None)
    texts = rec.get("savedTexts") or []
    return {
        "p2": texts[1] if len(texts) > 1 else None,
        "expectedInOrder": expected_in_order("Bravo second paragraph", 5, [k for _, k, _ in keys]),
        "keyGapsMs": [round(e["t"] - t0, 1) for e in kds] if t0 is not None else None,
        "order": labels,
        "betweenFirstDeleteAndMove": between,
        "placeCaretBeforeMove": click_i is not None,
        "deleteBetweenClickAndMove": click_i is not None and any(str(a).startswith("delete") for a in between[click_i:]),
        "timeline": timeline(log, t0),
    }


def summarise_v5(rec: dict) -> dict:
    log, recd = rec.get("log", []), rec.get("recorder") or []
    z_kd = first(log, lambda e: e.get("k") == "kd" and e.get("key") == "Z")
    closed = first(recd, lambda e: e.get("k") == "mut" and e.get("target") == "dialog" and e.get("dialogOpen") is False)
    z_rec = first(recd, lambda e: e.get("k") == "kd" and e.get("key") == "Z")
    y_kd = first(log, lambda e: e.get("k") == "kd" and e.get("key") == "Y")
    y_rec = first(recd, lambda e: e.get("k") == "kd" and e.get("key") == "Y")
    # Z's window: from Z's keydown to Y's (the added discriminator's first key), page clock.
    after_z = [e for e in log if z_kd and e.get("t", 0) >= z_kd["t"] and (not y_kd or e.get("t", 0) < y_kd["t"])]
    rec_after_z = [e for e in recd if z_rec and e.get("t", 0) >= z_rec["t"] and (not y_rec or e.get("t", 0) < y_rec["t"])]
    texts = rec.get("savedTexts") or []
    return {
        "closeToZKdMs": round(z_rec["t"] - closed["t"], 1) if z_rec and closed else None,
        "zKeydownTarget": z_rec and z_rec.get("target"), "zKeydownActive": z_rec and z_rec.get("active"),
        "sinkDisabledAtZ": z_rec and z_rec.get("sinkDisabled"), "sinkReadOnlyAtZ": z_rec and z_rec.get("sinkReadOnly"),
        "documentHasFocusAtZ": z_rec and z_rec.get("hasFocus"),
        "zPrevented": (first(log, lambda e: e.get("k") == "kdp" and e.get("key") == "Z") or {}).get("prevented"),
        "zKeypress": any(e.get("k") == "kp" and e.get("key") == "Z" for e in recd),
        "zKeypressPrevented": (first(recd, lambda e: e.get("k") == "kpp" and e.get("key") == "Z") or {}).get("prevented"),
        "zBeforeinput": [e.get("type") for e in after_z if e.get("k") == "bi"],
        "anyBeforeinputAfterZ": [f"{e.get('type')}@{e.get('target')}" for e in rec_after_z if e.get("k") == "bi"],
        "anyInputAfterZ": [f"{e.get('type')}@{e.get('target')}" for e in rec_after_z if e.get("k") == "in"],
        "afterZ": rec.get("afterZ"),
        "insertTextAfterZ": any(e.get("k") == "rq" and e.get("op") == "insertText" for e in after_z),
        "sinkMutations": [(round(e["t"] - closed["t"], 1) if closed else e["t"], e.get("attr"), e.get("sinkDisabled"))
                          for e in recd if e.get("k") == "mut" and e.get("target") == "sink"],
        "focusins": [(round(e["t"] - closed["t"], 1) if closed else e["t"], e.get("target")) for e in recd if e.get("k") == "focusin"],
        "zHits": hits(texts, "Z"), "paragraphs": [t[:40] for t in texts[:4]],
        "yHits": hits(texts, "Y"), "xHits": hits(texts, "X"),
        "beforeinputData": [f"{e.get('data')}@{e.get('target')}" for e in recd if e.get("k") == "bi"],
        "clickOp": ((rec.get("click") or {}).get("response") or {}).get("op"),
        "order": [e.get("action") or e.get("op") for e in log if e.get("k") == "rq" and not e.get("ask")
                  and (not y_kd or e.get("t", 0) < y_kd["t"])],
        "orderAfterY": [e.get("action") or e.get("op") for e in log if e.get("k") == "rq" and not e.get("ask")
                        and y_kd and e.get("t", 0) >= y_kd["t"]],
    }


# ------------------------------------------------------------------ rounds

def settle_long(ctx: item1.Ctx) -> dict:
    """The item-1 D10 open: the first pageRectangles reply, then up to 40 s for all 60 parts."""
    _reply, entries = v20.settle_rects(ctx.session)
    ctx.trace.all += entries
    t0 = time.monotonic()
    while time.monotonic() - t0 < 40:
        latest = v20.latest_rects(ctx.trace.all)
        if latest and latest.get("parts") == 60:
            break
        time.sleep(1.0)
        ctx.drain()
    latest = v20.latest_rects(ctx.trace.all)
    return {"parts": latest and latest.get("parts")}


def settle_after(ctx: item1.Ctx) -> None:
    time.sleep(1.0)
    ctx.quiet(limit=60)
    time.sleep(0.5)
    ctx.quiet(limit=60)


def keep(ctx: item1.Ctx, rec: dict, mark: int, label: str) -> None:
    ctx.drain()
    rec["log"] = [e for e in ctx.log.all[mark:] if e.get("k") in LOG_KINDS]
    rec["save"] = ctx.save(label)
    if rec["save"].get("saved"):
        raw = (ctx.docs / f"{label}.odt").read_bytes()
        rec["savedTexts"] = paragraphs(raw)


def round_move(ctx: item1.Ctx, variant: str, label: str) -> dict:
    fixture = "long60" if variant == "v4" else "plain3"
    dirty = variant != "v3"
    rec = {"fixture": fixture, "dirty": dirty, "foreign": ctx.foreign()}
    rec["load"] = ctx.load("v21")
    rec["open"] = ctx.open(fixture)
    if fixture == "long60":
        rec["rects"] = settle_long(ctx)
    rec["start"] = ctx.start_state()
    if dirty:
        rec["typedZ"] = ctx.type_marker()
    ctx.ev_quiet()
    mark, last_seq = len(ctx.log.all), ctx.log.last
    if variant == "v2":
        inp.key(ctx.session, ctx.browser, "End", ("ctrl",))
        rec["sent"] = {"how": "after-move-reply", **key_after_move_reply(ctx, last_seq, "Q", 50)}
    else:
        rec["sent"] = timed_keys(ctx, [(0, "End", ("ctrl",)), (30, "Q", ())])
    move = ctx.wait_rs(mark, lambda e: e.get("op") == "editorActionV2" and e.get("action") == "move-document-end", 30)
    rec["insert"] = ctx.wait_rs(mark, lambda e: e.get("op") == "insertText", 30)
    if move is not None and move.get("ok"):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            ctx.log.drain()
            if any(e.get("k") == "ask7" and e.get("forRq") == move.get("rq") for e in ctx.log.all[mark:]):
                break
            time.sleep(0.05)
    settle_after(ctx)
    rec["finalAsk"] = (ctx.ask().get("full") or {})
    keep(ctx, rec, mark, label)
    rec["summary"] = summarise_move(rec, dirty)
    return rec


def round_v5(ctx: item1.Ctx, delay_ms: int, label: str) -> dict:
    rec = {"delayMs": delay_ms, "foreign": ctx.foreign()}
    rec["load"] = ctx.load("v21")
    rec["open"] = ctx.open("plain3")
    rec["start"] = ctx.start_state()
    origin = pp.evaluate(ctx.session, "(() => location.origin)()")
    rec["grant"] = clip.grant(ctx.session, ctx.browser, origin)
    rec["clipboard"] = clip.write_text(ctx.session, V5_TEXT)
    r7_support.run_in_page(ctx.session, RECORDER)
    if delay_ms == NO_DIALOG:
        # Added control: the clipboard instrument's steps exactly as above, no dialog, then the same keys.
        r7_support.run_in_page(ctx.session, "document.querySelector('#sink').focus({ preventScroll: true });")
        time.sleep(0.3)
        ctx.drain()
        mark = len(ctx.log.all)
        inp.key(ctx.session, ctx.browser, "Z")
        time.sleep(0.3)
        rec["afterZ"] = pp.evaluate(ctx.session, AFTER_Z)
        settle_after(ctx)
        return finish_v5(ctx, rec, mark, label)
    entry = item1.element_center(ctx, '#toolbar [data-action="paste-markdown"]')
    if entry is None:
        raise StepError("no-entry: the paste-markdown button is hidden or missing")
    inp.click(ctx.session, ctx.browser, *entry)
    time.sleep(0.5)
    rec["dialogOpen"] = pp.evaluate(ctx.session, "(() => document.querySelector('#markdown-dialog').open)()")
    clip.press_ctrl_v(ctx.session, ctx.browser)
    time.sleep(0.8)
    rec["readback"] = clip.readback(ctx.session, "#markdown-text")
    if rec["readback"].get("sha256") != (rec["clipboard"] or {}).get("sha256"):
        raise StepError(f"input-mismatch: the textarea holds {rec['readback']}")
    insert = item1.element_center(ctx, "#markdown-insert")
    if insert is None:
        raise StepError("no 插入 button")
    ctx.drain()
    mark = len(ctx.log.all)
    inp.click(ctx.session, ctx.browser, *insert)
    t0 = time.monotonic()
    closed_after = None
    while time.monotonic() - t0 < 60:
        if not pp.evaluate(ctx.session, "(() => document.querySelector('#markdown-dialog').open)()"):
            closed_after = round((time.monotonic() - t0) * 1000)
            break
    rec["dialogClosedAfterMs"] = closed_after
    if closed_after is None:
        raise StepError("the dialog did not close within 60 s")
    if delay_ms == LATE:
        rec["lateQuiet"] = ctx.quiet(limit=30)
        time.sleep(1.0)
    elif delay_ms:
        time.sleep(delay_ms / 1000)
    inp.key(ctx.session, ctx.browser, "Z")
    time.sleep(0.3)
    rec["afterZ"] = pp.evaluate(ctx.session, AFTER_Z)
    settle_after(ctx)
    return finish_v5(ctx, rec, mark, label)


def finish_v5(ctx: item1.Ctx, rec: dict, mark: int, label: str) -> dict:
    # Added discriminator: a second key with no click (Y), then a real click at the engine's caret and X.
    inp.key(ctx.session, ctx.browser, "Y")
    settle_after(ctx)
    caret = (ctx.ask().get("full") or {}).get("caret")
    if caret:
        rec["click"] = ctx.click_caret(caret)
        inp.key(ctx.session, ctx.browser, "X")
        settle_after(ctx)
    rec["recorder"] = pp.evaluate(ctx.session, READ_RECORDER)
    keep(ctx, rec, mark, label)
    rec["summary"] = summarise_v5(rec)
    return rec


def round_v6(ctx: item1.Ctx, page: str, label: str, keys: list) -> dict:
    rec = {"page": page, "keys": keys, "foreign": ctx.foreign()}
    rec["load"] = ctx.load(page)
    rec["open"] = ctx.open("plain3")
    rec["start"] = ctx.start_state()
    rec["placement"] = item1.run_script(ctx, PLACEMENT_BRAVO, "placement", None)["steps"]
    rec["placementCaret"] = ((ctx.ask().get("full") or {}).get("caret"))
    ctx.ev_quiet()
    mark = len(ctx.log.all)
    rec["sent"] = timed_keys(ctx, keys)
    settle_after(ctx)
    keep(ctx, rec, mark, label)
    rec["summary"] = summarise_v6(rec, keys)
    return rec


def guarded(fn, *args) -> dict:
    try:
        rec = fn(*args)
        rec["outcome"] = "done"
    except StepError as error:
        rec = {"outcome": "step-error", "error": str(error)}
    except Exception as error:  # noqa: BLE001
        rec = {"outcome": "runner-error", "error": f"{type(error).__name__}: {error}",
               "trace": traceback.format_exc()[-1500:]}
    return rec


# ------------------------------------------------------------------ tables (no browser)

def _cell(v) -> str:
    return "" if v is None else str(v).replace("|", "\\|")


def tables(directory: Path) -> str:
    lines = []
    for path in sorted(directory.glob("report-*.json")):
        report = json.loads(path.read_text())
        browser = report["browser"]
        lines.append(f"\n### {browser} ({report.get('browserVersion')}), `{path.name}`\n")
        for variant, block in report["results"].items():
            rounds = block.get("rounds", [])
            lines.append(f"\n**{variant.upper()}** ({block.get('what')})\n")
            if variant in ("v1", "v2", "v3", "v4"):
                lines.append("| round | Q lands | Q kd − Ctrl+End kd (ms) | Q kd − move reply (ms) | move completion (round trip ms) "
                             "| reply caret | +500 ms ask caret | insertText | request order |")
                lines.append("|---|---|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('round')} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} |||||||| ")
                        continue
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("round"), s.get("qClass"), s.get("gapEndKdToQKdMs"), s.get("gapMoveReplyToQKdMs"),
                        f"{s.get('moveCompletion')} ({s.get('moveRoundTripMs')})", s.get("moveReplyCaret"), s.get("ask7Caret"),
                        f"{s.get('insertTextCompletion')} caret {s.get('insertTextCaret')}", " → ".join(map(str, s.get("order") or [])))) + " |")
            elif variant == "v5":
                lines.append("| round | delay | dialog close → Z kd (ms) | Z kd target / active | sink disabled at Z | keypress (prevented) "
                             "| beforeinput / input anywhere after Z | insertText | Z in saved doc | then Y (no click), X (after click) "
                             "| request order |")
                lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    delay = DELAY_LABEL.get(r.get("delayMs"), r.get("delayMs"))
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('round')} | {delay} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} ||||||| ")
                        continue
                    z = s.get("zHits") or []
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("round"), delay, s.get("closeToZKdMs"), f"{s.get('zKeydownTarget')} / {s.get('zKeydownActive')}",
                        s.get("sinkDisabledAtZ"), f"{s.get('zKeypress')} ({s.get('zKeypressPrevented')})",
                        f"{s.get('anyBeforeinputAfterZ')} / {s.get('anyInputAfterZ')}", s.get("insertTextAfterZ"),
                        "; ".join(f"para {h['para']} off {h['offset']} {h['text'][:28]!r}" for h in z) or "absent",
                        f"Y {'in' if s.get('yHits') else 'absent'}, X after click {'in' if s.get('xHits') else 'absent'}",
                        " → ".join(map(str, s.get("order") or [])))) + " |")
            else:
                lines.append("| page | round | key gaps (ms) | saved P2 | in order would be | place-caret between delete and move "
                             "| a delete between that click and the move | request order |")
                lines.append("|---|---|---|---|---|---|---|---|")
                for r in rounds:
                    s = r.get("summary") or {}
                    if r.get("outcome") != "done":
                        lines.append(f"| {r.get('page')} | {r.get('round')} | {r.get('outcome')}: {_cell(r.get('error'))[:80]} ||||| ")
                        continue
                    lines.append("| " + " | ".join(_cell(x) for x in (
                        r.get("page"), r.get("round"), s.get("keyGapsMs"), repr(s.get("p2")), repr(s.get("expectedInOrder")),
                        s.get("placeCaretBeforeMove"), s.get("deleteBetweenClickAndMove"),
                        " → ".join(map(str, s.get("order") or [])))) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------------ main

WHAT = {"v1": "plain3, dirty, Q 30 ms after Ctrl+End's keydown", "v2": "plain3, dirty, Q 50 ms after the move's reply",
        "v3": "plain3, clean control, Q 30 ms after Ctrl+End's keydown", "v4": "long60, dirty, Q 30 ms after Ctrl+End's keydown",
        "v5": "Markdown dialog `# a`, Z 0 / 300 ms after it closes (+ added controls late, no-dialog)",
        "v6": "«Bravo|»: Backspace @0, ArrowRight @20, Delete @40",
        "v6e": "(added) «Bravo|»: Backspace @0, Backspace @20, ArrowRight @40, Delete @60 (D8 (e) with ArrowRight)"}


def main() -> int:
    sys.modules.setdefault("diag_v21_dirty_move", sys.modules[__name__])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--browser", choices=("chrome", "firefox"))
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--window", default="1400x1000")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--smoke", action="store_true", help="label the report a development run")
    ap.add_argument("--wait-lock", type=float, default=0.0)
    ap.add_argument("--table", type=Path, help="print markdown tables from the reports in this directory")
    args = ap.parse_args()
    if args.table:
        print(tables(args.table))
        return 0
    if not args.browser or not args.out:
        raise SystemExit("--browser and --out are required")
    variants = [v for v in args.variants.split(",") if v]
    if [v for v in variants if v not in VARIANTS]:
        raise SystemExit(f"unknown variants; known {VARIANTS}")
    window = tuple(int(v) for v in args.window.split("x"))
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    report_path = args.out / f"report-{args.browser}-{stamp}.json"
    docs = args.out / "docs" / f"{args.browser}-{stamp}"
    docs.mkdir(parents=True, exist_ok=True)
    pre = common.pre_run_checks()
    if pre["refuse"]:
        raise SystemExit(f"pre-run checks refuse: {pre['refuse']}")
    fixtures = {p.stem: p.read_bytes() for p in sorted(item1.FIXTURE_DIR.glob("*.odt"))}
    fixtures["long60"] = build_long_document(60)
    report = {"tool": "diag_v21_dirty_move.py", "toolSha256": common.sha256_file(Path(__file__)),
              "recordedNotJudged": True, "counted": False, "smoke": args.smoke, "browser": args.browser,
              "variants": variants, "rounds": args.rounds, "window": window, "startedAt": common.now_iso(),
              "preRun": pre, "inputs": {name: common.sha256_bytes(raw) for name, raw in fixtures.items()
                                        if name in ("plain3", "long60")}, "results": {}}
    scratch = Path(tempfile.mkdtemp(prefix="diag-dirty-move-"))
    pages = item1.Pages(scratch, fixtures, None)

    def flush() -> None:
        report["pages"] = pages.identity
        report_path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))

    session = None
    with common.browser_lock(f"diag_v21_dirty_move {args.browser} {','.join(variants)}", wait_s=args.wait_lock) as holder:
        report["lock"] = {**holder, "acquiredAt": common.now_iso()}
        try:
            pages.base("v21")
            served = pages.identity["v21"]["pageServedSha256"]
            report["v21PageCheck"] = {"served": served, "expectedPrefix": V21_PAGE_PREFIX,
                                      "matches": served.startswith(V21_PAGE_PREFIX),
                                      "identityOk": pages.identity["v21"].get("identityOk")}
            if not report["v21PageCheck"]["matches"]:
                flush()
                raise SystemExit(f"the v21 page served is {served[:16]}, not {V21_PAGE_PREFIX}")
            if "v6" in variants or "v6e" in variants:
                pages.base("dist0224")
            session = common.open_browser(args.browser, window,
                                          firefox_prefs=clip.FIREFOX_PREFS if "v5" in variants else None)
            report["browserVersion"] = getattr(session, "version", None)
            ctx = item1.Ctx(session, args.browser, pages, report, docs)
            for variant in variants:
                t0 = time.monotonic()
                block = {"what": WHAT[variant], "rounds": []}
                report["results"][variant] = block
                if variant == "v5":
                    jobs = [(delay, n) for delay in (0, 300, LATE, NO_DIALOG) for n in range(1, args.rounds + 1)]
                    for delay, n in jobs:
                        rec = guarded(round_v5, ctx, delay, f"v5-{DELAY_LABEL.get(delay, delay)}-r{n}")
                        block["rounds"].append({"round": n, "delayMs": delay, **rec})
                        flush()
                elif variant in ("v6", "v6e"):
                    for page in ("v21", "dist0224"):
                        for n in range(1, args.rounds + 1):
                            rec = guarded(round_v6, ctx, page, f"{variant}-{page}-r{n}", KEYS_OF[variant])
                            block["rounds"].append({"round": n, "page": page, **rec})
                            flush()
                else:
                    for n in range(1, args.rounds + 1):
                        rec = guarded(round_move, ctx, variant, f"{variant}-r{n}")
                        block["rounds"].append({"round": n, **rec})
                        flush()
                block["seconds"] = round(time.monotonic() - t0, 1)
                flush()
        finally:
            report["completedAt"] = common.now_iso()
            if session is not None:
                report["close"] = common.close_browser(session)
            pages.close()
            flush()
    out = {v: [r.get("outcome") for r in b["rounds"]] for v, b in report["results"].items()}
    print(json.dumps({"report": str(report_path), "outcomes": out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
