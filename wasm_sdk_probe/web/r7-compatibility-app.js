import { createDocumentEngine } from "./document-sdk.js";
import { DocumentPreflightError, preflightDocument } from "./r7/document-preflight.js";

const $ = (selector) => document.querySelector(selector);
const params = new URLSearchParams(location.search);
const group = params.get("group") === "repeat" ? "repeat" : "full";
const workerDwellMs = Number(params.get("workerDwellMs") || (group === "full" ? 1100 : 0));
const batchStart = Math.max(0, Number(params.get("batchStart") || 0));
const batchSize = Math.max(0, Number(params.get("batchSize") || 0));
const metrics = {
  schemaVersion: 1,
  release: "R7-C",
  group,
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  manifest: null,
  artifact: null,
  cases: [],
  workers: { created: 0, terminated: 0 },
  workerDwellMs,
  batch: { start: batchStart, size: batchSize },
  phase: "loading",
  complete: false,
  pass: false,
  decisionCandidate: "STOP",
  error: null,
};
globalThis.__probe_metrics = metrics;
globalThis.__r7_compatibility = metrics;

const outputs = new Map();

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  $("#log").textContent += `[${performance.now().toFixed(1)} ms] ${text}\n`;
  $("#log").scrollTop = $("#log").scrollHeight;
}

function serializeError(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "DOCUMENT_OPEN_FAILED",
    message: String(error?.message || error),
    details: error?.details || null,
  };
}

async function sha256(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)]
    .map((value) => value.toString(16).padStart(2, "0")).join("");
}

function bufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
}

globalThis.__r7_compatibility_output_ids = () => [...outputs.keys()];
globalThis.__r7_compatibility_get_output_base64 = (id) => {
  if (!outputs.has(id))
    throw new Error(`unknown compatibility output: ${id}`);
  return bufferToBase64(outputs.get(id));
};

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

function engineFactory(label) {
  return createDocumentEngine({
    workerUrl: "./profiles/writer-review-r6/sdk-worker.js",
    timeoutMs: 60000,
    workerFactory(url) {
      const worker = new Worker(url, { name: `r7-c-${label}-${metrics.workers.created + 1}` });
      metrics.workers.created += 1;
      let terminated = false;
      return {
        addEventListener: (...args) => worker.addEventListener(...args),
        postMessage: (...args) => worker.postMessage(...args),
        terminate() {
          if (terminated)
            return;
          terminated = true;
          metrics.workers.terminated += 1;
          worker.terminate();
        },
      };
    },
  });
}

function captureArtifact(engine) {
  if (metrics.artifact)
    return;
  metrics.artifact = {
    profile: engine.manifest.profile,
    sdkVersion: engine.manifest.sdkVersion,
    coreCommit: engine.manifest.coreCommit,
    loader: engine.manifest.artifactFiles?.["probe.js"],
    wasm: engine.manifest.artifactFiles?.["probe.wasm"],
  };
}

async function tileDigest(documentHandle, yRatio, scale) {
  const widthTwips = Math.min(documentHandle.widthTwips, 7680);
  const heightTwips = Math.min(documentHandle.heightTwips, 7680);
  const yTwips = Math.max(0, Math.min(
    documentHandle.heightTwips - heightTwips,
    Math.round((documentHandle.heightTwips - heightTwips) * yRatio),
  ));
  const started = performance.now();
  const tile = await documentHandle.render({
    xTwips: 0, yTwips, widthTwips, heightTwips,
    canvasWidthPx: Math.round(128 * scale),
    canvasHeightPx: Math.round(128 * scale),
  }, { timeoutMs: 180000 });
  return {
    yRatio, scale, yTwips, width: tile.width, height: tile.height,
    bytes: tile.pixels.byteLength, sha256: await sha256(tile.pixels),
    revision: tile.revision, ms: performance.now() - started,
  };
}

async function healthCheck(controlBytes, label) {
  const engine = await engineFactory(`health-${label}`);
  try {
    captureArtifact(engine);
    const documentHandle = await engine.open(controlBytes.slice(0), {
      name: "health.odt", transfer: true, timeoutMs: 180000,
    });
    await tileDigest(documentHandle, 0, 1);
    await documentHandle.close({ timeoutMs: 180000 });
    return { pass: true };
  } catch (error) {
    return { pass: false, error: serializeError(error) };
  } finally {
    engine.dispose();
  }
}

async function runCase(item, controlBytes) {
  const result = {
    id: item.id, tier: item.tier, path: item.path, expected: item.expected,
    inputBytes: null, inputSha256: null, preflight: null, opened: false,
    dimensions: null, tiles: [], anchors: [], semantics: {}, mutation: null,
    output: null, close: null, health: null, error: null, pass: false,
  };
  $("#current").textContent = item.id;
  const bytes = await fetchBytes(`./r7-compat-fixtures/${item.path}`);
  result.inputBytes = bytes.byteLength;
  result.inputSha256 = await sha256(bytes);
  try {
    result.preflight = preflightDocument(bytes, {
      name: item.path, limits: metrics.manifest.limits,
    });
  } catch (error) {
    result.error = serializeError(error);
    result.preflight = { status: "typed-failure", error: result.error };
  }
  if (item.expected.open === "typed-failure") {
    result.health = await healthCheck(controlBytes, item.id);
    result.pass = result.error?.code === item.expected.typedCode
      && result.health.pass
      && !result.opened;
    return result;
  }
  if (result.error)
    return result;

  const engine = await engineFactory(item.id);
  try {
    captureArtifact(engine);
    const openStarted = performance.now();
    const documentHandle = await engine.open(bytes.slice(0), {
      name: item.path, transfer: true, timeoutMs: item.limits.openMs,
    });
    result.opened = true;
    result.openMs = performance.now() - openStarted;
    result.dimensions = {
      parts: documentHandle.parts,
      widthTwips: documentHandle.widthTwips,
      heightTwips: documentHandle.heightTwips,
    };
    for (const ratio of [0, 0.5, 1])
      result.tiles.push(await tileDigest(documentHandle, ratio, 1));
    result.tiles.push(await tileDigest(documentHandle, 0.5, 1.5));
    for (const anchor of item.anchors) {
      const found = await documentHandle.search(anchor.text, { timeoutMs: 60000 });
      const selection = found.found ? await documentHandle.getSelection({ timeoutMs: 60000 }) : null;
      result.anchors.push({
        ...anchor, found: found.found, selectionText: selection?.text || "",
        revision: found.revision,
      });
    }
    if (item.features.includes("comment") || item.features.includes("comments")) {
      const comments = await documentHandle.listComments({ timeoutMs: 60000 });
      result.semantics.comments = { count: comments.comments.length, revision: comments.revision };
    }
    if (item.features.includes("tracked-changes")) {
      const changes = await documentHandle.listTrackedChanges({ timeoutMs: 60000 });
      result.semantics.trackedChanges = { count: changes.changes.length, revision: changes.revision };
    }
    if (item.mutationPolicy === "append-and-save") {
      const anchor = item.anchors[0];
      const selection = await documentHandle.search(anchor.text, { timeoutMs: 60000 });
      if (!selection.found)
        throw new Error(`mutation anchor not found: ${anchor.text}`);
      const replacement = `${anchor.text} R7-C mutation`;
      const replaced = await documentHandle.replaceSelection(replacement, {
        expectedRevision: documentHandle.revision, timeoutMs: 60000,
      });
      result.mutation = {
        kind: "revision-guarded-replace", beforeRevision: selection.revision,
        revision: replaced.revision, replacement,
      };
      const saved = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
      outputs.set(item.id, saved);
      result.output = { bytes: saved.byteLength, sha256: await sha256(saved), format: "odt" };
    }
    const closeStarted = performance.now();
    await documentHandle.close({ timeoutMs: 180000 });
    result.close = { status: "passed", ms: performance.now() - closeStarted };
    result.pass = result.opened
      && result.tiles.length === 4
      && result.tiles.every((tile) => tile.bytes === tile.width * tile.height * 4)
      && result.anchors.every((anchor) => anchor.found && anchor.selectionText === anchor.text)
      && (!result.mutation || result.output?.bytes > 0)
      && result.close.status === "passed";
  } catch (error) {
    result.error = serializeError(error);
  } finally {
    engine.dispose();
  }
  return result;
}

function selectedDocuments(documents) {
  let selected;
  if (group === "full") {
    selected = documents.filter((item) =>
      item.tier === "L2" || item.tier === "L3" || item.tier === "L4"
      || item.id.startsWith("l1-hyperlink-font"));
  } else {
    selected = documents.filter((item) =>
      item.tier === "L0"
      || ["l1-plain", "l1-layout-table-image", "l1-review"]
        .some((prefix) => item.id.startsWith(prefix)));
  }
  return batchSize > 0 ? selected.slice(batchStart, batchStart + batchSize) : selected;
}

async function main() {
  try {
    metrics.manifest = await fetchJson("./r7-compat-fixtures/manifest.json");
    $("#group").textContent = group;
    const control = metrics.manifest.documents.find((item) => item.id === "l0-t1");
    const controlBytes = await fetchBytes(`./r7-compat-fixtures/${control.path}`);
    const documents = selectedDocuments(metrics.manifest.documents);
    metrics.phase = "matrix";
    for (const [index, item] of documents.entries()) {
      const result = await runCase(item, controlBytes);
      metrics.cases.push(result);
      $("#completed").textContent = `${metrics.cases.length} / ${documents.length}`;
      log({ id: result.id, pass: result.pass, code: result.error?.code, opened: result.opened });
      if (!result.pass && item.expected.open === "pass")
        break;
      if (workerDwellMs > 0 && index + 1 < documents.length)
        await new Promise((resolve) => setTimeout(resolve, workerDwellMs));
    }
    metrics.pass = metrics.crossOriginIsolated
      && metrics.cases.length === documents.length
      && metrics.cases.every((item) => item.pass)
      && metrics.artifact?.profile === "writer-review";
    metrics.decisionCandidate = metrics.pass ? "PARTIAL_GO_ODT_FIRST" : "STOP";
    metrics.phase = "complete";
    metrics.complete = true;
    $("#decision").textContent = metrics.decisionCandidate;
    $("#status").textContent = metrics.pass ? "compatibility group pass" : "compatibility group failed";
  } catch (error) {
    metrics.error = serializeError(error);
    metrics.phase = "error";
    metrics.complete = true;
    $("#status").textContent = `error: ${metrics.error.code}`;
    log(metrics.error);
  }
}

main();
