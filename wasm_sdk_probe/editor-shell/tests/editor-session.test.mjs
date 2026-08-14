import assert from "node:assert/strict";
import test from "node:test";

import { EditorSession } from "../editor-session.js";

function fixture(options = {}) {
  const calls = [];
  const listeners = new Set();
  const clipboardWrites = [];
  const openedBytes = [];
  const requests = [];
  const saveRequests = [];
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
    async save(formatOptions, requestOptions) {
      calls.push("save");
      saveRequests.push({ formatOptions, requestOptions });
      return new ArrayBuffer(24);
    },
    async close() { calls.push("close"); },
  };
  const engine = {
    manifest: {
      profile: "e1-editor-v1",
      capabilities: ["narrow-editor-v1"],
      editorContract: { version: 1 },
    },
    onEvent(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    async open(bytes) {
      calls.push("open");
      openedBytes.push(bytes.slice(0));
      revision = 0;
      document.revision = 0;
      return document;
    },
    async _request(operation, payload, requestOptions) {
      calls.push(`${operation}:${payload.action || "state"}`);
      requests.push({ operation, payload: { ...payload }, options: requestOptions });
      if (operation === "editorGetStateV1")
        return state();
      if (operation === "editorSelectRangeV1")
        return { revision };
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
    engine,
    listeners,
    openedBytes,
    requests,
    saveRequests,
    session: new EditorSession({
      engineFactory: async () => engine,
      maxWorkerGenerations: options.maxWorkerGenerations,
      selectionTimeoutMs: options.selectionTimeoutMs,
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

const selectionStart = Object.freeze({ xTwips: 10, yTwips: 20 });
const selectionEnd = Object.freeze({ xTwips: 30, yTwips: 40 });

function rejectSelectionReadback(value) {
  const request = value.engine._request.bind(value.engine);
  let selectionIssued = false;
  value.engine._request = async (...args) => {
    const [operation] = args;
    const result = await request(...args);
    if (operation === "editorSelectRangeV1")
      selectionIssued = true;
    else if (operation === "editorGetStateV1" && selectionIssued) {
      selectionIssued = false;
      const error = new Error("selection readback timed out");
      error.code = "TIMEOUT";
      throw error;
    }
    return result;
  };
  return () => { value.engine._request = request; };
}

test("selectRange applies the bounded selection timeout by default", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.selectRange(selectionStart, selectionEnd);
  const request = value.requests.find((entry) => entry.operation === "editorSelectRangeV1");
  assert.equal(request.options.timeoutMs, 5000);
  assert.notEqual(request.options.timeoutMs, 30000);
  await value.session.close();
});

test("selectRange preserves a caller timeout over the configured selection timeout", async () => {
  const value = fixture({ selectionTimeoutMs: 4321 });
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.selectRange(selectionStart, selectionEnd, { timeoutMs: 1234 });
  await value.session.selectRange(selectionStart, selectionEnd);
  const requests = value.requests.filter((entry) => entry.operation === "editorSelectRangeV1");
  assert.deepEqual(requests.map((entry) => entry.options.timeoutMs), [1234, 4321]);
  await value.session.close();
});

test("only selection-extending character movement gets the selection timeout", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.moveCharacter("right", { extendSelection: true });
  await value.session.moveCharacter("right");
  const requests = value.requests.filter((entry) => entry.operation === "editorActionV1"
    && entry.payload.action === "move-character-right");
  assert.equal(requests[0].options.timeoutMs, 5000);
  assert.equal(requests[1].options.timeoutMs, undefined);
  await value.session.close();
});

test("a dirty session checkpoints before issuing a selection", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.commitText("檢查點");
  await value.session.selectRange(selectionStart, selectionEnd);
  assert.ok(value.calls.indexOf("save") < value.calls.indexOf("editorSelectRangeV1:state"));
  assert.equal(value.saveRequests[0].requestOptions.timeoutMs, 5000);
  assert.equal(value.session.state.snapshot.hasCheckpoint, true);
  assert.equal(value.session.state.snapshot.checkpointRevision, 1);
  const bytes = value.session.checkpointBytes();
  assert.equal(bytes.byteLength, 24);
  new Uint8Array(bytes)[0] = 255;
  assert.equal(new Uint8Array(value.session.checkpointBytes())[0], 0);
  await value.session.close();
});

test("a clean session does not take a selection checkpoint", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.selectRange(selectionStart, selectionEnd);
  assert.equal(value.calls.includes("save"), false);
  assert.equal(value.session.state.snapshot.hasCheckpoint, false);
  assert.equal(value.session.state.snapshot.checkpointRevision, null);
  assert.equal(value.session.checkpointBytes(), null);
  await value.session.close();
});

test("a second selection at the checkpointed revision does not save again", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.commitText("只存一次");
  await value.session.selectRange(selectionStart, selectionEnd);
  await value.session.selectRange(selectionEnd, selectionStart);
  assert.equal(value.calls.filter((entry) => entry === "save").length, 1);
  assert.equal(value.requests.filter((entry) => entry.operation === "editorSelectRangeV1").length, 2);
  await value.session.close();
});

test("a rejected checkpoint does not prevent the selection", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.commitText("仍可選取");
  value.document.save = async () => {
    value.calls.push("save-rejected");
    const error = new Error("checkpoint save failed");
    error.code = "SAVE_FAILED";
    throw error;
  };
  await value.session.selectRange(selectionStart, selectionEnd);
  assert.equal(value.calls.includes("save-rejected"), true);
  assert.equal(value.calls.includes("editorSelectRangeV1:state"), true);
  assert.equal(value.session._checkpointError.code, "SAVE_FAILED");
  // The gesture survives the failed checkpoint, but the host has to be able to
  // see that it failed: without this, "nothing to rescue" and "we tried to
  // protect your work and could not" are the same observable state, and the
  // recovery banner stays silent for the user who has most to lose
  // (SPEC-E1-C 4.1, v8).
  assert.equal(value.session.state.snapshot.checkpointError.code, "SAVE_FAILED");
  assert.equal(value.session.state.snapshot.hasCheckpoint, false);
  assert.equal(value.session.state.snapshot.state, "ready");
  await value.session.close();
});

test("a later successful checkpoint clears the reported failure", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.commitText("先失敗");
  const working = value.document.save;
  value.document.save = async () => {
    const error = new Error("checkpoint save failed");
    error.code = "SAVE_FAILED";
    throw error;
  };
  await value.session.selectRange(selectionStart, selectionEnd);
  assert.equal(value.session.state.snapshot.checkpointError.code, "SAVE_FAILED");

  value.document.save = working;
  await value.session.commitText("再成功");
  await value.session.selectRange(selectionStart, selectionEnd);
  assert.equal(value.session.state.snapshot.hasCheckpoint, true);
  // A stale failure left behind would make the banner warn about work that is
  // in fact protected -- the opposite error, and just as misleading.
  assert.equal(value.session.state.snapshot.checkpointError, null);
  await value.session.close();
});

test("a selection TIMEOUT enters recovery without saving after the timeout", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.commitText("逾時前保存");
  rejectSelectionReadback(value);
  await assert.rejects(
    () => value.session.selectRange(selectionStart, selectionEnd),
    { code: "TIMEOUT" },
  );
  const timedOutReadback = value.calls.lastIndexOf("editorGetStateV1:state");
  assert.equal(value.calls.filter((entry) => entry === "save").length, 1);
  assert.equal(value.calls.slice(timedOutReadback + 1).includes("save"), false);
  assert.equal(value.session.state.snapshot.state, "recoverable-error");
  await value.session.close();
});

test("restart reopens newer checkpoint bytes after a selection TIMEOUT", async () => {
  const value = fixture();
  const authorityBytes = new ArrayBuffer(16);
  new Uint8Array(authorityBytes)[0] = 17;
  await value.session.open({ bytes: authorityBytes });
  await value.session.commitText("保留的內容");
  rejectSelectionReadback(value);
  await assert.rejects(
    () => value.session.selectRange(selectionStart, selectionEnd),
    { code: "TIMEOUT" },
  );
  await value.session.restart();
  assert.equal(value.openedBytes.length, 2);
  assert.equal(value.openedBytes[0].byteLength, 16);
  assert.equal(value.openedBytes[1].byteLength, 24);
  assert.equal(new Uint8Array(value.openedBytes[1])[0], 0);
  assert.equal(value.session.state.snapshot.hasCheckpoint, true);
  await value.session.close();
});

test("a repeated post-recovery revision still creates a new checkpoint", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.commitText("第一世代");
  const restoreReadback = rejectSelectionReadback(value);
  await assert.rejects(
    () => value.session.selectRange(selectionStart, selectionEnd),
    { code: "TIMEOUT" },
  );
  await value.session.restart();
  restoreReadback();
  assert.equal(value.document.revision, 0);

  await value.session.commitText("第二世代");
  assert.equal(value.document.revision, 1);
  await value.session.selectRange(selectionStart, selectionEnd);
  assert.equal(value.calls.filter((entry) => entry === "save").length, 2);
  assert.equal(value.session.state.snapshot.checkpointRevision, 1);
  await value.session.close();
});

test("restart opens the newest bytes when Worker revisions restart", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.commitText("權威版本一");
  await value.session.commitText("權威版本二");
  value.document.save = async () => {
    const bytes = new ArrayBuffer(32);
    new Uint8Array(bytes)[0] = 51;
    return bytes;
  };
  await value.session.save();
  for (const listener of value.listeners) {
    listener({
      event: "worker-crashed",
      error: { code: "WORKER_CRASHED", message: "fixture crash" },
    });
  }
  await value.session.restart();
  assert.equal(value.document.revision, 0);
  assert.equal(new Uint8Array(value.openedBytes[1])[0], 51);

  await value.session.commitText("較新的檢查點");
  value.document.save = async () => {
    const bytes = new ArrayBuffer(24);
    new Uint8Array(bytes)[0] = 92;
    return bytes;
  };
  rejectSelectionReadback(value);
  await assert.rejects(
    () => value.session.selectRange(selectionStart, selectionEnd),
    { code: "TIMEOUT" },
  );
  await value.session.restart();
  assert.equal(value.openedBytes.length, 3);
  assert.equal(value.openedBytes[2].byteLength, 24);
  assert.equal(new Uint8Array(value.openedBytes[2])[0], 92);
  await value.session.close();
});

test("a successful save supersedes an older checkpoint for restart", async () => {
  const value = fixture();
  await value.session.open({ bytes: new ArrayBuffer(16) });
  await value.session.commitText("舊檢查點");
  await value.session.selectRange(selectionStart, selectionEnd);
  await value.session.commitText("更新權威版本");
  value.document.save = async () => {
    value.calls.push("save-authority");
    const bytes = new ArrayBuffer(32);
    new Uint8Array(bytes)[0] = 91;
    return bytes;
  };
  await value.session.save();
  assert.equal(value.session.state.snapshot.hasCheckpoint, false);
  assert.equal(value.session.state.snapshot.checkpointRevision, null);
  assert.equal(value.session.checkpointBytes(), null);
  for (const listener of value.listeners) {
    listener({
      event: "worker-crashed",
      error: { code: "WORKER_CRASHED", message: "fixture crash" },
    });
  }
  await value.session.restart();
  assert.equal(value.openedBytes[1].byteLength, 32);
  assert.equal(new Uint8Array(value.openedBytes[1])[0], 91);
  await value.session.close();
});

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
