import assert from "node:assert/strict";
import test from "node:test";

import { ReaderStateMachine } from "../state-machine.js";

test("reader state follows the documented loading, stale, reload, and close path", () => {
  const changes = [];
  const state = new ReaderStateMachine((snapshot) => changes.push(snapshot.state));
  state.transition("loading-core", { documentId: "doc-1", version: "v1", etag: '"v1"' });
  state.transition("loading-document", { profile: "writer-review" });
  state.transition("ready", { sdkRevision: 0 });
  state.transition("stale", {
    remoteUpdate: { documentId: "doc-1", previousVersion: "v1", version: "v2" },
  });
  state.transition("reloading");
  state.transition("ready", { version: "v2", etag: '"v2"', remoteUpdate: null });
  state.transition("closed");
  assert.deepEqual(changes, [
    "loading-core", "loading-document", "ready", "stale", "reloading", "ready", "closed",
  ]);
  assert.equal(state.snapshot.nextAction, "none");
});

test("reader refuses silent reload when local bytes exist", () => {
  const state = new ReaderStateMachine();
  state.transition("loading-core");
  state.transition("loading-document");
  state.transition("ready");
  state.markLocalBytes(true);
  state.transition("stale");
  assert.equal(state.snapshot.nextAction, "download-local-or-reload");
  assert.throws(
    () => state.assertReloadAllowed(),
    (error) => error.code === "LOCAL_BYTES_AT_RISK",
  );
  assert.doesNotThrow(() => state.assertReloadAllowed({ downloadedLocalBytes: true }));
  assert.doesNotThrow(() => state.assertReloadAllowed({ discardLocalBytes: true }));
});

test("reader rejects impossible transitions and updates after close", () => {
  const state = new ReaderStateMachine();
  assert.throws(() => state.transition("ready"), /invalid reader transition/);
  state.transition("closed");
  assert.throws(() => state.update({ version: "v2" }), /closed reader state/);
});
