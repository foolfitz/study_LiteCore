// Finding 038 on the SHIPPED editor artifact.
//
// Everything measured for 038 so far ran on the E2 discovery engine, through
// `editorDiscoverySelect`.  The shipped editor does not expose that path at all
// -- e1-editor-v1 declares `narrow-editor-v1` and not
// `editor-discovery-closed-actions` -- so "the shipped range selection triggers
// this" has been an inference across artifacts, in a project whose central rule
// is that behaviour binds to the artifact it was measured on (findings 027,
// 036).  This is the measurement that either earns that sentence or retracts it.
//
// So: the shipped client (`NarrowEditorClient.selectRange`, which goes through
// `editorSelectRangeV1`), on e1-editor-v1, against a document whose footnote
// body holds an as-char frame.
//
// It runs BEFORE any guard or recovery ships, because once one does, "what does
// today's user actually experience when this fires" stops being answerable --
// the same reason finding 037's five-action sweep had to run before its guard.
//
// Three cases, fresh engine each, in increasing order of expected damage:
//
//   plain-full     a paragraph with no frame anywhere: the control that says
//                  the sequence works at all on this artifact
//   note-partial   the note paragraph, selected only as far as 2400 twips,
//                  which on the discovery engine does NOT reach the citation
//                  and does NOT wedge
//   note-full      the note paragraph, selected past the end of the line, which
//                  covers the citation.  Last, because if it wedges it takes
//                  whatever follows with it.
//
// What is recorded is not just "did it wedge" but what the caller was told, and
// when: the shipped selectRange issues the request and then reads the selection
// back, so there are two places it can stop and they mean different things to a
// user interface.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorClient } from "./editor-shell/editor-client.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e1-editor-v1";
const fixture = params.get("fixture") || "frame-contexts.odt";
const stepTimeoutMs = Number.parseInt(params.get("timeoutMs") || "15000", 10);

const status = document.querySelector("#status");
const logNode = document.querySelector("#log");

const metrics = {
  schemaVersion: 1,
  release: "e1-note-frame-select",
  finding: "038 on the shipped artifact",
  profile,
  fixture,
  stepTimeoutMs,
  userAgent: navigator.userAgent,
  manifest: null,
  cases: [],
  complete: false,
  error: null,
};
globalThis.__e1_note_frame = metrics;
globalThis.__probe_metrics = metrics;

function log(value) {
  logNode.textContent += `${typeof value === "string" ? value : JSON.stringify(value)}\n`;
}

function errorValue(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: String(error?.message || error),
  };
}

function firstRectangle(search) {
  const raw = (search?.selections?.[0]?.rectangles || "").split(";")[0];
  const numbers = raw.split(",").map((item) => Number.parseInt(item.trim(), 10));
  if (numbers.length !== 4 || numbers.some((item) => !Number.isFinite(item)))
    throw new Error("search did not return a usable rectangle");
  return { x: numbers[0], y: numbers[1], width: numbers[2], height: numbers[3] };
}

const CASES = [
  { label: "plain-full", anchor: "FX-PLAIN", spanTwips: null },
  { label: "note-partial", anchor: "FX-NOTE", spanTwips: 2400 },
  { label: "note-full", anchor: "FX-NOTE", spanTwips: null },
];

/** Is the editor still answering, and does it still hold a usable selection? */
async function probeUsable(client, documentHandle) {
  const probe = {};
  const started = performance.now();
  try {
    const state = await client.getState({ timeoutMs: stepTimeoutMs });
    probe.getState = "answered";
    probe.selection = state?.selection
      ? { collapsed: state.selection.collapsed,
          rectangles: (state.selection.rectangles || []).length }
      : null;
  } catch (error) {
    probe.getState = "failed";
    probe.getStateError = errorValue(error);
  }
  try {
    const selection = await documentHandle.getSelection({ timeoutMs: stepTimeoutMs });
    probe.selectionType = selection.selectionType;
    probe.selectionText = (selection.text || "").slice(0, 40);
  } catch (error) {
    probe.getSelectionError = errorValue(error);
  }
  probe.elapsedMs = Math.round(performance.now() - started);
  probe.usable = probe.getState === "answered" && !probe.getSelectionError;
  return probe;
}

async function runCase(fixtureBuffer, spec) {
  const entry = { ...spec, status: "running" };
  metrics.cases.push(entry);
  let engine = null;
  let documentHandle = null;
  const started = performance.now();
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`,
      timeoutMs: 30000,
      closeRecoveryTimeoutMs: 10000,
    });
    metrics.manifest = engine.manifest;
    engine.onEvent((event) => {
      // Recovery is the whole question for one of the options on the table, so
      // any recovery event is kept rather than summarised away.
      if (String(event.event || "").includes("recovery")
          || event.event === "worker-crashed")
        (entry.engineEvents ||= []).push(event.event);
    });
    documentHandle = await engine.open(fixtureBuffer.slice(0), {
      name: fixture, transfer: true, timeoutMs: 180000,
    });
    const client = new NarrowEditorClient(documentHandle);

    const found = await documentHandle.search(spec.anchor, { timeoutMs: 30000 });
    if (!found?.found)
      throw new Error(`anchor not found: ${spec.anchor}`);
    const rectangle = firstRectangle(found);
    const midY = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
    const endX = spec.spanTwips
      ? rectangle.x + spec.spanTwips
      : rectangle.x + 8000;
    entry.rectangle = rectangle;
    entry.selectTo = endX;

    entry.before = await probeUsable(client, documentHandle);

    const selectStarted = performance.now();
    try {
      await client.selectRange(
        { xTwips: rectangle.x, yTwips: midY },
        { xTwips: endX, yTwips: midY },
        { timeoutMs: stepTimeoutMs });
      entry.selectRange = "completed";
    } catch (error) {
      entry.selectRange = "failed";
      entry.selectRangeError = errorValue(error);
    }
    entry.selectRangeMs = Math.round(performance.now() - selectStarted);

    entry.after = await probeUsable(client, documentHandle);
    entry.status = entry.after.usable ? "editor-survived" : "editor-wedged";
  } catch (error) {
    entry.error = errorValue(error);
    entry.status = "failed";
  } finally {
    if (documentHandle) {
      const closeStarted = performance.now();
      try {
        await documentHandle.close({ timeoutMs: 30000 });
        entry.close = "completed";
      } catch (error) {
        entry.close = "failed";
        entry.closeError = errorValue(error);
      }
      entry.closeMs = Math.round(performance.now() - closeStarted);
    }
    try {
      engine?.dispose();
    } catch (error) {
      entry.disposeError = errorValue(error);
    }
    entry.elapsedMs = Math.round(performance.now() - started);
  }
  log(entry);
  return entry;
}

async function main() {
  try {
    status.textContent = "loading fixture";
    const response = await fetch(`./e1-fixtures/${fixture}`, { cache: "no-cache" });
    if (!response.ok)
      throw new Error(`fixture fetch failed: ${response.status}`);
    const buffer = await response.arrayBuffer();
    for (const spec of CASES) {
      status.textContent = spec.label;
      await runCase(buffer, spec);
    }
    status.textContent = "complete";
  } catch (error) {
    metrics.error = errorValue(error);
    status.textContent = "failed";
    log({ fatal: metrics.error });
  } finally {
    metrics.complete = true;
  }
}

main();
