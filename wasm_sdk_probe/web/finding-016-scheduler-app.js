import { createDocumentEngine } from "./sdk/document-sdk.js";
import { EditorDiscoveryClient } from "./e1/editor-discovery-client.js";

const status = document.querySelector("#status");
const logNode = document.querySelector("#log");
const canvas = document.querySelector("#canvas");
const context = canvas.getContext("2d");
const metrics = {
  schemaVersion: 1,
  release: "E1-Finding-016-scheduler-drain",
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  fixture: "plain-grapheme",
  phase: "starting",
  complete: false,
  pass: false,
  events: [],
  checkpoints: [],
  error: null,
};
let outputBuffer = null;
globalThis.__finding_016_scheduler = metrics;
globalThis.__probe_metrics = metrics;
globalThis.__finding_016_scheduler_get_output_base64 = () => {
  if (!outputBuffer)
    return "";
  const bytes = new Uint8Array(outputBuffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
};

function log(value) {
  logNode.textContent += `${typeof value === "string" ? value : JSON.stringify(value)}\n`;
}

function checkpoint(name, detail = {}) {
  metrics.phase = name;
  metrics.checkpoints.push({ name, ...detail });
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

function countDelta(after, before, field) {
  return Number(after?.[field] || 0) - Number(before?.[field] || 0);
}

function schedulerDelay() {
  return new Promise((resolve) => globalThis.setTimeout(resolve, 1000));
}

async function run() {
  let engine = null;
  let documentHandle = null;
  try {
    checkpoint("load-fixture");
    const corpus = await (await fetch("./e1-fixtures/manifest.json", { cache: "no-cache" })).json();
    const fixture = corpus.fixtures.find((item) => item.id === metrics.fixture);
    if (!fixture)
      throw new Error("plain-grapheme fixture is unavailable");

    checkpoint("initialize-engine");
    engine = await createDocumentEngine({
      workerUrl: "./profiles/finding-016-scheduler/sdk-worker.js",
      timeoutMs: 30000,
      closeRecoveryTimeoutMs: 10000,
    });
    metrics.manifest = engine.manifest;
    engine.onEvent((event) => {
      if (["editor-state", "editor-callback-parse-error", "worker-crashed"].includes(event.event))
        metrics.events.push(event);
    });

    const input = await (await fetch(`./e1-fixtures/${fixture.path}`)).arrayBuffer();
    checkpoint("open", { bytes: input.byteLength });
    documentHandle = await engine.open(input, {
      name: fixture.path,
      transfer: true,
      timeoutMs: 180000,
    });
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

    checkpoint("place-caret");
    const selected = await documentHandle.search("0123456789");
    if (!selected.found)
      throw new Error("delete anchor was not found");
    const rectangle = firstRectangle(selected);
    const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
    metrics.collapse = await client.select("selection-reset-unstable", {
      startXTwips: rectangle.x,
      startYTwips: y,
      endXTwips: rectangle.x,
      endYTwips: y,
    });
    metrics.preconditionState = await client.getState();
    metrics.preconditionPass = metrics.preconditionState.selectionType === "none"
      && metrics.preconditionState.selection?.observed === true
      && metrics.preconditionState.selection?.collapsed === true;
    if (!metrics.preconditionPass)
      throw new Error("delete precondition is not a callback-confirmed collapsed caret");

    checkpoint("baseline-delay", { milliseconds: 1000 });
    await schedulerDelay();
    checkpoint("baseline-drain");
    metrics.baselineDrain = await client.drainScheduler({ timeoutMs: 30000 });
    metrics.baselineState = await client.getState();

    checkpoint("delete-forward");
    metrics.deletion = await client.action("delete-forward", {
      manualObservation: true,
      timeoutMs: 30000,
    });
    metrics.immediateState = await client.getState();

    checkpoint("post-delete-delay", { milliseconds: 1000 });
    await schedulerDelay();
    checkpoint("post-delete-drain");
    metrics.postDeleteDrain = await client.drainScheduler({ timeoutMs: 30000 });
    metrics.finalState = await client.getState();

    const baseline = metrics.baselineDrain.after;
    const immediate = metrics.immediateState.schedulerProbe;
    const beforeDrain = metrics.postDeleteDrain.before;
    const finalProbe = metrics.postDeleteDrain.after;
    const naturalStateDelta = countDelta(immediate, baseline, "stateChangedCount");
    const naturalWordCountDelta = countDelta(immediate, baseline, "wordCountUpdateCount");
    const delayedNaturalWordCountDelta = countDelta(
      beforeDrain,
      immediate,
      "wordCountUpdateCount",
    );
    const drainStateDelta = Number(metrics.postDeleteDrain.delta?.stateChangedCount || 0);
    const drainWordCountDelta = Number(metrics.postDeleteDrain.delta?.wordCountUpdateCount || 0);
    const exactCharacterDelta = Number.isInteger(baseline?.wordCountCharacters)
      && baseline.wordCountCharacters >= 0
      && finalProbe?.wordCountCharacters === baseline.wordCountCharacters - 1;
    metrics.schedulerDiscriminator = {
      naturalStateDelta,
      naturalWordCountDelta,
      delayedNaturalWordCountDelta,
      drainStateDelta,
      drainWordCountDelta,
      exactCharacterDelta,
      expectedPostDeleteCharacters: 93,
      observedBeforeDrainCharacters: beforeDrain?.wordCountCharacters,
      observedAfterDrainCharacters: finalProbe?.wordCountCharacters,
    };
    if (delayedNaturalWordCountDelta > 0 && beforeDrain?.wordCountCharacters === 93)
      metrics.decision = "WORD_COUNT_CALLBACK_DELIVERED_WITHOUT_DRAIN";
    else if (drainStateDelta > 0 && drainWordCountDelta > 0
             && finalProbe?.wordCountCharacters === 93)
      metrics.decision = "DRAIN_RECOVERS_DELAYED_CALLBACK";
    else
      metrics.decision = "NO_ATTRIBUTABLE_CALLBACK_AFTER_DRAIN";
    metrics.schedulerHypothesisSupported = metrics.decision === "DRAIN_RECOVERS_DELAYED_CALLBACK";

    checkpoint("verify-mutation");
    metrics.expectedSearch = await documentHandle.search("123456789");
    metrics.originalSearch = await documentHandle.search("0123456789");
    metrics.exactMutation = metrics.expectedSearch.found === true
      && metrics.originalSearch.found === false;

    checkpoint("save");
    outputBuffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
    metrics.output = { bytes: outputBuffer.byteLength };
    metrics.rawCallbackExposed = metrics.events.some((event) => "payload" in event || event.event === "lok");
    metrics.pass = metrics.crossOriginIsolated
      && metrics.manifest?.diagnostic?.experiment === "finding-016-scheduler-drain"
      && metrics.preconditionPass
      && metrics.deletion?.revision === metrics.deletion?.beforeRevision + 1
      && metrics.deletion?.changed === null
      && metrics.exactMutation
      && [
        "WORD_COUNT_CALLBACK_DELIVERED_WITHOUT_DRAIN",
        "DRAIN_RECOVERS_DELAYED_CALLBACK",
      ].includes(metrics.decision)
      && outputBuffer.byteLength > 0
      && !metrics.rawCallbackExposed;

    checkpoint("close", { pass: metrics.pass, decision: metrics.decision });
    await documentHandle.close({ timeoutMs: 30000 });
    documentHandle = null;
    engine.dispose();
    engine = null;
  } catch (error) {
    metrics.error = errorValue(error);
    metrics.pass = false;
    metrics.decision ||= error?.code === "TIMEOUT"
      ? "SCHEDULER_DRAIN_TIMEOUT"
      : "EXPERIMENT_ERROR";
    log({ fatal: metrics.error, decision: metrics.decision });
    if (documentHandle) {
      try {
        await documentHandle.close({ timeoutMs: 10000 });
      } catch {}
    }
    engine?.dispose();
  } finally {
    metrics.complete = true;
    metrics.phase = "complete";
    status.textContent = `${metrics.pass ? "pass" : "failed"}: ${metrics.decision || "unknown"}`;
  }
}

run().catch((error) => {
  metrics.error = errorValue(error);
  metrics.complete = true;
  metrics.pass = false;
  metrics.decision = "EXPERIMENT_ERROR";
});
