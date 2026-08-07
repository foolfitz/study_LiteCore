import assert from "node:assert/strict";
import test from "node:test";

import {
  ReleaseStateError,
  createReleaseState,
  planReleaseEviction,
  transitionReleaseState,
  validateReleaseState,
} from "../release-state.js";

function stage(state, releaseId, roles = ["shell", "wasm"]) {
  state = transitionReleaseState(state, {
    type: "DISCOVER_CANDIDATE", releaseId, graphHash: `hash-${releaseId}`,
    cacheName: `cache-${releaseId}`, totalArtifacts: roles.length,
  }).state;
  let bytes = 0;
  for (const role of roles) {
    bytes += 10;
    state = transitionReleaseState(state, {
      type: "STAGE_PROGRESS", releaseId, role, cachedBytes: bytes,
    }).state;
  }
  return transitionReleaseState(state, { type: "STAGE_READY", releaseId }).state;
}

function activateHealthy(state, releaseId) {
  state = transitionReleaseState(state, { type: "ACTIVATE_BEGIN", releaseId }).state;
  state = transitionReleaseState(state, { type: "ACTIVATE_COMMIT", releaseId }).state;
  return transitionReleaseState(state, { type: "HEALTH_PASS", releaseId }).state;
}

test("fresh candidate becomes active and last-known-good only after health", () => {
  let state = stage(createReleaseState(), "release-a");
  state = transitionReleaseState(state, { type: "ACTIVATE_BEGIN", releaseId: "release-a" }).state;
  state = transitionReleaseState(state, { type: "ACTIVATE_COMMIT", releaseId: "release-a" }).state;
  assert.equal(state.currentReleaseId, "release-a");
  assert.equal(state.lastKnownGoodReleaseId, null);
  assert.equal(state.releases["release-a"].status, "active-health-pending");
  state = transitionReleaseState(state, { type: "HEALTH_PASS", releaseId: "release-a" }).state;
  assert.equal(state.lastKnownGoodReleaseId, "release-a");
  assert.equal(state.releases["release-a"].health, "passed");
  assert.equal(validateReleaseState(state).pass, true);
});

test("failed candidate health restores previous known-good", () => {
  let state = activateHealthy(stage(createReleaseState(), "release-a"), "release-a");
  state = stage(state, "release-b");
  state = transitionReleaseState(state, { type: "ACTIVATE_BEGIN", releaseId: "release-b" }).state;
  state = transitionReleaseState(state, { type: "ACTIVATE_COMMIT", releaseId: "release-b" }).state;
  const failed = transitionReleaseState(state, {
    type: "HEALTH_FAIL", releaseId: "release-b", reason: "fixture-open-failed",
  });
  assert.equal(failed.state.currentReleaseId, "release-a");
  assert.equal(failed.state.lastKnownGoodReleaseId, "release-a");
  assert.equal(failed.state.releases["release-b"].status, "failed");
  assert.deepEqual(failed.actions.map((item) => item.type), [
    "delete-release-cache", "rollback-complete",
  ]);
});

test("interrupted staging and health-pending activation recover conservatively", () => {
  let state = activateHealthy(stage(createReleaseState(), "release-a"), "release-a");
  state = transitionReleaseState(state, {
    type: "DISCOVER_CANDIDATE", releaseId: "release-b", graphHash: "hash-b",
    cacheName: "cache-b", totalArtifacts: 2,
  }).state;
  state = transitionReleaseState(state, {
    type: "STAGE_PROGRESS", releaseId: "release-b", role: "shell", cachedBytes: 10,
  }).state;
  let recovered = transitionReleaseState(state, { type: "RECOVER" });
  assert.equal(recovered.state.currentReleaseId, "release-a");
  assert.equal(recovered.state.releases["release-b"].status, "failed");
  assert.equal(recovered.actions[0].type, "delete-release-cache");

  state = stage(recovered.state, "release-c");
  state = transitionReleaseState(state, { type: "ACTIVATE_BEGIN", releaseId: "release-c" }).state;
  state = transitionReleaseState(state, { type: "ACTIVATE_COMMIT", releaseId: "release-c" }).state;
  recovered = transitionReleaseState(state, { type: "RECOVER" });
  assert.equal(recovered.state.currentReleaseId, "release-a");
  assert.equal(recovered.state.releases["release-c"].status, "failed");
});

test("client pin forbids hot switch and eviction", () => {
  let state = activateHealthy(stage(createReleaseState(), "release-a"), "release-a");
  state = transitionReleaseState(state, {
    type: "PIN_CLIENT", clientId: "client-1", releaseId: "release-a",
  }).state;
  assert.throws(() => transitionReleaseState(state, {
    type: "PIN_CLIENT", clientId: "client-1", releaseId: "release-b",
  }), ReleaseStateError);
  assert.throws(() => transitionReleaseState(state, {
    type: "EVICT", releaseId: "release-a",
  }), (error) => error.code === "RELEASE_PINNED");
});

test("eviction plan deletes failed and excess retiring releases but protects pins", () => {
  let state = activateHealthy(stage(createReleaseState({ retentionLimit: 3 }), "release-a"), "release-a");
  for (const id of ["release-b", "release-c", "release-d"])
    state = activateHealthy(stage(state, id), id);
  state = transitionReleaseState(state, {
    type: "PIN_CLIENT", clientId: "old-client", releaseId: "release-b",
  }).state;
  state.releases["release-a"].status = "failed";
  state.releases["release-a"].health = "failed";
  const plan = planReleaseEviction(state);
  assert.ok(plan.evictReleaseIds.includes("release-a"));
  assert.ok(!plan.evictReleaseIds.includes("release-b"));
  assert.ok(!plan.evictReleaseIds.includes("release-d"));
  assert.equal(plan.boundedAfterPlan, true);
});

test("failed staging leaves active release untouched", () => {
  let state = activateHealthy(stage(createReleaseState(), "release-a"), "release-a");
  state = transitionReleaseState(state, {
    type: "DISCOVER_CANDIDATE", releaseId: "release-b", graphHash: "hash-b",
    cacheName: "cache-b", totalArtifacts: 2,
  }).state;
  const result = transitionReleaseState(state, {
    type: "STAGE_FAILED", releaseId: "release-b", reason: "hash-mismatch",
  });
  assert.equal(result.state.currentReleaseId, "release-a");
  assert.equal(result.state.lastKnownGoodReleaseId, "release-a");
  assert.equal(result.state.releases["release-b"].status, "failed");
});

test("repair commit atomically switches cache identity and preserves active health", () => {
  let state = activateHealthy(stage(createReleaseState(), "release-a"), "release-a");
  const oldCache = state.releases["release-a"].cacheName;
  const result = transitionReleaseState(state, {
    type: "REPAIR_COMMIT",
    releaseId: "release-a",
    cacheName: "cache-release-a-repair-1",
    cachedBytes: 20,
  });
  assert.equal(result.state.currentReleaseId, "release-a");
  assert.equal(result.state.lastKnownGoodReleaseId, "release-a");
  assert.equal(result.state.releases["release-a"].health, "passed");
  assert.equal(result.state.releases["release-a"].cacheName, "cache-release-a-repair-1");
  assert.deepEqual(result.actions, [{ type: "delete-cache-name", cacheName: oldCache }]);
});
