import assert from "node:assert/strict";
import { test } from "node:test";
import {
  DeliveryError,
  ROLE_ORDER,
  expectedReleaseId,
  safeRelativeUrl,
  startVerifiedEngine,
  validateReleaseManifest,
  verifyRelease,
} from "../verified-loader.js";

const encoder = new TextEncoder();
const media = Object.fromEntries(ROLE_ORDER.map((role) => [role,
  role === "wasm-binary" ? "application/wasm"
    : role.endsWith("-data") ? "application/octet-stream"
      : role.endsWith("-metadata") || role === "sdk-manifest" ? "application/json; charset=utf-8"
        : role === "entry-html" ? "text/html; charset=utf-8"
          : role === "stylesheet" ? "text/css; charset=utf-8" : "text/javascript; charset=utf-8",
]));

async function hash(value) {
  const digest = await crypto.subtle.digest("SHA-256", value);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function fixture(policy = "standard") {
  const sdkManifest = {
    artifactFiles: { "probe.js": "probe.js", "probe.wasm": "probe.wasm" },
    capabilities: ["open-odt", "save-odt"],
    coreCommit: "1".repeat(40),
    profile: "writer-review",
    resourcePacks: [
      { id: "cjk-r5", loadAtStartup: true },
      { id: "fallback-fonts-r5", loadAtStartup: policy === "full-fidelity" },
    ],
    sdkVersion: "test-sdk",
  };
  const bytes = new Map();
  for (const role of ROLE_ORDER)
    bytes.set(role, encoder.encode(role === "sdk-manifest" ? JSON.stringify(sdkManifest) : `bytes-${role}`));
  const artifacts = [];
  for (const role of ROLE_ORDER) {
    const value = bytes.get(role);
    artifacts.push({
      role,
      url: `${role}.bin`,
      sha256: await hash(value),
      rawBytes: value.byteLength,
      mediaType: media[role],
      contentEncoding: "identity",
      required: !role.startsWith("fallback-") || policy === "full-fidelity",
      cachePolicy: role.startsWith("fallback-")
        ? (policy === "full-fidelity" ? "immutable" : "optional-pack") : "entry",
    });
  }
  const manifest = {
    schemaVersion: 1,
    releaseId: "",
    createdAt: "2026-08-04T00:00:00+08:00",
    sdkVersion: "test-sdk",
    profile: "writer-review",
    coreCommit: "1".repeat(40),
    entry: "r7-reference.html",
    capabilities: ["open-odt", "save-odt"],
    artifacts,
  };
  manifest.releaseId = await expectedReleaseId(manifest);
  const compression = {
    schemaVersion: 1,
    releaseId: manifest.releaseId,
    policy,
    hashBoundary: "decoded-artifact-bytes",
    artifacts: artifacts.map((item) => ({
      role: item.role,
      gzip: { encodedBytes: item.rawBytes },
    })),
  };
  return { manifest, compression, bytes, sdkManifest };
}

function response(value, contentType, encoding = "identity", status = 200) {
  return new Response(value, {
    status,
    headers: {
      "Content-Type": contentType,
      "Content-Encoding": encoding,
      "Content-Length": String(value.byteLength),
    },
  });
}

function fetcher(data, mutate = {}) {
  return async (input) => {
    const url = new URL(input);
    if (url.pathname.endsWith("release-manifest.json"))
      return Response.json(mutate.manifest || data.manifest);
    if (url.pathname.endsWith("compression-index.json"))
      return Response.json(data.compression);
    const role = ROLE_ORDER.find((candidate) => url.pathname.endsWith(`${candidate}.bin`));
    const artifact = data.manifest.artifacts.find((item) => item.role === role);
    const value = mutate.role === role && mutate.bytes !== undefined
      ? mutate.bytes : data.bytes.get(role);
    return response(value, mutate.role === role && mutate.mediaType ? mutate.mediaType : artifact.mediaType,
      mutate.role === role && mutate.encoding ? mutate.encoding : "identity");
  };
}

test("safe relative URL contract rejects schemes, traversal, credentials, and fragments", () => {
  assert.equal(safeRelativeUrl("profiles/worker.js"), true);
  for (const value of ["../worker.js", "/worker.js", "https://x/worker.js", "//x/worker.js",
    "user@example/worker.js", "worker.js?x=1", "worker.js#x", "a\\b"])
    assert.equal(safeRelativeUrl(value), false, value);
});

test("standard and full-fidelity closed manifests validate", async () => {
  for (const policy of ["standard", "full-fidelity"]) {
    const data = await fixture(policy);
    assert.equal(await validateReleaseManifest(data.manifest, policy), data.manifest);
  }
});

test("all required artifacts verify before Worker start is authorized", async () => {
  const data = await fixture();
  const verified = await verifyRelease({
    manifestUrl: "https://app.test/releases/id/release-manifest.json",
    fetchImpl: fetcher(data), requireIsolation: false,
  });
  assert.equal(verified.pass, true);
  assert.equal(verified.artifacts.length, 15);
  assert.equal(verified.workerStarted, false);
});

test("verified artifact callback receives exact bytes before Worker authorization", async () => {
  const data = await fixture();
  const observed = [];
  const verified = await verifyRelease({
    manifestUrl: "https://app.test/releases/id/release-manifest.json",
    fetchImpl: fetcher(data),
    requireIsolation: false,
    async onArtifactVerified(item) {
      observed.push({
        role: item.artifact.role,
        bytes: item.buffer.byteLength,
        sha256: await hash(item.buffer),
        expected: item.artifact.sha256,
      });
    },
  });
  assert.equal(observed.length, 15);
  assert.ok(observed.every((item) => item.bytes > 0 && item.sha256 === item.expected));
  assert.equal(verified.compressionIndex.releaseId, verified.releaseId);
  assert.equal(verified.workerStarted, false);
  assert.equal(verified.artifacts.find((item) => item.role === "wasm-binary").buffer, null);
});

test("artifact persistence failure prevents release verification", async () => {
  const data = await fixture();
  let persisted = 0;
  await assert.rejects(verifyRelease({
    manifestUrl: "https://app.test/releases/id/release-manifest.json",
    fetchImpl: fetcher(data),
    requireIsolation: false,
    onArtifactVerified() {
      persisted += 1;
      throw Object.assign(new Error("intentional cache write failure"), {
        code: "CACHE_WRITE_FAILED",
      });
    },
  }), (error) => error.code === "CACHE_WRITE_FAILED");
  assert.equal(persisted, 1);
});

test("wrong media, encoding, size, and hash are typed pre-Worker failures", async () => {
  const data = await fixture();
  const cases = [
    [{ role: "wasm-binary", mediaType: "text/plain" }, "ARTIFACT_MEDIA_TYPE_MISMATCH"],
    [{ role: "wasm-binary", encoding: "gzip" }, "ARTIFACT_ENCODING_MISMATCH"],
    [{ role: "wasm-binary", bytes: encoder.encode("short") }, "ARTIFACT_SIZE_MISMATCH"],
    [{ role: "wasm-binary", bytes: encoder.encode("bytes-wasm-binAry") }, "ARTIFACT_HASH_MISMATCH"],
  ];
  for (const [mutate, code] of cases) {
    await assert.rejects(
      verifyRelease({
        manifestUrl: "https://app.test/releases/id/release-manifest.json",
        fetchImpl: fetcher(data, mutate), requireIsolation: false,
      }),
      (error) => error instanceof DeliveryError && error.code === code
        && error.details.mutationState === "none",
      code,
    );
  }
});

test("unsafe or self-inconsistent manifest is rejected before artifact fetch", async () => {
  const data = await fixture();
  const manifest = structuredClone(data.manifest);
  manifest.artifacts[0].url = "../escape";
  let artifactFetches = 0;
  const base = fetcher(data, { manifest });
  const fetchImpl = async (url, options) => {
    if (!String(url).endsWith("release-manifest.json"))
      artifactFetches += 1;
    return base(url, options);
  };
  await assert.rejects(
    verifyRelease({ manifestUrl: "https://app.test/release-manifest.json", fetchImpl, requireIsolation: false }),
    (error) => error.code === "RELEASE_MANIFEST_INVALID",
  );
  assert.equal(artifactFetches, 0);
});

test("verified engine checks release handshake and enforces fidelity restart", async () => {
  const data = await fixture();
  const verified = await verifyRelease({
    manifestUrl: "https://app.test/releases/id/release-manifest.json",
    fetchImpl: fetcher(data), requireIsolation: false,
  });
  let starts = 0;
  let disposed = false;
  const engine = {
    manifest: { ...data.sdkManifest, releaseId: data.manifest.releaseId },
    dispose() { disposed = true; },
  };
  const session = await startVerifiedEngine(verified, {
    moduleImporter: async () => ({ createDocumentEngine: async () => engine }),
    onWorkerStart: () => { starts += 1; },
  });
  assert.equal(starts, 1);
  assert.equal(session.requestFidelity("standard").restartRequired, false);
  assert.throws(() => session.requestFidelity("full-fidelity"),
    (error) => error.code === "FONT_PACK_RESTART_REQUIRED");
  session.dispose();
  assert.equal(disposed, true);
});

test("handshake mismatch disposes the engine and never claims a session", async () => {
  const data = await fixture();
  const verified = await verifyRelease({
    manifestUrl: "https://app.test/releases/id/release-manifest.json",
    fetchImpl: fetcher(data), requireIsolation: false,
  });
  let disposed = false;
  await assert.rejects(startVerifiedEngine(verified, {
    moduleImporter: async () => ({
      createDocumentEngine: async () => ({
        manifest: { ...data.sdkManifest, releaseId: "writer-review-0000000000000000" },
        dispose() { disposed = true; },
      }),
    }),
  }), (error) => error.code === "WORKER_HANDSHAKE_MISMATCH");
  assert.equal(disposed, true);
});

test("timeout and external abort retain their delivery taxonomy", async () => {
  const pendingFetch = (_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(
      new DOMException("aborted", "AbortError")
    ), { once: true });
  });
  await assert.rejects(verifyRelease({
    manifestUrl: "https://app.test/release-manifest.json",
    fetchImpl: pendingFetch,
    timeoutMs: 5,
    requireIsolation: false,
  }), (error) => error.code === "DELIVERY_TIMEOUT");

  const controller = new AbortController();
  const attempt = verifyRelease({
    manifestUrl: "https://app.test/release-manifest.json",
    fetchImpl: pendingFetch,
    signal: controller.signal,
    requireIsolation: false,
  });
  controller.abort();
  await assert.rejects(attempt, (error) => error.code === "DELIVERY_ABORTED");
});

test("artifact origin must be a credential-free origin-only URL", async () => {
  const data = await fixture();
  for (const artifactOrigin of [
    "https://user:secret@artifact.test/",
    "https://artifact.test/path",
    "data:text/plain,artifact",
  ]) {
    await assert.rejects(verifyRelease({
      manifestUrl: "https://app.test/releases/id/release-manifest.json",
      artifactOrigin,
      fetchImpl: fetcher(data),
      requireIsolation: false,
    }), (error) => error.code === "RELEASE_MANIFEST_INVALID");
  }
});
