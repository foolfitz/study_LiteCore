const TRANSITIONS = Object.freeze({
  idle: new Set(["loading", "closed"]),
  loading: new Set(["ready", "recoverable-error", "closed"]),
  ready: new Set(["busy", "restart-required", "recoverable-error", "closed"]),
  busy: new Set(["ready", "restart-required", "recoverable-error", "closed"]),
  "restart-required": new Set(["loading", "closed"]),
  "recoverable-error": new Set(["loading", "closed"]),
  closed: new Set(),
});

export class EditorStateMachine {
  constructor(onChange = () => {}) {
    this._onChange = onChange;
    this._snapshot = Object.freeze({
      state: "idle",
      documentName: null,
      revision: null,
      dirty: false,
      generation: 0,
      pending: 0,
      editorState: null,
      hasSavedBytes: false,
      error: null,
    });
  }

  get snapshot() {
    return this._snapshot;
  }

  transition(next, patch = {}) {
    const current = this._snapshot.state;
    if (!TRANSITIONS[current]?.has(next))
      throw new Error(`invalid editor transition ${current} -> ${next}`);
    return this._replace({ ...patch, state: next });
  }

  update(patch = {}) {
    if (this._snapshot.state === "closed")
      throw new Error("closed editor state cannot be updated");
    return this._replace(patch);
  }

  _replace(patch) {
    this._snapshot = Object.freeze({ ...this._snapshot, ...patch });
    this._onChange(this._snapshot);
    return this._snapshot;
  }
}
