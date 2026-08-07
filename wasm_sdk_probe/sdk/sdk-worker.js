"use strict";

const PROTOCOL_VERSION = 1;
const STATUS_NAMES = new Map([
  [0, "OK"],
  [1, "INVALID_ARGUMENT"],
  [2, "INCOMPATIBLE_ABI"],
  [3, "NOT_STARTED"],
  [4, "DUPLICATE_REQUEST"],
  [5, "REQUEST_NOT_FOUND"],
  [6, "NOT_CANCELLABLE"],
  [7, "INTERNAL_ERROR"],
]);

let moduleInstance = null;
let modulePromise = null;
let manifestPromise = null;
let activeManifest = null;
let debugEnabled = false;
const pending = new Map();
const openStates = new Map();
const loadedResourcePacks = new Set();
const encoder = new TextEncoder();
const OPERATION_CAPABILITIES = new Map([
  ["open", "open-odt"],
  ["paint", "rgba-tile"],
  ["click", "insert-text"],
  ["insertText", "insert-text"],
  ["search", "search"],
  ["getSelection", "selection-text"],
  ["replaceSelection", "replace-selection"],
  ["undo", "undo"],
  ["addComment", "comments"],
  ["listComments", "comments"],
  ["setTrackChanges", "tracked-changes"],
  ["listTrackedChanges", "tracked-changes"],
  ["editorActionV1", "narrow-editor-v1"],
  ["editorGetStateV1", "narrow-editor-v1"],
  ["editorSelectRangeV1", "narrow-editor-v1"],
  ["editorDiscoveryAction", "editor-discovery-closed-actions"],
  ["editorDiscoverySelect", "editor-discovery-closed-actions"],
  ["editorDiscoveryGetState", "editor-discovery-closed-actions"],
  ["finding016DrainScheduler", "finding-016-scheduler-probe"],
  ["save", "save-odt"],
  ["close", "open-odt"],
]);
const EDITOR_V1_ACTION_IDS = Object.freeze({
  "move-character-left": 1,
  "move-character-right": 2,
  "delete-backward": 3,
  "delete-forward": 4,
  "insert-paragraph-break": 5,
  "insert-line-break": 6,
  "set-bold": 7,
  "set-italic": 8,
  "set-underline": 9,
  "set-strikethrough": 10,
});
const EDITOR_V1_MOVE_ACTIONS = new Set([
  "move-character-left",
  "move-character-right",
]);
const EDITOR_V1_FORMAT_ACTIONS = new Set([
  "set-bold", "set-italic", "set-underline", "set-strikethrough",
]);
const EDITOR_DISCOVERY_ACTION_IDS = Object.freeze({
  "move-character-left": 1,
  "move-character-right": 2,
  "move-line-up": 3,
  "move-line-down": 4,
  "move-line-home": 5,
  "move-line-end": 6,
  "delete-backward": 7,
  "delete-forward": 8,
  "insert-paragraph-break": 9,
  "insert-line-break": 10,
  "undo": 11,
  "redo": 12,
  "set-bold": 13,
  "set-italic": 14,
  "set-paragraph-body": 15,
  "set-paragraph-heading": 16,
  "set-list-none": 17,
  "set-list-unordered": 18,
  "set-list-ordered": 19,
});
const EDITOR_DISCOVERY_SELECTION_IDS = Object.freeze({
  "mouse-drag": 1,
  "text-handles-unstable": 2,
  "selection-reset-unstable": 3,
});

function editorDiscoveryEnabled() {
  return activeManifest?.diagnostic?.scope === "e1-odt-editing-discovery"
    && activeManifest?.capabilities?.includes("editor-discovery-closed-actions");
}

function editorV1Enabled() {
  return activeManifest?.capabilities?.includes("narrow-editor-v1")
    && activeManifest?.editorContract?.version === 1;
}

function productEditorState(value = {}) {
  return {
    sourceSequence: value.sourceSequence,
    documentChangeSequence: value.documentChangeSequence,
    visible: value.visible === true,
    caret: value.caret ?? null,
    selection: value.selection ?? {
      observed: false,
      collapsed: true,
      start: null,
      end: null,
      rectangles: [],
    },
    format: {
      bold: typeof value.format?.bold === "boolean" ? value.format.bold : null,
      italic: typeof value.format?.italic === "boolean" ? value.format.italic : null,
    },
  };
}

function postResponse(requestId, ok, value, transfer = []) {
  const message = {
    protocolVersion: PROTOCOL_VERSION,
    kind: "response",
    requestId,
    ok,
    ...(ok ? { result: value } : { error: value }),
  };
  self.postMessage(message, transfer);
}

function postEvent(event, fields = {}) {
  self.postMessage({
    protocolVersion: PROTOCOL_VERSION,
    kind: "event",
    event,
    ...fields,
  });
}

function fail(requestId, code, message, detail = {}) {
  pending.delete(requestId);
  openStates.delete(requestId);
  postResponse(requestId, false, { code, message, ...detail });
}

function complete(requestId, result, transfer = []) {
  pending.delete(requestId);
  openStates.delete(requestId);
  postResponse(requestId, true, result, transfer);
}

function ccall(name, returnType, argumentTypes = [], argumentsList = []) {
  if (!moduleInstance)
    throw new Error("WASM module is not initialized");
  return moduleInstance.ccall(name, returnType, argumentTypes, argumentsList);
}

function callStatus(name, argumentTypes, argumentsList) {
  return Number(ccall(name, "number", argumentTypes, argumentsList));
}

function withWasmBytes(bytes, callback) {
  const length = bytes.byteLength;
  const pointer = Number(ccall("oxsdk_buffer_alloc", "number", ["number"], [length]));
  if (!pointer)
    throw new Error(`unable to allocate ${length} bytes in WASM`);
  try {
    moduleInstance.HEAPU8.set(bytes, pointer);
    return callback(pointer, length);
  } finally {
    ccall("oxsdk_buffer_free", null, ["number"], [pointer]);
  }
}

function withUtf8(text, callback) {
  return withWasmBytes(encoder.encode(text), callback);
}

function accept(request, invoke) {
  pending.set(request.requestId, {
    operation: request.operation,
    payload: request.payload || {},
  });
  try {
    const status = invoke();
    if (status !== 0) {
      fail(
        request.requestId,
        STATUS_NAMES.get(status) || "UNKNOWN_STATUS",
        `${request.operation} was rejected before queueing`,
        { status },
      );
    }
  } catch (error) {
    fail(request.requestId, "WORKER_EXCEPTION", String(error?.stack || error));
  }
}

function copyOwnedBuffer(event) {
  const pointer = Number(event.ptr);
  const size = Number(event.size);
  if (!Number.isSafeInteger(pointer) || pointer <= 0 || !Number.isSafeInteger(size)
      || size <= 0 || pointer + size > moduleInstance.HEAPU8.byteLength) {
    if (pointer > 0)
      ccall("oxsdk_buffer_free", null, ["number"], [pointer]);
    throw new Error(`invalid owned WASM buffer ptr=${pointer} size=${size}`);
  }
  try {
    return moduleInstance.HEAPU8.slice(pointer, pointer + size).buffer;
  } finally {
    ccall("oxsdk_buffer_free", null, ["number"], [pointer]);
  }
}

function maybeCompleteOpen(requestId) {
  const state = openStates.get(requestId);
  if (!state?.opened || !state?.viewReady)
    return;
  const event = state.opened;
  complete(requestId, {
    documentHandle: event.documentHandle,
    revision: event.revision,
    parts: event.parts,
    width: event.width,
    height: event.height,
    tileMode: event.tileMode,
    viewReady: true,
  });
  postEvent("view-ready", {
    documentHandle: event.documentHandle,
    revision: event.revision,
  });
}

function parseEngineJson(value, label) {
  try {
    return JSON.parse(value || "{}");
  } catch (error) {
    throw new Error(`${label} returned invalid JSON: ${error}`);
  }
}

async function loadManifest() {
  if (!manifestPromise) {
    manifestPromise = (async () => {
      const response = await fetch(new URL("./sdk-manifest.json", self.location.href), {
        cache: "no-cache",
      });
      if (!response.ok)
        throw new Error(`sdk manifest request failed with HTTP ${response.status}`);
      return response.json();
    })();
  }
  return manifestPromise;
}

async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

function safeResourcePath(filename) {
  return typeof filename === "string"
         && filename.startsWith("/instdir/share/fonts/truetype/")
         && !filename.includes("..")
         && !filename.includes("\\")
         && filename.length < 512;
}

async function loadResourcePack(pack) {
  if (!pack || typeof pack.id !== "string" || loadedResourcePacks.has(pack.id))
    return;
  const metadataUrl = new URL(pack.metadata, self.location.href);
  const dataUrl = new URL(pack.data, self.location.href);
  const [metadataResponse, dataResponse] = await Promise.all([
    fetch(metadataUrl),
    fetch(dataUrl),
  ]);
  if (!metadataResponse.ok || !dataResponse.ok) {
    throw new Error(
      `resource pack ${pack.id} fetch failed: metadata=${metadataResponse.status} data=${dataResponse.status}`,
    );
  }
  const [metadata, buffer] = await Promise.all([
    metadataResponse.json(),
    dataResponse.arrayBuffer(),
  ]);
  if (!Array.isArray(metadata.files)
      || metadata.remote_package_size !== buffer.byteLength
      || pack.bytes !== buffer.byteLength) {
    throw new Error(`resource pack ${pack.id} size or metadata mismatch`);
  }
  const expectedHash = String(pack.sha256 || "").toLowerCase();
  if (!/^[0-9a-f]{64}$/.test(expectedHash)
      || expectedHash !== String(metadata.sha256 || "").toLowerCase()
      || await sha256Hex(buffer) !== expectedHash) {
    throw new Error(`resource pack ${pack.id} SHA-256 mismatch`);
  }

  const bytes = new Uint8Array(buffer);
  const paths = new Set();
  let previousEnd = 0;
  for (const file of metadata.files) {
    if (!safeResourcePath(file.filename) || paths.has(file.filename)
        || !Number.isInteger(file.start) || !Number.isInteger(file.end)
        || file.start !== previousEnd || file.end <= file.start
        || file.end > bytes.byteLength) {
      throw new Error(`resource pack ${pack.id} contains an invalid file range or path`);
    }
    paths.add(file.filename);
    previousEnd = file.end;
  }
  if (previousEnd !== bytes.byteLength)
    throw new Error(`resource pack ${pack.id} does not cover its complete data blob`);

  for (const file of metadata.files) {
    const directory = file.filename.slice(0, file.filename.lastIndexOf("/"));
    moduleInstance.FS.mkdirTree(directory);
    moduleInstance.FS.writeFile(file.filename, bytes.subarray(file.start, file.end));
  }
  loadedResourcePacks.add(pack.id);
  postEvent("resource-pack-loaded", {
    resourcePack: pack.id,
    files: metadata.files.length,
    bytes: buffer.byteLength,
    sha256: expectedHash,
  });
}

async function loadStartupResourcePacks(manifest) {
  for (const pack of manifest.resourcePacks || []) {
    if (pack.loadAtStartup === true)
      await loadResourcePack(pack);
  }
}

function ensureModule(manifest) {
  if (modulePromise)
    return modulePromise;
  modulePromise = (async () => {
    self.__probe_on_event = handleCEvent;
    const artifactFiles = manifest.artifactFiles || {};
    const loaderUrl = new URL(artifactFiles["probe.js"] || "./probe.js", self.location.href).href;
    importScripts(loaderUrl);
    const factory = self.createProbeModule;
    if (typeof factory !== "function")
      throw new Error("probe.js did not expose createProbeModule in the worker");
    moduleInstance = await factory({
      // importScripts() leaves self.location at sdk-worker.js. Without this
      // override Emscripten's pthread pool would spawn sdk-worker.js again
      // instead of loading the generated pthread entrypoint in probe.js.
      mainScriptUrlOrBlob: loaderUrl,
      print: (text) => {
        if (debugEnabled)
          postEvent("diagnostic", { level: "stdout", message: String(text) });
      },
      printErr: (text) => {
        if (debugEnabled)
          postEvent("diagnostic", { level: "stderr", message: String(text) });
      },
      locateFile: (path) => new URL(artifactFiles[path] || path, self.location.href).href,
    });
    return moduleInstance;
  })();
  return modulePromise;
}

function handleCEvent(rawEvent) {
  let event;
  try {
    event = JSON.parse(rawEvent);
  } catch (error) {
    postEvent("worker-protocol-error", { message: String(error), rawEvent });
    return;
  }

  const requestId = Number(event.requestId || 0);
  switch (event.type) {
    case "ready": {
      if (!requestId)
        return;
      Promise.all([loadManifest(), Promise.resolve({
        abiVersion: event.abiVersion,
        capabilityBits: event.capabilities,
      })]).then(([manifest, runtime]) => {
        if (Number.isInteger(manifest.expectedCapabilityBits)
            && manifest.expectedCapabilityBits !== runtime.capabilityBits) {
          throw new Error(
            `manifest capability bits ${manifest.expectedCapabilityBits} do not match runtime ${runtime.capabilityBits}`,
          );
        }
        complete(requestId, { ...manifest, ...runtime });
      }).catch((error) => {
        fail(requestId, "MANIFEST_ERROR", String(error?.stack || error));
      });
      break;
    }
    case "opened": {
      if (!requestId)
        return;
      const state = openStates.get(requestId) || {};
      state.opened = event;
      openStates.set(requestId, state);
      maybeCompleteOpen(requestId);
      break;
    }
    case "view-ready": {
      if (!requestId)
        return;
      const state = openStates.get(requestId) || {};
      state.viewReady = event;
      openStates.set(requestId, state);
      maybeCompleteOpen(requestId);
      break;
    }
    case "tile": {
      if (!requestId)
        return;
      try {
        const pixels = copyOwnedBuffer(event);
        complete(requestId, {
          pixels,
          width: event.w,
          height: event.h,
          revision: event.revision,
        }, [pixels]);
      } catch (error) {
        fail(requestId, "BUFFER_ERROR", String(error?.stack || error));
      }
      break;
    }
    case "clicked":
      if (requestId)
        complete(requestId, { revision: event.revision });
      break;
    case "inserted":
      if (requestId)
        complete(requestId, { method: event.method, revision: event.revision });
      break;
    case "search-result": {
      if (!requestId)
        return;
      try {
        // LOK_CALLBACK_SEARCH_NOT_FOUND carries the query string as its raw
        // payload, while SEARCH_RESULT_SELECTION carries JSON.  Only the
        // successful callback has a JSON result to decode.
        const detail = event.found === true && event.resultPayload
          ? parseEngineJson(event.resultPayload, "search")
          : {};
        complete(requestId, {
          found: event.found === true,
          query: event.query || "",
          selections: Array.isArray(detail.searchResultSelection)
            ? detail.searchResultSelection
            : [],
          revision: event.revision,
        });
      } catch (error) {
        fail(requestId, "RESULT_PARSE_ERROR", String(error?.stack || error));
      }
      break;
    }
    case "selection":
      if (requestId) {
        complete(requestId, {
          // "none" is a success, not an error: it covers a caret-only
          // selection. Confirm a collapsed caret against the editor state's
          // selection.observed/collapsed pair, which comes from the
          // LOK_CALLBACK_TEXT_SELECTION path rather than the transferable.
          // Defaults to "unknown", never "none": an engine that predates the
          // selection-type readback emits no field, and treating that as
          // "nothing is selected" would let a caret precondition pass while a
          // selection is still live.
          selectionType: event.selectionType || "unknown",
          text: event.text || "",
          mimeType: event.mimeType,
          revision: event.revision,
        });
      }
      break;
    case "replaced":
    case "undone":
    case "comment-added":
    case "track-changes-set":
      if (requestId)
        complete(requestId, { revision: event.revision });
      break;
    case "comments": {
      if (!requestId)
        return;
      try {
        const data = parseEngineJson(event.dataJson, "comments");
        complete(requestId, {
          comments: Array.isArray(data.comments) ? data.comments : [],
          revision: event.revision,
        });
      } catch (error) {
        fail(requestId, "RESULT_PARSE_ERROR", String(error?.stack || error));
      }
      break;
    }
    case "tracked-changes": {
      if (!requestId)
        return;
      try {
        const data = parseEngineJson(event.dataJson, "tracked changes");
        complete(requestId, {
          changes: Array.isArray(data.redlines) ? data.redlines : [],
          revision: event.revision,
        });
      } catch (error) {
        fail(requestId, "RESULT_PARSE_ERROR", String(error?.stack || error));
      }
      break;
    }
    case "editor-action-completed":
      if (requestId) {
        const operation = pending.get(requestId)?.operation;
        const result = {
          action: event.action,
          option: event.option === true,
          beforeRevision: event.beforeRevision,
          revision: event.revision,
          changed: typeof event.changed === "boolean" ? event.changed : null,
          completion: event.completion,
          callbackSequenceBefore: event.callbackSequenceBefore,
          callbackSequenceAfter: event.callbackSequenceAfter,
          state: operation === "editorActionV1"
            ? productEditorState(event.state)
            : event.state,
        };
        if (operation !== "editorActionV1")
          result.selectionBarrier = event.selectionBarrier;
        complete(requestId, result);
      }
      break;
    case "editor-selection-completed":
      if (requestId) {
        complete(requestId, {
          method: event.method,
          revision: event.revision,
          completion: event.completion,
          callbackSequenceBefore: event.callbackSequenceBefore,
          callbackSequenceAfter: event.callbackSequenceAfter,
          state: event.state,
        });
      }
      break;
    case "editor-state-result":
      if (requestId) {
        const operation = pending.get(requestId)?.operation;
        if (operation === "editorGetStateV1") {
          complete(requestId, {
            documentHandle: event.documentHandle,
            revision: event.revision,
            ...productEditorState(event),
            selectionType: event.selectionType || "unknown",
            selectionTextMissing: event.selectionTextMissing === true,
            selectionText: event.selectionText || "",
          });
          break;
        }
        complete(requestId, {
          documentHandle: event.documentHandle,
          revision: event.revision,
          sourceSequence: event.sourceSequence,
          documentChangeSequence: event.documentChangeSequence,
          visible: event.visible,
          caret: event.caret,
          selection: event.selection,
          a11y: event.a11y,
          // Defaults to "unknown", never "none": an engine that predates the
          // selection-type readback emits no field, and treating that as
          // "nothing is selected" would let a caret precondition pass while a
          // selection is still live.
          selectionType: event.selectionType || "unknown",
          selectionTextMissing: event.selectionTextMissing === true,
          selectionText: event.selectionText || "",
          format: event.format,
          schedulerProbe: event.schedulerProbe,
        });
      }
      break;
    case "finding-016-scheduler-drained":
      if (requestId) {
        complete(requestId, {
          documentHandle: event.documentHandle,
          beforeRevision: event.beforeRevision,
          revision: event.revision,
          before: event.before,
          after: event.after,
          delta: event.delta,
        });
      }
      break;
    case "editor-state":
      if (editorDiscoveryEnabled()) {
        postEvent("editor-state", {
          documentHandle: event.documentHandle,
          revision: event.revision,
          source: event.source,
          sourceSequence: event.sourceSequence,
          documentChangeSequence: event.documentChangeSequence,
          visible: event.visible,
          caret: event.caret,
          selection: event.selection,
          a11y: event.a11y,
          format: event.format,
          schedulerProbe: event.schedulerProbe,
        });
      }
      break;
    case "editor-callback-parse-error":
      if (editorDiscoveryEnabled()) {
        postEvent("editor-callback-parse-error", {
          documentHandle: event.documentHandle,
          revision: event.revision,
          callbackId: event.callbackId,
        });
      }
      break;
    case "saved": {
      if (!requestId)
        return;
      try {
        const buffer = copyOwnedBuffer(event);
        complete(requestId, {
          buffer,
          format: event.format,
          revision: event.revision,
        }, [buffer]);
      } catch (error) {
        fail(requestId, "BUFFER_ERROR", String(error?.stack || error));
      }
      break;
    }
    case "closed":
      if (requestId)
        complete(requestId, { documentHandle: event.documentHandle });
      break;
    case "cancelled":
      if (requestId)
        fail(requestId, "CANCELLED", "request was cancelled before execution");
      break;
    case "error":
      if (requestId) {
        fail(requestId, event.code || "ENGINE_ERROR", event.message || event.msg || "engine error", {
          operation: event.operation || event.where,
          documentHandle: event.documentHandle,
          revision: event.revision,
          expectedRevision: event.expectedRevision,
          currentRevision: event.currentRevision,
        });
      } else {
        postEvent("engine-error", {
          error: { code: event.code || "ENGINE_ERROR", message: event.message || event.msg },
        });
      }
      break;
    case "lok":
      if (event.id === 0 || event.id === 1) {
        postEvent("document-invalidated", {
          documentHandle: event.documentHandle,
          revision: event.revision,
        });
      } else if (debugEnabled && [12, 15, 16, 30, 31, 32].includes(event.id)) {
        postEvent("diagnostic", { level: "lok-review", detail: event });
      }
      break;
    case "stage":
      if (debugEnabled)
        postEvent("diagnostic", { level: "stage", detail: event });
      break;
    default:
      if (debugEnabled)
        postEvent("diagnostic", { level: "event", detail: event });
  }
}

async function handleInit(request) {
  debugEnabled = request.payload?.debug === true;
  pending.set(request.requestId, { operation: request.operation });
  try {
    const manifest = await loadManifest();
    activeManifest = manifest;
    await ensureModule(manifest);
    await loadStartupResourcePacks(manifest);
    const actualAbi = Number(ccall("oxsdk_abi_version", "number"));
    const requestedAbi = Number(request.payload.requestedAbiVersion);
    const compatibleAbi = (actualAbi >>> 16) === (requestedAbi >>> 16)
                          && (requestedAbi & 0xffff) <= (actualAbi & 0xffff);
    if (!compatibleAbi) {
      fail(request.requestId, "INCOMPATIBLE_ABI",
           `worker ABI ${actualAbi} is not compatible with requested ${requestedAbi}`);
      return;
    }
    const status = callStatus(
      "oxsdk_engine_start",
      ["number", "number"],
      [requestedAbi, request.requestId],
    );
    if (status !== 0) {
      fail(request.requestId, STATUS_NAMES.get(status) || "UNKNOWN_STATUS",
           "engine start was rejected", { status });
    }
  } catch (error) {
    fail(request.requestId, "WORKER_INIT_FAILED", String(error?.stack || error));
  }
}

function handleRequest(request) {
  if (request.operation === "init") {
    void handleInit(request);
    return;
  }
  if (!moduleInstance) {
    postResponse(request.requestId, false, {
      code: "NOT_INITIALIZED",
      message: "worker must complete init before document operations",
    });
    return;
  }

  const payload = request.payload || {};
  const requiredCapability = OPERATION_CAPABILITIES.get(request.operation);
  if (requiredCapability
      && !activeManifest?.capabilities?.includes(requiredCapability)) {
    postResponse(request.requestId, false, {
      code: "UNSUPPORTED_OPERATION",
      message: `${request.operation} is unavailable in profile ${activeManifest?.profile || "unknown"}`,
      operation: request.operation,
      requiredCapability,
      profile: activeManifest?.profile,
    });
    return;
  }
  if (request.operation.startsWith("editorDiscovery")
      && !editorDiscoveryEnabled()) {
    postResponse(request.requestId, false, {
      code: "UNSUPPORTED_OPERATION",
      message: "editor discovery operations require the isolated E1 diagnostic profile",
      operation: request.operation,
      profile: activeManifest?.profile,
    });
    return;
  }
  if (request.operation.startsWith("editor")
      && request.operation.endsWith("V1")
      && !editorV1Enabled()) {
    postResponse(request.requestId, false, {
      code: "UNSUPPORTED_OPERATION",
      message: "editor v1 operations require the isolated narrow editor profile",
      operation: request.operation,
      profile: activeManifest?.profile,
    });
    return;
  }
  switch (request.operation) {
    case "open":
      openStates.set(request.requestId, {});
      accept(request, () => {
        if (!(payload.buffer instanceof ArrayBuffer))
          return 1;
        const bytes = new Uint8Array(payload.buffer);
        return withWasmBytes(bytes, (inputPointer, inputLength) =>
          withUtf8(String(payload.name || "input.odt"), (namePointer, nameLength) =>
            callStatus(
              "oxsdk_document_open",
              ["number", "number", "number", "number", "number"],
              [request.requestId, inputPointer, inputLength, namePointer, nameLength],
            )));
      });
      break;
    case "paint":
      accept(request, () => callStatus(
        "oxsdk_document_paint",
        ["number", "number", "number", "number", "number", "number", "number", "number"],
        [request.requestId, payload.documentHandle, payload.xTwips, payload.yTwips,
          payload.widthTwips, payload.heightTwips, payload.canvasWidthPx, payload.canvasHeightPx],
      ));
      break;
    case "click":
      accept(request, () => callStatus(
        "oxsdk_document_click",
        ["number", "number", "number", "number"],
        [request.requestId, payload.documentHandle, payload.xTwips, payload.yTwips],
      ));
      break;
    case "insertText":
      accept(request, () => withUtf8(String(payload.text || ""), (pointer, length) =>
        callStatus(
          "oxsdk_document_insert_text",
          ["number", "number", "number", "number"],
          [request.requestId, payload.documentHandle, pointer, length],
        )));
      break;
    case "search":
      accept(request, () => withUtf8(String(payload.query || ""), (pointer, length) =>
        callStatus(
          "oxsdk_document_search",
          ["number", "number", "number", "number", "number"],
          [request.requestId, payload.documentHandle, pointer, length,
            payload.backward === true ? 1 : 0],
        )));
      break;
    case "getSelection":
      accept(request, () => callStatus(
        "oxsdk_document_get_selection",
        ["number", "number"],
        [request.requestId, payload.documentHandle],
      ));
      break;
    case "replaceSelection":
      accept(request, () => withUtf8(String(payload.text || ""), (pointer, length) =>
        callStatus(
          "oxsdk_document_replace_selection",
          ["number", "number", "number", "number", "number"],
          [request.requestId, payload.documentHandle, payload.expectedRevision,
            pointer, length],
        )));
      break;
    case "undo":
      accept(request, () => callStatus(
        "oxsdk_document_undo",
        ["number", "number", "number"],
        [request.requestId, payload.documentHandle, payload.expectedRevision],
      ));
      break;
    case "addComment":
      accept(request, () => withUtf8(String(payload.text || ""),
        (textPointer, textLength) => withUtf8(String(payload.author || ""),
          (authorPointer, authorLength) => callStatus(
            "oxsdk_document_add_comment",
            ["number", "number", "number", "number", "number", "number", "number"],
            [request.requestId, payload.documentHandle, payload.expectedRevision,
              textPointer, textLength, authorPointer, authorLength],
          ))));
      break;
    case "listComments":
      accept(request, () => callStatus(
        "oxsdk_document_list_comments",
        ["number", "number"],
        [request.requestId, payload.documentHandle],
      ));
      break;
    case "setTrackChanges":
      accept(request, () => callStatus(
        "oxsdk_document_set_track_changes",
        ["number", "number", "number", "number"],
        [request.requestId, payload.documentHandle, payload.expectedRevision,
          payload.enabled === true ? 1 : 0],
      ));
      break;
    case "listTrackedChanges":
      accept(request, () => callStatus(
        "oxsdk_document_list_changes",
        ["number", "number"],
        [request.requestId, payload.documentHandle],
      ));
      break;
    case "editorActionV1": {
      const actionId = EDITOR_V1_ACTION_IDS[payload.action];
      const forbiddenFields = ["keyCode", "unoCommand", "command"];
      const hasForbiddenField = forbiddenFields.some((field) =>
        Object.hasOwn(payload, field));
      const validRevision = Number.isInteger(payload.expectedRevision)
        && payload.expectedRevision >= 0
        && payload.expectedRevision <= 0xffffffff;
      const typedFlags = typeof payload.extendSelection === "boolean"
        && typeof payload.enabled === "boolean";
      const validMoveOption = EDITOR_V1_MOVE_ACTIONS.has(payload.action)
        || payload.extendSelection === false;
      const validFormatOption = EDITOR_V1_FORMAT_ACTIONS.has(payload.action)
        || payload.enabled === false;
      if (!Number.isInteger(actionId) || !validRevision || !typedFlags
          || !validMoveOption || !validFormatOption || hasForbiddenField) {
        postResponse(request.requestId, false, {
          code: "INVALID_ARGUMENT",
          message: "editorActionV1 requires a closed action and typed options",
        });
        break;
      }
      accept(request, () => callStatus(
        "oxsdk_editor_action",
        ["number", "number", "number", "number", "number", "number"],
        [request.requestId, payload.documentHandle, payload.expectedRevision,
          actionId, payload.extendSelection ? 1 : 0, payload.enabled ? 1 : 0],
      ));
      break;
    }
    // SPEC E1-D.  The selection method is not a parameter: the engine entry
    // point is hard-wired to the setTextSelection path, because the
    // synthesised-mouse-event path reports success while selecting nothing
    // (SPEC E1-D section 2.1).  A range that selects nothing is a valid
    // outcome; the caller judges by reading the selection back.
    case "editorSelectRangeV1": {
      const coordinates = [
        payload.startXTwips, payload.startYTwips,
        payload.endXTwips, payload.endYTwips,
      ];
      const forbiddenFields = ["method", "keyCode", "unoCommand", "command"];
      if (coordinates.some((value) => !Number.isInteger(value) || value < 0)
          || forbiddenFields.some((field) => Object.hasOwn(payload, field))) {
        postResponse(request.requestId, false, {
          code: "INVALID_ARGUMENT",
          message: "editorSelectRangeV1 requires four non-negative integer twips and no method",
        });
        break;
      }
      accept(request, () => callStatus(
        "oxsdk_editor_select_range",
        ["number", "number", "number", "number", "number", "number"],
        [request.requestId, payload.documentHandle, ...coordinates],
      ));
      break;
    }
    case "editorGetStateV1":
      accept(request, () => callStatus(
        "oxsdk_editor_get_state",
        ["number", "number"],
        [request.requestId, payload.documentHandle],
      ));
      break;
    case "editorDiscoveryAction": {
      const actionId = EDITOR_DISCOVERY_ACTION_IDS[payload.action];
      if (!Number.isInteger(actionId)
          || !Number.isInteger(payload.expectedRevision)
          || payload.expectedRevision < 0
          || typeof payload.extendSelection !== "boolean"
          || typeof payload.option !== "boolean") {
        postResponse(request.requestId, false, {
          code: "INVALID_ARGUMENT",
          message: "editorDiscoveryAction requires a closed action and typed options",
        });
        break;
      }
      accept(request, () => callStatus(
        "oxsdk_editor_discovery_action",
        ["number", "number", "number", "number", "number", "number"],
        [request.requestId, payload.documentHandle, payload.expectedRevision,
          actionId, payload.extendSelection ? 1 : 0, payload.option ? 1 : 0],
      ));
      break;
    }
    case "editorDiscoverySelect": {
      const methodId = EDITOR_DISCOVERY_SELECTION_IDS[payload.method];
      const coordinates = [
        payload.startXTwips, payload.startYTwips,
        payload.endXTwips, payload.endYTwips,
      ];
      if (!Number.isInteger(methodId)
          || coordinates.some((value) => !Number.isInteger(value) || value < 0)) {
        postResponse(request.requestId, false, {
          code: "INVALID_ARGUMENT",
          message: "editorDiscoverySelect requires a closed method and non-negative integer twips",
        });
        break;
      }
      accept(request, () => callStatus(
        "oxsdk_editor_discovery_select",
        ["number", "number", "number", "number", "number", "number", "number"],
        [request.requestId, payload.documentHandle, methodId, ...coordinates],
      ));
      break;
    }
    case "editorDiscoveryGetState":
      accept(request, () => callStatus(
        "oxsdk_editor_discovery_get_state",
        ["number", "number"],
        [request.requestId, payload.documentHandle],
      ));
      break;
    case "finding016DrainScheduler":
      accept(request, () => callStatus(
        "oxsdk_editor_discovery_drain_scheduler",
        ["number", "number"],
        [request.requestId, payload.documentHandle],
      ));
      break;
    case "save":
      accept(request, () => withUtf8(String(payload.format || ""), (pointer, length) =>
        callStatus(
          "oxsdk_document_save",
          ["number", "number", "number", "number"],
          [request.requestId, payload.documentHandle, pointer, length],
        )));
      break;
    case "close":
      accept(request, () => callStatus(
        "oxsdk_document_close",
        ["number", "number"],
        [request.requestId, payload.documentHandle],
      ));
      break;
    default:
      postResponse(request.requestId, false, {
        code: "UNKNOWN_OPERATION",
        message: `unknown worker operation: ${request.operation}`,
      });
  }
}

function handleCancel(message) {
  if (!moduleInstance) {
    postEvent("cancel-result", {
      requestId: message.requestId,
      status: "NOT_STARTED",
    });
    return;
  }
  const status = callStatus("oxsdk_request_cancel", ["number"], [message.requestId]);
  postEvent("cancel-result", {
    requestId: message.requestId,
    status: STATUS_NAMES.get(status) || "UNKNOWN_STATUS",
  });
}

self.addEventListener("message", (event) => {
  const message = event.data;
  if (!message || message.protocolVersion !== PROTOCOL_VERSION) {
    if (message?.requestId) {
      postResponse(message.requestId, false, {
        code: "PROTOCOL_MISMATCH",
        message: `worker requires protocol version ${PROTOCOL_VERSION}`,
      });
    }
    return;
  }
  if (message.kind === "request")
    handleRequest(message);
  else if (message.kind === "cancel")
    handleCancel(message);
});
