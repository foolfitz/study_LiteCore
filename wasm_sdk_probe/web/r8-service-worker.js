"use strict";

import { verifyRelease } from "./delivery/verified-loader.js";
import {
  createReleaseState,
  planReleaseEviction,
  transitionReleaseState,
  validateReleaseState,
} from "./delivery/release-state.js";

const DB_NAME = "oxsdk-r8c-metadata-v1";
const DB_STORE = "state";
const RELEASE_CACHE_PREFIX = "oxsdk-r8c-release-v1-";
const SHELL_CACHE = "oxsdk-r8c-shell-v1";
const SHELL_URLS = [
  "./r8-update.html",
  "./r8-update-app.js",
  "./r8-service-worker.js",
  "./delivery/verified-loader.js",
  "./delivery/release-state.js",
  "./r6-fixtures/t1-plain-zh.odt",
];
const HEALTH_ANCHOR = "Final line：ODT round-trip 完整性檢查。";
let operationQueue = Promise.resolve();

class R8CacheError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "R8CacheError";
    this.code = code;
    this.details = details;
  }
}

function requestPromise(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("IndexedDB request failed"));
  });
}

function transactionPromise(transaction) {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error || new Error("IndexedDB transaction failed"));
    transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted"));
  });
}

async function openDatabase() {
  const request = indexedDB.open(DB_NAME, 1);
  request.onupgradeneeded = () => request.result.createObjectStore(DB_STORE);
  return requestPromise(request);
}

async function rawReadState() {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(DB_STORE, "readonly");
    const store = transaction.objectStore(DB_STORE);
    const state = await requestPromise(store.get("current"));
    const backup = await requestPromise(store.get("backup"));
    await transactionPromise(transaction);
    return { state, backup };
  } finally {
    database.close();
  }
}

async function rawWriteState(state, previous = null) {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(DB_STORE, "readwrite");
    const store = transaction.objectStore(DB_STORE);
    if (previous)
      store.put(previous, "backup");
    store.put(state, "current");
    await transactionPromise(transaction);
  } finally {
    database.close();
  }
}

async function loadState() {
  const records = await rawReadState();
  if (records.state && validateReleaseState(records.state).pass)
    return { state: records.state, metadataRecovery: null };
  if (records.backup && validateReleaseState(records.backup).pass) {
    await rawWriteState(records.backup, records.backup);
    return { state: records.backup, metadataRecovery: "restored-valid-backup" };
  }
  const state = createReleaseState({ retentionLimit: 3 });
  await rawWriteState(state, state);
  return {
    state,
    metadataRecovery: records.state || records.backup
      ? "no-valid-metadata-no-release-guessed" : "initialized-empty",
  };
}

async function applyEvent(state, event) {
  const result = transitionReleaseState(state, event);
  await rawWriteState(result.state, state);
  return result;
}

function cacheName(releaseId) {
  return `${RELEASE_CACHE_PREFIX}${releaseId}`;
}

function cachedBase(releaseId) {
  return new URL(`./__r8c_cache__/releases/${releaseId}/`, self.location.origin);
}

function cachedUrl(releaseId, relative) {
  return new URL(relative, cachedBase(releaseId)).href;
}

function jsonResponse(value) {
  const bytes = new TextEncoder().encode(`${JSON.stringify(value, null, 2)}\n`);
  return new Response(bytes, {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Length": String(bytes.byteLength),
      "Cache-Control": "public, max-age=31536000, immutable",
      "Cross-Origin-Resource-Policy": "same-origin",
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "require-corp",
    },
  });
}

function artifactResponse(item) {
  return new Response(item.buffer, {
    headers: {
      "Content-Type": item.artifact.mediaType,
      "Content-Length": String(item.buffer.byteLength),
      "Cache-Control": "public, max-age=31536000, immutable",
      "Cross-Origin-Resource-Policy": "same-origin",
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "require-corp",
      "X-OXSDK-R8-Verified-SHA256": item.verified.sha256,
    },
  });
}

async function sha256(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function prepareShell() {
  const cache = await caches.open(SHELL_CACHE);
  for (const value of SHELL_URLS) {
    const url = new URL(value, self.location.href);
    const existing = await cache.match(url, { ignoreSearch: true });
    if (existing)
      continue;
    const response = await fetch(url, { cache: "no-store", credentials: "omit" });
    if (!response.ok)
      throw new R8CacheError("CACHE_WRITE_FAILED", `shell HTTP ${response.status}: ${url}`);
    await cache.put(url, response);
  }
  return { cacheName: SHELL_CACHE, entries: (await cache.keys()).length };
}

function barrierError(barrier, releaseId, details = {}) {
  return new R8CacheError("R8_BARRIER_REACHED", `deterministic barrier reached: ${barrier}`, {
    barrier, releaseId, ...details,
  });
}

async function stageRelease(payload) {
  const {
    releaseId,
    manifestUrl,
    manifestSha256,
    artifactOrigin,
    requiredArtifactCount = 15,
    interruptAt = null,
    interruptRole = null,
    writeFailureRole = null,
  } = payload;
  if (!/^writer-review-[0-9a-f]{16}$/.test(releaseId)
      || !/^[0-9a-f]{64}$/.test(manifestSha256))
    throw new R8CacheError("RELEASE_MANIFEST_INVALID", "release identity is invalid");

  const targetCacheName = cacheName(releaseId);
  await caches.delete(targetCacheName);
  const targetCache = await caches.open(targetCacheName);
  const { state: initial } = await loadState();
  let state = (await applyEvent(initial, {
    type: "DISCOVER_CANDIDATE",
    releaseId,
    graphHash: manifestSha256,
    cacheName: targetCacheName,
    totalArtifacts: requiredArtifactCount,
  })).state;
  if (interruptAt === "manifest-verified")
    throw barrierError("manifest-verified", releaseId);

  let manifestBytes;
  try {
    const manifestResponse = await fetch(manifestUrl, {
      cache: "no-store", credentials: "omit",
    });
    if (!manifestResponse.ok)
      throw new R8CacheError("RELEASE_MANIFEST_INVALID", `manifest HTTP ${manifestResponse.status}`);
    manifestBytes = await manifestResponse.arrayBuffer();
    const actualManifestHash = await sha256(manifestBytes);
    if (actualManifestHash !== manifestSha256)
      throw new R8CacheError("RELEASE_MANIFEST_INVALID", "release-set manifest hash mismatch", {
        expected: manifestSha256, actual: actualManifestHash,
      });
    const manifestHeaders = new Headers(manifestResponse.headers);
    const prefetchedManifest = () => new Response(manifestBytes.slice(0), {
      status: 200,
      headers: manifestHeaders,
    });
    const networkFetch = (input, options) => {
      const requested = new URL(input, self.location.href);
      if (requested.href === new URL(manifestUrl, self.location.href).href)
        return Promise.resolve(prefetchedManifest());
      return fetch(input, options);
    };

    let cachedBytes = 0;
    let cachedArtifacts = 0;
    const verified = await verifyRelease({
      manifestUrl,
      policy: "standard",
      transport: "identity",
      cacheMode: "cold",
      fetchImpl: networkFetch,
      artifactOrigin,
      requireIsolation: false,
      timeoutMs: 600000,
      urlTransform(_role, url) {
        url.searchParams.set("representation", "identity");
        return url;
      },
      async onArtifactVerified(item) {
        if (item.artifact.role === writeFailureRole)
          throw new R8CacheError("CACHE_WRITE_FAILED", `intentional write failure: ${writeFailureRole}`, {
            releaseId, role: writeFailureRole,
          });
        await targetCache.put(
          cachedUrl(releaseId, item.artifact.url), artifactResponse(item),
        );
        cachedBytes += item.buffer.byteLength;
        cachedArtifacts += 1;
        state = (await applyEvent(state, {
          type: "STAGE_PROGRESS",
          releaseId,
          role: item.artifact.role,
          cachedBytes,
          barrier: "artifact-cached",
        })).state;
        if (interruptAt === "artifact-cached"
            && (!interruptRole || interruptRole === item.artifact.role))
          throw barrierError("artifact-cached", releaseId, { role: item.artifact.role });
      },
    });
    if (cachedArtifacts !== requiredArtifactCount)
      throw new R8CacheError("CANDIDATE_NOT_READY", "verified artifact count differs", {
        expected: requiredArtifactCount, actual: cachedArtifacts,
      });
    await targetCache.put(
      cachedUrl(releaseId, "release-manifest.json"), jsonResponse(verified.manifest),
    );
    await targetCache.put(
      cachedUrl(releaseId, "compression-index.json"), jsonResponse(verified.compressionIndex),
    );
    await prepareShell();
    if (interruptAt === "metadata-before-ready")
      throw barrierError("metadata-before-ready", releaseId, { cachedArtifacts });
    state = (await applyEvent(state, { type: "STAGE_READY", releaseId })).state;
    return {
      releaseId,
      cacheName: targetCacheName,
      cachedArtifacts,
      cachedBytes,
      state,
    };
  } catch (error) {
    if (error?.code === "R8_BARRIER_REACHED")
      throw error;
    const loaded = await loadState();
    if (loaded.state.releases[releaseId]) {
      const failed = await applyEvent(loaded.state, {
        type: "STAGE_FAILED", releaseId, reason: error?.code || error?.name || "stage-failed",
      });
      state = failed.state;
    }
    await caches.delete(targetCacheName);
    throw error;
  }
}

async function cachedFetch(releaseId, input, explicitCacheName = null) {
  let selectedCacheName = explicitCacheName;
  if (!selectedCacheName) {
    const { state } = await loadState();
    selectedCacheName = state.releases[releaseId]?.cacheName;
  }
  if (!selectedCacheName)
    return new Response("cached release unavailable", { status: 503 });
  const cache = await caches.open(selectedCacheName);
  const requested = new URL(input instanceof Request ? input.url : input, self.location.href);
  const response = await cache.match(requested, { ignoreSearch: true });
  if (!response)
    return new Response("cached artifact unavailable", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  return response;
}

async function verifyCachedRelease(releaseId, explicitCacheName = null) {
  try {
    const verified = await verifyRelease({
      manifestUrl: cachedUrl(releaseId, "release-manifest.json"),
      policy: "standard",
      transport: "identity",
      cacheMode: "warm",
      fetchImpl: (input) => cachedFetch(releaseId, input, explicitCacheName),
      artifactOrigin: self.location.origin,
      requireIsolation: false,
      timeoutMs: 600000,
    });
    return {
      releaseId: verified.releaseId,
      artifactCount: verified.artifacts.length,
      durationMs: verified.durationMs,
      pass: verified.pass,
    };
  } catch (error) {
    throw new R8CacheError("CACHED_ARTIFACT_INVALID", "cached release validation failed", {
      releaseId,
      cause: error?.code || error?.name || "Error",
      role: error?.details?.role || null,
    });
  }
}

async function repairRelease(payload) {
  const {
    releaseId, manifestUrl, manifestSha256, artifactOrigin,
  } = payload;
  const loaded = await loadState();
  const release = loaded.state.releases[releaseId];
  if (!release || !["ready", "active", "retiring"].includes(release.status))
    throw new R8CacheError("ROLLBACK_TARGET_UNAVAILABLE", "repair target is not a usable cached release");
  const repairCacheName = `${RELEASE_CACHE_PREFIX}${releaseId}-repair-${loaded.state.sequence + 1}`;
  await caches.delete(repairCacheName);
  const repairCache = await caches.open(repairCacheName);
  try {
    const manifestResponse = await fetch(manifestUrl, {
      cache: "no-store", credentials: "omit",
    });
    if (!manifestResponse.ok)
      throw new R8CacheError("RELEASE_MANIFEST_INVALID", `repair manifest HTTP ${manifestResponse.status}`);
    const manifestBytes = await manifestResponse.arrayBuffer();
    const actualManifestHash = await sha256(manifestBytes);
    if (actualManifestHash !== manifestSha256)
      throw new R8CacheError("RELEASE_MANIFEST_INVALID", "repair manifest hash mismatch", {
        expected: manifestSha256, actual: actualManifestHash,
      });
    const headers = new Headers(manifestResponse.headers);
    const networkFetch = (input, options) => {
      const requested = new URL(input, self.location.href);
      if (requested.href === new URL(manifestUrl, self.location.href).href)
        return Promise.resolve(new Response(manifestBytes.slice(0), { status: 200, headers }));
      return fetch(input, options);
    };
    let cachedBytes = 0;
    const verified = await verifyRelease({
      manifestUrl,
      policy: "standard",
      transport: "identity",
      cacheMode: "cold",
      fetchImpl: networkFetch,
      artifactOrigin,
      requireIsolation: false,
      timeoutMs: 600000,
      urlTransform(_role, url) {
        url.searchParams.set("representation", "identity");
        return url;
      },
      async onArtifactVerified(item) {
        await repairCache.put(
          cachedUrl(releaseId, item.artifact.url), artifactResponse(item),
        );
        cachedBytes += item.buffer.byteLength;
      },
    });
    await repairCache.put(
      cachedUrl(releaseId, "release-manifest.json"), jsonResponse(verified.manifest),
    );
    await repairCache.put(
      cachedUrl(releaseId, "compression-index.json"), jsonResponse(verified.compressionIndex),
    );
    const cacheCheck = await verifyCachedRelease(releaseId, repairCacheName);
    if (!cacheCheck.pass)
      throw new R8CacheError("CACHED_ARTIFACT_INVALID", "repair cache did not verify");
    const result = await applyEvent(loaded.state, {
      type: "REPAIR_COMMIT",
      releaseId,
      cacheName: repairCacheName,
      cachedBytes,
    });
    await executeActions(result.actions);
    return {
      releaseId,
      cacheName: repairCacheName,
      cachedBytes,
      cacheCheck,
      state: result.state,
      actions: result.actions,
    };
  } catch (error) {
    await caches.delete(repairCacheName);
    if (error?.code)
      throw error;
    throw new R8CacheError("CACHE_WRITE_FAILED", `repair failed: ${error}`, {
      releaseId,
      cause: error?.name || "Error",
    });
  }
}

async function cacheInventory(state) {
  const names = await caches.keys();
  const releaseCaches = [];
  for (const name of names.filter((item) => item.startsWith(RELEASE_CACHE_PREFIX))) {
    const cache = await caches.open(name);
    releaseCaches.push({ name, entries: (await cache.keys()).length });
  }
  return {
    cacheNames: names,
    releaseCaches,
    retainedReleaseCount: Object.keys(state.releases).length,
  };
}

async function reconcileClientPins(state) {
  const live = new Set((await clients.matchAll({
    type: "window", includeUncontrolled: true,
  })).map((client) => client.id));
  let output = state;
  for (const clientId of Object.keys(state.clientPins)) {
    if (!live.has(clientId))
      output = (await applyEvent(output, { type: "UNPIN_CLIENT", clientId })).state;
  }
  return output;
}

async function executeActions(actions) {
  for (const action of actions) {
    if (action.type === "delete-release-cache" && action.releaseId)
      await caches.delete(cacheName(action.releaseId));
    if (action.type === "delete-cache-name" && action.cacheName)
      await caches.delete(action.cacheName);
  }
}

async function handleCommand(command, payload, source) {
  let loaded = await loadState();
  let state = await reconcileClientPins(loaded.state);
  switch (command) {
    case "status":
      return {
        instance: "r8c-service-worker-v1",
        metadataRecovery: loaded.metadataRecovery,
        state,
        validation: validateReleaseState(state),
        inventory: await cacheInventory(state),
      };
    case "stage-release":
      return stageRelease(payload);
    case "verify-cached":
      return verifyCachedRelease(payload.releaseId);
    case "repair-release":
      return repairRelease(payload);
    case "activate-release": {
      let result = await applyEvent(state, {
        type: "ACTIVATE_BEGIN", releaseId: payload.releaseId,
      });
      state = result.state;
      if (payload.interruptAt === "activation-prepared")
        throw barrierError("activation-prepared", payload.releaseId);
      result = await applyEvent(state, {
        type: "ACTIVATE_COMMIT", releaseId: payload.releaseId,
      });
      return { state: result.state, actions: result.actions };
    }
    case "health-result": {
      const type = payload.pass ? "HEALTH_PASS" : "HEALTH_FAIL";
      const result = await applyEvent(state, {
        type, releaseId: payload.releaseId, reason: payload.reason,
      });
      await executeActions(result.actions);
      return { state: result.state, actions: result.actions };
    }
    case "recover": {
      const result = await applyEvent(state, { type: "RECOVER" });
      await executeActions(result.actions);
      return { state: result.state, actions: result.actions };
    }
    case "pin": {
      if (!source?.id)
        throw new R8CacheError("CLIENT_ID_UNAVAILABLE", "message source has no client ID");
      const result = await applyEvent(state, {
        type: "PIN_CLIENT", clientId: source.id, releaseId: payload.releaseId,
      });
      return { clientId: source.id, releaseId: payload.releaseId, state: result.state };
    }
    case "unpin": {
      if (!source?.id)
        throw new R8CacheError("CLIENT_ID_UNAVAILABLE", "message source has no client ID");
      const result = await applyEvent(state, { type: "UNPIN_CLIENT", clientId: source.id });
      return { clientId: source.id, state: result.state };
    }
    case "rollback": {
      const result = await applyEvent(state, {
        type: "ROLLBACK", toReleaseId: payload.releaseId,
      });
      return { state: result.state, actions: result.actions };
    }
    case "evict": {
      const plan = planReleaseEviction(state);
      const executed = [];
      for (const releaseId of plan.evictReleaseIds) {
        const result = await applyEvent(state, { type: "EVICT", releaseId });
        state = result.state;
        await executeActions(result.actions);
        executed.push(releaseId);
      }
      return { plan, executed, state };
    }
    case "delete-entry": {
      const selectedCache = state.releases[payload.releaseId]?.cacheName;
      if (!selectedCache)
        throw new R8CacheError("ROLLBACK_TARGET_UNAVAILABLE", "release cache is unavailable");
      const cache = await caches.open(selectedCache);
      const manifestResponse = await cache.match(
        cachedUrl(payload.releaseId, "release-manifest.json"), { ignoreSearch: true },
      );
      if (!manifestResponse)
        throw new R8CacheError("ROLLBACK_TARGET_UNAVAILABLE", "cached manifest is unavailable");
      const manifest = await manifestResponse.json();
      const artifact = manifest.artifacts.find((item) => item.role === payload.role);
      if (!artifact)
        throw new R8CacheError("RELEASE_MANIFEST_INVALID", `unknown role: ${payload.role}`);
      const deleted = await cache.delete(cachedUrl(payload.releaseId, artifact.url), {
        ignoreSearch: true,
      });
      return { releaseId: payload.releaseId, role: payload.role, deleted };
    }
    case "corrupt-entry": {
      const selectedCache = state.releases[payload.releaseId]?.cacheName;
      if (!selectedCache)
        throw new R8CacheError("ROLLBACK_TARGET_UNAVAILABLE", "release cache is unavailable");
      const cache = await caches.open(selectedCache);
      const manifestResponse = await cache.match(
        cachedUrl(payload.releaseId, "release-manifest.json"), { ignoreSearch: true },
      );
      const manifest = await manifestResponse.json();
      const artifact = manifest.artifacts.find((item) => item.role === payload.role);
      await cache.put(cachedUrl(payload.releaseId, artifact.url), new Response("tampered", {
        headers: {
          "Content-Type": artifact.mediaType,
          "Content-Length": "8",
        },
      }));
      return { releaseId: payload.releaseId, role: payload.role, corrupted: true };
    }
    case "corrupt-metadata": {
      await rawWriteState({ schemaVersion: 999, corrupted: true }, state);
      return { corrupted: true };
    }
    case "prepare-shell":
      return prepareShell();
    case "clear-test-state": {
      for (const name of await caches.keys()) {
        if (name.startsWith(RELEASE_CACHE_PREFIX) || name === SHELL_CACHE)
          await caches.delete(name);
      }
      const empty = createReleaseState({ retentionLimit: 3 });
      await rawWriteState(empty, empty);
      return { cleared: true, state: empty };
    }
    default:
      throw new R8CacheError("COMMAND_UNKNOWN", `unknown R8-C command: ${command}`);
  }
}

function serializeError(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: String(error?.message || error),
    details: error?.details || null,
  };
}

self.addEventListener("install", (event) => {
  event.waitUntil(Promise.resolve());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin)
    return;
  if (url.pathname.includes("/__r8c_cache__/releases/")) {
    event.respondWith((async () => {
      const match = url.pathname.match(/\/__r8c_cache__\/releases\/(writer-review-[0-9a-f]{16})\//);
      if (!match)
        return new Response("invalid cached release URL", { status: 400 });
      const releaseId = match[1];
      const { state } = await loadState();
      const pinned = state.clientPins[event.clientId];
      if (pinned && pinned !== releaseId)
        return new Response("client release pin mismatch", { status: 409 });
      return cachedFetch(releaseId, event.request);
    })());
    return;
  }
  const shellPath = [
    "/r8-update.html", "/r8-update-app.js", "/r8-service-worker.js",
    "/delivery/verified-loader.js", "/delivery/release-state.js",
    "/r6-fixtures/t1-plain-zh.odt",
  ].some((path) => url.pathname.endsWith(path));
  if (shellPath) {
    event.respondWith((async () => {
      const cache = await caches.open(SHELL_CACHE);
      return (await cache.match(event.request, { ignoreSearch: true })) || fetch(event.request);
    })());
  }
});

self.addEventListener("message", (event) => {
  const port = event.ports?.[0];
  if (!port)
    return;
  const run = () => handleCommand(
    event.data?.command, event.data?.payload || {}, event.source,
  );
  const operation = operationQueue.then(run, run);
  operationQueue = operation.catch(() => {});
  event.waitUntil(operation.then(
    (result) => port.postMessage({ ok: true, result }),
    (error) => port.postMessage({ ok: false, error: serializeError(error) }),
  ));
});

export { HEALTH_ANCHOR };
