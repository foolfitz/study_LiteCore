#!/usr/bin/env python3
"""Drive the E2-C product page down the paths a USER takes, not the ones a
harness takes.

Why this exists
---------------
On 2026-08-16 three product defects were found in one day, by a person, in the
D5 operator round -- and not one of them was reachable by any automated round
this tree had:

  * finding 049: the product's own save button wrote 15 bytes of
    "[object Object]".  Every harness calls `session.save()` itself and
    destructures `{bytes}`, so every harness measured the SHELL's save and none
    of them ever pressed the button.
  * finding 050: every IME commit after the first in a session was rejected as a
    buffer mismatch.  Every harness calls `session.commitText()` directly, so
    none of them ever went through the adapter's composition path, and none of
    them ever typed a SECOND time.
  * Ctrl+C never asked the engine for the selection.  Nothing called
    `copySelection()`; the shell had it all along.

The shape they share is one sentence: **where the harness's path and the user's
path differ, only the user's path is unmeasured.**  This runner closes that gap
for the three known shapes and leaves a place to add the next one.

What this is NOT
----------------
The events here are synthesised, so `isTrusted` is false throughout.  **This is
not D5 and no cell may cite it.**  D5's entire subject is trusted input and
needs a human; this is a regression net underneath it.  What the two have in
common is only the path -- the product's own handlers.

Declared shims (SPEC E2-C 6: a harness that patches the page it observes says so
where the evidence can see it):

  * `URL.createObjectURL` -- the product saves by handing a Blob to a download
    link, and nothing outside the page can read a download.
  * `HTMLAnchorElement.prototype.click` for anchors carrying `download` -- so a
    headless browser is never asked to open a save dialog, which would block
    every subsequent command.  What this leaves unmeasured is the download
    plumbing itself (href/download/click); an operator established that by hand
    on 2026-08-16 (findings/evidence/049/verified-by-operator/).
  * `#toast.textContent` is cleared before a step, so that "the product said
    nothing" is distinguishable from "the product said something earlier".

Being able to fail
------------------
`--mutate` reintroduces one of the three defects into a symlink mirror of dist/
(dist itself is never written) and requires the matching check to go RED while
the others stay green.  A check that cannot be shown to fail is not a check --
this tree has recorded that lesson often enough to build it into the tool.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_long_document import build as build_long_document  # noqa: E402
from e1_support import sha256 as sha256_file  # noqa: E402
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from validate_e1_c import shell_bundle_digest  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

# The three texts committed through the composition path.  Distinct, and absent
# from every fixture, so finding them in the saved ODT is a statement about this
# run.
IME_TEXTS = ["甲一", "乙二", "丙三"]

# The marker the insert button types.  Distinct from IME_TEXTS and absent from
# every fixture, so finding it in a saved ODT is a statement about the press
# that put it there.
# Checks that are RED for a real, filed defect rather than for anything this run
# did.  Declared here so a mutation round is not confounded by them -- and
# declared with the finding, because "known failure" without a name is how a red
# check becomes wallpaper.  `finish()` reports the declaration STALE the moment
# one of these passes, so it cannot outlive the defect.
KNOWN_RED = {
    # 2026-08-18: `bold-can-be-turned-off-again` came OFF this list. It passes
    # now -- shell v17 stopped blocking the queue on a dispatched failure, so
    # both presses run and the engine's format state toggles. Bold turns on and
    # off from the product's seat. What has NOT been fixed is the engine's
    # predicate, and the check below is what stays red for it: keeping a passing
    # check declared would have been the stale declaration the runner is built
    # to shout about.
    "a-format-that-worked-is-not-reported-as-failed":
        "finding 059: core APPLIES the parameterised inline format on the "
        "shipped artifact and reports success:false, and the engine turns that "
        "into LOK_COMMAND_FAILED (probe_engine.cpp:1696, :2286). So the product "
        "tells the user an action failed while the document shows it worked. "
        "Engine-side, needs a link "
        "(queue-inline-format-argument-is-rejected-by-core).",
    "a-long-document-is-drawn-or-the-product-says-it-is-not":
        "finding 062: above a canvas height of about 32,767 the product paints "
        "a blank page, reports `ready`, and says nothing -- and the SAME "
        "twenty-page document draws on a 1x display and is blank on a 2x one. "
        "The canvas element's own cap was measured at 65,535 in both browsers, "
        "so this is a 16-bit limit inside the render path and not the browser's. "
        "The LAYER is deliberately not named: render() does not throw, so this "
        "cannot say whether the engine returned an empty tile or the page lost "
        "a good one, and that is what decides whether the fix needs a link "
        "(queue-long-document-renders-blank-in-silence).",
}

# The two markers `recover-from-an-error` is scored on. RESCUE_SAVED is typed
# and then saved, so it lives in the authority bytes; RESCUE_UNSAVED is typed
# after that save and exists only inside the engine -- it is the work a user
# would lose. Non-ASCII on purpose, and distinct from every other marker here.
RESCUE_SAVED = "救回標記已存"
RESCUE_UNSAVED = "救回標記未存"

# Long enough to push a two-page document onto a third page, and its first
# characters are a marker, so "the edit reached the document" is a question
# about a string rather than about a length.
LONG_INSERT = "LDGROW" + (" grow the document past its last page" * 90)

INSERT_MARK = "插入鈕標記"
# Non-ASCII on purpose: a paste path that mangles UTF-8 passes an ASCII marker.
PASTE_MARK = "貼上標記PASTEMARK"

# The fixture's own text, used as a witness that a check did not destroy the
# document around what it was measuring.  It is only ever REQUIRED if a previous
# capture in the same run showed it present, so a run on a document that does
# not contain it degrades to the IME witnesses rather than to a false red.
FIXTURE_SENTINEL = "E1-LC-END"


def surviving_witnesses(previous_content: str) -> list[str]:
    """What the run has already SEEN in the document, and may therefore require.

    Adjudicated 2026-08-16.  The first version of these clauses required the
    three IME strings outright, and the `ime` mutation -- which drops two of
    them by design -- turned two unrelated checks red.  A check must not require
    content whose presence is another check's SUBJECT; it may require content
    whose presence IT verified, in its own prior capture.

    Deriving the set costs nothing: the saves are already captured.  A mutation
    can shrink this set but can never make a check red for another check's
    reason.
    """
    return [w for w in (*IME_TEXTS, FIXTURE_SENTINEL) if w in previous_content]

# --------------------------------------------------------------------- shims

INSTALL = """(() => {
// `window`, not `globalThis`: geckodriver evaluates each script in a
// Marionette sandbox whose global is recreated per call, so a shim
// installed on `globalThis` is gone by the next evaluate.  Reads of page
// globals work either way, which is what made this look fine in Chrome.
if (window.__pp) return "already";
const pp = { saves: [], anchorClicks: 0, error: null };
window.__pp = pp;
const nativeCreate = window.URL.createObjectURL.bind(window.URL);
window.URL.createObjectURL = (blob) => {
  const url = nativeCreate(blob);
  void (async () => {
    try {
      const bytes = new Uint8Array(await blob.arrayBuffer());
      let binary = "";
      for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
      pp.saves.push({ bytes: bytes.length, type: blob.type, b64: btoa(binary) });
    } catch (error) { pp.error = String(error); }
  })();
  return url;
};
const nativeClick = window.HTMLAnchorElement.prototype.click;
window.HTMLAnchorElement.prototype.click = function () {
  if (this.hasAttribute("download")) { pp.anchorClicks += 1; return; }
  return nativeClick.call(this);
};
// EVERY toast, not just the one still on screen.  `openDocument()` renders and
// then its caller toasts "opened", so a repaint failure raised during the open
// is overwritten before anything can read it -- and "the product said nothing"
// is the subject of a check, so it cannot be measured by reading a field that
// the success message has already scribbled over.
pp.toasts = [];
const toastNode = document.querySelector('#toast');
if (toastNode) {
  new MutationObserver(() => {
    const text = toastNode.textContent;
    if (text && pp.toasts[pp.toasts.length - 1] !== text) pp.toasts.push(text);
  }).observe(toastNode, { childList: true, characterData: true, subtree: true });
}
return "installed";
})()"""

READ_TOASTS = "(() => (window.__pp ? window.__pp.toasts.slice() : null))()"

CLEAR_TOASTS = """(() => {
if (window.__pp) window.__pp.toasts.length = 0;
return true;
})()"""

# A document of a KNOWN page count, handed to the product's own file input as
# bytes.  Not fetched from the server: a user's document does not arrive from
# the host that served the page, and nothing has to be written into dist/ --
# which is the frozen artifact tree and the one place this round must not
# quietly grow a file (the E2-B lesson).
OPEN_BYTES = """(() => {
const input = document.querySelector('#file');
if (!input) return "no-input";
const binary = atob("ARG_B64");
const bytes = new Uint8Array(binary.length);
for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
const file = new File([bytes], "ARG_NAME",
                      { type: "application/vnd.oasis.opendocument.text" });
const transfer = new DataTransfer();
transfer.items.add(file);
input.files = transfer.files;
input.dispatchEvent(new Event("change", { bubbles: true }));
return "dispatched";
})()"""

GEOMETRY = """(() => {
const canvas = document.querySelector('#canvas');
return { width: canvas.width, height: canvas.height,
         cssWidth: canvas.style.width, cssHeight: canvas.style.height,
         devicePixelRatio: globalThis.devicePixelRatio };
})()"""

# Ink in the top strip only.  Cheap enough to poll on a 32,000-pixel canvas,
# and it answers the only question that matters here: is the document drawn AT
# ALL.  Finding 058 is why this is asked in pixels rather than inferred from a
# state field -- data arriving is not the same as anything being painted.
TOP_INK = """(() => {
const canvas = document.querySelector('#canvas');
const w = canvas.width;
const rows = Math.min(400, canvas.height);
const data = canvas.getContext('2d').getImageData(0, 0, w, rows).data;
const inked = new Uint8Array(w);
let count = 0;
for (let y = 0; y < rows; y += 1) {
  for (let x = 0; x < w; x += 1) {
    const i = (y * w + x) * 4;
    if (data[i+3] > 128 && data[i] < 100 && data[i+1] < 100 && data[i+2] < 100) {
      count += 1; inked[x] = 1;
    }
  }
}
let columns = 0;
for (let x = 0; x < w; x += 1) if (inked[x]) columns += 1;
// COLUMNS, not a pixel count.  The caret is two pixels wide and about thirty
// tall, so on a 2x display it puts 56 dark pixels on an otherwise blank canvas
// -- which passed a "more than 50 dark pixels" test and reported a blank
// document as drawn.  Text spans hundreds of columns; a caret spans two.
return { ink: count, columns, rows,
         height: canvas.height, width: w };
})()"""

CLEAR_TOAST = """(() => {
document.querySelector('#toast').textContent = '';
return true;
})()"""

READ_TOAST = "(() => document.querySelector('#toast').textContent)()"

READ_NOTICE = """(() => {
const notice = document.querySelector('#notice');
if (!notice) return { present: false };
return { present: true, shown: notice.dataset.show === "1",
         text: document.querySelector('#notice-text').textContent };
})()"""

# Hand the product a file through its own <input type=file>, the way a chooser
# would.  The File is synthesised because neither driver can operate a native
# file dialog -- so this exercises the page's change handler and NOT the picker,
# which the check records as its own limit rather than leaving implied.
OPEN_FILE = """(() => {
const input = document.querySelector('#file');
if (!input) return "no-input";
void (async () => {
  const bytes = await (await fetch("ARG_URL", { cache: "no-cache" })).arrayBuffer();
  const file = new File([bytes], "ARG_NAME",
                        { type: "application/vnd.oasis.opendocument.text" });
  const transfer = new DataTransfer();
  transfer.items.add(file);
  input.files = transfer.files;
  input.dispatchEvent(new Event("change", { bubbles: true }));
})();
return "dispatched";
})()"""

# Finding 058.  Not "did the image change" -- that passes on any repaint, and
# not "read the caret rectangle from the session" either: the product page
# deliberately publishes no handle, which is the convention that keeps it a
# product rather than a harness.
#
# So: sample a narrow column of the canvas at the point that was clicked, with
# the caret there and again after it has moved away.  The tile does not change
# between the two reads -- only the caret does -- so the DIFFERENCE is the
# caret's ink at a place the harness chose. A page that draws no caret scores
# the same both times, whatever glyphs happen to be in the column.
# The drawn caret's COLUMN, and the line's own ink extent, in one read.
#
# Finding 060: the previous oracle counted dark pixels in a band at a fixed
# viewport fraction, and the canvas is sized from el.desk.clientWidth -- so its
# verdict depended on the browser window, and it went red on a build where the
# caret was demonstrably being drawn.
#
# This anchors to the CONTENT instead: the columns carrying ink on the clicked
# line are measured in the same read, so "where the caret is" is expressed
# relative to where the text is rather than to the viewport.  A wider window
# moves both together.
CARET_COLUMNS = """(() => {
const canvas = document.querySelector('#canvas');
const y = Math.floor(canvas.height * ARG_Y) - 18;
const h = 46;
if (y < 0 || y + h > canvas.height) return { available: false };
const data = canvas.getContext('2d').getImageData(0, y, canvas.width, h).data;
const columns = new Array(canvas.width).fill(0);
for (let row = 0; row < h; row += 1) {
  for (let x = 0; x < canvas.width; x += 1) {
    const i = (row * canvas.width + x) * 4;
    if (data[i] < 100 && data[i+1] < 100 && data[i+2] < 100) columns[x] += 1;
  }
}
return { available: true, columns, width: canvas.width, band: { y, h } };
})()"""

# Which LINE is which, from the page's own pixels.
#
# `format-a-paragraph` has to aim the caret at a NAMED paragraph using nothing
# but the user's route -- a click on the canvas.  The product publishes no
# handle on the session and the v2 shell has no text search, so the only thing
# that can say where a paragraph is drawn is the drawing.
#
# Rows carrying ink are grouped into bands and matched, in order, against the
# lines of the document the product just saved.  Three things had to be
# measured rather than assumed (2026-08-19, all three got this wrong first):
#
#   * unpainted canvas reads as (0,0,0,0), which passes a "dark pixel" test --
#     without the alpha term the whole margin counted as ink and the page came
#     back as three bands;
#   * the page border is a column inked down the whole page and two solid
#     rules across it.  The columns are dropped here; the rules are dropped by
#     their density, below;
#   * a repaint in flight reports a different band count from the same page,
#     so the scan is taken until it stops moving.
INK_ROWS = """(() => {
const canvas = document.querySelector('#canvas');
const w = canvas.width, h = canvas.height;
const data = canvas.getContext('2d').getImageData(0, 0, w, h).data;
const dark = new Uint8Array(w * h);
const columnTotals = new Int32Array(w);
for (let y = 0; y < h; y += 1) {
  for (let x = 0; x < w; x += 1) {
    const i = (y * w + x) * 4;
    if (data[i+3] > 128 && data[i] < 100 && data[i+1] < 100 && data[i+2] < 100) {
      dark[y * w + x] = 1; columnTotals[x] += 1;
    }
  }
}
// A column inked down a large fraction of the page is the page border, not a
// glyph.  0.20 rather than 0.50: a two-page document's border runs down 41% of
// the canvas, and at 0.50 neither edge was found.  Measured 2026-08-19 --
// border columns score 0.41-0.43 of the height, the noise outside the page
// 0.005-0.010, and no glyph column comes near either.
const border = [];
for (let x = 0; x < w; x += 1) border.push(columnTotals[x] > h * 0.20);
// The border columns bracket the printable area.  Everything outside them is
// off-page, and off-page is where the renderer leaves uninitialised pixels:
// two ragged strips about 13px wide putting 10-18 dark pixels into EVERY row,
// which merged a whole page of separate lines into one 340-row band.
let inside = -1, outside = w;
for (let x = 0; x < w; x += 1) if (border[x]) { if (inside < 0) inside = x; outside = x; }
const clipped = inside >= 0 && outside - inside > w * 0.5;
const counts = [], firsts = [], lasts = [];
for (let y = 0; y < h; y += 1) {
  let count = 0, first = -1, last = -1;
  for (let x = 0; x < w; x += 1) {
    if (!dark[y * w + x] || border[x]) continue;
    if (clipped && (x < inside || x > outside)) continue;
    count += 1; if (first < 0) first = x; last = x;
  }
  counts.push(count); firsts.push(first); lasts.push(last);
}
return { width: w, height: h, counts, firsts, lasts, clipped,
         page: [inside, outside],
         borderColumns: border.reduce((n, v) => n + (v ? 1 : 0), 0) };
})()"""

# The product writes the button's own text into #s-latency, so the wait for
# "this action finished" is discriminating without the harness inventing a
# name for it.
BUTTON_LABEL = """(() => {
const button = document.querySelector('#toolbar button[data-action="ARG_ACTION"]');
return button ? button.textContent.trim() : null;
})()"""

# Backspace, Delete and the arrows, through the page's own handlers. `keydown`
# for the arrows because they raise no beforeinput; `beforeinput` for the two
# delete types because that is where the browser reports them.
TYPE_KEY = """(() => {
const sink = document.querySelector('#sink');
sink.focus();
const notPrevented = sink.dispatchEvent(new KeyboardEvent('keydown',
  { key: 'ARG_KEY', bubbles: true, cancelable: true,
    ctrlKey: ARG_CTRL }));
return { handled: !notPrevented };
})()"""

DELETE_KEY = """(() => {
const sink = document.querySelector('#sink');
sink.focus();
const notPrevented = sink.dispatchEvent(new InputEvent('beforeinput',
  { inputType: 'ARG_TYPE', bubbles: true, cancelable: true }));
return { handled: !notPrevented };
})()"""

CUT = """(() => {
const sink = document.querySelector('#sink');
sink.focus();
const notPrevented = sink.dispatchEvent(
  new ClipboardEvent('cut', { bubbles: true, cancelable: true }));
return { handled: !notPrevented };
})()"""

SAVE_COUNT = "(() => (window.__pp ? window.__pp.saves.length : -1))()"

READ_SAVE = "(() => (window.__pp ? window.__pp.saves[ARG_INDEX] : null) || null)()"

PRESS = """(() => {
const button = document.querySelector('#toolbar button[data-action="ARG_ACTION"]');
if (!button) return false;
button.click();
return true;
})()"""

POINT_AT = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const x = box.left + box.width * ARG_X;
const y = box.top + box.height * ARG_Y;
canvas.dispatchEvent(new PointerEvent('pointerdown', {
  clientX: x, clientY: y, button: 0, buttons: 1, pointerId: 1, bubbles: true }));
canvas.dispatchEvent(new PointerEvent('pointerup', {
  clientX: x, clientY: y, button: 0, buttons: 0, pointerId: 1, bubbles: true }));
return true;
})()"""

DRAG = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const at = (fx, fy) => ({ x: box.left + box.width * fx, y: box.top + box.height * fy });
const a = at(ARG_X1, ARG_Y1);
const b = at(ARG_X2, ARG_Y2);
const send = (type, point, buttons) => canvas.dispatchEvent(new PointerEvent(type, {
  clientX: point.x, clientY: point.y, button: 0, buttons, pointerId: 1, bubbles: true }));
send('pointerdown', a, 1);
send('pointermove', { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, 1);
send('pointermove', b, 1);
send('pointerup', b, 0);
return true;
})()"""

# One composition, through the product page's own input sink.
#
# The line that matters is `sink.value += TEXT`.  A real IME does not write that
# line -- the browser does, as the default action of `beforeinput` with
# inputType `insertCompositionText`, which is NOT cancelable during composition.
# Synthetic events run no default action, so without this the textarea would
# stay empty, the adapter's buffer comparison would short-circuit on an empty
# string, and finding 050 would be invisible to this harness exactly as it was
# invisible to every other one.  Appending (not assigning) is what the browser
# does, and it is what makes the fix's absence observable: nothing in this tree
# clears that buffer except the fix.
COMPOSE = """(() => {
const sink = document.querySelector('#sink');
sink.focus();
sink.dispatchEvent(new CompositionEvent('compositionstart', { data: '', bubbles: true }));
sink.dispatchEvent(new CompositionEvent('compositionupdate', { data: 'ARG_TEXT', bubbles: true }));
sink.dispatchEvent(new InputEvent('beforeinput', {
  inputType: 'insertCompositionText', data: 'ARG_TEXT', bubbles: true, cancelable: false }));
sink.value += 'ARG_TEXT';
sink.dispatchEvent(new CompositionEvent('compositionend', { data: 'ARG_TEXT', bubbles: true }));
return sink.value;
})()"""

SET_TEXT = """(() => {
const field = document.querySelector('#text');
field.value = 'ARG_TEXT';
return field.value;
})()"""

# Is the product OFFERING its recovery, or is the button merely in the DOM?
# `#notice` is `display: none` until `data-show="1"`, so a click on a hidden
# button drives a path the user cannot reach -- which is what the first version
# of this check did.
# Finding 047's recipe, with nothing in between -- which is the whole of it.
#
# Driving it as three WebDriver calls does not reproduce: each round trip plus
# the poll that waits for the caret toast spends more than the ~2 s after which
# 047's own controls show the failure stops happening.  Pressed from inside the
# page, the three land in the session's FIFO back to back, which is the sequence
# the finding measured.
INDUCE_047 = """(() => {
const toolbar = document.querySelector('#toolbar');
const press = (action) => toolbar
  .querySelector(`[data-action="${action}"]`).click();
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const x = box.left + box.width * ARG_X;
const y = box.top + box.height * ARG_Y;
press('save');
canvas.dispatchEvent(new PointerEvent('pointerdown', {
  clientX: x, clientY: y, button: 0, buttons: 1, pointerId: 1, bubbles: true }));
canvas.dispatchEvent(new PointerEvent('pointerup', {
  clientX: x, clientY: y, button: 0, buttons: 0, pointerId: 1, bubbles: true }));
press('set-list-unordered');
return true;
})()"""

# Finding 053's own route into a dispatched failure, and the only one that does
# not depend on 047 still reproducing.
#
# Click past the end of a line -- measured natively: below/past the text the
# clamp saturates at the end-of-line offset -- then break the paragraph, which
# leaves the caret in a NEW EMPTY paragraph.  A list action there is finding
# 046's cell: `.uno:SelectText` overshoots into the neighbour, the barrier
# refuses a mutation that succeeded, and the error is
# EDITOR_FORMAT_POSTCONDITION_FAILED with `dispatched: true`.
#
# That is the error whose prescription the product could not carry out.  It also
# drives `action:insert-paragraph-break`, which nothing had driven either.
INDUCE_EMPTY_PARAGRAPH = """(() => {
const toolbar = document.querySelector('#toolbar');
const press = (action) => toolbar
  .querySelector(`[data-action="${action}"]`).click();
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const x = box.left + box.width * ARG_X;
const y = box.top + box.height * ARG_Y;
canvas.dispatchEvent(new PointerEvent('pointerdown', {
  clientX: x, clientY: y, button: 0, buttons: 1, pointerId: 1, bubbles: true }));
canvas.dispatchEvent(new PointerEvent('pointerup', {
  clientX: x, clientY: y, button: 0, buttons: 0, pointerId: 1, bubbles: true }));
return true;
})()"""

BREAK_THEN_LIST = """(() => {
const toolbar = document.querySelector('#toolbar');
const press = (action) => toolbar
  .querySelector(`[data-action="${action}"]`).click();
press('insert-paragraph-break');
return true;
})()"""

READ_NOTICE = """(() => {
const notice = document.querySelector('#notice');
const button = document.querySelector('#notice-action');
return {
  shown: notice ? notice.dataset.show === "1" : null,
  text: document.querySelector('#notice-text').textContent,
  label: button ? button.textContent : null,
  disabled: button ? button.disabled : null,
};
})()"""

# The product's recovery path.  The button lives outside #toolbar and has no
# data-action, so PRESS cannot reach it -- which is part of why no round ever
# had.  `.click()` fires the listener whether or not #notice is displayed.
CLICK_NOTICE = """(() => {
const button = document.querySelector('#notice-action');
if (!button) return false;
button.click();
return true;
})()"""

COPY = """(() => {
const sink = document.querySelector('#sink');
sink.focus();
const notPrevented = sink.dispatchEvent(
  new ClipboardEvent('copy', { bubbles: true, cancelable: true }));
return { handlerRan: !notPrevented };
})()"""

# A paste carrying real text.  `clipboardData` is only settable through the
# ClipboardEvent constructor on some engines; when it is not, the event arrives
# with nothing on it and the check must say it could not run rather than fail
# the product -- so the driver reports whether the payload survived.
PASTE = """(() => {
const sink = document.querySelector('#sink');
sink.focus();
let data = null;
try {
  data = new DataTransfer();
  data.setData('text/plain', 'ARG_TEXT');
} catch (error) { return { payloadSurvived: false, why: String(error) }; }
const event = new ClipboardEvent('paste',
  { bubbles: true, cancelable: true, clipboardData: data });
// Firefox's constructor drops clipboardData (measured 2026-08-17: the handler
// ran and reported an empty clipboard).  Define it instead, exposing only the
// two members the clipboard adapter reads -- `types` and `getData` -- so the
// shim cannot accidentally supply an affordance the real event lacks.
let shimmed = false;
if (!event.clipboardData || event.clipboardData.getData('text/plain') !== 'ARG_TEXT') {
  Object.defineProperty(event, 'clipboardData', {
    configurable: true,
    get: () => ({ types: ['text/plain'],
                  getData: (type) => (type === 'text/plain' ? 'ARG_TEXT' : '') }),
  });
  shimmed = true;
}
const payloadSurvived =
  !!event.clipboardData &&
  event.clipboardData.getData('text/plain') === 'ARG_TEXT';
const notPrevented = sink.dispatchEvent(event);
return { payloadSurvived, shimmed, eventCanceled: !notPrevented };
})()"""

# ----------------------------------------------------------------- mutations

MUTATIONS = {
    # The defect as it actually was until 2026-08-17: the session had
    # pasteEvent() and no listener called it, so a paste fell through to the
    # browser's default on a canvas -- silently nothing.  Renaming the event is
    # the closest thing to "the handler was never written".
    # Cut, restored to what shipped until 2026-08-17: no handler at all, so the
    # browser's default cut runs against a canvas with no DOM selection and
    # silently does nothing.
    "cut": {
        "check": "ctrl-x-is-handled-by-the-product",
        "path": "e2-editor-app.js",
        "find": 'el.sink.addEventListener("cut", (event) => {',
        "replace": 'el.sink.addEventListener("cut-never-wired", (event) => {',
        "reintroduces": "an editor with no cut",
        "alsoRed": [],
    },
    # The typing path.  Removing the delete mapping restores the state the
    # product shipped in: Backspace does nothing, because the adapter ignores
    # the input type and nothing else was listening.
    "backspace": {
        "check": "backspace-and-arrows-reach-the-document",
        "path": "e2-editor-app.js",
        "find": "  const action = DELETE_INPUT_TYPES[event.inputType];",
        "replace": "  const action = undefined;",
        "reintroduces": "an editor you can type into but cannot correct",
        "alsoRed": [],
    },
    # Finding 058.  Turning off the caret draw restores the state the product
    # shipped in until 2026-08-17: a tile and nothing else. The check has to go
    # red on that, or it is measuring a repaint rather than a caret.
    "caret": {
        "check": "the-caret-is-drawn-where-it-was-placed",
        "path": "e2-editor-app.js",
        "find": "  if (caret && editorState.selection?.collapsed !== false) {",
        "replace": '  if (caret && editorState.selection?.collapsed === "never") {',
        "reintroduces": "an editor with no visible caret",
        "alsoRed": [],
    },
    # Finding 060's fix, the placement half.  The caret is still drawn, and
    # drawn on the right line -- it just ignores the x it was given.  The old
    # band-counting oracle passed on exactly this, which is why the check had to
    # be re-anchored to the line's own ink.
    "caret-ignores-x": {
        "check": "the-caret-lands-where-the-click-was",
        "path": "e2-editor-app.js",
        "find": "    const [x, y, , height] = box(caret);",
        "replace": "    const [, y, , height] = box(caret); const x = 0;",
        "reintroduces": "a caret that is drawn, on the right line, in the wrong "
                        "place",
        # Declared, and it names a real limit rather than hiding one: this
        # oracle sees the caret by watching it MOVE, so a caret pinned to a
        # constant column is indistinguishable from one that is never drawn.
        # Both checks therefore go red together under this mutation.
        "alsoRed": ["the-caret-is-drawn-where-it-was-placed"],
    },
    # Finding 059's disposition half, shell v17.  Turning the branch off
    # restores what shipped until 2026-08-18: LOK_COMMAND_FAILED fell through to
    # `unknown-rollback`, the queue blocked, and the product prescribed a
    # rollback for a change that -- measured on both sides -- had succeeded.
    "inline-format-rollback": {
        "check": "a-failed-format-does-not-block-the-session",
        "path": "editor-shell-v2/paragraph-editor-client.js",
        "find": '  if (error?.code === "LOK_COMMAND_FAILED")\n'
                '    return "dispatched-unverified";',
        "replace": '  if (error?.code === "LOK_COMMAND_FAILED-never")\n'
                   '    return "dispatched-unverified";',
        "reintroduces": "an editor that tells you to discard your work to undo a "
                        "change that succeeded",
        # Declared collateral, and it is the mutation telling the truth: with
        # the queue blocked again the SECOND B press never runs, so bold cannot
        # be turned off either.  Measured 2026-08-18 -- this check went red
        # under the mutation and green without it, which is what made the
        # dependency visible rather than assumed.
        "alsoRed": ["bold-can-be-turned-off-again"],
    },
    # Finding 046's residual, the disposition half.  Turning the sentinel off
    # restores the pre-2026-08-17 behaviour exactly: the operation rejects, the
    # frozen base class sees MUTATION_OUTCOME_UNKNOWN in its RECOVERY_ERRORS,
    # and the session blocks -- so an ordinary blank-line bullet again leaves
    # rollback as the user's only exit.
    "review-disposition": {
        "check": "bulleting-a-blank-line-does-not-demand-a-rollback",
        "path": "editor-shell-v2/narrow-editor-v2-session.js",
        "find": '          if (recoveryFor(error) === "review")',
        "replace": '          if (recoveryFor(error) === "review-off-by-mutation")',
        "reintroduces": "a blank-line bullet that bricks the session",
        "alsoRed": [],
        # With the queue blocked again, the recovery path HAS an inducer again,
        # so this check goes from NOT_ESTABLISHED back to PASS. Declared so the
        # run does not look like the mutation fixed something.
        "alsoNotEstablished": [],
    },
    # `format-a-paragraph`, the swallow: 標題 and 內文 fall off the end of the
    # toolbar's handler chain, so pressing them does nothing at all.  This is
    # the state the coverage registry said all five structure actions were in
    # -- present on the toolbar, driven by nobody -- and it is the shape of
    # findings 049 and 050.
    #
    # Deliberately NARROWED to the two paragraph-style actions.  Measured
    # 2026-08-19: swallowing `set-list-*` as well turns three unrelated checks
    # red, two of them for a real reason worth writing down -- the 046 cell and
    # the recovery recipe both reach their subject by pressing 項目符號, so with
    # that button dead they have no way in -- and one by accident, because the
    # cut check drags at fixed viewport fractions and an unbulleted paragraph
    # moves the line it was aiming at.  A mutation whose collateral is an
    # aiming accident teaches its reader to ignore red.  The misroute mutation
    # below covers the list actions.
    "paragraph-action-swallowed": {
        "check": "format-a-paragraph-changes-that-paragraph",
        "path": "e2-editor-app.js",
        "find": "    : EDITOR_V2_ACTIONS.includes(action) ? () => editorAction(action)",
        "replace": '    : EDITOR_V2_ACTIONS.includes(action)\n'
                   '      && !action.startsWith("set-paragraph")\n'
                   '      ? () => editorAction(action)',
        "reintroduces": "a toolbar whose 標題 and 內文 buttons do nothing",
        "alsoRed": [],
    },
    # The same five buttons, wired to the wrong command.  Every arm still
    # dispatches, the session stays healthy, the revision advances and a
    # document-wide "is there a numbered list" test still passes -- the
    # paragraph the user aimed at is simply in the wrong state.  This is the
    # mutation the exact-text anchor exists for.
    "paragraph-action-misrouted": {
        "check": "format-a-paragraph-changes-that-paragraph",
        "path": "e2-editor-app.js",
        "find": "    : EDITOR_V2_ACTIONS.includes(action) ? () => editorAction(action)",
        "replace": '    : EDITOR_V2_ACTIONS.includes(action)\n'
                   '      ? () => editorAction(action === "set-list-ordered"\n'
                   '                           ? "set-list-unordered" : action)',
        "reintroduces": "a 編號 button that makes bullets",
        "alsoRed": [],
    },
    # Finding 046's shape: the action lands on the paragraph BELOW the one the
    # user clicked.  Every completion code is green, the document changes, and
    # the wrong paragraph moved.  390 twips is this corpus's line pitch (the
    # D3 scorer's caret tolerance is half of it).
    "caret-off-by-one-line": {
        "check": "format-a-paragraph-changes-that-paragraph",
        "path": "e2-editor-app.js",
        "find": "    yTwips: Math.max(0, Math.round(\n"
                "      (event.clientY - rectangle.top) / rectangle.height\n"
                "      * session.document.heightTwips)),",
        "replace": "    yTwips: Math.max(0, 390 + Math.round(\n"
                   "      (event.clientY - rectangle.top) / rectangle.height\n"
                   "      * session.document.heightTwips)),",
        "reintroduces": "an editor that formats the paragraph below the one you "
                        "clicked",
        # Declared collateral, measured 2026-08-19 rather than predicted: this
        # mutation shifts EVERY click in the run by a line, and the two checks
        # below aim by fixed viewport fractions, so the 046 cell and the cut
        # check's drag both land somewhere else.  That is the mutation telling
        # the truth about how those two aim.
        "alsoRed": ["bulleting-a-blank-line-does-not-demand-a-rollback",
                    "ctrl-x-is-handled-by-the-product"],
        # A NAMED LIMIT, and it is the opposite of what I predicted when this
        # mutation was written: both caret checks stay GREEN under it.  Their
        # oracle is horizontal -- two clicks on one line, scored against that
        # line's own ink -- and a caret displaced a whole line down is still
        # "where the click was" as far as they can tell, because the band they
        # sample is tall enough to contain the line below.  So the caret row
        # covers WHICH COLUMN, not which line; which line is covered here, by
        # the neighbour clause, and nowhere else.
    },
    # `recover-from-an-error`, the mechanism the whole row rests on.  With the
    # pre-gesture checkpoint degraded to a no-op the product still recovers,
    # still comes back `ready`, and still saves a legal ODT -- it just silently
    # drops everything typed since the last save.  The three-branch oracle
    # alone CANNOT see this: the product would declare 無 and deliver 無, which
    # is consistent.  The capability clause is what catches it, and this
    # mutation is why that clause exists (adjudicated 2026-08-18).
    "checkpoint-before-selection-noop": {
        "check": "recovery-returns-what-the-product-promised",
        "path": "editor-shell/editor-session.js",
        "find": "    if (!this.state.snapshot.dirty "
                "|| contentStamp === this._checkpointStamp)\n      return;",
        "replace": "    if (true || !this.state.snapshot.dirty\n"
                   "        || contentStamp === this._checkpointStamp)\n"
                   "      return;",
        "reintroduces": "an editor that loses everything since your last save "
                        "and does not say so",
        "alsoRed": [],
    },
    # The third branch, reached by making the checkpoint save miss its
    # deadline.  Not a defect being reintroduced but a CONDITION being
    # injected, and the check is expected to go red on it for a reason worth
    # writing down: the shell distinguishes "nothing to rescue" from "we tried
    # to protect your work and failed" (recovery-notice.js, checkpointFailed)
    # and the product's notice does not, so the user is told the first when the
    # second is true.  If the notice ever learns to say it, this declaration
    # goes stale loudly.
    "checkpoint-write-fails": {
        "check": "recovery-returns-what-the-product-promised",
        "path": "editor-shell/editor-session.js",
        "find": "        { timeoutMs: this._selectionTimeoutMs },",
        "replace": "        { timeoutMs: 1 },",
        "reintroduces": "a rescue that fails silently and reads as 'there was "
                        "nothing to rescue'",
        "alsoRed": [],
    },
    # The registered latency threshold, made to bite.  A pre-registered number
    # that nothing can ever exceed is decoration, and this tree has been caught
    # by that shape before: `renderDocument()` allows itself 60 seconds, so the
    # cell would pass on an editor where every keystroke took half a minute.
    # 3,000 ms, and the reason it is not 1,500 is a measurement rather than a
    # margin: a 1,500 ms delay per REPAINT produced only 765-832 ms of
    # user-visible latency, because what this times is keystroke to visible
    # ink and the page coalesces repaints (`renderAgain`).  The delay a build
    # carries and the wait a user feels are not the same number, and the
    # threshold is written about the second one.
    "slow-repaint": {
        "check": "editing-a-long-document-stays-responsive",
        "path": "e2-editor-app.js",
        "find": "async function renderDocument(retriesLeft = 6) {",
        "replace": "async function renderDocument(retriesLeft = 6) {\n"
                   "  await new Promise((resolve) => setTimeout(resolve, 3000));",
        "reintroduces": "an editor you wait for after every keystroke",
        "alsoRed": [],
    },
    # Aimed at the mechanism that actually commits a paste. Measured
    # 2026-08-17, twice: a page-level paste handler was written first on the
    # assumption that nothing handled paste, and it DOUBLED every paste
    # (markOccurrences 2); then this mutation was aimed at beforeinput's
    # commit-text branch and was not detected either. The adapter binds `paste`
    # directly (input-adapter.js:78) and `handlePaste` commits it. Two wrong
    # guesses about which code runs, both caught by requiring the mutation to
    # be detected rather than by reading.
    "paste": {
        "check": "ctrl-v-reaches-the-document",
        "path": "input/input-adapter.js",
        "find": '    this._trace(event, "paste", { action: "commit-plain-text", htmlPresent });',
        "replace": ('    this._trace(event, "paste", { action: "paste-dropped-by-mutation" });\n'
                    '    if (text) return Promise.resolve({ committed: false, reason: "mutation" });'),
        "reintroduces": "a product you cannot paste into",
        # Nothing else: the paste runs after every other check has been judged,
        # and the IME checks commit through the composition path.
        "alsoRed": [],
    },
    # The failure this check exists to catch is not "opening crashes" -- it is
    # opening that LOOKS right: the filename updates, the state goes ready, and
    # the document the engine holds is still the old one.  So the mutation keeps
    # every visible signal and swaps only the bytes.  A check that asked whether
    # the label changed would pass this mutation, which is why it does not ask.
    "open-file": {
        "check": "product-opens-a-document-the-user-chose",
        "path": "e2-editor-app.js",
        "find": "    .then((bytes) => openDocument(bytes, file.name))",
        "replace": ('    .then(() => fetch("./e1-fixtures/list-contexts.odt")\n'
                    '      .then((r) => r.arrayBuffer())\n'
                    '      .then((b) => openDocument(b, file.name)))'),
        "reintroduces": "a product that can only open its own samples",
        # Nothing else: the open runs last, after every other check has already
        # been judged, so this mutation cannot reach them.
        "alsoRed": [],
    },
    "save": {
        "check": "product-save-button-writes-a-real-odt",
        "path": "e2-editor-app.js",
        "find": 'const { bytes } = await run("儲存", () => session.save());',
        "replace": 'const bytes = await run("儲存", () => session.save());',
        "reintroduces": "finding 049",
        # Breaking the save button also blinds the IME check, whose document
        # half is read THROUGH the product's own save -- there is no other way
        # out of the page, which is the reason finding 049 could hide for as
        # long as it did.  Declared rather than papered over: the alternative
        # is an IME check that asks only whether the revision moved, and that
        # is exactly the criterion round 5 passed while two thirds of a user's
        # typing was being dropped.
        # The insert and undo oracles are guarded by `is_an_odt` too, so a
        # broken save takes them down with it.  Declared, for the same reason
        # as above.
        #
        # The rollback check is deliberately NOT here: it is NOT_ESTABLISHED on
        # every run today, so requiring it to go red would require a check that
        # never runs to fail, and the 2026-08-16 save-mutation round reported
        # NOT DETECTED for exactly that reason.  Listing it would have been the
        # declaration claiming more than the harness does.
        # The recovery check ends by requiring the product to save a real ODT
        # after recovering -- that is how it shows the session is usable and not
        # merely in a good-looking state -- so a broken save takes it down too.
        # Added 2026-08-16 after the run said so: this is the coupling being
        # declared, not the check being weakened.
        "alsoRed": ["every-ime-commit-reaches-the-document",
                    "notice-action-recovers-the-session"],
        # Both of these read their outcome out of the document, and this
        # mutation removes the only way to read it -- so neither can go red,
        # they can only fail to run.  Declared as such rather than left out: a
        # declaration that omits a coupling stops being falsifiable, and the run
        # verifies this outcome and reports the declaration stale if either
        # check ever runs at all.
        #
        # `product-insert-...` moved here from `alsoRed` on 2026-08-16, and the
        # machine check is what moved it: once the witnesses became DERIVED from
        # the previous save, a broken save leaves an empty witness set, and an
        # empty witness set is NOT_ESTABLISHED by construction.  The declaration
        # had gone on claiming a red the harness could no longer deliver.
        "alsoNotEstablished": ["product-insert-button-inserts-what-the-field-holds",
                               "product-undo-button-reverses-the-last-edit"],
    },
    "ime": {
        "check": "every-ime-commit-reaches-the-document",
        "path": "input/input-adapter.js",
        "find": '      this._target.value = "";',
        "replace": "      /* mutation: finding 050 reintroduced */;",
        "reintroduces": "finding 050",
    },
    "copy": {
        "check": "ctrl-c-asks-the-engine",
        "path": "e2-editor-app.js",
        "find": 'el.sink.addEventListener("copy", (event) => {',
        "replace": 'el.sink.addEventListener("copy-removed-by-mutation", (event) => {',
        "reintroduces": "the Ctrl+C gap found in the D5 operator round",
    },
    # The three paths the coverage audit named HIGH on 2026-08-16.  Each
    # mutation is the shape the defect would actually take on that path.
    "undo": {
        "check": "product-undo-button-reverses-the-last-edit",
        "path": "e2-editor-app.js",
        "find": '    action === "undo" ? () => run("復原", () => session.undo())',
        "replace": '    action === "undo" ? () => run("復原", () => Promise.resolve())',
        "reintroduces": "finding 049's shape on the undo path: the button runs, "
                        "the toast reports a time, and the document is untouched",
    },
    "insert-text": {
        "check": "product-insert-button-inserts-what-the-field-holds",
        "path": "e2-editor-app.js",
        "find": "  const text = el.text.value;",
        "replace": "  const text = el.text.placeholder;",
        "reintroduces": "finding 049 exactly: the handler reads the wrong "
                        "property off the right element",
        # Same shape as the save mutation: this destroys the undo check's
        # precondition (the marker is never inserted, so there is nothing whose
        # removal undo could be judged on).  Precondition-destruction is a
        # general property of mutations upstream of a check's setup.
        "alsoNotEstablished": ["product-undo-button-reverses-the-last-edit"],
    },
    "rollback": {
        "check": "notice-action-recovers-the-session",
        "path": "e2-editor-app.js",
        "find": '  void run("回到檢查點", () => session.rollback())',
        "replace": '  void run("回到檢查點", () => session.undo())',
        "reintroduces": "the recovery path wired to undo instead of rollback -- "
                        "which SPEC E2-B 5.13 rules out explicitly, because undo "
                        "goes through the queue a post-dispatch failure has just "
                        "blocked and would only return EDITOR_NOT_READY",
        # This was declared `expectedToBeDetected: False` while the check could
        # not run at all -- the product offers the button only from
        # `recoverable-error`, and nothing could induce that state from the
        # page.  Once the 053 route existed, the run reported the declaration
        # STALE and detected the mutation, which is what the self-reporting
        # limit was built to do.  The declaration is gone; this is a live
        # verification now.
    },
    # Undo that takes back MORE than the last edit.  Before the witnesses were
    # derived, the `ime` mutation's collateral was the accidental proof that the
    # survival clauses could fire; decoupling them removed that proof, so this
    # restores it deliberately.  A second undo reverses the last IME commit too,
    # which is in the witness set derived from the save before it.
    "undo-twice": {
        "check": "product-undo-button-reverses-the-last-edit",
        "path": "e2-editor-app.js",
        "find": '    action === "undo" ? () => run("復原", () => session.undo())',
        "replace": ('    action === "undo" ? () => run("復原",'
                    " () => session.undo().then(() => session.undo()))"),
        "reintroduces": "nothing that has happened; an undo that reverses two "
                        "edits, which is what the survival witnesses exist to "
                        "notice",
    },
    # The narrowest mutation that stops the 047 recipe from doing anything: the
    # toolbar ignores the one action it dispatches.  It exists so that
    # "NOT_ESTABLISHED because the queue did not block" can be shown to be
    # different from "NOT_ESTABLISHED because the toolbar is broken" -- the
    # hiding place an adversarial review named on 2026-08-16.  Narrow on
    # purpose: no other check presses this button.
    "toolbar-drops-the-list-action": {
        "check": "notice-action-recovers-the-session",
        "path": "e2-editor-app.js",
        "find": "    : EDITOR_V2_ACTIONS.includes(action) ? () => editorAction(action)",
        "replace": ('    : (EDITOR_V2_ACTIONS.includes(action)'
                    ' && action !== "set-list-unordered")'
                    " ? () => editorAction(action)"),
        "reintroduces": "nothing that has happened; a toolbar that silently "
                        "drops one action, which is what the guard on the "
                        "NOT_ESTABLISHED branch exists to notice",
    },
    # Not a defect this tree has had: a handler that runs, prevents the default
    # and reports success WITHOUT asking the engine.  It is here because
    # adversarial review named it as something this check might not catch, and
    # the answer belongs in the evidence rather than in an assumption.
    "copy-lies": {
        "check": "ctrl-c-asks-the-engine",
        "path": "e2-editor-app.js",
        "find": '  void run("複製", () => session.copySelection())\n    .then((result) => toast(`已複製 ${result?.codePoints ?? "?"} 字`))\n    .catch(() => {});',
        "replace": '  toast(`已複製 1 字`);   /* mutation: never asks the engine */',
        "reintroduces": "nothing that has happened; a hypothetical handler that "
                        "reports success without calling copySelection",
        "expectedToBeDetected": False,
        "why": "From outside the page, 'the engine was asked' is not observable: "
               "the product's only outward signal is its own toast, and a lying "
               "handler writes the same toast. Recorded as a named limit of this "
               "harness. What would close it is the shell's clipboard trace being "
               "reported somewhere a harness can read, which is a product change "
               "and therefore a decision, not a detail.",
    },
}


def build_mirror(source: Path, target: Path, overrides: dict[str, bytes]) -> None:
    """Mirror `source` into `target` with symlinks, materialising `overrides`.

    dist/ is 7.5 GB and holds every frozen profile; copying it to break one file
    would be both slow and a way to accidentally write to a frozen artifact.
    Everything is a symlink except the directories leading to an override.
    """
    real_dirs: set[str] = set()
    for relative in overrides:
        parent = Path(relative).parent
        while parent != Path("."):
            real_dirs.add(parent.as_posix())
            parent = parent.parent

    def walk(relative: Path) -> None:
        source_dir = source / relative
        target_dir = target / relative
        target_dir.mkdir(parents=True, exist_ok=True)
        for entry in source_dir.iterdir():
            child = relative / entry.name if relative != Path(".") else Path(entry.name)
            key = child.as_posix()
            if key in overrides:
                (target / child).write_bytes(overrides[key])
            elif entry.is_dir() and key in real_dirs:
                walk(child)
            else:
                os.symlink(entry.resolve(), target / child)

    walk(Path("."))


# The shell generation this run actually SERVED, derived rather than declared.
#
# A report that only says `mutation: none` is a report that says what the runner
# was ASKED for.  Nothing in it distinguishes a run against today's shell from a
# run against a mirror with one file rewritten, or from a report written days
# ago against an older generation -- and a checklist that accepts such a report
# as acceptance evidence is the finding 044 shape one file further out.
#
# So this hashes the twelve files the v2 bundle declares, READ FROM THE ROOT THE
# SERVER WAS POINTED AT.  A mutation or a shim rewrites one of those twelve (the
# product page itself is one of them), so the digest moves on its own and no
# separate honesty flag is needed.  Same digest function as the bundle manifest,
# imported rather than reimplemented: two copies of a hash rule drift.
SHELL_BUNDLE_V2 = PROJECT / "e2" / "editor-shell-v2-bundle-v17.json"


def served_in_dist(relative: str) -> str:
    """Where a bundle path lands under a served root.

    The entrypoint lives at web/ in the source tree and at the root in dist/;
    every other module keeps its directory.  Same rule validate_e1_c documents
    for the E1-C bundle.
    """
    return relative.split("/", 1)[1] if relative.startswith("web/") else relative


def served_shell_identity(root: Path) -> dict:
    manifest = json.loads(SHELL_BUNDLE_V2.read_text(encoding="utf-8"))
    paths = [entry["path"] for entry in manifest.get("included") or []]
    hashes: dict[str, str | None] = {}
    for path in paths:
        served = root / served_in_dist(path)
        hashes[path] = sha256_file(served) if served.is_file() else None
    return {
        "bundle": SHELL_BUNDLE_V2.relative_to(PROJECT).as_posix(),
        "declaredSha256": manifest.get("bundleSha256"),
        "servedSha256": shell_bundle_digest(hashes),
        "missing": sorted(p for p, h in hashes.items() if h is None),
    }


def apply_mutation(name: str, scratch: Path) -> tuple[Path, dict]:
    spec = MUTATIONS[name]
    original = (PROJECT / "dist" / spec["path"]).read_text(encoding="utf-8")
    hits = original.count(spec["find"])
    if hits != 1:
        raise SystemExit(
            f"mutation '{name}' expects exactly one occurrence of its pattern in "
            f"dist/{spec['path']}, found {hits}.  The tree moved under the "
            f"mutation; fix the pattern rather than the count.")
    mutated = original.replace(spec["find"], spec["replace"])
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root,
                 {spec["path"]: mutated.encode("utf-8")})
    return root, {"mutation": name, "file": spec["path"],
                  "reintroduces": spec["reintroduces"],
                  "mustGoRed": spec["check"]}


# ------------------------------------------------------------------- helpers


def caret_from_columns(near_start: dict, past_end: dict) -> dict:
    """Where the caret was drawn, expressed relative to the line's own ink.

    Two reads of the same band, one after clicking near the start of the line
    and one after clicking past its end.  The text does not move between them,
    so the column that GAINED ink is the caret's second position and the one
    that LOST it is the first -- no reference image and no knowledge of the
    engine's coordinates is needed.

    The line's ink extent comes from the columns that carry ink in BOTH reads,
    which excludes the caret itself precisely because it moved.
    """
    a, b = near_start.get("columns") or [], past_end.get("columns") or []
    if not a or not b or len(a) != len(b):
        return {"available": False}
    # Full-height columns are the page frame, not text.  Measured 2026-08-18:
    # the first run of this oracle reported inkSpan 724 on a 725px canvas,
    # because the band's leftmost and rightmost inked columns are the document
    # border -- so "fraction along the line" was really "fraction across the
    # canvas" and a click at x=0.92 scored 0.605.  A glyph never fills every row
    # of a band that includes the line spacing; a border does.
    height = (near_start.get("band") or {}).get("h") or 0
    shared = [x for x in range(len(a))
              if 0 < min(a[x], b[x]) and max(a[x], b[x]) < height]
    if len(shared) < 2:
        return {"available": False, "why": "the band carries no text ink"}
    delta = [b[x] - a[x] for x in range(len(a))]
    gained = max(range(len(delta)), key=lambda x: delta[x])
    lost = min(range(len(delta)), key=lambda x: delta[x])
    left, right = shared[0], shared[-1]
    span = right - left
    return {
        "available": True,
        "inkLeft": left, "inkRight": right, "inkSpan": span,
        "caretAfterClickNearStart": lost, "caretAfterClickPastEnd": gained,
        "strokeGained": delta[gained], "strokeLost": -delta[lost],
        # Position along the line, 0 at the first inked column and 1 at the last.
        "fractionNearStart": (lost - left) / span if span else None,
        "fractionPastEnd": (gained - left) / span if span else None,
    }


ODF_NS = {"office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
          "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}

# A text line that has been split by a thin row inside its own glyphs is still
# one line; two lines of this corpus are 16px apart at the closest.
BAND_MERGE_GAP = 5


def text_bands(scan: dict, floor: int = 2) -> list[dict]:
    """The canvas's lines of text, as row bands.

    Everything that is not a line of text is rejected by DENSITY -- the widest
    inked row of the band over the band's own horizontal extent.  Measured
    2026-08-19 on this fixture: the page's rules score 1.00, the sparse noise
    along the page edges 0.004-0.024, and lines of text 0.43-0.60.  Two orders
    of magnitude of daylight on either side, and the rejected bands are
    reported so the reason is visible rather than assumed.
    """
    runs: list[dict] = []
    start = None
    for y, count in enumerate(scan["counts"]):
        if count > floor and start is None:
            start = y
        elif count <= floor and start is not None:
            runs.append({"top": start, "bottom": y - 1})
            start = None
    if start is not None:
        runs.append({"top": start, "bottom": len(scan["counts"]) - 1})
    merged: list[dict] = []
    for run in runs:
        if merged and run["top"] - merged[-1]["bottom"] <= BAND_MERGE_GAP:
            merged[-1]["bottom"] = run["bottom"]
        else:
            merged.append(run)
    out: list[dict] = []
    for band in merged:
        rows = range(band["top"], band["bottom"] + 1)
        firsts = [scan["firsts"][y] for y in rows if scan["firsts"][y] >= 0]
        if not firsts:
            continue
        band["maxInk"] = max(scan["counts"][y] for y in rows)
        band["first"] = min(firsts)
        band["last"] = max(scan["lasts"][y] for y in rows)
        band["extent"] = band["last"] - band["first"] + 1
        band["density"] = band["maxInk"] / band["extent"]
        band["centreFraction"] = ((band["top"] + band["bottom"]) / 2
                                  / scan["height"])
        if 0.15 <= band["density"] < 0.9:
            out.append(band)
    return out


def stable_bands(session, tries: int = 12) -> tuple[dict, list[dict]]:
    """A scan the page has stopped changing under.

    Measured 2026-08-19: read straight after a save, the same page reported 11
    bands once and 9 a moment later -- a repaint caught in flight.  A fixed
    sleep would have hidden that; this waits for the shape to repeat.
    """
    scan: dict = {}
    bands: list[dict] = []
    previous = None
    for _ in range(tries):
        scan = evaluate(session, INK_ROWS) or {"counts": [], "firsts": [],
                                               "lasts": [], "height": 1,
                                               "width": 1}
        bands = text_bands(scan)
        shape = [(b["top"], b["bottom"]) for b in bands]
        if previous is not None and shape == previous:
            return scan, bands
        previous = shape
        time.sleep(0.5)
    return scan, bands


def document_lines(report: dict) -> list[dict]:
    """The body as the flat list of LINES a user sees, with each line's kind.

    A list contributes one line per item, because that is what is drawn and
    what a click lands on.

    The kind is read from the paragraph's STYLE, not from its element name.
    Measured 2026-08-19: the product's own heading action writes
    `<text:p text:style-name="Heading_20_1">`, not `<text:h>`, so an oracle
    keyed on the element name reports a working heading action as a no-op --
    which is exactly what the first version of this check did.
    """
    content = report.get("content") or ""
    if not content:
        return []
    kinds: dict[str, str] = {}
    for blob in (content, report.get("styles") or ""):
        for match in re.finditer(
                r'<text:list-style[^>]*style:name="([^"]+)"(.*?)</text:list-style>',
                blob, re.S):
            levels = set(re.findall(r"<text:list-level-style-(\w+)",
                                    match.group(2)))
            if "bullet" in levels:
                kinds[match.group(1)] = "bullet"
            elif "number" in levels:
                kinds[match.group(1)] = "number"
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return []
    body = root.find("office:body/office:text", ODF_NS)
    style_of = f"{{{ODF_NS['text']}}}style-name"
    out: list[dict] = []
    for child in (body if body is not None else []):
        tag = child.tag.split("}")[-1]
        if tag in ("p", "h"):
            style = child.get(style_of) or ""
            out.append({"kind": "heading" if tag == "h"
                        or style.startswith("Heading") else "body",
                        "style": style,
                        "text": "".join(child.itertext()).strip()})
        elif tag == "list":
            style = child.get(style_of) or ""
            kind = kinds.get(style) or "list"
            for item in child:
                if item.tag.split("}")[-1] != "list-item":
                    continue
                out.append({"kind": kind, "style": style,
                            "text": "".join(item.itertext()).strip()})
    return out


def set_device_pixel_ratio(session, ratio):
    """Chrome only. Firefox has no CDP here, so its arms say so and score nothing.

    The wall this cell measures moves by more than a factor of three across
    ordinary displays, and a headless run sits on the most forgiving square --
    so a cell that reported one number would be describing the harness rather
    than the product.
    """
    call = getattr(session, "call", None)
    if call is None:
        return {"requested": ratio, "applied": None,
                "why": "this browser session has no CDP; dpr cannot be set"}
    try:
        call("Emulation.setDeviceMetricsOverride",
             {"width": 0, "height": 0, "deviceScaleFactor": ratio,
              "mobile": False})
        return {"requested": ratio,
                "applied": evaluate(session,
                                    "(() => globalThis.devicePixelRatio)()")}
    except Exception as error:            # noqa: BLE001 -- reported, not raised
        return {"requested": ratio, "applied": None,
                "why": f"{type(error).__name__}: {error}"}


def open_long_document(session, pages: int, name: str, timeout: float = 300):
    """A document of an EXACT page count, through the product's file input."""
    payload = base64.b64encode(build_long_document(pages)).decode("ascii")
    dispatched = evaluate(session, OPEN_BYTES.replace("ARG_B64", payload)
                          .replace("ARG_NAME", name))
    state = wait_for(session,
                     lambda s: (s.get("doc") or "") == name
                     and s.get("state") == "ready", timeout)
    return {"pages": pages, "name": name, "dispatched": dispatched,
            "state": (state or {}).get("state")}


# A caret is about 60 dark pixels and it MOVES on every edit, so "the ink
# changed" is satisfied by the caret alone -- measured 2026-08-19 under the
# slow-repaint mutation, which reported 0.28 s while every repaint was being
# delayed by a second and a half.  The marker below is long enough that its own
# glyphs are several hundred pixels of ink, and the delta has to clear that.
KEYSTROKE_MARKER = "LDXLDXLDXLDXLDXLDXLDXLDX"
CARET_SIZED_INK = 200


def wait_until_drawn(session, timeout: float = 45):
    """Is the document ON SCREEN yet -- not: is the session ready.

    `ready` is a statement about the session; the tile arrives afterwards.
    Reading the pixels once, straight after `ready`, reports a page that is
    merely still rendering as a page that renders nothing.
    """
    deadline = time.monotonic() + timeout
    last: dict = {}
    while time.monotonic() < deadline:
        last = evaluate(session, TOP_INK) or {}
        if (last.get("columns") or 0) > 40:
            return {"drawn": True, "ink": last,
                    "seconds": round(timeout - (deadline - time.monotonic()), 2)}
        time.sleep(0.5)
    return {"drawn": False, "ink": last, "seconds": timeout}


def settle_ink(session, tries: int = 40, poll: float = 0.4):
    """Wait until the canvas stops changing, and say what it settled on.

    Measured 2026-08-19: without this, a repaint still in flight from the
    PREVIOUS action lands a fraction of a second after the keystroke and the
    measurement stops on it -- so a build with every repaint delayed by a
    second and a half reported a third of a second, and the mutation aimed at
    the latency threshold went undetected.  The clock cannot start while the
    picture is still moving.
    """
    previous = None
    for _ in range(tries):
        current = (evaluate(session, TOP_INK) or {}).get("ink")
        if current is not None and current == previous:
            return current
        previous = current
        time.sleep(poll)
    return previous


def keystroke_to_ink(session, timeout: float = 90):
    """How long a user waits to SEE the characters they typed.

    Not the latency pill: `run()` writes that BEFORE awaiting renderDocument
    (`web/e2-editor-app.js:281-282`), so the pill excludes the repaint, which
    is the whole of what gets expensive on a long document.
    """
    before = settle_ink(session)
    started = time.monotonic()
    evaluate(session, SET_TEXT.replace("ARG_TEXT", KEYSTROKE_MARKER))
    evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
    while time.monotonic() - started < timeout:
        now = (evaluate(session, TOP_INK) or {}).get("ink")
        if now is not None and before is not None \
                and abs(now - before) > CARET_SIZED_INK:
            return {"seconds": round(time.monotonic() - started, 3),
                    "inkBefore": before, "inkAfter": now,
                    "requiredDelta": CARET_SIZED_INK}
        time.sleep(0.05)
    return {"seconds": None, "inkBefore": before,
            "inkAfter": (evaluate(session, TOP_INK) or {}).get("ink"),
            "requiredDelta": CARET_SIZED_INK}


def wait_for(session, predicate, timeout, poll=0.4):
    deadline = time.monotonic() + timeout
    state = None
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if state and predicate(state):
            return state
        time.sleep(poll)
    return state


def revision_of(state) -> int | None:
    text = (state or {}).get("revision") or ""
    return int(text) if text.isdigit() else None


def wait_saves(session, count, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if (evaluate(session, SAVE_COUNT) or 0) >= count:
            return True
        time.sleep(0.3)
    return False


def capture_save(session, index: int, timeout=90) -> dict:
    """Press the product's own save button and report what the bytes were.

    `index` is the position in the shim's capture list, which is also the number
    of saves this run has already taken.  Returns {} if nothing arrived, and the
    callers treat that as a failed check rather than as an absence of evidence.
    """
    evaluate(session, CLEAR_TOAST)
    evaluate(session, PRESS.replace("ARG_ACTION", "save"))
    if not wait_saves(session, index + 1, timeout):
        return {}
    raw = evaluate(session, READ_SAVE.replace("ARG_INDEX", str(index)))
    return zip_report(base64.b64decode(raw["b64"])) if raw else {}


def zip_report(raw: bytes) -> dict:
    """What the bytes are, in enough detail to refuse a ZIP that is not an ODT.

    Adversarial review, 2026-08-16: the first version of the save check asked
    only for the ZIP magic and a clean CRC, so a valid ZIP containing one text
    file passed it -- as would a DOCX.  `content.xml` was read into the report
    and the read's failure recorded in `zipError`, which nothing looked at.  A
    field the verdict does not read is not a check.
    """
    out = {"bytes": len(raw), "magic": raw[:4].hex(), "isZip": raw[:4] == b"PK\x03\x04"}
    if not out["isZip"]:
        out["head"] = raw[:64].decode("utf-8", "replace")
        return out
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            out["entries"] = len(names)
            out["badEntry"] = archive.testzip()
            out["hasContentXml"] = "content.xml" in names
            out["mimetype"] = (archive.read("mimetype").decode("utf-8", "replace")
                               if "mimetype" in names else None)
            out["content"] = archive.read("content.xml").decode("utf-8", "replace")
            # The corpus defines its own list styles in styles.xml and an
            # action creates automatic ones in content.xml; reading only one of
            # the two leaves half the lists unclassifiable, and
            # "unclassifiable" is what a bullet list masquerading as a numbered
            # one looks like.
            out["styles"] = (archive.read("styles.xml").decode("utf-8", "replace")
                             if "styles.xml" in names else "")
    except Exception as error:            # noqa: BLE001 -- reported, not raised
        out["zipError"] = str(error)
    if out.get("content"):
        try:
            ElementTree.fromstring(out["content"])
            out["contentXmlParses"] = True
        except ElementTree.ParseError as error:
            out["contentXmlParses"] = False
            out["xmlError"] = str(error)
    return out


def is_an_odt(report: dict) -> bool:
    """Every condition the name claims, and each one able to fail on its own."""
    return (bool(report.get("isZip")) and report.get("badEntry") is None
            and report.get("zipError") is None
            and bool(report.get("hasContentXml"))
            and report.get("contentXmlParses") is True
            and report.get("mimetype")
            == "application/vnd.oasis.opendocument.text")


# ---------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--mutate", choices=tuple(MUTATIONS) + ("none",), default="none")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--out", default=None, help="write the report here as JSON")
    args = parser.parse_args()

    report: dict = {
        "schemaVersion": 1,
        "release": "e2-c-product-path",
        "browser": args.browser,
        # NOT a parameter.  Until 2026-08-19 this was `--fixture`, a flag that
        # was written into the report and read by nothing: `navigate()` does
        # not carry it and the page always boots `list-contexts`
        # (web/e2-editor-app.js:701).  A report field that does not control
        # what it names is finding 029's shape, and a run claiming to have
        # measured a document it never opened is worse than one that says
        # nothing.  Filled in below from what the page itself reports.
        "fixture": None,
        "isTrusted": False,
        "notD5": "synthetic events; SPEC E2-C D5 requires trusted input and a human",
        "shims": ["URL.createObjectURL",
                  "HTMLAnchorElement.prototype.click (download anchors)",
                  "#toast.textContent cleared between steps",
                  "ClipboardEvent.clipboardData (Firefox drops it from the "
                  "constructor; defined onto the event with types/getData only)",
                  "#toast is observed and every message recorded -- the "
                  "product's success toast overwrites a repaint failure raised "
                  "during the same open, and 'the product said nothing' is "
                  "the subject of a check",
                  "Emulation.setDeviceMetricsOverride (Chrome only) to sweep "
                  "devicePixelRatio; the wall this measures moves by more than "
                  "3x across ordinary displays"],
        "mutation": args.mutate if args.mutate != "none" else None,
        "checks": [],
        "steps": [],
    }

    scratch = Path(tempfile.mkdtemp(prefix="e2c-product-path-"))
    root = PROJECT / "dist"
    if args.mutate != "none":
        root, mutation_report = apply_mutation(args.mutate, scratch)
        report["mutationDetail"] = mutation_report
    # Written AFTER the mirror is built, so it describes what was served rather
    # than what was intended.
    report["servedShell"] = served_shell_identity(root)

    def check(cid, ok, outcome=None, **fields):
        """One check, with three outcomes rather than two.

        NOT_ESTABLISHED is for a check whose PRECONDITION could not be reached
        -- not for one that failed.  A harness that reports those as failures
        teaches its readers to ignore red, and one that reports them as passes
        is worse.  `finish()` counts them as neither.
        """
        report["checks"].append({
            "id": cid, "ok": bool(ok),
            "outcome": outcome or ("PASS" if ok else "FAIL"), **fields})

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        navigate(session, base)

        booted = wait_for(session, lambda s: s.get("state") in ("ready", "stopped",
                                                               "expired"),
                          args.timeout)
        report["fixture"] = (booted or {}).get("doc")
        report["steps"].append({"step": "boot", "state": booted})
        if not booted or booted.get("state") != "ready":
            report["failedAt"] = "boot"
            return finish(report, args)

        report["steps"].append({"step": "install-shims",
                                "result": evaluate(session, INSTALL)})

        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        caret = wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        report["steps"].append({"step": "place-caret", "state": caret})
        if not caret or "失敗" in (caret.get("latency") or ""):
            report["failedAt"] = "place-caret"
            return finish(report, args)

        # ------------------------------------------------ 049: the save button
        evaluate(session, CLEAR_TOAST)
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        captured = wait_saves(session, 1)
        toast_after_save = evaluate(session, READ_TOAST) or ""
        saved = evaluate(session, READ_SAVE.replace("ARG_INDEX", "0")) if captured else None
        first = zip_report(base64.b64decode(saved["b64"])) if saved else {}
        check("product-save-button-writes-a-real-odt",
              is_an_odt(first) and "NaN" not in toast_after_save,
              observed={"capturedBytes": first.get("bytes"),
                        "magic": first.get("magic"),
                        "head": first.get("head"),
                        "entries": first.get("entries"),
                        "hasContentXml": first.get("hasContentXml"),
                        "contentXmlParses": first.get("contentXmlParses"),
                        "mimetype": first.get("mimetype"),
                        "zipError": first.get("zipError"),
                        "toast": toast_after_save,
                        "anchorClicks": evaluate(session,
                                                 "(() => window.__pp.anchorClicks)()")},
              oracle="the bytes the product hands to the download ARE an ODT -- ZIP "
                     "magic, clean CRC, an ODT mimetype entry and a content.xml "
                     "that parses -- and its own toast reports a size rather than "
                     "NaN")

        # -------------------------------------- 050: three commits, three edits
        before = revision_of(evaluate(session, READ_STATE))
        commits = []
        last = before if before is not None else 0
        for text in IME_TEXTS:
            evaluate(session, CLEAR_TOAST)
            sink = evaluate(session, COMPOSE.replace("ARG_TEXT", text))
            # A commit that is going to be dropped is dropped silently, so this
            # waits for the revision it expects and gives up rather than hanging.
            settled = wait_for(session,
                               lambda s, floor=last: revision_of(s) is not None
                               and revision_of(s) > floor,
                               8)
            observed = revision_of(settled)
            commits.append({"text": text, "sinkAfter": sink, "revision": observed,
                            "toast": evaluate(session, READ_TOAST)})
            if observed is not None:
                last = max(last, observed)
        after = revision_of(evaluate(session, READ_STATE))
        report["steps"].append({"step": "ime-commits", "commits": commits,
                                "revisionBefore": before, "revisionAfter": after})

        # The document, not only the counter: the counter is what round 5's
        # analyzer looked at, and it reported success while two thirds of a
        # user's typing was being dropped.
        evaluate(session, CLEAR_TOAST)
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        wait_saves(session, 2)
        second_raw = evaluate(session, READ_SAVE.replace("ARG_INDEX", "1"))
        second = zip_report(base64.b64decode(second_raw["b64"])) if second_raw else {}
        content = second.get("content") or ""
        present = [t for t in IME_TEXTS if t in content]
        advanced = (after - before) if (after is not None and before is not None) else None
        # Per commit, not only in total.  Adversarial review, 2026-08-16: a
        # product that committed all three texts on the FIRST compositionend and
        # dropped the other two would still show +3 overall with all three
        # strings present.  The per-commit revisions were already being recorded
        # and simply were not being judged.
        stepwise = []
        expected = before
        for entry in commits:
            expected = None if expected is None else expected + 1
            stepwise.append({"text": entry["text"], "expected": expected,
                             "observed": entry["revision"],
                             "ok": expected is not None
                             and entry["revision"] == expected})
        each_landed = bool(stepwise) and all(row["ok"] for row in stepwise)
        check("every-ime-commit-reaches-the-document",
              advanced == len(IME_TEXTS) and len(present) == len(IME_TEXTS)
              and each_landed,
              observed={"revisionBefore": before, "revisionAfter": after,
                        "advancedBy": advanced, "committed": IME_TEXTS,
                        "foundInSavedOdt": present,
                        "perCommitRevision": stepwise,
                        "savedBytes": second.get("bytes")},
              oracle="three commits through the product's composition path each "
                     "advance the revision by exactly one, IN TURN, and all three "
                     "strings are in the saved ODT")

        # ------------------------------------------------------ Ctrl+C reaches
        evaluate(session, DRAG.replace("ARG_X1", "0.20").replace("ARG_Y1", "0.28")
                 .replace("ARG_X2", "0.75").replace("ARG_Y2", "0.28"))
        time.sleep(1.5)
        evaluate(session, CLEAR_TOAST)
        copy_result = evaluate(session, COPY)
        time.sleep(1.5)
        copy_toast = evaluate(session, READ_TOAST) or ""
        # The outcome is classified by WHERE in copySelection it came from, not
        # by whether the product said something.  Read against
        # input/clipboard-adapter.js:
        #   已複製 N 字             -- selection read, clipboard written
        #   CLIPBOARD_DENIED        -- raised only by typedClipboardError(_, "write"),
        #                              i.e. AFTER getSelection returned a non-empty
        #                              text/plain selection.  The engine answered;
        #                              WebDriver refused the OS clipboard.
        #   CLIPBOARD_EMPTY_SELECTION -- the engine was asked and had nothing
        #   CLIPBOARD_UNAVAILABLE   -- never reached the engine
        #   (silence)               -- the defect: no handler at all
        if "已複製" in copy_toast:
            outcome = "copied"
        elif "CLIPBOARD_DENIED" in copy_toast:
            outcome = "selection-read-clipboard-write-denied"
        elif "CLIPBOARD_EMPTY_SELECTION" in copy_toast:
            outcome = "engine-asked-nothing-selected"
        elif copy_toast.strip():
            outcome = "other-failure"
        else:
            outcome = "silent"
        check("ctrl-c-asks-the-engine",
              bool(copy_result and copy_result.get("handlerRan"))
              and outcome in ("copied", "selection-read-clipboard-write-denied"),
              observed={"handlerRan": (copy_result or {}).get("handlerRan"),
                        "toast": copy_toast, "outcome": outcome},
              oracle="a copy event on the product page is handled by the product "
                     "(default prevented) and the ENGINE returns a non-empty "
                     "selection for it -- proved by which error the clipboard "
                     "adapter raises, since CLIPBOARD_DENIED on the copy path is "
                     "reachable only after getSelection has succeeded",
              notEstablished="whether the OS clipboard received the text; WebDriver "
                             "refuses clipboard access, so that half belongs to D5")

        # ------------------------------------------- the three HIGH-risk paths
        #
        # `e2/product-path-coverage.json` named `action:undo`,
        # `action:insert-text` and `listener:click#notice-action` HIGH and driven
        # by nothing.  The last of those is the product's RECOVERY path, and a
        # recovery path nobody has ever pressed is a recovery path nobody knows
        # works.  They run after the checks above so those keep the exact flow
        # they were written for.

        # --- action:insert-text -------------------------------------------
        #
        # Collapse the caret first.  The copy check above leaves the drag's
        # selection live, and `commitText` REPLACES a selection -- correctly, and
        # measured: the first run of the witness clause below went red with all
        # three IME texts gone, because the insert had replaced the line they
        # were on.  The product was right and the check's premise was wrong.
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        evaluate(session, CLEAR_TOAST)
        field = evaluate(session, SET_TEXT.replace("ARG_TEXT", INSERT_MARK))
        before_insert = revision_of(evaluate(session, READ_STATE))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
        inserted_state = wait_for(
            session,
            lambda s, floor=before_insert: revision_of(s) is not None
            and floor is not None and revision_of(s) > floor, 20)
        after_insert = revision_of(inserted_state)
        insert_toast = evaluate(session, READ_TOAST) or ""
        third = capture_save(session, 2)
        insert_content = third.get("content") or ""
        # Witnesses that the insert ADDED the marker rather than replacing the
        # document with it -- "the marker is somewhere in content.xml" is also
        # true of a button that inserts it and destroys everything else.  The
        # set is DERIVED from the save this run already took, so a mutation
        # aimed at another check cannot make this one red (see
        # surviving_witnesses).
        expected_witnesses = surviving_witnesses(content)
        kept_witnesses = [w for w in expected_witnesses if w in insert_content]
        check("product-insert-button-inserts-what-the-field-holds",
              field == INSERT_MARK and is_an_odt(third)
              and INSERT_MARK in insert_content
              and kept_witnesses == expected_witnesses
              and before_insert is not None and after_insert == before_insert + 1,
              outcome=None if expected_witnesses else "NOT_ESTABLISHED",
              observed={"fieldAfterSet": field, "revisionBefore": before_insert,
                        "revisionAfter": after_insert,
                        "markInSavedOdt": INSERT_MARK in insert_content,
                        "witnessesExpected": expected_witnesses,
                        "witnessesKept": kept_witnesses,
                        "toast": insert_toast, "savedBytes": third.get("bytes")},
              oracle="the text standing in the product's own field, inserted by "
                     "the product's own button, advances the revision by exactly "
                     "one and is in the document the product then saves")

        # --- action:undo ---------------------------------------------------
        before_undo = revision_of(evaluate(session, READ_STATE))
        evaluate(session, CLEAR_TOAST)
        evaluate(session, PRESS.replace("ARG_ACTION", "undo"))
        undone_state = wait_for(
            session,
            lambda s, floor=before_undo: revision_of(s) is not None
            and revision_of(s) != floor, 20)
        undo_toast = evaluate(session, READ_TOAST) or ""
        fourth = capture_save(session, 3)
        undo_content = fourth.get("content") or ""
        # `is_an_odt` is not decoration here.  Every oracle below is an ABSENCE,
        # and a save that produced nothing would satisfy an absence for the
        # wrong reason -- which is the exact shape finding 049 hid behind.
        #
        # Nor is the precondition.  The `insert-text` mutation run of
        # 2026-08-16 showed this check going GREEN while undo was untested: the
        # marker was never inserted, so "the marker is gone" was true before
        # undo ran.  An absence is only evidence if the thing was there first.
        was_inserted = INSERT_MARK in insert_content
        # And not MORE than the last edit.  Adversarial review, 2026-08-16: the
        # oracle "the marker is gone" is equally satisfied by a button that
        # deletes the paragraph, empties the document, or rolls the whole
        # session back -- the same confusion SPEC E2-B 5.13 warns about, in the
        # other direction.  The IME commits went in before the marker, so they
        # are the witnesses that undo stopped where it should have.
        undo_witnesses = surviving_witnesses(insert_content)
        undo_kept = [w for w in undo_witnesses if w in undo_content]
        check("product-undo-button-reverses-the-last-edit",
              is_an_odt(fourth) and INSERT_MARK not in undo_content
              and undo_kept == undo_witnesses
              and revision_of(undone_state) != before_undo,
              outcome=None if (was_inserted and undo_witnesses)
              else "NOT_ESTABLISHED",
              observed={"revisionBefore": before_undo,
                        "revisionAfter": revision_of(undone_state),
                        "markWasThereBeforeUndo": was_inserted,
                        "markStillInSavedOdt": INSERT_MARK in undo_content,
                        "witnessesExpected": undo_witnesses,
                        "witnessesKept": undo_kept,
                        "toast": undo_toast, "savedBytes": fourth.get("bytes")},
              oracle="pressing the product's own undo button takes the text the "
                     "insert button just added back OUT of the document -- read "
                     "from the saved ODT, not from the revision counter, because "
                     "D1 covers undo through the shell and this is the button")

        # --- listener:click#notice-action, the recovery path ----------------
        #
        # The first version of this check pressed the button from `ready` and
        # went red with `editor cannot restart from ready`.  That was the check
        # being wrong, not the product: `#notice` is displayed only for
        # `recoverable-error` and `restart-required`, which is exactly the set
        # `EditorSession.restart()` accepts.  Pressing a button the product is
        # not offering measures nothing.
        #
        # So the state has to be reached first, and finding 047 is how: save,
        # then a click-placed caret, then a format action, with nothing in
        # between, produces `MUTATION_OUTCOME_UNKNOWN` -- which IS in
        # RECOVERY_ERRORS, so the queue blocks, the state becomes
        # `recoverable-error`, and the product puts the notice up.  100%
        # reproducible on this artifact, both browsers, four controlled arms.
        evaluate(session, CLEAR_TOAST)
        evaluate(session, INDUCE_047.replace("ARG_X", "0.30").replace("ARG_Y", "0.34"))
        blocked = wait_for(
            session, lambda s: s.get("state") in ("recoverable-error",
                                                  "restart-required"), 60)
        attempts = [{"recipe": "finding 047: save, click, format",
                     "state": (blocked or {}).get("state"),
                     "latency": (blocked or {}).get("latency")}]

        # Finding 053's own route, tried when 047's does not block.  It rests on
        # a defect that is current and reproducible (046) rather than on one
        # whose sequence stopped reproducing, and it is also 053's end-to-end
        # reproduction: the error whose prescription the product could not carry
        # out, produced by the product's own buttons.
        if (blocked or {}).get("state") not in ("recoverable-error",
                                                "restart-required"):
            evaluate(session, CLEAR_TOAST)
            evaluate(session, INDUCE_EMPTY_PARAGRAPH
                     .replace("ARG_X", "0.92").replace("ARG_Y", "0.28"))
            wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
            evaluate(session, BREAK_THEN_LIST)
            wait_for(session, lambda s: "斷行" in (s.get("latency") or "")
                     or "段落" in (s.get("latency") or ""), 30)
            evaluate(session, CLEAR_TOAST)
            evaluate(session, PRESS.replace("ARG_ACTION", "set-list-unordered"))
            blocked = wait_for(
                session, lambda s: s.get("state") in ("recoverable-error",
                                                      "restart-required"), 60)
            empty_cell_state = evaluate(session, READ_STATE) or {}
            empty_cell_toast = evaluate(session, READ_TOAST) or ""
            attempts.append({
                "recipe": "finding 053: click past the line end, break the "
                          "paragraph, list the empty one (finding 046's cell)",
                "state": (blocked or {}).get("state"),
                "latency": (blocked or {}).get("latency"),
                "toast": empty_cell_toast})

            # Finding 046's residual.  Bulleting a blank line is an ordinary
            # edit; until 2026-08-17 it put the session into recoverable-error
            # and told the user to discard everything since the checkpoint.
            # The barrier still declines to verify this shape -- that part is
            # correct and unchanged -- but the DISPOSITION is now "review": the
            # queue stays open, so undo is reachable, which is the only thing
            # that makes the advice honest.
            check("bulleting-a-blank-line-does-not-demand-a-rollback",
                  empty_cell_state.get("state") == "ready"
                  and "無法單獨核對" in empty_cell_toast
                  and "請回到檢查點" not in empty_cell_toast,
                  observed={"state": empty_cell_state.get("state"),
                            "toast": empty_cell_toast,
                            "queueStillOpen":
                                empty_cell_state.get("state") == "ready"},
                  oracle="the product's own buttons, on the cell finding 046 was "
                         "measured on: the session stays ready (so undo is "
                         "reachable) and the message says dispatched-but-"
                         "unverified rather than prescribing a rollback",
                  notEstablished="that the bullet APPLIED. The barrier could not "
                                 "verify it and neither can this check -- saying "
                                 "otherwise is the claim finding 046 was filed "
                                 "for. What is checked is the disposition")

            # DECLARED COST, measured both ways on 2026-08-17: this cell was the
            # only route this runner had into `recoverable-error`, so keeping the
            # queue open costs `notice-action-recovers-the-session` its inducer
            # and it now reports NOT_ESTABLISHED. The `review-disposition`
            # mutation shows the pair moving together -- sentinel off, this check
            # red and the recovery check PASS again. The recovery path is not
            # broken and is not covered; a new inducer is owed (a dispatched
            # failure whose shape is NOT multi-block-readback, e.g. the
            # footnote-apparatus shape on the endnote fixture).
        offered = evaluate(session, READ_NOTICE)
        report["steps"].append({"step": "induce-dispatched-failure",
                                "state": blocked, "notice": offered,
                                "attempts": attempts})

        pressed_notice = evaluate(session, CLICK_NOTICE)
        # rollback() is restart(): a fresh Worker reopened from the newest of
        # the checkpoint and authority bytes.  The document goes away and comes
        # back, so this waits for `ready` rather than for a revision.
        restarted = wait_for(session, lambda s: s.get("state") == "ready", 180)
        notice_toast = evaluate(session, READ_TOAST) or ""
        # The session is not merely in a good-looking state: it can still do the
        # thing the user came for.
        after_rollback = capture_save(session, 5)
        reached = (blocked or {}).get("state") in ("recoverable-error",
                                                   "restart-required")
        # Adversarial review, 2026-08-16: NOT_ESTABLISHED must not become a
        # place for regressions to hide.  "The recipe did not block the queue"
        # is the expected outcome today, but it is ALSO what a removed
        # `set-list-unordered` handler or a broken toolbar would produce.  So
        # the recipe has to have visibly done something: either it blocked the
        # queue, or the format action it dispatched completed.
        latency = (blocked or {}).get("latency") or ""
        recipe_ran = "項目符號" in latency
        # The notice verdict used to `return finish()` on both of its
        # unreachable branches. That was fine while it was the last check; it is
        # not fine now that checks follow it, and shell v14 made the
        # NOT_ESTABLISHED branch the NORMAL path -- so returning there silently
        # stopped running the paste and open-file checks. Measured, not noticed:
        # the run came back with seven checks instead of nine.
        notice_judged = False
        if not reached and not recipe_ran:
            check("notice-action-recovers-the-session", False,
                  observed={"stateAfterRecipe": (blocked or {}).get("state"),
                            "latency": (blocked or {}).get("latency"),
                            "notice": offered},
                  oracle="finding 047's recipe must either block the queue or"
                         " complete the format action it dispatches; neither"
                         " happened, so the product path itself is broken --"
                         " this is NOT the 'precondition unreachable' case")
            notice_judged = True
        if not reached and not notice_judged:
            # Finding 047's sequence did not block the queue here.  That is NOT
            # a verdict on 047: it was measured on 2026-08-15 through a
            # different harness and a shell generation before finding 048
            # changed what placeCaret waits for -- and 047's own diagnosis was
            # that placeCaret's confirmation did not guarantee the next action.
            # Whether 048's fix closed 047 is a question for its own round, not
            # something to conclude from a run that was trying to do something
            # else.  Filed as `queue-047-may-have-closed-under-048`.
            check("notice-action-recovers-the-session", False,
                  outcome="NOT_ESTABLISHED",
                  observed={"stateAfterRecipe": (blocked or {}).get("state"),
                            "latency": (blocked or {}).get("latency"),
                            "notice": offered,
                            "pressedAnyway": evaluate(session, CLICK_NOTICE),
                            "toastFromPressingItAnyway":
                                evaluate(session, READ_TOAST)},
                  why="the product offers this button only in "
                      "`recoverable-error` or `restart-required`, which is the "
                      "same set EditorSession.restart() accepts, and finding "
                      "047's recipe -- the one documented route into that state "
                      "from the product's own UI -- did not block the queue in "
                      "this run.  Pressing the hidden button anyway is recorded "
                      "above and measures nothing about the recovery path.",
                  oracle="a dispatched failure blocks the queue, the product "
                         "OFFERS its recovery button, pressing it returns the "
                         "session to ready, and the product can save afterwards")
            notice_judged = True
        if not notice_judged:
          check("notice-action-recovers-the-session",
                reached and bool((offered or {}).get("shown"))
                and (offered or {}).get("disabled") is False
                and bool(pressed_notice)
                and (restarted or {}).get("state") == "ready"
                and is_an_odt(after_rollback),
                observed={"stateAfterFailure": (blocked or {}).get("state"),
                          "noticeOffered": offered,
                          "buttonFound": pressed_notice,
                          "stateAfterPress": (restarted or {}).get("state"),
                          "toast": notice_toast,
                          "savedBytesAfter": after_rollback.get("bytes"),
                          "savedIsOdt": is_an_odt(after_rollback)},
                oracle="a dispatched failure blocks the queue, the product OFFERS "
                       "its recovery button, pressing it returns the session to "
                       "ready, and the product can save a real ODT afterwards -- "
                       "undo in its place would return EDITOR_NOT_READY on the "
                       "queue the failure just blocked, which is why SPEC E2-B "
                       "5.13 prescribes rollback and not undo",
                notEstablished="WHICH bytes came back.  A save moves the authority "
                               "bytes and there is no way to read the document out "
                               "of the page except by saving, so an edit made after "
                               "the failure cannot be shown to have been discarded "
                               "without destroying the thing being measured")

        # --------------------------- the typing path: Backspace and the arrows
        # Not shortcuts. Until 2026-08-17 the product could be typed into and
        # not corrected: the adapter dropped both delete input types and the
        # arrows raised no beforeinput at all, so fixing one character meant
        # clicking and pressing a toolbar button.
        #
        # Placed after every check that takes a save by POSITIONAL index. The
        # first attempt ran before them and turned the insert check red -- this
        # check REMOVES a character, and the insert check's witnesses are
        # derived from an earlier save, so a backspace can delete the thing
        # another check is standing on.
        evaluate(session, POINT_AT.replace("ARG_X", "0.45").replace("ARG_Y", "0.28"))
        wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        evaluate(session, CLEAR_TOAST)
        before_bs = revision_of(evaluate(session, READ_STATE))
        bs = evaluate(session, DELETE_KEY.replace("ARG_TYPE", "deleteContentBackward"))
        bs_state = wait_for(
            session,
            lambda s, floor=before_bs: revision_of(s) is not None
            and floor is not None and revision_of(s) > floor, 25)
        arrow = evaluate(session, TYPE_KEY.replace("ARG_KEY", "ArrowLeft")
                         .replace("ARG_CTRL", "false"))
        arrow_state = wait_for(
            session, lambda s: "游標左移" in (s.get("latency") or "")
            or "◀" in (s.get("latency") or ""), 25)
        check("backspace-and-arrows-reach-the-document",
              bool((bs or {}).get("handled"))
              and bs_state is not None
              and bool((arrow or {}).get("handled"))
              and arrow_state is not None,
              observed={"backspaceHandled": (bs or {}).get("handled"),
                        "revisionBefore": before_bs,
                        "revisionAfterBackspace": revision_of(bs_state or {}),
                        "arrowHandled": (arrow or {}).get("handled"),
                        "latencyAfterArrow": (arrow_state or {}).get("latency")},
              oracle="a Backspace reaches the ENGINE (the page cancels the event "
                     "and the revision advances) and an ArrowLeft dispatches a "
                     "caret move -- both through the page's own handlers, "
                     "neither of which existed before",
              notEstablished="which character was removed; that is delete-backward's "
                             "own contract and D1 covers it through the shell")

        # ------------------------------------------------------------- Ctrl+X
        # Cut is copy plus a delete, in that order, so a failed copy must not
        # still remove the text. Under WebDriver the clipboard write is refused,
        # which means the delete correctly does NOT run -- so this check can
        # only establish that the product handles the event and asks the engine.
        evaluate(session, DRAG.replace("ARG_X1", "0.20").replace("ARG_Y1", "0.32")
                 .replace("ARG_X2", "0.60").replace("ARG_Y2", "0.32"))
        time.sleep(1.5)
        evaluate(session, CLEAR_TOAST)
        cut_result = evaluate(session, CUT)
        time.sleep(2.0)
        cut_toast = evaluate(session, READ_TOAST) or ""
        cut_reached_engine = ("已剪下" in cut_toast
                              or "CLIPBOARD_DENIED" in cut_toast)
        check("ctrl-x-is-handled-by-the-product",
              bool((cut_result or {}).get("handled")) and cut_reached_engine,
              observed={"handled": (cut_result or {}).get("handled"),
                        "toast": cut_toast},
              oracle="a cut event on the product page is handled by the product "
                     "(default prevented) and reaches the engine's selection "
                     "read -- proved the same way the copy check does, by which "
                     "error the clipboard adapter raises",
              notEstablished="that the text was REMOVED. The delete runs only "
                             "after a successful clipboard write, and WebDriver "
                             "refuses that -- which is the behaviour we want "
                             "(a failed copy must not still delete) and it is "
                             "why the removal half belongs to D5")

        # ------------------------------------------------------ Ctrl+V arrives
        # The mirror of the copy defect: `pasteEvent()` sat on the session and
        # nothing called it, so the product could copy OUT of the document and
        # not back in.  Placed here, after every check with a positional save
        # index, so adding it cannot renumber them.
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        evaluate(session, CLEAR_TOAST)
        before_paste = revision_of(evaluate(session, READ_STATE))
        paste_result = evaluate(session, PASTE.replace("ARG_TEXT", PASTE_MARK))
        pasted_state = wait_for(
            session,
            lambda s, floor=before_paste: revision_of(s) is not None
            and floor is not None and revision_of(s) > floor, 20)
        paste_toast = evaluate(session, READ_TOAST) or ""
        saves_before_paste = evaluate(session, SAVE_COUNT) or 0
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        pasted_doc = (zip_report(base64.b64decode(
            evaluate(session, READ_SAVE.replace(
                "ARG_INDEX", str(saves_before_paste)))["b64"]))
            if wait_saves(session, saves_before_paste + 1) else {})
        payload_survived = bool((paste_result or {}).get("payloadSurvived"))
        check("ctrl-v-reaches-the-document",
              payload_survived
              and pasted_state is not None
              and is_an_odt(pasted_doc)
              and (pasted_doc.get("content") or "").count(PASTE_MARK) == 1,
              outcome=None if payload_survived else "NOT_ESTABLISHED",
              observed={"payloadSurvived": payload_survived,
                        "clipboardDataShimmed": (paste_result or {}).get("shimmed"),
                        # Observed, NOT required: whoever cancels the paste
                        # event is not the subject. The product has no paste
                        # listener at all (see e2-editor-app.js) and the text
                        # still arrives, which is the whole point.
                        "eventCanceled": (paste_result or {}).get("eventCanceled"),
                        "revisionBefore": before_paste,
                        "revisionAfter": revision_of(pasted_state or {}),
                        "toast": paste_toast,
                        "markOccurrences":
                            (pasted_doc.get("content") or "").count(PASTE_MARK)},
              oracle="a paste event on the product page reaches the DOCUMENT: it "
                     "advances the revision, and the pasted "
                     "text appears EXACTLY ONCE in the ODT the product saves "
                     "afterwards -- the document, not the toast. Exactly once, not "
                     "merely present: the sink also sees `beforeinput` with "
                     "insertFromPaste, so a page-level paste handler that fails to "
                     "cancel the event commits the same text twice, and `in` would "
                     "call that a pass",
              notEstablished="whether a REAL Ctrl+V carrying the OS clipboard "
                             "reaches this handler. The payload is synthesised "
                             "through the ClipboardEvent constructor, and where "
                             "that constructor drops the payload (Firefox) it is "
                             "defined onto the event exposing only `types` and "
                             "`getData`. If even that does not take, the check "
                             "reports NOT_ESTABLISHED rather than failing the "
                             "product")

        # ------------------ 058 and 060: is the caret drawn, and drawn WHERE?
        # Every other check in this file reads the DOM or the saved ODT, and all
        # of them pass on a page that paints nothing but the tile.  That is how
        # a product with no visible caret kept nine checks green (058).
        #
        # The oracle is anchored to the LINE'S OWN INK, not to viewport
        # fractions.  Finding 060: the first version counted dark pixels in a
        # band at fixed fractions, and since layoutCanvas sizes the canvas from
        # el.desk.clientWidth its verdict moved with the browser window -- it
        # went red on a build where the caret was demonstrably being drawn.
        #
        # Two clicks on the SAME line: one near its start, one well past its
        # end.  The text does not move between the reads, so the column that
        # gains ink is the caret's second position and the one that loses it is
        # the first.
        CARET_LINE = "0.28"
        evaluate(session, POINT_AT.replace("ARG_X", "0.06")
                 .replace("ARG_Y", CARET_LINE))
        wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        time.sleep(1.0)
        columns_start = evaluate(session, CARET_COLUMNS
                                 .replace("ARG_Y", CARET_LINE)) or {}
        # Past the end of the text: the caret must snap to the line's end, which
        # is what makes "it went where I clicked" checkable without knowing the
        # engine's coordinates.
        evaluate(session, POINT_AT.replace("ARG_X", "0.92")
                 .replace("ARG_Y", CARET_LINE))
        wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        time.sleep(1.0)
        columns_end = evaluate(session, CARET_COLUMNS
                               .replace("ARG_Y", CARET_LINE)) or {}
        caret = caret_from_columns(columns_start, columns_end)
        reachable = bool(columns_start.get("available")
                         and columns_end.get("available")
                         and caret.get("available"))

        check("the-caret-is-drawn-where-it-was-placed",
              reachable and caret.get("strokeGained", 0) > 0
              and caret.get("strokeLost", 0) > 0,
              outcome=None if reachable else "NOT_ESTABLISHED",
              observed=caret,
              oracle="two clicks on the same line move a drawn caret: one "
                     "column gains ink and another loses it. Anchored to the "
                     "line's own ink rather than to viewport fractions, so the "
                     "verdict does not depend on the browser window (060). "
                     "LIMIT: this sees the caret by watching it move, so a "
                     "caret pinned to a constant column reads the same as one "
                     "that is never drawn",
              notEstablished="the sampled band carries no text ink, which is a "
                             "harness problem rather than a product one")

        # And drawn WHERE.  A caret that ignores x, or sits at a fixed offset,
        # or lands on the wrong line, fails this while passing the one above.
        span = caret.get("inkSpan") or 0
        near = caret.get("fractionNearStart")
        past = caret.get("fractionPastEnd")
        check("the-caret-lands-where-the-click-was",
              bool(reachable and span > 0 and near is not None
                   and past is not None and near < 0.25 and past > 0.75),
              outcome=None if reachable and span > 0 else "NOT_ESTABLISHED",
              observed=caret,
              oracle="a click near the start of a line puts the caret in its "
                     "first quarter, and a click past the end puts it in the "
                     "last quarter -- measured against that line's own ink "
                     "extent. A caret that ignores x, one at a constant offset, "
                     "and one on the wrong line all fail this",
              notEstablished="no line ink was found to measure against")


        # ------------------------------- 045, the product half: bold turns OFF
        # LAST on purpose. Three constraints stack up: the checks above take
        # saves by POSITIONAL index so inserting anything earlier renumbers
        # them; the session must be healthy, and the notice block can leave it
        # in recoverable-error; and set-bold is offered for a COLLAPSED caret
        # only -- measured here, `EDITOR_FORMAT_GESTURE_UNSUPPORTED` on a range
        # selection, which is SPEC E2-C 2.5's gesture mask doing its job.
        #
        # The oracle is the product's own rendering of engine state. The page
        # sets aria-pressed on B from `editorState.format.bold`, and sends
        # `enabled: !(state === true)`. If it went back to sending `true`
        # unconditionally -- the defect -- the engine would stay bold and
        # aria-pressed would stay "true" on the second press.
        evaluate(session, POINT_AT.replace("ARG_X", "0.30").replace("ARG_Y", "0.24"))
        wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        evaluate(session, CLEAR_TOAST)
        read_pressed = ("(() => document.querySelector('#toolbar "
                        "button[data-action=\"set-bold\"]')"
                        ".getAttribute('aria-pressed'))()")
        pressed_before = evaluate(session, read_pressed)
        evaluate(session, PRESS.replace("ARG_ACTION", "set-bold"))
        time.sleep(2.0)
        pressed_on = evaluate(session, read_pressed)
        bold_toast = evaluate(session, READ_TOAST) or ""
        evaluate(session, PRESS.replace("ARG_ACTION", "set-bold"))
        time.sleep(2.0)
        pressed_off = evaluate(session, read_pressed)
        # The engine has to be able to answer at all; a build whose format cache
        # never fills would leave this null and the check cannot speak.
        answerable = pressed_on is not None or pressed_off is not None
        check("bold-can-be-turned-off-again",
              answerable and pressed_on == "true" and pressed_off == "false",
              outcome=None if answerable else "NOT_ESTABLISHED",
              observed={"ariaPressedBefore": pressed_before,
                        "ariaPressedAfterFirstPress": pressed_on,
                        "ariaPressedAfterSecondPress": pressed_off,
                        "toastAfterFirstPress": bold_toast},
              oracle="pressing B twice on a collapsed caret leaves the engine "
                     "reporting NOT bold. Until 2026-08-17 the page sent "
                     "`enabled: true` unconditionally, so the second press "
                     "asked for bold again and this would stay \"true\"",
              notEstablished="the engine reported no format state at all "
                             "(aria-pressed absent), so nothing here is about "
                             "the page's choice of `enabled`")

        # ------------- 059: a format that worked must not be reported as failed
        # KNOWN_RED, and the check that carries finding 059's ENGINE half now
        # that `bold-can-be-turned-off-again` passes. The product's own toast is
        # the subject: the document says the action worked (measured on both
        # sides, findings/evidence/059/), and the user is told it failed.
        check("a-format-that-worked-is-not-reported-as-failed",
              "LOK_COMMAND_FAILED" not in bold_toast,
              observed={"toastAfterFirstPress": bold_toast},
              oracle="pressing B does not report a failure to the user. Core "
                     "applies the command; the engine's predicate requires "
                     "success:true and turns core's success:false into "
                     "LOK_COMMAND_FAILED, so the product reports a failure for "
                     "an action the saved document shows succeeded")

        # ------------------- 059: a failed format must not block the session
        # Placed here, after the bold presses above, and deliberately NOT
        # sharing their check: `bold-can-be-turned-off-again` is KNOWN_RED for
        # finding 059's engine half, and a mutation owned by a check that is
        # already red cannot be shown to have been detected.
        #
        # The subject is the DISPOSITION, not the formatting.  Measured on both
        # sides on 2026-08-18: core applies the parameterised inline format on
        # the shipped artifact and reports success:false, so the product used to
        # prescribe "go back to the checkpoint" for a change that had succeeded
        # -- it asked the user to discard work to undo something that worked.
        blocked_state = evaluate(session, READ_STATE) or {}
        notice_shown = evaluate(session, READ_NOTICE)
        check("a-failed-format-does-not-block-the-session",
              blocked_state.get("state") == "ready"
              and not (notice_shown or {}).get("shown"),
              observed={"stateAfterTwoBoldPresses": blocked_state.get("state"),
                        "notice": notice_shown,
                        "toast": bold_toast},
              oracle="after a format action fails, the session is still `ready` "
                     "and no rollback notice is shown. LOK_COMMAND_FAILED is "
                     "emitted only from the UNO command RESULT handler, so core "
                     "answered and the dispatch is established -- the honest "
                     "disposition is `review` (undo stays reachable), not "
                     "`rollback` (discard everything since the checkpoint)")

        # --------------------- format-a-paragraph: five actions, five states
        # The checklist row is "把一段變成標題、內文、項目符號或編號" and until
        # now nothing pressed those buttons -- the coverage registry carried
        # all five as uncovered, which is the shape findings 049, 050 and the
        # unbound Ctrl+C all had.
        #
        # Three disciplines, each of which a simpler version of this check
        # would have got wrong:
        #
        #   * every arm aims at a paragraph in the OPPOSITE state, so an
        #     implementation that does nothing cannot pass.  `set-list-none` on
        #     a paragraph that is not a list, or `set-paragraph-body` on a body
        #     paragraph, is a no-op that scores green;
        #   * the verdict is anchored to the target paragraph's exact TEXT.
        #     The fixture already contains a heading, a bullet list and a
        #     numbered list, so "this document has a heading in it" passes both
        #     when the action changed the wrong paragraph and when it changed
        #     nothing;
        #   * the NEIGHBOURS must survive -- finding 046's shape, where an
        #     action reported against one paragraph had acted on another.
        #
        # The document is re-opened from the fixture first, through the
        # product's own file input, because everything above this point has
        # been editing it: the paste, the backspace and the rollback all move
        # the line structure this check reads.  And it is verified by its BYTES
        # (a witness only that file carries), not by the name the page was
        # handed -- 2026-08-18 spent four rounds measuring a 404 page that the
        # label said was the fixture.
        evaluate(session, CLEAR_TOAST)
        reopened = evaluate(session, OPEN_FILE
                            .replace("ARG_URL", "./e1-fixtures/list-contexts.odt")
                            .replace("ARG_NAME", "format-a-paragraph.odt"))
        wait_for(session, lambda s: (s.get("doc") or "") == "format-a-paragraph.odt"
                 and s.get("state") == "ready", 90)
        baseline = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
        lines = document_lines(baseline)
        arms_spec = [
            {"action": "set-paragraph-heading", "marker": "E1-LC-ISOLATED",
             "was": "body", "becomes": "heading"},
            {"action": "set-paragraph-body", "marker": "E1-LC-HEADING",
             "was": "heading", "becomes": "body"},
            {"action": "set-list-unordered", "marker": "E1-LC-BETWEEN",
             "was": "body", "becomes": "bullet"},
            {"action": "set-list-ordered", "marker": "E1-LC-END",
             "was": "body", "becomes": "number"},
            {"action": "set-list-none", "marker": "E1-LC-BULLET-ONE",
             "was": "bullet", "becomes": "body"},
        ]
        fixture_is_open = (
            is_an_odt(baseline)
            and bool(lines)
            and all(line["text"] for line in lines)
            and all(sum(1 for line in lines if arm["marker"] in line["text"]) == 1
                    for arm in arms_spec))
        arms: list[dict] = []
        for arm in arms_spec:
            record = {"action": arm["action"], "marker": arm["marker"],
                      "from": arm["was"], "to": arm["becomes"]}
            arms.append(record)
            if not fixture_is_open:
                record["outcome"] = "NOT_ESTABLISHED"
                record["why"] = "the fixture is not open (see openedFixture)"
                continue
            scan, bands = stable_bands(session)
            hits = [i for i, line in enumerate(lines)
                    if arm["marker"] in line["text"]]
            record["bands"] = len(bands)
            record["lines"] = len(lines)
            if len(hits) != 1 or len(bands) != len(lines):
                record["outcome"] = "NOT_ESTABLISHED"
                record["why"] = (
                    f"{len(hits)} lines carry the marker and the canvas shows "
                    f"{len(bands)} bands for {len(lines)} lines, so this arm "
                    "cannot say WHICH paragraph it is clicking on")
                continue
            target = hits[0]
            record["lineIndex"] = target
            record["observedBefore"] = lines[target]["kind"]
            if lines[target]["kind"] != arm["was"]:
                record["outcome"] = "NOT_ESTABLISHED"
                record["why"] = (
                    f"the target is already {lines[target]['kind']}, so this "
                    "arm would score green on an action that does nothing")
                continue
            band = bands[target]
            x_fraction = (band["first"] + 4) / scan["width"]
            record["aim"] = {"x": round(x_fraction, 5),
                             "y": round(band["centreFraction"], 5),
                             "band": [band["top"], band["bottom"]]}
            evaluate(session, POINT_AT
                     .replace("ARG_X", f"{x_fraction:.5f}")
                     .replace("ARG_Y", f"{band['centreFraction']:.5f}"))
            placed = wait_for(session,
                              lambda s: "定位游標" in (s.get("latency") or ""), 60)
            record["caret"] = (placed or {}).get("latency")
            # 052's shape: a click the engine will not turn into a caret. The
            # arm has no seat to act from, which is a precondition and not a
            # verdict on the action.
            if not placed or "失敗" in (placed.get("latency") or ""):
                record["outcome"] = "NOT_ESTABLISHED"
                record["why"] = "the caret could not be placed on the target"
                continue
            label = evaluate(session, BUTTON_LABEL
                             .replace("ARG_ACTION", arm["action"]))
            record["buttonLabel"] = label
            evaluate(session, CLEAR_TOAST)
            record["pressed"] = evaluate(session, PRESS
                                         .replace("ARG_ACTION", arm["action"]))
            # A button that does nothing is a FAILURE, not an unreachable
            # precondition: the swallow mutation has to be able to turn this
            # red, so the arm goes on to read the document either way.
            acted = wait_for(session,
                             lambda s, want=label: bool(want)
                             and want in (s.get("latency") or ""), 30)
            record["latency"] = (acted or {}).get("latency")
            record["toast"] = evaluate(session, READ_TOAST)
            after_doc = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
            after = document_lines(after_doc)
            same_shape = len(after) == len(lines)
            record["observedAfter"] = (after[target]["kind"]
                                       if same_shape and target < len(after)
                                       else None)
            record["style"] = (after[target]["style"]
                               if same_shape and target < len(after) else None)
            reached = same_shape and after[target]["kind"] == arm["becomes"]
            text_kept = same_shape and after[target]["text"] == lines[target]["text"]
            neighbours = [
                after[j]["kind"] == lines[j]["kind"]
                and after[j]["text"] == lines[j]["text"]
                for j in (target - 1, target + 1)
                if same_shape and 0 <= j < len(lines)]
            record["neighboursSurvived"] = all(neighbours)
            record["lineCountKept"] = same_shape
            record["textKept"] = text_kept
            record["ok"] = bool(is_an_odt(after_doc) and reached and text_kept
                                and all(neighbours))
            record["outcome"] = "PASS" if record["ok"] else "FAIL"
            if after:
                lines = after
        judged = [a for a in arms if a["outcome"] in ("PASS", "FAIL")]
        established = len(judged) == len(arms_spec)
        check("format-a-paragraph-changes-that-paragraph",
              established and all(a["ok"] for a in judged),
              outcome=None if established else "NOT_ESTABLISHED",
              observed={"openedFixture": {"dispatch": reopened,
                                          "isOdt": is_an_odt(baseline),
                                          "lines": len(lines),
                                          "markersUnique": fixture_is_open},
                        "arms": arms},
              oracle="each of the five paragraph actions, pressed on the "
                     "product's own toolbar with the caret clicked onto a "
                     "paragraph in the OPPOSITE state, leaves THAT paragraph "
                     "in the target state with its text unchanged and both "
                     "neighbours untouched -- read from the ODT the product "
                     "saves, and matched by the paragraph's own text",
              notEstablished="range gestures. The five arms all act on a "
                             "collapsed caret; converting several paragraphs "
                             "at once is refused by the gesture mask "
                             "(p1-2-gesture-mask-inherited), and the blank-line "
                             "cell belongs to finding 046's queue item")

        # --------------------------------- opening a document the user chose
        # Until 2026-08-17 the product could only open the samples in its own
        # dropdown, which makes it a demo of an editor rather than an editor.
        # The oracle is deliberately NOT "the filename changed" -- a page that
        # ignored the bytes entirely would still pass that.  It saves afterwards
        # and looks for text that exists ONLY in the file that was handed over.
        evaluate(session, CLEAR_TOAST)
        opened = evaluate(session, OPEN_FILE
                          .replace("ARG_URL", "./e1-fixtures/markdown-syntax.odt")
                          .replace("ARG_NAME", "chosen-by-the-user.odt"))
        shown = wait_for(session,
                         lambda s: (s.get("doc") or "") == "chosen-by-the-user.odt",
                         60)
        saves_before = evaluate(session, SAVE_COUNT)
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        captured_open = wait_saves(session, (saves_before or 0) + 1)
        after_open = (zip_report(base64.b64decode(
            evaluate(session, READ_SAVE.replace(
                "ARG_INDEX", str((saves_before or 0))))["b64"]))
            if captured_open else {})
        text_after = (after_open.get("content") or "")
        check("product-opens-a-document-the-user-chose",
              opened == "dispatched" and bool(shown)
              and is_an_odt(after_open)
              and "MD-CONTROL" in text_after
              and "E1-LC-HEADING" not in text_after,
              observed={"dispatch": opened,
                        "docLabel": (shown or {}).get("doc"),
                        "savedIsOdt": is_an_odt(after_open),
                        "hasChosenFilesText": "MD-CONTROL" in text_after,
                        "stillHasFixtureText": "E1-LC-HEADING" in text_after},
              oracle="a file handed to the product's own file input is the "
                     "document the engine now holds: saving afterwards returns "
                     "text that exists only in THAT file and none of the text "
                     "from the fixture that was open before",
              notEstablished="that a real OS file picker reaches this handler. "
                             "The File is synthesised and assigned to the input, "
                             "which exercises the page's change handler and not "
                             "the chooser -- the same class of gap D5 exists for")

        # ----------------------------- edit-a-real-length-document: the wall
        # The one checklist row still marked `missing`, and it was marked that
        # way without a measurement -- nothing in this tree could produce a
        # document of a known page count until today.
        #
        # What is judged is NOT "twenty pages must work". Two things, each able
        # to fail on its own, both registered before anything was measured
        # (findings/evidence/sdk-e2/e2-c-validation/long-document/PREDICTION.md):
        #
        #   HONESTY  -- at a length where rendering has broken, the product must
        #               SAY so. Handing back a blank canvas in silence is a
        #               failure, and finding 058 is the precedent: nine checks
        #               stayed green on a page that painted nothing.
        #   USABILITY -- keystroke to visible ink, against a threshold written
        #               down in advance (1,000 ms). `renderDocument()` allows
        #               itself 60 seconds, so without a pre-registered number
        #               this cell would pass while every keystroke took half a
        #               minute.
        #
        # The dpr sweep is not decoration. The wall is a canvas HEIGHT, and
        # canvas height is backingWidth x devicePixelRatio x pages -- so the
        # same document that draws on a 1x display is blank on a 2x one, and a
        # headless run at dpr 1 sits on the most forgiving square there is.
        long_report: dict = {"registeredThresholdMs": 1000, "arms": []}

        def long_arm(pages, dpr, label, edit=True):
            record = {"arm": label, "pages": pages}
            record["dpr"] = set_device_pixel_ratio(session, dpr)
            evaluate(session, CLEAR_TOAST)
            evaluate(session, CLEAR_TOASTS)
            record.update(open_long_document(
                session, pages, f"long-{pages:02d}p-dpr{dpr}.odt"))
            record["geometry"] = evaluate(session, GEOMETRY)
            settled = wait_until_drawn(session)
            record["ink"] = settled["ink"]
            record["drawnAfterSeconds"] = settled["seconds"]
            record["drawn"] = settled["drawn"]
            if edit and record["drawn"]:
                scan, bands = stable_bands(session)
                if bands:
                    band = bands[0]
                    evaluate(session, POINT_AT
                             .replace("ARG_X",
                                      f"{(band['first'] + 4) / scan['width']:.5f}")
                             .replace("ARG_Y", f"{band['centreFraction']:.5f}"))
                    wait_for(session,
                             lambda s: "定位游標" in (s.get("latency") or ""), 60)
                    floor = revision_of(evaluate(session, READ_STATE))
                    record["latency"] = keystroke_to_ink(session)
                    record["revisionAdvanced"] = (
                        revision_of(evaluate(session, READ_STATE)) or 0) > (floor or 0)
            # Every toast the product raised, not the one still on screen.
            record["toasts"] = evaluate(session, READ_TOASTS)
            record["state"] = (evaluate(session, READ_STATE) or {}).get("state")
            long_report["arms"].append(record)
            return record

        # 995 canvas pixels per page at devicePixelRatio 1 on this viewport
        # (measured: 2 pages 2007px, 3 pages 3002px), so the wall sits near 33
        # pages at 1x and near 17 at 2x. The pair is chosen so that the SAME
        # twenty-page document is the drawn arm at 1x and the blank arm at 2x:
        # nothing about the document changes between them, only the display.
        short = long_arm(1, 1, "one-page")
        middle = long_arm(5, 1, "five-pages")
        below = long_arm(20, 1, "below-the-wall")
        above = long_arm(35, 1, "above-the-wall", edit=False)
        above_dpr2 = long_arm(20, 2, "the-same-document-on-a-2x-display",
                              edit=False)

        # The fourth wall, and the one a size sweep alone cannot see:
        # `heightTwips` is assigned once from the open metadata
        # (`sdk/document-sdk.js:374`) and `document-invalidated` calls
        # `renderDocument()` and nothing else (`web/e2-editor-app.js:622`) --
        # no metadata re-read, no `layoutCanvas()`. So after an edit that makes
        # the document taller the canvas still describes the document as it was
        # opened.
        #
        # The ground truth is the SAME code path: save the edited bytes and
        # open them fresh. If that canvas is taller than the one on screen, the
        # document grew and the screen did not.
        set_device_pixel_ratio(session, 1)
        evaluate(session, CLEAR_TOASTS)
        grew = {"arm": "an-edit-that-makes-the-document-taller", "pages": 2}
        grew.update(open_long_document(session, 2, "long-grow.odt"))
        first_geometry = evaluate(session, GEOMETRY) or {}
        grew["heightWhenOpened"] = first_geometry.get("height")
        scan, bands = stable_bands(session)
        if bands and grew["state"] == "ready":
            band = bands[-1]
            evaluate(session, POINT_AT
                     .replace("ARG_X",
                              f"{(band['first'] + 4) / scan['width']:.5f}")
                     .replace("ARG_Y", f"{band['centreFraction']:.5f}"))
            wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
            floor = revision_of(evaluate(session, READ_STATE))
            evaluate(session, SET_TEXT.replace("ARG_TEXT", LONG_INSERT))
            evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
            wait_for(session, lambda s, f=floor: revision_of(s) is not None
                     and f is not None and revision_of(s) > f, 60)
            grew["heightAfterTheEdit"] = (evaluate(session, GEOMETRY)
                                          or {}).get("height")
            edited = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
            grew["editReachedTheDocument"] = LONG_INSERT[:32] in (
                edited.get("content") or "")
            # Re-open the saved bytes through the product's own file input, so
            # the comparison is between two runs of the same code.
            raw = evaluate(session, READ_SAVE.replace(
                "ARG_INDEX", str((evaluate(session, SAVE_COUNT) or 1) - 1)))
            if raw:
                evaluate(session, OPEN_BYTES.replace("ARG_B64", raw["b64"])
                         .replace("ARG_NAME", "long-grown-reopened.odt"))
                wait_for(session,
                         lambda s: (s.get("doc") or "") == "long-grown-reopened.odt"
                         and s.get("state") == "ready", 300)
                grew["heightWhenReopened"] = (evaluate(session, GEOMETRY)
                                              or {}).get("height")
        grew["toasts"] = evaluate(session, READ_TOASTS)
        long_report["arms"].append(grew)

        really_grew = (isinstance(grew.get("heightWhenReopened"), int)
                       and isinstance(grew.get("heightWhenOpened"), int)
                       and grew["heightWhenReopened"] > grew["heightWhenOpened"]
                       and bool(grew.get("editReachedTheDocument")))
        grew["canvasFollowedTheDocument"] = (
            really_grew
            and grew.get("heightAfterTheEdit") == grew.get("heightWhenReopened"))
        grew["groundTruthEstablished"] = really_grew

        # --- HONESTY -------------------------------------------------------
        def spoke_up(record):
            """Did the product tell the user anything about the failure?"""
            said = " ".join(record.get("toasts") or [])
            return ("重繪" in said or "失敗" in said
                    or record.get("state") not in ("ready", None))

        silent = [record for record in (above, above_dpr2)
                  if not record["drawn"] and not spoke_up(record)]
        silent_growth = (really_grew and not grew["canvasFollowedTheDocument"]
                         and not spoke_up(grew))
        long_report["silentArms"] = [record["arm"] for record in silent]
        long_report["silentGrowth"] = silent_growth
        check("a-long-document-is-drawn-or-the-product-says-it-is-not",
              below["drawn"] and not silent and not silent_growth,
              observed={"belowTheWallDrawn": below["drawn"],
                        "silentArms": long_report["silentArms"],
                        "silentGrowth": silent_growth,
                        "arms": long_report["arms"]},
              oracle="a document short enough to render IS rendered, and at "
                     "any length where rendering has broken the product says "
                     "so -- a blank canvas with the session reporting `ready` "
                     "and no message is the failure this checks for. Includes "
                     "the growth case: an edit that makes the document taller "
                     "must either be drawn or be explained",
              notEstablished="WHERE the pixels are lost. render() does not "
                             "throw and no error reaches the page, so this "
                             "cannot say whether the engine returned an empty "
                             "tile or the page failed to paint a good one -- "
                             "and naming a layer without measuring it is what "
                             "findings 040 and 048 were about")

        # A DEVIATION from the plan, recorded rather than quietly taken: the
        # plan asked for a mutation that shrinks MAX_BACKING_WIDTH, so that the
        # wall moves and this cell has to follow it -- proof that it measures a
        # wall and not a constant somebody typed. That mutation would be owned
        # by the check above, which is KNOWN_RED, and a mutation owned by a
        # check that is already red cannot be shown to have been detected. The
        # wall's independence from any constant in this file is instead
        # established by measurement: it was found by sweeping devicePixelRatio
        # on one fixed document (32,590 draws, 32,889 blank), and the canvas
        # element's own cap was measured separately at 65,535. The falsifier
        # the plan wanted is owed again once 062 is fixed.
        #
        # --- USABILITY -----------------------------------------------------
        measured = [record for record in (short, middle, below)
                    if (record.get("latency") or {}).get("seconds") is not None]
        worst = max((record["latency"]["seconds"] for record in measured),
                    default=None)
        long_report["worstKeystrokeSeconds"] = worst
        check("editing-a-long-document-stays-responsive",
              len(measured) == 3 and worst is not None
              and worst * 1000 <= long_report["registeredThresholdMs"]
              and all(record.get("revisionAdvanced") for record in measured),
              outcome=None if len(measured) == 3 else "NOT_ESTABLISHED",
              observed={"thresholdMs": long_report["registeredThresholdMs"],
                        "worstSeconds": worst,
                        "perArm": [{"pages": r["pages"],
                                    "seconds": (r.get("latency") or {}).get("seconds"),
                                    "revisionAdvanced": r.get("revisionAdvanced")}
                                   for r in (short, middle, below)]},
              oracle="a keystroke becomes visible ink within the 1,000 ms "
                     "registered in PREDICTION.md, at every length the product "
                     "can still draw, and the document actually advances a "
                     "revision. The threshold was written down before the "
                     "measurement because renderDocument() allows itself 60 "
                     "seconds and would otherwise pass",
              notEstablished="lengths past the wall. Nothing is drawn there, "
                             "so there is no ink to time")
        set_device_pixel_ratio(session, 1)

        # ------------------- recover-from-an-error: judge the product by its
        # ------------------- own declaration, not by our hopes
        #
        # LAST in the file, and it has to be: the inducer is finding 038, which
        # leaves the engine's pthread unable to answer anything ever again.  A
        # check that runs after it is running against a corpse.
        #
        # The oracle is NOT "a legal ODT comes back afterwards" -- that passes
        # on reopening the untouched authority bytes, which is precisely the
        # outcome a user would call losing their work.
        #
        # Adjudicated 2026-08-18: it is also not "M1 must survive and M2 may or
        # may not".  `_checkpointBeforeSelection` saves before EVERY selection
        # gesture on a dirty document, and 038's inducer IS a selection
        # gesture, so on today's shell M2 should come back too.  An oracle that
        # accepts either answer cannot go red when that mechanism degrades to a
        # no-op -- finding 046's shape exactly.
        #
        # So the product is judged against what IT declared, in the place the
        # user can see it, BEFORE the button was pressed: `#s-checkpoint` reads
        # 有（rN） / 寫入失敗 / 無.  Three branches, and the oracle is decoupled
        # from the inducer -- when 038 is fixed and the inducer is replaced,
        # only the recipe changes.
        #
        # Plus a CAPABILITY clause the three branches cannot supply on their
        # own: when the inducer is a selection gesture on a dirty document, the
        # declaration may not be 無.  Without it, a `_checkpointBeforeSelection`
        # that had degraded to a no-op would declare 無, deliver 無, and be
        # scored consistent.
        recovery: dict = {}
        evaluate(session, CLEAR_TOAST)
        recovery["opened"] = evaluate(session, OPEN_FILE
                                      .replace("ARG_URL",
                                               "./e1-fixtures/endnote-frame.odt")
                                      .replace("ARG_NAME",
                                               "recover-from-an-error.odt"))
        wait_for(session,
                 lambda s: (s.get("doc") or "") == "recover-from-an-error.odt"
                 and s.get("state") == "ready", 90)
        # The save comes FIRST: it is a round trip through the engine, so it
        # both proves the fixture is really open (by its bytes) and gives the
        # line list the aim is derived from.  Measured 2026-08-19: scanning
        # straight after `ready` caught the page still showing the PREVIOUS
        # document's tile -- four bands that belonged to a file this check had
        # already finished with -- and the marker went into the wrong
        # paragraph.  `ready` is a statement about the session, not about what
        # is on the screen.
        opening = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
        base_lines = document_lines(opening)
        recovery["openedLines"] = [line["text"][:48] for line in base_lines]
        note_index = [i for i, line in enumerate(base_lines)
                      if "EN-NOTE" in line["text"]]
        scan, bands = stable_bands(session)
        # The page draws the endnote apparatus as well as the body, so there
        # are MORE bands than lines here -- but the body paragraphs are drawn
        # first and in order, so the note paragraph's line index is its band
        # index.  Waiting for that inequality is what makes "the tile on
        # screen is this document's" a condition rather than a hope.
        for _ in range(8):
            if len(bands) >= len(base_lines):
                break
            time.sleep(1.0)
            scan, bands = stable_bands(session)
        recovery["bands"] = [[b["top"], b["bottom"]] for b in bands]
        recovery["noteLineIndex"] = note_index
        established = (is_an_odt(opening) and len(note_index) == 1
                       and len(bands) >= len(base_lines))
        if established:
            band = bands[note_index[0]]
            x_fraction = (band["first"] + 4) / scan["width"]
            evaluate(session, POINT_AT.replace("ARG_X", f"{x_fraction:.5f}")
                     .replace("ARG_Y", f"{band['centreFraction']:.5f}"))
            placed = wait_for(session,
                              lambda s: "定位游標" in (s.get("latency") or ""), 60)
            recovery["caret"] = (placed or {}).get("latency")
            established = bool(placed) and "失敗" not in (placed.get("latency") or "")
        if established:
            floor = revision_of(evaluate(session, READ_STATE))
            evaluate(session, COMPOSE.replace("ARG_TEXT", RESCUE_SAVED))
            wait_for(session, lambda s, f=floor: revision_of(s) is not None
                     and f is not None and revision_of(s) > f, 25)
            saved_doc = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
            saved_lines = document_lines(saved_doc)
            # The marker is typed a few pixels into the first glyph, so the
            # caret lands after the first CHARACTER and the marker is inserted
            # inside the word: "E救回標記已存N-NOTE ...".  Matching the anchor
            # without removing the marker first reported that a marker sitting
            # in the right paragraph was in the wrong one.
            host = [line for line in saved_lines
                    if "EN-NOTE" in line["text"].replace(RESCUE_SAVED, "")]
            recovery["markerLandedOnTheNoteParagraph"] = bool(host) \
                and RESCUE_SAVED in host[0]["text"]
            recovery["markerLandedIn"] = [line["text"][:48]
                                          for line in saved_lines
                                          if RESCUE_SAVED in line["text"]]
            recovery["checkpointAfterSave"] = \
                (evaluate(session, READ_STATE) or {}).get("checkpoint")
            established = bool(recovery["markerLandedOnTheNoteParagraph"])
        if established:
            # M2: typed AFTER the save, so it exists only in the engine.  This
            # is the work a user would lose.
            floor = revision_of(evaluate(session, READ_STATE))
            evaluate(session, COMPOSE.replace("ARG_TEXT", RESCUE_UNSAVED))
            dirty = wait_for(session, lambda s, f=floor: revision_of(s) is not None
                             and f is not None and revision_of(s) > f, 25)
            recovery["revisionWithUnsavedWork"] = revision_of(dirty or {})
            established = dirty is not None
        if established:
            # The inducer.  Finding 038: a drag that COVERS the endnote
            # reference mark of a paragraph whose note body holds an as-char
            # frame.  The selection itself returns; the drain's next read of
            # the selection never does, and TIMEOUT is in RECOVERY_ERRORS.
            scan, bands = stable_bands(session)
            for _ in range(8):
                if len(bands) >= len(base_lines):
                    break
                time.sleep(1.0)
                scan, bands = stable_bands(session)
            recovery["bandsAtInducer"] = [[b["top"], b["bottom"]] for b in bands]
            # The SAME derived index as the marker used. The first version of
            # this left a hard-coded 1 here and dragged across the endnote's
            # own body instead of the reference mark -- the selection was
            # healthy, nothing wedged, and the check reported "038 no longer
            # reproduces". A wrong aim reads exactly like a fixed defect.
            band = (bands[note_index[0]]
                    if len(bands) >= len(base_lines) else None)
            if band is None:
                established = False
            else:
                left = max(0.0, (band["first"] - 6) / scan["width"])
                right = min(1.0, (band["last"] + 10) / scan["width"])
                recovery["inducer"] = {
                    "name": "INDUCE_FOOTNOTE_APPARATUS",
                    "finding": "038",
                    "recipe": "drag across the endnote reference mark, then one "
                              "more operation -- the selection returns healthy "
                              "and the NEXT read is what wedges the engine",
                    "drag": [round(left, 5), round(right, 5),
                             round(band["centreFraction"], 5)]}
                evaluate(session, DRAG
                         .replace("ARG_X1", f"{left:.5f}")
                         .replace("ARG_Y1", f"{band['centreFraction']:.5f}")
                         .replace("ARG_X2", f"{right:.5f}")
                         .replace("ARG_Y2", f"{band['centreFraction']:.5f}"))
                # The checkpoint is written INSIDE the selection's queue item,
                # before the engine is asked to select anything, so it is
                # already there while the session is still healthy.  Waiting
                # for it is how the recipe proves the gesture ran at all.
                after_drag = wait_for(
                    session, lambda s: (s.get("checkpoint") or "").startswith("有"),
                    60)
                recovery["stateAfterDrag"] = (after_drag or {}).get("state")
                recovery["checkpointAfterDrag"] = (after_drag or {}).get("checkpoint")
                # ONE MORE OPERATION, and it is not optional.  Finding 038's
                # own correction (2026-08-13): the selection returns and the
                # engine is still alive -- what kills it is the first READ of
                # that selection.  `_drain` short-circuits its getState when
                # the operation's result already carries `state`, so the
                # selection's own drain never performs that read and the
                # session sits `ready` indefinitely.  Measured 2026-08-19: 77
                # seconds of health after the drag, then a single click ->
                # `busy` -> `recoverable-error` about 30 s later, which is the
                # drain's own getState deadline.
                #
                # A CLICK, not a drag: placeCaret takes no checkpoint, so the
                # declaration under test is the one the drag already made.
                evaluate(session, POINT_AT.replace("ARG_X", "0.30")
                         .replace("ARG_Y", f"{band['centreFraction']:.5f}"))
                wedged = wait_for(session,
                                  lambda s: s.get("state") in ("recoverable-error",
                                                               "restart-required"),
                                  150)
                recovery["stateAfterNextOperation"] = (wedged or {}).get("state")
                established = (wedged or {}).get("state") in ("recoverable-error",
                                                              "restart-required")
        if established:
            # The declaration, read at the moment the product offers the
            # button -- before it is pressed, which is the whole point.
            declared = (wedged or {}).get("checkpoint") or ""
            offered = evaluate(session, READ_NOTICE) or {}
            recovery["declaredCheckpoint"] = declared
            recovery["notice"] = offered
            recovery["pressed"] = evaluate(session, CLICK_NOTICE)
            back = wait_for(session, lambda s: s.get("state") == "ready", 240)
            recovery["stateAfterPressing"] = (back or {}).get("state")
            rescued = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
            text = rescued.get("content") or ""
            saved_back = RESCUE_SAVED in text
            unsaved_back = RESCUE_UNSAVED in text
            recovery["savedWorkCameBack"] = saved_back
            recovery["unsavedWorkCameBack"] = unsaved_back
            recovery["stillAnOdt"] = is_an_odt(rescued)
            branch = ("checkpoint" if declared.startswith("有")
                      else "write-failed" if "寫入失敗" in declared
                      else "none")
            recovery["branch"] = branch
            # 無 is a legitimate answer for a session that has nothing to
            # rescue -- but not for THIS inducer, which is a selection gesture
            # on a dirty document, the exact case the checkpoint exists for.
            capability_held = branch != "none"
            recovery["capabilityClause"] = {
                "requires": "a selection gesture on a dirty document must not "
                            "leave the product declaring 無",
                "held": capability_held}
            if branch == "checkpoint":
                honoured = saved_back and unsaved_back
            elif branch == "none":
                honoured = saved_back and not unsaved_back
            else:
                # "We tried to protect your work and the save FAILED" is not
                # the same thing to say as "there was nothing to protect", and
                # the product's notice has only the second sentence -- its
                # branch is on `hasCheckpoint` alone, so both cases print the
                # line below.  The shell already decides the difference
                # (recovery-notice.js, `checkpointFailed`); the product does
                # not render it.  So this branch requires the notice to SAY
                # something else, and today it cannot.
                honoured = saved_back and (offered.get("text") or "") != \
                    "引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。"
            recovery["declarationHonoured"] = honoured
            check("recovery-returns-what-the-product-promised",
                  bool(honoured and capability_held
                       and (back or {}).get("state") == "ready"
                       and is_an_odt(rescued)),
                  observed=recovery,
                  oracle="the product declares where its recovery button will "
                         "take the user BEFORE it is pressed -- #s-checkpoint "
                         "reads 有（rN）, 寫入失敗 or 無 -- and pressing it "
                         "delivers exactly that: with a checkpoint, both the "
                         "saved and the unsaved marker come back; without one, "
                         "the saved marker comes back and the unsaved one does "
                         "not. Plus a capability clause the branches cannot "
                         "supply: this inducer IS a selection gesture on a "
                         "dirty document, so the declaration may not be 無",
                  notEstablished="whether a checkpoint WRITE FAILURE is "
                                 "surfaced. The shell decides it "
                                 "(recovery-notice.js: checkpointFailed) and "
                                 "the product's notice has a two-way branch on "
                                 "hasCheckpoint only, so that case reaches the "
                                 "user as 'there was nothing to rescue'. This "
                                 "run did not produce it")
        else:
            check("recovery-returns-what-the-product-promised", False,
                  outcome="NOT_ESTABLISHED",
                  observed=recovery,
                  why="the inducer did not put the session into a state where "
                      "the product OFFERS its recovery button. The recipe is "
                      "finding 038 -- a drag covering the endnote reference "
                      "mark of a paragraph whose note body holds an as-char "
                      "frame -- and this is the loud exit for 038 no longer "
                      "reproducing, NOT a silent pass. The recovery path is "
                      "then uncovered again and needs a new inducer",
                  oracle="see the established branch: the product's own "
                         "declaration, honoured")
        return finish(report, args)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        shutil.rmtree(scratch, ignore_errors=True)


def finish(report: dict, args) -> int:
    checks = report["checks"]
    # A check whose precondition was never reached is neither evidence for the
    # product nor against it.  It is counted separately so that a run does not
    # go green on a path it did not exercise, and does not go red on one it
    # could not.
    unestablished = [c["id"] for c in checks
                     if c.get("outcome") == "NOT_ESTABLISHED"]
    report["notEstablishedChecks"] = unestablished
    judged = [c for c in checks if c.get("outcome") != "NOT_ESTABLISHED"]
    # A declared known-red check that PASSES means the defect is fixed and the
    # declaration is now hiding a real signal.  Reported either way.
    still_red = [c["id"] for c in judged if c["id"] in KNOWN_RED and not c["ok"]]
    healed = [c["id"] for c in judged if c["id"] in KNOWN_RED and c["ok"]]
    report["knownRed"] = {cid: KNOWN_RED[cid] for cid in still_red}
    report["staleKnownRedDeclarations"] = healed

    spec = MUTATIONS[args.mutate] if args.mutate != "none" else None
    if spec and spec.get("expectedToBeDetected") is False:
        # A mutation this harness does NOT claim to catch.  Recorded with its
        # reason, so the limit lives in the evidence instead of in somebody's
        # head -- and if it ever IS caught, the run says the limit is stale.
        # `judged`, not `checks`: a NOT_ESTABLISHED check has ok False, and
        # reading that as "detected" would turn a check that never ran into a
        # declaration that the limit is stale.
        red = [c for c in judged if c["id"] == spec["check"] and not c["ok"]]
        # Adversarial review, 2026-08-16: this branch used to set ok True
        # unconditionally, so a run with a declared-undetectable mutation exited
        # 0 even when the SAVE, IME, insert and undo checks were all failing.
        # A declaration about one check is not a pass for the others.
        others_ok = all(c["ok"] for c in judged if c["id"] != spec["check"])
        report["mustGoRed"] = []
        report["ok"] = bool(others_ok)
        report["verdict"] = (
            "this mutation is DETECTED after all -- the recorded limit is out of "
            "date and should be removed" if red
            else ("not detected, as declared: " + spec.get("why", "")
                  if others_ok else
                  "the declared-undetectable mutation was not detected, AS "
                  "DECLARED, but another check failed in the same run"))
    elif spec:
        # The declared NOT_ESTABLISHED collateral, verified rather than assumed:
        # a check declared here that RAN (red or green) means the declaration is
        # stale, and the run says so instead of quietly agreeing with itself.
        declared_void = spec.get("alsoNotEstablished", [])
        stale_void = [c["id"] for c in checks
                      if c["id"] in declared_void
                      and c.get("outcome") != "NOT_ESTABLISHED"]
        report["declaredNotEstablished"] = declared_void
        report["staleNotEstablishedDeclarations"] = stale_void
        must_be_red = {spec["check"], *spec.get("alsoRed", [])}
        report["mustGoRed"] = sorted(must_be_red)
        # A must-go-red check that was NOT_ESTABLISHED did not detect anything:
        # it never ran.  Counting it as a detection would be the exact failure
        # this whole mechanism exists to prevent, so `judged` is used here.
        reds = [c for c in judged if c["id"] in must_be_red]
        others_ok = all(c["ok"] for c in judged
                        if c["id"] not in must_be_red
                        and c["id"] not in declared_void
                        and c["id"] not in KNOWN_RED)
        report["ok"] = bool(len(reds) == len(must_be_red)
                            and all(not c["ok"] for c in reds) and others_ok
                            and not stale_void)
        report["verdict"] = (
            "the mutation was detected by the check that owns it"
            if report["ok"] else
            ("a check declared NOT_ESTABLISHED for this mutation ran after all:"
             f" {stale_void} -- the declaration is stale" if stale_void else
             "THE MUTATION WAS NOT DETECTED -- the check cannot fail, did not "
             "run, or another check failed with it"))
    else:
        report["ok"] = bool(judged) and all(
            c["ok"] for c in judged if c["id"] not in KNOWN_RED)
        report["verdict"] = (
            ("every product path this covers behaves"
             + (f"; {len(unestablished)} not established" if unestablished else "")
             + (f"; {len(still_red)} known red" if still_red else ""))
            if report["ok"] else "a product path is broken")
    if healed:
        report["ok"] = False
        report["verdict"] = (f"a check declared KNOWN_RED passed: {healed} -- the "
                             "defect is fixed and the declaration must be removed "
                             "before it hides the next one")
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
