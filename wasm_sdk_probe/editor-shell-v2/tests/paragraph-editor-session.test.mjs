import assert from "node:assert/strict";
import test from "node:test";

import { recoveryFor, ParagraphEditorSession }
  from "../paragraph-editor-session.js";

const barrier = (dispatched) => ({ details: { formatBarrier: { dispatched } } });

test("a pre-dispatch refusal needs no recovery", () => {
  assert.equal(recoveryFor({ code: "EDITOR_FORMAT_GESTURE_UNSUPPORTED",
                             ...barrier(false) }), "none");
  assert.equal(recoveryFor({ code: "EDITOR_FORMAT_SELECTION_NOT_READABLE",
                             ...barrier(false) }), "none");
});

test("anything dispatched rolls back", () => {
  assert.equal(recoveryFor({ code: "MUTATION_OUTCOME_UNKNOWN",
                             ...barrier(true) }), "rollback");
  assert.equal(recoveryFor({ code: "EDITOR_FORMAT_POSTCONDITION_FAILED",
                             ...barrier(true) }), "rollback");
});

test("a barrier that was not forwarded rolls back, not continues", () => {
  // The asymmetry is the argument: a needless rollback costs one action, a
  // missed one leaves a changed document the host believes is clean.
  assert.equal(recoveryFor({ code: "MUTATION_OUTCOME_UNKNOWN" }), "rollback");
});

test("a boundary rejection still demands a fresh worker", () => {
  assert.equal(recoveryFor({ code: "EDITOR_BOUNDARY_UNSUPPORTED" }), "restart");
  assert.equal(recoveryFor({ code: "WORKER_CRASHED" }), "restart");
});

test("undo is NOT the prescribed recovery for a dispatched failure", () => {
  // 5.13's correction, kept as a test so it cannot quietly come back: undo
  // goes through the queue the failure blocks, so a host told to prompt for it
  // would be prescribing something that returns EDITOR_NOT_READY.
  assert.notEqual(recoveryFor({ code: "MUTATION_OUTCOME_UNKNOWN",
                                ...barrier(true) }), "undo");
});

test("the disposition is attached to the error the caller receives", async () => {
  const document = {
    handle: 1, revision: 0,
    _assertUsable() {},
    _engine: {
      manifest: { capabilities: ["narrow-editor-v2"],
                  editorContract: { version: 2, actions: {} } },
      async _request() {
        const error = new Error("dispatched but unverified");
        error.code = "MUTATION_OUTCOME_UNKNOWN";
        error.details = { formatBarrier: { dispatched: true } };
        throw error;
      },
    },
  };
  const session = new ParagraphEditorSession({ document });
  await assert.rejects(() => session.setList("unordered"),
                       (error) => error.recovery === "rollback");
});
