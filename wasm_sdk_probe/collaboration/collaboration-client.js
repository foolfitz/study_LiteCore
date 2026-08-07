import {
  COLLABORATION_CONTRACT_VERSION,
  CollaborationError,
} from "./contract.js";

export class CollaborationClient {
  constructor(options) {
    this.baseUrl = String(options?.baseUrl || "").replace(/\/$/, "");
    this.fetch = options?.fetch || globalThis.fetch?.bind(globalThis);
    if (!this.baseUrl || !this.fetch)
      throw new TypeError("CollaborationClient requires baseUrl and fetch");
    this.lastEventSequence = new Map();
  }

  async _request(path, options = {}) {
    const response = await this.fetch(`${this.baseUrl}${path}`, options);
    const contentType = response.headers.get("content-type") || "";
    if (!response.ok) {
      const payload = contentType.includes("application/json")
        ? await response.json()
        : { error: { code: "HTTP_ERROR", message: await response.text(), details: {} } };
      throw new CollaborationError(
        payload.error?.code || "HTTP_ERROR",
        payload.error?.message || `HTTP ${response.status}`,
        payload.error?.details || {},
      );
    }
    if (contentType.includes("application/json"))
      return response.json();
    return {
      bytes: await response.arrayBuffer(),
      etag: response.headers.get("etag"),
      blobSha256: response.headers.get("x-blob-sha256"),
      version: response.headers.get("x-document-version"),
    };
  }

  _json(path, method, body) {
    return this._request(path, {
      method,
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  getDocument(documentId) {
    return this._request(`/api/documents/${encodeURIComponent(documentId)}`);
  }

  getBlob(documentId, version) {
    return this._request(`/api/documents/${encodeURIComponent(documentId)}/versions/${encodeURIComponent(version)}/blob`);
  }

  getCollaboration(documentId) {
    return this._request(`/api/documents/${encodeURIComponent(documentId)}/collaboration`);
  }

  heartbeat(documentId, input) {
    return this._json(`/api/documents/${encodeURIComponent(documentId)}/presence`, "POST", input);
  }

  createComment(documentId, input) {
    return this._json(`/api/documents/${encodeURIComponent(documentId)}/comments`, "POST", input);
  }

  resolveComment(documentId, commentId, input) {
    return this._json(`/api/documents/${encodeURIComponent(documentId)}/comments/${encodeURIComponent(commentId)}/resolve`, "POST", input);
  }

  createSuggestion(documentId, input) {
    return this._json(`/api/documents/${encodeURIComponent(documentId)}/suggestions`, "POST", input);
  }

  decideSuggestion(documentId, suggestionId, input) {
    return this._json(`/api/documents/${encodeURIComponent(documentId)}/suggestions/${encodeURIComponent(suggestionId)}/decision`, "POST", input);
  }

  acquireLease(documentId, input) {
    return this._json(`/api/documents/${encodeURIComponent(documentId)}/lease`, "POST", input);
  }

  renewLease(documentId, leaseId, input) {
    return this._json(`/api/documents/${encodeURIComponent(documentId)}/lease/${encodeURIComponent(leaseId)}/renew`, "POST", input);
  }

  releaseLease(documentId, leaseId, input) {
    return this._json(`/api/documents/${encodeURIComponent(documentId)}/lease/${encodeURIComponent(leaseId)}`, "DELETE", input);
  }

  putBlob(documentId, input, bytes) {
    return this._request(`/api/documents/${encodeURIComponent(documentId)}/blob`, {
      method: "PUT",
      headers: {
        "content-type": "application/vnd.oasis.opendocument.text",
        "x-contract-version": input.contractVersion,
        "x-request-id": input.requestId,
        "x-base-version": input.baseVersion,
        "if-match": input.ifMatch,
        "x-lease-id": input.leaseId,
        "x-lease-token": input.token,
        "x-blob-sha256": input.blobSha256,
        "x-created-by": input.createdBy,
        ...(input.suggestionId ? { "x-suggestion-id": input.suggestionId } : {}),
      },
      body: bytes,
    });
  }

  eventsSince(documentId, lastEventSequence = this.lastEventSequence.get(documentId) || 0) {
    return this._request(`/api/documents/${encodeURIComponent(documentId)}/events?lastEventSequence=${lastEventSequence}`);
  }

  async convergeEvents(documentId, applyEvent, lastEventSequence = this.lastEventSequence.get(documentId) || 0) {
    const response = await this.eventsSince(documentId, lastEventSequence);
    if (response.contractVersion.split(".")[0] !== COLLABORATION_CONTRACT_VERSION.split(".")[0])
      throw new CollaborationError("CONTRACT_VERSION_MISMATCH", "event contract major mismatch");
    if (response.data.mode === "snapshot") {
      this.lastEventSequence.set(documentId, response.eventSequence);
      return { mode: "snapshot", snapshot: response.data.snapshot, applied: 0 };
    }
    let sequence = lastEventSequence;
    let applied = 0;
    for (const event of response.data.events) {
      if (event.eventSequence <= sequence)
        continue;
      if (event.eventSequence !== sequence + 1)
        throw new CollaborationError("EVENT_GAP", "event stream contains a sequence gap", {
          expected: sequence + 1,
          actual: event.eventSequence,
        });
      await applyEvent?.(event);
      sequence = event.eventSequence;
      applied += 1;
    }
    this.lastEventSequence.set(documentId, sequence);
    return { mode: "replay", applied, lastEventSequence: sequence };
  }

  reset(options = {}) {
    return this._json("/__test/reset", "POST", options);
  }

  advanceClock(milliseconds) {
    return this._json("/__test/clock", "POST", { milliseconds });
  }

  armFault(phase) {
    return this._json("/__test/fault", "POST", { phase });
  }

  debugState(documentId) {
    return this._request(`/__test/state/${encodeURIComponent(documentId)}`);
  }

  unknownMutation(documentId, input) {
    return this._json(`/api/documents/${encodeURIComponent(documentId)}/mutations`, "POST", input);
  }
}
