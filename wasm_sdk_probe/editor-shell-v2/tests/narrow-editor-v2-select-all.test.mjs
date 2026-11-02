// SPEC-M3-select-all-v26 5.2 (U1): select-all in the client and the session.
//
//   * the client accepts `select-all` with the "move" postcondition: revision
//     held, `changed: false`, a documented callback or the readback -- the two
//     completions measured on v25 (findings/evidence/select-all-v25/run-01);
//   * the session lets it through its own allowlist (review item 1: a second
//     copy of the list refused it before the queue) and queues it as a
//     NON-mutation (review item 2: otherwise Ctrl+A on an untouched document
//     marks it unsaved -- finding 098's shape -- and a read-only document
//     refuses it);
//   * a profile that withholds or omits it does not offer it.
//
// New exports are read through the module namespace, so on a client without
// them this file fails on its assertions rather than on an import.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import * as clientModule from "../narrow-editor-v2-client.js";
import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";

const { NarrowEditorV2Client, postconditionClassOf } = clientModule;
const read = (relative) => readFileSync(fileURLToPath(new URL(relative, import.meta.url)), "utf8");
const V20 = JSON.parse(read("../../dist/profiles/e2-editor-v20/sdk-manifest.json"));
const GRANT = { id: 21, gestures: ["collapsed", "range-single", "range-cross"], limits: [] };

// `null` = the action OMITTED from the manifest.  Not `undefined`: a default
// parameter would turn that back into GRANT (the first red witness did exactly
// that -- the omitted case was red for the wrong reason).
function manifest(selectAll) {
  const out = structuredClone(V20);
  if (selectAll === null) delete out.editorContract.actions["select-all"];
  else out.editorContract.actions["select-all"] = selectAll;
  return out;
}

// The two replies v25 gave (run-01): from a caret, and from a range or a blank document.
const REPLY = (completion, over = {}) => (payload) => ({
  action: payload.action, beforeRevision: payload.expectedRevision, revision: payload.expectedRevision,
  changed: false, completion, callbackSequenceBefore: 12, callbackSequenceAfter: 16,
  state: { selection: { observed: true, collapsed: false, rectangles: [{ x: 1418, y: 1418, width: 9000, height: 413 }] } },
  ...over,
});

function clientWith(reply, selectAll = GRANT) {
  const issued = [];
  const handle = {
    handle: 1, revision: 7, _assertUsable() {},
    _engine: { manifest: manifest(selectAll), async _request(operation, payload) {
      issued.push({ operation, payload });
      return reply(payload);
    } },
  };
  return { client: new NarrowEditorV2Client(handle), issued };
}

function sessionFixture(selectAll = GRANT) {
  const calls = [];
  let revision = 0;
  const state = () => ({ documentHandle: 1, revision, sourceSequence: revision, caret: null,
                         selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
                         selectionType: "none", selectionTextMissing: false, selectionText: "",
                         format: { bold: false, italic: false } });
  const makeEngine = () => {
    const document = {
      handle: 1, revision: 0, widthTwips: 1000, heightTwips: 2000, _assertUsable() {},
      async render() { return { pixels: new ArrayBuffer(4), revision }; },
      async save() { calls.push("save"); return Uint8Array.of(1).buffer; },
      async undo() { calls.push("undo"); document.revision = ++revision; return { revision }; },
      async close() {},
    };
    const engine = {
      manifest: manifest(selectAll),
      onEvent() { return () => {}; },
      async open() { revision = 0; document.revision = 0; return document; },
      async _request(operation, payload) {
        if (operation === "editorGetStateV2") return state();
        calls.push(`${operation}:${payload.action}`);
        return REPLY("documented-callback-visible-cursor")(payload);
      },
      dispose() {},
    };
    document._engine = engine;
    return engine;
  };
  const session = new NarrowEditorV2Session({
    engineFactory: async () => makeEngine(), secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } },
  });
  return { session, calls };
}

test("U1: select-all takes the move postcondition", () => {
  assert.equal(postconditionClassOf("select-all"), "move");
});

test("U1: the client exports the select-all list and the union it accepts", () => {
  assert.deepEqual(clientModule.EDITOR_SELECT_ALL_ACTIONS, ["select-all"]);
  assert.deepEqual(clientModule.EDITOR_ACCEPTED_ACTIONS,
                   [...clientModule.EDITOR_V4_ACTIONS, "select-all",
                    "set-align-left", "set-align-center", "set-align-right", "set-align-justify",
                    "toggle-heading-1", "toggle-heading-2", "toggle-heading-3", "toggle-heading-4",
                    "toggle-list-unordered", "toggle-list-ordered"]);
});

test("U1: the client sends select-all with both option flags false and the expected revision", async () => {
  for (const completion of ["documented-callback-visible-cursor", "verified-move-readback"]) {
    const { client, issued } = clientWith(REPLY(completion));
    const result = await client.action("select-all");
    assert.equal(result.completion, completion);
    assert.deepEqual(issued, [{ operation: "editorActionV2", payload: {
      documentHandle: 1, expectedRevision: 7, action: "select-all", extendSelection: false, enabled: false } }]);
  }
});

test("U1: a select-all reply that claims a document change is rejected", async () => {
  for (const over of [{ revision: 8 }, { changed: true }, { completion: "uno-command-result" }]) {
    const { client } = clientWith(REPLY("documented-callback-visible-cursor", over));
    await assert.rejects(() => client.action("select-all"),
                         (error) => error.code === "EDITOR_RESULT_INVALID", JSON.stringify(over));
  }
});

test("U1: offered only when the manifest grants it -- withheld and omitted both say no", () => {
  assert.equal(clientWith(REPLY("verified-move-readback"), GRANT).client.offers("select-all"), true);
  assert.equal(clientWith(REPLY("verified-move-readback"),
                          { id: 21, gestures: [], limits: [] }).client.offers("select-all"), false);
  assert.equal(clientWith(REPLY("verified-move-readback"), null).client.offers("select-all"), false);
});

test("U1: the session queues select-all, as a non-mutation, and the document stays clean", async () => {
  const { session, calls } = sessionFixture();
  await session.open({ bytes: Uint8Array.of(0).buffer, name: "d.odt" });
  const options = [];
  const enqueue = session._enqueue.bind(session);
  session._enqueue = (label, operation, opts) => { options.push([label, opts]); return enqueue(label, operation, opts); };
  await session.action("select-all");
  assert.ok(calls.includes("editorActionV2:select-all"), "select-all never reached the engine");
  assert.deepEqual(options.filter(([label]) => label === "action:select-all").map(([, o]) => o?.mutation), [false]);
  assert.equal(session.actionMutates("select-all"), false);
  assert.equal(session.hasUnsavedEdits(), false, "Ctrl+A marked an untouched document unsaved");
});

test("U1: a read-only session still selects all", async () => {
  const { session, calls } = sessionFixture();
  session.setViewOnly(true);
  await session.open({ bytes: Uint8Array.of(0).buffer, name: "d.odt" });
  await session.action("select-all");
  assert.ok(calls.includes("editorActionV2:select-all"), "read-only refused select-all");
});
