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
const BOUNDARY_CAPABLE_MOVES = new Set([
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
    if (!ACTIONS.has(action)) {
      const error = new Error(`unsupported v2 editor action: ${String(action)}`);
      error.code = "EDITOR_ACTION_UNSUPPORTED";
      return Promise.reject(this._withDisposition(error));
    }
    return this._enqueue(
      `action:${action}`,
      async ({ document, editor }) => {
        if (BOUNDARY_CAPABLE_MOVES.has(action))
          await this._checkpointBeforeBoundaryMove(document);
        try {
          return await editor.action(action, options);
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
          if (stateUnavailableOnDelete(action, error)) {
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

  _enqueue(label, operation, options = {}) {
    if (this._viewOnly && options?.mutation === true) {
      const error = new Error(`view-only: ${label} would change the document`);
      error.code = "EDITOR_VIEW_ONLY";
      error.recovery = "none";
      return Promise.reject(error);
    }
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
    return super._enqueue(label, operation, options);
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
      super._enqueue(held.label, held.operation, held.options).then(held.resolve, held.reject);
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
