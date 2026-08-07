import { createDocumentEngine } from "./document-sdk.js";
import { HostInputAdapter, summarizeUnicode } from "./input/input-adapter.js";
import { PlainTextClipboardAdapter } from "./input/clipboard-adapter.js";
import { PageHintNavigator, classifyHyperlinkTarget } from "./r7/page-navigation.js";

const $ = (selector) => document.querySelector(selector);
const params = new URLSearchParams(location.search);
const automatic = params.get("automatic") === "1";
const usabilityMode = params.get("usability") === "1";
const metrics = {
  schemaVersion: 1,
  release: "R7-B",
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  artifact: null,
  phase: "loading",
  synthetic: automatic,
  input: { trace: [], states: [], commits: [], searches: [], pureContract: null },
  clipboard: { trace: [], contract: null },
  usability: null,
  workers: { created: 0, terminated: 0 },
  output: null,
  manual: {
    browser: navigator.userAgent,
    sessions: {},
    activeMethod: null,
    commits: [],
    trace: [],
    cancelProbes: [],
    clipboard: {},
    searches: [],
    output: null,
  },
  complete: false,
  pass: false,
  error: null,
};
globalThis.__probe_metrics = metrics;
globalThis.__r7_reference = metrics;

let fixtureBytes = null;
let engine = null;
let documentHandle = null;
let workerControl = null;
let adapter = null;
let clipboardAdapter = null;
let outputBuffer = null;
let caretIndex = 0;
let pageNavigator = null;

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

globalThis.__r7_get_output_base64 = () => {
  if (!outputBuffer)
    throw new Error("R7 output is not ready");
  return bufferToBase64(outputBuffer);
};

function createEngine() {
  return createDocumentEngine({
    workerUrl: "./profiles/writer-review-r6/sdk-worker.js",
    timeoutMs: 60000,
    workerFactory(url) {
      const worker = new Worker(url, { name: `r7-reference-${metrics.workers.created + 1}` });
      metrics.workers.created += 1;
      let terminated = false;
      workerControl = {
        terminate() {
          if (terminated)
            return;
          terminated = true;
          metrics.workers.terminated += 1;
          worker.terminate();
        },
        crash() {
          worker.dispatchEvent(new ErrorEvent("error", { message: "intentional R7-B crash" }));
          this.terminate();
        },
      };
      return {
        addEventListener: (...args) => worker.addEventListener(...args),
        postMessage: (...args) => worker.postMessage(...args),
        terminate: () => workerControl.terminate(),
      };
    },
  });
}

async function loadFixture() {
  const response = await fetch("./r7-fixtures/r7-plain.odt", { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fixture fetch failed: ${response.status}`);
  fixtureBytes = await response.arrayBuffer();
}

async function renderViewport() {
  const viewport = $("#viewport");
  const surface = $("#surface");
  const widthTwips = Math.min(documentHandle.widthTwips, Math.max(1, viewport.clientWidth * 15));
  const heightTwips = Math.min(documentHandle.heightTwips, Math.max(1, viewport.clientHeight * 15));
  const tile = await documentHandle.render({
    xTwips: 0, yTwips: 0, widthTwips, heightTwips,
    canvasWidthPx: Math.max(1, Math.floor(widthTwips / 15)),
    canvasHeightPx: Math.max(1, Math.floor(heightTwips / 15)),
  }, { timeoutMs: 180000 });
  const canvas = document.createElement("canvas");
  canvas.className = "document-tile";
  canvas.width = tile.width;
  canvas.height = tile.height;
  canvas.getContext("2d").putImageData(new ImageData(
    new Uint8ClampedArray(tile.pixels), tile.width, tile.height,
  ), 0, 0);
  $("#tiles").replaceChildren(canvas);
  surface.style.width = `${Math.max(viewport.clientWidth, documentHandle.widthTwips / 15)}px`;
  surface.style.height = `${Math.max(viewport.clientHeight, documentHandle.heightTwips / 15)}px`;
}

async function placeCaret() {
  const positions = [
    { xTwips: 3000, yTwips: Math.max(720, documentHandle.heightTwips - 1200) },
    { xTwips: 4800, yTwips: Math.max(720, documentHandle.heightTwips - 900) },
  ];
  const position = positions[caretIndex++ % positions.length];
  await documentHandle.click(position.xTwips, position.yTwips, { timeoutMs: 60000 });
  return position;
}

function updateInputState(state) {
  $("#input-state").textContent = state.status;
  $("#queue-depth").textContent = `${state.queueDepth} / 8`;
  $("#manual-input").disabled = state.blocked;
  metrics.input.states.push({ atMs: performance.now(), ...state });
}

function createAdapters(target, sink) {
  const input = new HostInputAdapter({
    maxUtf8Bytes: 16 * 1024,
    maxQueueDepth: 8,
    onState: updateInputState,
    onTrace(entry) {
      target.trace.push(entry);
      if (!automatic && target !== metrics.manual)
        metrics.manual.trace.push(entry);
    },
    async commit(text, metadata) {
      const beforeRevision = documentHandle.revision;
      const result = await documentHandle.insertText(text, { timeoutMs: 60000 });
      const entry = {
        ...summarizeUnicode(text), metadata, beforeRevision, revision: result.revision,
        method: result.method,
      };
      target.commits.push(entry);
      if (!automatic && target !== metrics.manual)
        metrics.manual.commits.push({ ...entry, inputMethod: metrics.manual.activeMethod });
      else if (!automatic)
        target.commits[target.commits.length - 1].inputMethod = metrics.manual.activeMethod;
      $("#revision").textContent = String(result.revision);
      sink.value = "";
      log({ commit: entry });
      await placeCaret();
      return result;
    },
  });
  input.attach(sink);
  const clipboard = new PlainTextClipboardAdapter({
    inputAdapter: input,
    clipboard: navigator.clipboard,
    secureContext: globalThis.isSecureContext,
    getSelection: () => documentHandle.getSelection({ timeoutMs: 60000 }),
    onTrace: (entry) => metrics.clipboard.trace.push(entry),
  });
  return { input, clipboard };
}

async function openDocument() {
  engine = await createEngine();
  metrics.artifact = {
    profile: engine.manifest.profile,
    sdkVersion: engine.manifest.sdkVersion,
    coreCommit: engine.manifest.coreCommit,
    loader: engine.manifest.artifactFiles?.["probe.js"],
    wasm: engine.manifest.artifactFiles?.["probe.wasm"],
  };
  $("#profile").textContent = engine.manifest.profile;
  $("#sdk-version").textContent = engine.manifest.sdkVersion;
  documentHandle = await engine.open(fixtureBytes.slice(0), {
    name: "r7-input-fixture.odt", transfer: true, timeoutMs: 180000,
  });
  $("#revision").textContent = String(documentHandle.revision);
  pageNavigator = new PageHintNavigator({
    pageCount: Number(params.get("pageCount") || 1),
    documentHeightTwips: documentHandle.heightTwips,
  });
  $("#location").textContent = pageNavigator.snapshot.label;
  await renderViewport();
  await placeCaret();
}

function syntheticEvent(properties = {}) {
  return {
    cancelable: true,
    defaultPrevented: false,
    preventDefault() { this.defaultPrevented = true; },
    ...properties,
  };
}

async function pureContractProbe() {
  let release;
  const mutations = [];
  const input = new HostInputAdapter({
    maxQueueDepth: 2,
    commit: async (text) => {
      mutations.push(text);
      if (text === "in-flight")
        await new Promise((resolve) => { release = resolve; });
      return { revision: mutations.length, method: "paste" };
    },
  });
  const first = input.commitText("in-flight");
  const queued = input.commitText("cancel-on-stale").then(
    () => ({ status: "unexpected-success" }),
    (error) => ({ status: "rejected", code: error.code }),
  );
  const backpressure = await input.commitText("queue-full").then(
    () => ({ status: "unexpected-success" }),
    (error) => ({ status: "rejected", code: error.code }),
  );
  const invalidation = input.invalidate("stale", { blocked: true });
  release();
  await first;
  const queuedResult = await queued;
  const blocked = await input.commitText("blocked").then(
    () => ({ status: "unexpected-success" }),
    (error) => ({ status: "rejected", code: error.code }),
  );
  return {
    mutations,
    backpressure,
    invalidation,
    queued: queuedResult,
    blocked,
    pass: backpressure.code === "INPUT_BACKPRESSURE"
      && invalidation.cancelled === 1
      && queuedResult.code === "INPUT_CANCELLED"
      && blocked.code === "INPUT_BLOCKED"
      && JSON.stringify(mutations) === JSON.stringify(["in-flight"]),
  };
}

async function clipboardContractProbe() {
  let mutations = 0;
  const mockInput = new HostInputAdapter({
    commit: async () => { mutations += 1; return { revision: mutations }; },
  });
  const deniedError = Object.assign(new Error("denied"), { name: "NotAllowedError" });
  const denied = new PlainTextClipboardAdapter({
    inputAdapter: mockInput,
    clipboard: { readText: async () => { throw deniedError; } },
    secureContext: true,
  });
  const withoutGesture = await denied.pasteFromClipboard().then(
    () => ({ status: "unexpected-success" }),
    (error) => ({ status: "rejected", code: error.code }),
  );
  const deniedRead = await denied.pasteFromClipboard({ userGesture: true }).then(
    () => ({ status: "unexpected-success" }),
    (error) => ({ status: "rejected", code: error.code }),
  );
  const unsupported = await denied.pasteEvent({
    preventDefault() {}, clipboardData: { types: ["image/png"], getData: () => "" },
  }).then(
    () => ({ status: "unexpected-success" }),
    (error) => ({ status: "rejected", code: error.code }),
  );
  return {
    withoutGesture, deniedRead, unsupported, mutationDelta: mutations,
    pass: withoutGesture.code === "CLIPBOARD_DENIED"
      && deniedRead.code === "CLIPBOARD_DENIED"
      && unsupported.code === "UNSUPPORTED_CLIPBOARD_TYPE"
      && mutations === 0,
  };
}

async function runAutomatic() {
  metrics.phase = "automatic-input";
  $("#status").textContent = "執行 R7-B synthetic contract";
  const sink = $("#manual-input");
  ({ input: adapter, clipboard: clipboardAdapter } = createAdapters(metrics.input, sink));
  const beforeComposition = metrics.input.commits.length;
  adapter.handleCompositionStart(syntheticEvent({ data: "" }));
  adapter.handleCompositionUpdate(syntheticEvent({ data: "臺" }));
  await adapter.handleBeforeInput(syntheticEvent({
    inputType: "insertCompositionText", data: "臺",
  }));
  const composition = adapter.handleCompositionEnd(syntheticEvent({ data: "臺灣文件測試" }));
  const duplicate = await adapter.handleBeforeInput(syntheticEvent({
    inputType: "insertText", data: "臺灣文件測試",
  }));
  await composition;
  await adapter.idle();

  const beforeCancel = metrics.input.commits.length;
  adapter.handleCompositionStart(syntheticEvent());
  adapter.handleCompositionUpdate(syntheticEvent({ data: "取消不得落地-R7-B" }));
  adapter.cancelComposition("escape");
  await adapter.handleCompositionEnd(syntheticEvent({ data: "" }));

  const unicodeCases = [
    "這是一段二十字以上的繁體中文輸入驗收句子",
    "「全形標點」，。！？；：",
    "𠀀", "😀", "👨‍👩‍👧‍👦", "e\u0301", "é", "\n",
    "連續提交一-R7-B", "連續提交二-R7-B",
  ];
  for (const text of unicodeCases)
    await adapter.commitText(text, { source: "synthetic-unicode" });

  const pasteEvent = {
    isTrusted: false,
    preventDefault() {},
    clipboardData: {
      types: ["text/html", "text/plain"],
      getData: (type) => type === "text/plain"
        ? "R7-B-clipboard-𠀀😀👨‍👩‍👧‍👦éé"
        : "<b>must-not-enter-document</b>",
    },
  };
  await clipboardAdapter.pasteEvent(pasteEvent, { synthetic: true });
  await adapter.idle();

  metrics.input.pureContract = await pureContractProbe();
  metrics.clipboard.contract = await clipboardContractProbe();
  const expected = [
    "臺灣文件測試", ...unicodeCases.filter((text) => text !== "\n"),
    "R7-B-clipboard-𠀀😀👨‍👩‍👧‍👦éé",
  ];
  for (const text of expected) {
    const result = await documentHandle.search(text, { timeoutMs: 60000 });
    metrics.input.searches.push({ text, found: result.found });
  }
  const cancelled = await documentHandle.search("取消不得落地-R7-B", { timeoutMs: 60000 });
  metrics.input.searches.push({ text: "取消不得落地-R7-B", found: cancelled.found, expected: false });
  outputBuffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
  metrics.output = { bytes: outputBuffer.byteLength, sha256: await sha256(outputBuffer) };
  metrics.pass = metrics.crossOriginIsolated
    && metrics.artifact.profile === "writer-review"
    && metrics.input.commits.length - beforeComposition === unicodeCases.length + 2
    && metrics.input.commits.length - beforeCancel === unicodeCases.length + 1
    && duplicate.reason === "post-composition-duplicate"
    && metrics.input.searches.every((item) => item.found === (item.expected ?? true))
    && metrics.input.pureContract.pass
    && metrics.clipboard.contract.pass
    && metrics.output.bytes > 0;
  metrics.phase = "complete";
  $("#status").textContent = metrics.pass ? "R7-B automatic pass" : "R7-B automatic failed";
}

function currentManualSession() {
  const key = metrics.manual.activeMethod;
  if (!key)
    return null;
  return metrics.manual.sessions[key] ||= {
    inputMethod: key, commitStart: metrics.manual.commits.length, cancel: null,
  };
}

function manualSummary() {
  return {
    schemaVersion: 1,
    release: "R7-B-headed-manual",
    browser: metrics.manual.browser,
    artifact: metrics.artifact,
    sessions: metrics.manual.sessions,
    commits: metrics.manual.commits,
    cancelProbes: metrics.manual.cancelProbes,
    trustedNativePasteCount: metrics.manual.trace.filter((entry) =>
      entry.type === "paste" && entry.isTrusted).length,
    clipboard: metrics.manual.clipboard,
    searches: metrics.manual.searches,
    output: metrics.manual.output,
    accessibility: metrics.manual.accessibility || null,
    verifiedAt: metrics.manual.verifiedAt || null,
    pass: metrics.manual.pass === true,
  };
}

function bindControls() {
  $("#search-next").addEventListener("click", async () => {
    try {
      const result = await documentHandle.search($("#search").value, { timeoutMs: 60000 });
      const selection = result.found ? await documentHandle.getSelection() : null;
      $("#search-result").textContent = result.found
        ? `已找到：${selection.text}` : "找不到；無公開 geometry 可精確捲動";
    } catch (error) {
      $("#message").textContent = `${error.code || "ERROR"}: ${error.message}`;
    }
  });
  $("#zoom-100").addEventListener("click", () => { $("#surface").style.zoom = "1"; });
  $("#zoom-150").addEventListener("click", () => { $("#surface").style.zoom = "1.5"; });
  const pageIntents = {
    "page-first": "first", "page-previous": "previous",
    "page-next": "next", "page-last": "last",
  };
  for (const [id, intent] of Object.entries(pageIntents))
    $(`#${id}`).addEventListener("click", () => {
      const hint = pageNavigator.target(intent);
      const viewport = $("#viewport");
      const maximum = Math.max(0, viewport.scrollHeight - viewport.clientHeight);
      const ratio = hint.pageCount === 1 ? 0 : (hint.currentPage - 1) / (hint.pageCount - 1);
      viewport.scrollTop = Math.round(ratio * maximum);
      $("#location").textContent = hint.label;
    });
  $("#viewport").addEventListener("scroll", () => {
    const viewport = $("#viewport");
    $("#location").textContent = pageNavigator.updateFromScroll(
      viewport.scrollTop, viewport.scrollHeight, viewport.clientHeight,
    ).label;
  });
  $("#manual-arm").addEventListener("click", () => {
    metrics.manual.activeMethod = $("#manual-method").value;
    currentManualSession();
    $("#manual-input").focus();
    $("#manual-status").textContent = `正在記錄 ${metrics.manual.activeMethod}`;
  });
  $("#cancel-arm").addEventListener("click", () => {
    const session = currentManualSession();
    if (!session) {
      $("#manual-status").textContent = "請先選擇並開始 input method";
      return;
    }
    session.cancel = {
      status: "armed", commitBaseline: metrics.manual.commits.length,
      traceStart: metrics.manual.trace.length,
    };
    $("#manual-input").focus();
    $("#manual-status").textContent = "請開始 preedit 後直接按 Esc，再按確認";
  });
  $("#cancel-check").addEventListener("click", async () => {
    await adapter.idle();
    const session = currentManualSession();
    const probe = session?.cancel;
    if (!probe) {
      $("#manual-status").textContent = "cancel 尚未 armed";
      return;
    }
    const trace = metrics.manual.trace.slice(probe.traceStart);
    const end = trace.findLast((item) => item.type === "compositionend") || null;
    Object.assign(probe, {
      status: "checked",
      requestDelta: metrics.manual.commits.length - probe.commitBaseline,
      compositionEnd: end,
      trustedPreedit: trace.some((item) => item.isTrusted
        && ["compositionstart", "compositionupdate", "beforeinput"].includes(item.type)),
    });
    probe.pass = probe.requestDelta === 0 && end?.commitText === "" && probe.trustedPreedit;
    metrics.manual.cancelProbes.push({ inputMethod: metrics.manual.activeMethod, ...probe });
    $("#manual-status").textContent = probe.pass ? "cancel 通過" : "cancel failed；請保留本輪 evidence";
  });
  $("#clipboard-write").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("#native-source").value);
      metrics.manual.clipboard.write = { status: "passed" };
      $("#manual-status").textContent = "Unicode fixture 已寫入 clipboard";
    } catch (error) {
      metrics.manual.clipboard.write = { status: "failed", error: serializeError(error) };
    }
  });
  $("#clipboard-read").addEventListener("click", async () => {
    const before = metrics.manual.commits.length;
    try {
      const result = await clipboardAdapter.pasteFromClipboard({ userGesture: true });
      metrics.manual.clipboard.read = {
        status: "passed", commitDelta: metrics.manual.commits.length - before,
        committed: result.committed,
      };
    } catch (error) {
      metrics.manual.clipboard.read = {
        status: "failed", commitDelta: metrics.manual.commits.length - before,
        error: serializeError(error),
      };
    }
    $("#manual-status").textContent = `clipboard read ${metrics.manual.clipboard.read.status}`;
  });
  $("#copy-selection").addEventListener("click", async () => {
    try {
      metrics.manual.clipboard.copy = { status: "passed", ...await clipboardAdapter.copySelection() };
    } catch (error) {
      metrics.manual.clipboard.copy = { status: "failed", error: serializeError(error) };
    }
    $("#manual-status").textContent = `selection copy ${metrics.manual.clipboard.copy.status}`;
  });
  $("#manual-verify").addEventListener("click", async () => {
    try {
      await adapter.idle();
      metrics.manual.searches = [];
      for (const commit of metrics.manual.commits) {
        if (commit.text === "\n")
          continue;
        const result = await documentHandle.search(commit.text, { timeoutMs: 60000 });
        metrics.manual.searches.push({ text: commit.text, inputMethod: commit.inputMethod, found: result.found });
      }
      outputBuffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
      metrics.manual.output = { bytes: outputBuffer.byteLength, sha256: await sha256(outputBuffer) };
      const methods = ["chewing", "cangjie", "pinyin"];
      metrics.manual.verifiedAt = new Date().toISOString();
      metrics.manual.pass = methods.every((method) =>
        metrics.manual.commits.some((item) => item.inputMethod === method
          && item.metadata?.source === "composition"))
        && methods.every((method) => metrics.manual.cancelProbes.some((item) =>
          item.inputMethod === method && item.pass))
        && metrics.manual.searches.every((item) => item.found)
        && metrics.manual.trace.some((item) => item.type === "paste" && item.isTrusted)
        && metrics.manual.clipboard.write?.status === "passed"
        && metrics.manual.clipboard.read?.status === "passed"
        && metrics.manual.accessibility?.keyboard?.pass === true
        && metrics.manual.output.bytes > 0;
      $("#manual-evidence").value = JSON.stringify(manualSummary(), null, 2);
      $("#manual-status").textContent = metrics.manual.pass ? "集中人工驗收 pass" : "人工驗收尚有缺項";
    } catch (error) {
      $("#manual-status").textContent = `${error.code || "ERROR"}: ${error.message}`;
    }
  });
  $("#copy-evidence").addEventListener("click", async () => {
    const text = JSON.stringify(manualSummary(), null, 2);
    $("#manual-evidence").value = text;
    try {
      await navigator.clipboard.writeText(text);
      $("#manual-status").textContent = "evidence JSON 已複製";
    } catch {
      $("#manual-evidence").focus();
      $("#manual-evidence").select();
      $("#manual-status").textContent = "JSON 已全選，請按 Ctrl+C";
    }
  });
  $("#download").addEventListener("click", async () => {
    const bytes = outputBuffer || await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
    const url = URL.createObjectURL(new Blob([bytes], { type: "application/vnd.oasis.opendocument.text" }));
    const anchor = Object.assign(document.createElement("a"), { href: url, download: "r7-reference-local.odt" });
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  });
  $("#reload").addEventListener("click", () => location.reload());
  $("#keyboard-arm").addEventListener("click", () => {
    metrics.manual.accessibility = {
      focusTrace: [], keyTrace: [], armedAt: new Date().toISOString(),
      documentContentAccessibility: "unsupported",
      hyperlinkActivation: "unsupported-public-capability",
    };
    $("#manual-status").textContent = "請用 Tab／Shift+Tab 走過搜尋、頁面、縮放、輸入、下載與重新載入控制";
    $("#search").focus();
  });
  document.addEventListener("focusin", (event) => {
    if (!metrics.manual.accessibility)
      return;
    metrics.manual.accessibility.focusTrace.push({
      id: event.target.id || null,
      tag: event.target.tagName,
      atMs: performance.now(),
    });
  });
  document.addEventListener("keydown", (event) => {
    if (!metrics.manual.accessibility || !event.isTrusted)
      return;
    metrics.manual.accessibility.keyTrace.push({
      key: event.key, shiftKey: event.shiftKey, target: event.target.id || null,
    });
  }, true);
  $("#keyboard-check").addEventListener("click", () => {
    const evidence = metrics.manual.accessibility;
    if (!evidence) {
      $("#manual-status").textContent = "鍵盤記錄尚未開始";
      return;
    }
    const focused = new Set(evidence.focusTrace.map((item) => item.id));
    const required = [
      "search", "search-next", "page-next", "zoom-150",
      "manual-input", "download", "reload",
    ];
    evidence.keyboard = {
      required,
      missing: required.filter((id) => !focused.has(id)),
      trustedTab: evidence.keyTrace.some((item) => item.key === "Tab"),
      trustedShiftTab: evidence.keyTrace.some((item) => item.key === "Tab" && item.shiftKey),
    };
    evidence.keyboard.pass = evidence.keyboard.missing.length === 0
      && evidence.keyboard.trustedTab && evidence.keyboard.trustedShiftTab;
    evidence.orcaOperatorConfirmed = $("#orca-confirm").checked;
    $("#manual-status").textContent = evidence.keyboard.pass
      ? "鍵盤流程通過；Orca 確認只要求一個 browser"
      : `鍵盤流程缺少：${evidence.keyboard.missing.join(", ")}`;
  });
}

function accessibleName(element) {
  const explicit = element.getAttribute("aria-label") || element.getAttribute("title");
  if (explicit)
    return explicit.trim();
  if (element.id) {
    const label = document.querySelector(`label[for="${CSS.escape(element.id)}"]`);
    if (label)
      return label.textContent.trim();
  }
  return (element.textContent || element.value || "").trim();
}

async function runUsabilityAutomatic() {
  metrics.phase = "usability";
  $("#status").textContent = "執行 R7-D usability assertions";
  const controls = [...document.querySelectorAll(
    "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex='0']",
  )];
  const focusOrder = [];
  for (const control of controls) {
    control.focus();
    focusOrder.push({ id: control.id || null, tag: control.tagName, name: accessibleName(control), focused: document.activeElement === control });
  }
  pageNavigator.target("first");
  $("#page-next").click();
  const pageAfterOneActivation = pageNavigator.snapshot.currentPage;
  $("#page-last").click();
  const lastPage = pageNavigator.snapshot.currentPage;
  $("#zoom-150").click();
  const zoom150 = $("#surface").style.zoom;
  const search = await documentHandle.search("Final line：ODT round-trip 完整性檢查。", { timeoutMs: 60000 });
  const linkCases = [
    "https://example.test/r7", "#r7-bookmark",
    "javascript:alert(1)", "file:///etc/passwd", "macro:Run",
  ].map((target) => ({ target, result: classifyHyperlinkTarget(target) }));
  const requiredIds = [
    "page-first", "page-previous", "page-next", "page-last",
    "zoom-100", "zoom-150", "reload", "download", "search",
    "search-next", "manual-method", "manual-input",
  ];
  const required = requiredIds.map((id) => {
    const item = focusOrder.find((entry) => entry.id === id);
    return { id, present: Boolean(item), name: item?.name || "", focused: item?.focused === true };
  });
  const status = $("#status");
  const locationHint = $("#location").textContent;
  const result = {
    synthetic: true,
    controls: focusOrder,
    required,
    status: {
      role: status.getAttribute("role"),
      live: status.getAttribute("aria-live"),
      text: status.textContent,
    },
    page: { pageAfterOneActivation, lastPage, locationHint },
    zoom150,
    search: { found: search.found, geometryPolicy: "selection-only-no-scroll-geometry" },
    hyperlinks: linkCases,
    documentContentAccessibility: "unsupported",
    pass: required.every((item) => item.present && item.focused && item.name)
      && status.getAttribute("role") === "status"
      && status.getAttribute("aria-live") === "polite"
      && pageAfterOneActivation === 2
      && lastPage === pageNavigator.pageCount
      && locationHint.startsWith("頁面位置提示：")
      && zoom150 === "1.5"
      && search.found
      && linkCases.slice(0, 2).every((item) => item.result.supported)
      && linkCases.slice(2).every((item) => !item.result.supported),
  };
  metrics.usability = result;
  metrics.pass = result.pass;
  metrics.phase = "complete";
  $("#status").textContent = result.pass ? "R7-D usability automatic pass" : "R7-D usability automatic failed";
}

async function main() {
  try {
    await loadFixture();
    await openDocument();
    bindControls();
    if (automatic) {
      await runAutomatic();
      await documentHandle.close({ timeoutMs: 180000 });
      engine.dispose();
      metrics.complete = true;
    } else {
      ({ input: adapter, clipboard: clipboardAdapter } = createAdapters(metrics.manual, $("#manual-input")));
      if (usabilityMode) {
        await runUsabilityAutomatic();
        await documentHandle.close({ timeoutMs: 180000 });
        engine.dispose();
        metrics.complete = true;
      } else {
        metrics.phase = "manual-ready";
        $("#status").textContent = "manual ready";
        $("#next-action").textContent = "依序完成三種輸入法與 clipboard";
      }
    }
  } catch (error) {
    metrics.error = serializeError(error);
    metrics.phase = "error";
    metrics.complete = true;
    $("#status").textContent = `error: ${metrics.error.code}`;
    $("#message").textContent = metrics.error.message;
    log(metrics.error);
  }
}

main();
