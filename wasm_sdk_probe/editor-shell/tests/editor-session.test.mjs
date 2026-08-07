import assert from "node:assert/strict";
import test from "node:test";

import { EditorSession } from "../editor-session.js";

function fixture(options = {}) {
  const calls = [];
  const listeners = new Set();
  const clipboardWrites = [];
  let revision = 0;
  const state = () => ({
    documentHandle: 1,
    revision,
    sourceSequence: revision + 1,
    documentChangeSequence: revision,
    visible: true,
    caret: null,
    selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
    selectionType: "none",
    selectionTextMissing: false,
    selectionText: "",
    format: { bold: false, italic: false },
  });
  const document = {
    handle: 1,
    revision: 0,
    widthTwips: 1000,
    heightTwips: 2000,
    _assertUsable() {},
    async render() { return { pixels: new ArrayBuffer(4), revision }; },
    async click() { calls.push("click"); },
    async getSelection() {
      calls.push("selection");
      return {
        text: "臺灣😀",
        mimeType: "text/plain;charset=utf-8",
        selectionType: "text",
        revision,
      };
    },
    async insertText(text) {
      calls.push(`text:${text}`);
      await Promise.resolve();
      this.revision = ++revision;
      return { revision, method: "paste" };
    },
    async undo() { calls.push("undo"); this.revision = ++revision; return { revision }; },
    async save() { calls.push("save"); return new ArrayBuffer(24); },
    async close() { calls.push("close"); },
  };
  const engine = {
    manifest: {
      profile: "e1-editor-v1",
      capabilities: ["narrow-editor-v1"],
      editorContract: { version: 1 },
    },
    onEvent(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    async open() { calls.push("open"); return document; },
    async _request(operation, payload) {
      calls.push(`${operation}:${payload.action || "state"}`);
      if (operation === "editorGetStateV1")
        return state();
      if (payload.action === "delete-forward" && fixture.boundaryFailure) {
        const error = new Error("boundary");
        error.code = "EDITOR_BOUNDARY_UNSUPPORTED";
        throw error;
      }
      const moving = payload.action.startsWith("move-");
      if (!moving)
        document.revision = ++revision;
      return {
        action: payload.action,
        beforeRevision: payload.expectedRevision,
        revision,
        changed: !moving,
        completion: moving
          ? "documented-callback-visible-cursor"
          : payload.action.startsWith("delete-")
            ? "verified-selection-delete" : "uno-command-result",
        state: state(),
      };
    },
    dispose() { calls.push("dispose"); },
  };
  document._engine = engine;
  return {
    calls,
    clipboardWrites,
    document,
    listeners,
    session: new EditorSession({
      engineFactory: async () => engine,
      maxWorkerGenerations: options.maxWorkerGenerations,
      secureContext: true,
      clipboard: options.clipboard || {
        async writeText(text) { clipboardWrites.push(text); },
        async readText() { return "剪貼簿文字"; },
      },
    }),
  };
}
fixture.boundaryFailure = false;

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

test("session serializes committed text and editor mutations", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16), name: "fixture.odt" });
  const first = value.session.commitText("甲");
  const second = value.session.insertBreak("paragraph");
  await Promise.all([first, second]);
  assert.deepEqual(value.calls.filter((entry) => entry.startsWith("text:")
    || entry.includes("insert-paragraph-break")), [
    "text:甲", "editorActionV1:insert-paragraph-break",
  ]);
  assert.equal(value.session.state.snapshot.revision, 2);
  assert.equal(value.session.state.snapshot.dirty, true);
  await value.session.close();
});

test("boundary rejection blocks queued mutations and restart does not replay them", async () => {
  fixture.boundaryFailure = true;
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await assert.rejects(() => value.session.delete("forward"), {
    code: "EDITOR_BOUNDARY_UNSUPPORTED",
  });
  assert.equal(value.session.state.snapshot.state, "restart-required");
  await assert.rejects(() => value.session.commitText("不可重送"), { code: "EDITOR_NOT_READY" });
  fixture.boundaryFailure = false;
  await value.session.restart();
  assert.equal(value.session.state.snapshot.state, "ready");
  assert.equal(value.calls.includes("text:不可重送"), false);
  assert.equal(value.calls.filter((entry) => entry === "open").length, 2);
  await value.session.close();
});

test("save replaces restart authority bytes and clears dirty state", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.commitText("乙");
  const saved = await value.session.save();
  assert.equal(saved.bytes.byteLength, 24);
  assert.equal(value.session.state.snapshot.dirty, false);
  assert.equal(value.session.state.snapshot.hasSavedBytes, true);
  await value.session.close();
});

test("restart isolates a late old-generation drain from queued new-generation operations", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  const stale = deferred();
  const firstOutcome = value.session._enqueue(
    "stale-generation-operation",
    () => stale.promise,
    { mutation: true },
  ).catch((error) => error);
  const queuedOutcome = value.session.commitText("不可重播").catch((error) => error);
  for (const listener of value.listeners) {
    listener({
      event: "worker-crashed",
      error: { code: "WORKER_CRASHED", message: "fixture crash" },
    });
  }
  assert.equal((await queuedOutcome).code, "WORKER_CRASHED");
  assert.equal(value.session.state.snapshot.state, "recoverable-error");

  await value.session.restart();
  const fresh = deferred();
  value.document.save = async () => {
    value.calls.push("save-deferred");
    return fresh.promise;
  };
  const savePromise = value.session.save();
  const freshDrain = value.session._activeDrain;
  const nextMutation = value.session.commitText("新世代排隊操作");

  stale.resolve({ revision: 99 });
  const staleError = await firstOutcome;
  assert.equal(staleError.code, "STALE_EDITOR_GENERATION");
  assert.equal(value.session._activeDrain, freshDrain);
  assert.equal(value.calls.includes("text:新世代排隊操作"), false);

  fresh.resolve(new ArrayBuffer(24));
  const saved = await savePromise;
  await nextMutation;
  assert.equal(saved.bytes.byteLength, 24);
  assert.equal(value.calls.includes("text:不可重播"), false);
  assert.equal(value.calls.includes("text:新世代排隊操作"), true);
  assert.equal(value.session.state.snapshot.state, "ready");
  assert.equal(value.session.state.snapshot.pending, 0);
  await value.session.close();
});

test("a late old-generation rejection cannot re-enter recovery after restart", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  const stale = deferred();
  const staleOutcome = value.session._enqueue(
    "stale-generation-operation",
    () => stale.promise,
  ).catch((error) => error);
  for (const listener of value.listeners) {
    listener({
      event: "worker-crashed",
      error: { code: "WORKER_CRASHED", message: "fixture crash" },
    });
  }
  await value.session.restart();

  const late = Object.assign(new Error("late old Worker rejection"), {
    code: "WORKER_CRASHED",
  });
  stale.reject(late);
  assert.equal((await staleOutcome).code, "WORKER_CRASHED");
  const saved = await value.session.save();
  assert.equal(saved.bytes.byteLength, 24);
  assert.equal(value.session.state.snapshot.state, "ready");
  assert.equal(value.session.state.snapshot.pending, 0);
  await value.session.close();
});

test("a late old-generation save cannot replace current authority bytes", async () => {
  const value = fixture();
  const originalAuthorityBytes = new ArrayBuffer(16);
  await value.session.open({ bytes: originalAuthorityBytes });
  const staleSave = deferred();
  value.document.save = async () => staleSave.promise;
  const staleOutcome = value.session.save().catch((error) => error);
  for (const listener of value.listeners) {
    listener({
      event: "worker-crashed",
      error: { code: "WORKER_CRASHED", message: "fixture crash" },
    });
  }
  await value.session.restart();

  staleSave.resolve(new ArrayBuffer(99));
  assert.equal((await staleOutcome).code, "STALE_EDITOR_GENERATION");
  assert.equal(value.session._authorityBytes.byteLength, originalAuthorityBytes.byteLength);
  assert.equal(value.session.state.snapshot.hasSavedBytes, false);
  assert.equal(value.session.state.snapshot.state, "ready");
  await value.session.close();
});

test("plain-text clipboard copy is non-mutating and paste enters the FIFO input boundary", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  const beforeRevision = value.session.document.revision;
  const copied = await value.session.copySelection();
  assert.deepEqual(value.clipboardWrites, ["臺灣😀"]);
  assert.equal(copied.revision, beforeRevision);
  const pasted = await value.session.pasteFromClipboard({ userGesture: true });
  assert.equal(pasted.committed, true);
  assert.equal(value.calls.includes("text:剪貼簿文字"), true);
  assert.equal(value.session.document.revision, beforeRevision + 1);
  await value.session.close();
});

test("clipboard denial causes zero mutation", async () => {
  const denied = Object.assign(new Error("denied"), { name: "NotAllowedError" });
  const value = fixture({
    clipboard: {
      async writeText() {},
      async readText() { throw denied; },
    },
  });
  await value.session.open({ bytes: new ArrayBuffer(16) });
  const beforeRevision = value.session.document.revision;
  await assert.rejects(
    () => value.session.pasteFromClipboard({ userGesture: true }),
    { code: "CLIPBOARD_DENIED" },
  );
  assert.equal(value.session.document.revision, beforeRevision);
  assert.equal(value.calls.some((entry) => entry.startsWith("text:")), false);
  await value.session.close();
});

test("Worker generation ceiling fails closed and requires a page reload", async () => {
  const value = fixture({ maxWorkerGenerations: 2 });
  await value.session.open({ bytes: new ArrayBuffer(16) });
  fixture.boundaryFailure = true;
  await assert.rejects(() => value.session.delete("forward"), {
    code: "EDITOR_BOUNDARY_UNSUPPORTED",
  });
  fixture.boundaryFailure = false;
  await value.session.restart();
  fixture.boundaryFailure = true;
  await assert.rejects(() => value.session.delete("forward"), {
    code: "EDITOR_BOUNDARY_UNSUPPORTED",
  });
  fixture.boundaryFailure = false;
  await assert.rejects(
    () => value.session.restart(),
    (error) => error.code === "WORKER_GENERATION_LIMIT"
      && error.details.requiresPageReload === true,
  );
  assert.equal(value.session.state.snapshot.state, "recoverable-error");
  assert.equal(value.calls.filter((entry) => entry === "open").length, 2);
  await value.session.close();
});
