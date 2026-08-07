import assert from "node:assert/strict";
import test from "node:test";

import { EditorStateMachine } from "../state-machine.js";

test("editor states allow only the frozen lifecycle", () => {
  const seen = [];
  const machine = new EditorStateMachine((snapshot) => seen.push(snapshot.state));
  machine.transition("loading");
  machine.transition("ready", { revision: 0 });
  machine.transition("busy");
  machine.transition("restart-required", { error: { code: "EDITOR_BOUNDARY_UNSUPPORTED" } });
  machine.transition("loading");
  machine.transition("ready", { generation: 2 });
  machine.transition("closed");
  assert.deepEqual(seen, [
    "loading", "ready", "busy", "restart-required", "loading", "ready", "closed",
  ]);
  assert.throws(() => machine.update({ dirty: true }), /closed editor state/);
});

test("illegal transitions fail closed", () => {
  const machine = new EditorStateMachine();
  assert.throws(() => machine.transition("ready"), /invalid editor transition/);
});
