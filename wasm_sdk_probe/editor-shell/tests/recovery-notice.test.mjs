import assert from "node:assert/strict";
import test from "node:test";

import { recoveryNotice } from "../recovery-notice.js";

// The interesting cases are all "does the host claim something that is not
// true", so each test below has a partner that differs in one field and must
// come out the other way.  A suite that only checked the happy path would pass
// against a function returning `{visible: false}` for everything.

const stopped = {
  state: "recoverable-error",
  generation: 1,
  hasCheckpoint: true,
  checkpointRevision: 4,
  error: { code: "TIMEOUT", message: "editorGetStateV1 timed out", details: {} },
};

test("a stopped session holding a checkpoint offers the rescue and the restart", () => {
  const notice = recoveryNotice(stopped);
  assert.equal(notice.visible, true);
  assert.equal(notice.hasCheckpoint, true);
  assert.equal(notice.checkpointRevision, 4);
  assert.equal(notice.canRescue, true);
  assert.equal(notice.restartPossible, true);
});

test("a running session says nothing", () => {
  for (const state of ["idle", "loading", "ready", "busy", "blocked", "closed"])
    assert.equal(recoveryNotice({ ...stopped, state }).visible, false);
});

test("restart-required is stopped too", () => {
  assert.equal(recoveryNotice({ ...stopped, state: "restart-required" }).visible, true);
});

test("without a checkpoint the notice appears but promises no rescue", () => {
  const notice = recoveryNotice({ ...stopped, hasCheckpoint: false, checkpointRevision: null });
  assert.equal(notice.visible, true);
  assert.equal(notice.hasCheckpoint, false);
  assert.equal(notice.canRescue, false);
  assert.equal(notice.checkpointRevision, null);
});

test("a failure before any engine existed is not reported as lost work", () => {
  // The demo's startup path calls its state handler with a synthetic snapshot
  // carrying neither generation nor checkpoint.  Treating that as "your
  // unsaved edits are gone" would invent a loss out of a failed page load.
  const notice = recoveryNotice({
    state: "recoverable-error",
    revision: null,
    error: { code: "STARTUP_FAILED", message: "fetch failed" },
  });
  assert.equal(notice.visible, false);
});

test("a checkpoint alone is enough to speak, whatever the generation says", () => {
  const notice = recoveryNotice({ ...stopped, generation: 0 });
  assert.equal(notice.visible, true);
  assert.equal(notice.canRescue, true);
});

test("an exhausted session must not point at its restart button", () => {
  const limited = recoveryNotice({
    ...stopped,
    error: {
      code: "WORKER_GENERATION_LIMIT",
      message: "Worker generation limit 3 reached; reload the page",
      details: { generation: 3, maximumWorkerGenerations: 3, requiresPageReload: true },
    },
  });
  assert.equal(limited.restartPossible, false);
  // Still rescuable: that is the whole point -- restart is gone, the bytes
  // are not.
  assert.equal(limited.canRescue, true);
});

test("requiresPageReload alone exhausts the session", () => {
  // The code is not the only carrier: `_blockQueue` can escalate a boundary
  // rejection with details of its own, and a host that keyed on the string
  // would miss it.
  const notice = recoveryNotice({
    ...stopped,
    error: { code: "STALE_DOCUMENT", message: "boundary", details: { requiresPageReload: true } },
  });
  assert.equal(notice.restartPossible, false);
});

test("a non-integer checkpoint revision is reported as unknown, not printed", () => {
  for (const value of [undefined, null, "4", 4.5, Number.NaN]) {
    const notice = recoveryNotice({ ...stopped, checkpointRevision: value });
    assert.equal(notice.canRescue, true);
    assert.equal(notice.checkpointRevision, null);
  }
});
