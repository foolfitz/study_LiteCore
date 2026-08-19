export const PROTOCOL_VERSION = 1;
export const ABI_VERSION = 0x00010001;
const DEFAULT_CLOSE_RECOVERY_TIMEOUT_MS = 10000;

export class DocumentSdkError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "DocumentSdkError";
    this.code = code;
    this.details = details;
  }
}

export class SdkTimeoutError extends DocumentSdkError {
  constructor(operation, timeoutMs) {
    super("TIMEOUT", `${operation} timed out after ${timeoutMs} ms`, {
      operation,
      timeoutMs,
    });
    this.name = "SdkTimeoutError";
  }
}

export class SdkAbortError extends DocumentSdkError {
  constructor(operation) {
    super("ABORTED", `${operation} was aborted`, { operation });
    this.name = "AbortError";
  }
}

export class WorkerCrashedError extends DocumentSdkError {
  constructor(message = "document worker crashed") {
    super("WORKER_CRASHED", message);
    this.name = "WorkerCrashedError";
  }
}

export class WorkerRestartedError extends DocumentSdkError {
  constructor() {
    super("WORKER_RESTARTED", "document worker was restarted");
    this.name = "WorkerRestartedError";
  }
}

export class StaleDocumentError extends DocumentSdkError {
  constructor() {
    super("STALE_DOCUMENT", "document belongs to an earlier worker generation");
    this.name = "StaleDocumentError";
  }
}

export class StaleRevisionError extends DocumentSdkError {
  constructor(message = "document revision does not match", details = {}) {
    super("STALE_REVISION", message, details);
    this.name = "StaleRevisionError";
  }
}

export class DocumentClosedError extends DocumentSdkError {
  constructor() {
    super("DOCUMENT_CLOSED", "document is already closed");
    this.name = "DocumentClosedError";
  }
}

function defaultWorkerFactory(url) {
  return new Worker(url, { name: "oxoffice-document-engine" });
}

function remoteError(payload, operation) {
  const error = payload?.error || {};
  const details = { operation, ...error };
  if (error.code === "STALE_REVISION")
    return new StaleRevisionError(error.message, details);
  return new DocumentSdkError(
    error.code || "WORKER_ERROR",
    error.message || `${operation} failed`,
    details,
  );
}

export class DocumentEngine {
  constructor(options = {}) {
    this._workerUrl = options.workerUrl
      ? new URL(options.workerUrl, globalThis.location?.href || import.meta.url)
      : new URL("./sdk-worker.js", import.meta.url);
    this._workerFactory = options.workerFactory || defaultWorkerFactory;
    this._defaultTimeoutMs = options.timeoutMs ?? 30000;
    const requestedCloseRecoveryTimeout = Number(
      options.closeRecoveryTimeoutMs ?? DEFAULT_CLOSE_RECOVERY_TIMEOUT_MS,
    );
    this._closeRecoveryTimeoutMs = Number.isFinite(requestedCloseRecoveryTimeout)
      && requestedCloseRecoveryTimeout > 0
      ? requestedCloseRecoveryTimeout
      : DEFAULT_CLOSE_RECOVERY_TIMEOUT_MS;
    this._debug = options.debug === true;
    this._worker = null;
    this._pending = new Map();
    this._listeners = new Set();
    this._nextRequestId = 1;
    this._generation = 1;
    this._disposed = false;
    this._ready = false;
    this.manifest = null;
  }

  async _initialize() {
    this._spawnWorker();
    this.manifest = await this._request(
      "init",
      { requestedAbiVersion: ABI_VERSION, debug: this._debug },
      { timeoutMs: Math.max(this._defaultTimeoutMs, 120000) },
    );
    this._ready = true;
    return this;
  }

  _spawnWorker() {
    const worker = this._workerFactory(this._workerUrl);
    this._worker = worker;
    const onMessage = (event) => {
      if (this._worker === worker)
        this._handleMessage(event.data);
    };
    const onError = (event) => {
      if (this._worker !== worker)
        return;
      const message = event?.message || "document worker emitted an error";
      this._handleCrash(new WorkerCrashedError(message));
    };
    const onMessageError = () => {
      if (this._worker === worker)
        this._handleCrash(new WorkerCrashedError("document worker message could not be decoded"));
    };
    worker.addEventListener("message", onMessage);
    worker.addEventListener("error", onError);
    worker.addEventListener("messageerror", onMessageError);
  }

  _nextId() {
    const value = this._nextRequestId;
    this._nextRequestId = value === 0xffffffff ? 1 : value + 1;
    return value;
  }

  _post(message, transfer = []) {
    if (!this._worker)
      throw new WorkerCrashedError("document worker is not available");
    this._worker.postMessage(message, transfer);
  }

  _request(operation, payload = {}, options = {}, transfer = []) {
    if (this._disposed)
      return Promise.reject(new DocumentSdkError("ENGINE_DISPOSED", "engine is disposed"));
    if (options.signal?.aborted)
      return Promise.reject(new SdkAbortError(operation));

    const requestId = this._nextId();
    const timeoutMs = options.timeoutMs ?? this._defaultTimeoutMs;
    return new Promise((resolve, reject) => {
      const entry = {
        operation,
        resolve,
        reject,
        timer: 0,
        signal: options.signal || null,
        abortListener: null,
      };

      const failAndCancel = (error) => {
        if (!this._pending.delete(requestId))
          return;
        this._cleanupPending(entry);
        try {
          this._post({
            protocolVersion: PROTOCOL_VERSION,
            kind: "cancel",
            requestId,
          });
        } catch {
          // The original timeout/abort remains the useful public error.
        }
        reject(error);
      };

      if (Number.isFinite(timeoutMs) && timeoutMs > 0) {
        entry.timer = setTimeout(
          () => failAndCancel(new SdkTimeoutError(operation, timeoutMs)),
          timeoutMs,
        );
      }
      if (entry.signal) {
        entry.abortListener = () => failAndCancel(new SdkAbortError(operation));
        entry.signal.addEventListener("abort", entry.abortListener, { once: true });
      }

      this._pending.set(requestId, entry);
      try {
        this._post({
          protocolVersion: PROTOCOL_VERSION,
          kind: "request",
          requestId,
          operation,
          payload,
        }, transfer);
      } catch (error) {
        this._pending.delete(requestId);
        this._cleanupPending(entry);
        reject(error);
      }
    });
  }

  _cleanupPending(entry) {
    if (entry.timer)
      clearTimeout(entry.timer);
    if (entry.signal && entry.abortListener)
      entry.signal.removeEventListener("abort", entry.abortListener);
  }

  _handleMessage(message) {
    if (!message || message.protocolVersion !== PROTOCOL_VERSION) {
      this._handleCrash(new WorkerCrashedError("worker protocol version mismatch"));
      return;
    }
    if (message.kind === "event") {
      this._emitEvent(message);
      return;
    }
    if (message.kind !== "response")
      return;

    const entry = this._pending.get(message.requestId);
    if (!entry)
      return;
    this._pending.delete(message.requestId);
    this._cleanupPending(entry);
    if (message.ok)
      entry.resolve(message.result);
    else
      entry.reject(remoteError(message, entry.operation));
  }

  _rejectPending(error) {
    for (const entry of this._pending.values()) {
      this._cleanupPending(entry);
      entry.reject(error);
    }
    this._pending.clear();
  }

  _handleCrash(error) {
    this._ready = false;
    this._rejectPending(error);
    this._emitEvent({
      protocolVersion: PROTOCOL_VERSION,
      kind: "event",
      event: "worker-crashed",
      error: { code: error.code, message: error.message },
    });
  }

  _emitEvent(event) {
    for (const listener of this._listeners)
      listener(event);
  }

  async _recoverTimedOutClose(documentHandle, timeoutMs) {
    const previousGeneration = this._generation;
    const detail = {
      strategy: "worker-restart",
      timeoutMs,
      previousGeneration,
    };
    this._emitEvent({
      protocolVersion: PROTOCOL_VERSION,
      kind: "event",
      event: "document-close-recovery-started",
      documentHandle,
      detail,
    });
    try {
      await this.restart();
    } catch (error) {
      this._emitEvent({
        protocolVersion: PROTOCOL_VERSION,
        kind: "event",
        event: "document-close-recovery-failed",
        documentHandle,
        detail: {
          ...detail,
          error: {
            code: error?.code || "RECOVERY_FAILED",
            message: String(error?.message || error),
          },
        },
      });
      throw error;
    }
    this._emitEvent({
      protocolVersion: PROTOCOL_VERSION,
      kind: "event",
      event: "document-close-recovery-complete",
      documentHandle,
      detail: {
        ...detail,
        generation: this._generation,
      },
    });
  }

  onEvent(listener) {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  async open(input, options = {}) {
    if (!this._ready)
      throw new WorkerCrashedError("engine is not ready; call restart() first");
    if (!(input instanceof ArrayBuffer) || input.byteLength === 0)
      throw new DocumentSdkError("INVALID_ARGUMENT", "open input must be a non-empty ArrayBuffer");

    const buffer = options.transfer === true ? input : input.slice(0);
    const result = await this._request(
      "open",
      { buffer, name: options.name || "input.odt" },
      options,
      [buffer],
    );
    return new DocumentHandle(this, this._generation, result);
  }

  async restart() {
    if (this._disposed)
      throw new DocumentSdkError("ENGINE_DISPOSED", "engine is disposed");
    this._ready = false;
    this._generation += 1;
    this._rejectPending(new WorkerRestartedError());
    if (this._worker)
      this._worker.terminate();
    this._worker = null;
    this._spawnWorker();
    this.manifest = await this._request(
      "init",
      { requestedAbiVersion: ABI_VERSION, debug: this._debug },
      { timeoutMs: Math.max(this._defaultTimeoutMs, 120000) },
    );
    this._ready = true;
    return this.manifest;
  }

  dispose() {
    if (this._disposed)
      return;
    this._disposed = true;
    this._ready = false;
    this._generation += 1;
    this._rejectPending(new DocumentSdkError("ENGINE_DISPOSED", "engine is disposed"));
    if (this._worker)
      this._worker.terminate();
    this._worker = null;
  }
}

export class DocumentHandle {
  constructor(engine, generation, metadata) {
    this._engine = engine;
    this._generation = generation;
    this._closed = false;
    this.handle = metadata.documentHandle;
    this.revision = metadata.revision;
    this.parts = metadata.parts;
    this.widthTwips = metadata.width;
    this.heightTwips = metadata.height;
    this.tileMode = metadata.tileMode;
  }

  _assertUsable() {
    if (this._closed)
      throw new DocumentClosedError();
    if (this._generation !== this._engine._generation)
      throw new StaleDocumentError();
  }

  _expectedRevision(options) {
    const expectedRevision = options.expectedRevision ?? this.revision;
    if (!Number.isInteger(expectedRevision) || expectedRevision < 0
        || expectedRevision > 0xffffffff) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "expectedRevision must be an unsigned 32-bit integer",
      );
    }
    return expectedRevision;
  }

  async render(region = {}, options = {}) {
    this._assertUsable();
    const result = await this._engine._request("paint", {
      documentHandle: this.handle,
      xTwips: region.xTwips ?? 0,
      yTwips: region.yTwips ?? 0,
      widthTwips: region.widthTwips ?? 7680,
      heightTwips: region.heightTwips ?? 7680,
      canvasWidthPx: region.canvasWidthPx ?? 512,
      canvasHeightPx: region.canvasHeightPx ?? 512,
    }, options);
    this.revision = result.revision;
    // Finding 062: the document's size was read once, at open, and nothing ever
    // re-read it -- so after an edit that added a page every client was sizing
    // its canvas from a stale number and had no way to find out.  The engine
    // now reports the size on the paint reply; keeping the handle current here
    // means a client that only ever calls render() is already correct, and
    // `documentSizeChanged` lets one that has already sized something act.
    if (typeof result.documentWidthTwips === "number")
      this.widthTwips = result.documentWidthTwips;
    if (typeof result.documentHeightTwips === "number")
      this.heightTwips = result.documentHeightTwips;
    return result;
  }

  async click(xTwips, yTwips, options = {}) {
    this._assertUsable();
    const result = await this._engine._request("click", {
      documentHandle: this.handle,
      xTwips,
      yTwips,
    }, options);
    this.revision = result.revision;
  }

  async insertText(text, options = {}) {
    this._assertUsable();
    if (typeof text !== "string" || text.length === 0)
      throw new DocumentSdkError("INVALID_ARGUMENT", "insertText requires non-empty text");
    const result = await this._engine._request("insertText", {
      documentHandle: this.handle,
      text,
    }, options);
    this.revision = result.revision;
    return result;
  }

  async search(query, options = {}) {
    this._assertUsable();
    if (typeof query !== "string" || query.length === 0)
      throw new DocumentSdkError("INVALID_ARGUMENT", "search requires non-empty text");
    const result = await this._engine._request("search", {
      documentHandle: this.handle,
      query,
      backward: options.backward === true,
    }, options);
    this.revision = result.revision;
    return result;
  }

  async getSelection(options = {}) {
    this._assertUsable();
    const result = await this._engine._request("getSelection", {
      documentHandle: this.handle,
    }, options);
    this.revision = result.revision;
    return result;
  }

  async replaceSelection(text, options = {}) {
    this._assertUsable();
    if (typeof text !== "string" || text.length === 0) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT", "replaceSelection requires non-empty text",
      );
    }
    const result = await this._engine._request("replaceSelection", {
      documentHandle: this.handle,
      expectedRevision: this._expectedRevision(options),
      text,
    }, options);
    this.revision = result.revision;
    return result;
  }

  async undo(options = {}) {
    this._assertUsable();
    const result = await this._engine._request("undo", {
      documentHandle: this.handle,
      expectedRevision: this._expectedRevision(options),
    }, options);
    this.revision = result.revision;
    return result;
  }

  async addComment(text, options = {}) {
    this._assertUsable();
    if (typeof text !== "string" || text.length === 0)
      throw new DocumentSdkError("INVALID_ARGUMENT", "addComment requires non-empty text");
    const author = options.author ?? "OxOffice SDK";
    if (typeof author !== "string" || author.length === 0)
      throw new DocumentSdkError("INVALID_ARGUMENT", "comment author must be non-empty");
    const result = await this._engine._request("addComment", {
      documentHandle: this.handle,
      expectedRevision: this._expectedRevision(options),
      text,
      author,
    }, options);
    this.revision = result.revision;
    return result;
  }

  async listComments(options = {}) {
    this._assertUsable();
    const result = await this._engine._request("listComments", {
      documentHandle: this.handle,
    }, options);
    this.revision = result.revision;
    return result;
  }

  async setTrackChanges(enabled, options = {}) {
    this._assertUsable();
    if (typeof enabled !== "boolean")
      throw new DocumentSdkError("INVALID_ARGUMENT", "enabled must be boolean");
    const result = await this._engine._request("setTrackChanges", {
      documentHandle: this.handle,
      expectedRevision: this._expectedRevision(options),
      enabled,
    }, options);
    this.revision = result.revision;
    return result;
  }

  async listTrackedChanges(options = {}) {
    this._assertUsable();
    const result = await this._engine._request("listTrackedChanges", {
      documentHandle: this.handle,
    }, options);
    this.revision = result.revision;
    return result;
  }

  async save(options = {}, requestOptions = {}) {
    this._assertUsable();
    const format = options.format || "odt";
    const result = await this._engine._request("save", {
      documentHandle: this.handle,
      format,
    }, requestOptions);
    this.revision = result.revision;
    return result.buffer;
  }

  async close(options = {}) {
    if (this._closed)
      return;
    this._assertUsable();
    const requestedTimeout = Number(options.timeoutMs ?? this._engine._defaultTimeoutMs);
    const timeoutMs = Number.isFinite(requestedTimeout) && requestedTimeout > 0
      ? Math.min(requestedTimeout, this._engine._closeRecoveryTimeoutMs)
      : this._engine._closeRecoveryTimeoutMs;
    try {
      await this._engine._request("close", {
        documentHandle: this.handle,
      }, { ...options, timeoutMs });
    } catch (error) {
      if (!(error instanceof SdkTimeoutError))
        throw error;
      await this._engine._recoverTimedOutClose(this.handle, timeoutMs);
    }
    this._closed = true;
  }
}

export async function createDocumentEngine(options = {}) {
  const engine = new DocumentEngine(options);
  return engine._initialize();
}
