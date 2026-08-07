import { createDocumentEngine } from "./sdk/document-sdk.js";
import { EditorDiscoveryClient } from "./e1/editor-discovery-client.js";

const status = document.querySelector("#status");
const logNode = document.querySelector("#log");
const canvas = document.querySelector("#canvas");
const context = canvas.getContext("2d");
const queryParameters = new URLSearchParams(location.search);
const smokeMode = queryParameters.get("smoke") === "1";
const boundarySmokeMode = queryParameters.get("boundarySmoke") === "1";
const outputs = new Map();
const metrics = {
  schemaVersion: 1,
  release: "E1-Finding-016-selection-barrier",
  mode: boundarySmokeMode ? "boundary-smoke" : (smokeMode ? "smoke" : "full"),
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  phase: "starting",
  complete: false,
  pass: false,
  decision: null,
  positiveCases: [],
  boundaryCases: [],
  events: [],
  outputs: [],
  rawCallbackExposed: false,
  automaticRetry: false,
  error: null,
};

globalThis.__finding_016_selection_barrier = metrics;
globalThis.__probe_metrics = metrics;
globalThis.__finding_016_selection_barrier_get_outputs = () => {
  const encoded = {};
  for (const [name, buffer] of outputs) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 0x8000)
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
    encoded[name] = btoa(binary);
  }
  return encoded;
};

function log(value) {
  logNode.textContent += `${typeof value === "string" ? value : JSON.stringify(value)}\n`;
}

function checkpoint(name, detail = {}) {
  metrics.phase = name;
  status.textContent = name;
  log({ checkpoint: name, ...detail });
}

function errorValue(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: String(error?.message || error),
    details: error?.details || null,
  };
}

function firstRectangle(searchResult) {
  const value = searchResult?.selections?.[0]?.rectangles || "";
  const values = value.split(";")[0].split(",")
    .map((item) => Number.parseInt(item.trim(), 10));
  if (values.length !== 4 || values.some((item) => !Number.isFinite(item)))
    throw new Error("search did not return a usable anchor rectangle");
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

function expectedCodePoints(text) {
  return Array.from(text, (value) => value.codePointAt(0));
}

function equalNumbers(left, right) {
  return Array.isArray(left) && left.length === right.length
    && left.every((value, index) => value === right[index]);
}

async function placeCaret(documentHandle, client, query, boundary) {
  const selected = await documentHandle.search(query, { timeoutMs: 30000 });
  if (!selected.found)
    throw new Error(`caret anchor is missing: ${query}`);
  const rectangle = firstRectangle(selected);
  const x = boundary === "start"
    ? rectangle.x + 1
    : rectangle.x + Math.max(1, rectangle.width - 1);
  const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  await client.select("selection-reset-unstable", {
    startXTwips: x,
    startYTwips: y,
    endXTwips: x,
    endYTwips: y,
  }, { timeoutMs: 30000 });
  const state = await client.getState({ timeoutMs: 30000 });
  const pass = state.selectionType === "none"
    && state.selection?.observed === true
    && state.selection?.collapsed === true;
  if (!pass)
    throw new Error(`caret did not collapse at ${boundary} of ${query}`);
  return { rectangle, x, y, state };
}

async function render(documentHandle) {
  const tile = await documentHandle.render({
    xTwips: 0,
    yTwips: 0,
    widthTwips: Math.min(documentHandle.widthTwips, 12240),
    heightTwips: Math.min(documentHandle.heightTwips, 15840),
    canvasWidthPx: canvas.width,
    canvasHeightPx: canvas.height,
  }, { timeoutMs: 180000 });
  context.putImageData(
    new ImageData(new Uint8ClampedArray(tile.pixels), tile.width, tile.height),
    0,
    0,
  );
}

async function openFixture(engine, corpus, fixtureId) {
  const fixture = corpus.fixtures.find((item) => item.id === fixtureId);
  if (!fixture)
    throw new Error(`fixture is unavailable: ${fixtureId}`);
  const input = await (await fetch(`./e1-fixtures/${fixture.path}`)).arrayBuffer();
  const documentHandle = await engine.open(input, {
    name: fixture.path,
    transfer: true,
    timeoutMs: 180000,
  });
  await render(documentHandle);
  return { fixture, documentHandle, client: new EditorDiscoveryClient(documentHandle) };
}

async function runPositive(documentHandle, client, definition) {
  const record = { id: definition.id, repetitions: [] };
  metrics.positiveCases.push(record);
  const repetitionCount = smokeMode ? 1 : 3;
  for (let repetition = 1; repetition <= repetitionCount; ++repetition) {
    checkpoint("positive", { id: definition.id, repetition });
    const placement = await placeCaret(
      documentHandle,
      client,
      definition.anchor,
      definition.boundary,
    );
    const beforeRevision = documentHandle.revision;
    const actionStarted = performance.now();
    try {
      const deletion = await client.action(definition.action, { timeoutMs: 30000 });
      const actionMs = performance.now() - actionStarted;
      const mutated = await documentHandle.search(definition.mutated, { timeoutMs: 30000 });
      const original = await documentHandle.search(definition.original, { timeoutMs: 30000 });
      const undo = await documentHandle.undo({
        expectedRevision: documentHandle.revision,
        timeoutMs: 30000,
      });
      const restored = await documentHandle.search(definition.original, { timeoutMs: 30000 });
      const selectedTextMatches = deletion.selectionBarrier?.selectedText
        === definition.selected
        && equalNumbers(
          deletion.selectionBarrier?.codePoints,
          expectedCodePoints(definition.selected),
        );
      const entry = {
        repetition,
        status: "passed",
        beforeRevision,
        revision: deletion.revision,
        revisionDelta: deletion.revision - deletion.beforeRevision,
        changed: deletion.changed,
        completion: deletion.completion,
        actionMs,
        selectedText: deletion.selectionBarrier?.selectedText ?? null,
        selectedTextMatches,
        selectionBarrier: deletion.selectionBarrier,
        placement: { x: placement.x, y: placement.y },
        exactMutation: mutated.found === true && original.found === false,
        undoRevisionDelta: undo.revision - deletion.revision,
        undoRestored: restored.found === true,
      };
      entry.status = entry.revisionDelta === 1
        && entry.changed === true
        && entry.completion === "verified-selection-delete"
        && entry.selectedTextMatches
        && entry.exactMutation
        && entry.undoRevisionDelta === 1
        && entry.undoRestored
        ? "passed"
        : "failed";
      record.repetitions.push(entry);
      log({ positive: definition.id, ...entry });
    } catch (error) {
      const entry = {
        repetition,
        status: "failed",
        beforeRevision,
        error: errorValue(error),
      };
      record.repetitions.push(entry);
      log({ positive: definition.id, ...entry });
      throw error;
    }
  }
}

async function runBoundary(documentHandle, client, definition) {
  checkpoint("boundary", { id: definition.id });
  await placeCaret(documentHandle, client, definition.anchor, definition.boundary);
  const beforeRevision = documentHandle.revision;
  const actionStarted = performance.now();
  let error = null;
  let deletion = null;
  try {
    deletion = await client.action(definition.action, { timeoutMs: 30000 });
  } catch (caught) {
    error = errorValue(caught);
    if (error.code !== "EDITOR_BOUNDARY_UNSUPPORTED") {
      const entry = {
        id: definition.id,
        status: "failed",
        code: error.code,
        error,
        deletion: null,
        beforeRevision,
        actionMs: performance.now() - actionStarted,
        afterActionRevision: beforeRevision,
        revisionDelta: 0,
        contentUnchanged: null,
        verificationSkipped: "unexpected action error requires a fresh worker",
      };
      metrics.boundaryCases.push(entry);
      log({ boundary: entry });
      throw caught;
    }
  }
  if (deletion?.changed === true) {
    await documentHandle.undo({
      expectedRevision: documentHandle.revision,
      timeoutMs: 30000,
    });
  }
  const unchanged = await documentHandle.search(definition.unchanged, { timeoutMs: 30000 });
  const entry = {
    id: definition.id,
    status: error?.code === "EDITOR_BOUNDARY_UNSUPPORTED" ? "rejected" : "failed",
    code: error?.code || null,
    error,
    deletion,
    actionMs: performance.now() - actionStarted,
    beforeRevision,
    afterActionRevision: deletion?.revision ?? beforeRevision,
    revisionDelta: deletion?.revision ? deletion.revision - beforeRevision : 0,
    contentUnchanged: unchanged.found === true,
  };
  metrics.boundaryCases.push(entry);
  log({ boundary: entry });
}

async function saveFinal(documentHandle, name, anchors) {
  const buffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
  outputs.set(name, buffer);
  metrics.outputs.push({ name, bytes: buffer.byteLength, anchors });
}

async function createTestEngine() {
  const engine = await createDocumentEngine({
    workerUrl: "./profiles/finding-016-selection-barrier/sdk-worker.js",
    timeoutMs: 30000,
    closeRecoveryTimeoutMs: 10000,
  });
  metrics.manifest ??= engine.manifest;
  engine.onEvent((event) => {
    if (["editor-state", "editor-callback-parse-error", "worker-crashed"].includes(event.event))
      metrics.events.push(event);
  });
  return engine;
}

async function runIsolatedBoundary(corpus, fixtureId, definition, outputName, anchors) {
  let engine = null;
  let documentHandle = null;
  try {
    engine = await createTestEngine();
    const opened = await openFixture(engine, corpus, fixtureId);
    documentHandle = opened.documentHandle;
    await runBoundary(documentHandle, opened.client, definition);
    await saveFinal(documentHandle, outputName, anchors);
    await documentHandle.close({ timeoutMs: 30000 });
    documentHandle = null;
  } finally {
    if (documentHandle) {
      try {
        await documentHandle.close({ timeoutMs: 10000 });
      } catch {}
    }
    engine?.dispose();
  }
}

async function run() {
  let engine = null;
  let documentHandle = null;
  try {
    checkpoint("load-corpus");
    const corpus = await (await fetch("./e1-fixtures/manifest.json", { cache: "no-cache" })).json();
    checkpoint("initialize-engine");
    engine = await createTestEngine();

    let opened = await openFixture(engine, corpus, "plain-grapheme");
    documentHandle = opened.documentHandle;
    let client = opened.client;
    const positives = [
      { id: "ascii-forward", anchor: "0123456789", boundary: "start", action: "delete-forward", selected: "0", original: "ASCII abc XYZ 0123456789", mutated: "ASCII abc XYZ 123456789" },
      { id: "ascii-backward", anchor: "0123456789", boundary: "end", action: "delete-backward", selected: "9", original: "ASCII abc XYZ 0123456789", mutated: "ASCII abc XYZ 012345678" },
      { id: "zh-forward", anchor: "臺灣中文游標測試", boundary: "start", action: "delete-forward", selected: "臺", original: "臺灣中文游標測試", mutated: "灣中文游標測試" },
      { id: "zh-backward", anchor: "臺灣中文游標測試", boundary: "end", action: "delete-backward", selected: "試", original: "臺灣中文游標測試", mutated: "臺灣中文游標測" },
      { id: "emoji-forward", anchor: "😀", boundary: "start", action: "delete-forward", selected: "😀", original: "emoji 😀 grapheme", mutated: "emoji  grapheme" },
      { id: "emoji-backward", anchor: "😀", boundary: "end", action: "delete-backward", selected: "😀", original: "emoji 😀 grapheme", mutated: "emoji  grapheme" },
      { id: "combining-forward", anchor: "é", boundary: "start", action: "delete-forward", selected: "é", original: "combining é boundary", mutated: "combining  boundary" },
      { id: "combining-backward", anchor: "é", boundary: "end", action: "delete-backward", selected: "é", original: "combining é boundary", mutated: "combining  boundary" },
    ];
    const selectedPositives = boundarySmokeMode
      ? []
      : (smokeMode ? positives.slice(0, 1) : positives);
    for (const definition of selectedPositives)
      await runPositive(documentHandle, client, definition);

    if (smokeMode) {
      await saveFinal(documentHandle, "plain-smoke.odt", [
        "E1-PLAIN-START", "臺灣中文游標測試", "emoji 😀 grapheme",
        "combining é boundary", "E1-PLAIN-END",
      ]);
      metrics.rawCallbackExposed = metrics.events.some((event) =>
        "payload" in event || "resultPayload" in event || event.event === "lok");
      const smokeEntry = metrics.positiveCases[0]?.repetitions?.[0];
      metrics.pass = metrics.crossOriginIsolated
        && metrics.manifest?.profile === "finding-016-selection-barrier"
        && metrics.manifest?.diagnostic?.stateWordCountUsedForCompletion === false
        && smokeEntry?.status === "passed"
        && metrics.outputs.length === 1
        && !metrics.rawCallbackExposed;
      metrics.decision = metrics.pass ? "SMOKE_PASS" : "STOP_OR_RESCOPE";
      checkpoint("close-smoke", { pass: metrics.pass, decision: metrics.decision });
      await documentHandle.close({ timeoutMs: 30000 });
      documentHandle = null;
      engine.dispose();
      engine = null;
      return;
    }

    if (boundarySmokeMode) {
      await runBoundary(documentHandle, client, {
        id: "document-start-backward",
        anchor: "E1-PLAIN-START",
        boundary: "start",
        action: "delete-backward",
        unchanged: "E1-PLAIN-START",
      });
      await saveFinal(documentHandle, "plain-boundary-smoke.odt", [
        "E1-PLAIN-START", "臺灣中文游標測試", "emoji 😀 grapheme",
        "combining é boundary", "E1-PLAIN-END",
      ]);
      const boundaryEntry = metrics.boundaryCases[0];
      metrics.rawCallbackExposed = metrics.events.some((event) =>
        "payload" in event || "resultPayload" in event || event.event === "lok");
      metrics.pass = metrics.crossOriginIsolated
        && metrics.manifest?.profile === "finding-016-selection-barrier"
        && boundaryEntry?.status === "rejected"
        && boundaryEntry?.revisionDelta === 0
        && boundaryEntry?.contentUnchanged === true
        && metrics.outputs.length === 1
        && !metrics.rawCallbackExposed;
      metrics.decision = metrics.pass
        ? "BOUNDARY_SMOKE_PASS"
        : "STOP_OR_RESCOPE";
      checkpoint("close-boundary-smoke", {
        pass: metrics.pass,
        decision: metrics.decision,
      });
      await documentHandle.close({ timeoutMs: 30000 });
      documentHandle = null;
      engine.dispose();
      engine = null;
      return;
    }

    await saveFinal(documentHandle, "plain-positive-final.odt", [
      "E1-PLAIN-START", "臺灣中文游標測試", "emoji 😀 grapheme",
      "combining é boundary", "E1-PLAIN-END",
    ]);
    await documentHandle.close({ timeoutMs: 30000 });
    documentHandle = null;
    engine.dispose();
    engine = null;

    const plainAnchors = [
      "E1-PLAIN-START", "臺灣中文游標測試", "emoji 😀 grapheme",
      "combining é boundary", "E1-PLAIN-END",
    ];
    const tableAnchors = [
      "E1-TABLE-BEFORE", "E1-CELL-A1", "E1-CELL-B2", "E1-TABLE-AFTER",
    ];
    await runIsolatedBoundary(corpus, "plain-grapheme", {
      id: "document-start-backward",
      anchor: "E1-PLAIN-START",
      boundary: "start",
      action: "delete-backward",
      unchanged: "E1-PLAIN-START",
    }, "boundary-document-start.odt", plainAnchors);
    await runIsolatedBoundary(corpus, "plain-grapheme", {
      id: "paragraph-end-forward",
      anchor: "E1-PLAIN-START",
      boundary: "end",
      action: "delete-forward",
      unchanged: "E1-PLAIN-START",
    }, "boundary-paragraph-end.odt", plainAnchors);
    await runIsolatedBoundary(corpus, "table-boundary", {
      id: "table-cell-start-backward",
      anchor: "E1-CELL-A1",
      boundary: "start",
      action: "delete-backward",
      unchanged: "E1-CELL-A1",
    }, "boundary-table-start.odt", tableAnchors);
    await runIsolatedBoundary(corpus, "table-boundary", {
      id: "table-cell-end-forward",
      anchor: "E1-CELL-A1",
      boundary: "end",
      action: "delete-forward",
      unchanged: "E1-CELL-A1",
    }, "boundary-table-end.odt", tableAnchors);

    metrics.rawCallbackExposed = metrics.events.some((event) =>
      "payload" in event || "resultPayload" in event || event.event === "lok");
    const positivesPass = metrics.positiveCases.every((item) =>
      item.repetitions.length === 3
      && item.repetitions.every((entry) => entry.status === "passed"));
    const boundariesPass = metrics.boundaryCases.length === 4
      && metrics.boundaryCases.every((entry) => entry.status === "rejected"
        && entry.revisionDelta === 0 && entry.contentUnchanged);
    metrics.pass = metrics.crossOriginIsolated
      && metrics.manifest?.profile === "finding-016-selection-barrier"
      && metrics.manifest?.diagnostic?.stateWordCountUsedForCompletion === false
      && metrics.manifest?.diagnostic?.boundaryRejectionRequiresFreshWorker === true
      && positivesPass && boundariesPass
      && metrics.outputs.length === 5
      && !metrics.rawCallbackExposed;
    metrics.decision = metrics.pass
      ? "SELECTION_BARRIER_BROWSER_CANDIDATE_WITH_BOUNDARY_RESTART"
      : "STOP_OR_RESCOPE";
    checkpoint("close", { pass: metrics.pass, decision: metrics.decision });
  } catch (error) {
    metrics.error = errorValue(error);
    metrics.pass = false;
    metrics.decision = "STOP_OR_RESCOPE";
    log({ fatal: metrics.error });
    if (documentHandle) {
      try {
        await documentHandle.close({ timeoutMs: 10000 });
      } catch {}
    }
    engine?.dispose();
  } finally {
    metrics.complete = true;
    status.textContent = metrics.pass ? "pass" : "failed";
  }
}

run();
