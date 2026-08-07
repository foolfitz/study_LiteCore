import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorClient } from "./editor-shell/editor-client.js";

// Does finding 021 already reach the shipped editor, and how wide is it?
//
// probe_engine.cpp answers set-bold / set-italic with `documented-state-noop`
// whenever the cached value equals the requested one.  That shortcut sits
// *outside* OXSDK_E2_FORMAT_BARRIER, so it is compiled into e1-editor-v1,
// whose updateEditorFormatState (the `#else` branch) has no formatStateStale
// flag at all.  If the cache can hold a previous position's value, the user
// presses the button, is told "already in that state", and nothing happens.
//
// Every exposure case is paired with a control that differs only in whether
// the cache was primed.  Target text, request and profile are identical, so a
// difference in outcome can only come from the cached value.  The page judges
// nothing: it saves an ODT per case and the runner reads the result out of the
// file.  Nothing here pumps the scheduler or rebuilds the frozen artifact.
const status = document.querySelector("#status");
const logNode = document.querySelector("#log");

const FIXTURE = "styled-list.odt";
const BOLD_ANCHOR = "bold anchor";
const ITALIC_ANCHOR = "italic anchor";
const PLAIN_ANCHOR = "E1-STYLED-END";

// prime: clicked first, to populate the cache.  Click is the shipped shell's
// placement path and the only one that delivers a payload at all -- search
// placement leaves the cache null, which cannot reach the shortcut.
// target: selected by search, so the format applies to real text and the saved
// ODT can be judged.
const CASES = [
  {
    label: "control-bold",
    format: "bold",
    enabled: true,
    target: PLAIN_ANCHOR,
    expect: "target becomes bold",
  },
  {
    label: "exposure-bold",
    format: "bold",
    enabled: true,
    prime: BOLD_ANCHOR,
    target: PLAIN_ANCHOR,
    expect: "cache says bold, target is not -- shortcut must not fire",
  },
  {
    label: "control-italic",
    format: "italic",
    enabled: true,
    target: PLAIN_ANCHOR,
    expect: "target becomes italic",
  },
  {
    label: "exposure-italic",
    format: "italic",
    enabled: true,
    prime: ITALIC_ANCHOR,
    target: PLAIN_ANCHOR,
    expect: "cache says italic, target is not -- shortcut must not fire",
  },
  {
    label: "control-unbold",
    format: "bold",
    enabled: false,
    target: BOLD_ANCHOR,
    expect: "target loses bold",
  },
  {
    label: "exposure-unbold",
    format: "bold",
    enabled: false,
    prime: PLAIN_ANCHOR,
    target: BOLD_ANCHOR,
    expect: "cache says not bold, target is -- shortcut must not fire",
  },
];

const metrics = {
  schemaVersion: 2,
  release: "finding-022-e1-exposure",
  stage: "inline-format-noop",
  profile: "e1-editor-v1",
  fixture: FIXTURE,
  complete: false,
  cases: [],
};

const outputs = new Map();
// run_browser_probe's navigate() treats this as "the page module loaded".
globalThis.__probe_metrics = metrics;
globalThis.__e1_bold_noop = metrics;
globalThis.__e1_bold_noop_get_output_base64 = (label) => {
  const bytes = outputs.get(label);
  if (!bytes)
    return "";
  let binary = "";
  for (let index = 0; index < bytes.length; index += 1)
    binary += String.fromCharCode(bytes[index]);
  return btoa(binary);
};

function log(entry) {
  logNode.textContent += `${JSON.stringify(entry, null, 1)}\n`;
}

function errorValue(error) {
  return {
    code: error?.code ?? "UNKNOWN",
    message: error?.message ?? String(error),
  };
}

// editorGetStateV1 nests the watched values under `format`; `null` is the
// engine's "never reported", a different answer from false that must not be
// flattened into one.
function stateOf(state) {
  if (!state || typeof state !== "object")
    return null;
  return {
    bold: state.format?.bold ?? null,
    italic: state.format?.italic ?? null,
    revision: state.revision ?? null,
  };
}

function firstRectangle(search) {
  const rectangles = search?.rectangles ?? search?.selection?.rectangles ?? [];
  return Array.isArray(rectangles) && rectangles.length ? rectangles[0] : null;
}

async function clickAtAnchor(documentHandle, anchor) {
  const search = await documentHandle.search(anchor, { timeoutMs: 60000 });
  const rectangle = firstRectangle(search);
  if (!rectangle)
    return { anchor, clicked: false, reason: "no rectangle" };
  const x = rectangle.x + Math.max(1, Math.floor(rectangle.width / 2));
  const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  await documentHandle.click(x, y, { timeoutMs: 30000 });
  return { anchor, clicked: true, caret: { x, y } };
}

// Bounded host-side wait, no retry of the action itself: give the broadcast a
// chance to land so the cache is populated before the target is selected.
async function awaitFormatKnown(client, format, deadlineMs = 4000) {
  const deadline = performance.now() + deadlineMs;
  let state = stateOf(await client.getState({ timeoutMs: 30000 }));
  while (state?.[format] === null && performance.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 100));
    state = stateOf(await client.getState({ timeoutMs: 30000 }));
  }
  return state;
}

async function selectAnchor(documentHandle, anchor) {
  const found = await documentHandle.search(anchor, { timeoutMs: 60000 });
  return { anchor, found: found?.found ?? null };
}

// One engine per case.  Reusing a single engine across cases made a later
// case's first search time out; an independent session per case removes that
// confound and matches how a user would arrive at each sequence anyway.
async function runCase(fixtureBuffer, spec) {
  const entry = { ...spec, status: "running" };
  metrics.cases.push(entry);
  let engine = null;
  let documentHandle = null;
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${metrics.profile}/sdk-worker.js`,
      timeoutMs: 30000,
      closeRecoveryTimeoutMs: 10000,
    });
    metrics.manifest = engine.manifest;
    // open() takes an ArrayBuffer and transfer: true detaches it, so each case
    // slices its own copy off the fetched buffer.
    documentHandle = await engine.open(fixtureBuffer.slice(0), {
      name: FIXTURE,
      transfer: true,
      timeoutMs: 180000,
    });
    const client = new NarrowEditorClient(documentHandle);
    entry.stateAtOpen = stateOf(await client.getState({ timeoutMs: 30000 }));

    if (spec.prime) {
      entry.priming = await clickAtAnchor(documentHandle, spec.prime);
      entry.stateAfterPriming = await awaitFormatKnown(client, spec.format);
    }

    entry.targetSelection = await selectAnchor(documentHandle, spec.target);
    entry.stateBeforeAction = stateOf(await client.getState({ timeoutMs: 30000 }));

    try {
      entry.result = await client.setInlineFormat(
        spec.format, spec.enabled, { timeoutMs: 30000 },
      );
    } catch (error) {
      entry.result = { error: errorValue(error) };
    }
    entry.stateAfterAction = stateOf(await client.getState({ timeoutMs: 30000 }));

    const buffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
    outputs.set(spec.label, new Uint8Array(buffer));
    entry.status = "passed";
  } catch (error) {
    entry.error = errorValue(error);
    entry.status = "failed";
  } finally {
    if (documentHandle) {
      try {
        await documentHandle.close({ timeoutMs: 60000 });
      } catch (error) {
        entry.closeError = errorValue(error);
      }
    }
    if (engine) {
      try {
        engine.dispose();
      } catch (error) {
        entry.disposeError = errorValue(error);
      }
    }
  }
  log(entry);
  return entry;
}

async function main() {
  try {
    const params = new URLSearchParams(location.search);
    // Lets the same page verify a fixed build without touching the frozen one.
    metrics.profile = params.get("profile") || "e1-editor-v1";
    status.textContent = "loading fixture";
    const response = await fetch(`./e1-fixtures/${FIXTURE}`);
    if (!response.ok)
      throw new Error(`fixture fetch failed: ${response.status}`);
    const fixtureBuffer = await response.arrayBuffer();

    for (const spec of CASES) {
      status.textContent = spec.label;
      await runCase(fixtureBuffer, spec);
    }
    metrics.complete = true;
    status.textContent = "complete";
  } catch (error) {
    metrics.error = errorValue(error);
    metrics.complete = true;
    status.textContent = "failed";
    log({ fatal: metrics.error });
  }
}

main();
