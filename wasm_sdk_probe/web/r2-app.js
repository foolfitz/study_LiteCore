import {
  createDocumentEngine,
  SdkAbortError,
  SdkTimeoutError,
  StaleDocumentError,
  WorkerCrashedError,
} from "./document-sdk.js";

const $ = (id) => document.getElementById(id);
const elements = {
  file: $("file"),
  canvas: $("canvas"),
  log: $("log"),
  status: $("status"),
  download: $("download"),
};

const metrics = {
  schema_version: 2,
  protocol_version: 1,
  page_load_epoch_ms: performance.timeOrigin,
  user_agent: navigator.userAgent,
  cross_origin_isolated: globalThis.crossOriginIsolated,
  t_ready_ms: null,
  isolation: null,
  manifest: null,
  runs: [],
  memory: [],
  lifecycle: [],
  conformance: [],
};
globalThis.__r2_metrics = metrics;
globalThis.__probe_metrics = metrics;

let engine = null;
let initializationPromise = null;
let outputBuffer = null;
let outputObjectUrl = null;

function setStatus(value) {
  elements.status.textContent = value;
}

function appendLog(value) {
  const timestamp = performance.now().toFixed(1).padStart(9);
  const text = typeof value === "string" ? value : JSON.stringify(value);
  elements.log.textContent += `[${timestamp} ms] ${text}\n`;
  elements.log.scrollTop = elements.log.scrollHeight;
}

function requireFile() {
  const [file] = elements.file.files;
  if (!file)
    throw new Error("請先選擇一份 ODT 文件");
  return file;
}

function drawTile(tile) {
  const expected = tile.width * tile.height * 4;
  if (!(tile.pixels instanceof ArrayBuffer) || tile.pixels.byteLength !== expected)
    throw new Error(`invalid tile buffer: expected ${expected}, got ${tile.pixels?.byteLength}`);
  elements.canvas.width = tile.width;
  elements.canvas.height = tile.height;
  const pixels = new Uint8ClampedArray(tile.pixels);
  elements.canvas.getContext("2d").putImageData(
    new ImageData(pixels, tile.width, tile.height), 0, 0,
  );
}

function publishOutput(buffer) {
  outputBuffer = buffer;
  const blob = new Blob([buffer], { type: "application/vnd.oasis.opendocument.text" });
  if (outputObjectUrl)
    URL.revokeObjectURL(outputObjectUrl);
  outputObjectUrl = URL.createObjectURL(blob);
  elements.download.disabled = false;
}

globalThis.__probe_get_output_base64 = () => {
  if (!outputBuffer)
    throw new Error("R2 output is not ready");
  const bytes = new Uint8Array(outputBuffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  return btoa(binary);
};

async function measureMemory(phase, runIndex) {
  if (new URLSearchParams(location.search).get("memory") === "skip") {
    metrics.memory.push({
      phase,
      run_index: runIndex,
      browser: navigator.userAgent,
      bytes: null,
      method: "skipped by memory=skip (functional run)",
    });
    return;
  }
  if (typeof performance.measureUserAgentSpecificMemory !== "function") {
    metrics.memory.push({
      phase,
      run_index: runIndex,
      browser: navigator.userAgent,
      bytes: null,
      method: "measureUserAgentSpecificMemory unavailable",
    });
    return;
  }
  try {
    const value = await performance.measureUserAgentSpecificMemory();
    metrics.memory.push({
      phase,
      run_index: runIndex,
      browser: navigator.userAgent,
      bytes: value.bytes,
      method: "performance.measureUserAgentSpecificMemory",
    });
  } catch (error) {
    metrics.memory.push({
      phase,
      run_index: runIndex,
      browser: navigator.userAgent,
      bytes: null,
      method: `measureUserAgentSpecificMemory failed: ${error}`,
    });
  }
}

async function runAll() {
  await initializationPromise;
  const file = requireFile();
  const run = {
    browser: navigator.userAgent,
    doc: file.name,
    cache: new URLSearchParams(location.search).get("cache") || "unspecified",
    t_ready_ms: metrics.t_ready_ms,
    t_open_ms: null,
    t_first_tile_ms: null,
    t_insert_ms: null,
    t_save_ms: null,
    insert_method: null,
    input_transferred: false,
    main_thread_isolated: false,
    pass: false,
  };
  const runIndex = metrics.runs.length;
  metrics.runs.push(run);

  setStatus("run all: preparing");
  const input = await file.arrayBuffer();
  await measureMemory("before-open", runIndex);

  setStatus("run all: opening");
  let startedAt = performance.now();
  const documentHandle = await engine.open(input, {
    name: file.name,
    transfer: true,
    timeoutMs: 180000,
  });
  run.t_open_ms = performance.now() - startedAt;
  run.input_transferred = input.byteLength === 0;
  await measureMemory("after-open", runIndex);

  setStatus("run all: painting");
  startedAt = performance.now();
  let tile = await documentHandle.render();
  run.t_first_tile_ms = performance.now() - startedAt;
  drawTile(tile);
  await measureMemory("after-paint", runIndex);

  setStatus("run all: clicking");
  await documentHandle.click(1700, 1700);

  setStatus("run all: inserting");
  startedAt = performance.now();
  const insert = await documentHandle.insertText("測");
  run.t_insert_ms = performance.now() - startedAt;
  run.insert_method = insert.method;

  setStatus("run all: repainting");
  tile = await documentHandle.render();
  drawTile(tile);

  setStatus("run all: saving");
  startedAt = performance.now();
  const output = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
  run.t_save_ms = performance.now() - startedAt;
  publishOutput(output);
  await measureMemory("after-save", runIndex);

  await documentHandle.close();
  run.main_thread_isolated = metrics.isolation?.pass === true;
  run.pass = run.input_transferred && run.main_thread_isolated
             && insert.method === "paste" && output.byteLength > 0;
  if (!run.pass)
    throw new Error(`R2 run invariants failed: ${JSON.stringify(run)}`);
  setStatus("run all: complete");
  appendLog({ type: "metrics", run });
}

async function runLifecycle() {
  await initializationPromise;
  const file = requireFile();
  const documentHandle = await engine.open(await file.arrayBuffer(), {
    name: file.name,
    transfer: false,
    timeoutMs: 180000,
  });
  const generationBefore = engine.manifest;
  await engine.restart();
  let staleRejected = false;
  try {
    await documentHandle.render();
  } catch (error) {
    staleRejected = error instanceof StaleDocumentError && error.code === "STALE_DOCUMENT";
  }
  if (!staleRejected)
    throw new Error("old document handle remained usable after Worker restart");

  const reopened = await engine.open(await file.arrayBuffer(), {
    name: file.name,
    transfer: false,
    timeoutMs: 180000,
  });
  await reopened.close();
  const result = {
    pass: true,
    stale_handle_rejected: staleRejected,
    abi_before: generationBefore.abiVersion,
    abi_after: engine.manifest.abiVersion,
  };
  metrics.lifecycle.push(result);
  setStatus("lifecycle: complete");
  appendLog({ type: "lifecycle", result });
  return result;
}

function waitForSdkEvent(predicate, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      unsubscribe();
      reject(new Error("timed out waiting for SDK event"));
    }, timeoutMs);
    const unsubscribe = engine.onEvent((event) => {
      if (!predicate(event))
        return;
      clearTimeout(timer);
      unsubscribe();
      resolve(event);
    });
  });
}

function rawWorkerRequest(worker, request, transfer = []) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new Error(`${request.operation} boundary test timed out`)),
      120000,
    );
    const onMessage = (event) => {
      if (event.data?.kind !== "response" || event.data.requestId !== request.requestId)
        return;
      clearTimeout(timer);
      worker.removeEventListener("message", onMessage);
      resolve(event.data);
    };
    worker.addEventListener("message", onMessage);
    worker.addEventListener("error", (event) => {
      clearTimeout(timer);
      reject(new Error(event.message || "boundary test worker crashed"));
    }, { once: true });
    worker.postMessage(request, transfer);
  });
}

async function testInitRejection(requestId, requestedAbiVersion, expectedCode) {
  const worker = new Worker("./sdk-worker.js", { name: "oxoffice-init-boundary-test" });
  try {
    const response = await rawWorkerRequest(worker, {
      protocolVersion: 1,
      kind: "request",
      requestId,
      operation: "init",
      payload: { requestedAbiVersion, debug: false },
    });
    return response.ok === false && response.error?.code === expectedCode;
  } finally {
    worker.terminate();
  }
}

async function testInvalidArgument() {
  const worker = new Worker("./sdk-worker.js", { name: "oxoffice-argument-boundary-test" });
  try {
    const initialized = await rawWorkerRequest(worker, {
      protocolVersion: 1,
      kind: "request",
      requestId: 0x70000002,
      operation: "init",
      payload: { requestedAbiVersion: 0x00010000, debug: false },
    });
    const input = new Uint8Array([0x50]).buffer;
    const response = await rawWorkerRequest(worker, {
      protocolVersion: 1,
      kind: "request",
      requestId: 0x70000003,
      operation: "open",
      payload: { buffer: input, name: "input.txt" },
    }, [input]);
    return initialized.ok === true
           && response.ok === false && response.error?.code === "INVALID_ARGUMENT";
  } finally {
    worker.terminate();
  }
}

async function testWorkerCrashRecovery(file) {
  const crashWorkerSource = `
    "use strict";
    self.addEventListener("message", (event) => {
      const request = event.data;
      if (request?.kind !== "request")
        return;
      const respond = (result) => self.postMessage({
        protocolVersion: 1,
        kind: "response",
        requestId: request.requestId,
        ok: true,
        result,
      });
      if (request.operation === "init") {
        respond({
          sdkVersion: "0.2.0-r2-crash-fixture",
          protocolVersion: 1,
          abiVersion: 65536,
          abiVersionText: "1.0",
          coreCommit: "crash-fixture",
          profile: "browser-crash-fixture",
          capabilities: [],
          capabilityBits: 0,
        });
      } else if (request.operation === "open") {
        respond({
          documentHandle: 9001,
          revision: 0,
          parts: 1,
          width: 7680,
          height: 7680,
          tileMode: 0,
        });
      } else if (request.operation === "paint") {
        throw new Error("intentional R2 browser worker crash");
      }
    });
  `;
  const crashWorkerUrl = URL.createObjectURL(
    new Blob([crashWorkerSource], { type: "text/javascript" }),
  );
  let workerCount = 0;
  let crashEngine = null;
  try {
    crashEngine = await createDocumentEngine({
      workerUrl: "./sdk-worker.js",
      timeoutMs: 30000,
      workerFactory: (url) => {
        workerCount += 1;
        return workerCount === 1
          ? new Worker(crashWorkerUrl, { name: "oxoffice-crash-fixture" })
          : new Worker(url, { name: "oxoffice-crash-recovery" });
      },
    });
    let crashEventSeen = false;
    const unsubscribe = crashEngine.onEvent((event) => {
      if (event.event === "worker-crashed")
        crashEventSeen = true;
    });
    const oldDocument = await crashEngine.open(new ArrayBuffer(8));
    let crashRejected = false;
    try {
      await oldDocument.render({}, { timeoutMs: 30000 });
    } catch (error) {
      crashRejected = error instanceof WorkerCrashedError
                      && error.code === "WORKER_CRASHED";
    }
    unsubscribe();

    await crashEngine.restart();
    let staleAfterRecovery = false;
    try {
      await oldDocument.render();
    } catch (error) {
      staleAfterRecovery = error instanceof StaleDocumentError;
    }
    const recovered = await crashEngine.open(await file.arrayBuffer(), {
      name: file.name,
      transfer: false,
      timeoutMs: 180000,
    });
    const tile = await recovered.render({
      canvasWidthPx: 64,
      canvasHeightPx: 64,
    });
    await recovered.close();
    return crashRejected && crashEventSeen && staleAfterRecovery
           && workerCount === 2 && tile.pixels.byteLength === 64 * 64 * 4;
  } finally {
    crashEngine?.dispose();
    URL.revokeObjectURL(crashWorkerUrl);
  }
}

async function runConformance() {
  await initializationPromise;
  const file = requireFile();

  const preservedInput = await file.arrayBuffer();
  const preservedByteLength = preservedInput.byteLength;
  const staleDocument = await engine.open(preservedInput, {
    name: file.name,
    transfer: false,
    timeoutMs: 180000,
  });
  const copiedInputPreserved = preservedInput.byteLength === preservedByteLength;
  await engine.restart();
  let staleHandleRejected = false;
  try {
    await staleDocument.render();
  } catch (error) {
    staleHandleRejected = error instanceof StaleDocumentError;
  }

  const transferredInput = await file.arrayBuffer();
  const documentHandle = await engine.open(transferredInput, {
    name: file.name,
    transfer: true,
    timeoutMs: 180000,
  });
  const transferredInputConsumed = transferredInput.byteLength === 0;
  const cancelResult = waitForSdkEvent(
    (event) => event.event === "cancel-result" && event.status === "OK",
  );
  const blocker = documentHandle.render({
    canvasWidthPx: 2048,
    canvasHeightPx: 2048,
  }, { timeoutMs: 180000 });
  const controller = new AbortController();
  const queued = documentHandle.render({}, {
    signal: controller.signal,
    timeoutMs: 180000,
  });
  controller.abort();
  let abortRejected = false;
  try {
    await queued;
  } catch (error) {
    abortRejected = error instanceof SdkAbortError && error.code === "ABORTED";
  }
  const [largeTile, cancelEvent] = await Promise.all([blocker, cancelResult]);
  const queuedCancelPassed = abortRejected && cancelEvent.status === "OK"
                             && largeTile.pixels.byteLength === 2048 * 2048 * 4;

  const timeoutCancelResult = waitForSdkEvent(
    (event) => event.event === "cancel-result" && event.status === "OK",
  );
  const timeoutBlocker = documentHandle.render({
    canvasWidthPx: 2048,
    canvasHeightPx: 2048,
  }, { timeoutMs: 180000 });
  const timedRequest = documentHandle.render({}, { timeoutMs: 1 });
  let timeoutRejected = false;
  try {
    await timedRequest;
  } catch (error) {
    timeoutRejected = error instanceof SdkTimeoutError && error.code === "TIMEOUT";
  }
  const [timeoutTile, timeoutCancelEvent] = await Promise.all([
    timeoutBlocker,
    timeoutCancelResult,
  ]);
  const timeoutCancelPassed = timeoutRejected && timeoutCancelEvent.status === "OK"
                              && timeoutTile.pixels.byteLength === 2048 * 2048 * 4;

  const savedOutput = await documentHandle.save(
    { format: "odt" },
    { timeoutMs: 180000 },
  );
  const outputOwnershipPassed = savedOutput instanceof ArrayBuffer
                                && savedOutput.byteLength > 0;

  const oldHandle = documentHandle.handle;
  await documentHandle.close();
  const current = await engine.open(await file.arrayBuffer(), {
    name: file.name,
    transfer: false,
    timeoutMs: 180000,
  });
  let invalidHandleRejected = false;
  let doubleCloseRejected = false;
  try {
    await engine._request("paint", {
      documentHandle: oldHandle,
      xTwips: 0,
      yTwips: 0,
      widthTwips: 7680,
      heightTwips: 7680,
      canvasWidthPx: 16,
      canvasHeightPx: 16,
    });
  } catch (error) {
    invalidHandleRejected = error.code === "INVALID_HANDLE";
  }
  try {
    await engine._request("close", { documentHandle: oldHandle });
  } catch (error) {
    doubleCloseRejected = error.code === "INVALID_HANDLE";
  }
  await current.close();

  let soakPassed = true;
  let lastHandle = current.handle;
  const soakIterations = 10;
  for (let iteration = 0; iteration < soakIterations; iteration += 1) {
    const soakInput = await file.arrayBuffer();
    const soakDocument = await engine.open(soakInput, {
      name: file.name,
      transfer: true,
      timeoutMs: 180000,
    });
    const soakTile = await soakDocument.render({
      canvasWidthPx: 64,
      canvasHeightPx: 64,
    });
    soakPassed = soakPassed && soakInput.byteLength === 0
                 && soakDocument.handle > lastHandle
                 && soakTile.pixels.byteLength === 64 * 64 * 4;
    lastHandle = soakDocument.handle;
    await soakDocument.close();
  }

  engine.dispose();
  const abiMismatchRejected = await testInitRejection(
    0x70000001, 0x00020000, "INCOMPATIBLE_ABI",
  );
  const zeroRequestIdRejected = await testInitRejection(
    0, 0x00010000, "INVALID_ARGUMENT",
  );
  const invalidArgumentRejected = await testInvalidArgument();
  const workerCrashRecovery = await testWorkerCrashRecovery(file);

  const result = {
    pass: staleHandleRejected && queuedCancelPassed && invalidHandleRejected
          && doubleCloseRejected && abiMismatchRejected
          && zeroRequestIdRejected && invalidArgumentRejected
          && copiedInputPreserved && transferredInputConsumed
          && outputOwnershipPassed && timeoutCancelPassed
          && soakPassed && workerCrashRecovery,
    stale_handle_rejected: staleHandleRejected,
    queued_cancel: queuedCancelPassed,
    timeout_cancel: timeoutCancelPassed,
    invalid_handle_rejected: invalidHandleRejected,
    double_close_rejected: doubleCloseRejected,
    abi_mismatch_rejected: abiMismatchRejected,
    zero_request_id_rejected: zeroRequestIdRejected,
    invalid_argument_rejected: invalidArgumentRejected,
    copied_input_preserved: copiedInputPreserved,
    transferred_input_consumed: transferredInputConsumed,
    output_ownership: outputOwnershipPassed,
    soak_open_render_close_iterations: soakIterations,
    soak_open_render_close: soakPassed,
    worker_crash_recovery: workerCrashRecovery,
  };
  if (!result.pass)
    throw new Error(`R2 conformance failed: ${JSON.stringify(result)}`);
  metrics.conformance.push(result);
  setStatus("conformance: complete");
  appendLog({ type: "conformance", result });
  return result;
}

function guard(action) {
  return async () => {
    try {
      await action();
    } catch (error) {
      appendLog(`action failed: ${error.stack || error}`);
      setStatus("action failed");
    }
  };
}

async function initialize() {
  metrics.isolation = {
    createProbeModule: typeof globalThis.createProbeModule,
    FS: typeof globalThis.FS,
    HEAPU8: typeof globalThis.HEAPU8,
  };
  metrics.isolation.pass = metrics.isolation.createProbeModule === "undefined"
                           && metrics.isolation.FS === "undefined"
                           && metrics.isolation.HEAPU8 === "undefined";
  engine = await createDocumentEngine({
    workerUrl: "./sdk-worker.js",
    timeoutMs: 30000,
    debug: new URLSearchParams(location.search).get("debug") === "1",
  });
  engine.onEvent((event) => appendLog(event));
  metrics.manifest = engine.manifest;
  metrics.t_ready_ms = performance.now();
  setStatus("ready");
  appendLog({ type: "ready", manifest: engine.manifest, isolation: metrics.isolation });
}

globalThis.__r2_run_all = runAll;
globalThis.__r2_run_lifecycle = runLifecycle;
globalThis.__r2_run_conformance = runConformance;

$("run-all").addEventListener("click", guard(runAll));
$("run-lifecycle").addEventListener("click", guard(runLifecycle));
$("run-conformance").addEventListener("click", guard(runConformance));
elements.download.addEventListener("click", () => {
  if (!outputObjectUrl)
    return;
  const anchor = document.createElement("a");
  anchor.href = outputObjectUrl;
  anchor.download = "out.odt";
  anchor.click();
});
$("copy-metrics").addEventListener("click", guard(async () => {
  await navigator.clipboard.writeText(JSON.stringify(metrics, null, 2));
  setStatus("metrics copied");
}));

initializationPromise = initialize().catch((error) => {
  appendLog(`worker initialization failed: ${error.stack || error}`);
  setStatus("module initialization failed");
  throw error;
});
