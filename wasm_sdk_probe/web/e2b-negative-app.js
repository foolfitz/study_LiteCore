// SPEC E2-B 5.10: the negative matrix.
//
// Two rules from the spec are structural here rather than aspirational.
//
// One: every row is one mutation away from a baseline that passes.  The
// manifest rows get that from make_negative_profiles.py (one named change per
// variant, artifacts hard-linked so they cannot drift); the payload rows get it
// by sending the SAME request as the positive case with exactly one field
// altered.
//
// Two: zero mutation is judged on saved bytes.  Every row saves the document
// before and after its attempt, and the judge compares <office:body>.  A row
// that only checked the returned error would pass just as happily if the
// engine had refused loudly and mutated anyway.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { ParagraphEditorClient } from "./editor-shell-v2/paragraph-editor-client.js";

const params = new URLSearchParams(location.search);
const baseline = params.get("profile") || "e2-editor-v2";
const rounds = Number.parseInt(params.get("rounds") || "1", 10);

const metrics = {
  schemaVersion: 1,
  release: "spec-e2b-negative-matrix",
  baselineProfile: baseline,
  browser: navigator.userAgent,
  rounds,
  rows: [],
  complete: false,
  error: null,
};
globalThis.__e2b_negative = metrics;
globalThis.__probe_metrics = metrics;
const saves = [];
globalThis.__e2b_negative_save_count = () => saves.length;
globalThis.__e2b_negative_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: error?.message || String(error),
  formatBarrier: error?.details?.formatBarrier ?? null,
});

async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}

// The rows.  `profile` names a variant built by make_negative_profiles.py;
// `attempt` is what the row does once the document is open.
const FIXTURE = "list-contexts.odt";
const MULTI = "multi-paragraph.odt";

const ROWS = [
  {
    id: "N1", name: "action-withheld-by-manifest",
    profile: `${baseline}-n1-action-withheld`, fixture: FIXTURE,
    expect: ["UNSUPPORTED_OPERATION"],
    why: "proves the manifest CONSTRAINS rather than describes",
    attempt: (handle) => new ParagraphEditorClient(handle).action("set-list-ordered"),
  },
  {
    id: "N2", name: "capability-withheld",
    profile: `${baseline}-n2-capability-withheld`, fixture: FIXTURE,
    expect: ["UNSUPPORTED_OPERATION"],
    why: "the first of the worker's two gates",
    attempt: (handle) => new ParagraphEditorClient(handle).action("set-list-unordered"),
  },
  {
    id: "N3", name: "contract-version-1",
    profile: `${baseline}-n3-contract-version-1`, fixture: FIXTURE,
    expect: ["UNSUPPORTED_OPERATION"],
    why: "an allowlist's version is an identity, not a range",
    attempt: (handle) => new ParagraphEditorClient(handle).action("set-list-unordered"),
  },
  {
    id: "N5", name: "v2-action-id-into-v1-profile",
    // The V1 profile, deliberately.  Aimed at the v2 profile this row observed
    // UNSUPPORTED_OPERATION instead -- and rightly, because a v2 profile does
    // not declare narrow-editor-v1, so the capability gate refused it before
    // the action map was ever consulted.  That is a true refusal but it is N3's
    // refusal, not this one.  What this row exists to prove is that a V1 build
    // does not accept a v2 action id, and only the v1 profile can show that.
    profile: "e1-editor-v1", fixture: FIXTURE,
    // Declared, so the runner's attribution check can tell a deliberate
    // cross-profile row from a row that drove the wrong artifact by accident.
    // Without the flag the check fires on this row and everyone learns to
    // ignore it, which is how a real misattribution gets through later.
    crossProfile: true,
    expect: ["INVALID_ARGUMENT"],
    why: "a v1 profile must not accept a v2 action id",
    attempt: (handle) => handle._engine._request("editorActionV1", {
      documentHandle: handle.handle, expectedRevision: handle.revision,
      action: "set-list-unordered", extendSelection: false, enabled: false,
    }, { timeoutMs: 30000 }),
  },
  {
    id: "N6", name: "unknown-action-name",
    profile: baseline, fixture: FIXTURE,
    expect: ["EDITOR_ACTION_UNSUPPORTED", "INVALID_ARGUMENT"],
    why: "the action set is closed",
    attempt: (handle) => new ParagraphEditorClient(handle).action("set-list-roman"),
  },
  {
    id: "N7", name: "option-flag-on-a-paragraph-action",
    profile: baseline, fixture: FIXTURE,
    expect: ["INVALID_ARGUMENT"],
    why: "neither flag has a meaning for the five paragraph actions",
    attempt: (handle) => handle._engine._request("editorActionV2", {
      documentHandle: handle.handle, expectedRevision: handle.revision,
      action: "set-list-unordered", extendSelection: true, enabled: false,
    }, { timeoutMs: 30000 }),
  },
  {
    id: "N8", name: "stale-revision",
    profile: baseline, fixture: FIXTURE,
    expect: ["STALE_REVISION", "EDITOR_STALE_REVISION", "INVALID_ARGUMENT"],
    why: "the optimistic-concurrency guard",
    attempt: (handle) => new ParagraphEditorClient(handle)
      .action("set-list-unordered", { expectedRevision: handle.revision + 7 }),
  },
  {
    id: "N9a", name: "forbidden-field-unoCommand",
    profile: baseline, fixture: FIXTURE, expect: ["INVALID_ARGUMENT"],
    why: "one field at a time: sending three would only prove one is checked",
    attempt: (handle) => handle._engine._request("editorActionV2", {
      documentHandle: handle.handle, expectedRevision: handle.revision,
      action: "set-list-unordered", extendSelection: false, enabled: false,
      unoCommand: ".uno:Bold",
    }, { timeoutMs: 30000 }),
  },
  {
    id: "N9b", name: "forbidden-field-keyCode",
    profile: baseline, fixture: FIXTURE, expect: ["INVALID_ARGUMENT"],
    why: "one field at a time",
    attempt: (handle) => handle._engine._request("editorActionV2", {
      documentHandle: handle.handle, expectedRevision: handle.revision,
      action: "set-list-unordered", extendSelection: false, enabled: false,
      keyCode: 1024,
    }, { timeoutMs: 30000 }),
  },
  {
    id: "N9c", name: "forbidden-field-command",
    profile: baseline, fixture: FIXTURE, expect: ["INVALID_ARGUMENT"],
    why: "one field at a time",
    attempt: (handle) => handle._engine._request("editorActionV2", {
      documentHandle: handle.handle, expectedRevision: handle.revision,
      action: "set-list-unordered", extendSelection: false, enabled: false,
      command: "anything",
    }, { timeoutMs: 30000 }),
  },
  {
    id: "N11", name: "gesture-withheld-by-manifest",
    profile: `${baseline}-n11-gesture-withheld`, fixture: MULTI,
    expect: ["EDITOR_FORMAT_GESTURE_UNSUPPORTED"],
    why: "the ONLY row that tests a gesture limit; without it a partial GO on a "
       + "gesture is unprovable",
    crossRange: true,
    attempt: (handle) => new ParagraphEditorClient(handle).action("set-list-unordered"),
  },
];

// N4 is deliberately different: it must fail at INIT, before any document
// exists, so it cannot be expressed as an attempt on an open handle.
async function runAbiMismatch(round) {
  const row = { id: "N4", name: "abi-version-mismatch", round,
                profile: `${baseline}-n4-abi-version-mismatch`,
                expect: ["INCOMPATIBLE_ABI"],
                why: "a manifest is a claim; the binary is the fact" };
  let engine = null;
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${row.profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    row.observed = null;
    row.refused = false;
  } catch (error) {
    row.observed = publicError(error);
    row.refused = true;
  } finally {
    engine?.dispose();
  }
  // No document is ever opened, so there is nothing to save and nothing that
  // could have been mutated.  Recorded rather than left implicit.
  row.zeroMutationBy = "no document was opened";
  log(row);
  metrics.rows.push(row);
}

async function selectCrossRange(handle) {
  const client = new ParagraphEditorClient(handle);
  let anchorY = null;
  for (let y = 1300; y <= 4400 && anchorY === null; y += 130) {
    await client.selectRange({ xTwips: 1450, yTwips: y },
                             { xTwips: 9000, yTwips: y }, { timeoutMs: 15000 });
    const selection = await handle.getSelection({ timeoutMs: 15000 });
    if ((selection.text || "").includes("E1-MULTI-START"))
      anchorY = y;
  }
  if (anchorY === null)
    return false;
  await client.selectRange({ xTwips: 1450, yTwips: anchorY },
                           { xTwips: 9000, yTwips: anchorY + 390 },
                           { timeoutMs: 15000 });
  return true;
}

async function runRow(spec, round) {
  const row = { id: spec.id, name: spec.name, round, profile: spec.profile,
                fixture: spec.fixture, expect: spec.expect, why: spec.why,
                crossProfile: Boolean(spec.crossProfile) };
  let engine = null;
  let handle = null;
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${spec.profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    const bytes = await fetch(`./e1-fixtures/${spec.fixture}`, { cache: "no-cache" })
      .then((response) => response.arrayBuffer());
    handle = await engine.open(bytes.slice(0), {
      name: spec.fixture, timeoutMs: 180000 });

    // The baseline is a save through THIS engine with no action -- never the
    // authored fixture, which the export normalises (the e2b-gate lesson).
    const before = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
    saves.push({ row: spec.id, round, phase: "before",
                 b64: await toBase64(before) });

    if (spec.crossRange && !(await selectCrossRange(handle))) {
      row.void = "anchor not found; the row did not reach its attempt";
      log(row); metrics.rows.push(row); return;
    }

    try {
      row.result = await spec.attempt(handle);
      row.refused = false;
    } catch (error) {
      row.observed = publicError(error);
      row.refused = true;
    }

    const after = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
    saves.push({ row: spec.id, round, phase: "after",
                 b64: await toBase64(after) });
    row.zeroMutationBy = "saved document comparison";
  } catch (error) {
    row.fatal = publicError(error);
  } finally {
    await handle?.close({ timeoutMs: 15000 }).catch(() => {});
    engine?.dispose();
  }
  log(row);
  metrics.rows.push(row);
}

void (async () => {
  try {
    for (let round = 1; round <= rounds; round++) {
      await runAbiMismatch(round);
      for (const spec of ROWS)
        await runRow(spec, round);
    }
  } catch (error) {
    metrics.error = publicError(error);
    log({ fatal: metrics.error });
  } finally {
    metrics.complete = true;
    log({ complete: true, rows: metrics.rows.length, saves: saves.length });
  }
})();
