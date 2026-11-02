// SPEC-P-demo-batch-3 3.2: the client and the session accept what a v31 manifest offers, and a manifest without it offers nothing.
// Red first: Codex's review reproduced EDITOR_ACTION_UNSUPPORTED here on all four.
import assert from "node:assert/strict";
import test from "node:test";
import { EDITOR_ACCEPTED_ACTIONS, NarrowEditorV2Client, postconditionClassOf } from "../narrow-editor-v2-client.js";
import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";

const ALIGN = ["set-align-left", "set-align-center", "set-align-right", "set-align-justify"];

function client(actions) {
  const requests = [];
  const document = {
    revision: 7, handle: 1, _assertUsable() {},
    _engine: {
      manifest: {capabilities: ["narrow-editor-v2"], editorContract: {version: 2, abiVersion: 6, actions}},
      async _request(operation, payload) {
        requests.push({operation, ...payload});
        return {action: payload.action, beforeRevision: payload.expectedRevision, revision: payload.expectedRevision + 1,
                changed: null, completion: "verified-format-readback"};
      },
    },
  };
  return {requests, client: new NarrowEditorV2Client(document), document};
}

test("all four are accepted, classed as paragraph actions and reach the wire with both flags false", async () => {
  const actions = Object.fromEntries(ALIGN.map((name, i) => [name, {id: 24 + i, gestures: ["collapsed", "range-single", "range-cross"], limits: []}]));
  for (const action of ALIGN) {
    const {client: c, requests, document} = client(actions);
    assert.equal(c.offers(action), true);
    assert.ok(EDITOR_ACCEPTED_ACTIONS.includes(action));
    assert.equal(postconditionClassOf(action), "paragraph");
    assert.equal(NarrowEditorV2Session.isParagraphAction(action), true);
    await c.action(action);
    assert.deepEqual(requests.map(r => [r.operation, r.action, r.extendSelection, r.enabled]), [["editorActionV2", action, false, false]]);
    assert.equal(document.revision, 8);
  }
});

test("a manifest without them does not offer them", () => {
  const {client: c} = client({"set-bold": {id: 7, gestures: ["collapsed"], limits: []}});
  for (const action of ALIGN) assert.equal(c.offers(action), false);
});

test("a flag on an alignment is refused before the wire", async () => {
  const {client: c, requests} = client({"set-align-left": {id: 24, gestures: ["collapsed"], limits: []}});
  await assert.rejects(c.action("set-align-left", {extendSelection: true}), {code: "INVALID_ARGUMENT"});
  assert.equal(requests.length, 0);
});
