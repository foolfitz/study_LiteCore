import { createDocumentEngine } from "./document-sdk.js";
import { HostInputAdapter, summarizeUnicode } from "./input/input-adapter.js";

const $ = (selector) => document.querySelector(selector);
const statusElement = $("#status");
const manualStatusElement = $("#manual-status");
const logElement = $("#log");
const params = new URLSearchParams(location.search);
const lifecycleCycles = Number(params.get("lifecycleCycles") || 10);
const crashCycles = Number(params.get("crashCycles") || 3);
const metrics = {
  schemaVersion: 1,
  release: "R7-A-discovery",
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  phase: "loading",
  manifest: null,
  sdkEvents: [],
  workers: { created: 0, terminated: 0, intentionalCrashes: 0 },
  input: { synthetic: true, trace: [], commits: [], unicode: [], cancel: null, output: null },
  clipboard: { synthetic: true, api: {}, trace: [], mutationDeltaWithoutGesture: null },
  formats: { cases: [], docxClassification: "not-run" },
  lifecycle: { requestedCycles: lifecycleCycles, cycles: [], crashRequestedCycles: crashCycles, crashes: [] },
  browserMemory: [],
  manual: {
    required: true,
    status: "not-run",
    browser: navigator.userAgent,
    crossOriginIsolated: globalThis.crossOriginIsolated,
    operatorInputMethod: "Fcitx5 Chewing (operator-confirmed)",
    trace: [],
    commits: [],
    caretPlacements: [],
  },
  complete: false,
  pass: false,
  decisionCandidate: "STOP",
  error: null,
};
globalThis.__r7_discovery = metrics;
globalThis.__probe_metrics = metrics;

let outputBuffer = null;
let corpusManifest = null;
let plainOdtBytes = null;
let manualSession = null;

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  logElement.textContent += `[${performance.now().toFixed(1)} ms] ${text}\n`;
  logElement.scrollTop = logElement.scrollHeight;
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
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

function bufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
}

globalThis.__r7_discovery_get_output_base64 = () => {
  if (!outputBuffer)
    throw new Error("R7 Unicode output is not ready");
  return bufferToBase64(outputBuffer);
};

function makeEngine(label) {
  let control = null;
  const promise = createDocumentEngine({
    workerUrl: "./profiles/writer-review-r6/sdk-worker.js",
    timeoutMs: 60000,
    workerFactory(url) {
      const worker = new Worker(url, { name: `r7-${label}-${metrics.workers.created + 1}` });
      metrics.workers.created += 1;
      let terminated = false;
      control = {
        terminate() {
          if (terminated)
            return;
          terminated = true;
          metrics.workers.terminated += 1;
          worker.terminate();
        },
        crash() {
          metrics.workers.intentionalCrashes += 1;
          worker.dispatchEvent(new ErrorEvent("error", {
            message: `intentional R7-A ${label} Document Worker crash`,
          }));
          this.terminate();
        },
      };
      return {
        addEventListener: (...args) => worker.addEventListener(...args),
        postMessage: (...args) => worker.postMessage(...args),
        terminate: () => control.terminate(),
      };
    },
  });
  return promise.then((engine) => {
    engine.onEvent((event) => {
      if (event.event !== "diagnostic")
        metrics.sdkEvents.push({ label, ...event });
    });
    return { engine, get control() { return control; } };
  });
}

async function fetchBytes(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fetch failed ${response.status}: ${path}`);
  return response.arrayBuffer();
}

async function renderFirstTile(documentHandle) {
  const started = performance.now();
  const tile = await documentHandle.render({
    xTwips: 0,
    yTwips: 0,
    widthTwips: Math.min(7680, documentHandle.widthTwips),
    heightTwips: Math.min(7680, documentHandle.heightTwips),
    canvasWidthPx: 128,
    canvasHeightPx: 128,
  }, { timeoutMs: 180000 });
  if (!(tile.pixels instanceof ArrayBuffer) || tile.pixels.byteLength !== tile.width * tile.height * 4)
    throw new Error("invalid first tile buffer");
  return { ms: performance.now() - started, bytes: tile.pixels.byteLength, revision: tile.revision };
}

async function measureBrowserMemory(phase) {
  const item = { phase, atMs: performance.now(), bytes: null, method: null };
  if (typeof performance.measureUserAgentSpecificMemory !== "function") {
    item.method = "unavailable";
  } else {
    try {
      const value = await performance.measureUserAgentSpecificMemory();
      item.bytes = value.bytes;
      item.method = "performance.measureUserAgentSpecificMemory";
    } catch (error) {
      item.method = "failed";
      item.error = serializeError(error);
    }
  }
  metrics.browserMemory.push(item);
}

async function loadCorpus() {
  const response = await fetch("./r7-fixtures/manifest.json", { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`manifest fetch failed: ${response.status}`);
  corpusManifest = await response.json();
  const odt = corpusManifest.documents.find((item) => item.id === "r7-plain-odt");
  plainOdtBytes = await fetchBytes(`./r7-fixtures/${odt.path}`);
}

async function probePermission(name) {
  if (!navigator.permissions?.query)
    return { supported: false, state: "unavailable" };
  try {
    const result = await navigator.permissions.query({ name });
    return { supported: true, state: result.state };
  } catch (error) {
    return { supported: false, state: "unsupported-descriptor", error: serializeError(error) };
  }
}

async function settleWithin(promise, timeoutMs) {
  let timer;
  try {
    return await Promise.race([
      promise.then((value) => ({ status: "fulfilled", value })).catch((error) => ({ status: "rejected", error: serializeError(error) })),
      new Promise((resolve) => { timer = setTimeout(() => resolve({ status: "timeout" }), timeoutMs); }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

async function runInputAndClipboard() {
  metrics.phase = "input";
  statusElement.textContent = "probing synthetic input and Unicode";
  const holder = await makeEngine("input");
  const { engine } = holder;
  metrics.manifest = engine.manifest;
  const documentHandle = await engine.open(plainOdtBytes.slice(0), {
    name: "r7-plain.odt", transfer: true, timeoutMs: 180000,
  });
  await renderFirstTile(documentHandle);
  await documentHandle.click(2400, 2400, { timeoutMs: 60000 });
  const adapter = new HostInputAdapter({
    maxUtf8Bytes: 16 * 1024,
    onTrace: (entry) => {
      metrics.input.trace.push(entry);
      if (entry.type === "paste")
        metrics.clipboard.trace.push(entry);
    },
    commit: async (text, metadata) => {
      const beforeRevision = documentHandle.revision;
      const result = await documentHandle.insertText(text, { timeoutMs: 60000 });
      metrics.input.commits.push({
        ...summarizeUnicode(text), metadata, beforeRevision, revision: result.revision,
      });
      return result;
    },
  });
  const sink = $("#manual-input");
  adapter.attach(sink);

  sink.dispatchEvent(new CompositionEvent("compositionstart", { data: "", bubbles: true }));
  sink.dispatchEvent(new CompositionEvent("compositionupdate", { data: "臺", bubbles: true }));
  sink.dispatchEvent(new InputEvent("beforeinput", {
    data: "臺", inputType: "insertCompositionText", bubbles: true, cancelable: true,
  }));
  sink.dispatchEvent(new CompositionEvent("compositionend", { data: "臺灣合成-R7", bubbles: true }));
  sink.dispatchEvent(new InputEvent("beforeinput", {
    data: "臺灣合成-R7", inputType: "insertText", bubbles: true, cancelable: true,
  }));
  await adapter.idle();
  // LOK paste may leave the first insertion selected. The host must place a
  // caret before the next independent commit or it can replace that selection.
  await documentHandle.click(2400, 2400, { timeoutMs: 60000 });

  const cancelBefore = adapter.state.requestCount;
  sink.dispatchEvent(new CompositionEvent("compositionstart", { data: "", bubbles: true }));
  sink.dispatchEvent(new CompositionEvent("compositionupdate", { data: "取消不落地-R7", bubbles: true }));
  adapter.cancelComposition("synthetic-escape");
  sink.dispatchEvent(new CompositionEvent("compositionend", { data: "", bubbles: true }));
  await adapter.idle();
  metrics.input.cancel = {
    requestDelta: adapter.state.requestCount - cancelBefore,
    found: null,
  };

  const unicodeCases = [
    ["traditional-cjk", "臺灣文件測試"],
    ["fullwidth-punctuation", "「」，。！？；："],
    ["astral-cjk", "𠀀"],
    ["emoji", "😀"],
    ["zwj-family", "👨‍👩‍👧‍👦"],
    ["combining", "e\u0301"],
    ["nfc", "é"],
    ["line-before", "換行前-R7"],
    ["line-break", "\n"],
    ["line-after", "換行後-R7"],
    ["consecutive-one", "連續一-R7"],
    ["consecutive-two", "連續二-R7"],
  ];
  for (const [id, text] of unicodeCases) {
    const before = documentHandle.revision;
    const commit = await adapter.commitText(text, { source: "unicode-probe", id });
    metrics.input.unicode.push({
      id,
      ...summarizeUnicode(text),
      beforeRevision: before,
      revision: documentHandle.revision,
      committed: commit.committed,
      found: null,
    });
  }
  const emptyBefore = adapter.state.requestCount;
  const empty = await adapter.commitText("", { source: "limit-probe" });
  let oversizedError = null;
  try {
    await adapter.commitText("界".repeat(6000), { source: "limit-probe" });
  } catch (error) {
    oversizedError = serializeError(error);
  }
  metrics.input.limits = {
    emptyCommitted: empty.committed,
    oversizedError,
    requestDelta: adapter.state.requestCount - emptyBefore,
  };

  const clipboardMutationBefore = adapter.state.requestCount;
  metrics.clipboard.api = {
    secureContext: globalThis.isSecureContext,
    clipboardPresent: Boolean(navigator.clipboard),
    readTextPresent: typeof navigator.clipboard?.readText === "function",
    writeTextPresent: typeof navigator.clipboard?.writeText === "function",
    readPermission: await probePermission("clipboard-read"),
    writePermission: await probePermission("clipboard-write"),
  };
  if (navigator.clipboard?.readText)
    metrics.clipboard.api.readWithoutGesture = await settleWithin(navigator.clipboard.readText(), 3000);
  metrics.clipboard.mutationDeltaWithoutGesture = adapter.state.requestCount - clipboardMutationBefore;

  const syntheticPasteBefore = adapter.state.requestCount;
  let syntheticPasteMode = "ClipboardEvent";
  try {
    const transfer = new DataTransfer();
    transfer.setData("text/plain", "R7-clipboard-臺灣😀");
    transfer.setData("text/html", "<b>R7-clipboard-臺灣😀</b>");
    sink.dispatchEvent(new ClipboardEvent("paste", { clipboardData: transfer, bubbles: true, cancelable: true }));
  } catch (error) {
    syntheticPasteMode = "adapter-fallback";
    await adapter.handlePaste({
      cancelable: true,
      preventDefault() {},
      clipboardData: { getData: (type) => type === "text/plain" ? "R7-clipboard-臺灣😀" : "<b>ignored</b>" },
    });
    metrics.clipboard.syntheticConstructorError = serializeError(error);
  }
  await adapter.idle();
  if (adapter.state.requestCount === syntheticPasteBefore) {
    syntheticPasteMode = `${syntheticPasteMode}-empty+adapter-fallback`;
    metrics.clipboard.syntheticEventPayloadAvailable = false;
    await adapter.handlePaste({
      cancelable: true,
      preventDefault() {},
      clipboardData: {
        getData: (type) => type === "text/plain"
          ? "R7-clipboard-臺灣😀"
          : "<b>R7-clipboard-臺灣😀</b>",
      },
    });
    await adapter.idle();
  } else {
    metrics.clipboard.syntheticEventPayloadAvailable = true;
  }
  // Search creates a document selection. Perform all mutation first so the
  // next insertText cannot replace an earlier probe selection.
  const compositionSearch = await documentHandle.search("臺灣合成-R7");
  const cancelSearch = await documentHandle.search("取消不落地-R7");
  metrics.input.cancel.found = cancelSearch.found;
  for (const item of metrics.input.unicode) {
    if (item.text !== "\n")
      item.found = (await documentHandle.search(item.text)).found;
  }
  const clipboardSearch = await documentHandle.search("R7-clipboard-臺灣😀");
  metrics.clipboard.syntheticPaste = { mode: syntheticPasteMode, found: clipboardSearch.found };

  outputBuffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
  metrics.input.output = { bytes: outputBuffer.byteLength, sha256: await sha256(outputBuffer) };
  metrics.input.syntheticPass = compositionSearch.found
    && metrics.input.commits.filter((item) => item.text === "臺灣合成-R7").length === 1
    && metrics.input.cancel.requestDelta === 0
    && !metrics.input.cancel.found
    && metrics.input.unicode.every((item) => item.committed && (item.text === "\n" || item.found))
    && metrics.input.limits.requestDelta === 0
    && metrics.input.limits.oversizedError?.code === "INPUT_TOO_LARGE";
  metrics.clipboard.syntheticPass = clipboardSearch.found
    && metrics.clipboard.mutationDeltaWithoutGesture === 0;
  adapter.detach();
  await documentHandle.close({ timeoutMs: 180000 });
  engine.dispose();
  log({ input: metrics.input.syntheticPass, clipboard: metrics.clipboard.syntheticPass });
}

async function formatCase(definition, controlBytes) {
  const result = { ...definition, stage: "init", opened: false, anchorFound: null, firstTile: null, closeMs: null, error: null, workerHealthy: false };
  const holder = await makeEngine(`format-${definition.id}`);
  const { engine } = holder;
  try {
    const bytes = await fetchBytes(`./r7-fixtures/${definition.path}`);
    result.inputBytes = bytes.byteLength;
    result.inputSha256 = await sha256(bytes);
    let documentHandle = null;
    try {
      result.stage = "open";
      documentHandle = await engine.open(bytes, { name: definition.name, transfer: true, timeoutMs: 180000 });
      result.opened = true;
      result.dimensions = { parts: documentHandle.parts, widthTwips: documentHandle.widthTwips, heightTwips: documentHandle.heightTwips };
      result.stage = "render";
      result.firstTile = await renderFirstTile(documentHandle);
      if (definition.anchor) {
        result.stage = "search";
        result.anchorFound = (await documentHandle.search(definition.anchor, { timeoutMs: 60000 })).found;
      }
      result.stage = "close";
      const closeStarted = performance.now();
      await documentHandle.close({ timeoutMs: 180000 });
      result.closeMs = performance.now() - closeStarted;
      result.workerHealthy = true;
      result.stage = "complete";
    } catch (error) {
      result.error = serializeError(error);
      result.failureStage = result.stage;
      result.stage = "health-check";
      try {
        const health = await engine.open(controlBytes.slice(0), { name: "health.odt", transfer: true, timeoutMs: 180000 });
        await renderFirstTile(health);
        await health.close({ timeoutMs: 180000 });
        result.workerHealthy = true;
      } catch (healthError) {
        result.healthError = serializeError(healthError);
      }
      result.stage = "complete";
    }
  } finally {
    engine.dispose();
  }
  result.safe = definition.expected === "positive"
    ? (!result.opened || result.anchorFound === true) && result.workerHealthy
    : !result.opened && result.workerHealthy && Boolean(result.error?.code);
  return result;
}

async function runFormats() {
  metrics.phase = "formats";
  statusElement.textContent = "probing ODT/DOCX classification";
  const odt = corpusManifest.documents.find((item) => item.id === "r7-plain-odt");
  const docx = corpusManifest.documents.find((item) => item.id === "r7-plain-docx");
  const corruptOdt = corpusManifest.documents.find((item) => item.id === "r7-corrupt-truncated-odt");
  const corruptDocx = corpusManifest.documents.find((item) => item.id === "r7-corrupt-truncated-docx");
  const unknown = corpusManifest.documents.find((item) => item.id === "r7-unknown-bin");
  const anchor = odt.anchors[0];
  const definitions = [
    { id: "odt-name-odt", path: odt.path, name: "plain.odt", expected: "positive", anchor },
    { id: "odt-name-docx", path: odt.path, name: "plain.docx", expected: "positive", anchor },
    { id: "docx-name-docx", path: docx.path, name: "plain.docx", expected: "positive", anchor },
    { id: "docx-name-odt", path: docx.path, name: "plain.odt", expected: "positive", anchor },
    { id: "corrupt-odt", path: corruptOdt.path, name: "corrupt.odt", expected: "typed-failure" },
    { id: "corrupt-docx", path: corruptDocx.path, name: "corrupt.docx", expected: "typed-failure" },
    { id: "unknown", path: unknown.path, name: "unknown.bin", expected: "typed-failure" },
  ];
  for (const definition of definitions) {
    const result = await formatCase(definition, plainOdtBytes);
    metrics.formats.cases.push(result);
    log({ format: result.id, opened: result.opened, anchorFound: result.anchorFound, code: result.error?.code, health: result.workerHealthy, safe: result.safe });
  }
  const namedDocx = metrics.formats.cases.find((item) => item.id === "docx-name-docx");
  const disguisedDocx = metrics.formats.cases.find((item) => item.id === "docx-name-odt");
  if (namedDocx.opened && namedDocx.anchorFound && disguisedDocx.opened && disguisedDocx.anchorFound)
    metrics.formats.docxClassification = "content-detected-pass";
  else if (!namedDocx.opened && !disguisedDocx.opened && namedDocx.workerHealthy && disguisedDocx.workerHealthy)
    metrics.formats.docxClassification = "typed-unsupported";
  else if (namedDocx.opened !== disguisedDocx.opened || namedDocx.anchorFound !== disguisedDocx.anchorFound)
    metrics.formats.docxClassification = "name-dependent";
  else
    metrics.formats.docxClassification = "unsafe-or-inconclusive";
  metrics.formats.pass = metrics.formats.cases.every((item) => item.safe)
    && metrics.formats.docxClassification !== "unsafe-or-inconclusive";
}

async function runLifecycle() {
  metrics.phase = "lifecycle";
  statusElement.textContent = `probing ${lifecycleCycles} lifecycle cycles`;
  const holder = await makeEngine("lifecycle");
  const { engine } = holder;
  try {
    for (let cycle = 1; cycle <= lifecycleCycles; cycle += 1) {
      const item = { cycle, openMs: null, firstTileMs: null, closeMs: null, pass: false };
      try {
        const openStarted = performance.now();
        const documentHandle = await engine.open(plainOdtBytes.slice(0), { name: "lifecycle.odt", transfer: true, timeoutMs: 180000 });
        item.openMs = performance.now() - openStarted;
        item.firstTileMs = (await renderFirstTile(documentHandle)).ms;
        const closeStarted = performance.now();
        await documentHandle.close({ timeoutMs: 180000 });
        item.closeMs = performance.now() - closeStarted;
        item.pass = true;
      } catch (error) {
        item.error = serializeError(error);
      }
      metrics.lifecycle.cycles.push(item);
      if (!item.pass)
        break;
    }
  } finally {
    engine.dispose();
  }

  metrics.phase = "crash-restart";
  statusElement.textContent = `probing ${crashCycles} crash/restart cycles`;
  for (let cycle = 1; cycle <= crashCycles; cycle += 1) {
    const item = { cycle, crashEvent: false, staleRejected: false, restartPass: false, pass: false };
    const holderForCrash = await makeEngine(`crash-${cycle}`);
    const { engine: crashEngine } = holderForCrash;
    const eventsBefore = metrics.sdkEvents.length;
    try {
      const stale = await crashEngine.open(plainOdtBytes.slice(0), { name: "crash.odt", transfer: true, timeoutMs: 180000 });
      await renderFirstTile(stale);
      holderForCrash.control.crash();
      await new Promise((resolve) => setTimeout(resolve, 50));
      item.crashEvent = metrics.sdkEvents.slice(eventsBefore).some((event) => event.event === "worker-crashed");
      try {
        await crashEngine.open(plainOdtBytes.slice(0), {
          name: "before-restart.odt", transfer: true, timeoutMs: 5000,
        });
      } catch (error) {
        item.crashStateRejected = error.code === "WORKER_CRASHED";
        item.crashStateError = serializeError(error);
      }
      await crashEngine.restart();
      try {
        await stale.render({ canvasWidthPx: 16, canvasHeightPx: 16 });
      } catch (error) {
        item.staleRejected = error.code === "STALE_DOCUMENT";
        item.staleError = serializeError(error);
      }
      const recovered = await crashEngine.open(plainOdtBytes.slice(0), { name: "recovered.odt", transfer: true, timeoutMs: 180000 });
      await renderFirstTile(recovered);
      await recovered.close({ timeoutMs: 180000 });
      item.restartPass = true;
      item.pass = item.crashEvent && item.crashStateRejected
        && item.staleRejected && item.restartPass;
    } catch (error) {
      item.error = serializeError(error);
    } finally {
      crashEngine.dispose();
    }
    metrics.lifecycle.crashes.push(item);
    if (!item.pass)
      break;
  }
  metrics.lifecycle.pass = metrics.lifecycle.cycles.length === lifecycleCycles
    && metrics.lifecycle.cycles.every((item) => item.pass)
    && metrics.lifecycle.crashes.length === crashCycles
    && metrics.lifecycle.crashes.every((item) => item.pass);
}

async function startManualSession() {
  if (manualSession)
    return manualSession;
  manualStatusElement.textContent = "初始化人工驗收文件…";
  const holder = await makeEngine("manual");
  metrics.manual.artifact = {
    profile: holder.engine.manifest?.profile,
    sdkVersion: holder.engine.manifest?.sdkVersion,
    loader: holder.engine.manifest?.artifactFiles?.["probe.js"],
    wasm: holder.engine.manifest?.artifactFiles?.["probe.wasm"],
  };
  const documentHandle = await holder.engine.open(plainOdtBytes.slice(0), { name: "manual.odt", transfer: true, timeoutMs: 180000 });
  await renderFirstTile(documentHandle);
  await documentHandle.click(2400, 2400, { timeoutMs: 60000 });
  const adapter = new HostInputAdapter({
    maxUtf8Bytes: 16 * 1024,
    onTrace: (entry) => metrics.manual.trace.push(entry),
    commit: async (text, metadata) => {
      const beforeRevision = documentHandle.revision;
      const result = await documentHandle.insertText(text, { timeoutMs: 60000 });
      const entry = { ...summarizeUnicode(text), metadata, beforeRevision, revision: result.revision };
      metrics.manual.commits.push(entry);
      log({ manualCommit: entry });
      manualStatusElement.textContent = `commit #${metrics.manual.commits.length}: ${text}`;
      const caret = metrics.manual.commits.length % 2 === 1
        ? { xTwips: 3600, yTwips: 3000 }
        : { xTwips: 2400, yTwips: 4200 };
      await documentHandle.click(caret.xTwips, caret.yTwips, { timeoutMs: 60000 });
      metrics.manual.caretPlacements.push({ afterRequest: metadata.requestNumber, ...caret });
      return result;
    },
  });
  adapter.attach($("#manual-input"));
  manualSession = { holder, documentHandle, adapter };
  metrics.manual.status = "ready";
  manualStatusElement.textContent = "ready；請聚焦輸入區並使用真實 Fcitx Chewing";
  $("#manual-input").focus();
  return manualSession;
}

function manualEvidenceSummary() {
  return {
    schemaVersion: 1,
    release: "R7-A-headed-manual",
    browser: metrics.manual.browser,
    operatorInputMethod: metrics.manual.operatorInputMethod,
    artifact: metrics.manual.artifact,
    commits: metrics.manual.commits,
    caretPlacements: metrics.manual.caretPlacements,
    imeEvidence: metrics.manual.imeEvidence,
    cancelProbe: metrics.manual.cancelProbe,
    trustedNativePasteCount: metrics.manual.trace.filter((entry) =>
      entry.type === "paste" && entry.isTrusted).length,
    clipboardWrite: metrics.manual.clipboardWrite,
    clipboardRead: metrics.manual.clipboardRead,
    searches: metrics.manual.searches,
    output: metrics.manual.output,
    verifiedAt: metrics.manual.verifiedAt,
    pass: metrics.manual.pass,
  };
}

$("#manual-start").addEventListener("click", () => startManualSession().catch((error) => {
  metrics.manual.error = serializeError(error);
  manualStatusElement.textContent = `${metrics.manual.error.code}: ${metrics.manual.error.message}`;
}));
$("#manual-cancel-arm").addEventListener("click", async () => {
  const session = await startManualSession();
  metrics.manual.cancelProbe = {
    status: "armed",
    commitBaseline: metrics.manual.commits.length,
    traceStart: metrics.manual.trace.length,
  };
  $("#manual-input").focus();
  manualStatusElement.textContent = "請開始一段 Chewing preedit，不選字，直接按 Esc；再按確認按鈕";
});
$("#manual-cancel-check").addEventListener("click", async () => {
  const session = await startManualSession();
  await session.adapter.idle();
  const probe = metrics.manual.cancelProbe || {
    status: "not-armed",
    commitBaseline: metrics.manual.commits.length,
    traceStart: metrics.manual.trace.length,
  };
  const trace = metrics.manual.trace.slice(probe.traceStart);
  const compositionEnd = trace.findLast((entry) => entry.type === "compositionend") || null;
  Object.assign(probe, {
    status: "checked",
    requestDelta: metrics.manual.commits.length - probe.commitBaseline,
    compositionEnd,
    trustedPreedit: trace.some((entry) =>
      entry.isTrusted && ["compositionstart", "compositionupdate", "beforeinput"].includes(entry.type)),
  });
  probe.pass = probe.requestDelta === 0
    && compositionEnd?.data === ""
    && probe.trustedPreedit;
  metrics.manual.cancelProbe = probe;
  manualStatusElement.textContent = probe.pass
    ? "cancel 通過：compositionend 空字串、零 SDK mutation"
    : "cancel 未通過；請保留 evidence，不要重複嘗試掩蓋結果";
});
$("#clipboard-write").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText("R7-manual-clipboard-臺灣😀");
    metrics.manual.clipboardWrite = { status: "passed" };
    manualStatusElement.textContent = "fixture 純文字已寫入 OS clipboard";
  } catch (error) {
    metrics.manual.clipboardWrite = { status: "failed", error: serializeError(error) };
    manualStatusElement.textContent = `clipboard write failed: ${error.name}`;
  }
});
$("#clipboard-read").addEventListener("click", async () => {
  const before = metrics.manual.commits.length;
  try {
    const session = await startManualSession();
    const text = await navigator.clipboard.readText();
    await session.adapter.commitClipboardText(text, { isTrustedGesture: true });
    const search = text ? await session.documentHandle.search(text) : { found: false };
    metrics.manual.clipboardRead = { status: "passed", commitDelta: metrics.manual.commits.length - before, found: search.found, ...summarizeUnicode(text) };
    manualStatusElement.textContent = "clipboard 純文字已 commit 一次";
  } catch (error) {
    metrics.manual.clipboardRead = { status: "failed", commitDelta: metrics.manual.commits.length - before, error: serializeError(error) };
    manualStatusElement.textContent = `clipboard read failed: ${error.name}`;
  }
});
$("#manual-verify").addEventListener("click", async () => {
  try {
    const session = await startManualSession();
    await session.adapter.idle();
    metrics.manual.searches = [];
    for (const commit of metrics.manual.commits) {
      if (commit.text === "\n") {
        metrics.manual.searches.push({
          text: commit.text, searchable: false, found: null,
          verification: "saved ODT only; public search does not accept newline as an anchor",
        });
      } else {
        const search = await session.documentHandle.search(commit.text);
        metrics.manual.searches.push({ text: commit.text, searchable: true, found: search.found });
      }
    }
    const saved = await session.documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
    metrics.manual.output = { bytes: saved.byteLength, sha256: await sha256(saved) };
    metrics.manual.verifiedAt = new Date().toISOString();
    metrics.manual.status = "saved";
    const compositionEvents = metrics.manual.trace.filter((entry) =>
      ["compositionstart", "compositionupdate", "compositionend", "beforeinput"].includes(entry.type));
    metrics.manual.imeEvidence = {
      trustedCompositionStart: compositionEvents.some((entry) =>
        entry.type === "compositionstart" && entry.isTrusted),
      trustedCompositionUpdate: compositionEvents.some((entry) =>
        entry.type === "compositionupdate" && entry.isTrusted),
      trustedCompositionBeforeInput: compositionEvents.some((entry) =>
        entry.type === "beforeinput"
        && entry.inputType === "insertCompositionText"
        && entry.isTrusted),
      compositionEndTrustValues: [...new Set(compositionEvents
        .filter((entry) => entry.type === "compositionend")
        .map((entry) => entry.isTrusted))],
    };
    metrics.manual.pass = metrics.manual.commits.length > 0
      && metrics.manual.searches.every((item) => item.searchable === false || item.found)
      && metrics.manual.cancelProbe?.pass === true
      && metrics.manual.imeEvidence.trustedCompositionStart
      && metrics.manual.imeEvidence.trustedCompositionUpdate
      && metrics.manual.imeEvidence.trustedCompositionBeforeInput
      && metrics.manual.trace.some((entry) => entry.type === "paste" && entry.isTrusted)
      && metrics.manual.clipboardWrite?.status === "passed"
      && metrics.manual.clipboardRead?.status === "passed"
      && metrics.manual.clipboardRead?.found === true
      && metrics.manual.output.bytes > 0;
    $("#manual-evidence").value = JSON.stringify(manualEvidenceSummary(), null, 2);
    manualStatusElement.textContent = metrics.manual.pass
      ? `manual pass；saved ${saved.byteLength} bytes，請複製 evidence JSON`
      : `manual failed；saved ${saved.byteLength} bytes，請保留並複製 evidence JSON`;
    log({ manualResult: metrics.manual });
  } catch (error) {
    metrics.manual.error = serializeError(error);
    manualStatusElement.textContent = `${metrics.manual.error.code}: ${metrics.manual.error.message}`;
  }
});
$("#manual-copy-evidence").addEventListener("click", async () => {
  const text = JSON.stringify(manualEvidenceSummary(), null, 2);
  $("#manual-evidence").value = text;
  try {
    await navigator.clipboard.writeText(text);
    manualStatusElement.textContent = "人工 evidence JSON 已複製；請貼回對話";
  } catch (error) {
    metrics.manual.evidenceCopyError = serializeError(error);
    $("#manual-evidence").value = text;
    $("#manual-evidence").focus();
    $("#manual-evidence").select();
    manualStatusElement.textContent = "自動複製失敗；JSON 已全選，請按 Ctrl+C";
  }
});

async function run() {
  try {
    await measureBrowserMemory("before");
    await loadCorpus();
    await runInputAndClipboard();
    await runFormats();
    await runLifecycle();
    await measureBrowserMemory("after");
    const docxPartial = ["typed-unsupported", "name-dependent"]
      .includes(metrics.formats.docxClassification);
    metrics.pass = metrics.crossOriginIsolated
      && metrics.manifest?.profile === "writer-review"
      && metrics.input.syntheticPass
      && metrics.clipboard.syntheticPass
      && metrics.formats.pass
      && metrics.lifecycle.pass;
    metrics.decisionCandidate = metrics.pass ? (docxPartial ? "PARTIAL_GO" : "GO") : "STOP";
    metrics.phase = "complete";
    statusElement.textContent = metrics.pass
      ? `complete: ${metrics.decisionCandidate}; headed manual pending`
      : "complete: STOP invariants failed";
  } catch (error) {
    metrics.error = serializeError(error);
    metrics.phase = "error";
    statusElement.textContent = `error: ${metrics.error.code}`;
    log(metrics.error);
  } finally {
    metrics.complete = true;
  }
}

run();
