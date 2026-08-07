"use strict";

export class ReleaseStateError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "ReleaseStateError";
    this.code = code;
    this.details = details;
  }
}

function copy(value) {
  return structuredClone(value);
}

function fail(code, message, details = {}) {
  throw new ReleaseStateError(code, message, details);
}

function releaseOf(state, releaseId) {
  const release = state.releases[releaseId];
  if (!release)
    fail("RELEASE_UNKNOWN", `unknown release: ${releaseId}`, { releaseId });
  return release;
}

function appendJournal(state, event, actions) {
  state.sequence += 1;
  state.journal.push({
    sequence: state.sequence,
    type: event.type,
    releaseId: event.releaseId || event.toReleaseId || null,
    actions: actions.map((item) => item.type),
  });
  if (state.journal.length > 64)
    state.journal.splice(0, state.journal.length - 64);
}

export function createReleaseState(options = {}) {
  const retentionLimit = options.retentionLimit ?? 3;
  if (!Number.isInteger(retentionLimit) || retentionLimit < 2)
    fail("STATE_INVALID", "retentionLimit must be an integer of at least two");
  return {
    schemaVersion: 1,
    retentionLimit,
    sequence: 0,
    currentReleaseId: null,
    candidate: null,
    lastKnownGoodReleaseId: null,
    activation: null,
    releases: {},
    clientPins: {},
    journal: [],
  };
}

export function validateReleaseState(state) {
  const errors = [];
  if (state?.schemaVersion !== 1)
    errors.push("schemaVersion differs from one");
  if (!Number.isInteger(state?.retentionLimit) || state.retentionLimit < 2)
    errors.push("retentionLimit is invalid");
  if (!state?.releases || typeof state.releases !== "object")
    errors.push("releases is not an object");
  if (!state?.clientPins || typeof state.clientPins !== "object")
    errors.push("clientPins is not an object");
  if (state?.currentReleaseId) {
    const current = state.releases?.[state.currentReleaseId];
    if (!current || !["active", "active-health-pending"].includes(current.status))
      errors.push("current release is absent or not active");
  }
  if (state?.lastKnownGoodReleaseId) {
    const knownGood = state.releases?.[state.lastKnownGoodReleaseId];
    if (!knownGood || knownGood.health !== "passed")
      errors.push("last-known-good release is absent or unhealthy");
  }
  if (state?.candidate && !state.releases?.[state.candidate.releaseId])
    errors.push("candidate release is absent");
  for (const [clientId, releaseId] of Object.entries(state?.clientPins || {})) {
    if (!clientId || !state.releases?.[releaseId])
      errors.push(`client pin is invalid: ${clientId}`);
  }
  if (state?.activation) {
    if (!state.releases?.[state.activation.toReleaseId])
      errors.push("activation target is absent");
    if (state.activation.fromReleaseId && !state.releases?.[state.activation.fromReleaseId])
      errors.push("activation source is absent");
    if (!["prepared", "health-pending"].includes(state.activation.phase))
      errors.push("activation phase is invalid");
  }
  return { errors, pass: errors.length === 0 };
}

function assertValid(state) {
  const validation = validateReleaseState(state);
  if (!validation.pass)
    fail("STATE_INVALID", validation.errors.join("; "), { errors: validation.errors });
}

export function transitionReleaseState(input, event) {
  assertValid(input);
  const state = copy(input);
  const actions = [];
  const now = event.at || null;

  switch (event.type) {
    case "DISCOVER_CANDIDATE": {
      if (!event.releaseId || !event.graphHash || !Number.isInteger(event.totalArtifacts)
          || event.totalArtifacts < 1)
        fail("EVENT_INVALID", "candidate discovery requires release, graph hash, and artifact count");
      if (event.releaseId === state.currentReleaseId)
        fail("CANDIDATE_IS_CURRENT", "current release cannot be rediscovered as a candidate");
      const existing = state.releases[event.releaseId];
      if (existing && existing.graphHash !== event.graphHash)
        fail("RELEASE_ID_COLLISION", "same release ID has a different graph hash", {
          releaseId: event.releaseId,
        });
      state.releases[event.releaseId] = {
        releaseId: event.releaseId,
        graphHash: event.graphHash,
        cacheName: event.cacheName,
        status: "staging",
        health: "unknown",
        totalArtifacts: event.totalArtifacts,
        stagedRoles: [],
        cachedBytes: 0,
        barrier: "manifest-verified",
        updatedAt: now,
      };
      state.candidate = { releaseId: event.releaseId, status: "staging" };
      break;
    }
    case "STAGE_PROGRESS": {
      if (state.candidate?.releaseId !== event.releaseId)
        fail("CANDIDATE_MISMATCH", "stage progress does not match the candidate");
      const release = releaseOf(state, event.releaseId);
      if (release.status !== "staging")
        fail("CANDIDATE_NOT_STAGING", "stage progress requires a staging candidate");
      if (!release.stagedRoles.includes(event.role))
        release.stagedRoles.push(event.role);
      release.cachedBytes = Math.max(release.cachedBytes, Number(event.cachedBytes) || 0);
      release.barrier = event.barrier || "artifact-cached";
      release.updatedAt = now;
      break;
    }
    case "STAGE_READY": {
      if (state.candidate?.releaseId !== event.releaseId)
        fail("CANDIDATE_MISMATCH", "ready release does not match the candidate");
      const release = releaseOf(state, event.releaseId);
      if (release.status !== "staging"
          || release.stagedRoles.length !== release.totalArtifacts)
        fail("CANDIDATE_INCOMPLETE", "candidate graph is not fully staged", {
          staged: release.stagedRoles.length,
          expected: release.totalArtifacts,
        });
      release.status = "ready";
      release.barrier = "metadata-before-ready";
      release.updatedAt = now;
      state.candidate.status = "ready";
      break;
    }
    case "STAGE_FAILED": {
      const release = releaseOf(state, event.releaseId);
      release.status = "failed";
      release.health = "failed";
      release.failure = event.reason || "stage-failed";
      release.updatedAt = now;
      if (state.candidate?.releaseId === event.releaseId)
        state.candidate.status = "failed";
      actions.push({ type: "delete-release-cache", releaseId: event.releaseId });
      break;
    }
    case "ACTIVATE_BEGIN": {
      if (state.candidate?.releaseId !== event.releaseId
          || state.candidate.status !== "ready")
        fail("CANDIDATE_NOT_READY", "activation requires the ready candidate");
      state.activation = {
        fromReleaseId: state.currentReleaseId,
        toReleaseId: event.releaseId,
        phase: "prepared",
      };
      actions.push({ type: "persist-activation-journal", releaseId: event.releaseId });
      break;
    }
    case "ACTIVATE_COMMIT": {
      if (state.activation?.toReleaseId !== event.releaseId
          || state.activation.phase !== "prepared")
        fail("ACTIVATION_NOT_PREPARED", "activation commit has no prepared journal");
      const release = releaseOf(state, event.releaseId);
      if (release.status !== "ready")
        fail("CANDIDATE_NOT_READY", "activation target is not ready");
      release.status = "active-health-pending";
      release.updatedAt = now;
      state.currentReleaseId = event.releaseId;
      state.activation.phase = "health-pending";
      actions.push({ type: "run-bounded-health-check", releaseId: event.releaseId });
      break;
    }
    case "HEALTH_PASS": {
      if (state.activation?.toReleaseId !== event.releaseId
          || state.activation.phase !== "health-pending")
        fail("HEALTH_NOT_PENDING", "health pass has no pending activation");
      const previous = state.activation.fromReleaseId;
      const release = releaseOf(state, event.releaseId);
      release.status = "active";
      release.health = "passed";
      release.updatedAt = now;
      if (previous && previous !== event.releaseId) {
        const previousRelease = releaseOf(state, previous);
        previousRelease.status = "retiring";
        previousRelease.updatedAt = now;
      }
      state.lastKnownGoodReleaseId = event.releaseId;
      state.currentReleaseId = event.releaseId;
      state.candidate = null;
      state.activation = null;
      break;
    }
    case "HEALTH_FAIL": {
      if (state.activation?.toReleaseId !== event.releaseId
          || state.activation.phase !== "health-pending")
        fail("HEALTH_NOT_PENDING", "health failure has no pending activation");
      const previous = state.activation.fromReleaseId;
      const release = releaseOf(state, event.releaseId);
      release.status = "failed";
      release.health = "failed";
      release.failure = event.reason || "activation-health-failed";
      release.updatedAt = now;
      state.currentReleaseId = previous;
      if (previous) {
        const previousRelease = releaseOf(state, previous);
        previousRelease.status = "active";
      }
      state.candidate = { releaseId: event.releaseId, status: "failed" };
      state.activation = null;
      actions.push({ type: "delete-release-cache", releaseId: event.releaseId });
      actions.push({ type: "rollback-complete", releaseId: previous });
      break;
    }
    case "PIN_CLIENT": {
      const release = releaseOf(state, event.releaseId);
      if (!["ready", "active", "active-health-pending", "retiring"].includes(release.status))
        fail("RELEASE_NOT_PINNABLE", "client cannot pin an incomplete or failed release");
      const previous = state.clientPins[event.clientId];
      if (previous && previous !== event.releaseId)
        fail("CLIENT_ALREADY_PINNED", "client cannot hot-switch its pinned release", {
          clientId: event.clientId,
          previous,
          requested: event.releaseId,
        });
      state.clientPins[event.clientId] = event.releaseId;
      break;
    }
    case "UNPIN_CLIENT":
      delete state.clientPins[event.clientId];
      break;
    case "ROLLBACK": {
      const target = releaseOf(state, event.toReleaseId);
      if (target.health !== "passed" || target.status === "failed")
        fail("ROLLBACK_TARGET_UNAVAILABLE", "rollback target is not a healthy cached release");
      const from = state.currentReleaseId;
      if (from && from !== event.toReleaseId)
        releaseOf(state, from).status = "retiring";
      target.status = "active";
      state.currentReleaseId = event.toReleaseId;
      state.lastKnownGoodReleaseId = event.toReleaseId;
      state.candidate = null;
      state.activation = null;
      actions.push({ type: "reload-required", fromReleaseId: from, releaseId: event.toReleaseId });
      break;
    }
    case "REPAIR_COMMIT": {
      const release = releaseOf(state, event.releaseId);
      if (!["ready", "active", "retiring"].includes(release.status)
          || typeof event.cacheName !== "string" || !event.cacheName)
        fail("REPAIR_INVALID", "repair commit requires a cached usable release");
      const previousCacheName = release.cacheName;
      release.cacheName = event.cacheName;
      release.cachedBytes = event.cachedBytes;
      release.barrier = "repair-committed";
      release.updatedAt = now;
      if (previousCacheName && previousCacheName !== event.cacheName)
        actions.push({ type: "delete-cache-name", cacheName: previousCacheName });
      break;
    }
    case "EVICT": {
      const releaseId = event.releaseId;
      if (releaseId === state.currentReleaseId || releaseId === state.lastKnownGoodReleaseId
          || Object.values(state.clientPins).includes(releaseId))
        fail("RELEASE_PINNED", "active, known-good, or client-pinned release cannot be evicted", {
          releaseId,
        });
      releaseOf(state, releaseId);
      delete state.releases[releaseId];
      if (state.candidate?.releaseId === releaseId)
        state.candidate = null;
      actions.push({ type: "delete-release-cache", releaseId });
      break;
    }
    case "RECOVER": {
      for (const release of Object.values(state.releases)) {
        if (release.status === "staging") {
          release.status = "failed";
          release.health = "failed";
          release.failure = "interrupted-staging";
          actions.push({ type: "delete-release-cache", releaseId: release.releaseId });
          if (state.candidate?.releaseId === release.releaseId)
            state.candidate.status = "failed";
        }
      }
      if (state.activation?.phase === "prepared") {
        state.activation = null;
      } else if (state.activation?.phase === "health-pending") {
        const failedId = state.activation.toReleaseId;
        const previous = state.activation.fromReleaseId;
        const failedRelease = releaseOf(state, failedId);
        failedRelease.status = "failed";
        failedRelease.health = "failed";
        failedRelease.failure = "interrupted-health-check";
        state.currentReleaseId = previous;
        if (previous)
          releaseOf(state, previous).status = "active";
        state.candidate = { releaseId: failedId, status: "failed" };
        state.activation = null;
        actions.push({ type: "delete-release-cache", releaseId: failedId });
      }
      break;
    }
    default:
      fail("EVENT_UNKNOWN", `unknown release state event: ${event.type}`);
  }

  appendJournal(state, event, actions);
  assertValid(state);
  return { state, actions };
}

export function planReleaseEviction(state) {
  assertValid(state);
  const protectedIds = new Set([
    state.currentReleaseId,
    state.lastKnownGoodReleaseId,
    ...Object.values(state.clientPins),
  ].filter(Boolean));
  const releases = Object.values(state.releases);
  const priority = { failed: 0, staging: 1, retiring: 2, ready: 3,
    "active-health-pending": 4, active: 5 };
  const candidates = releases
    .filter((item) => !protectedIds.has(item.releaseId))
    .sort((left, right) => (priority[left.status] - priority[right.status])
      || (left.releaseId < right.releaseId ? -1 : 1));
  const excess = Math.max(0, releases.length - state.retentionLimit);
  const failed = candidates.filter((item) => ["failed", "staging"].includes(item.status));
  const selected = [...failed];
  for (const item of candidates) {
    if (selected.includes(item))
      continue;
    if (releases.length - selected.length <= state.retentionLimit)
      break;
    selected.push(item);
  }
  return {
    protectedReleaseIds: [...protectedIds].sort(),
    evictReleaseIds: selected.map((item) => item.releaseId),
    excess,
    boundedAfterPlan: releases.length - selected.length <= state.retentionLimit,
  };
}
