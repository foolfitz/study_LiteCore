import {
  DeliveryError,
  startVerifiedEngine,
  verifyRelease,
} from "./delivery/verified-loader.js";

const params = new URLSearchParams(location.search);
const topology = params.get("topology") || "t0";
const policy = params.get("policy") || "standard";
const transport = params.get("transport") || "identity";
const cacheMode = params.get("cache") || "cold";
const scenario = params.get("scenario") || "success";
const expectedCode = params.get("expect") || null;
const artifactOrigin = params.get("artifactOrigin") || location.origin;
const fault = params.get("deliveryFault") || null;
const faultRole = params.get("faultRole") || null;
const staleReleaseId = params.get("staleReleaseId") || null;
const redirectTargetOrigin = params.get("redirectTargetOrigin") || null;
const documentPath = params.get("document") || "./r7-compat-fixtures/l0-t1-plain-zh.odt";
const documentName = params.get("name") || documentPath.split("/").at(-1) || "input.odt";
const searchText = params.get("search") || "Final line：ODT round-trip 完整性檢查。";
const statusElement = document.querySelector("#status");
const logElement = document.querySelector("#log");
const canvas = document.querySelector("#tile");

const metrics = {
  schemaVersion: 1,
  release: "R8-B-versioned-artifact-delivery",
  browser: navigator.userAgent,
  topology,
  policy,
  transport,
  cacheMode,
  scenario,
  artifactOrigin,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  startedAt: new Date().toISOString(),
  phases: [],
  workersStarted: 0,
  documentMutations: 0,
  verified: null,
  candidateReleaseId: null,
  handshake: null,
  document: null,
  output: null,
  error: null,
  status: "running",
  pass: false,
};
globalThis.__r8_delivery = metrics;

let outputBuffer = null;
globalThis.__r8_delivery_output_base64 = () => {
  if (!outputBuffer)
    throw new Error("R8-B output is unavailable");
  const bytes = new Uint8Array(outputBuffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
};

function setStatus(value) {
  metrics.status = value;
  statusElement.textContent = value;
}

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  metrics.phases.push({ atMs: performance.now(), value: typeof value === "string" ? value : value.type || "detail" });
  logElement.textContent += `${text}\n`;
}

function serializeError(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: String(error?.message || error),
    details: error?.details || null,
  };
}

async function sha256(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function summarizeVerified(verified) {
  return {
    releaseId: verified.releaseId,
    policy: verified.policy,
    transport: verified.transport,
    cacheMode: verified.cacheMode,
    manifestUrl: verified.manifestUrl,
    artifactOrigin: verified.artifactOrigin,
    durationMs: verified.durationMs,
    artifacts: verified.artifacts.map(({ buffer, ...item }) => item),
    pass: verified.pass,
  };
}

async function releaseFromIndex() {
  const response = await fetch("./releases/index.json", { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`release index HTTP ${response.status}`);
  const index = await response.json();
  const selected = index.releases.find((item) => item.policy === policy);
  if (!selected)
    throw new Error(`release index has no policy ${policy}`);
  metrics.candidateReleaseId = selected.releaseId;
  return new URL(`./${selected.manifestUrl}`, location.href);
}

function transformedArtifactUrl(role, url) {
  url.searchParams.set("representation", transport);
  if (fault && role === faultRole) {
    url.searchParams.set("fault", fault);
    if (staleReleaseId)
      url.searchParams.set("staleReleaseId", staleReleaseId);
    if (redirectTargetOrigin)
      url.searchParams.set("redirectTargetOrigin", redirectTargetOrigin);
  }
  return url;
}

async function verifyCandidate(signal = null) {
  const manifestUrl = params.get("manifestUrl")
    ? new URL(params.get("manifestUrl"), location.href) : await releaseFromIndex();
  if (params.get("manifestFault"))
    manifestUrl.searchParams.set("fault", params.get("manifestFault"));
  log({ type: "manifest-selected", manifestUrl: manifestUrl.href, policy });
  const timeoutMs = Number(params.get("verifyTimeoutMs") || 600000);
  const verified = await verifyRelease({
    manifestUrl,
    policy,
    transport,
    cacheMode,
    timeoutMs,
    signal,
    artifactOrigin,
    urlTransform: transformedArtifactUrl,
  });
  metrics.verified = summarizeVerified(verified);
  return verified;
}

async function exerciseDocument(session) {
  const fixtureResponse = await fetch(new URL(documentPath, location.href), { cache: "no-cache" });
  if (!fixtureResponse.ok)
    throw new Error(`document fixture HTTP ${fixtureResponse.status}`);
  const fixture = await fixtureResponse.arrayBuffer();
  const fixtureHash = await sha256(fixture);
  const openedAt = performance.now();
  const documentHandle = await session.engine.open(fixture, {
    name: documentName,
    transfer: false,
    timeoutMs: 180000,
  });
  const openMs = performance.now() - openedAt;
  const widthTwips = Math.min(documentHandle.widthTwips, 4800);
  const heightTwips = Math.min(documentHandle.heightTwips, 4800);
  const tile = await documentHandle.render({
    xTwips: 0, yTwips: 0, widthTwips, heightTwips,
    canvasWidthPx: 256, canvasHeightPx: 256,
  }, { timeoutMs: 180000 });
  canvas.width = tile.width;
  canvas.height = tile.height;
  canvas.getContext("2d").putImageData(new ImageData(
    new Uint8ClampedArray(tile.pixels), tile.width, tile.height,
  ), 0, 0);
  const search = await documentHandle.search(searchText, { timeoutMs: 60000 });
  outputBuffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
  const outputHash = await sha256(outputBuffer);
  await documentHandle.close({ timeoutMs: 180000 });
  metrics.document = {
    name: documentName,
    path: documentPath,
    inputBytes: fixture.byteLength,
    inputSha256: fixtureHash,
    openMs,
    widthTwips: documentHandle.widthTwips,
    heightTwips: documentHandle.heightTwips,
    tile: { width: tile.width, height: tile.height, revision: tile.revision },
    search: { text: searchText, found: search.found },
    closeCompleted: true,
  };
  metrics.output = { bytes: outputBuffer.byteLength, sha256: outputHash };
  return search.found;
}

async function runSuccess() {
  const verified = await verifyCandidate();
  if (scenario === "handshake-mismatch")
    verified.sdkManifest = { ...verified.sdkManifest, profile: "intentional-mismatch" };
  const session = await startVerifiedEngine(verified, {
    timeoutMs: 180000,
    workerFactory(url) {
      metrics.workersStarted += 1;
      return new Worker(url, { name: `r8-b-${metrics.workersStarted}` });
    },
  });
  metrics.handshake = {
    releaseId: session.engine.manifest.releaseId,
    profile: session.engine.manifest.profile,
    sdkVersion: session.engine.manifest.sdkVersion,
    coreCommit: session.engine.manifest.coreCommit,
    artifactFiles: session.engine.manifest.artifactFiles,
    resourcePacks: session.engine.manifest.resourcePacks,
  };
  if (scenario === "fidelity-restart") {
    try {
      session.requestFidelity(policy === "standard" ? "full-fidelity" : "standard");
      throw new Error("fidelity switch unexpectedly succeeded");
    } catch (error) {
      if (!(error instanceof DeliveryError) || error.code !== "FONT_PACK_RESTART_REQUIRED")
        throw error;
      metrics.error = serializeError(error);
      metrics.pass = metrics.workersStarted === 1 && metrics.documentMutations === 0;
      session.dispose();
      return;
    }
  }
  const searchFound = await exerciseDocument(session);
  session.dispose();
  metrics.pass = searchFound
    && metrics.workersStarted >= 1
    && metrics.documentMutations === 0
    && metrics.handshake.releaseId === verified.releaseId
    && metrics.output.bytes > 0;
}

async function main() {
  try {
    setStatus("verifying-release");
    if (scenario === "verify-only") {
      const verified = await verifyCandidate();
      metrics.pass = verified.pass === true
        && metrics.workersStarted === 0 && metrics.documentMutations === 0;
    } else if (scenario === "cancel") {
      const controller = new AbortController();
      setTimeout(() => controller.abort(), Number(params.get("cancelAfterMs") || 25));
      try {
        await verifyCandidate(controller.signal);
        throw new Error("cancelled release unexpectedly verified");
      } catch (error) {
        metrics.error = serializeError(error);
        metrics.pass = metrics.error.code === (expectedCode || "DELIVERY_ABORTED")
          && metrics.workersStarted === 0 && metrics.documentMutations === 0;
      }
    } else if (scenario === "negative") {
      try {
        await verifyCandidate();
        throw new Error("negative release unexpectedly verified");
      } catch (error) {
        metrics.error = serializeError(error);
        metrics.pass = Boolean(expectedCode)
          && metrics.error.code === expectedCode
          && metrics.workersStarted === 0
          && metrics.documentMutations === 0;
      }
    } else {
      await runSuccess();
    }
  } catch (error) {
    metrics.error = serializeError(error);
    metrics.pass = Boolean(expectedCode)
      && metrics.error.code === expectedCode
      && metrics.documentMutations === 0
      && (scenario === "handshake-mismatch" ? metrics.workersStarted === 1 : metrics.workersStarted === 0);
  }
  metrics.completedAt = new Date().toISOString();
  setStatus(metrics.pass ? "complete" : "failed");
  log({ type: "r8-delivery-result", pass: metrics.pass, scenario, workersStarted: metrics.workersStarted });
}

main();
