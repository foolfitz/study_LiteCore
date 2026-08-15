// SPEC E2-B 5.13: what a host does when a paragraph action fails.
//
// The short version, and it is short because the alternative was measured and
// rejected: **a dispatched-but-unverified failure is recovered by rolling back
// to the last checkpoint, not by asking the user to undo.**
//
// Asking the user to undo does not work in this shell.  `undo()` goes through
// the same queue (`editor-session.js:434` calls `_enqueue`), and the codes that
// carry these failures are in `RECOVERY_ERRORS`, so the queue is already
// blocked when the prompt would appear -- the user's undo returns
// `EDITOR_NOT_READY`.  The engine's own message says "check it and use undo",
// and that is right for a HUMAN reading it; it is not an instruction a host can
// execute.
//
// Rolling back is affordable here for a specific, measured reason.
// `_checkpointBeforeSelection()` saves before every range selection, and the v2
// gesture is drag-then-press: the checkpoint lands on the drag, immediately
// before the format action.  So a rollback loses at most the one action that
// failed -- whose outcome was unknown anyway.  That is why SPEC E2-B section 9
// now requires the format buttons to follow a selection gesture: press one
// without a preceding drag and the checkpoint is not there, and this reasoning
// stops holding.
//
// Lives in editor-shell-v2/ rather than beside editor-session.js because
// `editor-shell/*.js` is hash-registered by E1-C's shell bundle and adding a
// file there unbinds a shipped verdict.

import { formatFailureDisposition, ParagraphEditorClient }
  from "./paragraph-editor-client.js";

/**
 * How a host should respond to a paragraph-action failure.
 *
 * Returns one of:
 *   "none"            nothing was dispatched; the document is untouched and the
 *                     session may continue
 *   "rollback"        something was dispatched and could not be verified; reopen
 *                     from the last checkpoint (or authority) bytes
 *   "restart"         the handle is not usable; a fresh worker is required
 */
export function recoveryFor(error) {
  const code = error?.code;
  // A boundary rejection has always demanded a fresh worker (E1-B section 5),
  // and nothing about paragraph actions changes that.
  if (code === "EDITOR_BOUNDARY_UNSUPPORTED")
    return "restart";
  if (code === "WORKER_CRASHED" || code === "WORKER_RESTARTED")
    return "restart";

  const disposition = formatFailureDisposition(error);
  if (disposition === "refused-no-mutation")
    return "none";
  // "unknown-rollback" lands here too, and deliberately: when the barrier was
  // not forwarded there is no way to tell a refusal from a dispatch, and the
  // asymmetry is stark.  A needless rollback costs one action; a missed one
  // leaves a changed document the host believes is clean.
  return "rollback";
}

/**
 * The paragraph actions, wrapped so a host gets the disposition with the error.
 *
 * Deliberately NOT a subclass of EditorSession: that class is hash-registered,
 * and this needs none of its queue machinery -- what it needs is for the host
 * to be told, in one field, whether to roll back.
 */
export class ParagraphEditorSession {
  constructor(session) {
    if (!session || typeof session !== "object")
      throw new TypeError("ParagraphEditorSession requires an EditorSession");
    this.session = session;
  }

  /** The v2 client for the session's current document. */
  _client() {
    const document = this.session.document;
    if (!document)
      throw new Error("the session has no open document");
    return new ParagraphEditorClient(document);
  }

  /** Which gestures the profile offers for an action, for enabling buttons. */
  gesturesFor(action) {
    return this._client().gesturesFor(action);
  }

  async action(action, options = {}) {
    try {
      return await this._client().action(action, options);
    } catch (error) {
      // The disposition rides on the error rather than being inferred by the
      // caller, so that every host makes the same choice from the same field.
      error.recovery = recoveryFor(error);
      throw error;
    }
  }

  setList(kind, options = {}) {
    return this.action(
      kind === "none" ? "set-list-none"
        : kind === "unordered" ? "set-list-unordered" : "set-list-ordered",
      options);
  }

  setParagraphStyle(style, options = {}) {
    return this.action(
      style === "heading" ? "set-paragraph-heading" : "set-paragraph-body",
      options);
  }
}
