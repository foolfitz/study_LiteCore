import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";

const V2 = JSON.parse(readFileSync(fileURLToPath(new URL("../../dist/profiles/e2-editor-v2/sdk-manifest.json", import.meta.url)), "utf8"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
function state(revision) {
  return { documentHandle: 1, revision, caret: null, selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
           selectionType: "none", selectionTextMissing: false, selectionText: "", format: { bold: false, italic: false } };
}
function fixture(delay = 20) {
  const calls = []; let revision = 0;
  const document = { handle: 1, revision: 0, widthTwips: 1000, heightTwips: 2000, _assertUsable() {},
    async render() { return { pixels: new ArrayBuffer(4), revision }; },
    async save() { return new ArrayBuffer(16); },
    async insertText(text) { calls.push(`insert ${text}`); await sleep(delay); document.revision = ++revision; return { revision, state: state(revision) }; },
    async getSelection() { return { text: "", selectionType: "text", revision }; },
    async close() {} };
  const engine = { manifest: V2, onEvent() { return () => {}; },
    async open() { return document; },
    async _request(operation, payload) {
      if (operation === "editorGetStateV2") return state(revision);
      calls.push(`action ${payload.action}`); await sleep(5); document.revision = ++revision;
      return { action: payload.action, beforeRevision: payload.expectedRevision, revision, changed: true,
               completion: "verified-selection-delete", state: state(revision) }; },
    dispose() {} };
  document._engine = engine;
  const session = new NarrowEditorV2Session({ engineFactory: async () => engine, secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } } });
  return { calls, session };
}
async function opened() { const f = fixture(); await f.session.open({ bytes: new ArrayBuffer(8), name: "d.odt" }); return f; }

test("typed X, Y, then Delete at once: Delete waits for Y", async () => {
  const { calls, session } = await opened();
  const x = session.input.commitText("X"), y = session.input.commitText("Y");
  const del = session.action("delete-backward");
  await Promise.all([x, y, del]);
  assert.deepEqual(calls, ["insert X", "insert Y", "action delete-backward"]);
});
test("X, Y, Delete, Z: Z after the Delete", async () => {
  const { calls, session } = await opened();
  const x = session.input.commitText("X"), y = session.input.commitText("Y");
  const del = session.action("delete-backward");
  const z = session.input.commitText("Z");
  await Promise.all([x, y, del, z]);
  assert.deepEqual(calls, ["insert X", "insert Y", "action delete-backward", "insert Z"]);
});
test("two keys in a row keep their order", async () => {
  const { calls, session } = await opened();
  const x = session.input.commitText("X"), y = session.input.commitText("Y");
  const a = session.action("delete-backward"), b = session.action("delete-forward");
  await Promise.all([x, y, a, b]);
  assert.deepEqual(calls, ["insert X", "insert Y", "action delete-backward", "action delete-forward"]);
});
test("nothing typed: the key goes straight in", async () => {
  const { calls, session } = await opened();
  await session.action("delete-backward");
  assert.deepEqual(calls, ["action delete-backward"]);
});
test("typed text cancelled: the key still runs (idle backstop)", async () => {
  const { calls, session } = await opened();
  const x = session.input.commitText("X"), y = session.input.commitText("Y").catch((e) => e.code);
  const del = session.action("delete-backward");
  session.input.invalidate("test");
  assert.equal(await y, "INPUT_CANCELLED");
  await Promise.all([x, del]);
  assert.deepEqual(calls, ["insert X", "action delete-backward"]);
});
