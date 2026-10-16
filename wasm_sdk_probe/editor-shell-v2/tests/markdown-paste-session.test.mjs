// SPEC-M3-link-batch-v21 4.2 / 10.1 / 10.3 / 10.4 / 11.2 M9, M11: the session's
// half of the Markdown paste and the enqueue seam the page's held deletes read.
//
//   * 10.4: every pre-dispatch refusal disposes as `recovery: "none"` -- the
//     list is held to the ENGINE's own (`kPreDispatchCodes` in
//     src/markdown_paste.hpp, read here: form two, a code added there and not
//     here turns this red), and `dispatched: false` alone says it too;
//   * 10.1: the work is banked BEFORE the paste is dispatched, and a failed
//     checkpoint refuses the paste (MARKDOWN_CHECKPOINT_FAILED, nothing sent);
//     M9's dirty arm: a paste the engine cannot verify goes back to THAT
//     checkpoint, so a marker typed and not saved survives the rollback;
//   * M11: a paste is a mutation -- `dirty` afterwards, so autosave arms;
//   * 10.3: `enqueueCount` counts every enqueue path and `beforeEnqueue` runs
//     before the new item is pushed.
//
// The fixture is narrow-editor-v2-session.test.mjs's shape: the real session,
// the real client, an engine and document that answer like the worker.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";
import { recoveryFor } from "../paragraph-editor-session.js";
import { MARKDOWN_PRE_DISPATCH_CODES, formatFailureDisposition } from "../paragraph-editor-client.js";

const read = (relative) => readFileSync(fileURLToPath(new URL(relative, import.meta.url)), "utf8");
const V20 = JSON.parse(read("../../dist/profiles/e2-editor-v20/sdk-manifest.json"));
const V21 = structuredClone(V20);
V21.editorContract.pasteMarkdown = "document-sdk-paste-markdown";

/** The engine's pre-dispatch codes as src/markdown_paste.hpp lists them, and its post-dispatch one. */
function headerCodes() {
  let source;
  try {
    source = read("../../src/markdown_paste.hpp");
  } catch (error) {
    if (error.code === "ENOENT") assert.fail("src/markdown_paste.hpp is not there: the list this test holds the "
                                             + "session to does not exist yet (part E, step 2)");
    throw error;
  }
  const names = new Map([...source.matchAll(/constexpr const char \*(k\w+) = "([A-Z_]+)";/g)]
    .map((m) => [m[1], m[2]]));
  const list = source.match(/kPreDispatchCodes\[\] = \{([\s\S]*?)\};/);
  assert.ok(list, "kPreDispatchCodes is not in src/markdown_paste.hpp where this test reads it");
  const pre = [...list[1].matchAll(/\b(k\w+)\b/g)].map((m) => {
    assert.ok(names.has(m[1]), `${m[1]} has no string in the header`);
    return names.get(m[1]);
  });
  return { pre, post: names.get("kCodeOutcomeUnknown") };
}

function fixture({ manifest = V21, paste = null, saveFails = false } = {}) {
  const calls = [];
  const opened = [];
  let revision = 0;
  let saves = 0;
  let engines = 0;
  const state = () => ({ documentHandle: 1, revision, sourceSequence: revision, caret: null,
                         selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
                         selectionType: "none", selectionTextMissing: false, selectionText: "",
                         format: { bold: false, italic: false } });
  const makeEngine = () => {
    engines += 1;
    const document = {
      handle: 1, revision: 0, widthTwips: 1000, heightTwips: 2000,
      _assertUsable() {},
      async render() { return { pixels: new ArrayBuffer(4), revision }; },
      async insertText(text) { calls.push(`insertText:${text}`); document.revision = ++revision; return { revision }; },
      async save() {
        calls.push("save");
        if (saveFails) throw Object.assign(new Error("save failed"), { code: "TIMEOUT" });
        saves += 1;
        return Uint8Array.of(saves).buffer;      // which save made these bytes
      },
      async pasteMarkdown(text) {
        calls.push(`pasteMarkdown:${text}`);
        if (paste) {
          const outcome = paste(text);
          if (outcome instanceof Error) throw outcome;
        }
        document.revision = ++revision;
        return { revision };
      },
      async undo() { calls.push("undo"); document.revision = ++revision; return { revision }; },
      async redo() { calls.push("redo"); document.revision = ++revision; return { revision }; },
      async click() { calls.push("click"); },
      async close() {},
    };
    const engine = {
      manifest,
      onEvent() { return () => {}; },
      async open(bytes) { opened.push([...new Uint8Array(bytes)]); revision = 0; document.revision = 0; return document; },
      async _request(operation, payload) {
        if (operation === "editorGetStateV2") return state();
        if (operation === "editorSelectRangeV2") { calls.push("selectRange"); return { revision, state: state() }; }
        if (operation === "editorPlaceCaretV2") { calls.push("placeCaret"); return { revision, completion: "verified-caret-readback", state: state() }; }
        calls.push(`${operation}:${payload.action}`);
        return { action: payload.action, beforeRevision: payload.expectedRevision, revision,
                 changed: false, completion: "documented-callback-visible-cursor", state: state() };
      },
      dispose() {},
    };
    document._engine = engine;
    return engine;
  };
  const labels = [];
  const session = new NarrowEditorV2Session({
    engineFactory: async () => makeEngine(),
    secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } },
    beforeEnqueue: (label) => labels.push(label),
  });
  return { session, calls, opened, labels, engines: () => engines };
}

async function opened(options) {
  const f = fixture(options);
  await f.session.open({ bytes: Uint8Array.of(0).buffer, name: "d.odt" });
  return f;
}

const refusal = (code, extra = {}) =>
  Object.assign(new Error(code), { code, details: { operation: "paste-markdown", dispatched: false, ...extra } });

// ------------------------------------------------------------------ 10.4

test("10.4: every code in the engine's kPreDispatchCodes disposes as none, by the code alone", () => {
  const { pre, post } = headerCodes();
  assert.ok(pre.length >= 6, `the header lists ${pre.length} pre-dispatch codes; the interface has six refusals`);
  for (const code of pre) {
    // No `dispatched` field: this is the list itself being checked, not the flag.
    assert.equal(formatFailureDisposition({ code }), "refused-no-mutation", code);
    assert.equal(recoveryFor({ code }), "none", code);
  }
  assert.equal(post, "MUTATION_OUTCOME_UNKNOWN");
  assert.equal(recoveryFor({ code: post }), "rollback", "the one post-dispatch code must keep its rollback");
});

test("10.4: the interface's five named codes and the session's own are pre-dispatch", () => {
  for (const code of ["INVALID_ARGUMENT", "MARKDOWN_ENCODING_UNSUPPORTED", "MARKDOWN_NEEDS_CARET",
                      "MARKDOWN_REMOTE_IMAGE", "MARKDOWN_HTML_UNSUPPORTED", "MARKDOWN_CHECKPOINT_FAILED"]) {
    assert.equal(recoveryFor({ code }), "none", code);
  }
  assert.ok(MARKDOWN_PRE_DISPATCH_CODES.every((code) => code.startsWith("MARKDOWN_")));
});

test("10.4: `dispatched: false` alone says none, whatever the code; a barrier's own answer still wins", () => {
  assert.equal(recoveryFor({ code: "SOME_FUTURE_REFUSAL", details: { dispatched: false } }), "none");
  assert.equal(recoveryFor({ code: "SOME_FUTURE_REFUSAL", details: { dispatched: true } }), "rollback");
  assert.equal(recoveryFor({ code: "SOME_FUTURE_REFUSAL" }), "rollback", "unknown and unsaid stays fail-closed");
  assert.equal(recoveryFor({ code: "MUTATION_OUTCOME_UNKNOWN",
                             details: { dispatched: false, formatBarrier: { dispatched: true } } }), "rollback",
               "a barrier that says dispatched outranks a bare flag");
});

// ------------------------------------------------------------------ M11, M8

test("M11: a paste is a mutation -- dirty afterwards (autosave's trigger), the revision up by one", async () => {
  const { session, calls } = await opened();
  assert.equal(session.state.snapshot.dirty, false);
  const result = await session.pasteMarkdown("# 標題");
  assert.equal(result.revision, 1);
  assert.equal(session.state.snapshot.dirty, true);
  assert.equal(session.state.snapshot.revision, 1);
  assert.deepEqual(calls, ["pasteMarkdown:# 標題"], "a clean document has nothing to bank before the paste");
});

test("M8 (session): offersPasteMarkdown reads the contract -- false on the real v20 manifest, true when declared", async () => {
  assert.equal((await opened({ manifest: V20 })).session.offersPasteMarkdown(), false);
  assert.equal((await opened({ manifest: V21 })).session.offersPasteMarkdown(), true);
  assert.equal(fixture().session.offersPasteMarkdown(), false, "before open there is nothing to offer");
  // The mutation flag the page's controls read: fail-closed, the paste changes the document.
  assert.equal(fixture().session.actionMutates("paste-markdown"), true);
});

// ------------------------------------------------------------------ 10.1, M9

test("10.1: on a dirty document the work is banked BEFORE the paste is dispatched", async () => {
  const { session, calls } = await opened();
  await session.commitText("X");
  await session.pasteMarkdown("**b**");
  assert.deepEqual(calls, ["insertText:X", "save", "pasteMarkdown:**b**"]);
  assert.equal(session.state.snapshot.hasCheckpoint, true);
});

test("10.1 / M9: a checkpoint that cannot be written refuses the paste -- MARKDOWN_CHECKPOINT_FAILED, nothing sent", async () => {
  const { session, calls } = await opened({ saveFails: true });
  await session.commitText("X");
  await assert.rejects(() => session.pasteMarkdown("**b**"), (error) => {
    assert.equal(error.code, "MARKDOWN_CHECKPOINT_FAILED");
    assert.equal(error.details.dispatched, false);
    assert.equal(error.recovery, "none");
    return true;
  });
  assert.deepEqual(calls, ["insertText:X", "save"], "the paste went out over a failed checkpoint");
  assert.equal(session.state.snapshot.state, "ready", "a refusal that changed nothing blocked the queue");
  assert.equal(session.state.snapshot.revision, 1);
});

test("M9 (dirty arm): a paste the engine cannot verify rolls back to the checkpoint taken just before it -- the unsaved marker survives", async () => {
  const unknown = Object.assign(new Error("unverified"), {
    code: "MUTATION_OUTCOME_UNKNOWN", details: { operation: "paste-markdown", dispatched: true } });
  const { session, calls, opened: reopened } = await opened({ paste: () => unknown });
  await session.commitText("X");                         // typed, not saved
  await assert.rejects(() => session.pasteMarkdown("**b**"), (error) => {
    assert.equal(error.code, "MUTATION_OUTCOME_UNKNOWN");
    assert.equal(error.recovery, "rollback");
    return true;
  });
  assert.equal(session.state.snapshot.state, "recoverable-error");
  assert.equal(session.restartKeepsContent(), true, "the reopen would not bring back the typed marker");
  await session.rollback();
  assert.equal(session.state.snapshot.state, "ready");
  // Reopened from save #1 -- the checkpoint banked after "X" and before the paste.
  assert.deepEqual(reopened.at(-1), [1]);
  assert.deepEqual(calls.slice(0, 3), ["insertText:X", "save", "pasteMarkdown:**b**"]);
});

test("M9 (clean arm): with nothing typed, the rollback reopens the opened bytes and nothing is banked", async () => {
  const unknown = Object.assign(new Error("unverified"), { code: "MUTATION_OUTCOME_UNKNOWN",
                                                          details: { dispatched: true } });
  const { session, calls, opened: reopened } = await opened({ paste: () => unknown });
  await assert.rejects(() => session.pasteMarkdown("# a"));
  assert.equal(session.state.snapshot.state, "recoverable-error");
  await session.rollback();
  assert.deepEqual(reopened.at(-1), [0], "not the bytes it was opened from");
  assert.equal(calls.includes("save"), false);
});

for (const code of ["INVALID_ARGUMENT", "MARKDOWN_ENCODING_UNSUPPORTED", "MARKDOWN_NEEDS_CARET",
                    "MARKDOWN_REMOTE_IMAGE", "MARKDOWN_HTML_UNSUPPORTED", "MARKDOWN_UNDO_UNREADABLE"]) {
  test(`M3 (session): the engine's pre-dispatch ${code} -- recovery none, the queue open, nothing marked dirty`, async () => {
    const { session } = await opened({ paste: () => refusal(code) });
    await assert.rejects(() => session.pasteMarkdown("x"),
                         (error) => error.code === code && error.recovery === "none");
    assert.equal(session.state.snapshot.state, "ready");
    assert.equal(session.state.snapshot.dirty, false);
    assert.equal(session.state.snapshot.revision, 0);
  });
}

test("view-only: the paste is refused before it is queued, and not counted as enqueued", async () => {
  const { session, calls, labels } = await opened();
  session.setViewOnly(true);
  const before = session.enqueueCount;
  await assert.rejects(() => session.pasteMarkdown("# a"),
                       (error) => error.code === "EDITOR_VIEW_ONLY" && error.recovery === "none");
  assert.deepEqual(calls, []);
  assert.equal(session.enqueueCount, before);
  assert.equal(labels.includes("paste-markdown"), false);
});

// ------------------------------------------------------------------ 10.3

test("10.3: enqueueCount counts every enqueue path, and beforeEnqueue sees each label first", async () => {
  const { session, labels } = await opened();
  const paths = [
    ["commit-text", () => session.commitText("a")],
    ["action:move-line-end", () => session.action("move-line-end")],
    ["action:move-document-start", () => session.action("move-document-start")],
    ["place-caret", () => session.placeCaret(10, 10, { caretTimeoutMs: 50, caretAckGraceMs: 0 }).catch(() => {})],
    ["select-range", () => session.selectRange({ xTwips: 0, yTwips: 0 }, { xTwips: 5, yTwips: 5 })],
    ["undo", () => session.undo()],
    ["redo", () => session.redo()],
    ["save", () => session.save()],
    ["paste-markdown", () => session.pasteMarkdown("# a")],
  ];
  for (const [label, run] of paths) {
    const before = session.enqueueCount;
    await run();
    assert.equal(session.enqueueCount, before + 1, `${label} was not counted`);
    assert.equal(labels.at(-1), label);
  }
});

test("10.3 rule 4: what beforeEnqueue enqueues goes into the queue AHEAD of the item that called it", async () => {
  const order = [];
  let session = null;
  let releasing = false;
  const f = fixture();
  session = new NarrowEditorV2Session({
    engineFactory: async () => f.session._engineFactory(),
    secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } },
    // A host releasing one held item: it enqueues synchronously, from inside the hook.
    beforeEnqueue: (label) => {
      if (releasing || label !== "redo") return;
      releasing = true;
      void session._enqueue("released", async () => { order.push("released"); return {}; });
      releasing = false;
    },
  });
  await session.open({ bytes: Uint8Array.of(0).buffer, name: "d.odt" });
  const held = session._enqueue("blocker", () => new Promise((resolve) => setTimeout(() => {
    order.push("blocker"); resolve({});
  }, 20)));
  const redo = session._enqueue("redo", async () => { order.push("redo"); return {}; });
  await Promise.all([held, redo]);
  assert.deepEqual(order, ["blocker", "released", "redo"]);
  assert.equal(session.enqueueCount, 3);
});
