import { createDocumentEngine } from "./document-sdk.js";

const $ = (selector) => document.querySelector(selector);
const params = new URLSearchParams(location.search);
const fixtureId = params.get("fixture") || "t2-original";
const requestedArtifact = params.get("artifact") || "writer-review";
const workerUrls = {
  "writer-review": "./profiles/writer-review-r6/sdk-worker.js",
  diagnostic: "./profiles/finding-012-diagnostic/sdk-worker.js",
};
const workerUrl = workerUrls[requestedArtifact] || null;
const timeoutMs = Math.max(1000, Math.min(180000, Number(params.get("timeoutMs") || 10000)));
const metrics = {
  schemaVersion: 1,
  release: requestedArtifact === "diagnostic"
    ? "finding-012-r7-attribution"
    : "finding-012-r7-minimization",
  requestedArtifact,
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  fixture: null,
  artifact: null,
  workers: { created: 0, terminated: 0, active: 0, forcedTermination: false },
  handles: { opened: 0, closed: 0, active: 0 },
  sdkEvents: [],
  stage: "loading",
  close: null,
  complete: false,
  pass: false,
  error: null,
};
globalThis.__probe_metrics = metrics;
globalThis.__finding_012 = metrics;

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  $("#log").textContent += `[${performance.now().toFixed(1)} ms] ${text}\n`;
}

function setStage(stage) {
  metrics.stage = stage;
  $("#stage").textContent = stage;
}

function serializeError(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: String(error?.message || error),
    details: error?.details || null,
  };
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fetch failed ${response.status}: ${path}`);
  return response.json();
}

async function fetchBytes(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fetch failed ${response.status}: ${path}`);
  return response.arrayBuffer();
}

function createEngine() {
  if (!workerUrl)
    throw Object.assign(new Error(`artifact is not allowlisted: ${requestedArtifact}`), { code: "UNKNOWN_ARTIFACT" });
  return createDocumentEngine({
    workerUrl,
    timeoutMs: 60000,
    debug: true,
    workerFactory(url) {
      const worker = new Worker(url, { name: `finding-012-${fixtureId}` });
      metrics.workers.created += 1;
      metrics.workers.active += 1;
      let terminated = false;
      return {
        addEventListener: (...args) => worker.addEventListener(...args),
        postMessage: (...args) => worker.postMessage(...args),
        terminate() {
          if (terminated)
            return;
          terminated = true;
          metrics.workers.terminated += 1;
          metrics.workers.active -= 1;
          worker.terminate();
        },
      };
    },
  });
}

async function main() {
  let engine = null;
  let documentHandle = null;
  try {
    const manifest = await fetchJson("./r7-finding-012/manifest.json");
    const fixture = manifest.variants.find((item) => item.id === fixtureId);
    if (!fixture)
      throw Object.assign(new Error(`fixture is not in finding 012 allowlist: ${fixtureId}`), { code: "UNKNOWN_FIXTURE" });
    metrics.fixture = {
      id: fixture.id,
      path: fixture.path,
      bytes: fixture.bytes,
      sha256: fixture.sha256,
      retainedFeatures: fixture.retainedFeatures,
      removedFeatures: fixture.removedFeatures,
    };
    $("#fixture").textContent = fixture.id;
    $("#features").textContent = fixture.retainedFeatures.join(", ") || "none";
    const bytes = await fetchBytes(`./r7-finding-012/${fixture.path}`);
    if (bytes.byteLength !== fixture.bytes)
      throw new Error(`fixture byte mismatch: ${bytes.byteLength}/${fixture.bytes}`);

    setStage("engine-init");
    engine = await createEngine();
    engine.onEvent((event) => {
      metrics.sdkEvents.push({ atMs: performance.now(), ...event });
      log({ sdkEvent: event });
    });
    metrics.artifact = {
      profile: engine.manifest.profile,
      sdkVersion: engine.manifest.sdkVersion,
      coreCommit: engine.manifest.coreCommit,
      loader: engine.manifest.artifactFiles?.["probe.js"],
      wasm: engine.manifest.artifactFiles?.["probe.wasm"],
    };

    setStage("open");
    const openStarted = performance.now();
    documentHandle = await engine.open(bytes, {
      name: fixture.path, transfer: true, timeoutMs: 180000,
    });
    metrics.handles.opened += 1;
    metrics.handles.active += 1;
    metrics.open = {
      ms: performance.now() - openStarted,
      documentHandle: documentHandle.handle,
      revision: documentHandle.revision,
      parts: documentHandle.parts,
      widthTwips: documentHandle.widthTwips,
      heightTwips: documentHandle.heightTwips,
    };

    setStage("close");
    const closeStarted = performance.now();
    try {
      await documentHandle.close({ timeoutMs });
      metrics.handles.closed += 1;
      metrics.handles.active -= 1;
      documentHandle = null;
      const recoveryEvents = metrics.sdkEvents
        .filter((event) => event.event?.startsWith("document-close-recovery"))
        .map((event) => ({ event: event.event, detail: event.detail || null }));
      metrics.close = {
        status: "passed",
        ms: performance.now() - closeStarted,
        timeoutMs,
        recovery: {
          used: recoveryEvents.length > 0,
          events: recoveryEvents,
        },
      };
    } catch (error) {
      metrics.close = {
        status: "typed-failure", ms: performance.now() - closeStarted,
        timeoutMs, error: serializeError(error),
      };
    }
    engine.dispose();
    if (metrics.close.status !== "passed") {
      metrics.workers.forcedTermination = true;
      metrics.handles.active = 0;
    }
    setStage("complete");
    metrics.pass = metrics.close.status === "passed"
      && metrics.handles.closed === 1
      && metrics.workers.active === 0;
    metrics.complete = true;
    $("#close").textContent = metrics.close.status === "passed"
      ? `${metrics.close.ms.toFixed(1)} ms` : `${metrics.close.error.code} at ${timeoutMs} ms`;
    $("#status").textContent = metrics.pass ? "close pass" : "close timeout/failure";
    log({ complete: true, close: metrics.close, workers: metrics.workers });
  } catch (error) {
    engine?.dispose();
    metrics.error = serializeError(error);
    metrics.complete = true;
    setStage("error");
    $("#status").textContent = `${metrics.error.code}: ${metrics.error.message}`;
    log(metrics.error);
  }
}

main();
