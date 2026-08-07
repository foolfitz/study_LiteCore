const params = new URLSearchParams(location.search);
const mode = params.get("mode") || "inert";
const bufferMib = Number(params.get("bufferMib") || 0);
// The engine is linked -sPTHREAD_POOL_SIZE=7 -sTOTAL_MEMORY=1GB, so one
// navigation of the real harness costs 1 SDK worker + 7 pthread-pool workers
// sharing a 1 GB SharedArrayBuffer.  The single-worker/256 MiB rungs do NOT
// cover that shape; this one does, without any LibreOffice code.
const poolWorkers = Number(params.get("poolWorkers") || 0);
// keepAlive mirrors the real harness's teardown path: the engine worker is
// never terminated explicitly -- navigation kills it.  The plain rungs
// terminate explicitly, which is a different cleanup path in both browsers.
const keepAlive = params.get("keepAlive") === "1";

const metrics = {
  schemaVersion: 1,
  release: "E1-C-session-depth-control",
  mode,
  bufferMib,
  poolWorkers,
  crossOriginIsolated: globalThis.crossOriginIsolated === true,
  workers: { created: 0, terminated: 0, intentionalCrashes: 0 },
  operations: [],
  complete: false,
  pass: false,
  error: null,
};

// The chrome driver gates navigate() on this global, exactly as it does for the
// real harness.  Setting it here keeps the two loops measuring the same thing.
globalThis.__probe_metrics = metrics;
globalThis.__e1_c = metrics;

function log(entry) {
  document.querySelector("#log").textContent +=
    `${JSON.stringify(entry)}\n`;
}

function runWorker() {
  return new Promise((resolve, reject) => {
    const worker = new Worker("./e1-c-session-depth-worker.js", { type: "module" });
    metrics.workers.created += 1;
    const timer = setTimeout(() => {
      worker.terminate();
      reject(new Error("control worker did not answer within 120000 ms"));
    }, 120000);
    worker.onmessage = (event) => {
      clearTimeout(timer);
      if (!keepAlive) {
        worker.terminate();
        metrics.workers.terminated += 1;
      }
      resolve(event.data);
    };
    worker.onerror = (event) => {
      clearTimeout(timer);
      worker.terminate();
      metrics.workers.terminated += 1;
      reject(new Error(event.message || "control worker failed"));
    };
    worker.postMessage({
      bufferMib: mode === "buffer" ? bufferMib : 0,
      // 16 KiB wasm pages per MiB: a shared WebAssembly.Memory of the same
      // size the engine links with (-sTOTAL_MEMORY=1GB => 16384 pages).
      wasmMemPages: mode === "wasmmem" ? bufferMib * 16 : 0,
      compilePath: mode === "compile"
        ? (params.get("compilePath") || "./profiles/e1-editor-v1/probe.wasm")
        : null,
    });
  });
}

/**
 * The engine's shape without the engine: one SharedArrayBuffer shared by a pool
 * of workers, all created and torn down within a single navigation.
 */
async function runPool() {
  const shared = new SharedArrayBuffer(bufferMib * 1024 * 1024);
  new Uint8Array(shared, 0, 1)[0] = 1;
  const workers = [];
  try {
    const answers = await Promise.all(
      Array.from({ length: poolWorkers }, () => new Promise((resolve, reject) => {
        const worker = new Worker("./e1-c-session-depth-worker.js", { type: "module" });
        workers.push(worker);
        metrics.workers.created += 1;
        const timer = setTimeout(
          () => reject(new Error("pool worker did not answer within 120000 ms")),
          120000,
        );
        worker.onmessage = (event) => { clearTimeout(timer); resolve(event.data); };
        worker.onerror = (event) => {
          clearTimeout(timer);
          reject(new Error(event.message || "pool worker failed"));
        };
        worker.postMessage({ shared });
      })),
    );
    return {
      workers: answers.length,
      bufferBytes: shared.byteLength,
      touched: answers.filter((item) => item.touchedShared).length,
    };
  } finally {
    if (!keepAlive) {
      for (const worker of workers) {
        worker.terminate();
        metrics.workers.terminated += 1;
      }
    }
  }
}

/**
 * The engine's load path without (or with) the engine binary: a CLASSIC worker
 * that importScripts an emscripten glue and awaits createProbeModule, exactly
 * as sdk-worker.js does.  Deliberately NOT terminated on success: the real
 * harness leaves the engine worker (and its 7 nested pthread-pool workers)
 * alive until navigation tears the document down, and if the wedge lives in
 * that teardown an explicit terminate() here would wash the evidence away.
 */
function runEngineShapeWorker(request) {
  return new Promise((resolve, reject) => {
    const worker = new Worker("./e1-c-session-depth-engine-worker.js");
    metrics.workers.created += 1;
    const timer = setTimeout(() => {
      reject(new Error("engine-shape worker did not answer within 120000 ms"));
    }, 120000);
    worker.onmessage = (event) => {
      clearTimeout(timer);
      const answer = event.data || {};
      if (answer.ready === true)
        resolve(answer);
      else
        reject(new Error(answer.error || "engine-shape worker failed"));
    };
    worker.onerror = (event) => {
      clearTimeout(timer);
      reject(new Error(event.message || "engine-shape worker failed"));
    };
    worker.postMessage(request);
  });
}

async function main() {
  try {
    if (mode === "inert") {
      metrics.operations.push({ name: "inert", status: "passed" });
    } else if (mode === "worker" || mode === "buffer" || mode === "wasmmem"
        || mode === "compile") {
      const answer = await runWorker();
      metrics.operations.push({ name: mode, status: "passed", result: answer });
    } else if (mode === "pool") {
      const answer = await runPool();
      metrics.operations.push({ name: mode, status: "passed", result: answer });
    } else if (mode === "enginestart") {
      // The real SDK init chain -- sdk-worker.js, manifest, module, startup
      // resource packs, oxsdk_engine_start -- with no document ever opened.
      // Imported dynamically so the lower rungs keep depending on no SDK.
      const { createDocumentEngine } = await import("./sdk/document-sdk.js");
      metrics.workers.created += 1;
      const engine = await createDocumentEngine({
        workerUrl: "./profiles/e1-editor-v1/sdk-worker.js",
        timeoutMs: 30000,
      });
      // Deliberately no dispose(): the real harness leaves the engine worker
      // alive until navigation tears the document down.
      metrics.operations.push({
        name: mode,
        status: "passed",
        result: {
          ready: true,
          abiVersion: engine.manifest?.abiVersion,
          capabilityBits: engine.manifest?.capabilityBits,
          profile: engine.manifest?.profile,
        },
      });
    } else if (mode === "minimal" || mode === "realinstant") {
      const answer = await runEngineShapeWorker(mode === "minimal"
        ? { gluePath: "./e1-c-minimal/minimal.js", pingExport: "oxsdk_minimal_ping" }
        : {
          manifestPath: "./profiles/e1-editor-v1/sdk-manifest.json",
          pingExport: "oxsdk_abi_version",
        });
      metrics.operations.push({ name: mode, status: "passed", result: answer });
    } else {
      throw new Error(`unknown mode: ${mode}`);
    }
    metrics.pass = true;
  } catch (error) {
    metrics.error = { name: error.name, message: error.message };
    metrics.pass = false;
  } finally {
    metrics.complete = true;
    log({ mode, pass: metrics.pass, workers: metrics.workers });
  }
}

main();
