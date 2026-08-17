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
import { NarrowEditorV2Client, EDITOR_V2_ACTIONS }
  from "./narrow-editor-v2-client.js";
import { EDITOR_V2_PARAGRAPH_ACTIONS } from "./paragraph-editor-client.js";
import { recoveryFor } from "./paragraph-editor-session.js";

const PARAGRAPH = new Set(EDITOR_V2_PARAGRAPH_ACTIONS);
const ACTIONS = new Set(EDITOR_V2_ACTIONS);

// A Symbol, not a string key: this rides through the base class's resolve path
// on an object the base class treats as an opaque result, and a string key
// could collide with a field a future engine payload adds.  It never leaves
// `action()` -- the `.then` below unwraps it and rethrows the original error.
const DISPATCHED_UNVERIFIED = Symbol("dispatchedUnverified");

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
