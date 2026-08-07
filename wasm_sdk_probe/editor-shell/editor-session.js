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
    this._authorityName = null;
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
      this.document = await this.engine.open(this._authorityBytes.slice(0), {
        name: this._authorityName,
        transfer: true,
        timeoutMs: 180000,
      });
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
        dirty: false,
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

  placeCaret(xTwips, yTwips, options = {}) {
    return this._enqueue("place-caret", async ({ document, editor }) => {
      await document.click(xTwips, yTwips, options);
      const timeoutMs = Math.min(options.caretTimeoutMs ?? 30000, 30000);
      const deadline = Date.now() + timeoutMs;
      let state = null;
      do {
        state = await editor.getState(options);
        if (state.selectionType === "none"
            && state.selection?.observed === true
            && state.selection?.collapsed === true) {
          return { state, revision: document.revision };
        }
        await new Promise((resolve) => setTimeout(resolve, 10));
      } while (Date.now() < deadline);
      const error = new Error("click did not produce a callback-confirmed collapsed caret");
      error.code = "EDITOR_STATE_UNAVAILABLE";
      error.details = { xTwips, yTwips, timeoutMs, state };
      throw error;
    });
  }

  // SPEC E1-D.  Not a mutation: the document is unchanged, only what is
  // selected.  Goes through the queue anyway so it cannot interleave with a
  // mutation that is still in flight.
  selectRange(start, end, options = {}) {
    return this._enqueue(
      "select-range",
      ({ editor }) => editor.selectRange(start, end, options),
    );
  }

  commitText(text, options = {}) {
    return this._enqueue("commit-text", ({ document }) => document.insertText(text, options), {
      mutation: true,
    });
  }

  moveCharacter(direction, options = {}) {
    return this._enqueue(
      `move-character-${direction}`,
      ({ editor }) => editor.moveCharacter(direction, options),
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
      return { bytes, revision: document.revision };
    }, { finalize: (result) => {
      const { bytes } = result;
      this._authorityBytes = bytes.slice(0);
      this.state.update({ dirty: false, hasSavedBytes: true });
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
