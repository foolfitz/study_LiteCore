export const PROVIDER_CONTRACT_VERSION = "1.0";
export const PROVIDER_WORKER_PROTOCOL_VERSION = 1;
export const DEFAULT_MAX_OPERATION_TEXT_BYTES = 1024 * 1024;

const SUPPORTED_CAPABILITIES = new Set(["text.translate"]);
const SUPPORTED_INPUTS = new Set(["selection.text"]);
const SUPPORTED_OPERATIONS = new Set(["replaceSelection"]);
const PROVIDER_ID_PATTERN = /^(?:[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$/;
const ENDPOINT_ID_PATTERN = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const SEMVER_PATTERN = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;

export class ProviderSdkError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "ProviderSdkError";
    this.code = code;
    this.details = details;
  }
}

export class ProviderAbortError extends ProviderSdkError {
  constructor(providerId, endpointId) {
    super("PROVIDER_ABORTED", `provider invocation was aborted: ${providerId}/${endpointId}`, {
      providerId,
      endpointId,
    });
    this.name = "ProviderAbortError";
  }
}

export class ProviderWorkerCrashedError extends ProviderSdkError {
  constructor(message = "provider worker crashed") {
    super("PROVIDER_WORKER_CRASHED", message);
    this.name = "ProviderWorkerCrashedError";
  }
}

function providerError(code, message, details = {}) {
  throw new ProviderSdkError(code, message, details);
}

function isPlainObject(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value))
    return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function assertPlainObject(value, code, label) {
  if (!isPlainObject(value))
    providerError(code, `${label} must be a plain object`);
}

function assertOnlyKeys(value, allowed, code, label) {
  const unknown = Object.keys(value).filter((key) => !allowed.has(key));
  if (unknown.length > 0)
    providerError(code, `${label} contains unknown fields`, { fields: unknown });
}

function cloneSerializable(value, code, label) {
  try {
    return structuredClone(value);
  } catch (error) {
    providerError(code, `${label} must be structured-clone serializable`, {
      cause: error instanceof Error ? error.message : String(error),
    });
  }
}

function deepFreeze(value) {
  if (value === null || typeof value !== "object" || Object.isFrozen(value))
    return value;
  for (const child of Object.values(value))
    deepFreeze(child);
  return Object.freeze(value);
}

function validUint32(value) {
  return Number.isInteger(value) && value >= 0 && value <= 0xffffffff;
}

function utf8Length(value) {
  return new TextEncoder().encode(value).byteLength;
}

function validateParameters(parameters) {
  assertPlainObject(parameters, "INVALID_INPUT", "parameters");
  const entries = Object.entries(parameters);
  if (entries.length > 16)
    providerError("INVALID_INPUT", "parameters may contain at most 16 entries");
  const normalized = {};
  for (const [key, value] of entries) {
    if (!ENDPOINT_ID_PATTERN.test(key))
      providerError("INVALID_INPUT", `invalid parameter name: ${key}`);
    if (!["string", "number", "boolean"].includes(typeof value)
        || (typeof value === "number" && !Number.isFinite(value))) {
      providerError("INVALID_INPUT", `parameter ${key} must be a scalar value`);
    }
    if (typeof value === "string" && utf8Length(value) > 256)
      providerError("INVALID_INPUT", `parameter ${key} exceeds 256 UTF-8 bytes`);
    normalized[key] = value;
  }
  return normalized;
}

export function validateProviderDescriptor(candidate) {
  const descriptor = cloneSerializable(candidate, "INVALID_DESCRIPTOR", "descriptor");
  assertPlainObject(descriptor, "INVALID_DESCRIPTOR", "descriptor");
  assertOnlyKeys(
    descriptor,
    new Set(["contractVersion", "id", "version", "displayName", "capabilities", "endpoints"]),
    "INVALID_DESCRIPTOR",
    "descriptor",
  );
  if (descriptor.contractVersion !== PROVIDER_CONTRACT_VERSION) {
    providerError("INCOMPATIBLE_PROVIDER_CONTRACT", "provider contract version mismatch", {
      expected: PROVIDER_CONTRACT_VERSION,
      actual: descriptor.contractVersion,
    });
  }
  if (typeof descriptor.id !== "string" || !PROVIDER_ID_PATTERN.test(descriptor.id))
    providerError("INVALID_DESCRIPTOR", "provider id must be a lowercase reverse-DNS name");
  if (typeof descriptor.version !== "string" || !SEMVER_PATTERN.test(descriptor.version))
    providerError("INVALID_DESCRIPTOR", "provider version must be semver");
  if (typeof descriptor.displayName !== "string" || descriptor.displayName.length === 0
      || utf8Length(descriptor.displayName) > 128) {
    providerError("INVALID_DESCRIPTOR", "displayName must be 1-128 UTF-8 bytes");
  }
  if (!Array.isArray(descriptor.capabilities) || descriptor.capabilities.length === 0)
    providerError("INVALID_DESCRIPTOR", "capabilities must be a non-empty array");
  const capabilities = new Set();
  for (const capability of descriptor.capabilities) {
    if (!SUPPORTED_CAPABILITIES.has(capability))
      providerError("INVALID_DESCRIPTOR", `unsupported capability: ${capability}`);
    if (capabilities.has(capability))
      providerError("INVALID_DESCRIPTOR", `duplicate capability: ${capability}`);
    capabilities.add(capability);
  }
  if (!Array.isArray(descriptor.endpoints) || descriptor.endpoints.length === 0)
    providerError("INVALID_DESCRIPTOR", "endpoints must be a non-empty array");
  const endpointIds = new Set();
  const endpointCapabilities = new Set();
  for (const endpoint of descriptor.endpoints) {
    assertPlainObject(endpoint, "INVALID_DESCRIPTOR", "endpoint");
    assertOnlyKeys(
      endpoint,
      new Set(["id", "capability", "input", "outputOperations"]),
      "INVALID_DESCRIPTOR",
      "endpoint",
    );
    if (typeof endpoint.id !== "string" || !ENDPOINT_ID_PATTERN.test(endpoint.id))
      providerError("INVALID_DESCRIPTOR", `invalid endpoint id: ${endpoint.id}`);
    if (endpointIds.has(endpoint.id))
      providerError("INVALID_DESCRIPTOR", `duplicate endpoint id: ${endpoint.id}`);
    endpointIds.add(endpoint.id);
    if (!capabilities.has(endpoint.capability))
      providerError("INVALID_DESCRIPTOR", `endpoint capability is not declared: ${endpoint.capability}`);
    endpointCapabilities.add(endpoint.capability);
    if (!SUPPORTED_INPUTS.has(endpoint.input) || endpoint.input !== "selection.text")
      providerError("INVALID_DESCRIPTOR", `unsupported endpoint input: ${endpoint.input}`);
    if (!Array.isArray(endpoint.outputOperations) || endpoint.outputOperations.length === 0)
      providerError("INVALID_DESCRIPTOR", "outputOperations must be a non-empty array");
    const operationTypes = new Set();
    for (const operation of endpoint.outputOperations) {
      if (!SUPPORTED_OPERATIONS.has(operation))
        providerError("INVALID_DESCRIPTOR", `unsupported output operation: ${operation}`);
      if (operationTypes.has(operation))
        providerError("INVALID_DESCRIPTOR", `duplicate output operation: ${operation}`);
      operationTypes.add(operation);
    }
  }
  for (const capability of capabilities) {
    if (!endpointCapabilities.has(capability))
      providerError("INVALID_DESCRIPTOR", `capability has no endpoint: ${capability}`);
  }
  return deepFreeze(descriptor);
}

function endpointFor(descriptor, endpointId) {
  const endpoint = descriptor.endpoints.find((item) => item.id === endpointId);
  if (!endpoint) {
    providerError("UNKNOWN_ENDPOINT", `unknown provider endpoint: ${endpointId}`, {
      providerId: descriptor.id,
      endpointId,
    });
  }
  return endpoint;
}

export function validateSelectionTextInput(candidate) {
  const input = cloneSerializable(candidate, "INVALID_INPUT", "provider input");
  assertPlainObject(input, "INVALID_INPUT", "provider input");
  assertOnlyKeys(
    input,
    new Set(["kind", "text", "revision", "parameters"]),
    "INVALID_INPUT",
    "provider input",
  );
  if (input.kind !== "selection.text")
    providerError("INVALID_INPUT", `unsupported input kind: ${input.kind}`);
  if (typeof input.text !== "string" || input.text.length === 0)
    providerError("INVALID_INPUT", "selection text must be non-empty");
  if (!validUint32(input.revision))
    providerError("INVALID_INPUT", "selection revision must be an unsigned 32-bit integer");
  input.parameters = validateParameters(input.parameters ?? {});
  return deepFreeze(input);
}

export function validateProviderOperation(candidate, options) {
  const operation = cloneSerializable(candidate, "INVALID_OPERATION", "provider operation");
  assertPlainObject(operation, "INVALID_OPERATION", "provider operation");
  assertOnlyKeys(
    operation,
    new Set(["type", "text", "expectedRevision"]),
    "INVALID_OPERATION",
    "provider operation",
  );
  const descriptor = validateProviderDescriptor(options?.descriptor);
  const endpoint = endpointFor(descriptor, options?.endpointId);
  const input = validateSelectionTextInput(options?.input);
  if (!endpoint.outputOperations.includes(operation.type)) {
    providerError("INVALID_OPERATION", "operation was not declared by the endpoint", {
      providerId: descriptor.id,
      endpointId: endpoint.id,
      operation: operation.type,
    });
  }
  if (operation.type !== "replaceSelection")
    providerError("INVALID_OPERATION", `unsupported operation: ${operation.type}`);
  if (typeof operation.text !== "string" || operation.text.length === 0)
    providerError("INVALID_OPERATION", "replaceSelection text must be non-empty");
  const maximum = options?.maxTextBytes ?? DEFAULT_MAX_OPERATION_TEXT_BYTES;
  if (!Number.isInteger(maximum) || maximum <= 0)
    providerError("INVALID_OPERATION", "maxTextBytes must be a positive integer");
  const bytes = utf8Length(operation.text);
  if (bytes > maximum) {
    providerError("INVALID_OPERATION", "replaceSelection text exceeds the configured limit", {
      bytes,
      maximum,
    });
  }
  if (!validUint32(operation.expectedRevision)
      || operation.expectedRevision !== input.revision) {
    providerError("INVALID_OPERATION", "operation revision does not match the selection snapshot", {
      expectedRevision: input.revision,
      actualRevision: operation.expectedRevision,
    });
  }
  return deepFreeze(operation);
}

function normalizeProgress(value) {
  const progress = cloneSerializable(value, "INVALID_PROGRESS", "provider progress");
  assertPlainObject(progress, "INVALID_PROGRESS", "provider progress");
  assertOnlyKeys(
    progress,
    new Set(["fraction", "message"]),
    "INVALID_PROGRESS",
    "provider progress",
  );
  if (typeof progress.fraction !== "number" || !Number.isFinite(progress.fraction)
      || progress.fraction < 0 || progress.fraction > 1) {
    providerError("INVALID_PROGRESS", "progress fraction must be between 0 and 1");
  }
  if (progress.message !== undefined
      && (typeof progress.message !== "string" || utf8Length(progress.message) > 256)) {
    providerError("INVALID_PROGRESS", "progress message must be at most 256 UTF-8 bytes");
  }
  return deepFreeze(progress);
}

export class ProviderRegistry {
  constructor() {
    this._providers = new Map();
  }

  register(descriptorCandidate, adapter) {
    const descriptor = validateProviderDescriptor(descriptorCandidate);
    if (!adapter || typeof adapter.invoke !== "function")
      providerError("INVALID_ADAPTER", "provider adapter must implement invoke()");
    if (this._providers.has(descriptor.id))
      providerError("DUPLICATE_PROVIDER", `provider is already registered: ${descriptor.id}`);
    this._providers.set(descriptor.id, { descriptor, adapter });
    return descriptor;
  }

  unregister(providerId) {
    const entry = this._providers.get(providerId);
    if (!entry)
      return false;
    this._providers.delete(providerId);
    if (typeof entry.adapter.dispose === "function")
      entry.adapter.dispose();
    return true;
  }

  listProviders() {
    return [...this._providers.values()].map((entry) => entry.descriptor);
  }

  get(providerId) {
    const entry = this._providers.get(providerId);
    if (!entry)
      providerError("PROVIDER_NOT_FOUND", `provider is not registered: ${providerId}`);
    return entry;
  }

  dispose() {
    for (const providerId of [...this._providers.keys()])
      this.unregister(providerId);
  }
}

export function createInProcessProviderAdapter(provider) {
  if (!provider || typeof provider.invoke !== "function")
    providerError("INVALID_ADAPTER", "in-process provider must implement invoke()");
  return Object.freeze({
    kind: "in-process",
    async invoke(invocation, options = {}) {
      if (options.signal?.aborted)
        throw new ProviderAbortError(invocation.providerId, invocation.endpointId);
      const safeInvocation = deepFreeze(cloneSerializable(
        invocation, "INVALID_INPUT", "provider invocation",
      ));
      const context = Object.freeze({
        signal: options.signal,
        reportProgress(value) {
          const progress = normalizeProgress(value);
          options.onProgress?.(progress);
        },
      });
      try {
        const result = await provider.invoke(safeInvocation, context);
        if (options.signal?.aborted)
          throw new ProviderAbortError(invocation.providerId, invocation.endpointId);
        return result;
      } catch (error) {
        if (options.signal?.aborted)
          throw new ProviderAbortError(invocation.providerId, invocation.endpointId);
        if (error instanceof ProviderSdkError)
          throw error;
        throw new ProviderSdkError(
          "PROVIDER_ERROR",
          error instanceof Error ? error.message : String(error),
        );
      }
    },
  });
}

function validateSelectionSnapshot(snapshot) {
  assertPlainObject(snapshot, "INVALID_DOCUMENT_ADAPTER", "selection snapshot");
  if (typeof snapshot.text !== "string" || snapshot.text.length === 0)
    providerError("INVALID_DOCUMENT_ADAPTER", "selection snapshot text must be non-empty");
  if (!validUint32(snapshot.revision))
    providerError("INVALID_DOCUMENT_ADAPTER", "selection snapshot revision must be uint32");
  return { text: snapshot.text, revision: snapshot.revision };
}

export function createWebDocumentAdapter(documentHandle) {
  if (!documentHandle || typeof documentHandle.getSelection !== "function"
      || typeof documentHandle.replaceSelection !== "function") {
    providerError("INVALID_DOCUMENT_ADAPTER", "web document must support selection and replace");
  }
  return Object.freeze({
    binding: "web",
    async snapshotSelection(options = {}) {
      return validateSelectionSnapshot(await documentHandle.getSelection({ signal: options.signal }));
    },
    async applyValidatedOperation(operation, options = {}) {
      return documentHandle.replaceSelection(operation.text, {
        expectedRevision: operation.expectedRevision,
        signal: options.signal,
      });
    },
  });
}

export function createDesktopDocumentAdapter(binding) {
  if (!binding || typeof binding.readSelection !== "function"
      || typeof binding.replaceSelection !== "function") {
    providerError(
      "INVALID_DOCUMENT_ADAPTER",
      "desktop binding must implement readSelection() and replaceSelection()",
    );
  }
  return Object.freeze({
    binding: "desktop",
    async snapshotSelection(options = {}) {
      return validateSelectionSnapshot(await binding.readSelection({ signal: options.signal }));
    },
    async applyValidatedOperation(operation, options = {}) {
      return binding.replaceSelection(operation.text, {
        expectedRevision: operation.expectedRevision,
        signal: options.signal,
      });
    },
  });
}

export class ProviderHost {
  constructor(options = {}) {
    if (!(options.registry instanceof ProviderRegistry))
      providerError("INVALID_ARGUMENT", "ProviderHost requires a ProviderRegistry");
    this.registry = options.registry;
    this.maxTextBytes = options.maxTextBytes ?? DEFAULT_MAX_OPERATION_TEXT_BYTES;
  }

  async invokeSelection(options) {
    const providerId = options?.providerId;
    const endpointId = options?.endpointId;
    const documentAdapter = options?.documentAdapter;
    const signal = options?.signal;
    if (signal?.aborted)
      throw new ProviderAbortError(providerId, endpointId);
    if (!documentAdapter || typeof documentAdapter.snapshotSelection !== "function"
        || typeof documentAdapter.applyValidatedOperation !== "function") {
      providerError("INVALID_DOCUMENT_ADAPTER", "invokeSelection requires a document adapter");
    }
    const entry = this.registry.get(providerId);
    const endpoint = endpointFor(entry.descriptor, endpointId);
    if (endpoint.input !== "selection.text")
      providerError("INVALID_INPUT", `endpoint does not accept a selection: ${endpointId}`);

    if (typeof entry.adapter.ready === "function")
      await entry.adapter.ready();
    const snapshot = await documentAdapter.snapshotSelection({ signal });
    const input = validateSelectionTextInput({
      kind: "selection.text",
      text: snapshot.text,
      revision: snapshot.revision,
      parameters: options.parameters ?? {},
    });
    const invocation = deepFreeze({ providerId, endpointId, input });
    const candidate = await entry.adapter.invoke(invocation, {
      signal,
      onProgress: options.onProgress,
    });
    if (signal?.aborted)
      throw new ProviderAbortError(providerId, endpointId);
    const operation = validateProviderOperation(candidate, {
      descriptor: entry.descriptor,
      endpointId,
      input,
      maxTextBytes: this.maxTextBytes,
    });
    const result = await documentAdapter.applyValidatedOperation(operation, { signal });
    return deepFreeze({
      providerId,
      endpointId,
      inputRevision: input.revision,
      operation,
      result: cloneSerializable(result, "INVALID_DOCUMENT_ADAPTER", "document result"),
    });
  }
}

function remoteProviderError(message) {
  const error = message?.error || {};
  return new ProviderSdkError(
    error.code || "PROVIDER_ERROR",
    error.message || "provider invocation failed",
    error.details || {},
  );
}

export class WorkerProviderAdapter {
  constructor(options = {}) {
    if (!options.workerUrl && !options.workerFactory)
      providerError("INVALID_ADAPTER", "workerUrl or workerFactory is required");
    const factory = options.workerFactory || ((url) => new Worker(url, {
      type: "module",
      name: `oxoffice-provider:${options.providerId || "unknown"}`,
    }));
    this.kind = "worker";
    this._providerId = options.providerId;
    this._contractVersion = options.contractVersion ?? PROVIDER_CONTRACT_VERSION;
    this._nextRequestId = 1;
    this._pending = new Map();
    this._disposed = false;
    this._crashedError = null;
    this.runtimeInfo = null;
    this._worker = factory(options.workerUrl);
    this._readyPromise = new Promise((resolve, reject) => {
      this._resolveReady = resolve;
      this._rejectReady = reject;
    });
    const readyTimeoutMs = options.readyTimeoutMs ?? 30000;
    if (!Number.isInteger(readyTimeoutMs) || readyTimeoutMs <= 0)
      providerError("INVALID_ADAPTER", "readyTimeoutMs must be a positive integer");
    this._readyTimer = setTimeout(() => {
      this._handleCrash(new ProviderWorkerCrashedError(
        `provider worker did not become ready within ${readyTimeoutMs} ms`,
      ));
    }, readyTimeoutMs);
    this._worker.addEventListener("message", (event) => this._handleMessage(event.data));
    this._worker.addEventListener("error", (event) => {
      this._handleCrash(new ProviderWorkerCrashedError(event?.message || "provider worker crashed"));
    });
    this._worker.addEventListener("messageerror", () => {
      this._handleCrash(new ProviderWorkerCrashedError("provider worker message could not be decoded"));
    });
  }

  ready() {
    return this._readyPromise;
  }

  _post(message) {
    if (this._crashedError)
      throw this._crashedError;
    if (this._disposed)
      throw new ProviderWorkerCrashedError("provider worker is disposed");
    this._worker.postMessage(message);
  }

  _cleanup(entry) {
    if (entry.signal && entry.abortListener)
      entry.signal.removeEventListener("abort", entry.abortListener);
  }

  _handleMessage(message) {
    if (!message || message.providerProtocolVersion !== PROVIDER_WORKER_PROTOCOL_VERSION) {
      this._handleCrash(new ProviderWorkerCrashedError("provider worker protocol mismatch"));
      return;
    }
    if (message.kind === "ready") {
      if ((this._providerId && message.providerId !== this._providerId)
          || message.contractVersion !== this._contractVersion) {
        this._handleCrash(new ProviderWorkerCrashedError("provider worker identity mismatch"));
        return;
      }
      this.runtimeInfo = deepFreeze(cloneSerializable(
        message.runtimeInfo || {}, "INVALID_ADAPTER", "provider runtime info",
      ));
      clearTimeout(this._readyTimer);
      this._resolveReady(this.runtimeInfo);
      return;
    }
    const entry = this._pending.get(message.requestId);
    if (!entry)
      return;
    if (message.kind === "progress") {
      try {
        entry.onProgress?.(normalizeProgress(message.progress));
      } catch (error) {
        this._pending.delete(message.requestId);
        this._cleanup(entry);
        entry.reject(error);
      }
      return;
    }
    if (message.kind !== "result" && message.kind !== "error")
      return;
    this._pending.delete(message.requestId);
    this._cleanup(entry);
    if (message.kind === "result")
      entry.resolve(message.operation);
    else
      entry.reject(remoteProviderError(message));
  }

  _handleCrash(error) {
    if (this._crashedError)
      return;
    this._crashedError = error;
    clearTimeout(this._readyTimer);
    this._rejectReady?.(error);
    for (const entry of this._pending.values()) {
      this._cleanup(entry);
      entry.reject(error);
    }
    this._pending.clear();
  }

  async invoke(invocation, options = {}) {
    await this.ready();
    if (options.signal?.aborted)
      throw new ProviderAbortError(invocation.providerId, invocation.endpointId);
    const requestId = this._nextRequestId;
    this._nextRequestId = requestId === 0xffffffff ? 1 : requestId + 1;
    return new Promise((resolve, reject) => {
      const entry = {
        resolve,
        reject,
        signal: options.signal,
        onProgress: options.onProgress,
        abortListener: null,
      };
      if (entry.signal) {
        entry.abortListener = () => {
          if (!this._pending.delete(requestId))
            return;
          this._cleanup(entry);
          try {
            this._post({
              providerProtocolVersion: PROVIDER_WORKER_PROTOCOL_VERSION,
              kind: "cancel",
              requestId,
            });
          } catch {
            // The local abort result remains authoritative if the worker already crashed.
          }
          reject(new ProviderAbortError(invocation.providerId, invocation.endpointId));
        };
        entry.signal.addEventListener("abort", entry.abortListener, { once: true });
      }
      this._pending.set(requestId, entry);
      try {
        this._post({
          providerProtocolVersion: PROVIDER_WORKER_PROTOCOL_VERSION,
          kind: "invoke",
          requestId,
          providerId: invocation.providerId,
          endpointId: invocation.endpointId,
          input: invocation.input,
        });
      } catch (error) {
        this._pending.delete(requestId);
        this._cleanup(entry);
        reject(error);
      }
    });
  }

  dispose() {
    if (this._disposed)
      return;
    this._disposed = true;
    if (!this._crashedError)
      this._handleCrash(new ProviderWorkerCrashedError("provider worker was disposed"));
    this._worker.terminate();
  }
}

export function installProviderWorkerRuntime(scope, provider) {
  const descriptor = validateProviderDescriptor(provider?.descriptor);
  if (!scope || typeof scope.addEventListener !== "function"
      || typeof scope.postMessage !== "function" || typeof provider?.invoke !== "function") {
    providerError("INVALID_ADAPTER", "invalid provider worker runtime configuration");
  }
  const controllers = new Map();
  scope.addEventListener("message", (event) => {
    const message = event.data;
    if (!message || message.providerProtocolVersion !== PROVIDER_WORKER_PROTOCOL_VERSION)
      return;
    if (message.kind === "cancel") {
      controllers.get(message.requestId)?.abort();
      return;
    }
    if (message.kind !== "invoke")
      return;
    const controller = new AbortController();
    controllers.set(message.requestId, controller);
    let active = true;
    const post = (payload) => scope.postMessage({
      providerProtocolVersion: PROVIDER_WORKER_PROTOCOL_VERSION,
      requestId: message.requestId,
      ...payload,
    });
    Promise.resolve().then(async () => {
      if (message.providerId !== descriptor.id)
        providerError("PROVIDER_NOT_FOUND", "provider worker received the wrong provider id");
      endpointFor(descriptor, message.endpointId);
      const invocation = deepFreeze({
        providerId: descriptor.id,
        endpointId: message.endpointId,
        input: validateSelectionTextInput(message.input),
      });
      const context = Object.freeze({
        signal: controller.signal,
        reportProgress(value) {
          if (active && !controller.signal.aborted)
            post({ kind: "progress", progress: normalizeProgress(value) });
        },
      });
      const operation = await provider.invoke(invocation, context);
      if (controller.signal.aborted)
        throw new ProviderAbortError(descriptor.id, message.endpointId);
      post({ kind: "result", operation });
    }).catch((error) => {
      const normalized = error instanceof ProviderSdkError
        ? error
        : new ProviderSdkError("PROVIDER_ERROR", error instanceof Error ? error.message : String(error));
      post({
        kind: "error",
        error: {
          code: normalized.code,
          message: normalized.message,
          details: normalized.details,
        },
      });
    }).finally(() => {
      active = false;
      controllers.delete(message.requestId);
    });
  });
  scope.postMessage({
    providerProtocolVersion: PROVIDER_WORKER_PROTOCOL_VERSION,
    kind: "ready",
    providerId: descriptor.id,
    contractVersion: descriptor.contractVersion,
    runtimeInfo: {
      globalKind: "dedicated-worker",
      document: typeof scope.document,
      createProbeModule: typeof scope.createProbeModule,
      FS: typeof scope.FS,
      HEAPU8: typeof scope.HEAPU8,
    },
  });
}
