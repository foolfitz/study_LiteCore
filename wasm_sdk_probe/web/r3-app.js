import {
  StaleRevisionError,
  createDocumentEngine,
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
  schema_version: 3,
  protocol_version: 1,
  page_load_epoch_ms: performance.timeOrigin,
  user_agent: navigator.userAgent,
  cross_origin_isolated: globalThis.crossOriginIsolated,
  t_ready_ms: null,
  isolation: null,
  manifest: null,
  runs: [],
  conformance: [],
  memory: [],
};
globalThis.__r3_metrics = metrics;
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
    throw new Error("請先選擇 t1-plain-zh.odt");
  return file;
}

function containsText(value, expected) {
  return JSON.stringify(value).includes(expected);
}

function drawTile(tile) {
  const expected = tile.width * tile.height * 4;
  if (!(tile.pixels instanceof ArrayBuffer) || tile.pixels.byteLength !== expected)
    throw new Error(`invalid tile buffer: expected ${expected}`);
  elements.canvas.width = tile.width;
  elements.canvas.height = tile.height;
  elements.canvas.getContext("2d").putImageData(
    new ImageData(new Uint8ClampedArray(tile.pixels), tile.width, tile.height), 0, 0,
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
    throw new Error("R3 output is not ready");
  const bytes = new Uint8Array(outputBuffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
};

function rawWorkerRequest(worker, request) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new Error(`ABI ${request.payload.requestedAbiVersion} timed out`)),
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
      reject(new Error(event.message || "ABI test worker crashed"));
    }, { once: true });
    worker.postMessage(request);
  });
}

async function testAbiRequest(requestId, requestedAbiVersion) {
  const worker = new Worker("./sdk-worker.js", { name: "oxoffice-r3-abi-test" });
  try {
    return await rawWorkerRequest(worker, {
      protocolVersion: 1,
      kind: "request",
      requestId,
      operation: "init",
      payload: { requestedAbiVersion, debug: false },
    });
  } finally {
    worker.terminate();
  }
}

async function runConformance() {
  await initializationPromise;
  const abi10 = await testAbiRequest(0x71000001, 0x00010000);
  const abi12 = await testAbiRequest(0x71000002, 0x00010002);
  const abi20 = await testAbiRequest(0x71000003, 0x00020000);
  const capabilities = new Set(engine.manifest.capabilities);
  const result = {
    abi_1_0_client_accepted: abi10.ok === true && abi10.result?.abiVersion === 0x00010001,
    abi_1_2_client_rejected: abi12.ok === false
                             && abi12.error?.code === "INCOMPATIBLE_ABI",
    abi_2_0_client_rejected: abi20.ok === false
                             && abi20.error?.code === "INCOMPATIBLE_ABI",
    semantic_capabilities: [
      "search", "selection-text", "replace-selection", "undo", "comments",
      "tracked-changes",
    ].every((capability) => capabilities.has(capability)),
    no_generic_uno_surface: typeof engine.postUnoCommand === "undefined",
  };
  result.pass = Object.values(result).every(Boolean);
  if (!result.pass)
    throw new Error(`R3 ABI conformance failed: ${JSON.stringify(result)}`);
  metrics.conformance.push(result);
  setStatus("R3 conformance: complete");
  appendLog({ type: "r3-conformance", result });
  return result;
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
    insert_method: "replace-selection",
    input_transferred: false,
    main_thread_isolated: false,
    search_selection: false,
    replace_undo: false,
    stale_revision_rejected: false,
    comment_added: false,
    comment_undo: false,
    comment_readded: false,
    comment_roundtrip: false,
    tracked_changes: false,
    final_revision: null,
    pass: false,
  };
  metrics.runs.push(run);

  setStatus("R3: opening");
  const input = await file.arrayBuffer();
  let startedAt = performance.now();
  const documentHandle = await engine.open(input, {
    name: file.name,
    transfer: true,
    timeoutMs: 180000,
  });
  run.t_open_ms = performance.now() - startedAt;
  run.input_transferred = input.byteLength === 0;

  setStatus("R3: search and selection");
  const firstMatch = await documentHandle.search("LibreOfficeKit", { timeoutMs: 30000 });
  const firstSelection = await documentHandle.getSelection();
  run.search_selection = firstMatch.found && firstSelection.text === "LibreOfficeKit";

  setStatus("R3: replace and stale guard");
  startedAt = performance.now();
  await documentHandle.replaceSelection("LOK-R3", {
    expectedRevision: firstSelection.revision,
  });
  run.t_insert_ms = performance.now() - startedAt;
  try {
    await documentHandle.replaceSelection("SHOULD-NOT-APPEAR", {
      expectedRevision: firstSelection.revision,
    });
  } catch (error) {
    run.stale_revision_rejected = error instanceof StaleRevisionError
                                  && error.code === "STALE_REVISION"
                                  && error.details?.expectedRevision === firstSelection.revision
                                  && error.details?.currentRevision === documentHandle.revision;
  }

  setStatus("R3: undo replacement");
  await documentHandle.undo({ expectedRevision: documentHandle.revision });
  const undoMatch = await documentHandle.search("LibreOfficeKit");
  const undoSelection = await documentHandle.getSelection();
  run.replace_undo = undoMatch.found && undoSelection.text === "LibreOfficeKit";

  setStatus("R3: comment and comment undo");
  await documentHandle.search("臺灣軟體工程");
  await documentHandle.addComment("R3 review note", {
    author: "OxOffice SDK",
    expectedRevision: documentHandle.revision,
  });
  const commentsAfterAdd = await documentHandle.listComments();
  const commentAdded = containsText(commentsAfterAdd.comments, "R3 review note");
  appendLog({ type: "r3-comments-after-add", comments: commentsAfterAdd.comments });
  await documentHandle.undo({ expectedRevision: documentHandle.revision });
  const commentsAfterUndo = await documentHandle.listComments();
  const commentUndone = !containsText(commentsAfterUndo.comments, "R3 review note");
  appendLog({ type: "r3-comments-after-undo", comments: commentsAfterUndo.comments });
  await documentHandle.search("臺灣軟體工程");
  await documentHandle.addComment("R3 review note", {
    author: "OxOffice SDK",
    expectedRevision: documentHandle.revision,
  });
  const commentsAfterReadd = await documentHandle.listComments();
  const commentReadded = containsText(commentsAfterReadd.comments, "R3 review note");
  appendLog({ type: "r3-comments-after-readd", comments: commentsAfterReadd.comments });
  run.comment_added = commentAdded;
  run.comment_undo = commentUndone;
  run.comment_readded = commentReadded;
  run.comment_roundtrip = commentAdded && commentUndone && commentReadded;

  setStatus("R3: tracked replacement");
  await documentHandle.setTrackChanges(true, {
    expectedRevision: documentHandle.revision,
  });
  const trackedMatch = await documentHandle.search("English words");
  const trackedSelection = await documentHandle.getSelection();
  await documentHandle.replaceSelection("English terms", {
    expectedRevision: trackedSelection.revision,
  });
  const changes = await documentHandle.listTrackedChanges();
  run.tracked_changes = trackedMatch.found
                        && trackedSelection.text === "English words"
                        && changes.changes.length > 0;

  setStatus("R3: rendering and saving");
  startedAt = performance.now();
  const tile = await documentHandle.render();
  run.t_first_tile_ms = performance.now() - startedAt;
  drawTile(tile);
  startedAt = performance.now();
  const output = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
  run.t_save_ms = performance.now() - startedAt;
  publishOutput(output);
  run.final_revision = documentHandle.revision;
  await documentHandle.close();

  run.main_thread_isolated = metrics.isolation?.pass === true;
  run.pass = run.input_transferred && run.main_thread_isolated
             && run.search_selection && run.replace_undo
             && run.stale_revision_rejected && run.comment_roundtrip
             && run.tracked_changes && output.byteLength > 0;
  if (!run.pass)
    throw new Error(`R3 invariants failed: ${JSON.stringify(run)}`);
  setStatus("R3: complete");
  appendLog({ type: "r3-metrics", run });
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
  metrics.isolation.pass = Object.values(metrics.isolation).every(
    (value) => value === "undefined",
  );
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

globalThis.__r3_run_all = runAll;
globalThis.__r3_run_conformance = runConformance;
$("run-all").addEventListener("click", guard(runAll));
$("run-conformance").addEventListener("click", guard(runConformance));
elements.download.addEventListener("click", () => {
  if (!outputObjectUrl)
    return;
  const anchor = document.createElement("a");
  anchor.href = outputObjectUrl;
  anchor.download = "r3-review-out.odt";
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
