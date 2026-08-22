#!/usr/bin/env python3
"""Finding 064's mechanism: is it the repaint between the press and the typing?

An inline format set through the product never reaches the text typed next --
all four formats, both directions, eight arms.  The ATTRIBUTION is already done
and is not what this probe is for: D1's harness, on the same artifact
`29ec627b`, read by the same `inline_styles_of()`, gets all eight right.  The
engine is fine; the product path is broken.

What is not established is the MECHANISM, and until it is, nobody can say
whether the remedy is a shell change (independent, parallel, no link) or an
engine change (payload item 7, and the link waits).  So this probe measures ONE
named candidate rather than hunting:

    `run()` awaits `renderDocument()` after every operation
    (web/e2-editor-app.js:377-382), so the product inserts a paintTile +
    getDocumentSize round trip between the format action and the typing.
    D1 does not -- it SAVES there instead (web/e2-c-d1-app.js:381-382) and
    then types.

Prediction, written first:
findings/evidence/064/PREDICTION-render-between-format-and-typing.md

WHERE THE INSTRUMENT SITS, AND WHY IT IS NOT THE `run()` CALL SITE.  The page
has a SECOND render source: `onEvent` schedules a repaint whenever the engine
reports `document-invalidated` (web/e2-editor-app.js:768-769).  A diagnostic
that deleted the `await renderDocument()` on line 382 would leave that one
running and could report "the render is not the mechanism" while a render still
happened.  The hook therefore goes INSIDE `renderDocument()`, where every caller
passes -- and `renderDocument()` is the page's only paintTile source, because
the page never calls `scheduleViewport()` and `TileScheduler` has no timer.

THE MUTATION IS A BOOLEAN, NOT A SECOND FILE.  Baseline and variant run the
same mirrored bytes and differ only in whether `__f064.suppress` was true across
the press-to-commit window.  "The mirror changed something else" is therefore
not available as an explanation.

dist/ is never written; probe.wasm is byte-identical to `29ec627b`; the report is
stamped `evidenceClass: "diagnostic"`.

Usage:
  probe_064_format_reaches_typing.py --browser chrome [--arms A,B,...] [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e1_support import sha256 as sha256_file  # noqa: E402
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from run_e2_c_product_path import (  # noqa: E402
    CARET_COLUMNS, CLEAR_TOAST, INSTALL, LINE_INK, ODF_NS, POINT_AT, PRESS,
    READ_TOAST,
    SET_TEXT, build_mirror, capture_save, caret_click_fractions,
    caret_from_columns, inline_styles_of, is_an_odt, place_caret_and_settle,
    revision_of, served_shell_identity, wait_for,
)
from xml.etree import ElementTree  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

# The one edit.  Inert unless `globalThis.__f064` exists, so the mirrored page
# is the shipped page for anything that does not install the hook.
RENDER_ANCHOR = """async function renderDocument(retriesLeft = 6) {
  if (!session?.document"""

RENDER_PATCHED = """async function renderDocument(retriesLeft = 6) {
  // DIAGNOSTIC, finding 064.  Not shipped.  See
  // tools/probe_064_format_reaches_typing.py.
  const diag = globalThis.__f064;
  if (diag) {
    if (diag.suppress) { diag.suppressed += 1; return; }
    diag.renders += 1;
  }
  if (!session?.document"""

# FINDING 067's engine half.  The adapter already traces `commit-end` with the
# WHOLE result of the commit, and the engine's insertText reply carries
# `method` -- "paste" when LOK's paste accepted the text, "postKeyEvent" when it
# refused and the engine fell back to posting key events.  Nobody forwards that
# field anywhere a probe can see it, so this mirror records the traces the page
# already receives.  Inert without `globalThis.__f067`.
TRACE_ANCHOR = """    onInputTrace(entry) {
      if (entry?.action === "composition-rejected" || entry?.status === "failed")"""

TRACE_PATCHED = """    onInputTrace(entry) {
      // DIAGNOSTIC, finding 067.  Not shipped.
      if (globalThis.__f067) globalThis.__f067.traces.push(entry);
      if (entry?.action === "composition-rejected" || entry?.status === "failed")"""

# FINDING 068.  The page draws the caret from `editorState.caret` and only when
# `selection.collapsed !== false`, and `paint()` runs on every state update.
# Five pixel attempts established WHAT happens -- no caret on that line after
# typing, one after a move -- and none of them could say WHICH of the three
# conditions failed, because a pixel that is not there looks the same whatever
# withheld it.  These two hooks ask the page directly.  Inert without
# `globalThis.__f068`.
STATE_ANCHOR = """  updateGestureAffordance();
  // Finding 058.  The caret arrives as a state update, not as a document
  // change, so redrawing only on render would leave it a gesture behind.
  paint();"""

STATE_PATCHED = """  updateGestureAffordance();
  // DIAGNOSTIC, finding 068.  Not shipped.
  {
    const diag = globalThis.__f068;
    if (diag) {
      const es = session?.state?.snapshot?.editorState;
      diag.updates.push({
        label: diag.label,
        hasEditorState: !!es,
        caret: es && es.caret ? { x: es.caret.x, y: es.caret.y,
                                  width: es.caret.width,
                                  height: es.caret.height } : null,
        collapsed: es && es.selection ? es.selection.collapsed : null,
        rectangles: es && es.selection && es.selection.rectangles
                    ? es.selection.rectangles.length : null,
        revision: session?.state?.snapshot?.revision ?? null,
        // THE DISCRIMINATOR.  `sourceSequence` counts EVERY editor callback
        // that changed state; `documentChangeSequence` is the value it had at
        // the last INVALIDATE_TILES.  If the two are equal after a commit, the
        // tile invalidation was the ONLY callback that arrived -- so no cursor
        // callback came, as against one that came and reported the same
        // rectangle.  Those are different defects with different remedies and
        // a stale caret x cannot tell them apart.
        sourceSequence: es ? es.sourceSequence : null,
        documentChangeSequence: es ? es.documentChangeSequence : null,
      });
    }
  }
  // Finding 058.  The caret arrives as a state update, not as a document
  // change, so redrawing only on render would leave it a gesture behind.
  paint();"""

# The decision itself, recorded where it is made.  Recording the inputs is not
# enough: `paint()` has two earlier returns (no cached tiles; no editorState or
# no document) and either one produces exactly the same absent pixel.
PAINT_ANCHOR = """function paint() {
  if (!lastTiles.length) return;"""

PAINT_PATCHED = """function paint() {
  const diag068 = globalThis.__f068;
  const note068 = (why, extra) => {
    if (diag068) diag068.paints.push({ label: diag068.label, why, ...extra });
  };
  if (!lastTiles.length) { note068("no-cached-tiles", {}); return; }"""

PAINT_ANCHOR_2 = """  const editorState = session?.state?.snapshot?.editorState;
  if (!editorState || !session?.document) return;"""

PAINT_PATCHED_2 = """  const editorState = session?.state?.snapshot?.editorState;
  if (!editorState || !session?.document) {
    note068("no-editor-state-or-document",
            { hasEditorState: !!editorState, hasDocument: !!session?.document });
    return;
  }"""

PAINT_ANCHOR_3 = """  const caret = editorState.caret;
  if (caret && editorState.selection?.collapsed !== false) {"""

PAINT_PATCHED_3 = """  const caret = editorState.caret;
  note068(caret ? (editorState.selection?.collapsed !== false
                   ? "drew-caret" : "collapsed-is-false")
                : "no-caret-in-state",
          { caretX: caret ? caret.x : null,
            collapsed: editorState.selection
                       ? editorState.selection.collapsed : null });
  if (caret && editorState.selection?.collapsed !== false) {"""

# FINDING 068's SECOND QUESTION, and the one that decides the remedy: does
# LOK's cursor callback ARRIVE after a paste-based commit?
#
# Two answers, two different fixes, and `sourceSequence` cannot separate them --
# it counts callbacks that CHANGED state, and a callback that arrives with an
# unparseable payload changes nothing, exactly like one that never came.
#
# The engine already distinguishes them and already says so out loud.  Every
# state change emits `editor-state` with a `source` naming the callback
# ("visible-cursor", "invalidate-tiles", "selection-rectangles", ...), and a
# cursor-range callback whose payload does not parse emits
# `editor-callback-parse-error` (probe_engine.cpp:2316).  The WORKER already
# forwards both.  Both are gated behind `editorDiscoveryEnabled()`, which is
# false on a product profile because the builder pops `diagnostic` from the
# manifest -- so on the shipped page these events are constructed and dropped.
#
# The mirror ungates exactly those two forwards.  Named constant rather than
# `|| true` so the edit is greppable and cannot be mistaken for the shipped
# condition.
WORKER_GATE_ANCHOR = """function editorDiscoveryEnabled() {"""

WORKER_GATE_PATCHED = """// DIAGNOSTIC, finding 068.  Not shipped.  Ungates the two events below; it
// does not enable discovery, and no discovery OPERATION becomes reachable.
const DIAGNOSTIC_F068_FORWARD_STATE_EVENTS = true;
function editorDiscoveryEnabled() {"""

WORKER_PARSE_ANCHOR = """    case "editor-callback-parse-error":
      if (editorDiscoveryEnabled()) {"""

WORKER_PARSE_PATCHED = """    case "editor-callback-parse-error":
      if (editorDiscoveryEnabled() || DIAGNOSTIC_F068_FORWARD_STATE_EVENTS) {"""

EVENT_ANCHOR = """    onEvent(event) {
      if (event.event === "document-invalidated")"""

EVENT_PATCHED = """    onEvent(event) {
      // DIAGNOSTIC, finding 068.  Records only; changes no behaviour.
      {
        const diag = globalThis.__f068;
        if (diag) diag.events.push({
          label: diag.label, event: event && event.event,
          source: event && event.source,
          callbackId: event && event.callbackId,
          caretX: event && event.caret ? event.caret.x : null,
          sourceSequence: event && event.sourceSequence,
        });
      }
      if (event.event === "document-invalidated")"""

INSTALL_068 = """(() => {
globalThis.__f068 = { updates: [], paints: [], events: [], label: "boot" };
return true;
})()"""

LABEL_068 = """(() => {
if (!globalThis.__f068) return null;
globalThis.__f068.label = "ARG_LABEL";
return globalThis.__f068.label;
})()"""

READ_068 = """(() => {
const d = globalThis.__f068;
if (!d) return null;
return { updates: d.updates, paints: d.paints, events: d.events };
})()"""

INSTALL_TRACES = """(() => {
globalThis.__f067 = { traces: [] };
return true;
})()"""

READ_TRACES = """(() => {
const d = globalThis.__f067;
if (!d) return null;
// `type` is the TRACE LABEL ("commit-start", "commit-end", "beforeinput"):
// eventSnapshot() builds {type, isTrusted, inputType, data, ...extra}, so the
// label lives in `type` and `action` only exists when a caller put it in
// `extra`.  Read the wrong one and every commit-end looks like it is missing.
return d.traces.map((e) => ({
  label: e && e.type, action: e && e.action, status: e && e.status,
  requestNumber: e && e.requestNumber,
  inputType: (e && e.metadata && e.metadata.inputType) || (e && e.inputType),
  result: e && e.result ? { method: e.result.method,
                            revision: e.result.revision } : null,
}));
})()"""

INSTALL_HOOK = """(() => {
globalThis.__f064 = { renders: 0, suppressed: 0, suppress: false };
return true;
})()"""

READ_HOOK = """(() => {
const d = globalThis.__f064;
return d ? { renders: d.renders, suppressed: d.suppressed, suppress: d.suppress }
         : null;
})()"""

SET_SUPPRESS = """(() => {
if (!globalThis.__f064) return null;
globalThis.__f064.suppress = ARG_VALUE;
return globalThis.__f064.suppress;
})()"""

# What the page believes about the format, and whether the button was offered.
# Recorded, never used as the verdict: `aria-pressed` being right while the
# document is untouched IS finding 064.  It is here for one job only -- to show
# that the ON press actually asked for ON, so that "the marker has no italic"
# cannot be explained by a press that asked for OFF.
READ_BUTTON = """(() => {
const b = document.querySelector('#toolbar button[data-action="ARG_ACTION"]');
if (!b) return null;
return { pressed: b.getAttribute('aria-pressed'), offered: !b.disabled };
})()"""

# WHERE THE KEYBOARD IS POINTING.  The page routes typing through `#sink`
# (`session.attachInput(el.sink)`), and `el.sink.focus()` appears exactly ONCE in
# the whole page -- inside the canvas `pointerdown` handler.  The toolbar's click
# handler never restores it.  So this asks the one question an operator asked on
# 2026-08-22: after pressing a style button, where did the keyboard go?
READ_FOCUS = """(() => {
const a = document.activeElement;
if (!a) return null;
return { id: a.id || null, tag: a.tagName,
         action: a.dataset ? (a.dataset.action || null) : null,
         text: (a.textContent || "").trim().slice(0, 12) };
})()"""

BUTTON_BOX = """(() => {
const b = document.querySelector('ARG_SELECTOR');
if (!b) return null;
const r = b.getBoundingClientRect();
return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
})()"""

# Typing through the sink, in two variants that differ by ONE line.
#
# Every keyboard helper in run_e2_c_product_path.py calls `sink.focus()` before
# dispatching -- the harness restoring, every time, the focus a real user cannot
# get back without clicking.  That is the defect being measured here, so this
# probe needs a variant that does NOT do it.
TYPE_SINK = """(() => {
const sink = document.querySelector('#sink');
ARG_FOCUS
const target = document.activeElement || sink;
target.dispatchEvent(new InputEvent('beforeinput', {
  inputType: 'insertText', data: 'ARG_TEXT', bubbles: true, cancelable: true }));
return { dispatchedTo: target.id || target.tagName };
})()"""


# The band the caret was placed in, summed.  A caret is two columns wide and
# about thirty rows tall -- some seventy dark pixels -- while a marker of two
# dozen glyphs is thousands.  So the SUM discriminates "the tile was repainted"
# from "only the overlay moved", which matters because `updateState` calls
# `paint()` on every state update and redraws the CACHED tile plus the caret
# even when no render happened.
INK_THRESHOLD = 500        # a repaint of this marker; measured values reported


def band_ink(session, y: str) -> dict:
    ink = evaluate(session, LINE_INK.replace("ARG_Y", y)) or {}
    columns = ink.get("columns") or []
    return {"available": bool(ink.get("available")),
            "sum": sum(columns), "inkLeft": ink.get("inkLeft"),
            "inkRight": ink.get("inkRight")}


def boot(session, base, timeout):
    """A fresh page, its shims, and the hook.  One arm per page load."""
    navigate(session, base)
    booted = wait_for(session,
                      lambda s: s.get("state") in ("ready", "stopped", "expired"),
                      timeout)
    if not booted or booted.get("state") != "ready":
        return None
    evaluate(session, INSTALL)
    evaluate(session, INSTALL_HOOK)
    return booted


def commit(session, text: str, timeout=20) -> dict:
    """Type through the product's own insert field, and wait for the revision.

    Returns the revisions on both sides.  A commit that did not advance the
    revision has not happened, and every caller treats that as NOT_ESTABLISHED
    rather than as an answer.
    """
    before = revision_of(evaluate(session, READ_STATE))
    evaluate(session, SET_TEXT.replace("ARG_TEXT", text))
    evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
    settled = wait_for(session,
                       lambda s, floor=before: revision_of(s) is not None
                       and floor is not None and revision_of(s) > floor, timeout)
    return {"before": before, "after": revision_of(settled)}


def suppress(session, value: bool):
    return evaluate(session,
                    SET_SUPPRESS.replace("ARG_VALUE",
                                         "true" if value else "false"))


def instrument_control(session, base, timeout) -> dict:
    """C1: show that the flag both stops a repaint and releases it again.

    THE ARMS BELOW ARE WORTHLESS WITHOUT THIS.  A suppressed repaint and a
    repaint that never had a reason to happen look identical from the document
    side, and "nothing happened" comes back green either way -- three separate
    checks were lost to exactly that on 2026-08-21.

    Three states, on one page: commit with the render on (the band's ink must
    move), commit with it suppressed (the band must not move), then release and
    force a render (it must move again).
    """
    record: dict = {"id": "control-instrument"}
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    if not clicks:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "no line ink at y=0.24 to aim the caret at"
        return record
    place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")

    record["ink0"] = band_ink(session, "0.24")
    record["hook0"] = evaluate(session, READ_HOOK)

    suppress(session, False)
    record["visible"] = commit(session, "C064VISIBLEAAAAAAAAAAAAA")
    time.sleep(1.0)
    record["ink1"] = band_ink(session, "0.24")
    record["hook1"] = evaluate(session, READ_HOOK)

    suppress(session, True)
    record["hidden"] = commit(session, "C064HIDDENBBBBBBBBBBBBBB")
    time.sleep(1.0)
    record["ink2"] = band_ink(session, "0.24")
    record["hook2"] = evaluate(session, READ_HOOK)

    suppress(session, False)
    # Any action through `run()` repaints; a caret move changes no text, so the
    # ink that appears is the SUPPRESSED commit catching up and nothing else.
    evaluate(session, PRESS.replace("ARG_ACTION", "move-character-left"))
    time.sleep(2.0)
    record["ink3"] = band_ink(session, "0.24")
    record["hook3"] = evaluate(session, READ_HOOK)

    rendered = abs(record["ink1"]["sum"] - record["ink0"]["sum"])
    frozen = abs(record["ink2"]["sum"] - record["ink1"]["sum"])
    released = abs(record["ink3"]["sum"] - record["ink2"]["sum"])
    record["delta"] = {"rendered": rendered, "frozen": frozen,
                       "released": released, "threshold": INK_THRESHOLD}
    counters_bite = bool(
        record["hook1"] and record["hook2"] and record["hook3"]
        and record["hook1"]["renders"] > (record["hook0"] or {}).get("renders", 0)
        and record["hook2"]["suppressed"] > record["hook1"]["suppressed"]
        and record["hook2"]["renders"] == record["hook1"]["renders"]
        and record["hook3"]["renders"] > record["hook2"]["renders"])
    canvas_bites = bool(rendered >= INK_THRESHOLD and frozen < INK_THRESHOLD
                        and released >= INK_THRESHOLD)
    record["countersBite"] = counters_bite
    record["canvasBites"] = canvas_bites
    both_commits = bool(record["visible"]["after"] and record["hidden"]["after"])
    record["ok"] = bool(counters_bite and canvas_bites and both_commits)
    record["outcome"] = ("PASS" if record["ok"]
                         else "NOT_ESTABLISHED" if not both_commits else "FAIL")
    return record


def format_arm(session, base, timeout, *, arm: str, marker: str,
               suppressed: bool, save_in_slot: bool, paragraph_break: bool,
               wait_seconds: float, action: str = "set-italic",
               wait_press: bool = True) -> dict:
    """One press of set-italic, one marker typed under it, one saved ODT.

    ITALIC ONLY, and one marker per page load.  `fo:font-style="italic"` is
    unambiguous in ODF and does not need the `"none"` reading that underline and
    strikethrough do; and six markers committed at one caret coalesce into a
    single <text:span> where every later press rewrites the earlier ones
    (measured 2026-08-21, and it is in the finding).
    """
    prop = action.replace("set-", "")
    record: dict = {"id": arm, "marker": marker, "action": action, "format": prop,
                    "variables": {"suppressRender": suppressed,
                                  "saveBetween": save_in_slot,
                                  "paragraphBreak": paragraph_break,
                                  "waitSeconds": wait_seconds,
                                  "action": action,
                                  # THE QUIET GAP.  The runner does not poll
                                  # after the press; it sits silent for 1.5 s.
                                  # A probe that polls keeps messages flowing
                                  # into the engine over the same interval, and
                                  # "the harness was talking" is not a variable
                                  # anyone declared.
                                  "waitForPressRevision": wait_press}}
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    if not clicks:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "no line ink at y=0.24 to aim the caret at"
        return record
    # `past` puts the caret at the END of the line, which is where an arm that
    # declines the paragraph break has to type: into existing text, D1's shape.
    record["clicks"] = {k: clicks.get(k) for k in ("derived", "near", "past")}
    place_caret_and_settle(session, POINT_AT,
                           clicks["near"] if paragraph_break else clicks["past"],
                           "0.24")

    if paragraph_break:
        floor = revision_of(evaluate(session, READ_STATE))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
        broke = wait_for(session,
                         lambda s, f=floor: revision_of(s) is not None
                         and f is not None and revision_of(s) > f, 20)
        record["paragraphBreakRevision"] = revision_of(broke)
        if record["paragraphBreakRevision"] is None:
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = "the paragraph break did not advance the revision"
            return record

    evaluate(session, CLEAR_TOAST)
    record["buttonBefore"] = evaluate(session,
                                      READ_BUTTON.replace("ARG_ACTION", action))
    record["hookAtPress"] = evaluate(session, READ_HOOK)
    if suppressed:
        suppress(session, True)
    press_floor = revision_of(evaluate(session, READ_STATE))
    evaluate(session, PRESS.replace("ARG_ACTION", action))
    if wait_press:
        pressed = wait_for(session,
                           lambda s, f=press_floor: revision_of(s) is not None
                           and f is not None and revision_of(s) > f, 20)
        record["pressRevision"] = {"before": press_floor,
                                   "after": revision_of(pressed)}
    time.sleep(wait_seconds)
    if not wait_press:
        record["pressRevision"] = {
            "before": press_floor,
            "after": revision_of(evaluate(session, READ_STATE))}
    record["toastAfterPress"] = evaluate(session, READ_TOAST) or ""
    record["buttonAfter"] = evaluate(session,
                                     READ_BUTTON.replace("ARG_ACTION", action))

    saves = 0
    if save_in_slot:
        # D1's interleave, driven through the product's own session: the slot
        # the render occupied, occupied by a save instead.
        record["interleavedSave"] = {
            "isOdt": is_an_odt(capture_save(session, saves))}
        saves += 1

    record["hookBeforeCommit"] = evaluate(session, READ_HOOK)
    record["commit"] = commit(session, marker)
    record["hookAfterCommit"] = evaluate(session, READ_HOOK)
    if suppressed:
        suppress(session, False)

    saved = capture_save(session, saves)
    record["savedIsOdt"] = is_an_odt(saved)
    style = inline_styles_of(saved, marker) if saved else {"found": False}
    record["style"] = {k: style.get(k) for k in
                       ("found", "carrier", "styleName", "bold", "italic",
                        "underline", "strikethrough")}

    # The window, quantified rather than assumed.
    at_press = record["hookAtPress"] or {}
    at_commit = record["hookAfterCommit"] or {}
    record["window"] = {
        "renders": at_commit.get("renders", 0) - at_press.get("renders", 0),
        "suppressed": at_commit.get("suppressed", 0) - at_press.get("suppressed", 0),
    }

    # A question asked of a marker that is not in the document returns NULL.
    # `fractionNearStart: -0.229` is one day old.
    if not record["savedIsOdt"] or not style.get("found"):
        record["formatOnMarker"] = None
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the marker is not in the saved document, so whether it "
                         "carries the format has no answer")
        return record
    if record["commit"]["after"] is None:
        record["formatOnMarker"] = None
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the commit did not advance the revision"
        return record
    if (record["buttonAfter"] or {}).get("pressed") != "true":
        # Not a failure of the format to REACH the text: a press that did not
        # ask for ON cannot be read as one that did.
        record["formatOnMarker"] = style.get(prop)
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the ON press did not leave the button pressed, so this "
                         "arm did not ask for the format at all")
        return record
    if suppressed and record["window"]["renders"] != 0:
        record["formatOnMarker"] = style.get(prop)
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("a render happened inside the window this arm claims to "
                         "have suppressed")
        return record
    if not suppressed and record["window"]["renders"] < 1:
        record["formatOnMarker"] = style.get(prop)
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "no render happened in the window this arm depends on"
        return record

    record["formatOnMarker"] = style.get(prop)
    record["outcome"] = "PASS" if style.get(prop) is True else "FAIL"
    return record


def paragraph_map(saved: dict, markers: list[str]) -> dict:
    """Which paragraph each marker actually landed in.

    THE ARMS CLAIM ONE PARAGRAPH EACH.  `format_arm` presses
    insert-paragraph-break before every press precisely so that a format press
    at a collapsed caret has nothing to restyle -- and the finding records that
    fix as made.  Whether it HELD is a different question from whether it was
    written, and the eight-arm replay came back with seven of eight markers
    carrying no <text:span> at all, which is what coalescence looks like.

    So this reads the saved body as paragraphs in document order and says, for
    each marker, which one it is in.  Two markers with the same index were never
    separated.
    """
    content = saved.get("content") or ""
    if not content:
        return {"available": False, "why": "no content.xml"}
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        return {"available": False, "why": f"content.xml does not parse: {error}"}
    body = root.find("office:body/office:text", ODF_NS)
    if body is None:
        return {"available": False, "why": "no office:text"}
    paragraphs = []
    for index, node in enumerate(body.iter()):
        tag = node.tag.split("}")[-1]
        if tag not in ("p", "h"):
            continue
        paragraphs.append("".join(node.itertext()))
    where = {}
    for marker in markers:
        hits = [i for i, text in enumerate(paragraphs) if marker in text]
        where[marker] = hits[0] if len(hits) == 1 else (hits or None)
    return {"available": True, "paragraphs": len(paragraphs),
            "markerParagraph": where,
            "distinct": len({v for v in where.values() if isinstance(v, int)}),
            "expected": len(markers),
            "texts": [text for text in paragraphs
                      if any(marker in text for marker in markers)]}


def runner_sequence(session, base, timeout, *, save_each: bool = False) -> dict:
    """The product-path runner's inline block, verbatim, on one page load.

    THE FIRST RUN OF THIS PROBE FOUND THE BASELINE PASSING -- a single
    `set-italic` arm on a freshly booted page puts italic on the marker.  The
    runner's FIRST inline arm is `set-bold` and it fails, so the difference is
    not the repaint and it is not "italic versus bold" unless this says so.

    Two things separate the two shapes, and this arm collapses one of them: the
    runner runs EIGHT arms in one page load, in this order, while the probe's
    baseline runs one.  If all eight come back without their format here, the
    cause lives inside the sequence; if all eight carry it, the cause is
    upstream of the inline block, in the session state the runner has already
    built by the time it gets here.

    Deliberately a copy of the runner's `format_arm`, down to the fixed 1.5 s
    and the absence of a revision wait after the press.  A reproduction that
    tidies the thing it reproduces is not one.
    """
    record: dict = {"id": "runner-sequence", "arms": []}
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    record["clicks"] = {k: clicks.get(k) for k in ("derived", "near", "past")}
    place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")

    def arm(action: str, marker: str, wanted: bool) -> dict:
        evaluate(session, CLEAR_TOAST)
        break_before = revision_of(evaluate(session, READ_STATE))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
        wait_for(session,
                 lambda s, f=break_before: revision_of(s) is not None
                 and f is not None and revision_of(s) > f, 20)
        offered = evaluate(session, READ_BUTTON.replace("ARG_ACTION", action))
        evaluate(session, PRESS.replace("ARG_ACTION", action))
        time.sleep(1.5)
        after_press = evaluate(session, READ_BUTTON.replace("ARG_ACTION", action))
        before = revision_of(evaluate(session, READ_STATE))
        evaluate(session, SET_TEXT.replace("ARG_TEXT", marker))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
        settled = wait_for(session,
                           lambda s, f=before: revision_of(s) is not None
                           and f is not None and revision_of(s) > f, 20)
        return {"action": action, "marker": marker, "wanted": wanted,
                "buttonBefore": offered, "buttonAfter": after_press,
                "commit": {"before": before, "after": revision_of(settled)},
                "toast": evaluate(session, READ_TOAST) or ""}

    record["savesTaken"] = 0
    INLINE = [("set-bold", "bold", "SQBOLDON", "SQBOLDOFF"),
              ("set-italic", "italic", "SQITALON", "SQITALOFF"),
              ("set-underline", "underline", "SQUNDON", "SQUNDOFF"),
              ("set-strikethrough", "strikethrough", "SQSTRON", "SQSTROFF")]
    for action, prop, on_marker, off_marker in INLINE:
        for marker, wanted in ((on_marker, True), (off_marker, False)):
            entry = arm(action, marker, wanted)
            if save_each:
                # THE VERDICT AS IT STOOD AT THE MOMENT THE MARKER WAS TYPED.
                # The eight-arm replay reads every marker from ONE save taken
                # after all eight, so "the format never arrived" and "the format
                # arrived and a later arm rewrote it" are the same observation
                # there.  They are not the same defect.
                snapshot = capture_save(session, record["savesTaken"])
                record["savesTaken"] += 1
                # EVERY marker typed so far, not only this one.  Reading only
                # the newest one answers "did the format arrive" and cannot
                # answer "when did the earlier ones lose it", and those are
                # different defects with different owners.
                entry["allMarkersNow"] = {}
                for _a2, prop2, on2, off2 in INLINE:
                    for other in (on2, off2):
                        style = (inline_styles_of(snapshot, other)
                                 if snapshot else {})
                        if not style.get("found"):
                            continue
                        entry["allMarkersNow"][other] = {
                            "carrier": style.get("carrier"),
                            "styleName": style.get("styleName"),
                            prop2: style.get(prop2)}
                style = inline_styles_of(snapshot, marker) if snapshot else {}
                entry["styleWhenTyped"] = {
                    k: style.get(k) for k in
                    ("found", "carrier", "styleName", "bold", "italic",
                     "underline", "strikethrough")}
            record["arms"].append(entry)

    record["hook"] = evaluate(session, READ_HOOK)
    saved = capture_save(session, record["savesTaken"])
    record["savedIsOdt"] = is_an_odt(saved)
    verdicts = []
    for action, prop, on_marker, off_marker in INLINE:
        on_style = inline_styles_of(saved, on_marker) if saved else {"found": False}
        off_style = inline_styles_of(saved, off_marker) if saved else {"found": False}
        verdicts.append({
            "format": prop,
            "on": {"found": on_style.get("found"), prop: on_style.get(prop),
                   "styleName": on_style.get("styleName")},
            "off": {"found": off_style.get("found"), prop: off_style.get(prop),
                    "styleName": off_style.get("styleName")},
            "ok": bool(on_style.get("found") and off_style.get("found")
                       and on_style.get(prop) is True
                       and off_style.get(prop) is False),
        })
    record["verdicts"] = verdicts
    record["paragraphs"] = paragraph_map(
        saved, [m for _a, _p, on, off in INLINE for m in (on, off)])
    found_all = all(v["on"]["found"] and v["off"]["found"] for v in verdicts)
    if not record["savedIsOdt"] or not found_all:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "not every marker is in the saved document"
        return record
    record["outcome"] = "PASS" if all(v["ok"] for v in verdicts) else "FAIL"
    return record


def retention_arm(session, base, timeout) -> dict:
    """Does formatting already IN the document survive the next thing you do?

    The eight-arm replay established that each marker carries its format at the
    moment it is typed and has lost it by the end of the next arm -- exactly one
    <text:span> exists in the file at any time.  An arm bundles three actions
    (a paragraph break, a format press, a commit), so it cannot say which of
    them does it.

    This separates them.  One marker is formatted once; then the other two
    actions are performed ALONE, with a save after each, and the question asked
    of the FIRST marker every time is whether it still carries bold.

      1. break, set-bold ON, type M1        -- M1 must be bold (the precondition)
      2. break, type M2   (no press)        -- is M1 still bold?
      3. set-italic ON    (no break, no typing) -- is M1 still bold?

    Step 1 failing makes the rest NOT_ESTABLISHED: a marker that was never bold
    cannot be asked whether it stopped being bold.
    """
    record: dict = {"id": "retention", "steps": []}
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    record["clicks"] = {k: clicks.get(k) for k in ("derived", "near", "past")}
    place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")

    MARKERS = ["RETMARKONE", "RETMARKTWO", "RETMARKTHREE"]
    saves = 0

    def snapshot(label: str) -> dict:
        nonlocal saves
        saved = capture_save(session, saves)
        saves += 1
        content = (saved or {}).get("content") or ""
        row = {"after": label, "isOdt": is_an_odt(saved), "markers": {},
               # THE FILE ITSELF.  "M1 lost its bold" and "the export writes
               # exactly one span" are the same observation through
               # inline_styles_of() and are different defects with different
               # owners, so count what is actually in content.xml.
               "spans": content.count("<text:span"),
               "textStyles": content.count('style:family="text"'),
               "paragraphsWithMarker": [
                   fragment for fragment in re.findall(r"<text:[ph][ >].*?</text:[ph]>",
                                                       content, re.S)
                   if any(marker in fragment for marker in MARKERS)],
               "automaticStyles": re.findall(
                   r'<style:style style:name="[^"]*" style:family="text".*?/?>'
                   r'(?:.*?</style:style>)?', content, re.S)[:8]}
        for marker in MARKERS:
            style = inline_styles_of(saved, marker) if saved else {}
            if style.get("found"):
                row["markers"][marker] = {
                    k: style.get(k) for k in
                    ("carrier", "styleName", "bold", "italic", "underline",
                     "strikethrough")}
        record["steps"].append(row)
        return row

    def paragraph_break():
        floor = revision_of(evaluate(session, READ_STATE))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
        wait_for(session,
                 lambda s, f=floor: revision_of(s) is not None
                 and f is not None and revision_of(s) > f, 20)

    # 1 -- the precondition
    paragraph_break()
    evaluate(session, PRESS.replace("ARG_ACTION", "set-bold"))
    time.sleep(1.5)
    record["boldPressed"] = evaluate(session,
                                     READ_BUTTON.replace("ARG_ACTION", "set-bold"))
    record["commit1"] = commit(session, MARKERS[0])
    first = snapshot("break + set-bold ON + type M1")

    if not first["isOdt"] or first["markers"].get(MARKERS[0], {}).get("bold") is not True:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("M1 was not bold to begin with, so nothing here can say "
                         "it stopped being bold")
        return record

    # 2 -- a break and a commit, with NO format press
    paragraph_break()
    record["commit2"] = commit(session, MARKERS[1])
    after_typing = snapshot("break + type M2, no press")

    # 3 -- a format press, with NO break and NO typing
    evaluate(session, PRESS.replace("ARG_ACTION", "set-italic"))
    time.sleep(1.5)
    record["italicPressed"] = evaluate(
        session, READ_BUTTON.replace("ARG_ACTION", "set-italic"))
    after_press = snapshot("set-italic ON alone")

    survived_typing = after_typing["markers"].get(MARKERS[0], {}).get("bold")
    survived_press = after_press["markers"].get(MARKERS[0], {}).get("bold")
    record["m1BoldAfterTyping"] = survived_typing
    record["m1BoldAfterPress"] = survived_press
    record["culprit"] = (
        "typing/paragraph-break" if survived_typing is not True
        else "the format press" if survived_press is not True
        else "neither -- M1 kept its bold through both")
    record["outcome"] = "PASS" if survived_press is True else "FAIL"
    return record


def retention_ladder(session, base, timeout, *, click_away: bool = True) -> dict:
    """WHICH single action takes the bold off text that already has it.

    The first retention arm bundled a paragraph break with a commit and could
    only say "one of those two".  This performs the candidates ONE AT A TIME,
    with a save after each, and asks the same question of the same marker every
    time: is RETMARKONE still bold?

    The first candidate is the one that decides how big this is.  A PURE CARET
    MOVE changes no text at all -- if the bold does not survive it, then the
    bold was never IN the document: it is an attribute of the cursor that the
    exporter paints onto whatever run the cursor happens to be sitting in, and
    every "the format reached the text" result in this tree, D1's included, was
    reading the cursor rather than the document.

    Ordered cheapest-consequence first, and every step is preceded by the one
    before it -- the ladder stops meaning anything once the bold is gone, so the
    record says which step it went at.
    """
    record: dict = {"id": "retention-ladder", "clickAway": click_away,
                    "steps": []}
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    record["clicks"] = {k: clicks.get(k) for k in ("derived", "near", "past")}
    place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")

    MARKER = "RETLADDERONE"
    saves = 0

    def snapshot(label: str) -> dict:
        nonlocal saves
        saved = capture_save(session, saves)
        saves += 1
        content = (saved or {}).get("content") or ""
        style = inline_styles_of(saved, MARKER) if saved else {}
        row = {"after": label, "isOdt": is_an_odt(saved),
               "bold": style.get("bold") if style.get("found") else None,
               "carrier": style.get("carrier"), "styleName": style.get("styleName"),
               "spans": content.count("<text:span"),
               "paragraph": next(
                   (f for f in re.findall(r"<text:[ph][ >].*?</text:[ph]>",
                                          content, re.S) if MARKER in f), None)}
        record["steps"].append(row)
        return row

    def act(action: str):
        floor = revision_of(evaluate(session, READ_STATE))
        evaluate(session, PRESS.replace("ARG_ACTION", action))
        wait_for(session,
                 lambda s, f=floor: revision_of(s) is not None
                 and f is not None and revision_of(s) != f, 12)
        time.sleep(0.8)

    # The precondition: bold text, in the document, in a span.
    act("insert-paragraph-break")
    evaluate(session, PRESS.replace("ARG_ACTION", "set-bold"))
    time.sleep(1.5)
    record["commit"] = commit(session, MARKER)
    first = snapshot("break + set-bold ON + type the marker")
    if not first["isOdt"] or first["bold"] is not True:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the marker was not bold to begin with, so nothing here "
                         "can say when it stopped being bold")
        return record

    def click_elsewhere():
        """A caret placement in a DIFFERENT paragraph, through the canvas.

        The strongest form of the question.  move-character-left/right stay
        inside the run, so they cannot tell a real text attribute from one
        anchored to the cursor and merely PAINTED over whatever run the cursor
        sits in.  A click into another paragraph can: if the bold does not
        survive it, the bold was never in the document.
        """
        place_caret_and_settle(session, POINT_AT, clicks["near"], "0.62")
        time.sleep(0.8)

    LADDER = [
        # A pure caret move: no text changes, nothing is inserted or removed.
        (lambda: act("move-character-left"),
         "move the caret one character left"),
        (lambda: act("move-character-right"), "move it back"),
    ]
    if click_away:
        # THE VARIABLE.  Without these two the caret is still sitting at the end
        # of the run it just formatted when the break arrives; with them it has
        # left the run and come back to a different offset in the same line.
        LADDER += [
            (click_elsewhere, "click the caret into a different paragraph"),
            (lambda: place_caret_and_settle(session, POINT_AT,
                                            clicks["near"], "0.24"),
             "click back onto the marker's line"),
        ]
    LADDER += [(lambda: act("insert-paragraph-break"),
                "a paragraph break, alone")]
    for step, label in LADDER:
        step()
        row = snapshot(label)
        if row["bold"] is not True:
            record["lostAt"] = label
            break
    else:
        # Everything above survived; the remaining candidate is the commit.
        record["commit2"] = commit(session, "RETLADDERTWO")
        row = snapshot("type a second marker")
        if row["bold"] is not True:
            record["lostAt"] = "type a second marker"

    record["outcome"] = "FAIL" if record.get("lostAt") else "PASS"
    record["conclusion"] = (
        f"the bold left the document at: {record['lostAt']}"
        if record.get("lostAt")
        else "the bold survived every step in this ladder")
    return record


def focus_after_toolbar(session, base, timeout) -> dict:
    """After a REAL click on a style button, where is the keyboard pointing?

    Reported by an operator on 2026-08-22: "after pressing a style button the
    focus does not return to the editing surface, it stays on the button", and
    in the same breath "styles apply sometimes, mostly not, I cannot see a
    pattern".  Those may be one thing: if the keyboard is on a button, the only
    way back to the text is a canvas click -- and a canvas click MOVES THE
    CARET.

    A REAL click matters and `button.click()` will not do.  `HTMLElement.click()`
    dispatches the event without running the default action, so it does not move
    focus; a person's mousedown does.  This arm therefore drives the button
    through CDP `Input.dispatchMouseEvent`, which does run default actions --
    which makes it CHROME ONLY, and it says so rather than quietly measuring
    something else on Firefox.
    """
    record: dict = {"id": "focus-after-toolbar", "steps": []}
    call = getattr(session, "call", None)
    if call is None:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("this browser session has no CDP, so a real click "
                         "cannot be delivered and focus cannot be measured")
        return record
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")
    record["focusAfterCanvasClick"] = evaluate(session, READ_FOCUS)

    box = evaluate(session, BUTTON_BOX.replace(
        "ARG_SELECTOR", '#toolbar button[data-action="set-bold"]'))
    if not box:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the set-bold button has no box to click"
        return record
    for kind in ("mousePressed", "mouseReleased"):
        call("Input.dispatchMouseEvent",
             {"type": kind, "x": box["x"], "y": box["y"], "button": "left",
              "clickCount": 1})
    time.sleep(1.5)
    record["focusAfterButtonClick"] = evaluate(session, READ_FOCUS)
    record["buttonState"] = evaluate(session,
                                     READ_BUTTON.replace("ARG_ACTION", "set-bold"))

    before = revision_of(evaluate(session, READ_STATE))
    record["steps"].append(
        {"typed": "MKNOFOCUS", "focusRestored": False,
         "dispatch": evaluate(session, TYPE_SINK.replace("ARG_FOCUS", "")
                              .replace("ARG_TEXT", "MKNOFOCUS"))})
    settled = wait_for(session,
                       lambda s, f=before: revision_of(s) is not None
                       and f is not None and revision_of(s) > f, 6)
    record["steps"][-1]["revision"] = {"before": before,
                                       "after": revision_of(settled)}

    # POSITIVE CONTROL: the same dispatch with focus restored must land.  If it
    # does not, this arm measured nothing and says so.
    before = revision_of(evaluate(session, READ_STATE))
    record["steps"].append(
        {"typed": "MKREFOCUS", "focusRestored": True,
         "dispatch": evaluate(session,
                              TYPE_SINK.replace("ARG_FOCUS", "sink.focus();")
                              .replace("ARG_TEXT", "MKREFOCUS"))})
    settled = wait_for(session,
                       lambda s, f=before: revision_of(s) is not None
                       and f is not None and revision_of(s) > f, 10)
    record["steps"][-1]["revision"] = {"before": before,
                                       "after": revision_of(settled)}

    saved = capture_save(session, 0)
    record["savedIsOdt"] = is_an_odt(saved)
    content = (saved or {}).get("content") or ""
    record["inDocument"] = {"MKNOFOCUS": "MKNOFOCUS" in content,
                            "MKREFOCUS": "MKREFOCUS" in content}

    control_ok = bool(record["savedIsOdt"] and record["inDocument"]["MKREFOCUS"])
    focus = record["focusAfterButtonClick"] or {}
    record["keyboardLeftTheText"] = focus.get("action") == "set-bold"
    if not control_ok:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the positive control did not land -- typing through "
                         "the sink WITH focus restored did not reach the "
                         "document, so nothing here can be read")
        return record
    record["outcome"] = "FAIL" if record["keyboardLeftTheText"] else "PASS"
    record["conclusion"] = (
        "after a real click the keyboard is on the button, not the text; the "
        "only way back is a canvas click, which moves the caret"
        if record["keyboardLeftTheText"]
        else "focus stayed on the editing surface")
    return record


def click_between_format_and_typing(session, base, timeout) -> dict:
    """Does the canvas click a person MUST make discard the pending format?

    The consequence half of `focus-after-toolbar`, and it needs no CDP: press
    the format button, then either type straight away or click the canvas first
    -- the click being the only thing that returns the keyboard to the text.

    One variable. Two page loads.
    """
    record: dict = {"id": "click-between-format-and-typing", "arms": []}

    def one(click_first: bool, marker: str) -> dict:
        arm = {"clickedCanvasFirst": click_first, "marker": marker}
        if not boot(session, base, timeout):
            arm["outcome"] = "NOT_ESTABLISHED"
            arm["why"] = "the page did not reach ready"
            return arm
        clicks = caret_click_fractions(
            evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
        arm["clicks"] = {k: clicks.get(k) for k in ("derived", "near", "past")}
        place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")
        floor = revision_of(evaluate(session, READ_STATE))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
        wait_for(session,
                 lambda s, f=floor: revision_of(s) is not None
                 and f is not None and revision_of(s) > f, 20)
        evaluate(session, PRESS.replace("ARG_ACTION", "set-bold"))
        time.sleep(1.5)
        arm["buttonAfterPress"] = evaluate(
            session, READ_BUTTON.replace("ARG_ACTION", "set-bold"))
        if click_first:
            # The gesture a person is FORCED into: click back onto the text to
            # get the keyboard there.
            place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")
        arm["commit"] = commit(session, marker)
        saved = capture_save(session, 0)
        arm["savedIsOdt"] = is_an_odt(saved)
        style = inline_styles_of(saved, marker) if saved else {}
        arm["style"] = {k: style.get(k) for k in
                        ("found", "carrier", "styleName", "fromParagraphStyle",
                         "bold")}
        if not arm["savedIsOdt"] or not style.get("found"):
            arm["outcome"] = "NOT_ESTABLISHED"
            arm["why"] = "the marker is not in the saved document"
            return arm
        arm["outcome"] = "PASS" if style.get("bold") is True else "FAIL"
        return arm

    record["arms"].append(one(False, "MKNOCLICK"))
    record["arms"].append(one(True, "MKAFTERCLICK"))
    straight, clicked = record["arms"][0], record["arms"][1]
    if straight.get("outcome") != "PASS":
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("typing straight after the press did not produce bold "
                         "either, so the click cannot be blamed for anything")
    else:
        record["outcome"] = "FAIL" if clicked.get("outcome") == "FAIL" else "PASS"
        record["conclusion"] = (
            "the canvas click a person must make to type discards the pending "
            "format" if clicked.get("outcome") == "FAIL"
            else "the format survives the click")
    return record


def real_enter(session, base, timeout) -> dict:
    """Does a REAL Enter key do anything to the document?

    From the operator's 2026-08-21 round: the two ODTs saved either side of a
    keyboard Enter had **byte-identical** content.xml.  That round could not
    tell "Enter is dead" from "the keyboard is dead", because finding 066 had
    the focus sitting on a toolbar button the whole time.  066 is fixed, so the
    question is now askable.

    A REAL key, through CDP `Input.dispatchKeyEvent`, for the same reason 066
    needed a real click: only a real key runs the default action that produces
    `beforeinput` with `inputType: "insertParagraph"`, which is what the input
    adapter turns into `commitText("\n")`.

    POSITIVE CONTROL, and the whole arm depends on it: after the Enter, more
    text is typed.  If that text does not arrive either, the keyboard is dead
    and this arm has measured nothing about Enter.
    """
    record: dict = {"id": "real-enter"}
    call = getattr(session, "call", None)
    if call is None:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "no CDP, so a real key cannot be delivered"
        return record
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    record["clicks"] = {k: clicks.get(k) for k in ("derived", "near")}
    place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")
    record["focus"] = evaluate(session, READ_FOCUS)

    record["before"] = commit(session, "ENTBEFORE")
    saved_before = capture_save(session, 0)
    record["savedBeforeIsOdt"] = is_an_odt(saved_before)

    floor = revision_of(evaluate(session, READ_STATE))
    for kind in ("rawKeyDown", "char", "keyUp"):
        payload = {"type": kind, "key": "Enter", "windowsVirtualKeyCode": 13,
                   "nativeVirtualKeyCode": 13, "code": "Enter"}
        if kind == "char":
            payload["text"] = "\r"
        call("Input.dispatchKeyEvent", payload)
    settled = wait_for(session,
                       lambda s, f=floor: revision_of(s) is not None
                       and f is not None and revision_of(s) > f, 8)
    record["enterRevision"] = {"before": floor, "after": revision_of(settled)}
    record["toastAfterEnter"] = evaluate(session, READ_TOAST) or ""
    saved_after = capture_save(session, 1)
    record["savedAfterIsOdt"] = is_an_odt(saved_after)

    # The positive control.
    record["control"] = commit(session, "ENTAFTER")
    saved_control = capture_save(session, 2)

    def paragraphs(saved):
        content = (saved or {}).get("content") or ""
        if not content:
            return None
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return None
        return sum(1 for n in root.iter()
                   if n.tag.split("}")[-1] in ("p", "h"))

    record["paragraphs"] = {
        "beforeEnter": paragraphs(saved_before),
        "afterEnter": paragraphs(saved_after),
        "afterControl": paragraphs(saved_control),
    }
    a = (saved_before or {}).get("content") or ""
    b = (saved_after or {}).get("content") or ""
    record["contentIdentical"] = bool(a) and a == b
    record["controlLanded"] = "ENTAFTER" in ((saved_control or {}).get("content") or "")

    if not record["controlLanded"]:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the control text did not reach the document either, "
                         "so the keyboard is not working and nothing here says "
                         "anything about Enter")
        return record
    moved = (record["paragraphs"]["afterEnter"] is not None
             and record["paragraphs"]["beforeEnter"] is not None
             and record["paragraphs"]["afterEnter"]
             > record["paragraphs"]["beforeEnter"])
    record["outcome"] = "PASS" if moved else "FAIL"
    record["conclusion"] = (
        "a real Enter adds a paragraph" if moved
        else "a real Enter changes nothing in the document, while typing on "
             "either side of it works")
    return record


def caret_model_or_drawing(session, base, timeout) -> dict:
    """Is the caret in the WRONG PLACE, or just DRAWN in the wrong place?

    Operator, 2026-08-22: "the caret should be after the text, but it is before
    the last character."

    That could be two very different defects, and separating them costs one
    save.  If the caret's MODEL position were one character to the left, then
    text typed next would land one character to the left -- so the second thing
    typed would appear BEFORE the last character of the first.  If the document
    comes back with the two runs contiguous and in order, the model is right and
    what is wrong is the drawing.

    The document is the oracle here, not the canvas, and deliberately: pixels
    are what the report is about, but pixels cannot tell these two apart and the
    document can.
    """
    record: dict = {"id": "caret-model-or-drawing"}
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    record["clicks"] = {k: clicks.get(k) for k in ("derived", "near", "past")}
    if not clicks.get("derived"):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the line's ink was not found, so the caret was aimed "
                         "at a viewport fraction and this arm cannot say where "
                         "it landed")
        return record
    place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")

    # An empty paragraph, so nothing else on the line can be confused for the
    # typed runs.
    floor = revision_of(evaluate(session, READ_STATE))
    evaluate(session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
    wait_for(session,
             lambda s, f=floor: revision_of(s) is not None
             and f is not None and revision_of(s) > f, 20)

    record["first"] = commit(session, "CARETONE")
    record["second"] = commit(session, "CARETTWO")
    saved = capture_save(session, 0)
    record["savedIsOdt"] = is_an_odt(saved)
    content = (saved or {}).get("content") or ""
    record["contiguousInOrder"] = "CARETONECARETTWO" in content
    record["bothPresent"] = "CARETONE" in content and "CARETTWO" in content
    # What a caret one character to the left would produce.
    record["secondLandedInsideFirst"] = "CARETONCARETTWOE" in content
    for tag in ("CARETONE", "CARETTWO"):
        index = content.find(tag)
        record.setdefault("context", {})[tag] = (
            content[max(0, index - 40):index + 40] if index >= 0 else None)

    if not record["savedIsOdt"] or not record["bothPresent"]:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "one of the two runs is not in the saved document"
        return record
    record["outcome"] = "PASS" if record["contiguousInOrder"] else "FAIL"
    record["conclusion"] = (
        "the caret's MODEL position is correct -- the second run follows the "
        "first exactly -- so what the operator saw is the caret being DRAWN in "
        "the wrong place, not being in the wrong place"
        if record["contiguousInOrder"]
        else "the second run did not follow the first: the caret's model "
             "position is wrong, not merely its drawing")
    return record


def keyboard_formats(session, base, timeout) -> dict:
    """All four inline formats, pressed with a REAL click and typed on the KEYBOARD.

    This is the operator's second round, automated -- and it only became
    possible once finding 066 was fixed.  Before that the real click parked the
    keyboard on the button and nothing typed afterwards reached the document at
    all, which is what "styles apply sometimes, mostly not" was.

    Two things make it the user's path rather than the harness's:

      * a REAL click through CDP, because `HTMLElement.click()` runs no default
        action and would not exercise the focus behaviour at all;
      * typing through `#sink`'s `beforeinput` with NOTHING restoring focus --
        every keyboard helper in run_e2_c_product_path.py opens with
        `sink.focus()`, and that line is what hid 066.

    The shipped inline-format check drives the "insert text" field instead
    (`session.commitText`), which never touches the keyboard.  So this asks a
    question nothing else in the tree asks.

    Each arm gets its own paragraph, its own clear-format, and its own save.
    """
    record: dict = {"id": "keyboard-formats", "arms": []}
    call = getattr(session, "call", None)
    if call is None:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "no CDP, so a real click cannot be delivered"
        return record
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    record["clicks"] = {k: clicks.get(k) for k in ("derived", "near")}
    place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")

    def real_click(selector: str) -> bool:
        box = evaluate(session, BUTTON_BOX.replace("ARG_SELECTOR", selector))
        if not box:
            return False
        for kind in ("mousePressed", "mouseReleased"):
            call("Input.dispatchMouseEvent",
                 {"type": kind, "x": box["x"], "y": box["y"],
                  "button": "left", "clickCount": 1})
        time.sleep(1.2)
        return True

    saves = 0
    for action, prop, marker in (("set-bold", "bold", "KBBOLD"),
                                 ("set-italic", "italic", "KBITALIC"),
                                 ("set-underline", "underline", "KBUNDER"),
                                 ("set-strikethrough", "strikethrough",
                                  "KBSTRIKE")):
        arm = {"action": action, "format": prop, "marker": marker}
        floor = revision_of(evaluate(session, READ_STATE))
        real_click('#toolbar button[data-action="insert-paragraph-break"]')
        wait_for(session,
                 lambda s, f=floor: revision_of(s) is not None
                 and f is not None and revision_of(s) > f, 20)
        # A clean slate: the caret carries formats forward, so without this each
        # arm would inherit the one before it.
        real_click("#clear-format")
        time.sleep(1.0)
        arm["buttonBefore"] = evaluate(
            session, READ_BUTTON.replace("ARG_ACTION", action))
        real_click(f'#toolbar button[data-action="{action}"]')
        arm["focusAfterPress"] = evaluate(session, READ_FOCUS)
        arm["buttonAfter"] = evaluate(
            session, READ_BUTTON.replace("ARG_ACTION", action))

        before = revision_of(evaluate(session, READ_STATE))
        arm["dispatch"] = evaluate(
            session, TYPE_SINK.replace("ARG_FOCUS", "").replace("ARG_TEXT", marker))
        settled = wait_for(session,
                           lambda s, f=before: revision_of(s) is not None
                           and f is not None and revision_of(s) > f, 12)
        arm["commit"] = {"before": before, "after": revision_of(settled)}

        saved = capture_save(session, saves)
        saves += 1
        arm["savedIsOdt"] = is_an_odt(saved)
        style = inline_styles_of(saved, marker) if saved else {}
        arm["style"] = {k: style.get(k) for k in
                        ("found", "carrier", "styleName", "fromParagraphStyle",
                         prop)}
        if not arm["savedIsOdt"] or not style.get("found"):
            arm["outcome"] = "NOT_ESTABLISHED"
            arm["why"] = ("the marker never reached the document, so whether it "
                          "carries the format has no answer")
        elif (arm["buttonAfter"] or {}).get("pressed") != "true":
            arm["outcome"] = "NOT_ESTABLISHED"
            arm["why"] = "the press did not leave the button on, so this arm did not ask for the format"
        else:
            arm["outcome"] = "PASS" if style.get(prop) is True else "FAIL"
        record["arms"].append(arm)

    judged = [a for a in record["arms"] if a["outcome"] in ("PASS", "FAIL")]
    if len(judged) != len(record["arms"]):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "at least one arm could not be measured"
    else:
        record["outcome"] = ("PASS" if all(a["outcome"] == "PASS" for a in judged)
                             else "FAIL")
    record["conclusion"] = ", ".join(
        f"{a['format']}={a['outcome']}" for a in record["arms"])
    return record


# THE CARET BY ITS COLOUR, in one read.
#
# `paint()` fills the caret with `#1a1a1a` = rgb(26,26,26) exactly
# (web/e2-editor-app.js), while the glyphs arrive inside the engine's tile.  So
# the caret can be isolated without pairing two reads at all -- which matters,
# because pairing is what defeated the first four attempts at this: the page
# borders are full-band-height strokes that differ between reads and swamp a
# caret that is a couple of columns wide.
#
# Reported as three separate populations so the reader can see the separation
# rather than trust a threshold: exact caret grey, near-black glyph ink, and
# everything else dark.
CARET_BY_COLOUR = """(() => {
const canvas = document.querySelector('#canvas');
const y = Math.floor(canvas.height * ARG_Y) - 24;
const h = 58;
if (y < 0 || y + h > canvas.height) return { available: false };
const data = canvas.getContext('2d').getImageData(0, y, canvas.width, h).data;
const caret = new Array(canvas.width).fill(0);
const glyph = new Array(canvas.width).fill(0);
for (let row = 0; row < h; row += 1) {
  for (let x = 0; x < canvas.width; x += 1) {
    const i = (row * canvas.width + x) * 4;
    const r = data[i], g = data[i+1], b = data[i+2], a = data[i+3];
    if (a < 128) continue;
    if (r === 26 && g === 26 && b === 26) caret[x] += 1;
    else if (r < 110 && g < 110 && b < 110) glyph[x] += 1;
  }
}
const cols = (arr) => arr.reduce((out, v, x) => (v ? out.concat([[x, v]]) : out), []);
return { available: true, width: canvas.width, band: { y, h },
         caretColumns: cols(caret), glyphColumns: cols(glyph) };
})()"""


def caret_columns_when_painted(session, y: str, timeout: float = 20) -> dict:
    """`CARET_COLUMNS`, waited for, and it is NOT `LINE_INK`.

    `caret_from_columns` needs `band: {y, h}` to tell glyphs from the page
    border -- a glyph never fills every row of a band that includes the line
    spacing, a border does.  `LINE_INK` does not carry `band`, so feeding it in
    makes `height` 0, the filter reject every column, and the helper answer
    "the band carries no text ink" on a band full of text.  Measured here on
    2026-08-22, twice, before reading the helper's own source.

    Two readers whose outputs look alike and are not interchangeable: the field
    that distinguishes them is the one nobody looks at.
    """
    deadline = time.monotonic() + timeout
    read: dict = {}
    previous: list | None = None
    while time.monotonic() < deadline:
        read = evaluate(session, CARET_COLUMNS.replace("ARG_Y", y)) or {}
        columns = read.get("columns") or []
        if read.get("available") and any(columns):
            # TWO IDENTICAL READS IN A ROW, not one that merely has ink.
            #
            # A single read can land mid-repaint.  The first version of this
            # took one, and the two reads it produced differed by FULL
            # BAND-HEIGHT strokes at columns 13/14 and 710/711 -- the page
            # borders, present in one and absent in the other.  Those swamp the
            # caret, which is a fraction of that height, and the arm then
            # reports nonsense about a caret that moved 280 columns to the
            # right when it was asked to go left.
            if previous is not None and columns == previous:
                return read
            previous = columns
        time.sleep(0.4)
    return read


# THE CARET IS THE ONLY THING THE PAGE DRAWS.
#
# Everything else on the canvas arrives inside the engine's tile.  `paint()`
# fills the caret with `#1a1a1a` = rgb(26,26,26) exactly, and the selection wash
# with #b7d3f2 under `multiply`.  So an exact (26,26,26) pixel is the page's own
# ink -- and this scans the WHOLE canvas for it rather than a band, which is
# what defeated five earlier attempts: banding needs a y guess, and pairing two
# banded reads gets swamped by the page borders (full-band-height strokes that
# differ between reads).
#
# Anti-aliasing of black-on-white does produce the odd exact (26,26,26) pixel --
# four of them, measured, on a canvas with no caret in the band.  A caret is a
# SOLID rectangle a few columns wide and tens of rows tall, so the two
# populations separate on "how many such pixels does this column hold": noise is
# ones and twos, a caret is tens.  The threshold is reported next to the data so
# a reader can see the separation instead of trusting it.
#
# Scanned in strips: this canvas is sized to the document and can be tens of
# thousands of rows, and one getImageData over all of it is hundreds of
# megabytes.
CARET_PIXELS = """(() => {
const canvas = document.querySelector('#canvas');
const context = canvas.getContext('2d');
const width = canvas.width, height = canvas.height;
const STRIP = 512;
const caretPerColumn = new Array(width).fill(0);
const glyphPerColumn = new Array(width).fill(0);
let caretTop = null, caretBottom = null;
let glyphTop = null, glyphBottom = null;
for (let top = 0; top < height; top += STRIP) {
  const rows = Math.min(STRIP, height - top);
  const data = context.getImageData(0, top, width, rows).data;
  for (let row = 0; row < rows; row += 1) {
    for (let x = 0; x < width; x += 1) {
      const i = (row * width + x) * 4;
      if (data[i + 3] < 128) continue;
      const r = data[i], g = data[i + 1], b = data[i + 2];
      if (r === 26 && g === 26 && b === 26) {
        caretPerColumn[x] += 1;
        const y = top + row;
        if (caretTop === null || y < caretTop) caretTop = y;
        if (caretBottom === null || y > caretBottom) caretBottom = y;
      } else if (r < 110 && g < 110 && b < 110) {
        glyphPerColumn[x] += 1;
        const y = top + row;
        if (glyphTop === null || y < glyphTop) glyphTop = y;
        if (glyphBottom === null || y > glyphBottom) glyphBottom = y;
      }
    }
  }
}
const columns = (arr, floor) => arr.reduce(
  (out, v, x) => (v >= floor ? out.concat([[x, v]]) : out), []);
// The WHOLE-CANVAS dark profile as well.  Exact-colour matching finds nothing
// because the caret is `Math.round(scaleX * 15)` = ONE pixel wide at this
// scale and sits at a fractional x, so `fillRect` anti-aliases it across two
// columns and no pixel is ever exactly (26,26,26).  A difference between two
// whole-canvas profiles cancels the static glyphs and leaves the caret --
// provided the page borders are stable, which is checked rather than assumed.
const scale = { widthTwips: null, caretWidthPx: null };
return { available: true, width, height,
         caretColumns: columns(caretPerColumn, 1),
         caretRows: { top: caretTop, bottom: caretBottom },
         glyphRows: { top: glyphTop, bottom: glyphBottom },
         darkPerColumn: glyphPerColumn.map((v, x) => v + caretPerColumn[x]),
         scale };
})()"""


def line_ink_when_painted(session, y: str, timeout: float = 20) -> dict:
    """`LINE_INK`, but waited for rather than hoped for.

    A bare read can land before the canvas has been painted -- or before a
    repaint that an edit triggered has finished -- and then it reports no ink.
    Downstream that becomes `derived: false` and a caret aimed at a viewport
    fraction, which is exactly the degradation that made one arm of the
    2026-08-21 retention ladder unusable as a control.

    So this waits for the signal instead of sleeping for a guess, and returns
    the last read either way so the caller can say NOT_ESTABLISHED with the
    numbers in hand.
    """
    deadline = time.monotonic() + timeout
    read: dict = {}
    while time.monotonic() < deadline:
        read = evaluate(session, LINE_INK.replace("ARG_Y", y)) or {}
        if read.get("available"):
            return read
        time.sleep(0.4)
    return read


def caret_drawn_where(session, base, timeout) -> dict:
    """WHERE, in columns, is the caret drawn after typing?

    The other half of operator observation 1, and the model half is already
    settled: typing twice at one caret produces contiguous, in-order text
    (`caret-model-or-drawing`), so the model is right and the drawing is what is
    wrong.  A screenshot on 2026-08-22 shows the caret sitting between the last
    two characters of `CARETHERE`.  This puts a number on it.

    Method, and it needs no reference image: read the band, move the caret one
    character left, read it again.  The text does not move between the reads, so
    the column that LOST ink is where the caret was after typing and the column
    that GAINED it is where it went -- `caret_from_columns` exists for exactly
    this and reports the text's own ink extent from the columns inked in BOTH.

    Typed at the END of an existing line rather than in a fresh paragraph, so
    the band is one this probe already knows how to find and `inkRight` is the
    right edge of the text that was just typed.

    POSITIVE CONTROL: both strokes must be non-zero.  A caret that was not
    located in one of the reads makes `argmin` return column 0 by tie-break, and
    that index is not a position -- the same trap that let
    `the-caret-lands-where-the-click-was` pass at -0.229 on 2026-08-21.
    """
    record: dict = {"id": "caret-drawn-where"}
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    ink = line_ink_when_painted(session, "0.24")
    clicks = caret_click_fractions(ink)
    record["clicks"] = {k: clicks.get(k) for k in ("derived", "near", "past")}
    if not clicks.get("derived"):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the line's ink was not found, so nothing here is aimed"
        return record
    place_caret_and_settle(session, POINT_AT, clicks["past"], "0.24")

    # LONG ENOUGH THAT THE MOVES STAY ON THE LINE.  With a nine-character
    # marker, five moves and then five more walk off the front of the line and
    # the "caret" is found at the page border -- measured, and the advance that
    # came out of it (23px) contradicted the marker's own width (88px for nine
    # characters).  Twice MOVES must be comfortably less than the marker.
    MARKER = "CARETRULERABCDEFGHIJKLMN"
    record["commit"] = commit(session, MARKER)
    if record["commit"]["after"] is None:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the marker did not reach the document"
        return record
    after_typing = caret_columns_when_painted(session, "0.24")
    # The colour read, taken at the same moment and answering the same question
    # without pairing anything.
    by_colour = evaluate(session, CARET_BY_COLOUR.replace("ARG_Y", "0.24")) or {}
    caret_cols = [x for x, _ in (by_colour.get("caretColumns") or [])]
    glyph_cols = [x for x, _ in (by_colour.get("glyphColumns") or [])]
    record["byColour"] = {
        "available": by_colour.get("available"),
        "caretColumns": by_colour.get("caretColumns"),
        "glyphInkLeft": min(glyph_cols) if glyph_cols else None,
        "glyphInkRight": max(glyph_cols) if glyph_cols else None,
        "glyphColumnCount": len(glyph_cols),
    }
    if caret_cols and glyph_cols:
        caret_x = sum(caret_cols) / len(caret_cols)
        record["byColour"]["caretCentre"] = caret_x
        record["byColour"]["offsetFromGlyphEnd"] = caret_x - max(glyph_cols)

    # FIVE characters, not one.  One character is a ~14px stroke moving ~14px,
    # and the first attempt at this could not separate it from repaint noise:
    # three columns changed in the whole band and the extrema were a full-height
    # stroke at column 14 and a 14-row stroke at 294, which is not a caret
    # moving one place.  Five moves put the two caret positions far enough apart
    # that the pairing is unambiguous, and the advance is then the distance
    # divided by five rather than a single small difference.
    MOVES = 5
    for _ in range(MOVES):
        evaluate(session, PRESS.replace("ARG_ACTION", "move-character-left"))
        time.sleep(0.5)
    time.sleep(1.0)
    after_move = caret_columns_when_painted(session, "0.24")

    def summarise(read):
        cols = read.get("columns") or []
        return {"available": read.get("available"), "inkLeft": read.get("inkLeft"),
                "inkRight": read.get("inkRight"), "width": read.get("width"),
                "inkedColumns": sum(1 for c in cols if c),
                "sum": sum(cols)}

    record["readAfterTyping"] = summarise(after_typing)
    record["readAfterMove"] = summarise(after_move)
    # THE DELTAS THEMSELVES, not just their extrema.  `caret_from_columns`
    # reports argmin/argmax, and this tree already knows that an index from a
    # tie-break is not a position -- so when the extrema do not look like a
    # caret moving one character, the data has to be readable without them.
    ca, cb = after_typing.get("columns") or [], after_move.get("columns") or []
    if ca and cb and len(ca) == len(cb):
        deltas = [(x, cb[x] - ca[x]) for x in range(len(ca)) if cb[x] != ca[x]]
        deltas.sort(key=lambda item: item[1])
        record["deltas"] = {
            "changedColumns": len(deltas),
            "mostNegative": deltas[:8],
            "mostPositive": deltas[-8:][::-1],
            "bandHeight": (after_typing.get("band") or {}).get("h"),
        }
    record["canvasBefore"] = {"width": ink.get("width")}
    columns = caret_from_columns(after_typing, after_move)
    record["columns"] = columns
    if not columns.get("available"):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = columns.get("why") or "the band carries no text ink"
        return record
    caret_typed = columns.get("caretAfterClickNearStart")
    caret_moved = columns.get("caretAfterClickPastEnd")
    if caret_typed is None or caret_moved is None:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the caret was not located in one of the two reads "
                         f"(strokes {columns.get('strokeLost')} / "
                         f"{columns.get('strokeGained')}), and an index that "
                         "came from a tie-break is not a position")
        return record

    # One character, measured rather than assumed: the caret moved exactly one
    # character left between the reads, so the distance between the two caret
    # columns IS this font's advance width at this scale.
    advance = (caret_typed - caret_moved) / MOVES
    record["measured"] = {
        "caretAfterTyping": caret_typed,
        "caretAfterOneLeft": caret_moved,
        "characterAdvancePx": advance,
        "movesLeft": MOVES,
        "textInkRight": columns.get("inkRight"),
        "textInkLeft": columns.get("inkLeft"),
        "offsetFromTextEnd": caret_typed - columns.get("inkRight"),
        "offsetInCharacters": (round((caret_typed - columns.get("inkRight"))
                                     / advance, 2) if advance else None),
    }
    # Did anything OTHER than the caret change?  A full-band-height stroke is a
    # page border, never a glyph and never a caret in a band that includes the
    # line spacing.  If one of those moved between the reads, the canvas was not
    # stable and the pairing of lost/gained columns means nothing.
    band_height = (after_typing.get("band") or {}).get("h") or 0
    borders = [item for item in (record.get("deltas") or {}).get("mostNegative", [])
               + (record.get("deltas") or {}).get("mostPositive", [])
               if band_height and abs(item[1]) >= band_height]
    record["borderColumnsThatMoved"] = sorted({item[0] for item in borders})
    if record["borderColumnsThatMoved"]:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the canvas was not stable between the two reads: "
                         f"full-band-height strokes changed at columns "
                         f"{record['borderColumnsThatMoved']}, which are page "
                         "borders, not the caret. Nothing here can be paired")
        return record
    if advance <= 0:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("moving the caret left did not move the drawn caret to "
                         "the left, so the advance width is not measured and "
                         "the offset cannot be expressed in characters")
        return record

    # The caret belongs at the insertion point, which is past the last glyph.
    # Half an advance of tolerance either way: a caret drawn ON the last glyph's
    # right edge is right, one drawn a whole character back is the report.
    ok = caret_typed >= columns["inkRight"] - advance / 2
    record["outcome"] = "PASS" if ok else "FAIL"
    record["conclusion"] = (
        "the caret is drawn at the end of the typed text"
        if ok else
        f"the caret is drawn {record['measured']['offsetInCharacters']} "
        f"characters from the end of the text it should be sitting after")
    return record


def enter_insert_method(session, base, timeout) -> dict:
    """WHICH route did the engine take for the newline, and did it claim success?

    Finding 067 half two.  `handleInsertText` (src/probe_engine.cpp:2730-2755)
    tries LOK's `paste` and falls back to `postKeyEvent`, then increments the
    revision **unconditionally** and reports `{"type":"inserted"}`.  Its reply
    already carries `method`, which says which route ran -- and nothing forwards
    it anywhere a probe can read.  So this mirrors the page's `onInputTrace` to
    record what it is already being handed.

    It answers a question the fix does not: whether `paste("\n")` was ACCEPTED
    and did nothing, or was refused and the fallback did nothing.  Those are
    different upstream stories and the engine half should not be specified
    without knowing which.
    """
    record: dict = {"id": "enter-insert-method"}
    call = getattr(session, "call", None)
    if call is None:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "no CDP, so a real Enter cannot be delivered"
        return record
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record
    evaluate(session, INSTALL_TRACES)

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")

    # A control first: ordinary text through the same boundary, so the trace
    # shape is known to be readable before the interesting key is pressed.
    record["controlCommit"] = commit(session, "MTHCONTROL")
    time.sleep(1.0)
    record["tracesAfterControl"] = evaluate(session, READ_TRACES)

    def press_enter(shift: bool):
        floor = revision_of(evaluate(session, READ_STATE))
        for kind in ("rawKeyDown", "char", "keyUp"):
            payload = {"type": kind, "key": "Enter",
                       "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13,
                       "code": "Enter", "modifiers": 8 if shift else 0}
            if kind == "char":
                payload["text"] = "\r"
            call("Input.dispatchKeyEvent", payload)
        wait_for(session,
                 lambda s, f=floor: revision_of(s) is not None
                 and f is not None and revision_of(s) > f, 8)
        time.sleep(1.0)
        return evaluate(session, READ_TRACES) or []

    def input_types(entries):
        return sorted({e.get("inputType") for e in entries if e.get("inputType")})

    plain = press_enter(False)
    record["traces"] = plain
    record["plainEnterInputTypes"] = input_types(plain)
    # SHIFT+ENTER.  The routing design turns on this: in a <textarea> the
    # browser may report BOTH as insertLineBreak, and then `inputType` alone
    # cannot say which key the user pressed -- so a fix cannot offer the
    # paragraph break and the line break as different things from the keyboard.
    evaluate(session, INSTALL_TRACES)
    shifted = press_enter(True)
    record["shiftEnterInputTypes"] = input_types(shifted)
    record["shiftTraces"] = shifted
    record["distinguishable"] = (
        record["plainEnterInputTypes"] != record["shiftEnterInputTypes"]
        if record["plainEnterInputTypes"] and record["shiftEnterInputTypes"]
        else None)
    traces = plain

    ends = [e for e in traces if e.get("label") == "commit-end" and e.get("result")]
    record["commitEnds"] = ends
    # PAIR BY requestNumber.  `commit-end` is traced with a null event, so it
    # carries no inputType of its own -- only `commit-start` does.  Filtering
    # the ends on inputType therefore matches nothing and reads as "the Enter
    # never reached the commit boundary", which is the opposite of the truth.
    starts = {e.get("requestNumber"): e.get("inputType")
              for e in traces if e.get("label") == "commit-start"}
    enter = [e for e in ends
             if starts.get(e.get("requestNumber")) in ("insertParagraph",
                                                       "insertLineBreak")]
    record["enterCommit"] = enter[-1] if enter else None
    if record["enterCommit"]:
        record["enterCommit"] = dict(
            record["enterCommit"],
            inputType=starts.get(record["enterCommit"].get("requestNumber")))
    control_readable = any(e.get("result", {}).get("method") for e in ends)
    if not control_readable:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("no commit-end trace carried a `method`, so the mirror "
                         "is not reading what it claims to read")
        return record
    if not record["enterCommit"]:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the Enter produced no commit at all -- it never "
                         "reached the adapter's commit boundary")
        return record
    record["method"] = record["enterCommit"]["result"].get("method")
    record["outcome"] = "PASS"
    record["conclusion"] = (
        f"the newline went through the engine's `{record['method']}` route and "
        f"the engine reported revision {record['enterCommit']['result'].get('revision')}")
    return record


# The text's right edge on a given band of ROWS, excluding the page's own caret
# colour.  Paired with CARET_PIXELS so both are measured on the same rows.
GLYPH_RIGHT_ON_ROWS = """(() => {
const canvas = document.querySelector('#canvas');
const top = ARG_TOP, bottom = ARG_BOTTOM;
if (top === null || bottom === null) return null;
const rows = bottom - top + 1;
const width = canvas.width;
const data = canvas.getContext('2d').getImageData(0, top, width, rows).data;
let left = null, right = null, count = 0;
for (let x = 0; x < width; x += 1) {
  let dark = 0;
  for (let row = 0; row < rows; row += 1) {
    const i = (row * width + x) * 4;
    if (data[i + 3] < 128) continue;
    const r = data[i], g = data[i + 1], b = data[i + 2];
    if (r === 26 && g === 26 && b === 26) continue;   // the page's caret
    if (r < 110 && g < 110 && b < 110) dark += 1;
  }
  // A glyph never fills every row of the caret's band; the page border does.
  if (dark > 0 && dark < rows) {
    if (left === null) left = x;
    right = x;
    count += 1;
  }
}
return { inkLeft: left, inkRight: right, inkedColumns: count, rows };
})()"""


# Which ROWS are dark in a named column.  Two columns that changed between two
# reads are only caret positions if they are on the SAME LINE and about as tall
# as each other; a two-row difference and a fifteen-row one are not the same
# kind of thing, and the column index alone cannot say so.
COLUMN_ROWS = """(() => {
const canvas = document.querySelector('#canvas');
const x = ARG_X, width = canvas.width, height = canvas.height;
const data = canvas.getContext('2d').getImageData(x, 0, 1, height).data;
const rows = [];
for (let y = 0; y < height; y += 1) {
  const i = y * 4;
  if (data[i + 3] >= 128 && data[i] < 110 && data[i+1] < 110 && data[i+2] < 110)
    rows.push(y);
}
const runs = [];
for (const y of rows) {
  const last = runs[runs.length - 1];
  if (last && y === last[1] + 1) last[1] = y;
  else runs.push([y, y]);
}
return { column: x, darkRows: rows.length, runs: runs.slice(0, 12) };
})()"""


# Every column holding a run of consecutive dark rows at least ARG_MIN long.
#
# A caret is a solid vertical stroke; a glyph stem in this font at this scale is
# about eleven rows and the caret is fifteen, so a floor between them separates
# them.  This asks WHERE THE CARET IS without differencing anything -- which
# matters, because the caret right after typing leaves no difference at all.
TALL_RUNS = """(() => {
const canvas = document.querySelector('#canvas');
const width = canvas.width, height = canvas.height, MIN = ARG_MIN;
const out = [];
const STRIP = 512;
const runStart = new Array(width).fill(-1);
const runLen = new Array(width).fill(0);
for (let top = 0; top < height; top += STRIP) {
  const rows = Math.min(STRIP, height - top);
  const data = canvas.getContext('2d').getImageData(0, top, width, rows).data;
  for (let row = 0; row < rows; row += 1) {
    for (let x = 0; x < width; x += 1) {
      const i = (row * width + x) * 4;
      const dark = data[i + 3] >= 128 && data[i] < 110
                   && data[i + 1] < 110 && data[i + 2] < 110;
      if (dark) {
        if (runLen[x] === 0) runStart[x] = top + row;
        runLen[x] += 1;
      } else {
        if (runLen[x] >= MIN) out.push([x, runStart[x], runLen[x]]);
        runLen[x] = 0;
      }
    }
  }
}
for (let x = 0; x < width; x += 1)
  if (runLen[x] >= MIN) out.push([x, runStart[x], runLen[x]]);
return { minimum: MIN, runs: out };
})()"""


def caret_pixels(session, base, timeout) -> dict:
    """Where is the caret DRAWN, in canvas columns, and is that after the text?

    Finding 068's open half.  The model side is settled -- typing twice at one
    caret produces contiguous, in-order text -- so what is left is the drawing,
    and an operator has now reported it twice, two days apart, with a
    screenshot.

    Five earlier attempts failed and each failure is written into the finding.
    This one drops the two things that defeated them: it does not band (no y
    guess) and it does not pair two reads (nothing for the page borders to
    swamp).  It isolates the caret by the one property nothing else on the
    canvas has -- the page draws it, in a colour of its own.

    POSITIVE CONTROL: the caret must MOVE when asked to.  A column of caret-
    coloured pixels that sits still under `move-character-left` is not a caret,
    and the arm says so rather than reporting its position.
    """
    record: dict = {"id": "caret-pixels"}
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record

    ink = line_ink_when_painted(session, "0.24")
    clicks = caret_click_fractions(ink)
    record["clicks"] = {k: clicks.get(k) for k in ("derived", "near", "past")}
    if not clicks.get("derived"):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the line's ink was not found, so nothing here is aimed"
        return record
    # `past`, not `near`: breaking at the END of a line leaves the new paragraph
    # EMPTY, so the marker is the only thing on its line and the line's right
    # edge IS the marker's right edge.  Breaking mid-line brings the remainder
    # along -- measured in the earlier arms of this probe, where marker
    # paragraphs came back as `CARETHERE1-LC-NUMBER-ONE` -- and then the ink
    # span is not the marker's and every number derived from it is wrong.
    place_caret_and_settle(session, POINT_AT, clicks["past"], "0.24")

    # An empty paragraph, so the line the caret ends up on carries the marker
    # and nothing else.
    floor = revision_of(evaluate(session, READ_STATE))
    evaluate(session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
    wait_for(session,
             lambda s, f=floor: revision_of(s) is not None
             and f is not None and revision_of(s) > f, 20)

    # LONG ENOUGH THAT THE MOVES STAY ON THE LINE.  With a nine-character
    # marker, five moves and then five more walk off the front of it and the
    # "caret" is found at the page border -- measured, and the advance that came
    # out of it (23px) contradicted the marker's own width (88px for nine
    # characters).  Twice MOVES must be comfortably less than the marker.
    MARKER = "CARETRULERABCDEFGHIJKLMN"
    # TYPED ON THE KEYBOARD, not through the insert field.  `commit()` drives
    # the page's "insert text" field and button; the operator who reported this
    # typed.  Those are different paths -- the gap that produced findings 066
    # and 067 in one night -- so this arm takes the one the report came from.
    before_typing = revision_of(evaluate(session, READ_STATE))
    record["dispatch"] = evaluate(
        session, TYPE_SINK.replace("ARG_FOCUS", "sink.focus();")
        .replace("ARG_TEXT", MARKER))
    settled = wait_for(session,
                       lambda s, f=before_typing: revision_of(s) is not None
                       and f is not None and revision_of(s) > f, 12)
    record["commit"] = {"before": before_typing, "after": revision_of(settled)}
    if record["commit"]["after"] is None:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the marker did not reach the document"
        return record
    # THE PRECONDITION, checked rather than assumed: the marker must be alone in
    # its paragraph, or the line's ink is not the marker's ink.
    saved = capture_save(session, 0)
    paragraphs = []
    content = (saved or {}).get("content") or ""
    if content:
        try:
            root = ElementTree.fromstring(content)
            paragraphs = ["".join(n.itertext()) for n in root.iter()
                          if n.tag.split("}")[-1] in ("p", "h")]
        except ElementTree.ParseError:
            paragraphs = []
    record["markerParagraph"] = next(
        (para for para in paragraphs if MARKER in para), None)
    if record["markerParagraph"] != MARKER:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the marker is not alone in its paragraph "
                         f"({record['markerParagraph']!r}), so the line's ink "
                         "span is not the marker's and no advance can be "
                         "derived from it")
        return record
    time.sleep(1.5)

    def scan(label: str) -> dict:
        read = evaluate(session, CARET_PIXELS) or {}
        columns = read.get("caretColumns") or []
        solid = [(x, n) for x, n in columns if n >= 8]
        return {"label": label, "width": read.get("width"),
                "height": read.get("height"),
                "caretRows": read.get("caretRows"),
                "glyphRows": read.get("glyphRows"),
                "allCaretColumns": columns,
                "solidColumns": solid,
                "noiseColumns": [(x, n) for x, n in columns if n < 8],
                "darkPerColumn": read.get("darkPerColumn") or []}

    # SUPPRESS THE REPAINT BETWEEN THE TWO READS.
    #
    # Without this the delta is unreadable: a caret move goes through `run()`,
    # which repaints, and a fresh paintTile anti-aliases slightly differently
    # everywhere -- 686 of 725 columns changed, measured, swamping a caret that
    # is one column wide.  With `renderDocument` suppressed, `updateState` still
    # calls `paint()`, which redraws the CACHED tile (byte-identical) plus the
    # caret at its new place.  So the only thing that can differ between the two
    # reads is the caret.
    #
    # This is the same hook the very first arm of this probe installed, used for
    # the opposite purpose: there it asked whether a repaint destroyed
    # formatting, here it holds the background still so a one-pixel mark can be
    # seen against it.
    record["hookBefore"] = evaluate(session, READ_HOOK)
    suppress(session, True)
    after_typing = scan("after typing")
    record["afterTyping"] = after_typing
    # WHERE IS THE CARET RIGHT NOW -- asked directly, not by differencing.
    # A glyph stem in this font at this scale runs about eleven rows and the
    # caret fifteen, so a floor of thirteen separates them.
    record["tallRunsAfterTyping"] = evaluate(
        session, TALL_RUNS.replace("ARG_MIN", "13"))

    MOVES = 5
    for _ in range(MOVES):
        evaluate(session, PRESS.replace("ARG_ACTION", "move-character-left"))
        time.sleep(0.4)
    time.sleep(1.0)
    after_move = scan("after five moves left")
    record["afterMove"] = after_move
    record["tallRunsAfterMove"] = evaluate(
        session, TALL_RUNS.replace("ARG_MIN", "13"))
    record["hookAfter"] = evaluate(session, READ_HOOK)
    suppress(session, False)

    # POSITIVE CONTROL for the suppression itself: renders must not have
    # advanced across the window, and the flag must have bitten at least once.
    before_hook = record["hookBefore"] or {}
    after_hook = record["hookAfter"] or {}
    record["renderWindow"] = {
        "renders": after_hook.get("renders", 0) - before_hook.get("renders", 0),
        "suppressed": after_hook.get("suppressed", 0)
                      - before_hook.get("suppressed", 0),
    }
    if record["renderWindow"]["renders"] != 0 \
            or record["renderWindow"]["suppressed"] < 1:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the repaint was not held still between the two reads "
                         f"({record['renderWindow']}), so the difference "
                         "between them is not the caret alone")
        return record

    # THE VERDICT IS BUILT ON THE DIRECT OBSERVATION, not on a difference.
    #
    # Five earlier attempts tried to locate the caret by differencing two reads,
    # and every one of them abstained: the caret is `Math.round(scaleX * 15)` =
    # ONE pixel wide at this scale, drawn at a fractional x, so it never lands
    # on an exact colour, and a fresh paintTile re-anti-aliases the whole canvas
    # so the difference is noise everywhere.  Suppressing the repaint fixed the
    # noise, and then the differencing still could not see the caret after
    # typing -- because there is nothing there to see.
    #
    # So: ask each read directly which columns hold a run of dark rows tall
    # enough to be a caret.  A glyph in this font at this scale runs about
    # eleven rows and the caret fifteen.
    runs_typed = {tuple(r) for r in
                  (record.get("tallRunsAfterTyping") or {}).get("runs") or []}
    runs_moved = {tuple(r) for r in
                  (record.get("tallRunsAfterMove") or {}).get("runs") or []}
    record["tallRunDiff"] = {
        "onlyAfterTyping": sorted(runs_typed - runs_moved),
        "onlyAfterMove": sorted(runs_moved - runs_typed),
    }

    # The caret after the move is the run that appears; it is also the POSITIVE
    # CONTROL, because a caret that never appears anywhere means the scan
    # cannot see carets at all and nothing below may be read.
    appeared = record["tallRunDiff"]["onlyAfterMove"]
    if len(appeared) != 1:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the caret did not appear as exactly one new tall run "
                         f"when it was moved ({appeared}), so this scan cannot "
                         "see the caret and its silence elsewhere means nothing")
        return record
    caret_column, caret_top, caret_len = appeared[0]
    record["caretAfterMove"] = {"column": caret_column, "top": caret_top,
                                "rows": caret_len}

    band = (caret_top, caret_top + caret_len - 1)
    record["caretBand"] = band
    on_band = sorted(r for r in runs_typed if band[0] - 4 <= r[1] <= band[1] + 4)
    record["tallRunsOnThatLineAfterTyping"] = on_band

    record["textOnCaretRows"] = evaluate(
        session, GLYPH_RIGHT_ON_ROWS.replace("ARG_TOP", str(band[0]))
        .replace("ARG_BOTTOM", str(band[1])))
    text = record["textOnCaretRows"] or {}
    left, right = text.get("inkLeft"), text.get("inkRight")
    record["measured"] = {
        "caretColumnAfterMove": caret_column,
        "caretRows": caret_len,
        "movesLeft": MOVES,
        "textInkLeft": left,
        "textInkRight": right,
        "caretWidthPx": 1,
    }
    if left is not None and right is not None and right > left:
        advance = (right - left) / (len(MARKER) - 1)
        record["measured"]["characterAdvancePx"] = round(advance, 2)
        record["measured"]["expectedCaretAfterMove"] = round(
            right - MOVES * advance, 1)
        record["measured"]["caretAfterMoveIsWhereExpected"] = (
            abs(caret_column - (right - MOVES * advance)) <= advance)

    if not on_band:
        record["outcome"] = "FAIL"
        record["conclusion"] = (
            "AFTER TYPING THERE IS NO CARET ON THAT LINE AT ALL -- not one "
            "column in the band holds a caret-height run -- and the very same "
            f"scan finds one at column {caret_column} as soon as the caret is "
            "moved. The caret is not redrawn when text is committed; it appears "
            "only once a caret action runs")
        return record
    record["outcome"] = "PASS"
    record["conclusion"] = (
        f"a caret-height run is present on that line after typing: {on_band}")
    return record



def caret_state_after_commit(session, base, timeout) -> dict:
    """Finding 068: WHICH of the three conditions withholds the caret?

    The pixels already said WHAT happens -- no caret-height run on that line
    after typing, exactly one after a caret move.  What a missing pixel cannot
    say is WHY, because `paint()` has four ways to draw nothing and they all
    look identical on a canvas:

      1. it returned early with no cached tiles;
      2. it returned early with no editorState or no document;
      3. `editorState.caret` was absent;
      4. `selection.collapsed` was exactly `false`, which suppresses the caret
         on purpose so a range highlight does not get a caret painted in it.

    So this arm asks the page instead of the canvas.  Every state update
    records what the snapshot held, every `paint()` records which of the four
    it took, and both are labelled with the step that caused them.

    THE POSITIVE CONTROL IS THE MOVE, and it is not optional: if no `paint()`
    reports `drew-caret` after the move either, the instrument never saw a
    caret at all and its silence after the commit means nothing.  That is the
    same discipline the pixel arm needed and for the same reason.
    """
    record: dict = {"id": "caret-state-after-commit"}
    if not boot(session, base, timeout):
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the page did not reach ready"
        return record
    if evaluate(session, INSTALL_068) is not True:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "the finding 068 hook did not install"
        return record

    clicks = caret_click_fractions(
        evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
    evaluate(session, LABEL_068.replace("ARG_LABEL", "click"))
    place_caret_and_settle(session, POINT_AT, clicks["near"], "0.24")

    # A caret must be drawable BEFORE anything is typed, or the arm is measuring
    # a page that never draws one.
    evaluate(session, LABEL_068.replace("ARG_LABEL", "after-click"))
    time.sleep(0.6)

    evaluate(session, LABEL_068.replace("ARG_LABEL", "commit"))
    record["commit"] = commit(session, "CARETSTATE")
    time.sleep(1.5)

    evaluate(session, LABEL_068.replace("ARG_LABEL", "move"))
    evaluate(session, PRESS.replace("ARG_ACTION", "move-character-left"))
    time.sleep(1.5)

    seen = evaluate(session, READ_068) or {}
    record["updates"] = seen.get("updates") or []
    record["paints"] = seen.get("paints") or []
    record["events"] = seen.get("events") or []
    record["hook"] = evaluate(session, READ_HOOK)

    def paints(label):
        return [p for p in record["paints"] if p.get("label") == label]

    def updates(label):
        return [u for u in record["updates"] if u.get("label") == label]

    record["byLabel"] = {
        label: {
            "paints": [p.get("why") for p in paints(label)],
            "caretInState": [bool(u.get("caret")) for u in updates(label)],
            "caretX": [(u.get("caret") or {}).get("x") for u in updates(label)],
            "collapsed": [u.get("collapsed") for u in updates(label)],
            "sourceSequence": [u.get("sourceSequence") for u in updates(label)],
            # THE ANSWER TO THE REMEDY QUESTION.  Each engine state change names
            # the callback that caused it, so "visible-cursor" appearing (or
            # not) between the commit and the next step is the discriminator
            # that `sourceSequence` alone cannot be.
            "callbackSources": [e.get("source") for e in record["events"]
                                if e.get("label") == label
                                and e.get("event") == "editor-state"],
            "parseErrors": [e.get("callbackId") for e in record["events"]
                            if e.get("label") == label
                            and e.get("event") == "editor-callback-parse-error"],
            "documentChangeSequence": [u.get("documentChangeSequence")
                                       for u in updates(label)],
        }
        for label in ("click", "after-click", "commit", "move")
    }

    drew_after_move = any(p.get("why") == "drew-caret" for p in paints("move"))
    if not drew_after_move:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("no paint() drew a caret after the move either, so "
                         "this instrument never saw the page draw one and its "
                         "silence after the commit means nothing")
        return record

    commit_paints = [p.get("why") for p in paints("commit")]
    record["drewAfterCommit"] = "drew-caret" in commit_paints

    # WHERE it drew, which is the question the first run of this arm replaced
    # the original one with.  "A caret was drawn" was never the interesting
    # half: the page draws whatever rectangle the engine last reported, so a
    # drawn caret at an unchanged x is a STALE caret, and on a canvas that is
    # indistinguishable from a caret drawn in the wrong place.
    def last_x(label):
        xs = [x for x in record["byLabel"][label]["caretX"] if x is not None]
        return xs[-1] if xs else None

    before, after, moved = (last_x("click"), last_x("commit"), last_x("move"))
    record["caretX"] = {"beforeCommit": before, "afterCommit": after,
                        "afterMove": moved}
    if before is None or after is None or moved is None:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = "one of the three steps reported no caret x at all"
        return record

    # The positive control for STALENESS, distinct from the one for drawing:
    # the move must change x, or this arm cannot detect an x that fails to
    # change and its silence about the commit means nothing.
    if moved == after:
        record["outcome"] = "NOT_ESTABLISHED"
        record["why"] = ("the caret x did not change on the move either, so "
                         "this arm cannot see the caret x move at all")
        return record

    record["caretMovedOnCommit"] = after != before
    if record["drewAfterCommit"] and record["caretMovedOnCommit"]:
        record["outcome"] = "PASS"
        record["conclusion"] = (
            "paint() drew a caret after the commit and its x had moved, so the "
            "caret follows typed text")
        return record

    if record["drewAfterCommit"] and not record["caretMovedOnCommit"]:
        seqs = record["byLabel"]["commit"]
        record["outcome"] = "FAIL"
        record["conclusion"] = (
            f"a caret WAS drawn after the commit, at x={after} -- exactly where "
            f"it was before the commit ({before}) -- and one caret action then "
            f"moved it to {moved}. The page is not declining to draw; the "
            "engine is reporting the pre-commit rectangle. On a canvas a stale "
            "caret and a mis-drawn caret look the same, which is why this is "
            "read from the state and not from pixels.")
        record["callbackEvidence"] = {
            "sourceSequence": seqs["sourceSequence"],
            "documentChangeSequence": seqs["documentChangeSequence"],
            "readAs": "equal values mean the tile invalidation was the only "
                      "callback that arrived, so no cursor callback came at "
                      "all; different values mean one came and did not move "
                      "the rectangle",
        }
        return record

    # WHICH of the four, named.  This is the whole point of the arm.
    reasons = sorted(set(commit_paints))
    record["outcome"] = "FAIL"
    record["whyNotDrawn"] = reasons
    record["conclusion"] = (
        "after the commit paint() ran " + str(len(commit_paints))
        + " time(s) and drew no caret; the reason(s) it recorded: "
        + (", ".join(reasons) if reasons else "none -- paint() never ran at all")
        + ". The same instrument reports drew-caret after the move.")
    return record


ARMS: dict[str, dict] = {
    # P-064-0.  The negative control: this must reproduce 064.
    "baseline": {"marker": "MKF064BASE", "suppressed": False,
                 "save_in_slot": False, "paragraph_break": True,
                 "wait_seconds": 1.5},
    # P-064-1.  The prediction under test.
    "suppressed": {"marker": "MKF064SUPP", "suppressed": True,
                   "save_in_slot": False, "paragraph_break": True,
                   "wait_seconds": 1.5},
    # P-064-2.  D1's shape, on the product path.
    "save-in-slot": {"marker": "MKF064SAVE", "suppressed": True,
                     "save_in_slot": True, "paragraph_break": True,
                     "wait_seconds": 1.5},
    # The ladder, run only if P-064-1 fails.  One variable each.
    "no-break": {"marker": "MKF064NOBR", "suppressed": False,
                 "save_in_slot": False, "paragraph_break": False,
                 "wait_seconds": 1.5},
    "no-wait": {"marker": "MKF064NOWT", "suppressed": False,
                "save_in_slot": False, "paragraph_break": True,
                "wait_seconds": 0.1},
    # The two things that separate the passing isolated arm from the runner's
    # failing FIRST arm.  One variable each.
    "iso-bold": {"marker": "MKF064BOLD", "suppressed": False,
                 "save_in_slot": False, "paragraph_break": True,
                 "wait_seconds": 1.5, "action": "set-bold"},
    # Same italic arm that passed, with the polling removed: nothing touches
    # the page between the press and the commit, which is what the runner does.
    "iso-quiet": {"marker": "MKF064QUIET", "suppressed": False,
                  "save_in_slot": False, "paragraph_break": True,
                  "wait_seconds": 1.5, "wait_press": False},
    # If the quiet gap is the variable, its LENGTH should behave like a timer.
    "quiet-0s2": {"marker": "MKF064Q02", "suppressed": False,
                  "save_in_slot": False, "paragraph_break": True,
                  "wait_seconds": 0.2, "wait_press": False},
    "quiet-0s6": {"marker": "MKF064Q06", "suppressed": False,
                  "save_in_slot": False, "paragraph_break": True,
                  "wait_seconds": 0.6, "wait_press": False},
    "quiet-3s0": {"marker": "MKF064Q30", "suppressed": False,
                  "save_in_slot": False, "paragraph_break": True,
                  "wait_seconds": 3.0, "wait_press": False},
}

DEFAULT_ARMS = ["baseline", "suppressed", "save-in-slot"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--arms", default=",".join(DEFAULT_ARMS),
                        help="comma-separated: runner-sequence, " + ", ".join(ARMS))
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--out", default=None, help="write the report here as JSON")
    args = parser.parse_args()

    wanted = [name.strip() for name in args.arms.split(",") if name.strip()]
    unknown = [name for name in wanted
               if name not in ARMS
               and name not in ("runner-sequence", "runner-sequence-saved",
                                "retention", "retention-ladder",
                                "retention-ladder-adjacent",
                                "focus-after-toolbar",
                                "click-between-format-and-typing",
                                "real-enter", "caret-model-or-drawing",
                                "keyboard-formats", "caret-drawn-where",
                                "enter-insert-method", "caret-pixels",
                                "caret-state-after-commit")]
    if unknown:
        raise SystemExit(f"unknown arm(s): {unknown}; known: {sorted(ARMS)}")

    root = PROJECT / "dist"
    page_rel = "e2-editor-app.js"
    page_text = (root / page_rel).read_text(encoding="utf-8")
    if page_text.count(RENDER_ANCHOR) != 1:
        raise SystemExit(
            "renderDocument's head is not where this diagnostic expects it in "
            + page_rel + "; the tree moved under the diagnostic. Fix the anchor "
            "rather than patching blindly -- a hook that lands in the wrong "
            "function measures nothing and looks green.")

    scratch = Path(tempfile.mkdtemp(prefix="f064-mechanism-"))
    mirror = scratch / "root"
    if page_text.count(TRACE_ANCHOR) != 1:
        raise SystemExit(
            "the page's onInputTrace is not where this diagnostic expects it in "
            + page_rel + "; the tree moved under the diagnostic.")
    # FINDING 068's four anchors, each checked for EXACTLY ONE occurrence.
    # A patch that silently fails to apply produces a probe that records
    # nothing and reports it as "the condition never fired" -- the same shape
    # as a real absence, and green.
    for name, anchor in (("the page's onEvent", EVENT_ANCHOR),
                         ("the state-update tail", STATE_ANCHOR),
                         ("paint()'s head", PAINT_ANCHOR),
                         ("paint()'s editorState guard", PAINT_ANCHOR_2),
                         ("paint()'s caret branch", PAINT_ANCHOR_3)):
        if page_text.count(anchor) != 1:
            raise SystemExit(
                f"{name} is not where finding 068's diagnostic expects it in "
                + page_rel + f" (found {page_text.count(anchor)}); the tree "
                "moved under the diagnostic. Fix the anchor rather than "
                "patching blindly.")

    patched = (page_text.replace(RENDER_ANCHOR, RENDER_PATCHED, 1)
               .replace(TRACE_ANCHOR, TRACE_PATCHED, 1)
               .replace(STATE_ANCHOR, STATE_PATCHED, 1)
               .replace(PAINT_ANCHOR, PAINT_PATCHED, 1)
               .replace(PAINT_ANCHOR_2, PAINT_PATCHED_2, 1)
               .replace(PAINT_ANCHOR_3, PAINT_PATCHED_3, 1)
               .replace(EVENT_ANCHOR, EVENT_PATCHED, 1))
    # And the patches must have LANDED.  Counting anchors before is not the
    # same claim: `.replace` on an anchor that overlaps another patch's output
    # can consume it.
    for marker in ("globalThis.__f068", "note068(", "no-caret-in-state"):
        if marker not in patched:
            raise SystemExit(f"finding 068's patch did not land: {marker!r} is "
                             "absent from the mirrored page")
    # The worker is the SECOND mirrored file, and it has to be: the two events
    # that answer finding 068's remaining question are built in the engine,
    # forwarded by the worker, and dropped there on a product profile.  Patching
    # only the page would record an empty list and read as "no callback ever
    # arrived" -- the very answer under test, arrived at by not listening.
    worker_rel = "profiles/e2-editor-v3/sdk-worker.js"
    # SUBSTITUTED FROM SOURCE, and this is declared in the report.
    #
    # The v3 profile's copy of the worker is FROZEN -- it is one of the five
    # identities that profile binds, and rebuilding the profile to refresh it
    # would rewrite the manifest and unbind round two's evidence.  So finding
    # 068's remedy, which lives in the worker, cannot be tested by rebuilding
    # anything.  The mirror runs the SOURCE worker against the frozen wasm
    # instead: probe.wasm is untouched and byte-identical, and the worker is
    # the file under test.
    #
    # The fix ships for real in the v4 profile, whose builder will hash
    # whichever worker is in the tree at link time.
    worker_source = PROJECT / "sdk" / "sdk-worker.js"
    worker_text = worker_source.read_text(encoding="utf-8")
    # `editor-state` is no longer in this list, and its absence is the FIX:
    # finding 068's remedy made that forward unconditional in the shipped
    # worker, so there is nothing left to ungate.  If this probe still patched
    # it, the patch would fail to match and the anchor check would refuse --
    # which is the check working, not a regression.
    for name, anchor in (("the discovery gate", WORKER_GATE_ANCHOR),
                         ("the parse-error forward", WORKER_PARSE_ANCHOR)):
        if worker_text.count(anchor) != 1:
            raise SystemExit(
                f"{name} is not where finding 068's diagnostic expects it in "
                + worker_rel + f" (found {worker_text.count(anchor)})")
    worker_patched = (worker_text
                      .replace(WORKER_GATE_ANCHOR, WORKER_GATE_PATCHED, 1)
                      .replace(WORKER_PARSE_ANCHOR, WORKER_PARSE_PATCHED, 1))
    if worker_patched.count("DIAGNOSTIC_F068_FORWARD_STATE_EVENTS") != 2:
        raise SystemExit("finding 068's worker patch did not land twice")
    build_mirror(root, mirror, {page_rel: patched.encode("utf-8"),
                                worker_rel: worker_patched.encode("utf-8")})

    report: dict = {
        "schemaVersion": 1,
        "release": "f064-mechanism",
        "evidenceClass": "diagnostic",
        "finding": "064",
        "browser": args.browser,
        "note": "This run did NOT use the shipped page. It answers ONE named "
                "question -- whether the repaint the product performs between a "
                "format action and the next commit is what stops the format "
                "reaching the text -- and it is not a product measurement.",
        "prediction": "findings/evidence/064/"
                      "PREDICTION-render-between-format-and-typing.md",
        "mirrored": [page_rel, worker_rel],
        "workerSubstitutedFromSource": str(worker_source.relative_to(PROJECT)),
        "hook": "renderDocument() counts its calls and returns early while "
                "globalThis.__f064.suppress is true; inert when __f064 is absent",
        "whyInsideRenderDocument":
            "the page has a second render source -- onEvent schedules a repaint "
            "on document-invalidated (web/e2-editor-app.js:768-769) -- so a "
            "diagnostic at the run() call site (line 382) would leave a render "
            "running and report a false negative",
        "eliminatedBySourceReading": [
            "an extra editor.getState() between the press and the typing: "
            "_drain takes `result?.state ||` first (editor-shell/"
            "editor-session.js:301-302) and NarrowEditorV2Client rejects a "
            "result without `state` (editor-shell-v2/"
            "narrow-editor-v2-client.js:117), so the format action never "
            "reaches the fallback",
            "the engine's format barrier: its targets are the list and "
            "paragraph-style commands (src/probe_engine.cpp:1224-1241); the "
            "four inline actions take the plain uno-command-result route",
            "the insert call itself: session.commitText() ends at "
            "document.insertText (editor-shell/editor-session.js:511), which is "
            "the call D1 makes",
        ],
        "wasmUnchanged": True,
        "profileWasmSha256": sha256_file(
            root / "profiles" / "e2-editor-v3" / "probe.wasm"),
        "shims": ["URL.createObjectURL",
                  "HTMLAnchorElement.prototype.click (download anchors)",
                  "#toast.textContent cleared between steps",
                  "globalThis.__f064, this probe's own counter and flag"],
        "arms": [],
    }
    report["servedShell"] = served_shell_identity(mirror)

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(mirror)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")

        control = instrument_control(session, base, args.timeout)
        report["control"] = control

        for name in wanted:
            if name == "caret-drawn-where":
                report["arms"].append(
                    caret_drawn_where(session, base, args.timeout))
                continue
            if name == "keyboard-formats":
                report["arms"].append(
                    keyboard_formats(session, base, args.timeout))
                continue
            if name == "caret-pixels":
                report["arms"].append(caret_pixels(session, base, args.timeout))
                continue
            if name == "caret-state-after-commit":
                report["arms"].append(
                    caret_state_after_commit(session, base, args.timeout))
                continue
            if name == "caret-model-or-drawing":
                report["arms"].append(
                    caret_model_or_drawing(session, base, args.timeout))
                continue
            if name == "enter-insert-method":
                report["arms"].append(
                    enter_insert_method(session, base, args.timeout))
                continue
            if name == "real-enter":
                report["arms"].append(real_enter(session, base, args.timeout))
                continue
            if name == "focus-after-toolbar":
                report["arms"].append(
                    focus_after_toolbar(session, base, args.timeout))
                continue
            if name == "click-between-format-and-typing":
                report["arms"].append(
                    click_between_format_and_typing(session, base, args.timeout))
                continue
            if name in ("retention-ladder", "retention-ladder-adjacent"):
                arm_record = retention_ladder(
                    session, base, args.timeout,
                    click_away=name == "retention-ladder")
                arm_record["id"] = name
                report["arms"].append(arm_record)
                continue
            if name == "retention":
                report["arms"].append(retention_arm(session, base, args.timeout))
                continue
            if name in ("runner-sequence", "runner-sequence-saved"):
                arm_record = runner_sequence(
                    session, base, args.timeout,
                    save_each=name == "runner-sequence-saved")
                arm_record["id"] = name
                report["arms"].append(arm_record)
                continue
            report["arms"].append(
                format_arm(session, base, args.timeout, arm=name, **ARMS[name]))
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:                # noqa: BLE001 -- teardown
                pass
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    # The verdict, and it refuses to speak when the instrument did not bite.
    by_id = {arm["id"]: arm for arm in report["arms"]}
    if not report["control"].get("ok"):
        report["verdict"] = ("NOT_ESTABLISHED: the instrument was not shown to "
                             "bite, so no arm below means anything")
    elif by_id.get("baseline") and by_id["baseline"]["outcome"] != "FAIL":
        report["verdict"] = (
            "NOT_ESTABLISHED: the baseline did not reproduce finding 064 on the "
            f"mirrored page (outcome {by_id['baseline']['outcome']}), so nothing "
            "else in this run may be read")
    elif "suppressed" in by_id:
        suppressed_arm = by_id["suppressed"]
        if suppressed_arm["outcome"] == "PASS":
            report["verdict"] = (
                "P-064-1 HOLDS: with the repaint suppressed across the "
                "press-to-commit window the format reaches the text. Finding "
                "064 is product-side and its remedy is a shell change")
        elif suppressed_arm["outcome"] == "FAIL":
            report["verdict"] = (
                "P-064-1 FAILS: suppressing the repaint changes nothing. The "
                "repaint is not the mechanism; run the ladder (no-break, "
                "no-wait) before saying anything about which layer owns this")
        else:
            report["verdict"] = (
                "NOT_ESTABLISHED: the suppressed arm could not be measured -- "
                + str(suppressed_arm.get("why")))
    else:
        report["verdict"] = "no verdict: the suppressed arm was not run"

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
