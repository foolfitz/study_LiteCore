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

import { EditorSession } from "../editor-shell/editor-session.js";
import { NarrowEditorV2Client, EDITOR_V3_ACTIONS }
  from "./narrow-editor-v2-client.js";
import { EDITOR_V2_PARAGRAPH_ACTIONS } from "./paragraph-editor-client.js";
import { recoveryFor } from "./paragraph-editor-session.js";

const PARAGRAPH = new Set(EDITOR_V2_PARAGRAPH_ACTIONS);
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
const ACTIONS = new Set(EDITOR_V3_ACTIONS);

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

export class NarrowEditorV2Session extends EditorSession {
  constructor(options = {}) {
    super(options);
    let client = null;
    this.clientReplacements = 0;
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
    this._guardEditorStateAgainstStaleWrites();
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
   * Any of the fifteen, through the same queue as everything else.
   *
   * The queue is the point.  A paragraph action that ran outside it could
   * interleave with a committed keystroke, and the revision each of them
   * expects would be the other's.
   */
  action(action, options = {}) {
    if (!ACTIONS.has(action)) {
      const error = new Error(`unsupported v2 editor action: ${String(action)}`);
      error.code = "EDITOR_ACTION_UNSUPPORTED";
      return Promise.reject(this._withDisposition(error));
    }
    return this._enqueue(
      `action:${action}`,
      async ({ editor }) => {
        try {
          return await editor.action(action, options);
        } catch (error) {
          this._blockQueueIfDispatched(error);
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
      { mutation: true },
    )
      .then((result) => {
        const carried = result?.[DISPATCHED_UNVERIFIED];
        if (carried) throw carried;
        return result;
      })
      .catch((error) => { throw this._withDisposition(error); });
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

  offers(action) {
    return this.editor?.offers(action) ?? false;
  }

  offersRedo() {
    return this.editor?.offersRedo() ?? false;
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

  /** Is this action one of the five whose postcondition is route C's? */
  static isParagraphAction(action) {
    return PARAGRAPH.has(action);
  }
}
