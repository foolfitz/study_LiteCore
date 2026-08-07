"use strict";

const params = new URLSearchParams(location.search);
const topology = params.get("topology") || "t0";
const phase = params.get("phase") || "initial";
const artifactOrigin = params.get("artifactOrigin") || location.origin;
const statusElement = document.querySelector("#status");
const logElement = document.querySelector("#log");
const encoder = new TextEncoder();
const CANARY_TEXT = "R8-DELIVERY-CANARY-v1\n";

const metrics = {
  schemaVersion: 1,
  release: "R8-A-delivery-discovery",
  topology,
  phase,
  appOrigin: location.origin,
  artifactOrigin,
  browser: navigator.userAgent,
  startedAt: new Date().toISOString(),
  capabilities: {},
  manifest: null,
  faults: {},
  serviceWorker: {},
  cache: {},
  storage: {},
  logs: [],
  pass: false,
};
globalThis.__r8_discovery = metrics;

function log(value) {
  const item = typeof value === "string" ? value : JSON.stringify(value);
  metrics.logs.push(item);
  logElement.textContent += `${item}\n`;
}

function setStatus(value) {
  metrics.status = value;
  statusElement.textContent = value;
}

function serializeError(error) {
  return {
    name: error?.name || "Error",
    message: String(error?.message || error),
  };
}

async function sha256(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

async function storageEstimate() {
  if (!navigator.storage?.estimate)
    return { available: false };
  const estimate = await navigator.storage.estimate();
  return {
    available: true,
    usage: Number.isFinite(estimate.usage) ? estimate.usage : null,
    quota: Number.isFinite(estimate.quota) ? estimate.quota : null,
    persisted: navigator.storage.persisted ? await navigator.storage.persisted() : null,
  };
}

async function fetchBody(url, options = {}) {
  const startedAt = performance.now();
  const response = await fetch(url, {
    cache: "no-store",
    credentials: "omit",
    ...options,
  });
  const buffer = await response.arrayBuffer();
  return {
    status: response.status,
    ok: response.ok,
    bytes: buffer.byteLength,
    sha256: await sha256(buffer),
    text: new TextDecoder().decode(buffer),
    durationMs: performance.now() - startedAt,
    headers: {
      contentType: response.headers.get("Content-Type") || "",
      contentEncoding: response.headers.get("Content-Encoding") || "identity",
      cacheControl: response.headers.get("Cache-Control") || "",
      corp: response.headers.get("Cross-Origin-Resource-Policy") || "",
      cors: response.headers.get("Access-Control-Allow-Origin") || "",
      coop: response.headers.get("Cross-Origin-Opener-Policy") || "",
      coep: response.headers.get("Cross-Origin-Embedder-Policy") || "",
    },
  };
}

async function expectedFailure(action) {
  try {
    const value = await action();
    return { rejected: false, value };
  } catch (error) {
    return { rejected: true, error: serializeError(error) };
  }
}

async function faultDiscovery() {
  const endpoint = `${artifactOrigin}/__r8__/canary`;
  const canaryHash = await sha256(encoder.encode(CANARY_TEXT));
  const ok = await fetchBody(`${endpoint}?scenario=ok`);
  const gzip = await fetchBody(`${endpoint}?scenario=gzip`);
  const wrongType = await fetchBody(`${endpoint}?scenario=wrong-type`);
  const wrongBytes = await fetchBody(`${endpoint}?scenario=wrong-bytes`);
  const http500 = await fetchBody(`${endpoint}?scenario=http-500`);
  const delay = await fetchBody(`${endpoint}?scenario=delay`);
  const truncated = await expectedFailure(() => fetchBody(`${endpoint}?scenario=truncated`));
  truncated.detected = truncated.rejected
    || truncated.value?.bytes !== encoder.encode(CANARY_TEXT).byteLength
    || truncated.value?.sha256 !== canaryHash;
  const result = {
    canaryHash,
    ok,
    gzip,
    wrongType,
    wrongBytes,
    http500,
    delay,
    truncated,
  };
  if (topology === "t1") {
    result.noCors = await expectedFailure(() => fetchBody(`${endpoint}?scenario=no-cors`));
    result.noCorpNoCors = await expectedFailure(() => fetchBody(
      `${endpoint}?scenario=no-corp`, { mode: "no-cors" },
    ));
  }
  result.pass = ok.ok && ok.sha256 === canaryHash
    && gzip.ok && gzip.sha256 === canaryHash && gzip.text === CANARY_TEXT
    && wrongType.ok && wrongType.headers.contentType.startsWith("text/plain")
    && wrongBytes.ok && wrongBytes.sha256 !== canaryHash
    && !http500.ok && http500.status === 500
    && delay.ok && delay.durationMs >= 200
    && truncated.detected
    && (topology !== "t1" || (result.noCors.rejected && result.noCorpNoCors.rejected));
  return result;
}

function serviceWorkerTarget(registration) {
  return registration.active || registration.waiting || registration.installing;
}

async function waitForWorker(registration) {
  const ready = await navigator.serviceWorker.ready;
  let worker = serviceWorkerTarget(ready) || serviceWorkerTarget(registration);
  if (worker?.state === "activated")
    return { registration: ready, worker };
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("service worker activation timeout")), 30000);
    const observe = () => {
      worker = serviceWorkerTarget(ready) || serviceWorkerTarget(registration);
      if (worker?.state === "activated") {
        clearTimeout(timeout);
        resolve();
      } else if (worker) {
        worker.addEventListener("statechange", observe, { once: true });
      }
    };
    observe();
  });
  return { registration: ready, worker };
}

async function swCommand(worker, command, payload = {}, timeoutMs = 180000) {
  const channel = new MessageChannel();
  const response = new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error(`${command} timed out`)), timeoutMs);
    channel.port1.onmessage = (event) => {
      clearTimeout(timeout);
      if (event.data?.ok)
        resolve(event.data.result);
      else
        reject(Object.assign(new Error(event.data?.error?.message || `${command} failed`), event.data?.error));
    };
  });
  worker.postMessage({ command, payload }, [channel.port2]);
  return response;
}

function resolvedArtifact(item) {
  const base = topology === "t1" && item.role !== "entry-html"
    ? `${artifactOrigin}/`
    : `${location.origin}/`;
  return { ...item, url: new URL(item.url, base).href };
}

function cacheArtifacts(manifest) {
  const selected = new Set(["entry-html", "wasm-loader", "wasm-binary"]);
  return manifest.artifacts.filter((item) => selected.has(item.role)).map(resolvedArtifact);
}

async function registerServiceWorker(releaseId) {
  const script = `./r8-discovery-sw.js?release=${encodeURIComponent(releaseId)}`;
  const registration = await navigator.serviceWorker.register(script, { scope: "./" });
  await registration.update();
  return waitForWorker(registration);
}

async function initialCacheProbe(manifest, registration, worker) {
  const cacheName = `oxsdk-r8a-${topology}-${manifest.releaseId}`;
  const artifacts = cacheArtifacts(manifest);
  metrics.storage.before = await storageEstimate();
  const before = await swCommand(worker, "status");
  const roundtrip = await swCommand(worker, "cache-roundtrip", { cacheName, artifacts });
  const verified = await swCommand(worker, "verify-cache", { cacheName, artifacts });
  metrics.storage.after = await storageEstimate();
  const after = await swCommand(worker, "status");
  return {
    cacheName,
    artifacts,
    before,
    roundtrip,
    verified,
    after,
    registeredScope: registration.scope,
    pass: verified.pass
      && verified.verified.length === artifacts.length
      && after.cacheNames.includes(cacheName)
      && verified.verified.some((item) => item.role === "wasm-binary" && item.bytes > 100_000_000),
  };
}

async function restartCacheProbe(manifest, registration, worker) {
  const cacheName = `oxsdk-r8a-${topology}-${manifest.releaseId}`;
  const artifacts = cacheArtifacts(manifest);
  metrics.storage.before = await storageEstimate();
  const before = await swCommand(worker, "status");
  const verified = await swCommand(worker, "verify-cache", { cacheName, artifacts });
  const cleared = await swCommand(worker, "clear-cache", { cacheName });
  const after = await swCommand(worker, "status");
  const unregistered = await registration.unregister();
  metrics.storage.after = await storageEstimate();
  return {
    cacheName,
    artifacts,
    before,
    verified,
    cleared,
    after,
    unregistered,
    pass: before.cacheNames.includes(cacheName)
      && verified.pass
      && cleared.deleted
      && !after.cacheNames.includes(cacheName)
      && unregistered,
  };
}

async function run() {
  setStatus("discovering capabilities");
  metrics.capabilities = {
    secureContext: globalThis.isSecureContext,
    crossOriginIsolated: globalThis.crossOriginIsolated,
    sharedArrayBuffer: typeof SharedArrayBuffer === "function",
    serviceWorker: "serviceWorker" in navigator,
    cacheStorage: "caches" in globalThis,
    storageEstimate: typeof navigator.storage?.estimate === "function",
    compressionStream: typeof CompressionStream === "function",
    decompressionStream: typeof DecompressionStream === "function",
  };
  if (!metrics.capabilities.serviceWorker || !metrics.capabilities.cacheStorage)
    throw new Error("Service Worker or CacheStorage is unavailable");

  const manifestResponse = await fetch("./r8/release-manifest.json", { cache: "no-store" });
  if (!manifestResponse.ok)
    throw new Error(`release manifest HTTP ${manifestResponse.status}`);
  metrics.manifest = await manifestResponse.json();

  setStatus("probing deterministic faults");
  if (phase === "initial")
    metrics.faults = await faultDiscovery();

  setStatus("registering service worker");
  const { registration, worker } = await registerServiceWorker(metrics.manifest.releaseId);
  metrics.serviceWorker.controller = Boolean(navigator.serviceWorker.controller);
  metrics.serviceWorker.workerState = worker.state;
  metrics.serviceWorker.scriptURL = worker.scriptURL;
  metrics.serviceWorker.status = await swCommand(worker, "status");

  setStatus(phase === "restart" ? "verifying persistent cache" : "caching verified release subset");
  try {
    metrics.cache = phase === "restart"
      ? await restartCacheProbe(metrics.manifest, registration, worker)
      : await initialCacheProbe(metrics.manifest, registration, worker);
  } catch (error) {
    metrics.cache = { pass: false, error: serializeError(error) };
  }

  const capabilityPass = metrics.capabilities.secureContext
    && metrics.capabilities.crossOriginIsolated
    && metrics.capabilities.sharedArrayBuffer
    && metrics.capabilities.serviceWorker
    && metrics.capabilities.cacheStorage;
  metrics.pass = capabilityPass
    && metrics.cache.pass
    && (phase !== "initial" || metrics.faults.pass);
  metrics.completedAt = new Date().toISOString();
  setStatus(metrics.pass ? "complete" : "failed");
  log({ type: "r8-discovery-result", pass: metrics.pass, topology, phase });
}

run().catch((error) => {
  metrics.error = serializeError(error);
  metrics.completedAt = new Date().toISOString();
  metrics.pass = false;
  setStatus("failed");
  log({ type: "r8-discovery-error", error: metrics.error });
});
