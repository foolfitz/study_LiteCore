// SPEC-P-key-burst: typed text that waits in the adapter merges into the
// waiting entry; any other operation seals it.  The adapter is the real one
// (E1-C's, unchanged); the session is the product's.
import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorV2Session, coalesceTypedText } from "../narrow-editor-v2-session.js";
import { HostInputAdapter } from "../../input/input-adapter.js";

const V2_MANIFEST = JSON.parse(readFileSync(
  fileURLToPath(new URL("../../dist/profiles/e2-editor-v2/sdk-manifest.json", import.meta.url)), "utf8"));
const TYPED = { source: "beforeinput", inputType: "insertText", isTrusted: true };
const BREAK = { source: "beforeinput", inputType: "insertParagraph", isTrusted: true };

function editorState(revision) {
  return { documentHandle: 1, revision, caret: null,
           selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
           selectionType: "none", selectionTextMissing: false, selectionText: "",
           format: { bold: false, italic: false } };
}

/** The finding-111 engine (narrow-editor-v2-session.test.mjs `typing`), with a failing insert on request. */
function typing({ delay = 20, failOn = null } = {}) {
  const calls = [];
  let revision = 0;
  const document = {
    handle: 1, revision: 0, widthTwips: 1000, heightTwips: 2000, _assertUsable() {},
    async render() { return { pixels: new ArrayBuffer(4), revision }; },
    async save() { calls.push("save"); return new ArrayBuffer(16); },
    async insertText(text) {
      calls.push(`insert ${text}`);
      await new Promise((resolve) => setTimeout(resolve, delay));
      if (text === failOn) throw Object.assign(new Error("refused"), { code: "EDITOR_X" });
      document.revision = ++revision;
      return { revision, state: editorState(revision) };
    },
    async getSelection() { return { text: "", selectionType: "text", revision }; },
    async close() {},
  };
  const engine = {
    manifest: V2_MANIFEST,
    onEvent() { return () => {}; },
    async open() { return document; },
    async _request(operation, payload) {
      if (operation === "editorGetStateV2") return editorState(revision);
      calls.push(`action ${payload.action}`);
      await new Promise((resolve) => setTimeout(resolve, 5));
      document.revision = ++revision;
      return { action: payload.action, beforeRevision: payload.expectedRevision, revision, changed: true,
               completion: "verified-selection-delete", state: editorState(revision) };
    },
    dispose() {},
  };
  document._engine = engine;
  const session = new NarrowEditorV2Session({
    engineFactory: async () => engine, secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } },
  });
  return { calls, session };
}

async function typed(options) {
  const f = typing(options);
  await f.session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  return f;
}

const type = (session, text, metadata = TYPED) => [...text].map((ch) => session.input.commitText(ch, metadata));

test("the seam: the session's own adapter is the coalescing one, and its fields are where this reads them", async () => {
  const { session } = await typed();
  assert.equal(session.typedBurst, coalesceTypedText(session.input));
  assert.ok(Array.isArray(session.input._queue));
  for (const field of ["_requestCount", "_generation", "_maxUtf8Bytes"])
    assert.equal(typeof session.input[field], "number", field);
  assert.equal(typeof session.input._trace, "function");
});

test("a burst of forty: none refused, two inserts, every character once and in order", async () => {
  const { calls, session } = await typed();
  const text = "abcdefghijklmnopqrstuvwxyz0123456789 xyz";
  const results = await Promise.allSettled(type(session, text));
  assert.deepEqual(results.filter((r) => r.status === "rejected"), []);
  assert.deepEqual(calls, [`insert ${text[0]}`, `insert ${text.slice(1)}`]);
  assert.equal(session.typedBurst.record.merged, text.length - 2);
});

test("without the merge the same burst loses everything past eight (the red the spec measures)", async () => {
  const f = typing();
  await f.session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  const bare = new HostInputAdapter({ commit: (t, metadata) => f.session.commitText(t, { metadata }) });
  const results = await Promise.allSettled([..."abcdefghijkl"].map((ch) => bare.commitText(ch, TYPED)));
  assert.equal(results.filter((r) => r.reason?.code === "INPUT_BACKPRESSURE").length, 4);
});

test("a key seals: abc, Backspace, de -- the delete lands after c and before d", async () => {
  const { calls, session } = await typed();
  const before = type(session, "abc");
  const del = session.action("delete-backward");
  const after = type(session, "de");
  await Promise.all([...before, del, ...after]);
  assert.deepEqual(calls, ["insert a", "insert bc", "action delete-backward", "insert de"]);
});

test("save seals as well: x in flight, yz waiting, save, w", async () => {
  const { calls, session } = await typed();
  const first = type(session, "xyz");
  const saved = session.save();
  const last = type(session, "w");
  await Promise.all([...first, saved, ...last]);
  assert.deepEqual(calls, ["insert x", "insert yz", "save", "insert w"]);
});

test("line breaks, IME commits and pastes keep one entry each", async () => {
  const { calls, session } = await typed();
  // Two bursts: entries that do not merge still count against the limit of eight (spec 2.5).
  await Promise.all([
    ...type(session, "ab"),
    session.input.commitText("\n", BREAK),
    ...type(session, "cd"),
    session.input.commitText("中文", { source: "composition", compositionId: 1, isTrusted: true }),
    ...type(session, "e"),
  ]);
  await Promise.all([
    session.input.commitClipboardText("PASTE"),
    ...type(session, "f"),
    session.input.commitText("g", { source: "beforeinput", inputType: "insertReplacementText" }),
    ...type(session, "h"),
  ]);
  assert.deepEqual(calls, ["insert a", "insert b", "insert \n", "insert cd", "insert 中文", "insert e",
                           "insert PASTE", "insert f", "insert g", "insert h"]);
});

test("the byte limit: a merge that would pass it starts a new entry", async () => {
  const { calls, session } = await typed();
  session.input._maxUtf8Bytes = 4;
  await Promise.all(type(session, "abcdefgh"));
  assert.deepEqual(calls, ["insert a", "insert bcde", "insert fgh"]);
});

test("a cancelled entry cancels every character merged into it", async () => {
  const { calls, session } = await typed();
  const results = type(session, "abcd").map((p) => p.then(() => "ok", (error) => error.code));
  session.input.invalidate("test");
  assert.deepEqual(await Promise.all(results), ["ok", "INPUT_CANCELLED", "INPUT_CANCELLED", "INPUT_CANCELLED"]);
  assert.deepEqual(calls, ["insert a"]);
});

test("a failed entry fails every character merged into it, and the next burst still merges", async () => {
  const { calls, session } = await typed({ failOn: "bcd" });
  const results = type(session, "abcd").map((p) => p.then(() => "ok", (error) => error.code));
  const outcome = await Promise.all(results);
  assert.equal(outcome[0], "ok");
  assert.deepEqual(outcome.slice(1).every((code) => code === outcome[1] && code !== "ok"), true);
  assert.deepEqual(calls.slice(0, 2), ["insert a", "insert bcd"]);
});

test("a blocked adapter merges nothing", async () => {
  const { session } = await typed();
  const first = type(session, "ab").map((p) => p.catch((error) => error.code));
  session.input.setBlocked(true, "test");
  const more = await session.input.commitText("c", TYPED).catch((error) => error.code);
  assert.equal(more, "INPUT_BLOCKED");
  await Promise.all(first);
});

test("held behind typed text, a key's barrier still counts entries: X, YZ waiting, Delete, then W", async () => {
  const { calls, session } = await typed({ delay: 30 });
  const x = type(session, "XYZ");
  const del = session.action("delete-backward");
  const w = type(session, "W");
  assert.equal(session.input.state.requestCount, 3);
  await Promise.all([...x, del, ...w]);
  assert.deepEqual(calls, ["insert X", "insert YZ", "action delete-backward", "insert W"]);
});
