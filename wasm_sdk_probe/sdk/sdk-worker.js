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
  // redo rides on undo's capability rather than minting one, because it is the
  // same faculty: a profile that can walk the undo stack one way can walk it
  // the other, and a separate capability string would let a manifest claim a
  // half of it that the engine does not have halves of.
  ["redo", "undo"],
  ["addComment", "comments"],
  ["listComments", "comments"],
  ["setTrackChanges", "tracked-changes"],
  ["listTrackedChanges", "tracked-changes"],
  ["editorActionV1", "narrow-editor-v1"],
  ["editorGetStateV1", "narrow-editor-v1"],
  ["editorSelectRangeV1", "narrow-editor-v1"],
  ["editorActionV2", "narrow-editor-v2"],
  ["editorGetStateV2", "narrow-editor-v2"],
  ["editorSelectRangeV2", "narrow-editor-v2"],
  ["editorPlaceCaretV2", "narrow-editor-v2"],
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
// SPEC E2-B 5.11.  Wire ids 1-10 are v1's, unchanged, so a v2 caller sends the
// v1 ids for those; only the five paragraph actions are new here.
const EDITOR_V2_ACTION_IDS = Object.freeze({
  ...EDITOR_V1_ACTION_IDS,
  "set-list-none": 11,
  "set-list-unordered": 12,
  "set-list-ordered": 13,
  "set-paragraph-heading": 14,
  "set-paragraph-body": 15,
});
// ABI 4 appends six under a SUCCESSOR profile identity.  Ids 1-15 are spread in
// verbatim -- that is what "successor" means here, and the exact-match ABI
// handshake at init is what makes appending safe: a v3 client that reaches a v4
// profile dies with INCOMPATIBLE_ABI instead of sending id 16 to a binary where
// it means nothing.
//
// Widening the table does NOT widen what a v2 or v3 profile can dispatch: the
// manifest intersection below is what decides, and their manifests do not list
// these names.  That is exactly the job the intersection exists to do.
const EDITOR_V3_ACTION_IDS = Object.freeze({
  ...EDITOR_V2_ACTION_IDS,
  "move-line-up": 16,
  "move-line-down": 17,
  "move-line-home": 18,
  "move-line-end": 19,
  "delete-selection": 20,
  "select-all": 21,
});

// Neither option flag is accepted by the five paragraph actions (N7).
const EDITOR_V2_PARAGRAPH_ACTIONS = new Set([
  "set-list-none", "set-list-unordered", "set-list-ordered",
  "set-paragraph-heading", "set-paragraph-body",
]);

// SPEC E2-B 5.7: the manifest constrains, it does not merely describe.
//
// Intersection, and the direction is deliberate: a manifest can withhold an
// action this worker knows how to dispatch, and can never add one.  Without
// this the freeze condition "remove a capability and prove zero mutation" is
// unsatisfiable -- the worker would dispatch from its own hard-coded map
// whatever the manifest said.
function manifestAllowsAction(action) {
  const actions = activeManifest?.editorContract?.actions;
  if (!actions)
    return true;                      // v1 profiles carry a name list; unchanged
  if (Array.isArray(actions))
    return actions.includes(action);
  if (!Object.hasOwn(actions, action))
    return false;
  // WITHHELD IS NOT ABSENT, and both spellings have to mean the same thing here
  // or they mean different things to the client and the engine.
  //
  // An action ships dark by being PRESENT with no gestures -- it must be
  // present, because the engine initialises every entry to all-permitted on the
  // first mask call and an omitted action would keep that default.  Reading
  // presence alone would then report a dark action as offered, and the client
  // would build a control for something the engine refuses every time.
  const gestures = actions[action]?.gestures;
  if (Array.isArray(gestures) && gestures.length === 0)
    return false;
  return true;
}

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

// SPEC E2-B 5.5: which contract each editor operation belongs to, written out.
//
// This replaces `operation.startsWith("editor") && operation.endsWith("V1")`.
// That test encoded the contract in the SHAPE OF THE NAME, which is why a v2
// profile would have refused all ten existing actions: they are still spelled
// ...V1 and `editorV1Enabled()` requires editorContract.version === 1.
const EDITOR_OPERATIONS = new Map([
  ["editorActionV1", { capability: "narrow-editor-v1", version: 1 }],
  ["editorGetStateV1", { capability: "narrow-editor-v1", version: 1 }],
  ["editorSelectRangeV1", { capability: "narrow-editor-v1", version: 1 }],
  ["editorActionV2", { capability: "narrow-editor-v2", version: 2 }],
  ["editorGetStateV2", { capability: "narrow-editor-v2", version: 2 }],
  ["editorSelectRangeV2", { capability: "narrow-editor-v2", version: 2 }],
  ["editorPlaceCaretV2", { capability: "narrow-editor-v2", version: 2 }],
]);

// The operations whose result carries the PRODUCT projection of editor state.
// Keyed by membership, not by string equality with one name: the old test was
// `operation === "editorActionV1"`, so adding editorActionV2 beside it would
// have handed every v2 action the raw diagnostic state -- widening the product
// ABI and breaking E1-B's ban on exposing a11y/scheduler state.
const PRODUCT_EDITOR_OPERATIONS = new Set([
  "editorActionV1", "editorActionV2",
]);

function editorContractEnabled(operation) {
  const spec = EDITOR_OPERATIONS.get(operation);
  if (!spec)
    return true;   // not an editor operation; other gates apply
  return activeManifest?.capabilities?.includes(spec.capability)
    && activeManifest?.editorContract?.version === spec.version;
}

// The product projection of the format barrier.
//
// Named fields only, for the same reason productEditorState exists: the
// engine's barrier record carries diagnostic internals (stage counters,
// crosstalk counts, the raw readback markup) that the product contract does
// not promise and must not start promising by accident.  What a host needs is
// the shape, whether anything was dispatched, and which route ran.
function productFormatBarrier(value = {}) {
  return {
    failureShape: value.failureShape || "",
    // The disposition a host acts on.  A pre-dispatch refusal leaves the
    // document untouched; anything after the dispatch may have changed it, and
    // SPEC E2-B 5.13 says the response to that is a rollback to the last
    // checkpoint -- not a prompt to undo, which cannot run while the queue is
    // blocked by the same failure.
    // "idle" is the only stage a barrier can end in without having posted the
    // uno command: routing refuses before the stage advances (probe_engine.cpp
    // sets AwaitingResult immediately before postUnoCommand).  Everything else
    // means the command went out.
    dispatched: typeof value.stage === "string" && value.stage !== "idle",
    route: value.route ?? null,
    // Finding 046's identity gate, and whether it RAN.  Projected because this
    // allowlist is where engine fields go to be forgotten (p1-3c's itemCount),
    // and because a verdict reached WITHOUT the identity check is a different
    // verdict -- fail-open by design here, since failing closed would take
    // every format action down whenever accessibility is unavailable, but
    // never silently.
    paragraphIdentity: value.paragraphIdentity ?? null,
    preBlocks: value.preBlocks ?? null,
    postBlocks: value.postBlocks ?? null,
    // Whether those two counts were ever written.  Measured 2026-08-16
    // (findings/evidence/046/browser-vs-native/): `preBlocks` is assigned only
    // on the range routes and `postBlocks` only on the cross route, so on the
    // collapsed route both read 0 -- including on a barrier that SUCCEEDED
    // over a paragraph with text in it.  Two rounds of evidence, and finding
    // 046's whole native-versus-browser disagreement, rested on reading that
    // zero as "read the paragraph and found no blocks".
    //
    // Null on the shipped v2 engine, which does not send these: absent is the
    // honest answer for a build that cannot say.
    preBlocksObserved: value.preBlocksObserved ?? null,
    postBlocksObserved: value.postBlocksObserved ?? null,
    // The two readback facts a host needs to tell "nothing was read" from
    // "only list items were read" -- the distinction finding 046's remaining
    // criterion (relink queue 3b) is written on.  `itemCount` alone cannot do
    // it: the engine's `multiBlock` is `blockCount > 1 || itemCount > 1`, and
    // an empty read is `parsed: false` with every count at zero, which is
    // indistinguishable from a parsed read of nothing without this field.
    readbackParsed: value.readback?.parsed ?? null,
    readbackBlockCount: value.readback?.blockCount ?? null,
    // Does the selection the postcondition read describe cover the caret the
    // action was dispatched from?  The engine has checked this since finding
    // 034 and fails on it (`selection-does-not-contain-restore-point`), but
    // the answer never reached the product, so a host could not tell a verdict
    // about ITS paragraph from a verdict about a neighbour -- which is exactly
    // what happens on an empty paragraph, where the selection pair walks up
    // one paragraph (findings/evidence/046/native/).
    containment: value.containment
      ? { checked: value.containment.checked ?? null,
          held: value.containment.held ?? null }
      : null,
    // Not a diagnostic extra, which is why it is here despite the rule above.
    // The engine classifies with `multiBlock = blockCount > 1 || itemCount > 1`
    // (probe_engine.cpp), so a host that sees only postBlocks cannot tell
    // "nothing was read back" from "only list items were read back" -- and
    // SPEC E2-C 9.5.9 measured both landing on postBlocks 0 with different
    // outcomes on the same empty paragraph.  Finding 046's remaining criterion
    // rests on exactly that distinction, so without this field the criterion
    // can only be guessed at.  Nested under `readback` in the engine's record.
    itemCount: value.readback?.itemCount ?? null,
    crossIdentityHeld: value.crossIdentityHeld ?? null,
    crossStateHeld: value.crossStateHeld ?? null,
  };
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
      // Added 2026-08-19 with the engine cache for these two.  The allowlist
      // note below is not decoration: the engine started reporting underline
      // and strikethrough and the product still saw null, because nothing here
      // named them -- the same way the tile reply's document size was invisible
      // until the tile branch named it, in the same afternoon.
      underline: typeof value.format?.underline === "boolean"
        ? value.format.underline : null,
      strikethrough: typeof value.format?.strikethrough === "boolean"
        ? value.format.strikethrough : null,
    },
    // queue-verify-caret-by-block-identity.  This projection is an ALLOWLIST,
    // so an engine field that nothing adds here never reaches the product --
    // which is exactly how `itemCount` came to be measured natively and
    // reported nowhere (relink queue item p1-3c).  Adding the engine half
    // without this one would have repeated it.
    //
    // A fingerprint and an offset, never the paragraph's text: the engine keeps
    // the raw a11y payload closed on purpose, and the host's question is "is
    // this the same paragraph as before", not "what does it say".
    // `formatStale` is the validity bit for `format` directly above.  The
    // engine emitted it only in the main-loop build until 2026-08-17, so the
    // product shipped the cache without it.
    formatStale: typeof value.formatStale === "boolean" ? value.formatStale : null,
    caretParagraph: value.a11y ? {
      // `enabled` is not decoration.  The v3 link shipped with accessibility
      // never switched on, and the only symptom was that every paragraph read
      // back empty -- indistinguishable from a genuinely empty paragraph.  A
      // host that gets `enabled: false` knows the fingerprint means nothing;
      // one that only gets `observed` cannot tell.
      enabled: value.a11y.enabled === true,
      unavailable: value.a11y.unavailable || null,
      // Three different questions, and the v3 link proved they are different:
      // `enabled` = accessibility was switched on; `observed` = a callback has
      // fired at some point; `fresh` = the LAST synchronous read succeeded, so
      // the fingerprint below describes where the caret is NOW.
      fresh: value.a11y.paragraphFresh === true,
      observed: value.a11y.observed === true,
      fingerprint: value.a11y.paragraphFingerprint ?? null,
      length: typeof value.a11y.contentLength === "number"
        ? value.a11y.contentLength : null,
      offset: typeof value.a11y.position === "number"
        ? value.a11y.position : null,
      listPrefixLength: typeof value.a11y.listPrefixLength === "number"
        ? value.a11y.listPrefixLength : null,
      // ROADMAP 3.4.  The paragraph's TEXT, and its arrival here reverses the
      // closure the comment above describes rather than sneaking past it: the
      // fingerprint exists because "the host needs to compare, not to read",
      // which was true while the only consumer was the identity gate. A screen
      // reader needs to read, and measured 2026-08-22 no other layer has the
      // text -- the engine hashed it and dropped it, and `selectionText` is
      // the SELECTION, so reading a paragraph through it would mean changing
      // the user's selection to announce it.
      //
      // `null` rather than `""` when the profile does not carry it, and the
      // distinction is load-bearing: a profile built without
      // OXSDK_A11Y_PARAGRAPH_TEXT emits no field at all, and "" would say the
      // paragraph is empty. The manifest's `caretParagraphText` is how a host
      // tells the two apart BEFORE reading, the same way `redo` is declared.
      text: typeof value.a11y.paragraphText === "string"
        ? value.a11y.paragraphText : null,
    } : null,
    // ROADMAP 3.4's structure half.  A NAMED PROJECTION, not the engine's
    // diagnostic tree: the engine also emits `a11y.tree` on a diagnostic build
    // and that one carries depths, child counts and state bits, which is
    // exactly what E1-B forbids promoting.  Only the product shape is
    // forwarded, and only the fields a projection needs.
    //
    // `null` when absent rather than `[]`, for the same reason `text` is null
    // rather than "": a host must be able to tell "this profile does not carry
    // an outline" from "this document has no paragraphs". The manifest's
    // `documentOutline` says which before a host looks.
    documentOutline: (value.a11y && value.a11y.outline
                      && Array.isArray(value.a11y.outline.paragraphs))
      ? {
          paragraphCount: value.a11y.outline.paragraphCount ?? null,
          // The caps travel with the data. A projection that cannot tell a
          // short document from a truncated one is the 64-child bound all
          // over again, one layer up.
          cap: value.a11y.outline.cap ?? null,
          textCap: value.a11y.outline.textCap ?? null,
          paragraphs: value.a11y.outline.paragraphs.map((p) => ({
            role: p.role,
            level: typeof p.level === "number" ? p.level : null,
            focused: p.focused === true,
            textLength: typeof p.textLength === "number" ? p.textLength : null,
            text: typeof p.text === "string" ? p.text : "",
          })),
        }
      : null,
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
          // Finding 062: the document's size, as of this paint.  The reply is
          // whitelisted rather than forwarded wholesale, so a field the engine
          // starts sending is invisible to every client until it is named here
          // -- which is why adding it to the engine alone changed nothing.
          documentWidthTwips: event.documentWidthTwips,
          documentHeightTwips: event.documentHeightTwips,
          documentSizeChanged: event.documentSizeChanged,
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
    // FINDING 071.  The engine has emitted `redone` since redo was added and
    // nothing here listened, so the request never completed: the session sat
    // busy forever, the toolbar's `run()` never resolved so not even a failure
    // toast appeared, and the next save queued behind it and timed out. A
    // capability that hangs the session is worse than one that is absent.
    //
    // Fourth layer of the same lag the ABI 4 link has now found three times --
    // client, session allowlist, page label map, and here. Each one was a
    // separate list of what exists, and each was updated on its own.
    case "redone":
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
          state: PRODUCT_EDITOR_OPERATIONS.has(operation)
            ? productEditorState(event.state)
            : event.state,
        };
        if (!PRODUCT_EDITOR_OPERATIONS.has(operation))
          result.selectionBarrier = event.selectionBarrier;
        // SPEC E2-B section 5 item 5: promising a typed failure shape and not
        // forwarding it makes the promise unkeepable on the product.  The
        // diagnostic profile has been getting this by a builder patch, which
        // is itself the evidence that the shared worker never forwarded it.
        if (event.formatBarrier)
          result.formatBarrier = productFormatBarrier(event.formatBarrier);
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
    // The answer to "where did the caret go", forwarded whole.  The state goes
    // through the product projection like every other product operation's, so
    // the paragraph fingerprint and offset reach the host and the document's
    // text does not.
    case "editor-caret-placed":
      if (requestId) {
        complete(requestId, {
          revision: event.revision,
          completion: event.completion,
          callbackSequenceBefore: event.callbackSequenceBefore,
          callbackSequenceAfter: event.callbackSequenceAfter,
          state: productEditorState(event.state),
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
          // THE SECOND WRITER, and it had to be found by measuring.
          //
          // Adding `caretParagraph` to the `editor-state` announcement alone
          // was not enough: `editor-session.js` REPLACES the page's
          // `editorState` with this reply, while the announcement MERGES into
          // it. So whichever landed last decided whether the projected name
          // existed, and roadmap 3.4's projection reported "no paragraph" on
          // two of three caret placements -- the exact half-working shape that
          // motivated carrying the name at all.
          //
          // Same function as the actions use, for the same reason: two copies
          // of a projection rule drift.  Both projected fields -- see the
          // announcement's copy of this comment for what leaving one out cost.
          caretParagraph: productEditorState(event).caretParagraph,
          documentOutline: productEditorState(event).documentOutline,
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
      // FINDING 068.  Forwarded on EVERY profile, not just a discovery one.
      //
      // The engine announces each editor state change and names the callback
      // that caused it.  This was gated behind `editorDiscoveryEnabled()`,
      // which is false on a product profile because the builder pops
      // `diagnostic` from the manifest -- so on the shipped product these
      // events were constructed and then dropped.
      //
      // What that cost: the page's only other source of editor state is the
      // drain's `getState()`, called once per queued operation, and insert
      // replies immediately after `paste()`.  Measured, eleven runs: the
      // page's last read is answered at sourceSequence 5 and the cursor
      // callback carrying the new rectangle is sequence 6.  Nothing asked
      // again, so the caret stayed where it was before the text -- which is
      // exactly what an operator reported twice, two days running.
      //
      // This exposes NOTHING NEW: every field below is already in the reply
      // the product's own `editorGetStateV2` returns (see "editor-state-result"
      // above).  The gate was withholding an announcement, not a surface.
      {
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
          // MEASURED 2026-08-23: the page NEVER holds the product projection.
          //
          // `productEditorState` is applied to the v2 ACTIONS' replies, and
          // this announcement -- which fires on every engine state change and
          // is gated only on a rising sourceSequence -- is the most frequent
          // writer of the page's `editorState`. So the page's snapshot is the
          // raw shape essentially always: three caret placements, `a11y`
          // present every time and `caretParagraph` absent every time.
          //
          // That means the same datum reaches the page under two names
          // depending on which reply landed last, and a consumer cannot know
          // which one it holds. Roadmap 3.4's projection is exactly such a
          // consumer, and "works after an action, silent after a state read"
          // is the half-working failure this tree keeps paying for.
          //
          // ADDED, not swapped. Removing the raw fields is the right end state
          // (E1-B bans promoting a11y counters and the scheduler probe to
          // product state, and today they are on the page) but it is a
          // different, wider change with its own blast radius -- recorded as
          // `queue-product-page-holds-the-raw-editor-state`. One name that is
          // always there is what 3.4 needs; taking the other away can wait for
          // a round that can measure what it breaks.
          //
          // Derived from the SAME function the actions use, never a second
          // copy of the rule: two copies of a projection drift.
          //
          // BOTH projected fields, and the second one is here because leaving
          // it out is the mistake this comment already describes: roadmap
          // 3.4's structure reached the worker and stopped, because only
          // `caretParagraph` had been added to the raw branches. The page
          // reads the raw shape, so a projected field that is not listed here
          // does not exist as far as the product is concerned.
          caretParagraph: productEditorState(event).caretParagraph,
          documentOutline: productEditorState(event).documentOutline,
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
          // The failure shape rides here.  Without it the host cannot tell a
          // pre-dispatch refusal (nothing changed) from a dispatched-but-
          // unverified outcome (roll back), and those want opposite responses.
          formatBarrier: event.formatBarrier
            ? productFormatBarrier(event.formatBarrier) : undefined,
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
    // SPEC E2-B 5.4: the editor ABI is versioned separately, and the manifest's
    // abiVersion is a CLAIM while the binary's is a fact.  Findings 027/036 are
    // about those two coming apart -- a profile is assembled, the hash is not a
    // function of the source, and a stale wasm beside a fresh manifest runs
    // today with nobody the wiser.  Exact match, because an allowlist's
    // version is an identity, not a range.
    const contract = activeManifest?.editorContract;
    if (contract && typeof contract.abiVersion === "number") {
      const actualEditorAbi = Number(ccall("oxsdk_editor_abi_version", "number"));
      if (actualEditorAbi !== contract.abiVersion) {
        fail(request.requestId, "INCOMPATIBLE_ABI",
             `editor ABI ${actualEditorAbi} in this binary does not match `
             + `${contract.abiVersion} declared by profile `
             + `${activeManifest?.profile || "unknown"}`);
        return;
      }
    }

    // SPEC E2-B 5.7: push the manifest's gesture restrictions into the engine.
    //
    // The engine reads no manifest, and the mask cannot ride on a dispatch
    // because both option flags must be 0 for the paragraph actions.  Without
    // this call the `gestures` field is decorative: it would describe a
    // narrowing that nothing enforces, which is the defect 5.7 exists to
    // remove.  Narrowing only -- the engine intersects.
    const actions = contract?.actions;
    const bits = contract?.gestureBits;
    if (actions && bits && !Array.isArray(actions)) {
      for (const [name, spec] of Object.entries(actions)) {
        if (!Number.isInteger(spec?.id) || !Array.isArray(spec?.gestures))
          continue;
        let mask = 0;
        for (const gesture of spec.gestures)
          mask |= Number(bits[gesture]) || 0;
        callStatus("oxsdk_editor_set_action_gestures", ["number", "number"],
                   [spec.id, mask]);
      }
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
  if (!editorContractEnabled(request.operation)) {
    postResponse(request.requestId, false, {
      code: "UNSUPPORTED_OPERATION",
      message: `${request.operation} requires an editor profile declaring `
        + `${EDITOR_OPERATIONS.get(request.operation).capability} at contract `
        + `version ${EDITOR_OPERATIONS.get(request.operation).version}`,
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
    // A document-level operation and NOT an editor action, so it has no wire id
    // and no gesture -- the same shape as undo, which it is the sibling of.
    // The relink queue asked for `"redo": 16` in this file; that criterion was
    // written before the design and describes a different remedy. Giving redo a
    // wire id would put it in the action table, where the gesture mask and the
    // extendSelection/enabled validation apply to it, and none of the three has
    // a meaning for walking the undo stack.
    case "redo":
      accept(request, () => callStatus(
        "oxsdk_document_redo",
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
    case "editorActionV2": {
      const actionId = EDITOR_V3_ACTION_IDS[payload.action];
      const forbiddenFields = ["keyCode", "unoCommand", "command"];
      const hasForbiddenField = forbiddenFields.some((field) =>
        Object.hasOwn(payload, field));
      const validRevision = Number.isInteger(payload.expectedRevision)
        && payload.expectedRevision >= 0
        && payload.expectedRevision <= 0xffffffff;
      const typedFlags = typeof payload.extendSelection === "boolean"
        && typeof payload.enabled === "boolean";
      const paragraph = EDITOR_V2_PARAGRAPH_ACTIONS.has(payload.action);
      // Both flags strictly false for the five paragraph actions: neither has
      // a meaning there, and a flag with no meaning that is accepted anyway is
      // a field somebody will eventually set.
      const validMoveOption = paragraph
        ? payload.extendSelection === false
        : (EDITOR_V1_MOVE_ACTIONS.has(payload.action)
           || payload.extendSelection === false);
      const validFormatOption = paragraph
        ? payload.enabled === false
        : (EDITOR_V1_FORMAT_ACTIONS.has(payload.action)
           || payload.enabled === false);
      if (!Number.isInteger(actionId) || !validRevision || !typedFlags
          || !validMoveOption || !validFormatOption || hasForbiddenField) {
        postResponse(request.requestId, false, {
          code: "INVALID_ARGUMENT",
          message: "editorActionV2 requires a closed action and typed options",
        });
        break;
      }
      if (!manifestAllowsAction(payload.action)) {
        postResponse(request.requestId, false, {
          code: "UNSUPPORTED_OPERATION",
          message: `${payload.action} is not offered by profile `
            + `${activeManifest?.profile || "unknown"}`,
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
    case "editorGetStateV2":
      accept(request, () => callStatus(
        "oxsdk_editor_get_state",
        ["number", "number"],
        [request.requestId, payload.documentHandle],
      ));
      break;
    // SPEC E1-D.  The selection method is not a parameter: the engine entry
    // point is hard-wired to the setTextSelection path, because the
    // synthesised-mouse-event path reports success while selecting nothing
    // (SPEC E1-D section 2.1).  A range that selects nothing is a valid
    // outcome; the caller judges by reading the selection back.
    // queue-verify-caret-by-block-identity.  `click` replies before core has
    // processed anything and says nothing about where the caret went, so every
    // caller had to invert the mapping and guess from a rectangle -- findings
    // 048, 051 and 052 are that inversion's three shapes.  This one answers
    // with the caret paragraph's fingerprint and the offset in it, and it
    // answers even when nothing moved, which is the case the 30-second waits
    // were made of.
    case "editorPlaceCaretV2": {
      if (!Number.isInteger(payload.xTwips) || payload.xTwips < 0
          || !Number.isInteger(payload.yTwips) || payload.yTwips < 0) {
        postResponse(request.requestId, false, {
          code: "INVALID_ARGUMENT",
          message: `${request.operation} requires non-negative integer twips`,
        });
        break;
      }
      accept(request, () => callStatus(
        "oxsdk_editor_place_caret",
        ["number", "number", "number", "number"],
        [request.requestId, payload.documentHandle,
          payload.xTwips, payload.yTwips],
      ));
      break;
    }
    case "editorSelectRangeV2":
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
          message: `${request.operation} requires four non-negative integer `
            + "twips and no method",
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
