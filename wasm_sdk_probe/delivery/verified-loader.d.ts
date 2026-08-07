export type FidelityPolicy = "standard" | "full-fidelity";
export type TransportEncoding = "identity" | "gzip";
export type CacheMode = "cold" | "warm";

export class DeliveryError extends Error {
  code: string;
  details: Readonly<Record<string, unknown>>;
}

export interface VerifyReleaseOptions {
  manifestUrl: string | URL;
  policy?: FidelityPolicy;
  transport?: TransportEncoding;
  cacheMode?: CacheMode;
  signal?: AbortSignal | null;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
  urlTransform?: (role: string, url: URL) => URL | string;
  artifactOrigin?: string | URL | null;
  requireIsolation?: boolean;
  crossOriginIsolated?: boolean;
  onArtifactVerified?: ((item: {
    releaseId: string;
    artifact: Record<string, unknown>;
    verified: Record<string, unknown>;
    buffer: ArrayBuffer;
  }) => void | Promise<void>) | null;
}

export interface VerifiedRelease {
  schemaVersion: number;
  releaseId: string;
  policy: FidelityPolicy;
  transport: TransportEncoding;
  cacheMode: CacheMode;
  manifest: Record<string, unknown>;
  compressionIndex: Record<string, unknown>;
  manifestUrl: string;
  baseUrl: string;
  artifactOrigin: string;
  sdkManifest: Record<string, unknown>;
  artifacts: Array<Record<string, unknown>>;
  durationMs: number;
  workerStarted: boolean;
  pass: boolean;
}

export function canonicalJson(value: unknown): string;
export function safeRelativeUrl(value: unknown): boolean;
export function expectedReleaseId(manifest: Record<string, unknown>): Promise<string>;
export function validateReleaseManifest(
  manifest: Record<string, unknown>, policy?: FidelityPolicy,
): Promise<Record<string, unknown>>;
export function verifyRelease(options: VerifyReleaseOptions): Promise<VerifiedRelease>;

export class VerifiedReleaseSession {
  releaseId: string;
  policy: FidelityPolicy;
  transport: TransportEncoding;
  engine: unknown;
  requestFidelity(policy: FidelityPolicy): Record<string, unknown>;
  dispose(): void;
}

export function startVerifiedEngine(
  verified: VerifiedRelease,
  options?: Record<string, unknown>,
): Promise<VerifiedReleaseSession>;
