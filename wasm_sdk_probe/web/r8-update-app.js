"use strict";

import { startVerifiedEngine, verifyRelease } from "./delivery/verified-loader.js";

const params = new URLSearchParams(location.search);
const action = params.get("action") || "status";
const topology = params.get("topology") || "t0";
const artifactOrigin = params.get("artifactOrigin") || location.origin;
const expectedCode = params.get("expect") || null;
const statusElement = document.querySelector("#status");
const releaseElement = document.querySelector("#release-state");
const logElement = document.querySelector("#log");
const canvas = document.querySelector("#tile");

const metrics = {
  schemaVersion: 1,
  release: "R8-C-service-worker",
  browser: navigator.userAgent,
  topology,
  action,
  artifactOrigin,
  online: navigator.onLine,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  startedAt: new Date().toISOString(),
  serviceWorker: null,
  releaseSet: null,
  commands: [],
  runtime: null,
  error: null,
  status: "running",
  pass: false,
};
globalThis.__r8_update = metrics;

function setStatus(value) {
  metrics.status = value;
  statusElement.textContent = value;
}

function log(value) {
  logElement.textContent += `${typeof value === "string" ? value : JSON.stringify(value)}\n`;
}

function serializeError(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: String(error?.message || error),
    details: error?.details || null,
  };
}

function workerTarget(registration) {
  return registration.active || registration.waiting || registration.installing;
}

async function activeWorker() {
  const registration = await navigator.serviceWorker.register(
    "./r8-service-worker.js", { type: "module", scope: "./" },
  );
  let worker = workerTarget(registration);
  if (worker?.state !== "activated") {
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("Service Worker activation timeout")), 30000);
      const check = () => {
        worker = workerTarget(registration);
        if (worker?.state === "activated") {
          clearTimeout(timeout);
          resolve();
        } else {
          worker?.addEventListener("statechange", check, { once: true });
        }
      };
      check();
    });
  }
  return { registration, worker };
}

async function command(name, payload = {}, timeoutMs = 900000) {
  const { worker } = await activeWorker();
  const channel = new MessageChannel();
  const response = new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error(`${name} timed out`)), timeoutMs);
    channel.port1.onmessage = (event) => {
      clearTimeout(timeout);
      if (event.data?.ok)
        resolve(event.data.result);
      else {
        const error = Object.assign(
          new Error(event.data?.error?.message || `${name} failed`), event.data?.error || {},
        );
        reject(error);
      }
    };
  });
  worker.postMessage({ command: name, payload }, [channel.port2]);
  try {
    const result = await response;
    metrics.commands.push({ name, status: "passed", result });
    return result;
  } catch (error) {
    metrics.commands.push({ name, status: "failed", error: serializeError(error) });
    throw error;
  }
}
globalThis.__r8_update_command = command;

async function loadReleaseSet() {
  const response = await fetch("./r8c/release-set.json", {
    cache: "no-store", credentials: "omit",
  });
  if (!response.ok)
    throw new Error(`release set HTTP ${response.status}`);
  const value = await response.json();
  if (value.pass !== true || !Array.isArray(value.releases))
    throw new Error("release set is invalid");
  metrics.releaseSet = value;
  return value;
}

function releaseSlot(releaseSet, slot) {
  const item = releaseSet.releases.find((release) => release.slot === slot);
  if (!item)
    throw new Error(`release set has no slot ${slot}`);
  return {
    ...item,
    manifestUrl: new URL(`./r8c/${item.manifestUrl}`, location.href).href,
  };
}

function cachedManifestUrl(releaseId) {
  return new URL(`./__r8c_cache__/releases/${releaseId}/release-manifest.json`, location.href);
}

async function runtimeHealth(releaseId, options = {}) {
  await command("pin", { releaseId });
  let session = null;
  let documentHandle = null;
  try {
    let verified;
    try {
      verified = await verifyRelease({
        manifestUrl: cachedManifestUrl(releaseId),
        policy: "standard",
        transport: "identity",
        cacheMode: "warm",
        artifactOrigin: location.origin,
        requireIsolation: true,
        timeoutMs: 600000,
      });
    } catch (error) {
      throw Object.assign(new Error(`cached release validation failed: ${error?.message || error}`), {
        code: "CACHED_ARTIFACT_INVALID",
        details: { releaseId, cause: error?.code || error?.name || "Error" },
      });
    }
    let workersStarted = 0;
    session = await startVerifiedEngine(verified, {
      timeoutMs: 180000,
      workerFactory(url) {
        workersStarted += 1;
        return new Worker(url, { name: `r8-c-health-${workersStarted}` });
      },
    });
    const fixtureResponse = await fetch("./r6-fixtures/t1-plain-zh.odt", {
      cache: "no-cache", credentials: "omit",
    });
    if (!fixtureResponse.ok)
      throw new Error(`health fixture HTTP ${fixtureResponse.status}`);
    const fixture = await fixtureResponse.arrayBuffer();
    documentHandle = await session.engine.open(fixture, {
      name: "r8-c-health.odt", transfer: false, timeoutMs: 180000,
    });
    const search = await documentHandle.search(
      "Final line：ODT round-trip 完整性檢查。", { timeoutMs: 60000 },
    );
    const tile = await documentHandle.render({
      xTwips: 0,
      yTwips: 0,
      widthTwips: Math.min(documentHandle.widthTwips, 4800),
      heightTwips: Math.min(documentHandle.heightTwips, 4800),
      canvasWidthPx: 256,
      canvasHeightPx: 256,
    }, { timeoutMs: 180000 });
    canvas.width = tile.width;
    canvas.height = tile.height;
    canvas.getContext("2d").putImageData(new ImageData(
      new Uint8ClampedArray(tile.pixels), tile.width, tile.height,
    ), 0, 0);
    await documentHandle.close({ timeoutMs: 180000 });
    documentHandle = null;
    const result = {
      releaseId,
      verifiedArtifacts: verified.artifacts.length,
      workersStarted,
      searchFound: search.found,
      tile: { width: tile.width, height: tile.height, revision: tile.revision },
      documentMutations: 0,
      pass: search.found && workersStarted === 1,
    };
    metrics.runtime = result;
    return result;
  } finally {
    if (documentHandle)
      await documentHandle.close({ timeoutMs: 10000 }).catch(() => {});
    session?.dispose();
    if (!options.keepPin)
      await command("unpin").catch(() => {});
  }
}
globalThis.__r8_runtime_health = runtimeHealth;

async function stageSlot(slot, extra = {}) {
  const releaseSet = metrics.releaseSet || await loadReleaseSet();
  const release = releaseSlot(releaseSet, slot);
  const result = await command("stage-release", {
    releaseId: release.releaseId,
    manifestUrl: release.manifestUrl,
    manifestSha256: release.manifestSha256,
    requiredArtifactCount: release.requiredArtifactCount || 15,
    artifactOrigin,
    ...extra,
  });
  return { release, result };
}

async function updateVisibleState() {
  const status = await command("status");
  const state = status.state;
  releaseElement.textContent = [
    `current: ${state.currentReleaseId || "none"}`,
    `candidate: ${state.candidate?.releaseId || "none"}`,
    `online: ${navigator.onLine}`,
  ].join("; ");
  metrics.serviceWorker = status;
  return status;
}

async function executeAction() {
  if (!("serviceWorker" in navigator) || !("caches" in globalThis))
    throw new Error("Service Worker or CacheStorage is unavailable");
  await activeWorker();
  if (action === "clear") {
    await command("clear-test-state");
  } else if (action === "prepare-shell") {
    await command("prepare-shell");
  } else if (action === "fresh") {
    const { release } = await stageSlot("A");
    await command("activate-release", { releaseId: release.releaseId });
    const health = await runtimeHealth(release.releaseId);
    if (!health.pass)
      throw new Error("fresh release health failed");
    await command("health-result", { releaseId: release.releaseId, pass: true });
  } else if (action === "stage") {
    await stageSlot(params.get("slot") || "B", {
      interruptAt: params.get("interruptAt"),
      interruptRole: params.get("interruptRole"),
      writeFailureRole: params.get("writeFailureRole"),
    });
  } else if (action === "activate") {
    const releaseSet = await loadReleaseSet();
    const release = releaseSlot(releaseSet, params.get("slot") || "B");
    await command("activate-release", {
      releaseId: release.releaseId,
      interruptAt: params.get("interruptAt"),
    });
    if (params.get("health") === "fail") {
      await command("health-result", {
        releaseId: release.releaseId, pass: false, reason: "intentional-r8c-health-failure",
      });
    } else {
      const health = await runtimeHealth(release.releaseId);
      await command("health-result", { releaseId: release.releaseId, pass: health.pass });
    }
  } else if (action === "offline" || action === "health") {
    const status = await command("status");
    const releaseId = params.get("releaseId") || status.state.currentReleaseId;
    if (!releaseId)
      throw Object.assign(new Error("offline release is unavailable"), {
        code: "OFFLINE_RELEASE_UNAVAILABLE",
      });
    const health = await runtimeHealth(releaseId, { keepPin: params.get("keepPin") === "1" });
    if (!health.pass)
      throw new Error("cached runtime health failed");
  } else if (action === "pin-only") {
    const status = await command("status");
    const releaseId = params.get("releaseId") || status.state.currentReleaseId;
    await command("pin", { releaseId });
  } else if (action === "recover") {
    await command("recover");
  } else if (action === "repair") {
    const releaseSet = await loadReleaseSet();
    const release = releaseSet.releases.find((item) => item.releaseId === params.get("releaseId"));
    if (!release)
      throw new Error("repair release is absent from the frozen release set");
    await command("repair-release", {
      releaseId: release.releaseId,
      manifestUrl: new URL(`./r8c/${release.manifestUrl}`, location.href).href,
      manifestSha256: release.manifestSha256,
      artifactOrigin,
    });
  } else if (action === "rollback") {
    await command("rollback", { releaseId: params.get("releaseId") });
  } else if (action === "verify-cache") {
    await command("verify-cached", { releaseId: params.get("releaseId") });
  } else if (action === "delete-entry" || action === "corrupt-entry") {
    await command(action, {
      releaseId: params.get("releaseId"), role: params.get("role") || "app-module",
    });
  } else if (action === "corrupt-metadata") {
    await command("corrupt-metadata");
  } else if (action === "evict") {
    await command("evict");
  } else if (action !== "status") {
    throw new Error(`unknown R8-C action: ${action}`);
  }
  await updateVisibleState();
}

for (const [selector, handler] of [
  ["#retry", () => location.reload()],
  ["#continue", () => updateVisibleState()],
  ["#reload", async () => {
    if (metrics.unsavedMutation)
      throw Object.assign(new Error("unsaved mutation blocks reload"), { code: "UNSAVED_RELOAD_BLOCKED" });
    location.reload();
  }],
  ["#rollback", async () => {
    const status = await command("status");
    await command("rollback", { releaseId: status.state.lastKnownGoodReleaseId });
    await updateVisibleState();
  }],
]) {
  document.querySelector(selector).addEventListener("click", () => Promise.resolve(handler()).catch(log));
}

async function main() {
  try {
    setStatus("running");
    await executeAction();
    metrics.pass = true;
  } catch (error) {
    metrics.error = serializeError(error);
    metrics.pass = Boolean(expectedCode) && metrics.error.code === expectedCode;
    log(metrics.error);
    if (metrics.pass) {
      try {
        await updateVisibleState();
      } catch (statusError) {
        metrics.pass = false;
        metrics.statusError = serializeError(statusError);
        log(metrics.statusError);
      }
    }
  }
  metrics.completedAt = new Date().toISOString();
  setStatus(metrics.pass ? "complete" : "failed");
  log({ type: "r8-c-result", action, pass: metrics.pass });
}

main();
