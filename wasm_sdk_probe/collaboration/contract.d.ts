export const COLLABORATION_CONTRACT_VERSION: "1.0";
export const ODT_MEDIA_TYPE: "application/vnd.oasis.opendocument.text";

export type ContractEnvelope<T> = {
  contractVersion: "1.0";
  requestId?: string;
  documentId: string;
  snapshotVersion: number;
  eventSequence: number;
  data: T;
};

export type DocumentVersion = {
  documentId: string;
  version: string;
  etag: string;
  blobSha256: string;
  bytes: number;
  mediaType: typeof ODT_MEDIA_TYPE;
  createdAt: string;
  createdBy: string;
  parentVersion: string | null;
};

export type Presence = {
  sessionId: string;
  actorId: string;
  displayName: string;
  viewedVersion: string;
  locationHint?: { part?: string | number; page?: number };
  lastSeenAt: string;
  expiresAt: string;
};

export type SidecarComment = {
  id: string;
  documentId: string;
  baseVersion: string;
  parentId: string | null;
  body: string;
  authorId: string;
  status: "open" | "resolved";
  createdAt: string;
  resolvedAt?: string;
  resolvedBy?: string;
};

export type Suggestion = {
  id: string;
  documentId: string;
  baseVersion: string;
  anchor: {
    quote: string;
    prefix: string;
    suffix: string;
    locationHint?: { part?: string | number; rectangles?: string };
  };
  replacement: string;
  authorId: string;
  status: "open" | "accepted" | "rejected" | "conflict";
  createdAt: string;
  decidedAt?: string;
  decidedBy?: string;
  acceptedInVersion?: string;
  conflictReason?: string;
  audit?: { providerId: string; endpointId: string; invocationId: string };
};

export type EditLease = {
  leaseId: string;
  token: string;
  documentId: string;
  actorId: string;
  baseVersion: string;
  issuedAt: string;
  expiresAt: string;
};

export type CollaborationErrorCode =
  | "CONTRACT_VERSION_MISMATCH" | "INVALID_ARGUMENT" | "NOT_FOUND"
  | "IDEMPOTENCY_CONFLICT" | "VERSION_CONFLICT" | "LEASE_HELD"
  | "LEASE_EXPIRED" | "INVALID_LEASE" | "ANCHOR_NOT_FOUND"
  | "ANCHOR_AMBIGUOUS" | "EVENT_GAP" | "HASH_MISMATCH"
  | "FAULT_INJECTED" | "RESPONSE_INTERRUPTED";

export class CollaborationError extends Error {
  code: CollaborationErrorCode | string;
  details: Record<string, unknown>;
  constructor(code: CollaborationErrorCode | string, message: string, details?: Record<string, unknown>);
}

export function assertContractVersion(version: unknown): string;
export function validateMutationEnvelope(candidate: unknown, allowedKeys: string[]): Record<string, unknown>;
export function validateSuggestionInput(candidate: unknown, limits: Record<string, number>): Record<string, unknown>;
