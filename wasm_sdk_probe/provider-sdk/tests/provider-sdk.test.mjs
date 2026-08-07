import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  ProviderAbortError,
  ProviderHost,
  ProviderRegistry,
  ProviderSdkError,
  ProviderWorkerCrashedError,
  WorkerProviderAdapter,
  createDesktopDocumentAdapter,
  createInProcessProviderAdapter,
  createWebDocumentAdapter,
  validateProviderDescriptor,
} from "../provider-sdk.js";
import provider from "../../providers/text-translate-provider.js";
import { descriptor } from "../../providers/text-translate-descriptor.js";

const fixture = JSON.parse(await readFile(
  new URL("../fixtures/text-translate.json", import.meta.url),
  "utf8",
));

function makeDocumentBinding(binding) {
  const state = {
    text: fixture.input.text,
    revision: fixture.input.revision,
    replacements: [],
  };
  const readSelection = async () => ({ text: state.text, revision: state.revision });
  const replaceSelection = async (text, options) => {
    if (options.expectedRevision !== state.revision) {
      const error = new Error("stale revision");
      error.code = "STALE_REVISION";
      throw error;
    }
    state.text = text;
    state.revision += 1;
    state.replacements.push({ text, expectedRevision: options.expectedRevision });
    return { revision: state.revision };
  };
  const adapter = binding === "web"
    ? createWebDocumentAdapter({ getSelection: readSelection, replaceSelection })
    : createDesktopDocumentAdapter({ readSelection, replaceSelection });
  return { state, adapter };
}

function makeHost(providerImplementation = provider, options = {}) {
  const registry = new ProviderRegistry();
  registry.register(descriptor, createInProcessProviderAdapter(providerImplementation));
  return {
    registry,
    host: new ProviderHost({ registry, ...options }),
  };
}

test("R4 descriptor registration is closed, immutable, and discoverable", () => {
  assert.deepEqual(descriptor, fixture.provider);
  const normalized = validateProviderDescriptor(fixture.provider);
  assert.ok(Object.isFrozen(normalized));
  assert.ok(Object.isFrozen(normalized.endpoints[0]));

  const registry = new ProviderRegistry();
  registry.register(fixture.provider, createInProcessProviderAdapter(provider));
  assert.deepEqual(registry.listProviders(), [fixture.provider]);
  assert.throws(
    () => registry.register(fixture.provider, createInProcessProviderAdapter(provider)),
    (error) => error instanceof ProviderSdkError && error.code === "DUPLICATE_PROVIDER",
  );
  assert.throws(
    () => validateProviderDescriptor({ ...fixture.provider, capabilities: ["raw.uno"] }),
    (error) => error instanceof ProviderSdkError && error.code === "INVALID_DESCRIPTOR",
  );
  registry.dispose();
});

test("the same domain fixture produces the same operation through Web and desktop adapters", async () => {
  const { host, registry } = makeHost();
  const web = makeDocumentBinding("web");
  const desktop = makeDocumentBinding("desktop");
  const webProgress = [];
  const desktopProgress = [];

  const webResult = await host.invokeSelection({
    providerId: descriptor.id,
    endpointId: fixture.endpointId,
    documentAdapter: web.adapter,
    parameters: fixture.input.parameters,
    onProgress: (progress) => webProgress.push(progress),
  });
  const desktopResult = await host.invokeSelection({
    providerId: descriptor.id,
    endpointId: fixture.endpointId,
    documentAdapter: desktop.adapter,
    parameters: fixture.input.parameters,
    onProgress: (progress) => desktopProgress.push(progress),
  });

  assert.deepEqual(webResult.operation, fixture.expectedOperation);
  assert.deepEqual(desktopResult.operation, fixture.expectedOperation);
  assert.deepEqual(webResult.operation, desktopResult.operation);
  assert.equal(web.state.text, fixture.expectedOperation.text);
  assert.equal(desktop.state.text, fixture.expectedOperation.text);
  assert.equal(web.state.replacements.length, 1);
  assert.equal(desktop.state.replacements.length, 1);
  assert.deepEqual(webProgress.map((item) => item.fraction), [0.25, 0.75, 1]);
  assert.deepEqual(desktopProgress, webProgress);
  registry.dispose();
});

test("Provider receives an immutable snapshot and no document mutation surface", async () => {
  let observed = null;
  let mutationRejected = false;
  const implementation = {
    async invoke(invocation, context) {
      observed = {
        invocationKeys: Object.keys(invocation).sort(),
        contextKeys: Object.keys(context).sort(),
        inputFrozen: Object.isFrozen(invocation.input),
        parametersFrozen: Object.isFrozen(invocation.input.parameters),
        hasDocument: "document" in invocation || "document" in context,
        hasEngine: "engine" in invocation || "engine" in context,
        hasUno: "uno" in invocation || "uno" in context,
        hasModule: "Module" in invocation || "Module" in context,
        hasApply: "applyOperation" in invocation || "applyOperation" in context,
      };
      try {
        invocation.input.text = "tampered";
      } catch {
        mutationRejected = true;
      }
      return fixture.expectedOperation;
    },
  };
  const { host, registry } = makeHost(implementation);
  const document = makeDocumentBinding("web");
  await host.invokeSelection({
    providerId: descriptor.id,
    endpointId: fixture.endpointId,
    documentAdapter: document.adapter,
    parameters: fixture.input.parameters,
  });

  assert.deepEqual(observed.invocationKeys, ["endpointId", "input", "providerId"]);
  assert.deepEqual(observed.contextKeys, ["reportProgress", "signal"]);
  assert.equal(observed.inputFrozen, true);
  assert.equal(observed.parametersFrozen, true);
  assert.equal(observed.hasDocument, false);
  assert.equal(observed.hasEngine, false);
  assert.equal(observed.hasUno, false);
  assert.equal(observed.hasModule, false);
  assert.equal(observed.hasApply, false);
  assert.equal(mutationRejected, true);
  registry.dispose();
});

test("invalid or over-privileged operations never reach the document sink", async (t) => {
  const cases = [
    {
      name: "unknown operation",
      operation: { type: "rawUno", text: "bad", expectedRevision: 0 },
    },
    {
      name: "wrong snapshot revision",
      operation: { type: "replaceSelection", text: "bad", expectedRevision: 1 },
    },
    {
      name: "unknown operation field",
      operation: {
        type: "replaceSelection", text: "bad", expectedRevision: 0, command: ".uno:Paste",
      },
    },
    {
      name: "oversized output",
      operation: { type: "replaceSelection", text: "0123456789", expectedRevision: 0 },
      maxTextBytes: 8,
    },
  ];
  for (const sample of cases) {
    await t.test(sample.name, async () => {
      const implementation = { invoke: async () => sample.operation };
      const { host, registry } = makeHost(implementation, {
        maxTextBytes: sample.maxTextBytes,
      });
      let sinkCalls = 0;
      const documentAdapter = {
        binding: "test",
        snapshotSelection: async () => ({
          text: fixture.input.text,
          revision: fixture.input.revision,
        }),
        applyValidatedOperation: async () => {
          sinkCalls += 1;
        },
      };
      await assert.rejects(
        () => host.invokeSelection({
          providerId: descriptor.id,
          endpointId: fixture.endpointId,
          documentAdapter,
          parameters: fixture.input.parameters,
        }),
        (error) => error instanceof ProviderSdkError && error.code === "INVALID_OPERATION",
      );
      assert.equal(sinkCalls, 0);
      registry.dispose();
    });
  }
});

test("AbortSignal cancellation is typed and cannot apply a late result", async () => {
  const implementation = {
    invoke(invocation, context) {
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => resolve(fixture.expectedOperation), 100);
        context.signal.addEventListener("abort", () => {
          clearTimeout(timer);
          reject(new Error("provider observed abort"));
        }, { once: true });
      });
    },
  };
  const { host, registry } = makeHost(implementation);
  const controller = new AbortController();
  let sinkCalls = 0;
  const invoking = host.invokeSelection({
    providerId: descriptor.id,
    endpointId: fixture.endpointId,
    documentAdapter: {
      binding: "test",
      snapshotSelection: async () => ({ text: fixture.input.text, revision: 0 }),
      applyValidatedOperation: async () => { sinkCalls += 1; },
    },
    parameters: fixture.input.parameters,
    signal: controller.signal,
  });
  setTimeout(() => controller.abort(), 5);
  await assert.rejects(
    () => invoking,
    (error) => error instanceof ProviderAbortError && error.code === "PROVIDER_ABORTED",
  );
  await new Promise((resolve) => setTimeout(resolve, 120));
  assert.equal(sinkCalls, 0);
  registry.dispose();
});

class FakeProviderWorker {
  constructor() {
    this.listeners = new Map();
    this.messages = [];
    this.terminated = false;
    queueMicrotask(() => this.emit("message", {
      providerProtocolVersion: 1,
      kind: "ready",
      providerId: descriptor.id,
      contractVersion: "1.0",
      runtimeInfo: {
        globalKind: "dedicated-worker",
        document: "undefined",
        createProbeModule: "undefined",
        FS: "undefined",
        HEAPU8: "undefined",
      },
    }));
  }

  addEventListener(type, listener) {
    const listeners = this.listeners.get(type) || [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  postMessage(message) {
    this.messages.push(message);
    if (message.kind !== "invoke")
      return;
    queueMicrotask(() => {
      this.emit("message", {
        providerProtocolVersion: 1,
        kind: "progress",
        requestId: message.requestId,
        progress: { fraction: 0.5, message: "fake worker" },
      });
      this.emit("message", {
        providerProtocolVersion: 1,
        kind: "result",
        requestId: message.requestId,
        operation: fixture.expectedOperation,
      });
      // A misbehaving transport cannot complete the same request twice.
      this.emit("message", {
        providerProtocolVersion: 1,
        kind: "result",
        requestId: message.requestId,
        operation: { ...fixture.expectedOperation, text: "DUPLICATE-SHOULD-BE-IGNORED" },
      });
    });
  }

  emit(type, value) {
    for (const listener of this.listeners.get(type) || [])
      listener(type === "message" ? { data: value } : value);
  }

  terminate() {
    this.terminated = true;
  }
}

test("Worker provider transport handshakes, reports progress, and stays document-isolated", async () => {
  const workers = [];
  const adapter = new WorkerProviderAdapter({
    providerId: descriptor.id,
    workerFactory() {
      const worker = new FakeProviderWorker();
      workers.push(worker);
      return worker;
    },
  });
  const registry = new ProviderRegistry();
  registry.register(descriptor, adapter);
  const host = new ProviderHost({ registry });
  const document = makeDocumentBinding("web");
  const progress = [];
  const result = await host.invokeSelection({
    providerId: descriptor.id,
    endpointId: fixture.endpointId,
    documentAdapter: document.adapter,
    parameters: fixture.input.parameters,
    onProgress: (value) => progress.push(value),
  });

  assert.deepEqual(result.operation, fixture.expectedOperation);
  assert.equal(progress[0].fraction, 0.5);
  assert.deepEqual(adapter.runtimeInfo, {
    globalKind: "dedicated-worker",
    document: "undefined",
    createProbeModule: "undefined",
    FS: "undefined",
    HEAPU8: "undefined",
  });
  assert.equal(workers[0].messages[0].kind, "invoke");
  assert.equal("document" in workers[0].messages[0], false);
  assert.equal("documentHandle" in workers[0].messages[0], false);
  assert.equal(document.state.replacements.length, 1);
  assert.equal(document.state.text, fixture.expectedOperation.text);
  registry.dispose();
  assert.equal(workers[0].terminated, true);
});

test("Worker crash rejects pending and future invocations with a typed error", async () => {
  const workers = [];
  const adapter = new WorkerProviderAdapter({
    providerId: descriptor.id,
    workerFactory() {
      const worker = new FakeProviderWorker();
      worker.postMessage = function postMessage(message) {
        this.messages.push(message);
      };
      workers.push(worker);
      return worker;
    },
  });
  const registry = new ProviderRegistry();
  registry.register(descriptor, adapter);
  const host = new ProviderHost({ registry });
  const document = makeDocumentBinding("web");
  await adapter.ready();

  const pending = host.invokeSelection({
    providerId: descriptor.id,
    endpointId: fixture.endpointId,
    documentAdapter: document.adapter,
    parameters: fixture.input.parameters,
  });
  setTimeout(() => workers[0].emit("error", { message: "simulated provider crash" }), 5);
  await assert.rejects(
    () => pending,
    (error) => error instanceof ProviderWorkerCrashedError
               && error.code === "PROVIDER_WORKER_CRASHED",
  );
  await assert.rejects(
    () => host.invokeSelection({
      providerId: descriptor.id,
      endpointId: fixture.endpointId,
      documentAdapter: document.adapter,
      parameters: fixture.input.parameters,
    }),
    (error) => error instanceof ProviderWorkerCrashedError,
  );
  assert.equal(document.state.replacements.length, 0);
  registry.dispose();
});
