import { SdkAbortError, createDocumentEngine } from "./document-sdk.js";

const $ = (selector) => document.querySelector(selector);
const params = new URLSearchParams(location.search);
const scenario = params.get("scenario") || "s1";
const cycles = Number(params.get("cycles") || ({ s1: 1, "s2-reuse": 50, "s2-fresh": 50, s3: 20 }[scenario] || 1));
const soakMinutes = Number(params.get("soakMinutes") || 30);
const soakIntervalMs = Number(params.get("soakIntervalMs") || 60000);
const closeTimeoutMs = Number(params.get("closeTimeoutMs") || 180000);
const sampleDwellMs = Number(params.get("sampleDwellMs") || 1100);
const s5Variant = params.get("s5Variant") || "reader";

const metrics = {
  schemaVersion: 1,
  release: "R7-D",
  scenario,
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  artifact: null,
  manifestHash: null,
  fixture: null,
  workers: { created: 0, terminated: 0, crashes: 0, active: 0 },
  handles: { opened: 0, closed: 0, active: 0 },
  tiles: { activeBytes: 0, peakBytes: 0, rendered: 0, lateDraws: 0 },
  lifecycle: [],
  crashes: [],
  browserMemory: {
    jsHeap: globalThis.performance?.memory ? "available" : "unavailable",
    wasmHeap: "unavailable-public-sdk",
    tileCache: "host-observed",
  },
  sampleState: {
    token: 0, checkpoint: "loading", cycle: 0, block: 0,
    workersAfterClose: null, wasmHeapBytes: null, jsHeapBytes: null,
    tileCacheBytes: 0, documentVersion: null, revision: null,
  },
  output: null,
  knownDegradation: null,
  phase: "loading",
  complete: false,
  pass: false,
  error: null,
};
globalThis.__probe_metrics = metrics;
globalThis.__r7_longevity = metrics;

let outputBuffer = null;
let manifest = null;
let t1Bytes = null;
let t2Bytes = null;
let stressBytes = null;

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  $("#log").textContent += `[${performance.now().toFixed(1)} ms] ${text}\n`;
  $("#log").scrollTop = $("#log").scrollHeight;
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
    .map((value) => value.toString(16).padStart(2, "0")).join("");
}

function bufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
}

globalThis.__r7_longevity_get_output_base64 = () => outputBuffer ? bufferToBase64(outputBuffer) : null;

function checkpoint(name, cycle = metrics.sampleState.cycle, details = {}) {
  const block = cycle > 0 ? Math.ceil(cycle / 10) : 0;
  const jsHeapBytes = globalThis.performance?.memory?.usedJSHeapSize ?? null;
  metrics.sampleState = {
    token: metrics.sampleState.token + 1,
    checkpoint: name,
    cycle,
    block,
    workersAfterClose: details.workersAfterClose ?? null,
    wasmHeapBytes: null,
    jsHeapBytes,
    tileCacheBytes: metrics.tiles.activeBytes,
    documentVersion: details.documentVersion ?? metrics.fixture?.sha256 ?? null,
    revision: details.revision ?? null,
    activeWorkers: metrics.workers.active,
    activeHandles: metrics.handles.active,
    atMs: performance.now(),
  };
  $("#cycle").textContent = String(cycle);
  $("#checkpoint").textContent = name;
  $("#workers").textContent = String(metrics.workers.active);
  $("#handles").textContent = String(metrics.handles.active);
}

async function sampleDwell() {
  if (sampleDwellMs > 0)
    await new Promise((resolve) => setTimeout(resolve, sampleDwellMs));
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

function makeEngine(label) {
  let currentControl = null;
  const promise = createDocumentEngine({
    workerUrl: "./profiles/writer-review-r6/sdk-worker.js",
    timeoutMs: 60000,
    workerFactory(url) {
      const worker = new Worker(url, { name: `r7-d-${scenario}-${label}-${metrics.workers.created + 1}` });
      metrics.workers.created += 1;
      metrics.workers.active += 1;
      let terminated = false;
      currentControl = {
        terminate() {
          if (terminated)
            return;
          terminated = true;
          metrics.workers.terminated += 1;
          metrics.workers.active -= 1;
          worker.terminate();
        },
        crash(barrier) {
          metrics.workers.crashes += 1;
          worker.dispatchEvent(new ErrorEvent("error", {
            message: `intentional R7-D ${barrier} crash`,
          }));
          this.terminate();
        },
      };
      return {
        addEventListener: (...args) => worker.addEventListener(...args),
        postMessage: (...args) => worker.postMessage(...args),
        terminate: () => currentControl.terminate(),
      };
    },
  });
  return promise.then((engine) => {
    if (!metrics.artifact) {
      metrics.artifact = {
        profile: engine.manifest.profile,
        sdkVersion: engine.manifest.sdkVersion,
        coreCommit: engine.manifest.coreCommit,
        loader: engine.manifest.artifactFiles?.["probe.js"],
        wasm: engine.manifest.artifactFiles?.["probe.wasm"],
      };
    }
    return { engine, crash: (barrier) => currentControl.crash(barrier) };
  });
}

async function open(engine, bytes, name) {
  const started = performance.now();
  const documentHandle = await engine.open(bytes.slice(0), {
    name, transfer: true, timeoutMs: 180000,
  });
  metrics.handles.opened += 1;
  metrics.handles.active += 1;
  return { documentHandle, ms: performance.now() - started };
}

async function close(documentHandle, timeoutMs = closeTimeoutMs) {
  const started = performance.now();
  await documentHandle.close({ timeoutMs });
  metrics.handles.closed += 1;
  metrics.handles.active -= 1;
  return performance.now() - started;
}

async function renderTile(documentHandle, yRatio = 0, scale = 1) {
  const widthTwips = Math.min(7680, documentHandle.widthTwips);
  const heightTwips = Math.min(7680, documentHandle.heightTwips);
  const yTwips = Math.max(0, Math.min(
    documentHandle.heightTwips - heightTwips,
    Math.round((documentHandle.heightTwips - heightTwips) * yRatio),
  ));
  const started = performance.now();
  const tile = await documentHandle.render({
    xTwips: 0, yTwips, widthTwips, heightTwips,
    canvasWidthPx: Math.round(256 * scale),
    canvasHeightPx: Math.round(256 * scale),
  }, { timeoutMs: 180000 });
  metrics.tiles.rendered += 1;
  metrics.tiles.activeBytes = tile.pixels.byteLength;
  metrics.tiles.peakBytes = Math.max(metrics.tiles.peakBytes, metrics.tiles.activeBytes);
  const result = {
    yRatio, scale, yTwips, bytes: tile.pixels.byteLength,
    sha256: await sha256(tile.pixels), revision: tile.revision,
    ms: performance.now() - started,
  };
  metrics.tiles.activeBytes = 0;
  return result;
}

async function queuedCancel(documentHandle) {
  const region = {
    xTwips: 0, yTwips: 0,
    widthTwips: Math.min(7680, documentHandle.widthTwips),
    heightTwips: Math.min(7680, documentHandle.heightTwips),
    canvasWidthPx: 512, canvasHeightPx: 512,
  };
  const controller = new AbortController();
  const completionOrder = [];
  const first = documentHandle.render(region, { timeoutMs: 180000 })
    .then(() => completionOrder.push("first"));
  const cancelled = documentHandle.render(region, { signal: controller.signal, timeoutMs: 180000 })
    .then(() => ({ code: "UNEXPECTED_SUCCESS" }))
    .catch((error) => ({ code: error.code, isAbortError: error instanceof SdkAbortError }));
  const third = documentHandle.render(region, { timeoutMs: 180000 })
    .then(() => completionOrder.push("third"));
  controller.abort();
  const cancelResult = await cancelled;
  await Promise.all([first, third]);
  return { completionOrder, cancelResult, pass: cancelResult.code === "ABORTED" };
}

async function runS1() {
  const item = { run: 1, tiles: [], searches: [], pass: false };
  const holder = await makeEngine("s1");
  let documentHandle = null;
  try {
    checkpoint("opening", 1);
    const opened = await open(holder.engine, stressBytes, "l4-stress-100.odt");
    documentHandle = opened.documentHandle;
    item.openMs = opened.ms;
    checkpoint("rendering", 1, { revision: documentHandle.revision });
    for (const [ratio, scale] of [[0, 1], [0.5, 1], [1, 1], [0.5, 1.5]])
      item.tiles.push(await renderTile(documentHandle, ratio, scale));
    item.generationCancel = await queuedCancel(documentHandle);
    for (const text of metrics.fixture.anchors) {
      const result = await documentHandle.search(text, { timeoutMs: 60000 });
      item.searches.push({ text, found: result.found, revision: result.revision });
    }
    outputBuffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
    metrics.output = { bytes: outputBuffer.byteLength, sha256: await sha256(outputBuffer) };
    item.closeMs = await close(documentHandle);
    documentHandle = null;
    holder.engine.dispose();
    checkpoint("post-close", 1, { workersAfterClose: metrics.workers.active });
    await sampleDwell();
    item.pass = item.tiles.length === 4 && item.searches.every((entry) => entry.found)
      && item.generationCancel.pass && metrics.output.bytes > 0
      && metrics.workers.active === 0 && metrics.handles.active === 0;
  } finally {
    if (documentHandle)
      metrics.handles.active = Math.max(0, metrics.handles.active - 1);
    holder.engine.dispose();
  }
  metrics.lifecycle.push(item);
  return item.pass;
}

async function lifecycleCycle(engine, cycle, bytes, expectedReusableWorkers, emitCheckpoint) {
  const item = { cycle, pass: false };
  let documentHandle = null;
  try {
    checkpoint("opening", cycle);
    const opened = await open(engine, bytes, "r7-lifecycle.odt");
    documentHandle = opened.documentHandle;
    item.openMs = opened.ms;
    item.tile = await renderTile(documentHandle, cycle % 3 / 2, cycle % 2 ? 1 : 1.5);
    item.closeMs = await close(documentHandle);
    documentHandle = null;
    item.pass = metrics.handles.active === 0;
  } catch (error) {
    item.error = serializeError(error);
  }
  if (emitCheckpoint) {
    checkpoint("post-close", cycle, {
      workersAfterClose: Math.max(0, metrics.workers.active - expectedReusableWorkers),
    });
    await sampleDwell();
  }
  metrics.lifecycle.push(item);
  return item.pass;
}

async function runS2(reuse) {
  let reusable = null;
  try {
    if (reuse)
      reusable = await makeEngine("reuse");
    for (let cycle = 1; cycle <= cycles; cycle += 1) {
      const holder = reusable || await makeEngine(`fresh-${cycle}`);
      const passed = await lifecycleCycle(holder.engine, cycle, t1Bytes, reuse ? 1 : 0, reuse);
      if (!reuse)
        holder.engine.dispose();
      if (!reuse) {
        checkpoint("post-close", cycle, { workersAfterClose: metrics.workers.active });
        await sampleDwell();
      }
      if (!passed)
        break;
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
  } finally {
    reusable?.engine.dispose();
  }
  checkpoint("finished", metrics.lifecycle.length, { workersAfterClose: metrics.workers.active });
  return metrics.lifecycle.length === cycles && metrics.lifecycle.every((item) => item.pass)
    && metrics.workers.active === 0 && metrics.handles.active === 0;
}

async function runCrashCycle(cycle) {
  const barrier = ["open", "render-queue", "local-unsaved", "saved-local-bytes"][(cycle - 1) % 4];
  const marker = `R7-D-crash-${cycle}-must-not-replay`;
  const item = {
    cycle, barrier, crashEvent: false, staleRejected: false,
    markerReplayed: null, savedBytesAvailable: false, pass: false,
  };
  const holder = await makeEngine(`crash-${cycle}`);
  let stale = null;
  try {
    checkpoint(`crash-${barrier}`, cycle);
    stale = (await open(holder.engine, t1Bytes, `crash-${cycle}.odt`)).documentHandle;
    if (barrier === "render-queue") {
      const pending = [0, 0.5, 1].map((ratio) => renderTile(stale, ratio, 1)
        .then(() => ({ status: "fulfilled" }), (error) => ({ status: "rejected", error: serializeError(error) })));
      holder.crash(barrier);
      item.pending = await Promise.all(pending);
    } else {
      if (barrier === "local-unsaved" || barrier === "saved-local-bytes") {
        await stale.search("Final line：ODT round-trip 完整性檢查。", { timeoutMs: 60000 });
        await stale.replaceSelection(marker, { expectedRevision: stale.revision, timeoutMs: 60000 });
        if (barrier === "saved-local-bytes") {
          const saved = await stale.save({ format: "odt" }, { timeoutMs: 180000 });
          item.savedBytesAvailable = saved.byteLength > 0;
          item.savedSha256 = await sha256(saved);
        }
      }
      holder.crash(barrier);
    }
    metrics.handles.active = Math.max(0, metrics.handles.active - 1);
    await new Promise((resolve) => setTimeout(resolve, 20));
    item.crashEvent = true;
    await holder.engine.restart();
    try {
      await stale.render({ canvasWidthPx: 8, canvasHeightPx: 8 });
    } catch (error) {
      item.staleRejected = error.code === "STALE_DOCUMENT";
      item.staleError = serializeError(error);
    }
    const recovered = (await open(holder.engine, t1Bytes, `recovered-${cycle}.odt`)).documentHandle;
    const replay = await recovered.search(marker, { timeoutMs: 60000 });
    item.markerReplayed = replay.found;
    item.recoveredTile = await renderTile(recovered, 0, 1);
    item.closeMs = await close(recovered);
    holder.engine.dispose();
    checkpoint("post-close", cycle, { workersAfterClose: metrics.workers.active });
    await sampleDwell();
    item.pass = item.crashEvent && item.staleRejected && !item.markerReplayed
      && (barrier === "saved-local-bytes" ? item.savedBytesAvailable : !item.savedBytesAvailable)
      && metrics.workers.active === 0 && metrics.handles.active === 0;
  } catch (error) {
    item.error = serializeError(error);
  } finally {
    holder.engine.dispose();
  }
  metrics.crashes.push(item);
  return item.pass;
}

async function runS3() {
  for (let cycle = 1; cycle <= cycles; cycle += 1)
    if (!await runCrashCycle(cycle))
      break;
  return metrics.crashes.length === cycles && metrics.crashes.every((item) => item.pass);
}

async function runS4() {
  const holder = await makeEngine("soak");
  let documentHandle = null;
  const crashAt = new Set([
    Math.max(1, Math.floor(soakMinutes / 3)),
    Math.max(1, Math.floor(soakMinutes * 2 / 3)),
    Math.max(1, Math.floor(soakMinutes)),
  ]);
  const started = performance.now();
  try {
    documentHandle = (await open(holder.engine, stressBytes, "l4-soak.odt")).documentHandle;
    for (let minute = 1; minute <= soakMinutes; minute += 1) {
      const item = { cycle: minute, pass: false };
      const operationStarted = performance.now();
      try {
        item.tile = await renderTile(documentHandle, (minute % 10) / 9, minute % 2 ? 1 : 1.5);
        const anchor = metrics.fixture.anchors[(minute - 1) % metrics.fixture.anchors.length];
        item.search = await documentHandle.search(anchor, { timeoutMs: 60000 });
        if (crashAt.has(minute)) {
          holder.crash(`soak-minute-${minute}`);
          metrics.handles.active = Math.max(0, metrics.handles.active - 1);
          await holder.engine.restart();
          documentHandle = (await open(holder.engine, stressBytes, `l4-soak-${minute}.odt`)).documentHandle;
          item.crashRestart = true;
        }
        item.ms = performance.now() - operationStarted;
        item.pass = item.search.found;
      } catch (error) {
        item.error = serializeError(error);
      }
      metrics.lifecycle.push(item);
      checkpoint("soak-minute-complete", minute, { revision: documentHandle?.revision ?? null });
      if (!item.pass)
        break;
      const target = started + minute * soakIntervalMs;
      const waitMs = Math.max(0, target - performance.now());
      if (waitMs)
        await new Promise((resolve) => setTimeout(resolve, waitMs));
    }
    await close(documentHandle);
    documentHandle = null;
    holder.engine.dispose();
    checkpoint("post-close", metrics.lifecycle.length, { workersAfterClose: metrics.workers.active });
    await sampleDwell();
  } finally {
    holder.engine.dispose();
  }
  return metrics.lifecycle.length === soakMinutes && metrics.lifecycle.every((item) => item.pass)
    && metrics.workers.crashes === crashAt.size
    && metrics.workers.active === 0 && metrics.handles.active === 0;
}

async function renderDiscovery(documentHandle) {
  const width = documentHandle.widthTwips;
  const height = documentHandle.heightTwips;
  const regionWidth = Math.min(7680, width);
  const regionHeight = Math.min(7680, height);
  const regions = [
    { xTwips: 0, yTwips: 0 },
    { xTwips: 0, yTwips: Math.max(0, Math.min(height - regionHeight, regionHeight)) },
    {
      xTwips: Math.max(0, width - Math.max(1, Math.floor(regionWidth / 2))),
      yTwips: Math.max(0, height - Math.max(1, Math.floor(regionHeight / 2))),
    },
  ];
  const results = [];
  for (const region of regions) {
    const tile = await documentHandle.render({
      ...region, widthTwips: regionWidth, heightTwips: regionHeight,
      canvasWidthPx: 256, canvasHeightPx: 256,
    }, { timeoutMs: 180000 });
    results.push({ ...region, bytes: tile.pixels.byteLength, sha256: await sha256(tile.pixels) });
  }
  return results;
}

async function runS5(known) {
  const holder = await makeEngine(known ? "finding012-known" : "finding012-normal");
  const item = {
    kind: known ? "known-discovery" : "normal-reader",
    variant: known ? "discovery" : s5Variant,
    stage: "open", pass: false,
  };
  let documentHandle = null;
  try {
    const opened = await open(holder.engine, t2Bytes, "t2-styled.odt");
    documentHandle = opened.documentHandle;
    item.openMs = opened.ms;
    item.stage = "render";
    if (known) {
      item.tiles = await renderDiscovery(documentHandle);
      item.queueAbort = await queuedCancel(documentHandle);
      item.stage = "search";
      item.search = await documentHandle.search("RGBA tile", { timeoutMs: 60000 });
    } else {
      if (["reader", "render", "semantic"].includes(s5Variant))
        item.tile = await renderTile(documentHandle, 0, 1);
      if (["comments", "semantic"].includes(s5Variant))
        item.comments = await documentHandle.listComments({ timeoutMs: 60000 });
      if (["reader", "search", "semantic"].includes(s5Variant))
        item.search = await documentHandle.search(
          "文件結尾：請確認表格、圖片、註解與標題樣式均保留。", { timeoutMs: 60000 },
        );
    }
    item.stage = "close";
    try {
      item.closeMs = await close(documentHandle, closeTimeoutMs);
      documentHandle = null;
      item.close = { status: "passed" };
    } catch (error) {
      item.close = { status: "typed-failure", error: serializeError(error) };
      metrics.handles.active = Math.max(0, metrics.handles.active - 1);
      documentHandle = null;
    }
    item.stage = "complete";
    holder.engine.dispose();
    checkpoint("post-close", 1, { workersAfterClose: metrics.workers.active });
    await sampleDwell();
    if (known && item.close.status !== "passed") {
      metrics.knownDegradation = {
        finding: "012", sequence: "known-discovery", close: item.close,
        forcedWorkerTermination: true,
      };
    }
    const searchPass = ["reader", "search", "semantic"].includes(s5Variant)
      ? item.search?.found === true : true;
    item.pass = searchPass
      && (!known ? item.close.status === "passed" : true)
      && metrics.workers.active === 0 && metrics.handles.active === 0;
  } catch (error) {
    item.error = serializeError(error);
  } finally {
    holder.engine.dispose();
  }
  metrics.lifecycle.push(item);
  return item.pass;
}

async function load() {
  manifest = await fetchJson("./r7-compat-fixtures/manifest.json");
  metrics.manifestHash = await sha256(new TextEncoder().encode(JSON.stringify(manifest)));
  const byId = Object.fromEntries(manifest.documents.map((item) => [item.id, item]));
  const stress = byId["l4-stress-100"];
  metrics.fixture = {
    id: stress.id, sha256: stress.sha256, bytes: stress.bytes,
    pageCount: stress.expected.pageCount,
    anchors: stress.anchors.map((item) => item.text),
  };
  [t1Bytes, t2Bytes, stressBytes] = await Promise.all([
    fetchBytes(`./r7-compat-fixtures/${byId["l0-t1"].path}`),
    fetchBytes(`./r7-compat-fixtures/${byId["l0-t2"].path}`),
    fetchBytes(`./r7-compat-fixtures/${stress.path}`),
  ]);
}

async function main() {
  $("#scenario").textContent = scenario;
  try {
    await load();
    metrics.phase = scenario;
    checkpoint("ready", 0);
    let pass = false;
    if (scenario === "s1")
      pass = await runS1();
    else if (scenario === "s2-reuse")
      pass = await runS2(true);
    else if (scenario === "s2-fresh")
      pass = await runS2(false);
    else if (scenario === "s3")
      pass = await runS3();
    else if (scenario === "s4")
      pass = await runS4();
    else if (scenario === "s5-normal")
      pass = await runS5(false);
    else if (scenario === "s5-known")
      pass = await runS5(true);
    else
      throw new Error(`unknown scenario: ${scenario}`);
    metrics.pass = metrics.crossOriginIsolated && metrics.artifact?.profile === "writer-review" && pass;
    metrics.phase = "complete";
    metrics.complete = true;
    checkpoint("complete", metrics.sampleState.cycle, { workersAfterClose: metrics.workers.active });
    $("#status").textContent = metrics.pass ? "pass" : "failed";
    $("#decision").textContent = metrics.pass ? "PASS" : "STOP";
    log({ scenario, pass: metrics.pass, workers: metrics.workers, handles: metrics.handles });
  } catch (error) {
    metrics.error = serializeError(error);
    metrics.phase = "error";
    metrics.complete = true;
    $("#status").textContent = `${metrics.error.code}: ${metrics.error.message}`;
    $("#decision").textContent = "STOP";
    log(metrics.error);
  }
}

main();
