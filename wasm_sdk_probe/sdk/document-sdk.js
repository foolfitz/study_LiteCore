export const PROTOCOL_VERSION = 1;
export const ABI_VERSION = 0x00010001;
const DEFAULT_CLOSE_RECOVERY_TIMEOUT_MS = 10000;
// Finding 133 (SPEC-M3-autosave §9.20).  A deadline timer that fires more than
// this late was not starved by a slow engine: the page -- and the Worker with
// it -- was stopped (a frozen tab, a sleeping machine).  Such a deadline is not
// reported as TIMEOUT (which the session reads as "the engine is dead"); it is
// moved to now + the grace and looked at again.  The grace is a fixed 10 s,
// not the budget the request had left: a request that still needs more than
// that after the stop times out after its extension (L-133-grace, §9.22).
const DEFAULT_LATE_DEADLINE_MS = 2000;
const DEFAULT_LATE_DEADLINE_GRACE_MS = 10000;

export class DocumentSdkError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "DocumentSdkError";
    this.code = code;
    this.details = details;
  }
}

export class SdkTimeoutError extends DocumentSdkError {
  constructor(operation, timeoutMs, extension = null) {
    const extended = extension
      ? ` (+${extension.extendedMs} ms in ${extension.extensions} extension(s) after a late deadline)`
      : "";
    super("TIMEOUT", `${operation} timed out after ${timeoutMs} ms${extended}`, {
      operation,
      timeoutMs,
      ...(extension || {}),
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

// SPEC-M3-link-batch 4.3 / 10.8: the engine's raw page-rectangle string did
// not parse, or its count disagrees with `getParts()`.  TYPED so a page can
// tell it from every other failure, and so that a document that has pages
// never comes back as an empty list.
export class PageRectanglesError extends DocumentSdkError {
  constructor(message, details = {}) {
    super("PAGE_RECTANGLES_INVALID", message, details);
    this.name = "PageRectanglesError";
  }
}

const PAGE_RECTANGLES_DECLARATION = "document-sdk-page-rectangles";
const TWIPS_FIELD = /^(0|[1-9][0-9]*)$/;

// SPEC-M3-link-batch-v21 9.2: the OPERATIVE limit of a Markdown paste, in
// UTF-8 bytes.  The engine's 64 KiB is the hard limit, fixed at link time; this
// one is where the product's limit actually lives, so lowering it (11.2 M6's
// fallback to 16 KiB) is a shell change and never a relink.  Checked before any
// request is issued.
export const MARKDOWN_PASTE_LIMIT_BYTES = 65536;
const PASTE_MARKDOWN_DECLARATION = "document-sdk-paste-markdown";
const utf8 = new TextEncoder();

// SPEC-M3-link-batch-v24 4.3 (finding 168): which engine route a commit takes,
// by the input adapter's `source`.  Typed text goes through .uno:InsertText,
// which replaces a selection the way the keyboard does; a real paste keeps
// Writer's paste.  The keys are exactly the adapter's `source:` literals --
// T3 extracts them from input/*.js and requires equality, so a new commit
// source cannot ship without being routed here.
export const INSERT_ROUTE_BY_SOURCE = new Map([
  ["beforeinput", "uno-insert-text"],
  ["composition", "uno-insert-text"],
  ["clipboard-event", "paste"],
  ["clipboard-api", "paste"],
]);
export const TYPED_INSERT_DECLARATION = "document-sdk-insert-typed-text";
// Enter is another family and NUL cannot cross jsonEscape: those keep paste.
const TYPED_INSERT_REFUSED = /[\u0000\n\r]/;

function insertRoute(text, source) {
  if (source !== undefined && source !== null && source !== ""
      && !INSERT_ROUTE_BY_SOURCE.has(source)) {
    throw new DocumentSdkError(
      "INSERT_ORIGIN_UNKNOWN",
      `insertText has no route for metadata source ${JSON.stringify(source)}`,
      { operation: "insertText", dispatched: false, source });
  }
  return INSERT_ROUTE_BY_SOURCE.get(source) === "uno-insert-text"
      && !TYPED_INSERT_REFUSED.test(text)
    ? "uno-insert-text" : "paste";
}

/**
 * Parse `getPartPageRectangles()`'s string: "x, y, w, h; x, y, w, h; ..." in
 * twips, one rectangle per page in page order, no trailing separator
 * (sw/source/core/crsr/crsrsh.cxx SwCursorShell::getPageRectangles strips the
 * last "; "; measured natively in findings/evidence/link-batch/page-rectangles/).
 *
 * Strict on purpose: every field a non-negative decimal integer, every page
 * with positive width and height, and the count equal to `parts` -- two core
 * sources for the page count (S-10), so a disagreement is an error here and
 * not a silently shorter list.  Anything else throws PageRectanglesError; an
 * empty list is never returned, because a page would read it as "no pages",
 * which is a confident wrong answer about the user's file.
 */
export function parsePageRectangles(text, parts) {
  const invalid = (message, details = {}) =>
    new PageRectanglesError(`page rectangles: ${message}`, { text, parts, ...details });
  if (!Number.isInteger(parts) || parts < 1)
    throw invalid("parts must be a positive integer");
  if (typeof text !== "string" || text.trim() === "")
    throw invalid("the engine returned no rectangle string");
  const rectangles = text.split(";").map((piece, index) => {
    const fields = piece.split(",").map((field) => field.trim());
    if (fields.length !== 4 || !fields.every((field) => TWIPS_FIELD.test(field)))
      throw invalid(`rectangle ${index} is not four non-negative integers`, { piece });
    const [x, y, width, height] = fields.map(Number);
    if (width < 1 || height < 1)
      throw invalid(`rectangle ${index} has no area`, { piece });
    return { x, y, width, height };
  });
  if (rectangles.length !== parts) {
    throw invalid(`${rectangles.length} rectangles for ${parts} parts`,
                  { rectangles: rectangles.length });
  }
  return rectangles;
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
    // Injectable only so the unit tests need not wait (133-U); the page never
    // passes them.  performance.now() is monotonic: a clock step cannot fake
    // a late deadline.
    this._now = typeof options.now === "function"
      ? options.now
      : () => globalThis.performance?.now?.() ?? Date.now();
    const lateDeadline = Number(options.lateDeadlineMs ?? DEFAULT_LATE_DEADLINE_MS);
    this._lateDeadlineMs = Number.isFinite(lateDeadline) && lateDeadline > 0
      ? lateDeadline : DEFAULT_LATE_DEADLINE_MS;
    const lateGrace = Number(options.lateDeadlineGraceMs ?? DEFAULT_LATE_DEADLINE_GRACE_MS);
    this._lateDeadlineGraceMs = Number.isFinite(lateGrace) && lateGrace > 0
      ? lateGrace : DEFAULT_LATE_DEADLINE_GRACE_MS;
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
        // Finding 133: on time (late <= _lateDeadlineMs) it is a TIMEOUT as
        // before; found late, the page was stopped, so no failure and no
        // cancel -- the deadline becomes now + the grace and is looked at
        // again (and again, if the page is stopped once more).
        let dueAt = this._now() + timeoutMs;
        let extendedMs = 0;
        let extensions = 0;
        const expire = () => {
          if (!this._pending.has(requestId))
            return;
          if (this._now() - dueAt > this._lateDeadlineMs) {
            extensions += 1;
            extendedMs += this._lateDeadlineGraceMs;
            dueAt = this._now() + this._lateDeadlineGraceMs;
            entry.timer = setTimeout(expire, this._lateDeadlineGraceMs);
            return;
          }
          failAndCancel(new SdkTimeoutError(operation, timeoutMs,
            extensions ? { extendedMs, extensions } : null));
        };
        entry.timer = setTimeout(expire, timeoutMs);
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
    // SPEC-P-ms-formats E5: the format the engine accepted the document as
    // (odt, docx, ods, xlsx), from the open reply.  A worker that does not say
    // -- every profile before e2-editor-v33 / ods-editor-v5 -- leaves it null,
    // and the caller decides what null means; this never guesses from a name.
    this.format = typeof metadata.format === "string" && metadata.format !== ""
      ? metadata.format : null;
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

  // SPEC-M3-link-batch-v24 4.3: on a profile that declares the typed route,
  // EVERY insert says which route the SDK chose (`route`), so a request without
  // one can only come from another SDK.  On any other profile `metadata` is not
  // read at all and the request is the one that profile shipped with and was
  // measured on -- no route, no new error (fable ruling 2, follow-up A1).
  async insertText(text, options = {}) {
    this._assertUsable();
    if (typeof text !== "string" || text.length === 0)
      throw new DocumentSdkError("INVALID_ARGUMENT", "insertText requires non-empty text");
    const payload = { documentHandle: this.handle, text };
    if (this._engine.manifest?.editorContract?.typedInsert === TYPED_INSERT_DECLARATION)
      payload.route = insertRoute(text, options.metadata?.source);
    const result = await this._engine._request("insertText", payload, options);
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

  // The sibling of undo, and deliberately written as one: same shape, same
  // revision handling, same absence of arguments.  redo is a document-level
  // operation rather than an editor action, so it has no wire id -- an action
  // id would drag the gesture mask and the option-flag validation along with
  // it, and none of those has a meaning for walking the undo stack.
  async redo(options = {}) {
    this._assertUsable();
    const result = await this._engine._request("redo", {
      documentHandle: this.handle,
      expectedRevision: this._expectedRevision(options),
    }, options);
    this.revision = result.revision;
    return result;
  }

  // SPEC-M3-link-batch 4.3 / 10.8 (S-11): the page number's data.  A
  // document-level export like redo -- no wire id, no gesture -- and GATED
  // like redo, on the contract's declaration, because the export is compiled:
  // on a profile whose binary predates it the symbol is simply not there.
  // Absent means UNSUPPORTED_OPERATION before any request is issued.
  //
  // The reply's raw string is parsed HERE, never in the engine (10.8); a
  // malformed string, or a count that disagrees with getParts(), is a typed
  // error and never an empty list.  Twips throughout.  The handle's size and
  // revision follow the reply, as they follow a paint reply.
  async pageRectangles(options = {}) {
    this._assertUsable();
    const contract = this._engine.manifest?.editorContract;
    if (contract?.pageRectangles !== PAGE_RECTANGLES_DECLARATION) {
      throw new DocumentSdkError(
        "UNSUPPORTED_OPERATION",
        "the active profile does not declare page rectangles",
      );
    }
    const result = await this._engine._request("pageRectangles", {
      documentHandle: this.handle,
    }, options);
    const rectangles = parsePageRectangles(result.rectangles, result.parts);
    this.revision = result.revision;
    if (typeof result.documentWidthTwips === "number")
      this.widthTwips = result.documentWidthTwips;
    if (typeof result.documentHeightTwips === "number")
      this.heightTwips = result.documentHeightTwips;
    return {
      rectangles,
      parts: result.parts,
      widthTwips: result.documentWidthTwips,
      heightTwips: result.documentHeightTwips,
      revision: result.revision,
    };
  }

  // SPEC-M3-link-batch-v21 4.2 / 9.2 / 11.2: paste `text` as Markdown at the
  // caret.  A document-level export like pageRectangles -- no wire id, no
  // gesture -- and gated the same way, on the contract's declaration
  // (`pasteMarkdown: "document-sdk-paste-markdown"`), because the export is
  // compiled.  Absent means UNSUPPORTED_OPERATION before any request.
  //
  // The size check is the operative limit (MARKDOWN_PASTE_LIMIT_BYTES), in
  // UTF-8 bytes as the engine counts them; over it is INVALID_ARGUMENT with
  // nothing sent, and `details.limitBytes` says this layer refused (11.2 M3
  // asserts which layer).  Empty text is refused here too: the worker cannot
  // put zero bytes into WASM.  Everything else about the content -- remote
  // images, raw HTML, "no block", NUL, the caret rule -- is the engine's to
  // judge, with md4c, before it dispatches (9.3, 9.14, 10.4).
  async pasteMarkdown(text, options = {}) {
    this._assertUsable();
    const contract = this._engine.manifest?.editorContract;
    if (contract?.pasteMarkdown !== PASTE_MARKDOWN_DECLARATION) {
      throw new DocumentSdkError(
        "UNSUPPORTED_OPERATION",
        "the active profile does not declare the Markdown paste",
      );
    }
    if (typeof text !== "string" || text.length === 0) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT", "pasteMarkdown requires non-empty text",
        { operation: "pasteMarkdown", dispatched: false });
    }
    const utf8Bytes = utf8.encode(text).byteLength;
    if (utf8Bytes > MARKDOWN_PASTE_LIMIT_BYTES) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        `the Markdown is ${utf8Bytes} UTF-8 bytes; the limit is ${MARKDOWN_PASTE_LIMIT_BYTES}`,
        { operation: "pasteMarkdown", dispatched: false,
          limitBytes: MARKDOWN_PASTE_LIMIT_BYTES, utf8Bytes });
    }
    const result = await this._engine._request("pasteMarkdown", {
      documentHandle: this.handle,
      text,
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
