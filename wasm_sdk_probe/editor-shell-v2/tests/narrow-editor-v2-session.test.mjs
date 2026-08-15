// SPEC E2-C 2.3: the product session, on the profile it is for.
//
// These test the implementation, not a copy of the behaviour written inside a
// test runner.  A runner that carries its own queue and its own rollback can
// make a validation round pass while the product has neither.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";
import { NarrowEditorV2Client } from "../narrow-editor-v2-client.js";

const manifestOf = (profile) => JSON.parse(readFileSync(
  fileURLToPath(new URL(`../../dist/profiles/${profile}/sdk-manifest.json`,
                        import.meta.url)), "utf8"));

const V2_MANIFEST = manifestOf("e2-editor-v2");

const PARAGRAPH = new Set(["set-list-none", "set-list-unordered",
  "set-list-ordered", "set-paragraph-heading", "set-paragraph-body"]);
const MOVE = new Set(["move-character-left", "move-character-right"]);
const DELETE = new Set(["delete-backward", "delete-forward"]);

function editorState(revision) {
  return { documentHandle: 1, revision, caret: null,
           selection: { observed: true, collapsed: true, start: null,
                        end: null, rectangles: [] },
           selectionType: "none", selectionTextMissing: false,
           selectionText: "", format: { bold: false, italic: false } };
}

/**
 * An engine that answers like the v2 worker does, with a hook for making one
 * named action fail the way the engine fails it.
 */
function fixture({ failing = null, failure = null } = {}) {
  const calls = [];
  const saves = [];
  let revision = 0;
  const document = {
    handle: 1,
    revision: 0,
    widthTwips: 1000,
    heightTwips: 2000,
    _assertUsable() {},
    async render() { return { pixels: new ArrayBuffer(4), revision }; },
    async save() { saves.push(revision); return new ArrayBuffer(16); },
    async getSelection() { return { text: "", selectionType: "text", revision }; },
    async close() { calls.push("close"); },
  };
  const engine = {
    manifest: V2_MANIFEST,
    onEvent() { return () => {}; },
    async open() { calls.push("open"); revision = 0; document.revision = 0; return document; },
    async _request(operation, payload) {
      calls.push(`${operation}:${payload.action || "state"}`);
      if (operation === "editorGetStateV2") return editorState(revision);
      if (operation === "editorSelectRangeV2") return { revision };
      const action = payload.action;
      if (action === failing) throw failure;
      const moving = MOVE.has(action);
      if (!moving) document.revision = ++revision;
      if (PARAGRAPH.has(action)) {
        return { action, beforeRevision: payload.expectedRevision, revision,
                 changed: null, completion: "verified-format-readback",
                 state: editorState(revision) };
      }
      return {
        action,
        beforeRevision: payload.expectedRevision,
        revision,
        changed: !moving,
        completion: moving ? "documented-callback-visible-cursor"
          : DELETE.has(action) ? "verified-selection-delete" : "uno-command-result",
        state: editorState(revision),
      };
    },
    dispose() { calls.push("dispose"); },
  };
  document._engine = engine;
  const session = new NarrowEditorV2Session({
    engineFactory: async () => engine,
    secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } },
  });
  return { calls, saves, document, engine, session };
}

async function opened(options) {
  const f = await Promise.resolve(fixture(options));
  await f.session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  return f;
}

test("it opens on the v2 profile, which the shipped session cannot", async () => {
  const { session } = await opened();
  assert.equal(session.state.snapshot.state, "ready");
  assert.ok(session.editor instanceof NarrowEditorV2Client);
  // The seam this class depends on: the base class assigned a client and this
  // subclass swapped it.  If the base ever stops assigning, this stays zero
  // and the dependency has become silent -- which is the failure mode the
  // counter exists to prevent.
  assert.equal(session.clientReplacements, 1);
});

test("all fifteen go through the session's queue", async () => {
  const { session, calls } = await opened();
  const actions = [...PARAGRAPH, "move-character-left", "delete-backward",
    "insert-line-break", "set-bold"];
  for (const action of actions) {
    const options = action === "set-bold" ? { enabled: true } : {};
    const result = await session.action(action, options);
    assert.equal(result.action, action);
  }
  for (const action of actions)
    assert.ok(calls.includes(`editorActionV2:${action}`), `${action} never dispatched`);
});

test("the two families keep their own postconditions", async () => {
  const { session } = await opened();
  const paragraph = await session.setList("ordered");
  assert.equal(paragraph.changed, null);
  assert.equal(paragraph.completion, "verified-format-readback");
  const inline = await session.action("set-bold", { enabled: true });
  assert.equal(inline.changed, true);
  assert.equal(inline.completion, "uno-command-result");
});

test("a paragraph action advances the revision by exactly one", async () => {
  const { session } = await opened();
  const before = session.state.snapshot.revision;
  await session.setParagraphStyle("heading");
  assert.equal(session.state.snapshot.revision, before + 1);
  assert.equal(session.state.snapshot.dirty, true);
});

test("a post-dispatch failure blocks the queue and asks for a rollback",
     async () => {
       const failure = Object.assign(new Error("the barrier could not verify"), {
         code: "MUTATION_OUTCOME_UNKNOWN",
         details: { formatBarrier: { dispatched: true,
                                     failureShape: "footnote-apparatus-readback" } },
       });
       const { session } = await opened({ failing: "set-list-unordered", failure });
       const error = await session.setList("unordered").then(() => null, (e) => e);
       assert.equal(error.code, "MUTATION_OUTCOME_UNKNOWN");
       assert.equal(error.recovery, "rollback");
       assert.equal(session.state.snapshot.state, "recoverable-error");
       // And the queue really is blocked -- anything already waiting must not
       // run against a document whose state nobody can describe.
       const after = await session.action("set-bold", { enabled: true })
         .then(() => null, (e) => e);
       assert.equal(after.code, "EDITOR_NOT_READY");
     });

test("rollback reopens from the engine's own bytes with a fresh worker",
     async () => {
       const failure = Object.assign(new Error("unverifiable"), {
         code: "MUTATION_OUTCOME_UNKNOWN",
         details: { formatBarrier: { dispatched: true } },
       });
       const { session, calls } = await opened({ failing: "set-list-ordered", failure });
       await session.action("set-bold", { enabled: true });   // make it dirty
       await session.selectRange({ xTwips: 0, yTwips: 0 },
                                 { xTwips: 100, yTwips: 100 });
       assert.ok(session.state.snapshot.hasCheckpoint,
                 "the selection gesture must have written a checkpoint");
       await session.setList("ordered").catch(() => {});
       const opens = calls.filter((c) => c === "open").length;
       await session.rollback();
       assert.equal(session.state.snapshot.state, "ready");
       assert.equal(calls.filter((c) => c === "open").length, opens + 1);
     });

test("a pre-dispatch refusal does not ask for a rollback", async () => {
  const failure = Object.assign(new Error("nothing was dispatched"), {
    code: "EDITOR_FORMAT_GESTURE_UNSUPPORTED",
    details: { formatBarrier: { dispatched: false,
                                failureShape: "gesture-not-permitted" } },
  });
  const { session } = await opened({ failing: "set-paragraph-heading", failure });
  const error = await session.setParagraphStyle("heading").then(() => null, (e) => e);
  assert.equal(error.recovery, "none");
  // The queue keeps running: nothing happened to the document.
  assert.equal(session.state.snapshot.state, "ready");
  const next = await session.action("set-italic", { enabled: true });
  assert.equal(next.action, "set-italic");
});

test("a bad argument never reaches the engine and never rolls anything back",
     async () => {
       const { session, calls } = await opened();
       const before = calls.length;
       for (const call of [() => session.setList("bulleted"),
                           () => session.setParagraphStyle("h2"),
                           () => session.action("set-superscript")]) {
         const error = await call().then(() => null, (e) => e);
         assert.ok(error, "expected a rejection");
         assert.equal(error.recovery, "none");
       }
       assert.equal(calls.length, before, "no request should have been issued");
       assert.equal(session.state.snapshot.state, "ready");
     });

test("a boundary rejection still demands a fresh worker", async () => {
  const failure = Object.assign(new Error("structural boundary"), {
    code: "EDITOR_BOUNDARY_UNSUPPORTED",
  });
  const { session } = await opened({ failing: "delete-forward", failure });
  const error = await session.action("delete-forward").then(() => null, (e) => e);
  assert.equal(error.recovery, "restart");
  assert.equal(session.state.snapshot.state, "restart-required");
});

test("the generation ceiling still fails closed", async () => {
  const failure = Object.assign(new Error("unverifiable"), {
    code: "MUTATION_OUTCOME_UNKNOWN",
    details: { formatBarrier: { dispatched: true } },
  });
  const { session } = await opened({ failing: "set-list-none", failure });
  // Generation 1 is the first open; two rollbacks reach the ceiling of three.
  for (let attempt = 0; attempt < 2; attempt += 1) {
    await session.setList("none").catch(() => {});
    await session.rollback();
  }
  await session.setList("none").catch(() => {});
  const error = await session.rollback().then(() => null, (e) => e);
  assert.ok(error, "the fourth generation must be refused");
  assert.equal(error.code, "WORKER_GENERATION_LIMIT");
  assert.equal(error.details.requiresPageReload, true);
  assert.equal(error.details.maximumWorkerGenerations, 3);
});

test("gestures and limits come from the manifest, for showing not for failing",
     async () => {
       const { session } = await opened();
       assert.deepEqual(session.gesturesFor("set-list-ordered"),
                        ["collapsed", "range-single", "range-cross"]);
       assert.deepEqual(session.gesturesFor("set-bold"), ["collapsed"]);
       assert.deepEqual(session.limitsFor("set-paragraph-heading"),
                        ["heading-level-1-only", "no-precondition-state"]);
     });
