export const COLLABORATION_CONTRACT_VERSION = "1.0";
export const ODT_MEDIA_TYPE = "application/vnd.oasis.opendocument.text";

export const ERROR_CODES = Object.freeze([
  "CONTRACT_VERSION_MISMATCH",
  "INVALID_ARGUMENT",
  "NOT_FOUND",
  "IDEMPOTENCY_CONFLICT",
  "VERSION_CONFLICT",
  "LEASE_HELD",
  "LEASE_EXPIRED",
  "INVALID_LEASE",
  "ANCHOR_NOT_FOUND",
  "ANCHOR_AMBIGUOUS",
  "EVENT_GAP",
  "HASH_MISMATCH",
  "FAULT_INJECTED",
  "RESPONSE_INTERRUPTED",
]);

export class CollaborationError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "CollaborationError";
    this.code = code;
    this.details = details;
  }
}

export function fail(code, message, details = {}) {
  throw new CollaborationError(code, message, details);
}

export function assertContractVersion(version) {
  if (typeof version !== "string" || !/^\d+\.\d+$/.test(version))
    fail("CONTRACT_VERSION_MISMATCH", "contract version must use major.minor form");
  const [major] = version.split(".").map(Number);
  if (major !== 1) {
    fail("CONTRACT_VERSION_MISMATCH", "collaboration contract major version mismatch", {
      expected: COLLABORATION_CONTRACT_VERSION,
      actual: version,
    });
  }
  return version;
}

export function isPlainObject(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value))
    return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

export function assertObject(value, label = "request") {
  if (!isPlainObject(value))
    fail("INVALID_ARGUMENT", `${label} must be a plain object`);
}

export function assertOnlyKeys(value, keys, label = "request") {
  const allowed = new Set(keys);
  const unknown = Object.keys(value).filter((key) => !allowed.has(key));
  if (unknown.length)
    fail("INVALID_ARGUMENT", `${label} contains unknown fields`, { fields: unknown });
}

export function assertOpaqueId(value, label) {
  if (typeof value !== "string" || value.length < 1 || value.length > 128
      || !/^[A-Za-z0-9._:-]+$/.test(value)) {
    fail("INVALID_ARGUMENT", `${label} must be an opaque identifier`);
  }
  return value;
}

export function utf8Bytes(value) {
  return new TextEncoder().encode(value).byteLength;
}

export function assertText(value, label, maximumBytes, { allowEmpty = false } = {}) {
  if (typeof value !== "string" || (!allowEmpty && value.length === 0))
    fail("INVALID_ARGUMENT", `${label} must be ${allowEmpty ? "text" : "non-empty text"}`);
  const bytes = utf8Bytes(value);
  if (bytes > maximumBytes)
    fail("INVALID_ARGUMENT", `${label} exceeds its UTF-8 byte limit`, { bytes, maximumBytes });
  return value;
}

export function canonicalJson(value) {
  if (Array.isArray(value))
    return `[${value.map(canonicalJson).join(",")}]`;
  if (isPlainObject(value)) {
    return `{${Object.keys(value).sort().map((key) =>
      `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function clone(value) {
  return structuredClone(value);
}

export function validateMutationEnvelope(candidate, allowedKeys) {
  assertObject(candidate);
  assertOnlyKeys(candidate, ["contractVersion", "requestId", ...allowedKeys]);
  assertContractVersion(candidate.contractVersion);
  assertOpaqueId(candidate.requestId, "requestId");
  return candidate;
}

export function validateSuggestionInput(candidate, limits) {
  validateMutationEnvelope(candidate, ["baseVersion", "anchor", "replacement", "authorId", "audit"]);
  assertOpaqueId(candidate.baseVersion, "baseVersion");
  assertOpaqueId(candidate.authorId, "authorId");
  assertObject(candidate.anchor, "anchor");
  assertOnlyKeys(candidate.anchor, ["quote", "prefix", "suffix", "locationHint"], "anchor");
  assertText(candidate.anchor.quote, "anchor.quote", limits.quoteBytes);
  assertText(candidate.anchor.prefix, "anchor.prefix", limits.contextBytes, { allowEmpty: true });
  assertText(candidate.anchor.suffix, "anchor.suffix", limits.contextBytes, { allowEmpty: true });
  assertText(candidate.replacement, "replacement", limits.replacementBytes);
  if (candidate.anchor.locationHint !== undefined) {
    assertObject(candidate.anchor.locationHint, "anchor.locationHint");
    assertOnlyKeys(candidate.anchor.locationHint, ["part", "rectangles"], "anchor.locationHint");
    if (candidate.anchor.locationHint.rectangles !== undefined)
      assertText(candidate.anchor.locationHint.rectangles, "locationHint.rectangles", limits.contextBytes);
  }
  if (candidate.audit !== undefined) {
    assertObject(candidate.audit, "audit");
    assertOnlyKeys(candidate.audit, ["providerId", "endpointId", "invocationId"], "audit");
    for (const [key, value] of Object.entries(candidate.audit))
      assertText(value, `audit.${key}`, 128);
  }
  return clone(candidate);
}

export function publicError(error, context = {}) {
  const code = error instanceof CollaborationError ? error.code : "INTERNAL_ERROR";
  const message = error instanceof CollaborationError ? error.message : "internal service error";
  return {
    contractVersion: COLLABORATION_CONTRACT_VERSION,
    requestId: context.requestId,
    documentId: context.documentId,
    snapshotVersion: context.snapshotVersion ?? 0,
    eventSequence: context.eventSequence ?? 0,
    error: { code, message, details: error instanceof CollaborationError ? error.details : {} },
  };
}
