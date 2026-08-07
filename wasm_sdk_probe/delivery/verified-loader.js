"use strict";

export const DELIVERY_SCHEMA_VERSION = 1;
export const ROLE_ORDER = Object.freeze([
  "entry-html", "stylesheet", "app-module", "document-sdk", "input-adapter",
  "clipboard-adapter", "page-navigation", "sdk-worker", "sdk-manifest",
  "wasm-loader", "wasm-binary", "base-data", "base-metadata", "cjk-data",
  "cjk-metadata", "fallback-data", "fallback-metadata",
]);

const MANIFEST_FIELDS = new Set([
  "schemaVersion", "releaseId", "createdAt", "sdkVersion", "profile",
  "coreCommit", "entry", "capabilities", "artifacts",
]);
const ARTIFACT_FIELDS = new Set([
  "role", "url", "sha256", "rawBytes", "mediaType", "contentEncoding",
  "required", "cachePolicy",
]);
const FALLBACK_ROLES = new Set(["fallback-data", "fallback-metadata"]);
const ERROR_POLICY = Object.freeze({
  RELEASE_MANIFEST_INVALID: [false, "select-known-good"],
  RELEASE_UNSUPPORTED: [false, "select-supported-release"],
  ARTIFACT_HTTP_ERROR: [true, "retry-release"],
  ARTIFACT_MEDIA_TYPE_MISMATCH: [false, "reject-release"],
  ARTIFACT_ENCODING_MISMATCH: [false, "reject-release"],
  ARTIFACT_SIZE_MISMATCH: [false, "reject-release"],
  ARTIFACT_HASH_MISMATCH: [false, "reject-release"],
  CROSS_ORIGIN_ISOLATION_REQUIRED: [false, "fix-deployment-headers"],
  DELIVERY_ABORTED: [true, "retry-release"],
  DELIVERY_TIMEOUT: [true, "retry-release"],
  WORKER_HANDSHAKE_MISMATCH: [false, "reject-release"],
  FONT_PACK_RESTART_REQUIRED: [true, "save-and-reload-release"],
});

export class DeliveryError extends Error {
  constructor(code, message, details = {}) {
    const [retryable, safeNextAction] = ERROR_POLICY[code] || [false, "reject-release"];
    super(message);
    this.name = code === "DELIVERY_ABORTED" ? "AbortError" : "DeliveryError";
    this.code = code;
    this.details = Object.freeze({
      stage: details.stage || "unknown",
      releaseId: details.releaseId || null,
      role: details.role || null,
      retryable,
      safeNextAction,
      mutationState: "none",
      ...details,
    });
  }
}

function sameFields(value, expected) {
  if (!value || typeof value !== "object" || Array.isArray(value))
    return false;
  const actual = Object.keys(value);
  return actual.length === expected.size && actual.every((field) => expected.has(field));
}

function normalized(value) {
  if (Array.isArray(value))
    return value.map(normalized);
  if (value && typeof value === "object")
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, normalized(value[key])]));
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(normalized(value));
}

async function sha256Bytes(value) {
  const digest = await crypto.subtle.digest("SHA-256", value);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function expectedReleaseId(manifest) {
  const seed = structuredClone(manifest);
  delete seed.releaseId;
  const hash = await sha256Bytes(new TextEncoder().encode(canonicalJson(seed)));
  return `writer-review-${hash.slice(0, 16)}`;
}

export function safeRelativeUrl(value) {
  if (typeof value !== "string" || !value || value.length > 512 || value.includes("\\")
      || value.startsWith("/") || !/^[A-Za-z0-9._/-]+$/.test(value))
    return false;
  try {
    const parsed = new URL(value, "https://r8.invalid/base/");
    if (parsed.origin !== "https://r8.invalid" || parsed.search || parsed.hash)
      return false;
  } catch {
    return false;
  }
  return value.split("/").every((part) => part && part !== "." && part !== "..");
}

function manifestError(message, releaseId = null) {
  return new DeliveryError("RELEASE_MANIFEST_INVALID", message, {
    stage: "manifest-validate", releaseId,
  });
}

export async function validateReleaseManifest(manifest, policy = "standard") {
  if (!["standard", "full-fidelity"].includes(policy))
    throw new DeliveryError("RELEASE_UNSUPPORTED", `unknown fidelity policy: ${policy}`, {
      stage: "manifest-validate", releaseId: manifest?.releaseId || null,
    });
  if (!sameFields(manifest, MANIFEST_FIELDS))
    throw manifestError("manifest fields differ from the closed schema", manifest?.releaseId);
  if (manifest.schemaVersion !== 1 || manifest.profile !== "writer-review"
      || manifest.entry !== "r7-reference.html"
      || !/^writer-review-[0-9a-f]{16}$/.test(manifest.releaseId)
      || !/^[0-9a-f]{40}$/.test(manifest.coreCommit)
      || typeof manifest.sdkVersion !== "string" || !manifest.sdkVersion)
    throw manifestError("manifest identity fields are invalid", manifest.releaseId);
  if (!Array.isArray(manifest.capabilities) || !manifest.capabilities.length
      || manifest.capabilities.some((item) => typeof item !== "string" || !item)
      || canonicalJson(manifest.capabilities) !== canonicalJson([...new Set(manifest.capabilities)].sort()))
    throw manifestError("manifest capabilities must be sorted and unique", manifest.releaseId);
  if (!Array.isArray(manifest.artifacts)
      || canonicalJson(manifest.artifacts.map((item) => item?.role)) !== canonicalJson(ROLE_ORDER))
    throw manifestError("manifest roles differ from the frozen graph", manifest.releaseId);
  for (const artifact of manifest.artifacts) {
    if (!sameFields(artifact, ARTIFACT_FIELDS) || !safeRelativeUrl(artifact.url)
        || !/^[0-9a-f]{64}$/.test(artifact.sha256)
        || !Number.isSafeInteger(artifact.rawBytes) || artifact.rawBytes <= 0
        || typeof artifact.mediaType !== "string" || !artifact.mediaType
        || artifact.contentEncoding !== "identity"
        || typeof artifact.required !== "boolean"
        || !["entry", "immutable", "optional-pack"].includes(artifact.cachePolicy))
      throw manifestError(`artifact ${artifact?.role || "unknown"} is invalid`, manifest.releaseId);
    const required = !FALLBACK_ROLES.has(artifact.role) || policy === "full-fidelity";
    if (artifact.required !== required)
      throw manifestError(`${artifact.role} required differs from ${policy}`, manifest.releaseId);
    if (policy === "full-fidelity" && FALLBACK_ROLES.has(artifact.role)
        && artifact.cachePolicy !== "immutable")
      throw manifestError(`${artifact.role} must be immutable for full fidelity`, manifest.releaseId);
  }
  if (manifest.releaseId !== await expectedReleaseId(manifest))
    throw manifestError("release ID does not match canonical manifest identity", manifest.releaseId);
  return manifest;
}

function combineAbort(externalSignal, timeoutMs) {
  const controller = new AbortController();
  let timedOut = false;
  let timer = 0;
  const abort = () => controller.abort(externalSignal?.reason);
  if (externalSignal?.aborted)
    abort();
  else
    externalSignal?.addEventListener("abort", abort, { once: true });
  if (Number.isFinite(timeoutMs) && timeoutMs > 0) {
    timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
  }
  return {
    signal: controller.signal,
    timedOut: () => timedOut,
    dispose() {
      if (timer)
        clearTimeout(timer);
      externalSignal?.removeEventListener("abort", abort);
    },
  };
}

function transportEncoding(response) {
  return (response.headers.get("Content-Encoding") || "identity").toLowerCase();
}

function exactMediaType(response) {
  return (response.headers.get("Content-Type") || "").toLowerCase();
}

function artifactError(code, message, manifest, artifact, stage = "artifact-validate", extra = {}) {
  return new DeliveryError(code, message, {
    stage, releaseId: manifest.releaseId, role: artifact.role, ...extra,
  });
}

async function fetchJson(fetchImpl, url, options, code, stage) {
  let response;
  try {
    response = await fetchImpl(url, options);
  } catch (error) {
    if (options?.signal?.aborted || error?.name === "AbortError")
      throw error;
    throw new DeliveryError(code, String(error?.message || error), { stage, cause: error?.name || "Error" });
  }
  if (!response.ok)
    throw new DeliveryError(code, `HTTP ${response.status} for ${url}`, { stage, httpStatus: response.status });
  try {
    return { response, value: await response.json() };
  } catch (error) {
    throw new DeliveryError(code, `invalid JSON from ${url}: ${error}`, { stage });
  }
}

function validateCompressionIndex(index, manifest, policy) {
  if (!index || index.schemaVersion !== 1 || index.releaseId !== manifest.releaseId
      || index.policy !== policy || index.hashBoundary !== "decoded-artifact-bytes"
      || !Array.isArray(index.artifacts))
    throw manifestError("compression index does not match release", manifest.releaseId);
  const roles = index.artifacts.map((item) => item.role);
  if (canonicalJson(roles) !== canonicalJson(ROLE_ORDER))
    throw manifestError("compression index roles differ from release", manifest.releaseId);
  return new Map(index.artifacts.map((item) => [item.role, item]));
}

async function fetchArtifact(fetchImpl, baseUrl, manifest, artifact, compression,
                             transport, cacheMode, signal, urlTransform, artifactOrigin,
                             retainBuffer = false) {
  const releasePath = baseUrl.pathname;
  const roleBase = artifactOrigin && [
    "wasm-binary", "base-data", "base-metadata", "cjk-data", "cjk-metadata",
    "fallback-data", "fallback-metadata",
  ].includes(artifact.role)
    ? new URL(releasePath, artifactOrigin) : baseUrl;
  const sourceUrl = new URL(artifact.url, roleBase);
  if (sourceUrl.origin !== roleBase.origin)
    throw artifactError("RELEASE_MANIFEST_INVALID", "artifact escaped the release origin", manifest, artifact);
  const transformed = urlTransform ? urlTransform(artifact.role, new URL(sourceUrl)) : sourceUrl;
  const url = transformed instanceof URL ? transformed : new URL(transformed);
  const startedAt = performance.now();
  let response;
  try {
    response = await fetchImpl(url, {
      cache: cacheMode === "cold" ? "no-store" : "default",
      credentials: "omit",
      signal,
    });
  } catch (error) {
    if (signal.aborted)
      throw error;
    throw artifactError("ARTIFACT_HTTP_ERROR", String(error?.message || error), manifest, artifact,
      "artifact-fetch", { cause: error?.name || "Error" });
  }
  if (!response.ok)
    throw artifactError("ARTIFACT_HTTP_ERROR", `HTTP ${response.status} for ${artifact.role}`,
      manifest, artifact, "artifact-fetch", { httpStatus: response.status });
  if (sourceUrl.origin !== baseUrl.origin
      && (response.headers.get("Cross-Origin-Resource-Policy") || "").toLowerCase() !== "cross-origin")
    throw artifactError("CROSS_ORIGIN_ISOLATION_REQUIRED",
      `${artifact.role} lacks Cross-Origin-Resource-Policy: cross-origin`, manifest, artifact,
      "artifact-fetch", { sourceOrigin: sourceUrl.origin });
  if (response.url) {
    const finalUrl = new URL(response.url);
    if (finalUrl.origin !== sourceUrl.origin)
      throw artifactError("ARTIFACT_HTTP_ERROR", `${artifact.role} redirected outside its release origin`,
        manifest, artifact, "artifact-fetch", { finalUrl: finalUrl.href });
  }
  const actualMedia = exactMediaType(response);
  if (actualMedia !== artifact.mediaType.toLowerCase())
    throw artifactError("ARTIFACT_MEDIA_TYPE_MISMATCH",
      `${artifact.role} media type ${actualMedia || "missing"} != ${artifact.mediaType}`,
      manifest, artifact, "artifact-validate", { expected: artifact.mediaType, actual: actualMedia });
  const encoding = transportEncoding(response);
  if (encoding !== transport)
    throw artifactError("ARTIFACT_ENCODING_MISMATCH",
      `${artifact.role} encoding ${encoding} != ${transport}`, manifest, artifact,
      "artifact-validate", { expected: transport, actual: encoding });
  const expectedEncodedBytes = transport === "gzip"
    ? compression.get(artifact.role)?.gzip?.encodedBytes : artifact.rawBytes;
  const contentLength = Number(response.headers.get("Content-Length"));
  if (!Number.isSafeInteger(expectedEncodedBytes) || expectedEncodedBytes <= 0
      || !Number.isSafeInteger(contentLength) || contentLength !== expectedEncodedBytes)
    throw artifactError("ARTIFACT_SIZE_MISMATCH",
      `${artifact.role} encoded Content-Length mismatch`, manifest, artifact,
      "artifact-validate", { expectedEncodedBytes, contentLength });
  let buffer;
  try {
    buffer = await response.arrayBuffer();
  } catch (error) {
    throw artifactError("ARTIFACT_SIZE_MISMATCH",
      `${artifact.role} response body was incomplete: ${error}`, manifest, artifact,
      "artifact-validate", { cause: error?.name || "Error" });
  }
  if (buffer.byteLength !== artifact.rawBytes)
    throw artifactError("ARTIFACT_SIZE_MISMATCH",
      `${artifact.role} decoded bytes ${buffer.byteLength} != ${artifact.rawBytes}`,
      manifest, artifact, "artifact-validate",
      { expectedDecodedBytes: artifact.rawBytes, actualDecodedBytes: buffer.byteLength });
  const hash = await sha256Bytes(buffer);
  if (hash !== artifact.sha256)
    throw artifactError("ARTIFACT_HASH_MISMATCH", `${artifact.role} SHA-256 mismatch`,
      manifest, artifact, "artifact-validate", { expected: artifact.sha256, actual: hash });
  return {
    role: artifact.role,
    url: url.href,
    mediaType: actualMedia,
    transportEncoding: encoding,
    encodedBytes: contentLength,
    decodedBytes: buffer.byteLength,
    sha256: hash,
    durationMs: performance.now() - startedAt,
    cacheMode,
    buffer: retainBuffer || ["document-sdk", "sdk-manifest"].includes(artifact.role)
      ? buffer : null,
  };
}

export async function verifyRelease(options) {
  const {
    manifestUrl,
    policy = "standard",
    transport = "identity",
    cacheMode = "cold",
    signal = null,
    timeoutMs = 600000,
    fetchImpl = globalThis.fetch?.bind(globalThis),
    urlTransform = null,
    artifactOrigin = null,
    requireIsolation = true,
    crossOriginIsolated = globalThis.crossOriginIsolated,
    onArtifactVerified = null,
  } = options || {};
  if (typeof fetchImpl !== "function")
    throw new TypeError("verifyRelease requires fetch");
  if (!manifestUrl)
    throw new TypeError("verifyRelease requires manifestUrl");
  if (onArtifactVerified !== null && typeof onArtifactVerified !== "function")
    throw new TypeError("onArtifactVerified must be a function or null");
  if (!["identity", "gzip"].includes(transport))
    throw new DeliveryError("RELEASE_UNSUPPORTED", `unsupported transport: ${transport}`,
      { stage: "manifest-validate" });
  if (requireIsolation && crossOriginIsolated !== true)
    throw new DeliveryError("CROSS_ORIGIN_ISOLATION_REQUIRED",
      "cross-origin isolation is required before release verification", { stage: "manifest-fetch" });

  const abort = combineAbort(signal, timeoutMs);
  const startedAt = performance.now();
  try {
    const absoluteManifest = new URL(manifestUrl, globalThis.location?.href || "http://127.0.0.1/");
    const manifestFetch = await fetchJson(fetchImpl, absoluteManifest, {
      cache: "no-cache", credentials: "omit", signal: abort.signal,
    }, "RELEASE_MANIFEST_INVALID", "manifest-fetch");
    const manifest = await validateReleaseManifest(manifestFetch.value, policy);
    const baseUrl = new URL("./", absoluteManifest);
    const artifactOriginUrl = artifactOrigin
      ? new URL(artifactOrigin, absoluteManifest) : new URL(baseUrl.origin);
    if (!/^https?:$/.test(artifactOriginUrl.protocol) || artifactOriginUrl.username
        || artifactOriginUrl.password || artifactOriginUrl.pathname !== "/"
        || artifactOriginUrl.search || artifactOriginUrl.hash)
      throw manifestError("artifact origin is not an origin-only HTTP(S) URL", manifest.releaseId);
    const normalizedArtifactOrigin = artifactOriginUrl.origin;
    const compressionFetch = await fetchJson(fetchImpl, new URL("compression-index.json", baseUrl), {
      cache: "no-cache", credentials: "omit", signal: abort.signal,
    }, "RELEASE_MANIFEST_INVALID", "manifest-fetch");
    const compression = validateCompressionIndex(compressionFetch.value, manifest, policy);
    const artifacts = [];
    for (const artifact of manifest.artifacts.filter((item) => item.required)) {
      const verifiedArtifact = await fetchArtifact(
        fetchImpl, baseUrl, manifest, artifact, compression,
        transport, cacheMode, abort.signal, urlTransform, normalizedArtifactOrigin,
        onArtifactVerified !== null,
      );
      if (onArtifactVerified) {
        const { buffer, ...summary } = verifiedArtifact;
        await onArtifactVerified({
          releaseId: manifest.releaseId,
          artifact: structuredClone(artifact),
          verified: summary,
          buffer,
        });
      }
      if (!["document-sdk", "sdk-manifest"].includes(artifact.role))
        verifiedArtifact.buffer = null;
      artifacts.push(verifiedArtifact);
    }
    const sdkManifestArtifact = artifacts.find((item) => item.role === "sdk-manifest");
    let sdkManifest;
    try {
      sdkManifest = JSON.parse(new TextDecoder().decode(sdkManifestArtifact.buffer));
    } catch (error) {
      throw new DeliveryError("RELEASE_MANIFEST_INVALID", `SDK manifest JSON is invalid: ${error}`,
        { stage: "artifact-validate", releaseId: manifest.releaseId, role: "sdk-manifest" });
    }
    return {
      schemaVersion: DELIVERY_SCHEMA_VERSION,
      releaseId: manifest.releaseId,
      policy,
      transport,
      cacheMode,
      manifest,
      compressionIndex: compressionFetch.value,
      manifestUrl: absoluteManifest.href,
      baseUrl: baseUrl.href,
      artifactOrigin: normalizedArtifactOrigin,
      sdkManifest,
      artifacts,
      durationMs: performance.now() - startedAt,
      workerStarted: false,
      pass: artifacts.length === manifest.artifacts.filter((item) => item.required).length,
    };
  } catch (error) {
    if (error instanceof DeliveryError)
      throw error;
    if (abort.signal.aborted) {
      const code = abort.timedOut() ? "DELIVERY_TIMEOUT" : "DELIVERY_ABORTED";
      throw new DeliveryError(code, abort.timedOut() ? "release verification timed out" : "release verification aborted",
        { stage: "artifact-fetch" });
    }
    throw error;
  } finally {
    abort.dispose();
  }
}

async function browserModuleImporter(buffer, mediaType) {
  const blobUrl = URL.createObjectURL(new Blob([buffer], { type: mediaType }));
  try {
    return await import(blobUrl);
  } finally {
    URL.revokeObjectURL(blobUrl);
  }
}

function handshakeMatches(verified, handshake) {
  const expected = structuredClone(verified.sdkManifest);
  if (verified.artifactOrigin !== new URL(verified.baseUrl).origin) {
    const toArtifactOrigin = (value) => {
      const resolved = new URL(value, verified.artifacts.find((item) => item.role === "sdk-worker").url);
      return `${verified.artifactOrigin}${resolved.pathname}`;
    };
    for (const key of ["probe.wasm", "soffice.data", "soffice.data.js.metadata"])
      expected.artifactFiles[key] = toArtifactOrigin(expected.artifactFiles[key]);
    for (const pack of expected.resourcePacks || []) {
      pack.data = toArtifactOrigin(pack.data);
      pack.metadata = toArtifactOrigin(pack.metadata);
    }
  }
  return handshake?.releaseId === verified.releaseId
    && handshake?.profile === verified.manifest.profile
    && handshake?.sdkVersion === verified.manifest.sdkVersion
    && handshake?.coreCommit === verified.manifest.coreCommit
    && canonicalJson(handshake?.capabilities || []) === canonicalJson(expected.capabilities || [])
    && canonicalJson(handshake?.artifactFiles || {}) === canonicalJson(expected.artifactFiles || {})
    && canonicalJson(handshake?.resourcePacks || []) === canonicalJson(expected.resourcePacks || []);
}

export async function startVerifiedEngine(verified, options = {}) {
  if (!verified?.pass || verified.workerStarted)
    throw new DeliveryError("RELEASE_UNSUPPORTED", "release is not ready for one-time Worker start", {
      stage: "worker-start", releaseId: verified?.releaseId || null,
    });
  const documentSdk = verified.artifacts.find((item) => item.role === "document-sdk");
  const worker = verified.artifacts.find((item) => item.role === "sdk-worker");
  if (!documentSdk?.buffer || !worker)
    throw new DeliveryError("RELEASE_MANIFEST_INVALID", "verified SDK artifacts are missing", {
      stage: "worker-start", releaseId: verified.releaseId,
    });
  const importer = options.moduleImporter || browserModuleImporter;
  const module = await importer(documentSdk.buffer, documentSdk.mediaType);
  if (typeof module.createDocumentEngine !== "function")
    throw new DeliveryError("RELEASE_UNSUPPORTED", "verified document SDK has no engine factory", {
      stage: "worker-start", releaseId: verified.releaseId,
    });
  verified.workerStarted = true;
  options.onWorkerStart?.({ releaseId: verified.releaseId, workerUrl: worker.url });
  let engine;
  try {
    const workerUrl = new URL(worker.url);
    workerUrl.searchParams.set("artifactOrigin", verified.artifactOrigin);
    engine = await module.createDocumentEngine({
      workerUrl,
      timeoutMs: options.timeoutMs ?? 120000,
      closeRecoveryTimeoutMs: options.closeRecoveryTimeoutMs ?? 10000,
      ...(options.workerFactory ? { workerFactory: options.workerFactory } : {}),
    });
  } catch (error) {
    throw new DeliveryError("WORKER_HANDSHAKE_MISMATCH", `verified Worker failed to initialize: ${error}`,
      { stage: "worker-handshake", releaseId: verified.releaseId, cause: error?.code || error?.name });
  }
  if (!handshakeMatches(verified, engine.manifest)) {
    engine.dispose?.();
    throw new DeliveryError("WORKER_HANDSHAKE_MISMATCH", "Worker handshake differs from verified release", {
      stage: "worker-handshake", releaseId: verified.releaseId,
      actualReleaseId: engine.manifest?.releaseId || null,
    });
  }
  return new VerifiedReleaseSession(verified, engine);
}

export class VerifiedReleaseSession {
  constructor(verified, engine) {
    this.releaseId = verified.releaseId;
    this.policy = verified.policy;
    this.transport = verified.transport;
    this.verified = verified;
    this.engine = engine;
    this.disposed = false;
  }

  requestFidelity(policy) {
    if (policy === this.policy)
      return { releaseId: this.releaseId, policy: this.policy, restartRequired: false };
    throw new DeliveryError("FONT_PACK_RESTART_REQUIRED",
      `fidelity ${policy} requires a verified release restart`, {
        stage: "worker-start", releaseId: this.releaseId,
        currentPolicy: this.policy, requestedPolicy: policy,
      });
  }

  dispose() {
    if (this.disposed)
      return;
    this.disposed = true;
    this.engine.dispose?.();
  }
}
