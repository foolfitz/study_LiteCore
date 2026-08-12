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
// "wedge-trace" is finding 037's diagnostic: the same discriminator cases
// against the SAME wasm artifact as e2-format-discovery -- byte-identical,
// hash checked at packaging time -- with a worker copy that forwards the LOK
// callback stream the shipped one drops.  A barrier that never returns writes
// no evidence of its own, so the callback stream is the only record of how far
// the engine got; running it on a rebuilt engine would have answered a
// different artifact's question (finding 027).
const profile = mode === "scheduler-attribution"
  ? "e2-scheduler-attribution"
  : mode === "locale-attribution"
    ? "e2-locale-attribution"
    : mode === "mainloop-pei-attribution"
      ? "e2-mainloop-pei-attribution"
      : mode === "mainloop-attribution" || mode === "mainloop-move-attribution"
        ? "e2-mainloop-attribution"
        : mode === "wedge-trace" || mode === "wedge-split"
          ? "e2-wedge-trace"
          : "e2-format-discovery";
// Finding 037.  The guard shipped in c89f069e makes the hang unreachable, which
// is the point of it -- and also means the hang can only be studied on an
// earlier artifact.  Overriding the profile is how a diagnostic run reaches the
// pre-guard engine without any of this being rebuilt; the override is recorded
// in the metrics so a run can never be read as if it used the shipped one.
const profileOverride = params.get("profileOverride");
const activeProfile = profileOverride || profile;
// Which discriminator cases to run, in the order the table declares them.  A
// case that wedges the handle takes every later case down with it (finding
// 037), so being able to run one row plus its control is what makes the wedge
// measurable at all rather than a thing that happens at the end of a long run.
const caseFilter = (params.get("cases") || "")
  .split(",").map((value) => value.trim()).filter(Boolean);
// The worker only forwards the callback stream under debug.  Implied by
// wedge-trace, so a traced run cannot be started without it.
const engineDebug = params.get("debug") === "1"
  || mode === "wedge-trace" || mode === "wedge-split";
// Finding 037.  The five closed actions share one read step, so all five are
// expected to wedge on the same paragraph -- but "expected" is not "measured",
// and once a guard ships the wedge stops being reachable at all.  So the other
// four have to be measured before the fix or never.  wedge-trace only: the
// discriminator's own cases declare their action for a reason.
const actionOverride = mode === "wedge-trace" ? params.get("action") : null;
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
  profile: activeProfile,
  profileOverride: profileOverride || null,
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
  a5: null,
  discriminator: null,
  // Finding 037.  The last engineTrace entry before the record ends is the
  // last thing the engine reported doing, which for a barrier that never
  // returns is the only evidence there is.  A ring rather than a list: the
  // preamble emits thousands of tile invalidations and keeping them all would
  // trade the answer for the noise in front of it.  Counting by id separately
  // means the ring can drop entries without the totals losing them.
  engineTrace: [],
  engineTraceDropped: 0,
  engineTraceCounts: {},
  cancelResults: [],
  wedgeSplit: null,
  closeMs: null,
  control: [],
  readbackAfterControl: [],
  dispatch: [],
  outputs: [],
  error: null,
  pass: false,
};
const outputs = new Map();
// The liveness ladder needs the engine itself, not a document handle: two of
// its three rungs are about whether anything below the handle still answers.
let activeEngine = null;
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

// A5: the negative and boundary cases the frozen matrix names.
//
// These are run through the real client, never by hand-crafting an engine
// message -- a rejection that only a fabricated request can trigger says
// nothing about what a caller can actually reach.
// Where the crosstalk case moves the caret to.  It must NOT be a paragraph
// already in the state the case dispatches, or the test cannot tell a correct
// restore from a hijacked read of this very paragraph -- the case would pass
// either way.  styled-list originally pointed at E1-STYLED-HEADING, which is a
// Heading 1 in the fixture while the case dispatches set-paragraph-heading:
// exactly the trap finding 033 describes, built into its own test.
const A5_CROSSTALK_ANCHORS = {
  "styled-list": "E1-LIST-ONE",
  "multi-paragraph": "E1-MULTI-START",
  "plain-grapheme": "E1-PLAIN-START",
  "table-boundary": "E1-TABLE-BEFORE",
};
// The anchor A5 drives its cases from, per fixture.  table-boundary points at
// a table cell on purpose: that is the boundary case.
const A5_ANCHORS = {
  ...A3_ANCHORS,
  "table-boundary": "E1-CELL-A1",
};

async function runA5(client, documentHandle, anchorText) {
  const crosstalkAnchor = A5_CROSSTALK_ANCHORS[fixtureId] || null;
  const place = (target) => caretAtAnchor(documentHandle, client, target, "search");
  const cases = [];

  async function record(name, expectation, body) {
    const entry = { case: name, expects: expectation };
    // Resync before the case as well as after it.  An action that the caller
    // timed out on can still complete afterwards and advance the revision, so
    // a value sampled at the end of the previous case is already behind by the
    // time this one dispatches.
    try {
      const before = await client.getState();
      if (Number.isInteger(before?.revision))
        documentHandle.revision = before.revision;
      entry.revisionBefore = documentHandle.revision;
    } catch (error) {
      entry.revisionBeforeError = errorValue(error);
    }
    try {
      entry.outcome = await body(entry);
      entry.status = "completed";
    } catch (error) {
      entry.error = errorValue(error);
      entry.status = "rejected";
    }
    try {
      const state = await client.getState();
      entry.stateAfter = formatOf(state);
      // Resync the revision between cases.  A case that ends in a rejection
      // leaves the client's cached revision behind whatever the engine did,
      // and the next case then fails with STALE_REVISION before it dispatches
      // anything -- which is a harness artefact wearing the costume of a
      // product result.  The table-boundary case was reported that way once.
      if (Number.isInteger(state?.revision))
        documentHandle.revision = state.revision;
      entry.revisionAfter = documentHandle.revision;
    } catch (error) {
      entry.stateAfterError = errorValue(error);
    }
    cases.push(entry);
    log(entry);
  }

  // 1. unsupported-action: a name outside the closed set must be refused by
  //    type, before anything is dispatched.
  await record("unsupported-action", "typed rejection, nothing dispatched",
    async () => client.action("set-paragraph-subtitle"));

  // 2. stale-revision: an action carrying a revision the document has moved
  //    past must not mutate.  The revision is captured, then deliberately
  //    aged by performing a real action.
  await record("stale-revision", "typed rejection, zero mutation", async (entry) => {
    await place(anchorText);
    const stale = documentHandle.revision;
    await client.action("set-list-unordered");
    entry.staleRevision = stale;
    entry.currentRevision = documentHandle.revision;
    return client.action("set-list-ordered", { expectedRevision: stale });
  });

  // 3. state-crosstalk: move the caret to an unrelated paragraph immediately
  //    after dispatching.  The barrier reads the document itself now, so the
  //    risk is that it reads the paragraph the caret moved to.  The saved file
  //    is what settles it, judged by the runner.
  //
  //    The caret move is now refused while a barrier is in flight (finding 033
  //    BUSY gate), so the attempt is recorded either way rather than aborting
  //    the case.  The case does not assert the refusal: what it asserts is that
  //    the completion describes the dispatched paragraph, and that has to hold
  //    whether the move was refused or let through.
  await record("state-crosstalk", "completion describes the dispatched paragraph",
    async (entry) => {
      await place(anchorText);
      const pending = client.action("set-paragraph-heading");
      entry.movedTo = crosstalkAnchor;
      try {
        entry.crosstalkPlacement = await place(crosstalkAnchor);
        entry.caretMoveAccepted = true;
      } catch (error) {
        entry.caretMoveAccepted = false;
        entry.caretMoveError = errorValue(error);
      }
      return pending;
    });

  // 5. table-boundary: a paragraph inside a table cell.  The matrix says a
  //    typed rejection followed by a fresh Worker; what it must never be is a
  //    completion the document does not support, so the outcome is recorded
  //    either way and the saved file settles it.
  if (fixtureId === "table-boundary") {
    await record("table-boundary", "typed outcome, and the document agrees",
      async (entry) => {
        entry.placement = await place(anchorText);
        return client.action("set-list-unordered");
      });
  }

  // 6. list-teardown: finding 012 was a close that never returned on a styled
  //    document.  Toggling a list rewrites the paragraph into <text:list>
  //    wrappers, which is the same class of structure, so the close after this
  //    cycle is timed rather than assumed.
  await record("list-teardown", "close returns well inside the timeout",
    async (entry) => {
      await place(anchorText);
      await client.action("set-list-unordered");
      await place(anchorText);
      await client.action("set-list-ordered");
      await place(anchorText);
      await client.action("set-list-none");
      entry.cycleComplete = true;
      return null;
    });

  // Last on purpose.  A caller timeout leaves an action still in flight, and
  // when it completes it advances the revision past what the client cached --
  // so every case after this one starts stale and gets refused before it
  // dispatches anything.  That is how table-boundary first reported
  // STALE_REVISION and looked, briefly, like a product result.
  // timeout-after-dispatch: a caller timeout while the barrier is in
  //    flight.  No retry may be issued, and the next action must be refused
  //    as BUSY rather than queued behind it.
  await record("timeout-after-dispatch", "caller timeout, then BUSY, no retry",
    async (entry) => {
      await place(anchorText);
      try {
        await client.action("set-list-ordered", { timeoutMs: 1 });
        entry.timedOut = false;
      } catch (error) {
        entry.timedOut = true;
        entry.timeoutError = errorValue(error);
      }
      try {
        return await client.action("set-list-none", { timeoutMs: 30000 });
      } catch (error) {
        entry.followUpError = errorValue(error);
        return null;
      }
    });

  return cases;
}

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  logNode.textContent += `${text}\n`;
}

// LibreOfficeKitEnums.h, copied for the ids this diagnostic can actually meet.
// An id with no name here still records as a number -- naming is for reading
// the trace, not for deciding what to keep, and a filter that dropped unnamed
// ids would hide exactly the callback nobody expected.
const LOK_CALLBACK_NAMES = {
  0: "INVALIDATE_TILES", 1: "INVALIDATE_VISIBLE_CURSOR", 2: "TEXT_SELECTION",
  3: "TEXT_SELECTION_START", 4: "TEXT_SELECTION_END", 5: "CURSOR_VISIBLE",
  6: "GRAPHIC_SELECTION", 8: "STATE_CHANGED", 9: "STATUS_INDICATOR_START",
  10: "STATUS_INDICATOR_SET_VALUE", 11: "STATUS_INDICATOR_FINISH",
  12: "SEARCH_NOT_FOUND", 13: "DOCUMENT_SIZE_CHANGED",
  15: "SEARCH_RESULT_SELECTION", 16: "UNO_COMMAND_RESULT", 18: "MOUSE_POINTER",
  22: "ERROR", 23: "CONTEXT_MENU", 24: "INVALIDATE_VIEW_CURSOR",
  25: "TEXT_VIEW_SELECTION", 27: "GRAPHIC_VIEW_SELECTION",
  28: "VIEW_CURSOR_VISIBLE", 33: "INVALIDATE_HEADER", 35: "RULER_UPDATE",
  36: "WINDOW", 38: "CLIPBOARD_CHANGED", 39: "CONTEXT_CHANGED",
  45: "REFERENCE_MARKS", 48: "TAB_STOP_LIST", 52: "DOCUMENT_BACKGROUND_COLOR",
  55: "CONTENT_CONTROL", 57: "FONTS_MISSING", 60: "VIEW_RENDER_STATE",
  70: "CORE_LOG", 71: "TOOLTIP",
};

const ENGINE_TRACE_LIMIT = 900;

// Finding 037.  Each entry is one LOK callback as the engine saw it, stamped
// on arrival at the page.  The stamp is what makes a gap readable: "the last
// callback was UNO_COMMAND_RESULT at 41 200 ms and the run ended at 61 300 ms"
// is a measurement, while the same list without times is just an ordering.
function recordEngineTrace(detail) {
  const id = Number(detail?.id);
  const key = `${id}:${LOK_CALLBACK_NAMES[id] || "UNNAMED"}`;
  metrics.engineTraceCounts[key] = (metrics.engineTraceCounts[key] || 0) + 1;
  metrics.engineTrace.push({
    id,
    name: LOK_CALLBACK_NAMES[id] || null,
    atMs: Math.round(performance.now()),
    // Truncated, not dropped: UNO_COMMAND_RESULT carries which command
    // finished and TEXT_SELECTION carries whether anything is selected, and
    // both of those are the difference between "a callback arrived" and
    // "the barrier could have advanced on it".
    payload: String(detail?.payload || "").slice(0, 240),
  });
  while (metrics.engineTrace.length > ENGINE_TRACE_LIMIT) {
    metrics.engineTrace.shift();
    ++metrics.engineTraceDropped;
  }
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
// The format barrier's wedge, measured rather than argued.
//
// `.uno:EndOfParaSel` has nothing to select on an empty paragraph, so the
// non-empty TEXT_SELECTION the barrier waits for in AwaitingSelection never
// arrives.  Every fixture used by A3/A4/A5 has text in every paragraph, which
// is why 375 judged dispatches never reached this -- and "press the list button
// on a blank line" is an ordinary editing gesture, not an exotic one.
//
// This case is written so it gives *different* answers on the two engines it
// will run against: on a build with no deadline the action dies of the client
// timeout and the handle is wedged (the follow-up is refused BUSY); on a build
// with one it fails typed, quickly, and the handle still works.  Both outcomes
// are recorded; neither is asserted here, because the judgement belongs in the
// validator where it can be read.
async function runDeadline(client, documentHandle) {
  const entry = { case: "empty-paragraph-barrier", status: "running" };
  try {
    // Placement is geometric, so it is checked rather than trusted: the caret
    // must land strictly between the two text anchors, or this measures
    // nothing and says so instead of reporting a wedge it did not cause.
    const before = await documentHandle.search("E1-EMPTY-BEFORE");
    const after = await documentHandle.search("E1-EMPTY-AFTER");
    const beforeRect = firstRectangle(before);
    const afterRect = firstRectangle(after);
    entry.anchors = { before: beforeRect, after: afterRect };
    if (!beforeRect || !afterRect)
      throw new Error("empty-paragraph anchors not found");
    const x = beforeRect.x + 1;
    const y = Math.round((beforeRect.y + beforeRect.height + afterRect.y) / 2);
    entry.caret = { x, y };
    // Named for what it actually checks.  It was `caretIsBetweenAnchors`, which
    // reads as a statement about where the caret went -- and it passed on a run
    // whose readback proved the caret was on the paragraph *above* the empty
    // one.  It only ever validated the coordinate we asked for.
    //
    // Where the caret really landed is answerable, but only from the readback
    // markup, which is recorded in `outcome`/`error` below.  This case does not
    // assert it; the native probe at
    // findings/evidence/sdk-e2/discovery/paragraph-selection-edges/ is what
    // settles caret position, because there the caret can be walked paragraph
    // by paragraph instead of guessed at from geometry.
    entry.caretRequestedBetweenAnchors =
      y > beforeRect.y + beforeRect.height && y < afterRect.y;
    await client.placeCaret(x, y);

    const started = performance.now();
    try {
      entry.outcome = await client.action("set-list-unordered", { timeoutMs: 20000 });
      entry.status = "completed";
    } catch (error) {
      entry.error = errorValue(error);
      entry.status = "rejected";
    }
    entry.elapsedMs = Math.round(performance.now() - started);

    // The wedge signature: is the handle still usable afterwards?  A search is
    // the cheapest caret-moving command and is exactly what the BUSY gate
    // refuses while a barrier is in flight.
    try {
      const probe = await documentHandle.search("E1-EMPTY-AFTER");
      entry.handleUsableAfter = Boolean(probe?.found);
    } catch (error) {
      entry.handleUsableAfter = false;
      entry.handleError = errorValue(error);
    }
  } catch (error) {
    entry.status = "failed";
    entry.setupError = errorValue(error);
  }
  log(entry);
  return [entry];
}

// Finding 034 discriminators.
//
// The barrier reads whichever paragraph its select step lands on, and until now
// nothing in this harness could put the caret anywhere but offset Len() --
// caretAtAnchor places at rectangle.x + width, and a search leaves the caret
// after its match.  That is the one offset where the current selection pair is
// correct, which is why 375 judged dispatches never saw this.
//
// Each case names both the text of the paragraph it dispatches on and the text
// of the paragraph the escape would land on, and the judgement is which of the
// two appears in the readback markup.  That check is impossible to satisfy from
// both sides at once -- unlike "is the readback in the target state", which
// finding 033 already showed passes whichever paragraph was read whenever the
// neighbour happens to match.
//
// The cases are written to give different answers on the two builds they run
// against, and the old build doubles as the instrument that proves the gesture
// reaches offset 0 at all: if HOME did not get there, the escape would not fire
// and the old-build run would look exactly like the new one.
const DISCRIMINATOR_CASES = {
  "styled-list": [
    {
      case: "offset-len-control",
      anchor: "E1-STYLED-END",
      dispatchedText: "E1-STYLED-END",
      escapeText: "E1-LIST-TWO",
      home: false,
      action: "set-list-unordered",
      expects: "passes on both builds; without it a failure below could be the suite rather than the offset",
    },
    {
      // Not an offset case at all -- the caret stays at offset Len, where the
      // old select pair is correct -- and it is here because the offset version
      // of it was measured first and its failure had a second cause.
      //
      // This paragraph is the only one in any E2 fixture carrying character
      // formatting, and formatTagIsKnown accepts ul/ol/li/h1/p and nothing
      // else, so the read meets <b>, sets unknownTag and fails closed.  That is
      // a defect in the readback's closed tag set, not in the select step, and
      // it predates this build: every A3/A4/A5 anchor is a plain paragraph,
      // which is why 375 judged dispatches never met it.  Kept as its own case
      // so the two causes cannot be confused for each other again.
      case: "inline-formatting-readback",
      anchor: "bold anchor",
      dispatchedText: "bold anchor",
      escapeText: "E1-STYLED-HEADING",
      home: false,
      action: "set-list-unordered",
      expects: "fails on both builds, unknownTag=true -- the readback's tag set, not the caret offset",
    },
    {
      // The paragraph above is already a bulleted list item, so an escaped read
      // finds the target state and the barrier reports verified success for a
      // paragraph it never looked at.  This is the shape finding 033 named and
      // could only reach through caller concurrency; here one keystroke does it.
      //
      // Named for what it demonstrates and no more.  It is NOT "the document
      // ended up wrong": E1-LIST-TWO is already a list item in the fixture, so
      // the outcome is right by construction.  What is false is the claim to
      // have verified it -- the markup carries the other paragraph's text.  An
      // outcome-level false positive additionally needs a dispatch that fails,
      // which is a separate condition (A5 reaches one at the table boundary).
      case: "offset-zero-verifies-wrong-paragraph",
      anchor: "E1-LIST-TWO",
      dispatchedText: "E1-LIST-TWO",
      escapeText: "E1-LIST-ONE",
      home: true,
      action: "set-list-unordered",
      expects: "old build: reports verified-format-readback while the markup carries E1-LIST-ONE",
    },
  ],
  // The escape case moved here from styled-list.  multi-paragraph has five
  // plain paragraphs, no lists and no character formatting, so an escape shows
  // up as an escape and nothing else can also be failing.
  "multi-paragraph": [
    {
      case: "offset-len-control",
      anchor: "E1-MULTI-END omega",
      dispatchedText: "E1-MULTI-END omega",
      escapeText: "\u7b2c\u56db\u6bb5\u843d delta",
      home: false,
      action: "set-list-unordered",
      expects: "passes on both builds",
    },
    {
      case: "offset-zero-escapes-to-previous",
      anchor: "\u7b2c\u4e09\u6bb5\u8de8\u884c gamma",
      dispatchedText: "\u7b2c\u4e09\u6bb5\u8de8\u884c gamma",
      escapeText: "\u7b2c\u4e8c\u6bb5\u4e2d\u6587 beta",
      home: true,
      action: "set-list-unordered",
      expects: "old build: reads the paragraph above and reports failure while the document did become a list",
    },
  ],
  "empty-paragraph": [
    {
      // Placement by keystroke, not by geometry.  The geometric attempt in the
      // deadline mode landed on the paragraph above and its own check validated
      // the coordinate it had asked for rather than where the caret went.
      case: "empty-mid-document",
      anchor: "E1-EMPTY-BEFORE",
      dispatchedText: null,
      escapeText: "E1-EMPTY-BEFORE",
      down: 1,
      home: false,
      action: "set-list-unordered",
      expects: "selection spans two paragraphs; must fail closed, and on a build with the multi-block guard it must say so by type",
    },
    {
      // The last paragraph of the document, where finding 034 measured no
      // selection at all (selType 0).  Nothing will ever advance the barrier
      // out of AwaitingSelection here.
      case: "empty-document-end",
      anchor: "E1-EMPTY-AFTER",
      dispatchedText: null,
      escapeText: "E1-EMPTY-AFTER",
      down: 1,
      home: false,
      action: "set-list-unordered",
      expects: "the stall the deadline exists to end; must fail typed and quickly, and the handle must still work",
    },
  ],
  // Finding 035 / M2, run on the WASM engine.  Two jobs at once.
  //
  // One: the structural set was decided from a NATIVE 26.8 sweep, and the
  // barrier ships in WASM.  Same coreCommit and no worktree patch touches sw/,
  // but the two builds are not byte-identical -- the CSS property order inside
  // a style attribute is reversed between them -- so "same serialiser" is an
  // inference until each shape is read on this side too.
  //
  // Two: the parser was verified by slicing it out of probe_engine.cpp and
  // compiling that text natively.  That tests the source.  This tests the
  // artifact that ships, which is the thing a verdict can be bound to.
  //
  // set-list-none is the action throughout, because on a paragraph that is not
  // a list item it changes nothing while still driving the full postcondition
  // read.  PC-LIST-ITEM is the one row where it really mutates, so it is last.
  "paragraph-content": [
    ...[
      ["PC-PLAIN", "PC-H2", "verified: the shape the old tag set already accepted"],
      ["PC-H2", "PC-H3", "verified, blockTag h2: refused as an unknown tag before this build"],
      ["PC-H3", "PC-H4", "verified, blockTag h3"],
      ["PC-H4", "PC-H5", "verified, blockTag h4"],
      ["PC-H5", "PC-H6", "verified, blockTag h5"],
      ["PC-H6", "PC-H7", "verified, blockTag h6"],
      ["PC-H7", "PC-H10", "verified, blockTag p: ODF outline level 7 has no HTML tag and serialises as a paragraph"],
      ["PC-H10", "PC-PRE", "verified, blockTag p: same narrowing at level 10"],
      ["PC-PRE", "PC-QUOTE", "verified, blockTag pre"],
      ["PC-QUOTE", "PC-TITLE", "verified, blockTag blockquote"],
      ["PC-TITLE", "PC-SUBTITLE", "verified, blockTag p: Title is indistinguishable from body text here"],
      ["PC-SUBTITLE", "PC-LINK", "verified, blockTag p"],
      ["PC-LINK", "PC-BOOKMARK", "verified: <a> is nested, so it is ignored rather than fatal"],
      ["PC-BOOKMARK", "PC-FOOTNOTE", "verified: the bookmark's <a name=...> is nested too"],
      ["PC-COMMENT", "PC-IMAGE", "verified: the annotation serialises as an HTML comment, which carries no tag name"],
      ["PC-BREAK", "PC-CJK-BOLD", "verified: <br/> does not open a block"],
      ["PC-CJK-BOLD", "PC-SECTION", "verified: the CJK font run and its <b> are nested -- the paragraph finding 035 was written about"],
      ["PC-SECTION", "PC-LIST-ITEM", "verified: text:section leaves no wrapper in the readback"],
    ].map(([anchor, neighbour, expects]) => ({
      case: anchor.toLowerCase(),
      anchor,
      dispatchedText: anchor,
      escapeText: neighbour,
      home: false,
      action: "set-list-none",
      expects,
    })),
    {
      // The one row that must still be refused, and the reason the whole
      // structural set had to be decided rather than guessed.  A footnote's
      // body is a second body-level block, so either the div is unknown or the
      // block count is two; it is refused under its own shape so that neither
      // the cross-paragraph channel nor the unmeasured-tag channel has to carry
      // traffic that belongs to a measured, deliberate refusal.
      case: "pc-footnote",
      anchor: "PC-FOOTNOTE",
      dispatchedText: "PC-FOOTNOTE",
      escapeText: "PC-COMMENT",
      home: false,
      action: "set-list-none",
      expects: "REFUSED with failureShape footnote-apparatus-readback and footnoteApparatus true, not multi-block-readback and not unknown-structural-tag",
    },
    {
      // Last on purpose: this is the only row where set-list-none is not a
      // no-op, so running it earlier would edit the document the later rows are
      // read from.
      case: "pc-list-item",
      anchor: "PC-LIST-ITEM",
      dispatchedText: "PC-LIST-ITEM",
      escapeText: "PC-SECTION",
      home: false,
      action: "set-list-none",
      expects: "verified: the list is removed, so the read comes back with no list tag",
    },
    {
      // LAST, and not for tidiness.  On the first run of this suite this row
      // timed out at 20 s, the handle stopped answering, and every row after it
      // died on getState -- so five shapes went unmeasured because of where one
      // shape sat in the list.  It is the only row whose selection type is
      // COMPLEX (LOK_SELTYPE_COMPLEX, measured natively in M2), and the 5 s
      // per-stage deadline did not rescue it, which is a defect in its own
      // right.  Kept in the suite because dropping it would hide the wedge;
      // kept last so it cannot take the other rows down with it again -- and
      // still last now that the guard exists, because "the guard held" is a
      // claim about this row that the rows after it must not depend on.
      case: "pc-image",
      anchor: "PC-IMAGE",
      dispatchedText: "PC-IMAGE",
      escapeText: "PC-BREAK",
      home: false,
      action: "set-list-none",
      expects: "REFUSED with failureShape selection-type-not-readable and selectionType 3, in under a second -- finding 037's guard. Before the guard this row wedged the engine thread at 20 s and took the handle with it",
    },
  ],
  // Finding 037, guard coverage.  The wedge-split census (2026-08-12) read each
  // of these selection types without ever making the html read: as-char png,
  // svg, unresolvable link and char-anchored frames are all COMPLEX, so the
  // guard refuses them -- and so is IV-TEXTBOX, a frame with no image in it at
  // all, which is why "inline image" turned out to be the wrong name for the
  // trigger.
  //
  // IV-PARAGRAPH is why this table exists.  It reads back as TEXT, so the guard
  // lets it through to the html read, and whether that read returns is exactly
  // the question the type cannot answer for it.  It runs LAST for the same
  // reason PC-IMAGE does: if it wedges, the rows after it go unmeasured rather
  // than measured.
  "image-variants": [
    ...[
      ["IV-PLAIN", "IV-TAIL", "verified: no frame anywhere, the control that says the run worked"],
      ["IV-ASCHAR", "IV-PLAIN", "REFUSED selection-type-not-readable, selectionType 3"],
      ["IV-SVG", "IV-PLAIN", "REFUSED selection-type-not-readable: a vector graphic is COMPLEX too"],
      ["IV-LINKED", "IV-PLAIN", "REFUSED selection-type-not-readable: an unresolvable link is still COMPLEX"],
      ["IV-CHAR", "IV-PLAIN", "REFUSED selection-type-not-readable: char anchoring is COMPLEX"],
      ["IV-TEXTBOX", "IV-PLAIN", "REFUSED selection-type-not-readable: a frame with NO image is COMPLEX, so the trigger is the frame"],
      ["IV-LIST", "IV-PLAIN", "REFUSED selection-type-not-readable: inside a list item as well"],
      ["IV-TAIL", "IV-PLAIN", "verified: the paragraph after the frames still reads back"],
      ["IV-PARAGRAPH", "IV-TAIL", "OPEN: reads back as TEXT, so the guard does not refuse it -- does the html read return?"],
    ].map(([anchor, neighbour, expects]) => ({
      case: anchor.toLowerCase(),
      anchor,
      dispatchedText: anchor,
      escapeText: neighbour,
      home: false,
      action: "set-list-none",
      expects,
    })),
  ],
};

function barrierOf(outcome, error) {
  return outcome?.formatBarrier || error?.details?.formatBarrier || null;
}

// Counts the block-level tags in the readback markup.  Two of them means the
// selection covered more than one paragraph, so whatever the barrier concluded
// was concluded about an unknown mixture.
function blockTagCensus(html) {
  const text = String(html || "");
  const count = (pattern) => (text.match(pattern) || []).length;
  return {
    p: count(/<p[\s>]/gi),
    h1: count(/<h1[\s>]/gi),
    li: count(/<li[\s>]/gi),
    ul: count(/<ul[\s>]/gi),
    ol: count(/<ol[\s>]/gi),
  };
}

async function runDiscriminator(client, documentHandle) {
  const declared = DISCRIMINATOR_CASES[fixtureId];
  if (!declared)
    throw new Error(`no discriminator cases for fixture: ${fixtureId}`);
  // A named case that does not exist is a typo, and a typo that silently runs
  // nothing looks exactly like a case that passed.
  for (const name of caseFilter) {
    if (!declared.some((definition) => definition.case === name))
      throw new Error(`unknown discriminator case: ${name}`);
  }
  const cases = caseFilter.length
    ? declared.filter((definition) => caseFilter.includes(definition.case))
    : declared;
  const results = [];
  for (const declaredCase of cases) {
    const definition = actionOverride
      ? { ...declaredCase, action: actionOverride }
      : declaredCase;
    const entry = {
      case: definition.case,
      expects: definition.expects,
      action: definition.action,
      // Recorded whenever it is in force, so a row cannot be read as if it had
      // run the action its `expects` was written for.
      actionOverride: actionOverride || null,
      declaredAction: declaredCase.action,
      dispatchedText: definition.dispatchedText,
      escapeText: definition.escapeText,
      status: "running",
    };
    try {
      // Resync first: a case that ended in a rejection leaves the cached
      // revision behind the engine's, and the next one then dies of
      // STALE_REVISION before dispatching anything -- a harness artefact in the
      // costume of a product result.
      const before = await client.getState();
      if (Number.isInteger(before?.revision))
        documentHandle.revision = before.revision;

      entry.placement = await caretAtAnchor(
        documentHandle, client, definition.anchor, "search");
      for (let step = 0; step < (definition.down || 0); ++step)
        await client.moveCaret("move-line-down");

      const caretBefore = (await client.getState())?.caret || null;
      if (definition.home) {
        await client.moveCaret("move-line-home");
        const caretAfter = (await client.getState())?.caret || null;
        entry.caret = { before: caretBefore, after: caretAfter };
        // Recorded, not asserted.  It answers "did the keystroke move the caret
        // towards the start of the same line", which is what makes a null
        // result readable; it does not by itself prove offset 0, and saying it
        // did would repeat the mistake caretRequestedBetweenAnchors made.
        //
        // Tested on the coordinates, not on an `available` flag: the worker's
        // normalised caret carries x/y/width/height and no such field, so the
        // first version of this line read false on a run where the caret had
        // demonstrably moved 2026 twips left on the same line.  A flag that is
        // false whether or not the thing happened is not a check.
        const finite = (rect) => Number.isFinite(rect?.x) && Number.isFinite(rect?.y);
        entry.caretMovedLeftOnSameLine = Boolean(
          finite(caretBefore) && finite(caretAfter)
          && caretAfter.x < caretBefore.x && caretAfter.y === caretBefore.y);
      } else {
        entry.caret = { before: caretBefore, after: caretBefore };
      }

      const started = performance.now();
      try {
        entry.outcome = await client.action(definition.action, { timeoutMs: 20000 });
        entry.status = "completed";
      } catch (error) {
        entry.error = errorValue(error);
        entry.status = "rejected";
      }
      entry.elapsedMs = Math.round(performance.now() - started);

      const barrier = barrierOf(entry.outcome, entry.error);
      const html = barrier?.readback?.html || "";
      entry.readback = {
        html,
        bytes: barrier?.readback?.bytes ?? null,
        listTag: barrier?.readback?.listTag ?? null,
        blockTag: barrier?.readback?.blockTag ?? null,
        parsed: barrier?.readback?.parsed ?? null,
        // Finding 035 / M2.  The scan now has three ways to stop early and each
        // reports a different shape; recording only "it failed" would put them
        // back into the one bucket the split exists to break up.  unknownTagName
        // is the one field that turns "we refused" into something actionable.
        unknownTag: barrier?.readback?.unknownTag ?? null,
        unknownTagName: barrier?.readback?.unknownTagName ?? null,
        malformedNesting: barrier?.readback?.malformedNesting ?? null,
        footnoteApparatus: barrier?.readback?.footnoteApparatus ?? null,
        multiBlock: barrier?.readback?.multiBlock ?? null,
        blockCount: barrier?.readback?.blockCount ?? null,
        itemCount: barrier?.readback?.itemCount ?? null,
        failureShape: barrier?.failureShape ?? null,
        restoreConfirmed: barrier?.readback?.restoreConfirmed ?? null,
        blockTags: blockTagCensus(html),
      };
      // Finding 037.  Recorded on every row, not only the refused ones: this
      // is what makes "which paragraph shapes does the guard refuse?" a
      // question ordinary sweep evidence answers.  -1 means the barrier ended
      // before the read step, which is not the same as "the selection was
      // fine".
      entry.selectionType = barrier?.selectionType ?? null;
      entry.selectionTypeReadable = barrier?.selectionTypeReadable ?? null;
      // The whole point of the suite.  Both flags are recorded even when they
      // agree, because "neither text is present" is its own answer and must not
      // be reported as "the right one was".
      // Searched with the tags stripped.  The serialiser splits a paragraph
      // across <font>/<span> whenever a run needs a different font -- which it
      // does for every CJK run -- so "第三段跨行 gamma" is never contiguous in
      // the markup, and a raw includes() reported false for both texts on a run
      // where the markup plainly carried one of them.  Whitespace is collapsed
      // for the same reason: the split leaves a space inside the span.
      const flat = html.replace(/<[^>]*>/g, "").replace(/\s+/g, " ");
      const carries = (needle) => flat.includes(needle.replace(/\s+/g, " "));
      entry.markupHasDispatchedText = definition.dispatchedText
        ? carries(definition.dispatchedText) : null;
      entry.markupHasEscapeText = definition.escapeText
        ? carries(definition.escapeText) : null;
      // Recorded so a false above stays distinguishable from "the retained
      // markup stopped before the body".  2048 bytes is the cap and these
      // readbacks are ~600, but a longer paragraph would reach it.
      entry.readback.retainedReachedBody = html.includes("<body");

      // The wedge signature: is the handle still usable?  A search is the
      // cheapest caret mover and is exactly what the BUSY gate refuses while a
      // barrier is in flight.
      try {
        const probe = await documentHandle.search(definition.anchor);
        entry.handleUsableAfter = Boolean(probe?.found);
      } catch (error) {
        entry.handleUsableAfter = false;
        entry.handleError = errorValue(error);
      }
      const after = await client.getState();
      if (Number.isInteger(after?.revision))
        documentHandle.revision = after.revision;
      entry.stateAfter = formatOf(after);
    } catch (error) {
      entry.status = "failed";
      entry.setupError = errorValue(error);
    }
    // Outside the try on purpose: the rung that matters most is the one after a
    // case that threw.
    if (mode === "wedge-trace")
      entry.liveness = await livenessLadder(client);
    results.push(entry);
    log(entry);
  }
  return results;
}

// Finding 037, second stage.  The callback trace located the wedge inside the
// barrier's read step, which contains exactly two LOK calls that could fail to
// return -- getTextSelection("text/html") and setTextSelection(RESET) -- and
// the callback stream cannot separate them, because neither emits anything on
// the way in.  So drive each one on its own, on the same paragraph, without the
// barrier: mouse-drag the selection into place, ask for the selection text
// (which is the same getFromTransferable machinery the html read uses), then
// issue the reset by itself.
//
// PC-PLAIN runs the identical sequence first.  A step that hangs on both rows
// is a property of the probe, not of the image.
// Per fixture.  image-variants pulls the frame apart one property at a time,
// because finding 037's guard keys on the selection type and the only shape
// ever measured as COMPLEX is an as-char embedded PNG -- one sample.  A shape
// that reports TEXT and hangs anyway would walk straight through the guard, and
// this mode is the safe way to ask: it selects and reads the type, and never
// makes the html read that does not return.
const WEDGE_SPLIT_ANCHORS = {
  "paragraph-content": ["PC-PLAIN", "PC-IMAGE"],
  "image-variants": ["IV-PLAIN", "IV-ASCHAR", "IV-SVG", "IV-LINKED", "IV-CHAR",
                     "IV-PARAGRAPH", "IV-TEXTBOX", "IV-LIST", "IV-TAIL"],
  // Finding 012's open question.  The rows barely matter here -- what the run
  // is for is the close at the end of it, on a document that has frames and no
  // images anywhere.
  "frame-no-image": ["FNI-PLAIN", "FNI-TEXTBOX", "FNI-TAIL"],
  "frame-paragraph-anchored": ["FPA-PLAIN", "FPA-FRAME", "FPA-TAIL"],
};
const WEDGE_SPLIT_TIMEOUT_MS = 10000;

async function runWedgeSplit(client, documentHandle) {
  const declared = WEDGE_SPLIT_ANCHORS[fixtureId];
  if (!declared)
    throw new Error(`no wedge-split anchors for fixture: ${fixtureId}`);
  for (const name of caseFilter) {
    if (!declared.includes(name))
      throw new Error(`unknown wedge-split anchor: ${name}`);
  }
  const anchors = caseFilter.length
    ? declared.filter((name) => caseFilter.includes(name)) : declared;
  const results = [];
  for (const anchor of anchors) {
    const entry = { anchor, steps: [] };
    const step = async (name, fn) => {
      const started = performance.now();
      const record = { step: name, atMs: Math.round(started) };
      try {
        record.value = await fn();
        record.status = "completed";
      } catch (error) {
        record.status = "failed";
        record.error = errorValue(error);
      }
      record.elapsedMs = Math.round(performance.now() - started);
      entry.steps.push(record);
      log({ wedgeSplit: anchor, ...record });
      return record;
    };

    const located = await step("locate", async () => {
      const search = await documentHandle.search(anchor, {
        timeoutMs: WEDGE_SPLIT_TIMEOUT_MS });
      const rectangle = firstRectangle(search);
      if (!rectangle)
        throw new Error(`anchor rectangle unavailable: ${anchor}`);
      return rectangle;
    });
    const rectangle = located.value;
    if (!rectangle) {
      results.push(entry);
      continue;
    }
    const midY = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
    // Past the end of the line on purpose: the point is to cover whatever
    // follows the anchor text, which on PC-IMAGE is the image.
    const endX = rectangle.x + 8000;

    await step("drag-select", () => activeEngine._request("editorDiscoverySelect", {
      documentHandle: documentHandle.handle,
      method: "mouse-drag",
      startXTwips: rectangle.x,
      startYTwips: midY,
      endXTwips: endX,
      endYTwips: midY,
    }, { timeoutMs: WEDGE_SPLIT_TIMEOUT_MS }));

    // What actually got selected.  Without this the two rows cannot be
    // compared: a drag that selected a different span would make any
    // difference downstream a difference in the input, not in the call.
    await step("selection-rectangles", async () => {
      const state = await client.getState({ timeoutMs: WEDGE_SPLIT_TIMEOUT_MS });
      return state?.state?.selection || state?.selection || null;
    });

    // Probe G: getSelectionTypeAndText("text/plain;charset=utf-8"), which is
    // the transferable path the html readback also goes through.
    await step("get-selection-text", () => documentHandle.getSelection({
      timeoutMs: WEDGE_SPLIT_TIMEOUT_MS }));

    // Probe R: the barrier's restore call, alone.
    await step("selection-reset", () => activeEngine._request("editorDiscoverySelect", {
      documentHandle: documentHandle.handle,
      method: "selection-reset-unstable",
      startXTwips: rectangle.x + rectangle.width,
      startYTwips: midY,
      endXTwips: rectangle.x + rectangle.width,
      endYTwips: midY,
    }, { timeoutMs: WEDGE_SPLIT_TIMEOUT_MS }));

    entry.liveness = await livenessLadder(client);
    results.push(entry);
  }
  return results;
}

// Finding 037.  "The handle stopped answering" does not say what stopped, and
// the answer decides what a fix could even look like.  Three rungs, ordered by
// how much of the stack each one needs:
//
//   workerJs   an operation the Worker rejects in its own JS, before it calls
//              into wasm at all.  Alive means the Worker thread still runs.
//   engine     a real operation, which only completes if the engine thread
//              pops it off the queue.
//   wasmMain   the cancel the SDK posts automatically when a request times
//              out.  The Worker answers it by calling oxsdk_request_cancel
//              from its own thread, so a reply means the module is still
//              callable and the engine's global mutex is not held.
//
// Run after every case, the passing ones included: rungs that have only ever
// been run against a broken state cannot show that they can fail.
async function livenessLadder(client) {
  const ladder = { atMs: Math.round(performance.now()) };

  const workerJsStarted = performance.now();
  try {
    await activeEngine._request(
      "oxsdkLivenessProbeNoSuchOperation", {}, { timeoutMs: 5000 });
    // A worker that accepts this is not the worker this probe was written
    // against, and reporting it as liveness would be reporting a guess.
    ladder.workerJs = "unexpected-success";
  } catch (error) {
    ladder.workerJs = error?.code === "UNKNOWN_OPERATION" ? "alive" : "other";
    ladder.workerJsError = errorValue(error);
  }
  ladder.workerJsMs = Math.round(performance.now() - workerJsStarted);

  const cancelsBefore = metrics.cancelResults.length;
  const engineStarted = performance.now();
  try {
    await client.getState({ timeoutMs: 5000 });
    ladder.engine = "alive";
  } catch (error) {
    ladder.engine = error?.code === "TIMEOUT" ? "timed-out" : "other";
    ladder.engineError = errorValue(error);
  }
  ladder.engineMs = Math.round(performance.now() - engineStarted);

  // Only meaningful when the rung above timed out, because that timeout is
  // what makes the SDK post the cancel this rung is waiting for.
  if (ladder.engine === "timed-out") {
    const waitStarted = performance.now();
    while (metrics.cancelResults.length === cancelsBefore
        && performance.now() - waitStarted < 5000)
      await new Promise((resolve) => setTimeout(resolve, 50));
    ladder.wasmMain = metrics.cancelResults.length > cancelsBefore
      ? "alive" : "no-reply";
    ladder.wasmMainMs = Math.round(performance.now() - waitStarted);
    ladder.cancelResult = metrics.cancelResults[cancelsBefore] || null;
  } else {
    ladder.wasmMain = "not-probed";
  }
  log({ liveness: ladder });
  return ladder;
}

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
      workerUrl: `./profiles/${activeProfile}/sdk-worker.js`,
      timeoutMs: 30000,
      closeRecoveryTimeoutMs: 10000,
      debug: engineDebug,
    });
    activeEngine = engine;
    metrics.manifest = engine.manifest;
    engine.onEvent((event) => {
      if (event.event === "diagnostic" && event.level === "lok-trace") {
        recordEngineTrace(event.detail);
        return;
      }
      if (event.event === "cancel-result") {
        metrics.cancelResults.push({
          requestId: event.requestId,
          status: event.status,
          atMs: Math.round(performance.now()),
        });
        return;
      }
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
    if (mode === "wedge-split") {
      checkpoint("wedge-split");
      metrics.wedgeSplit = await runWedgeSplit(client, documentHandle);
    } else if (mode === "discriminator" || mode === "wedge-trace") {
      checkpoint("discriminator");
      metrics.discriminator = await runDiscriminator(client, documentHandle);
      // One save at the end.  The false-failure case is judged on the gap
      // between what the barrier reported and what the document became, so the
      // file is not optional evidence here -- it is half the case.
      try {
        // Shorter under wedge-trace: the point of that mode is the callback
        // stream, and it deliberately runs a case that stops answering, so a
        // three-minute save timeout would only add three minutes of silence to
        // the record.  The attempt itself is kept -- whether a wedged handle
        // still saves is part of what the mode measures.
        const buffer = await documentHandle.save(
          { format: "odt" }, { timeoutMs: mode === "wedge-trace" ? 30000 : 180000 });
        outputs.set("discriminator-final", buffer);
        metrics.outputs.push({ label: "discriminator-final", bytes: buffer.byteLength });
      } catch (error) {
        metrics.discriminatorSaveError = errorValue(error);
      }
    } else if (mode === "deadline") {
      checkpoint("deadline");
      metrics.deadline = await runDeadline(client, documentHandle);
      try {
        const buffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
        outputs.set("deadline-final", buffer);
        metrics.outputs.push({ label: "deadline-final", bytes: buffer.byteLength });
      } catch (error) {
        metrics.deadlineSaveError = errorValue(error);
      }
    } else if (mode === "a5") {
      checkpoint("negative");
      metrics.a5 = await runA5(
        client, documentHandle, A5_ANCHORS[fixtureId] || a3Anchor);
      // One save at the end: the negative cases are judged on what the
      // document did *not* become, so the file is the evidence for all of them
      // together rather than per case.
      try {
        const buffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
        outputs.set("a5-final", buffer);
        metrics.outputs.push({ label: "a5-final", bytes: buffer.byteLength });
      } catch (error) {
        metrics.a5SaveError = errorValue(error);
      }
    } else {
      checkpoint("dispatch");
      await runDispatch(documentHandle, client);
    }

    checkpoint("close");
    // Timed, because finding 012 was a close that never returned on a styled
    // document and "it closed" is not the same claim as "it closed promptly".
    {
      const started = performance.now();
      await documentHandle.close({ timeoutMs: 30000 });
      metrics.closeMs = Math.round(performance.now() - started);
      log({ checkpoint: "close", closeMs: metrics.closeMs });
    }
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
