const DEFAULT_MAX_UTF8_BYTES = 16 * 1024;
const DEFAULT_MAX_QUEUE_DEPTH = 8;
const TEXT_INPUT_TYPES = new Set([
  "insertText",
  "insertReplacementText",
  "insertFromPaste",
]);

export class InputAdapterError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "InputAdapterError";
    this.code = code;
    this.details = details;
  }
}

function utf8Bytes(text) {
  return new TextEncoder().encode(text).byteLength;
}

function codePoints(text) {
  return Array.from(text, (character) =>
    `U+${character.codePointAt(0).toString(16).toUpperCase().padStart(4, "0")}`,
  );
}

function eventSnapshot(event, type, extra = {}) {
  return {
    type,
    isTrusted: event?.isTrusted === true,
    inputType: event?.inputType || null,
    data: typeof event?.data === "string" ? event.data : null,
    defaultPrevented: event?.defaultPrevented === true,
    ...extra,
  };
}

/**
 * Host-side composition and plain-text clipboard adapter.
 *
 * `commit` is the only mutation boundary. Composition updates and cancel paths
 * never invoke it. SDK details remain outside this module.
 */
export class HostInputAdapter {
  constructor(options = {}) {
    if (typeof options.commit !== "function")
      throw new TypeError("HostInputAdapter requires a commit(text, metadata) function");
    this._commit = options.commit;
    this._onTrace = options.onTrace || (() => {});
    this._onState = options.onState || (() => {});
    this._maxUtf8Bytes = options.maxUtf8Bytes ?? DEFAULT_MAX_UTF8_BYTES;
    this._maxQueueDepth = options.maxQueueDepth ?? DEFAULT_MAX_QUEUE_DEPTH;
    if (!Number.isInteger(this._maxQueueDepth) || this._maxQueueDepth < 1)
      throw new TypeError("maxQueueDepth must be a positive integer");
    this._target = null;
    this._composing = false;
    this._compositionText = "";
    this._compositionId = 0;
    this._activeCompositionId = null;
    this._committedCompositionIds = new Set();
    this._duplicateToken = null;
    this._queue = [];
    this._queueIdleResolvers = [];
    this._processing = false;
    this._generation = 0;
    this._blocked = false;
    this._blockedReason = null;
    this._status = "idle";
    this._lastError = null;
    this._requestCount = 0;
    this._revision = 0;
    this._listeners = new Map([
      ["compositionstart", (event) => this.handleCompositionStart(event)],
      ["compositionupdate", (event) => this.handleCompositionUpdate(event)],
      ["compositionend", (event) => this.handleCompositionEnd(event)],
      ["beforeinput", (event) => this.handleBeforeInput(event)],
      ["paste", (event) => this.handlePaste(event)],
    ]);
  }

  get state() {
    return {
      status: this._status,
      composing: this._composing,
      compositionText: this._compositionText,
      compositionId: this._activeCompositionId,
      requestCount: this._requestCount,
      revision: this._revision,
      queueDepth: this._queue.length + (this._processing ? 1 : 0),
      blocked: this._blocked,
      blockedReason: this._blockedReason,
      error: this._lastError,
    };
  }

  _setStatus(status, patch = {}) {
    this._status = status;
    if (Object.hasOwn(patch, "error"))
      this._lastError = patch.error;
    this._onState(this.state);
  }

  attach(target) {
    if (!target?.addEventListener || !target?.removeEventListener)
      throw new TypeError("input target must implement addEventListener/removeEventListener");
    if (this._target === target)
      return;
    this.detach();
    this._target = target;
    for (const [type, listener] of this._listeners)
      target.addEventListener(type, listener);
    this._trace(null, "attach");
  }

  detach() {
    if (this._target) {
      for (const [type, listener] of this._listeners)
        this._target.removeEventListener(type, listener);
    }
    this._target = null;
    this.cancelComposition("teardown");
    this.invalidate("teardown", { blocked: false });
    this._trace(null, "detach");
  }

  _trace(event, type, extra = {}) {
    this._onTrace(eventSnapshot(event, type, {
      composing: this._composing,
      compositionId: this._activeCompositionId,
      requestCount: this._requestCount,
      revision: this._revision,
      status: this._status,
      queueDepth: this._queue.length + (this._processing ? 1 : 0),
      ...extra,
    }));
  }

  _prevent(event) {
    if (event?.cancelable !== false)
      event?.preventDefault?.();
  }

  handleCompositionStart(event) {
    if (this._blocked) {
      this._prevent(event);
      this._trace(event, "compositionstart", { action: "blocked", reason: this._blockedReason });
      return;
    }
    this._composing = true;
    this._compositionText = "";
    this._activeCompositionId = ++this._compositionId;
    this._duplicateToken = null;
    this._setStatus("composing", { error: null });
    this._trace(event, "compositionstart");
  }

  handleCompositionUpdate(event) {
    if (!this._composing)
      return;
    this._compositionText = typeof event?.data === "string" ? event.data : this._compositionText;
    this._trace(event, "compositionupdate", { compositionText: this._compositionText });
  }

  handleCompositionEnd(event) {
    const wasComposing = this._composing;
    const text = typeof event?.data === "string" ? event.data : this._compositionText;
    const compositionId = this._activeCompositionId;
    const sinkText = typeof this._target?.value === "string" ? this._target.value : "";
    this._composing = false;
    this._compositionText = "";
    this._activeCompositionId = null;
    this._trace(event, "compositionend", { wasComposing, compositionId, commitText: text, sinkText });
    if (!wasComposing || !text) {
      this._setStatus(this._blocked ? "blocked" : "idle");
      return Promise.resolve({ committed: false, reason: "empty-or-inactive-composition" });
    }
    if (this._blocked) {
      this._setStatus("blocked");
      return Promise.reject(new InputAdapterError(
        "INPUT_BLOCKED", "input is blocked", { reason: this._blockedReason },
      ));
    }
    if (sinkText && sinkText !== text) {
      const error = new InputAdapterError(
        "INPUT_COMPOSITION_MISMATCH",
        "compositionend data and host input buffer disagree",
        { compositionId, eventText: text, sinkText },
      );
      this._setStatus("recoverable-error", { error: { code: error.code, message: error.message } });
      this._trace(event, "composition-rejected", { reason: "buffer-mismatch", compositionId });
      return Promise.reject(error);
    }
    if (this._committedCompositionIds.has(compositionId)) {
      this._setStatus("idle");
      return Promise.resolve({ committed: false, reason: "duplicate-composition" });
    }
    this._committedCompositionIds.add(compositionId);

    const token = { text, available: true };
    this._duplicateToken = token;
    queueMicrotask(() => {
      if (this._duplicateToken === token)
        this._duplicateToken = null;
    });
    return this.commitText(text, {
      source: "composition", compositionId, isTrusted: event?.isTrusted === true,
    });
  }

  handleBeforeInput(event) {
    const inputType = event?.inputType || "";
    const data = typeof event?.data === "string" ? event.data : "";
    if (this._composing || inputType === "insertCompositionText") {
      this._prevent(event);
      this._trace(event, "beforeinput", { action: "composition-update-suppressed" });
      return Promise.resolve({ committed: false, reason: "composition-update" });
    }
    if (
      this._duplicateToken?.available
      && this._duplicateToken.text === data
      && TEXT_INPUT_TYPES.has(inputType)
    ) {
      this._duplicateToken.available = false;
      this._prevent(event);
      this._trace(event, "beforeinput", { action: "post-composition-duplicate-suppressed" });
      return Promise.resolve({ committed: false, reason: "post-composition-duplicate" });
    }
    if (inputType === "insertLineBreak" || inputType === "insertParagraph") {
      this._prevent(event);
      this._trace(event, "beforeinput", { action: "commit-line-break" });
      return this.commitText("\n", { source: "beforeinput", inputType, isTrusted: event?.isTrusted === true });
    }
    if (!TEXT_INPUT_TYPES.has(inputType)) {
      this._trace(event, "beforeinput", { action: "ignored-input-type" });
      return Promise.resolve({ committed: false, reason: "unsupported-input-type" });
    }
    this._prevent(event);
    this._trace(event, "beforeinput", { action: "commit-text" });
    return this.commitText(data, { source: "beforeinput", inputType, isTrusted: event?.isTrusted === true });
  }

  handlePaste(event) {
    this._prevent(event);
    const text = event?.clipboardData?.getData?.("text/plain") ?? "";
    const htmlPresent = Boolean(event?.clipboardData?.getData?.("text/html"));
    this._trace(event, "paste", { action: "commit-plain-text", htmlPresent });
    return this.commitText(text, {
      source: "clipboard-event",
      htmlPresent,
      isTrusted: event?.isTrusted === true,
    });
  }

  cancelComposition(reason = "cancel") {
    const wasComposing = this._composing;
    this._composing = false;
    this._compositionText = "";
    this._activeCompositionId = null;
    this._duplicateToken = null;
    if (!this._processing && this._queue.length === 0)
      this._setStatus(this._blocked ? "blocked" : "idle");
    this._trace(null, "compositioncancel", { reason, wasComposing });
    return { committed: false, reason };
  }

  setBlocked(blocked, reason = "blocked") {
    this._blocked = blocked === true;
    this._blockedReason = this._blocked ? String(reason) : null;
    if (this._blocked) {
      this.cancelComposition(reason);
      this.invalidate(reason, { blocked: true });
      this._setStatus("blocked", { error: null });
    } else if (!this._processing && this._queue.length === 0) {
      this._setStatus("idle", { error: null });
    }
    if (this._target && "disabled" in this._target)
      this._target.disabled = this._blocked;
    this._trace(null, "blocked-change", { blocked: this._blocked, reason: this._blockedReason });
  }

  invalidate(reason = "stale", options = {}) {
    this._generation += 1;
    const queued = this._queue.splice(0);
    const error = new InputAdapterError(
      "INPUT_CANCELLED", "queued input was cancelled", { reason },
    );
    for (const item of queued)
      item.reject(error);
    if (options.blocked === true) {
      this._blocked = true;
      this._blockedReason = String(reason);
    }
    if (!this._processing)
      this._setStatus(this._blocked ? "blocked" : "idle");
    this._trace(null, "queue-invalidated", { reason, cancelled: queued.length });
    this._resolveIdle();
    return { cancelled: queued.length, generation: this._generation };
  }

  commitClipboardText(text, metadata = {}) {
    return this.commitText(text, { source: "clipboard-api", ...metadata });
  }

  commitText(text, metadata = {}) {
    if (typeof text !== "string")
      return Promise.reject(new InputAdapterError("INVALID_TEXT", "commit text must be a string"));
    if (text.length === 0) {
      this._trace(null, "commit-skipped", { reason: "empty", metadata });
      return Promise.resolve({ committed: false, reason: "empty" });
    }
    if (this._blocked) {
      const error = new InputAdapterError(
        "INPUT_BLOCKED", "input is blocked", { reason: this._blockedReason },
      );
      this._trace(null, "commit-rejected", { reason: "blocked", metadata });
      return Promise.reject(error);
    }
    const bytes = utf8Bytes(text);
    if (bytes > this._maxUtf8Bytes) {
      this._trace(null, "commit-rejected", { reason: "input-too-large", bytes, metadata });
      return Promise.reject(new InputAdapterError(
        "INPUT_TOO_LARGE",
        `input is ${bytes} UTF-8 bytes; limit is ${this._maxUtf8Bytes}`,
        { bytes, maxUtf8Bytes: this._maxUtf8Bytes },
      ));
    }

    const queuedDepth = this._queue.length + (this._processing ? 1 : 0);
    if (queuedDepth >= this._maxQueueDepth) {
      const error = new InputAdapterError(
        "INPUT_BACKPRESSURE",
        `input queue is full; limit is ${this._maxQueueDepth}`,
        { maxQueueDepth: this._maxQueueDepth },
      );
      this._trace(null, "commit-rejected", { reason: "queue-full", metadata });
      return Promise.reject(error);
    }
    const requestNumber = ++this._requestCount;
    const generation = this._generation;
    const pending = new Promise((resolve, reject) => {
      this._queue.push({
        requestNumber, generation, text, metadata, bytes, resolve, reject,
      });
    });
    this._pump();
    return pending;
  }

  async _pump() {
    if (this._processing)
      return;
    const item = this._queue.shift();
    if (!item) {
      if (!this._composing)
        this._setStatus(this._blocked ? "blocked" : "idle");
      this._resolveIdle();
      return;
    }
    if (item.generation !== this._generation) {
      item.reject(new InputAdapterError(
        "INPUT_CANCELLED", "queued input was cancelled", { reason: "stale-generation" },
      ));
      this._pump();
      return;
    }
    this._processing = true;
    this._setStatus("committing", { error: null });
    try {
      this._trace(null, "commit-start", {
        requestNumber: item.requestNumber,
        text: item.text,
        utf16Length: item.text.length,
        utf8Bytes: item.bytes,
        codePoints: codePoints(item.text),
        metadata: item.metadata,
      });
      const result = await this._commit(item.text, {
        ...item.metadata,
        requestNumber: item.requestNumber,
        utf8Bytes: item.bytes,
        generation: item.generation,
      });
      if (Number.isInteger(result?.revision))
        this._revision = result.revision;
      this._trace(null, "commit-end", { requestNumber: item.requestNumber, result });
      item.resolve({
        committed: true,
        requestNumber: item.requestNumber,
        bytes: item.bytes,
        result,
      });
    } catch (error) {
      this._lastError = {
        code: error?.code || "INPUT_COMMIT_FAILED",
        message: error?.message || String(error),
      };
      this._trace(null, "commit-error", {
        requestNumber: item.requestNumber,
        error: this._lastError,
      });
      item.reject(error);
    } finally {
      this._processing = false;
      if (this._lastError && this._queue.length === 0)
        this._setStatus("recoverable-error", { error: this._lastError });
      this._pump();
    }
  }

  idle() {
    if (!this._processing && this._queue.length === 0)
      return Promise.resolve();
    return new Promise((resolve) => this._queueIdleResolvers.push(resolve));
  }

  _resolveIdle() {
    if (this._processing || this._queue.length)
      return;
    for (const resolve of this._queueIdleResolvers.splice(0))
      resolve();
  }
}

export function summarizeUnicode(text) {
  return {
    text,
    utf16Length: text.length,
    utf8Bytes: utf8Bytes(text),
    codePoints: codePoints(text),
  };
}
