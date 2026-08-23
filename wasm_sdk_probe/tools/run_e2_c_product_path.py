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
KNOWN_RED: dict[str, str] = {
    # EMPTY, and that is the third time this file has been empty.
    #
    # It held finding 064 (2026-08-21) and then finding 065 (2026-08-21), and
    # BOTH ARE RETRACTED.  They were the same defect seen twice: not in the
    # product and not in the engine, but in `inline_styles_of()`, which stopped
    # at "the marker is not inside a <text:span>, therefore it carries no
    # formatting".  ODF does not work that way -- a uniformly formatted
    # paragraph carries its character properties on its own automatic style and
    # emits no span at all -- and "the marker alone in its paragraph" is exactly
    # what every arm here produces.
    #
    # Caught by an OPERATOR on 2026-08-22, who could see bold on the canvas
    # while the saved document read `bold: false`.  Nothing automated in this
    # tree could have caught it: every check that could have is downstream of
    # the same function.
    #
    # Both retractions ran through this file's own mechanism -- a declared-red
    # check that passes fails the round as a stale declaration -- and it worked
    # both times.

    # Was empty as of 2026-08-19, and that was a first for this file.
    #
    # Both entries came off on the same run, and the runner is what said so:
    # it reports a declared-red check that PASSES as a STALE DECLARATION and
    # fails the round, so neither could quietly outlive its defect.
    #
    #   * `a-format-that-worked-is-not-reported-as-failed` -- finding 059's
    #     engine half. The engine no longer gates the four inline formats on
    #     core's `success` field, which was measured ANTI-correlated with the
    #     request being honoured; it compares the observed state against the
    #     requested one instead.
    #   * `the-canvas-follows-a-document-that-grew` -- finding 062's second
    #     half. The engine reports the document's size on the paint reply, so a
    #     page that grew by a page is no longer drawn at the size it had when
    #     it was opened.
    #
    # Both shipped in the relink of 2026-08-19 (artifact 296f3ea727725fbb).
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

# Typed through the composition path and then undone from the keyboard.
KEYBOARD_MARK = "鍵盤標記KBD"

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
  // Read the RECORDS, not the node.  Reading `toastNode.textContent` once per
  // callback loses every message that was replaced inside the same batch, and
  // that is exactly the case this has to catch: `openDocument()` renders and
  // its caller then toasts "opened", so a repaint failure raised during the
  // open is overwritten in the same turn.  Measured 2026-08-19 -- the product
  // DID report a failed repaint and this observer recorded only the success.
  new MutationObserver((records) => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        const text = node.textContent;
        if (text) pp.toasts.push(text);
      }
      if (record.type === "characterData" && record.target.data)
        pp.toasts.push(record.target.data);
    }
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

# Roadmap 3.4's region, read from the page because THIS check is about what the
# page decided to say. The accessibility TREE is measured by
# `probe_aria_projection.py`; asking the DOM here would be the wrong instrument
# for that question and the right one for this.
# What the toolbar says the engine's format cache holds.  Absent when the
# engine says it does not know, which the page renders by REMOVING the
# attribute rather than by guessing "off".
FORMAT_BUTTON_STATE = """(() => {
const b = document.querySelector('#toolbar button[data-action="ARG_ACTION"]');
return b ? b.getAttribute('aria-pressed') : null;
})()"""

READ_A11Y_REGION = """(() => {
const para = document.querySelector('#a11y-para');
const doc = document.querySelector('#a11y-doc');
if (!para || !doc) return { present: false };
return { present: true, text: para.textContent,
         reason: para.dataset.reason, offers: doc.dataset.offers };
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
const EXCLUDE_CARET = ARG_EXCLUDE_CARET;
const canvas = document.querySelector('#canvas');
const w = canvas.width, h = canvas.height;
const data = canvas.getContext('2d').getImageData(0, 0, w, h).data;
const dark = new Uint8Array(w * h);
const columnTotals = new Int32Array(w);
const opaqueTotals = new Int32Array(w);
for (let y = 0; y < h; y += 1) {
  for (let x = 0; x < w; x += 1) {
    const i = (y * w + x) * 4;
    if (data[i+3] > 128) opaqueTotals[x] += 1;
    if (data[i+3] > 128 && data[i] < 100 && data[i+1] < 100 && data[i+2] < 100) {
      dark[y * w + x] = 1; columnTotals[x] += 1;
    }
  }
}
// THE PAGE IS OPAQUE AND EVERYTHING AROUND IT IS NOT.
//
// Finding 075, and it is the border test below that this replaces in practice.
// That test looks for a column inked DARK down a fifth of the canvas, and on
// this fixture it finds ONE column and never clips -- measured offline on four
// captured canvases, both cores, at rest and after a caret. It protected
// nothing; the shipped core was safe only because its off-page area is
// TRANSPARENT, so `data[i+3] > 128` already excluded it.
//
// The accessibility core stops being transparent there. After a caret
// placement it leaves uninitialised memory in the margins: 184 distinct alpha
// values where the shipped core has 33, 290 opaque pixels where the shipped
// core has 0, and 31 of them dark enough to count as ink. Thirty-one pixels,
// scattered one to three per row in the gaps BETWEEN lines, merged two lines
// into one band and inflated its extent from 157 to 634 -- which collapsed the
// density to 0.133, a hair under the 0.15 floor, and the band was discarded
// with two paragraphs inside it that the user can see perfectly well.
//
// Opacity is the discriminator because it is a property this rendering
// actually HAS in both states: the page is drawn opaque, the surround is not.
// Measured on the same four canvases -- page columns are >= 96.9% opaque,
// off-page columns at most 7.6% even with the garbage in them, and all four
// agree on the same page range (15..709). The threshold is the same 0.20 the
// border test uses, and the daylight around it is 13x in the worst case.
//
// It cannot change the shipped core's readings: there it drops 0 pixels, on
// every canvas measured. That is not a hope, it is what "the surround is
// transparent" means.
let pageLeft = -1, pageRight = w;
for (let x = 0; x < w; x += 1)
  if (opaqueTotals[x] > h * 0.20) { if (pageLeft < 0) pageLeft = x; pageRight = x; }
const pageClipped = pageLeft >= 0 && pageRight - pageLeft > w * 0.5;
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
// THE CARET IS INK, AND THIS HARNESS AIMS FROM INK.
//
// Finding 072.  Once finding 068 made the caret land where the user is
// actually typing, a 16-row vertical bar started sitting in the 10-row gap
// between two lines of text -- and text_bands() merges runs separated by 8
// rows or fewer, so those two lines became ONE band and every check that aims
// by band index aimed a line off.  The bar makes the ink CONTIGUOUS from the
// bottom of one line to the top of the next, so there is no separate run for
// a filter to drop: the caret has to go before the rows are counted, which is
// here.  (The first remedy dropped thin RUNS, passed seven unit tests, and
// changed nothing.)
//
// WHERE it is comes from the DOM rather than from a guess about which column
// looks like a caret.  #sink rides the caret since finding 069 because an IME
// puts its candidate window against the focused element -- that is a PRODUCT
// requirement, not a handle published for this harness, which the page
// deliberately does not do (see CARET_COLUMNS above).
//
// AND THE DOM ALONE IS NOT ENOUGH.  paint() moves the sink only on the paints
// where it DRAWS a caret, and it draws none while a selection is a range --
// so during a drag the sink sits at the caret's last position and there is no
// caret there now.  Excluding that rectangle would delete real glyphs from
// the scan.  So the two have to agree: the page says the caret is here, AND a
// vertical stroke is in fact there.  When they disagree nothing is excluded
// and the scan is what it always was.
const sink = document.querySelector('#sink');
const canvasRect = canvas.getBoundingClientRect();
let caret = null;
let caretRemoved = false;
let caretWhy = 'no #sink in the page';
if (sink && canvasRect.width > 0 && canvasRect.height > 0) {
  const s = sink.getBoundingClientRect();
  const sx = w / canvasRect.width, sy = h / canvasRect.height;
  const x0 = Math.round((s.left - canvasRect.left) * sx);
  const y0 = Math.round((s.top - canvasRect.top) * sy);
  const y1 = Math.round((s.bottom - canvasRect.top) * sy) - 1;
  // THE INTERIOR ROWS, NOT ALL OF THEM, and this is the difference between a
  // remedy that fires and one that reports "stale sink" at the caret it is
  // looking straight at.
  //
  // The bar is a fillRect at FRACTIONAL coordinates and, at
  // devicePixelRatio 1, one nominal backing pixel wide -- so its alpha in a
  // column is the PRODUCT of the horizontal and vertical coverage, and the
  // first and last rows are dimmed by the vertical factor on top of a
  // horizontal factor already below 1.  Measured on this page's own geometry
  // (725x1012 backing; a 15.59-row bar at y=88.125 whose column coverage is
  // 0.744): 14 dark rows inside a 16-row sink window.  A ratio taken over all
  // sixteen wants 14.4 and declines.  Taken over the fourteen interior rows
  // it is 14/14, and a glyph column is still 5/14.  Both populations keep
  // their daylight; only the antialiased ends are dropped.
  const top = y0 + 1, bottom = y1 - 1;
  const rows = bottom - top + 1;
  if (x0 < 0 || x0 >= w || y0 < 0 || y1 >= h || rows < 3) {
    caretWhy = 'the sink is not inside the canvas';
  } else {
    // A drawn caret is a filled rectangle, so its column carries ink on
    // essentially every interior row of its own height.  A glyph column does
    // not: text is dense per ROW and sparse per COLUMN, and that asymmetry is
    // the whole reason the two can be told apart.
    //
    // PAGE BORDERS ARE EXCLUDED FIRST.  A border is inked down the whole page
    // and satisfies any vertical-stroke test, so a stale sink parked within
    // two columns of one would "find" a caret that is not there -- and the
    // field that records it is the positive control, which would then be
    // satisfied by the wrong thing.
    const solid = (x) => {
      if (x < 0 || x >= w || border[x]) return false;
      let n = 0;
      for (let y = top; y <= bottom; y += 1) if (dark[y * w + x]) n += 1;
      return n >= rows * 0.9;
    };
    // THE SINK'S COLUMN IS NOT EXACTLY THE BAR'S COLUMN.  moveSinkToCaret
    // rounds to CSS pixels and paint() draws in BACKING pixels, so converting
    // back can land up to 0.5*devicePixelRatio + 0.5 columns away -- two, on
    // the ratio-3 arm of this harness's own devicePixelRatio sweep.  Three
    // either side covers that slack plus the widest bar this page can draw
    // (round(canvasWidth * 15 / widthTwips), three at the 2400-pixel cap).
    //
    // Every solid column in that window at once, rather than a seed and two
    // walks: a walk that goes left to exhaustion before going right can spend
    // its whole budget on the wrong side of a seed that was not the leftmost
    // column, and a window has no side to prefer.
    const columns = [];
    for (let x = x0 - 3; x <= x0 + 3; x += 1) if (solid(x)) columns.push(x);
    if (!columns.length) {
      caretWhy = 'no vertical stroke stands under the sink: either the page '
               + 'is drawing no caret there and this is a stale sink '
               + 'position, or the one-pixel bar fell between two columns and '
               + 'rendered too pale to be ink -- in which case it is not '
               + 'bridging anything either';
    } else {
      caret = { x: columns[0], y: y0, width: columns[columns.length - 1] - columns[0] + 1,
                height: y1 - y0 + 1, columns: columns.length, rowsTested: rows };
      caretWhy = null;
      // One row of margin above and below, for the antialiased ends the
      // solidity test just declined to count.  Nothing is lost by taking a
      // row too many where the bar is: the caret is painted LAST and
      // opaquely, so whatever glyph was under it is already gone from this
      // canvas.
      if (EXCLUDE_CARET) {
        for (let y = Math.max(0, y0 - 1); y <= Math.min(h - 1, y1 + 1); y += 1)
          for (const x of columns) dark[y * w + x] = 0;
        caretRemoved = true;
      }
    }
  }
}
const counts = [], firsts = [], lasts = [];
// Reported rather than silently dropped: on the shipped core this stays 0, so
// a non-zero value is the accessibility core's garbage being seen and named.
let offPageInk = 0;
for (let y = 0; y < h; y += 1) {
  let count = 0, first = -1, last = -1;
  for (let x = 0; x < w; x += 1) {
    if (!dark[y * w + x] || border[x]) continue;
    if (clipped && (x < inside || x > outside)) continue;
    if (pageClipped && (x < pageLeft || x > pageRight)) { offPageInk += 1; continue; }
    count += 1; if (first < 0) first = x; last = x;
  }
  counts.push(count); firsts.push(first); lasts.push(last);
}
return { width: w, height: h, counts, firsts, lasts, clipped,
         page: [inside, outside],
         pageOpaque: [pageLeft, pageRight], pageClipped, offPageInk,
         caret, caretWhy, caretRemoved,
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

# FINDING 066.  Where the keyboard is pointing, and where a real click sends it.
READ_FOCUS = """(() => {
const a = document.activeElement;
if (!a) return null;
return { id: a.id || null, tag: a.tagName,
         action: a.dataset ? (a.dataset.action || null) : null };
})()"""

BUTTON_BOX = """(() => {
const b = document.querySelector('ARG_SELECTOR');
if (!b) return null;
const r = b.getBoundingClientRect();
return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
})()"""

# Typing through the sink WITHOUT restoring focus first.
#
# Every other keyboard helper in this file opens with `sink.focus()`, and that
# line is exactly what hid finding 066 for as long as it existed: the harness
# handed back, every single time, the focus a user could only recover by
# clicking the canvas.  This one deliberately does not.
TYPE_WHEREVER_FOCUS_IS = """(() => {
const target = document.activeElement;
if (!target) return { dispatchedTo: null };
target.dispatchEvent(new InputEvent('beforeinput', {
  inputType: 'insertText', data: 'ARG_TEXT', bubbles: true, cancelable: true }));
return { dispatchedTo: target.id || target.tagName };
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

# One gesture, one script -- the shape the working DRAG probe uses.
#
# Split across separate evaluate() calls this never extended the selection at
# all, on any arm including the no-abort control, so the check could only ever
# abstain.  Rebuilt as a single script with the abort injected BETWEEN the two
# pointermoves, which is also where a real pointercancel or window blur would
# land: mid-gesture, after the drag has started to select.
ABORT_DRAG = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const at = (fx) => ({ x: box.left + box.width * fx,
                      y: box.top + box.height * ARG_Y });
const a = at(ARG_X1);
const b = at(ARG_X2);
const send = (type, point, buttons) => canvas.dispatchEvent(
  new PointerEvent(type, { clientX: point.x, clientY: point.y, button: 0,
                           buttons, pointerId: 1, bubbles: true }));
send('pointerdown', a, 1);
send('pointermove', { x: (a.x + b.x) / 2, y: a.y }, 1);
if ('ARG_KIND' === 'pointercancel') {
  canvas.dispatchEvent(new PointerEvent('pointercancel', {
    button: 0, buttons: 0, pointerId: 1, bubbles: true }));
} else if ('ARG_KIND' === 'blur') {
  window.dispatchEvent(new Event('blur'));
}
send('pointermove', b, 1);
send('pointerup', b, 0);
return true;
})()"""

RESIZE_DESK = """(() => {
const desk = document.querySelector('#desk');
const canvas = document.querySelector('#canvas');
if (!desk || !canvas) return { available: false };
const before = canvas.width;
const previous = desk.style.width;
desk.style.width = Math.max(320, Math.round(desk.clientWidth * 0.6)) + 'px';
window.__ppDeskWidth = previous;
window.dispatchEvent(new Event('resize'));
return { available: true, beforeCanvasWidth: before };
})()"""

RESTORE_DESK = """(() => {
const desk = document.querySelector('#desk');
if (!desk) return false;
desk.style.width = window.__ppDeskWidth ?? '';
window.dispatchEvent(new Event('resize'));
return true;
})()"""

SWITCH_FIXTURE = """(() => {
const picker = document.querySelector('#fixture');
if (!picker || picker.options.length < 2) return { available: false,
  options: picker ? picker.options.length : null };
const current = picker.value;
const other = [...picker.options].map((o) => o.value).find((v) => v !== current);
if (!other) return { available: false, options: picker.options.length };
picker.value = other;
picker.dispatchEvent(new Event('change', { bubbles: true }));
return { available: true, from: current, to: other,
         options: picker.options.length };
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
  // The DECISION the product rendered, not the sentence it chose to render it
  // with.  Adjudicated 2026-08-19: an oracle that compares wording goes green
  // the day somebody rephrases, and the shell's whole point is that hosts may
  // differ in wording and may not differ in whether they claim work was saved.
  rescue: notice ? (notice.dataset.rescue || null) : null,
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
    # FINDING 067.  The binding lives in the page's keydown handler because a
    # <textarea> reports Enter and Shift+Enter identically at the adapter's
    # commit boundary (measured), and the adapter is frozen anyway.  Disabling
    # the branch hands both keys back to the adapter, which is what 067 was.
    "enter-key-not-bound": {
        "check": "the-enter-key-reaches-the-document",
        "path": "e2-editor-app.js",
        "find": '  if (event.key === "Enter" && !event.isComposing) {',
        "replace": '  if (false && !event.isComposing) {',
        "reintroduces": "finding 067",
        "alsoRed": [],
        "alsoNotEstablished": [],
    },
    # FINDING 066, and the reason it needs a mutation at all: the check that
    # owns it is the only one in this file that uses a REAL click, so nothing
    # else would notice if it stopped being able to fail.  Reverting the two
    # lines puts the keyboard back on the button.
    "focus": {
        "check": "the-toolbar-gives-the-keyboard-back",
        "path": "e2-editor-app.js",
        "find": "  event.preventDefault();\n"
                "  if (session) el.sink.focus({ preventScroll: true });",
        "replace": "  return;",
        "reintroduces": "finding 066",
        "alsoRed": [],
        "alsoNotEstablished": [],
    },
    # The defect as it actually was until 2026-08-17: the session had
    # pasteEvent() and no listener called it, so a paste fell through to the
    # browser's default on a canvas -- silently nothing.  Renaming the event is
    # the closest thing to "the handler was never written".
    # Cut, restored to what shipped until 2026-08-17: no handler at all, so the
    # browser's default cut runs against a canvas with no DOM selection and
    # silently does nothing.
    "cut": {
        "check": "cut-removes-the-selected-text",
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
    # The edit BUTTONS, 2026-08-21.  Swapping one arrow is enough to move the
    # marker to the wrong place, and it keeps every action dispatching -- a
    # mutation that skipped a dispatch would also stop the latency the other
    # waits key on, and would then be measuring the harness.
    "edit-arrows-swapped": {
        "check": "the-edit-buttons-do-what-they-say",
        "path": "e2-editor-app.js",
        "find": "  await run(label, () => session.action(action, options));",
        "replace": "  await run(label, () => session.action("
                   "action === \"move-character-left\" ? "
                   "\"move-character-right\" : action, options));",
        "reintroduces": "arrow buttons that move the caret the wrong way",
        "alsoRed": [],
    },
    # The forwarding this tree nearly WAIVED as undrivable.  One line, and
    # removing it is exactly the defect the row exists to exclude.
    "open-button-forwards-nowhere": {
        "check": "the-open-button-opens-the-file-chooser",
        "path": "e2-editor-app.js",
        "find": 'el.openFile.addEventListener("click", () => el.file.click());',
        "replace": 'el.openFile.addEventListener("click", () => {});',
        "reintroduces": "an open button that does nothing",
        "alsoRed": [],
    },
    # The three listeners driven for the first time on 2026-08-21.
    "gesture-abort-not-wired": {
        "check": "an-aborted-gesture-stops-selecting",
        "path": "e2-editor-app.js",
        "find": 'el.canvas.addEventListener("pointercancel", () => endDrag(null));',
        "replace": 'el.canvas.addEventListener("pointercancel-never", () => endDrag(null));',
        "reintroduces": "a drag the browser cancelled that keeps selecting",
        "alsoRed": [],
        # DECLARED UNDETECTABLE, and the declaration is the honest half of a
        # check that does not yet work.  `an-aborted-gesture-stops-selecting`
        # carries a positive control -- a drag with NO abort, which must extend
        # the selection -- and on 2026-08-21 that control failed on all four
        # gesture shapes tried, so the check abstains instead of passing.  While
        # it abstains it cannot go red for this mutation either.  If it ever IS
        # detected, the run says the declaration is stale, which is precisely
        # the alarm wanted: it would mean the control finally works.
        "expectedToBeDetected": False,
        "why": "the check's positive control cannot start an extending drag "
               "through this harness, so the check reports NOT_ESTABLISHED and "
               "nothing about aborting one is measured yet. The observable, not "
               "the gesture, is what is missing: copy and cut DO produce a "
               "range at their own named line, so the next step is a direct "
               "selection observable (the copy path reports codePoints) rather "
               "than reading button.disabled.",
    },
    "resize-does-not-repaint": {
        "check": "the-canvas-follows-a-window-that-changed-size",
        "path": "e2-editor-app.js",
        "find": "globalThis.addEventListener(\"resize\", () => {\n  layoutCanvas();\n  void renderDocument();\n});",
        "replace": "globalThis.addEventListener(\"resize\", () => {\n  layoutCanvas();\n});",
        "reintroduces": "a window resize that resizes the canvas and leaves it blank",
        "alsoRed": [],
    },
    "sample-picker-does-nothing": {
        "check": "the-sample-picker-opens-a-second-document",
        "path": "e2-editor-app.js",
        "find": 'el.fixture.addEventListener("change", () => {',
        "replace": 'el.fixture.addEventListener("change-never", () => {',
        "reintroduces": "a sample picker that picks nothing",
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
                    "cut-removes-the-selected-text"],
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
        "reintroduces": "a checkpoint save that misses its deadline",
        "alsoRed": [],
        # Declared NOT detectable, and the declaration is the point: this
        # injects a CONDITION rather than a defect, and since finding 061 was
        # fixed the product handles that condition correctly -- it says the
        # rescue was attempted and failed instead of saying there was never one.
        # So the round asserts the product is RIGHT here. If this ever starts
        # being detected, the run says the declaration is out of date, which is
        # exactly the alarm wanted: it would mean the third branch regressed.
        "expectedToBeDetected": False,
        "why": "the third branch is a state the product now renders correctly. "
               "Before 2026-08-19 this mutation WAS detected, and that was "
               "finding 061 -- the pill read 寫入失敗 while the notice told the "
               "user there had never been a checkpoint.",
    },
    # What must still be able to fail: the product declaring its decision at
    # all.  With the stamp gone the notice and the status pill can disagree
    # again, and the check's `surfacesAgree` clause is what notices.
    "notice-does-not-declare-its-decision": {
        "check": "recovery-returns-what-the-product-promised",
        "path": "e2-editor-app.js",
        "find": '  el.notice.dataset.rescue = notice.canRescue ? "checkpoint"\n'
                '    : notice.checkpointFailed ? "failed" : "none";',
        "replace": '  el.notice.dataset.rescue = "none";',
        "reintroduces": "a notice whose account of your work does not have to "
                        "match the product's own status",
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
    # Finding 062's fix, taken away: one tile for the whole document again.
    # Above 32,767 px the engine returns a correctly sized buffer it never drew
    # into and reports success, so this restores exactly what shipped until
    # 2026-08-19 -- a blank page, `ready`, and no message.
    "one-tile-for-the-whole-document": {
        "check": "a-long-document-is-drawn-or-the-product-says-it-is-not",
        "path": "e2-editor-app.js",
        "find": "const MAX_TILE_HEIGHT = 32767;",
        "replace": "const MAX_TILE_HEIGHT = 1000000;",
        "reintroduces": "a long document drawn as a blank page, in silence",
        # The tile check inside renderDocument turns the silence into a message,
        # so with the strips gone the product now SAYS the repaint failed
        # instead of showing nothing -- which is why the arms are not silent and
        # the check goes red on `drawn` rather than on `silentArms`.
        "alsoRed": [],
    },
    # Finding 062's second half, the page's side of it.  The engine now reports
    # that the document changed size, and this is the page acting on it; with
    # the branch off, the canvas keeps the height the document had when it was
    # opened and the new page is never drawn -- which is exactly what shipped
    # until the 2026-08-19 relink.
    "ignore-a-document-that-grew": {
        "check": "the-canvas-follows-a-document-that-grew",
        "path": "e2-editor-app.js",
        "find": "      if (tile.documentSizeChanged) documentResized = true;",
        "replace": "      if (false) documentResized = true;",
        "reintroduces": "an editor whose page count is frozen at the moment you "
                        "opened the file",
        "alsoRed": [],
    },
    # The keyboard row's whole point: the toolbar is not the only way in.  With
    # the format branch gone the buttons still work and the shortcuts do
    # nothing, which is exactly the state the row was in until 2026-08-19.
    "keyboard-formats-not-bound": {
        "check": "the-keyboard-reaches-the-document",
        "path": "e2-editor-app.js",
        "find": '    const formatAction = { b: "set-bold", i: "set-italic",\n'
                '                           u: "set-underline" }[event.key.toLowerCase()];',
        "replace": "    const formatAction = undefined;",
        "reintroduces": "an editor whose formats are toolbar-only",
        "alsoRed": [],
    },
    # REPLACES `cut-swallows-its-failure`, WHICH HAD BEEN DEAD SINCE THE LINK.
    #
    # That mutation's pattern still named `session.action("delete-backward")`
    # inside the cut handler, and the v4 link work replaced that line with the
    # `offers("delete-selection")` ternary.  Its pattern matched dist ZERO
    # times, so `apply_mutation` would have exited loudly -- but only if
    # somebody ran it, and nobody did between the link and 2026-08-22.  A
    # mutation that cannot be applied is a check with no evidence it can fail,
    # which is the same silence the mutation itself was written to break.
    #
    # What this one reintroduces is the state the product actually shipped in
    # until today: the fallback arm, where the delete half is `delete-backward`,
    # declared caret-only, and refused on every range.  Cut becomes copy again.
    # It is a better control than the old one for two reasons: it applies, and
    # it drives the REFUSAL path, which the widened manifest has removed from
    # the product's own route (queue-cut-refusal-lost-its-inducer).
    # The four line-movement keys, back to the state the product shipped in
    # from 2026-08-17 until the ABI 4 link: not in the map at all, so
    # `KEY_ACTIONS[event.key]` is undefined, the handler returns before
    # preventDefault, and the key is left to the browser -- which on a canvas
    # does nothing at all, silently.
    #
    # This mutation exists because the check it guards did not, for four days
    # after the actions shipped. The acceptance row read `blocked` through the
    # link and then read as satisfied on the strength of an arm that asserts
    # AGREEMENT with the running profile -- green on v3 because the keys were
    # correctly absent, and green on v4 for the opposite reason. Nothing drove
    # the keys themselves.
    # Finding 073, restored: the sink stays one transparent pixel while an IME
    # composes, so the user cannot see the bopomofo they are part way through.
    # Renaming the event is the closest thing to "the handler was never
    # written", which is literally what shipped until 2026-08-22 -- there were
    # no composition handlers in this file at all.
    "composition-never-shown": {
        "check": "the-composition-you-are-typing-is-visible",
        "path": "e2-editor-app.js",
        "find": 'el.sink.addEventListener("compositionstart", () => showComposition(el.sink.value));\n'
                'el.sink.addEventListener("compositionupdate", (event) => showComposition(event.data));',
        "replace": 'el.sink.addEventListener("compositionstart-never-wired", () => showComposition(el.sink.value));\n'
                   'el.sink.addEventListener("compositionupdate-never-wired", (event) => showComposition(event.data));',
        "reintroduces": "an editor where typing Chinese shows you nothing "
                        "until the character commits",
        "alsoRed": [],
    },
    "line-movement-keys-unbound": {
        "check": "the-vertical-arrows-move-the-caret",
        "path": "e2-editor-app.js",
        "find": '  ArrowUp: "move-line-up",\n'
                '  ArrowDown: "move-line-down",\n'
                '  Home: "move-line-home",\n'
                '  End: "move-line-end",\n',
        "replace": "",
        "reintroduces": "an editor whose Up, Down, Home and End keys do "
                        "nothing and say nothing",
        "alsoRed": [],
    },
    # FINDING 063 ITSELF, put back -- the swallow, not the fallback.
    #
    # 063's shape was that the delete's failure never reached the user: it sat
    # outside `run()`, in a `.then` whose `.catch` discarded it, so with a
    # working clipboard the copy succeeded, the delete was refused, the session
    # went to recoverable-error, and the only thing on screen was a notice
    # telling the user to restart -- no word about what had failed. This
    # restores the discard at the point where it still does that: inside the
    # operation, where `run()` can no longer see the rejection.
    #
    # ONLY MEANINGFUL WITH --refusal-diagnostic, and that is declared rather
    # than left to be discovered. On the shipped manifest the delete succeeds,
    # nothing throws, and this mutation changes no observable at all -- it
    # would report "the product survived it", which is the reading a dead
    # mutation gives and the reason `cut-swallows-its-failure` had to be
    # replaced.
    # Roadmap 3.4. The projection is wired by ONE call in `updateState`;
    # removing it leaves the region in the page and empty, which is precisely
    # the failure mode the check exists for -- a screen reader reads an empty
    # document region as a blank document.
    "projection-not-wired": {
        "check": "the-document-region-says-why-it-is-empty",
        "path": "e2-editor-app.js",
        "find": "  projectFocusedParagraph(snapshot);\n",
        "replace": "",
        "reintroduces": "a document region that is silently empty instead of "
                        "saying why it has nothing",
        "alsoRed": [],
    },
    "cut-swallows-the-refusal": {
        "check": "a-refused-action-is-reported-and-changes-nothing",
        "path": "e2-editor-app.js",
        "requiresFlag": "--refusal-diagnostic",
        "find": "    await session.action(session.offers(\"delete-selection\")\n"
                "                         ? \"delete-selection\" : \"delete-backward\", {});",
        "replace": "    try {\n"
                   "      await session.action(session.offers(\"delete-selection\")\n"
                   "                           ? \"delete-selection\" : \"delete-backward\", {});\n"
                   "    } catch (swallowed) { void swallowed; }",
        "reintroduces": "a refused cut that tells the user nothing, which is "
                        "finding 063 as it shipped",
        "alsoRed": [],
    },
    "cut-falls-back-to-the-caret-only-delete": {
        "check": "cut-removes-the-selected-text",
        "path": "e2-editor-app.js",
        "find": "    await session.action(session.offers(\"delete-selection\")\n"
                "                         ? \"delete-selection\" : \"delete-backward\", {});",
        "replace": "    await session.action(session.offers(\"delete-selection\")\n"
                   "                         ? \"delete-backward\" : \"delete-backward\", {});",
        "reintroduces": "a cut that copies and then fails to delete, which is "
                        "what shipped from 2026-08-17 until the manifest was "
                        "widened",
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
    "redo": {
        "check": "product-redo-button-restores-what-undo-removed",
        "path": "e2-editor-app.js",
        "find": '    : action === "redo" ? () => run("重做", () => session.redo())',
        "replace": '    : action === "redo" ? () => run("重做", () => Promise.resolve())',
        "reintroduces": "finding 049's shape on the redo path: the button runs, "
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
SHELL_BUNDLE_V2 = PROJECT / "e2" / "editor-shell-v2-bundle-v27.json"


PRODUCT_PROFILE_IN_PAGE = re.compile(
    r"\./profiles/([A-Za-z0-9._-]+)/sdk-worker\.js")


def product_profile(root: Path) -> str:
    """Which profile the SERVED PAGE loads, read from the page itself.

    Introduced 2026-08-23 for the v5 cutover, and the reason is the failure it
    prevents rather than tidiness.  Three places here rewrote
    `profiles/e2-editor-v4/sdk-manifest.json` by name to build their diagnostic
    mirrors.  Moving the product to v5 would not have broken them -- it would
    have left them mirroring a manifest **no longer loaded**, so
    `--range-delete-diagnostic` and `--cut-via-replace-selection` would report
    a widened or narrowed gesture while the page ran the shipped one. A silent
    mis-target is worse than a crash, and it is exactly the shape of finding
    044 one layer out.

    Raises rather than guessing: a page whose profile cannot be read is a page
    this runner does not know how to mirror, and picking a default there would
    reintroduce the same silence.
    """
    page = root / "e2-editor-app.js"
    match = PRODUCT_PROFILE_IN_PAGE.search(page.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(
            f"cannot tell which profile {page} loads -- the mirror would have "
            f"to guess, and a diagnostic aimed at the wrong manifest reports "
            f"about an artifact the page is not running")
    return match.group(1)


def offered_actions(root: Path, names) -> dict:
    """Which of these actions the SERVED manifest offers.

    Read from the profile the SERVED PAGE points at, rather than from a profile
    name written here.  The diagnostic runs serve a mirror and the product's
    profile has been renamed once per link, so a hardcoded path answers about
    whatever is in `dist/` while the page may be running something else --
    which is exactly the trap `probe_064_format_reaches_typing.py`'s READ_OFFERS
    is sitting in today (it fetches `profiles/e2-editor-v4/` unconditionally and
    would report v4's offers on a page running v3).

    An empty dict means "could not tell", and the caller reports
    NOT_ESTABLISHED rather than reading it as "nothing is offered".
    """
    page = root / "e2-editor-app.js"
    if not page.is_file():
        return {}
    match = re.search(r"\./profiles/([A-Za-z0-9._-]+)/sdk-worker\.js",
                      page.read_text(encoding="utf-8"))
    if not match:
        return {}
    manifest = root / "profiles" / match.group(1) / "sdk-manifest.json"
    if not manifest.is_file():
        return {}
    contract = json.loads(manifest.read_text(encoding="utf-8")).get(
        "editorContract") or {}
    actions = contract.get("actions") or {}
    out: dict = {"profile": match.group(1),
                 "abiVersion": contract.get("abiVersion")}
    for name in names:
        if isinstance(actions, list):
            out[name] = name in actions
        else:
            spec = actions.get(name)
            # An empty `gestures` list is WITHHELD, not unrestricted -- the
            # same rule the worker's mask loop and the client's offers() use.
            out[name] = bool(spec) and (
                not isinstance(spec.get("gestures"), list)
                or len(spec["gestures"]) > 0)
    return out


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


# Where the line's own ink starts and ends, from ONE read.
#
# Finding 060 anchored the sampled BAND to the line's ink instead of a viewport
# fraction.  The click position stayed a hardcoded viewport fraction, and on
# 2026-08-21 that turned out to be the same defect one layer along: at x=0.06
# the click lands in the left MARGIN, the engine snaps the caret to the line's
# first character, and the caret is then drawn on top of ink that is already
# dark -- so the column shows no delta and the caret reads as "never drawn".
# Measured on Firefox: x=0.06 gives strokeLost 0 three runs running, x=0.20
# gives 19.  Whether 0.06 separates depends on the canvas width, which depends
# on the browser window, which is exactly what 060 was about.
LINE_INK = """(() => {
const canvas = document.querySelector('#canvas');
const y = Math.floor(canvas.height * ARG_Y) - 18;
const h = 46;
if (y < 0 || y + h > canvas.height) return { available: false };
const data = canvas.getContext('2d').getImageData(0, y, canvas.width, h).data;
let left = null, right = null;
const columns = new Array(canvas.width).fill(0);
for (let x = 0; x < canvas.width; x += 1) {
  let dark = 0;
  for (let row = 0; row < h; row += 1) {
    const i = (row * canvas.width + x) * 4;
    if (data[i] < 100 && data[i+1] < 100 && data[i+2] < 100) dark += 1;
  }
  // A glyph never fills every row of a band that includes the line spacing; a
  // border does.  Same discrimination caret_from_columns makes.
  if (dark > 0 && dark < h) { if (left === null) left = x; right = x; }
  columns[x] = dark;
}
return { available: left !== null && right !== null && right > left,
         inkLeft: left, inkRight: right, width: canvas.width,
         columns };
})()"""


def caret_click_fractions(ink: dict) -> dict:
    """Two click positions expressed as fractions of the CANVAS, from the LINE.

    POINT_AT multiplies by the bounding rect's width and CARET_COLUMNS indexes
    the backing store, so the two only agree on a dimensionless fraction --
    which is what this returns.

    `near` is placed just inside the text rather than at its very first
    character: the caret at position 0 coincides with the first glyph's left
    edge and cannot be told apart from it by an ink delta.
    """
    if not ink.get("available"):
        return {"derived": False, "near": "0.06", "past": "0.92",
                "why": "no line ink found; falling back to viewport fractions, "
                       "which is the geometry dependence this exists to remove"}
    left, right = ink["inkLeft"], ink["inkRight"]
    width, span = ink["width"], ink["inkRight"] - ink["inkLeft"]
    # Just inside the text, not in the margin.  That is the whole fix: at a
    # click in the margin the engine snaps the caret to character position 0,
    # where it coincides with the first glyph's left edge and an ink delta
    # cannot see it at all (Firefox, strokeLost 0 on three consecutive runs).
    #
    # AIMING AT A GAP WAS TRIED AND MADE IT WORSE -- recorded because the
    # reason generalises.  Picking the sparsest column in the first quarter
    # took Chrome from strokeLost 2 to 1.  The harness chooses where it
    # CLICKS; the engine chooses where the caret LANDS, and it lands on a
    # character boundary, which is adjacent to glyph ink by definition.  A gap
    # in the ink is not a gap the caret can occupy.
    near = left + 0.12 * span
    past = min(right + 0.06 * span, width - 2)
    return {"derived": True,
            "near": f"{near / width:.6f}", "past": f"{past / width:.6f}",
            "inkLeft": left, "inkRight": right, "canvasWidth": width}


# The product's own "turn every inline format off" button.  It is a plain
# button rather than a `data-action` one, so PRESS cannot reach it.
CLEAR_FORMAT = """(() => {
const button = document.querySelector('#clear-format');
if (!button) return false;
button.click();
return true;
})()"""

CLEAR_LATENCY = """(() => {
document.querySelector('#s-latency').textContent = '';
return true;
})()"""


def place_caret_and_settle(session, point_at: str, x: str, y: str,
                           timeout: float = 60) -> dict:
    """Click, and wait for THIS placement rather than for a stale one.

    `run()` in the page writes "<label> NNN ms" into #s-latency only after the
    operation resolves and renderDocument() completes -- but it never clears the
    field first (web/e2-editor-app.js:377-382).  Every earlier step that places
    a caret therefore leaves "定位游標" sitting there, so a predicate that merely
    asks whether the text CONTAINS it is already true before the click, returns
    at once, and leaves the fixed sleep below to cover the whole round trip on
    its own.

    Clearing the field first makes the wait mean what it says.  Same technique
    the runner already declares for #toast, and no page change -- so it mints no
    shell generation.
    """
    evaluate(session, CLEAR_LATENCY)
    evaluate(session, point_at.replace("ARG_X", x).replace("ARG_Y", y))
    return wait_for(session,
                    lambda s: "定位游標" in (s.get("latency") or ""), timeout)


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
    # A COLUMN INDEX THAT CAME FROM A TIE-BREAK IS NOT A POSITION.
    #
    # `gained`/`lost` are argmax/argmin over `delta`.  When the caret was not
    # located in one of the two reads that read contributes no non-zero delta,
    # the extremum is 0, and argmax/argmin return **index 0** -- the leftmost
    # column of the canvas -- purely by tie-break.  Measured on Firefox
    # 2026-08-21, mutation none: strokeGained 24, strokeLost 0, and
    # fractionNearStart was computed from that index anyway as
    # (0 - 101) / 442 = -0.229.  `the-caret-lands-where-the-click-was` asks for
    # near < 0.25, so it PASSED -- because the caret had not been found.
    #
    # The two checks differ in what they are entitled to here, and that is why
    # this is not simply `available: False`:
    #   - `the-caret-is-drawn-where-it-was-placed` has the STROKES as its
    #     subject.  A zero stroke is its answer, not a gap in its data, and it
    #     must go on FAILING -- that is finding 058, a product that draws no
    #     caret at all.
    #   - `the-caret-lands-where-the-click-was` has the POSITIONS as its
    #     subject, and a position it cannot support must be withheld.
    # So the strokes are always reported and a fraction is reported only when
    # the read it comes from actually found the caret.
    stroke_gained, stroke_lost = delta[gained], -delta[lost]
    return {
        "available": True,
        "inkLeft": left, "inkRight": right, "inkSpan": span,
        "caretAfterClickNearStart": lost if stroke_lost > 0 else None,
        "caretAfterClickPastEnd": gained if stroke_gained > 0 else None,
        "strokeGained": stroke_gained, "strokeLost": stroke_lost,
        # Position along the line, 0 at the first inked column and 1 at the last.
        # None means "this read did not find the caret", never "column zero".
        "fractionNearStart":
            (lost - left) / span if span and stroke_lost > 0 else None,
        "fractionPastEnd":
            (gained - left) / span if span and stroke_gained > 0 else None,
    }


ODF_NS = {"office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
          "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
          "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
          "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"}

# Which ODF text property carries each of the four inline formats, and what
# counts as "on".  Underline and strike are not booleans: ODF spells them as a
# LINE STYLE whose "off" value is the literal string "none", so `present` and
# `on` are different questions and only the second one is the format.
INLINE_FORMAT_PROPERTIES = {
    "bold": ("fo", "font-weight", lambda v: v not in (None, "normal")),
    "italic": ("fo", "font-style", lambda v: v not in (None, "normal")),
    "underline": ("style", "text-underline-style",
                  lambda v: v not in (None, "none")),
    "strikethrough": ("style", "text-line-through-style",
                      lambda v: v not in (None, "none")),
}


def inline_styles_of(report: dict, marker: str) -> dict:
    """Which inline formats the text carrying `marker` actually has.

    THE ONLY ORACLE THAT WORKS AT A COLLAPSED CARET, and the matrix settled
    that on 2026-08-15 -- before D1 ran -- by amending its own cells:

        at a collapsed caret an inline format leaves <office:body>
        byte-identical and shows up only in text committed afterwards.

    So "did the format take" cannot be asked of the document that was already
    there.  Comparing the saved ODT against the paragraph's own text, the way
    the paragraph ACTIONS are checked, would pass on a no-op -- which is what
    the first draft of this plan proposed.  It has to be asked of a marker
    typed after the format was applied, which is what this reads.

    A marker with no <text:span> around it is not a failure to find it: it is
    the answer "this text carries no inline formatting at all", which is
    exactly what a working `clear-format` must produce.
    """
    content = report.get("content") or ""
    if not content:
        return {"found": False, "why": "no content.xml"}
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        return {"found": False, "why": f"content.xml does not parse: {error}"}

    name_of = f"{{{ODF_NS['style']}}}name"
    parent_of = f"{{{ODF_NS['style']}}}parent-style-name"
    styles: dict[str, dict] = {}
    for style in root.iter(f"{{{ODF_NS['style']}}}style"):
        properties = style.find("style:text-properties", ODF_NS)
        styles[style.get(name_of) or ""] = {
            "parent": style.get(parent_of),
            "properties": dict(properties.attrib) if properties is not None else {},
        }

    def resolved(style_name: str | None) -> dict:
        """Walk the parent chain, nearest definition winning."""
        chain, seen = [], set()
        while style_name and style_name in styles and style_name not in seen:
            seen.add(style_name)
            chain.append(styles[style_name]["properties"])
            style_name = styles[style_name]["parent"]
        merged: dict = {}
        for properties in reversed(chain):
            merged.update(properties)
        return merged

    span_style_of = f"{{{ODF_NS['text']}}}style-name"
    carrier, style_name = None, None
    for span in root.iter(f"{{{ODF_NS['text']}}}span"):
        if marker in "".join(span.itertext()):
            carrier, style_name = "span", span.get(span_style_of)
            break
    if carrier is None:
        for tag in ("p", "h"):
            for paragraph in root.iter(f"{{{ODF_NS['text']}}}{tag}"):
                if marker in "".join(paragraph.itertext()):
                    carrier = "paragraph"
                    style_name = paragraph.get(span_style_of)
                    break
            if carrier:
                break
    if carrier is None:
        return {"found": False, "why": f"{marker!r} is not in the saved document"}

    # THE PARAGRAPH'S STYLE COUNTS, and until 2026-08-22 it did not.
    #
    # This used to stop at `carrier = "paragraph"` and resolve nothing, on the
    # stated grounds that "this asks about INLINE formatting, and text that is
    # not in a span has none of it".  That premise is FALSE for ODF: when a
    # paragraph is UNIFORMLY formatted, LibreOffice's export writes the
    # character properties into the paragraph's own automatic style --
    #
    #   <style:style style:name="P1" style:family="paragraph"
    #                style:parent-style-name="Standard">
    #     <style:text-properties fo:font-weight="bold" .../></style:style>
    #   <text:p text:style-name="P1">MANUALBOLD</text:p>
    #
    # -- and emits no span at all.  So "not in a span" does not mean "not
    # formatted"; it very often means "formatted, and uniformly".
    #
    # This is a FALSE NEGATIVE precisely where these checks live: every arm
    # presses insert-paragraph-break and then types its marker, so the marker
    # ends up ALONE in its paragraph, which is the uniform case.  Found on
    # 2026-08-22 by an operator who could see bold on the canvas while this
    # function reported `bold: false` on the saved document -- the human's eyes
    # against the oracle, and the oracle was wrong.
    #
    # `fromParagraphStyle` is reported rather than hidden: a caller that needs
    # to tell "the user pressed B" from "this text is bold because it is a
    # heading" can look, and the parent chain is walked either way so a named
    # parent's properties are included.
    properties = resolved(style_name)
    out = {"found": True, "carrier": carrier, "styleName": style_name,
           "fromParagraphStyle": carrier == "paragraph",
           "properties": properties}
    for format_name, (prefix, attribute, is_on) in INLINE_FORMAT_PROPERTIES.items():
        out[format_name] = bool(is_on(properties.get(
            f"{{{ODF_NS[prefix]}}}{attribute}")))
    return out




# A text line split by a thin row inside its own glyphs is still one line.
#
# Two populations, both measured rather than assumed: the gaps BETWEEN lines in
# these fixtures are 10-16 rows (list-contexts 12-16, endnote-frame 10), and a
# split inside one line is a few rows.  8 sits between them with room on each
# side.
#
# It was 5, and 5 was too tight: on the relinked artifact of 2026-08-19 a 16pt
# heading split into two runs and four arms reported NOT_ESTABLISHED.  The first
# repair was cleverer -- half the MEDIAN gap on the page -- and it was WORSE: on
# a page with a large empty area (the endnote fixture, whose body lines are
# followed by an 873-row gap) the median is a page gap, the threshold becomes
# 133, and three separate lines merge into one band.  A fixed number that both
# populations are measured against beats a rule that is right on the page it was
# written for.
BAND_MERGE_GAP = 8

# Finding 072's remedy, and the switch that turns it off.  A run with
# --no-caret-exclusion reproduces the merged band directly, so "the caret is
# what joined those two lines" stays a claim someone can re-measure in one
# command instead of a claim they have to take from this comment.
EXCLUDE_CARET = True


def text_bands(scan: dict, floor: int = 0) -> list[dict]:
    """The canvas's lines of text, as row bands.

    The floor is 0, not 2, and that is the point: the scan excludes everything
    outside the opaque page (finding 075; the page-border test it used to rely
    on finds one column on this fixture and never fires), so a row between two
    lines carries EXACTLY no ink,
    while a thin row inside a tall glyph carries one or two pixels.  A floor of
    2 threw those away and split a 16pt heading into two bands -- intermittently,
    which is worse than always.  Ink inside the printable area is ink.

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
    # Recorded so that a future mismatch is diagnosable from the report rather
    # than from another round of probing: if bands and lines ever disagree
    # again, these are the numbers that say whether the threshold is wrong.
    observed_gaps = sorted(runs[index + 1]["top"] - runs[index]["bottom"]
                           for index in range(len(runs) - 1))
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
        band["gapsOnThisPage"] = observed_gaps[:12]
        if 0.15 <= band["density"] < 0.9:
            out.append(band)
    return out


# What the page clip actually threw away, across every scan in a run.
#
# The comment in `INK_ROWS` says the count is "reported rather than silently
# dropped", and when this was first written that was FALSE: the scan returned
# it and nothing carried it into the report, so the sentence described an
# intention. A diagnostic nobody can read is not a diagnostic -- the same rule
# that killed two findings on 2026-08-21.
OFF_PAGE_INK = {"worst": 0, "scans": 0, "scansWithInk": 0, "pageRange": None,
                "pageClipped": None}


def note_off_page_ink(scan: dict) -> None:
    dropped = scan.get("offPageInk")
    if dropped is None:
        return
    OFF_PAGE_INK["scans"] += 1
    if dropped:
        OFF_PAGE_INK["scansWithInk"] += 1
    # The range from the WORST scan, not from the last one.  The first version
    # overwrote it every scan and reported `[0, 724]` -- the whole canvas -- next
    # to a non-zero drop count, which cannot both be true and reads as a
    # contradiction in the report rather than as a diagnostic.
    if int(dropped) >= OFF_PAGE_INK["worst"]:
        OFF_PAGE_INK["worst"] = int(dropped)
        OFF_PAGE_INK["pageRange"] = scan.get("pageOpaque")
        OFF_PAGE_INK["pageClipped"] = scan.get("pageClipped")


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
        scan = evaluate(session, INK_ROWS.replace(
            "ARG_EXCLUDE_CARET", "true" if EXCLUDE_CARET else "false")) or {
                "counts": [], "firsts": [], "lasts": [], "height": 1,
                "width": 1, "caret": None,
                "caretWhy": "the scan itself returned nothing"}
        note_off_page_ink(scan)
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


SINK_POSITION = """(() => {
const sink = document.querySelector('#sink');
if (!sink) return null;
// `offsetLeft`/`offsetTop` rather than the inline style, so this reads what the
// element IS at rather than what was last assigned to it -- a style that failed
// to apply would otherwise read back as if it had.
return { left: sink.offsetLeft, top: sink.offsetTop,
         height: sink.offsetHeight };
})()"""


# Whether the page TOOK a key, which is a different question from whether the
# caret moved.  A key the page never bound is left to the browser and does
# nothing; a key it bound and could not act on also does nothing.  Measured on
# v3, where ArrowUp came back `defaultPrevented: false` with no error shown --
# so without this the two readings are the same.
INSTALL_KEY_TAKEN = """(() => {
if (globalThis.__keytaken) { globalThis.__keytaken.keys = []; return true; }
globalThis.__keytaken = { keys: [] };
// On `document`, and in the BUBBLE phase: the page's handler is on #sink, so a
// capture-phase listener here would run BEFORE it and read defaultPrevented as
// false for every key including the ones that work.
document.addEventListener("keydown", (event) => {
  globalThis.__keytaken.keys.push({ key: event.key,
                                    defaultPrevented: event.defaultPrevented });
});
return true;
})()"""

# FINDING 073.  What the sink LOOKS like, not only where it is.
#
# `opacity` and `width` come from getComputedStyle rather than from the inline
# style, so a rule that failed to apply reads as not applied instead of as
# whatever was last assigned -- the same reason SINK_POSITION uses offsetLeft.
SINK_APPEARANCE = """(() => {
const sink = document.querySelector('#sink');
if (!sink) return null;
const style = getComputedStyle(sink);
return { opacity: Number(style.opacity), width: sink.offsetWidth,
         left: sink.offsetLeft, top: sink.offsetTop,
         composing: sink.dataset.composing === "1",
         value: sink.value, focused: document.activeElement === sink };
})()"""


READ_KEY_TAKEN = """(() => {
const d = globalThis.__keytaken;
return d ? d.keys : null;
})()"""


REDO_BUTTON = """(() => {
const button = document.querySelector('#toolbar button[data-action="redo"]');
if (!button) return null;
// `hidden` is the product's own answer to "does this profile carry redo".  It
// is read rather than assumed because `.click()` fires on a hidden button too,
// so a profile without redo would otherwise be tested by pressing a control the
// product is not offering -- the same mistake the notice-action check made.
return { present: true, hidden: button.hidden === true };
})()"""


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
    # A DECLARED diagnostic, not a product configuration.
    #
    # queue-cut-cannot-remove-text: the manifest declares the ten v1 actions
    # caret-only because range dispatch "was characterised for the paragraph
    # actions, not for delete or insert" -- an honest declaration of a
    # measurement nobody made.  This flag supplies the measurement WITHOUT
    # widening the shipped manifest: the widened one is served from a symlink
    # mirror, dist/ is never written, and probe.wasm stays byte-identical.
    #
    # Both range bits together, never one: probe_engine.cpp:4364-4374 requires
    # BOTH for a selection the build has not classified, so one bit alone
    # refuses every range and two arms split by bit would measure the same
    # refusal twice.
    # The SECOND cut diagnostic, and it asks whether cut needs the engine AT ALL.
    #
    # The empty-text refusal is a JavaScript guard (document-sdk.js:468-472);
    # the engine's handleReplaceSelection (probe_engine.cpp:3199-3216) is a
    # plain LOK paste with no empty-text gate.  And replaceSelection does not go
    # near the selection barrier, whose collapsed-caret requirement is BY DESIGN
    # (:3143-3151 refuses a pre-existing selection, then posts shift+Left/Right
    # to make its own).  So if LOK's paste with zero-length text deletes the
    # selection, cut closes with no engine change and no link.
    #
    # Two shipped files are mirrored; dist/ is never written and probe.wasm
    # stays byte-identical.  Prediction written first:
    # findings/evidence/queue-cut-cannot-remove-text/PREDICTION-replace-selection.md
    parser.add_argument("--cut-via-replace-selection", action="store_true",
                        help="mirror the SDK's empty-text guard away and make "
                             "cut's delete half call replaceSelection(\"\"); "
                             "stamps the report diagnostic")
    parser.add_argument("--range-delete-diagnostic", action="store_true",
                        help="grant the action named by --range-delete-action "
                             "both range gestures in a MIRRORED manifest, to "
                             "measure whether the engine removes a range at "
                             "all; stamps the report diagnostic")
    # THE INVERSE OF THE ABOVE, AND IT IS WHY THIS FLAG EXISTS.
    #
    # Finding 063 is that a REFUSED cut used to send the session into
    # recoverable-error and tell the user to discard unsaved work, over an
    # action that had dispatched nothing.  `ctrl-x-is-handled-by-the-product`
    # verified the fix on every run -- until 2026-08-22 widened
    # `delete-selection`, which removed the refusal from the product's own path
    # and left the coverage to a mutation.  A mutation asserts that a check goes
    # RED; it does not assert that the refusal was reported, the document left
    # alone and the session kept alive.  That is a weaker claim about a defect
    # that bricked sessions (`queue-cut-refusal-lost-its-inducer`).
    #
    # NARROWING to `gestures: []` reproduces the ORIGINAL inducer rather than an
    # approximation of it: `offers()` reads a present-but-empty gesture list as
    # withheld, so the page falls back to `delete-backward` exactly as it did on
    # v3, and the engine refuses it on a range because it is caret-only.  Same
    # action, same refusal, same code -- on the shipped wasm, with one mirrored
    # manifest and no product change.
    parser.add_argument("--refusal-diagnostic", action="store_true",
                        help="withhold the action named by --refusal-action in "
                             "a MIRRORED manifest (gestures: []), so the "
                             "product's cut path meets a refusal again and "
                             "finding 063's three properties can be asserted; "
                             "stamps the report diagnostic")
    parser.add_argument("--refusal-action", default="delete-selection",
                        help="which action --refusal-diagnostic withholds")
    # RUN THE WHOLE NET AGAINST A PROFILE THAT IS NOT THE SHIPPED ONE.
    #
    # Added 2026-08-23 to tell two hypotheses apart without editing the product
    # page and risking leaving it edited. `a11y-projection` and `e2-editor-v5`
    # share a CORE and differ by one compile flag, so pointing this net at each
    # is the cheapest discriminator between "the a11y core changed behaviour"
    # and "walking the outline on every state read did".
    #
    # Mirrored, never written: the page's worker URL and its pinned wasm hash
    # move TOGETHER, because a page given one without the other runs an engine
    # its own guard is supposed to reject.
    parser.add_argument("--profile", default=None,
                        help="serve the product page against this profile "
                             "instead of the one it ships pointing at; stamps "
                             "the report diagnostic")
    parser.add_argument("--no-caret-exclusion", action="store_true",
                        help="leave the drawn caret in the ink scan. Finding "
                             "072: the caret bridges the gap between two "
                             "lines and text_bands() merges them, so this "
                             "reproduces the wrong aim on demand")
    parser.add_argument("--range-delete-action", default="delete-backward",
                        help="which action the diagnostic above widens. "
                             "`delete-selection` is the one that matters since "
                             "ABI 4: the shipped manifest grants it "
                             "`range-single` only, and the engine requires BOTH "
                             "range bits for an unclassified range "
                             "(probe_engine.cpp:4471), so that grant is an off "
                             "switch rather than a narrowing")
    args = parser.parse_args()
    global EXCLUDE_CARET
    EXCLUDE_CARET = not args.no_caret_exclusion

    report: dict = {
        "schemaVersion": 1,
        "release": "e2-c-product-path",
        "browser": args.browser,
        # Finding 072.  Recorded on every run because it changes what every
        # band-aimed check aims AT, and a report that does not say which scan
        # produced it cannot be compared with one taken the other way.
        "caretExcludedFromInk": not args.no_caret_exclusion,
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
                  "3x across ordinary displays",
                  "Browser.grantPermissions clipboardReadWrite (Chrome only). "
                  "WebDriver refuses clipboard writes by default, and the "
                  "product's cut is copy-then-delete -- so without the "
                  "permission the delete correctly never runs and whether the "
                  "text is REMOVED cannot be measured at all. Granting it is "
                  "how a real user's browser behaves after they allow it"],
        "mutation": args.mutate if args.mutate != "none" else None,
        "checks": [],
        "steps": [],
    }

    scratch = Path(tempfile.mkdtemp(prefix="e2c-product-path-"))
    root = PROJECT / "dist"
    if args.mutate != "none":
        root, mutation_report = apply_mutation(args.mutate, scratch)
        report["mutationDetail"] = mutation_report
    if args.cut_via_replace_selection:
        sdk_rel = "sdk/document-sdk.js"
        page_rel = "e2-editor-app.js"
        sdk_text = (root / sdk_rel).read_text(encoding="utf-8")
        guard = ('    if (typeof text !== "string" || text.length === 0) {\n'
                 '      throw new DocumentSdkError(\n'
                 '        "INVALID_ARGUMENT", "replaceSelection requires '
                 'non-empty text",\n'
                 '      );\n'
                 '    }\n')
        if guard not in sdk_text:
            raise SystemExit(
                "the empty-text guard is not where this diagnostic expects it "
                "in " + sdk_rel + "; the tree moved under the diagnostic. Fix "
                "the pattern rather than dropping the guard blindly.")
        sdk_patched = sdk_text.replace(
            guard,
            '    if (typeof text !== "string") {\n'
            '      throw new DocumentSdkError(\n'
            '        "INVALID_ARGUMENT", "replaceSelection requires a string",\n'
            '      );\n'
            '    }\n', 1)
        page_text = (root / page_rel).read_text(encoding="utf-8")
        delete_half = '    await session.action("delete-backward", {});'
        if delete_half not in page_text:
            raise SystemExit(
                "cut's delete half is not where this diagnostic expects it in "
                + page_rel + "; the tree moved under the diagnostic.")
        page_patched = page_text.replace(
            delete_half,
            '    await session.document.replaceSelection("");', 1)
        # A THIRD gate, found by running this: the WORKER refuses the call
        # before the engine sees it.  `withWasmBytes` (sdk-worker.js:348-353)
        # asks oxsdk_buffer_alloc for `length` bytes and throws when the pointer
        # is falsy -- and a zero-length allocation returns 0, so a generic
        # allocation-failure check also refuses every empty payload.
        # Incidental, not a policy about empty text.  Allocating max(1, length)
        # while still passing `length` to the callback is identical for every
        # non-zero payload and only changes the length-0 case.
        # The worker the PAGE loads is the profile's copy, not dist/sdk/ --
        # the stack trace in the first run of this diagnostic said so
        # (profiles/e2-editor-v4/sdk-worker.js). Mirroring the wrong one
        # changes nothing and looks like the gate moved.
        worker_rel = f"profiles/{product_profile(root)}/sdk-worker.js"
        worker_text = (root / worker_rel).read_text(encoding="utf-8")
        alloc = ('  const pointer = Number(ccall("oxsdk_buffer_alloc", '
                 '"number", ["number"], [length]));')
        if alloc not in worker_text:
            raise SystemExit(
                "the buffer allocation is not where this diagnostic expects it "
                "in " + worker_rel + "; the tree moved under the diagnostic.")
        worker_patched = worker_text.replace(
            alloc,
            '  const pointer = Number(ccall("oxsdk_buffer_alloc", "number", '
            '["number"], [Math.max(1, length)]));', 1)
        mirror = scratch / "cut-replace-selection-root"
        build_mirror(root, mirror,
                     {sdk_rel: sdk_patched.encode("utf-8"),
                      page_rel: page_patched.encode("utf-8"),
                      worker_rel: worker_patched.encode("utf-8")})
        root = mirror
        report["cutViaReplaceSelection"] = {
            "evidenceClass": "diagnostic",
            "note": "This run did NOT use the shipped SDK or the shipped page. "
                    "It answers whether LOK's paste with zero-length text "
                    "deletes a selection -- which decides whether cut needs an "
                    "engine change at all. Not a product measurement.",
            "mirrored": [sdk_rel, page_rel, worker_rel],
            "gatesRemoved": [
                "document-sdk.js:468 -- the JS empty-text guard",
                "sdk-worker.js:352 -- withWasmBytes throwing on a zero-length "
                "allocation, which is a generic allocation-failure check and "
                "not a policy about empty text",
            ],
            "declaredBypass": "session.document.replaceSelection() goes around "
                              "the shell's _enqueue, so the state machine does "
                              "not see this mutation. A shipped fix would wrap "
                              "it in EditorSession -- a shell change, not a "
                              "link.",
            "wasmUnchanged": True,
            "prediction": "findings/evidence/queue-cut-cannot-remove-text/"
                          "PREDICTION-replace-selection.md",
        }
    if args.range_delete_diagnostic:
        relative = f"profiles/{product_profile(root)}/sdk-manifest.json"
        manifest = json.loads((root / relative).read_text(encoding="utf-8"))
        contract = manifest["editorContract"]
        widened_action = args.range_delete_action
        if widened_action not in contract["actions"]:
            raise SystemExit(
                f"--range-delete-action {widened_action!r} is not in this "
                f"profile's action map: {sorted(contract['actions'])}")
        before = list(contract["actions"][widened_action]["gestures"])
        # BOTH range bits, and `collapsed` only if it already had it.  Adding
        # `collapsed` to delete-selection would give it delete-backward's job
        # as well, and then a green would not say which action removed the
        # text.
        after = ["range-single", "range-cross"]
        if "collapsed" in before:
            after = ["collapsed", *after]
        contract["actions"][widened_action]["gestures"] = after
        widened = json.dumps(manifest, ensure_ascii=False,
                             indent=2).encode("utf-8")
        mirror = scratch / "range-delete-root"
        build_mirror(root, mirror, {relative: widened})
        root = mirror
        report["rangeDeleteDiagnostic"] = {
            "evidenceClass": "diagnostic",
            "note": "This run did NOT use the shipped manifest. It is filed to "
                    "answer whether the ENGINE removes a range at all, which "
                    "the shipped manifest withholds by declaring the ten v1 "
                    "actions caret-only. It is not a product measurement and "
                    "must never be read as one.",
            "action": widened_action,
            "gesturesBefore": before,
            "gesturesAfter": after,
            "wasmUnchanged": True,
            "prediction": "findings/evidence/queue-cut-cannot-remove-text/"
                          "PREDICTION.md",
        }
    if args.refusal_diagnostic:
        if args.range_delete_diagnostic:
            raise SystemExit(
                "--refusal-diagnostic and --range-delete-diagnostic both "
                "rewrite the same manifest in opposite directions; running "
                "them together would produce a report whose gesture list is "
                "whichever one happened to be applied second")
        relative = f"profiles/{product_profile(root)}/sdk-manifest.json"
        manifest = json.loads((root / relative).read_text(encoding="utf-8"))
        contract = manifest["editorContract"]
        withheld_action = args.refusal_action
        if withheld_action not in contract["actions"]:
            raise SystemExit(
                f"--refusal-action {withheld_action!r} is not in this "
                f"profile's action map: {sorted(contract['actions'])}")
        before = list(contract["actions"][withheld_action]["gestures"])
        if not before:
            raise SystemExit(
                f"--refusal-action {withheld_action!r} already ships with no "
                f"gestures, so withholding it changes nothing and the run "
                f"would report a refusal the SHIPPED manifest also produces")
        # PRESENT AND EMPTY, never removed.  The engine sets every entry to
        # all-permitted on the first mask call and intersects from there, so
        # deleting the action here would ship it WIDE OPEN -- the opposite of
        # this arm's intent, and silent.  Same rule the shipped manifest obeys
        # for select-all.
        contract["actions"][withheld_action]["gestures"] = []
        narrowed = json.dumps(manifest, ensure_ascii=False,
                              indent=2).encode("utf-8")
        mirror = scratch / "refusal-root"
        build_mirror(root, mirror, {relative: narrowed})
        root = mirror
        report["refusalDiagnostic"] = {
            "evidenceClass": "diagnostic",
            "note": "This run did NOT use the shipped manifest. It withholds "
                    "one action so the product's cut path meets a refusal "
                    "again, which is the state finding 063 is about and which "
                    "the 2026-08-22 widening removed from the product's own "
                    "path. It is a measurement of the REFUSAL DISPOSITION and "
                    "must never be read as a measurement of what cut does on "
                    "the shipped profile.",
            "action": withheld_action,
            "gesturesBefore": before,
            "gesturesAfter": [],
            "wasmUnchanged": True,
            "expectedFallback":
                "the page reads a present-but-empty gesture list as withheld "
                "(`offers()`), so cut's delete half falls back to "
                "`delete-backward`, which is caret-only and is refused on the "
                "range a cut necessarily has -- the v3 path verbatim",
            "restores": "queue-cut-refusal-lost-its-inducer",
        }
    if args.profile:
        page_rel = "e2-editor-app.js"
        source = (root / page_rel).read_text(encoding="utf-8")
        manifest_path = root / "profiles" / args.profile / "sdk-manifest.json"
        if not manifest_path.is_file():
            raise SystemExit(f"--profile {args.profile!r} has no manifest at "
                             f"{manifest_path}")
        wasm = json.loads(manifest_path.read_text(
            encoding="utf-8"))["editorContract"]["wasmSha256"]
        worker_matches = re.findall(
            r'"\./profiles/[A-Za-z0-9._-]+/sdk-worker\.js"', source)
        pin_match = re.search(r'const PINNED_WASM_SHA256 = "([0-9a-f]+)";',
                              source)
        if len(worker_matches) != 1 or not pin_match:
            raise SystemExit(
                "the page does not carry exactly one worker URL and one pinned "
                "hash, so this mirror cannot rewrite it without guessing")
        page = source.replace(worker_matches[0],
                              f'"./profiles/{args.profile}/sdk-worker.js"', 1)
        page = page.replace(pin_match.group(0),
                            f'const PINNED_WASM_SHA256 = "{wasm[:16]}";', 1)
        mirror = scratch / "profile-root"
        build_mirror(root, mirror, {page_rel: page.encode("utf-8")})
        root = mirror
        report["profileDiagnostic"] = {
            "evidenceClass": "diagnostic",
            "note": "This run did NOT use the shipped page. It was mirrored to "
                    "load a different profile, so every result here is about "
                    "that profile and must not be quoted as the product's.",
            "profile": args.profile,
            "pinBefore": pin_match.group(1),
            "pinAfter": wasm[:16],
        }

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
        # Before navigating, so the page never sees a denied clipboard.
        clipboard_grant = {"granted": False, "why": "not attempted"}
        call = getattr(session, "call", None)
        if call is not None:
            try:
                call("Browser.grantPermissions",
                     {"origin": f"http://127.0.0.1:{port}",
                      "permissions": ["clipboardReadWrite",
                                      "clipboardSanitizedWrite"]})
                # A granted permission is not enough: `clipboard.writeText`
                # also requires the document to be FOCUSED, and a headless page
                # driven over CDP is not.  Both, or the write is refused for a
                # reason that has nothing to do with the product.
                call("Emulation.setFocusEmulationEnabled", {"enabled": True})
                clipboard_grant = {"granted": True, "focusEmulated": True}
            except Exception as error:      # noqa: BLE001 -- reported, not raised
                clipboard_grant = {"granted": False,
                                   "why": f"{type(error).__name__}: {error}"}
        else:
            clipboard_grant = {"granted": False,
                               "why": "this browser session has no CDP"}
        report["clipboardPermission"] = clipboard_grant
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

        # --- action:redo ----------------------------------------------------
        #
        # Immediately after undo, and that ordering is the check: undo has just
        # taken the marker out, so redo putting it back is a statement about
        # redo rather than about whatever was in the document before.
        #
        # Reachable only since the ABI 4 profile. The coverage registry carried
        # this path as WAIVED with the reason pinned to the v3 manifest hash;
        # that pin expired the moment the v4 artifact shipped, and the audit
        # demanded the path be driven instead. This is that.
        redo_button = evaluate(session, REDO_BUTTON) or {}
        redo_offered = bool(redo_button.get("present")) and not redo_button.get("hidden")
        # The marker must be ABSENT going in, or "the marker is present after
        # redo" is satisfied by a document that never lost it -- the same
        # absence-needs-a-precondition rule the undo check above learned.
        marker_gone_before_redo = INSERT_MARK not in undo_content
        before_redo = revision_of(evaluate(session, READ_STATE))
        evaluate(session, CLEAR_TOAST)
        if redo_offered:
            evaluate(session, PRESS.replace("ARG_ACTION", "redo"))
        redone_state = wait_for(
            session,
            lambda s, floor=before_redo: revision_of(s) is not None
            and revision_of(s) != floor, 20) if redo_offered else None
        redo_toast = evaluate(session, READ_TOAST) or ""
        fifth = capture_save(session, 4) if redo_offered else {}
        redo_content = fifth.get("content") or ""
        # Same witnesses as undo: redo must put back the last edit and nothing
        # else. A redo that replayed the whole session would also satisfy "the
        # marker is back".
        redo_kept = [w for w in undo_witnesses if w in redo_content]
        check("product-redo-button-restores-what-undo-removed",
              is_an_odt(fifth) and INSERT_MARK in redo_content
              and redo_kept == undo_witnesses
              and redone_state is not None
              and revision_of(redone_state) != before_redo,
              outcome=None if (redo_offered and marker_gone_before_redo
                               and undo_witnesses) else "NOT_ESTABLISHED",
              observed={"buttonOffered": redo_button,
                        "markerGoneBeforeRedo": marker_gone_before_redo,
                        "revisionBefore": before_redo,
                        "revisionAfter": revision_of(redone_state) if redone_state else None,
                        "markBackInSavedOdt": INSERT_MARK in redo_content,
                        "witnessesExpected": undo_witnesses,
                        "witnessesKept": redo_kept,
                        "toast": redo_toast, "savedBytes": fifth.get("bytes")},
              oracle="pressing the product's own 重做 button puts back exactly "
                     "the text undo just removed -- read from the saved ODT, and "
                     "with the earlier commits as witnesses so a redo that "
                     "replayed more than one edit is not mistaken for a correct "
                     "one. NOT_ESTABLISHED rather than FAIL on a profile that "
                     "does not carry redo: the button is hidden there and "
                     "pressing it would measure nothing")

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

        # ------------------------------------------- the keyboard, on its own
        # The row promises Ctrl+Z / B / I / U / A, and until 2026-08-19 four of
        # those were deliberately unwired: under finding 059 every inline format
        # failed on the shipped engine, so binding them to the keyboard would
        # have copied one defect onto a second path.  With 059 fixed they are
        # wired, and this drives them WITHOUT touching the toolbar -- the whole
        # point of the row is that the toolbar is not the only way in.
        keyboard: dict = {}
        read_pressed_for = ("(() => { const b = document.querySelector("
                            "'#toolbar button[data-action=\"ARG_ACTION\"]'); "
                            "return b ? b.getAttribute('aria-pressed') : null; })()")
        scan, bands = stable_bands(session)
        if bands:
            band = bands[1] if len(bands) > 1 else bands[0]
            evaluate(session, POINT_AT
                     .replace("ARG_X", f"{(band['first'] + 4) / scan['width']:.5f}")
                     .replace("ARG_Y", f"{band['centreFraction']:.5f}"))
            wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)

        def press_accel(key):
            evaluate(session, TYPE_KEY.replace("ARG_KEY", key)
                     .replace("ARG_CTRL", "true"))
            time.sleep(1.6)

        # Bold and underline, twice each: once to turn on, once to turn off.
        # Off is what makes it a toggle rather than a one-way switch, and
        # underline could not answer at all until the relink gave it a state
        # cache.
        for action, key in (("set-bold", "b"), ("set-underline", "u")):
            press_accel(key)
            on = evaluate(session, read_pressed_for.replace("ARG_ACTION", action))
            press_accel(key)
            off = evaluate(session, read_pressed_for.replace("ARG_ACTION", action))
            keyboard[action] = {"afterFirst": on, "afterSecond": off,
                                "toggled": on == "true" and off == "false"}

        # Ctrl+A is not measured because it is not bound: select-all is not one
        # of the fifteen actions, and the geometric substitute was measured
        # selecting nothing (see the page's own comment).  The row's sentence
        # was changed rather than the check widened.
        # Ctrl+Z: type a marker through the composition path, then undo it from
        # the keyboard and read the DOCUMENT, not the revision counter.
        floor = revision_of(evaluate(session, READ_STATE))
        evaluate(session, COMPOSE.replace("ARG_TEXT", KEYBOARD_MARK))
        wait_for(session, lambda s, f=floor: revision_of(s) is not None
                 and f is not None and revision_of(s) > f, 25)
        typed_doc = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
        keyboard["markerTyped"] = KEYBOARD_MARK in (typed_doc.get("content") or "")
        press_accel("z")
        # Ctrl+S: the save itself is the observation -- the shim captures the
        # bytes, and nothing pressed the button.
        saves_before = evaluate(session, SAVE_COUNT) or 0
        press_accel("s")
        keyboard["ctrlSSaved"] = wait_saves(session, saves_before + 1, 90)
        undone_doc = (zip_report(base64.b64decode(evaluate(
            session, READ_SAVE.replace("ARG_INDEX", str(saves_before)))["b64"]))
            if keyboard["ctrlSSaved"] else {})
        keyboard["markerGoneAfterUndo"] = KEYBOARD_MARK not in (
            undone_doc.get("content") or "")
        check("the-keyboard-reaches-the-document",
              bool(keyboard.get("set-bold", {}).get("toggled")
                   and keyboard.get("set-underline", {}).get("toggled")
                   and keyboard["markerTyped"]
                   and keyboard["ctrlSSaved"]
                   and keyboard["markerGoneAfterUndo"]
                   and is_an_odt(undone_doc)),
              observed=keyboard,
              oracle="Ctrl+B and Ctrl+U each turn their format ON and then OFF, "
                     "read from the engine's own state as the page renders it "
                     "into aria-pressed; Ctrl+A produces a selection the "
                     "product recognises as a RANGE (its collapsed-only format "
                     "buttons go disabled); Ctrl+Z takes a typed marker back "
                     "out of the SAVED document; and Ctrl+S writes that "
                     "document without anything pressing the save button",
              notEstablished="Ctrl+I, which goes through exactly the same "
                             "`editorAction` call as Ctrl+B and Ctrl+U with a "
                             "different slot, so a third identical arm would "
                             "re-measure the same wiring; and Ctrl+A, which is "
                             "not bound at all -- select-all is not one of the "
                             "fifteen actions and the geometric substitute was "
                             "measured selecting nothing "
                             "(queue-no-select-all-action)")

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
        clicks = caret_click_fractions(
            evaluate(session, LINE_INK.replace("ARG_Y", CARET_LINE)) or {})
        place_caret_and_settle(session, POINT_AT, clicks["near"], CARET_LINE)
        time.sleep(1.0)
        columns_start = evaluate(session, CARET_COLUMNS
                                 .replace("ARG_Y", CARET_LINE)) or {}
        # Past the end of the text: the caret must snap to the line's end, which
        # is what makes "it went where I clicked" checkable without knowing the
        # engine's coordinates.
        place_caret_and_settle(session, POINT_AT, clicks["past"], CARET_LINE)
        time.sleep(1.0)
        columns_end = evaluate(session, CARET_COLUMNS
                               .replace("ARG_Y", CARET_LINE)) or {}
        caret = caret_from_columns(columns_start, columns_end)
        # Recorded so a later reader can see WHERE this run clicked; a verdict
        # whose input is derived must show the derivation.
        caret["clickedAt"] = clicks
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
                     "verdict does not depend on the browser window (060), "
                     "and the CLICK is derived from that ink too rather than "
                     "from a viewport fraction. "
                     "LIMIT: this sees the caret by watching it move, so a "
                     "caret pinned to a constant column reads the same as one "
                     "that is never drawn. "
                     "LIMIT: the caret is 1 px and lands on a character "
                     "boundary, so it is adjacent to glyph ink by "
                     "construction and strokeLost can be small -- measured 19 "
                     "on Firefox and 2 on Chrome at the same derived "
                     "position. It is a margin, not a cliff, and the robust "
                     "alternative (differencing a clean root against the "
                     "`caret` mutation mirror, which is how finding 060 was "
                     "actually diagnosed) costs a second page load and is not "
                     "run per round",
              notEstablished="the sampled band carries no text ink, which is a "
                             "harness problem rather than a product one")

        # And drawn WHERE.  A caret that ignores x, or sits at a fixed offset,
        # or lands on the wrong line, fails this while passing the one above.
        span = caret.get("inkSpan") or 0
        near = caret.get("fractionNearStart")
        past = caret.get("fractionPastEnd")
        # NOT_ESTABLISHED now also covers "a read did not find the caret".
        # Without this the check reads a tie-break index as a position and can
        # pass on a caret it never saw -- which is what it did on Firefox until
        # 2026-08-21.  Whether the caret is drawn at all stays the OTHER
        # check's question, and that one still fails rather than abstaining.
        measurable = bool(reachable and span > 0
                          and near is not None and past is not None)
        check("the-caret-lands-where-the-click-was",
              bool(measurable and near < 0.25 and past > 0.75),
              outcome=None if measurable else "NOT_ESTABLISHED",
              observed=caret,
              oracle="a click near the start of a line puts the caret in its "
                     "first quarter, and a click past the end puts it in the "
                     "last quarter -- measured against that line's own ink "
                     "extent. A caret that ignores x, one at a constant offset, "
                     "and one on the wrong line all fail this",
              notEstablished="no line ink was found to measure against, or a "
                             "read did not find the caret at all -- a column "
                             "index that came from a tie-break is not a "
                             "position, so no fraction is reported for it")


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
        # --- and one RANGE arm, which the row was wrongly said to be missing --
        # The note on this checklist row used to say multi-paragraph conversion
        # was refused by the gesture mask.  That was a real thing measured on
        # the wrong actions: the FOUR INLINE formats declare `["collapsed"]`,
        # but all five paragraph actions declare all three gestures and the
        # profile's crossParagraphDisposition is `verify-every-block`.  Nothing
        # was blocking it; nothing had driven it.
        #
        # Aimed at the two numbered lines, which the five arms above leave
        # untouched, so this arm still acts on paragraphs in the opposite state.
        cross: dict = {"arm": "range-cross", "action": "set-list-none"}
        arms.append(cross)
        scan, bands = stable_bands(session)
        numbered = [index for index, line in enumerate(lines)
                    if line["kind"] == "number"]
        pair = next(([a, b] for a, b in zip(numbered, numbered[1:])
                     if b == a + 1), [])
        cross["numberedLines"] = numbered
        cross["lineIndexes"] = pair
        cross["bands"] = len(bands)
        cross["lines"] = len(lines)
        if len(pair) == 2 and len(bands) == len(lines):
            first, second = bands[pair[0]], bands[pair[1]]
            evaluate(session, DRAG
                     .replace("ARG_X1", f"{(first['first'] + 4) / scan['width']:.5f}")
                     .replace("ARG_Y1", f"{first['centreFraction']:.5f}")
                     .replace("ARG_X2", f"{(second['last'] + 6) / scan['width']:.5f}")
                     .replace("ARG_Y2", f"{second['centreFraction']:.5f}"))
            time.sleep(2.0)
            # The product's own affordance is the precondition: if it greys the
            # button out for this selection shape, the user cannot do this and
            # the arm has nothing to measure.
            offered = {b["action"]: b["disabled"]
                       for b in (evaluate(session, READ_STATE) or {}).get("buttons", [])}
            cross["buttonOffered"] = offered.get("set-list-none") is False
            label = evaluate(session, BUTTON_LABEL.replace("ARG_ACTION",
                                                           "set-list-none"))
            evaluate(session, CLEAR_TOAST)
            evaluate(session, PRESS.replace("ARG_ACTION", "set-list-none"))
            wait_for(session, lambda s, want=label: bool(want)
                     and want in (s.get("latency") or ""), 30)
            cross["toast"] = evaluate(session, READ_TOAST)
            after = document_lines(capture_save(
                session, evaluate(session, SAVE_COUNT) or 0))
            same = len(after) == len(lines)
            cross["bothChanged"] = same and all(
                after[index]["kind"] == "body"
                and after[index]["text"] == lines[index]["text"] for index in pair)
            cross["neighboursSurvived"] = same and all(
                after[index]["kind"] == lines[index]["kind"]
                and after[index]["text"] == lines[index]["text"]
                for index in (pair[0] - 1, pair[1] + 1)
                if 0 <= index < len(lines))
            cross["ok"] = bool(cross["buttonOffered"] and cross["bothChanged"]
                               and cross["neighboursSurvived"])
            cross["outcome"] = "PASS" if cross["ok"] else "FAIL"
            if after:
                lines = after
        else:
            cross["outcome"] = "NOT_ESTABLISHED"
            cross["why"] = ("no adjacent pair of numbered lines to drag across, "
                            "or the band-to-line mapping did not hold")

        judged = [a for a in arms if a["outcome"] in ("PASS", "FAIL")]
        established = len(judged) == len(arms_spec) + 1
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
              notEstablished="the blank-line cell, which belongs to finding "
                             "046's queue item. Range gestures ARE covered now: "
                             "the sixth arm drags across two paragraphs and "
                             "requires both to change and their neighbours to "
                             "survive")

        # ------------------------------------------------------------- Ctrl+X
        # MOVED here on 2026-08-19, from before the paste check.  It aims at a
        # NAMED line, and by its old position the document had picked up an
        # empty paragraph from the recovery recipe -- ten lines, eight ink
        # bands, no way to say which paragraph the drag would cover, so the
        # check reported NOT_ESTABLISHED and measured nothing.  Here the
        # paragraph-format block has just re-opened the fixture, so the mapping
        # holds.
        # Cut is copy plus a delete, in that order, so a failed copy must not
        # still remove the text. Under WebDriver the clipboard write is refused,
        # which means the delete correctly does NOT run -- so this check can
        # only establish that the product handles the event and asks the engine.
        # Aimed at a NAMED line rather than at a viewport fraction, so "the text
        # went away" is a statement about a specific paragraph and its
        # neighbours can be required to survive.  E1-LC-BETWEEN is chosen
        # because nothing else in this run stands on it: it is not one of the
        # witnesses `surviving_witnesses()` derives, and T3b re-opens the
        # fixture before it uses it.
        cut_before = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
        cut_lines = document_lines(cut_before)
        cut_target = [index for index, line in enumerate(cut_lines)
                      if "E1-LC-BETWEEN" in line["text"]]
        scan, bands = stable_bands(session)
        cut_record: dict = {"lines": len(cut_lines), "bands": len(bands),
                            "targetIndex": cut_target}
        cut_aimed = len(cut_target) == 1 and len(bands) == len(cut_lines)
        if cut_aimed:
            band = bands[cut_target[0]]
            # PART of the line, not all of it.  Dragging across the whole line
            # and cutting removes the paragraph, which is a multi-block
            # mutation: the barrier cannot verify it, the outcome comes back
            # MUTATION_OUTCOME_UNKNOWN, and the session lands in
            # recoverable-error -- measured 2026-08-19, and it is finding 046's
            # family rather than anything about cut.  Cutting inside one
            # paragraph is both the ordinary thing a user does and the thing
            # this check can hold the product to.
            evaluate(session, DRAG
                     .replace("ARG_X1", f"{max(0.0, (band['first'] + 2) / scan['width']):.5f}")
                     .replace("ARG_Y1", f"{band['centreFraction']:.5f}")
                     .replace("ARG_X2", f"{((band['first'] + band['last']) / 2) / scan['width']:.5f}")
                     .replace("ARG_Y2", f"{band['centreFraction']:.5f}"))
            time.sleep(1.5)
        evaluate(session, CLEAR_TOAST)
        evaluate(session, CLEAR_TOASTS)
        cut_result = evaluate(session, CUT)
        time.sleep(2.5)
        cut_toast = evaluate(session, READ_TOAST) or ""
        cut_record["toast"] = cut_toast
        cut_record["handled"] = (cut_result or {}).get("handled")
        cut_after = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
        after_lines = document_lines(cut_after)
        # What a cut can and cannot do under THIS contract, measured rather than
        # assumed on 2026-08-19 once the clipboard actually worked:
        #
        #   * the copy half succeeds;
        #   * the delete half is REFUSED, because `delete-backward` is declared
        #     caret-only for the v1 actions and a cut necessarily runs on a
        #     range -- so cut cannot remove text at all here;
        #   * therefore the document must be UNCHANGED, which is exactly what
        #     the refusal's own message claims.
        #
        # This became visible only when the harness stopped being denied the
        # clipboard: with the write refused the delete never ran, so the whole
        # path was unmeasured. It also found finding 063 -- the refusal used to
        # brick the session.
        after_texts = [line["text"] for line in after_lines]
        cut_record["documentUnchanged"] = after_texts == [
            line["text"] for line in cut_lines]
        cut_record["stateAfterCut"] = (evaluate(session, READ_STATE) or {}).get("state")
        cut_record["toasts"] = evaluate(session, READ_TOASTS)
        said = " ".join(cut_record.get("toasts") or [])
        cut_record["refusalReported"] = "EDITOR_FORMAT_GESTURE_UNSUPPORTED" in said
        # THE MEASUREMENT queue-cut-cannot-remove-text asks for, recorded on
        # every run and read by the diagnostic one.  `documentUnchanged` answers
        # "did anything move"; these answer "did the TARGET go, and did its
        # neighbours survive" -- which is the difference between a delete and a
        # document that lost a paragraph somewhere else.
        if cut_aimed:
            target_text = cut_lines[cut_target[0]]["text"]
            neighbours = [cut_lines[i]["text"]
                          for i in (cut_target[0] - 1, cut_target[0] + 1)
                          if 0 <= i < len(cut_lines)]
            # AN EMPTY CAPTURE IS NOT AN EMPTY DOCUMENT.
            #
            # The first version reported targetStillPresent:false and
            # neighboursSurvive:false from a save that never happened -- the
            # session had gone to recoverable-error and the product answered
            # `EDITOR_NOT_READY: save is unavailable`, so `after_texts` was []
            # and every "is it still there" question answered "no".  That reads
            # as "the cut deleted the whole document" and means "nothing was
            # measured".  Same shape as the caret oracle's tie-break, found the
            # same day: a question asked of missing data must return null.
            readable = is_an_odt(cut_after) and bool(after_texts)
            cut_record["rangeDelete"] = {
                "documentReadableAfter": readable,
                "targetText": target_text,
                "targetStillPresent":
                    any(target_text == t for t in after_texts) if readable else None,
                "targetTextAnywhere":
                    any(target_text in t for t in after_texts) if readable else None,
                "neighboursSurvive": all(
                    any(n == t for t in after_texts)
                    for n in neighbours) if readable else None,
                "linesBefore": len(cut_lines),
                "linesAfter": len(after_texts) if readable else None,
                "why": None if readable
                       else "the save after the cut did not produce a readable "
                            "ODT, so whether the text was removed is NOT "
                            "measured here -- see toasts",
            }
        # A CAPABILITY GAP IS NOT A DEFECT, AND MUST NOT WEAR ITS COSTUME.
        #
        # The clipboard grant is Chrome-only -- it needs CDP, and the Firefox
        # session has none.  Without it `clipboard.writeText` is refused, the
        # copy half fails, and the delete half never runs, so the refusal this
        # check exists to verify (finding 063) cannot be produced at all.
        # Until 2026-08-21 the check simply FAILED there, which makes a browser
        # the harness cannot drive indistinguishable from a product that broke
        # -- the exact confusion the recovery check's loud exit was built to
        # avoid.  Measured: Firefox reported `CLIPBOARD_DENIED`, an unchanged
        # document, and a live session, and was scored a product failure.
        cut_record["clipboardGranted"] = bool(clipboard_grant.get("granted"))
        cut_measurable = cut_aimed and cut_record["clipboardGranted"]
        # WIDENED 2026-08-22, and the oracle is replaced rather than relaxed.
        #
        # Until today `delete-selection` shipped with `["range-single"]`, and
        # under this engine's gate that is an OFF SWITCH rather than a narrower
        # offer: an unclassified selection needs BOTH range bits, so the cut
        # was refused on every range and the check's job was to verify that the
        # product said so and changed nothing (finding 063).  The manifest now
        # grants both, on four measured cross-paragraph shapes
        # (findings/evidence/queue-cut-cannot-remove-text/RESULT-range-cross.md),
        # so the question a check can ask has changed: not "is the refusal
        # handled" but "is the text GONE".
        #
        # WHAT THIS COST, written here rather than left to be discovered: the
        # refusal that finding 063 is about no longer happens on the product's
        # own path, so this run no longer exercises it.  That route now lives
        # in the `cut-falls-back-to-the-caret-only-delete` mutation and, since
        # 2026-08-22, in `--refusal-diagnostic` -- which asserts finding 063's
        # three properties positively instead of asserting that a check goes
        # red.  `queue-cut-refusal-lost-its-inducer` carries the reasoning.
        removed = cut_record.get("rangeDelete") or {}
        # THE TWO ARMS ARE MUTUALLY EXCLUSIVE, and saying so here is the point.
        #
        # Under --refusal-diagnostic the manifest withholds the delete, so the
        # text is SUPPOSED to survive.  Scoring `cut-removes-the-selected-text`
        # there would report a product failure caused by the harness's own
        # mirror -- the shape of mistake this file already carries a NOT_ESTAB-
        # LISHED path for on the clipboard axis.
        refusal_induced = bool(args.refusal_diagnostic)
        cut_scorable = cut_measurable and not refusal_induced
        check("cut-removes-the-selected-text",
              bool(cut_measurable and (cut_result or {}).get("handled")
                   and cut_record["stateAfterCut"] == "ready"
                   and not cut_record["refusalReported"]
                   and removed.get("documentReadableAfter")
                   and removed.get("targetStillPresent") is False
                   and removed.get("targetTextAnywhere") is False
                   and removed.get("neighboursSurvive")
                   and is_an_odt(cut_after)),
              outcome=None if cut_scorable else "NOT_ESTABLISHED",
              observed=cut_record,
              oracle="a cut on a range REMOVES that text from the saved "
                     "document, leaves both neighbouring paragraphs verbatim, "
                     "reports no refusal, and leaves the session `ready`. The "
                     "oracle is the SAVED ODT and it is anchored to a named "
                     "paragraph: a revision that advanced proves a dispatch, "
                     "not a deletion, and 'the document changed' passes on a "
                     "cut that removed the wrong paragraph",
              notEstablished="anything at all, when clipboardGranted is "
                             "false: this browser session has no CDP, so the "
                             "copy half is denied by the DRIVER and the delete "
                             "half never runs. That is a gap in what the "
                             "harness can reach, not a defect in the product. "
                             "Also not established here, and it is a LOSS "
                             "rather than a gap: that a REFUSED cut is "
                             "reported to the user and changes nothing "
                             "(finding 063). The manifest now grants the "
                             "gesture, so the product path produces no refusal "
                             "to observe -- that is what --refusal-diagnostic "
                             "is for, and under it THIS check is the one that "
                             "cannot be established")

        # ------------------------------------------------- finding 063, kept
        #
        # The three properties of a refused cut, asserted rather than implied.
        # It abstains on the shipped manifest because there is no refusal to
        # judge, and it is the reason `--refusal-diagnostic` exists: the widen-
        # ing that made cut work took away the state its own regression check
        # needed, for the third time in this tree (046's disposition, 038's
        # inducer, now this).
        #
        # `documentUnchanged` is the term that needs a POSITIVE CONTROL, and it
        # has one without any extra driving: the SAME drive, on the SAME line,
        # with the shipped manifest, is `cut-removes-the-selected-text`, which
        # requires the target to be GONE. One run of each says the document is
        # untouched because the action was refused, and not because the drag
        # missed or the key never arrived. Without that pair, "nothing changed"
        # and "nothing happened" are the same observation -- and this tree has
        # written that lesson down three times in one day.
        #
        # `saveStillWorks` is the third property and it is not decoration:
        # finding 063's actual harm was a notice telling the user to discard
        # unsaved work. A session that reports `ready` but can no longer save
        # has failed 063 while passing a state check.
        refusal_measurable = cut_measurable and refusal_induced
        refusal_record = {
            "induced": refusal_induced,
            "withheldAction": (report.get("refusalDiagnostic") or {}).get("action"),
            "refusalReported": cut_record["refusalReported"],
            "toasts": cut_record.get("toasts"),
            "documentUnchanged": cut_record["documentUnchanged"],
            "stateAfterCut": cut_record["stateAfterCut"],
            "saveStillWorks": is_an_odt(cut_after) and bool(after_lines),
            "handled": cut_record["handled"],
        }
        check("a-refused-action-is-reported-and-changes-nothing",
              bool(refusal_measurable
                   and refusal_record["handled"]
                   and refusal_record["refusalReported"]
                   and refusal_record["documentUnchanged"]
                   and refusal_record["stateAfterCut"] == "ready"
                   and refusal_record["saveStillWorks"]),
              outcome=None if refusal_measurable else "NOT_ESTABLISHED",
              observed=refusal_record,
              oracle="a cut whose delete half the profile REFUSES is reported "
                     "to the user with its reason, leaves the saved document "
                     "byte-for-byte what it was, leaves the session `ready`, "
                     "and leaves saving available. Finding 063 was all four "
                     "going wrong at once: the refusal was swallowed, the "
                     "session went to recoverable-error, and the only thing "
                     "the user saw was a notice telling them to discard "
                     "unsaved work -- over an action that had dispatched "
                     "nothing",
              notEstablished="anything, unless --refusal-diagnostic mirrored a "
                             "manifest that withholds the delete. On the "
                             "shipped profile the gesture is granted and the "
                             "cut succeeds, so there is no refusal to judge "
                             "and this check must abstain rather than pass on "
                             "an empty precondition. Also not established when "
                             "clipboardGranted is false: the copy half is "
                             "denied by the driver and the delete half never "
                             "runs")


        # --------------- the other three inline formats, and clear-format
        #
        # Until 2026-08-21 exactly ONE of the four inline formats was driven
        # through the product (set-bold), and it was checked against
        # `aria-pressed` -- the page's own cache of what the engine told it.
        # The 2026-08-19 relink's entire payload was making underline and
        # strikethrough REACH that cache so they could be toggled off, and
        # nothing had pressed either button since.  An engine field nobody
        # forwards does not exist (handoff section 4), and the same afternoon
        # proved it twice.
        #
        # The oracle here is the SAVED DOCUMENT, not the cache, because the
        # cache being wrong IS the defect class this is looking for.  And it is
        # a marker, not the paragraph: at a collapsed caret an inline format
        # leaves <office:body> byte-identical (matrix, amended 2026-08-15), so
        # the format shows only in text committed afterwards.
        #
        # Both directions for every format.  On-only is what let the toggle bug
        # live for weeks.
        formats_record: dict = {"arms": [], "clear": {}}
        inline_ok = True

        def format_arm(action: str, marker: str, turn_on: bool,
                       normalise: bool = True) -> None:
            """Press one format button, commit a marker under it, AND SAVE.

            EACH ARM GETS ITS OWN PARAGRAPH, and that is not tidiness.  The
            first version committed every marker at the same caret, so all six
            coalesced into ONE text run -- and a format press on a collapsed
            caret inside a run restyles that run, so each press rewrote the
            markers before it.  The saved document came back with all six
            markers in a single <text:span> whose style said
            fo:font-style="normal", style:text-underline-style="none",
            style:text-line-through-style="none" -- the LAST arm's state,
            applied retroactively to all of them.  Measured 2026-08-21; the
            explicit "none" values are what gave it away, since absence of
            formatting does not spell itself out.

            AND THEN THE ISOLATION DEVICE BECAME THE SECOND VERSION OF THE TRAP.
            Finding 064 was filed the same day from this sequence: all eight
            arms reporting no format at all.  They were wrong.  Every arm is
            correct AT THE MOMENT ITS MARKER IS TYPED -- measured, eight for
            eight, findings/evidence/064/ -- and the NEXT arm's opening
            `insert-paragraph-break` lands exactly where it takes the previous
            marker's formatting away (finding 065).  Reading all eight verdicts
            from one save at the end therefore reported eight failures where
            there were none.

            So each arm now takes its OWN save and is judged from it.  Every
            question about a document has a time; a check that takes its oracle
            once at the end has answered about that moment and no other.
            """
            evaluate(session, CLEAR_TOAST)
            # A fresh, empty paragraph: nothing for the format press to
            # restyle, so it can only set the pending state for what is typed.
            #
            # NOT ENOUGH ON ITS OWN, and finding 077 is why.  A new paragraph
            # INHERITS the caret's formatting, so an arm that only breaks the
            # line starts from whatever the rest of the run left behind.  The
            # toolbar is a TOGGLE whose request is derived from the cache
            # (`enabled: formatStateFor(action) !== true`), so one wrong
            # starting value makes the press ask for the OPPOSITE of what this
            # arm wants -- and then leaves the next arm inverted too.  Measured
            # on v5: the very first arm started at `true`, and every bold arm
            # after it failed deterministically while italic, underline and
            # strikethrough passed.  The precondition is established below.
            break_before = revision_of(evaluate(session, READ_STATE))
            evaluate(session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
            wait_for(session,
                     lambda st, floor=break_before: revision_of(st) is not None
                     and floor is not None and revision_of(st) > floor, 20)
            offered = evaluate(
                session,
                "(() => { const b = document.querySelector('#toolbar "
                f"button[data-action=\"{action}\"]'); "
                "return b ? !b.disabled : null; })()")
            evaluate(session, PRESS.replace("ARG_ACTION", action))
            # WAIT ON THE COMPLETION SIGNAL, AND RECORD THE STATE CACHE.
            #
            # Two things, and keeping them apart is the whole lesson of this
            # block. Version one slept 1.5 s and version two waited on
            # `aria-pressed`; the second looked more principled and took v5
            # from 30/2/6 to 22/5/11, because eight of thirteen arms sat out a
            # 20 s timeout and the extra 160 s dragged unrelated checks red.
            #
            # But `aria-pressed` was not a bad INSTRUMENT -- it was a bad WAIT.
            # The v4 control says so: 13 of 13 arms confirmed in ~202 ms, both
            # directions, none of them trivially. On the accessibility core
            # ZERO of thirteen observed a transition. That contrast is finding
            # 077 and it is the only reason this block still reads the
            # attribute.
            #
            # So: wait on `#s-latency`, which the page writes as
            # "<label> NNN ms" after the operation resolves AND
            # renderDocument() completes -- the signal
            # `place_caret_and_settle` already uses. Clear it first, which the
            # arm at `format-a-paragraph-changes-that-paragraph` does not do
            # (it clears only #toast); its arms all press different actions so
            # a stale label has not bitten it, but `format_arm` presses
            # `set-bold` four times, where it would.
            #
            # And read the cache before and after WITHOUT gating on it, so a
            # cache that stops following is visible in every report instead of
            # being something one investigation happened to notice.
            # ESTABLISH THE STARTING STATE. `清除格式` asserts nothing about
            # what was on -- it asks for every inline format OFF -- which is
            # exactly the property needed to normalise from.
            #
            # NOT FOR EVERY ARM, and the first version of this was wrong about
            # that: the last four arms ACCUMULATE, because
            # `clear-format-removes-every-inline-format` needs a document with
            # all four formats on at once, and clearing an already-clear
            # document is a no-op any broken button passes. Normalising each of
            # them took that check from PASS to NOT_ESTABLISHED on v4 -- a
            # regression my own fix introduced, caught by re-running the core
            # that was already green.
            press_label = evaluate(
                session, BUTTON_LABEL.replace("ARG_ACTION", action))
            if normalise:
                evaluate(session, CLEAR_LATENCY)
                evaluate(session, CLEAR_FORMAT)
                wait_for(session,
                         lambda st: "清除格式" in (st.get("latency") or ""), 30)
                # An OFF arm needs the format ON before the press under test,
                # and the only way to turn it on is the same toggle -- which
                # now sends ON, because the cache was just cleared.
                if not turn_on:
                    evaluate(session, CLEAR_LATENCY)
                    evaluate(session, PRESS.replace("ARG_ACTION", action))
                    wait_for(session,
                             lambda st, want=press_label: bool(want)
                             and want in (st.get("latency") or ""), 30)
            state_before = evaluate(
                session, FORMAT_BUTTON_STATE.replace("ARG_ACTION", action))
            # ASSERTED, not assumed: `清除格式` is itself NOT_ESTABLISHED on the
            # accessibility profile, so an arm that trusted it would report a
            # product failure that was really its own setup not taking.
            #
            # An arm that deliberately inherits asserts nothing -- but it says
            # so in the record, so "inherited" and "checked" never look alike.
            precondition_wanted = ("false" if turn_on else "true") if normalise \
                else None
            precondition_ok = (state_before == precondition_wanted
                               if normalise else True)
            evaluate(session, CLEAR_LATENCY)
            evaluate(session, PRESS.replace("ARG_ACTION", action))
            pressed_at = time.monotonic()
            settled = wait_for(
                session,
                lambda st, want=press_label: bool(want)
                and want in (st.get("latency") or ""), 30)
            press_waited_ms = round((time.monotonic() - pressed_at) * 1000)
            press_latency = (settled or {}).get("latency")
            state_after = evaluate(
                session, FORMAT_BUTTON_STATE.replace("ARG_ACTION", action))
            before = revision_of(evaluate(session, READ_STATE))
            evaluate(session, SET_TEXT.replace("ARG_TEXT", marker))
            evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
            wait_for(session,
                     lambda st, floor=before: revision_of(st) is not None
                     and floor is not None and revision_of(st) > floor, 20)
            # This arm's own document, taken before the next arm can disturb
            # it.  `prop` comes from INLINE_ARMS below via the action.
            saved = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
            prop = INLINE_PROPERTY_OF[action]
            style = inline_styles_of(saved, marker)
            arm = {"action": action, "marker": marker, "wanted": turn_on,
                   # The completion signal: null latency means the wait
                   # timed out, which is the case the fixed sleep used to hide.
                   "formatPressLabel": press_label,
                   "formatPressLatency": press_latency,
                   "formatPressWaitedMs": press_waited_ms,
                   # Finding 077. The toolbar's `aria-pressed` comes only from
                   # the engine's broadcast format cache, and the page ALSO
                   # derives the value it dispatches from it
                   # (`enabled: formatStateFor(action) !== true`). So a cache
                   # that stops following is both a wrong ARIA state and a
                   # button that sends the wrong request. Observed, never
                   # waited on.
                   "formatCacheBefore": state_before,
                   "formatCacheAfter": state_after,
                   "normalised": normalise,
                   "preconditionWanted": precondition_wanted,
                   "preconditionEstablished": precondition_ok if normalise
                                              else None,
                   "formatCacheFollowed":
                       state_after == ("true" if turn_on else "false"),
                   "formatCacheMoved": state_after != state_before,
                   "buttonOffered": offered,
                   "toast": evaluate(session, READ_TOAST) or "",
                   "savedIsOdt": is_an_odt(saved),
                   "found": style.get("found"),
                   "styleName": style.get("styleName"),
                   "carrier": style.get("carrier"),
                   # ALL FOUR, not only this arm's own.  clear-format's
                   # precondition is "every format was on at once", and the only
                   # document in which that is true is this arm's own save.
                   "styles": {name: style.get(name)
                              for name in INLINE_FORMAT_PROPERTIES},
                   prop: style.get(prop)}
            # A marker that is not in the document has no opinion about
            # formatting, and `False` is not the honest way to say so.
            # An arm that did not start where it meant to has not tested the
            # product, and `False` is not the honest way to say so.  Same rule
            # as the missing-marker case below it, and the same reason.
            arm["ok"] = (None if not precondition_ok
                         or not arm["savedIsOdt"] or not style.get("found")
                         else style.get(prop) is turn_on)
            if not precondition_ok:
                arm["why"] = (
                    f"the arm needed {action} to start {precondition_wanted} "
                    f"and the toolbar reported {state_before!r} after 清除格式, "
                    f"so the press under test asked for the opposite of what "
                    f"this arm wanted (finding 077)")
            formats_record["arms"].append(arm)

        # A collapsed caret: every one of the four is offered for `collapsed`
        # and for nothing else, so this is the only gesture that can drive them.
        inline_clicks = caret_click_fractions(
            evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
        place_caret_and_settle(session, POINT_AT, inline_clicks["near"], "0.24")

        # Bold is in here too, and deliberately.  `bold-can-be-turned-off-again`
        # is GREEN and checks `aria-pressed` -- the page's own cache of what the
        # engine said.  A cache can be written correctly while the document is
        # never touched, which is precisely finding 064's shape, so bold's
        # document side has never actually been asked.  Measured, not assumed.
        INLINE_ARMS = [("set-bold", "bold", "MKBOLDON", "MKBOLDOFF"),
                       ("set-italic", "italic", "MKITALON", "MKITALOFF"),
                       ("set-underline", "underline", "MKUNDON", "MKUNDOFF"),
                       ("set-strikethrough", "strikethrough",
                        "MKSTRON", "MKSTROFF")]
        INLINE_PROPERTY_OF = {action: prop
                              for action, prop, _on, _off in INLINE_ARMS}
        for action, prop, on_marker, off_marker in INLINE_ARMS:
            format_arm(action, on_marker, True)
            format_arm(action, off_marker, False)

        by_marker = {arm["marker"]: arm for arm in formats_record["arms"]}
        inline_established = True
        for action, prop, on_marker, off_marker in INLINE_ARMS:
            on_arm = by_marker.get(on_marker, {})
            off_arm = by_marker.get(off_marker, {})
            verdict = {"format": prop,
                       "on": {"found": on_arm.get("found"),
                              prop: on_arm.get(prop),
                              "styleName": on_arm.get("styleName")},
                       "off": {"found": off_arm.get("found"),
                               prop: off_arm.get(prop),
                               "styleName": off_arm.get("styleName")},
                       "readFrom": "each arm's own save"}
            verdict["ok"] = (None if on_arm.get("ok") is None
                             or off_arm.get("ok") is None
                             else bool(on_arm["ok"] and off_arm["ok"]))
            if verdict["ok"] is None:
                inline_established = False
            inline_ok = inline_ok and verdict["ok"] is True
            formats_record.setdefault("verdicts", []).append(verdict)

        check("every-inline-format-reaches-the-document",
              bool(inline_ok),
              outcome=None if inline_established else "NOT_ESTABLISHED",
              observed=formats_record,
              oracle="italic, underline and strikethrough are each pressed ON "
                     "and then OFF through the product's own toolbar, and after "
                     "each press a unique marker is committed through the "
                     "product's own insert field. In the SAVED ODT the marker "
                     "typed under the ON press must carry that format's ODF "
                     "property and the one under the OFF press must not. The "
                     "oracle is the document rather than aria-pressed because "
                     "the page's cache being wrong is the defect this looks "
                     "for -- underline and strikethrough only reached that "
                     "cache in the 2026-08-19 relink, and nothing had pressed "
                     "them since. A collapsed caret leaves <office:body> "
                     "byte-identical, so a marker is the only thing that can "
                     "carry the answer. EACH ARM IS READ FROM ITS OWN SAVE, "
                     "taken before the next arm runs: the next arm's opening "
                     "paragraph break takes the previous marker's formatting "
                     "away (finding 065), so one save at the end reports eight "
                     "failures where there are none -- which is what finding "
                     "064 was, and it is retracted")

        # --- listener:click#clear-format ---------------------------------
        #
        # Registered as not-driven since 2026-08-19 with the reason "finding
        # 059 has every one of those failing on the shipped artifact".  059's
        # fix shipped in the 296f3ea7 relink and the tree is on 29ec627b, so
        # that reason was pinned and went red (T0).  This is the path being
        # driven, which is what actually retires it.
        #
        # Turning all four ON first is the point: clearing an already-clear
        # document is a no-op that any broken button passes.
        #
        # Normalised ONCE, here, rather than per arm: the four below have to
        # accumulate, and they need a known floor to accumulate from.
        evaluate(session, CLEAR_LATENCY)
        evaluate(session, CLEAR_FORMAT)
        wait_for(session,
                 lambda st: "清除格式" in (st.get("latency") or ""), 30)
        for action in ("set-bold", "set-italic", "set-underline",
                       "set-strikethrough"):
            format_arm(action, "MKALLON" if action == "set-strikethrough"
                       else f"MKPRE{action[-3:].upper()}", True,
                       normalise=False)
        by_marker = {arm["marker"]: arm for arm in formats_record["arms"]}
        evaluate(session, CLEAR_TOAST)
        cleared_pressed = evaluate(
            session,
            "(() => { const b = document.querySelector('#clear-format'); "
            "if (!b) return null; b.click(); return true; })()")
        time.sleep(2.0)
        clear_toast = evaluate(session, READ_TOAST) or ""
        before_clear_mark = revision_of(evaluate(session, READ_STATE))
        evaluate(session, SET_TEXT.replace("ARG_TEXT", "MKCLEARED"))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
        wait_for(session,
                 lambda st, floor=before_clear_mark: revision_of(st) is not None
                 and floor is not None and revision_of(st) > floor, 20)
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        cleared_saved = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
        all_on = inline_styles_of(cleared_saved, "MKALLON")
        cleared = inline_styles_of(cleared_saved, "MKCLEARED")
        # READ FROM MKALLON'S OWN SAVE, not from the post-clear document.
        # Asking the cleared document whether every format WAS on is asking it
        # about a moment it no longer records: clear-format presses at a
        # collapsed caret restyle the run the caret is in, and MKALLON is in it.
        # The precondition therefore looked unbuildable when it was simply being
        # read too late -- the same mistake, one check over, as finding 064.
        all_on_when_typed = (by_marker.get("MKALLON") or {}).get("styles") or {}
        formats_record["clear"] = {
            "buttonFound": cleared_pressed, "toast": clear_toast,
            "allOnWhenTyped": all_on_when_typed,
            "allOn": {k: all_on.get(k) for k in
                      ("found", "bold", "italic", "underline", "strikethrough")},
            "cleared": {k: cleared.get(k) for k in
                        ("found", "carrier", "bold", "italic", "underline",
                         "strikethrough")},
        }
        every_format_was_on = bool(
            (by_marker.get("MKALLON") or {}).get("found")
            and all(all_on_when_typed.get(k) for k in INLINE_FORMAT_PROPERTIES))
        formats_record["clear"]["everyFormatWasOn"] = every_format_was_on
        check("clear-format-removes-every-inline-format",
              bool(cleared_pressed and every_format_was_on
                   and cleared.get("found")
                   and not any(cleared.get(k) for k in INLINE_FORMAT_PROPERTIES)
                   and is_an_odt(cleared_saved)),
              outcome=None if every_format_was_on else "NOT_ESTABLISHED",
              observed=formats_record["clear"],
              oracle="all four inline formats are turned ON and a marker "
                     "committed under them, the product's own #clear-format "
                     "button is clicked, and a second marker is committed "
                     "after it. The first marker must carry all four in the "
                     "saved ODT and the second must carry none -- clearing an "
                     "already-clear document is a no-op that a broken button "
                     "would pass",
              notEstablished="the four formats were not all ON before the "
                             "clear, so what the button did cannot be read: a "
                             "clear that removes nothing and a clear that "
                             "never ran look identical from here. The "
                             "precondition is read from MKALLON's OWN save "
                             "rather than from the cleared document, because "
                             "asking a cleared document whether every format "
                             "WAS on asks it about a moment it no longer "
                             "records -- which is why this looked unbuildable "
                             "under finding 064, now retracted")

        # ----------------------------------- 065: does it SURVIVE the next key
        #
        # `every-inline-format-reaches-the-document` asks whether the format
        # reaches the text.  It does.  What nothing asked was whether the text
        # KEEPS it, and the two were confused for a whole finding: reading eight
        # arms from one save at the end reported eight failures because each
        # arm's opening paragraph break had taken the previous arm's formatting
        # away.
        #
        # So this asks the surviving question directly, and it is a user's
        # sentence: press B, type, press Enter. One marker, one break, nothing
        # else in between.
        #
        # LAST, deliberately.  Every press here goes through the page's own
        # `editorAction`, which decides `enabled` from the cached format state
        # -- so an arm that leaves bold ON makes the NEXT block's "turn it on"
        # press send `enabled: false`.  Placed before clear-format, this arm did
        # exactly that and knocked out that check's precondition.  Measured, and
        # it is the same lesson as finding 045 from the other side: a toggle
        # read from cache is a sequencing dependency between checks.
        format_arm("set-bold", "MKSURVIVE", True)
        by_marker = {arm["marker"]: arm for arm in formats_record["arms"]}
        survive_before = by_marker.get("MKSURVIVE") or {}
        break_floor = revision_of(evaluate(session, READ_STATE))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
        wait_for(session,
                 lambda st, floor=break_floor: revision_of(st) is not None
                 and floor is not None and revision_of(st) > floor, 20)
        survive_saved = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
        survive_after = inline_styles_of(survive_saved, "MKSURVIVE")
        survive_established = bool(
            survive_before.get("savedIsOdt") and survive_before.get("bold") is True
            and is_an_odt(survive_saved) and survive_after.get("found"))
        formats_record["survivesBreak"] = {
            "boldWhenTyped": survive_before.get("bold"),
            "styleNameWhenTyped": survive_before.get("styleName"),
            "boldAfterBreak": (survive_after.get("bold")
                               if survive_after.get("found") else None),
            "styleNameAfterBreak": survive_after.get("styleName"),
            "carrierAfterBreak": survive_after.get("carrier"),
            "spansAfterBreak": (survive_saved.get("content") or "").count(
                "<text:span"),
        }
        check("formatting-survives-the-next-paragraph-break",
              bool(survive_established and survive_after.get("bold") is True),
              outcome=None if survive_established else "NOT_ESTABLISHED",
              observed=formats_record["survivesBreak"],
              oracle="a marker typed under a bold press is bold in ITS OWN "
                     "save, and is STILL bold in a save taken after one "
                     "insert-paragraph-break and nothing else. The precondition "
                     "is half the check: a marker that was never bold cannot "
                     "show that it stopped being bold, and that arm reports "
                     "NOT_ESTABLISHED rather than a failure. Finding 065")

        # AFTER 065, and that placement is load-bearing.
        #
        # This arm ends with bold ON (it presses the button and types under it),
        # and the page decides `enabled` from the cached format state -- so a
        # check that runs next and means to turn bold ON sends `enabled: false`
        # instead.  Placed before 065, it did exactly that and knocked out that
        # check's precondition: NOT_ESTABLISHED, measured 2026-08-22.
        #
        # That is the SECOND time this trap has been sprung in this file in two
        # days, the first being this same 065 arm against clear-format.  A
        # toggle read from a cache is an ordering dependency between checks, and
        # the comment saying so was already here when it happened again.
        # ------------------- 066: does the toolbar give the keyboard back?
        #
        # An operator reported this on 2026-08-22 and nothing automated in this
        # tree could have: EVERY keyboard helper here opens with `sink.focus()`,
        # handing back the focus a user can only recover by clicking the canvas
        # -- and that click moves the caret and discards the inline format they
        # just set.  The harness was papering over the defect on every run.
        #
        # A REAL click is required and `button.click()` will not do:
        # `HTMLElement.click()` runs no default action, so it never moves focus
        # and this check would pass on a broken page.  CDP only, therefore
        # CHROME only, and Firefox reports NOT_ESTABLISHED rather than a pass.
        focus_record: dict = {}
        cdp = getattr(session, "call", None)
        if cdp is None:
            focus_record["why"] = ("this browser session has no CDP, so a real "
                                   "click cannot be delivered")
        else:
            place_caret_and_settle(session, POINT_AT, inline_clicks["near"], "0.24")
            focus_record["afterCanvasClick"] = evaluate(session, READ_FOCUS)
            box = evaluate(session, BUTTON_BOX.replace(
                "ARG_SELECTOR", '#toolbar button[data-action="set-bold"]'))
            if not box:
                focus_record["why"] = "the set-bold button has no box to click"
            else:
                for kind in ("mousePressed", "mouseReleased"):
                    cdp("Input.dispatchMouseEvent",
                        {"type": kind, "x": box["x"], "y": box["y"],
                         "button": "left", "clickCount": 1})
                time.sleep(1.5)
                focus_record["afterButtonClick"] = evaluate(session, READ_FOCUS)
                before_focus_type = revision_of(evaluate(session, READ_STATE))
                focus_record["dispatch"] = evaluate(
                    session,
                    TYPE_WHEREVER_FOCUS_IS.replace("ARG_TEXT", "MKFOCUS"))
                settled = wait_for(
                    session,
                    lambda st, floor=before_focus_type: revision_of(st) is not None
                    and floor is not None and revision_of(st) > floor, 12)
                focus_record["revision"] = {"before": before_focus_type,
                                            "after": revision_of(settled)}
                focus_saved = capture_save(
                    session, evaluate(session, SAVE_COUNT) or 0)
                focus_record["savedIsOdt"] = is_an_odt(focus_saved)
                focus_record["markerInDocument"] = (
                    "MKFOCUS" in ((focus_saved or {}).get("content") or ""))
        focus_measurable = bool(
            focus_record.get("afterButtonClick") and focus_record.get("savedIsOdt"))
        check("the-toolbar-gives-the-keyboard-back",
              bool(focus_measurable
                   and (focus_record.get("afterButtonClick") or {}).get("id") == "sink"
                   and focus_record.get("markerInDocument")),
              outcome=None if focus_measurable else "NOT_ESTABLISHED",
              observed=focus_record,
              oracle="after a REAL mouse click on a style button, "
                     "document.activeElement is still the editing sink, AND "
                     "text typed straight afterwards -- with nothing restoring "
                     "focus -- reaches the saved document. Finding 066: it used "
                     "to be the button, so typing went nowhere, and the canvas "
                     "click needed to recover moved the caret and discarded the "
                     "format",
              notEstablished="anything, on a browser without CDP. A real click "
                             "is the whole point: HTMLElement.click() runs no "
                             "default action and never moves focus, so a "
                             "synthetic press would pass this on a page where "
                             "it is broken")

        # ------------- the five caret and edit BUTTONS nobody had pressed
        #
        # delete-backward, delete-forward, insert-line-break,
        # move-character-left and move-character-right all had a toolbar button
        # and no automated round.  `backspace-and-arrows-reach-the-document`
        # drives the KEYBOARD path (beforeinput); these are the buttons, and
        # this tree has been bitten five times by "the button is there, nobody
        # pressed it" (049, 050, 053, 054, 063).
        #
        # One paragraph, one save, five actions -- and the sequence is built so
        # that EACH action failing produces a DIFFERENT final string, so a green
        # cannot be bought by any one of them being a no-op:
        #
        #   type ABCDEFG            ABCDEFG
        #   delete-backward x2      ABCDE      (no-op -> ABCDEFG...)
        #   move-character-left x2  caret after C
        #   insert X                ABCXDE     (left no-op -> ABCDEX)
        #   move-character-right    caret after D
        #   delete-forward          ABCXD      (right no-op -> ABCXE;
        #                                       forward no-op -> ABCXDE)
        #   insert-line-break                  (no-op -> no <text:line-break/>)
        edit_record: dict = {"steps": []}

        def edit_press(action: str, times: int = 1) -> None:
            for _ in range(times):
                before = revision_of(evaluate(session, READ_STATE))
                evaluate(session, CLEAR_TOAST)
                evaluate(session, PRESS.replace("ARG_ACTION", action))
                moved = wait_for(
                    session,
                    lambda st, floor=before: revision_of(st) is not None
                    and floor is not None and revision_of(st) > floor, 12)
                edit_record["steps"].append(
                    {"action": action,
                     "revisionBefore": before,
                     "revisionAfter": revision_of(moved),
                     "toast": evaluate(session, READ_TOAST) or ""})

        def edit_type(text: str) -> None:
            before = revision_of(evaluate(session, READ_STATE))
            evaluate(session, SET_TEXT.replace("ARG_TEXT", text))
            evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
            wait_for(session,
                     lambda st, floor=before: revision_of(st) is not None
                     and floor is not None and revision_of(st) > floor, 20)
            edit_record["steps"].append({"action": "insert-text", "text": text})

        # Break at the END of a line, so the new paragraph starts EMPTY.
        #
        # First run broke mid-paragraph and the remainder came along: the
        # paragraph read EDITBTNABCXD + "LC-NUMBER-ONE".  Relaxing the oracle to
        # startswith() would have destroyed the separability this sequence is
        # built on -- a delete-forward no-op yields EDITBTNABCXDE..., which
        # still starts with the wanted string.  So the SETUP is fixed instead of
        # the assertion.  (Do not widen a check to close a row.)
        edit_clicks = caret_click_fractions(
            evaluate(session, LINE_INK.replace("ARG_Y", "0.28")) or {})
        place_caret_and_settle(session, POINT_AT, edit_clicks["past"], "0.28")
        edit_record["brokeAtLineEnd"] = edit_clicks.get("derived")
        edit_press("insert-paragraph-break")
        edit_type("EDITBTNABCDEFG")
        edit_press("delete-backward", 2)
        edit_press("move-character-left", 2)
        edit_type("X")
        edit_press("move-character-right")
        edit_press("delete-forward")
        edit_press("insert-line-break")
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        edit_saved = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
        edit_texts = [line["text"] for line in document_lines(edit_saved)]
        edit_record["wanted"] = "EDITBTNABCXD"
        edit_record["paragraphWithMarker"] = next(
            (t for t in edit_texts if "EDITBTN" in t), None)
        # `move-character-*` produce no revision of their own on some builds --
        # recorded rather than asserted, because the VERDICT is the document.
        edit_record["revisionSilentActions"] = [
            step["action"] for step in edit_record["steps"]
            if step.get("revisionAfter") is not None
            and step.get("revisionBefore") == step.get("revisionAfter")]
        edit_record["hasLineBreak"] = "<text:line-break/>" in (
            edit_saved.get("content") or "")
        check("the-edit-buttons-do-what-they-say",
              bool(edit_record["paragraphWithMarker"] == "EDITBTNABCXD"
                   and edit_record["hasLineBreak"]
                   and is_an_odt(edit_saved)),
              observed=edit_record,
              oracle="delete-backward, delete-forward, insert-line-break and "
                     "move-character-left/right are pressed as BUTTONS, in a "
                     "sequence where each one being a no-op yields a different "
                     "final string: ABCDEFG -> delete-backward x2 -> "
                     "move-left x2 -> insert X -> move-right -> delete-forward "
                     "must leave exactly EDITBTNABCXD, and insert-line-break "
                     "must put a <text:line-break/> in the saved ODT. The "
                     "keyboard path is a different check; this is the toolbar, "
                     "which no round had ever pressed")

        # --- listener:click#open-file -------------------------------------
        #
        # Registered as uncovered with "it opens the OS file chooser, which no
        # driver here can operate".  That is true of #file, and NOT true of the
        # path: the listener is one line that forwards to #file.click(), and
        # the runner already shims a .click() to COUNT it instead of performing
        # it (HTMLAnchorElement, for download anchors).  Driving the forwarding
        # needs no chooser and no human; what still needs a human is the
        # chooser itself, and `listener:change#file` already covers what comes
        # back from it.  The first draft of this plan proposed waiving this,
        # which would have closed the row without walking the path.
        forwarded = evaluate(session, """(() => {
const file = document.querySelector('#file');
const button = document.querySelector('#open-file');
if (!file || !button) return { available: false };
const native = file.click;
let calls = 0;
file.click = function () { calls += 1; };       // counted, never performed
button.click();
const afterButton = calls;
file.click = native;
return { available: true, afterButton };
})()""") or {}
        edit_record["openFileForwarding"] = forwarded
        check("the-open-button-opens-the-file-chooser",
              bool(forwarded.get("available") and forwarded.get("afterButton") == 1),
              outcome=None if forwarded.get("available") else "NOT_ESTABLISHED",
              observed=forwarded,
              oracle="clicking the product's own #open-file button forwards "
                     "exactly one click to the hidden #file input. The click is "
                     "shimmed to be counted rather than performed, so no OS "
                     "chooser opens and no human is needed -- the same "
                     "technique this runner already uses for download anchors. "
                     "What the chooser hands back is listener:change#file's "
                     "job and is checked separately",
              notEstablished="#open-file or #file is not in the page at all")


        # ------------- the three listeners that abort or relayout a gesture
        #
        # pointercancel and blur both call endDrag(null); resize relayouts and
        # re-renders.  None had ever been driven.  The observable for the first
        # two is the product's OWN state projection: pumpDrag() sets
        # lastSelectionShape and calls updateGestureAffordance(), which disables
        # the four inline-format buttons on a range because they are declared
        # collapsed-only.  So "did the drag really stop" can be read from the
        # toolbar without reaching into a module-local variable.
        def format_buttons_disabled() -> bool | None:
            state = evaluate(session, READ_STATE) or {}
            flags = [b.get("disabled") for b in (state.get("buttons") or [])
                     if b.get("action") in ("set-bold", "set-italic",
                                            "set-underline", "set-strikethrough")]
            return all(flags) if flags else None

        def abort_arm(kind: str | None) -> dict:
            """Drag across a line, maybe aborting mid-gesture, and see if it selected.

            `kind=None` is the POSITIVE CONTROL and it is the whole reason this
            check means anything.  Measured 2026-08-21: without it, the
            `gesture-abort-not-wired` mutation -- which unwires pointercancel
            entirely -- left this check GREEN, because the drag had never
            started and a selection that never extended proved nothing. That is
            "unreachable rather than untested, and it looks green" (handoff
            section 5), walked into on the same day it was quoted.
            """
            # Coordinates from stable_bands, the SAME derivation the copy and
            # cut drags use.  Three shapes derived from LINE_INK and viewport
            # fractions were tried first and none of them extended the
            # selection on ANY arm, control included -- so the check could only
            # abstain.  Reuse of a gesture already proven to select beats a
            # fourth guess at coordinates.
            scan_a, bands_a = stable_bands(session)
            band = next((b for b in bands_a
                         if (b["last"] - b["first"]) > 40), None)
            if band is None or not scan_a.get("width"):
                return {"kind": kind or "no-abort (control)",
                        "aborted": kind is not None,
                        "formatButtonsDisabledBefore": None,
                        "formatButtonsDisabledAfterAbortAndMove": None,
                        "why": "no text band wide enough to drag across"}
            width = scan_a["width"]
            x1 = f"{max(0.0, (band['first'] + 2) / width):.5f}"
            x2 = f"{((band['first'] + band['last']) / 2) / width:.5f}"
            y = f"{band['centreFraction']:.5f}"
            place_caret_and_settle(session, POINT_AT, x1, y)
            time.sleep(0.8)
            before = format_buttons_disabled()
            evaluate(session, ABORT_DRAG
                     .replace("ARG_X1", x1).replace("ARG_X2", x2)
                     .replace("ARG_Y", y)
                     .replace("ARG_KIND", kind or "none"))
            # Poll, do not sleep: selectRange queues behind the placeCaret that
            # pointerdown itself starts.
            deadline = time.monotonic() + 20
            after = format_buttons_disabled()
            while after is not True and time.monotonic() < deadline:
                time.sleep(0.5)
                after = format_buttons_disabled()
            return {"kind": kind or "no-abort (control)",
                    "aborted": kind is not None,
                    "formatButtonsDisabledBefore": before,
                    "formatButtonsDisabledAfterAbortAndMove": after}

        control = abort_arm(None)
        aborts = [abort_arm("pointercancel"), abort_arm("blur")]
        # The control must show a drag EXTENDING the selection, or nothing
        # below is evidence about aborting one.
        drag_reaches = control["formatButtonsDisabledAfterAbortAndMove"] is True
        check("an-aborted-gesture-stops-selecting",
              bool(drag_reaches
                   and all(a["formatButtonsDisabledBefore"] is False
                           and a["formatButtonsDisabledAfterAbortAndMove"] is False
                           for a in aborts)),
              outcome=None if drag_reaches else "NOT_ESTABLISHED",
              observed={"control": control, "arms": aborts},
              oracle="a drag is started, then aborted by pointercancel (and "
                     "separately by window blur), then the pointer keeps "
                     "moving. The selection must NOT extend -- read through the "
                     "product's own affordance, since the four inline-format "
                     "buttons are collapsed-only and go disabled the moment a "
                     "range exists. Both listeners call endDrag(null) and "
                     "neither had ever been driven",
              notEstablished="the control arm -- a drag with NO abort -- did "
                             "not extend the selection, so this harness cannot "
                             "start a drag here and an abort that stops one "
                             "proves nothing. Without this clause the check "
                             "passed even with pointercancel unwired entirely")

        # MOVED HERE, LATE, AND THE REASON IS THE FIRST RUNS.
        #
        # This check types 36 characters into the fixture, and everything from
        # the format checks through the aborted-gesture one aims by BAND INDEX
        # on that same document. Sitting among them it changed the line count
        # -- measured: `ctrl-x` saw 9 bands one round and 8 the next, so its
        # drag selected nothing and it reported CLIPBOARD_EMPTY_SELECTION.
        # Intermittently, which is how it was nearly attributed to something
        # else entirely.
        #
        # Nothing after this point aims by band on the pristine fixture: the
        # next check resizes the desk, and the one after opens another
        # document.
        # ------------------- 068: does the caret follow the text you type?
        #
        # READ FROM THE SINK, not from pixels. Finding 069 put the hidden input
        # sink on the caret (it has to be there, or an IME's candidate window
        # opens somewhere else and composition scrolls the page), so the page
        # now publishes the caret's position in the DOM as `#sink`'s offset.
        #
        # LIMIT, stated because it is the whole shape of this check: this reads
        # the position the page DRAWS FROM, not the pixels it drew. A page that
        # computed the right position and painted nothing would pass. Whether a
        # caret is drawn at all is the OTHER check above; this one is about
        # whether the position keeps up.
        #
        # THREE ROUNDS, and that is not thoroughness for its own sake. Before
        # the fix this defect was intermittent at 2/7 -- the page's snapshot was
        # refreshed once per queued operation and the cursor callback landed
        # one sequence later, so whether the caret was current depended on which
        # side of that race the read fell. A single round would report green
        # about a fifth of the time.
        caret_typing = {"rounds": [], "line": "0.28"}
        typing_clicks = caret_click_fractions(
            evaluate(session, LINE_INK.replace("ARG_Y", caret_typing["line"]))
            or {})
        # The control for the INSTRUMENT: the sink must track the caret at all.
        # Without it, a sink pinned at 0,0 reports "never moved" for every round
        # and the check fails for a reason that has nothing to do with typing.
        place_caret_and_settle(session, POINT_AT, typing_clicks["near"],
                               caret_typing["line"])
        time.sleep(0.8)
        caret_typing["sinkAtLineStart"] = evaluate(session, SINK_POSITION) or {}
        place_caret_and_settle(session, POINT_AT, typing_clicks["past"],
                               caret_typing["line"])
        time.sleep(0.8)
        caret_typing["sinkAtLineEnd"] = evaluate(session, SINK_POSITION) or {}
        start_left = (caret_typing["sinkAtLineStart"] or {}).get("left")
        end_left = (caret_typing["sinkAtLineEnd"] or {}).get("left")
        caret_typing["sinkTracksTheCaret"] = (
            start_left is not None and end_left is not None
            and end_left > start_left)

        for index in range(3):
            mark = f"CARETFOLLOW{index}"
            before = evaluate(session, SINK_POSITION) or {}
            before_left, before_top = before.get("left"), before.get("top")
            floor = revision_of(evaluate(session, READ_STATE))
            evaluate(session, COMPOSE.replace("ARG_TEXT", mark))
            landed = wait_for(session,
                              lambda s, f=floor: revision_of(s) is not None
                              and f is not None and revision_of(s) > f, 25)
            time.sleep(1.2)
            after = evaluate(session, SINK_POSITION) or {}
            after_left, after_top = after.get("left"), after.get("top")
            # FORWARD IN READING ORDER, not "further right".
            #
            # The first version of this check asked for a larger `left`, and
            # round 1 failed with 617 -> 296. That was not the caret failing to
            # follow: the typing WRAPPED, so the caret moved onto the next line
            # and legitimately went left. A caret that wrapped is ahead of where
            # it was, and an oracle that cannot say so is wrong about the
            # product rather than the other way round.
            moved = (before_left is not None and after_left is not None
                     and before_top is not None and after_top is not None
                     and (after_top > before_top
                          or (after_top == before_top
                              and after_left > before_left)))
            caret_typing["rounds"].append({
                "round": index, "mark": mark,
                "leftBefore": before_left, "leftAfter": after_left,
                "topBefore": before_top, "topAfter": after_top,
                "wrapped": (before_top is not None and after_top is not None
                            and after_top > before_top),
                "revisionAdvanced": revision_of(landed) != floor,
                "moved": moved,
            })

        typed_rounds = [r for r in caret_typing["rounds"]
                        if r["revisionAdvanced"]]
        caret_typing["roundsThatReachedTheDocument"] = len(typed_rounds)
        check("caret-follows-the-text-you-type",
              bool(typed_rounds) and all(r["moved"] for r in typed_rounds),
              outcome=None if (caret_typing["sinkTracksTheCaret"]
                               and len(typed_rounds) == 3)
              else "NOT_ESTABLISHED",
              observed=caret_typing,
              oracle="typing moves the caret FORWARD IN READING ORDER -- "
                     "further right on the same line, or onto a lower one if "
                     "the text wrapped -- three times out of three. Read from "
                     "`#sink`'s offset, "
                     "which finding 069 pinned to the caret, so this is the "
                     "position the page draws from. LIMIT: it is not the "
                     "pixels -- a page that computed the right position and "
                     "painted nothing would pass here and fail "
                     "`the-caret-is-drawn-where-it-was-placed`",
              notEstablished="either the sink does not track the caret at all "
                             "(so 'it did not move' says nothing about typing) "
                             "or fewer than three rounds reached the document. "
                             "Three is not thoroughness: before the fix this "
                             "defect was intermittent at 2/7, and a single "
                             "round would report green about a fifth of the "
                             "time")

        # ----------------------------------------- the OTHER four arrow keys
        #
        # Added 2026-08-22, and the reason it did not exist until now is the
        # point of it.  The acceptance row for line movement sat at `blocked`
        # ("needs a relink") through the ABI 4 link and then read as done,
        # because `arrow-keys-match-the-profile` was PASSing -- but every file
        # under findings/evidence/arrow-keys/ was run against `e2-editor-v3`,
        # where `move-line-up` is FALSE, and that arm asserts AGREEMENT with the
        # running profile.  On v3 the agreeing behaviour is "the key does
        # nothing".  The same green means the opposite thing on v4, and nobody
        # had re-run it.  Meanwhile `backspace-and-arrows-reach-the-document`
        # drives only the LEFT arrow.
        #
        # So four of the six arrows were shipped, believed to work, and driven
        # by nothing.  This is the tree's own rule arriving from a new
        # direction: a check that is green when the thing it checks is turned
        # OFF carries no information, and reading its verdict without reading
        # which artifact it ran on is how that goes unnoticed.
        #
        # READ FROM THE SINK, like caret-follows above: finding 069 pinned it to
        # the caret, so the caret's position is a DOM observable.  Same stated
        # limit -- this is the position the page draws FROM, not the pixels.
        #
        # LAST, and after everything that aims by band index: it moves the caret
        # around without typing, but the caret is ink and ink is what the band
        # scan reads.
        arrows: dict = {"line": "0.28", "presses": []}
        arrow_cdp = getattr(session, "call", None)
        vertical = ["move-line-up", "move-line-down",
                    "move-line-home", "move-line-end"]
        arrow_offers = offered_actions(root, vertical)
        arrows["offered"] = arrow_offers
        arrows["allOffered"] = bool(arrow_offers) and all(
            arrow_offers.get(name) is True for name in vertical)
        if arrow_cdp is None or not arrows["allOffered"]:
            check("the-vertical-arrows-move-the-caret", False,
                  outcome="NOT_ESTABLISHED", observed=arrows,
                  why="no CDP (so a real key cannot be delivered), or this "
                      "profile does not offer the four line-movement actions. "
                      "On a profile without them the page deliberately leaves "
                      "those keys to the browser, and "
                      "`arrow-keys-match-the-profile` is the arm that checks "
                      "THAT",
                  oracle="see the established branch")
        else:
            arrow_clicks = caret_click_fractions(
                evaluate(session, LINE_INK.replace("ARG_Y", arrows["line"]))
                or {})
            place_caret_and_settle(session, POINT_AT, arrow_clicks["near"],
                                   arrows["line"])
            time.sleep(0.8)

            def arrow(key, code, vk):
                before = evaluate(session, SINK_POSITION) or {}
                evaluate(session, INSTALL_KEY_TAKEN)
                for kind in ("rawKeyDown", "keyUp"):
                    arrow_cdp("Input.dispatchKeyEvent",
                              {"type": kind, "key": key, "code": code,
                               "windowsVirtualKeyCode": vk,
                               "nativeVirtualKeyCode": vk})
                time.sleep(1.2)
                after = evaluate(session, SINK_POSITION) or {}
                taken = evaluate(session, READ_KEY_TAKEN) or []
                record = {"key": key,
                          "leftBefore": before.get("left"),
                          "leftAfter": after.get("left"),
                          "topBefore": before.get("top"),
                          "topAfter": after.get("top"),
                          # THE INSTRUMENT'S OWN CONTROL, and it is not
                          # optional here: a key the page never took is
                          # indistinguishable from one it took and could not
                          # act on, and both look like "the caret did not
                          # move".  Measured on v3, where ArrowUp came back
                          # defaultPrevented FALSE and no error was shown.
                          "takenByThePage": [k.get("defaultPrevented")
                                             for k in taken
                                             if k.get("key") == key]}
                arrows["presses"].append(record)
                return record

            # End then Home, on one line, so the horizontal pair is judged
            # without a vertical move in between; then Down and Up, which must
            # be inverses of each other.
            to_end = arrow("End", "End", 35)
            to_home = arrow("Home", "Home", 36)
            down = arrow("ArrowDown", "ArrowDown", 40)
            up = arrow("ArrowUp", "ArrowUp", 38)

            def moved(record, axis, direction):
                a, b = record[f"{axis}Before"], record[f"{axis}After"]
                if a is None or b is None:
                    return False
                return b > a if direction > 0 else b < a

            arrows["endWentRight"] = moved(to_end, "left", +1)
            arrows["homeWentLeft"] = moved(to_home, "left", -1)
            arrows["downWentLower"] = moved(down, "top", +1)
            arrows["upWentBack"] = moved(up, "top", -1)
            # Inverses, not just "each moved something".  A pair that both
            # travel the same way is two broken keys that each pass a
            # "did it move" test.
            #
            # AND THIS ONE IS VACUOUSLY TRUE WHEN NOTHING HAPPENS -- measured,
            # not foreseen: under `line-movement-keys-unbound` both presses
            # leave the caret at row 250, so `up.topAfter == down.topBefore`
            # holds and this reads green while all four keys are dead.  It is
            # carried by the conjunction below (`downWentLower` is False there),
            # so the check still fails -- but a predicate that a page doing
            # NOTHING satisfies is the shape this tree keeps being bitten by,
            # and it is written down rather than left to hold by luck.
            arrows["downAndUpAreInverses"] = (
                down.get("topAfter") is not None
                and up.get("topAfter") == down.get("topBefore"))
            arrows["everyKeyWasTaken"] = all(
                bool(r["takenByThePage"]) and all(r["takenByThePage"])
                for r in arrows["presses"])
            check("the-vertical-arrows-move-the-caret",
                  bool(arrows["endWentRight"] and arrows["homeWentLeft"]
                       and arrows["downWentLower"] and arrows["upWentBack"]
                       and arrows["downAndUpAreInverses"]
                       and arrows["everyKeyWasTaken"]),
                  observed=arrows,
                  oracle="End moves the caret right along its line and Home "
                         "moves it back left; ArrowDown moves it onto a lower "
                         "line and ArrowUp returns it to exactly the row it "
                         "started on -- inverses, not merely both moving, "
                         "because two keys travelling the same way each pass a "
                         "'did it move' test. Every one of the four must also "
                         "come back `defaultPrevented`: a key the page never "
                         "took looks exactly like one it took and could not "
                         "act on. LIMIT: read from `#sink`, so this is the "
                         "position the page draws FROM, not the pixels it drew")

        # -------------------------------- what you are part way through typing
        #
        # FINDING 073, reported by an operator using 新酷音 on 2026-08-22: the
        # bopomofo is invisible.  The sink is one transparent pixel by design
        # and the browser draws an IME's PREEDIT inside it, so a user composing
        # 台 sees nothing at all until the character commits.
        #
        # THIS ARM EXISTS BECAUSE IT TURNED OUT NOT TO BE HUMAN-ONLY.  A real
        # input method cannot be driven from here -- that is D5 by definition,
        # and `every-ime-commit-reaches-the-document` above uses a synthetic
        # composition for the COMMIT path.  But CDP's `Input.imeSetComposition`
        # drives the renderer's own IME path, which is what fires
        # compositionstart/update on the focused element.  So the question "can
        # the user see what they are typing" has an instrument after all, and
        # the operator does not have to be the regression net.
        #
        # BOTH ENDS ARE CHECKED.  A sink that becomes visible and stays visible
        # is a box of stale text sitting on top of the document, which is worse
        # than the defect: the user would have to reload to get their page back.
        composing: dict = {}
        comp_cdp = getattr(session, "call", None)
        if comp_cdp is None:
            check("the-composition-you-are-typing-is-visible", False,
                  outcome="NOT_ESTABLISHED", observed=composing,
                  why="no CDP, so `Input.imeSetComposition` cannot be sent and "
                      "no composition can be started at all",
                  oracle="see the established branch")
        else:
            comp_clicks = caret_click_fractions(
                evaluate(session, LINE_INK.replace("ARG_Y", "0.28")) or {})
            place_caret_and_settle(session, POINT_AT, comp_clicks["near"], "0.28")
            time.sleep(0.8)
            composing["atRest"] = evaluate(session, SINK_APPEARANCE) or {}
            # Bopomofo, because that is what the operator was typing and because
            # a Latin preedit would be narrow enough to hide inside the
            # resting box's own width.
            preedit = "ㄊㄞˊ"
            try:
                comp_cdp("Input.imeSetComposition",
                         {"text": preedit, "selectionStart": len(preedit),
                          "selectionEnd": len(preedit)})
                composing["sent"] = True
            except Exception as error:            # noqa: BLE001
                composing["sent"] = False
                composing["error"] = repr(error)
            time.sleep(1.0)
            composing["whileComposing"] = evaluate(session, SINK_APPEARANCE) or {}
            # Cancelled rather than committed: this arm is about what is VISIBLE
            # during composition, and committing would put text in the document
            # and make it about the commit path, which is another check's job.
            try:
                comp_cdp("Input.imeSetComposition",
                         {"text": "", "selectionStart": 0, "selectionEnd": 0})
            except Exception:                     # noqa: BLE001
                pass
            time.sleep(1.0)
            composing["afterwards"] = evaluate(session, SINK_APPEARANCE) or {}

            rest = composing["atRest"]
            during = composing["whileComposing"]
            after = composing["afterwards"]
            # THE POSITIVE CONTROL, and without it this whole arm is worthless:
            # if the composition never started, the sink is invisible for a
            # reason that has nothing to do with the product, and "invisible"
            # would read as the defect.
            composing["compositionActuallyStarted"] = bool(
                during.get("composing") or during.get("value"))
            composing["visibleWhileComposing"] = (
                during.get("opacity", 0) > 0 and during.get("width", 0) > 2)
            composing["wideEnoughToRead"] = during.get("width", 0) >= 14
            # AT THE CARET, not merely somewhere.  A visible box in the corner
            # of the page is not the user seeing what they type.
            composing["stayedAtTheCaret"] = (
                rest.get("left") is not None
                and during.get("left") == rest.get("left")
                and during.get("top") == rest.get("top"))
            composing["hiddenAgainAfterwards"] = (
                after.get("opacity", 1) == 0 and after.get("width", 99) <= 2)
            check("the-composition-you-are-typing-is-visible",
                  bool(composing["visibleWhileComposing"]
                       and composing["wideEnoughToRead"]
                       and composing["stayedAtTheCaret"]
                       and composing["hiddenAgainAfterwards"]),
                  outcome=None if composing["compositionActuallyStarted"]
                  else "NOT_ESTABLISHED",
                  observed=composing,
                  oracle="while an IME is composing, the sink is visible, wide "
                         "enough to read, and still at the caret -- and it is "
                         "back to one transparent pixel when the composition "
                         "ends. Both halves: a sink that becomes visible and "
                         "stays visible is a box of stale text on top of the "
                         "document, which is worse than not seeing the preedit",
                  notEstablished="that the composition started at all. `Input."
                                 "imeSetComposition` reached the renderer but "
                                 "nothing composed, so an invisible sink says "
                                 "nothing about the product -- it is the "
                                 "instrument, not the page")

        # ------------------------------------ roadmap 3.4, the honesty half
        #
        # THIS RUN IS ON THE SHIPPED PROFILE, which does not carry the focused
        # paragraph's text, so the reading half of the projection cannot be
        # measured here -- that lives in `probe_aria_projection.py` against a
        # profile that does. What CAN be measured here, and matters more on the
        # product, is that the document region SAYS SO instead of standing
        # empty.
        #
        # An empty region announces to a screen reader as "document, blank",
        # which is a confident wrong answer about the user's own file. The
        # engine already refuses that shape one layer down by reporting
        # `core-built-without-accessibility` rather than `enabled: true`, and
        # this is the same rule at the top of the stack.
        projection = evaluate(session, READ_A11Y_REGION) or {}
        # REWRITTEN 2026-08-23, and the reason is worth keeping: the first
        # version asserted `offers == "0"` and `reason == "profile"` -- it was
        # written when NO profile could project a paragraph, so "the region
        # explains its emptiness" and "the region says the engine cannot do
        # this" were the same sentence. e2-editor-v5 declares
        # `caretParagraphText`, and the check went red on a profile that had
        # just started doing the very thing the region is for. It was pinned to
        # a remedy, not to a property.
        #
        # The property is that the region is NEVER SILENTLY EMPTY: a screen
        # reader reads an empty document region as a blank document, and the
        # user cannot tell that apart from a file that lost its contents. That
        # holds on every profile; only the sentence changes.
        #
        # Whether the projected TEXT is the right paragraph is not asked here
        # and deliberately so -- the only comparison available at this point in
        # the run is the page against itself, and the document has been edited
        # since it was opened. That property lives in G3.4-3
        # (`probe_aria_projection.py`), which compares against the fixture's own
        # XML on a pristine document.
        reason = projection.get("reason")
        offers = projection.get("offers")
        text = (projection.get("text") or "").strip()
        known = {"paragraph", "profile", "noDocument", "noParagraph",
                 "disabled", "stale", "noText"}
        consistent = (
            (reason in ("profile", "noDocument")) if offers == "0"
            else (reason != "profile") if offers == "1"
            else False)
        check("the-document-region-says-why-it-is-empty",
              bool(projection.get("present") and text
                   and reason in known and consistent),
              observed=projection,
              oracle="the accessibility region always carries something to "
                     "read: the focused paragraph on a profile that offers "
                     "one, and a sentence naming the cause on a profile that "
                     "does not. Empty is the failure. `reason` must be a code "
                     "this page can produce and must agree with `offers`, so "
                     "that a region holding stale text, or one claiming the "
                     "engine cannot do what its contract says it can, cannot "
                     "pass")

        resized = evaluate(session, RESIZE_DESK) or {}
        time.sleep(2.0)
        resized["afterCanvasWidth"] = (evaluate(
            session, "(() => document.querySelector('#canvas').width)()"))
        resized["inkAfter"] = ((evaluate(
            session, LINE_INK.replace("ARG_Y", "0.28")) or {}).get("available"))
        evaluate(session, RESTORE_DESK)
        time.sleep(1.5)
        check("the-canvas-follows-a-window-that-changed-size",
              bool(resized.get("available")
                   and resized.get("afterCanvasWidth")
                   and resized["afterCanvasWidth"] != resized.get("beforeCanvasWidth")
                   and resized.get("inkAfter") is True),
              outcome=None if resized.get("available") else "NOT_ESTABLISHED",
              observed=resized,
              oracle="the desk is narrowed and a resize event dispatched: the "
                     "canvas backing store must change size AND the document "
                     "must still be drawn afterwards. A relayout that resizes "
                     "the canvas and never repaints leaves a blank page, which "
                     "is finding 062's shape one layer up",
              notEstablished="#desk or #canvas is not in the page")

        # --- listener:change#fixture --------------------------------------
        #
        # MEDIUM, and the registry says why: it is the only product path that
        # comes near `queue-search-after-reopen-wedges`, because the session
        # disposes its engine on close and this is the product's second open.
        fixture_switch = evaluate(session, SWITCH_FIXTURE) or {}
        if fixture_switch.get("available"):
            # The picker's VALUE is a stem; the product shows it with `.odt`.
            # Measured 2026-08-21: comparing them for equality made the wait
            # burn its whole timeout on a switch that had already happened.
            switched = wait_for(
                session,
                lambda st, want=fixture_switch.get("to"):
                (st.get("doc") or "").startswith(want)
                and st.get("state") == "ready", 90)
            fixture_switch["docAfter"] = (switched or {}).get("doc")
            fixture_switch["stateAfter"] = (switched or {}).get("state")
            # Ink ANYWHERE, not at one hardcoded band: a different sample puts
            # its text somewhere else, and "no ink at y=0.28" would report a
            # perfectly drawn document as blank.  Same mistake finding 060 was
            # about, and it does not get to happen twice in one day.
            _, fixture_bands = stable_bands(session)
            fixture_switch["inkBands"] = len(fixture_bands)
        check("the-sample-picker-opens-a-second-document",
              bool(fixture_switch.get("available")
                   and str(fixture_switch.get("docAfter") or "").startswith(
                       str(fixture_switch.get("to")))
                   and fixture_switch.get("stateAfter") == "ready"
                   and (fixture_switch.get("inkBands") or 0) > 0),
              outcome=None if fixture_switch.get("available")
              else "NOT_ESTABLISHED",
              observed=fixture_switch,
              oracle="choosing a different sample from the product's own picker "
                     "opens it: the document name becomes the chosen one, the "
                     "session returns to `ready`, and the new document is "
                     "actually DRAWN -- ink found ANYWHERE, since a different "
                     "sample puts its text on different lines. This is the "
                     "product's second open on one "
                     "page, so it is also the only product path that comes near "
                     "queue-search-after-reopen-wedges",
              notEstablished="the picker offers fewer than two samples, so "
                             "there is nothing to switch to")


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

        # PLACED HERE, and the placement is the third lesson of its kind in
        # this file in two days.
        #
        # This block ADDS PARAGRAPHS, and everything between the inline formats
        # and here aims its caret by GEOMETRY -- `the-edit-buttons-do-what-they-say`
        # clicks past the end of the line at y=0.28 specifically so its
        # paragraph break lands at a line END.  Run before it, this block
        # reflows the document, that click lands mid-paragraph, the remainder
        # comes along, and its exact-string oracle fails.  Measured: it went red
        # the first time this check was inserted above it, and the check itself
        # was fine.
        #
        # So it runs after the last geometry-aimed check and immediately before
        # the long-document section, which opens a document of its own and
        # washes away everything this one leaves.  The first thing below is a
        # re-open, so it does not depend on what came before either.
        # ------------------------- 067: does the Enter KEY reach the document?
        #
        # It did not, and the revision counter said it had: the frozen input
        # adapter turns `beforeinput` insertParagraph/insertLineBreak into
        # `commitText("\\n")`, the engine's `paste` ACCEPTS that newline and does
        # nothing with it, and `handleInsertText` increments the revision anyway
        # (measured: method "paste", revision 1 -> 2, content.xml byte-identical,
        # findings/evidence/067/).  The toolbar's break buttons worked the whole
        # time -- only the user's keyboard was broken, which is why nothing here
        # noticed for as long as it existed.
        #
        # THE ORACLE IS THE PARAGRAPH COUNT, NEVER THE REVISION.  This tree has
        # the receipt: the revision advanced on every one of the broken presses.
        #
        # A REAL key, and CHROME ONLY: only a real key runs the default action
        # that produces `beforeinput`, and only CDP can deliver one.  Firefox
        # reports NOT_ESTABLISHED rather than passing, because a synthetic
        # keydown would pass this on a page where the binding is absent.
        enter_record: dict = {"arms": []}
        enter_cdp = getattr(session, "call", None)
        # A known document, through the product's own file input: everything
        # above this point has been editing the one that was open, and this
        # block counts PARAGRAPHS.
        evaluate(session, CLEAR_TOAST)
        enter_record["reopened"] = evaluate(
            session, OPEN_FILE.replace("ARG_URL", "./e1-fixtures/list-contexts.odt")
            .replace("ARG_NAME", "enter-key.odt"))
        wait_for(session, lambda s: (s.get("doc") or "") == "enter-key.odt"
                 and s.get("state") == "ready", 90)

        def press_key(shift: bool) -> None:
            for kind in ("rawKeyDown", "char", "keyUp"):
                payload = {"type": kind, "key": "Enter",
                           "windowsVirtualKeyCode": 13,
                           "nativeVirtualKeyCode": 13, "code": "Enter",
                           "modifiers": 8 if shift else 0}
                if kind == "char":
                    payload["text"] = "\r"
                enter_cdp("Input.dispatchKeyEvent", payload)
            time.sleep(1.5)

        def paragraphs_of(report: dict) -> list[str]:
            content = (report or {}).get("content") or ""
            if not content:
                return []
            try:
                root = ElementTree.fromstring(content)
            except ElementTree.ParseError:
                return []
            return ["".join(node.itertext()) for node in root.iter()
                    if node.tag.split("}")[-1] in ("p", "h")]

        def enter_arm(shift: bool, first: str, second: str) -> dict:
            arm = {"shift": shift, "first": first, "second": second}
            aim = caret_click_fractions(
                evaluate(session, LINE_INK.replace("ARG_Y", "0.24")) or {})
            arm["clicks"] = {k: aim.get(k) for k in ("derived", "near")}
            place_caret_and_settle(session, POINT_AT, aim["near"], "0.24")
            evaluate(session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
            time.sleep(1.2)
            before_first = revision_of(evaluate(session, READ_STATE))
            evaluate(session, TYPE_WHEREVER_FOCUS_IS.replace("ARG_TEXT", first))
            wait_for(session,
                     lambda st, floor=before_first: revision_of(st) is not None
                     and floor is not None and revision_of(st) > floor, 12)
            baseline = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
            arm["paragraphsBefore"] = len(paragraphs_of(baseline))
            arm["firstLanded"] = first in ((baseline or {}).get("content") or "")

            press_key(shift)
            before_second = revision_of(evaluate(session, READ_STATE))
            evaluate(session, TYPE_WHEREVER_FOCUS_IS.replace("ARG_TEXT", second))
            wait_for(session,
                     lambda st, floor=before_second: revision_of(st) is not None
                     and floor is not None and revision_of(st) > floor, 12)
            after = capture_save(session, evaluate(session, SAVE_COUNT) or 0)
            content = (after or {}).get("content") or ""
            paragraphs = paragraphs_of(after)
            arm["paragraphsAfter"] = len(paragraphs)
            arm["secondLanded"] = second in content
            arm["together"] = any(first in para and second in para
                                  for para in paragraphs)
            arm["lineBreaksBetween"] = any(
                first in para and second in para for para in paragraphs) and (
                    f"{first}<text:line-break/>{second}" in content)
            arm["savedIsOdt"] = is_an_odt(after)
            # A question asked of text that is not in the document has no answer.
            if not arm["savedIsOdt"] or not arm["firstLanded"] \
                    or not arm["secondLanded"]:
                arm["outcome"] = "NOT_ESTABLISHED"
                arm["why"] = ("the keyboard did not put both markers in the "
                              "document, so what the key between them did "
                              "cannot be read")
                return arm
            if shift:
                # A LINE break: same paragraph, with a <text:line-break/>
                # between the two markers.
                arm["ok"] = (arm["paragraphsAfter"] == arm["paragraphsBefore"]
                             and arm["lineBreaksBetween"])
            else:
                # A PARAGRAPH break: one more paragraph, and the two markers
                # are no longer in the same one.
                arm["ok"] = (arm["paragraphsAfter"] == arm["paragraphsBefore"] + 1
                             and not arm["together"])
            arm["outcome"] = "PASS" if arm["ok"] else "FAIL"
            return arm

        if enter_cdp is None:
            enter_record["why"] = ("this browser session has no CDP, so a real "
                                   "key cannot be delivered")
        else:
            enter_record["arms"].append(enter_arm(False, "ENTKEYA", "ENTKEYB"))
            enter_record["arms"].append(enter_arm(True, "SHFTKEYA", "SHFTKEYB"))
        judged_enter = [a for a in enter_record["arms"]
                        if a["outcome"] in ("PASS", "FAIL")]
        enter_measurable = len(judged_enter) == 2
        check("the-enter-key-reaches-the-document",
              bool(enter_measurable and all(a["ok"] for a in judged_enter)),
              outcome=None if enter_measurable else "NOT_ESTABLISHED",
              observed=enter_record,
              oracle="a REAL Enter delivered through CDP splits the paragraph -- "
                     "the saved ODT has one more <text:p> and the marker typed "
                     "before the key is no longer in the same paragraph as the "
                     "one typed after -- and a REAL Shift+Enter instead leaves "
                     "the paragraph count alone and puts a <text:line-break/> "
                     "between the two markers. THE ORACLE IS THE PARAGRAPH "
                     "COUNT, NEVER THE REVISION: under finding 067 the revision "
                     "advanced on every broken press while content.xml stayed "
                     "byte-identical",
              notEstablished="anything, on a browser without CDP. A real key is "
                             "the whole point: only it runs the default action "
                             "that produces `beforeinput`, so a synthetic "
                             "keydown would pass this on a page where the "
                             "binding is absent")

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
              below["drawn"] and above["drawn"] and above_dpr2["drawn"]
              and not silent,
              observed={"belowTheWallDrawn": below["drawn"],
                        "aboveTheWallDrawn": above["drawn"],
                        "sameDocumentAt2xDrawn": above_dpr2["drawn"],
                        "silentArms": long_report["silentArms"],
                        "arms": long_report["arms"]},
              oracle="every length the product will open is DRAWN, and at any "
                     "length where rendering has broken it says so -- a blank "
                     "canvas with the session reporting `ready` and no message "
                     "is the failure this checks for. The two long arms are "
                     "past the engine's 32,767 px tile limit (finding 062), so "
                     "they pass only because the page splits the request into "
                     "strips; the `one-tile-for-the-whole-document` mutation "
                     "takes that away and this must go red",
              notEstablished="WHERE in the engine the 2^15 boundary lives. "
                             "That it is a height limit and not a memory one is "
                             "measured (findings/evidence/062/layer/: two "
                             "widths, buffers differing twofold, same height "
                             "boundary); that a 2^15 boundary is a signed "
                             "16-bit quantity is an inference from the number, "
                             "and no source at that point has been read")

        # --- the half that is NOT fixed, as its own check ------------------
        # Splitting it out on 2026-08-19 when the drawing half was fixed: a
        # mutation owned by a check that is already red cannot be shown to have
        # been detected, so leaving both halves on one id would have meant the
        # strip fix could never be guarded.
        check("the-canvas-follows-a-document-that-grew",
              really_grew and grew["canvasFollowedTheDocument"],
              outcome=None if really_grew else "NOT_ESTABLISHED",
              observed=grew,
              oracle="an edit that makes the document taller is either drawn or "
                     "explained. Ground truth is the SAME code path: the edited "
                     "bytes are saved and re-opened, and if that canvas is "
                     "taller than the one on screen then the document grew and "
                     "the screen did not",
              notEstablished="that the edit made the document taller at all. "
                             "Without that, 'the canvas did not change' is not "
                             "evidence of anything -- which is what caught a "
                             "corpus whose pages held 83 lines")

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
            # THE POSITIVE CONTROL for finding 072's remedy, and it belongs
            # here because this is the band count the remedy exists to get
            # right.  Without it, "the exclusion silently stopped working" and
            # "this page happened to have no caret drawn" produce the same
            # bands and the same report.  `caretAtInducer` non-null says the
            # sink's position and the pixels agreed and a bar was taken out;
            # `caretWhyAtInducer` says which of the two disagreed when not.
            recovery["caretAtInducer"] = scan.get("caret")
            recovery["caretWhyAtInducer"] = scan.get("caretWhy")
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
            # The product declares its decision in two places -- the status
            # pill and the notice -- and they must not disagree.  This is what
            # finding 061 was: the pill said 寫入失敗 and the notice told the
            # user there had never been a checkpoint.
            expected_rescue = {"checkpoint": "checkpoint",
                               "none": "none",
                               "write-failed": "failed"}[branch]
            recovery["declaredByNotice"] = offered.get("rescue")
            recovery["surfacesAgree"] = offered.get("rescue") == expected_rescue
            if branch == "checkpoint":
                honoured = saved_back and unsaved_back
            elif branch == "none":
                honoured = saved_back and not unsaved_back
            else:
                # "We tried to protect your work and the save FAILED" is not
                # the same thing to say as "there was nothing to protect", and
                # the product's notice has only the second sentence -- its
                # branch is on `hasCheckpoint` alone.  The shell already decides
                # the difference (recovery-notice.js, `checkpointFailed`); the
                # product does not render it.
                #
                # Note what the defect is NOT, because getting this wrong loses
                # the argument to the first hostile reader: the sentence is not
                # false.  In this state `hasCheckpoint` really is false and the
                # bytes really are the same as case (b).  It is literally true
                # and causally misleading -- it attributes the loss to there
                # having been no protection, when protection was attempted and
                # its save failed.
                #
                # Three requirements, and the second and third were missing
                # until an adjudication on 2026-08-19 pointed at them:
                #   * the saved work comes back and the unsaved work does not,
                #     which is what 寫入失敗 implies and what nothing checked;
                #   * the notice is NEITHER of the product's two sentences --
                #     asking only that it differ from the no-checkpoint one
                #     would pass the strictly worse regression of printing the
                #     HAS-checkpoint sentence, which claims a rescue that does
                #     not exist;
                #   * both sentences come from the served source, so a rewording
                #     moves the reference instead of silently disarming this.
                honoured = saved_back and not unsaved_back
            recovery["declarationHonoured"] = honoured
            check("recovery-returns-what-the-product-promised",
                  bool(honoured and capability_held
                       and recovery["surfacesAgree"]
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

        # ------------------------------------------ P-CUT-4, the cross shape
        #
        # DIAGNOSTIC ONLY, and LAST.  `queue-cut-cannot-remove-text`'s
        # prediction reserves one arm with NO prediction attached: a range
        # spanning more than one paragraph, RECORDED rather than forecast,
        # because the five paragraph actions were characterised for
        # cross-paragraph ranges and the ten v1 actions were not.  Forecasting
        # here would be the same undeclared confidence that item exists to
        # remove.
        #
        # It matters now because of how the engine gate is written
        # (probe_engine.cpp, "an unclassified range must satisfy BOTH range
        # bits"): granting `range-cross` in order to make the ORDINARY
        # within-paragraph cut work makes every one of these shapes reachable
        # in the same stroke.  The widening decision cannot be taken without
        # them.
        #
        # FOUR SHAPES, NOT ONE, and the three past the first are here because
        # of where this tree's defects have actually lived.  Finding 046 was a
        # multi-block readback verifying the wrong paragraph, and the fixture's
        # list items are what a cross-block selection runs into: a cut that
        # takes two paragraphs cleanly says nothing about one that takes a
        # bullet list and a numbered list with a plain paragraph between them.
        #
        # Last, and behind the flag, because dragging across a whole paragraph
        # is a multi-block mutation and the 2026-08-21 measurement of the same
        # shape on `delete-backward` ended in recoverable-error.  If that is
        # what happens here it must not poison the thirty-four checks above.
        #
        # RECORDED, NOT SCORED.  There is no oracle for a behaviour nobody has
        # characterised, and both paragraph lists are stored WHOLE rather than
        # reduced to booleans I picked in advance -- a derived flag can only
        # answer the question I thought to ask, and these arms exist precisely
        # because I do not know what the question is yet.
        if args.range_delete_diagnostic:
            shapes = [
                {"name": "two-paragraphs-heading-into-body", "from": 0, "to": 1},
                {"name": "three-paragraphs-into-a-bullet-list",
                 "from": 2, "to": 4},
                {"name": "across-a-bullet-list-and-a-numbered-list",
                 "from": 3, "to": 7},
                {"name": "within-one-bullet-list", "from": 3, "to": 4},
            ]
            arms: list[dict] = []
            report["rangeDeleteDiagnostic"]["crossParagraph"] = arms
            # The paragraph list the fixture is supposed to have, learned from
            # the first arm and required of every later one.  See the name
            # below for why this is not optional.
            fixture_texts: list[str] | None = None
            for index, shape in enumerate(shapes):
                arm: dict = {"shape": shape["name"], "from": shape["from"],
                             "to": shape["to"], "why": None}
                arms.append(arm)
                evaluate(session, CLEAR_TOAST)
                evaluate(session, CLEAR_TOASTS)
                # Re-opened through the product's own file input before EVERY
                # arm.  The prediction's own trap list: a 2026-08-19 probe swept
                # a parameter ascending inside one session, carried state
                # between arms, and exonerated the engine wrongly.  A re-open is
                # not a fresh engine -- so `stateAfterOpen` is recorded per arm,
                # and an arm that opens into anything but `ready` measures
                # nothing and says so.
                # A DIFFERENT NAME PER ARM, and this is not cosmetic.  With
                # one name, the wait below is satisfied the instant it is asked
                # -- by the PREVIOUS arm's document, which already carries that
                # name and is already ready -- so the arm goes on to measure a
                # page that is still loading.  Measured: arms two, three and
                # four of the first sweep all reported `lines: 0` and declined,
                # which was honest but blamed the band mapping.  Same family as
                # the 2026-08-18 round that spent four rounds measuring a 404
                # page the label said was the fixture: a name is a label, and a
                # label the page already had is no evidence at all.
                name = f"cross-cut-{index}.odt"
                arm["openedAs"] = name
                arm["reopened"] = evaluate(
                    session, OPEN_FILE
                    .replace("ARG_URL", "./e1-fixtures/list-contexts.odt")
                    .replace("ARG_NAME", name))
                opened = wait_for(
                    session,
                    lambda s: (s.get("doc") or "") == name
                    and s.get("state") == "ready", 90)
                arm["stateAfterOpen"] = (opened or {}).get("state")
                if arm["stateAfterOpen"] != "ready":
                    arm["why"] = ("the fixture did not re-open into a ready "
                                  "session, so no range was ever selected and "
                                  "NOTHING in this arm is measured")
                    continue
                before_report = capture_save(
                    session, evaluate(session, SAVE_COUNT) or 0)
                before_lines = document_lines(before_report)
                scan, bands = stable_bands(session)
                arm["lines"] = len(before_lines)
                arm["bands"] = len(bands)
                # And the CONTENT, not just the name.  The first arm defines
                # what this fixture looks like; every later arm has to open
                # into the same nine paragraphs or it is measuring the leftover
                # of the arm before it.
                texts = [line["text"] for line in before_lines]
                if fixture_texts is None:
                    fixture_texts = texts
                elif texts != fixture_texts:
                    arm["why"] = ("the re-open did not restore the fixture -- "
                                  "this arm was looking at whatever the "
                                  "previous arm left behind, so NOTHING here "
                                  "is measured")
                    arm["textsSeen"] = texts
                    continue
                # The same aiming rule the within-paragraph arm uses: band to
                # paragraph is a trustworthy mapping only when every paragraph
                # draws as exactly one band.  Without that, "the drag crossed a
                # paragraph boundary" is an assumption, not an observation.
                if (len(bands) != len(before_lines)
                        or shape["to"] >= len(bands)):
                    arm["why"] = ("bands and paragraphs did not correspond one "
                                  "to one, so a drag cannot be aimed at a "
                                  "KNOWN paragraph boundary")
                    continue
                top, bottom = bands[shape["from"]], bands[shape["to"]]
                arm["fromText"] = before_lines[shape["from"]]["text"]
                arm["toText"] = before_lines[shape["to"]]["text"]
                arm["textsBefore"] = [line["text"] for line in before_lines]
                # Starting near the first paragraph's left edge and ending
                # halfway through the last: the range covers the whole of the
                # first, every boundary between, and part of the last -- the
                # shape a user makes when they drag down through a document.
                evaluate(session, DRAG
                         .replace("ARG_X1", f"{max(0.0, (top['first'] + 2) / scan['width']):.5f}")
                         .replace("ARG_Y1", f"{top['centreFraction']:.5f}")
                         .replace("ARG_X2", f"{((bottom['first'] + bottom['last']) / 2) / scan['width']:.5f}")
                         .replace("ARG_Y2", f"{bottom['centreFraction']:.5f}"))
                time.sleep(1.5)
                evaluate(session, CLEAR_TOAST)
                evaluate(session, CLEAR_TOASTS)
                cut = evaluate(session, CUT)
                time.sleep(2.5)
                arm["handled"] = (cut or {}).get("handled")
                arm["toasts"] = evaluate(session, READ_TOASTS)
                said = " ".join(arm.get("toasts") or [])
                arm["refusalReported"] = (
                    "EDITOR_FORMAT_GESTURE_UNSUPPORTED" in said)
                arm["stateAfterCut"] = (
                    evaluate(session, READ_STATE) or {}).get("state")
                after_report = capture_save(
                    session, evaluate(session, SAVE_COUNT) or 0)
                after_lines = document_lines(after_report)
                after_texts = [line["text"] for line in after_lines]
                # AN EMPTY CAPTURE IS NOT AN EMPTY DOCUMENT -- the same trap the
                # within-paragraph arm records.  A session in recoverable-error
                # answers EDITOR_NOT_READY to a save, and reading "the text is
                # gone" out of that would turn a refusal into a deletion.
                readable = is_an_odt(after_report) and bool(after_texts)
                arm["documentReadableAfter"] = readable
                arm["textsAfter"] = after_texts if readable else None
                arm["linesAfter"] = len(after_texts) if readable else None
                # The paragraphs the drag never touched.  A cut that removes
                # what was selected and something else as well is finding 046's
                # shape, and it is the one thing here that would settle the
                # decision on its own.
                arm["untouchedSurvive"] = None
                if readable:
                    untouched = [line["text"] for index, line
                                 in enumerate(before_lines)
                                 if index < shape["from"] or index > shape["to"]]
                    arm["untouched"] = untouched
                    arm["untouchedSurvive"] = all(
                        any(text == other for other in after_texts)
                        for text in untouched)
                if not readable:
                    arm["why"] = ("the save after the cut produced no readable "
                                  "ODT, so what the cut did to the document is "
                                  "NOT measured here -- read `toasts` and "
                                  "`stateAfterCut`")
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
    # Finding 075. On the shipped core `worst` is 0 on every scan; a non-zero
    # value is the accessibility core's uninitialised off-page memory being
    # seen and named instead of quietly merging two lines into one band.
    report["offPageInk"] = dict(OFF_PAGE_INK)
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
