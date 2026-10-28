// SPEC E2-C 2.4: the product page for the v2 contract.
//
// It exists because a client and a session are not a product.  Until this file,
// nothing a user could open drove NarrowEditorV2Client, and `demo-structure`
// offered five of the fifteen actions with no drag selection at all -- so D5's
// "select with a real pointer drag, then press a format button" had no product
// path to run on, and measuring it in a harness would have measured the
// harness.
//
// Three things this page is careful about, each of them a rule from evidence
// rather than a preference:
//
//   * Format buttons follow a SELECTION gesture.  SPEC E2-B 5.13 makes a failed
//     dispatch recoverable by rolling back to the checkpoint that
//     `_checkpointBeforeSelection` writes before a range selection.  Press a
//     format button with no gesture in front of it and the rollback reaches
//     further back than the one action.
//
//   * The toolbar never shows what the paragraph currently IS.  Route C does
//     not read the precondition (finding 022), so an "active" button would only
//     report what this page last asked for.  What the buttons DO reflect is the
//     manifest's gesture declaration for the current selection shape, which is
//     a statement about the contract rather than about the document.
//
//   * A dispatched failure is recovered by rolling back, not by undo: undo goes
//     through the queue that the failure has just blocked, so the user would
//     get EDITOR_NOT_READY.  The page offers the rollback explicitly.

import { createDocumentEngine, TYPED_INSERT_DECLARATION } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session, PageRectanglesScheduler, pageSpanOf, pageStatusText,
         selectionShapeEvidence, selectionShapeOf, visibleRegionTwips }
  from "./editor-shell-v2/narrow-editor-v2-session.js";
// Finding 061: this page used to re-derive the recovery notice from
// `hasCheckpoint` alone, and that two-way branch told a user whose checkpoint
// SAVE FAILED that there had never been one.  The shell decides this already,
// and its own spec revision (SPEC-E1-C 4.1 v8) says the third case exists
// precisely so nobody is left silent about a failed rescue.  Taking the
// decision instead of re-deriving it also retires the second defect the same
// re-derivation produced: finding 054, a flag nothing wrote.
import { recoveryNotice } from "./editor-shell/recovery-notice.js";
import { EDITOR_V2_ACTIONS } from "./editor-shell-v2/narrow-editor-v2-client.js";

// The artifact this page is for.  A page that runs on whatever build happens to
// be in dist/ is a page that can show behaviour no evidence covers.
//
// Moved to the ABI 4 successor on 2026-08-22, with the profile below.  The two
// move together or the page pins one artifact and loads another -- and the
// expiry screen exists to make exactly that mismatch loud, so a half-move
// would look like a broken build rather than a mistake.
const PINNED_WASM_SHA256 = "276158084a602178";

// M3's host entry (specs/SPEC-M3-host-entry.md).  A host that embeds this page
// -- the Nextcloud app -- puts `globalThis.liteCoreHost = { load, save }` in
// place BEFORE importing this module.  Read once, here: a host that appears
// later is not a host.  With one, the page opens what `load()` returns instead
// of its bundled sample, and a save hands the bytes to `save()` instead of a
// download link.  The M3 skeleton reached this page only through `#file`, so it
// paid for the sample's open on every document and could not save back at all.
const HOST = globalThis.liteCoreHost ?? null;
let hostSaves = Promise.resolve();

// ITEM 2, paste as Markdown (SPEC-M3-link-batch-v22 §11; fable ruling 5).  It
// ships from v22: the v22 link gives the engine thread a 1 MiB stack, and
// finding 153's inputs complete in both browsers there (v22 criterion C1).  In
// v21 this was false (v21 §12.3 (e)): one long paragraph overflowed the engine
// thread's 64 KiB stack, so the shell offered no entry whatever the profile
// declared.  This is still the shell's switch for the feature (v21 9.2): if
// item 2's criteria on v22 (v22 §11.2, E2) do not hold, it goes back to false
// before the shell is frozen, and the SDK stays callable (L-md-sdk-callable).
// With it on, the entry is shown only on a profile that declares the paste.
const PASTE_MARKDOWN_ENTRY_SHIPS = true;

// SPEC-M3-page-honesty: a file the user may not write opens view-only (the
// owner's ruling A, 2026-09-29).  The SESSION refuses -- its queue turns away
// every mutation before it is queued (NarrowEditorV2Session._enqueue) -- and
// the page only stops offering what would be refused, so a control this page
// forgets to disable still changes nothing.
const VIEW_ONLY_TEXT = "唯讀：只能檢視";
let viewOnly = false;

// FINDING 107.  Leaving with edits nobody saved lost them without a word: no
// `beforeunload` existed in this page, the shell's `dirty` fed only its
// checkpoints, and the host guarded only bytes it could not write.  "Unsaved"
// is the session's half (an edit landed or still in the engine,
// `hasUnsavedEdits()`) plus this page's: a save asked for and not yet
// SETTLED.  Counted from the press, because between the session producing the
// bytes (which marks it clean) and the host being handed them this page
// renders, and in that gap nothing is written anywhere.  Settled, not "kept":
// the host rejects a copy that landed and bytes it could not place with the
// same code, and it guards the second kind itself.
let savesUnsettled = 0;

// FINDING 127 (specs/SPEC-M3-autosave.md §9.2).  Nothing ever saved by itself:
// a dead session, a crashed tab or a power cut lost everything since the
// user's last press of save.  Collabora saves after 30 s idle and every 5
// minutes in a background process; ours blocks input for the engine's part of
// a save (0.6-0.75 s the first time after open, 0.15-0.3 s after that,
// findings/evidence/127/m2/), so: 30 s after the last activity; once edits have
// waited 5 minutes, 3 s; and at once when the tab goes hidden -- the last
// moment a browser reliably gives a page before it may discard it.  Only with
// a host: without one a save is a download.  Conditions are read from the
// sources (the session, the input adapter), never from this page's DOM.
const AUTOSAVE_IDLE_MS = 30000;
const AUTOSAVE_CAP_MS = 300000;
const AUTOSAVE_CAP_IDLE_MS = 3000;
const AUTOSAVE_RECHECK_MS = 3000;
const autosave = { timer: null, firstUnsavedAt: null, revision: null };

// Finding 128: editor actions out, and whether a repaint gave up on their BUSY
// and has not been made since (editorAction, renderDocument).  Finding 129: click-then-move pairs
// queued (moveFromPoint).  Finding 131: deletes the delete listener sent and has
// not seen settle.  Declared here, before anything can fire an event.
let engineActionsOut = 0;
let busyLeftToAction = false;
let pointMovesInFlight = 0;
let deletesInFlight = 0;
// FINDING 141 (task 2026-10-14o).  Deletes the listener sent that the ENGINE
// has not answered yet -- `deletesInFlight` also counts the repaint `run()`
// waits for -- and the presses of the same key held on the page behind them
// (`holdsDelete`, `settleDelete`).
//
// SPEC-M3-link-batch-v21 §10.3: held presses BELONG TO THE SEND THEY WAIT ON
// (`send.held`, each press with its own key), never to a shared field -- the
// old `heldDeletes.action` was overwritten by whatever was sent next, so a
// Backspace held behind a Backspace could be released as a Delete.  `count` is
// every press held anywhere (finding 144's depth reads it), `last` the newest
// delete this page sent, and `sending` is true only while that send is being
// put into the session's queue (see `releaseHeldDeletesBeforeEnqueue`).
let deletesUnanswered = 0;
const heldDeletes = { count: 0, last: null, sending: false };

// Fail closed: a session without `hasUnsavedEdits` throws here, and the host
// counts a throw as "ask" -- an optional call answering `false` would switch
// finding 107's fix off without a sign (review 2026-09-29, implementation).
// No document yet is the only "nothing to lose".  editor-shell-v2/tests/
// page-unsaved-work.test.mjs compiles this function with `session` and
// `savesUnsettled` as its only names in scope.
function hasUnsavedWork() {
  return (session ? session.hasUnsavedEdits() : false) || savesUnsettled > 0;
}

function guardLeave(event) {
  if (!hasUnsavedWork()) return;
  event.preventDefault();
  event.returnValue = "";
}

// With a host, the HOST decides, alone.  Its `beforeunload` is registered
// before this module is imported and releases the lock whenever it is not
// guarding; had this page asked on its own, a user who chose to stay would be
// left holding no lock and the next save would go to a conflict copy
// (specs/SPEC-M3-page-honesty.md §7.1).  So the page hands the host its
// question.  A host without `watchUnsaved` is an older host: the page still
// asks rather than let edits go silently.
if (HOST && typeof HOST.watchUnsaved === "function") HOST.watchUnsaved(hasUnsavedWork);
else {
  // An older host is a version mismatch, not a shipped pairing: said where a
  // driver reads the host's record (specs/SPEC-M3-page-honesty.md §7.1).
  if (HOST) document.documentElement.setAttribute("data-litecore-page-guard", "own");
  addEventListener("beforeunload", guardLeave);
}

const $ = (selector) => document.querySelector(selector);
const el = {
  canvas: $("#canvas"), paper: $("#paper"), desk: $("#desk"), sink: $("#sink"),
  toolbar: $("#toolbar"), fixture: $("#fixture"), text: $("#text"),
  openFile: $("#open-file"), file: $("#file"),
  clearFormat: $("#clear-format"),
  statePill: $("#state-pill"), toast: $("#toast"), expired: $("#expired"),
  notice: $("#notice"), noticeText: $("#notice-text"),
  noticeAction: $("#notice-action"),
  pinnedHash: $("#pinned-hash"), expectedHash: $("#expected-hash"),
  actualHash: $("#actual-hash"),
  a11yDoc: $("#a11y-doc"), a11yPara: $("#a11y-para"),
  a11yStructure: $("#a11y-structure"),
  pageStatus: $("#page-status"),
  // SPEC-M3-link-batch-v21 4.2 / 9.13 Q1 = A: the Markdown dialog.
  markdownDialog: $("#markdown-dialog"), markdownText: $("#markdown-text"),
  markdownMessage: $("#markdown-message"), markdownInsert: $("#markdown-insert"),
  markdownCancel: $("#markdown-cancel"),
  s: { state: $("#s-state"), revision: $("#s-revision"), pending: $("#s-pending"),
       generation: $("#s-generation"), checkpoint: $("#s-checkpoint"),
       latency: $("#s-latency"), doc: $("#s-doc") },
};

const MAX_BACKING_WIDTH = 2400;
const MOVE_ACTIONS = new Set(["move-character-left", "move-character-right"]);
const FORMAT_ACTIONS = new Set(["set-bold", "set-italic", "set-underline",
  "set-strikethrough"]);

let session = null;
let documentName = "—";
let rendering = false;
let renderAgain = false;
let lastSelectionShape = "collapsed";
// The last tile the engine painted, kept so a caret move can be drawn without
// asking for pixels again (finding 058).  Cleared on resize, where the canvas
// changes size and the cached pixels stop describing it.
//
// Release C′ (SPEC-M3-production-ui §17, §17.9): one entry per band, indexed
// by band, holding only the bands that overlap the window -- `{ image, y,
// label }`, `y` in document rows and `label` the change counter when the band
// was ASKED for.  Bounded: everything outside the window is dropped when the
// window moves and when a pass ends.
let lastTiles = [];

// Release C′: the canvas is a window onto the document, not the document.
//
// Finding 126: the whole document in one canvas is blank EVERYWHERE past about
// 65,535 rows -- 40 A4 pages at devicePixelRatio 2, 50 at 1.5, measured in both
// browsers, Chrome without a word.  So #paper is sized as the document and the
// canvas covers rows [winTop, winTop + canvas.height) of it, moved as the desk
// scrolls.  `docRows` is what the canvas height used to be -- the document in
// backing rows -- and every band, twips edge, 062 and 118 test still counts in
// it; only where the rows are drawn changed.
let docRows = 0;
let winTop = 0;
// §17.9 (c): the page's own change counter.  Every `document-invalidated` and
// every completed `run()` adds one; a band is stamped with it when it is asked
// for, and a band stamped below it is stale.  Not the engine's revision: the
// engine advances that AFTER the callbacks of the command that changed the
// document (probe_engine.cpp, nine sites), so a band painted between the two
// would carry the new number over the old pixels and never be asked for again.
let changes = 0;

// SPEC-M3-production-ui §16 (release P): the caret and selection on the canvas
// now, as `overlayShapes()` described them when `paint()` or `paintBand()` last
// drew them over the bands.  `paint()` compares against it, so a state write
// that moves neither costs no pixels.  Cleared with the canvas in
// `layoutCanvas()`.
const NO_OVERLAY = Object.freeze({ key: "", selection: [], caret: null, caretTwips: null });
let paintedOverlay = NO_OVERLAY;
// The editor state the overlay draws (overlayEditorState, finding 132).
let overlayState = null;

// Finding 062: the engine will not paint a tile taller than this.  Above it, it
// returns a correctly sized buffer it never drew into AND reports success --
// measured at two widths whose buffers differ by a factor of two (45 MB paints
// at 32,767 and 45 MB is blank at 32,768), so it is the height and not the
// memory.  Asking for one is therefore the PAGE's mistake: nothing forces this
// page to want the whole document in a single bitmap, and splitting the request
// needs no engine change and no link.
const MAX_TILE_HEIGHT = 32767;

function toast(message, bad = false) {
  el.toast.textContent = message;
  el.toast.classList.toggle("bad", bad);
  el.toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.toast.classList.remove("show"), 4000);
}

function describeError(error) {
  if (error?.code === "EDITOR_VIEW_ONLY") return VIEW_ONLY_TEXT;
  const code = error?.code ? `${error.code}：` : "";
  return `${code}${error?.message || String(error)}`;
}

/* ------------------------------------------------------------ page number */

// SPEC-M3-link-batch §4.3, §10.8, §10.10 Q-A, §12.3 (task 2026-10-13l).  The
// line at the bottom left, 「第 N 頁，共 M 頁」 or 「第 N–L 頁，共 M 頁」, drawn
// from `handle.pageRectangles()` by Writer's rule computed here: N is the
// first page intersecting the visible region, L the last, M the number of
// rectangles.  The rule, the text and the region conversion are
// `pageSpanOf`, `pageStatusText` and `visibleRegionTwips` in the session
// module, node-tested; this page only measures the view and sets an element.
//
// ITS OWN ELEMENT, `#page-status`, outside `.statusbar`: the host hides the
// dev status bar whole (`litecore/templates/editor.php:51`,
// `#litecore-editor-root .statusbar { display: none }`) and this line must be
// visible there.  Not a live region: scrolling must not speak (087/088).
//
// ABSENT UNLESS OFFERED.  On every profile that predates the v20 link
// (`offersPageRectangles()` false: v8, v19) the element stays `hidden` and
// `pageRectangles()` is never called -- the scheduler is gated on the same
// answer -- so this page on v19 behaves exactly as before.
//
// WHEN THE ENGINE IS ASKED (`PageRectanglesScheduler`, the decision in one
// clock-free, node-tested place): after every open of a document -- the first
// open, the reopen after a refusal, a restart -- keyed on the DOCUMENT object,
// because a fresh engine's counter starts at 0 again; when
// `editorState.documentSizeChangedCount` moves; when a paint reply says
// `documentSizeChanged` (renderDocument).  Never on `documentChangeSequence`
// (typing sends no INVALIDATE_TILES, spec F2), scroll, resize, zoom or caret
// movement: those recompute N and L from the last answer (`updatePageStatus`,
// from onDeskScroll and layoutCanvas; followCaret scrolls the desk, which is
// a scroll).  At most one read in flight, triggers meanwhile collapse into one
// follow-up, an answer for a document no longer current is dropped.
//
// A read that fails hides the line and says nothing: a page number is not
// worth a toast.  Named limit L-page-margin: the whole rectangle is used
// (Writer subtracts the margins first), so a view showing only the previous
// page's bottom margin counts that page.
const pageStatus = { document: null, rectangles: null };
const pageRectangles = new PageRectanglesScheduler({
  offered: () => session?.offersPageRectangles?.() === true,
  read: (document) => document.pageRectangles({ timeoutMs: 30000 }),
  onResult: (document, result) => {
    if (document !== session?.document || document !== pageStatus.document) return;
    pageStatus.rectangles = Array.isArray(result?.rectangles) ? result.rectangles : null;
    updatePageStatus();
  },
});

/** Every write of the session's state: a document opened, or its counter may have moved. */
function notePageRectangles(snapshot) {
  if (!["ready", "busy"].includes(snapshot?.state)) return;
  const document = session?.document ?? null;
  if (document === null) return;
  if (document !== pageStatus.document) {
    pageStatus.document = document;
    pageStatus.rectangles = null;
    updatePageStatus();   // hidden until this document's read answers
    pageRectangles.documentOpened(document, snapshot.editorState);
    return;
  }
  pageRectangles.stateObserved(document, snapshot.editorState);
}

function hidePageStatus() {
  if (el.pageStatus.hidden && el.pageStatus.textContent === "") return;
  el.pageStatus.hidden = true;
  el.pageStatus.textContent = "";
}

/** Recompute N and L from the last rectangles and the view.  No engine call, ever. */
function updatePageStatus() {
  const rectangles = pageStatus.rectangles;
  const document = session?.document ?? null;
  if (!rectangles || document === null || document !== pageStatus.document || !docRows) {
    hidePageStatus();
    return;
  }
  const [top, bottom] = visibleDocRows();
  const region = visibleRegionTwips(top, bottom, docRows, document.widthTwips, document.heightTwips);
  const text = pageStatusText(pageSpanOf(rectangles, region));
  if (text === null) { hidePageStatus(); return; }
  if (el.pageStatus.textContent !== text) el.pageStatus.textContent = text;
  el.pageStatus.hidden = false;
}

/* ---------------------------------------------------------- scroll bubble */

// SPEC-M3-scroll-page-bubble (the owner, 2026-10-14: 「拉著卷軸的游標旁邊會有
// 一個泡泡顯示當前頁數」; ruled the same day: it shows on ANY scroll of the
// desk -- thumb drag, wheel, keyboard, a caret the page follows -- and fades
// after scrolling stops, because a native scrollbar cannot tell a thumb drag
// from a wheel).  A second read-out of the page number, next to the thumb,
// where the eyes are while scrolling; the status line (finding 143) stays.
//
// SAYS the status line's page part only, 「第 4 頁」 or 「第 4–5 頁」 (spec
// §3.1): the same number the bar shows at the same instant, so the two never
// disagree and the text criterion is equality.  「共 M 頁」 stays on the bar.
//
// PLACED by proportion (spec §3.2).  No API reads a scrollbar thumb's
// position, so the page models it: f = scrollTop / (scrollHeight -
// clientHeight), a thumb t = max(clientHeight² / scrollHeight, 20) px, an
// arrow-button allowance a = 17 px when a classic scrollbar occupies width
// (offsetWidth - clientWidth > 0; the overlay kind occupies none and has no
// arrows), centre y = top + a + t/2 + f * (clientHeight - 2a - t), clamped so
// the bubble stays inside the desk.  Named limit L-bubble-thumb-model: the
// real thumb's length and the arrows are the browser's; the spec's N2 reads
// the real thumb from a screenshot and allows 24 px.  The side is the
// scrollbar's, read from the desk (`clientLeft` carries the bar's width in
// RTL, MDN) and the desk's direction, never from the locale.  All in CSS px
// from getBoundingClientRect, so zoom is nothing to it (L-bubble-zoom-untested).
// Nothing to scroll (scrollHeight <= clientHeight) -> no thumb -> no bubble;
// "one page" is not the rule, a one-page A4 still scrolls in a 794 px desk.
//
// MADE AND STYLED HERE, not in e2-editor.html: the html is bound by nothing
// (finding 094), and inline CSSOM styles are out of reach of the host's
// @scope and [hidden] overrides (finding 143's cost).  `position: fixed`, a
// sibling after #desk: a child of the scroller would scroll with the paper.
// aria-hidden, no role, no live region, no focus, pointer-events none:
// scrolling must not speak (findings 087/088) and the bubble must not take
// the keyboard from the sink.  `prefers-reduced-motion: reduce` -> no fade;
// the 1 s hold is not motion and stays.
const SCROLL_BUBBLE_HOLD_MS = 1000;      // after the last scroll event
const SCROLL_BUBBLE_FADE_MS = 180;       // the toast's .18s
const SCROLL_BUBBLE_THUMB_MIN_PX = 20;   // the model's shortest thumb
const SCROLL_BUBBLE_ARROW_PX = 17;       // a classic bar's arrow button, each end
const SCROLL_BUBBLE_RAIL_MIN_PX = 12;    // an overlay bar occupies 0 px but is drawn at the edge
const SCROLL_BUBBLE_GAP_PX = 6;          // between the bubble and the rail

/** The page part of the status line: 「第 4–5 頁，共 60 頁」 -> 「第 4–5 頁」; null unless there is one. */
function scrollBubbleText(statusText) {
  if (typeof statusText !== "string") return null;
  const head = statusText.split("，")[0].trim();
  return /^第 \S+ 頁$/.test(head) ? head : null;
}

/**
 * Where the bubble goes, in viewport CSS px, from what the desk measures:
 * `{ top, bottom, left, right, scrollTop, scrollHeight, clientHeight,
 * offsetWidth, clientWidth, clientLeft, direction }`.  Returns
 * `{ centreY, side, edgeX }` -- `edgeX` the bubble's edge nearest the rail,
 * on `side` -- or null when there is nothing to scroll.
 */
function scrollBubblePlace(desk, bubble) {
  const { top, bottom, left, right, scrollTop, scrollHeight, clientHeight, offsetWidth, clientWidth } = desk ?? {};
  if (![top, bottom, left, right, scrollTop, scrollHeight, clientHeight, offsetWidth, clientWidth].every(Number.isFinite)) return null;
  const range = scrollHeight - clientHeight;
  if (!(range > 0) || !(clientHeight > 0)) return null;
  const f = Math.max(0, Math.min(1, scrollTop / range));
  const rail = Math.max(0, offsetWidth - clientWidth);
  const arrow = rail > 0 ? SCROLL_BUBBLE_ARROW_PX : 0;
  const thumb = Math.max(clientHeight * clientHeight / scrollHeight, SCROLL_BUBBLE_THUMB_MIN_PX);
  const track = Math.max(0, clientHeight - 2 * arrow - thumb);
  const half = (Number.isFinite(bubble?.height) ? bubble.height : 0) / 2;
  const centreY = Math.max(top + half, Math.min(bottom - half, top + arrow + thumb / 2 + f * track));
  const gap = Math.max(rail, SCROLL_BUBBLE_RAIL_MIN_PX) + SCROLL_BUBBLE_GAP_PX;
  const clientLeft = Number.isFinite(desk.clientLeft) ? desk.clientLeft : 0;
  const side = clientLeft >= SCROLL_BUBBLE_RAIL_MIN_PX || desk.direction === "rtl" ? "left" : "right";
  return { centreY, side, edgeX: side === "left" ? left + gap : right - gap };
}

const scrollBubble = { element: null, reduced: false, timer: null, fadeTimer: null };

/** The element, made on the first scroll and styled here (see the section comment). */
function scrollBubbleElement() {
  if (scrollBubble.element) return scrollBubble.element;
  const node = document.createElement("div");
  node.id = "scroll-bubble";
  node.setAttribute("aria-hidden", "true");
  node.dataset.shown = "0";
  scrollBubble.reduced = typeof matchMedia === "function"
    && matchMedia("(prefers-reduced-motion: reduce)").matches === true;
  Object.assign(node.style, {
    position: "fixed", top: "0px", left: "0px", transform: "translateY(-50%)",
    background: "#24333f", color: "#fff", padding: "6px 10px", borderRadius: "6px",
    font: "13px/1.2 system-ui, sans-serif", whiteSpace: "nowrap",
    boxShadow: "0 1px 6px rgba(20,40,60,.3)", pointerEvents: "none", zIndex: "30",
    visibility: "hidden", opacity: "0",
    transition: scrollBubble.reduced ? "none" : `opacity ${SCROLL_BUBBLE_FADE_MS}ms`,
  });
  el.desk.insertAdjacentElement("afterend", node);
  scrollBubble.element = node;
  return node;
}

/** The desk scrolled: say the page next to the thumb, and start the hold over. */
function showScrollBubble() {
  const text = el.pageStatus.hidden ? null : scrollBubbleText(el.pageStatus.textContent);
  if (text === null) { hideScrollBubble(); return; }
  const node = scrollBubbleElement();
  if (node.textContent !== text) node.textContent = text;
  const rect = el.desk.getBoundingClientRect();
  const place = scrollBubblePlace({
    top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right,
    scrollTop: el.desk.scrollTop, scrollHeight: el.desk.scrollHeight, clientHeight: el.desk.clientHeight,
    offsetWidth: el.desk.offsetWidth, clientWidth: el.desk.clientWidth, clientLeft: el.desk.clientLeft,
    direction: getComputedStyle(el.desk).direction,
  }, { height: node.offsetHeight });
  if (place === null) { hideScrollBubble(); return; }
  node.style.top = `${Math.round(place.centreY)}px`;
  node.style.left = `${Math.round(place.side === "left" ? place.edgeX : place.edgeX - node.offsetWidth)}px`;
  clearTimeout(scrollBubble.timer);
  clearTimeout(scrollBubble.fadeTimer);
  scrollBubble.fadeTimer = null;
  node.style.visibility = "visible";
  node.style.opacity = "1";
  node.dataset.shown = "1";
  scrollBubble.timer = setTimeout(hideScrollBubble, SCROLL_BUBBLE_HOLD_MS);
}

/** Scrolling stopped (or the view changed under it): fade, then take it out of the way. */
function hideScrollBubble() {
  clearTimeout(scrollBubble.timer);
  scrollBubble.timer = null;
  const node = scrollBubble.element;
  if (!node || node.dataset.shown !== "1") return;
  node.dataset.shown = "0";
  node.style.opacity = "0";
  const gone = () => { if (node.dataset.shown === "0") node.style.visibility = "hidden"; };
  clearTimeout(scrollBubble.fadeTimer);
  if (scrollBubble.reduced) { scrollBubble.fadeTimer = null; gone(); }
  else scrollBubble.fadeTimer = setTimeout(gone, SCROLL_BUBBLE_FADE_MS);
}

/* ------------------------------------------------------------------ state */

/* ------------------------------------------------- roadmap 3.4: the projection
 *
 * A screen reader cannot read a canvas, and this whole document is one canvas.
 * Measured 2026-08-22 on the core that DOES provide accessibility: 171
 * accessibility-tree nodes and not one carrying a character of the document
 * (findings/evidence/aria-projection/BASELINE.md). So what the engine knows --
 * which paragraph the caret is in and what it says -- has to be put somewhere
 * the browser will build a tree from.
 *
 * SCOPE, named here rather than discovered in testing: this projects the
 * FOCUSED paragraph, because that is what the engine hands over. It is not a
 * browsable document; browse mode would need every paragraph and the engine
 * gives exactly one.
 *
 * The honesty rules are the point, not the decoration:
 *
 *   * a profile that does not carry the text SAYS SO. An empty region reads to
 *     a screen reader as "document, blank" -- a confident wrong answer about
 *     the user's own file, and the same defect the engine already refuses one
 *     layer down by reporting `core-built-without-accessibility` instead of
 *     `enabled: true`.
 *   * `fresh` is checked, not just `enabled`. `fresh` is the bit that says the
 *     last read succeeded, and until 2026-08-22 the engine reported it true on
 *     a build where no read can succeed -- so a projection that trusted
 *     `enabled` alone would read out the hash of an empty string as if it were
 *     a paragraph.
 *   * `dataset.reason` records WHY the region says what it says, so a run can
 *     tell "the projection is off" from "the projection ran and had nothing".
 */
// One reason per CAUSE, not one per user-visible sentence.
//
// The first run of this projection came back with two of three placements
// saying `engine`, and `engine` covered four different things at once -- so
// the reading was "something upstream is unhappy" and the run could not say
// which. A diagnosis that cannot name the layer is the defect this tree writes
// down every time (040, 048, 062); here it was in the instrument rather than
// in a conclusion, which is the cheap place for it to be.
//
// Several map to the same sentence on purpose: a screen reader user does not
// need to hear the difference between an absent block and a disabled one.
// `dataset.reason` carries it for the run; the text does not.
const A11Y_REASONS = {
  paragraph: null,
  profile: "這一版引擎沒有提供段落文字，所以無法朗讀文件內容。",
  noDocument: "尚未開啟文件。",
  noParagraph: "無障礙資訊目前不可用。",
  disabled: "無障礙資訊目前不可用。",
  stale: "尚未讀到游標所在的段落。",
  noText: "尚未讀到游標所在的段落。",
};

function projectFocusedParagraph(snapshot, structureSpeaks) {
  const para = snapshot?.editorState?.caretParagraph;
  let reason = "paragraph";
  let text = null;
  if (!session?.document) reason = "noDocument";
  else if (!session.offersCaretParagraphText?.()) reason = "profile";
  else if (!para) reason = "noParagraph";
  else if (para.enabled !== true) reason = "disabled";
  else if (para.fresh !== true) reason = "stale";
  else if (typeof para.text !== "string") reason = "noText";
  else text = para.text;

  // ONE PARAGRAPH, ONE VOICE (finding 088's residue).
  //
  // Measured 2026-09-06 on the candidate page, with the owner listening: every
  // non-heading paragraph was spoken TWICE, ~117 ms apart, as two separate
  // utterances. The two headings were spoken once -- and the walk's own record
  // says why: `#a11y-para` was empty on the first heading and stale on the
  // second, while it carried the focused node's exact text on all eight of the
  // others. Ten stops, no exception: two channels carrying the same text ->
  // spoken twice; one channel -> once.
  //
  // So when the structure projection is already naming this paragraph through
  // `aria-activedescendant`, this region says nothing. It is NOT removed: on a
  // profile with no structure projection it is the only home the reason
  // sentences (「尚未開啟文件。」) have, and `structureSpeaks` is null there.
  // WHOEVER HAS THE FOCUSED NODE OWNS THE CARET PATH -- and comparing the two
  // texts was not enough.  Measured 2026-09-06 at an 11-second dwell, with the
  // owner listening: at the SECOND heading the live region still held the
  // previous paragraph's text and Orca spoke it, one utterance after the
  // heading.  The two channels are fed by two different engine fields
  // (`caretParagraph` and `documentOutline`) and they do not advance together
  // across a heading boundary, so for one snapshot they disagree -- and a rule
  // that only silenced them when they AGREED let the disagreement out loud,
  // saying the older of the two.
  //
  // So the test is not "do they say the same thing" but "does the structure
  // channel have a focused node at all".  A one-snapshot lag then costs one
  // voice arriving late instead of two voices contradicting each other.
  // `structureSpeaks` is null -- not "" -- exactly when there is no focused
  // node, which is every profile with no structure projection, where the live
  // region is still the only home the reason sentences have.
  const doubled = structureSpeaks !== null;
  const next = doubled ? "" : (text ?? A11Y_REASONS[reason]);
  // Compared before assigning, because an aria-live region announces when its
  // text CHANGES. updateState runs on every snapshot, and reassigning the same
  // string would be a repeat announcement of a paragraph the user is still
  // sitting in -- the projection would be talking over them.
  if (el.a11yPara.textContent !== next) el.a11yPara.textContent = next;
  el.a11yPara.dataset.reason = reason;
  // Said out loud in the DOM, so a probe can tell "silent because the structure
  // has it" from "silent because there is nothing to say".
  el.a11yPara.dataset.deferredToStructure = doubled ? "1" : "0";
  el.a11yDoc.dataset.offers = session?.offersCaretParagraphText?.() ? "1" : "0";
}

/* ----------------------------------------- roadmap 3.4: the structure half
 *
 * WCAG 2.1 1.3.1 is Level A: information and relationships conveyed through
 * presentation must be programmatically determinable. A canvas conveys "this
 * is a heading" by drawing it larger; the DOM has to say it in roles.
 *
 * Everything below is driven by data that was MEASURED first
 * (findings/evidence/aria-projection/TREE-SHAPE.md):
 *
 *   role        AccessibleRole -- an enum. NOT the paragraph style name, which
 *               is a localised UI string (finding 031: `標題 1` under zh-TW),
 *               so a role derived from it passes in en-US and fails silently
 *               in the market this is for.
 *   level       numberingLevel + 1 == the ODT outline-level. Measured across
 *               seven levels including a gap.
 *   list item   isNumbered, read AFTER role, because a heading also reports
 *               numbered (outline numbering is numbering).
 *   order       child index at depth 1. 133 of 133 on a long document.
 *
 * IT IS A CONTRACT FIELD NOW. It was `a11y.tree` -- the engine's diagnostic
 * dump -- while the shape was being measured, and `documentOutline` since
 * e2-editor-v5: the worker's named projection of the same walk, carrying role,
 * level, focus and text and none of the depths, child counts or state bits
 * E1-B forbids promoting. The manifest declares it, so a page can tell an
 * absent outline from an empty document before reading one.
 *
 * Designed from a measurement rather than ahead of one: the shape came from
 * TREE-SHAPE.md, and "emit it on every state read" is what the diagnostic
 * build had already been doing without trouble on a 133-paragraph document.
 */
// FINDING 088. What the projection looked like last time, so an unchanged
// document is not rebuilt under a screen reader's feet.
//
// The FOCUS FLAG IS DELIBERATELY NOT IN THE SIGNATURE. It changes on every
// caret move, which is exactly when the rebuild must NOT happen -- putting it
// in would leave the guard technically present and permanently useless, which
// is worse than no guard because it looks like one.
let lastStructureSignature = null;
let lastFocusedElement = null;
// FINDING 093. The paragraphs the last projection was built from, kept so a
// window resize can re-place the nodes without waiting for the next state
// read. The twips do not move when the window does; the scale from twips to
// CSS pixels does -- the same reason `layoutCanvas()` is followed by a repaint
// that calls `moveSinkToCaret`.
let lastProjectedParagraphs = null;

/**
 * FINDING 093. Whether THE PROFILE says it carries each paragraph's rectangle.
 *
 * Read from the MANIFEST and never from the payload, and the distinction is
 * the whole of this function's value: it separates "this engine was linked
 * before the geometry existed" from "this engine promised geometry and did not
 * deliver it". The first degrades honestly and is what every artifact linked
 * before 2026-09-08 does; the second is a defect -- an engine that stopped
 * emitting, or a worker allowlist that dropped the fields on the way through
 * (`sdk/sdk-worker.js`), which is a thing that has happened in this tree and
 * was invisible for weeks when it did.
 *
 * Declared exactly like `caretParagraphText` and `documentOutline`, for the
 * reason those two are: a host must be able to tell an absent capability from
 * an empty answer BEFORE it reads the field.
 */
function geometryDeclared() {
  const contract = session?.engine?.manifest?.editorContract;
  return contract?.documentOutlineGeometry === "accessible-paragraph-geometry";
}

/**
 * FINDING 093. Put each projected node where its own paragraph is drawn.
 *
 * This is 069's fix, applied to the class of element rather than to one more
 * instance of it: `#sink` rides the caret so an IME's candidate window and the
 * browser's scroll-into-view land where the user is looking; a projected node
 * has to ride ITS PARAGRAPH, because a screen reader's browse cursor moves
 * through the projection WITHOUT moving the caret. Measured 2026-09-08 on a
 * 133-paragraph document: riding the caret passes the arrow-key arm 3/3 and
 * the browse arm 1/3, and only per-paragraph placement passes both
 * (`findings/evidence/093/RESULT-phase3-fix-shapes.md`).
 *
 * THE SCALE IS `moveSinkToCaret`'s, deliberately not `paint()`'s: `box()` in
 * `paint()` works in BACKING pixels, which differ from CSS pixels by
 * devicePixelRatio, and positioning a DOM element with those puts it at
 * roughly twice the offset on a HiDPI screen. Same trap, same two lines, and
 * the comment in `paint()` is where it was first paid for.
 *
 * NOTHING HERE MAY REACH `signature` (finding 088). The signature decides
 * whether the whole projection is torn down and rebuilt, and geometry changes
 * on every scroll of a re-laid-out window -- putting it in would rebuild the
 * tree under a screen reader's feet on every resize, which is 088 exactly.
 * Positions are written onto the nodes in place, in both branches of the
 * keep-or-rebuild decision, which is why this is a separate pass.
 */
function positionProjection(paragraphs) {
  const declared = geometryDeclared();
  // #paper, the document's own box: since release C′ the canvas is a window
  // onto the document and only #paper spans it (on the P page the two were one).
  const width = el.paper.clientWidth;
  const height = el.paper.clientHeight;
  const scalable = Boolean(width && height && session?.document);
  const scaleX = scalable ? width / session.document.widthTwips : 0;
  const scaleY = scalable ? height / session.document.heightTwips : 0;
  // `carried` counts the PAYLOAD and not the placement, so a page that has not
  // been laid out yet cannot be mistaken for an engine that sent nothing.
  let carried = 0;
  let placed = 0;
  paragraphs.forEach((node, index) => {
    const element = document.getElementById(`a11y-node-${index}`);
    if (!element) return;
    const has = typeof node.y === "number" && typeof node.height === "number";
    if (has) carried += 1;
    const usable = declared && has && scalable;
    // Absolute in every case, including the degraded one. The container no
    // longer clips, so a node left in normal flow would paint its text across
    // the document; and a node with no position of its own is exactly finding
    // 093 -- it sits wherever the flow leaves it.
    element.style.position = "absolute";
    element.style.left = usable
      ? `${Math.round((typeof node.x === "number" ? node.x : 0) * scaleX)}px`
      : "0px";
    element.style.top = usable ? `${Math.round(node.y * scaleY)}px` : "0px";
    element.style.width = "1px";
    // The paragraph's own height, for the reason `moveSinkToCaret` gives the
    // sink the caret's: `scrollIntoView({block: "nearest"})` stops as soon as
    // the target's bottom edge reaches the viewport's, so a 1px target puts
    // the line being read entirely below the fold. Measured 2026-09-08: band
    // top exactly 864 in an 864px viewport, overlap 0, three times out of
    // three.
    element.style.height = usable
      ? `${Math.max(1, Math.round(node.height * scaleY))}px`
      : "1px";
    element.style.overflow = "hidden";
    element.style.whiteSpace = "nowrap";
    // The clip `#a11y-doc` gave up so that these nodes could have somewhere to
    // be. Invisible, still in the accessibility tree, and measured not to add
    // a hit-test target over the canvas.
    element.style.clipPath = "inset(50%)";
    if (usable) placed += 1;
  });
  // SAID OUT LOUD IN THE DOM, because "the projection is not placed" has three
  // causes that look identical from outside and only one of them is a defect.
  //
  //   absent               the profile does not declare geometry. Every
  //                        artifact linked before 2026-09-08. Honest.
  //   present              declared, and the payload carries it.
  //   declared-but-missing declared, and NOTHING came through. The engine
  //                        stopped emitting, or the worker allowlist dropped
  //                        the fields. A DEFECT, and the product path fails on
  //                        it.
  //
  // Per-paragraph misses are reported (`geometryCarried` against the node
  // count) and deliberately NOT judged: `getBounds()` has branches this tree
  // has never reached -- empty preview pages, a paragraph whose accessible
  // parent is not the root -- and a threshold on a distribution nobody has
  // measured would be a number invented ahead of the evidence.
  el.a11yStructure.dataset.geometry =
    !declared ? "absent"
      : (paragraphs.length > 0 && carried === 0) ? "declared-but-missing"
        : "present";
  el.a11yStructure.dataset.geometryCarried = String(carried);
  el.a11yStructure.dataset.geometryPlaced = String(placed);
}

function projectStructure(snapshot) {
  // THE CONTRACT FIELD, not the diagnostic tree.
  //
  // This read `a11y.tree` while the outline was being measured, and that field
  // carries depths, child counts and state bits -- diagnostic internals E1-B
  // forbids promoting. `documentOutline` is the worker's named projection of
  // the same walk: role as a product word, level, focus, text, and nothing
  // else. The manifest declares it, so the page can tell an absent outline
  // from an empty document before it reads one.
  const outline = snapshot?.editorState?.documentOutline;
  const nodes = Array.isArray(outline?.paragraphs) ? outline.paragraphs : null;
  // A TRANSIENT IS NOT AN EMPTINESS, and this is the measured reason for it:
  // two readings on 2026-08-23 came back with no tree at all, both immediately
  // after a keystroke, and both recovered on the next one. Blanking here would
  // announce an empty document in the middle of typing.
  if (!nodes) {
    el.a11yStructure.dataset.state = outline ? "transient" : "unavailable";
    // OUT OF THE TREE ENTIRELY when there is nothing to project.
    //
    // Measured: without this the shipped profile's accessibility tree went
    // 175 -> 176 -- one empty, unroled container. Inert, and still a change to
    // what a screen reader is handed on a profile this increment is not
    // supposed to touch. `aria-hidden` is the difference between "the shipped
    // page is unchanged" being true and being nearly true.
    //
    // NOT `hidden` and NOT `display:none`: those would also work here, but the
    // container has to come BACK when a profile does carry the data, and the
    // clip pattern above exists precisely because the display properties
    // remove a node from the tree permanently in ways that are easy to get
    // wrong. One mechanism for hiding, one for absence.
    el.a11yStructure.setAttribute("aria-hidden", "true");
    el.a11yStructure.replaceChildren();
    // The projection is absent or empty; the sink must not keep pointing into
    // a structure that is no longer there.
    el.sink.removeAttribute("aria-activedescendant");
    lastStructureSignature = null;
    lastFocusedElement = null;
    lastProjectedParagraphs = null;
    // FINDING 093. A fourth state, named rather than left as an absent
    // attribute: there is no projection at all, so there is nothing to place
    // and the geometry question does not arise. This is the shipped profile's
    // state, and it must not read as "declared and missing".
    el.a11yStructure.dataset.geometry = "noProjection";
    // Explicit: this channel speaks nothing, so the live region must speak.
    return null;
  }
  el.a11yStructure.removeAttribute("aria-hidden");
  const paragraphs = nodes;
  // FINDING 088. `replaceChildren` on every snapshot destroyed and recreated
  // the list containers and the very node `aria-activedescendant` points at,
  // so Orca announced "leaving list", "List with 2 items" and the item again
  // -- measured 2026-09-05: each paragraph spoken 2-6 times, `leaving list`
  // nine times and `List with 2 items` ten times, for a document with two
  // lists. The owner heard it before any instrument reported it.
  //
  // The live region has carried this guard since it was written
  // (`projectFocusedParagraph`, "reassigning the same string would be a repeat
  // announcement of a paragraph the user is still sitting in"). This is that
  // reasoning applied to the half that did not have it.
  const signature = JSON.stringify(
    paragraphs.map((node) => [node.role ?? null, node.level ?? null,
                              node.text ?? ""]));
  const fragment = document.createDocumentFragment();
  let list = null;
  let focusedId = null;
  let focusedText = null;
  let index = -1;
  for (const node of paragraphs) {
    index += 1;
    const text = node.text ?? "";
    const isList = node.role === "listItem";
    if (!isList) list = null;
    let element;
    if (node.role === "heading") {
      element = document.createElement("div");
      element.setAttribute("role", "heading");
      // The engine already returns a 1-based level (NumberingLevel + 1),
      // measured to equal the document's own ODT outline-level across seven
      // levels including a gap. ARIA levels are 1-based too, so it passes
      // straight through -- no arithmetic here, which is the point: the
      // conversion lives once, next to the measurement that justified it.
      element.setAttribute("aria-level", String(node.level ?? 1));
    } else if (isList) {
      if (!list) {
        list = document.createElement("div");
        list.setAttribute("role", "list");
        fragment.appendChild(list);
      }
      element = document.createElement("div");
      element.setAttribute("role", "listitem");
    } else {
      element = document.createElement("p");
    }
    element.textContent = text;
    // FINDING 087. Every projected node gets a stable id so the sink can point
    // at one of them; without an id there is nothing for
    // `aria-activedescendant` to name.
    element.id = `a11y-node-${index}`;
    if (node.focused === true) {
      element.dataset.focused = "1";
      focusedId = element.id;
      // What this channel will speak, returned so the live region can stay
      // quiet rather than say it again. The TEXT, not the id: the live region
      // has no id to compare against, and what a screen reader repeats is the
      // words.
      focusedText = text;
    }
    (isList ? list : fragment).appendChild(element);
  }
  if (signature === lastStructureSignature) {
    // Same document, same shape: move the focus marker and the pointer, and
    // leave every node where the accessibility tree already has it.
    if (lastFocusedElement) delete lastFocusedElement.dataset.focused;
    const kept = focusedId ? document.getElementById(focusedId) : null;
    if (kept) kept.dataset.focused = "1";
    lastFocusedElement = kept;
  } else {
    el.a11yStructure.replaceChildren(fragment);
    lastStructureSignature = signature;
    lastFocusedElement = focusedId ? document.getElementById(focusedId) : null;
  }
  // FINDING 093, and it is AFTER the branch above rather than inside it,
  // which is the whole reason it is a separate pass. Geometry is not in the
  // signature (it must not be -- see 088 above and `positionProjection`), so
  // the kept branch would otherwise leave every node at the position it had
  // before the document was edited.
  lastProjectedParagraphs = paragraphs;
  positionProjection(paragraphs);
  // FINDING 087, and the reason it is HERE rather than on the live region.
  //
  // The live region announces text; it does not announce the role on its own
  // node. MEASURED with Orca 2026-09-03
  // (findings/evidence/087/RESULT-mechanisms.md): `role="heading"` plus
  // `aria-level` placed on the live region produced speech carrying the text
  // and no role, twice, for two different roles. The obvious one-attribute fix
  // does not work, and its silence is not evidence of anything -- the
  // `paragraph` role already sitting there is one Orca never speaks either.
  //
  // What DOES work, measured in the same session: pointing the focused
  // textbox at a node that carries the role. Orca then announced "heading 1"
  // on the heading and "List with 2 items" on entering the list, announcing
  // the container once rather than on every item.
  //
  // `aria-owns` is required: `aria-activedescendant` may only name a
  // descendant of the element carrying it, or of something it owns, and the
  // projection is not inside the textarea.
  if (focusedId) {
    if (el.sink.getAttribute("aria-owns") !== el.a11yStructure.id)
      el.sink.setAttribute("aria-owns", el.a11yStructure.id);
    if (el.sink.getAttribute("aria-activedescendant") !== focusedId)
      el.sink.setAttribute("aria-activedescendant", focusedId);
  } else {
    // No focused paragraph in this projection: point at nothing rather than at
    // a stale node. A DANGLING activedescendant is worse than none -- it names
    // a node that no longer exists and an AT may announce the wrong paragraph.
    el.sink.removeAttribute("aria-activedescendant");
  }
  el.a11yStructure.dataset.state = "projected";
  el.a11yStructure.dataset.paragraphs = String(paragraphs.length);
  // The cap travels to the DOM too. A projection that silently stops at the
  // engine's limit would look like a short document; `truncated` is how a run
  // tells those apart without reading the engine's source.
  const count = outline?.paragraphCount;
  el.a11yStructure.dataset.truncated =
    (typeof count === "number" && count > paragraphs.length) ? "1" : "0";
  return focusedId ? focusedText : null;
}

/**
 * FINDING 125 (the owner chose A; SPEC-M3-production-ui §17.9 (d)): 「處理中」
 * only once `busy` has lasted 700 ms.  Every arrow key is an engine command,
 * so every press flashed it -- 40 presses, 40 flashes, 35-41 ms each, with
 * the document unchanged.  Collabora Online opens its busy popup 700 ms late
 * for the same reason (Control.UIManager.ts :644-689; prior art, no code
 * taken).
 *
 * Two pills, one inside the other.  `#state-pill` is the machine-read one:
 * its `data-state` is written at once on every state write, as before, and so
 * is `data-label`, the word the state stands for -- every runner reads it
 * unchanged, and its box, which a runner clicks for user activation, is the
 * child's.  The child, `#state-shown`, is what a person sees: it takes the
 * class `pill` (so the page's `.pill[data-state=...]` styles apply to it and
 * not to the parent) and shows every state at once EXCEPT `busy`, which it
 * shows only after 700 ms of it; until then it keeps the state it showed
 * before -- never blank.  Leaving `busy` shows the new state at once.  Not a
 * throttle or a debounce: no state is delayed, only the one word's display.
 * `#state-pill.textContent` is therefore the shown word now, not the state's.
 */
const BUSY_SHOWN_AFTER_MS = 700;
let busyShownTimer = null;

function installStateShown() {
  const shown = document.createElement("span");
  shown.id = "state-shown";
  shown.className = "pill";
  shown.dataset.state = el.statePill.dataset.state ?? "";
  shown.textContent = el.statePill.textContent;
  el.statePill.dataset.label = el.statePill.textContent;
  el.statePill.classList.remove("pill");
  el.statePill.replaceChildren(shown);
  return shown;
}
const stateShown = installStateShown();

function showState(state, label) {
  el.statePill.dataset.state = state;
  el.statePill.dataset.label = label;
  if (state === "busy") {
    if (busyShownTimer === null && stateShown.dataset.state !== "busy") {
      busyShownTimer = setTimeout(() => {
        busyShownTimer = null;
        stateShown.dataset.state = "busy";
        stateShown.textContent = label;
      }, BUSY_SHOWN_AFTER_MS);
    }
    return;
  }
  clearTimeout(busyShownTimer);
  busyShownTimer = null;
  stateShown.dataset.state = state;
  stateShown.textContent = label;
}

function updateState(snapshot) {
  noteAutosaveState(snapshot);
  noteCollapsedCaret(snapshot.editorState);
  notePageRectangles(snapshot);
  showState(snapshot.state, {
    idle: "未開啟", loading: "載入中", ready: "就緒", busy: "處理中",
    "recoverable-error": "需要回復", "restart-required": "需要重新開啟",
    stopped: "已停止",
  }[snapshot.state] ?? snapshot.state);
  el.s.state.textContent = snapshot.state;
  el.s.revision.textContent = snapshot.revision ?? "—";
  el.s.pending.textContent = snapshot.pending ?? "—";
  el.s.generation.textContent = snapshot.generation ?? "—";
  el.s.checkpoint.textContent = snapshot.hasCheckpoint
    ? `有（r${snapshot.checkpointRevision ?? "?"}）`
    : snapshot.checkpointError ? "寫入失敗" : "無";
  // ORDER IS LOAD-BEARING NOW: the structure projection decides what it will
  // name, and the live region needs that answer to know whether to stay quiet.
  // Reading the DOM attribute instead would read the PREVIOUS snapshot's value,
  // which is the shape of bug this file has paid for twice.
  const structureSpeaks = projectStructure(snapshot);
  projectFocusedParagraph(snapshot, structureSpeaks);
  const notice = recoveryNotice(snapshot);
  el.notice.dataset.show = notice.visible ? "1" : "0";
  // The decision, stamped where a reader can see it: hosts may differ in
  // wording, they may not differ in whether they claim work was preserved.  A
  // check that asserts the wording would go green the day somebody rephrases
  // the sentence; this is the thing that must not change.
  el.notice.dataset.rescue = notice.canRescue ? "checkpoint"
    : notice.checkpointFailed ? "failed" : "none";
  if (notice.visible) {
    el.noticeText.textContent = notice.canRescue
      ? "這一步可能已經改到文件，而且無法驗證。回到選取手勢前的檢查點。"
      : notice.checkpointFailed
      ? "引擎需要重新開啟。我們試著先保住你的工作，那次存檔失敗了——自上次儲存以來的內容不會回來。"
      : "引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。";
    el.noticeAction.textContent = notice.canRescue
      ? "回到檢查點" : "重新開啟";
    // Finding 054 was this line reading a flag nothing writes.  It now comes
    // from the same module as everything else about this notice, which is the
    // point: one place decides, and re-deriving it here is what produced both
    // 054 and 061.
    el.noticeAction.disabled = !notice.restartPossible;
  }
  // B1.  At the generation ceiling the notice's restart would dispose the
  // engine and then be refused, so the page says what it did instead, and its
  // one button reloads the page (or, if nothing was attempted yet, saves).
  // The state is stamped for the same reason `data-rescue` is.
  if (notice.visible && session && !session.restartAvailable()) {
    const said = limitNotice();
    el.notice.dataset.limit = said.state;
    el.noticeText.textContent = said.text;
    el.noticeAction.textContent = said.action;
    el.noticeAction.disabled = said.disabled;
  } else {
    delete el.notice.dataset.limit;
  }
  updateGestureAffordance();
  updateRedoAffordance();
  updatePasteMarkdownAffordance();
  applySessionAvailability(snapshot);
  // Finding 058.  The caret arrives as a state update, not as a document
  // change, so redrawing only on render would leave it a gesture behind.
  paint();
  // L-134-RESTORE-FLASH (SPEC-M3-held-key §16).  Not while the page reopens the
  // engine after a refusal, until D has put the caret back or failed: the fresh
  // engine reports its caret at the document start, and following it took the
  // view there for about 0.7 s and back.  Collabora's Writer reconnect ignores
  // that caret for the same reason (findings/evidence/134/collabora-prior-art.md).
  // The skipped calls are not followed at all; the reopen follows once at its end.
  if (!reopening) followCaret();
}

let reopening = false;

// FINDING 136 (SPEC-M3-held-key §16; fable's ruling-3, addendum 4).  The caret D
// puts back after a reopen: the last one the engine pushed with no range
// selected.  A delete's barrier pushes its one-unit range as editor state, and
// a refusal at a cell end leaves that range in place -- its caret already in
// the next cell -- so the last pushed state is the barrier's, not the user's.
// Skipping ranges leaves the caret the last completed edit ended at, whatever
// the timing of the keys (a caret read when a delete is SENT is one character
// stale under a hold: the next delete goes out before the last one is done).
let lastCollapsedCaret = null;

function noteCollapsedCaret(editorState) {
  const caret = editorState?.caret;
  if (editorState?.selection?.collapsed === false) return;
  if (!Number.isFinite(caret?.x) || !Number.isFinite(caret?.y) || !Number.isFinite(caret?.height)) return;
  lastCollapsedCaret = caret;
}

/**
 * FINDING 124: the view follows the caret.  The arrow keys' default is
 * prevented (the sink would scroll itself), and nothing scrolled the desk in
 * its place: ArrowDown walked the caret off the bottom of the desk, measured
 * at the 15th press in Chrome and the 12th in Firefox, with `scrollTop` 0
 * throughout.
 *
 * Collabora Online's rule (CanvasTileLayer.js :1854-1922, :3027-, :3082-3135;
 * prior art, no code taken): only when the caret rectangle CHANGED, and only
 * when it is not wholly in view, the view is scrolled so the caret is in the
 * middle -- clamped to the desk's range.  A state write that leaves the caret
 * where it was never scrolls, so a user who wheeled away is not pulled back
 * until the caret moves again.  `#desk.scrollTop` only, not `scrollIntoView`,
 * which would scroll the host's page around this one too (069, 093).  Not
 * while a pointer drag is selecting (SPEC-M3-production-ui §17.9 (e)): the
 * caret is under the pointer, and following it would move the page under the
 * hand that is dragging -- named limit: no drag-autoscroll.  A drag's moves
 * are not remembered as followed, so the first caret after it is compared
 * with the one before it.
 *
 * Release C′ moves its window from the `scroll` event this causes.
 */
let followedCaret = null;

function followCaret() {
  const caret = session?.state?.snapshot?.editorState?.caret;
  if (!caret || !session?.document || drag.active) return;
  const key = `${caret.x} ${caret.y} ${caret.width} ${caret.height}`;
  if (key === followedCaret) return;
  followedCaret = key;
  const paper = el.paper.getBoundingClientRect();
  const view = el.desk.getBoundingClientRect();
  if (!paper.height || !view.height) return;
  const scale = paper.height / session.document.heightTwips;
  const top = paper.top + caret.y * scale;
  const bottom = top + Math.max(1, caret.height * scale);
  if (top >= view.top && bottom <= view.bottom) return;
  const centre = el.desk.scrollTop + (top + bottom) / 2 - (view.top + view.height / 2);
  el.desk.scrollTop = Math.max(0, Math.min(el.desk.scrollHeight - el.desk.clientHeight, centre));
}

/**
 * Grey a button out when the manifest does not offer that action for the shape
 * of selection currently in front of it.
 *
 * SPEC E2-C 2.5: the declaration for the ten inherited actions is `collapsed`
 * only, and the engine does not enforce it -- the mask is read on the paragraph
 * route alone.  The honest place to surface a narrowing nothing enforces is the
 * button, not a failure after the fact.
 */
function updateGestureAffordance() {
  // THE PAGE'S BELIEF, SAID OUT LOUD.
  //
  // `lastSelectionShape` is a module local, so until now the only way to read
  // it from outside was to infer it from which buttons went grey -- and that
  // inference broke the moment `e2-editor-v7` offered the four inline formats
  // for ranges, because `an-aborted-gesture-stops-selecting` used exactly that
  // proxy ("are the format buttons disabled?") to mean "is a range selected?".
  // Widening the manifest silently disarmed a check.  A belief a check has to
  // guess at is a belief that will be guessed at wrongly.
  el.toolbar.dataset.selectionShape = lastSelectionShape;
  if (!session?.editor) return;
  for (const button of el.toolbar.querySelectorAll("button[data-action]")) {
    const action = button.dataset.action;
    if (!EDITOR_V2_ACTIONS.includes(action)) continue;
    const gestures = session.gesturesFor(action);
    const offered = !Array.isArray(gestures) || gestures.includes(lastSelectionShape);
    button.disabled = !offered;
    button.title = offered ? "" :
      `manifest 沒有為「${lastSelectionShape}」宣告這個動作`;
  }
  // `aria-pressed` is set only when the answer is KNOWN: a button that renders
  // a state it is guessing at is the trap the toggle bug already was, one layer
  // up.  All four now, because since the 2026-08-19 relink the engine keeps a
  // cache for underline and strikethrough too -- they were always in core's
  // GetKitUnoCommandList and always broadcast; nobody had written the cache,
  // and this list was hard-coded to the two that had one.
  for (const action of ["set-bold", "set-italic", "set-underline",
                        "set-strikethrough"]) {
    const button = el.toolbar.querySelector(`[data-action="${action}"]`);
    if (!button) continue;
    const state = formatStateFor(action);
    if (state === null) button.removeAttribute("aria-pressed");
    else button.setAttribute("aria-pressed", state ? "true" : "false");
  }
  applyControlMutability();
}

// SPEC-M3-page-honesty §7.1 (V7).  Every toolbar control carries whether it
// changes the document, asked of the session -- the same set its view-only
// gate uses, and fail-closed, so a control the session does not know as a move
// counts as a change.  In view-only that alone decides `disabled`.  It runs at
// the end of updateGestureAffordance because that function re-sets the action
// buttons on every state update, and would otherwise switch them back on.
function applyControlMutability() {
  if (typeof session?.actionMutates !== "function") return;
  for (const button of el.toolbar.querySelectorAll("button")) {
    const mutates = session.actionMutates(button.dataset.action ?? button.id);
    button.dataset.mutates = mutates ? "1" : "0";
    if (viewOnly && mutates) button.disabled = true;
  }
}

// FINDING 109, the half the owner saw first: in `restart-required` every button
// still looked pressable, and each press answered EDITOR_NOT_READY.  Outside
// ready/busy the session refuses every operation before queueing it
// (EditorSession._enqueue), so the toolbar says so.  Runs after the two passes
// above, which re-enable the action buttons on every update; a button this
// turned off is marked, so that only those are given back -- one disabled for
// another reason (view-only, the manifest) stays as that reason left it.
// 📂 is not a session operation, and outside a host it is a way out.
function applySessionAvailability(snapshot) {
  const accepting = SESSION_ACCEPTS.has(snapshot.state);
  for (const button of el.toolbar.querySelectorAll("button")) {
    if (button === el.openFile) continue;
    if (!accepting) {
      if (!button.disabled) button.dataset.unavailable = "1";
      button.disabled = true;
    } else if (button.dataset.unavailable === "1") {
      delete button.dataset.unavailable;
      if (!EDITOR_V2_ACTIONS.includes(button.dataset.action)) button.disabled = false;
    }
  }
  if (accepting) applyControlMutability();
}

/**
 * Show 重做 only on a profile that carries redo.
 *
 * HIDDEN rather than DISABLED, and the difference is the point: a disabled
 * button says "this exists but not right now", which is a promise about a
 * later moment that will never arrive on this profile. Redo is absent from the
 * contract until the ABI 4 artifact, so on anything older there is nothing to
 * say.
 *
 * The same rule kept Ctrl+A unbound and kept Up/Down out of the key map until
 * the manifest carried their action.
 */
function updateRedoAffordance() {
  const button = el.toolbar.querySelector('[data-action="redo"]');
  if (!button) return;
  button.hidden = !session?.offersRedo?.();
}

/**
 * Show 「貼上為 Markdown…」 only on a profile that declares the paste
 * (SPEC-M3-link-batch-v21 4.2, 11.2 M8).  Hidden, not disabled, for redo's
 * reason above: on v20 there is no such operation at all, and a disabled
 * button would promise one.  This entry IS the product's switch for the
 * feature (9.2): if M1-M6 do not hold, the entry goes and the SDK path stays
 * callable (L-md-sdk-callable).  In v21 it was off (PASTE_MARKDOWN_ENTRY_SHIPS,
 * finding 153, v21 §12.3 (e)); v22 turns it on (v22 §11.2).
 *
 * The session is asked first and every time, whatever the switch says: the
 * shakedown's page hook (tools/v21_page_hook.py) captures the page's session
 * through this call on every state update.
 */
function updatePasteMarkdownAffordance() {
  const button = el.toolbar.querySelector('[data-action="paste-markdown"]');
  if (!button) return;
  const offered = session?.offersPasteMarkdown?.() === true;
  button.hidden = !(PASTE_MARKDOWN_ENTRY_SHIPS && offered);
}

/* ----------------------------------------------------------------- canvas */

/**
 * Release C′, §17.9 (a): how many document rows the canvas holds.
 *
 * Three times what the desk shows -- the view, and one view's worth either
 * side to scroll into before the window has to move -- but never under four
 * bands, and never more than the document.  Four is the fewest bands that hold
 * one whole A4 page at the width cap (2400 x 1.374 = 3,297.6 rows; three bands
 * are 3,069), and it is the term that decides in every window this tree
 * measures in: 3 x 540 x 2 = 3,240 at 1400 x 1000 and ratio 2, and Chrome's
 * default 800 x 600 leaves a 139-pixel desk.  `scale` is backing pixels per CSS
 * pixel, the canvas's own, not devicePixelRatio (the width cap breaks the
 * equality).
 */
function windowRows(documentRows, deskHeight, scale) {
  return Math.min(documentRows,
                  Math.max(3 * Math.floor(deskHeight * scale), 4 * RENDER_BAND_HEIGHT));
}

/** The window's first row for a view of document rows [top, bottom): the view centred, inside the document. */
function windowTopFor(top, bottom, rows) {
  if (rows >= docRows) return 0;
  return Math.min(docRows - rows, Math.max(0, Math.round((top + bottom) / 2 - rows / 2)));
}

/** Put the canvas over document rows [winTop, ...), in #paper's CSS pixels. */
function placeCanvas() {
  const paperHeight = parseFloat(el.paper.style.height) || 0;
  el.canvas.style.top = docRows ? `${winTop * paperHeight / docRows}px` : "0px";
}

/**
 * §17.11: the window and the bands, said where a reader can see them -- the
 * window as `docRows winTop W`, the counter, and each cached band as
 * `index:top:rows:label`.  For C1, C3 and C4 and for the harness's ink reads;
 * not a feature.
 */
function publishWindow() {
  el.canvas.dataset.window = `${docRows} ${winTop} ${el.canvas.height}`;
  el.canvas.dataset.changes = String(changes);
  el.canvas.dataset.bands = lastTiles
    .map((strip, index) => (strip ? `${index}:${strip.y}:${strip.image.height}:${strip.label}` : null))
    .filter(Boolean).join(" ");
}

function layoutCanvas() {
  if (!session?.document) return;
  const available = Math.max(320, el.desk.clientWidth - 40);
  const cssWidth = Math.min(available, 900);
  const ratio = session.document.heightTwips / session.document.widthTwips;
  const backingWidth = Math.min(MAX_BACKING_WIDTH,
                                Math.round(cssWidth * (globalThis.devicePixelRatio || 1)));
  const cssHeight = Math.round(cssWidth * ratio);
  // Release C′: #paper is the document's size -- what the canvas's CSS size
  // was -- and the canvas a window of it, at the same rows per CSS pixel, so a
  // document row lands on the screen where it always did.  Styles set here and
  // not in e2-editor.html, which is outside the hash net (finding 094) and
  // shipped by the host as it is.
  docRows = Math.round(backingWidth * ratio);
  el.paper.style.width = `${cssWidth}px`;
  el.paper.style.height = `${cssHeight}px`;
  el.paper.style.touchAction = "none";
  const rows = windowRows(docRows, el.desk.clientHeight, backingWidth / cssWidth);
  el.canvas.width = backingWidth;
  el.canvas.height = rows;
  el.canvas.style.position = "absolute";
  el.canvas.style.left = "0px";
  el.canvas.style.width = `${cssWidth}px`;
  el.canvas.style.height = `${rows * cssHeight / docRows}px`;
  // Around what the desk shows now, which also brings the window back inside
  // a document that got shorter (finding 118's relayout).
  const [top, bottom] = visibleDocRows();
  winTop = windowTopFor(top, bottom, rows);
  placeCanvas();
  // Setting width/height clears the canvas AND invalidates the cached tile,
  // which is sized in device pixels for the old dimensions -- and takes the
  // overlay drawn on it along.
  lastTiles = [];
  paintedOverlay = NO_OVERLAY;
  publishWindow();
  // FINDING 093. The projection's nodes are placed in CSS pixels derived from
  // twips, so the scale that produced them has just changed and every node is
  // now pointing at the wrong line. This is the one place the scale moves, so
  // it is the one place that has to say so -- `projectStructure` runs on state
  // reads, and a resize is not one.
  if (lastProjectedParagraphs) positionProjection(lastProjectedParagraphs);
  // The view's rows changed too: the page number is recomputed, not re-read.
  updatePageStatus();
}

/**
 * Release C′: the desk scrolled.  When what it shows comes within a quarter
 * window of the canvas's edge -- the window is three views tall, so the middle
 * view can travel three quarters of a view either way first -- the window is
 * centred on the view again, IN THIS TASK: the canvas moves, every band the
 * cache still holds is put back where it now falls, rows nothing holds are
 * cleared, the overlay is drawn, and a repaint is asked for.  The scroll itself
 * stays the browser's; the canvas moves with the content.
 *
 * §17.9 (g) S1: nothing when the window would not move -- the whole document
 * on the canvas, or the window already against the document's end.
 */
function onDeskScroll() {
  updatePageStatus();   // the page number follows the view; no engine call (§10.8)
  showScrollBubble();   // SPEC-M3-scroll-page-bubble §3.3: any scroll of the desk, from the line just set
  if (!session?.document || !docRows) return;
  const rows = el.canvas.height;
  if (rows >= docRows) return;
  const [top, bottom] = visibleDocRows();
  const margin = rows / 4;
  if (top >= winTop + margin && bottom <= winTop + rows - margin) return;
  const next = windowTopFor(top, bottom, rows);
  if (next === winTop) return;
  moveWindow(next);
}

function moveWindow(next) {
  winTop = next;
  placeCanvas();
  const bands = renderBands(docRows);
  for (const band of bands) if (!bandInWindow(band)) lastTiles[band.index] = null;
  // Said before anything is drawn at the new place, so that nothing on the
  // canvas is ever described by the window it left.
  publishWindow();
  const context = el.canvas.getContext("2d");
  for (const band of bands) {
    if (!bandInWindow(band)) continue;
    const strip = lastTiles[band.index];
    if (strip) context.putImageData(strip.image, 0, strip.y - winTop);
    else context.clearRect(0, band.top - winTop, el.canvas.width, band.rows);
  }
  // Every row of the canvas was just replaced, so no overlay is on it: draw
  // the current one whole.
  const shapes = overlayShapes() ?? NO_OVERLAY;
  drawOverlay(context, shapes);
  paintedOverlay = shapes;
  void renderDocument();
}

/** Does this band overlap the canvas's rows [winTop, winTop + canvas.height)? */
function bandInWindow(band) {
  return band.top < winTop + el.canvas.height && band.top + band.rows > winTop;
}

// The BUSY budget.  Every engine command is BUSY while a delete barrier is in
// flight (probe_engine.cpp `dispatch`), and SPEC-M3-paragraph-merge 10.1(g):
// a boundary delete that presses the user's own key can hold the barrier up to
// about 8 s (unit caret 2000 ms + two restore presses 2000 ms each + the key's
// deadline 2000 ms).  Six retries (720 ms) turned a correct merge into
// 「重繪失敗」; 84 x 120 ms covers ten seconds.
const RENDER_BUSY_RETRIES = 84;

// FINDING 122: the band height, in device pixels -- a thirty-second of the
// engine's tile limit (1023; about 1/22 of the owner's document per request).
// Derived from MAX_TILE_HEIGHT on purpose: the product-path net's
// `one-tile-for-the-whole-document` mutation raises that constant to reintroduce
// 062's blank long document, and with a band height of its own that mutation
// would quietly stop biting.  Derived, raising the limit still makes a band
// taller than the engine will paint.
//
// A sixteenth (2047) until SPEC-M3-production-ui §15.6 (fable's third ruling,
// B): a typed character waits behind the band in flight, and then for the
// visible band to render, and in Firefox each 2047-row band took 18-20 ms --
// commit max 93.4 ms at 80 ms between keys.  Halving the band halves both
// waits; a band's cost is close to proportional to its rows, so a full pass
// grows only by the per-request overhead.
const RENDER_BAND_HEIGHT = Math.floor(MAX_TILE_HEIGHT / 32);

/**
 * The canvas cut into bands: pixel edges, no gap, no overlap.  Every band is
 * RENDER_BAND_HEIGHT rows but the last, which is between half a band and a
 * band and a half -- or the whole canvas, when that is under half a band.
 *
 * FINDING 123: the last band used to be whatever was left, and could be a few
 * dozen rows that are mostly the transparent gap below the last page (19 rows
 * at devicePixelRatio 2 on the owner's document, all of them gap).  062's
 * `tileWasPainted` cannot tell that from a band the engine never drew, so every
 * pass ended in 「重繪失敗：TILE_NOT_PAINTED」 and the last band was never
 * blitted.  A last piece under half a band joins the band above it; the guard
 * stays as it is.
 */
function renderBands(total) {
  const bands = [];
  for (let top = 0, index = 0; top < total; top += RENDER_BAND_HEIGHT, index += 1)
    bands.push({ index, top, rows: Math.min(RENDER_BAND_HEIGHT, total - top) });
  if (bands.length > 1 && bands.at(-1).rows < RENDER_BAND_HEIGHT / 2) {
    const short = bands.pop();
    bands.at(-1).rows += short.rows;
  }
  return bands;
}

/**
 * The bands in the order to paint them: those overlapping the visible rows
 * first, then the rest by their distance from the visible rows, nearest first;
 * ties keep document order.
 *
 * FINDING 132 / L-128-rapid (SPEC-M3-held-key §3.1): among the visible bands,
 * those holding the caret (`caretRows`, document rows) come first.  A pass is
 * ended by the next key after the band in flight, so under a held key its first
 * band is the only one ever painted -- and that was always the top of the view:
 * with the caret in the second band the deleted text stayed on screen until the
 * key was released and the queue had drained (1.8 s after a 2 s hold).  A caret
 * outside the view does not jump the queue; the user is looking at the view.
 */
function bandOrder(bands, [visibleTop, visibleBottom], caretRows = null) {
  const distance = (band) => {
    const end = band.top + band.rows;
    if (end > visibleTop && band.top < visibleBottom) return 0;
    return band.top >= visibleBottom ? band.top - visibleBottom : visibleTop - end;
  };
  const holdsCaret = (band) => caretRows !== null
    && band.top < caretRows[1] && band.top + band.rows > caretRows[0];
  return bands.map((band) => {
    const d = distance(band);
    return { band, d, caret: d === 0 && holdsCaret(band) ? 0 : 1 };
  })
    .sort((a, b) => a.d - b.d || a.caret - b.caret || a.band.index - b.band.index)
    .map((entry) => entry.band);
}

/** The document rows the engine's caret covers, or null when it has not said. */
function caretDocRows() {
  const caret = session?.state?.snapshot?.editorState?.caret;
  const heightTwips = session?.document?.heightTwips;
  if (!caret || !heightTwips || !docRows) return null;
  const scale = docRows / heightTwips;
  return [Math.floor(caret.y * scale), Math.ceil((caret.y + caret.height) * scale)];
}

/**
 * The document rows (device pixels) visible inside the desk; the top rows when
 * unknown.  Measured on #paper, the document's box, since release C′ made the
 * canvas a window (the P page measured the canvas, which was the document).
 */
function visibleDocRows() {
  const paper = el.paper.getBoundingClientRect();
  const view = el.desk.getBoundingClientRect();
  if (!paper.height) return [0, Math.min(docRows, RENDER_BAND_HEIGHT)];
  const scale = docRows / paper.height;
  const top = Math.max(view.top, paper.top) - paper.top;
  const bottom = Math.min(view.bottom, paper.bottom) - paper.top;
  if (bottom <= top) return [0, Math.min(docRows, RENDER_BAND_HEIGHT)];
  return [Math.floor(top * scale), Math.ceil(bottom * scale)];
}

async function renderDocument(retriesLeft = RENDER_BUSY_RETRIES) {
  if (!session?.document
      || !["ready", "busy"].includes(session.state.snapshot.state))
    return;
  if (rendering) { renderAgain = true; return; }
  rendering = true;
  // Set when a BUSY retry takes over: the retry has already set `rendering`
  // again, and this call's `finally` must not clear it while the retried
  // request is in flight -- it did (`return renderDocument(...)` does not wait
  // for the promise), so a repaint asked for in that window started a second
  // loop (review N4, 2026-10-07; measured with a stub: two in flight).  With B
  // a barrier keeps the engine BUSY for up to about 8 s.
  let retried = false;
  try {
    // FINDING 122 (SPEC-M3-production-ui §15; fable's ruling B′).  This used to
    // ask for the whole canvas -- the whole document, about 80 MB of pixels on
    // the owner's 22 pages -- in one request after every change, and the next
    // typed character's insert waited behind it in the document Worker: each
    // key showed up about 150 ms late, and typing faster than that fell
    // further behind (measured, findings/evidence/typing-latency/).
    //
    // Now: bands of RENDER_BAND_HEIGHT, the bands under the view first and the
    // rest nearest first (Collabora Online orders its tiles the same way,
    // BitmapTileManager.ts `distanceFromView`; prior art, no code taken), each
    // blitted as it arrives.  The page asks for band k+1 only after band k
    // replies, so a typed character posted meanwhile reaches the engine first;
    // and a change arriving between bands (`renderAgain`) ends this pass, so
    // the next one starts again with what the user is looking at.  A band
    // keeps its old pixels until its new ones arrive -- nothing is cleared --
    // and once the page is quiet the last pass has covered every band.
    //
    // The pixel edges, and the twips edges derived from them, are 062's: no
    // seam, no overlap, no rounding that accumulates.
    //
    // Release C′ (§17.2 as amended by §17.9 (c)): a pass asks only for the
    // bands that overlap the window AND are stale -- not cached, or stamped
    // with a counter value below the current one.  Each band is stamped when
    // it is ASKED for, so a band whose request was in flight across a change
    // stays stale and is asked for again.  Bands outside the window are not
    // asked for at all: they are not cached, so whenever one comes into the
    // window it is stale and the pass that follows the move paints it.  After
    // any change every band in the window is painted again -- today's
    // behaviour, confined to the window.
    let documentResized = false;
    const total = docRows;
    const documentHeight = session.document.heightTwips;
    const bands = renderBands(total);
    if (lastTiles.length !== bands.length) lastTiles = new Array(bands.length).fill(null);
    const stale = (band) => !lastTiles[band.index] || lastTiles[band.index].label < changes;
    const wanted = bands.filter((band) => bandInWindow(band) && stale(band));
    for (const band of bandOrder(wanted, visibleDocRows(), caretDocRows())) {
      if (renderAgain) break;   // a newer change arrived; the next pass starts with the view
      if (!bandInWindow(band)) continue;   // the window moved; that move asked for a pass
      const label = changes;
      const yTwips = Math.round((band.top / total) * documentHeight);
      const endTwips = Math.round(((band.top + band.rows) / total) * documentHeight);
      const tile = await session.document.render({
        xTwips: 0, yTwips,
        widthTwips: session.document.widthTwips,
        heightTwips: endTwips - yTwips,
        canvasWidthPx: el.canvas.width,
        canvasHeightPx: band.rows,
      }, { timeoutMs: 60000 });
      // Finding 062's second half: until the engine started reporting it, a
      // document that grew a page left this canvas sized from the height it
      // had when it was opened, and nothing could tell.  The SDK has already
      // updated the handle by the time this returns, so re-laying out picks up
      // the new height.
      //
      // FINDING 118: and it is acted on BEFORE the painted test.  A band asked
      // against a height the document no longer has is not a fair question: a
      // document that LOST a page answers it with everything below its new end
      // unpainted, the test below threw, and the size change was lost with the
      // band -- the canvas kept two pages' rows for every later repaint.  So
      // stop, re-lay out, ask again.  The engine reports a change once, so the
      // next reply says false and a genuinely unpainted band (062) is still
      // caught, one request on.
      if (tile.documentSizeChanged) { documentResized = true; break; }
      if (!tileWasPainted(tile)) {
        throw Object.assign(
          new Error("引擎回了一張沒有畫進去的圖"),
          { code: "TILE_NOT_PAINTED" });
      }
      // A band the window left while it was in flight is not kept: the cache
      // holds the window only, and the band is stale wherever it comes back.
      if (!bandInWindow(band)) continue;
      const strip = {
        image: new ImageData(new Uint8ClampedArray(tile.pixels),
                             tile.width, tile.height),
        y: band.top,
        label,
      };
      lastTiles[band.index] = strip;
      paintBand(strip);
      publishWindow();
    }
    // Bounded (§17.2): whatever the window does not overlap is dropped.
    for (const band of bands) if (!bandInWindow(band)) lastTiles[band.index] = null;
    publishWindow();
    if (documentResized) {
      // Through `renderAgain` rather than by recursing here: that is the
      // path this function already uses to coalesce a repaint, and the
      // `finally` below is what runs it.  It terminates because the engine
      // reports a CHANGE, so the next reply for an unchanged document says
      // false.
      // SPEC-M3-link-batch §10.8: the size changed, so the page rectangles may
      // have too -- the one paint-side trigger for re-reading them.
      if (session?.document) pageRectangles.sizeChangeReported(session.document);
      layoutCanvas();
      renderAgain = true;
    }
    busyLeftToAction = false;   // finding 128: a pass got through
  } catch (error) {
    // A repaint that lands while a barrier is still settling comes back BUSY.
    // The canvas is a frame behind; the document is fine.
    // TILE_NOT_PAINTED is not transient: the same request will come back
    // unpainted every time, so retrying it would only make the user wait
    // longer for the same silence.
    // FINDING 128: an editor action is out, and `run()` repaints when it
    // returns (editorAction makes the repaint if it fails).
    if (error?.code === "BUSY" && engineActionsOut > 0) {
      busyLeftToAction = true;
      return;
    }
    if (error?.code === "BUSY" && retriesLeft > 0) {
      await new Promise((resolve) => setTimeout(resolve, 120));
      rendering = false;
      retried = true;
      return renderDocument(retriesLeft - 1);
    }
    // The page disposed this engine itself -- `restart()` (a boundary
    // refusal's reopen, the recovery notice) or `close()` -- while this repaint
    // waited for its reply, and the SDK rejects every pending request with
    // ENGINE_DISPOSED (document-sdk.js `dispose()`).  Nothing failed that the
    // user could act on, and the restart's own `run()` repaints the new
    // engine.  It toasted 「重繪失敗：ENGINE_DISPOSED」 beside the reopen's
    // sentence on the merge shakedown (2026-10-07: F01, C17), which M2-3
    // counts as a second toast.  Only this code: a crashed worker or a stale
    // handle is not the page's own doing and is still said.
    if (error?.code === "ENGINE_DISPOSED") return;
    toast(`重繪失敗：${describeError(error)}`, true);
  } finally {
    if (!retried) {
      rendering = false;
      if (renderAgain) { renderAgain = false; void renderDocument(); }
    }
  }
}

/**
 * Finding 058: draw the caret and the selection.
 *
 * The engine has always sent both -- `caret` and `selection.rectangles` reach
 * the page in `editorState`, and the page used the rectangles only to COUNT
 * them for gesture shape.  Its one drawing call pasted the tile.  LOK does not
 * paint the text cursor or the selection into tiles; they arrive as callback
 * rectangles for the client to draw, and the client never did.  So a user
 * clicked and saw nothing move, dragged and saw nothing highlight.
 *
 * Nine product-path checks were green throughout, because every one of them
 * reads the DOM or the saved ODT -- and all of those pass on a page that draws
 * nothing at all.
 *
 * The tile is cached so the overlay can be repainted on a caret move without
 * asking the engine for pixels again: a caret arriving as a state update must
 * not cost a full document render.
 */
/**
 * Did the engine actually draw into this buffer?
 *
 * Finding 062: above a certain height it returns a correctly sized buffer,
 * never draws into it, and reports success -- so the return value cannot be
 * trusted and the page has no other way to tell.  It can tell from the pixels,
 * cheaply, because an UNPAINTED buffer is all zeros including its alpha channel
 * while a page that is merely blank is opaque white.  So this asks about alpha
 * only, at a few hundred sample points: a bounded number of reads on a buffer
 * that can be a hundred megabytes.
 *
 * Deliberately not a colour test.  "Is there any dark pixel" would call a
 * genuinely blank page a failure, and a blank page is a thing documents have.
 *
 * And deliberately a MAJORITY, not "any opaque pixel".  The first version
 * returned true on the first non-zero alpha it found, and an unpainted buffer
 * is not uniformly zero -- measured, 88 of 2,105,340 sampled points are not,
 * and one of them near the start defeats the whole test.  A painted tile is
 * about 90% opaque and an unpainted one is 0%, so half is a threshold with two
 * orders of magnitude of room on either side.
 */
function tileWasPainted(tile) {
  const pixels = new Uint8Array(tile.pixels);
  if (pixels.length === 0) return false;
  const samples = 512;
  const step = Math.max(4, Math.floor(pixels.length / 4 / samples) * 4);
  let seen = 0;
  let opaque = 0;
  for (let index = 3; index < pixels.length; index += step) {
    seen += 1;
    if (pixels[index] > 128) opaque += 1;
  }
  return seen > 0 && opaque * 2 >= seen;
}

/**
 * Release P (SPEC-M3-production-ui §16; R2 in §15.14): bring the caret and the
 * selection on the canvas up to date, and nothing else.
 *
 * This used to put every cached band back and draw the overlay over all of
 * them, on every state write -- about six a typed key, each one the whole
 * canvas (52 MB at 725 px, four times that at devicePixelRatio 2), 20 ms a
 * key in Chrome and 32-46 ms in Firefox, most of it before the insert was
 * even posted -- to move a caret two pixels wide.
 *
 * Now: an overlay equal to the one on the canvas costs nothing.  A different
 * one puts back the bands' own pixels under the old and the new rectangles
 * only -- each widened to whole pixels and one more, from the cached band by a
 * dirty-rectangle putImageData, or by clearRect where no band has been painted
 * yet, which is what is there -- and draws the overlay clipped to those
 * rectangles, so the selection's multiply wash never lands on itself.
 * Synchronous, like before: no throttle, no coalescing, nothing deferred.
 */
function paint() {
  if (!lastTiles.length) return;
  const next = overlayShapes() ?? NO_OVERLAY;
  if (next.key === paintedOverlay.key) {
    // No pixel changes; the sink still follows the caret, as it did when
    // every paint drew it (the CSS size it is placed by is not in the key).
    if (next.caretTwips) moveSinkToCaret(next.caretTwips);
    return;
  }
  const context = el.canvas.getContext("2d");
  const areas = [...overlayAreas(paintedOverlay), ...overlayAreas(next)];
  // Release C′: the areas are canvas rows, the bands document rows; a band
  // sits `winTop` rows higher on the canvas than in the document.
  const bands = renderBands(docRows);
  for (const [x, y, width, height] of areas) {
    for (const band of bands) {
      const bandTop = band.top - winTop;
      const top = Math.max(y, bandTop);
      const bottom = Math.min(y + height, bandTop + band.rows);
      if (bottom <= top) continue;
      const strip = lastTiles[band.index];
      const stripTop = strip ? strip.y - winTop : 0;
      if (strip) context.putImageData(strip.image, 0, stripTop, x, top - stripTop, width, bottom - top);
      else context.clearRect(x, top, width, bottom - top);
    }
  }
  context.save();
  context.beginPath();
  for (const [x, y, width, height] of areas) context.rect(x, y, width, height);
  context.clip();
  drawOverlay(context, next);
  context.restore();
  paintedOverlay = next;
}

/** An overlay's rectangles widened to whole pixels and one more, inside the canvas. */
function overlayAreas(shapes) {
  const areas = [];
  for (const [x, y, width, height] of [...shapes.selection, ...(shapes.caret ? [shapes.caret] : [])]) {
    const left = Math.max(0, Math.floor(x) - 1);
    const top = Math.max(0, Math.floor(y) - 1);
    const right = Math.min(el.canvas.width, Math.ceil(x + width) + 1);
    const bottom = Math.min(el.canvas.height, Math.ceil(y + height) + 1);
    if (right > left && bottom > top) areas.push([left, top, right - left, bottom - top]);
  }
  return areas;
}

/**
 * FINDING 122: one band that just arrived.  Its rows are replaced, and the
 * caret and the selection are drawn again INSIDE those rows only -- the
 * selection is a multiply wash, so drawing it over rows that were not just
 * replaced would darken it twice.  Everywhere else the overlay already on the
 * canvas is the current one: every overlay change goes through `paint()`.
 */
function paintBand(strip) {
  const context = el.canvas.getContext("2d");
  // Release C′, §17.9 (g) S2: `winTop` is taken NOW, when the band is drawn,
  // not when it was asked for -- the window may have moved while it was in
  // flight.
  const top = strip.y - winTop;
  context.putImageData(strip.image, 0, top);
  const shapes = overlayShapes() ?? NO_OVERLAY;
  context.save();
  context.beginPath();
  context.rect(0, top, el.canvas.width, strip.image.height);
  context.clip();
  drawOverlay(context, shapes);
  context.restore();
  paintedOverlay = shapes;
}

/**
 * FINDING 132's blue flash (SPEC-M3-held-key §3.3; SPEC-M3-autosave §9.18
 * item 2).  The editor state the overlay draws.  While a delete this page sent
 * is out, a range in the engine's state is the barrier's: it selects the one
 * character before deleting it, and the engine pushes that selection like any
 * other -- drawn, every delete washed that character blue for 7-11 ms (measured,
 * findings/evidence/132/baseline/).  Finding 131's reasoning: the delete out can
 * only come back to a caret, so the range is not the user's.  The overlay keeps
 * the state it drew before, rather than drawing the engine's caret of that
 * moment, which may already sit left of the character still on screen.
 */
function overlayEditorState() {
  const editorState = session?.state?.snapshot?.editorState;
  if (!(deletesInFlight > 0 && editorState?.selection?.collapsed === false)) overlayState = editorState;
  return overlayState;
}

/**
 * The caret and the selection as the canvas draws them, in backing pixels, or
 * nothing.  `key` holds everything the drawn pixels depend on -- the canvas
 * and document sizes and every rectangle -- so two overlays with one key draw
 * the same pixels.
 */
function overlayShapes() {
  const editorState = overlayEditorState();
  if (!editorState || !session?.document) return;

  // Rectangles are twips in document space; the canvas holds document rows
  // [winTop, winTop + height) since release C′, so a rectangle sits `winTop`
  // rows higher on it (on the P page the canvas was the whole document).
  const scaleX = el.canvas.width / session.document.widthTwips;
  const scaleY = docRows / session.document.heightTwips;
  const box = (r) => [r.x * scaleX, r.y * scaleY - winTop,
                      Math.max(1, r.width * scaleX),
                      Math.max(1, r.height * scaleY)];

  const shapes = { selection: [], caret: null, caretTwips: null };
  const rectangles = editorState.selection?.rectangles;
  if (Array.isArray(rectangles) && rectangles.length) shapes.selection = rectangles.map(box);

  // Drawn only when the selection is collapsed: LOK keeps sending a cursor
  // rectangle during a range selection, and painting a caret in the middle of
  // a highlight says something about the document that is not true.
  const caret = editorState.caret;
  if (caret && editorState.selection?.collapsed !== false) {
    const [x, y, , height] = box(caret);
    shapes.caret = [x, y, Math.max(1, Math.round(scaleX * 15)), height];
    shapes.caretTwips = caret;
  }
  shapes.key = JSON.stringify([el.canvas.width, el.canvas.height, winTop, docRows,
                               session.document.widthTwips, session.document.heightTwips,
                               shapes.selection, shapes.caret]);
  return shapes;
}

function drawOverlay(context, shapes) {
  if (shapes.selection.length) {
    context.save();
    // Multiply keeps the glyphs readable under the wash instead of covering
    // them, which a filled rectangle at any useful opacity would do.
    context.globalCompositeOperation = "multiply";
    context.fillStyle = "#b7d3f2";
    for (const rectangle of shapes.selection) context.fillRect(...rectangle);
    context.restore();
  }

  // The caret last, so it is never washed over by the selection it sits in.
  if (shapes.caret) {
    // The sink rides the caret.  Two reasons, and the second is the one that
    // was reported: an IME's candidate window opens next to the focused
    // element, so a sink parked elsewhere puts the candidates in the wrong
    // place; and the browser scrolls the focused element into view when
    // composition starts, which is harmless only if the sink is already where
    // the user is looking.  Parked at the bottom of the document, as it was
    // until 2026-08-22, that scroll dragged the whole desk down on every
    // Chinese keystroke.
    //
    // CSS pixels, from the canvas's DISPLAYED size -- the shapes are in
    // BACKING pixels, which differ by devicePixelRatio, and positioning a DOM
    // element with those would put the sink at roughly twice the offset on a
    // HiDPI screen.
    moveSinkToCaret(shapes.caretTwips);
    context.save();
    context.fillStyle = "#1a1a1a";
    context.fillRect(...shapes.caret);
    context.restore();
  }
}

function moveSinkToCaret(caret) {
  // #paper's size: the document's box (release C′; the canvas is a window).
  const width = el.paper.clientWidth;
  const height = el.paper.clientHeight;
  if (!width || !height || !session?.document) return;
  const scaleX = width / session.document.widthTwips;
  const scaleY = height / session.document.heightTwips;
  el.sink.style.left = `${Math.round(caret.x * scaleX)}px`;
  el.sink.style.top = `${Math.round(caret.y * scaleY)}px`;
  // Matching the caret's height rather than staying 1px tall: an IME places
  // its candidate window against the focused element's box, so a sink the
  // height of the text line puts the candidates on the line instead of
  // clipping them to a single pixel row.
  el.sink.style.height = `${Math.max(1, Math.round(caret.height * scaleY))}px`;
}

function pointToTwips(event) {
  // #paper's box, the document's (release C′): a point anywhere on the paper,
  // inside the canvas's window or not, is the same twips as on the P page.
  const rectangle = el.paper.getBoundingClientRect();
  return {
    xTwips: Math.max(0, Math.round(
      (event.clientX - rectangle.left) / rectangle.width
      * session.document.widthTwips)),
    yTwips: Math.max(0, Math.round(
      (event.clientY - rectangle.top) / rectangle.height
      * session.document.heightTwips)),
  };
}

/* ---------------------------------------------------------------- actions */

// FINDING 109.  A delete at a paragraph boundary -- Delete at a paragraph's
// end, Backspace at its start -- is refused by the engine before anything is
// dispatched, and the refusal asks for a fresh Worker.  This page used to show
// the code and the engine's English, leave every button looking pressable, and
// offer one way out, which reopened the last SAVED bytes: everything typed
// since was gone.  The session now banks the work as part of the refusal
// (NarrowEditorV2Session `_checkpointBeforeBoundaryRestart`), so when a restart
// would reopen exactly what the user had (`restartKeepsContent()`), this page
// performs it without asking -- there is nothing to decide, and the notice's
// only button would have done the same.  When it would NOT (the checkpoint
// could not be written), the recovery notice stays up and says so, as before.
//
// Merging the two paragraphs is engine work.  An engine built with
// OXSDK_MERGE_KEY_UNDO (e2-editor-v15) merges by pressing the user's own key and
// completes like any delete; what still reaches this path from it is a refusal
// it describes in `details.mergeKey` (boundaryText below).
const BOUNDARY_TEXT = "目前還不能在段落交界刪除（把兩段合併成一段）。文件沒有被改動";
const SESSION_ACCEPTS = new Set(["ready", "busy"]);

// SPEC-M3-paragraph-merge 10.1(d), 10.1(h), M1-5.  An engine built with
// OXSDK_MERGE_KEY_UNDO merges at a paragraph boundary by pressing the user's
// own key, and its refusals say what happened in `details.mergeKey` (the SDK
// puts a remote error's fields in `details`).  "Not changed" is said ONLY for
// the stages that end before the key is posted and before anything could have
// moved the undo payload; an unknown stage, `restore-mutated` (the payload
// moved during the restore) and anything with the key posted get the
// uncertain sentence.  Fail-closed on purpose: a future stage added to the
// engine and not here can only make the page say less.  Engines without B
// (v8, v14) send no mergeKey and keep the old sentence, which is true there.
const MERGE_KEY_UNCHANGED_STAGES = new Set([
  "nothing-selected", "anchor-mismatch", "restore", "return-mismatch", "unit-late",
  "undo-read",
]);

// FINDING 119 (spec SPEC-M3-production-ui §14.1).  A delete the selection
// barrier could not verify in time.  The session banked the content and blocked
// as restart-required, and marked it `recovery: "restart"` -- the field, not the
// message, decides.  One of the engine's exits for this code is (in theory)
// after the delete was posted, so this path never says "unchanged": every typed
// change is kept, the key's own effect is uncertain.
function deleteUnverified(error) {
  return error?.code === "EDITOR_STATE_UNAVAILABLE" && error?.recovery === "restart";
}

function reopensAfterRefusal(error) {
  return error?.code === "EDITOR_BOUNDARY_UNSUPPORTED" || deleteUnverified(error);
}

function boundaryKeyUncertain(error) {
  if (deleteUnverified(error)) return true;
  const mergeKey = error?.details?.mergeKey ?? null;
  return mergeKey !== null
    && !(mergeKey.keyPosted === false && MERGE_KEY_UNCHANGED_STAGES.has(mergeKey.stage));
}

function boundaryText(error) {
  if (deleteUnverified(error)) return "這一下刪除沒有完成";
  const mergeKey = error?.details?.mergeKey ?? null;
  if (!mergeKey) return BOUNDARY_TEXT;
  if (boundaryKeyUncertain(error)) return "這一下刪除送出了，但沒能確認它做了什麼";
  return mergeKey.stage === "nothing-selected"
    ? "這一下沒有取得可刪除的內容。文件沒有被改動"
    : "這裡目前還不能這樣刪除。文件沒有被改動";
}

async function reopenAfterBoundaryRefusal(error) {
  const lead = boundaryText(error);
  const uncertain = boundaryKeyUncertain(error);
  // When the queue blocks, everything queued behind the refused delete is
  // rejected with the same error, so this runs once per rejected item; only
  // the first finds the session still waiting for a restart.
  if (session?.state?.snapshot?.state !== "restart-required") return;
  reopening = true;
  try {
    // B1 (specs/SPEC-M3-production-ui.md §9).  FIRST, before anything that
    // restarts: `restart()` disposes the engine and only then meets the Worker
    // generation ceiling, so the third refusal of a page load used to end with
    // no engine, save refused, and the work alive only in the checkpoint.
    if (!session.restartAvailable()) {
      toast(`${lead}。這個頁面不能再重新載入編輯引擎了——請看上方的說明。`, true);
      await rescueAtGenerationLimit();
      return;
    }
    if (!session.restartKeepsContent()) {
      toast(`${lead}，但沒能先保住尚未儲存的修改——請看上方的說明。`, true);
      return;
    }
    const unsaved = session.state.snapshot.dirty === true;
    // FINDING 134, D (SPEC-M3-held-key §14).  A reopened engine has its caret at
    // the document start, and nothing said so: the next key or typed text landed
    // there, out of the user's sight.  The caret the engine last reported goes
    // back by a click at its middle -- the reopened document is the checkpoint of
    // the same content, laid out by the same engine.  Read before `restart()`:
    // its `ready` writes the new engine's state.  When there is no caret to go
    // back to or the click is refused, the toast says where the caret is.
    // Finding 136: the last caret the engine pushed with no range selected.
    const caret = lastCollapsedCaret ?? session.state.snapshot.editorState?.caret ?? null;
    toast(`${lead}，正在重新載入…`);
    try {
      // The refusal disabled the input sink (input-adapter `setBlocked`), and a
      // disabled element loses focus; without this the user's next keys went
      // to the page body (review 2026-10-06, item 3; measured on the pre-fix
      // page: the next three keys landed nowhere, both browsers).
      //
      // INSIDE the operation, the moment `restart()` returns -- the session is
      // `ready` and the sink enabled by then -- and NOT after `run()`, which
      // also awaits the repaint.  Focusing after the repaint lost the first key
      // typed once the pill said 就緒 (shakedown 2026-10-06, B3x Chrome: `z` of
      // `zqb` and of `zqc` landed nowhere, the next two keys did; review
      // 2026-10-06b item 10 had predicted it).  No scroll: the sink sits at the
      // caret, which a restart puts at the document start (the other two
      // `focus()` calls in this file pass the same; 069's class).
      const restored = await run("重新載入", async () => {
        await session.restart();
        el.sink.focus({ preventScroll: true });
        if (!Number.isFinite(caret?.x) || !Number.isFinite(caret?.y) || !Number.isFinite(caret?.height)) return false;
        const now = session.state.snapshot.editorState?.caret;
        if (now?.x === caret.x && now?.y === caret.y) return true;
        try {
          await session.placeCaret(caret.x, caret.y + caret.height / 2);
          return true;
        } catch {
          return false;
        }
      });
      // Not "everything is still there": keys typed just around the refused one
      // can be lost.  Typed text waits in the input adapter's own queue while
      // Delete goes straight to the session's, so a key typed BEFORE the refused
      // delete can still be behind it and be rejected with it (finding 111;
      // review 2026-10-06b item 4), and keys after it always are (review
      // 2026-10-06 item 2).  Said, rather than claimed away.
      toast(`${lead}，已重新載入${uncertain
        ? "。請看一下那個位置：這一鍵可能生效了，也可能沒有"
        : unsaved ? "。緊接在這一鍵前後打的字可能沒有打進去，請看一下" : ""}${
        restored ? "" : "。游標現在在文件開頭"}。`);
    } catch {
      // run() has already said why.
    }
  } finally {
    reopening = false;
    followCaret();
  }
}


const LIMIT_LEAD = "這個頁面不能再重新載入編輯引擎了。";
// The host's own sentence is the one to show on failure: a refused write may
// have landed as a conflict copy (named in that sentence, no download button)
// or been stranded (download button) -- review 2026-10-06b item 3.  Without a
// host, `saved` means the download was HANDED OVER, which the user can cancel
// (item 6).  `clean` claims nothing about earlier saves, which the host may
// have copied or stranded (item 8).
const LIMIT_TEXT = {
  saving: () => `${LIMIT_LEAD}正在把你的修改${HOST ? "存回" : "下載"}…`,
  saved: () => HOST
    ? `${LIMIT_LEAD}你的修改已經存回。請重新整理頁面，就能繼續編輯。`
    : `${LIMIT_LEAD}你的修改已經交給瀏覽器下載。確認下載好了，再重新整理頁面、開啟剛下載的檔案。`,
  failed: () => `${LIMIT_LEAD}${HOST ? "存回" : "下載"}沒有成功：${limit.detail ?? "原因不明"}`
    + "處理好之後再重新整理頁面。",
  clean: () => `${LIMIT_LEAD}請重新整理頁面，就能繼續編輯。`,
  lost: () => `${LIMIT_LEAD}自上次儲存以來的修改沒能保住。重新整理頁面就能繼續編輯。`,
  pending: () => `${LIMIT_LEAD}請先${HOST ? "存回" : "下載"}尚未儲存的修改，再重新整理頁面。`,
};

// B1: what this page load did at the generation ceiling.  `null` until a
// rescue is attempted; then `saving`, `saved`, `failed`, `clean` or `lost`.
// At most one attempt per page load: after it the session is clean (the
// content was handed out as saved), so a second attempt would find nothing
// and report `clean` over a failed write -- and a failed write is the host's
// to strand and offer for download (finding 108).
const limit = { state: null, detail: null };

/** What the notice says at the ceiling; `pending` = nothing attempted yet. */
function limitState() {
  if (limit.state !== null) return limit.state;
  if (!session.hasUnsavedEdits()) return "clean";
  return session.restartKeepsContent() ? "pending" : "lost";
}

/** The notice at the ceiling: its sentence, its one button, and whether it is live. */
function limitNotice() {
  const state = limitState();
  return {
    state,
    text: LIMIT_TEXT[state](),
    action: state === "pending" ? (HOST ? "存回" : "下載") : "重新整理頁面",
    disabled: state === "saving",
  };
}

/** The bytes a restart would have reopened, through the ordinary save path. */
function takeRescueContent() {
  const bytes = session.takeContentForRescue();
  if (!bytes) {
    const error = new Error("the session holds no bytes that keep its content");
    error.code = "RESCUE_UNAVAILABLE";
    throw error;
  }
  return { bytes };
}

async function rescueAtGenerationLimit() {
  if (limit.state !== null) return;
  // The same decision the notice shows, not a second derivation of it
  // (review 2026-10-06b item 2: the two could drift).
  const now = limitState();
  limit.state = now === "pending" ? "saving" : now;
  updateState(session.state.snapshot);
  if (limit.state !== "saving") return;
  try {
    await saveDocument(takeRescueContent);
    limit.state = "saved";
  } catch (error) {
    // The host's sentence says where the bytes went (a copy, or stranded
    // behind its download button); RESCUE_UNAVAILABLE says nothing was taken.
    limit.detail = error?.message ?? String(error);
    limit.state = "failed";
  }
  updateState(session.state.snapshot);
}

async function run(label, operation, { quiet = false } = {}) {
  const started = performance.now();
  try {
    const result = await operation();
    // §17.9 (c): a completed operation is a change, whether or not its
    // `document-invalidated` came before the engine finished with it.
    changes += 1;
    publishWindow();
    el.s.latency.textContent = `${label} ${Math.round(performance.now() - started)} ms`;
    await renderDocument();
    return result;
  } catch (error) {
    // Refused by the view-only gate: nothing was attempted, so nothing failed.
    if (error?.code === "EDITOR_VIEW_ONLY") {
      el.s.latency.textContent = `${label}：唯讀`;
      toast(VIEW_ONLY_TEXT, true);
      throw error;
    }
    el.s.latency.textContent = `${label} 失敗`;
    if (reopensAfterRefusal(error)) {
      void reopenAfterBoundaryRefusal(error);
      throw error;
    }
    // The disposition is a field, not a guess from the message (E2-B 5.13).
    const recovery = error?.recovery;
    // An autosave's host part: the host bar says where the bytes went and
    // keeps saying it (SPEC-M3-autosave §9.2); a toast nobody asked for would
    // say it once, in a developer's words.
    if (quiet) throw error;
    toast(`${label}：${describeError(error)}` +
          (recovery === "rollback"
            // B1: at the ceiling there is no 「回到檢查點」 to press.
            ? (session?.restartAvailable?.() === false ? "（請看上方的說明）"
               : "（可能已經改到文件：請回到檢查點）")
           : recovery === "restart" ? "（需要重新開啟文件）"
           // Finding 046's residual.  Says dispatched-and-unverified, and does
           // NOT say it worked -- the barrier did not verify it.  Undo is
           // named because "review" leaves the queue open, which is the only
           // reason that advice is honest.
           // Two different reasons reach `review`, and telling the user the
           // wrong one is worse than saying less.  The disposition is still
           // read from the field (E2-B 5.13); only the EXPLANATION is chosen
           // by code.
           : recovery === "review"
             ? (error?.code === "LOK_COMMAND_FAILED"
                // Finding 059.
                ? "（動作已送出，引擎收到了核心的回覆但無法據以判定成敗，"
                  + "所以這裡不敢說它成功了。請看一下結果，不是你要的就按「復原」）"
                // FINDING 083.  Its own sentence, and it needs one: this shape
                // reaches `review` because NOTHING was selected, so telling the
                // user the check "covered more than one paragraph" would be
                // literally false about their document.  Finding 061 is the
                // precedent -- a sentence that is true of a different case is
                // misleading attribution, and this tree has filed that as a
                // defect once already.
                : error?.details?.formatBarrier?.failureShape
                    === "stage-deadline:awaiting-selection"
                ? "（動作已送出，但這一段是空的，檢查要用的選取取不到任何內容，"
                  + "所以無法核對。請看一下結果，不是你要的就按「復原」。"
                  + "這是檢查的極限，不是文件壞了）"
                : "（動作已送出，但這一格的檢查涵蓋了不只一個段落，無法單獨核對你的段落。"
                  + "請看一下結果，不是你要的就按「復原」。這是檢查的極限，不是文件壞了）")
           : ""), true);
    throw error;
  }
}

// Finding 045, the product half.  The ENGINE has taken an explicit boolean
// since the v3 link -- `inlineFormatArgument` builds
// {"Bold":{"type":"boolean","value":...}} from it -- and this line sent `true`
// unconditionally, so from a user's seat bold could be turned on and never off.
// The fix shipped in the artifact and the page never used it.
//
// Bold and italic are decided from state: the worker already projects
// `format: {bold, italic}` as a tri-state (null = the engine does not know).
// Underline and strikethrough have no state to read -- OUR engine keeps no
// cache for them.  The reason probe_engine.cpp gives (that neither is in core's
// GetKitUnoCommandList) is false: both are in it
// (sfx2/source/control/unoctitm.cxx:1165ff) and both were measured broadcasting
// on 2026-08-18, findings/evidence/059/native/predicate/.  The cache is missing,
// not impossible -- so they
// stay one-way here and get their off path from 清除格式 below, which claims
// nothing about the current state.
//
// Note what the 045 fix buys beyond correctness: an explicit set is ROBUST
// under a stale read.  Guess wrong and the user presses again and it is right,
// because the second dispatch names the value it wants.  A toggle would turn a
// stale read into a silent no-op.
function formatStateFor(action) {
  const format = session?.state?.snapshot?.editorState?.format;
  // All four, since the 2026-08-19 relink gave underline and strikethrough the
  // state cache they never had.  `?? null` and not `||`: the engine says null
  // when it does not know, and "I do not know" must not read as "off".
  if (action === "set-bold") return format?.bold ?? null;
  if (action === "set-italic") return format?.italic ?? null;
  if (action === "set-underline") return format?.underline ?? null;
  if (action === "set-strikethrough") return format?.strikethrough ?? null;
  return null;
}

// The name to put in front of a failure, for actions that have no button.
//
// `editorAction` used to read the label straight off the toolbar button, which
// held only while every dispatchable action had one. The ABI 4 profile made
// four movements and delete-selection reachable from the keyboard with no
// button behind them, and `querySelector(...).textContent` on a null threw a
// TypeError BEFORE `run()` -- so the key was swallowed by preventDefault,
// nothing dispatched, and the call site's `.catch(() => {})` ate the evidence.
// A key that looks bound and does nothing, arrived at through a label lookup.
const ACTION_LABELS = {
  "move-line-up": "上移一行",
  "move-line-down": "下移一行",
  "move-line-home": "移到行首",
  "move-line-end": "移到行尾",
  "delete-selection": "刪除選取",
  // SPEC-M3-link-batch-v21 4.1: Ctrl/Cmd+Home and Ctrl/Cmd+End, no button.
  "move-document-start": "移到文件開頭",
  "move-document-end": "移到文件結尾",
};

async function editorAction(action, { onResult = null, extendSelection = false, deleteKey = false } = {}) {
  // The keyboard still reaches here while the toolbar is off (finding 109's
  // reload, a restart): say nothing, rather than toast EDITOR_NOT_READY at
  // someone waiting for the document to come back.
  if (!SESSION_ACCEPTS.has(session?.state?.snapshot?.state)) return;
  const button = el.toolbar.querySelector(`[data-action="${action}"]`);
  const label = button ? button.textContent.trim()
                       : (ACTION_LABELS[action] ?? action);
  const options = FORMAT_ACTIONS.has(action)
    // `=== true` and not truthiness: null means the engine has no answer, and
    // the honest response to that is to ask for ON, which is what the button
    // says it does.
    ? { enabled: formatStateFor(action) !== true }
    : (extendSelection ? { extendSelection } : {});
  // FINDING 128.  A repaint that meets this action's barrier (BUSY) gives up
  // instead of waiting a fixed 120 ms and asking again: `run()` repaints as
  // soon as the action returns, and the deleted character used to stay on
  // screen for those 120 ms.  Only while an action is out -- not for a save,
  // whose host part leaves the engine free (SPEC-M3-autosave §9.1, review 1
  // item 3).  A failed action is not repainted by `run()`, so a repaint given
  // up meanwhile is made here.
  engineActionsOut += 1;
  try {
    // FINDING 141.  `onResult` sees the engine's answer BEFORE the repaint
    // `run()` waits for: the delete listener decides the fate of the presses it
    // is holding there, so a real-delete burst keeps the engine as busy as the
    // queue did (one answered and repainting, the next already out).
    if (deleteKey) {
      await run(label, () => session.deleteKey(action, options).then((result) => {
        if (onResult) onResult(result);
        return result;
      }));
    } else {
      await run(label, () => session.action(action, options).then((result) => {
        if (onResult) onResult(result);
        return result;
      }));
    }
  } finally {
    engineActionsOut -= 1;
    if (engineActionsOut === 0 && busyLeftToAction) {
      busyLeftToAction = false;
      void renderDocument();
    }
  }
}

// Every inline format turned off in one press.  It is honest precisely because
// it asserts nothing about what was on: it asks for off.
//
// It used to say this was the ONLY off path for underline and strikethrough,
// "which have no readable state".  As of the 2026-08-19 relink the engine keeps
// a cache for both -- they were always in core's GetKitUnoCommandList and
// always broadcast; nobody had written the cache.  Whether the page can SEE
// them is a separate question from whether the engine knows them.
async function clearInlineFormatting() {
  for (const action of ["set-bold", "set-italic", "set-underline",
                        "set-strikethrough"]) {
    await run("清除格式", () => session.action(action, { enabled: false }));
  }
  toast("已清除粗體、斜體、底線、刪除線");
}

async function insertText() {
  const text = el.text.value;
  if (!text) { toast("先在欄位裡輸入要插入的文字", true); return; }
  await run("插入文字", () => session.commitText(text));
}

/* --------------------------------------------------------- Markdown paste */

// SPEC-M3-link-batch-v21 4.2, 9.13 (Q1 = A), 11.2 M8/M11.  「貼上為 Markdown…」
// opens a dialog with a text box: the user pastes into it with an ordinary
// Ctrl+V (no clipboard permission, the same in both browsers), sees what will
// be converted, and presses 「插入」.  Ctrl+V into the document stays plain
// text (M7).  The box is the dialog's own element, so nothing typed into it
// passes through the input adapter (E1-C's) or the sink's listeners; 「取消」
// (or Escape) closes it and enqueues NOTHING (M11).
//
// Only on a collapsed caret (9.14, finding 148): 「插入」 with a range selected
// says 「請先取消選取」 and sends nothing; the engine refuses the cases this
// page cannot see (an image or a frame selected) with MARKDOWN_NEEDS_CARET.
// The dialog stays open while the paste is out, and a refusal that changed
// nothing (`recovery: "none"`) is said IN the dialog with the text kept, so
// the user can remove the image or wrap the HTML and try again.
const MARKDOWN_REFUSAL_TEXT = {
  // 9.3, L-md-no-remote-images.
  MARKDOWN_REMOTE_IMAGE: "Markdown 裡有網路圖片，尚不支援；請先移除圖片",
  // 9.14 and 10.4, L-md-no-html: any `<word>` outside code is raw HTML.
  MARKDOWN_HTML_UNSUPPORTED: "Markdown 裡有 HTML（程式碼以外的 <字>，例如 <br> 或 List<T>），"
    + "尚不支援；請用反引號把它包起來",
  // 9.14, L-md-collapsed-only.
  MARKDOWN_NEEDS_CARET: "請先取消選取",
  MARKDOWN_ENCODING_UNSUPPORTED: "引擎的文字編碼不是 UTF-8，這裡無法貼上 Markdown",
  // The `.uno:Undo` read the engine verifies the paste with failed before it.
  MARKDOWN_UNDO_UNREADABLE: "引擎讀不到復原紀錄，無法核對貼上的結果，所以沒有貼上；文件沒有變",
  // 10.1: the work is banked before every paste, and that save failed.
  MARKDOWN_CHECKPOINT_FAILED: "貼上前要先保住你的工作，那次存檔失敗了，所以沒有貼上",
};

/** The sentence for a failed Markdown paste. */
function markdownRefusalText(error) {
  const known = MARKDOWN_REFUSAL_TEXT[error?.code];
  if (known) return known;
  if (error?.code === "INVALID_ARGUMENT") {
    // The SDK's operative limit says which limit and how far over (9.2).
    if (Number.isInteger(error?.details?.limitBytes))
      return `Markdown 太長：${error.details.utf8Bytes} 位元組，上限 ${error.details.limitBytes}`;
    return "這段 Markdown 沒有可以貼上的內容、無法解析、含有 NUL 字元，或太長";
  }
  return `貼上為 Markdown：${describeError(error)}`
    + (error?.recovery === "rollback" ? "（可能已經改到文件：請回到檢查點）" : "");
}

function showMarkdownMessage(text) {
  el.markdownMessage.textContent = text;
  el.markdownMessage.hidden = false;
}

function openMarkdownDialog() {
  // Every route in -- today the toolbar's -- ends here while the entry is off.
  if (!PASTE_MARKDOWN_ENTRY_SHIPS) return;
  if (session?.offersPasteMarkdown?.() !== true) return;
  el.markdownMessage.hidden = true;
  el.markdownMessage.textContent = "";
  el.markdownInsert.disabled = false;
  if (!el.markdownDialog.open) el.markdownDialog.showModal();
  el.markdownText.focus();
}

/** Close the dialog and forget its text; the caret's sink gets the focus back. */
function closeMarkdownDialog() {
  if (el.markdownDialog.open) el.markdownDialog.close();
  el.markdownText.value = "";
  el.markdownMessage.hidden = true;
  el.markdownMessage.textContent = "";
  el.markdownInsert.disabled = false;
  // FINDING 152 (v22 §11.3, fix 3).  After a modal <dialog> closes, Chrome
  // leaves the sink focused but produces no beforeinput for the keys that
  // follow, until the sink is blurred and focused again.  So: blur, then focus.
  if (session) { el.sink.blur(); el.sink.focus({ preventScroll: true }); }
}

/** 「取消」 and Escape: nothing is enqueued, the document is not touched (11.2 M11). */
function cancelMarkdownDialog() {
  closeMarkdownDialog();
}

/** 「插入」: the dialog's text, at the caret, through the session's queue. */
async function insertMarkdownFromDialog() {
  const markdown = el.markdownText.value;
  if (!PASTE_MARKDOWN_ENTRY_SHIPS) return;
  if (!session?.document || session.offersPasteMarkdown?.() !== true) return;
  // What the text may be (empty, too long, an image, HTML ...) is judged by
  // the SDK and the engine, not here: one judge, and the same codes on both
  // routes (11.2 M3).  The selection is the one rule the page checks itself.
  const shape = selectionShapeOf({ state: session.state.snapshot.editorState }) ?? lastSelectionShape;
  if (shape !== "collapsed") { showMarkdownMessage("請先取消選取"); return; }
  el.markdownInsert.disabled = true;
  try {
    await run("貼上為 Markdown", () => session.pasteMarkdown(markdown), { quiet: true });
    closeMarkdownDialog();
    toast("已貼上 Markdown");
  } catch (error) {
    // run() has already said this one (EDITOR_VIEW_ONLY).
    if (error?.code === "EDITOR_VIEW_ONLY") { closeMarkdownDialog(); return; }
    if (error?.recovery === "none") {
      el.markdownInsert.disabled = false;
      showMarkdownMessage(markdownRefusalText(error));
      return;
    }
    closeMarkdownDialog();
    toast(markdownRefusalText(error), true);
  }
}

el.markdownCancel.addEventListener("click", cancelMarkdownDialog);
el.markdownDialog.addEventListener("cancel", (event) => {
  event.preventDefault();
  cancelMarkdownDialog();
});
el.markdownInsert.addEventListener("click", () => void insertMarkdownFromDialog());

// With a host, one save at a time, end to end: the session's bytes AND the
// host's write.  Two quick presses (or a held Ctrl+S) otherwise send two writes
// that both carry the version the host saw at open, so the second is refused as
// a conflict with nobody else involved -- and queueing only the host's half is
// not enough, because the order in which two `run("儲存")` calls return depends
// on their repaints, so the older bytes could be written last.  Without a host
// nothing changes: each press is its own download, as before.
// What a save writes.  The ordinary save asks the engine; at the generation
// ceiling (B1) there is no engine to ask, and `rescueAtGenerationLimit` hands
// in `takeRescueContent` instead -- same queue, same host, same accounting.
const takeSavedContent = () => run("儲存", () => session.save());
const takeAutosaveContent = () => run("自動儲存", () => session.save());

function saveDocument(take = takeSavedContent, options = {}) {
  // A view-only document has nothing to save, and a save here would be a PUT
  // the server refuses and a copy the user did not ask for.
  if (viewOnly) {
    toast(VIEW_ONLY_TEXT, true);
    return Promise.resolve();
  }
  savesUnsettled += 1;
  // Once, at the moment the save ends -- when the host's write settles (or the
  // download is handed over), NOT when `run()` has also repainted: a runner or a
  // user leaving right after 「存回 N ms」 would otherwise meet a page that still
  // says "unsaved", and the host would guard and keep the lock for nothing.
  // The `.then` below is the backstop for a save that failed before reaching
  // the host.
  let settled = false;
  const settle = () => {
    if (settled) return;
    settled = true;
    savesUnsettled -= 1;
  };
  if (!HOST) {
    const once = saveOnce(settle, take);
    once.then(settle, settle);
    return once;
  }
  const turn = hostSaves.then(() => saveOnce(settle, take, options));
  hostSaves = turn.catch(() => {});
  turn.then(settle, settle);
  return turn;
}

async function saveOnce(settle = () => {}, take = takeSavedContent, options = {}) {
  // `EditorSession.save()` resolves to {bytes, revision, contentStamp}, not to
  // the bytes.  Taking the whole result made `new Blob([result])` stringify it,
  // so every save from this button wrote 15 bytes of "[object Object]" and the
  // toast below reported NaN KB -- finding 049, found by an operator pressing
  // the button, because every harness in this tree calls session.save() itself
  // and destructures.
  const { bytes } = await take();
  if (HOST) {
    // Locks, versions and conflicts are the host's to decide; a throw from it
    // is shown as a failure (run() says `存回 失敗` and why), never as a save.
    // `session.save()` has already marked the session clean by now -- the same
    // as the download below, which the user can also cancel.  The bytes are
    // still the session's recovery authority, so pressing save again retries.
    //
    // SPEC-M3-autosave: the host tells where the bytes went -- after a save
    // had to go to a copy, every later one goes to that copy (the owner's O1 =
    // B), so the toast names the file the host wrote, not this page's name.
    // An autosave says nothing on success, and its host part fails quietly:
    // the host bar keeps saying where things stand.
    const auto = options.trigger === "auto";
    let saved;
    try {
      saved = await run(auto ? "自動存回" : "存回",
                        () => HOST.save(bytes, { name: documentName, trigger: auto ? "auto" : "manual",
                                                 conditions: options.conditions })
                          .finally(settle),
                        { quiet: auto });
    } catch (error) {
      // A copy is a file written; stranded bytes are taken too (the host keeps
      // them and guards leaving), so the 5-minute count starts again rather
      // than turning every 3 s pause of an offline user into a blocking save
      // (review 2 item 3).
      if (error?.outcome === "copy" || error?.outcome === "stranded") autosaveLanded();
      throw error;
    }
    autosaveLanded();
    if (!auto)
      toast(`已存回 ${saved?.name ?? documentName}（${(bytes.byteLength / 1024).toFixed(1)} KB）`);
    return;
  }
  const url = URL.createObjectURL(
    new Blob([bytes], { type: "application/vnd.oasis.opendocument.text" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = documentName.replace(/\.odt$/i, "") + "-v2.odt";
  anchor.click();
  settle();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  toast(`已存出 ${(bytes.byteLength / 1024).toFixed(1)} KB`);
}

// FINDING 066.  A mouse click on a toolbar button moves the keyboard onto the
// button -- ordinary <button> behaviour -- and this page never gave it back.
// `el.sink.focus()` appeared exactly ONCE in this file, inside the canvas
// pointerdown handler, so the only way a user could type again was to click the
// canvas -- and that click MOVES THE CARET, which discards the inline format
// they had just set.  Measured 2026-08-22, both halves: press B and type and
// nothing reaches the document at all (the keystrokes go to the button); click
// first and the text arrives without the format.  findings/evidence/066/.
//
// Two lines and both are load-bearing:
//
//   * `preventDefault` on mousedown stops the button taking the keyboard in the
//     first place, which is what every editor toolbar does.  `click` still
//     fires, so nothing about the action changes.
//   * focusing the sink covers the case the first line cannot: a user whose
//     FIRST act is pressing B, before ever clicking the document, has focus on
//     <body> and preventing the button from taking it does not help.
//
// Focusing the sink does NOT move the caret -- only a canvas pointerdown does
// that -- so this cannot itself become the defect it repairs.
//
// Buttons only, deliberately: `#fixture` and `#text` live in this toolbar too
// and a user must still be able to click into them.
//
// The keyboard-activated path is NOT covered and that is on purpose: someone who
// tabs to a button and presses Space keeps focus there, which is what keyboard
// navigation is supposed to do.
el.toolbar.addEventListener("mousedown", (event) => {
  if (!event.target.closest("button")) return;
  event.preventDefault();
  if (session) el.sink.focus({ preventScroll: true });
});

el.toolbar.addEventListener("click", (event) => {
  const action = event.target.closest("button")?.dataset.action;
  if (!action || !session) return;
  const handler =
    action === "undo" ? () => run("復原", () => session.undo())
    : action === "redo" ? () => run("重做", () => session.redo())
    : action === "insert-text" ? () => insertText()
    : action === "paste-markdown" ? () => openMarkdownDialog()
    : action === "save" ? () => saveDocument()
    : EDITOR_V2_ACTIONS.includes(action) ? () => editorAction(action)
    : null;
  if (handler) void Promise.resolve(handler()).catch(() => {});
});

// Named so a test can compile it (review 2026-10-06b item 2).
function onNoticeAction() {
  // B1: at the ceiling a rollback disposes the engine and is then refused.
  if (session && !session.restartAvailable()) {
    if (limitState() === "pending") void rescueAtGenerationLimit();
    else location.reload();
    return;
  }
  // FINDING 119's run: after this reopen the next key typed without a click
  // landed nowhere -- the block had disabled the sink, which loses focus.  Given
  // back the moment the session is ready, inside the operation, as the
  // boundary reopen does (and for the same measured reason: after the repaint
  // is too late for the first key).
  void run("回到檢查點", async () => {
    await session.rollback();
    el.sink.focus({ preventScroll: true });
  })
    .then(() => renderDocument())
    .catch(() => {});
}

el.noticeAction.addEventListener("click", onNoticeAction);

/* ------------------------------------------------------------------- drag */

// A real pointer drag through this page's own handler.  Coordinates, not
// synthesised mouse events: SPEC E1-D 2.1 measured the synthesised path
// reporting a selection it had not made.
const drag = { active: false, start: null, latest: null, inFlight: false,
  pointerId: null };

async function pumpDrag() {
  if (drag.inFlight || !drag.latest || !session?.editor) return;
  const end = drag.latest;
  drag.latest = null;
  drag.inFlight = true;
  try {
    const result = await session.selectRange(drag.start, end);
    // What the engine read back, not what we asked for -- AND FROM WHERE IT
    // ACTUALLY IS.
    //
    // FINDING 079.  This read `result.collapsed` and `result.rectangles`, which
    // is the shape `editor-shell/editor-client.js` BUILDS for the v1 path.  The
    // v2 client does not build anything: `ParagraphEditorClient.selectRange`
    // returns the worker's envelope verbatim, and its keys are
    // `method, revision, completion, callbackSequenceBefore,
    // callbackSequenceAfter, state` -- the selection is one level down, at
    // `state.selection`.  So both reads were `undefined`, `undefined === false`
    // is false, `undefined?.length ?? 0` is 0, and this expression returned
    // "collapsed" for EVERY drag, unconditionally.
    //
    // That is why 079 looked like staleness and is not: there was never a value
    // to go stale.  Nothing needed to arrive late or be reset; the shape was
    // manufactured from two fields that are not there.
    //
    // Measured 2026-08-23 on the shipped e2-editor-v7, both branches, with the
    // engine's own answer recorded in the same arm
    // (tools/probe_079_selection_shape.py --capture-result):
    //   drag inside one line    state.selection.collapsed=false, 1 rectangle,
    //                           engine copy path returns 12 characters
    //   drag across two lines   state.selection.collapsed=false, 3 rectangles,
    //                           engine copy path returns 34 characters
    // and the page reported `collapsed` for both.
    // THE DERIVATION LIVES IN ONE PLACE AND HAS ITS OWN TESTS.
    //
    // Deriving it here was the defect's shape as much as its content: an
    // inline read, with nothing under test, of a field layout some other layer
    // assembles.  A DOM flag catches the NEXT drift in this one reader; it does
    // nothing about a second reader looking in a second wrong place.
    // `selectionShapeOf` is in editor-shell-v2 with the recorded envelopes as
    // its fixtures, and one of its cases IS finding 079 -- a v1-shaped object
    // must come back unknown rather than `collapsed`.
    const shape = selectionShapeOf(result);
    if (shape === null) {
      // AN UNREADABLE RESULT IS NOT AN EMPTY SELECTION, and saying it is was
      // the whole of 079.  The previous value is kept rather than replaced by
      // a guess: guessing `collapsed` is the defect being fixed, and guessing a
      // range would grey out the two deletes and both breaks after an ordinary
      // click, which is the worse of the two failures.
      //
      // DEGENERATE CASE, stated rather than left to be discovered: if the FIRST
      // result of a session is unreadable, the value kept is the initial one,
      // `collapsed` -- so this policy degrades into the option it rejects, and
      // the only thing separating them is that the flag below is up.  That is
      // the point of the flag, and it is why the flag rather than the shape is
      // what the regression check reads.
      el.toolbar.dataset.selectionUnreadable = "1";
      // WHAT IT ACTUALLY GOT.  A flag that says only "this happened" sends the
      // next reader to a browser to find out what the object looked like; the
      // key names answer it from the report.  Names only -- `state` can carry
      // the focused paragraph's text on a profile that projects it, and a
      // public DOM attribute is no place for a user's paragraph.
      el.toolbar.dataset.selectionEvidence = selectionShapeEvidence(result);
    } else {
      delete el.toolbar.dataset.selectionUnreadable;
      delete el.toolbar.dataset.selectionEvidence;
      lastSelectionShape = shape;
    }
    updateGestureAffordance();
  } catch {
    // A refused range must not abort the gesture.
  } finally {
    drag.inFlight = false;
    if (drag.latest) void pumpDrag();
  }
}

function endDrag(event) {
  if (!drag.active) return;
  drag.active = false;
  if (drag.pointerId !== null) {
    try { el.paper.releasePointerCapture(drag.pointerId); } catch { /* gone */ }
    drag.pointerId = null;
  }
  if (!session?.document || !event) return;
  const end = pointToTwips(event);
  if (end.xTwips === drag.start.xTwips && end.yTwips === drag.start.yTwips)
    return;   // a click is a zero-length drag; leave the caret where it landed
  drag.latest = end;
  void pumpDrag();
}

// On #paper since release C′: the canvas is a window onto the document and
// the paper is the document, so a press anywhere on it is a press on the page.
el.paper.addEventListener("pointerdown", (event) => {
  if (!session?.document || event.button !== 0) return;
  event.preventDefault();
  const point = pointToTwips(event);
  el.sink.focus({ preventScroll: true });
  drag.active = true;
  drag.start = point;
  drag.latest = null;
  drag.pointerId = event.pointerId;
  try { el.paper.setPointerCapture(event.pointerId); }
  catch { drag.pointerId = null; }
  lastSelectionShape = "collapsed";
  void run("定位游標", () => session.placeCaret(point.xTwips, point.yTwips))
    .then(() => updateGestureAffordance())
    .catch(() => {});
});

// Ctrl+C.  The document is a canvas, so the browser's default copy has no DOM
// selection to take and puts nothing on the clipboard -- which is why four
// operator rounds of the D5 clipboard cell pasted either nothing or whatever
// had been copied from some other application earlier.  The shell has always
// had `copySelection()`, which asks the ENGINE for the selected text; nothing
// called it.
el.sink.addEventListener("copy", (event) => {
  if (!session?.document) return;
  event.preventDefault();
  void run("複製", () => session.copySelection())
    .then((result) => toast(`已複製 ${result?.codePoints ?? "?"} 字`))
    .catch(() => {});
});

// NO paste listener here, deliberately, and it is not an oversight.
//
// Ctrl+V looks like the copy defect above -- `session.pasteEvent()` exists and
// nothing calls it -- and on 2026-08-17 a handler was written on exactly that
// reasoning.  The mutation round measured it: the marker landed in the saved
// document TWICE (markOccurrences 2, revision +2).  Paste already arrives, as
// `beforeinput` with inputType insertFromPaste, which the input adapter
// attached to this sink already commits.  Adding a page-level handler makes a
// second commit of the same text.
//
// The two cases are not the same shape after all: the canvas has no DOM
// selection for the browser to copy FROM, so copy needed the engine asked; the
// sink is a real editable target, so paste arrives on its own.  `pasteEvent()`
// is for hosts without an input sink.  `ctrl-v-reaches-the-document` in the
// product-path runner now requires EXACTLY ONE occurrence, so re-adding a
// handler here goes red rather than looking like success.

// Backspace and Delete.  NOT a keyboard shortcut -- this is the primary way
// anybody corrects a typo, and until now the product had none: the input
// adapter drops `deleteContentBackward`/`deleteContentForward` into
// `ignored-input-type` (input-adapter.js) and does not preventDefault, so the
// keys did nothing and the user had to reach for the toolbar's ⌫ button.
//
// Handled HERE and not in the adapter, deliberately: the adapter's job is to
// commit text, and deleting is an editor action with its own contracted wire
// id. Checked before writing, after the paste episode: the adapter really does
// leave these alone, so this is not a second handler for the same event.
const DELETE_INPUT_TYPES = {
  deleteContentBackward: "delete-backward",
  deleteContentForward: "delete-forward",
};

// FINDING 073: show the user what they are part way through typing.
//
// The sink is one transparent pixel by design, and the browser draws an IME's
// preedit INSIDE it -- so composing 台 with 新酷音 wrote ㄊㄞˊ into a box
// nobody can see, and the first thing the user saw was the committed
// character. There are no compositionstart/update handlers anywhere else in
// this file: composition is entirely the browser's until `beforeinput`
// delivers the result, which is why nothing had to be undone to add this.
//
// The measuring context is a detached canvas, not the document's: this asks
// how wide the preedit is, and borrowing the drawing surface for that would
// make a text measurement depend on the render state.
const compositionRuler = document.createElement("canvas").getContext("2d");

function showComposition(text) {
  const style = getComputedStyle(el.sink);
  // The font size comes from the CARET's own height, which
  // `moveSinkToCaret` already set from the engine's cursor rectangle -- so the
  // preedit is about the size of the line it will land on rather than a
  // constant that is wrong at every zoom level. 0.75 is the usual ratio of an
  // em to a line box; the floor is legibility, not geometry.
  const line = el.sink.offsetHeight || 16;
  el.sink.style.fontSize = `${Math.max(11, Math.round(line * 0.75))}px`;
  compositionRuler.font = `${el.sink.style.fontSize} ${style.fontFamily}`;
  const width = compositionRuler.measureText(text || "").width;
  // A floor, because compositionstart arrives with nothing composed yet and a
  // zero-width box would flash. The padding is for the caret the browser draws
  // at the end of the preedit.
  el.sink.style.width = `${Math.max(14, Math.ceil(width) + 10)}px`;
  el.sink.dataset.composing = "1";
}

function hideComposition() {
  delete el.sink.dataset.composing;
  // Cleared rather than set back to 1px: the stylesheet owns the resting size,
  // and an inline width would silently outrank a later change to it.
  el.sink.style.width = "";
  el.sink.style.fontSize = "";
}

el.sink.addEventListener("compositionstart", () => showComposition(el.sink.value));
el.sink.addEventListener("compositionupdate", (event) => showComposition(event.data));
// BOTH endings. `compositionend` is the ordinary one; `blur` is the one that
// gets forgotten -- an IME abandoned by clicking away never fires
// compositionend in every browser, and a sink left visible sits on top of the
// document with stale text in it.
el.sink.addEventListener("compositionend", hideComposition);
el.sink.addEventListener("blur", hideComposition);

// FINDING 121.  Backspace or Delete with text selected went out as
// `delete-backward`/`delete-forward`, which every profile offers for a caret
// only, so the gesture gate refused it with a developer's sentence and nothing
// was deleted (both browsers; since the v19 cutover).  A range is deleted by
// `delete-selection` -- the action cut already uses, on the same test.  Named so
// a test can compile it (SPEC-M3-production-ui §15.2, 121-U).
//
// The shape is the ENGINE's current selection (the editor state it last
// pushed), not `lastSelectionShape`: that is the page's belief, set by drags
// and clicks only, so after typing over a selection or deleting it the belief
// would still say "range" and the next Backspace would go out as
// delete-selection on a caret -- refused the other way round.  The belief is
// the fallback only when the engine has not said.
//
// FINDING 131 (SPEC-M3-autosave §9.12, rule A).  Not while a delete this page
// sent is still out: its barrier selects one character and the engine pushes
// that as editor state like any other, so a key arriving then read a range
// that was never the user's, went out as delete-selection, and the gate
// refused it with the character left in place (one key in four in a 50 ms
// burst on 0.2.13, one in twenty on 0.2.12).  The delete out can only return
// to a caret, so the key keeps its own collapsed form.  The page's own count
// of deletes, not `engineActionsOut`: a real range, Ctrl+B, then Backspace
// must still go out as delete-selection.
function deleteActionFor(action, shape, offersSelectionDelete, deletesInFlight = 0) {
  if (deletesInFlight > 0) return action;
  return shape !== null && shape !== "collapsed" && offersSelectionDelete ? "delete-selection" : action;
}

// FINDING 141 (task 2026-10-14o; the owner chose A).  At a C boundary -- the
// document's start for Backspace, its end for Delete -- the engine answers a
// delete only when its 250 + 2,000 ms window expires (SPEC-M3-link-batch
// §10.5, `verified-boundary-noop`), and this listener sent EVERY press
// (finding 131's rule): a held key whose repeats arrive unflagged, or a user
// who presses again because nothing happened, queued one 2.26 s no-op per
// press, and the editor sat in 「處理中」 for N × 2.26 s with no toast and
// nothing to do (measured: 18 presses in one second, 40.6 s;
// findings/evidence/host-0.2.20-hand-test/).  H2 (`dropsHeldRepeat`) could not
// help: it keys on `event.repeat`, and finding 131 forbids dropping presses.
//
// So a press of a key whose delete is out and NOT YET ANSWERED is HELD here --
// counted, not queued -- and the engine's answer decides it (`settleDelete`):
//   * `verified-boundary-noop` with the state it came back with equal to the
//     state the delete was sent from (`boundaryNoopStands`): the held presses
//     are DROPPED, their answer is known -- nothing to delete here, nothing
//     moved. Legacy profiles pay their boundary window on the first press;
//     ABI6 uses actual outstanding work only, without that removed window.
//   * anything else -- a real delete, a refusal, an answer whose state moved,
//     an answer without a state: ONE held press is delivered again
//     (`releaseHeldDelete`), through dispatchDelete, so a burst of real
//     deletes is still deleted press for press (131), one answered and
//     repainting while the next is already out (132's depth).  A refusal drops
//     them, as 134's B drops the rest of a hold.
// "Answered" is the engine's reply (`editorAction`'s `onResult`), before the
// repaint `run()` awaits; `deletesInFlight`, which spans the repaint, keeps
// its meaning for the overlay, and H2's depth counts it together with the
// held presses (finding 144, `skipHeldRepeat`).  Fail closed towards 131: when
// the answer cannot be read as a standing no-op, the presses go out.  Named
// limit: a K1 that lands after the reply (L-C-late-K1) is not seen here.
//
// SPEC-M3-link-batch-v21 §10.3 (the hold rewritten, items 1-4).  With
// Ctrl+Home/End bound, "a delete of this key is out" stopped meaning "this
// press is at the same place": Backspace at the start, Ctrl+End, Backspace held
// the second press behind the first and DROPPED it with the first's no-op, so
// nothing was deleted at the end (D8 (a)).  Now (1) a press is held only while
// the session's most recent enqueue is an unanswered delete of the same key
// (`holdsDelete`, the session's `enqueueCount`); (2) each held press belongs to
// the send it waits on, with its own key (`send.held`); (3) that send's answer
// decides them -- a standing no-op drops them, anything else releases them in
// order; (4) anything else about to be enqueued while presses are held sends
// them first (`releaseHeldDeletesBeforeEnqueue`, the session's
// `beforeEnqueue`).  Finding 144's depth and finding 145's unconditional
// settle are unchanged.
//
// A held press is released by a direct call (`dispatchDelete`), not by a
// synthetic `beforeinput` on the sink (0.2.21 did that): a re-dispatched event
// reaches every `beforeinput` listener, so the frozen adapter traced it and
// 132-B's instrument counted it -- `beforeinputs` 102 against 52 keys -- and
// its clause (c) read red for the count alone (finding 144).

/** The caret and whether the selection is collapsed, or null when the state cannot say. */
function deleteStateOf(editorState) {
  const caret = editorState?.caret;
  const collapsed = editorState?.selection?.collapsed;
  if (!caret || typeof collapsed !== "boolean") return null;
  const { x, y, width, height } = caret;
  if (![x, y, width, height].every(Number.isFinite)) return null;
  return { x, y, width, height, collapsed };
}

/** A boundary no-op whose returned state equals the state it was sent from. */
function boundaryNoopStands(result, stateAtSend) {
  if (result?.completion !== "verified-boundary-noop" || result?.changed !== false) return false;
  if (result.revision !== result.beforeRevision) return false;
  const after = deleteStateOf(result.state);
  if (after === null || stateAtSend === null) return false;
  return after.collapsed && stateAtSend.collapsed
    && after.x === stateAtSend.x && after.y === stateAtSend.y
    && after.width === stateAtSend.width && after.height === stateAtSend.height;
}

/**
 * Hold this press?  SPEC-M3-link-batch-v21 §10.3 rule 1: IF AND ONLY IF the
 * session's most recent enqueue is a delete of the SAME key that the engine has
 * not answered.  `last` is the newest delete this page sent, `enqueueCount` the
 * session's count of everything enqueued (`NarrowEditorV2Session._enqueue`, the
 * one entry every path takes), compared with the count right after `last` went
 * in.  So a move, a click, a typed character, an undo or a save sent since
 * means the press is SENT: finding 141's hold existed for a key pressed again
 * at the same boundary, and after Ctrl+End the same Backspace is at another
 * place (D8 (a), (c), (d)).
 */
function holdsDelete(action, last, enqueueCount) {
  return last !== null && last.settled === false && last.action === action
    && enqueueCount === last.enqueueMark;
}

/** §10.3 rule 3: the presses held behind `send` are dropped -- their answer is known, or their document is gone. */
function dropHeldDeletes(send) {
  heldDeletes.count -= send.held.length;
  send.held = [];
}

/**
 * §10.3 rule 3: `send` was answered with something other than a standing
 * no-op, so its held presses go out in order -- the first now, the rest held
 * behind it, so a burst of real deletes keeps one answered and repainting and
 * the next already out (131's press-for-press, 132's depth).  A direct call
 * (finding 144: no synthetic event).
 */
function releaseHeldDelete(send) {
  if (send.held.length === 0) return;
  const [next, ...rest] = send.held;
  send.held = [];
  heldDeletes.count -= 1;
  dispatchDelete(next, rest);
}

/**
 * §10.3 rule 4: something else is about to be enqueued while presses are held
 * -- they go FIRST, in order, each as its own key, and only then the new item.
 * Installed as the session's `beforeEnqueue`, which runs synchronously at the
 * top of every enqueue, so "first" is the queue's own order.  Not for this
 * page's own delete sends (`heldDeletes.sending`): those are the presses.
 * Named cost L-hold-release-cost: at a document boundary each released press
 * pays its own C window (at most two, by 144's depth).
 */
function releaseHeldDeletesBeforeEnqueue() {
  const send = heldDeletes.last;
  if (heldDeletes.sending || send === null || send.held.length === 0) return;
  const presses = send.held;
  send.held = [];
  heldDeletes.count -= presses.length;
  for (const action of presses) dispatchDelete(action);
}

/** Once per sent delete, at the engine's answer (or at its failure, or when it never went out). */
function settleDelete(send, result, failed) {
  if (send.settled) return;
  send.settled = true;
  // Counted out in dispatchDelete, so counted back here whatever became of its
  // document.  FINDING 145: this used to return first when the document it was
  // sent on was gone -- and a refusal's reopen always makes a new one -- which
  // left `deletesUnanswered` above 0 for the rest of the page: every later
  // press of that key was held, and the held presses went out as the other
  // key's action at its answer.  The presses held behind a delete to a document
  // that is gone were aimed at that document, so they go with it, as at a
  // refusal (finding 134, B).
  deletesUnanswered -= 1;
  const documentGone = send.document !== session?.document;
  if (failed || documentGone || boundaryNoopStands(result, send.stateAtSend)) dropHeldDeletes(send);
  else releaseHeldDelete(send);
}

/**
 * One delete of the user's, sent now: a key's `beforeinput` that nothing held,
 * or a held press being released.  The form it goes out in is decided here,
 * at the moment of sending (finding 121's shape, finding 131's collapsed form
 * while a delete is out), and the counters are its.
 */
function dispatchDelete(action, held = []) {
  // Presses handed over with this one (`releaseHeldDelete`) were aimed at the
  // document that is gone, so they go with it.
  if (!session?.document) { heldDeletes.count -= held.length; return; }
  const shape = selectionShapeOf({ state: session.state.snapshot.editorState }) ?? lastSelectionShape;
  const ordered = session.engine?.manifest?.editorContract?.abiVersion === 6;
  const sent = ordered ? action : deleteActionFor(action, shape,
                               session.offers?.("delete-selection") === true, deletesInFlight);
  // `action` is the KEY (its original direction, §10.3 rule 2), `sent` the
  // form it went out in; `held` the presses that now wait on this one.
  const send = { action, document: session.document, stateAtSend: deleteStateOf(session.state.snapshot.editorState),
                 settled: false, held, enqueueMark: null };
  heldDeletes.last = send;
  deletesUnanswered += 1;
  // §10.3: this send is going into the session's queue -- not "something
  // else" for rule 4.  The session enqueues synchronously inside
  // `editorAction` (an async function: it cannot throw before the flag is
  // cleared below), so the count read right after it is this send's own, and
  // "nothing was enqueued since" is the count still being this one (rule 1).
  // A session without the counter reads undefined twice, which is the hold as
  // it was before §10.3.
  heldDeletes.sending = true;
  // Counted before the call and released however it ends -- an early return,
  // a refusal swallowed here, a disposed engine.  Once none is out, the overlay
  // is brought up to date: a range that arrived meanwhile was not drawn
  // (overlayEditorState), and no state write may follow to draw it.  A refusal
  // also ends what the rest of this hold sends (finding 134, B).
  deletesInFlight += 1;
  void editorAction(sent, { onResult: (result) => settleDelete(send, result, false), deleteKey: ordered })
    .catch(() => { deleteRefusedThisHold = true; settleDelete(send, null, true); })
    // A delete that never went out (the session not accepting) was never answered either.
    .finally(() => settleDelete(send, null, false))
    .finally(() => { deletesInFlight -= 1; })
    .then(() => { if (deletesInFlight === 0) paint(); });
  heldDeletes.sending = false;
  send.enqueueMark = session?.enqueueCount;
}

el.sink.addEventListener("beforeinput", (event) => {
  const action = DELETE_INPUT_TYPES[event.inputType];
  if (!action || !session?.document) return;
  event.preventDefault();
  // A retained move is earlier input even though it has no enqueue mark yet.
  if (session.engine?.manifest?.editorContract?.abiVersion === 6) releaseHeldSelectionMove();
  // FINDING 141, as SPEC-M3-link-batch-v21 §10.3 rule 1 narrows it: the
  // session's last enqueue is an unanswered delete of this key -- held behind
  // that send, with this key's direction, not queued.
  if (holdsDelete(action, heldDeletes.last, session.enqueueCount)) {
    heldDeletes.last.held.push(action);
    heldDeletes.count += 1;
    return;
  }
  dispatchDelete(action);
});

// FINDING 122 (SPEC-M3-production-ui §15.6; fable's third ruling, A).  A key
// that will reach the engine ends the repaint pass in flight.  Without this the
// page learned of the change only from `document-invalidated`, which comes
// back after the insert -- and by then it had already asked for one more band
// of the old pass, usually off screen: in Firefox about 30 ms per key spent on
// a band nobody was looking at, before the band under the caret (measured in
// `raw.blits`, findings/evidence/typing-latency/).  Setting `renderAgain` here
// lets the band in flight finish and blit, and the next pass starts with the
// view, asked for after the insert.
//
// ONLY while a pass is running: an idle page has nothing to end, and the
// invalidation that follows the key starts the next pass as it always did.
// The listener only reads the event -- no preventDefault, nothing said to the
// input adapter (E1-C binds it); it runs beside the adapter's own listener and
// the delete listener above, and changes neither.
//
// The types are those that reach the engine: the adapter commits text and
// line breaks (input-adapter.js TEXT_INPUT_TYPES, plus insertLineBreak and
// insertParagraph), and the listener above sends the two deletes.  A
// composition update reaches nothing until compositionend, so it is excluded.
const ENGINE_INPUT_TYPES = new Set([
  "insertText", "insertReplacementText", "insertFromPaste",
  "insertLineBreak", "insertParagraph",
  ...Object.keys(DELETE_INPUT_TYPES),
]);

function endRenderPassOnInput(event) {
  if (!rendering || event.isComposing || !ENGINE_INPUT_TYPES.has(event.inputType)) return;
  renderAgain = true;
}

el.sink.addEventListener("beforeinput", endRenderPassOnInput);

// Arrow keys produce no `beforeinput` at all, so they need keydown.
//
// All six are listed, and the PROFILE decides which of them bind. Until the
// ABI 4 link, `move-line-*` exist in the engine but are not in the v3
// contract, and `offers()` reports them absent -- so on that profile Up/Down/
// Home/End fall through untouched, exactly as when they were not listed here
// at all. The rule this file already states twice stays intact: a key that
// cannot dispatch must not be taken.
//
// Listing them now rather than after the link means the binding is not a
// second thing to remember on the day the artifact changes; it lights up
// because the manifest says the action exists, which is the same question
// `updateGestureAffordance` asks for the toolbar.
const KEY_ACTIONS = {
  ArrowLeft: "move-character-left",
  ArrowRight: "move-character-right",
  ArrowUp: "move-line-up",
  ArrowDown: "move-line-down",
  Home: "move-line-home",
  End: "move-line-end",
};

// FINDING 142 (SPEC-M3-link-batch-v21 4.1, 9.8, 11.1 D4, D5, D9).  Ctrl+Home
// and Ctrl+End (Cmd on a Mac) went to the hidden input, the document's caret
// did not move, and the next Backspace deleted where the caret really was.
// They are engine actions now, taken BEFORE `if (accel) return;` -- and only
// when the profile offers the action, the rule above: on v20, which has no
// such action, the key is left alone exactly as before (D5).  Never with
// Shift (extending a selection is the ordered-commands batch) or during an IME
// composition; not with Alt either, which is not the chord Writer binds
// (HOME_MOD1 / END_MOD1).  macOS's Cmd+Up/Down are not bound (L-142-mac-arrows).
const DOCUMENT_KEY_ACTIONS = { Home: "move-document-start", End: "move-document-end" };

el.sink.addEventListener("keydown", (event) => {
  if (!session?.document) return;
  const accel = event.ctrlKey || event.metaKey;
  // The three shortcuts below follow the toolbar's rule (SPEC-M3-production-ui
  // §3.1, review 2026-10-06 item 6): outside ready/busy they do nothing and say
  // nothing.  A guard, not a measured path: the sink is disabled whenever the
  // queue is blocked, and a disabled element has no focus to receive keys, so
  // in a stopped session these keys mostly never reach this handler -- and
  // Ctrl+S then reaches the browser's own save-page dialog (review 2026-10-06b
  // item 9; registered, spec §10).
  const accepting = SESSION_ACCEPTS.has(session.state.snapshot.state);
  if (accel && event.key.toLowerCase() === "z" && !event.shiftKey) {
    // Ctrl+Z, and it earns its place: finding 046's review disposition tells
    // the user to press 復原, and until now the only way to do that was to find
    // the button.
    event.preventDefault();
    if (accepting) void run("復原", () => session.undo()).catch(() => {});
    return;
  }
  if (accel && ((event.key.toLowerCase() === "z" && event.shiftKey)
                || event.key.toLowerCase() === "y")) {
    // Both spellings, because both are in the muscle memory this editor is
    // competing with. Gated like the button: on a profile without redo the key
    // is left alone rather than taken and dropped.
    if (!session.offersRedo?.()) return;
    event.preventDefault();
    if (accepting) void run("重做", () => session.redo()).catch(() => {});
    return;
  }
  if (accel && event.key.toLowerCase() === "s") {
    // Without preventDefault this opens the BROWSER's save dialog, which saves
    // the page rather than the document -- an answer to the user's request that
    // is worse than no answer.
    event.preventDefault();
    // FINDING 106.  A held Ctrl+S is one request, not one per key repeat: the
    // repeats were each a full save (thirty PUTs for a one-second hold, about
    // 35 s of saving on host 0.2.2).  The first keydown has `repeat: false`.
    if (event.repeat || !accepting) return;
    void saveDocument().catch(() => {});
    return;
  }
  // The inline formats, on the keys everybody already knows.  Deliberately NOT
  // wired until 2026-08-19: under finding 059 all four of these failed on the
  // shipped engine, and binding them to the keyboard would only have copied one
  // defect onto a second path.  With 059 fixed they go through `editorAction`,
  // the same function the toolbar buttons call, so the shortcut and the button
  // cannot drift apart -- including the `enabled` it derives from the engine's
  // own state.
  if (accel && !event.shiftKey) {
    const formatAction = { b: "set-bold", i: "set-italic",
                           u: "set-underline" }[event.key.toLowerCase()];
    if (formatAction) {
      event.preventDefault();
      void editorAction(formatAction).catch(() => {});
      return;
    }
    // Ctrl+A is deliberately NOT bound.  Select-all is not one of the fifteen
    // actions, and expressing it as a geometric range -- (0,0) to the
    // document's width and height -- was tried and MEASURED on 2026-08-19:
    // `selectRange` reports success in about half a second, the engine reports
    // the selection still collapsed, and the canvas shows no selection wash at
    // all.  A shortcut that looks like it worked and selected nothing is worse
    // than no shortcut, which is the same rule that put `preventDefault` on
    // Ctrl+S.  A real one needs a select-all ACTION in the contract
    // (queue-no-select-all-action).
  }
  // FINDING 067.  Enter did nothing, and the revision counter said it worked.
  //
  // The frozen input adapter turns `beforeinput` with `insertParagraph` or
  // `insertLineBreak` into `commitText("\n")` -- a text insert of a newline --
  // and the engine's `paste` ACCEPTS that newline, does nothing with it, and
  // increments the revision anyway (measured: method "paste", revision 1 -> 2,
  // content.xml byte-identical, findings/evidence/067/).  Meanwhile the toolbar
  // buttons for both breaks work and are covered every run: only the user's
  // keyboard was broken.
  //
  // WHY HERE AND NOT AT THE ADAPTER'S COMMIT BOUNDARY.  Measured on this page:
  // a plain Enter and Shift+Enter BOTH arrive as `insertLineBreak`, because
  // this sink is a <textarea> -- `insertParagraph` is what a contenteditable
  // reports, so that branch of the adapter is dead code here.  The two keys are
  // therefore indistinguishable at `commit(text, metadata)`, and no routing
  // decision taken there can offer both breaks.  `keydown` carries `shiftKey`;
  // `InputEvent` does not, and the adapter does not listen for keydown at all.
  //
  // `preventDefault` here means the browser generates NO `beforeinput`, so the
  // adapter's branch never fires and the two paths are disjoint by
  // construction -- no ordering dependency, and none of the double-commit the
  // paste handler was measured doing when it duplicated the adapter's work.
  //
  // `isComposing` is not optional: during an IME composition Enter COMMITS the
  // composition, and preventing it there would break Chinese input -- finding
  // 050's neighbourhood, and that file is frozen so a mistake here cannot be
  // repaired there.
  //
  // Ctrl/Cmd+Enter is swallowed rather than passed on. The contract has no
  // page-break action, and letting it fall through would reproduce 067 on that
  // chord -- the same rule that put `preventDefault` on Ctrl+S and left Ctrl+A
  // unbound: offering a key that cannot dispatch is worse than offering none.
  if (event.key === "Enter" && !event.isComposing) {
    event.preventDefault();
    if (!accel) {
      void editorAction(event.shiftKey ? "insert-line-break"
                                       : "insert-paragraph-break").catch(() => {});
    }
    return;
  }
  // Finding 142: Ctrl/Cmd+Home/End, when offered (see DOCUMENT_KEY_ACTIONS).
  if (takeDocumentKey(event)) return;
  if (accel) return;
  if (session.engine?.manifest?.editorContract?.abiVersion === 6 && takeSelectionMove(event)) return;
  const action = KEY_ACTIONS[event.key];
  // `offers()`, not `gesturesFor()`: the latter answers null both for a
  // v1-shaped manifest and for an action the profile does not carry, and
  // taking the key on the second would be the "looks like it worked" trap that
  // Ctrl+A is unbound to avoid.
  if (!action || !session.offers(action)) return;
  // FINDING 129 (SPEC-M3-autosave §3.7).  Shift+move asks to EXTEND the
  // selection, and no action here extends one until the next link; sending
  // the plain move did something other than what was asked.  Not taken.
  if (event.shiftKey) return;
  event.preventDefault();
  // FINDING 129.  On a range the six moves are refused (the profile grants
  // them `collapsed` only) and the refusal reached the user as a developer
  // sentence.  Writer moves FROM THE POINT -- the end the caret is at -- and
  // drops the selection (findings/evidence/129/native/).  The page cannot send
  // a move on a range, but it can click at the point, which collapses the
  // selection there, and then send the move on the caret: the same as Writer
  // in all 42 cells measured natively, except Down when the point is shown at
  // the end of a wrapped line (named limit L-129, §9.7).  While one such pair
  // is queued, further move keys go straight to the queue: they run after the
  // click, on a caret, and a second click at a point read before the first
  // move ran would put the caret back.
  //
  // Decided by `clicksBeforeMove`, the predicate `sendDocumentMove` uses too
  // (finding 150: neither path checked for a delete out).
  const shape = selectionShapeOf({ state: session.state.snapshot.editorState }) ?? lastSelectionShape;
  const gestures = session.gesturesFor(action);
  if (clicksBeforeMove(shape, gestures, pointMovesInFlight, deletesInFlight)) {
    void moveFromPoint(action).catch(() => {});
    return;
  }
  void editorAction(action).catch(() => {});
});

/** ABI6 grants these six moves directly, including range origins. */
function takeSelectionMove(event) {
  if (event.ctrlKey || event.metaKey || event.altKey || event.isComposing) return false;
  const action = KEY_ACTIONS[event.key];
  const shape = selectionShapeOf({ state: session?.state?.snapshot?.editorState }) ?? lastSelectionShape;
  if (!action || !session?.offersSelectionMove?.(action, shape)) return false;
  event.preventDefault();
  if (!SESSION_ACCEPTS.has(session.state.snapshot.state)) return true;
  // Do not let a held delete and a later held move straddle the same enqueue.
  releaseHeldDeletesBeforeEnqueue();
  const extendSelection = event.shiftKey === true;
  let hold = selectionMoveHolds.get(event.key);
  if (!event.repeat || !hold?.active || hold.document !== session.document
      || hold.extendSelection !== extendSelection) {
    hold = { key: event.key, extendSelection, document: session.document, active: true };
    selectionMoveHolds.set(event.key, hold);
  }
  if (event.repeat && selectionMovesOutstanding.size + (heldSelectionMove ? 1 : 0) >= HELD_DELETE_DEPTH)
    return true;
  const move = { id: ++selectionMoveSequence, action, extendSelection,
    hold, document: session.document, answered: false };
  if (event.repeat && selectionMovesOutstanding.size > 0) heldSelectionMove = move;
  else {
    if (!event.repeat) releaseHeldSelectionMove();
    sendSelectionMove(move);
  }
  return true;
}

// ABI6 repeats use the existing depth2 policy: admitted outstanding work and
// at most one repeat retained by the page. These are NOT wire-pending counts.
// The instrument derives wire pending from actual requests and terminals.
const selectionMoveHolds = new Map();
const selectionMovesOutstanding = new Set();
let heldSelectionMove = null;
let selectionMoveSending = false;
let selectionMoveSequence = 0;

function sendSelectionMove(move) {
  if (move.document !== session?.document) return;
  selectionMovesOutstanding.add(move);
  selectionMoveSending = true;
  void editorAction(move.action, { extendSelection: move.extendSelection, onResult: () => {
    move.answered = true;
    // Release at the answer, before repaint; retain132's paint-inclusive depth.
    if (![...selectionMovesOutstanding].some((item) => !item.answered)) releaseHeldSelectionMove();
  } }).catch(() => {
    if (heldSelectionMove?.hold === move.hold) heldSelectionMove = null;
  }).finally(() => {
    selectionMovesOutstanding.delete(move);
    if (selectionMovesOutstanding.size === 0) releaseHeldSelectionMove();
  });
  selectionMoveSending = false;
}

function releaseHeldSelectionMove() {
  const move = heldSelectionMove;
  heldSelectionMove = null;
  if (move?.hold.active && move.document === session?.document) sendSelectionMove(move);
}

function releaseHeldInputsBeforeEnqueue() {
  releaseHeldDeletesBeforeEnqueue();
  // Earlier retained input precedes an unrelated save, click, key or edit.
  if (!selectionMoveSending) releaseHeldSelectionMove();
}

function endSelectionMoveHold(event) {
  // A depth-rejected modifier change may have replaced the lookup entry while
  // an earlier admitted repeat still owns the old hold. Physical release must
  // reach both records; deleting an old record must not erase a newer one.
  const holds = new Set(selectionMoveHolds.values());
  if (heldSelectionMove) holds.add(heldSelectionMove.hold);
  for (const hold of holds) {
    if (event.type === "blur" || event.key === hold.key || (event.key === "Shift" && hold.extendSelection)) {
      hold.active = false;
      if (heldSelectionMove?.hold === hold) heldSelectionMove = null;
      if (selectionMoveHolds.get(hold.key) === hold) selectionMoveHolds.delete(hold.key);
    }
  }
}
window.addEventListener("keyup", endSelectionMoveHold, true);
window.addEventListener("blur", endSelectionMoveHold);

// Flush earlier retained input BEFORE the frozen adapter counts the new text.
// Waiting for beforeEnqueue is too late: finding111 would then (correctly for
// its own admission order) place the earlier move behind the newly typed text.
// These capture listeners neither commit text nor interfere with IME updates.
function releaseHeldSelectionMoveBeforeInput(event) {
  if (session?.engine?.manifest?.editorContract?.abiVersion !== 6
      || event.isComposing || session.input?.state?.composing) return;
  if (["insertText", "insertReplacementText", "insertFromPaste", "insertLineBreak", "insertParagraph"]
    .includes(event.inputType)) releaseHeldSelectionMove();
}
function releaseHeldSelectionMoveBeforeComposition(event) {
  if (session?.engine?.manifest?.editorContract?.abiVersion !== 6) return;
  const input = session.input?.state;
  const text = typeof event.data === "string" ? event.data : input?.compositionText;
  if (input?.composing && typeof text === "string" && text.length > 0) releaseHeldSelectionMove();
}
function releaseHeldSelectionMoveBeforePaste() {
  // The adapter also commits directly from paste; no beforeinput is required.
  // Clipboard content and validation remain entirely owned by the adapter.
  if (session?.engine?.manifest?.editorContract?.abiVersion === 6) releaseHeldSelectionMove();
}
el.sink.addEventListener("beforeinput", releaseHeldSelectionMoveBeforeInput, true);
el.sink.addEventListener("compositionend", releaseHeldSelectionMoveBeforeComposition, true);
el.sink.addEventListener("paste", releaseHeldSelectionMoveBeforePaste, true);

// FINDING 132 (SPEC-M3-held-key §3.2; the owner chose this, §4).  A held
// Backspace or Delete repeats every 30 ms on the owner's desk, and a delete
// takes the engine about 66 ms with the repaint between two of them, so the
// repeats queued faster than they were done: a 2 s hold went on deleting for
// 1.8 s after the key came up (measured, findings/evidence/132/baseline/).  A
// repeat is not sent while two deletes this page sent are out -- one in the
// engine and one waiting, so the engine never waits for the next repeat -- and
// the key stops within those two when it comes up.  How fast a held key
// deletes is the engine's either way; only the tail goes.  A press (`repeat`
// false) always goes out: a burst of separate presses is deleted press for
// press (finding 131).  Finding 106 is the precedent: a held Ctrl+S is one save.
const HELD_DELETE_DEPTH = 2;

// FINDING 144 (task 2026-10-14q).  The depth counts the deletes this page has
// SENT and not seen settle (`deletesInFlight`) PLUS the presses finding 141
// holds on the page behind an unanswered one (`heldDeletes.count`).  With the
// sent ones alone, 141's hold kept the count at one -- the second press is
// held, not sent -- so this cut never fired, every flagged repeat was held and
// then released one per engine answer, and a 2 s hold inside text deleted 52
// characters, 27–29 of them after the key came up (host 0.2.21, 132-B red,
// findings/evidence/host-0.2.21/k3/).  Counting the held press restores H2's
// bound: at most one delete unanswered and one press waiting, so at most two
// more after release.
function dropsHeldRepeat(event, deletesOutOrHeld) {
  return event.repeat === true && !event.isComposing
    && (event.key === "Backspace" || event.key === "Delete")
    && deletesOutOrHeld >= HELD_DELETE_DEPTH;
}

// preventDefault on the keydown: no `beforeinput` follows, so nothing is sent.
function skipHeldRepeat(event) {
  if (dropsHeldRepeat(event, deletesInFlight + heldDeletes.count)) event.preventDefault();
}

el.sink.addEventListener("keydown", skipHeldRepeat);

// FINDING 134, B (SPEC-M3-held-key §14; fable's ruling for the owner).  Once a
// delete this page sent is refused, the rest of that hold is not sent.  A
// refusal at a document end reopens the engine (one Worker generation), and
// the hold's repeats then reached the new engine: at the start each was
// refused again, up to the ceiling in 5-7 s; at the end the reopened caret was
// at the start, and the held Delete deleted from there until the key came up
// (71-83 characters, saved; findings/evidence/132/held-into-refusal/run-1/).
// The hold ends when its key comes up, when it is pressed anew, or when the
// window loses focus -- on the window and in capture, because the sink is
// disabled during the reopen and the key comes up on `body`.  A press always
// goes out (finding 131).  Like H2, this reads the driver's `repeat` flag; a
// keyboard path without it gets the behaviour this replaces.
let deleteRefusedThisHold = false;

function dropsRefusedRepeat(event, refusedThisHold) {
  return refusedThisHold && event.repeat === true && !event.isComposing
    && (event.key === "Backspace" || event.key === "Delete");
}

function endsHeldDelete(event) {
  if (event.type === "blur") return true;
  if (event.key !== "Backspace" && event.key !== "Delete") return false;
  return event.type === "keyup" || (event.type === "keydown" && event.repeat === false);
}

function skipRefusedRepeat(event) {
  if (dropsRefusedRepeat(event, deleteRefusedThisHold)) event.preventDefault();
}

function endHeldDelete(event) {
  if (endsHeldDelete(event)) deleteRefusedThisHold = false;
}

el.sink.addEventListener("keydown", skipRefusedRepeat);
window.addEventListener("keydown", endHeldDelete, true);
window.addEventListener("keyup", endHeldDelete, true);
window.addEventListener("blur", endHeldDelete);

// FINDING 150 (SPEC-M3-link-batch-v21 §12.3 (a); fable ruling 1, Q1).  Whether
// a move key goes through `moveFromPoint` (click at the point, then move) or
// straight out -- ONE predicate for the arrows' path and `sendDocumentMove`, so
// the two cannot drift apart again.  The point path is for a range the profile
// does not offer the move on (finding 129), and not while a point move is
// already queued: the moves behind it run on its caret.
//
// Nor while a delete this page sent is out: finding 131's rule A
// (`deleteActionFor`, above), applied where it was missing.  The delete's
// barrier selects one character and the engine pushes that as editor state, so
// a move key pressed then read a range that was never the user's, clicked at a
// caret read before the delete answered, and the Delete pressed next ran at
// the click, before the move.  The delete out can only return to a caret, so
// the move goes straight out on it.  Measured
// (findings/evidence/link-batch-v21/shakedown/diag-dirty-move/): V6e (Backspace,
// Backspace, ArrowRight, Delete) saved the wrong text 6/6 on this page and 6/6
// on 0.2.24's -- the arrows' path is older than Ctrl+End, which reuses it --
// and D8 (e), the same with Ctrl+End, the same text; with this rule V6e kept
// the key order 6/6, D8 (e) matched its expectation 6/6, and a real range
// (a drag, then ArrowRight) still clicked first, 6/6.  Not a timing rule: a
// count the page already keeps.
function clicksBeforeMove(shape, gestures, pointMovesInFlight, deletesInFlight) {
  if (deletesInFlight > 0) return false;
  return pointMovesInFlight === 0 && shape !== "collapsed"
    && Array.isArray(gestures) && !gestures.includes(shape);
}

async function moveFromPoint(action, actionOptions = {}) {
  const caret = session?.state?.snapshot?.editorState?.caret;
  // No point to click at (or no session taking actions): the move goes out as
  // it is, and whatever refuses it says so -- a key must not do nothing silently.
  if (!SESSION_ACCEPTS.has(session?.state?.snapshot?.state)
      || !Number.isFinite(caret?.x) || !Number.isFinite(caret?.y) || !Number.isFinite(caret?.height)) {
    await editorAction(action, actionOptions);
    return;
  }
  pointMovesInFlight += 1;
  try {
    await run("定位游標", () => session.placeCaret(caret.x, caret.y + caret.height / 2));
    lastSelectionShape = "collapsed";
    updateGestureAffordance();
    await editorAction(action, actionOptions);
  } finally {
    pointMovesInFlight -= 1;
  }
}

// FINDING 142, the keys (see DOCUMENT_KEY_ACTIONS).  `documentMovesUnanswered`
// counts, per action, the document moves this page sent that the engine has
// not answered: a press of the same key meanwhile is dropped, and so is every
// flagged repeat (11.1 D9) -- a held Ctrl+End must not queue one 250 ms move
// per repeat, and in a table a repeat would only walk one more level (Writer's
// steps, L-142-steps; L-142-no-repeat).
const documentMovesUnanswered = new Map();

/** The document move this keydown asks for, or null when the page must not take the key. */
function documentKeyAction(event, offered) {
  if (!(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey || event.isComposing) return null;
  const action = DOCUMENT_KEY_ACTIONS[event.key];
  return action !== undefined && offered(action) === true ? action : null;
}

/** 11.1 D9: a flagged repeat, or a press while this key's move is unanswered, is dropped. */
function dropsDocumentMove(event, unanswered) {
  return event.repeat === true || unanswered > 0;
}

/**
 * Send one document move.  On a range the profile does not offer it for (both
 * are `collapsed` only), the page clicks at the point first and then moves --
 * finding 129's `moveFromPoint`, the arrows' path, so the caret ends where
 * Writer's does after collapsing the range (11.1 D4).  The decision is the
 * arrows' own predicate, `clicksBeforeMove`: not while a delete is out
 * (finding 150).
 */
function sendDocumentMove(action) {
  documentMovesUnanswered.set(action, (documentMovesUnanswered.get(action) ?? 0) + 1);
  let open = true;
  const answered = () => {
    if (!open) return;
    open = false;
    documentMovesUnanswered.set(action, documentMovesUnanswered.get(action) - 1);
  };
  const shape = selectionShapeOf({ state: session.state.snapshot.editorState }) ?? lastSelectionShape;
  const gestures = session.gesturesFor(action);
  const fromPoint = clicksBeforeMove(shape, gestures, pointMovesInFlight, deletesInFlight);
  const sending = fromPoint ? moveFromPoint(action, { onResult: answered })
                            : editorAction(action, { onResult: answered });
  void Promise.resolve(sending).catch(() => {}).finally(answered);
}

/** Take Ctrl/Cmd+Home/End when the profile offers the move; true when the key was taken. */
function takeDocumentKey(event) {
  const action = documentKeyAction(event, (name) => session.offers(name));
  if (action === null) return false;
  event.preventDefault();
  if (!dropsDocumentMove(event, documentMovesUnanswered.get(action) ?? 0)) sendDocumentMove(action);
  return true;
}

// ---------------------------------------------------------------- autosave
// FINDING 127, the scheduler (§9.2 of specs/SPEC-M3-autosave.md).  Activity is
// a key into the sink, a composition, a pointer on the paper, and any edit
// that completes by whatever path (`noteAutosaveState`, below): each one
// re-arms a one-shot timer.  `setTimeout`, not `setInterval`: a hidden tab
// throttles chained intervals far harder.
function autosaveConditions() {
  const input = session?.input?.state ?? null;
  const snapshot = session?.state?.snapshot ?? null;
  return {
    viewOnly,
    state: snapshot?.state ?? null,
    pending: snapshot?.pending ?? null,
    composing: input ? input.composing === true : null,
    queueDepth: input ? input.queueDepth : null,
    dragging: drag.active || drag.inFlight,
    savesUnsettled,
    rescue: limit.state === "saving",
  };
}

function autosaveAllowed(c) {
  return !c.viewOnly && c.state === "ready" && c.pending === 0 && c.composing === false
    && c.queueDepth === 0 && !c.dragging && c.savesUnsettled === 0 && !c.rescue;
}

function armAutosave(delay) {
  if (!HOST) return;
  clearTimeout(autosave.timer);
  const capped = autosave.firstUnsavedAt !== null
    && Date.now() - autosave.firstUnsavedAt >= AUTOSAVE_CAP_MS;
  autosave.timer = setTimeout(() => void autosaveNow("idle"),
                              delay ?? (capped ? AUTOSAVE_CAP_IDLE_MS : AUTOSAVE_IDLE_MS));
}

function noteActivity() {
  if (!HOST || !session?.document) return;
  if (autosave.firstUnsavedAt === null && session.hasUnsavedEdits?.() === true)
    autosave.firstUnsavedAt = Date.now();
  armAutosave();
}

// A save that reached a file (the original, or a copy it now saves to).  Edits
// typed after its bytes were taken start the 5-minute count again.
function autosaveLanded() {
  autosave.firstUnsavedAt = session?.hasUnsavedEdits?.() === true ? Date.now() : null;
}

// From updateState: a new revision is an edit that completed, whichever way it
// came (toolbar, paste, cut, insert field, undo, a merge) -- review 1 item 9.
// A session back in `ready` with edits and nothing armed is armed again.
function noteAutosaveState(snapshot) {
  if (!HOST) return;
  if (snapshot.revision !== autosave.revision) {
    const first = autosave.revision === null;
    autosave.revision = snapshot.revision;
    if (!first) noteActivity();
  } else if (snapshot.state === "ready" && autosave.timer === null
             && session?.hasUnsavedEdits?.() === true) {
    armAutosave();
  }
}

async function autosaveNow(reason) {
  autosave.timer = null;
  if (!HOST || !session?.document || session.hasUnsavedEdits?.() !== true) return;
  const conditions = autosaveConditions();
  if (!autosaveAllowed(conditions)) {
    // Again in 3 s while the session may become ready by itself; otherwise
    // the next activity or the return to `ready` arms it.
    if (["ready", "busy"].includes(conditions.state)) armAutosave(AUTOSAVE_RECHECK_MS);
    return;
  }
  try {
    await saveDocument(takeAutosaveContent, { trigger: "auto", conditions: { ...conditions, reason } });
  } catch {
    // Shown by run() (the engine's part) or by the host bar (the host's part).
  }
}

if (HOST) {
  el.sink.addEventListener("keydown", noteActivity, true);
  for (const type of ["compositionstart", "compositionupdate", "compositionend"])
    el.sink.addEventListener(type, noteActivity);
  el.paper.addEventListener("pointerdown", noteActivity);
  el.paper.addEventListener("pointermove", () => { if (drag.active) noteActivity(); });
  el.paper.addEventListener("pointerup", noteActivity);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "hidden" || session?.hasUnsavedEdits?.() !== true) return;
    clearTimeout(autosave.timer);
    void autosaveNow("hidden");
  });
}

// Cut = copy, then delete what was copied.  Two dispatches rather than one
// because the contract has no cut action; the ORDER matters, since a failed
// copy must not still remove the text.
el.sink.addEventListener("cut", (event) => {
  if (!session?.document) return;
  event.preventDefault();
  // BOTH halves inside `run`, so the delete's failure is reported with its
  // disposition like every other action.  It used to sit in a `.then` whose
  // `.catch` swallowed it, and that hid finding 063 completely: with a working
  // clipboard the copy succeeds, the delete fails, the session lands in
  // recoverable-error, and the only thing the user saw was a notice telling
  // them to restart -- no word about what had failed.  "A rejection the user
  // cannot see is a rejection nobody reports" is already written in this file,
  // three handlers down, for finding 050.
  void run("剪下", async () => {
    const copied = await session.copySelection();
    // `delete-selection` when the profile carries it.
    //
    // `delete-backward` is declared caret-only in every manifest up to v3, and
    // a cut is a range BY DEFINITION -- so the delete half is refused every
    // time and cut has been effectively copy (finding 063,
    // queue-cut-cannot-remove-text). The remedy measured out as a distinct
    // action rather than a widening: widening delete-backward's gestures would
    // have discarded the one characterisation this pair has behind it, and the
    // run that tried it hit the selection barrier instead.
    //
    // On a profile without it this falls back to today's behaviour rather than
    // to a new one: the fallback is the defect, and replacing a known defect
    // with an untested path on the day of a link is how a link acquires a
    // second cause.
    await session.action(session.offers("delete-selection")
                         ? "delete-selection" : "delete-backward", {});
    return copied;
  })
    .then((copied) => toast(`已剪下 ${copied?.codePoints ?? "?"} 字`))
    .catch(() => {});
});

el.paper.addEventListener("pointermove", (event) => {
  if (!drag.active || !session?.document) return;
  if ((event.buttons & 1) === 0) { endDrag(event); return; }
  drag.latest = pointToTwips(event);
  void pumpDrag();
});

el.paper.addEventListener("pointerup", endDrag);
el.paper.addEventListener("pointercancel", () => endDrag(null));
globalThis.addEventListener("blur", () => endDrag(null));
globalThis.addEventListener("resize", () => {
  layoutCanvas();
  void renderDocument();
});
// SPEC-M3-scroll-page-bubble §3.3: the thumb the bubble sat next to has moved;
// the next scroll places it again.  Its own listener, after the one above,
// whose bytes are a product-path mutation's anchor (resize-does-not-repaint).
globalThis.addEventListener("resize", hideScrollBubble);
// Release C′: the window follows the scroll.  Passive -- it never stops one.
el.desk.addEventListener("scroll", onDeskScroll, { passive: true });

/* ------------------------------------------------------------------- boot */

// REVERTED TO e2-editor-v4 ON 2026-08-23, hours after the cutover, because the
// product path went RED on v5: the format barrier stopped advancing on a
// bulleted blank line, bold did not reach the document, and the band scan saw
// 7 bands for 9 lines. The accessibility tree was perfect on v5 -- 205 nodes,
// nine paragraphs with roles -- and that is not worth a product that cannot
// apply bold. See findings/evidence/aria-projection/ and the v5 finding.
//
// CUT OVER TO e2-editor-v7 ON 2026-08-23, and this is the first cutover where
// the pin does NOT move with the worker URL -- because the artifact did not
// move. v7 is v4's loader, wasm and worker byte for byte (`f923cfa5...` /
// `e6ee92ca...`) with one difference in the manifest: the four inline formats
// are offered for range selections as well as for a caret. No relink. That is
// what "a later profile can grant on the strength of a measurement" means, and
// this is the first time it has been used.
//
// Why: finding 078. Selected text could not be emboldened -- the manifest
// offered the inline formats for `collapsed` only, honestly, because range
// dispatch had never been characterised for them. The characterisation is now
// done: all four formats, both range shapes, the formatted text equal to the
// selected text, on this identity itself, with native LibreOffice writing the
// same shapes; and the operator confirmed it with a real mouse. Both range bits
// are granted because the engine requires both for a range it has not
// classified (granting one alone admits nothing -- measured three ways).
//
// The v5 identity is minted and archived; it is not shipped. v6 is minted and
// inert; see its SUPERSEDED.md. The two lines below still move together
// WHENEVER THE ARTIFACT MOVES: the worker URL says which profile, the pinned
// hash says which build of it, and a page that got one without the other would
// run an engine its evidence does not describe.
//
// THAT PARAGRAPH WAS ABOUT v5 AND SAT UNDER v7'S HEADING. It read "the core
// now has accessibility compiled in ... the contract gained caretParagraphText
// and documentOutline ... paragraphFresh no longer claims a successful read".
// None of it was true of v7: v7 is v4's wasm byte for byte, so no core, no
// contract field and no engine fix arrived with it. Left in place it would have
// told the next reader that this page was running an accessibility core.
// Corrected 2026-08-24 while cutting over to v8, which is where two of those
// three actually arrive.
//
// CUT OVER TO e2-editor-v8 ON 2026-08-24, and this time BOTH LINES MOVE,
// because the artifact does. `4a2710bba1ef07d9` / worker `070229cd10bda4a0`,
// from `f923cfa5aba30749` / `e6ee92ca290b7966`. The loader is unchanged
// (`c382b834aa768b91`), which is exactly why a page must not identify its
// engine by the loader.
//
// Why: finding 076. `paintTile` draws only the page and `putImageData` blits
// the whole buffer, so the tile's `malloc`'d remainder -- this process's heap,
// and this process's heap holds the user's document -- was being drawn onto a
// canvas the user can screenshot. The operator confirmed seeing it. The buffer
// is `calloc`'d now.
//
// What this link ships was MEASURED before it was taken, by preprocessing the
// product's own translation units with the product's own defines at the shipped
// commit and at the tree (`tools/what_the_link_ships.py`). Three things, not
// one, and reading the `#ifdef`s would have found only the first:
//
//   1. finding 076's `calloc`;
//   2. `refreshCaretParagraph()` returning early so `a11yParagraphFresh` is
//      false on a build where no accessibility read can succeed -- gated on a
//      RUNTIME flag, deliberately, so it is behind no `OXSDK_A11Y_*`;
//   3. 21 code lines in the worker forwarding `a11y.paragraphText` and
//      `a11y.outline`. Additive and presence-guarded, and inert here: this core
//      emits neither field and v8's manifest declares neither
//      `caretParagraphText` nor `documentOutline`, so nothing below reads them.
//
// SPEC E2-C section 11: round two's product is the v3 artifact.
//
// Hard-coded, not a query parameter.  A product page that takes its engine from
// the URL is a page whose evidence does not say which engine it measured, and
// round one bound four hashes precisely because that had been left implicit.
// The harness pages (`e2-c-d*-app.js`) do take `?profile=`; they are harnesses.
function engineFactory() {
  return createDocumentEngine({
    workerUrl: "./profiles/e2-editor-v24/sdk-worker.js",
    timeoutMs: 30000,
  });
}

function showExpired(details) {
  el.expired.style.display = "block";
  el.paper.style.display = "none";
  el.expectedHash.textContent = details?.expected ?? PINNED_WASM_SHA256;
  el.actualHash.textContent = details?.actual ?? "（manifest 沒有提供）";
  showState("expired", "已過期");
  for (const button of el.toolbar.querySelectorAll("button"))
    button.disabled = true;
  el.fixture.disabled = true;
  // The hidden input is unreachable once its button is disabled, but a control
  // that is only unreachable by layout is not disabled -- say it outright.
  el.file.disabled = true;
}

// The bytes are the only thing that ever differed between a bundled sample and
// a document the user chose: both end at the same `session.open({bytes, name})`.
// Splitting the fetch off is the whole of "open a real file" -- there is no
// engine side to it, which is why it does not need a link.
// FINDING 120.  The input adapter writes `disabled` on its target when it
// blocks, and neither `detach()` nor `attach()` puts it back; a new session's
// `setBlocked(false)` runs inside `open()`, before this page attaches the sink,
// so it cannot reach the element.  A session that stopped therefore left the
// sink disabled for every document opened after it in this page, and typing did
// nothing (measured, findings/evidence/120/).  The adapter is E1-C's; the page
// syncs the element to the NEW adapter's own answer.
function syncSinkToInput(sink, input) {
  sink.disabled = input?.state?.blocked === true;
}

async function openDocument(bytes, name, { readOnly = false } = {}) {
  if (session) {
    // The page number described the document being let go: an answer still in
    // flight for it is dropped, and the line hides until the next one reads.
    pageRectangles.closed();
    pageStatus.document = null;
    pageStatus.rectangles = null;
    hidePageStatus();
    try { await session.close(); } catch { /* a dead session must not block */ }
    session = null;
  }
  // B1's record belongs to the session that reached the ceiling, not to the
  // page: a second document opened here starts with no rescue attempted
  // (review 2026-10-06b item 5; the host disables the picker, so standalone only).
  limit.state = null;
  limit.detail = null;
  session = new NarrowEditorV2Session({
    engineFactory,
    clipboard: navigator.clipboard,
    secureContext: globalThis.isSecureContext,
    // SPEC-M3-link-batch-v21 §10.3 rule 4: held deletes go before anything else.
    beforeEnqueue: releaseHeldInputsBeforeEnqueue,
    onState: updateState,
    onEvent(event) {
      if (event.event === "document-invalidated") {
        changes += 1;   // §17.9 (c): every band asked for before this is stale
        publishWindow();
        queueMicrotask(() => void renderDocument());
      }
    },
    // Finding 050 was invisible for as long as it existed because these two
    // callbacks were never wired: the input adapter rejected every commit after
    // the first, said so in its trace, and the trace went nowhere.  A rejection
    // the user cannot see is a rejection nobody reports.
    //
    // Only failures surface -- a toast per keystroke would be its own defect.
    onInputTrace(entry) {
      if (entry?.error?.code === "EDITOR_VIEW_ONLY") {
        toast(VIEW_ONLY_TEXT, true);
        return;
      }
      // FINDING 130.  This compared `entry.action` and `entry.status`; the
      // adapter writes what happened in `type` and has no `failed` status, so
      // a refused keystroke was dropped and nothing was said (characters typed
      // while a save held the engine: findings/evidence/130/m1/).  The
      // sentence is the user's, not the adapter's code.
      const why = {
        "queue-full": "打得比引擎處理得快",
        "input-too-large": "一次送出的內容太大",
        blocked: "目前不能輸入",
        "buffer-mismatch": "輸入法的字沒有對上",
      }[entry?.reason] ?? "引擎沒有接受";
      if (entry?.type === "commit-rejected" || entry?.type === "commit-error"
          || entry?.type === "composition-rejected")
        toast(`有字沒有輸入：${why}，請檢查最後打的字`, true);
    },
    onClipboardTrace(entry) {
      if (entry?.status === "failed" || entry?.status === "rejected")
        toast(`剪貼簿未完成：${entry.code || entry.status}`, true);
    },
  });
  // Before open, so no input can land between the document appearing and the
  // gate closing.
  viewOnly = readOnly === true;
  session.setViewOnly?.(viewOnly);
  await session.open({ bytes, name });
  session.attachInput(el.sink);
  syncSinkToInput(el.sink, session.input);
  const actual = session.engine.manifest?.editorContract?.wasmSha256 ?? "";
  // SPEC-M3-link-batch-v24 4.4 (fable ruling 2, follow-up A2): this page
  // describes a build whose typing goes through .uno:InsertText.  A manifest
  // without that declaration types through paste -- finding 168's route --
  // and the SDK, shared with pages whose profiles never declare it, sends such
  // a request unchanged; so it is refused here, the way a wrong wasm is.
  const typedInsert = session.engine.manifest?.editorContract?.typedInsert;
  if (!actual.startsWith(PINNED_WASM_SHA256) || typedInsert !== TYPED_INSERT_DECLARATION) {
    showExpired({
      expected: PINNED_WASM_SHA256,
      actual: typedInsert === TYPED_INSERT_DECLARATION
        ? actual.slice(0, 16) : `${actual.slice(0, 16)}（未宣告打字路線）`,
    });
    throw Object.assign(new Error("this build is not the one this page describes"),
                        { code: "PAGE_BUILD_MISMATCH" });
  }
  documentName = name;
  el.s.doc.textContent = viewOnly ? `${name}（${VIEW_ONLY_TEXT}）` : name;
  // A read-only sink: typing and IME never start, arrow keys still arrive.
  el.sink.readOnly = viewOnly;
  el.text.disabled = viewOnly;
  layoutCanvas();
  await renderDocument();
  updateGestureAffordance();
}

async function openFixture(id) {
  const name = `${id}.odt`;
  const response = await fetch(`./e1-fixtures/${name}`, { cache: "no-cache" });
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  await openDocument(await response.arrayBuffer(), name);
}

el.fixture.addEventListener("change", () => {
  void openFixture(el.fixture.value)
    .catch((error) => toast(describeError(error), true));
});

el.openFile.addEventListener("click", () => el.file.click());

el.clearFormat.addEventListener("click", () => {
  if (!session?.document) return;
  void clearInlineFormatting().catch(() => {});
});

el.file.addEventListener("change", () => {
  const file = el.file.files?.[0];
  // Clearing the input is what lets the same file be re-opened; without it a
  // second pick of the same path fires no change event at all.
  el.file.value = "";
  if (!file) return;
  // The fixture select must stop naming a document that is no longer open --
  // a control that reports the wrong document is the shape of finding 054.
  el.fixture.value = "";
  void file.arrayBuffer()
    .then((bytes) => openDocument(bytes, file.name))
    .then(() => toast(`已開啟 ${file.name}`))
    .catch((error) => toast(describeError(error), true));
});

// With a host, the page opens the host's document and nothing else.  The two
// local pickers are switched off: a document opened from them would be written
// over the host's file by the next save.  A `liteCoreHost` that is not the
// contract's shape is refused rather than ignored -- falling back to the bundled
// sample would let the user edit a document they believe is theirs.
async function openFromHost() {
  el.fixture.disabled = true;
  el.openFile.disabled = true;
  el.file.disabled = true;
  if (typeof HOST.load !== "function" || typeof HOST.save !== "function")
    throw Object.assign(new Error("宿主入口不完整：需要 load() 與 save()"),
                        { code: "HOST_ENTRY_INVALID" });
  const { bytes, name, readOnly } = await HOST.load();
  if (!(bytes instanceof ArrayBuffer) || typeof name !== "string" || !name)
    throw Object.assign(new Error("宿主給的文件不是 { bytes: ArrayBuffer, name }"),
                        { code: "HOST_ENTRY_INVALID" });
  await openDocument(bytes, name, { readOnly: readOnly === true });
  toast(viewOnly ? `已開啟 ${name}（${VIEW_ONLY_TEXT}）` : `已開啟 ${name}`);
}

void (async () => {
  el.pinnedHash.textContent = PINNED_WASM_SHA256;
  if (!globalThis.crossOriginIsolated)
    toast("此頁需要 cross-origin isolation：請以 web/serve.py 提供", true);
  if (HOST) {
    await openFromHost();
    return;
  }
  const manifest = await fetch("./e1-fixtures/manifest.json", { cache: "no-cache" })
    .then((value) => value.json());
  el.fixture.replaceChildren(...manifest.fixtures.map((fixture) => {
    const option = document.createElement("option");
    option.value = fixture.id;
    option.textContent = fixture.id;
    return option;
  }));
  el.fixture.value = "list-contexts";
  await openFixture(el.fixture.value);
  toast("點一下放游標，或拖曳選一段，再按動作");
})().catch((error) => {
  if (error?.code === "PAGE_BUILD_MISMATCH") return;
  showState("stopped", "錯誤");
  toast(describeError(error), true);
});
