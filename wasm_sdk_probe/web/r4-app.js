import {
  StaleRevisionError,
  createDocumentEngine,
} from "./document-sdk.js";
import {
  PROVIDER_CONTRACT_VERSION,
  ProviderAbortError,
  ProviderHost,
  ProviderRegistry,
  ProviderSdkError,
  WorkerProviderAdapter,
  createInProcessProviderAdapter,
  createWebDocumentAdapter,
} from "./provider-sdk/provider-sdk.js";
import { descriptor } from "./providers/text-translate-descriptor.js";

const $ = (id) => document.getElementById(id);
const elements = {
  file: $("file"),
  canvas: $("canvas"),
  log: $("log"),
  status: $("status"),
  download: $("download"),
};

const metrics = {
  schema_version: 4,
  protocol_version: 1,
  provider_contract_version: PROVIDER_CONTRACT_VERSION,
  page_load_epoch_ms: performance.timeOrigin,
  user_agent: navigator.userAgent,
  cross_origin_isolated: globalThis.crossOriginIsolated,
  t_ready_ms: null,
  isolation: null,
  manifest: null,
  provider: null,
  runs: [],
  conformance: [],
  memory: [],
};
globalThis.__r4_metrics = metrics;
globalThis.__probe_metrics = metrics;

let engine = null;
let providerRegistry = null;
let providerAdapter = null;
let providerHost = null;
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
    throw new Error("R4 output is not ready");
  const bytes = new Uint8Array(outputBuffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
};

async function runConformance() {
  await initializationPromise;
  const listed = providerRegistry.listProviders();
  const isolation = providerAdapter.runtimeInfo || {};

  let blockedSinkCalls = 0;
  let invalidOperationBlocked = false;
  const badRegistry = new ProviderRegistry();
  badRegistry.register(descriptor, createInProcessProviderAdapter({
    invoke: async (invocation) => ({
      type: "rawUno",
      text: ".uno:Paste",
      expectedRevision: invocation.input.revision,
    }),
  }));
  const badHost = new ProviderHost({ registry: badRegistry });
  try {
    await badHost.invokeSelection({
      providerId: descriptor.id,
      endpointId: "translate-selection",
      documentAdapter: {
        binding: "conformance",
        snapshotSelection: async () => ({ text: "English words", revision: 0 }),
        applyValidatedOperation: async () => { blockedSinkCalls += 1; },
      },
      parameters: { "target-language": "zh-TW" },
    });
  } catch (error) {
    invalidOperationBlocked = error instanceof ProviderSdkError
                              && error.code === "INVALID_OPERATION";
  } finally {
    badRegistry.dispose();
  }

  let cancelSinkCalls = 0;
  let cancellationTyped = false;
  const controller = new AbortController();
  try {
    await providerHost.invokeSelection({
      providerId: descriptor.id,
      endpointId: "translate-selection",
      documentAdapter: {
        binding: "conformance",
        snapshotSelection: async () => ({ text: "English words", revision: 0 }),
        applyValidatedOperation: async () => { cancelSinkCalls += 1; },
      },
      parameters: { "target-language": "zh-TW" },
      signal: controller.signal,
      onProgress: () => controller.abort(),
    });
  } catch (error) {
    cancellationTyped = error instanceof ProviderAbortError
                        && error.code === "PROVIDER_ABORTED";
  }
  await new Promise((resolve) => setTimeout(resolve, 20));

  const result = {
    contract_1_0: PROVIDER_CONTRACT_VERSION === "1.0"
                  && listed[0]?.contractVersion === "1.0",
    provider_discovery: listed.length === 1 && listed[0]?.id === descriptor.id,
    descriptor_immutable: Object.isFrozen(listed[0])
                          && Object.isFrozen(listed[0]?.endpoints?.[0]),
    dedicated_worker: providerAdapter.kind === "worker"
                      && isolation.globalKind === "dedicated-worker",
    provider_worker_document_isolated: isolation.document === "undefined"
                                       && isolation.createProbeModule === "undefined"
                                       && isolation.FS === "undefined"
                                       && isolation.HEAPU8 === "undefined",
    invalid_operation_blocked: invalidOperationBlocked && blockedSinkCalls === 0,
    cancellation_typed_no_mutation: cancellationTyped && cancelSinkCalls === 0,
    no_generic_uno_surface: typeof providerHost.invokeUno === "undefined"
                            && typeof providerHost.postUnoCommand === "undefined",
    no_raw_document_surface: typeof providerAdapter.document === "undefined"
                             && typeof providerAdapter.documentHandle === "undefined",
  };
  result.pass = Object.values(result).every(Boolean);
  if (!result.pass)
    throw new Error(`R4 conformance failed: ${JSON.stringify(result)}`);
  metrics.conformance.push(result);
  setStatus("R4 conformance: complete");
  appendLog({ type: "r4-conformance", result });
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
    t_provider_ms: null,
    t_stale_provider_ms: null,
    t_first_tile_ms: null,
    t_save_ms: null,
    input_transferred: false,
    main_thread_isolated: false,
    provider_worker_isolated: false,
    provider_discovered: false,
    progress_reported: false,
    stale_provider_rejected: false,
    stale_text_absent_after_undo: false,
    validated_replace: false,
    output_text_selected: false,
    operation_type: null,
    operation_expected_revision: null,
    final_revision: null,
    pass: false,
  };
  metrics.runs.push(run);

  setStatus("R4: opening");
  const input = await file.arrayBuffer();
  let startedAt = performance.now();
  const documentHandle = await engine.open(input, {
    name: file.name,
    transfer: true,
    timeoutMs: 180000,
  });
  run.t_open_ms = performance.now() - startedAt;
  run.input_transferred = input.byteLength === 0;
  const documentAdapter = createWebDocumentAdapter(documentHandle);
  run.provider_discovered = providerRegistry.listProviders().some(
    (item) => item.id === descriptor.id,
  );

  setStatus("R4: stale asynchronous provider result");
  await documentHandle.search("English words");
  let firstProgressResolve;
  const firstProgress = new Promise((resolve) => { firstProgressResolve = resolve; });
  startedAt = performance.now();
  const staleInvocation = providerHost.invokeSelection({
    providerId: descriptor.id,
    endpointId: "translate-selection",
    documentAdapter,
    parameters: { "target-language": "zh-TW" },
    onProgress: (progress) => {
      appendLog({ type: "r4-stale-provider-progress", progress });
      firstProgressResolve();
    },
  });
  await firstProgress;
  await documentHandle.replaceSelection("R4-CONCURRENT-EDIT", {
    expectedRevision: documentHandle.revision,
  });
  try {
    await staleInvocation;
  } catch (error) {
    run.stale_provider_rejected = error instanceof StaleRevisionError
                                  && error.code === "STALE_REVISION"
                                  && error.details?.expectedRevision === 0
                                  && error.details?.currentRevision === 1;
  }
  run.t_stale_provider_ms = performance.now() - startedAt;
  await documentHandle.undo({ expectedRevision: documentHandle.revision });
  const restored = await documentHandle.search("English words");
  const restoredSelection = await documentHandle.getSelection();
  run.stale_text_absent_after_undo = restored.found
                                    && restoredSelection.text === "English words";

  setStatus("R4: validated Provider replacement");
  const progress = [];
  startedAt = performance.now();
  const providerResult = await providerHost.invokeSelection({
    providerId: descriptor.id,
    endpointId: "translate-selection",
    documentAdapter,
    parameters: { "target-language": "zh-TW" },
    onProgress: (value) => {
      progress.push(value);
      appendLog({ type: "r4-provider-progress", progress: value });
    },
  });
  run.t_provider_ms = performance.now() - startedAt;
  run.progress_reported = progress.length === 3
                          && progress[0].fraction === 0.25
                          && progress.at(-1).fraction === 1;
  run.operation_type = providerResult.operation.type;
  run.operation_expected_revision = providerResult.operation.expectedRevision;
  run.validated_replace = providerResult.operation.type === "replaceSelection"
                          && providerResult.operation.text === "R4 Provider：英文詞彙"
                          && providerResult.operation.expectedRevision === 2
                          && documentHandle.revision === 3;
  const outputMatch = await documentHandle.search("R4 Provider：英文詞彙");
  const outputSelection = await documentHandle.getSelection();
  run.output_text_selected = outputMatch.found
                             && outputSelection.text === "R4 Provider：英文詞彙";

  setStatus("R4: rendering and saving");
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

  const providerIsolation = providerAdapter.runtimeInfo || {};
  run.main_thread_isolated = metrics.isolation?.main?.pass === true;
  run.provider_worker_isolated = providerIsolation.document === "undefined"
                                 && providerIsolation.createProbeModule === "undefined"
                                 && providerIsolation.FS === "undefined"
                                 && providerIsolation.HEAPU8 === "undefined";
  run.pass = run.input_transferred && run.main_thread_isolated
             && run.provider_worker_isolated && run.provider_discovered
             && run.progress_reported && run.stale_provider_rejected
             && run.stale_text_absent_after_undo && run.validated_replace
             && run.output_text_selected && run.final_revision === 3
             && output.byteLength > 0;
  if (!run.pass)
    throw new Error(`R4 invariants failed: ${JSON.stringify(run)}`);
  setStatus("R4: complete");
  appendLog({ type: "r4-metrics", run });
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
  const mainIsolation = {
    createProbeModule: typeof globalThis.createProbeModule,
    FS: typeof globalThis.FS,
    HEAPU8: typeof globalThis.HEAPU8,
  };
  mainIsolation.pass = Object.values(mainIsolation).every(
    (value) => value === "undefined",
  );
  providerRegistry = new ProviderRegistry();
  providerAdapter = new WorkerProviderAdapter({
    workerUrl: new URL("./providers/text-translate-worker.js", import.meta.url),
    providerId: descriptor.id,
  });
  providerRegistry.register(descriptor, providerAdapter);
  providerHost = new ProviderHost({ registry: providerRegistry });
  const profile = new URLSearchParams(location.search).get("profile");
  const workerUrl = profile
    ? `./profiles/${encodeURIComponent(profile)}/sdk-worker.js`
    : "./sdk-worker.js";
  [engine] = await Promise.all([
    createDocumentEngine({
      workerUrl,
      timeoutMs: 30000,
      debug: new URLSearchParams(location.search).get("debug") === "1",
    }),
    providerAdapter.ready(),
  ]);
  engine.onEvent((event) => appendLog(event));
  metrics.manifest = engine.manifest;
  metrics.provider = {
    descriptor: providerRegistry.listProviders()[0],
    adapter: providerAdapter.kind,
    runtime: providerAdapter.runtimeInfo,
  };
  metrics.isolation = { main: mainIsolation, provider: providerAdapter.runtimeInfo };
  metrics.t_ready_ms = performance.now();
  setStatus("ready");
  appendLog({
    type: "ready",
    manifest: engine.manifest,
    provider: metrics.provider,
    isolation: metrics.isolation,
  });
}

globalThis.__r4_run_all = runAll;
globalThis.__r4_run_conformance = runConformance;
$("run-all").addEventListener("click", guard(runAll));
$("run-conformance").addEventListener("click", guard(runConformance));
elements.download.addEventListener("click", () => {
  if (!outputObjectUrl)
    return;
  const anchor = document.createElement("a");
  anchor.href = outputObjectUrl;
  anchor.download = "r4-provider-out.odt";
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
