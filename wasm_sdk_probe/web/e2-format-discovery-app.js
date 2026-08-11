import { createDocumentEngine } from "./sdk/document-sdk.js";
import { FormatDiscoveryClient } from "./e2/format-discovery-client.js";

// E2-A A2-wasm: reproduce the native state-readback observation in the browser.
//
// A2 asks one question -- do .uno:DefaultBullet, .uno:DefaultNumbering and
// .uno:StyleApply actually reach this profile, and does their value track the
// caret?  It deliberately does not judge the barrier; that is A3.  Dispatches
// are run too, but every postcondition here is taken from the saved ODT, never
// from the callback under test.  That is the same rule the native run used.
const params = new URLSearchParams(location.search);
const fixtureId = params.get("fixture") || "styled-list";
// "a2" measures what arrives on its own.  "scheduler-attribution" adds a
// scheduler drain after each placement, to separate "core never computes this"
// from "this build never runs the idle job that would".  "mainloop-attribution"
// runs the finding 021 candidate-1 profile: the engine sits in the upstream
// emscripten main loop (LOK runLoop, unipoll), no drain exists, and the
// question is whether the state stays fresh with no host pump at all.
const mode = params.get("mode") || "a2";
// "locale-attribution" is scheduler-attribution with one difference: the engine
// asks LOK for a zh-TW UI language at documentLoad.  Everything else -- the
// drain, the sequence, the postcondition checks -- is identical, so the two
// runs are directly comparable and any difference in the reported style strings
// is the language (finding 031).
const profile = mode === "scheduler-attribution"
  ? "e2-scheduler-attribution"
  : mode === "locale-attribution"
    ? "e2-locale-attribution"
    : mode === "mainloop-pei-attribution"
      ? "e2-mainloop-pei-attribution"
      : mode === "mainloop-attribution" || mode === "mainloop-move-attribution"
        ? "e2-mainloop-attribution"
        : "e2-format-discovery";
// Finding 021 discriminating experiments.  "mainloop-pei-attribution" runs
// the scheduler drain (ProcessEventsToIdle) under the live loop; if it still
// releases watched payloads the PEI-vs-loop difference is PEI's own
// semantics, otherwise it is whatever the old non-unipoll init set up.
// "mainloop-move-attribution" adds one real cursor dispatch after each API
// placement; if that schedules the recompute, the invalidation gap is
// specific to the API placement path.
const drainRefresh = mode === "scheduler-attribution"
  || mode === "locale-attribution"
  || mode === "mainloop-pei-attribution";
const mainloopWait = mode === "mainloop-attribution"
  || mode === "mainloop-move-attribution";
const nudgePlacement = mode === "mainloop-move-attribution";
const status = document.querySelector("#status");
const logNode = document.querySelector("#log");
const canvas = document.querySelector("#canvas");
const context = canvas.getContext("2d");

const metrics = {
  schemaVersion: 1,
  release: "E2-A-paragraph-format-discovery",
  stage: "A2-wasm",
  mode,
  profile,
  fixture: fixtureId,
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  phase: "starting",
  complete: false,
  checkpoints: [],
  // Every editor-state event, not just the format ones.  The first Chrome
  // attempt recorded format-state only, which meant a run with zero format
  // state could not be told apart from a run where the caret never moved.
  editorStateEvents: [],
  formatStateEvents: [],
  readback: [],
  control: [],
  readbackAfterControl: [],
  dispatch: [],
  outputs: [],
  error: null,
  pass: false,
};
const outputs = new Map();
globalThis.__e2_discovery = metrics;
// Shared ChromeSession.navigate() uses this generic readiness sentinel.
globalThis.__probe_metrics = metrics;
globalThis.__e2_discovery_get_output_base64 = (label) => {
  const buffer = outputs.get(label);
  if (!buffer)
    return "";
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
};

const READBACK_POSITIONS = [
  { id: "heading", anchor: "E1-STYLED-HEADING" },
  { id: "body-paragraph", anchor: "bold anchor" },
  { id: "list-item", anchor: "E1-LIST-ONE" },
  { id: "after-list", anchor: "E1-STYLED-END" },
];

// Each entry dispatches once and then saves, so the postcondition is judged
// from file bytes by the runner rather than from the state we are testing.
// A3's positive matrix: the three-state list cycle and the two-state style
// round trip, exactly as SPEC E2-A section 5 freezes them.  Kept separate from
// the A2 list rather than bolted onto it -- A2 measures what arrives, A3 judges
// the barrier, and a shared sequence would make the evidence for one depend on
// edits made for the other.
//
// Every step names the state it must land in, so the runner judges the saved
// document per step instead of only at the end of a cycle.  A cycle that ends
// correctly after a step went the wrong way and got corrected is not a pass.
//
// The anchor is per fixture, because the same closed action has to be shown
// working on more than one document shape and the three fixtures share no text.
// styled-list's anchor sits directly after an existing list, which is worth
// knowing: applying a list there merges with the neighbour.  The other two have
// no list at all, so they measure the same action without that confound.
const A3_ANCHORS = {
  "styled-list": "E1-STYLED-END",
  "multi-paragraph": "E1-MULTI-END",
  "plain-grapheme": "E1-PLAIN-END",
};
const a3Anchor = A3_ANCHORS[fixtureId] || null;
const A3_STEPS = [
  { label: "cycle-list-unordered", anchor: a3Anchor, action: "set-list-unordered" },
  { label: "cycle-list-ordered", anchor: a3Anchor, action: "set-list-ordered" },
  { label: "cycle-list-none", anchor: a3Anchor, action: "set-list-none" },
  { label: "roundtrip-heading", anchor: a3Anchor, action: "set-paragraph-heading" },
  { label: "roundtrip-body", anchor: a3Anchor, action: "set-paragraph-body" },
];

// A4: repeat dispatch (SPEC E2-A section 5, rewritten v11).
//
// Route C removed the precondition read, so a second press dispatches a second
// time.  Each action is driven to its target once and then pressed twice more
// on a paragraph that is already there, which asks both questions at once:
// does the document stay put (a toggle would invert), and does the barrier
// still complete when core broadcasts nothing because nothing changed.
//
// Generated rather than written out, so an action cannot be added to the closed
// set and silently left without repeats.
const A4_ACTIONS = [
  { action: "set-list-unordered", key: "list-unordered" },
  { action: "set-list-ordered", key: "list-ordered" },
  { action: "set-list-none", key: "list-none" },
  { action: "set-paragraph-heading", key: "paragraph-heading" },
  { action: "set-paragraph-body", key: "paragraph-body" },
];
const A4_STEPS = A4_ACTIONS.flatMap(({ action, key }) => [
  { label: `${key}-set`, anchor: a3Anchor, action },
  { label: `${key}-repeat-1`, anchor: a3Anchor, action },
  { label: `${key}-repeat-2`, anchor: a3Anchor, action },
]);

const DISPATCH_STEPS = [
  { label: "bullet-on", anchor: "E1-STYLED-END", action: "set-list-unordered" },
  { label: "numbering-on", anchor: "E1-STYLED-END", action: "set-list-ordered" },
  { label: "list-off", anchor: "E1-STYLED-END", action: "set-list-none" },
  { label: "heading-on", anchor: "E1-STYLED-END", action: "set-paragraph-heading" },
  { label: "body-on", anchor: "E1-STYLED-END", action: "set-paragraph-body" },
  // Repeats.  Route C dropped the precondition read, so pressing the same
  // button twice dispatches twice -- the case finding 030 was about and the
  // one the five steps above cannot reach, because every one of them is a
  // cross-state transition and a toggle and a setter agree on those.
  //
  // Each repeat lands on a paragraph that is already in the target state, so
  // it is simultaneously the idempotence check (does the document stay put)
  // and the silent-no-op check (does the barrier still complete when core
  // broadcasts nothing).
  { label: "bullet-on-repeat-1", anchor: "E1-STYLED-END", action: "set-list-unordered" },
  { label: "bullet-on-repeat-2", anchor: "E1-STYLED-END", action: "set-list-unordered" },
  { label: "heading-on-repeat-1", anchor: "E1-STYLED-END", action: "set-paragraph-heading" },
  { label: "heading-on-repeat-2", anchor: "E1-STYLED-END", action: "set-paragraph-heading" },
];

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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatOf(state) {
  return {
    bold: state?.format?.bold ?? null,
    italic: state?.format?.italic ?? null,
    listBullet: state?.format?.listBullet ?? null,
    listNumber: state?.format?.listNumber ?? null,
    paragraphStyle: state?.format?.paragraphStyle ?? null,
    // Finding 021 attribution: raw STATE_CHANGED arrivals reaching the engine,
    // and the subset it did not recognise.  Separates "core sent nothing" from
    // "we received something and dropped it".
    stateChangedTotal: state?.format?.stateChangedTotal ?? null,
    stateChangedUnrecognised: state?.format?.stateChangedUnrecognised ?? null,
    // Main-loop profile only (null elsewhere): the engine's own staleness
    // verdict and the poll counters that make "the loop is actually running"
    // provable from evidence.
    formatStale: state?.format?.formatStale ?? null,
    pollCount: state?.format?.pollCount ?? null,
    idlePollCount: state?.format?.idlePollCount ?? null,
  };
}

// Main-loop mode's replacement for the scheduler drain: a host-owned bounded
// wait for the engine to report the cache fresh again.  Nothing here pumps
// anything -- the upstream main loop is expected to do that on its own, and
// this loop only observes the typed staleness flag until it clears.  Same
// convention as E1-B's bounded poll after click.
async function awaitFreshFormatState(client, deadlineMs = 5000, intervalMs = 50) {
  const start = performance.now();
  let reads = 0;
  let format = null;
  while (performance.now() - start < deadlineMs) {
    format = formatOf(await client.getState());
    reads += 1;
    if (format.formatStale === false) {
      return {
        fresh: true,
        reads,
        waitedMs: Math.round(performance.now() - start),
        format,
      };
    }
    await sleep(intervalMs);
  }
  return {
    fresh: false,
    reads,
    waitedMs: Math.round(performance.now() - start),
    format,
  };
}

// A bounded observation window, not a completion barrier.  Nothing here is
// allowed to declare a mutation successful; it only decides when the broadcast
// has gone quiet so the observed value can be recorded with its wait time.
async function settleFormatState(deadlineMs = 4000, quietMs = 500) {
  const start = performance.now();
  let seen = metrics.editorStateEvents.length;
  let lastChange = performance.now();
  while (performance.now() - start < deadlineMs) {
    await sleep(50);
    if (metrics.editorStateEvents.length !== seen) {
      seen = metrics.editorStateEvents.length;
      lastChange = performance.now();
      continue;
    }
    if (performance.now() - lastChange >= quietMs) {
      return {
        settled: true,
        waitedMs: Math.round(performance.now() - start),
        editorStateEventCount: seen,
        formatStateEventCount: metrics.formatStateEvents.length,
      };
    }
  }
  return {
    settled: false,
    waitedMs: Math.round(performance.now() - start),
    editorStateEventCount: metrics.editorStateEvents.length,
    formatStateEventCount: metrics.formatStateEvents.length,
  };
}

function firstRectangle(searchResult) {
  const value = searchResult?.selections?.[0]?.rectangles || "";
  const first = value.split(";")[0];
  const values = first.split(",").map((item) => Number.parseInt(item.trim(), 10));
  if (values.length !== 4 || values.some((item) => !Number.isFinite(item)))
    return null;
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

// Two placement methods, because a run with no state must not be confusable
// with a run where the caret never moved.  "search" is the E1-A discovery path
// (setTextSelection RESET); "click" is the public mouse path the E1-B product
// session uses.  Both are recorded separately.
async function caretAtAnchor(documentHandle, client, anchor, method) {
  const search = await documentHandle.search(anchor);
  if (!search.found)
    throw new Error(`fixture anchor not found: ${anchor}`);
  const rectangle = firstRectangle(search);
  if (!rectangle)
    throw new Error(`anchor rectangle unavailable: ${anchor}`);
  const x = rectangle.x + Math.max(1, rectangle.width);
  const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  if (method === "click")
    await documentHandle.click(x, y);
  else
    await client.placeCaret(x, y);
  return { anchor, rectangle, caret: { x, y }, method };
}

async function runReadback(documentHandle, client, into, method) {
  for (const position of READBACK_POSITIONS) {
    const entry = { id: position.id, anchor: position.anchor, method, status: "running" };
    into.push(entry);
    try {
      const beforeFormat = metrics.formatStateEvents.length;
      const beforeAll = metrics.editorStateEvents.length;
      const before = formatOf(await client.getState());
      entry.placement = await caretAtAnchor(documentHandle, client, position.anchor, method);
      if (nudgePlacement) {
        // Experiment 2: one real cursor dispatch after the API placement.
        // Recorded leniently -- finding 018 makes move completion itself
        // nondeterministic, and what matters here is the broadcast that does
        // or does not follow, not the move's own completion verdict.
        try {
          entry.nudge = await client.nudgeCaret({ timeoutMs: 15000 });
        } catch (error) {
          entry.nudge = { error: errorValue(error) };
        }
      }
      entry.settle = await settleFormatState();
      const state = await client.getState();
      entry.format = formatOf(state);
      entry.revision = state?.revision ?? null;
      entry.selectionType = state?.selectionType ?? null;
      entry.caret = state?.caret ?? null;
      entry.formatStateEventsObserved = metrics.formatStateEvents.length - beforeFormat;
      entry.editorStateEventsObserved = metrics.editorStateEvents.length - beforeAll;
      // A value with no event behind it is last position's value still sitting
      // in the cache.  Recording it as a reading of *this* paragraph would be
      // the whole error this phase exists to detect, so it is marked instead.
      entry.fresh = entry.formatStateEventsObserved > 0;
      // Raw arrivals during this step, independent of whether any parsed.
      entry.stateChangedDelta = (entry.format?.stateChangedTotal ?? 0)
        - (before?.stateChangedTotal ?? 0);
      entry.stateChangedUnrecognisedDelta =
        (entry.format?.stateChangedUnrecognised ?? 0)
        - (before?.stateChangedUnrecognised ?? 0);
      if (drainRefresh) {
        const beforeDrainFormat = metrics.formatStateEvents.length;
        entry.drain = await client.drainScheduler({ timeoutMs: 30000 });
        entry.settleAfterDrain = await settleFormatState();
        entry.formatAfterDrain = formatOf(await client.getState());
        entry.formatStateEventsAfterDrain =
          metrics.formatStateEvents.length - beforeDrainFormat;
        entry.freshAfterDrain = entry.formatStateEventsAfterDrain > 0;
      }
      if (mainloopWait) {
        // No pump exists in this profile.  Record whether the engine's own
        // staleness flag clears with nothing but the main loop running, and
        // how long that took.
        entry.freshness = await awaitFreshFormatState(client);
      }
      entry.status = "passed";
    } catch (error) {
      entry.error = errorValue(error);
      entry.status = "failed";
    }
    log(entry);
  }
}

// Positive control: does the documented state pipeline produce anything at all
// in this profile?  set-bold's readback is an E1-C validated capability, so if
// it stays silent the instrument is at fault, and if it speaks while the three
// E2 payloads stay silent the difference is attributable to those commands.
async function runControl(client) {
  for (const enabled of [true, false]) {
    const entry = { action: "set-bold", enabled, status: "running" };
    metrics.control.push(entry);
    try {
      const beforeFormat = metrics.formatStateEvents.length;
      entry.formatBefore = formatOf(await client.getState());
      entry.result = await client.controlAction("set-bold", enabled, { timeoutMs: 30000 });
      entry.settle = await settleFormatState();
      entry.formatAfter = formatOf(await client.getState());
      entry.formatStateEventsObserved = metrics.formatStateEvents.length - beforeFormat;
      entry.status = "passed";
    } catch (error) {
      entry.error = errorValue(error);
      entry.status = "failed";
    }
    log(entry);
  }
}

async function runDispatch(documentHandle, client) {
  const sequence = mode === "a3" ? A3_STEPS
    : mode === "a4" ? A4_STEPS
      : DISPATCH_STEPS;
  for (const step of sequence) {
    const entry = { label: step.label, action: step.action, anchor: step.anchor, status: "running" };
    metrics.dispatch.push(entry);
    try {
      entry.placement = await caretAtAnchor(documentHandle, client, step.anchor, "search");
      if (drainRefresh) {
        // Finding 021 remediation: the engine now refuses to answer from a
        // cache the caret has moved away from, so the host refreshes first and
        // waits for the flush -- the same host-owned bounded wait E1-B uses
        // after click.  The engine never sleeps for this.
        entry.refresh = await client.drainScheduler({ timeoutMs: 30000 });
      }
      if (nudgePlacement) {
        try {
          entry.nudge = await client.nudgeCaret({ timeoutMs: 15000 });
        } catch (error) {
          entry.nudge = { error: errorValue(error) };
        }
      }
      if (mainloopWait) {
        // Candidate 1: the refresh step is a wait, not a pump.  The engine's
        // fail-closed precondition is unchanged; what changed is who makes the
        // state fresh -- the always-running upstream main loop (plus, in the
        // move experiment, the nudge dispatch above).
        entry.refresh = await awaitFreshFormatState(client);
      }
      entry.settleBefore = await settleFormatState();
      const stateBefore = await client.getState();
      entry.formatBefore = formatOf(stateBefore);
      entry.beforeRevision = documentHandle.revision;
      const started = performance.now();
      entry.result = await client.action(step.action, { timeoutMs: 30000 });
      entry.elapsedMs = Math.round(performance.now() - started);
      entry.status = "passed";
    } catch (error) {
      entry.error = errorValue(error);
      entry.status = "failed";
    }
    // Read the state after the dispatch whichever way it reported.  The old
    // shape only recorded it on success, so a barrier that failed *because of
    // what the state said* threw away the one reading that explains it -- which
    // is precisely the finding 031 case, where the postcondition string is
    // right there and simply is not the string being compared against.
    try {
      entry.settleAfter = await settleFormatState();
      entry.formatAfter = formatOf(await client.getState());
    } catch (error) {
      entry.formatAfterError = errorValue(error);
    }
    // Save regardless of how the dispatch reported, so the runner can judge the
    // document even when -- especially when -- the callback said something else.
    try {
      const buffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
      outputs.set(step.label, buffer);
      metrics.outputs.push({ label: step.label, bytes: buffer.byteLength });
      entry.saved = { label: step.label, bytes: buffer.byteLength };
    } catch (error) {
      entry.saveError = errorValue(error);
    }
    log(entry);
  }
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
      workerUrl: `./profiles/${profile}/sdk-worker.js`,
      timeoutMs: 30000,
      closeRecoveryTimeoutMs: 10000,
    });
    metrics.manifest = engine.manifest;
    engine.onEvent((event) => {
      if (event.event === "editor-state") {
        const record = {
          source: event.source,
          sourceSequence: event.sourceSequence,
          revision: event.revision,
          atMs: Math.round(performance.now()),
        };
        metrics.editorStateEvents.push(record);
        if (event.source === "format-state") {
          metrics.formatStateEvents.push({ ...record, format: formatOf(event) });
        }
        return;
      }
      if (event.event === "editor-callback-parse-error" || event.event === "worker-crashed"
          || event.event === "document-close-recovery-complete") {
        metrics.editorStateEvents.push({ source: event.event, revision: event.revision });
      }
    });

    const response = await fetch(`./e1-fixtures/${fixture.path}`);
    const input = await response.arrayBuffer();
    checkpoint("open", { bytes: input.byteLength });
    documentHandle = await engine.open(input, {
      name: fixture.path,
      transfer: true,
      timeoutMs: 180000,
    });
    const client = new FormatDiscoveryClient(documentHandle);
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

    metrics.openState = formatOf(await client.getState());
    // Ordered so each phase can only be explained one way.  Caret-only comes
    // first and is uncontaminated by any dispatch; the control then shows
    // whether the pipeline works at all; the caret-only sweep is repeated after
    // it to see whether a dispatch is what bootstraps the broadcast.
    checkpoint("readback-caret-only");
    await runReadback(documentHandle, client, metrics.readback, "search");
    await runReadback(documentHandle, client, metrics.readback, "click");
    checkpoint("control");
    await runControl(client);
    checkpoint("readback-after-control");
    await runReadback(documentHandle, client, metrics.readbackAfterControl, "search");
    checkpoint("dispatch");
    await runDispatch(documentHandle, client);

    checkpoint("close");
    await documentHandle.close({ timeoutMs: 30000 });
    documentHandle = null;
    engine.dispose();
    engine = null;

    const passedIn = (list) => list.filter((item) => item.status === "passed");
    const known = (list, field) => passedIn(list).some((item) => item.format?.[field] !== null);
    const anyList = [...metrics.readback, ...metrics.readbackAfterControl];
    // The fixture's own structure is the ground truth: E1-LIST-ONE sits inside
    // a <text:list>, "bold anchor" does not, and E1-STYLED-HEADING carries a
    // different paragraph style from the body paragraph.  A state that tracks
    // the caret has to reproduce those differences from fresh readings.
    const freshAt = (id) => passedIn(anyList).filter((item) => item.id === id && item.fresh);
    const anyFresh = (id, predicate) => freshAt(id).some((item) => predicate(item.format || {}));
    const caretTracking = (list) => {
      void list;
      const listInside = anyFresh("list-item", (format) => format.listBullet === true
        || format.listNumber === true);
      const listOutside = anyFresh("body-paragraph", (format) => format.listBullet === false
        && format.listNumber === false);
      const headingStyles = new Set(freshAt("heading").map((item) => item.format?.paragraphStyle));
      const bodyStyles = new Set(freshAt("body-paragraph").map((item) => item.format?.paragraphStyle));
      const styleTracked = headingStyles.size > 0 && bodyStyles.size > 0
        && [...headingStyles].every((style) => style !== null && !bodyStyles.has(style));
      return {
        listTracked: listInside && listOutside,
        listReadInsideList: listInside,
        listReadOutsideList: listOutside,
        styleTracked,
        headingStyles: [...headingStyles],
        bodyStyles: [...bodyStyles],
        freshPositions: passedIn(anyList).filter((item) => item.fresh).map((item) => item.id),
        stalePositions: passedIn(anyList).filter((item) => !item.fresh).map((item) => item.id),
      };
    };
    // A2's own gate: all three payloads must arrive, and at least one of them
    // must differ between caret positions.  A value that never changes could be
    // a constant we mistook for a reading.
    metrics.a2 = {
      listBulletKnown: known(anyList, "listBullet"),
      listNumberKnown: known(anyList, "listNumber"),
      paragraphStyleKnown: known(anyList, "paragraphStyle"),
      // Deliberately not "the values differ somewhere".  That earlier gate
      // passed on the plain null -> known transition at open, which says
      // nothing about whether a reading belongs to the paragraph the caret is
      // in.  Tracking means: a paragraph inside a list reads as inside a list,
      // a paragraph outside one reads as outside, and both readings are fresh.
      trackedCaret: caretTracking(anyList).listTracked
        && caretTracking(anyList).styleTracked,
      tracking: caretTracking(anyList),
      readbackComplete: passedIn(metrics.readback).length === READBACK_POSITIONS.length * 2,
      // The discriminator: whether a dispatch is what makes the state appear.
      caretOnlyProducedFormatState: metrics.readback.some(
        (item) => (item.formatStateEventsObserved || 0) > 0),
      caretMovedWithoutFormatState: metrics.readback.some(
        (item) => (item.editorStateEventsObserved || 0) > 0
          && (item.formatStateEventsObserved || 0) === 0),
      controlProducedFormatState: metrics.control.some(
        (item) => (item.formatStateEventsObserved || 0) > 0),
      caretTrackedAfterControl: passedIn(metrics.readbackAfterControl).some((item) => item.fresh),
    };
    metrics.rawCallbackExposed = metrics.formatStateEvents.some((event) => "payload" in event);
    if (mode.startsWith("mainloop")) {
      // The counters prove the loop ran; drainSchedulerCapabilityPresent
      // records whether a unit-test pump was even linked (false in the plain
      // mainloop profile, true by design in the PEI experiment).  The
      // document is closed by now, so the totals come from the last format
      // reading any phase recorded.
      const lastFormat = [
        ...metrics.readback.map((item) => item.format),
        ...metrics.readbackAfterControl.map((item) => item.format),
        ...metrics.dispatch.map((item) => item.refresh?.format),
        ...metrics.dispatch.map((item) => item.formatAfter),
      ].filter((format) => format && format.pollCount !== null).pop() ?? null;
      metrics.mainloopAttribution = {
        drainSchedulerCapabilityPresent:
          metrics.manifest?.capabilities?.includes("finding-016-scheduler-probe") === true,
        engineLoop: metrics.manifest?.diagnostic?.engineLoop ?? null,
        lastPollCount: lastFormat?.pollCount ?? null,
        lastIdlePollCount: lastFormat?.idlePollCount ?? null,
        refreshWaits: metrics.dispatch
          .map((item) => item.refresh)
          .filter(Boolean),
      };
    }
    metrics.pass = (
      metrics.crossOriginIsolated === true
      && (metrics.manifest?.diagnostic?.scope === "e2-paragraph-format-discovery"
        || metrics.manifest?.diagnostic?.scope === "e2-scheduler-attribution"
        || metrics.manifest?.diagnostic?.scope === "e2-mainloop-attribution"
        || metrics.manifest?.diagnostic?.scope === "e2-mainloop-pei-attribution")
      && metrics.manifest?.diagnostic?.formatBarrier === "verified-format-state-v1"
      && metrics.manifest?.diagnostic?.formatResultVerdictFieldsUsedForCompletion === false
      && metrics.a2.listBulletKnown
      && metrics.a2.listNumberKnown
      && metrics.a2.paragraphStyleKnown
      && metrics.a2.trackedCaret
      && metrics.a2.readbackComplete
      && !metrics.rawCallbackExposed
    );
    checkpoint("complete", { pass: metrics.pass, a2: metrics.a2 });
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
