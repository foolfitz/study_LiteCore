import { ReaderStateMachine } from "./state-machine.js";
import { TileScheduler } from "./tile-scheduler.js";

function publicError(error, fallback = "READER_ERROR") {
  return {
    code: error?.code || fallback,
    message: error?.message || String(error),
    details: error?.details || {},
  };
}

export class ReaderSession {
  constructor(options) {
    if (typeof options?.engineFactory !== "function")
      throw new TypeError("ReaderSession requires engineFactory");
    this._engineFactory = options.engineFactory;
    this._onTile = options.onTile || (() => {});
    this._onState = options.onState || (() => {});
    this._onEvent = options.onEvent || (() => {});
    this._tileOptions = options.tileOptions || {};
    this.state = new ReaderStateMachine((snapshot) => this._onState(snapshot));
    this.engine = null;
    this.document = null;
    this.scheduler = null;
    this.snapshot = null;
    this.localBytes = null;
    this._unsubscribe = null;
    this.workerGeneration = 0;
  }

  async open(snapshot) {
    if (this.state.snapshot.state !== "idle")
      throw new Error("reader session is already opened");
    this.state.transition("loading-core", {
      documentId: snapshot.documentId,
      version: snapshot.version,
      etag: snapshot.etag,
      error: null,
    });
    await this._openFresh(snapshot, "loading-document");
    return this.state.snapshot;
  }

  async _openFresh(snapshot, documentLoadingState) {
    try {
      this.engine = await this._engineFactory();
      this.workerGeneration += 1;
      this._unsubscribe = this.engine.onEvent((event) => this._handleEngineEvent(event));
      if (this.state.snapshot.state === "loading-core") {
        this.state.transition(documentLoadingState, {
          profile: this.engine.manifest.profile,
          coreCommit: this.engine.manifest.coreCommit,
          sdkVersion: this.engine.manifest.sdkVersion,
          providerContractVersion: this.engine.manifest.providerContractVersion,
        });
      }
      const bytes = snapshot.bytes.slice(0);
      this.document = await this.engine.open(bytes, {
        name: snapshot.name || `${snapshot.documentId}.odt`,
        transfer: true,
        timeoutMs: 180000,
      });
      this.snapshot = { ...snapshot, bytes: snapshot.bytes.slice(0) };
      this.scheduler = new TileScheduler({
        ...this._tileOptions,
        render: (region, requestOptions) => this.document.render(region, requestOptions),
        onTile: this._onTile,
        onError: (error) => this._handleTileError(error),
      });
      this.scheduler.configureDocument({
        documentVersion: snapshot.version,
        revision: this.document.revision,
        part: 0,
        scale: 1,
        widthTwips: this.document.widthTwips,
        heightTwips: this.document.heightTwips,
      });
      this.state.transition("ready", {
        documentId: snapshot.documentId,
        version: snapshot.version,
        etag: snapshot.etag,
        sdkRevision: this.document.revision,
        hasLocalBytes: false,
        remoteUpdate: null,
        error: null,
      });
    } catch (error) {
      if (this.state.snapshot.state === "loading-core"
          || this.state.snapshot.state === "loading-document"
          || this.state.snapshot.state === "reloading") {
        this.state.transition("fatal-error", { error: publicError(error) });
      }
      throw error;
    }
  }

  scheduleViewport(viewport) {
    if (!this.scheduler || !["ready", "stale", "saving"].includes(this.state.snapshot.state))
      throw new Error(`reader cannot render in state ${this.state.snapshot.state}`);
    return this.scheduler.scheduleViewport(viewport);
  }

  setScale(scale) {
    this.scheduler.setScale(scale);
    return this.scheduler.documentCssSize;
  }

  async search(query, options = {}) {
    if (!this.document)
      throw new Error("reader has no document");
    const result = await this.document.search(query, options);
    const selection = result.found ? await this.document.getSelection(options) : null;
    return {
      found: result.found,
      query: result.query,
      matchCount: result.found ? 1 : 0,
      selectionText: selection?.text || "",
      revision: result.revision,
    };
  }

  async classifyAnchor(quote) {
    const first = await this.document.search(quote);
    if (!first.found)
      return { classification: "not-found", candidates: 0 };
    const selection = await this.document.getSelection();
    if (selection.text !== quote)
      return { classification: "not-found", candidates: 0 };
    const firstSignature = JSON.stringify(first.selections || []);
    const second = await this.document.search(quote);
    if (!second.found)
      return { classification: "not-found", candidates: 0 };
    const secondSignature = JSON.stringify(second.selections || []);
    return firstSignature === secondSignature
      ? { classification: "unique", candidates: 1, selection }
      : { classification: "ambiguous", candidates: 2 };
  }

  async replaceSelection(text, expectedRevision = this.document?.revision) {
    const result = await this.document.replaceSelection(text, { expectedRevision });
    this.scheduler.invalidateRevision(result.revision);
    this.state.update({ sdkRevision: result.revision });
    return result;
  }

  async saveLocal() {
    if (!this.document)
      throw new Error("reader has no document");
    this.state.transition("saving");
    try {
      this.localBytes = await this.document.save(
        { format: "odt" }, { timeoutMs: 180000 },
      );
      this.state.transition("ready", {
        hasLocalBytes: true,
        sdkRevision: this.document.revision,
      });
      return this.localBytes;
    } catch (error) {
      this.state.transition("recoverable-error", { error: publicError(error) });
      throw error;
    }
  }

  markStale(remoteUpdate) {
    if (!["ready", "saving"].includes(this.state.snapshot.state))
      return this.state.snapshot;
    return this.state.transition("stale", { remoteUpdate });
  }

  markConflict(error) {
    if (!["ready", "saving", "stale"].includes(this.state.snapshot.state))
      throw new Error(`cannot mark conflict from ${this.state.snapshot.state}`);
    return this.state.transition("conflict", { error: publicError(error, "CONFLICT") });
  }

  async reload(snapshot, options = {}) {
    this.state.assertReloadAllowed(options);
    if (!["stale", "conflict", "recoverable-error"].includes(this.state.snapshot.state))
      throw new Error(`cannot reload from ${this.state.snapshot.state}`);
    const skipClose = this.state.snapshot.state === "recoverable-error"
      && this.state.snapshot.error?.code === "WORKER_CRASHED";
    this.state.transition("reloading", { error: null });
    await this._disposeRuntime({ skipClose });
    this.localBytes = null;
    await this._openFresh(snapshot, "reloading");
    return this.state.snapshot;
  }

  _handleEngineEvent(event) {
    this._onEvent(event);
    if (event.event === "document-invalidated" && this.scheduler && this.document) {
      this.scheduler.invalidateRevision(this.document.revision);
      this.state.update({ sdkRevision: this.document.revision });
    } else if (event.event === "worker-crashed"
               && !["closed", "fatal-error"].includes(this.state.snapshot.state)) {
      this.scheduler?.close();
      const current = this.state.snapshot.state;
      if (["ready", "saving", "stale"].includes(current)) {
        this.state.transition("recoverable-error", {
          error: publicError(event.error, "WORKER_CRASHED"),
          hasLocalBytes: this.localBytes instanceof ArrayBuffer,
        });
      }
    }
  }

  _handleTileError(error) {
    if (["ready", "stale", "saving"].includes(this.state.snapshot.state)) {
      this.state.transition("recoverable-error", {
        error: publicError(error, "TILE_ERROR"),
      });
    }
  }

  async _disposeRuntime({ skipClose = false } = {}) {
    this.scheduler?.close();
    this.scheduler = null;
    if (this.document && !skipClose) {
      try {
        await this.document.close({ timeoutMs: 30000 });
      } catch {
        // Disposing the Worker is the recovery boundary after a typed crash or
        // close timeout. A successful close is still asserted by browser tests.
      }
    }
    this.document = null;
    this._unsubscribe?.();
    this._unsubscribe = null;
    this.engine?.dispose();
    this.engine = null;
  }

  async close() {
    if (this.state.snapshot.state === "closed")
      return;
    const closeSucceeded = await (async () => {
      this.scheduler?.close();
      if (!this.document)
        return true;
      try {
        await this.document.close({ timeoutMs: 30000 });
        return true;
      } catch {
        return false;
      }
    })();
    this.document = null;
    this._unsubscribe?.();
    this._unsubscribe = null;
    this.engine?.dispose();
    this.engine = null;
    this.state.transition("closed", { closeSucceeded });
  }
}
