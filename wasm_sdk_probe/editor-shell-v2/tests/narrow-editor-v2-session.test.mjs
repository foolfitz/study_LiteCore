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
import { EditorStateMachine } from "../../editor-shell/state-machine.js";

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

// Finding 053.  The test above is titled "a post-dispatch failure" and
// exercises MUTATION_OUTCOME_UNKNOWN -- the one code the base class already had
// in RECOVERY_ERRORS.  The property it claims is general and was not: an
// EDITOR_FORMAT_POSTCONDITION_FAILED with `dispatched: true` prescribed a
// rollback and left the session in `ready`, where the button that performs it
// is not shown.  A test whose name claims more than its case is the shape this
// tree keeps paying for.
test("a DISPATCHED postcondition failure blocks the queue too, not just the "
     + "codes the base class knows", async () => {
       const failure = Object.assign(
         new Error("the document does not show the state this action asked for"),
         { code: "EDITOR_FORMAT_POSTCONDITION_FAILED",
           details: { formatBarrier: { dispatched: true,
                                       failureShape: "postcondition-not-met" } } });
       const { session } = await opened({ failing: "set-list-unordered", failure });
       const error = await session.setList("unordered").then(() => null, (e) => e);
       assert.equal(error.code, "EDITOR_FORMAT_POSTCONDITION_FAILED");
       assert.equal(error.recovery, "rollback");
       assert.equal(session.state.snapshot.state, "recoverable-error",
                    "the host must ENTER recoverable-error, not merely name the "
                    + "disposition (SPEC E2-B 5.13 clause three)");
       // The prescription is now performable: rollback() accepts this state.
       await session.rollback();
       assert.equal(session.state.snapshot.state, "ready");
     });

test("the base-class seam this depends on is still there", async () => {
  const { session } = await opened();
  // `_blockQueue` is a private of the frozen base class.  Depending on it is
  // the same trade as the client interception above, and it is pinned the same
  // way: if the base class ever renames or removes it, this fails loudly here
  // instead of silently leaving dispatched failures unblocked in the product.
  assert.equal(typeof session._blockQueue, "function");
  assert.equal(typeof session._blockQueueIfDispatched, "function");
});

test("an undispatched failure still leaves the queue running", async () => {
  // The other side of the same branch: `_blockQueueIfDispatched` must not turn
  // every failure into a blocked queue.
  const failure = Object.assign(new Error("refused before dispatch"), {
    code: "EDITOR_FORMAT_POSTCONDITION_FAILED",
    details: { formatBarrier: { dispatched: false,
                                failureShape: "routing-selection-not-observed" } },
  });
  const { session } = await opened({ failing: "set-list-ordered", failure });
  const error = await session.setList("ordered").then(() => null, (e) => e);
  assert.equal(error.recovery, "none");
  assert.equal(session.state.snapshot.state, "ready");
  const next = await session.action("set-bold", { enabled: true });
  assert.equal(next.action, "set-bold");
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

// ------------------------------------------------------- finding 084

/**
 * A session with a state machine and nothing else, so the guard can be driven
 * without an engine.  It reaches the same `this.state` the product's writers
 * reach -- the guard wraps the machine, not the drain, and that is the point:
 * every writer that can be stale goes through `update`.
 */
function guarded() {
  const seen = [];
  // A factory that is never called: the guard is installed in the constructor
  // and every writer it covers reaches `this.state` without an engine. Giving
  // it a real one would make these tests about the engine.
  const session = new NarrowEditorV2Session({
    engineFactory: () => { throw new Error("no engine in these tests"); },
    onState: (s) => seen.push(s),
  });
  return { session, seen };
}

function stateAt(sourceSequence, caretX) {
  return { sourceSequence, caret: { x: caretX, y: 100, width: 2, height: 20 },
           selection: { collapsed: true, rectangles: [] } };
}

test("finding 084: a state write whose sourceSequence went BACKWARDS does not "
     + "move the caret back", () => {
  const { session } = guarded();
  session.state.transition("loading");
  session.state.transition("ready", { editorState: stateAt(294, 3458) });
  // The announcement lands with the new caret.
  session.state.update({ editorState: stateAt(296, 5618) });
  assert.equal(session.state.snapshot.editorState.caret.x, 5618);
  // The drain's read -- answered at 294, applied now -- must not undo it.
  session.state.update({ revision: 129, editorState: stateAt(294, 3458) });
  assert.equal(session.state.snapshot.editorState.caret.x, 5618,
               "the caret was moved back to where it was a commit ago");
  assert.equal(session.state.snapshot.editorState.sourceSequence, 296);
  assert.equal(session.staleEditorStateWrites, 1);
});

test("finding 084: the REST of a stale patch still applies", () => {
  const { session } = guarded();
  session.state.transition("loading");
  session.state.transition("ready",
                           { revision: 128, dirty: false,
                             editorState: stateAt(294, 3458) });
  session.state.update({ editorState: stateAt(296, 5618) });
  session.state.update({ revision: 129, dirty: true,
                         editorState: stateAt(294, 3458) });
  // Only editorState is stale. Dropping the revision with it would leave the
  // page showing a revision the document has moved past.
  assert.equal(session.state.snapshot.revision, 129);
  assert.equal(session.state.snapshot.dirty, true);
  assert.equal(session.state.snapshot.editorState.caret.x, 5618);
});

test("finding 084: an ADVANCING write still lands, and so does an equal one",
     () => {
  const { session } = guarded();
  session.state.transition("loading");
  session.state.transition("ready", { editorState: stateAt(294, 3458) });
  session.state.update({ editorState: stateAt(295, 4000) });
  assert.equal(session.state.snapshot.editorState.caret.x, 4000);
  // Equal is not a regression: the drain's read answered at the same sequence
  // the announcement carried is the SAME moment, and refusing it would be a
  // guard against nothing.
  session.state.update({ editorState: stateAt(295, 4200) });
  assert.equal(session.state.snapshot.editorState.caret.x, 4200);
  assert.equal(session.staleEditorStateWrites, 0);
});

test("finding 084: a REOPEN may legitimately move the sequence backwards", () => {
  const { session } = guarded();
  session.state.transition("loading");
  session.state.transition("ready", { editorState: stateAt(296, 5618) });
  session.state.transition("recoverable-error");
  session.state.transition("loading");
  // A fresh engine counts from the start. This goes through `transition`, which
  // the guard deliberately does not wrap -- a reopen that could not lower the
  // sequence would leave the new engine's caret unreachable forever.
  session.state.transition("ready", { editorState: stateAt(2, 163) });
  assert.equal(session.state.snapshot.editorState.caret.x, 163);
  assert.equal(session.staleEditorStateWrites, 0);
});

test("finding 084: a write with no sourceSequence is not second-guessed", () => {
  const { session } = guarded();
  session.state.transition("loading");
  session.state.transition("ready", { editorState: stateAt(296, 5618) });
  // A host or profile that does not carry the counter must not have its state
  // silently dropped: not-knowing is not the same claim as going backwards.
  session.state.update({ editorState: { caret: { x: 9, y: 9 } } });
  assert.equal(session.state.snapshot.editorState.caret.x, 9);
  assert.equal(session.staleEditorStateWrites, 0);
});

test("finding 084: the guard is installed on the machine the writers use", () => {
  const { session } = guarded();
  // The drain calls `this.state.update` on the session's own machine. If the
  // guard were installed on a copy, every test above would still pass and the
  // product would still drop carets.
  assert.equal(typeof session.staleEditorStateWrites, "number");
  assert.notEqual(session.state.update, EditorStateMachine.prototype.update,
                  "session.state.update is the unwrapped machine method");
});

test("finding 084: the base class builds the machine ONCE, which is what makes "
     + "wrapping it in the constructor enough", () => {
  // The guard wraps `this.state` at construction. If a reopen or a rollback
  // ever replaced the machine, the wrapper would be silently dropped and every
  // test above would still pass -- the same shape as the client-assignment
  // interception above, which is pinned by a counter for the same reason.
  const source = readFileSync(
    fileURLToPath(new URL("../../editor-shell/editor-session.js",
                          import.meta.url)), "utf8");
  const assignments = source.match(/this\.state\s*=\s*new\s+EditorStateMachine/g);
  assert.equal(assignments?.length, 1,
               "editor-shell/editor-session.js assigns this.state more than "
               + "once, so the guard installed in the constructor no longer "
               + "covers every writer");
});

// --------------------- finding 084: order independence, not "currently winning"
//
// The tests above show the guard refuses the ONE interleaving that was measured
// in the product. That is not the same claim as "the newest state always wins",
// and the difference matters for a cutover: the accessibility core emits an
// extra state-changing callback per commit, so the arrival order this guard
// meets there is not the order it was written against.
//
// The invariant these prove is the strong one: after ANY interleaving of writes,
// the snapshot holds the HIGHEST sourceSequence that was written, and the caret
// that came with it. Proven over every permutation rather than over the one that
// was seen.

function drive(session, sequences) {
  for (const n of sequences) session.state.update({ editorState: stateAt(n, n * 10) });
  return session.state.snapshot.editorState;
}

function permutations(items) {
  if (items.length <= 1) return [items];
  const out = [];
  for (let i = 0; i < items.length; i += 1) {
    const rest = [...items.slice(0, i), ...items.slice(i + 1)];
    for (const tail of permutations(rest)) out.push([items[i], ...tail]);
  }
  return out;
}

test("finding 084: after ANY order of arrivals the newest state is the one held",
     () => {
  const arrivals = [294, 295, 296, 297];
  let checked = 0;
  for (const order of permutations(arrivals)) {
    const { session } = guarded();
    session.state.transition("loading");
    session.state.transition("ready", { editorState: stateAt(293, 2930) });
    const held = drive(session, order);
    assert.equal(held.sourceSequence, 297,
                 `order ${order.join(",")} left the snapshot at `
                 + `${held.sourceSequence}`);
    assert.equal(held.caret.x, 2970,
                 `order ${order.join(",")} left the caret at ${held.caret.x}`);
    checked += 1;
  }
  assert.equal(checked, 24, "not every permutation was driven");
});

test("finding 084: a DUPLICATED announcement is idempotent, in any position",
     () => {
  for (const order of [[296, 296, 294], [294, 296, 296], [296, 294, 296]]) {
    const { session } = guarded();
    session.state.transition("loading");
    session.state.transition("ready", { editorState: stateAt(293, 2930) });
    const held = drive(session, order);
    assert.equal(held.sourceSequence, 296, `order ${order.join(",")}`);
    assert.equal(held.caret.x, 2960, `order ${order.join(",")}`);
  }
});

test("finding 084: the sequence the snapshot holds NEVER decreases, whatever "
     + "arrives", () => {
  const { session, seen } = guarded();
  session.state.transition("loading");
  session.state.transition("ready", { editorState: stateAt(293, 2930) });
  // A deliberately hostile stream: forwards, backwards, repeats, a big jump.
  drive(session, [295, 294, 296, 294, 295, 300, 297, 300, 299]);
  const sequences = seen
    .map((s) => s.editorState?.sourceSequence)
    .filter((n) => Number.isInteger(n));
  for (let i = 1; i < sequences.length; i += 1)
    assert.ok(sequences[i] >= sequences[i - 1],
              `the snapshot went ${sequences[i - 1]} -> ${sequences[i]}`);
  assert.equal(session.state.snapshot.editorState.sourceSequence, 300);
  // Every backwards arrival was refused, and the counter says how many.
  assert.equal(session.staleEditorStateWrites, 5);
});

test("finding 084: TWO announcements per commit -- the a11y core's shape -- "
     + "still ends on the caret-bearing one", () => {
  // What the accessibility core actually does, from the measured logs: a commit
  // produces two state-changing callbacks, and the caret rides the SECOND. The
  // drain's read, answered before both, is applied between them. The order the
  // product met is the middle one; the other two are the same three writes in
  // the orders a different schedule could deliver them.
  for (const order of [["a1", "a2", "drain"], ["a1", "drain", "a2"],
                       ["drain", "a1", "a2"]]) {
    const { session } = guarded();
    session.state.transition("loading");
    session.state.transition("ready", { editorState: stateAt(294, 2940) });
    for (const step of order) {
      if (step === "a1") session.state.update({ editorState: stateAt(295, 2940) });
      if (step === "a2") session.state.update({ editorState: stateAt(296, 5618) });
      if (step === "drain")
        session.state.update({ revision: 129, editorState: stateAt(294, 2940) });
    }
    assert.equal(session.state.snapshot.editorState.caret.x, 5618,
                 `order ${order.join(",")} lost the caret`);
    assert.equal(session.state.snapshot.revision, 129,
                 `order ${order.join(",")} lost the revision`);
  }
});
