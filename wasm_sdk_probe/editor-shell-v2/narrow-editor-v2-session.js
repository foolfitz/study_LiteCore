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
      ({ editor }) => editor.action(action, options),
      { mutation: true },
    ).catch((error) => { throw this._withDisposition(error); });
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
