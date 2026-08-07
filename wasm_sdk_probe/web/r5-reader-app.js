import {
  DocumentSdkError,
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
  schema_version: 5,
  protocol_version: 1,
  page_load_epoch_ms: performance.timeOrigin,
  user_agent: navigator.userAgent,
  cross_origin_isolated: globalThis.crossOriginIsolated,
  t_ready_ms: null,
  manifest: null,
  events: [],
  runs: [],
};
globalThis.__r5_metrics = metrics;
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
    throw new Error("R5 reader output is not ready");
  const bytes = new Uint8Array(outputBuffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
};

async function expectUnsupported(invoke, operation) {
  try {
    await invoke();
  } catch (error) {
    if (error instanceof DocumentSdkError
        && error.code === "UNSUPPORTED_OPERATION"
        && error.details?.operation === operation) {
      return true;
    }
    throw error;
  }
  return false;
}

async function runAll() {
  await initializationPromise;
  const [file] = elements.file.files;
  if (!file)
    throw new Error("請先選擇 t1-plain-zh.odt");
  const run = {
    browser: navigator.userAgent,
    doc: file.name,
    cache: new URLSearchParams(location.search).get("cache") || "unspecified",
    profile: metrics.manifest?.profile,
    t_ready_ms: metrics.t_ready_ms,
    t_open_ms: null,
    t_search_latin_ms: null,
    t_search_cjk_ms: null,
    t_first_tile_ms: null,
    t_save_ms: null,
    input_transferred: false,
    capability_match: false,
    cjk_startup_pack_declared: false,
    latin_found: false,
    cjk_found: false,
    replace_rejected: false,
    comment_rejected: false,
    pass: false,
  };
  metrics.runs.push(run);

  setStatus("R5 reader: opening");
  const input = await file.arrayBuffer();
  let startedAt = performance.now();
  const documentHandle = await engine.open(input, {
    name: file.name,
    transfer: true,
    timeoutMs: 180000,
  });
  run.t_open_ms = performance.now() - startedAt;
  run.input_transferred = input.byteLength === 0;
  run.capability_match = metrics.manifest.capabilityBits === 59
                         && metrics.manifest.expectedCapabilityBits === 59
                         && !metrics.manifest.capabilities.includes("replace-selection")
                         && !metrics.manifest.capabilities.includes("comments");
  run.cjk_startup_pack_declared = metrics.manifest.resourcePacks.some(
    (pack) => pack.id === "cjk-r5" && pack.loadAtStartup === true,
  );

  setStatus("R5 reader: searching");
  startedAt = performance.now();
  run.latin_found = (await documentHandle.search("LibreOfficeKit")).found;
  run.t_search_latin_ms = performance.now() - startedAt;
  startedAt = performance.now();
  run.cjk_found = (await documentHandle.search("臺灣軟體工程")).found;
  run.t_search_cjk_ms = performance.now() - startedAt;

  setStatus("R5 reader: checking capability boundary");
  run.replace_rejected = await expectUnsupported(
    () => documentHandle.replaceSelection("must-not-apply"),
    "replaceSelection",
  );
  run.comment_rejected = await expectUnsupported(
    () => documentHandle.addComment("must-not-apply"),
    "addComment",
  );

  setStatus("R5 reader: rendering and saving");
  startedAt = performance.now();
  const tile = await documentHandle.render();
  run.t_first_tile_ms = performance.now() - startedAt;
  drawTile(tile);
  startedAt = performance.now();
  const output = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
  run.t_save_ms = performance.now() - startedAt;
  publishOutput(output);
  await documentHandle.close();

  run.pass = run.input_transferred && run.capability_match
             && run.cjk_startup_pack_declared && run.latin_found && run.cjk_found
             && run.replace_rejected && run.comment_rejected
             && output.byteLength > 0;
  if (!run.pass)
    throw new Error(`R5 reader invariants failed: ${JSON.stringify(run)}`);
  setStatus("R5 reader: complete");
  appendLog({ type: "r5-reader-metrics", run });
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
  const profile = new URLSearchParams(location.search).get("profile") || "writer-reader";
  engine = await createDocumentEngine({
    workerUrl: `./profiles/${encodeURIComponent(profile)}/sdk-worker.js`,
    timeoutMs: 30000,
    debug: new URLSearchParams(location.search).get("debug") === "1",
  });
  engine.onEvent((event) => {
    metrics.events.push(event);
    appendLog(event);
  });
  metrics.manifest = engine.manifest;
  metrics.t_ready_ms = performance.now();
  setStatus("ready");
  appendLog({ type: "ready", manifest: engine.manifest });
}

globalThis.__r5_run_all = runAll;
$("run-all").addEventListener("click", guard(runAll));
elements.download.addEventListener("click", () => {
  if (!outputObjectUrl)
    return;
  const anchor = document.createElement("a");
  anchor.href = outputObjectUrl;
  anchor.download = "r5-reader-out.odt";
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
