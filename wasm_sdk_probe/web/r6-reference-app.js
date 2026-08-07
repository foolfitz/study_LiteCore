import { createDocumentEngine } from "./document-sdk.js";
import { ReaderSession } from "./reader-shell/reader-session.js";
import { CollaborationClient } from "./collaboration/collaboration-client.js";
import { CollaborationError } from "./collaboration/contract.js";
import {
  ProviderHost,
  ProviderRegistry,
  WorkerProviderAdapter,
  validateProviderOperation,
} from "./provider-sdk/provider-sdk.js";
import { descriptor } from "./providers/text-translate-descriptor.js";

const params = new URLSearchParams(location.search);
const role = params.get("role") === "bob" ? "bob" : "alice";
const actor = role === "alice"
  ? { actorId: "alice", displayName: "Alice（fixture identity；非正式登入）" }
  : { actorId: "bob", displayName: "Bob（fixture identity；非正式登入）" };
const documentId = "r6-reference-document";
const client = new CollaborationClient({ baseUrl: location.origin });
const $ = (selector) => document.querySelector(selector);

const metrics = {
  schemaVersion: 1,
  release: "R6-C",
  role,
  sessionId: `${role}-${crypto.randomUUID()}`,
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  ready: false,
  readerStates: [],
  sdkEvents: [],
  commands: [],
  typedErrors: [],
  workersCreated: 0,
  workersTerminated: 0,
  providerWorkersCreated: 0,
  providerWorkersTerminated: 0,
  tileDraws: 0,
  firstTileMs: null,
  staleAtMs: null,
  staleToReloadReadyMs: null,
  eventCursor: 0,
  eventRecovery: [],
  version: null,
  etag: null,
  sdkRevision: null,
  authorityVersion: null,
  authorityHash: null,
  localBytesAvailable: false,
  localBytesSha256: null,
  providerDocumentMutation: false,
  providerBoundary: null,
  conflict: null,
  fatalError: null,
};
globalThis.__probe_metrics = metrics;
globalThis.__r6_reference_metrics = metrics;

let reader = null;
let currentSnapshot = null;
let collaboration = null;
let heldLease = null;
let pendingLocal = null;
let activeDocumentWorker = null;
let providerRuntime = null;
let requestNumber = 0;
let commandNumber = 0;
let generation = 0;
let scale = 1;
let openedAt = performance.now();
let invalidationTimer = 0;

function request(fields = {}) {
  return {
    contractVersion: "1.0",
    requestId: `${metrics.sessionId}-${++requestNumber}`,
    ...fields,
  };
}

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  $("#log").textContent += `[${performance.now().toFixed(1)} ms] ${text}\n`;
  $("#log").scrollTop = $("#log").scrollHeight;
}

async function sha256(bytes) {
  const buffer = bytes instanceof ArrayBuffer
    ? bytes
    : bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
}

function list(element, items, render, empty) {
  element.replaceChildren();
  if (!items.length) {
    const item = document.createElement("li");
    item.textContent = empty;
    element.append(item);
    return;
  }
  for (const value of items) {
    const item = document.createElement("li");
    item.textContent = render(value);
    element.append(item);
  }
}

function updateCollaborationUi() {
  if (!collaboration)
    return;
  list($("#presence-list"), collaboration.presence,
    (item) => `${item.displayName}；view=${item.viewedVersion}${item.locationHint ? "；location hint" : ""}`,
    "無在線 fixture session");
  list($("#comment-list"), collaboration.comments,
    (item) => `${item.id} ${item.authorId}: ${item.body} [${item.status}]${item.parentId ? ` reply→${item.parentId}` : ""}`,
    "尚無 comment");
  list($("#suggestion-list"), collaboration.suggestions,
    (item) => `${item.id} ${item.anchor.quote} → ${item.replacement} [${item.status}] base=${item.baseVersion}`,
    "尚無 suggestion");
  $("#lease").textContent = heldLease
    ? `${heldLease.leaseId} / ${heldLease.actorId} / ${heldLease.expiresAt}`
    : collaboration.lease
      ? `${collaboration.lease.leaseId} / ${collaboration.lease.actorId}（token 已隱藏）`
      : "未持有";
  $("#authority-version").textContent = collaboration.current.version;
  metrics.authorityVersion = collaboration.current.version;
  metrics.authorityHash = collaboration.current.blobSha256;
  if (reader && currentSnapshot
      && collaboration.current.version !== currentSnapshot.version
      && ["ready", "saving"].includes(reader.state.snapshot.state)) {
    reader.markStale({
      documentId,
      previousVersion: currentSnapshot.version,
      version: collaboration.current.version,
      eventSequence: metrics.eventCursor,
    });
  }
}

function updateReaderUi(snapshot) {
  metrics.readerStates.push({ atMs: performance.now(), ...snapshot });
  metrics.version = snapshot.version;
  metrics.etag = snapshot.etag;
  metrics.sdkRevision = snapshot.sdkRevision;
  $("#status").textContent = snapshot.state;
  $("#status").dataset.state = snapshot.state;
  $("#reader-state").textContent = snapshot.state;
  $("#document-id").textContent = snapshot.documentId || "—";
  $("#version").textContent = snapshot.version || "—";
  $("#etag").textContent = snapshot.etag || "—";
  $("#revision").textContent = snapshot.sdkRevision ?? "—";
  $("#next-action").textContent = snapshot.nextAction;
  $("#profile").textContent = snapshot.profile || "—";
  $("#sdk-version").textContent = snapshot.sdkVersion || "—";
  $("#local-base").textContent = currentSnapshot?.version || snapshot.version || "—";
  $("#local-bytes").textContent = metrics.localBytesAvailable
    ? `${pendingLocal?.bytes?.byteLength || reader?.localBytes?.byteLength || 0} bytes（可下載）`
    : "無";
  if (snapshot.state === "stale" && metrics.staleAtMs === null)
    metrics.staleAtMs = performance.now();
}

function engineFactory() {
  return createDocumentEngine({
    workerUrl: "./profiles/writer-review-r6/sdk-worker.js",
    timeoutMs: 30000,
    workerFactory(url) {
      const worker = new Worker(url, { name: `r6-${role}-document-${metrics.workersCreated + 1}` });
      metrics.workersCreated += 1;
      let terminated = false;
      const control = {
        worker,
        terminate() {
          if (terminated)
            return;
          terminated = true;
          metrics.workersTerminated += 1;
          worker.terminate();
        },
        crash() {
          worker.dispatchEvent(new ErrorEvent("error", {
            message: `intentional R6-C ${role} Document Worker crash`,
          }));
          this.terminate();
        },
      };
      activeDocumentWorker = control;
      return {
        addEventListener: (...args) => worker.addEventListener(...args),
        postMessage: (...args) => worker.postMessage(...args),
        terminate: () => control.terminate(),
      };
    },
  });
}

function drawTile(entry) {
  if (entry.generation !== generation)
    return;
  metrics.tileDraws += 1;
  if (metrics.firstTileMs === null)
    metrics.firstTileMs = performance.now() - openedAt;
  let canvas = $("#tiles").querySelector(`[data-key="${CSS.escape(entry.key)}"]`);
  if (!canvas) {
    canvas = document.createElement("canvas");
    canvas.className = "document-tile";
    canvas.dataset.key = entry.key;
    $("#tiles").append(canvas);
  }
  canvas.width = entry.tile.width;
  canvas.height = entry.tile.height;
  canvas.style.left = `${entry.xPx}px`;
  canvas.style.top = `${entry.yPx}px`;
  canvas.style.width = `${entry.cssWidth}px`;
  canvas.style.height = `${entry.cssHeight}px`;
  canvas.getContext("2d").putImageData(new ImageData(
    new Uint8ClampedArray(entry.tile.pixels), entry.tile.width, entry.tile.height,
  ), 0, 0);
}

function scheduleViewport() {
  if (!reader?.scheduler || !["ready", "stale", "saving"].includes(reader.state.snapshot.state))
    return 0;
  $("#tiles").replaceChildren();
  generation = reader.scheduleViewport({
    scrollLeft: $("#viewport").scrollLeft,
    scrollTop: $("#viewport").scrollTop,
    width: $("#viewport").clientWidth,
    height: $("#viewport").clientHeight,
  });
  return generation;
}

function updateSurface() {
  const size = reader.scheduler.documentCssSize;
  $("#surface").style.width = `${Math.ceil(size.width)}px`;
  $("#surface").style.height = `${Math.ceil(size.height)}px`;
}

async function waitForTile(drawsBefore, timeoutMs = 30000) {
  const deadline = performance.now() + timeoutMs;
  while (metrics.tileDraws <= drawsBefore) {
    if (performance.now() >= deadline)
      throw new Error("stable viewport did not produce a tile");
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
}

async function renderStableViewport() {
  scheduleViewport();
  await reader.scheduler.drain();
  await new Promise((resolve) => setTimeout(resolve, 50));
  const before = metrics.tileDraws;
  scheduleViewport();
  await reader.scheduler.drain();
  await waitForTile(before);
}

async function fetchAuthoritySnapshot() {
  const metadata = (await client.getDocument(documentId)).data.current;
  const blob = await client.getBlob(documentId, metadata.version);
  const actualHash = await sha256(blob.bytes);
  if (actualHash !== metadata.blobSha256 || blob.etag !== metadata.etag)
    throw new CollaborationError("HASH_MISMATCH", "authority metadata and blob disagree");
  return {
    documentId,
    version: metadata.version,
    etag: metadata.etag,
    name: `${documentId}-${metadata.version}.odt`,
    bytes: blob.bytes,
    metadata,
  };
}

async function openReader(snapshot) {
  reader = new ReaderSession({
    engineFactory,
    onState: updateReaderUi,
    onTile: drawTile,
    onEvent(event) {
      metrics.sdkEvents.push(event);
      log({ sdkEvent: event });
      if (event.event === "document-invalidated") {
        clearTimeout(invalidationTimer);
        invalidationTimer = setTimeout(scheduleViewport, 20);
      }
    },
    tileOptions: {
      tileSizePx: 384,
      prefetchTiles: 1,
      maxInFlight: 2,
      maxCacheBytes: 32 * 1024 * 1024,
    },
  });
  openedAt = performance.now();
  await reader.open(snapshot);
  currentSnapshot = snapshot;
  updateSurface();
  await renderStableViewport();
}

async function reloadAuthority() {
  const started = performance.now();
  const snapshot = await fetchAuthoritySnapshot();
  if (!reader) {
    await openReader(snapshot);
  } else {
    const state = reader.state.snapshot.state;
    if (["ready", "saving"].includes(state)) {
      reader.markStale({
        documentId,
        previousVersion: reader.state.snapshot.version,
        version: snapshot.version,
        eventSequence: metrics.eventCursor,
      });
    }
    await reader.reload(snapshot, { discardLocalBytes: true });
    currentSnapshot = snapshot;
    pendingLocal = null;
    metrics.localBytesAvailable = false;
    metrics.localBytesSha256 = null;
    heldLease = null;
    scale = 1;
    updateSurface();
    await renderStableViewport();
  }
  if (metrics.staleAtMs !== null)
    metrics.staleToReloadReadyMs = performance.now() - metrics.staleAtMs;
  await refreshSnapshot(true);
  updateReaderUi(reader.state.snapshot);
  return { version: snapshot.version, etag: snapshot.etag, reloadMs: performance.now() - started };
}

async function refreshSnapshot(moveCursor = false) {
  const envelope = await client.getCollaboration(documentId);
  collaboration = envelope.data;
  if (moveCursor) {
    metrics.eventCursor = envelope.eventSequence;
    client.lastEventSequence.set(documentId, envelope.eventSequence);
  }
  updateCollaborationUi();
  return { eventSequence: envelope.eventSequence, version: collaboration.current.version };
}

async function heartbeat() {
  const result = await client.heartbeat(documentId, request({
    sessionId: metrics.sessionId,
    actorId: actor.actorId,
    displayName: actor.displayName,
    viewedVersion: currentSnapshot.version,
    locationHint: { page: Math.floor($("#viewport").scrollTop / 800) + 1 },
  }));
  await refreshSnapshot(true);
  return { sessionId: result.data.sessionId, presenceCount: collaboration.presence.length };
}

async function createComment(args = {}) {
  const result = await client.createComment(documentId, request({
    baseVersion: currentSnapshot.version,
    parentId: args.parentId ?? null,
    body: args.body || `${role} sidecar comment`,
    authorId: actor.actorId,
  }));
  await refreshSnapshot();
  return result.data;
}

async function resolveComment(args) {
  const result = await client.resolveComment(documentId, args.commentId, request({ actorId: actor.actorId }));
  await refreshSnapshot();
  return result.data;
}

async function replyLatestComment() {
  await refreshSnapshot();
  const parent = collaboration.comments.at(-1);
  if (!parent)
    throw new CollaborationError("NOT_FOUND", "there is no comment to reply to");
  return createComment({ parentId: parent.id, body: `${role} manual reply` });
}

async function resolveFirstOpenComment() {
  await refreshSnapshot();
  const comment = collaboration.comments.find((item) => item.status === "open");
  if (!comment)
    throw new CollaborationError("NOT_FOUND", "there is no open comment to resolve");
  return resolveComment({ commentId: comment.id });
}

function disposeProvider() {
  providerRuntime?.registry.dispose();
  providerRuntime = null;
}

function createProviderRuntime() {
  disposeProvider();
  let workerControl = null;
  const adapter = new WorkerProviderAdapter({
    workerUrl: "./providers/text-translate-worker.js",
    providerId: descriptor.id,
    contractVersion: descriptor.contractVersion,
    workerFactory(url) {
      const worker = new Worker(url, { type: "module", name: `r6-${role}-provider` });
      metrics.providerWorkersCreated += 1;
      let terminated = false;
      workerControl = {
        worker,
        crash() {
          worker.dispatchEvent(new ErrorEvent("error", { message: "intentional Provider Worker crash" }));
          if (!terminated) {
            terminated = true;
            metrics.providerWorkersTerminated += 1;
            worker.terminate();
          }
        },
      };
      return {
        addEventListener: (...args) => worker.addEventListener(...args),
        postMessage: (...args) => worker.postMessage(...args),
        terminate: () => {
          if (terminated)
            return;
          terminated = true;
          metrics.providerWorkersTerminated += 1;
          worker.terminate();
        },
      };
    },
  });
  const registry = new ProviderRegistry();
  registry.register(descriptor, adapter);
  providerRuntime = {
    adapter,
    registry,
    host: new ProviderHost({ registry, maxTextBytes: 1024 * 1024 }),
    get workerControl() { return workerControl; },
  };
  return providerRuntime;
}

async function validatedProviderOperation(quote = "LibreOfficeKit", options = {}) {
  const runtime = providerRuntime || createProviderRuntime();
  const found = await reader.document.search(quote);
  if (!found.found)
    throw new CollaborationError("ANCHOR_NOT_FOUND", "provider selection quote was not found");
  const revisionBefore = reader.document.revision;
  const documentAdapter = {
    async snapshotSelection() {
      return reader.document.getSelection();
    },
    async applyValidatedOperation(operation) {
      return { sidecarOnly: true, type: operation.type };
    },
  };
  const result = await runtime.host.invokeSelection({
    providerId: descriptor.id,
    endpointId: "translate-selection",
    documentAdapter,
    parameters: { "target-language": "zh-TW" },
    signal: options.signal,
  });
  metrics.providerDocumentMutation ||= reader.document.revision !== revisionBefore;
  return result;
}

async function providerSuggestion() {
  const result = await validatedProviderOperation("LibreOfficeKit");
  const created = await client.createSuggestion(documentId, request({
    baseVersion: currentSnapshot.version,
    anchor: { quote: "LibreOfficeKit", prefix: "", suffix: "" },
    replacement: result.operation.text,
    authorId: actor.actorId,
    audit: {
      providerId: result.providerId,
      endpointId: result.endpointId,
      invocationId: `${metrics.sessionId}-provider-${requestNumber}`,
    },
  }));
  await refreshSnapshot();
  return {
    suggestionId: created.data.id,
    replacement: created.data.replacement,
    sdkRevision: reader.document.revision,
    sidecarOnly: !metrics.providerDocumentMutation,
  };
}

async function createSuggestion(args) {
  const result = await client.createSuggestion(documentId, request({
    baseVersion: currentSnapshot.version,
    anchor: {
      quote: args.quote,
      prefix: args.prefix || "",
      suffix: args.suffix || "",
      ...(args.rectangles ? { locationHint: { rectangles: args.rectangles } } : {}),
    },
    replacement: args.replacement,
    authorId: actor.actorId,
  }));
  await refreshSnapshot();
  return result.data;
}

async function acquireLease() {
  const started = performance.now();
  const result = await client.acquireLease(documentId, request({
    actorId: actor.actorId,
    baseVersion: currentSnapshot.version,
  }));
  heldLease = result.data;
  await refreshSnapshot();
  return { ...heldLease, waitMs: performance.now() - started };
}

async function renewLease() {
  if (!heldLease)
    throw new CollaborationError("INVALID_LEASE", "this client does not hold a lease");
  const result = await client.renewLease(documentId, heldLease.leaseId, request({
    token: heldLease.token,
    baseVersion: heldLease.baseVersion,
  }));
  heldLease = result.data;
  await refreshSnapshot();
  return heldLease;
}

async function releaseLease() {
  if (!heldLease)
    throw new CollaborationError("INVALID_LEASE", "this client does not hold a lease");
  const lease = heldLease;
  const result = await client.releaseLease(documentId, lease.leaseId, request({ token: lease.token }));
  heldLease = null;
  await refreshSnapshot();
  return result.data;
}

async function acceptSuggestion(args) {
  await refreshSnapshot();
  const suggestion = collaboration.suggestions.find((item) => item.id === args.suggestionId);
  if (!suggestion)
    throw new CollaborationError("NOT_FOUND", "suggestion is missing");
  if (suggestion.status !== "open" || suggestion.baseVersion !== collaboration.current.version
      || currentSnapshot.version !== collaboration.current.version) {
    throw new CollaborationError("VERSION_CONFLICT", "suggestion or local document is not on current version", {
      suggestionBase: suggestion.baseVersion,
      localBase: currentSnapshot.version,
      authorityVersion: collaboration.current.version,
    });
  }
  if (!heldLease)
    await acquireLease();
  const classification = await reader.classifyAnchor(suggestion.anchor.quote);
  if (classification.classification !== "unique") {
    const code = classification.classification === "not-found"
      ? "ANCHOR_NOT_FOUND"
      : "ANCHOR_AMBIGUOUS";
    await client.decideSuggestion(documentId, suggestion.id, request({
      actorId: actor.actorId,
      decision: "conflict",
      reason: code,
    }));
    metrics.conflict = {
      code,
      authorityVersion: collaboration.current.version,
      localBaseVersion: currentSnapshot.version,
    };
    $("#conflict").textContent = `${code}；authority=${collaboration.current.version}；local=${currentSnapshot.version}`;
    await refreshSnapshot();
    throw new CollaborationError(code, `suggestion anchor is ${classification.classification}`);
  }
  const selection = await reader.document.getSelection();
  if (selection.text !== suggestion.anchor.quote)
    throw new CollaborationError("ANCHOR_NOT_FOUND", "exact selection text changed before mutation");
  await reader.replaceSelection(suggestion.replacement, reader.document.revision);
  const saveStarted = performance.now();
  const savedBytes = await reader.saveLocal();
  const saveMs = performance.now() - saveStarted;
  pendingLocal = {
    bytes: savedBytes.slice(0),
    baseVersion: currentSnapshot.version,
    baseEtag: currentSnapshot.etag,
  };
  metrics.localBytesAvailable = true;
  metrics.localBytesSha256 = await sha256(savedBytes);
  updateReaderUi(reader.state.snapshot);
  const putStarted = performance.now();
  const committed = await client.putBlob(documentId, request({
    baseVersion: currentSnapshot.version,
    ifMatch: currentSnapshot.etag,
    leaseId: heldLease.leaseId,
    token: heldLease.token,
    blobSha256: metrics.localBytesSha256,
    createdBy: actor.actorId,
    suggestionId: suggestion.id,
  }), savedBytes);
  const putMs = performance.now() - putStarted;
  if (committed.data.version.blobSha256 !== metrics.localBytesSha256)
    throw new CollaborationError("HASH_MISMATCH", "commit response hash differs from local save");
  heldLease = null;
  const committedVersion = committed.data.version;
  reader.markStale({
    documentId,
    previousVersion: currentSnapshot.version,
    version: committedVersion.version,
    eventSequence: committed.eventSequence,
  });
  const reloadResult = await reloadAuthority();
  $("#search").value = suggestion.replacement;
  $("#search-result").textContent = `目前版本的 replacement：${suggestion.replacement}`;
  return {
    version: committedVersion.version,
    etag: committedVersion.etag,
    blobSha256: committedVersion.blobSha256,
    saveMs,
    putMs,
    reloadMs: reloadResult.reloadMs,
    suggestionStatus: committed.data.suggestion.status,
  };
}

async function localEditAndSave(args = {}) {
  const quote = args.quote || "LibreOfficeKit";
  const result = await reader.document.search(quote);
  if (!result.found)
    throw new CollaborationError(
      "ANCHOR_NOT_FOUND",
      `目前版本找不到本機編輯目標「${quote}」；請先搜尋存在的文字`,
    );
  const selection = await reader.document.getSelection();
  if (selection.text !== quote)
    throw new CollaborationError("ANCHOR_NOT_FOUND", "local selection is not exact");
  await reader.replaceSelection(args.replacement || `${role}-uncommitted`, reader.document.revision);
  const bytes = await reader.saveLocal();
  pendingLocal = {
    bytes: bytes.slice(0),
    baseVersion: currentSnapshot.version,
    baseEtag: currentSnapshot.etag,
  };
  metrics.localBytesAvailable = true;
  metrics.localBytesSha256 = await sha256(bytes);
  if (args.quote && $("#search").value === args.quote) {
    $("#search").value = args.replacement;
    $("#search-result").textContent = `本機未提交 replacement：${args.replacement}`;
  }
  updateReaderUi(reader.state.snapshot);
  return { bytes: bytes.byteLength, sha256: metrics.localBytesSha256, revision: reader.document.revision };
}

function localEditFromSearch() {
  const quote = $("#search").value.trim();
  if (!quote)
    throw new CollaborationError("INVALID_ARGUMENT", "請先在搜尋欄輸入本機編輯目標");
  return localEditAndSave({
    quote,
    replacement: `${actor.actorId}-local-R6`,
  });
}

async function undoLocal() {
  const result = await reader.document.undo({ expectedRevision: reader.document.revision });
  reader.scheduler.invalidateRevision(result.revision);
  reader.state.update({ sdkRevision: result.revision, hasLocalBytes: false });
  reader.localBytes = null;
  pendingLocal = null;
  metrics.localBytesAvailable = false;
  metrics.localBytesSha256 = null;
  await renderStableViewport();
  updateReaderUi(reader.state.snapshot);
  return { revision: result.revision, localBytesAvailable: false };
}

async function acceptFirstOpenSuggestion() {
  await refreshSnapshot();
  const suggestion = collaboration.suggestions.find((item) => item.status === "open");
  if (!suggestion)
    throw new CollaborationError("NOT_FOUND", "there is no open suggestion to accept");
  return acceptSuggestion({ suggestionId: suggestion.id });
}

async function stalePut() {
  if (!pendingLocal)
    throw new CollaborationError("INVALID_ARGUMENT", "no local bytes are available for stale submit");
  try {
    await client.putBlob(documentId, request({
      baseVersion: pendingLocal.baseVersion,
      ifMatch: pendingLocal.baseEtag,
      leaseId: "stale-fixture-lease",
      token: "stale-fixture-token",
      blobSha256: await sha256(pendingLocal.bytes),
      createdBy: actor.actorId,
    }), pendingLocal.bytes);
  } catch (error) {
    metrics.conflict = {
      code: error.code,
      authorityVersion: (await client.getDocument(documentId)).data.current.version,
      localBaseVersion: pendingLocal.baseVersion,
      localBytesAvailable: true,
    };
    $("#conflict").textContent = `${error.code}；authority=${metrics.conflict.authorityVersion}；local=${pendingLocal.baseVersion}`;
    throw error;
  }
  throw new Error("stale PUT unexpectedly succeeded");
}

async function pollEvents() {
  const started = performance.now();
  const response = await client.eventsSince(documentId, metrics.eventCursor);
  let mode = response.data.mode;
  let applied = 0;
  if (mode === "snapshot") {
    collaboration = response.data.snapshot;
    metrics.eventCursor = response.eventSequence;
  } else {
    let expected = metrics.eventCursor + 1;
    for (const event of response.data.events) {
      if (event.eventSequence < expected)
        continue;
      if (event.eventSequence !== expected)
        throw new CollaborationError("EVENT_GAP", "event replay contains a gap");
      expected += 1;
      applied += 1;
      log({ collaborationEvent: event });
      if (event.type === "document-updated"
          && currentSnapshot.version !== event.data.version
          && ["ready", "saving"].includes(reader.state.snapshot.state)) {
        reader.markStale(event.data);
      }
    }
    metrics.eventCursor = response.eventSequence;
    await refreshSnapshot(false);
  }
  client.lastEventSequence.set(documentId, metrics.eventCursor);
  updateCollaborationUi();
  const result = {
    mode,
    applied,
    eventSequence: metrics.eventCursor,
    version: collaboration.current.version,
    comments: collaboration.comments.length,
    suggestions: collaboration.suggestions.length,
    recoveryMs: performance.now() - started,
  };
  metrics.eventRecovery.push(result);
  return result;
}

async function search(args = {}) {
  const query = args.query || $("#search").value;
  const result = await reader.search(query);
  $("#search-result").textContent = result.found ? `命中：${result.selectionText}` : "未命中";
  return result;
}

async function providerBoundaryRegression() {
  const selection = await search({ query: "LibreOfficeKit" });
  const input = {
    kind: "selection.text",
    text: selection.selectionText,
    revision: selection.revision,
    parameters: { "target-language": "zh-TW" },
  };
  const blocked = [];
  for (const [name, operation, endpointId, maximum] of [
    ["generic-uno", { type: ".uno:Bold", text: "x", expectedRevision: input.revision }, "translate-selection", 1024],
    ["unknown-operation", { type: "writeAnything", text: "x", expectedRevision: input.revision }, "translate-selection", 1024],
    ["wrong-endpoint", { type: "replaceSelection", text: "x", expectedRevision: input.revision }, "wrong-endpoint", 1024],
    ["oversized", { type: "replaceSelection", text: "x".repeat(65), expectedRevision: input.revision }, "translate-selection", 64],
  ]) {
    try {
      validateProviderOperation(operation, { descriptor, endpointId, input, maxTextBytes: maximum });
    } catch (error) {
      blocked.push({ name, code: error.code });
    }
  }
  const before = (await client.getCollaboration(documentId)).data.suggestions.length;
  const abortController = new AbortController();
  const cancelled = validatedProviderOperation("LibreOfficeKit", { signal: abortController.signal });
  setTimeout(() => abortController.abort(), 10);
  let cancelCode = null;
  try {
    await cancelled;
  } catch (error) {
    cancelCode = error.code;
  }
  const crashRuntime = createProviderRuntime();
  const crashing = validatedProviderOperation("LibreOfficeKit");
  setTimeout(() => crashRuntime.workerControl.crash(), 10);
  let crashCode = null;
  try {
    await crashing;
  } catch (error) {
    crashCode = error.code;
  }
  const documentStillAlive = (await search({ query: "LibreOfficeKit" })).found;
  createProviderRuntime();
  const restarted = await validatedProviderOperation("LibreOfficeKit");
  const after = (await client.getCollaboration(documentId)).data.suggestions.length;
  const result = {
    blocked,
    cancelCode,
    crashCode,
    documentStillAlive,
    restartedOperation: restarted.operation.type,
    suggestionsBefore: before,
    suggestionsAfter: after,
  };
  metrics.providerBoundary = result;
  if (blocked.length !== 4 || cancelCode !== "PROVIDER_ABORTED"
      || crashCode !== "PROVIDER_WORKER_CRASHED" || !documentStillAlive
      || restarted.operation.type !== "replaceSelection" || before !== after) {
    throw new Error("Provider boundary regression invariant failed");
  }
  return result;
}

async function crashWithLocalEdit(args = {}) {
  const quote = args.quote || "LibreOfficeKit";
  const found = await reader.document.search(quote);
  if (!found.found)
    throw new CollaborationError("ANCHOR_NOT_FOUND", "crash fixture quote is missing");
  await reader.document.getSelection();
  await reader.replaceSelection(args.replacement || "crash-local-edit", reader.document.revision);
  if (args.save) {
    const bytes = await reader.saveLocal();
    pendingLocal = {
      bytes: bytes.slice(0),
      baseVersion: currentSnapshot.version,
      baseEtag: currentSnapshot.etag,
    };
    metrics.localBytesAvailable = true;
    metrics.localBytesSha256 = await sha256(bytes);
  } else {
    pendingLocal = null;
    metrics.localBytesAvailable = false;
    metrics.localBytesSha256 = null;
  }
  activeDocumentWorker.crash();
  await new Promise((resolve) => setTimeout(resolve, 20));
  updateReaderUi(reader.state.snapshot);
  return {
    state: reader.state.snapshot.state,
    code: reader.state.snapshot.error?.code,
    saved: args.save === true,
    localBytesAvailable: metrics.localBytesAvailable,
    recoveryMessage: metrics.localBytesAvailable
      ? "已保存的本機 bytes 可下載；不自動重送 mutation"
      : "尚未 save 的本機修改不可恢復；不自動重送 mutation",
  };
}

async function advanceClock(args) {
  const result = await client.advanceClock(args.milliseconds);
  await refreshSnapshot();
  return { now: result.now, presenceCount: collaboration.presence.length };
}

const commands = {
  reloadAuthority,
  refresh: () => refreshSnapshot(false),
  heartbeat,
  createComment,
  replyLatestComment,
  resolveFirstOpenComment,
  resolveComment,
  providerSuggestion,
  createSuggestion,
  acquireLease,
  renewLease,
  releaseLease,
  acceptSuggestion,
  acceptFirstOpenSuggestion,
  localEditAndSave,
  localEditFromSearch,
  undoLocal,
  stalePut,
  pollEvents,
  search,
  providerBoundaryRegression,
  crashWithLocalEdit,
  advanceClock,
  zoom: async (args) => {
    scale = args.scale;
    reader.setScale(scale);
    updateSurface();
    await renderStableViewport();
    return { scale, generation };
  },
};

function startCommand(name, args = {}) {
  const id = ++commandNumber;
  const record = { id, name, args, status: "running", startedAtMs: performance.now() };
  metrics.commands.push(record);
  Promise.resolve().then(async () => {
    if (!commands[name])
      throw new CollaborationError("INVALID_ARGUMENT", `unknown UI command: ${name}`);
    const result = await commands[name](args);
    Object.assign(record, {
      status: "passed",
      durationMs: performance.now() - record.startedAtMs,
      result,
    });
    $("#message").textContent = `${name} 完成`;
    log({ command: name, status: "passed", result });
  }).catch((error) => {
    const normalized = {
      code: error.code || "UNEXPECTED",
      message: error.message || String(error),
      details: error.details || {},
    };
    Object.assign(record, {
      status: "failed",
      durationMs: performance.now() - record.startedAtMs,
      error: normalized,
    });
    metrics.typedErrors.push({ command: name, ...normalized });
    $("#message").textContent = `${normalized.code}: ${normalized.message}`;
    $("#message").classList.add("error");
    log({ command: name, status: "failed", error: normalized });
  });
  return id;
}

function bind(selector, name, args = () => ({})) {
  $(selector).addEventListener("click", () => startCommand(name, args()));
}

bind("#reload", "reloadAuthority");
bind("#heartbeat", "heartbeat");
bind("#comment", "createComment");
bind("#reply-comment", "replyLatestComment");
bind("#resolve-comment", "resolveFirstOpenComment");
bind("#manual-suggestion", "createSuggestion", () => ({
  quote: "LibreOfficeKit", replacement: `${actor.actorId}-manual-R6`,
}));
bind("#provider-suggestion", "providerSuggestion");
bind("#refresh", "refresh");
bind("#poll-events", "pollEvents");
bind("#acquire", "acquireLease");
bind("#renew", "renewLease");
bind("#release", "releaseLease");
bind("#accept-first", "acceptFirstOpenSuggestion");
bind("#local-edit-save", "localEditFromSearch");
bind("#cancel-local", "undoLocal");
bind("#search-next", "search", () => ({ query: $("#search").value }));
bind("#zoom-100", "zoom", () => ({ scale: 1 }));
bind("#zoom-150", "zoom", () => ({ scale: 1.5 }));
bind("#worker-crash", "crashWithLocalEdit", () => ({ save: false }));

function download(bytes, filename) {
  if (!bytes)
    return;
  const url = URL.createObjectURL(new Blob([bytes], { type: "application/vnd.oasis.opendocument.text" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

$("#download-authority").addEventListener("click", async () => {
  const snapshot = await fetchAuthoritySnapshot();
  download(snapshot.bytes, `${documentId}-${snapshot.version}.odt`);
});
$("#download-local").addEventListener("click", () =>
  download(pendingLocal?.bytes || reader?.localBytes, `${documentId}-${role}-uncommitted.odt`));

let scrollTimer = 0;
$("#viewport").addEventListener("scroll", () => {
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(scheduleViewport, 30);
});

$("#role").textContent = `${actor.displayName} / ${metrics.sessionId}`;
$("#identity").textContent = actor.displayName;
globalThis.__r6_reference = { startCommand };

Promise.resolve().then(async () => {
  currentSnapshot = await fetchAuthoritySnapshot();
  await openReader(currentSnapshot);
  await heartbeat();
  createProviderRuntime();
  metrics.ready = true;
  $("#message").textContent = `${role} ready；fixture identity，非正式登入`;
  log({ type: "reference-ready", role, version: currentSnapshot.version });
}).catch((error) => {
  metrics.fatalError = { code: error.code || "INIT_FAILED", message: String(error.stack || error) };
  $("#status").textContent = "fatal-error";
  $("#status").dataset.state = "fatal-error";
  $("#message").textContent = metrics.fatalError.message;
  $("#message").classList.add("error");
  log(metrics.fatalError);
});
