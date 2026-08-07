export const READER_STATES = Object.freeze([
  "idle",
  "loading-core",
  "loading-document",
  "ready",
  "saving",
  "stale",
  "reloading",
  "conflict",
  "recoverable-error",
  "fatal-error",
  "closed",
]);

const ALLOWED_TRANSITIONS = Object.freeze({
  idle: new Set(["loading-core", "closed"]),
  "loading-core": new Set(["loading-document", "fatal-error", "closed"]),
  "loading-document": new Set(["ready", "recoverable-error", "fatal-error", "closed"]),
  ready: new Set([
    "saving", "stale", "conflict", "recoverable-error", "fatal-error", "closed",
  ]),
  saving: new Set([
    "ready", "stale", "conflict", "recoverable-error", "fatal-error", "closed",
  ]),
  stale: new Set(["reloading", "conflict", "fatal-error", "closed"]),
  reloading: new Set(["ready", "recoverable-error", "fatal-error", "closed"]),
  conflict: new Set(["reloading", "fatal-error", "closed"]),
  "recoverable-error": new Set(["reloading", "fatal-error", "closed"]),
  "fatal-error": new Set(["closed"]),
  closed: new Set(),
});

function copyError(error) {
  if (!error)
    return null;
  return Object.freeze({
    code: String(error.code || "UNKNOWN"),
    message: String(error.message || error),
    details: Object.freeze({ ...(error.details || {}) }),
  });
}

export class ReaderStateMachine {
  constructor(onChange = null) {
    this._onChange = onChange;
    this._snapshot = Object.freeze({
      state: "idle",
      documentId: null,
      version: null,
      etag: null,
      sdkRevision: null,
      profile: null,
      coreCommit: null,
      sdkVersion: null,
      providerContractVersion: null,
      hasLocalBytes: false,
      remoteUpdate: null,
      error: null,
      nextAction: "open",
    });
  }

  get snapshot() {
    return this._snapshot;
  }

  transition(nextState, patch = {}) {
    if (!READER_STATES.includes(nextState))
      throw new TypeError(`unknown reader state: ${nextState}`);
    if (!ALLOWED_TRANSITIONS[this._snapshot.state].has(nextState)) {
      throw new Error(
        `invalid reader transition: ${this._snapshot.state} -> ${nextState}`,
      );
    }
    const next = {
      ...this._snapshot,
      ...patch,
      state: nextState,
    };
    if (Object.hasOwn(patch, "error"))
      next.error = copyError(patch.error);
    if (Object.hasOwn(patch, "remoteUpdate") && patch.remoteUpdate)
      next.remoteUpdate = Object.freeze({ ...patch.remoteUpdate });
    next.nextAction = this._nextAction(next);
    this._snapshot = Object.freeze(next);
    this._onChange?.(this._snapshot);
    return this._snapshot;
  }

  update(patch = {}) {
    if (this._snapshot.state === "closed")
      throw new Error("closed reader state cannot be updated");
    const next = { ...this._snapshot, ...patch };
    if (Object.hasOwn(patch, "error"))
      next.error = copyError(patch.error);
    next.nextAction = this._nextAction(next);
    this._snapshot = Object.freeze(next);
    this._onChange?.(this._snapshot);
    return this._snapshot;
  }

  assertReloadAllowed({ discardLocalBytes = false, downloadedLocalBytes = false } = {}) {
    if (this._snapshot.hasLocalBytes && !discardLocalBytes && !downloadedLocalBytes) {
      const error = new Error("local bytes must be downloaded or explicitly discarded before reload");
      error.code = "LOCAL_BYTES_AT_RISK";
      throw error;
    }
  }

  markLocalBytes(present) {
    return this.update({ hasLocalBytes: present === true });
  }

  _nextAction(snapshot) {
    switch (snapshot.state) {
      case "idle": return "open";
      case "loading-core": return "wait-for-core";
      case "loading-document": return "wait-for-document";
      case "ready": return "read-or-request-edit";
      case "saving": return "wait-for-save";
      case "stale": return snapshot.hasLocalBytes ? "download-local-or-reload" : "reload";
      case "reloading": return "wait-for-reload";
      case "conflict": return snapshot.hasLocalBytes ? "download-local-and-reload" : "reload";
      case "recoverable-error": return "restart-and-reload";
      case "fatal-error": return "close";
      case "closed": return "none";
      default: return "none";
    }
  }
}
