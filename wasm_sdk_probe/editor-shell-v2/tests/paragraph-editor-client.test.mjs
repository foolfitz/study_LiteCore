import assert from "node:assert/strict";
import test from "node:test";

import {
  ParagraphEditorClient,
  EDITOR_V2_PARAGRAPH_ACTIONS,
  formatFailureDisposition,
} from "../paragraph-editor-client.js";

function fixture(overrides = {}) {
  const requests = [];
  const engine = {
    manifest: {
      profile: "e2-editor-v2",
      capabilities: ["narrow-editor-v2"],
      editorContract: {
        version: 2,
        actions: {
          "set-list-unordered": { id: 12, gestures: ["collapsed", "range-single"], limits: [] },
          "set-paragraph-heading": { id: 14, gestures: ["collapsed"], limits: ["heading-level-1-only"] },
        },
        ...overrides.contract,
      },
      ...overrides.manifest,
    },
    async _request(operation, payload) {
      requests.push({ operation, payload });
      return {
        action: payload.action,
        beforeRevision: payload.expectedRevision,
        revision: payload.expectedRevision + 1,
        changed: null,
        completion: "verified-format-readback",
        ...overrides.result,
      };
    },
  };
  const document = { handle: 7, revision: 3, _engine: engine, _assertUsable() {} };
  return { document, requests, client: new ParagraphEditorClient(document) };
}

test("a v1 profile is refused", async () => {
  const { client } = fixture({ manifest: { capabilities: ["narrow-editor-v1"] } });
  await assert.rejects(() => client.action("set-list-unordered"),
                       (e) => e.code === "UNSUPPORTED_OPERATION");
});

test("contract version 1 is refused even with the v2 capability", async () => {
  const { client } = fixture({ contract: { version: 1 } });
  await assert.rejects(() => client.action("set-list-unordered"),
                       (e) => e.code === "UNSUPPORTED_OPERATION");
});

test("the five paragraph actions dispatch on editorActionV2", async () => {
  for (const action of EDITOR_V2_PARAGRAPH_ACTIONS) {
    const { client, requests } = fixture();
    await client.action(action);
    assert.equal(requests[0].operation, "editorActionV2");
    assert.equal(requests[0].payload.action, action);
    assert.equal(requests[0].payload.extendSelection, false);
    assert.equal(requests[0].payload.enabled, false);
  }
});

test("a v1 action name is refused", async () => {
  const { client } = fixture();
  await assert.rejects(() => client.action("set-bold"),
                       (e) => e.code === "EDITOR_ACTION_UNSUPPORTED");
});

test("neither option flag may be supplied", async () => {
  for (const options of [{ extendSelection: true }, { extendSelection: false },
                         { enabled: true }, { enabled: false }]) {
    const { client } = fixture();
    await assert.rejects(() => client.action("set-list-unordered", options),
                         (e) => e.code === "INVALID_ARGUMENT");
  }
});

test("revision advances by exactly one and changed stays null", async () => {
  const { client, document } = fixture();
  const result = await client.action("set-list-unordered");
  assert.equal(result.changed, null);
  assert.equal(document.revision, 4);
});

test("a v1-shaped success is rejected, not silently accepted", async () => {
  // The whole point of 5.6 being per-action: this is what a delete result
  // looks like, and it must not satisfy a paragraph action.
  const { client } = fixture({ result: { changed: true, completion: "uno-command-result" } });
  await assert.rejects(() => client.action("set-list-unordered"),
                       (e) => e.code === "EDITOR_RESULT_INVALID");
});

test("a revision that does not advance is rejected", async () => {
  const { client } = fixture({ result: { revision: 3 } });
  await assert.rejects(() => client.action("set-list-unordered"),
                       (e) => e.code === "EDITOR_RESULT_INVALID");
});

test("gestures and limits are read from the manifest", () => {
  const { client } = fixture();
  assert.deepEqual(client.gesturesFor("set-list-unordered"), ["collapsed", "range-single"]);
  assert.deepEqual(client.limitsFor("set-paragraph-heading"), ["heading-level-1-only"]);
  assert.equal(client.gesturesFor("set-list-none"), null);
});

test("failure disposition turns on whether anything was dispatched", () => {
  assert.equal(formatFailureDisposition({ details: { formatBarrier: { dispatched: false } } }),
               "refused-no-mutation");
  assert.equal(formatFailureDisposition({ details: { formatBarrier: { dispatched: true } } }),
               "dispatched-rollback");
  // No barrier forwarded: fail closed. A needless rollback costs one action;
  // a missed one costs a document the host believes is clean.
  assert.equal(formatFailureDisposition({ code: "MUTATION_OUTCOME_UNKNOWN" }),
               "unknown-rollback");
});

test("a failure that never reached the engine does not roll the document back",
     async () => {
       // SPEC E2-C 2.5.  Fail-closed is for "we do not know whether it was
       // dispatched".  These three are known: they are raised before the
       // request is accepted, so there is nothing to roll back, and rolling
       // back would discard everything since the last checkpoint because a
       // caller passed a bad argument.
       for (const code of ["INVALID_ARGUMENT", "EDITOR_ACTION_UNSUPPORTED",
                           "UNSUPPORTED_OPERATION"]) {
         assert.equal(formatFailureDisposition({ code }), "refused-no-mutation",
                      `${code} must not be treated as possibly-dispatched`);
       }
       // And the errors the client itself throws must classify the same way --
       // testing the constant list alone would pass even if the client raised
       // something else entirely.
       const { client } = fixture();
       for (const call of [() => client.setList("bulleted"),
                           () => client.action("set-underline"),
                           () => client.action("set-list-none",
                                               { enabled: true })]) {
         const error = await call().then(() => null, (e) => e);
         assert.ok(error, "the call was expected to fail");
         assert.equal(formatFailureDisposition(error), "refused-no-mutation");
       }
     });

test("a barrier saying it was dispatched still wins over the code", () => {
  // The code list is a fallback for errors with no barrier, not an override.
  assert.equal(
    formatFailureDisposition({ code: "INVALID_ARGUMENT",
                               details: { formatBarrier: { dispatched: true } } }),
    "dispatched-rollback");
});

test("setList and setParagraphStyle reject anything outside the closed set", async () => {
  const { client } = fixture();
  await assert.rejects(() => client.setList("bulleted"), (e) => e.code === "INVALID_ARGUMENT");
  await assert.rejects(() => client.setParagraphStyle("h2"), (e) => e.code === "INVALID_ARGUMENT");
});
