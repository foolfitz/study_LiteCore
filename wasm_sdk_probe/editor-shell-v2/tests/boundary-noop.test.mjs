// SPEC-M3-link-batch 10.5 (ruling 2 condition 8; ruling 4 condition 35): C's
// second exit reaches the shell client as `verified-boundary-noop`, and the
// client's completion whitelist accepts it for the two caret-relative deletes
// ONLY with `changed === false` and an unchanged revision.
//
// Red cases in M1-3's shape (narrow-editor-v2-session.test.mjs): the same
// completion with `changed: true`, or with an advanced revision, must be
// EDITOR_RESULT_INVALID -- a "nothing changed" completion whose document
// claims say otherwise is exactly the plausible wrong answer the whitelist
// exists to refuse.  And the completion is accepted for NO other action: a
// movement, a format, a break or delete-selection answering with it is a
// malformed reply.
//
// Also here: `offersPageRectangles()`, the offers-style gate of 10.8 (S-11),
// read from the contract field like `offersRedo()` and never from the action
// map, because `page-rectangles` is not an action.

import assert from "node:assert/strict";
import test from "node:test";

import { NarrowEditorV2Client } from "../narrow-editor-v2-client.js";

const V2_MANIFEST = { capabilities: ["narrow-editor-v2"],
                      editorContract: { version: 2 } };

function handleFor(reply, manifest = V2_MANIFEST) {
  const issued = [];
  return {
    handle: 1,
    revision: 3,
    issued,
    _assertUsable() {},
    _engine: {
      manifest,
      async _request(operation, payload, options) {
        issued.push({ operation, payload: { ...payload }, options });
        return reply(payload);
      },
    },
  };
}

const noop = (overrides = {}) => (payload) => ({
  action: payload.action,
  beforeRevision: payload.expectedRevision,
  revision: payload.expectedRevision,
  changed: false,
  completion: "verified-boundary-noop",
  boundaryNoop: { waitedMs: 2251 },
  state: {},
  ...overrides,
});

const DELETES = ["delete-backward", "delete-forward"];

for (const action of DELETES) {
  test(`${action}: verified-boundary-noop with changed false and the revision unchanged is accepted`,
       async () => {
         const handle = handleFor(noop());
         const client = new NarrowEditorV2Client(handle);
         const result = await client.action(action);
         assert.equal(result.completion, "verified-boundary-noop");
         assert.equal(result.changed, false);
         assert.equal(result.revision, 3);
         assert.equal(handle.revision, 3, "the handle's revision must not move");
         assert.equal(result.boundaryNoop.waitedMs, 2251);
       });

  // M1-3's shape: the same completion, one document claim wrong at a time.
  for (const [label, overrides] of [
    ["changed true", { changed: true }],
    ["revision advanced", { revision: 4 }],
    ["changed true and revision advanced", { changed: true, revision: 4 }],
    ["changed null", { changed: null }],
    ["changed missing", { changed: undefined }],
    ["revision regressed", { revision: 2 }],
    ["beforeRevision wrong", { beforeRevision: 99 }],
  ]) {
    test(`${action}: verified-boundary-noop with ${label} is EDITOR_RESULT_INVALID`, async () => {
      const handle = handleFor(noop(overrides));
      const client = new NarrowEditorV2Client(handle);
      await assert.rejects(() => client.action(action),
                           (error) => error.code === "EDITOR_RESULT_INVALID");
      assert.equal(handle.revision, 3, "a rejected reply must not move the revision");
    });
  }
}

for (const action of ["move-character-left", "move-character-right", "move-line-up",
                      "move-line-end", "insert-paragraph-break", "insert-line-break",
                      "set-bold", "delete-selection"]) {
  test(`${action}: verified-boundary-noop is not a completion of this action`, async () => {
    const options = action === "set-bold" ? { enabled: true } : {};
    const handle = handleFor(noop());
    const client = new NarrowEditorV2Client(handle);
    await assert.rejects(() => client.action(action, options),
                         (error) => error.code === "EDITOR_RESULT_INVALID");
  });
}

test("the existing delete completions are still accepted beside the new one", async () => {
  for (const [completion, extra] of [
    ["verified-selection-delete", {}],
    ["verified-key-undo", { keyUndo: { comment: "", actionsAfter: 1 } }],
  ]) {
    const handle = handleFor((payload) => ({
      action: payload.action, beforeRevision: 3, revision: 4, changed: true,
      completion, state: {}, ...extra }));
    const result = await new NarrowEditorV2Client(handle).action("delete-backward");
    assert.equal(result.completion, completion);
    assert.equal(handle.revision, 4);
  }
});

// ---------------------------------------------------- offersPageRectangles

const clientWith = (contract) => new NarrowEditorV2Client({
  _assertUsable() {},
  _engine: { manifest: contract === undefined ? {} : { editorContract: contract } },
});

test("offersPageRectangles reads the contract field, not the action map", () => {
  const v20 = clientWith({ version: 2, actions: {},
                           pageRectangles: "document-sdk-page-rectangles" });
  assert.equal(v20.offersPageRectangles(), true);
  // It is not an action, so the action map must not claim it either way.
  assert.equal(v20.offers("page-rectangles"), false);
});

for (const [label, contract] of [
  ["a v19-shaped contract", { version: 2, redo: "document-sdk-redo",
                              actions: { "move-character-left": { id: 1, gestures: ["collapsed"] } } }],
  ["the field with another value", { version: 2, pageRectangles: "page-rectangles" }],
  ["the field as a boolean", { version: 2, pageRectangles: true }],
  ["no contract at all", undefined],
]) {
  test(`offersPageRectangles is false for ${label}`, () => {
    const client = clientWith(contract);
    assert.equal(client.offersPageRectangles(), false);
  });
}
