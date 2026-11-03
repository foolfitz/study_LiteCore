// SPEC E2-C 2.3: the product session for the v2 profile.
//
// Everything D1 and D2 promise -- one session for both action families, a FIFO
// queue, a checkpoint written before the selection gesture, a blocked queue and
// a fresh-worker rollback after any post-dispatch failure, the three-generation
// ceiling -- already exists, correct and validated, in EditorSession.  What did
// not exist is any way to run it on the v2 profile: EditorSession builds a
// NarrowEditorClient during open and awaits its getState, and that client
// refuses a manifest whose contract version is 2.  So the session could not
// open a document at all, and ParagraphEditorSession did not help -- it wraps a
// session, reads `session.document`, and bypasses the queue entirely.
//
// The choice here was between copying five hundred lines of queue, checkpoint
// and generation machinery into this directory, or finding the one seam where
// v1 and v2 differ.  They differ in exactly one place: which client class is
// constructed.  Everything downstream of that goes through a runtime object
// (`{document, editor, scheduler}`), and NarrowEditorV2Client answers every
// method EditorSession asks of it.
//
// So this subclass intercepts the assignment.  That means depending on a
// private field of the base class, which is normally a bad trade -- here it is
// not, because `editor-shell/editor-session.js` is hash-registered by E1-C's
// shell bundle: it cannot change without a deliberate act that unbinds a
// shipped verdict.  And the dependency is pinned by a test rather than assumed:
// if the base class stops assigning `this.editor`, the interception counter
// stays at zero and the test says so.
//
// Copying the machinery would have been the worse risk.  A second copy of the
// checkpoint and generation logic is a second thing that can be subtly wrong,
// in the part of the product where being subtly wrong costs the user's
// unsaved work.

import { EditorSession, caretIsOnLine, caretDiffers } from "../editor-shell/editor-session.js";
import { NarrowEditorV2Client, EDITOR_ACCEPTED_ACTIONS }
  from "./narrow-editor-v2-client.js";
import { EDITOR_ALIGN_ACTIONS, EDITOR_TOGGLE_ACTIONS, EDITOR_V2_PARAGRAPH_ACTIONS } from "./paragraph-editor-client.js";
import { recoveryFor } from "./paragraph-editor-session.js";

// Finding 140: the engine's place-caret answers that send `placeCaret` down
// v67's polling path instead of failing the click -- a profile whose worker
// does not carry the entry point, and an engine BUSY behind a barrier (the
// selection barrier, the format barrier, or another callback-correlated
// operation still pending).  Everything else is the caller's error.
const PLACE_CARET_FALLBACK_CODES = new Set(["BUSY", "UNSUPPORTED_OPERATION"]);

/**
 * SPEC-P-ms-formats 5.2: the format a document's saves are written in -- what
 * the engine said it opened (`DocumentHandle.format`, E5), or `odt` when it
 * said nothing (every Writer profile before e2-editor-v33).
 */
export function documentFormatOf(document) {
  const format = document?.format;
  return typeof format === "string" && format !== "" ? format : "odt";
}

const PARAGRAPH = new Set([...EDITOR_V2_PARAGRAPH_ACTIONS, ...EDITOR_ALIGN_ACTIONS, ...EDITOR_TOGGLE_ACTIONS]);
// EDITOR_V4_ACTIONS (ABI 5's list, SPEC-M3-link-batch-v21 4.1), and before it
// EDITOR_V3_ACTIONS, not EDITOR_V2_ACTIONS: this set is the SESSION's own
// allowlist, a second copy of the client's, and it was the layer the ABI 4
// link found. The client learned the five appended actions when they were
// written; this did not, so on the v4 profile the manifest offered
// `move-line-up`, the page gated on that and took the key, the client would
// have accepted it -- and the session refused it here with
// EDITOR_ACTION_UNSUPPORTED.
//
// The list stays a session-side allowlist rather than being deleted in favour
// of the client's: refusing an unknown action BEFORE it enters the queue is
// what keeps a typo from occupying a queue slot and blocking real edits. What
// was wrong was having a second copy that could lag, not having the check.
//
// SPEC-M3-select-all-v26 4.3 (review 2026-10-30 item 1): and now the CLIENT'S
// OWN UNION, EDITOR_ACCEPTED_ACTIONS, not EDITOR_V4_ACTIONS -- select-all is a
// grant outside the V4 list, and this copy refused it before the queue exactly
// the way it refused move-line-up at the ABI 4 link.  One list, read here and
// by the D13 census, is the remedy the paragraph above asks for.
const ACTIONS = new Set(EDITOR_ACCEPTED_ACTIONS);

// FINDING 096.  The six actions that reach the engine as a POSTED KEY, and
// therefore the six that can be pressed where there is nothing to move to.
//
// This is the path, not a list of the keys somebody has measured.  096
// measured Up and Down at a document boundary (40 attempts, 40 wedges, four
// artifacts including the shipping bytes); finding 018 measured End; Home and
// the two character moves are unmeasured in both directions.  What they share
// is `handleEditorAction`'s key branch: a key is posted, nothing changes, core
// broadcasts nothing, and the operation waits for a broadcast that is never
// coming.  Listing only the measured ones would be choosing the smaller
// protection by taste, and the cost of the larger one is bounded below.
//
// FINDING 098.  The set carries TWO consequences of that one engine path, and
// both are read from it rather than from a second list.  A posted key can
// wedge (096, above); and a posted key changes nothing -- the engine files it
// with `mutation = false`, the client's postcondition requires the revision to
// stay put and `changed: false` (narrow-editor-v2-client.js,
// `_validateInherited`), and the base class's own `moveCharacter` enqueues
// it as a non-mutation.  So `action()` enqueues these six as non-mutations
// as well.
//
// SPEC-M3-link-batch-v21 4.1: finding 142's two document moves take the same
// path (`Key::HOME | Mod1`, `Key::END | Mod1`, posted, `mutation = false`), and
// natively they are SILENT at the boundary -- at least 2 s without a callback
// when the caret is already at the start or the end -- which is exactly the
// shape this set exists for.  So eight.  `postconditionClassOf` in the client
// is the other statement of the same fact, and a test holds the two equal
// (11.1 D13).  (Nine since select-all, SPEC-M3-select-all-v26 -- see below.)  Which
// of the moves bank a dirty document before they go out is
// a second set, CHECKPOINTED_MOVES, below (finding 151).
//
// SPEC-M3-select-all-v26 4.3 (review 2026-10-30 item 2): select-all is the
// ninth.  It reaches the engine as a posted key (Key::A | Mod1, mutation =
// false) and takes the move postcondition, so D13 holds this set equal to the
// move class with it in.  Left out, it would go into the queue as a mutation:
// Ctrl+A would mark an untouched document unsaved (finding 098's shape) and a
// read-only document would refuse it.  Not in CHECKPOINTED_MOVES: selecting
// changes nothing that a checkpoint could save.
const BOUNDARY_CAPABLE_MOVES = new Set([
  "move-character-left", "move-character-right",
  "move-line-up", "move-line-down", "move-line-home", "move-line-end",
  "move-document-start", "move-document-end",
  "select-all",
]);

// FINDING 151 (SPEC-M3-link-batch-v21 §12.3 (b); fable ruling 1, Q2).  The
// moves that still take finding 096's checkpoint before they go out: the six
// arrow, Home and End moves, NOT finding 142's two document moves.
// BOUNDARY_CAPABLE_MOVES stays the posted keys (nine with select-all) -- which are
// non-mutations (098) and D13's closed list; this set names which of them pay
// for a save first.
//
// Why Ctrl+Home/End do not.  The checkpoint answers a posted key that, at a
// boundary, never gets the callback it waits for.  On this engine the two
// document moves answer by their readback within 251 ms (D7's silent presses,
// 250.6-251.2 ms), so that premise is false for them, and the claim is
// withdrawn rather than kept up by machinery (CLAUDE.md, criteria §4).  The
// checkpoint was also the trigger of finding 151: right after its save the
// move answers by that readback with the OLD caret, before Writer's
// GoToEndOfDoc has run, and the character typed next landed at the pre-move
// caret on a dirty document 18/18 (V1, V2, V4, both browsers); without it,
// at the document end 18/18 (V9, findings/evidence/link-batch-v21/shakedown/
// diag-dirty-move/).  What is given up: a dirty document's Ctrl+Home/End no
// longer banks the work, so after an engine death it rests on the next arrow
// move, the autosave or a save.
//
// Why the six still do.  Not because this engine needs it -- it answers their
// press too, and the same overtaking follows an arrow's checkpoint (V8d, 6/6,
// and on 0.2.24) -- but because the counted check
// `a-boundary-arrow-press-does-not-cost-the-work` pins their checkpoint, and
// taking it out goes through §34.  Their fix is the ordered-commands batch
// (finding 151's residual (b)).
const CHECKPOINTED_MOVES = new Set([
  "move-character-left", "move-character-right",
  "move-line-up", "move-line-down", "move-line-home", "move-line-end",
]);

// FINDING 119 (spec SPEC-M3-production-ui §14.1): the two deletes go through
// the selection barrier; a format barrier's EDITOR_STATE_UNAVAILABLE carries its
// own detail and keeps the disposition it has.
const SELECTION_BARRIER_DELETES = new Set(["delete-backward", "delete-forward"]);

export function stateUnavailableOnDelete(action, error) {
  return SELECTION_BARRIER_DELETES.has(action)
    && error?.code === "EDITOR_STATE_UNAVAILABLE"
    && (error?.details?.formatBarrier ?? error?.formatBarrier ?? null) === null;
}

// A Symbol, not a string key: this rides through the base class's resolve path
// on an object the base class treats as an opaque result, and a string key
// could collide with a field a future engine payload adds.  It never leaves
// `action()` -- the `.then` below unwraps it and rethrows the original error.
const DISPATCHED_UNVERIFIED = Symbol("dispatchedUnverified");

/**
 * The shape of the selection a `selectRange` result describes, or null when the
 * result does not describe one.
 *
 * FINDING 079, AND THIS IS THE SEAM THAT WAS MISSING.  The product page derived
 * the shape inline from `result.collapsed` and `result.rectangles` -- the shape
 * `editor-shell/editor-client.js` assembles on the V1 path.  The v2 client
 * assembles nothing: `ParagraphEditorClient.selectRange` hands back the
 * worker's envelope, whose keys are `method, revision, completion,
 * callbackSequenceBefore, callbackSequenceAfter, state`, and the selection sits
 * at `state.selection`.  Both reads were `undefined`, `undefined === false` is
 * false, `undefined?.length ?? 0` is 0, and the page computed `collapsed` for
 * every drag ever made.  Nothing was stale; nothing was ever read.
 *
 * It lives here, exported and unit-tested, rather than inline in the page,
 * because the defect's CLASS is "a derivation with no test read a shape some
 * other layer assembles".  A DOM flag on the page is a tripwire for the next
 * drift; it is not a guard against a second reader looking in a second wrong
 * place.  One accessor with its own tests is.
 *
 * Returns null rather than "collapsed" when it cannot tell.  Those are
 * different claims and conflating them is the whole finding: the caller decides
 * what to do about not knowing, and cannot do that if not-knowing has been
 * spelled as an answer.
 */
export function selectionShapeOf(result) {
  const selection = result?.state?.selection;
  if (typeof selection?.collapsed !== "boolean") return null;
  if (selection.collapsed) return "collapsed";
  // `rectangles.length > 1` as the cross-paragraph test is INHERITED, not
  // established here: a single paragraph that wraps onto two lines also yields
  // more than one rectangle.  Measured 2026-08-23 on e2-editor-v7 -- a drag
  // inside one line gave 1 rectangle and one across two paragraphs gave 3 --
  // which shows the two cases this profile meets are separated, not that the
  // rule is right in general.  Both range shapes are offered together for every
  // action that takes a range, so nothing currently turns on the distinction.
  return (selection.rectangles?.length ?? 0) > 1 ? "range-cross" : "range-single";
}

/**
 * What a result that could not be read looks like, for a caller that wants to
 * report rather than guess.  Keys only: the envelope carries document text in
 * `state`, and an unreadable-shape report is not a reason to copy a user's
 * paragraph into a DOM attribute.
 */
export function selectionShapeEvidence(result) {
  if (result === null || result === undefined) return String(result);
  if (typeof result !== "object") return typeof result;
  const top = Object.keys(result).join(",");
  const state = result.state && typeof result.state === "object"
    ? Object.keys(result.state).join(",") : null;
  return state === null ? top : `${top}|state:${state}`;
}

/**
 * Did the selection change?  (Ruling 6 Q2, finding 138; the companion of the
 * base class's `caretDiffers`.)
 *
 * The v2 state reply carries `selection: {observed, collapsed, start, end,
 * rectangles}` (the engine's `appendEditorState`, forwarded raw by the
 * worker's `editorGetStateV2` branch).  `collapsed` and `rectangles` are the
 * two fields a click can change -- a click on a live selection collapses it
 * -- so those two are compared: `collapsed`, the rectangle count, and each
 * rectangle's position.  Position only, for 052's reason: a relayout inside
 * the click's window can change a rectangle's height, and a relayout must not
 * stand in for a click.  `observed`, `start` and `end` are not compared --
 * `observed` is about the readback, not the document, and the end points
 * follow the rectangles.  Two absent selections do not differ.
 */
export function selectionDiffers(selection, previous) {
  if (!selection || !previous) return Boolean(selection) !== Boolean(previous);
  if (selection.collapsed !== previous.collapsed) return true;
  const rectangles = Array.isArray(selection.rectangles) ? selection.rectangles : [];
  const before = Array.isArray(previous.rectangles) ? previous.rectangles : [];
  if (rectangles.length !== before.length) return true;
  for (let index = 0; index < rectangles.length; index += 1) {
    if (caretDiffers(rectangles[index], before[index])) return true;
  }
  return false;
}

/* ------------------------------------------------------------------------
 * SPEC-M3-link-batch §4.3, §10.8, §10.10 Q-A, §12.3: the page number.
 *
 * The page draws 「第 N 頁，共 M 頁」 from `handle.pageRectangles()`, Writer's
 * rule computed on the page: N is the first page that intersects the visible
 * region, L the last, M the number of rectangles.  The three functions and the
 * scheduler below are the whole of that decision, kept here -- exported,
 * DOM-free, clock-free -- for the reason `selectionShapeOf` is: a derivation
 * the page would otherwise do inline, with no test, on a shape some other
 * layer assembles.  The page only wires them to an element.
 *
 * Named limit L-page-margin: Writer subtracts the page margins before it
 * tests the overlap (`SwViewShell::GetFirstLastVisPageNumbers`); the
 * rectangles carry no margins, so the whole rectangle is used and a view that
 * shows only a previous page's bottom margin counts that page.
 * ---------------------------------------------------------------------- */

function isRectangle(value) {
  return value !== null && typeof value === "object"
    && Number.isFinite(value.x) && Number.isFinite(value.y)
    && Number.isFinite(value.width) && Number.isFinite(value.height);
}

/** Strict on both axes: a region that only touches an edge sees nothing. */
function intersects(a, b) {
  return a.x < b.x + b.width && b.x < a.x + a.width
      && a.y < b.y + b.height && b.y < a.y + a.height;
}

/**
 * The 1-based span of pages a visible region covers -- `{first, last, count}`
 * -- or null when nothing intersects or the inputs are not rectangles.
 *
 * String order IS page order (core appends page frames in order,
 * `sw/source/core/crsr/crsrsh.cxx`, `SwCursorShell::getPageRectangles`), so
 * the list is never sorted and nothing is inferred from equal heights: a
 * landscape page or a section with its own page size breaks any such guess.
 * Total: a malformed entry is skipped for N and L and still counted in M, so
 * that M stays what the engine said (`rectangles.length` == `getParts()`, the
 * SDK parser's own rule).
 */
export function pageSpanOf(rectangles, region) {
  if (!Array.isArray(rectangles) || rectangles.length === 0 || !isRectangle(region)) return null;
  let first = 0;
  let last = 0;
  for (let index = 0; index < rectangles.length; index += 1) {
    const page = rectangles[index];
    if (!isRectangle(page) || !intersects(page, region)) continue;
    if (first === 0) first = index + 1;
    last = index + 1;
  }
  return first === 0 ? null : { first, last, count: rectangles.length };
}

/**
 * The visible region in twips, from what the page already measures: device
 * rows [top, bottom) of #paper inside #desk (`visibleDocRows()`), the
 * document's rows (`docRows`) and its size in twips.  The full document width:
 * the page never scrolls sideways, and Writer's rule is about the vertical
 * overlap.  Null when there is nothing to scale by or nothing visible.
 */
export function visibleRegionTwips(top, bottom, docRows, widthTwips, heightTwips) {
  if (![top, bottom, docRows, widthTwips, heightTwips].every(Number.isFinite)) return null;
  if (docRows <= 0 || widthTwips <= 0 || heightTwips <= 0 || bottom <= top) return null;
  const scale = heightTwips / docRows;
  return { x: 0, y: top * scale, width: widthTwips, height: (bottom - top) * scale };
}

/** 「第 N 頁，共 M 頁」, or 「第 N–L 頁，共 M 頁」 (U+2013) across pages; null for anything that is not a span. */
export function pageStatusText(span) {
  if (span === null || typeof span !== "object") return null;
  const { first, last, count } = span;
  if (![first, last, count].every(Number.isInteger)) return null;
  return first === last
    ? `第 ${first} 頁，共 ${count} 頁`
    : `第 ${first}–${last} 頁，共 ${count} 頁`;
}

/**
 * When the page asks the engine for the rectangles, and when it only
 * recomputes (§10.8).  Clock-free; `read(key)` is injected, so node can drive
 * it without a DOM or an engine.
 *
 * READS (one engine call each): after every open of a document -- the key is
 * the document, never the counter, because a fresh engine starts its counter
 * at 0 again; when the observed `documentSizeChangedCount` differs from the
 * value the last read was issued at; when a paint reply reported
 * `documentSizeChanged`.  NEVER on `documentChangeSequence` (typing sends no
 * INVALIDATE_TILES, F2), scroll, resize, zoom or caret movement: those only
 * recompute N and L on the page from the last answer.
 *
 * COALESCED: at most one read in flight; triggers that arrive meanwhile
 * collapse into exactly one follow-up, issued at the latest observed counter.
 * A read that fails reports null (the page hides the line, toasts nothing --
 * a page number is not worth a toast) and puts the scheduler back in its
 * "no read issued for this document" state, so the next state write of any
 * kind re-reads (ruling 6 Q4: a BUSY during a merge must not hide the line
 * until the next size change).  A read that always fails therefore costs one
 * read per state write while it fails, not one per trigger.  An answer for a
 * document that is no longer current is dropped.  A `read` that throws
 * synchronously is a failed read, not an exception on the page.
 *
 * Counted (reads, failures, dropped) for the reason every counter in this
 * file is: "it never read" and "it is not wired" are the same green otherwise.
 */
export class PageRectanglesScheduler {
  constructor({ read, offered = () => true, onResult = () => {} } = {}) {
    if (typeof read !== "function") throw new TypeError("PageRectanglesScheduler needs read(key)");
    this._read = read;
    this._offered = offered;
    this._onResult = onResult;
    this._key = null;        // the document the line describes
    this._observed = null;   // the latest documentSizeChangedCount seen for it
    this._issuedAt = null;   // the counter the last read was issued at
    this._inFlight = false;
    this._again = false;
    this.reads = 0;
    this.failures = 0;
    this.dropped = 0;
  }

  static counterOf(editorState) {
    const value = editorState?.documentSizeChangedCount;
    return Number.isInteger(value) ? value : null;
  }

  /** A document is open: the first open, a reopen after a refusal, a restart. */
  documentOpened(key, editorState) {
    if (key === null || key === undefined) return;
    this._key = key;
    this._observed = PageRectanglesScheduler.counterOf(editorState);
    this._issuedAt = null;
    this._schedule();
  }

  /** The page's editorState was written for `key`; only the counter matters. */
  stateObserved(key, editorState) {
    if (key !== this._key || this._key === null) return;
    const counter = PageRectanglesScheduler.counterOf(editorState);
    if (counter === null) return;
    this._observed = counter;
    if (this._issuedAt !== null && counter === this._issuedAt) return;
    if (this._issuedAt === null && this._inFlight) { this._again = true; return; }
    this._schedule();
  }

  /** A paint reply for `key` carried `documentSizeChanged: true`. */
  sizeChangeReported(key) {
    if (key !== this._key || this._key === null) return;
    this._schedule();
  }

  /** The session closed or the page let the document go: answers in flight are dropped. */
  closed() {
    this._key = null;
    this._again = false;
  }

  _schedule() {
    if (this._offered() !== true) { this._again = false; return; }
    if (this._inFlight) { this._again = true; return; }
    this._issue();
  }

  _issue() {
    const key = this._key;
    this._inFlight = true;
    this._again = false;
    this._issuedAt = this._observed;
    this.reads += 1;
    let answer;
    try {
      answer = Promise.resolve(this._read(key));
    } catch (error) {
      answer = Promise.reject(error);
    }
    answer.then((result) => this._settle(key, result, null),
                (error) => this._settle(key, null, error));
  }

  _settle(key, result, error) {
    this._inFlight = false;
    try {
      if (key !== this._key) this.dropped += 1;
      else if (error !== null) {
        this.failures += 1;
        // Ruling 6 Q4 (condition 48).  Back to "no read issued for this
        // document", so the next state write of any kind re-reads.  Without
        // this a read that failed BUSY (every command is BUSY while a barrier
        // is in flight, probe_engine.cpp:6100-6106) had recorded its counter
        // as issued, and the drain's state write after the merge -- the same
        // counter -- was ignored at stateObserved's early return; the line
        // stayed hidden until the next counter change, reopen or paint-reported
        // size change.  Retries are bounded by state writes, and the action
        // that caused the BUSY always ends with one.  One branch, no code
        // string: a torn reply is followed by its own counter push anyway, a
        // timeout means the session is dying, UNSUPPORTED_OPERATION is gated
        // off by offered().
        this._issuedAt = null;
        this._onResult(key, null, error);
      }
      else this._onResult(key, result, null);
    } finally {
      if (this._again && this._key !== null) this._schedule();
      else this._again = false;
    }
  }
}

export class NarrowEditorV2Session extends EditorSession {
  constructor(options = {}) {
    super(options);
    let client = null;
    this.clientReplacements = 0;
    // SPEC-M3-page-honesty §3: a read-only file opens view-only.  See _enqueue.
    this._viewOnly = false;
    // FINDING 111: operations held behind typed text (see _enqueue).
    this._afterTyped = [];
    Object.defineProperty(this, "editor", {
      configurable: true,
      enumerable: true,
      get: () => client,
      set: (assigned) => {
        if (assigned === null || assigned === undefined) {
          client = null;
          return;
        }
        // Built from the document the base class just opened, not from the
        // session's field, so that a base class which ever opened two
        // documents could not silently hand this the wrong one.
        client = new NarrowEditorV2Client(assigned.document);
        this.clientReplacements += 1;
      },
    });
    // FINDING 096.  Counted, not merely done -- the same reason the stale-write
    // guard below keeps a number: "the checkpoint was taken" and "the branch
    // that takes it is unreachable" produce the same green from outside, and a
    // check that reads only `hasCheckpoint` cannot tell a checkpoint this
    // gesture banked from one some earlier selection left behind.
    this.boundaryCheckpointsTaken = 0;
    this.boundaryCheckpointsSkipped = 0;
    // Finding 109: refusals that reached the checkpoint call (banked or not).
    this.boundaryRefusalCheckpoints = 0;
    // SPEC-M3-link-batch-v21 10.3: see `_enqueue`.
    this.enqueueCount = 0;
    this._beforeEnqueue = typeof options.beforeEnqueue === "function"
      ? options.beforeEnqueue : null;
    this._guardEditorStateAgainstStaleWrites();
    // Ruling 6 Q3 (condition 47): see _enqueueOwned.
    this._watchQueue();
  }

  /**
   * Finding 084.  Refuse a state write whose `sourceSequence` goes BACKWARDS.
   *
   * THE OTHER HALF OF FINDING 068's GUARD.  `snapshot.editorState` has two
   * writers: the engine's `editor-state` announcement, handled below, and the
   * drain's own `editor.getState()` in `EditorSession._drain()`.  068 gave the
   * ANNOUNCEMENT a guard and its comment says exactly why -- "a slow event
   * could land after a fresher read and move the caret backwards".  The
   * symmetric case was left unguarded: a slow READ landing after a fresher
   * EVENT. That is this defect, and it is the one the product actually hits.
   *
   * MEASURED 2026-08-27, `e2-editor-v11`, 48 commits: 10 of them dropped, and
   * every single one shows the same thing in the page's own state log --
   *
   *     seq=294 caret=3458,4904 rev=128
   *     seq=295 caret=3458,4904 rev=128
   *     seq=296 caret=5618,4904 rev=128   <- the caret ARRIVES
   *     seq=294 caret=3458,4904 rev=129   <- the drain writes it BACK
   *
   * -- `sourceSequence` going backwards while `revision` goes forwards in the
   * same row, which identifies the writer because only the drain writes those
   * two together. The sink was moved to the new caret and then moved back, and
   * nothing asks again until the next commit, so the caret is a commit behind
   * for a whole keystroke. The engine was never behind: asked 52-54 ms into
   * every one of those stalls, it already held the new caret.
   *
   * WHY IT WRAPS `update` AND NOT `transition`.  A reopen builds a FRESH engine
   * whose sequence counter starts near zero, and that is a legitimate move
   * backwards -- it goes through `transition`, which this does not touch. Every
   * writer that can be stale goes through `update`.
   *
   * WHY THE WHOLE `editorState` IS DROPPED rather than merged field by field.
   * The stale object is a snapshot of one moment; the fresher one is a snapshot
   * of a later moment. Everything the page reads out of it -- `caret`,
   * `selection`, `format`, `caretParagraph`, `documentOutline` -- is carried by
   * both. Merging would mean deciding which of two consistent snapshots each
   * field should come from, which is how a state gets assembled that never
   * existed.
   *
   * THE REST OF THE PATCH STILL APPLIES. `revision` and `dirty` ride along with
   * the drain's write and they are not stale; only `editorState` is.
   *
   * AND IT IS IN A SUBCLASS FOR FINDING 068's REASON, not out of taste: the
   * natural home is `EditorSession._drain()`, and `editor-shell/editor-session.js`
   * is bound to E1-C's verdict (`check_e1_c_bundle_intact.py`, shell bundle
   * `187706b2…`). Editing it unbinds a shipped verdict that has nothing to do
   * with this defect.
   */
  _guardEditorStateAgainstStaleWrites() {
    const machine = this.state;
    const write = machine.update.bind(machine);
    // Counted, not just prevented: "the guard never fired" and "the guard is
    // not installed" produce the same green otherwise, and this tree has paid
    // for that shape often enough to write the number down.
    this.staleEditorStateWrites = 0;
    machine.update = (patch = {}) => {
      const next = patch?.editorState?.sourceSequence;
      const current = machine.snapshot.editorState?.sourceSequence;
      if (Number.isInteger(next) && Number.isInteger(current)
          && next < current) {
        this.staleEditorStateWrites += 1;
        const { editorState, ...rest } = patch;
        return write(rest);
      }
      return write(patch);
    };
  }

  /**
   * Finding 068.  Take the caret from the engine's own announcement.
   *
   * WHY THIS IS AN OVERRIDE AND NOT AN EDIT TO THE BASE CLASS.  The natural
   * home for this is `EditorSession._handleEngineEvent`, and putting it there
   * is what I did first.  `check_e1_c_bundle_intact.py` refused it:
   * `editor-shell/editor-session.js` is bound to E1-C's verdict
   * (`E1_GO_ODT_EDITOR`, shell bundle `187706b2…`), so editing it unbinds a
   * verdict that has nothing to do with this defect.  A subclass reaches the
   * same event with none of that cost.
   *
   * THE DEFECT.  The drain reads editor state once per queued operation, and
   * insert replies as soon as the paste is posted -- before the cursor
   * callback carrying the new caret rectangle.  Measured over eleven runs: the
   * read is answered at `sourceSequence` 5, the cursor callback is sequence 6,
   * and nothing asked again, so the caret stayed one commit behind and the page
   * drew it there. That is what an operator reported twice, two days running.
   *
   * TWO GUARDS, neither decoration:
   *
   * `sourceSequence` must ADVANCE.  Events and drain reads are two sources for
   * one field, so without this a slow event could land after a fresher read and
   * move the caret backwards -- trading a caret that lags for one that jitters,
   * which is worse because it is not reproducible.
   *
   * The session must be USABLE.  During `loading` there is no document to draw
   * on, and during recovery the snapshot is the thing being rebuilt; publishing
   * a caret there would describe a document the page has already let go.
   */
  _handleEngineEvent(event) {
    super._handleEngineEvent(event);
    if (event?.event !== "editor-state") return;
    const phase = this.state.snapshot.state;
    if (phase !== "ready" && phase !== "busy") return;
    const next = event.sourceSequence;
    if (!Number.isInteger(next)) return;
    const current = this.state.snapshot.editorState?.sourceSequence;
    if (Number.isInteger(current) && next <= current) return;
    this.state.update({
      editorState: {
        ...this.state.snapshot.editorState,
        documentHandle: event.documentHandle,
        revision: event.revision,
        sourceSequence: next,
        documentChangeSequence: event.documentChangeSequence,
        // SPEC-M3-link-batch 12.3: the page number's re-read trigger.  This
        // object is an allowlist (the third writer of `editorState`; the other
        // two are the base class's open and drain, which pass the worker's
        // projections through), and a field not named here never reaches the
        // page -- the announcement that carries the counter's arrival is the
        // one with `source: "document-size-changed"`, and it goes through
        // HERE.  `null` on profiles whose engine emits none.
        documentSizeChangedCount: Number.isInteger(event.documentSizeChangedCount)
          ? event.documentSizeChangedCount : null,
        visible: event.visible,
        caret: event.caret,
        selection: event.selection,
        a11y: event.a11y,
        // The projected name, carried so the page has ONE name for the focused
        // paragraph whichever reply last wrote this snapshot.  Measured: this
        // announcement is the writer that wins in practice, so without this
        // line `caretParagraph` is absent from the page's state essentially
        // always -- see the worker's comment at the postEvent that sends it.
        caretParagraph: event.caretParagraph,
        documentOutline: event.documentOutline,
        format: event.format,
        schedulerProbe: event.schedulerProbe,
      },
    });
  }

  /**
   * FINDING 138 (ruling 6 Q2, condition 45).  Click, and return once the
   * engine has shown it processed THIS click.
   *
   * THE BASE'S CONTRACT, KEPT: the same arguments and options (`caretTimeoutMs`,
   * `caretAckGraceMs`), the same result shape, the same three
   * `caretConfirmedBy` values, the same EDITOR_CARET_NOT_PLACED error with the
   * same details.  Read the base's comment first; everything there about
   * finding 048 (a predicate equally true had the click never happened is not
   * a confirmation), 051 (the line band) and 052 (the caret moved off the
   * clicked line) still holds.
   *
   * THE DEFECT.  The base returns a same-line click as placed when
   * `sourceSequence` advanced and the caret is on the clicked line.  The
   * sequence advances for callbacks the click did not cause: on v19
   * LOK_CALLBACK_INVALIDATE_TILES sets editorStateChanged unconditionally
   * (probe_engine.cpp:2593-2596) and the base's own comment says so; v20 adds
   * DOCUMENT_SIZE_CHANGED.  A lone one inside the click's 22-28 ms window --
   * the caret already on the clicked line, at the old x -- ends the wait at
   * 4-6 ms with the OLD caret in the result, and the next synchronous paste or
   * format lands there.  Measured on the real base against a scripted engine
   * (ruling 6 §Q2's table): three false acknowledgements in seven arms.
   *
   * THE RULE.  Evidence = the sequence advanced AND a field the click can
   * change differs from the state read before the click: the caret position
   * (`caretDiffers`, position only, as the base) or the selection
   * (`selectionDiffers`: `collapsed` or `rectangles`).  Return on evidence when
   * on target; on `onTarget` after `graceMs` as today (the identical-point
   * click, where the engine has nothing to say); on evidence with the caret
   * moved off the line (052).  Never on the sequence alone.  Requiring the
   * caret to MOVE would be too narrow: a click that collapses a selection at
   * its caret end changes the selection and not the caret rectangle, and would
   * wait out the grace for nothing.  No arm pays more than it pays today; the
   * only arm that waits the grace is the one that waited it before, and the
   * test keeps it as a control.
   *
   * AN OVERRIDE, as 068's `_handleEngineEvent` and 084's guard are: the
   * natural home is `EditorSession.placeCaret`, and `editor-shell/
   * editor-session.js` is bound to E1-C's verdict (`check_e1_c_bundle_intact.py`,
   * shell bundle `187706b2…`).  The page's three callers are unchanged.
   *
   * NOT MEASURED ON WASM whether a lone tile or size callback occurs inside a
   * click's window (finding 138 says so); the harness is the evidence.
   *
   * FINDING 140 (ruling, 2026-10-14).  The wait above has two exits, and on a
   * blank page a click anywhere below the first line closes both: the caret
   * is not on the clicked line (there is no line there) and the engine clamps
   * it to the one position it already has, so it never moves.  Measured on
   * the owner's path: 30.0 s, 5,328-5,550 `getState` polls, then
   * EDITOR_CARET_NOT_PLACED, with the paste the user made meanwhile queued
   * behind it (findings/evidence/paste-latency/).  This is 052's named
   * residual ("the second click outside the text") met on the FIRST click of
   * every new document.
   *
   * THE FIX IS 052'S PRESCRIPTION: ask the engine.  `editorPlaceCaretV2`
   * posts the mouse events itself and answers on the cursor callback the
   * click caused, or -- when the click changed nothing and no callback came
   * -- at its own 250 ms readback deadline, naming which in `completion`.  It
   * never completes on a tile or size callback (its required callback is the
   * visible cursor), so 138's lone bump cannot end it.  The answer is still
   * JUDGED here with 138's predicate, never trusted for having arrived: on
   * evidence, the three verdicts the base has; without evidence and on the
   * clicked line, `already-at-target` after the grace, as today; without
   * evidence and off the line -- the blank-page click -- the same grace is
   * given first (048: a core that has not processed the click yet answers the
   * readback with the old caret; a click landing inside the grace is seen by
   * the re-read and judged as evidence), and then the click is reported
   * answered with the caret where the engine left it:
   * `engine-answered-the-caret-stayed`, `caretOnClickedLine: false`.  The
   * queue is no longer held: the paste behind it goes out at ≈ 0.4 s instead
   * of 30 s.  A click the core processes only AFTER the grace is accepted with
   * the old caret -- the same bound the identical-point click has always had,
   * named in the tests.
   *
   * THE POLLING PATH STAYS as the fallback: a client without the entry point,
   * a profile whose worker refuses it (UNSUPPORTED_OPERATION), or an engine
   * that is BUSY behind a barrier take v67's loop below, unchanged, with the
   * same timeout and error.  Any other engine error is the caller's.
   * `caretConfirmedBy` gains one value; nothing in the page reads it.
   *
   * SECOND PASS (task 10-14h, 2026-10-14).  The pre-v68 129-B witness found
   * two defects in the paragraph above as first shipped (every click asked
   * the engine):
   *
   *   1. The page sends `caret.y + caret.height / 2` (reopen, moveFromPoint);
   *      on a line of odd height that is a half-integer, the worker refuses
   *      it (INVALID_ARGUMENT: "requires non-negative integer twips"), and the
   *      refusal reached the user as a toast with the range left selected --
   *      6 of 54 cells in both browsers.  The engine is now asked with the
   *      ROUNDED point.  (v67's `document.click` took the same value into an
   *      i32 parameter, where the wasm boundary truncates it toward zero.)
   *   2. A click that collapses a range at the caret's own point moves no
   *      caret, so core emits no visible-cursor callback -- the only callback
   *      the engine's place-caret completes on -- and the engine answers at
   *      its 250 ms deadline: every 129-B click went from 26-32 ms to
   *      253-268 ms.  Measured on those bytes with `completion` recorded
   *      (findings/evidence/paste-latency/second-pass/): a moving click is
   *      answered on the callback at 24 ms, the collapse click at 251 ms
   *      (`verified-caret-readback`).  Nothing on this side can make the
   *      engine complete earlier, and returning before it has answered is
   *      not an option either: a pending place-caret holds gEditorPending
   *      and the key queued behind the click would be answered BUSY.
   *
   * THE RULE IS THE SELECTION THE CLICK IS MADE ON.  A click made while a
   * range is open collapses it; that collapse is the click's own evidence
   * under 138's predicate, pushed by the TEXT_SELECTION callback at the speed
   * v67 had, so such a click takes v67's polling path.  A click made on a
   * collapsed selection asks the engine: answered on the cursor callback when
   * the caret moves, at the readback deadline when it cannot (the blank page,
   * the identical point) -- the bound the first pass bought, kept.  The page
   * clicks before an arrow key only when a range is open (finding 129's
   * moveFromPoint), so every one of those pairs is on the polling path.
   *
   * The polling path gains ONE exit, so that the first pass's bound is not
   * given back there: collapsed by the click and the caret stayed off the
   * clicked line -- the engine processed the click and left the caret where
   * its clamp puts it -- is accepted after the grace, as the engine path
   * accepts it, under the same `engine-answered-the-caret-stayed`.  NAMED
   * LIMIT: with a range open and a click core never processes (no evidence
   * at all) the timeout contract is v67's; no second click is posted to ask
   * the engine.  No instance of that shape is known in a text document: a
   * plain click on an open range always collapses it.
   */
  placeCaret(xTwips, yTwips, options = {}) {
    return this._enqueue("place-caret", async ({ document, editor }) => {
      const timeoutMs = Math.min(options.caretTimeoutMs ?? 30000, 30000);
      const graceMs = Math.min(options.caretAckGraceMs ?? 400, timeoutMs);
      const before = await editor.getState(options);
      const beforeSequence = before?.sourceSequence ?? null;
      const beforeCaret = before?.caret ?? null;
      const beforeSelection = before?.selection ?? null;
      const judge = (state) => {
        const sequenceAdvanced = state?.sourceSequence !== beforeSequence;
        const onTarget = caretIsOnLine(state?.caret, yTwips);
        const caretMoved = caretDiffers(state?.caret, beforeCaret);
        const selectionChanged = selectionDiffers(state?.selection ?? null, beforeSelection);
        // The click's own evidence, never the sequence alone.
        return { sequenceAdvanced, onTarget, caretMoved, selectionChanged,
                 acknowledged: sequenceAdvanced && (caretMoved || selectionChanged) };
      };
      const placed = (state, started, confirmedBy, onTarget, extra = {}) => ({
        state,
        revision: document.revision,
        caretConfirmedBy: confirmedBy,
        caretOnClickedLine: onTarget,
        caretWaitedMs: Date.now() - started,
        ...extra,
      });

      // Finding 140, second pass: the engine's own answer for a click made on
      // a collapsed selection; a click made on an open range collapses it and
      // is judged from that evidence on v67's path below (see the comment).
      const rangeOpen = beforeSelection?.collapsed === false;

      if (!rangeOpen && typeof editor.placeCaret === "function") {
        const started = Date.now();
        let answer = null;
        try {
          // Integer twips: the worker refuses anything else, and the page's
          // point is a half-integer on a line of odd height.
          answer = await editor.placeCaret(Math.round(xTwips), Math.round(yTwips), {
            ...options, timeoutMs: options.timeoutMs ?? timeoutMs,
          });
        } catch (error) {
          if (!PLACE_CARET_FALLBACK_CODES.has(error?.code)) throw error;
          answer = null;   // BUSY or no such entry point: v67's loop below
        }
        if (answer !== null) {
          let state = answer.state ?? await editor.getState(options);
          let verdict = judge(state);
          // No evidence yet: the grace the identical-point click already
          // pays, counted from the request, re-reading the core meanwhile.
          while (!verdict.acknowledged && Date.now() - started < graceMs) {
            await new Promise((resolve) => setTimeout(resolve, 5));
            state = await editor.getState(options);
            verdict = judge(state);
          }
          const extra = { completion: answer.completion ?? null };
          if (verdict.onTarget)
            return placed(state, started, verdict.acknowledged ? "engine-acknowledged" : "already-at-target", true, extra);
          if (verdict.acknowledged && verdict.caretMoved)
            return placed(state, started, "engine-moved-the-caret-off-the-clicked-line", false, extra);
          return placed(state, started, "engine-answered-the-caret-stayed", false, extra);
        }
      }

      // v67's path (finding 138): post the click, poll for evidence.  The
      // point goes to `document.click` as the caller gave it, as v67 sent it
      // (129-B's reference rounds were made with those bytes on the wire).
      // One exit added by the second pass: collapsed by the click and the
      // caret stayed off the clicked line, accepted after the grace.
      const started = Date.now();
      await document.click(xTwips, yTwips, options);
      let state = before;
      do {
        state = await editor.getState(options);
        const verdict = judge(state);
        const elapsed = Date.now() - started;
        if ((verdict.onTarget && (verdict.acknowledged || elapsed >= graceMs))
            || (verdict.acknowledged && verdict.caretMoved)) {
          return placed(state, started, verdict.onTarget
            ? (verdict.acknowledged ? "engine-acknowledged" : "already-at-target")
            : "engine-moved-the-caret-off-the-clicked-line", verdict.onTarget);
        }
        if (verdict.acknowledged && !verdict.onTarget && !verdict.caretMoved && elapsed >= graceMs)
          return placed(state, started, "engine-answered-the-caret-stayed", false);
        await new Promise((resolve) => setTimeout(resolve, 5));
      } while (Date.now() - started < timeoutMs);
      const error = new Error(
        "the caret did not reach the point that was clicked");
      error.code = "EDITOR_CARET_NOT_PLACED";
      error.details = {
        xTwips, yTwips, timeoutMs, graceMs,
        caret: state?.caret ?? null,
        sequenceAdvanced: state?.sourceSequence !== beforeSequence,
      };
      throw error;
    });
  }

  /**
   * FINDING 096, half C.  Bank the work before a key that can wedge.
   *
   * THE DEFECT THIS HALF REMOVES, and it is not the hang.  096 has two halves
   * and they are separable: the press is never answered (the engine's, fixed
   * by arming a deadline on that path), and when the session then dies there
   * is nothing to go back to.  The second half is this one, and it does not
   * depend on the first being right.  `_checkpointBeforeSelection` runs only
   * ahead of a range selection and only when the document is dirty, so before
   * today no caret movement ever took one -- which is why the notice the owner
   * saw read 「沒有檢查點，所以自上次儲存以來的內容不會回來。」 after ONE arrow
   * key.  The product's protection was attached to the wrong gesture; it was
   * not missing.
   *
   * IT REUSES THE BASE CLASS'S CHECKPOINT rather than writing a second one.
   * `editor-shell/editor-session.js` is hash-registered by E1-C and cannot be
   * edited, but calling into it costs nothing -- and a second copy of the
   * checkpoint logic is a second thing that can be subtly wrong in the part of
   * the product where being subtly wrong costs the user's unsaved work (this
   * file's own header says so about the queue).
   *
   * THE CONTENT STAMP IS THE PRICE CONTROL: a user holding an arrow key down
   * on a dirty document must not pay a full ODT save per keypress, so a move
   * whose content was already banked skips.  The stamp is the base class's
   * (`_currentContentStamp` against `_checkpointStamp`, the same comparison
   * `_checkpointBeforeSelection` makes itself); it is asked here first only so
   * the skip can be counted.  It holds as a price control because a move is
   * not a mutation -- `action()` enqueues the six with `mutation: false`, so
   * the drain does not bump the stamp after one (finding 098).
   *
   * NOT THE REVISION, and this paragraph used to say the opposite.  Until
   * finding 099 the guard compared `_checkpointRevision` with
   * `document.revision`, because moves bumped the stamp and revision did not.
   * Revision and content part company in two ways, and either one made that
   * guard skip a checkpoint the user's work needed:
   *   - ACROSS WORKERS.  Revisions restart at zero with every Worker
   *     (probe_engine.cpp on open; the base class says so beside the stamps),
   *     while the checkpoint survives the rollback -- that is what it is for.
   *     After one rollback the guard compared two unrelated counters, and when
   *     they coincided the next death went back to the OLDER bytes under a
   *     notice saying 「回到檢查點」.
   *   - WITHIN ONE WORKER.  A format action that comes back "dispatched,
   *     unverified" (`recoveryFor` → "review", resolved in `action()` below)
   *     may have changed the document, and the drain counts it as a mutation --
   *     but the engine does not advance the revision on that path
   *     (`failFormatBarrier` never calls `advanceRevision`).
   * A stamp names one content state for the whole session: `_contentSequence`
   * never resets, every counted mutation takes a new value, and a reopen
   * restores the stamp of the bytes it opened (editor-session.js,
   * `_openFresh`).
   * That is the property this needs.
   *
   * WHAT IT DOES NOT DO.  It does not make the press answer, and it must not
   * be read as doing so: with a pre-fix engine the user still waits out the
   * SDK's 30 seconds.  What changes is that the notice then says 「回到檢查點」
   * and the button behind it actually returns the work.
   */
  async _checkpointBeforeBoundaryMove(document) {
    // Nothing typed since the last save: there is nothing to lose, and a save
    // here would be a cost with no beneficiary.  The base class asks the same
    // question first, and asking it here too keeps the cheap answer cheap.
    // `dirty` means "typed" only because moves are not mutations (098).
    if (!this.state.snapshot.dirty) return;
    if (this.state.snapshot.hasCheckpoint
        && this._checkpointStamp === this._currentContentStamp) {
      this.boundaryCheckpointsSkipped += 1;
      return;
    }
    this.boundaryCheckpointsTaken += 1;
    await this._checkpointBeforeSelection(document);
  }

  /**
   * FINDING 109.  Bank the work while the engine can still write it.
   *
   * A delete at a paragraph boundary (Delete at a paragraph's end, Backspace
   * at its start) is refused with EDITOR_BOUNDARY_UNSUPPORTED, and every site
   * that raises it refuses BEFORE dispatching: the selection barrier before
   * `postUnoCommand` (probe_engine.cpp, `verifyAndDispatchSelectionBarrierDelete`
   * and `rejectSelectionBarrierAtDeadline`), the a11y core's semantic check
   * before `startUnoMutation`.  The document is exactly what it was.  But the
   * barrier leaves its selection behind and asks for a fresh Worker, the base
   * class blocks the queue as `restart-required` on the code
   * (editor-shell/editor-session.js:319) -- and from there a save is refused
   * and a restart reopens the last SAVED bytes.  A user who had placed the
   * caret with the mouse had no checkpoint, so one Delete lost everything typed
   * since the last save.
   *
   * SPEC-M3-paragraph-merge 10.1(d): an engine built with
   * OXSDK_MERGE_KEY_UNDO also raises this code AFTER pressing the user's key,
   * when the undo payload did not move by its deadline
   * (`details.mergeKey.keyPosted === true`).  Then "the document is exactly
   * what it was" is no longer known: the key may or may not have acted, and
   * the content stamp did not move either way.  What still holds, and is all
   * this path promises: a clean or already-banked document reopens the bytes
   * from before the key, a dirty one banks the engine's current content, and
   * in both every typed change survives; only the key's own effect is
   * uncertain, and the page says so (tests: "M1-3: keyPosted refusal ...").
   *
   * So this runs inside the operation, after the refusal and before the
   * rethrow: the drain still owns the engine, nothing is queued ahead of it,
   * and the content stamp has not moved (a refused action is not counted as a
   * mutation).  It is the base class's checkpoint, unchanged -- a no-op on a
   * clean document or on content already banked, and a failure is recorded as
   * `checkpointError` rather than thrown, so the refusal the caller gets is
   * still the engine's.  Whether a restart then loses anything is
   * `restartKeepsContent()`'s question, asked of the stamps, not of this.
   */
  async _checkpointBeforeBoundaryRestart(document) {
    this.boundaryRefusalCheckpoints += 1;
    await this._checkpointBeforeSelection(document);
  }

  /**
   * Would `restart()` now reopen exactly the content this session holds?
   *
   * The same choice `_openFresh` makes (editor-shell/editor-session.js): the
   * checkpoint when it is newer than the last save, otherwise the saved bytes.
   * True when the stamp of what it would open is the current content stamp.
   * NOT `!dirty || hasCheckpoint`: a checkpoint save that failed leaves an
   * OLDER checkpoint in place with `hasCheckpoint` still true, and reopening
   * that one loses the edits made since -- the case a host must not paper over
   * by restarting on the user's behalf.
   */
  restartKeepsContent() {
    if (this._authorityBytes === null) return false;
    const useCheckpoint = this._checkpointBytes !== null
      && this._checkpointStamp !== null
      && this._checkpointStamp > this._authorityStamp;
    const reopened = useCheckpoint ? this._checkpointStamp : this._authorityStamp;
    return reopened === this._currentContentStamp;
  }

  /**
   * Would `restart()` get a fresh Worker, or hit the generation ceiling?
   *
   * B1 (specs/SPEC-M3-production-ui.md §8, §9).  Asked BEFORE `restart()`,
   * because `restart()` disposes the live engine first and only then does
   * `_openFresh` check the ceiling (editor-shell/editor-session.js:148).  A
   * host that restarts on the user's behalf without asking turned the third
   * boundary refusal of a page load back into finding 109: engine gone, save
   * refused, the work alive only in the checkpoint bytes.
   */
  restartAvailable() {
    return this._generation < this._maxWorkerGenerations;
  }

  /**
   * The bytes a restart would reopen, handed out as SAVED -- for a host that
   * cannot restart any more and must put the work somewhere before a reload.
   *
   * Only from a stopped session (nothing in flight can move the content stamp)
   * and only when `restartKeepsContent()` holds: anything else would hand out
   * older bytes as if they were the work.  `null` otherwise, and nothing is
   * touched.  Marking clean at the hand-over is `save()`'s convention: the host
   * write that follows is covered by the page's `savesUnsettled`, and a write
   * that fails is the host's to strand and guard (finding 108).  Left dirty,
   * the reload the user is asked for would be guarded for nothing.
   */
  takeContentForRescue() {
    if (!["restart-required", "recoverable-error"].includes(this.state.snapshot.state)
        || !this.restartKeepsContent())
      return null;
    const useCheckpoint = this._checkpointBytes !== null
      && this._checkpointStamp !== null
      && this._checkpointStamp > this._authorityStamp;
    if (useCheckpoint) {
      this._authorityBytes = this._checkpointBytes.slice(0);
      this._authorityStamp = this._checkpointStamp;
    }
    this._checkpointBytes = null;
    this._checkpointRevision = null;
    this._checkpointStamp = null;
    this._checkpointError = null;
    this.state.update({
      dirty: false,
      hasSavedBytes: true,
      hasCheckpoint: false,
      checkpointRevision: null,
      checkpointError: null,
    });
    return this._authorityBytes.slice(0);
  }

  /**
   * Any of the fifteen, through the same queue as everything else.
   *
   * The queue is the point.  A paragraph action that ran outside it could
   * interleave with a committed keystroke, and the revision each of them
   * expects would be the other's.
   */
  action(action, options = {}) {
    return this._action(action, options, false);
  }

  /** ABI6 product keys keep their direction until their existing queue turn. */
  deleteKey(action, options = {}) {
    if (!["delete-backward", "delete-forward"].includes(action)
        || this.engine?.manifest?.editorContract?.abiVersion !== 6) {
      const error = new Error("deleteKey requires an ABI6 backward or forward delete");
      error.code = "INVALID_ARGUMENT";
      return Promise.reject(this._withDisposition(error));
    }
    return this._action(action, options, true);
  }

  _action(action, options, fromKey) {
    if (!ACTIONS.has(action)) {
      const error = new Error(`unsupported v2 editor action: ${String(action)}`);
      error.code = "EDITOR_ACTION_UNSUPPORTED";
      return Promise.reject(this._withDisposition(error));
    }
    return this._enqueue(
      `action:${action}`,
      async ({ document, editor }, tools) => {
        let dispatchedAction = action;
        if (fromKey) {
          const generation = this._generation;
          // One ordered read at dequeue, not a cached page shape or a waiter.
          const state = await editor.getState(options);
          if (generation !== this._generation || document !== this.document) {
            const error = new Error("delete key belongs to a stale Worker generation");
            error.code = "STALE_EDITOR_GENERATION";
            throw error;
          }
          const shape = selectionShapeOf({ state });
          if (state?.documentHandle !== document.handle
              || state?.selection?.observed !== true || shape === null
              || (shape !== "collapsed" && !editor.gesturesFor("delete-selection")?.includes(shape))) {
            const error = new Error("the current selection does not permit this delete key");
            error.code = "EDITOR_FORMAT_GESTURE_UNSUPPORTED";
            error.details = { dispatched: false, keyAction: action };
            throw error;
          }
          if (shape !== "collapsed") dispatchedAction = "delete-selection";
        }
        if (CHECKPOINTED_MOVES.has(action))
          await this._checkpointBeforeBoundaryMove(document);
        try {
          const result = await editor.action(dispatchedAction, options);
          if (result?.completion === "verified-boundary-noop" && result?.changed === false)
            tools.completedUnchanged();
          return fromKey ? { ...result, keyAction: action } : result;
        } catch (error) {
          // FINDING 119.  A delete the selection barrier could not verify in
          // time comes back as EDITOR_STATE_UNAVAILABLE with no barrier detail;
          // the disposition default made that a rollback, so the queue blocked
          // in recoverable-error with no checkpoint and the only exit reopened
          // the last SAVED bytes -- everything typed since was gone (measured,
          // findings/evidence/fast-delete-recovery/).  109's mould instead:
          // bank what the engine holds now, block as restart-required, and let
          // the page reopen it.  Banked whatever the key did: one of the four
          // engine exits for this code is (in theory) after the delete was
          // posted, so nothing here or on the page may say "unchanged" -- every
          // typed change survives, only the key's own effect is uncertain.
          // Scoped by action and code, never by message text (spec §14.1).
          if (stateUnavailableOnDelete(dispatchedAction, error)) {
            await this._checkpointBeforeBoundaryRestart(document);
            this._blockQueue(error, "restart-required", "editor-boundary");
            error.recovery = "restart";
            throw error;
          }
          this._blockQueueIfDispatched(error);
          if (error?.code === "EDITOR_BOUNDARY_UNSUPPORTED")
            await this._checkpointBeforeBoundaryRestart(document);
          // Finding 046's residual.  Declining to block is NOT enough to keep
          // the queue open: the base class blocks on the CODE, and
          // MUTATION_OUTCOME_UNKNOWN is in its RECOVERY_ERRORS
          // (editor-shell/editor-session.js:20, reached at :325).  That file is
          // hash-registered by E1-C, so it cannot be edited.
          //
          // The base class only reaches that decision when the operation
          // REJECTS -- `item.reject(error)` at :316 runs first, then the block
          // is a side effect keyed on the code.  So resolve instead, and
          // rethrow outside the drain.  The caller still gets the original
          // error object, with its original code.
          //
          // The sentinel carries no `state`, so the drain's success path takes
          // its fallback at :301-302 and asks the engine for one.  That is not
          // incidental: if the engine is wedged the call raises TIMEOUT, which
          // IS in RECOVERY_ERRORS, and the queue blocks after all.  The
          // softening revokes itself whenever the engine cannot show it is
          // alive.
          if (recoveryFor(error) === "review")
            return { [DISPATCHED_UNVERIFIED]: error };
          throw error;
        }
      },
      // FINDING 098.  Every action used to go in with `mutation: true`, so one
      // arrow key marked a never-typed document dirty, bumped its content
      // stamp, and the second one banked a checkpoint of the bytes it was
      // opened from.  A move changes nothing -- see BOUNDARY_CAPABLE_MOVES.
      { mutation: !BOUNDARY_CAPABLE_MOVES.has(action) },
    )
      .then((result) => {
        const carried = result?.[DISPATCHED_UNVERIFIED];
        if (carried) throw carried;
        return result;
      })
      .catch((error) => { throw this._withDisposition(error); });
  }

  /**
   * View-only (SPEC-M3-page-honesty §3, the owner's ruling A of 2026-09-29: a
   * file the user may not write opens to be read, not edited).
   *
   * THE GATE IS THE QUEUE, not the buttons.  Every operation that changes the
   * document reaches the engine through `_enqueue` with `mutation: true` --
   * the base class's commitText, delete, insertBreak, setInlineFormat and
   * undo, and this class's action() (all but BOUNDARY_CAPABLE_MOVES) and
   * redo().  Refusing there, BEFORE the item is queued, means a control the
   * page forgot to disable still changes nothing: no operation runs, the state
   * does not move, the queue is not blocked, and no recovery is offered --
   * nothing happened, so `recovery` is "none" (set here, because
   * `recoveryFor` does not know this code and `_withDisposition` keeps a
   * recovery that is already there).
   *
   * Moves stay allowed on purpose: reading a document is moving through it.
   * A flag on the session, not on the input adapter, so a restart (a fresh
   * Worker) does not quietly make the document editable again.
   */
  setViewOnly(on) {
    this._viewOnly = on === true;
  }

  get viewOnly() {
    return this._viewOnly === true;
  }

  /**
   * Does this control change the document?  Read from the same set that
   * decides the queue flag in action(), so the page's buttons and the gate
   * cannot disagree.  Fail-closed: any name this class does not know as a
   * move -- including "save", "undo", a typo, or an action added later --
   * counts as changing the document.
   */
  actionMutates(name) {
    return !BOUNDARY_CAPABLE_MOVES.has(name);
  }

  /**
   * Finding 107: does the session hold edits that no save has taken yet?
   *
   * `dirty` is set when a mutation completes and cleared when a save's bytes
   * are produced; `pending` covers the edit still inside the engine (dirty is
   * written only after the operation and its state read return), at the price
   * of also counting a move in flight.  NOT the revision: revisions restart at
   * zero with every Worker, so after a rollback to a checkpoint newer than the
   * last save a revision comparison says "saved" when it is not (the 099
   * class).  The page adds its own half -- a save asked for and not yet
   * settled by the host -- because only the page knows when that ends.
   */
  hasUnsavedEdits() {
    const snapshot = this.state.snapshot;
    return snapshot.dirty === true || (snapshot.pending ?? 0) > 0;
  }

  /**
   * SPEC-P-ms-formats 5.2: the format this document is saved in -- the one the
   * engine accepted it as (E5), read from the open document.  `odt` when the
   * engine does not say, which is every profile before e2-editor-v33: those
   * open nothing else.
   */
  documentFormat() {
    return documentFormatOf(this.document);
  }

  /**
   * SPEC-P-ms-formats 5.2: a save writes the document's own format -- a DOCX
   * goes back as DOCX, to the same file (the owner's ruling 1).
   *
   * THE BASE CLASS's `save()` WITH ONE TOKEN CHANGED.  `EditorSession.save()`
   * passes `{ format: "odt" }`, and editor-shell/editor-session.js is bound by
   * E1-C's verdict (check_e1_c_bundle_intact.py), so the format cannot be
   * passed through it.  Everything else is the base's code (its comments are
   * at editor-shell/editor-session.js:558): the same queue label, the same
   * timeout, the same finalize.  Because the base is frozen
   * the copy cannot drift from it; narrow-editor-v2-session.test.mjs runs the
   * base's method and this one side by side on an ODT document and requires
   * the same requests and the same state.
   */
  save(options = {}) {
    return this._enqueue("save", async ({ document }) => {
      const bytes = await document.save(
        { format: documentFormatOf(document) },
        { timeoutMs: options.timeoutMs ?? 180000, signal: options.signal },
      );
      return { bytes, revision: document.revision, contentStamp: this._currentContentStamp };
    }, { finalize: (result) => {
      const { bytes, contentStamp } = result;
      this._authorityBytes = bytes.slice(0);
      this._authorityStamp = contentStamp;
      this._checkpointBytes = null;
      this._checkpointRevision = null;
      this._checkpointStamp = null;
      this._checkpointError = null;
      this.state.update({
        dirty: false,
        hasSavedBytes: true,
        hasCheckpoint: false,
        checkpointRevision: null,
        checkpointError: null,
      });
      return result;
    } });
  }

  /**
   * SPEC-P-ms-formats 5.2: checkpoints are in the document's own format too.
   *
   * WHY NOT LEAVE THEM ODT.  A checkpoint is reopened under the document's
   * name (`_openFresh` passes `_authorityName`), and at the generation ceiling
   * `takeContentForRescue()` hands it to the host, which writes it over the
   * user's file.  An ODT checkpoint of a DOCX would put ODT bytes into
   * `report.docx`.  In the document's format, the bytes and the name agree on
   * every path that reuses them.
   *
   * The base class's method with one token changed, for the same reason as
   * `save()` above and tested the same way.
   */
  async _checkpointBeforeSelection(document) {
    const revision = document.revision;
    const contentStamp = this._currentContentStamp;
    if (!this.state.snapshot.dirty || contentStamp === this._checkpointStamp)
      return;
    try {
      const bytes = await document.save(
        { format: documentFormatOf(document) },
        { timeoutMs: this._selectionTimeoutMs },
      );
      if (document !== this.document || contentStamp !== this._currentContentStamp)
        return;
      this._checkpointBytes = bytes.slice(0);
      this._checkpointRevision = revision;
      this._checkpointStamp = contentStamp;
      this._checkpointError = null;
      this.state.update({
        hasCheckpoint: true,
        checkpointRevision: revision,
        checkpointError: null,
      });
    } catch (error) {
      this._checkpointError = {
        code: error?.code || "CHECKPOINT_FAILED",
        message: error?.message || String(error),
        details: error?.details || {},
      };
      this.state.update({ checkpointError: this._checkpointError });
    }
  }

  /**
   * SPEC-P-ms-formats 5.2, Save As: the document's content in `format`, as a
   * copy.  Through the queue, so it holds everything typed before it; NOT a
   * save of this document -- nothing here is marked clean, and the bytes are
   * never this session's authority or checkpoint (they are in a format the
   * document was not opened as, so a reopen under this document's name would
   * read them as the wrong thing).  What happens to the copy is the caller's.
   */
  saveCopy(format, options = {}) {
    if (typeof format !== "string" || format === "")
      return Promise.reject(Object.assign(new Error("saveCopy requires a format"),
                                          { code: "INVALID_ARGUMENT", recovery: "none" }));
    return this._enqueue("save-copy", async ({ document }) => {
      const bytes = await document.save(
        { format },
        { timeoutMs: options.timeoutMs ?? 180000, signal: options.signal },
      );
      return { bytes, format, revision: document.revision };
    });
  }

  _enqueue(label, operation, options = {}) {
    if (this._viewOnly && options?.mutation === true) {
      const error = new Error(`view-only: ${label} would change the document`);
      error.code = "EDITOR_VIEW_ONLY";
      error.recovery = "none";
      return Promise.reject(error);
    }
    // SPEC-M3-link-batch-v21 10.3, the page's held deletes.  This method is
    // the ONE entry every enqueue path takes -- typed text (the adapter's
    // commit reaches `commitText`, which calls this), clicks, selections,
    // undo/redo, save, every action -- so it is where "what was enqueued last"
    // can be known at all:
    //   * `beforeEnqueue(label)` runs FIRST, synchronously, so a host holding
    //     presses can send them ahead of the new item, in order (rule 4);
    //   * `enqueueCount` then counts this one, so a host can ask "is the last
    //     thing I sent still the last thing enqueued?" (rule 1).
    // After the view-only gate: a refused mutation is not enqueued.
    this._beforeEnqueue?.(label);
    this.enqueueCount += 1;
    // FINDING 111.  Typed text waits in the input adapter's own queue and
    // reaches this queue one character at a time, each after the previous one
    // completed; a key (Delete, Enter, a format, save, a click) came straight
    // here and could be dispatched before a character typed BEFORE it --
    // measured with real keys, both browsers (findings/evidence/111/).  So an
    // operation that is not typed text, arriving while the adapter still holds
    // characters, is held with the adapter's request count as its barrier and
    // released by `commitText` right behind the character it followed.  The
    // adapter is E1-C's and cannot change; this reads its public `state`.
    // `queueDepth` counts the character in flight too, so the hold lasts one
    // character longer than it must -- never out of order.
    if (label !== "commit-text"
        && ((this.input?.state?.queueDepth ?? 0) > 0 || this._afterTyped.length > 0))
      return this._holdBehindTyped(label, operation, options);
    return this._enqueueOwned(label, operation, options);
  }

  /**
   * Ruling 6 Q3 (condition 47).  Enqueue so that the operation can flip its
   * own queue item's `mutation` -- the one place `super._enqueue` is reached
   * (this class's `_enqueue` and `_releaseHeld`).
   *
   * WHY.  C's second exit (`verified-boundary-noop`, `changed: false`, the
   * revision unchanged) is a delete that changed nothing, and the engine says
   * so.  `action()` decides `mutation` at enqueue time from the action name
   * alone, so the frozen drain then marked the document dirty, bumped the
   * content stamp, banked one ODT checkpoint on the next boundary move and,
   * with a host, armed an autosave of unchanged bytes -- 098 (a non-mutation
   * marked as a mutation) and 099 (a stand-in for content) again.
   *
   * THE SEAM, pinned in narrow-editor-v2-session.test.mjs beside the first
   * one: the base pushes the item onto `this._queue` synchronously inside
   * `super._enqueue` (editor-session.js:263) and reads `item.mutation` only
   * AFTER the operation returns (:304, :309).  So the operation may clear the
   * flag on the item it is running as, and the drain honours it.
   *
   * HOW THE ITEM IS FOUND, and why not by looking at the queue afterwards.
   * `_drain()` is async and runs synchronously up to its first `await`: when
   * no drain is active it shifts the new item off the queue and starts the
   * operation INSIDE `super._enqueue`, so by the time that returns the queue
   * is empty again.  Measured on the fixture (part-2 README, "Ruling 6
   * fixes"): the README §4 sketch (`this._queue[before]`) finds the item only
   * when a drain is already busy, and never for the user's lone Backspace.
   * The push itself is the only moment the item is reachable, so the queue's
   * `push` is observed (`_watchQueue`, installed in the constructor the way
   * 084's guard wraps `state.update`), and the item is claimed by the identity
   * of the operation it carries.  EDITOR_NOT_READY pushes nothing and claims
   * nothing.
   *
   * Compensating afterwards (restoring the stamp and `dirty` in a `.then`)
   * would be wrong: the drain starts the next queued operation synchronously
   * after resolving, and `_checkpointBeforeBoundaryMove` reads `dirty` at its
   * top before any `.then` runs.  The view-only gate is unaffected: it reads
   * `options.mutation` before the operation; the flip is after.
   */
  _enqueueOwned(label, operation, options = {}) {
    let item = null;
    const tools = {
      completedUnchanged: () => { if (item !== null) item.mutation = false; },
    };
    const owned = (runtime) => operation(runtime, tools);
    const promise = super._enqueue(label, owned, options);
    if (this._lastQueued?.operation === owned) item = this._lastQueued;
    return promise;
  }

  /**
   * See `_enqueueOwned`.  Remembers the newest item the base pushed onto
   * `this._queue`; counted, because "the observer never saw a push" and "the
   * observer is not installed" are the same green otherwise.  Depends on the
   * base keeping ONE array for the session's life (it does: `_queue` is
   * assigned in its constructor only; `_blockQueue` splices in place) -- pinned.
   */
  _watchQueue() {
    const queue = this._queue;
    const push = queue.push.bind(queue);
    this._lastQueued = null;
    this.queuePushesSeen = 0;
    queue.push = (...items) => {
      this.queuePushesSeen += items.length;
      if (items.length) this._lastQueued = items[items.length - 1];
      return push(...items);
    };
  }

  _holdBehindTyped(label, operation, options) {
    return new Promise((resolve, reject) => {
      this._afterTyped.push({ label, operation, options, resolve, reject,
                              barrier: this.input.state.requestCount, generation: this._generation });
      // Characters the adapter cancels never reach commitText; its idle
      // releases whatever is still held.
      void this.input.idle().then(() => this._releaseHeld(Infinity));
    });
  }

  _releaseHeld(limit) {
    while (this._afterTyped.length && this._afterTyped[0].barrier <= limit) {
      const held = this._afterTyped.shift();
      // The base class stamps the Worker generation at enqueue time, so an
      // operation released after a restart would run on the fresh Worker,
      // against a document the key was never pressed in (spec §14.1).
      if (held.generation !== this._generation) {
        const error = new Error(`editor operation ${held.label} was held behind typed text `
          + "across a Worker restart");
        error.code = "STALE_EDITOR_GENERATION";
        held.reject(error);
        continue;
      }
      this._enqueueOwned(held.label, held.operation, held.options).then(held.resolve, held.reject);
    }
  }

  commitText(text, options = {}) {
    const number = options?.metadata?.requestNumber;
    if (Number.isInteger(number)) this._releaseHeld(number - 1);
    const committed = super.commitText(text, options);
    if (Number.isInteger(number)) this._releaseHeld(number);
    return committed;
  }

  setList(kind, options = {}) {
    const action = kind === "none" ? "set-list-none"
      : kind === "unordered" ? "set-list-unordered"
      : kind === "ordered" ? "set-list-ordered" : null;
    if (!action) {
      const error = new Error("kind must be none, unordered or ordered");
      error.code = "INVALID_ARGUMENT";
      return Promise.reject(this._withDisposition(error));
    }
    return this.action(action, options);
  }

  setParagraphStyle(style, options = {}) {
    const action = style === "heading" ? "set-paragraph-heading"
      : style === "body" ? "set-paragraph-body" : null;
    if (!action) {
      const error = new Error("style must be heading or body");
      error.code = "INVALID_ARGUMENT";
      return Promise.reject(this._withDisposition(error));
    }
    return this.action(action, options);
  }

  /** Which gestures the profile offers, for enabling buttons rather than for failing. */
  gesturesFor(action) {
    return this.editor?.gesturesFor(action) ?? null;
  }

  offersSelectionMove(action, gesture) {
    return this.editor?.offersSelectionMove(action, gesture) ?? false;
  }

  offers(action) {
    return this.editor?.offers(action) ?? false;
  }

  offersRedo() {
    return this.editor?.offersRedo() ?? false;
  }

  /** SPEC-M3-link-batch 10.8 (S-11): whether this profile answers
   * `page-rectangles`.  Read from the contract field, like redo; false before
   * open and on every profile that predates the v20 link. */
  offersPageRectangles() {
    return this.editor?.offersPageRectangles() ?? false;
  }

  /** SPEC-M3-link-batch-v21 4.2: whether this profile declares the Markdown
   * paste.  Read from the contract field; false before open and on v20. */
  offersPasteMarkdown() {
    return this.editor?.offersPasteMarkdown?.() ?? false;
  }

  /**
   * SPEC-M3-link-batch-v21 4.2 / 10.1: paste `text` as Markdown at the caret,
   * as a MUTATION through the same queue as everything else (insertText's
   * class).
   *
   * THE CHECKPOINT COMES FIRST, AND A FAILED ONE STOPS THE PASTE.  A paste the
   * engine cannot verify answers MUTATION_OUTCOME_UNKNOWN, which blocks the
   * queue in recoverable-error (the base class's RECOVERY_ERRORS), and the way
   * out is a reopen of "the checkpoint if newer than the last save, otherwise
   * the last save".  Nothing banked the work before the paste, so on a dirty
   * document that reopen lost everything typed since the save -- finding 119's
   * shape (10.1, both review seats).  `_checkpointBeforeBoundaryMove` banks it
   * (nothing to do on a clean document or content already banked), but it
   * cannot report failure -- the base class swallows a failed save into
   * `checkpointError` so a selection gesture never fails on it -- so the
   * result is checked here by its postcondition: dirty content whose stamp the
   * checkpoint does not hold is NOT banked, and the paste is refused with
   * MARKDOWN_CHECKPOINT_FAILED before anything is dispatched.
   *
   * Pre-dispatch refusals (the engine's MARKDOWN_* codes, INVALID_ARGUMENT)
   * reject without blocking and carry `recovery: "none"`; anything the
   * disposition reads as possibly dispatched blocks the queue as `action()`
   * does.
   */
  pasteMarkdown(text, options = {}) {
    return this._enqueue("paste-markdown", async ({ document }) => {
      await this._checkpointBeforeBoundaryMove(document);
      if (this.state.snapshot.dirty === true
          && this._checkpointStamp !== this._currentContentStamp) {
        const error = new Error("the work could not be banked before the Markdown "
          + "paste, so the paste was not sent");
        error.code = "MARKDOWN_CHECKPOINT_FAILED";
        error.details = { dispatched: false,
                          checkpointError: this._checkpointError ?? null };
        error.recovery = "none";
        throw error;
      }
      try {
        return await document.pasteMarkdown(text, options);
      } catch (error) {
        this._blockQueueIfDispatched(error);
        throw error;
      }
    }, { mutation: true })
      .catch((error) => { throw this._withDisposition(error); });
  }

  offersCaretParagraphText() {
    return this.editor?.offersCaretParagraphText() ?? false;
  }

  offersDocumentOutline() {
    return this.editor?.offersDocumentOutline() ?? false;
  }

  /**
   * The sibling of the base class's `undo()`, and here rather than there for
   * the same reason `_handleEngineEvent` is: `editor-shell/editor-session.js`
   * is bound to E1-C's verdict, and redo has nothing to do with that verdict.
   *
   * Through the same queue as everything else -- a redo that ran outside it
   * could interleave with a committed keystroke, and then neither one knows
   * which revision it started from.
   */
  redo(options = {}) {
    return this._enqueue("redo", ({ document }) => document.redo(options),
                         { mutation: true });
  }

  limitsFor(action) {
    return this.editor?.limitsFor(action) ?? [];
  }

  /**
   * Go back to the last checkpoint: a fresh Worker, reopened from the newest
   * bytes the engine itself wrote.
   *
   * SPEC E2-B 5.13.  Not undo -- undo goes through the queue that a
   * post-dispatch failure has just blocked, so the caller would only get
   * EDITOR_NOT_READY.  This is the base class's restart, named for what the
   * host is actually doing so that a reader of the host code can see the
   * disposition being obeyed.
   */
  rollback() {
    return this.restart();
  }

  /**
   * A dispatched failure blocks the queue.  (Finding 053.)
   *
   * SPEC E2-B 5.13 clause three does not merely say the disposition is
   * rollback -- it says **the host enters `recoverable-error`**, and clause two
   * is written on that premise ("擋了 queue 就沒有『下一個 mutation』").  The
   * base class only enters it for the codes in its own RECOVERY_ERRORS list,
   * and `EDITOR_FORMAT_POSTCONDITION_FAILED` is not one of them.  So the
   * product told the user the document might have changed unverifiably and
   * prescribed "go back to the checkpoint", while the button that performs it
   * -- shown only in `recoverable-error` or `restart-required` -- stayed
   * hidden.  A prescription the host cannot carry out.
   *
   * The fix is here rather than in that list for a reason that is not
   * aesthetic: `editor-shell/editor-session.js` is hash-registered by E1-C's
   * shell bundle and cannot change without unbinding a shipped verdict, while
   * this directory exists precisely to hold the changes that would otherwise
   * have to go there (see the header).  Blocking from inside the enqueued
   * operation is what makes the two equivalent: `_blockQueue` invalidates the
   * drain, so the drain's own catch takes its `this._activeDrain !== drain`
   * branch and its `finally` does not transition back to `ready` -- the same
   * end state as extending the list, reached one frame earlier.
   *
   * Codes the base class already handles are unaffected: it never sees them,
   * because this call has already invalidated the drain by then.
   */
  _blockQueueIfDispatched(error) {
    if (recoveryFor(error) !== "rollback")
      return;
    if (!["ready", "busy"].includes(this.state.snapshot.state))
      return;
    this._blockQueue(error, "recoverable-error", "editor-recovery");
  }

  /**
   * Attach the disposition to the error, so every host makes the same choice
   * from the same field instead of parsing a message.
   */
  _withDisposition(error) {
    if (error && typeof error === "object" && !("recovery" in error))
      error.recovery = recoveryFor(error);
    return error;
  }

  /** Is this action one of those whose postcondition is route C's? */
  static isParagraphAction(action) {
    return PARAGRAPH.has(action);
  }
}
