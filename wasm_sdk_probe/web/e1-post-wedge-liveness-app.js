// Is the ENGINE dead after the finding 038 selection, or only the state read?
//
// Task 035's run turned up a detail the finding does not distinguish.  The
// shipped `NarrowEditorClient.selectRange` is two requests: `editorSelectRangeV1`
// and then a `getState` readback.  In every 038 run, on both artifacts, the
// error that came back was
//
//     TIMEOUT: editorGetStateV1 timed out after N ms
//
// -- never `editorSelectRangeV1`.  The select request RETURNS.  It is the read
// after it that never does.
//
// Finding 038 says the selection itself kills the engine, and cites an 8-second
// idle after the selection with no command issued at all.  That measurement was
// taken on the E2 discovery engine.  Applying it to `835b453d` is precisely the
// cross-artifact inference this project keeps having to retract, so it gets
// measured here instead of assumed.
//
// The two stories differ in what the product can do about it:
//
//   engine dead    every later request times out.  Nothing survives the
//                  selection, so a gate has to stop the selection.
//   read dead      the selection lands and the document keeps working; only the
//                  path through the poisoned content hangs.  Then a much
//                  cheaper mitigation exists -- select, skip the readback -- and
//                  (c') does not have to refuse the gesture at all.
//
// So: raw `editorSelectRangeV1` with NO readback, then exactly one probe, fresh
// engine per probe.  Each probe also runs after a plain selection, because a
// probe that hangs on both arms is a broken probe, not a finding -- the control
// that the first CPU-profile round of 037 did not have.
//
// PREDICTION, from finding 038 as written: the engine is dead, so all five
// probes time out in the note arm and all five answer in the plain arm.

import { createDocumentEngine } from "./sdk/document-sdk.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e1-editor-v1";
const fixture = params.get("fixture") || "frame-contexts.odt";
const probeTimeoutMs = Number.parseInt(params.get("timeoutMs") || "15000", 10);

const status = document.querySelector("#status");
const logNode = document.querySelector("#log");

const metrics = {
  schemaVersion: 1,
  release: "e1-post-wedge-liveness",
  question: "after the 038 selection, is the engine dead or only the state read",
  profile,
  fixture,
  probeTimeoutMs,
  userAgent: navigator.userAgent,
  manifest: null,
  cases: [],
  summary: null,
  complete: false,
  error: null,
};
globalThis.__e1_post_wedge = metrics;
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

// One probe each, so a hang cannot be blamed on the probe before it.  `getState`
// is the known-wedging control at the top; the rest are the question.
const PROBES = {
  "get-state": (handle) => handle._engine._request(
    "editorGetStateV1", { documentHandle: handle.handle }, { timeoutMs: probeTimeoutMs }),
  "get-selection": (handle) => handle.getSelection({ timeoutMs: probeTimeoutMs }),
  search: (handle) => handle.search("FX-PLAIN", { timeoutMs: probeTimeoutMs }),
  render: (handle) => handle.render(
    { xTwips: 0, yTwips: 0, widthTwips: 6000, heightTwips: 3000,
      widthPixels: 300, heightPixels: 150 },
    { timeoutMs: probeTimeoutMs }),
  "insert-text": (handle) => handle.insertText("Z", { timeoutMs: probeTimeoutMs }),
  // Whether the user can still rescue their work is not an academic question,
  // and save is the only answer to it.
  save: (handle) => handle.save({ format: "odt" }, { timeoutMs: probeTimeoutMs }),
};

const ARMS = {
  // The control: same gesture, same document, a paragraph with no frame.
  plain: { anchor: "FX-PLAIN", spanTwips: 8000 },
  // The 038 trigger: a selection that covers the citation of a footnote whose
  // body holds an as-char frame.
  note: { anchor: "FX-NOTE", spanTwips: 8000 },
  // The trigger AND the read that hangs on it.  `note` answers "does the
  // selection kill the engine".  This answers the different and more useful
  // question "does the FAILED READ kill it" -- if the loop is stuck inside that
  // handler from then on, everything after it is dead no matter what the
  // selection did, and a product that swallows the timeout is not recovering,
  // it is just not looking.
  "note-poisoned": { anchor: "FX-NOTE", spanTwips: 8000, preProbe: "get-state" },
};

async function runCase(bytes, armName, probeName) {
  const arm = ARMS[armName];
  const entry = { arm: armName, probe: probeName, status: "running" };
  metrics.cases.push(entry);
  status.textContent = `${armName}/${probeName}`;
  let engine = null;
  let handle = null;
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`,
      timeoutMs: 30000,
      closeRecoveryTimeoutMs: 10000,
    });
    metrics.manifest = engine.manifest;
    handle = await engine.open(bytes.slice(0), {
      name: fixture, transfer: true, timeoutMs: 180000,
    });

    const found = await handle.search(arm.anchor, { timeoutMs: 30000 });
    if (!found?.found)
      throw new Error(`anchor not found: ${arm.anchor}`);
    const rectangle = firstRectangle(found);
    const midY = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));

    // Raw, so nothing reads state back.  `NarrowEditorClient.selectRange` would
    // do the readback itself and the question would be unanswerable.
    const selectStarted = performance.now();
    try {
      await handle._engine._request("editorSelectRangeV1", {
        documentHandle: handle.handle,
        startXTwips: rectangle.x, startYTwips: midY,
        endXTwips: rectangle.x + arm.spanTwips, endYTwips: midY,
      }, { timeoutMs: probeTimeoutMs });
      entry.rawSelect = "resolved";
    } catch (error) {
      entry.rawSelect = "rejected";
      entry.rawSelectError = errorValue(error);
    }
    entry.rawSelectMs = Math.round(performance.now() - selectStarted);

    if (arm.preProbe) {
      const preStarted = performance.now();
      try {
        await PROBES[arm.preProbe](handle);
        entry.preProbe = "resolved";
      } catch (error) {
        entry.preProbe = "rejected";
        entry.preProbeError = errorValue(error);
      }
      entry.preProbeMs = Math.round(performance.now() - preStarted);
    }

    const probeStarted = performance.now();
    try {
      const value = await PROBES[probeName](handle);
      entry.probe_status = "resolved";
      // Enough of the answer to tell a real one from an empty one, without
      // pasting a tile's worth of pixels into the evidence file.
      entry.probeValue = ["render", "save"].includes(probeName)
        ? { bytes: value?.pixels?.byteLength ?? value?.bytes?.byteLength
            ?? value?.byteLength ?? null }
        : JSON.parse(JSON.stringify(value ?? null, (key, item) =>
          typeof item === "string" && item.length > 80 ? `${item.slice(0, 80)}…` : item));
    } catch (error) {
      entry.probe_status = "rejected";
      entry.probeError = errorValue(error);
    }
    entry.probeMs = Math.round(performance.now() - probeStarted);
    entry.status = "measured";
  } catch (error) {
    entry.error = errorValue(error);
    entry.status = "failed";
  } finally {
    try {
      engine?.dispose();
    } catch (error) {
      entry.disposeError = errorValue(error);
    }
  }
  log(entry);
  return entry;
}

function summarise() {
  const cell = (arm, probe) => metrics.cases.find(
    (item) => item.arm === arm && item.probe === probe);
  const summary = { probes: {}, verdict: {} };
  for (const probe of Object.keys(PROBES)) {
    const row = {};
    for (const arm of Object.keys(ARMS)) {
      const item = cell(arm, probe);
      row[arm] = item?.probe_status ?? null;
      row[`${arm}Ms`] = item?.probeMs ?? null;
    }
    // Only a probe that works on the control says anything about the trigger.
    row.controlled = row.plain === "resolved";
    summary.probes[probe] = row;
  }
  for (const arm of Object.keys(ARMS).filter((name) => name !== "plain")) {
    const controlled = Object.entries(summary.probes)
      .filter(([, item]) => item.controlled);
    const survivors = controlled.filter(([, item]) => item[arm] === "resolved");
    summary.verdict[arm] = {
      state: controlled.length === 0 ? "no-usable-control"
        : survivors.length === 0 ? "engine-dead"
          : survivors.length === controlled.length ? "engine-alive"
            : "partially-alive",
      survivingProbes: survivors.map(([name]) => name),
    };
  }
  summary.rawSelectResolvedInTriggerArms = metrics.cases
    .filter((item) => item.arm !== "plain")
    .every((item) => item.rawSelect === "resolved");
  // The pre-probe is the wedge itself; if it ever RESOLVED, that arm did not
  // measure what its name says and its verdict must not be read as one.
  summary.preProbeAlwaysWedged = metrics.cases
    .filter((item) => ARMS[item.arm]?.preProbe)
    .every((item) => item.preProbe === "rejected");
  metrics.summary = summary;
  log({ summary });
}

async function main() {
  try {
    status.textContent = "loading fixture";
    const response = await fetch(`./e1-fixtures/${fixture}`, { cache: "no-cache" });
    if (!response.ok)
      throw new Error(`fixture fetch failed: ${response.status}`);
    const bytes = await response.arrayBuffer();
    // Control arm first: if the probes cannot answer on a healthy engine, the
    // trigger arms are not worth running.
    for (const arm of Object.keys(ARMS)) {
      for (const probe of Object.keys(PROBES))
        await runCase(bytes, arm, probe);
    }
    summarise();
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
