// SPEC-M3-link-batch-v21 9.7 / 11.1 D13: the closed lists (form two -- the
// membership is read from the runtime's own lists, so an action appended
// tomorrow is covered without editing this file).
//
//   * every action the client sends has EXACTLY ONE postcondition class, and
//     each ABI 5 action is in the "move" class;
//   * the session's BOUNDARY_CAPABLE_MOVES is EQUAL to the "move" class -- read
//     from the session's own source, so a name in the set that is in no list
//     (a typo) is caught as well as a move left out;
//   * an action in no class is refused: `_validateInherited` no longer accepts
//     a reply by falling off the end of its branches (opus S3).
//
// And the ABI 5 moves' postcondition itself: the six moves' rule, accepted on
// the readback completion a silent boundary produces, rejected for any claim
// that the document changed.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { EDITOR_V4_ACTIONS, EDITOR_V4_APPENDED_ACTIONS, NarrowEditorV2Client,
         postconditionClassOf } from "../narrow-editor-v2-client.js";
import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";

const SESSION_SOURCE = readFileSync(
  fileURLToPath(new URL("../narrow-editor-v2-session.js", import.meta.url)), "utf8");
const V20 = JSON.parse(readFileSync(fileURLToPath(
  new URL("../../dist/profiles/e2-editor-v20/sdk-manifest.json", import.meta.url)), "utf8"));

/** The names in the session's `const BOUNDARY_CAPABLE_MOVES = new Set([...]);` literal. */
function boundaryCapableMoves() {
  const literal = SESSION_SOURCE.match(/^const BOUNDARY_CAPABLE_MOVES = new Set\(\[([\s\S]*?)\]\);$/m);
  assert.ok(literal, "BOUNDARY_CAPABLE_MOVES is not a literal set where this test reads it");
  return [...literal[1].matchAll(/"([a-z-]+)"/g)].map((m) => m[1]).sort();
}

function clientWith(reply) {
  const issued = [];
  const manifest = structuredClone(V20);
  manifest.editorContract.abiVersion = 5;
  for (const [action, id] of [["move-document-start", 22], ["move-document-end", 23]])
    manifest.editorContract.actions[action] = { id, gestures: ["collapsed"], limits: ["no-extend-selection"] };
  const handle = {
    handle: 1, revision: 7, _assertUsable() {},
    _engine: { manifest, async _request(operation, payload) {
      issued.push({ operation, payload });
      return typeof reply === "function" ? reply(payload) : reply;
    } },
  };
  return { client: new NarrowEditorV2Client(handle), issued, handle };
}

const MOVE_REPLY = (completion, over = {}) => (payload) => ({
  action: payload.action, beforeRevision: payload.expectedRevision, revision: payload.expectedRevision,
  changed: false, completion, state: { caret: { x: 1, y: 2, width: 0, height: 3 } }, ...over,
});

test("D13: every action the client sends has exactly one postcondition class", () => {
  assert.ok(EDITOR_V4_ACTIONS.length >= 22, "the census is not the whole list");
  const classes = ["move", "delete", "mutation", "paragraph"];
  for (const action of EDITOR_V4_ACTIONS) {
    const found = postconditionClassOf(action);
    assert.ok(classes.includes(found), `${action} has no postcondition class (${found})`);
  }
  // Exactly one: the function answers one class per name by construction, so
  // the claim that matters is that no two classes' rules both apply -- which
  // `_validateInherited`'s if/else chain over this one answer guarantees.
  assert.equal(postconditionClassOf("move-document-start"), "move");
  assert.equal(postconditionClassOf("move-document-end"), "move");
});

test("D13: each ABI 5 action is in the move class, and only there", () => {
  assert.deepEqual(EDITOR_V4_APPENDED_ACTIONS.map(postconditionClassOf), ["move", "move"]);
});

test("D13: BOUNDARY_CAPABLE_MOVES equals the move class over the client's list", () => {
  const moves = EDITOR_V4_ACTIONS.filter((action) => postconditionClassOf(action) === "move").sort();
  assert.deepEqual(boundaryCapableMoves(), moves);
  assert.equal(moves.length, 8, "six key-path moves and finding 142's two");
});

test("D13: the session's own mutation flag agrees, action by action", async () => {
  const session = new NarrowEditorV2Session({
    engineFactory: async () => { throw new Error("not opened"); },
    secureContext: true, clipboard: { async writeText() {}, async readText() { return ""; } },
  });
  for (const action of EDITOR_V4_ACTIONS)
    assert.equal(session.actionMutates(action), postconditionClassOf(action) !== "move", action);
});

test("D13: an action in no class is refused, not accepted by falling through", () => {
  const { client } = clientWith(null);
  for (const action of ["select-all", "move-document-middle", "paste-markdown"]) {
    assert.equal(postconditionClassOf(action), null, action);
    assert.throws(() => client._validateInherited(action, 7, {
      action, beforeRevision: 7, revision: 7, changed: false,
      completion: "documented-callback-visible-cursor", state: {},
    }), (error) => error.code === "EDITOR_RESULT_INVALID", action);
  }
});

test("D13: the client refuses an unknown action before any request; the session before it is queued", async () => {
  const { client, issued } = clientWith(null);
  await assert.rejects(() => client.action("select-all"), (error) => error.code === "EDITOR_ACTION_UNSUPPORTED");
  assert.deepEqual(issued, []);
  const session = new NarrowEditorV2Session({
    engineFactory: async () => { throw new Error("not opened"); },
    secureContext: true, clipboard: { async writeText() {}, async readText() { return ""; } },
  });
  await assert.rejects(() => session.action("move-document-middle"),
                       (error) => error.code === "EDITOR_ACTION_UNSUPPORTED" && error.recovery === "none");
  assert.equal(session.enqueueCount, 0, "a refused name was counted as enqueued");
});

for (const action of EDITOR_V4_APPENDED_ACTIONS) {
  test(`${action}: the moves' postcondition -- a callback or the boundary's readback, revision held, changed false`, async () => {
    for (const completion of ["documented-callback-visible-cursor", "verified-move-readback"]) {
      const { client, issued } = clientWith(MOVE_REPLY(completion));
      const result = await client.action(action);
      assert.equal(result.completion, completion);
      assert.deepEqual(issued[0].payload, { documentHandle: 1, expectedRevision: 7, action,
                                            extendSelection: false, enabled: false });
    }
  });

  test(`${action}: a reply that claims a change is rejected`, async () => {
    for (const over of [{ changed: true }, { revision: 8 }, { completion: "uno-command-result" },
                        { completion: "verified-boundary-noop" }]) {
      const { client } = clientWith(MOVE_REPLY("verified-move-readback", over));
      await assert.rejects(() => client.action(action),
                           (error) => error.code === "EDITOR_RESULT_INVALID", JSON.stringify(over));
    }
  });

  test(`${action}: extendSelection is refused by the client`, async () => {
    const { client, issued } = clientWith(MOVE_REPLY("verified-move-readback"));
    await assert.rejects(() => client.action(action, { extendSelection: true }),
                         (error) => error.code === "INVALID_ARGUMENT");
    assert.deepEqual(issued, []);
  });
}
