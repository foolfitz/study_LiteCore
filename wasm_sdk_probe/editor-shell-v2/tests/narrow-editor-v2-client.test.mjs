// The ten inherited actions must behave exactly as v1's client behaves.
//
// SPEC E2-C 2.2 chose to validate them in editor-shell-v2 rather than reach
// into the hash-bound v1 module, which means two copies of one rule set.  The
// copy is only safe if something compares them, and comparing SOURCE would not
// do it -- the rules could be reworded, reordered or partially applied and the
// text would still look alike.  So this compares BEHAVIOUR: the same call, the
// same engine reply, both clients, and the verdicts must be identical.
//
// The v1 pair that drifted (underline and strikethrough in editor-client.js but
// not in editor-client.d.ts) went unnoticed across two shipped artifacts, and
// the freeze test kept pinning eight of ten actions the whole time.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorClient } from "../../editor-shell/editor-client.js";
import { NarrowEditorV2Client, EDITOR_V2_ACTIONS,
         EDITOR_V2_INHERITED_ACTIONS } from "../narrow-editor-v2-client.js";
import { EDITOR_V2_PARAGRAPH_ACTIONS } from "../paragraph-editor-client.js";

const manifestOf = (profile) => JSON.parse(readFileSync(
  fileURLToPath(new URL(`../../dist/profiles/${profile}/sdk-manifest.json`,
                        import.meta.url)), "utf8"));

const V1_MANIFEST = manifestOf("e1-editor-v1");
const V2_MANIFEST = manifestOf("e2-editor-v2");

const MOVE = new Set(["move-character-left", "move-character-right"]);
const DELETE = new Set(["delete-backward", "delete-forward"]);
const FORMAT = new Set(["set-bold", "set-italic", "set-underline",
  "set-strikethrough"]);

/** The reply the engine gives when the action worked, by action class. */
function goodReply(action, revision) {
  if (MOVE.has(action)) {
    return { action, beforeRevision: revision, revision, changed: false,
             state: {}, completion: "documented-callback-state" };
  }
  if (DELETE.has(action)) {
    return { action, beforeRevision: revision, revision: revision + 1,
             changed: true, state: {}, completion: "verified-selection-delete" };
  }
  return { action, beforeRevision: revision, revision: revision + 1,
           changed: true, state: {}, completion: "uno-command-result" };
}

// Each mutation is a way an engine could lie or a way a shell could be sloppy.
// `documented-state-noop` is here by name: finding 022 produced exactly that
// completion from a stale cache, and it was removed from both sides.
const REPLY_MUTATIONS = [
  ["as-is", (reply) => reply],
  ["no state", (reply) => ({ ...reply, state: undefined })],
  ["wrong action", (reply) => ({ ...reply, action: "set-italic-ish" })],
  ["wrong beforeRevision", (reply) => ({ ...reply, beforeRevision: 99 })],
  ["revision not an integer", (reply) => ({ ...reply, revision: 1.5 })],
  ["revision unchanged", (reply, r) => ({ ...reply, revision: r })],
  ["revision jumps two", (reply, r) => ({ ...reply, revision: r + 2 })],
  ["changed true", (reply) => ({ ...reply, changed: true })],
  ["changed false", (reply) => ({ ...reply, changed: false })],
  ["changed null", (reply) => ({ ...reply, changed: null })],
  ["completion uno-command-result",
   (reply) => ({ ...reply, completion: "uno-command-result" })],
  ["completion verified-selection-delete",
   (reply) => ({ ...reply, completion: "verified-selection-delete" })],
  ["completion verified-format-readback",
   (reply) => ({ ...reply, completion: "verified-format-readback" })],
  ["completion documented-state-noop",
   (reply) => ({ ...reply, completion: "documented-state-noop" })],
  ["completion missing", (reply) => ({ ...reply, completion: undefined })],
  ["empty reply", () => ({})],
];

const OPTION_CASES = [
  ["default", {}],
  ["extendSelection true", { extendSelection: true }],
  ["extendSelection false", { extendSelection: false }],
  ["extendSelection not a boolean", { extendSelection: "yes" }],
  ["enabled true", { enabled: true }],
  ["enabled false", { enabled: false }],
  ["enabled not a boolean", { enabled: 1 }],
  ["expectedRevision negative", { expectedRevision: -1 }],
  ["expectedRevision not an integer", { expectedRevision: 2.5 }],
  ["expectedRevision explicit", { expectedRevision: 7 }],
];

function handleFor(manifest, mutate) {
  const issued = [];
  return {
    handle: 1,
    revision: 3,
    issued,
    _assertUsable() {},
    _engine: {
      manifest,
      async _request(operation, payload) {
        issued.push(operation);
        const r = payload.expectedRevision;
        return mutate(goodReply(payload.action, r), r);
      },
    },
  };
}

/** What the client did, reduced to something two implementations can be equal on. */
async function verdict(Client, manifest, action, options, mutate) {
  const handle = handleFor(manifest, mutate);
  const client = new Client(handle);
  try {
    const result = await client.action(action, options);
    return { outcome: "ok", revision: handle.revision,
             completion: result.completion, issued: handle.issued.length };
  } catch (error) {
    return { outcome: error.code || error.name, revision: handle.revision,
             completion: null, issued: handle.issued.length };
  }
}

test("the ten inherited actions decide identically in both clients", async () => {
  let compared = 0;
  let accepted = 0;
  for (const action of EDITOR_V2_INHERITED_ACTIONS) {
    for (const [optionLabel, options] of OPTION_CASES) {
      for (const [replyLabel, mutate] of REPLY_MUTATIONS) {
        const v1 = await verdict(NarrowEditorClient, V1_MANIFEST, action,
                                 options, mutate);
        const v2 = await verdict(NarrowEditorV2Client, V2_MANIFEST, action,
                                 options, mutate);
        assert.deepEqual(v2, v1,
                         `${action} / ${optionLabel} / ${replyLabel}`);
        compared += 1;
        if (v1.outcome === "ok") accepted += 1;
      }
    }
  }
  // Without this the whole comparison could be two clients refusing everything.
  assert.ok(accepted > 0, "no case was accepted; the matrix proves nothing");
  assert.equal(compared, EDITOR_V2_INHERITED_ACTIONS.length
               * OPTION_CASES.length * REPLY_MUTATIONS.length);
});

test("the comparison can fail", async () => {
  // The guard on the guard.  If a rule is removed from the v2 copy, the matrix
  // above must go red -- so break one on purpose here and require that it does.
  class Sloppy extends NarrowEditorV2Client {
    _validateInherited() { /* accepts anything */ }
  }
  let sawDifference = false;
  for (const [, mutate] of REPLY_MUTATIONS) {
    const v1 = await verdict(NarrowEditorClient, V1_MANIFEST, "set-bold",
                             { enabled: true }, mutate);
    const loose = await verdict(Sloppy, V2_MANIFEST, "set-bold",
                                { enabled: true }, mutate);
    if (v1.outcome !== loose.outcome) sawDifference = true;
  }
  assert.ok(sawDifference,
            "dropping the postcondition rules did not change any verdict");
});

test("the paragraph five are not revalidated here, they are delegated",
     async () => {
       // Route C's rules must exist in one place.  If this client validated
       // them too, `changed: null` would have to be accepted by the same code
       // that must reject it for delete.
       const handle = handleFor(V2_MANIFEST, (_reply, r) => ({
         action: "set-list-ordered", beforeRevision: r, revision: r + 1,
         changed: null, state: {}, completion: "verified-format-readback" }));
       const client = new NarrowEditorV2Client(handle);
       const result = await client.action("set-list-ordered");
       assert.equal(result.completion, "verified-format-readback");
       assert.equal(result.changed, null);
     });

test("a paragraph reply shape is still rejected for an inherited action",
     async () => {
       const handle = handleFor(V2_MANIFEST, (reply) => ({
         ...reply, changed: null, completion: "verified-format-readback" }));
       const client = new NarrowEditorV2Client(handle);
       await assert.rejects(() => client.action("delete-forward"),
                            (error) => error.code === "EDITOR_RESULT_INVALID");
     });

test("the fifteen are the manifest's fifteen", () => {
  const declared = Object.keys(V2_MANIFEST.editorContract.actions);
  assert.deepEqual(EDITOR_V2_ACTIONS.slice().sort(), declared.slice().sort());
  assert.equal(EDITOR_V2_INHERITED_ACTIONS.length
               + EDITOR_V2_PARAGRAPH_ACTIONS.length, 15);
});

test("the convenience methods reach the same actions as v1's", async () => {
  const pairs = [
    (c) => c.moveCharacter("left"),
    (c) => c.moveCharacter("right"),
    (c) => c.delete("backward"),
    (c) => c.delete("forward"),
    (c) => c.insertBreak("paragraph"),
    (c) => c.insertBreak("line"),
    (c) => c.setInlineFormat("bold", true),
    (c) => c.setInlineFormat("italic", false),
    (c) => c.setInlineFormat("underline", true),
    (c) => c.setInlineFormat("strikethrough", false),
  ];
  for (const call of pairs) {
    const v1Handle = handleFor(V1_MANIFEST, (reply) => reply);
    const v2Handle = handleFor(V2_MANIFEST, (reply) => reply);
    const a = await call(new NarrowEditorClient(v1Handle));
    const b = await call(new NarrowEditorV2Client(v2Handle));
    assert.equal(b.action, a.action);
    assert.equal(v2Handle.issued[0], "editorActionV2");
    assert.equal(v1Handle.issued[0], "editorActionV1");
  }
});

test("the client refuses a profile that is not v2", async () => {
  const handle = handleFor(V1_MANIFEST, (reply) => reply);
  const client = new NarrowEditorV2Client(handle);
  await assert.rejects(() => client.action("set-bold", { enabled: true }),
                       (error) => error.code === "UNSUPPORTED_OPERATION");
  assert.deepEqual(handle.issued, []);
});
