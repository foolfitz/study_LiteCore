import { createHash } from "node:crypto";

import {
  COLLABORATION_CONTRACT_VERSION,
  CollaborationError,
} from "./contract.js";

function hash(bytes) {
  return createHash("sha256").update(Buffer.from(bytes)).digest("hex");
}

function bytesOf(value) {
  return new TextEncoder().encode(value);
}

async function expectCode(code, operation) {
  try {
    await operation();
  } catch (error) {
    if (error?.code === code)
      return error;
    throw new Error(`expected ${code}, received ${error?.code || error}`, { cause: error });
  }
  throw new Error(`expected ${code}, but operation succeeded`);
}

export function createDomainAdapter(domain) {
  return {
    kind: "domain",
    reset: (options) => domain.reset(options),
    getDocument: (id) => domain.getDocument(id),
    getBlob: async (id, version) => {
      const result = domain.getBlob(id, version);
      return {
        bytes: result.bytes.buffer.slice(
          result.bytes.byteOffset,
          result.bytes.byteOffset + result.bytes.byteLength,
        ),
        etag: result.metadata.etag,
        blobSha256: result.metadata.blobSha256,
        version: result.metadata.version,
      };
    },
    getCollaboration: (id) => domain.collaborationSnapshot(id),
    heartbeat: (id, input) => domain.heartbeat(id, input),
    createComment: (id, input) => domain.createComment(id, input),
    resolveComment: (id, commentId, input) => domain.resolveComment(id, commentId, input),
    createSuggestion: (id, input) => domain.createSuggestion(id, input),
    decideSuggestion: (id, suggestionId, input) => domain.decideSuggestion(id, suggestionId, input),
    acquireLease: (id, input) => domain.acquireLease(id, input),
    renewLease: (id, leaseId, input) => domain.renewLease(id, leaseId, input),
    releaseLease: (id, leaseId, input) => domain.releaseLease(id, leaseId, input),
    putBlob: (id, input, bytes) => domain.putBlob(id, input, bytes),
    eventsSince: (id, sequence) => domain.eventsSince(id, sequence),
    advanceClock: (milliseconds) => domain.advanceClock(milliseconds),
    armFault: (phase) => domain.armFault(phase),
    debugState: (id) => domain.debugState(id),
    unknownMutation: () => {
      throw new CollaborationError("INVALID_ARGUMENT", "unknown mutation kind");
    },
  };
}

function requestFactory() {
  let number = 0;
  return (fields = {}) => ({
    contractVersion: COLLABORATION_CONTRACT_VERSION,
    requestId: `conformance-${++number}`,
    ...fields,
  });
}

function suggestionRequest(request, baseVersion = "v1", extra = {}) {
  return request({
    baseVersion,
    anchor: { quote: "LibreOfficeKit", prefix: "", suffix: "" },
    replacement: "LibreOfficeKit-R6",
    authorId: "bob",
    ...extra,
  });
}

function commitRequest(request, metadata, lease, bytes, extra = {}) {
  return request({
    baseVersion: metadata.version,
    ifMatch: metadata.etag,
    leaseId: lease.leaseId,
    token: lease.token,
    blobSha256: hash(bytes),
    createdBy: "alice",
    ...extra,
  });
}

export async function runConformance(adapter, fixture) {
  const documentId = fixture.documentId;
  const results = [];

  async function scenario(id, name, run) {
    const started = performance.now();
    try {
      const details = await run();
      results.push({ id, name, pass: true, durationMs: performance.now() - started, details });
    } catch (error) {
      results.push({
        id,
        name,
        pass: false,
        durationMs: performance.now() - started,
        error: { code: error?.code || "UNEXPECTED", message: String(error?.stack || error) },
      });
    }
  }

  await scenario(1, "immutable v1 metadata, ETag, hash and bytes agree", async () => {
    await adapter.reset();
    const metadata = (await adapter.getDocument(documentId)).data.current;
    const blob = await adapter.getBlob(documentId, "v1");
    const actual = hash(blob.bytes);
    if (metadata.version !== "v1" || metadata.etag !== `"sha256-${actual}"`
        || metadata.blobSha256 !== actual || metadata.bytes !== blob.bytes.byteLength
        || blob.etag !== metadata.etag)
      throw new Error("v1 metadata does not match immutable blob");
    return { version: metadata.version, etag: metadata.etag, sha256: actual, bytes: metadata.bytes };
  });

  await scenario(2, "presence heartbeat and deterministic TTL expiry", async () => {
    await adapter.reset();
    const request = requestFactory();
    await adapter.heartbeat(documentId, request({
      sessionId: "session-alice", actorId: "alice",
      displayName: fixture.actors.alice.displayName, viewedVersion: "v1",
    }));
    await adapter.heartbeat(documentId, request({
      sessionId: "session-bob", actorId: "bob",
      displayName: fixture.actors.bob.displayName, viewedVersion: "v1",
      locationHint: { page: 1 },
    }));
    const before = await adapter.getCollaboration(documentId);
    if (before.data.presence.length !== 2)
      throw new Error("both fixture identities must be present");
    await adapter.advanceClock(fixture.presenceTtlMs + 1);
    const after = await adapter.getCollaboration(documentId);
    const state = await adapter.debugState(documentId);
    const expiryEvents = state.events.filter((event) => event.type === "presence-expired");
    if (after.data.presence.length !== 0 || expiryEvents.length !== 2)
      throw new Error("presence TTL did not converge deterministically");
    return { before: 2, after: 0, expiryEvents: expiryEvents.length };
  });

  await scenario(3, "comment reply and resolve do not mutate the Office blob", async () => {
    await adapter.reset();
    const request = requestFactory();
    const before = (await adapter.getDocument(documentId)).data.current;
    const comment = (await adapter.createComment(documentId, request({
      baseVersion: "v1", parentId: null, body: "Bob comment", authorId: "bob",
    }))).data;
    const reply = (await adapter.createComment(documentId, request({
      baseVersion: "v1", parentId: comment.id, body: "Alice reply", authorId: "alice",
    }))).data;
    await adapter.resolveComment(documentId, comment.id, request({ actorId: "alice" }));
    const after = (await adapter.getDocument(documentId)).data.current;
    const state = await adapter.debugState(documentId);
    const types = state.events.map((event) => event.type);
    if (before.blobSha256 !== after.blobSha256 || before.version !== after.version
        || reply.parentId !== comment.id
        || types.join(",") !== "comment-created,comment-created,comment-resolved")
      throw new Error("sidecar comment sequence or blob isolation failed");
    return { types, blobSha256: after.blobSha256 };
  });

  await scenario(4, "suggestion schema rejects unsafe payloads", async () => {
    await adapter.reset();
    const request = requestFactory();
    await expectCode("INVALID_ARGUMENT", () => adapter.createSuggestion(
      documentId, suggestionRequest(request, "v1", {
        anchor: { quote: "", prefix: "", suffix: "" },
      }),
    ));
    await expectCode("INVALID_ARGUMENT", () => adapter.createSuggestion(
      documentId, suggestionRequest(request, "v1", { replacement: "" }),
    ));
    await expectCode("INVALID_ARGUMENT", () => adapter.createSuggestion(
      documentId, suggestionRequest(request, "v1", {
        replacement: "x".repeat(fixture.limits.replacementBytes + 1),
      }),
    ));
    await expectCode("INVALID_ARGUMENT", () => adapter.createSuggestion(
      documentId, { ...suggestionRequest(request), unknownMutationField: true },
    ));
    const snapshot = await adapter.getCollaboration(documentId);
    if (snapshot.data.suggestions.length !== 0)
      throw new Error("invalid suggestions mutated sidecar state");
    return { rejected: 4, suggestionCount: 0 };
  });

  await scenario(5, "single lease excludes Bob and never leaks its token", async () => {
    await adapter.reset();
    const request = requestFactory();
    const lease = (await adapter.acquireLease(documentId, request({ actorId: "alice", baseVersion: "v1" }))).data;
    await expectCode("LEASE_HELD", () => adapter.acquireLease(
      documentId, request({ actorId: "bob", baseVersion: "v1" }),
    ));
    const snapshot = await adapter.getCollaboration(documentId);
    const state = await adapter.debugState(documentId);
    if (snapshot.data.lease.token !== undefined
        || JSON.stringify(snapshot).includes(lease.token)
        || JSON.stringify(state.events).includes(lease.token))
      throw new Error("lease token leaked into snapshot or event");
    return { leaseId: lease.leaseId, holder: snapshot.data.lease.actorId, tokenRedacted: true };
  });

  await scenario(6, "lease plus CAS atomically creates v2 and accepts suggestion", async () => {
    await adapter.reset();
    const request = requestFactory();
    const before = (await adapter.getDocument(documentId)).data.current;
    const suggestion = (await adapter.createSuggestion(documentId, suggestionRequest(request))).data;
    const lease = (await adapter.acquireLease(documentId, request({ actorId: "alice", baseVersion: "v1" }))).data;
    const bytes = bytesOf("R6 conformance immutable version two");
    const committed = await adapter.putBlob(
      documentId,
      commitRequest(request, before, lease, bytes, { suggestionId: suggestion.id }),
      bytes,
    );
    const snapshot = await adapter.getCollaboration(documentId);
    const state = await adapter.debugState(documentId);
    const decided = snapshot.data.suggestions.find((item) => item.id === suggestion.id);
    if (committed.data.version.version !== "v2" || committed.data.version.parentVersion !== "v1"
        || decided.status !== "accepted" || decided.acceptedInVersion !== "v2"
        || snapshot.data.lease !== null || state.versionCount !== 2
        || !state.events.some((event) => event.type === "document-updated"))
      throw new Error("atomic blob/suggestion commit invariant failed");
    return { version: "v2", parentVersion: "v1", suggestionStatus: decided.status };
  });

  await scenario(7, "stale v1 compare-and-swap cannot create v3", async () => {
    await adapter.reset();
    const request = requestFactory();
    const v1 = (await adapter.getDocument(documentId)).data.current;
    const lease = (await adapter.acquireLease(documentId, request({ actorId: "alice", baseVersion: "v1" }))).data;
    const aliceBytes = bytesOf("Alice authoritative v2");
    await adapter.putBlob(documentId, commitRequest(request, v1, lease, aliceBytes), aliceBytes);
    const bobBytes = bytesOf("Bob stale bytes must not commit");
    await expectCode("VERSION_CONFLICT", () => adapter.putBlob(documentId, request({
      baseVersion: "v1", ifMatch: v1.etag, leaseId: "bob-old-lease", token: "bob-old-token",
      blobSha256: hash(bobBytes), createdBy: "bob",
    }), bobBytes));
    const state = await adapter.debugState(documentId);
    const current = (await adapter.getDocument(documentId)).data.current;
    if (state.versionCount !== 2 || current.blobSha256 !== hash(aliceBytes))
      throw new Error("stale submit caused lost update or extra version");
    return { error: "VERSION_CONFLICT", versionCount: 2, currentHash: current.blobSha256 };
  });

  await scenario(8, "wrong, expired and cross-document lease tokens are rejected", async () => {
    await adapter.reset();
    const request = requestFactory();
    const v1 = (await adapter.getDocument(documentId)).data.current;
    const bytes = bytesOf("invalid lease bytes");
    const lease = (await adapter.acquireLease(documentId, request({ actorId: "alice", baseVersion: "v1" }))).data;
    await expectCode("INVALID_LEASE", () => adapter.putBlob(documentId, {
      ...commitRequest(request, v1, lease, bytes), token: "wrong-token",
    }, bytes));
    await adapter.releaseLease(documentId, lease.leaseId, request({ token: lease.token }));
    const otherLease = (await adapter.acquireLease("r6-other-document", request({ actorId: "bob", baseVersion: "v1" }))).data;
    await expectCode("INVALID_LEASE", () => adapter.putBlob(documentId, {
      ...commitRequest(request, v1, otherLease, bytes),
    }, bytes));
    const expiring = (await adapter.acquireLease(documentId, request({ actorId: "alice", baseVersion: "v1" }))).data;
    await adapter.advanceClock(fixture.leaseTtlMs + 1);
    await expectCode("LEASE_EXPIRED", () => adapter.putBlob(
      documentId, commitRequest(request, v1, expiring, bytes), bytes,
    ));
    const state = await adapter.debugState(documentId);
    if (state.versionCount !== 1)
      throw new Error("invalid lease path mutated versions");
    return { rejected: ["INVALID_LEASE", "INVALID_LEASE", "LEASE_EXPIRED"], versionCount: 1 };
  });

  await scenario(9, "idempotency retries are stable and conflicting reuse is rejected", async () => {
    await adapter.reset();
    const fixed = {
      contractVersion: COLLABORATION_CONTRACT_VERSION,
      requestId: "fixed-idempotency-key",
      baseVersion: "v1", parentId: null, body: "same body", authorId: "alice",
    };
    const first = await adapter.createComment(documentId, fixed);
    const retry = await adapter.createComment(documentId, fixed);
    await expectCode("IDEMPOTENCY_CONFLICT", () => adapter.createComment(
      documentId, { ...fixed, body: "different body" },
    ));
    const snapshot = await adapter.getCollaboration(documentId);
    if (first.data.id !== retry.data.id || snapshot.data.comments.length !== 1)
      throw new Error("idempotent retry created duplicate state");
    return { commentId: first.data.id, count: 1, conflict: "IDEMPOTENCY_CONFLICT" };
  });

  await scenario(10, "event replay, duplicate de-duplication and snapshot fallback converge", async () => {
    await adapter.reset({ eventRetention: 3 });
    const request = requestFactory();
    for (let index = 0; index < 5; index += 1) {
      await adapter.createComment(documentId, request({
        baseVersion: "v1", parentId: null, body: `comment ${index}`, authorId: "alice",
      }));
    }
    const fallback = await adapter.eventsSince(documentId, 0);
    if (fallback.data.mode !== "snapshot" || fallback.data.snapshot.comments.length !== 5)
      throw new Error("evicted event gap did not require a complete snapshot");
    const tailStart = fallback.eventSequence - 2;
    const replay = await adapter.eventsSince(documentId, tailStart);
    if (replay.data.mode !== "replay" || replay.data.events.length !== 2)
      throw new Error("retained event gap did not replay exactly");
    const seen = new Set();
    for (const event of [...replay.data.events, ...replay.data.events])
      seen.add(event.eventSequence);
    if (seen.size !== replay.data.events.length)
      throw new Error("duplicate sequence did not de-duplicate");
    return {
      snapshotComments: fallback.data.snapshot.comments.length,
      replayed: replay.data.events.length,
      uniqueAfterDuplicate: seen.size,
    };
  });

  await scenario(11, "fault injection never leaves a partial version and post-commit retry recovers", async () => {
    await adapter.reset();
    let request = requestFactory();
    let v1 = (await adapter.getDocument(documentId)).data.current;
    let lease = (await adapter.acquireLease(documentId, request({ actorId: "alice", baseVersion: "v1" }))).data;
    let bytes = bytesOf("pre-commit fault candidate");
    let commit = commitRequest(request, v1, lease, bytes);
    await adapter.armFault("before-commit");
    await expectCode("FAULT_INJECTED", () => adapter.putBlob(documentId, commit, bytes));
    if ((await adapter.debugState(documentId)).versionCount !== 1)
      throw new Error("pre-commit fault produced a partial version");
    const recoveredBefore = await adapter.putBlob(documentId, commit, bytes);
    if (recoveredBefore.data.version.version !== "v2")
      throw new Error("retry after pre-commit fault did not commit v2");

    await adapter.reset();
    request = requestFactory();
    v1 = (await adapter.getDocument(documentId)).data.current;
    lease = (await adapter.acquireLease(documentId, request({ actorId: "alice", baseVersion: "v1" }))).data;
    bytes = bytesOf("post-commit response interruption");
    commit = commitRequest(request, v1, lease, bytes);
    await adapter.armFault("after-commit");
    await expectCode("RESPONSE_INTERRUPTED", () => adapter.putBlob(documentId, commit, bytes));
    const recoveredAfter = await adapter.putBlob(documentId, commit, bytes);
    const state = await adapter.debugState(documentId);
    if (recoveredAfter.data.version.version !== "v2" || state.versionCount !== 2)
      throw new Error("post-commit idempotency recovery created an extra version");
    return { beforeCommitVersionCount: 1, recoveredVersion: "v2", finalVersionCount: 2 };
  });

  await scenario(12, "contract major mismatch and unknown mutation are rejected", async () => {
    await adapter.reset();
    await expectCode("CONTRACT_VERSION_MISMATCH", () => adapter.createComment(documentId, {
      contractVersion: "2.0", requestId: "major-mismatch", baseVersion: "v1",
      parentId: null, body: "must fail", authorId: "alice",
    }));
    await expectCode("INVALID_ARGUMENT", () => adapter.unknownMutation(documentId, {
      contractVersion: "1.0", requestId: "unknown-mutation", kind: "generic-uno",
    }));
    if ((await adapter.getCollaboration(documentId)).data.comments.length !== 0)
      throw new Error("rejected contract request mutated state");
    return { rejected: ["CONTRACT_VERSION_MISMATCH", "INVALID_ARGUMENT"] };
  });

  return {
    schemaVersion: 1,
    release: "R6-B",
    adapter: adapter.kind,
    scenarios: results,
    passed: results.filter((result) => result.pass).length,
    failed: results.filter((result) => !result.pass).length,
    pass: results.length === 12 && results.every((result) => result.pass),
  };
}
