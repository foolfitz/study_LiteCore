import { createDocumentEngine } from "./sdk/document-sdk.js";
import { EditorDiscoveryClient } from "./e1/editor-discovery-client.js";

const params = new URLSearchParams(location.search);
const fixtureId = params.get("fixture") || "plain-grapheme";
const mode = params.get("mode") || "full";
const status = document.querySelector("#status");
const logNode = document.querySelector("#log");
const canvas = document.querySelector("#canvas");
const context = canvas.getContext("2d");
const metrics = {
  schemaVersion: 1,
  release: "E1-A-editing-discovery",
  fixture: fixtureId,
  mode,
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  phase: "starting",
  complete: false,
  events: [],
  operations: [],
  checkpoints: [],
  capabilityReductions: [],
  externalEvidence: [],
  output: null,
  error: null,
};
let outputBuffer = null;
globalThis.__e1_discovery = metrics;
// Shared ChromeSession.navigate() uses this generic readiness sentinel.
globalThis.__probe_metrics = metrics;
globalThis.__e1_discovery_get_output_base64 = () => {
  if (!outputBuffer)
    return "";
  const bytes = new Uint8Array(outputBuffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
};

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  logNode.textContent += `${text}\n`;
}

function checkpoint(name, detail = {}) {
  metrics.phase = name;
  metrics.checkpoints.push({ name, ...detail });
  status.textContent = `${fixtureId}: ${name}`;
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

async function record(family, name, repetition, callback, expectation = "positive") {
  const entry = { family, name, repetition, expectation, status: "running" };
  metrics.operations.push(entry);
  try {
    entry.result = await callback();
    entry.status = "passed";
  } catch (error) {
    entry.error = errorValue(error);
    entry.status = expectation === "typed-failure" || expectation === "discovery-negative"
      ? "passed" : "failed";
  }
  log(entry);
  return entry;
}

function firstRectangle(searchResult) {
  const value = searchResult?.selections?.[0]?.rectangles || "";
  const first = value.split(";")[0];
  const values = first.split(",").map((item) => Number.parseInt(item.trim(), 10));
  if (values.length !== 4 || values.some((value) => !Number.isFinite(value)))
    return { x: 1800, y: 1800, width: 1600, height: 400 };
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

async function selectAnchor(documentHandle, anchor) {
  const result = await documentHandle.search(anchor);
  if (!result.found)
    throw new Error(`fixture anchor not found: ${anchor}`);
  return firstRectangle(result);
}

async function placeCaretAtRectangleEnd(client, rectangle) {
  const x = rectangle.x + Math.max(1, rectangle.width);
  const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  return client.select("selection-reset-unstable", {
    startXTwips: x,
    startYTwips: y,
    endXTwips: x,
    endYTwips: y,
  });
}

async function placeCaretAtRectangleStart(client, rectangle) {
  const x = rectangle.x;
  const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  return client.select("selection-reset-unstable", {
    startXTwips: x,
    startYTwips: y,
    endXTwips: x,
    endYTwips: y,
  });
}

async function repeatedActions(client, family, names, count = 3, options = {}) {
  for (const name of names) {
    for (let repetition = 1; repetition <= count; repetition += 1) {
      await record(family, name, repetition, () => client.action(name, options));
    }
  }
}

async function repeatedFormatPair(documentHandle, client, name, anchor) {
  await selectAnchor(documentHandle, anchor);
  for (let repetition = 1; repetition <= 3; repetition += 1) {
    const disable = await record("format", name, repetition * 2 - 1, () =>
      client.action(name, { enabled: false }));
    disable.variant = "disable";
    const enable = await record("format", name, repetition * 2, () =>
      client.action(name, { enabled: true }));
    enable.variant = "enable";
  }
}

async function runPlain(documentHandle, client, anchor) {
  await selectAnchor(documentHandle, anchor);
  await repeatedActions(client, "caret", ["move-character-left", "move-character-right"]);
  await selectAnchor(documentHandle, anchor);
  await repeatedActions(
    client,
    "selection",
    ["move-character-left", "move-character-right"],
    3,
    { extendSelection: true },
  );

  const insertionRectangle = await selectAnchor(documentHandle, anchor);
  await placeCaretAtRectangleEnd(client, insertionRectangle);
  await documentHandle.insertText("XYZ");
  await repeatedActions(client, "mutation", ["delete-backward"]);
  await documentHandle.insertText("ABC");
  await repeatedActions(client, "caret", ["move-character-left"]);
  await repeatedActions(client, "mutation", ["delete-forward"]);
}

async function runMulti(documentHandle, client, anchor) {
  metrics.capabilityReductions.push({
    capability: "line-navigation",
    status: "not-promoted",
    reason: "Home/End callback completion was not deterministic across repeated runs",
  });
  const insertionRectangle = await selectAnchor(documentHandle, anchor);
  await placeCaretAtRectangleEnd(client, insertionRectangle);
  await repeatedActions(client, "mutation", ["insert-paragraph-break"]);
  await documentHandle.insertText("E1-PARAGRAPH-BREAK-ANCHOR");
  for (let repetition = 1; repetition <= 3; repetition += 1) {
    await record("history", "undo", repetition, async () => {
      const beforeRevision = documentHandle.revision;
      const result = await documentHandle.undo({
        expectedRevision: beforeRevision,
        timeoutMs: 30000,
      });
      return {
        action: "undo",
        beforeRevision,
        revision: result.revision,
        changed: result.revision === beforeRevision + 1,
        completion: "public-undo",
      };
    });
  }
  await record(
    "history-reduction",
    "redo",
    1,
    () => client.action("redo"),
    "typed-failure",
  );
  metrics.capabilityReductions.push({
    capability: "redo",
    status: "not-promoted",
    reason: "fixed diagnostic Redo lacks a successful command-result contract",
  });
  const lineBreakRectangle = await selectAnchor(documentHandle, "E1-MULTI-END omega");
  await placeCaretAtRectangleEnd(client, lineBreakRectangle);
  await repeatedActions(client, "mutation", ["insert-line-break"]);
  await documentHandle.insertText("E1-LINE-BREAK-ANCHOR");
}

async function runStyled(documentHandle, client, anchor, rectangle) {
  void anchor;
  void rectangle;
  metrics.capabilityReductions.push(
    {
      capability: "mouse-drag-and-text-handles",
      status: "not-promoted",
      reason: "prior isolated attempts did not yield a callback-correlated completion",
    },
    {
      capability: "paragraph-and-list-format",
      status: "not-promoted",
      reason: "prior commands lacked a cross-browser completion contract",
    },
  );
  await repeatedFormatPair(documentHandle, client, "set-bold", "bold anchor");
  await repeatedFormatPair(documentHandle, client, "set-italic", "italic anchor");
}

async function runTable(documentHandle, client) {
  metrics.capabilityReductions.push({
    capability: "structural-boundary-delete",
    status: "typed-unsupported",
    reason: "boundary rejection requires a fresh Worker before another operation",
  });
  metrics.externalEvidence.push({
    finding: "016",
    decision: "SELECTION_BARRIER_SUPPORTED_WITH_BOUNDARY_RESTART",
    path: "findings/evidence/016/selection-barrier-wasm/summary.json",
  });
  const rectangle = await selectAnchor(documentHandle, "E1-CELL-A1");
  await placeCaretAtRectangleEnd(client, rectangle);
  await repeatedActions(client, "table-caret", ["move-character-left", "move-character-right"]);
}

async function runFinding016Remediation(documentHandle, client, anchor) {
  if (fixtureId === "plain-grapheme") {
    await selectAnchor(documentHandle, "0123456789");
    await record("caret", "collapse-selection-left", 1, () =>
      client.action("move-character-left"));
    await repeatedActions(client, "remediation-positive", ["delete-forward"]);

    await selectAnchor(documentHandle, "ASCII abc");
    await record("caret", "collapse-selection-right", 1, () =>
      client.action("move-character-right"));
    await repeatedActions(client, "remediation-positive", ["delete-backward"]);

    await selectAnchor(documentHandle, "E1-PLAIN-START");
    await record("caret", "collapse-document-start", 1, () =>
      client.action("move-character-left"));
    for (let repetition = 1; repetition <= 3; repetition += 1) {
      await record("remediation-boundary", "delete-backward", repetition, () =>
        client.action("delete-backward"), "typed-failure");
    }

    await selectAnchor(documentHandle, "E1-PLAIN-END");
    await record("caret", "collapse-document-end", 1, () =>
      client.action("move-character-right"));
    for (let repetition = 1; repetition <= 3; repetition += 1) {
      await record("remediation-boundary", "delete-forward", repetition, () =>
        client.action("delete-forward"), "typed-failure");
    }
    return;
  }
  if (fixtureId === "multi-paragraph") {
    const rectangle = await selectAnchor(documentHandle, anchor);
    await placeCaretAtRectangleEnd(client, rectangle);
    await repeatedActions(client, "remediation-positive", [
      "insert-paragraph-break",
      "insert-line-break",
    ]);
    return;
  }
  if (fixtureId === "table-boundary") {
    await runTable(documentHandle, client);
    return;
  }
  throw new Error(`finding-016 remediation mode does not support ${fixtureId}`);
}

async function run() {
  let engine = null;
  let documentHandle = null;
  try {
    checkpoint("load-manifest");
    const corpus = await (await fetch("./e1-fixtures/manifest.json", { cache: "no-cache" })).json();
    const fixture = corpus.fixtures.find((item) => item.id === fixtureId);
    if (!fixture)
      throw new Error(`unknown fixture: ${fixtureId}`);
    metrics.fixtureManifest = fixture;
    checkpoint("initialize-engine");
    engine = await createDocumentEngine({
      workerUrl: "./profiles/e1-editor-discovery/sdk-worker.js",
      timeoutMs: 30000,
      closeRecoveryTimeoutMs: 10000,
    });
    metrics.manifest = engine.manifest;
    engine.onEvent((event) => {
      if (event.event === "editor-state" || event.event === "editor-callback-parse-error"
          || event.event === "worker-crashed" || event.event === "document-close-recovery-complete") {
        metrics.events.push(event);
      }
    });
    const response = await fetch(`./e1-fixtures/${fixture.path}`);
    const input = await response.arrayBuffer();
    checkpoint("open", { bytes: input.byteLength });
    documentHandle = await engine.open(input, { name: fixture.path, transfer: true, timeoutMs: 180000 });
    const client = new EditorDiscoveryClient(documentHandle);
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
    const anchor = fixture.anchors[0];
    const rectangle = await selectAnchor(documentHandle, anchor);
    metrics.initialState = await client.getState();
    checkpoint("operations", { anchor, rectangle });
    if (mode === "finding-016-remediation")
      await runFinding016Remediation(documentHandle, client, anchor);
    else if (fixtureId === "plain-grapheme")
      await runPlain(documentHandle, client, anchor);
    else if (fixtureId === "multi-paragraph")
      await runMulti(documentHandle, client, anchor);
    else if (fixtureId === "styled-list")
      await runStyled(documentHandle, client, anchor, rectangle);
    else if (fixtureId === "table-boundary")
      await runTable(documentHandle, client);
    else
      await repeatedActions(client, "regression", ["move-character-left", "move-character-right"]);

    await record("negative", "stale-revision", 1, () =>
      client.action("delete-forward", { expectedRevision: documentHandle.revision + 99 }), "typed-failure");
    await record("negative", "unsupported-action", 1, () =>
      client.action(".uno:Bold"), "typed-failure");
    metrics.finalState = await client.getState();
    checkpoint("save");
    outputBuffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
    metrics.output = { bytes: outputBuffer.byteLength };
    checkpoint("close");
    await documentHandle.close({ timeoutMs: 30000 });
    documentHandle = null;
    engine.dispose();
    engine = null;
    metrics.rawCallbackExposed = metrics.events.some((event) => "payload" in event || event.event === "lok");
    const formatMutations = metrics.operations.filter((item) => item.family === "format");
    const formatMutationsPass = formatMutations.length === 0
      || formatMutations.every((item) => item.status === "passed"
        && item.result?.changed === true
        && item.result?.revision === item.result?.beforeRevision + 1);
    metrics.pass = (
      metrics.crossOriginIsolated
      && metrics.manifest?.diagnostic?.scope === "e1-odt-editing-discovery"
      && metrics.manifest?.diagnostic?.selectionBarrier === "verified-single-writer-unit-v1"
      && metrics.manifest?.diagnostic?.boundaryRejectionRequiresFreshWorker === true
      && outputBuffer.byteLength > 0
      && !metrics.rawCallbackExposed
      && formatMutationsPass
      && metrics.operations.every((item) => item.status === "passed")
    );
    checkpoint("complete", { pass: metrics.pass });
  } catch (error) {
    metrics.error = errorValue(error);
    metrics.pass = false;
    log({ fatal: metrics.error });
    if (documentHandle) {
      try {
        await documentHandle.close({ timeoutMs: 10000 });
      } catch {}
    }
    engine?.dispose();
  } finally {
    metrics.complete = true;
    metrics.phase = "complete";
    status.textContent = `${fixtureId}: ${metrics.pass ? "pass" : "failed"}`;
  }
}

run().catch((error) => {
  metrics.error = errorValue(error);
  metrics.complete = true;
  metrics.pass = false;
});
