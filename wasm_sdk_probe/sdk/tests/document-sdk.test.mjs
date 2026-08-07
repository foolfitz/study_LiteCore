import assert from "node:assert/strict";
import test from "node:test";

import {
  DocumentClosedError,
  DocumentSdkError,
  SdkAbortError,
  SdkTimeoutError,
  StaleDocumentError,
  StaleRevisionError,
  WorkerCrashedError,
  createDocumentEngine,
} from "../document-sdk.js";

const manifest = {
  sdkVersion: "0.4.0-r4",
  protocolVersion: 1,
  abiVersion: 65537,
  abiVersionText: "1.1",
  providerContractVersion: "1.0",
  coreCommit: "test",
  profile: "test",
  capabilities: ["open-odt"],
  capabilityBits: 31,
};

class FakeWorker {
  constructor(handler) {
    this.handler = handler;
    this.listeners = new Map();
    this.messages = [];
    this.terminated = false;
  }

  addEventListener(type, listener) {
    const listeners = this.listeners.get(type) || [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  postMessage(message, transfer = []) {
    if (this.terminated)
      throw new Error("worker is terminated");
    this.messages.push({ message, transfer });
    queueMicrotask(() => this.handler?.(this, message, transfer));
  }

  terminate() {
    this.terminated = true;
  }

  emit(type, value) {
    for (const listener of this.listeners.get(type) || [])
      listener(type === "message" ? { data: value } : value);
  }

  respond(request, result) {
    this.emit("message", {
      protocolVersion: 1,
      kind: "response",
      requestId: request.requestId,
      ok: true,
      result,
    });
  }

  fail(request, code, message) {
    this.emit("message", {
      protocolVersion: 1,
      kind: "response",
      requestId: request.requestId,
      ok: false,
      error: { code, message },
    });
  }
}

function standardHandler(worker, message) {
  if (message.kind !== "request")
    return;
  switch (message.operation) {
    case "init": worker.respond(message, manifest); break;
    case "open":
      worker.respond(message, {
        documentHandle: 41,
        revision: 0,
        parts: 1,
        width: 1000,
        height: 2000,
        tileMode: 0,
      });
      break;
    case "paint":
      worker.respond(message, {
        pixels: new ArrayBuffer(16), width: 2, height: 2, revision: 0,
      });
      break;
    case "click": worker.respond(message, { revision: 0 }); break;
    case "insertText": worker.respond(message, { method: "paste", revision: 1 }); break;
    case "search":
      worker.respond(message, {
        found: true,
        query: message.payload.query,
        selections: [{ part: "0", rectangles: "1, 2, 3, 4" }],
        revision: 0,
      });
      break;
    case "getSelection":
      worker.respond(message, {
        selectionType: "text",
        text: "LibreOfficeKit",
        mimeType: "text/plain;charset=utf-8",
        revision: 0,
      });
      break;
    case "replaceSelection": worker.respond(message, { revision: 1 }); break;
    case "undo": worker.respond(message, { revision: 2 }); break;
    case "addComment": worker.respond(message, { revision: 3 }); break;
    case "listComments":
      worker.respond(message, { comments: [{ text: "R3 review" }], revision: 3 });
      break;
    case "setTrackChanges": worker.respond(message, { revision: 4 }); break;
    case "listTrackedChanges":
      worker.respond(message, { changes: [{ type: "Insert" }], revision: 5 });
      break;
    case "save": worker.respond(message, { buffer: new ArrayBuffer(8), revision: 1 }); break;
    case "close": worker.respond(message, { documentHandle: 41 }); break;
  }
}

function factoryWith(handler = standardHandler) {
  const workers = [];
  return {
    workers,
    factory() {
      const worker = new FakeWorker(handler);
      workers.push(worker);
      return worker;
    },
  };
}

async function makeEngine(setup, options = {}) {
  return createDocumentEngine({
    workerUrl: "https://example.test/sdk-worker.js",
    workerFactory: setup.factory,
    timeoutMs: 100,
    ...options,
  });
}

test("version handshake and request correlation expose no runtime internals", async () => {
  const setup = factoryWith();
  const engine = await makeEngine(setup);
  assert.equal(engine.manifest.abiVersion, 65537);
  assert.equal("FS" in engine, false);
  assert.equal("HEAPU8" in engine, false);
  assert.equal("module" in engine, false);

  const document = await engine.open(new ArrayBuffer(32));
  const [first, second] = await Promise.all([
    document.render({ canvasWidthPx: 2, canvasHeightPx: 2 }),
    document.render({ canvasWidthPx: 2, canvasHeightPx: 2 }),
  ]);
  assert.equal(first.pixels.byteLength, 16);
  assert.equal(second.pixels.byteLength, 16);
  engine.dispose();
});

test("open makes transfer ownership explicit and close is idempotent", async () => {
  const setup = factoryWith();
  const engine = await makeEngine(setup);
  const worker = setup.workers[0];

  const preserved = new ArrayBuffer(32);
  const first = await engine.open(preserved, { transfer: false });
  const firstOpen = worker.messages.find((entry) => entry.message.operation === "open");
  assert.notEqual(firstOpen.transfer[0], preserved);
  assert.equal(firstOpen.transfer[0], firstOpen.message.payload.buffer);

  await first.close();
  await first.close();
  assert.equal(worker.messages.filter((entry) => entry.message.operation === "close").length, 1);
  await assert.rejects(() => first.render(), DocumentClosedError);

  const consumed = new ArrayBuffer(64);
  await engine.open(consumed, { transfer: true });
  const opens = worker.messages.filter((entry) => entry.message.operation === "open");
  assert.equal(opens.at(-1).transfer[0], consumed);
  engine.dispose();
});

test("close timeout recycles the owning Worker and keeps the engine reusable", async () => {
  const recoveryEvents = [];
  const setup = factoryWith((worker, message, transfer) => {
    if (message.operation === "close" && setup.workers.indexOf(worker) === 0)
      return;
    standardHandler(worker, message, transfer);
  });
  const engine = await makeEngine(setup, { closeRecoveryTimeoutMs: 5 });
  engine.onEvent((event) => {
    if (event.event.startsWith("document-close-recovery"))
      recoveryEvents.push(event);
  });
  const document = await engine.open(new ArrayBuffer(32));

  await document.close({ timeoutMs: 1000 });

  assert.equal(setup.workers.length, 2);
  assert.equal(setup.workers[0].terminated, true);
  assert.deepEqual(
    recoveryEvents.map((event) => event.event),
    ["document-close-recovery-started", "document-close-recovery-complete"],
  );
  assert.equal(recoveryEvents[1].detail.strategy, "worker-restart");
  await assert.rejects(() => document.render(), DocumentClosedError);

  const reopened = await engine.open(new ArrayBuffer(32));
  assert.equal(reopened.handle, 41);
  await reopened.close();
  engine.dispose();
});

test("aborted close remains a typed failure and does not claim recovery", async () => {
  const recoveryEvents = [];
  const setup = factoryWith((worker, message, transfer) => {
    if (message.operation !== "close")
      standardHandler(worker, message, transfer);
  });
  const engine = await makeEngine(setup, { closeRecoveryTimeoutMs: 1000 });
  engine.onEvent((event) => {
    if (event.event.startsWith("document-close-recovery"))
      recoveryEvents.push(event);
  });
  const document = await engine.open(new ArrayBuffer(32));
  const controller = new AbortController();
  const closing = document.close({ signal: controller.signal, timeoutMs: 1000 });
  controller.abort();

  await assert.rejects(
    () => closing,
    (error) => error instanceof SdkAbortError && error.code === "ABORTED",
  );
  assert.equal(setup.workers.length, 1);
  assert.deepEqual(recoveryEvents, []);
  engine.dispose();
});

test("timeout rejects and emits a best-effort cancel", async () => {
  const setup = factoryWith((worker, message, transfer) => {
    if (message.operation !== "paint")
      standardHandler(worker, message, transfer);
  });
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(16));
  await assert.rejects(
    () => document.render({}, { timeoutMs: 5 }),
    (error) => error instanceof SdkTimeoutError && error.code === "TIMEOUT",
  );
  const cancel = setup.workers[0].messages.find((entry) => entry.message.kind === "cancel");
  assert.ok(cancel);
  engine.dispose();
});

test("AbortSignal rejects and emits cancel", async () => {
  const setup = factoryWith((worker, message, transfer) => {
    if (message.operation !== "paint")
      standardHandler(worker, message, transfer);
  });
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(16));
  const controller = new AbortController();
  const rendering = document.render({}, { signal: controller.signal, timeoutMs: 1000 });
  controller.abort();
  await assert.rejects(
    () => rendering,
    (error) => error instanceof SdkAbortError && error.name === "AbortError",
  );
  assert.ok(setup.workers[0].messages.some((entry) => entry.message.kind === "cancel"));
  engine.dispose();
});

test("worker crash rejects pending work and restart invalidates old handles", async () => {
  const setup = factoryWith((worker, message, transfer) => {
    if (message.operation !== "paint")
      standardHandler(worker, message, transfer);
  });
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(16));
  const rendering = document.render({}, { timeoutMs: 1000 });
  setup.workers[0].emit("error", { message: "simulated worker crash" });
  await assert.rejects(
    () => rendering,
    (error) => error instanceof WorkerCrashedError && error.code === "WORKER_CRASHED",
  );

  await engine.restart();
  assert.equal(setup.workers.length, 2);
  await assert.rejects(
    () => document.render(),
    (error) => error instanceof StaleDocumentError && error.code === "STALE_DOCUMENT",
  );
  engine.dispose();
});

test("protocol mismatch is treated as a worker crash", async () => {
  const setup = factoryWith((worker, message) => {
    worker.emit("message", {
      protocolVersion: 99,
      kind: "response",
      requestId: message.requestId,
      ok: true,
      result: manifest,
    });
  });
  await assert.rejects(
    () => makeEngine(setup),
    (error) => error instanceof WorkerCrashedError,
  );
});

test("R3 semantic review operations propagate monotonic revisions", async () => {
  const setup = factoryWith();
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(32));

  const match = await document.search("LibreOfficeKit");
  assert.equal(match.found, true);
  assert.equal(match.selections.length, 1);
  const selection = await document.getSelection();
  assert.equal(selection.text, "LibreOfficeKit");

  await document.replaceSelection("LOK", { expectedRevision: 0 });
  assert.equal(document.revision, 1);
  await document.undo({ expectedRevision: 1 });
  assert.equal(document.revision, 2);
  await document.addComment("R3 review", {
    author: "OxOffice SDK",
    expectedRevision: 2,
  });
  assert.equal((await document.listComments()).comments.length, 1);
  await document.setTrackChanges(true, { expectedRevision: 3 });
  assert.equal(document.revision, 4);
  assert.equal((await document.listTrackedChanges()).changes.length, 1);
  engine.dispose();
});

test("R3 stale revision is a typed error with current revision details", async () => {
  const setup = factoryWith((worker, message, transfer) => {
    if (message.operation === "replaceSelection") {
      worker.fail(message, "STALE_REVISION", "expected revision 0 but current is 2");
      return;
    }
    standardHandler(worker, message, transfer);
  });
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(16));
  await assert.rejects(
    () => document.replaceSelection("new", { expectedRevision: 0 }),
    (error) => error instanceof StaleRevisionError
               && error.code === "STALE_REVISION"
               && error.details.operation === "replaceSelection",
  );
  engine.dispose();
});

test("unsupported profile operations remain typed SDK errors", async () => {
  const setup = factoryWith((worker, message, transfer) => {
    if (message.operation === "replaceSelection") {
      worker.fail(message, "UNSUPPORTED_OPERATION", "not available in reader profile");
      return;
    }
    standardHandler(worker, message, transfer);
  });
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(16));
  await assert.rejects(
    () => document.replaceSelection("blocked"),
    (error) => error instanceof DocumentSdkError
               && error.code === "UNSUPPORTED_OPERATION"
               && error.details.operation === "replaceSelection",
  );
  engine.dispose();
});

function selectionHandler(result) {
  return (worker, message, transfer) => {
    if (message.operation === "getSelection") {
      worker.respond(message, {
        mimeType: "text/plain;charset=utf-8",
        revision: 0,
        ...result,
      });
      return;
    }
    standardHandler(worker, message, transfer);
  };
}

test("an empty selection reads back as a success, not a LOK error", async () => {
  // Finding 017: a collapsed caret has no plain-text flavor, so the old
  // getTextSelection() readback returned null and was reported as LOK_ERROR
  // ("Flavor text/plain;charset=utf-16 is not supported"). A caret is a normal
  // state and must resolve.
  const setup = factoryWith(selectionHandler({ selectionType: "none", text: "" }));
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(16));

  const selection = await document.getSelection();
  assert.equal(selection.selectionType, "none");
  assert.equal(selection.text, "");
  engine.dispose();
});

test("a complex selection is never reported as an empty selection", async () => {
  const setup = factoryWith(selectionHandler({ selectionType: "complex", text: "" }));
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(16));

  const selection = await document.getSelection();
  assert.equal(selection.selectionType, "complex");
  // Same empty text as the "none" case, so callers must branch on the type.
  assert.equal(selection.text, "");
  assert.notEqual(selection.selectionType, "none");
  engine.dispose();
});

test("a text selection still carries its text", async () => {
  const setup = factoryWith();
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(16));

  const selection = await document.getSelection();
  assert.equal(selection.selectionType, "text");
  assert.equal(selection.text, "LibreOfficeKit");
  engine.dispose();
});

test("a typed readback failure stays a typed error", async () => {
  // LOK_SELTYPE_TEXT promises text; a missing string is a real failure and
  // must not be smoothed into an empty selection.
  const setup = factoryWith((worker, message, transfer) => {
    if (message.operation === "getSelection") {
      worker.fail(message, "LOK_ERROR",
                  "selection type is text but no utf-8 text was returned");
      return;
    }
    standardHandler(worker, message, transfer);
  });
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(16));
  await assert.rejects(
    () => document.getSelection(),
    (error) => error instanceof DocumentSdkError && error.code === "LOK_ERROR",
  );
  engine.dispose();
});

test("a missing selection type never surfaces as an empty selection", async () => {
  // An engine predating the selection-type readback emits no selectionType.
  // Reporting that as "none" would let a collapsed-caret precondition pass
  // while a selection is still live, so it must not equal "none" at any layer.
  //
  // This harness mocks the worker boundary, so it covers document-sdk.js only.
  // The `|| "unknown"` default in sdk-worker.js sits below this mock and is
  // exercised by the headed browser run, not here.
  const setup = factoryWith(selectionHandler({ text: "still selected" }));
  const engine = await makeEngine(setup);
  const document = await engine.open(new ArrayBuffer(16));

  const selection = await document.getSelection();
  assert.notEqual(selection.selectionType, "none");
  engine.dispose();
});
