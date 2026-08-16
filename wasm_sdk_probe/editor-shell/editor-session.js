import { HostInputAdapter } from "../input/input-adapter.js";
import { PlainTextClipboardAdapter } from "../input/clipboard-adapter.js";
import { TileScheduler } from "../reader-shell/tile-scheduler.js";
import { NarrowEditorClient } from "./editor-client.js";
import { EditorStateMachine } from "./state-machine.js";

function publicError(error, fallback = "EDITOR_ERROR") {
  return {
    code: error?.code || fallback,
    message: error?.message || String(error),
    details: error?.details || {},
  };
}

const RECOVERY_ERRORS = new Set([
  "TIMEOUT",
  "WORKER_CRASHED",
  "WORKER_RESTARTED",
  "STALE_DOCUMENT",
  "MUTATION_OUTCOME_UNKNOWN",
  "EDITOR_RESULT_INVALID",
]);

/**
 * Is the reported caret on the line that was clicked?  (Findings 048, 051.)
 *
 * The caret rectangle IS the line box, so the question is whether the clicked
 * y falls in that box.  Scaled by the rectangle rather than by a twips
 * constant: a constant tuned on one corpus would silently mean "two lines" in
 * another.
 *
 * The band is NOT symmetric, and finding 051 is what the symmetric version
 * cost.  It was `|yTwips - caret.y| <= height/2`, which reads `caret.y` as the
 * middle of the line; it is the TOP.  So the accepted band ran from half a line
 * above the box to the box's own midpoint, and every click landing in the
 * BOTTOM HALF of the line it correctly hit was refused -- 30 seconds of waiting
 * and then EDITOR_CARET_NOT_PLACED, on the product page, for about half of all
 * clicks.  Measured on the shipped v2 artifact: a click at y=1739 with the
 * caret reported at y=1418 height=414 (box 1418..1832, sequence advanced, the
 * engine had done exactly what was asked) failed twice at 30.1 s, while a click
 * 200 twips higher on the SAME line confirmed in 0.3 s.
 *
 * Downward: to the bottom of the box and no further.  Below it is the next
 * line's box.
 *
 * Upward: half a line of slack, and that is measured -- real landings sit up to
 * 119 twips ABOVE the rectangle's top, because a click can fall in the gap
 * between two line boxes and the engine attributes it to the line below.  Half
 * a line clears every landing measured (119 in rectangles 276-414 tall) while a
 * caret stranded one line away (390 twips in that corpus) stays out.
 */
export function caretIsOnLine(caret, yTwips) {
  if (!caret || !Number.isFinite(caret.y) || !Number.isFinite(caret.height))
    return false;
  const slackAbove = Math.max(caret.height / 2, 1);
  return yTwips >= caret.y - slackAbove && yTwips <= caret.y + caret.height;
}

/**
 * Did the caret move?  (Finding 052.)
 *
 * Position only.  A caret that is in a different place is a caret the engine
 * moved, and the only thing that asked it to move was the click being
 * confirmed.  Height is deliberately not compared: the same position with a
 * different reported height is not a move, and treating it as one would let a
 * relayout stand in for a click.
 */
export function caretDiffers(caret, previous) {
  if (!caret || !previous) return Boolean(caret) !== Boolean(previous);
  return caret.x !== previous.x || caret.y !== previous.y;
}

export class EditorSession {
  constructor(options = {}) {
    if (typeof options.engineFactory !== "function")
      throw new TypeError("EditorSession requires engineFactory");
    this._engineFactory = options.engineFactory;
    this._onTile = options.onTile || (() => {});
    this._onEvent = options.onEvent || (() => {});
    this._tileOptions = options.tileOptions || {};
    this._maxWorkerGenerations = options.maxWorkerGenerations ?? 3;
    if (!Number.isInteger(this._maxWorkerGenerations) || this._maxWorkerGenerations < 1)
      throw new TypeError("maxWorkerGenerations must be a positive integer");
    this._selectionTimeoutMs = options.selectionTimeoutMs ?? 5000;
    if (!Number.isInteger(this._selectionTimeoutMs) || this._selectionTimeoutMs < 1)
      throw new TypeError("selectionTimeoutMs must be a positive integer");
    this.state = new EditorStateMachine(options.onState);
    this.engine = null;
    this.document = null;
    this.editor = null;
    this.scheduler = null;
    this.input = new HostInputAdapter({
      commit: (text, metadata) => this.commitText(text, { metadata }),
      onTrace: options.onInputTrace,
      onState: options.onInputState,
    });
    this.clipboard = new PlainTextClipboardAdapter({
      inputAdapter: this.input,
      clipboard: options.clipboard,
      secureContext: options.secureContext,
      getSelection: () => {
        if (!this.document) {
          const error = new Error("editor document is unavailable");
          error.code = "EDITOR_NOT_READY";
          throw error;
        }
        return this.document.getSelection({ timeoutMs: 30000 });
      },
      onTrace: options.onClipboardTrace,
    });
    this._authorityBytes = null;
    this._authorityStamp = 0;
    this._authorityName = null;
    this._checkpointBytes = null;
    this._checkpointRevision = null;
    this._checkpointStamp = null;
    this._checkpointError = null;
    // Document revisions restart at zero with every Worker.  Content stamps
    // are session-owned and never reset, so byte snapshots from different
    // Worker generations can be ordered without comparing unrelated counters.
    this._contentSequence = 0;
    this._currentContentStamp = 0;
    this.state.update({ hasCheckpoint: false, checkpointRevision: null });
    this._unsubscribe = null;
    this._queue = [];
    this._drainSequence = 0;
    this._activeDrain = null;
    this._generation = 0;
  }

  async open(snapshot) {
    if (this.state.snapshot.state !== "idle")
      throw new Error("editor session is already opened");
    if (!(snapshot?.bytes instanceof ArrayBuffer) || snapshot.bytes.byteLength === 0)
      throw new TypeError("open requires non-empty ODT bytes");
    this._authorityBytes = snapshot.bytes.slice(0);
    this._authorityName = snapshot.name || "document.odt";
    this.state.transition("loading", {
      documentName: this._authorityName,
      error: null,
    });
    await this._openFresh();
    return this.state.snapshot;
  }

  async _openFresh() {
    try {
      if (this._generation >= this._maxWorkerGenerations) {
        const error = new Error(
          `Worker generation limit ${this._maxWorkerGenerations} reached; reload the page`,
        );
        error.code = "WORKER_GENERATION_LIMIT";
        error.details = {
          generation: this._generation,
          maximumWorkerGenerations: this._maxWorkerGenerations,
          requiresPageReload: true,
        };
        throw error;
      }
      this.engine = await this._engineFactory();
      this._generation += 1;
      this._unsubscribe = this.engine.onEvent((event) => this._handleEngineEvent(event));
      const useCheckpoint = this._checkpointBytes !== null
        && this._checkpointStamp !== null
        && this._checkpointStamp > this._authorityStamp;
      const sourceBytes = useCheckpoint ? this._checkpointBytes : this._authorityBytes;
      const sourceStamp = useCheckpoint ? this._checkpointStamp : this._authorityStamp;
      this.document = await this.engine.open(sourceBytes.slice(0), {
        name: this._authorityName,
        transfer: true,
        timeoutMs: 180000,
      });
      this._currentContentStamp = sourceStamp;
      this.editor = new NarrowEditorClient(this.document);
      this.scheduler = new TileScheduler({
        ...this._tileOptions,
        render: (region, options) => this.document.render(region, options),
        onTile: this._onTile,
        onError: (error) => this._enterRecovery(error),
      });
      this.scheduler.configureDocument({
        documentVersion: `generation-${this._generation}`,
        revision: this.document.revision,
        part: 0,
        scale: 1,
        widthTwips: this.document.widthTwips,
        heightTwips: this.document.heightTwips,
      });
      const editorState = await this.editor.getState({ timeoutMs: 30000 });
      this.input.setBlocked(false);
      this.state.transition("ready", {
        revision: this.document.revision,
        dirty: useCheckpoint,
        generation: this._generation,
        pending: 0,
        editorState,
        error: null,
      });
    } catch (error) {
      this.state.transition("recoverable-error", { error: publicError(error) });
      this.input.setBlocked(true, "open-failed");
      throw error;
    }
  }

  attachInput(target) {
    this.input.attach(target);
  }

  copySelection(options = {}) {
    return this._enqueue(
      "copy-selection",
      () => this.clipboard.copySelection(options.metadata),
    );
  }

  pasteFromClipboard(options = {}) {
    if (!["ready", "busy"].includes(this.state.snapshot.state)) {
      const error = new Error(
        `editor clipboard paste is unavailable in ${this.state.snapshot.state}`,
      );
      error.code = "EDITOR_NOT_READY";
      return Promise.reject(error);
    }
    return this.clipboard.pasteFromClipboard(options);
  }

  pasteEvent(event, metadata = {}) {
    if (!["ready", "busy"].includes(this.state.snapshot.state)) {
      const error = new Error(
        `editor clipboard paste is unavailable in ${this.state.snapshot.state}`,
      );
      error.code = "EDITOR_NOT_READY";
      return Promise.reject(error);
    }
    return this.clipboard.pasteEvent(event, metadata);
  }

  scheduleViewport(viewport) {
    if (!this.scheduler || !["ready", "busy"].includes(this.state.snapshot.state))
      throw new Error(`editor cannot render in state ${this.state.snapshot.state}`);
    return this.scheduler.scheduleViewport(viewport);
  }

  setScale(scale) {
    this.scheduler.setScale(scale);
    return this.scheduler.documentCssSize;
  }

  _enqueue(label, operation, { mutation = false, finalize = null } = {}) {
    if (!["ready", "busy"].includes(this.state.snapshot.state)) {
      const error = new Error(`editor operation ${label} is unavailable in ${this.state.snapshot.state}`);
      error.code = "EDITOR_NOT_READY";
      return Promise.reject(error);
    }
    const generation = this._generation;
    const runtime = {
      document: this.document,
      editor: this.editor,
      scheduler: this.scheduler,
    };
    return new Promise((resolve, reject) => {
      this._queue.push({
        label, operation, mutation, finalize, generation, runtime, resolve, reject,
      });
      this.state.update({ pending: this._queue.length + (this._activeDrain === null ? 0 : 1) });
      void this._drain();
    });
  }

  _assertDrainOwner(drain, item) {
    if (this._activeDrain === drain && item.generation === this._generation)
      return;
    const error = new Error("editor operation completed for a stale Worker generation");
    error.code = "STALE_EDITOR_GENERATION";
    throw error;
  }

  async _drain() {
    if (this._activeDrain !== null)
      return;
    const drain = ++this._drainSequence;
    this._activeDrain = drain;
    if (this.state.snapshot.state === "ready")
      this.state.transition("busy");
    try {
      while (this._activeDrain === drain
          && this._queue.length
          && this.state.snapshot.state === "busy") {
        const item = this._queue.shift();
        this.state.update({ pending: this._queue.length + 1 });
        if (item.generation !== this._generation) {
          const error = new Error("queued editor operation belongs to a stale Worker generation");
          error.code = "STALE_EDITOR_GENERATION";
          item.reject(error);
          continue;
        }
        try {
          const result = await item.operation(item.runtime);
          this._assertDrainOwner(drain, item);
          const editorState = result?.state
            || await item.runtime.editor.getState({ timeoutMs: 30000 });
          this._assertDrainOwner(drain, item);
          if (item.mutation)
            this._currentContentStamp = ++this._contentSequence;
          item.runtime.scheduler?.invalidateRevision(item.runtime.document.revision);
          this.state.update({
            revision: item.runtime.document.revision,
            dirty: this.state.snapshot.dirty || item.mutation,
            editorState,
          });
          const finalResult = item.finalize
            ? item.finalize(result, item.runtime) : result;
          item.resolve(finalResult);
        } catch (error) {
          item.reject(error);
          if (this._activeDrain !== drain) {
            continue;
          } else if (error?.code === "EDITOR_BOUNDARY_UNSUPPORTED") {
            this._blockQueue(error, "restart-required", "editor-boundary");
          } else if (RECOVERY_ERRORS.has(error?.code)) {
            // A selection readback TIMEOUT means the engine thread is already
            // dead.  Saving on the way down would only consume another full
            // deadline; the pre-gesture checkpoint is the last safe save.
            this._blockQueue(error, "recoverable-error", "editor-recovery");
          }
        }
      }
    } finally {
      if (this._activeDrain === drain) {
        this._activeDrain = null;
        if (this.state.snapshot.state === "busy")
          this.state.transition("ready", { pending: 0 });
      }
    }
  }

  _invalidateDrain() {
    this._activeDrain = null;
  }

  _blockQueue(error, state, reason) {
    this._invalidateDrain();
    const queued = this._queue.splice(0);
    for (const item of queued)
      item.reject(error);
    this.input.setBlocked(true, reason);
    this.state.transition(state, {
      pending: 0,
      error: publicError(error),
    });
  }

  _enterRecovery(error) {
    if (["ready", "busy"].includes(this.state.snapshot.state))
      this._blockQueue(error, "recoverable-error", "runtime-recovery");
  }

  /**
   * Click, and return once the caret is where the click asked for it.
   *
   * FINDING 048.  This used to wait for
   * `selectionType === "none" && observed && collapsed` -- three things that
   * are already true when a document opens, so the wait ended immediately and
   * the call reported success before the engine had processed the click.  A
   * format action dispatched straight afterwards landed on whatever paragraph
   * the caret was on BEFORE.  A predicate that would be equally true if the
   * click had never happened is not a confirmation of the click.
   *
   * The engine takes 22-28 ms to process one (measured, both browsers).  Two
   * signals are available to a product profile, and this uses both because
   * neither is sufficient alone:
   *
   *   * `sourceSequence` -- the engine's count of callbacks that changed editor
   *     state.  It advances for every click that changes the cursor, including
   *     a click that lands on the line the caret is already on but at a
   *     different character.  It does NOT advance for a click on the exact
   *     point the cursor already occupies: the engine emits nothing, because
   *     nothing changed.  It also advances for callbacks that have nothing to
   *     do with the caret (a tile invalidation, say), which is why an advance
   *     on its own is not enough.
   *   * the caret rectangle against the clicked point.  Not enough on its own
   *     either: a click can fall in the gap between two line boxes, so a
   *     tolerance loose enough to accept every real landing also accepts the
   *     line above -- which is exactly the stale caret this is guarding
   *     against.
   *
   * So: return when the engine has said something AND the caret is on the
   * clicked line.  After `caretAckGraceMs` of complete silence, accept a caret
   * that is already on the clicked line -- that is the identical-point click,
   * where the engine has nothing to say because there is nothing to change.
   * Never return while the caret is somewhere else; time out instead.
   */
  placeCaret(xTwips, yTwips, options = {}) {
    return this._enqueue("place-caret", async ({ document, editor }) => {
      const timeoutMs = Math.min(options.caretTimeoutMs ?? 30000, 30000);
      // An order of magnitude above the measured 22-28 ms.  It only bounds the
      // identical-point case; every other click is confirmed by the engine.
      const graceMs = Math.min(options.caretAckGraceMs ?? 400, timeoutMs);
      const before = await editor.getState(options);
      const beforeSequence = before?.sourceSequence ?? null;
      const beforeCaret = before?.caret ?? null;
      const started = Date.now();
      await document.click(xTwips, yTwips, options);
      let state = before;
      do {
        state = await editor.getState(options);
        const acknowledged = state?.sourceSequence !== beforeSequence;
        const onTarget = caretIsOnLine(state?.caret, yTwips);
        // FINDING 052.  A click OUTSIDE every line box -- above the first line,
        // below the last, in the page margin -- is a click the engine handles
        // by putting the caret on the nearest line, which is what every editor
        // does and what a user reaching for the end of a document relies on.
        // The geometric test can never accept it: the caret is not on the
        // clicked line, because the clicked line does not exist.  Measured on
        // the product page: 13 of 26 clicks down a column were refused and
        // every one of them was outside the text, each after the full 30 s.
        //
        // The engine having MOVED the caret is the signal that it processed
        // this click, and it is not available to the geometric test.  It does
        // not weaken finding 048's guard: 048's failure is a caret that is
        // STALE, and a stale caret has by definition not moved.  An
        // acknowledgement that is not about the caret still does not end the
        // wait, because that path requires the caret to differ.
        const caretMoved = caretDiffers(state?.caret, beforeCaret);
        if ((onTarget && (acknowledged || Date.now() - started >= graceMs))
            || (acknowledged && caretMoved)) {
          return {
            state,
            revision: document.revision,
            caretConfirmedBy: onTarget
              ? (acknowledged ? "engine-acknowledged" : "already-at-target")
              : "engine-moved-the-caret-off-the-clicked-line",
            caretOnClickedLine: onTarget,
            caretWaitedMs: Date.now() - started,
          };
        }
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

  // SPEC E1-D.  Not a mutation: the document is unchanged, only what is
  // selected.  Goes through the queue anyway so it cannot interleave with a
  // mutation that is still in flight.
  selectRange(start, end, options = {}) {
    // Healthy selections finish in 6-33 ms while the broken engine path never
    // returns.  Five seconds bounds that failure and matches the engine's
    // existing FormatBarrierStageDeadlineMs.
    const selectionOptions = {
      ...options,
      timeoutMs: options.timeoutMs ?? this._selectionTimeoutMs,
    };
    return this._enqueue(
      "select-range",
      async ({ document, editor }) => {
        await this._checkpointBeforeSelection(document);
        return editor.selectRange(start, end, selectionOptions);
      },
    );
  }

  async _checkpointBeforeSelection(document) {
    const revision = document.revision;
    const contentStamp = this._currentContentStamp;
    if (!this.state.snapshot.dirty || contentStamp === this._checkpointStamp)
      return;
    try {
      const bytes = await document.save(
        { format: "odt" },
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
      // A background checkpoint must never turn a user's selection gesture
      // into a save failure, so this is swallowed as far as the gesture is
      // concerned -- but it must not be swallowed as far as the host is
      // concerned.  Keeping it in a private field made "nothing to rescue"
      // and "we tried to protect your work and failed" the same observable
      // state, and the recovery banner then stays silent at exactly the
      // moment it has something worth saying (SPEC-E1-C 4.1, v8).
      this._checkpointError = publicError(error, "CHECKPOINT_FAILED");
      this.state.update({ checkpointError: this._checkpointError });
    }
  }

  checkpointBytes() {
    return this._checkpointBytes?.slice(0) ?? null;
  }

  commitText(text, options = {}) {
    return this._enqueue("commit-text", ({ document }) => document.insertText(text, options), {
      mutation: true,
    });
  }

  moveCharacter(direction, options = {}) {
    const selectionOptions = options.extendSelection
      ? { ...options, timeoutMs: options.timeoutMs ?? this._selectionTimeoutMs }
      : options;
    return this._enqueue(
      `move-character-${direction}`,
      async ({ document, editor }) => {
        if (options.extendSelection)
          await this._checkpointBeforeSelection(document);
        return editor.moveCharacter(direction, selectionOptions);
      },
    );
  }

  delete(direction, options = {}) {
    return this._enqueue(
      `delete-${direction}`,
      ({ editor }) => editor.delete(direction, options),
      { mutation: true },
    );
  }

  insertBreak(kind, options = {}) {
    return this._enqueue(
      `insert-${kind}-break`,
      ({ editor }) => editor.insertBreak(kind, options),
      { mutation: true },
    );
  }

  setInlineFormat(format, enabled, options = {}) {
    return this._enqueue(
      `set-${format}`,
      ({ editor }) => editor.setInlineFormat(format, enabled, options),
      { mutation: true },
    );
  }

  undo(options = {}) {
    return this._enqueue("undo", ({ document }) => document.undo(options), { mutation: true });
  }

  save(options = {}) {
    return this._enqueue("save", async ({ document }) => {
      const bytes = await document.save(
        { format: "odt" },
        { timeoutMs: options.timeoutMs ?? 180000, signal: options.signal },
      );
      return { bytes, revision: document.revision, contentStamp: this._currentContentStamp };
    }, { finalize: (result) => {
      const { bytes, contentStamp } = result;
      this._authorityBytes = bytes.slice(0);
      this._authorityStamp = contentStamp;
      // This save ran after any checkpoint in the same FIFO, so authority now
      // contains at least that content.  Retaining the checkpoint could later
      // resurrect older bytes after revisions restart with a fresh Worker.
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

  async restart() {
    if (!["restart-required", "recoverable-error"].includes(this.state.snapshot.state))
      throw new Error(`editor cannot restart from ${this.state.snapshot.state}`);
    this._invalidateDrain();
    this.state.transition("loading", { error: null, pending: 0 });
    await this._disposeRuntime({ closeDocument: false });
    await this._openFresh();
    return this.state.snapshot;
  }

  _handleEngineEvent(event) {
    this._onEvent(event);
    if (event.event === "document-invalidated" && this.document)
      this.scheduler?.invalidateRevision(this.document.revision);
    if (event.event === "worker-crashed")
      this._enterRecovery(Object.assign(new Error(event.error?.message || "Worker crashed"), {
        code: event.error?.code || "WORKER_CRASHED",
      }));
  }

  async _disposeRuntime({ closeDocument = true } = {}) {
    this.scheduler?.close();
    this.scheduler = null;
    if (this.document && closeDocument) {
      try {
        await this.document.close({ timeoutMs: 30000 });
      } catch {
        // Worker disposal is the bounded recovery boundary.
      }
    }
    this.document = null;
    this.editor = null;
    this._unsubscribe?.();
    this._unsubscribe = null;
    this.engine?.dispose();
    this.engine = null;
  }

  async close() {
    if (this.state.snapshot.state === "closed")
      return;
    this.input.detach();
    const queued = this._queue.splice(0);
    const error = Object.assign(new Error("editor session closed"), { code: "EDITOR_CLOSED" });
    for (const item of queued)
      item.reject(error);
    this._invalidateDrain();
    await this._disposeRuntime();
    this.state.transition("closed", { pending: 0 });
  }
}
