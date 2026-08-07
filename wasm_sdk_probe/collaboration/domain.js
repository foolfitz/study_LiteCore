import { createHash } from "node:crypto";

import {
  COLLABORATION_CONTRACT_VERSION,
  CollaborationError,
  ODT_MEDIA_TYPE,
  assertObject,
  assertOnlyKeys,
  assertOpaqueId,
  assertText,
  canonicalJson,
  clone,
  fail,
  validateMutationEnvelope,
  validateSuggestionInput,
} from "./contract.js";

export class DeterministicClock {
  constructor(epochMs = Date.parse("2026-08-02T00:00:00.000Z")) {
    this._now = epochMs;
  }

  now() {
    return this._now;
  }

  iso() {
    return new Date(this._now).toISOString();
  }

  advance(milliseconds) {
    if (!Number.isFinite(milliseconds) || milliseconds < 0)
      fail("INVALID_ARGUMENT", "clock advance must be non-negative");
    this._now += milliseconds;
    return this.iso();
  }
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function strongEtag(hash) {
  return `"sha256-${hash}"`;
}

function bytesCopy(bytes) {
  if (bytes instanceof ArrayBuffer)
    return Buffer.from(bytes.slice(0));
  if (ArrayBuffer.isView(bytes))
    return Buffer.from(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
  fail("INVALID_ARGUMENT", "blob body must be binary bytes");
}

function publicLease(lease) {
  if (!lease)
    return null;
  const { token: _token, ...safe } = lease;
  return clone(safe);
}

export class CollaborationDomain {
  constructor(options) {
    if (!options?.fixture || !options?.initialBytes)
      throw new TypeError("CollaborationDomain requires fixture and initialBytes");
    this.fixture = clone(options.fixture);
    this.initialBytes = bytesCopy(options.initialBytes);
    this.clock = options.clock || new DeterministicClock();
    this.audit = [];
    this._fault = null;
    this.reset();
  }

  reset(options = {}, replacementInitialBytes = null) {
    if (replacementInitialBytes)
      this.initialBytes = bytesCopy(replacementInitialBytes);
    this.documents = new Map();
    this._idCounter = 0;
    this._tokenCounter = 0;
    this._fault = null;
    this.audit.length = 0;
    const retention = options.eventRetention ?? this.fixture.eventRetention;
    this._seedDocument(this.fixture.documentId, retention);
    this._seedDocument("r6-other-document", retention);
    return this.getDocument(this.fixture.documentId);
  }

  _seedDocument(documentId, eventRetention) {
    const bytes = Buffer.from(this.initialBytes);
    const hash = sha256(bytes);
    const version = {
      documentId,
      version: "v1",
      etag: strongEtag(hash),
      blobSha256: hash,
      bytes: bytes.byteLength,
      mediaType: ODT_MEDIA_TYPE,
      createdAt: this.clock.iso(),
      createdBy: "fixture",
      parentVersion: null,
    };
    this.documents.set(documentId, {
      documentId,
      currentVersion: "v1",
      versions: new Map([["v1", { metadata: version, bytes }]]),
      versionOrder: ["v1"],
      comments: new Map(),
      suggestions: new Map(),
      presence: new Map(),
      lease: null,
      expiredLeases: new Map(),
      idempotency: new Map(),
      events: [],
      eventSequence: 0,
      eventRetention,
    });
  }

  _document(documentId) {
    assertOpaqueId(documentId, "documentId");
    const document = this.documents.get(documentId);
    if (!document)
      fail("NOT_FOUND", "unknown document", { documentId });
    this._sweep(document);
    return document;
  }

  _snapshotVersion(document) {
    return document.versionOrder.length;
  }

  _envelope(document, data, requestId) {
    return {
      contractVersion: COLLABORATION_CONTRACT_VERSION,
      ...(requestId ? { requestId } : {}),
      documentId: document.documentId,
      snapshotVersion: this._snapshotVersion(document),
      eventSequence: document.eventSequence,
      data: clone(data),
    };
  }

  _appendEvent(document, type, data) {
    const event = {
      contractVersion: COLLABORATION_CONTRACT_VERSION,
      documentId: document.documentId,
      snapshotVersion: this._snapshotVersion(document),
      eventSequence: ++document.eventSequence,
      type,
      createdAt: this.clock.iso(),
      data: clone(data),
    };
    document.events.push(event);
    while (document.events.length > document.eventRetention)
      document.events.shift();
    this.audit.push({
      at: event.createdAt,
      documentId: document.documentId,
      eventSequence: event.eventSequence,
      type,
      data: clone(data),
    });
    return event;
  }

  _sweep(document) {
    const now = this.clock.now();
    for (const [sessionId, presence] of document.presence) {
      if (Date.parse(presence.expiresAt) <= now) {
        document.presence.delete(sessionId);
        this._appendEvent(document, "presence-expired", {
          sessionId,
          actorId: presence.actorId,
        });
      }
    }
    if (document.lease && Date.parse(document.lease.expiresAt) <= now) {
      const expired = document.lease;
      document.lease = null;
      document.expiredLeases.set(expired.leaseId, clone(expired));
      this._appendEvent(document, "lease-expired", {
        leaseId: expired.leaseId,
        actorId: expired.actorId,
        baseVersion: expired.baseVersion,
      });
    }
  }

  _newId(prefix) {
    this._idCounter += 1;
    return `${prefix}-${this._idCounter}`;
  }

  _newToken() {
    this._tokenCounter += 1;
    return `secret-r6-token-${this._tokenCounter}`;
  }

  _assertActor(actorId) {
    assertOpaqueId(actorId, "actorId");
    const allowed = Object.values(this.fixture.actors).some((actor) => actor.actorId === actorId);
    if (!allowed)
      fail("INVALID_ARGUMENT", "actor is not an allowed fixture identity", { actorId });
    return actorId;
  }

  _idempotent(document, request, operation) {
    const requestId = assertOpaqueId(request.requestId, "requestId");
    const fingerprint = canonicalJson(request);
    const prior = document.idempotency.get(requestId);
    if (prior) {
      if (prior.fingerprint !== fingerprint)
        fail("IDEMPOTENCY_CONFLICT", "requestId was already used with different content", { requestId });
      return clone(prior.result);
    }
    const result = operation();
    document.idempotency.set(requestId, { fingerprint, result: clone(result) });
    return result;
  }

  _current(document) {
    return document.versions.get(document.currentVersion);
  }

  getDocument(documentId) {
    const document = this._document(documentId);
    return this._envelope(document, {
      current: this._current(document).metadata,
      versionCount: document.versionOrder.length,
    });
  }

  getBlob(documentId, version) {
    const document = this._document(documentId);
    const entry = document.versions.get(version);
    if (!entry)
      fail("NOT_FOUND", "unknown document version", { documentId, version });
    return { metadata: clone(entry.metadata), bytes: Buffer.from(entry.bytes) };
  }

  collaborationSnapshot(documentId) {
    const document = this._document(documentId);
    return this._envelope(document, {
      current: this._current(document).metadata,
      presence: [...document.presence.values()].map(clone),
      comments: [...document.comments.values()].map(clone),
      suggestions: [...document.suggestions.values()].map(clone),
      lease: publicLease(document.lease),
    });
  }

  heartbeat(documentId, candidate) {
    const document = this._document(documentId);
    validateMutationEnvelope(candidate, ["sessionId", "actorId", "displayName", "viewedVersion", "locationHint"]);
    assertOpaqueId(candidate.sessionId, "sessionId");
    this._assertActor(candidate.actorId);
    assertText(candidate.displayName, "displayName", 256);
    if (!document.versions.has(candidate.viewedVersion))
      fail("VERSION_CONFLICT", "presence viewedVersion does not exist", { viewedVersion: candidate.viewedVersion });
    if (candidate.locationHint !== undefined) {
      assertObject(candidate.locationHint, "locationHint");
      assertOnlyKeys(candidate.locationHint, ["part", "page"], "locationHint");
    }
    return this._idempotent(document, candidate, () => {
      const presence = {
        sessionId: candidate.sessionId,
        actorId: candidate.actorId,
        displayName: candidate.displayName,
        viewedVersion: candidate.viewedVersion,
        ...(candidate.locationHint ? { locationHint: clone(candidate.locationHint) } : {}),
        lastSeenAt: this.clock.iso(),
        expiresAt: new Date(this.clock.now() + this.fixture.presenceTtlMs).toISOString(),
      };
      document.presence.set(presence.sessionId, presence);
      this._appendEvent(document, "presence-upserted", publicLease(presence));
      return this._envelope(document, presence, candidate.requestId);
    });
  }

  createComment(documentId, candidate) {
    const document = this._document(documentId);
    validateMutationEnvelope(candidate, ["baseVersion", "parentId", "body", "authorId"]);
    assertOpaqueId(candidate.baseVersion, "baseVersion");
    this._assertActor(candidate.authorId);
    assertText(candidate.body, "body", this.fixture.limits.commentBytes);
    if (!document.versions.has(candidate.baseVersion))
      fail("VERSION_CONFLICT", "comment baseVersion does not exist");
    if (candidate.parentId !== null && candidate.parentId !== undefined
        && !document.comments.has(candidate.parentId))
      fail("NOT_FOUND", "comment parent does not exist", { parentId: candidate.parentId });
    return this._idempotent(document, candidate, () => {
      const comment = {
        id: this._newId("comment"),
        documentId,
        baseVersion: candidate.baseVersion,
        parentId: candidate.parentId ?? null,
        body: candidate.body,
        authorId: candidate.authorId,
        status: "open",
        createdAt: this.clock.iso(),
      };
      document.comments.set(comment.id, comment);
      this._appendEvent(document, "comment-created", comment);
      return this._envelope(document, comment, candidate.requestId);
    });
  }

  resolveComment(documentId, commentId, candidate) {
    const document = this._document(documentId);
    validateMutationEnvelope(candidate, ["actorId"]);
    this._assertActor(candidate.actorId);
    const comment = document.comments.get(commentId);
    if (!comment)
      fail("NOT_FOUND", "comment does not exist", { commentId });
    return this._idempotent(document, { ...candidate, commentId }, () => {
      if (comment.status === "open") {
        comment.status = "resolved";
        comment.resolvedAt = this.clock.iso();
        comment.resolvedBy = candidate.actorId;
        this._appendEvent(document, "comment-resolved", {
          id: comment.id,
          resolvedAt: comment.resolvedAt,
          resolvedBy: comment.resolvedBy,
        });
      }
      return this._envelope(document, comment, candidate.requestId);
    });
  }

  createSuggestion(documentId, candidate) {
    const document = this._document(documentId);
    const validated = validateSuggestionInput(candidate, this.fixture.limits);
    this._assertActor(validated.authorId);
    if (!document.versions.has(validated.baseVersion))
      fail("VERSION_CONFLICT", "suggestion baseVersion does not exist");
    return this._idempotent(document, validated, () => {
      const suggestion = {
        id: this._newId("suggestion"),
        documentId,
        baseVersion: validated.baseVersion,
        anchor: clone(validated.anchor),
        replacement: validated.replacement,
        authorId: validated.authorId,
        status: "open",
        createdAt: this.clock.iso(),
        ...(validated.audit ? { audit: clone(validated.audit) } : {}),
      };
      document.suggestions.set(suggestion.id, suggestion);
      this._appendEvent(document, "suggestion-created", suggestion);
      return this._envelope(document, suggestion, validated.requestId);
    });
  }

  decideSuggestion(documentId, suggestionId, candidate) {
    const document = this._document(documentId);
    validateMutationEnvelope(candidate, ["actorId", "decision", "reason"]);
    this._assertActor(candidate.actorId);
    if (!["rejected", "conflict"].includes(candidate.decision))
      fail("INVALID_ARGUMENT", "decision endpoint accepts only rejected or conflict");
    if (candidate.reason !== undefined)
      assertText(candidate.reason, "reason", 1024);
    const suggestion = document.suggestions.get(suggestionId);
    if (!suggestion)
      fail("NOT_FOUND", "suggestion does not exist", { suggestionId });
    return this._idempotent(document, { ...candidate, suggestionId }, () => {
      if (suggestion.status !== "open")
        fail("VERSION_CONFLICT", "suggestion is already decided", { status: suggestion.status });
      suggestion.status = candidate.decision;
      suggestion.decidedAt = this.clock.iso();
      suggestion.decidedBy = candidate.actorId;
      if (candidate.reason)
        suggestion.conflictReason = candidate.reason;
      this._appendEvent(document, "suggestion-decided", suggestion);
      return this._envelope(document, suggestion, candidate.requestId);
    });
  }

  acquireLease(documentId, candidate) {
    const document = this._document(documentId);
    validateMutationEnvelope(candidate, ["actorId", "baseVersion"]);
    this._assertActor(candidate.actorId);
    if (candidate.baseVersion !== document.currentVersion)
      fail("VERSION_CONFLICT", "lease baseVersion is not current", { currentVersion: document.currentVersion });
    return this._idempotent(document, candidate, () => {
      if (document.lease)
        fail("LEASE_HELD", "document already has an active lease", { lease: publicLease(document.lease) });
      const lease = {
        leaseId: this._newId("lease"),
        token: this._newToken(),
        documentId,
        actorId: candidate.actorId,
        baseVersion: candidate.baseVersion,
        issuedAt: this.clock.iso(),
        expiresAt: new Date(this.clock.now() + this.fixture.leaseTtlMs).toISOString(),
      };
      document.lease = lease;
      this._appendEvent(document, "lease-acquired", publicLease(lease));
      return this._envelope(document, lease, candidate.requestId);
    });
  }

  _validateLease(document, leaseId, token, baseVersion) {
    const lease = document.lease;
    if (!lease) {
      const expired = document.expiredLeases.get(leaseId);
      if (expired && expired.token === token)
        fail("LEASE_EXPIRED", "edit lease has expired", { leaseId });
      fail("INVALID_LEASE", "no matching active lease", { leaseId });
    }
    if (lease.leaseId !== leaseId || lease.token !== token)
      fail("INVALID_LEASE", "lease id or token is invalid", { leaseId });
    if (lease.baseVersion !== baseVersion || document.currentVersion !== baseVersion)
      fail("VERSION_CONFLICT", "lease base version is stale", { currentVersion: document.currentVersion });
    return lease;
  }

  renewLease(documentId, leaseId, candidate) {
    const document = this._document(documentId);
    validateMutationEnvelope(candidate, ["token", "baseVersion"]);
    assertOpaqueId(candidate.token, "token");
    const lease = this._validateLease(document, leaseId, candidate.token, candidate.baseVersion);
    return this._idempotent(document, { ...candidate, leaseId }, () => {
      lease.expiresAt = new Date(this.clock.now() + this.fixture.leaseTtlMs).toISOString();
      return this._envelope(document, lease, candidate.requestId);
    });
  }

  releaseLease(documentId, leaseId, candidate) {
    const document = this._document(documentId);
    validateMutationEnvelope(candidate, ["token"]);
    assertOpaqueId(candidate.token, "token");
    return this._idempotent(document, { ...candidate, leaseId }, () => {
      if (!document.lease) {
        const expired = document.expiredLeases.get(leaseId);
        if (expired && expired.token === candidate.token)
          return this._envelope(document, { released: false, leaseId }, candidate.requestId);
        fail("INVALID_LEASE", "no matching active lease", { leaseId });
      }
      if (document.lease.leaseId !== leaseId || document.lease.token !== candidate.token)
        fail("INVALID_LEASE", "lease id or token is invalid", { leaseId });
      const released = document.lease;
      document.lease = null;
      this._appendEvent(document, "lease-released", {
        leaseId: released.leaseId,
        actorId: released.actorId,
        baseVersion: released.baseVersion,
      });
      return this._envelope(document, { released: true, leaseId }, candidate.requestId);
    });
  }

  armFault(phase) {
    if (!["before-commit", "after-commit"].includes(phase))
      fail("INVALID_ARGUMENT", "unknown fault injection phase", { phase });
    this._fault = phase;
  }

  _consumeFault(phase) {
    if (this._fault !== phase)
      return false;
    this._fault = null;
    return true;
  }

  putBlob(documentId, candidate, binary) {
    const document = this._document(documentId);
    validateMutationEnvelope(candidate, [
      "baseVersion", "ifMatch", "leaseId", "token", "blobSha256", "createdBy", "suggestionId",
    ]);
    for (const key of ["baseVersion", "leaseId", "token"])
      assertOpaqueId(candidate[key], key);
    this._assertActor(candidate.createdBy);
    assertText(candidate.ifMatch, "ifMatch", 256);
    if (!/^[a-f0-9]{64}$/.test(candidate.blobSha256))
      fail("INVALID_ARGUMENT", "blobSha256 must be lowercase SHA-256 hex");
    const bytes = bytesCopy(binary);
    if (bytes.byteLength === 0 || bytes.byteLength > this.fixture.limits.blobBytes)
      fail("INVALID_ARGUMENT", "blob size is outside the configured limit", { bytes: bytes.byteLength });
    const fingerprintRequest = { ...candidate, bytes: bytes.byteLength };
    const fingerprint = canonicalJson(fingerprintRequest);
    const prior = document.idempotency.get(candidate.requestId);
    if (prior) {
      if (prior.fingerprint !== fingerprint)
        fail("IDEMPOTENCY_CONFLICT", "requestId was already used with different content", { requestId: candidate.requestId });
      return clone(prior.result);
    }
    const current = this._current(document);
    if (candidate.baseVersion !== document.currentVersion || candidate.ifMatch !== current.metadata.etag) {
      fail("VERSION_CONFLICT", "blob compare-and-swap validator is stale", {
        currentVersion: document.currentVersion,
        currentEtag: current.metadata.etag,
      });
    }
    this._validateLease(document, candidate.leaseId, candidate.token, candidate.baseVersion);
    const actualHash = sha256(bytes);
    if (actualHash !== candidate.blobSha256)
      fail("HASH_MISMATCH", "blob SHA-256 does not match request", { actual: actualHash });
    const suggestion = candidate.suggestionId
      ? document.suggestions.get(candidate.suggestionId)
      : null;
    if (candidate.suggestionId && !suggestion)
      fail("NOT_FOUND", "suggestion does not exist", { suggestionId: candidate.suggestionId });
    if (suggestion && (suggestion.status !== "open" || suggestion.baseVersion !== document.currentVersion)) {
      fail("VERSION_CONFLICT", "suggestion is not open on the current version", {
        suggestionStatus: suggestion.status,
        suggestionBaseVersion: suggestion.baseVersion,
      });
    }
    if (this._consumeFault("before-commit"))
      fail("FAULT_INJECTED", "fault injected before atomic commit");

    const previousVersion = document.currentVersion;
    const versionId = `v${document.versionOrder.length + 1}`;
    const metadata = {
      documentId,
      version: versionId,
      etag: strongEtag(actualHash),
      blobSha256: actualHash,
      bytes: bytes.byteLength,
      mediaType: ODT_MEDIA_TYPE,
      createdAt: this.clock.iso(),
      createdBy: candidate.createdBy,
      parentVersion: previousVersion,
    };
    document.versions.set(versionId, { metadata, bytes: Buffer.from(bytes) });
    document.versionOrder.push(versionId);
    document.currentVersion = versionId;
    if (suggestion) {
      suggestion.status = "accepted";
      suggestion.decidedAt = this.clock.iso();
      suggestion.decidedBy = candidate.createdBy;
      suggestion.acceptedInVersion = versionId;
      this._appendEvent(document, "suggestion-decided", suggestion);
    }
    const releasedLease = document.lease;
    document.lease = null;
    this._appendEvent(document, "document-updated", {
      previousVersion,
      version: versionId,
      etag: metadata.etag,
      blobSha256: metadata.blobSha256,
    });
    this._appendEvent(document, "lease-released", {
      leaseId: releasedLease.leaseId,
      actorId: releasedLease.actorId,
      baseVersion: releasedLease.baseVersion,
    });
    const result = this._envelope(document, {
      version: metadata,
      suggestion: suggestion ? clone(suggestion) : null,
    }, candidate.requestId);
    document.idempotency.set(candidate.requestId, { fingerprint, result: clone(result) });
    if (this._consumeFault("after-commit"))
      fail("RESPONSE_INTERRUPTED", "response interrupted after committed mutation", { requestId: candidate.requestId });
    return result;
  }

  eventsSince(documentId, lastEventSequence) {
    const document = this._document(documentId);
    if (!Number.isInteger(lastEventSequence) || lastEventSequence < 0)
      fail("INVALID_ARGUMENT", "last event sequence must be a non-negative integer");
    const firstAvailable = document.events[0]?.eventSequence ?? document.eventSequence + 1;
    if (lastEventSequence > document.eventSequence)
      fail("EVENT_GAP", "client event sequence is ahead of the service", { current: document.eventSequence });
    if (lastEventSequence < firstAvailable - 1) {
      return this._envelope(document, {
        mode: "snapshot",
        event: {
          type: "snapshot-required",
          eventSequence: document.eventSequence,
        },
        snapshot: this.collaborationSnapshot(documentId).data,
      });
    }
    return this._envelope(document, {
      mode: "replay",
      events: document.events.filter((event) => event.eventSequence > lastEventSequence).map(clone),
    });
  }

  advanceClock(milliseconds) {
    this.clock.advance(milliseconds);
    for (const document of this.documents.values())
      this._sweep(document);
    return { now: this.clock.iso() };
  }

  debugState(documentId) {
    const document = this._document(documentId);
    return {
      currentVersion: document.currentVersion,
      versionCount: document.versionOrder.length,
      versions: document.versionOrder.map((version) => clone(document.versions.get(version).metadata)),
      eventSequence: document.eventSequence,
      events: document.events.map(clone),
      idempotencyCount: document.idempotency.size,
      audit: this.audit.filter((entry) => entry.documentId === documentId).map(clone),
    };
  }
}

export { CollaborationError };
