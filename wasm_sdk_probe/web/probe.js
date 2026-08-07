(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const elements = {
    file: $("file"),
    canvas: $("canvas"),
    log: $("log"),
    status: $("status"),
    download: $("download"),
    clickX: $("click-x"),
    clickY: $("click-y"),
    tileSize: $("tile-size"),
  };

  const metrics = {
    schema_version: 1,
    page_load_epoch_ms: performance.timeOrigin,
    user_agent: navigator.userAgent,
    cross_origin_isolated: globalThis.crossOriginIsolated,
    t_ready_ms: null,
    runs: [],
    memory: [],
  };
  globalThis.__probe_metrics = metrics;
  globalThis.__probe_get_output_base64 = () => {
    if (!module)
      throw new Error("WASM module is not ready");
    const bytes = module.FS.readFile("/tmp/out.odt");
    let binary = "";
    const chunkSize = 0x8000;
    for (let offset = 0; offset < bytes.length; offset += chunkSize)
      binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
    return btoa(binary);
  };

  let module = null;
  let ready = false;
  let viewReady = false;
  let outputBlob = null;
  let outputObjectUrl = null;
  let waiters = [];

  function setStatus(message) {
    elements.status.textContent = message;
  }

  function appendLog(message) {
    const timestamp = performance.now().toFixed(1).padStart(9);
    elements.log.textContent += `[${timestamp} ms] ${message}\n`;
    elements.log.scrollTop = elements.log.scrollHeight;
  }

  function waitForEvent(predicate, description, timeoutMs = 180000) {
    return new Promise((resolve, reject) => {
      const waiter = { predicate, resolve, reject, description, timer: 0 };
      waiter.timer = setTimeout(() => {
        waiters = waiters.filter((candidate) => candidate !== waiter);
        reject(new Error(`timed out waiting for ${description}`));
      }, timeoutMs);
      waiters.push(waiter);
    });
  }

  function resolveWaiters(event) {
    const pending = waiters;
    waiters = [];
    for (const waiter of pending) {
      if (waiter.predicate(event)) {
        clearTimeout(waiter.timer);
        waiter.resolve(event);
      } else {
        waiters.push(waiter);
      }
    }
  }

  function rejectWaiters(event) {
    const error = new Error(`${event.where}: ${event.msg}`);
    for (const waiter of waiters) {
      clearTimeout(waiter.timer);
      waiter.reject(error);
    }
    waiters = [];
  }

  function drawTile(event) {
    const expectedSize = event.w * event.h * 4;
    if (!module || event.size !== expectedSize)
      throw new Error(`invalid tile payload: expected ${expectedSize}, got ${event.size}`);

    const heapView = new Uint8ClampedArray(module.HEAPU8.buffer, event.ptr, event.size);
    const copiedPixels = new Uint8ClampedArray(heapView);
    module.ccall("probe_free", null, ["number"], [event.ptr]);

    elements.canvas.width = event.w;
    elements.canvas.height = event.h;
    const context = elements.canvas.getContext("2d");
    context.putImageData(new ImageData(copiedPixels, event.w, event.h), 0, 0);
  }

  globalThis.__probe_on_event = (rawEvent) => {
    appendLog(rawEvent);
    let event;
    try {
      event = JSON.parse(rawEvent);
      event.__receivedAt = performance.now();
      if (event.type === "tile")
        drawTile(event);
      if (event.type === "stage" && event.name === "open.begin")
        viewReady = false;
      if (event.type === "lok" && event.id === 70
          && event.payload.includes("afterCallbackRegistered invoked"))
        viewReady = true;
      if (event.type === "ready") {
        ready = true;
        if (metrics.t_ready_ms === null)
          metrics.t_ready_ms = event.__receivedAt;
        setStatus("ready");
      } else if (event.type === "error") {
        setStatus(`error: ${event.where}`);
        rejectWaiters(event);
        return;
      } else {
        setStatus(event.type);
      }
      resolveWaiters(event);
    } catch (error) {
      appendLog(`event handling error: ${error.stack || error}`);
      setStatus("event handling error");
    }
  };

  const modulePromise = createProbeModule({
    print: (text) => appendLog(`[stdout] ${text}`),
    printErr: (text) => appendLog(`[stderr] ${text}`),
    locateFile: (path) => path,
  }).then((createdModule) => {
    module = createdModule;
    setStatus("module loaded; starting engine");
    const eventPromise = waitForEvent((event) => event.type === "ready", "ready");
    module.ccall("probe_start", null, [], []);
    return eventPromise.then(() => module);
  }).catch((error) => {
    appendLog(`module initialization failed: ${error.stack || error}`);
    setStatus("module initialization failed");
    throw error;
  });

  async function getModule() {
    return modulePromise;
  }

  function requireInputFile() {
    const [file] = elements.file.files;
    if (!file)
      throw new Error("請先選擇一份 ODT 文件");
    return file;
  }

  async function writeInputFile() {
    const file = requireInputFile();
    const instance = await getModule();
    const bytes = new Uint8Array(await file.arrayBuffer());
    instance.FS.writeFile("/tmp/in.odt", bytes);
    const stored = instance.FS.stat("/tmp/in.odt");
    appendLog(`MEMFS /tmp/in.odt: input=${bytes.byteLength}, stored=${stored.size}, wasmHeap=${instance.HEAPU8.byteLength}`);
    return file;
  }

  function call(name, returnType = null, argumentTypes = [], argumentsList = []) {
    if (!module)
      throw new Error("WASM module is not ready");
    module.ccall(name, returnType, argumentTypes, argumentsList);
  }

  async function commandAndWait(name, argumentTypes, argumentsList, predicate, description) {
    await getModule();
    const startedAt = performance.now();
    const eventPromise = waitForEvent(predicate, description);
    call(name, null, argumentTypes, argumentsList);
    const event = await eventPromise;
    return { event, elapsedMs: event.__receivedAt - startedAt };
  }

  async function startProbe() {
    await getModule();
    if (ready)
      return;
    await commandAndWait("probe_start", [], [], (event) => event.type === "ready", "ready");
  }

  async function openDocument() {
    await writeInputFile();
    return commandAndWait(
      "probe_open", ["string"], ["file:///tmp/in.odt"],
      (event) => event.type === "opened", "opened");
  }

  async function paintDocument() {
    const tileSize = Number(elements.tileSize.value);
    return commandAndWait(
      "probe_paint_tile",
      ["number", "number", "number", "number", "number", "number"],
      [0, 0, tileSize, tileSize, 512, 512],
      (event) => event.type === "tile", "tile");
  }

  async function waitForViewReady() {
    if (viewReady)
      return;
    await waitForEvent(
      (event) => event.type === "lok" && event.id === 70
        && event.payload.includes("afterCallbackRegistered invoked"),
      "Writer view callback registration", 10000);
  }

  async function clickDocument() {
    await waitForViewReady();
    return commandAndWait(
      "probe_click", ["number", "number"],
      [Number(elements.clickX.value), Number(elements.clickY.value)],
      (event) => event.type === "clicked", "clicked");
  }

  async function insertText() {
    await getModule();
    await waitForViewReady();
    const startedAt = performance.now();
    const insertedPromise = waitForEvent(
      (event) => event.type === "inserted", "inserted");
    const invalidatePromise = waitForEvent(
      (event) => event.type === "lok" && (event.id === 0 || event.id === 1),
      "tile or visible-cursor invalidation after insert");
    call("probe_insert_text", null, ["string"], ["測"]);
    const [inserted, invalidate] = await Promise.all([insertedPromise, invalidatePromise]);
    return {
      event: inserted,
      invalidate,
      elapsedMs: invalidate.__receivedAt - startedAt,
    };
  }

  async function saveDocument() {
    try {
      module.FS.unlink("/tmp/out.odt");
    } catch (error) {
      if (!String(error).includes("No such file"))
        appendLog(`unlink old output: ${error}`);
    }

    const result = await commandAndWait(
      "probe_save", ["string"], ["odt"],
      (event) => event.type === "saved", "saved");
    const output = module.FS.readFile("/tmp/out.odt");
    outputBlob = new Blob([output], { type: "application/vnd.oasis.opendocument.text" });
    if (outputObjectUrl)
      URL.revokeObjectURL(outputObjectUrl);
    outputObjectUrl = URL.createObjectURL(outputBlob);
    elements.download.disabled = false;
    return result;
  }

  async function closeDocument() {
    return commandAndWait(
      "probe_close", [], [], (event) => event.type === "closed", "closed");
  }

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
      const measurement = await performance.measureUserAgentSpecificMemory();
      metrics.memory.push({
        phase,
        run_index: runIndex,
        browser: navigator.userAgent,
        bytes: measurement.bytes,
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
    const file = requireInputFile();
    await getModule();
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
      pass: false,
    };
    const runIndex = metrics.runs.length;
    metrics.runs.push(run);

    setStatus("run all: preparing");
    await writeInputFile();
    await measureMemory("before-open", runIndex);

    setStatus("run all: opening");
    run.t_open_ms = (await commandAndWait(
      "probe_open", ["string"], ["file:///tmp/in.odt"],
      (event) => event.type === "opened", "opened")).elapsedMs;
    await measureMemory("after-open", runIndex);

    setStatus("run all: painting");
    run.t_first_tile_ms = (await paintDocument()).elapsedMs;
    await measureMemory("after-paint", runIndex);

    setStatus("run all: clicking");
    await clickDocument();

    setStatus("run all: inserting");
    const insert = await insertText();
    run.t_insert_ms = insert.elapsedMs;
    run.insert_method = insert.event.method;

    setStatus("run all: repainting");
    await paintDocument();

    setStatus("run all: saving");
    run.t_save_ms = (await saveDocument()).elapsedMs;
    await measureMemory("after-save", runIndex);
    run.pass = true;
    setStatus("run all: complete");
    appendLog(`[metrics] ${JSON.stringify(run)}`);
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

  $("start").addEventListener("click", guard(startProbe));
  $("open").addEventListener("click", guard(openDocument));
  $("paint").addEventListener("click", guard(paintDocument));
  $("click").addEventListener("click", guard(clickDocument));
  $("insert").addEventListener("click", guard(insertText));
  $("save").addEventListener("click", guard(saveDocument));
  $("close").addEventListener("click", guard(closeDocument));
  $("run-all").addEventListener("click", guard(runAll));

  elements.download.addEventListener("click", () => {
    if (!outputBlob || !outputObjectUrl)
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
})();
