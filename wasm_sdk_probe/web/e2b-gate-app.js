// SPEC E2-B section 3: does a format action dispatched on a RANGE selection
// behave?
//
// E2-A narrowing 7 says every dispatch it measured started from a collapsed
// caret.  The gesture a v2 user performs -- drag across a paragraph, then press
// the button -- has never entered the matrix.  Task #49 left 24 incidental
// records of it (dispatchSelectionCollapsed:false, all clean), which is a cost
// model, not evidence: nobody asked the question in advance.
//
// The prediction and all dispositions were committed before this file existed:
// findings/evidence/sdk-e2/discovery/e2b-gate/PREDICTION.md
//
// Two things about the design are load-bearing.
//
// First, every positive arm has to prove the range EXISTED before the dispatch.
// All five actions are paragraph-level, so a range that silently collapsed to a
// caret would still leave the target paragraph in the target state and the
// check would pass while measuring nothing.  Hence the pre-dispatch quartet:
// selection text, dispatchSelectionCollapsed == false, rectangle count,
// direction.  A run that fails those is VOID, not failed.
//
// Second, the verdict comes from the saved ODT, and specifically from the
// paragraphs the arm did NOT select.  "This paragraph became a heading" does
// not establish "only this paragraph became a heading".
//
// Coordinates are not hardcoded.  A setup pass sweeps y, selects the full line
// width, and records what each y reads back as -- so the arms address anchors
// by text, and the map itself is evidence.
//
// G1 needs a paragraph that wraps across visual lines.  The first run of this
// gate aimed it at `第三段跨行 gamma` in multi-paragraph.odt and recorded the arm
// VOID: that paragraph is TALL, not wrapped, and a selection across its full
// vertical extent still reports one rectangle.  No fixture in the frozen E1
// corpus has a paragraph long enough to wrap at the page width, so G1 now uses
// wrapped-paragraph.odt from dist/e2b-fixtures/ (tools/create_e2b_fixtures.py).
// It arrives with a control arm, G1c: the same span mechanism aimed at a
// paragraph that does NOT wrap.  Without it, "G1 saw more than one rectangle"
// cannot be told apart from "this build reports more than one rectangle for
// everything".

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { FormatDiscoveryClient } from "./e2/format-discovery-client.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-combination";
const stepTimeoutMs = Number.parseInt(params.get("stepTimeoutMs") || "15000", 10);
const rounds = Number.parseInt(params.get("rounds") || "3", 10);

const metrics = {
  schemaVersion: 1,
  release: "spec-e2b-section-3-gate",
  prediction: "findings/evidence/sdk-e2/discovery/e2b-gate/PREDICTION.md",
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  profile,
  rounds,
  setup: {},
  arms: [],
  complete: false,
  error: null,
};
globalThis.__e2b_gate = metrics;
globalThis.__probe_metrics = metrics;   // run_browser_probe.py waits on this name
const saves = [];
globalThis.__e2b_gate_saves = saves;
globalThis.__e2b_gate_save_count = () => saves.length;
globalThis.__e2b_gate_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => {
  logNode.textContent += `${JSON.stringify(value)}\n`;
};

function publicError(error) {
  return {
    code: error?.code || error?.name || "ERROR",
    message: error?.message || String(error),
  };
}

const rangeSelect = (handle, x1, y1, x2, y2) =>
  handle._engine._request("editorSelectRangeV1", {
    documentHandle: handle.handle,
    startXTwips: x1, startYTwips: y1, endXTwips: x2, endYTwips: y2,
  }, { timeoutMs: stepTimeoutMs });

async function readSelection(handle) {
  try {
    const selection = await handle.getSelection({ timeoutMs: stepTimeoutMs });
    return {
      selectionType: selection.selectionType ?? null,
      text: selection.text ?? "",
      length: (selection.text || "").length,
    };
  } catch (error) {
    return { readFailed: publicError(error) };
  }
}

function rectanglesOf(state) {
  return (state?.selection?.rectangles || []).length;
}

// The count alone does not say the rectangles are stacked visual lines inside
// one paragraph -- it is also what a cross-paragraph selection would produce.
// Keeping the geometry lets the verdict show they are.
function rectangleGeometry(state) {
  // {x, y, width, height} per rectangle -- probe_engine.cpp:938.
  return (state?.selection?.rectangles || []).map((rect) => rect ?? null);
}

// The E1 corpus is frozen (dist/e1-fixtures/manifest.json: frozenDate
// 2026-08-04, mutationPolicy copy-only), so the wrapped-paragraph fixture lives
// in its own directory rather than being added to it.  Fixture identifiers stay
// bare filenames because they are used to build arm and file names.
const FIXTURE_DIR = {
  "list-contexts.odt": "e1-fixtures",
  "multi-paragraph.odt": "e1-fixtures",
  "wrapped-paragraph.odt": "e2b-fixtures",
};

async function openDocument(engine, fixture) {
  const dir = FIXTURE_DIR[fixture];
  if (!dir)
    throw new Error(`no directory registered for fixture ${fixture}`);
  const bytes = await fetch(`./${dir}/${fixture}`, { cache: "no-cache" })
    .then((response) => response.arrayBuffer());
  return engine.open(bytes.slice(0), { name: fixture, timeoutMs: 180000 });
}

async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}

// The setup pass.  It uses the same range-select call the arms use, on a
// throwaway document, before any format action -- so it cannot contaminate what
// the arms measure, and if it cannot find an anchor the arms that need it are
// skipped rather than run against a guess.
async function surveyFixture(engine, fixture) {
  const handle = await openDocument(engine, fixture);
  const rows = [];
  try {
    for (let y = 1300; y <= 4400; y += 130) {
      try {
        await rangeSelect(handle, 1450, y, 9000, y);
        const selection = await readSelection(handle);
        const state = await handle._engine._request("editorGetStateV1", {
          documentHandle: handle.handle,
        }, { timeoutMs: stepTimeoutMs }).catch(() => null);
        rows.push({ y, text: selection.text || "", rectangles: rectanglesOf(state) });
      } catch (error) {
        rows.push({ y, failed: publicError(error) });
      }
    }
  } finally {
    await handle.close({ timeoutMs: 15000 }).catch(() => {});
  }
  return rows;
}

function findAnchor(rows, anchor) {
  const hit = rows.find((row) => (row.text || "").includes(anchor));
  return hit ? { y: hit.y, text: hit.text, rectangles: hit.rectangles } : null;
}

// The vertical extent of one anchor, for the wrapped-line arm.
//
// The survey cannot tell a tall paragraph from a wrapped one: it selects a
// single y across the width, which lands inside one visual line either way and
// always reports one rectangle.  So the survey only supplies candidate top and
// bottom coordinates, and G1 establishes the geometry itself by selecting
// between them and requiring more than one rectangle.  If it gets one, that run
// is VOID -- the fixture did not provide the case -- not passed and not failed.
function findSpan(rows, anchor) {
  const hits = rows.filter((row) => (row.text || "").includes(anchor));
  if (hits.length < 2)
    return null;
  return {
    yTop: hits[0].y,
    yBottom: hits[hits.length - 1].y,
    steps: hits.length,
    text: hits[0].text,
  };
}

/** Fresh engine per arm: a wedged pending slot must not decide the next arm. */
async function runArm(name, spec, body) {
  const entry = { arm: name, expects: spec.expects, fixture: spec.fixture, rounds: [] };
  let engine = null;
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    metrics.productAbiAvailable =
      Boolean(engine.manifest?.capabilities?.includes("narrow-editor-v1"));
    if (!metrics.productAbiAvailable) {
      entry.skipped = "narrow-editor-v1 is not exported by this profile";
      return entry;
    }
    for (let round = 1; round <= rounds; round++) {
      const handle = await openDocument(engine, spec.fixture);
      const record = { round };
      try {
        await body(handle, new FormatDiscoveryClient(handle), record);
        const bytes = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
        record.savedBytes = bytes.byteLength;
        saves.push({
          arm: name, round, fixture: spec.fixture,
          b64: await toBase64(bytes),
        });
        record.saveIndex = saves.length - 1;
      } catch (error) {
        record.fatal = publicError(error);
      } finally {
        await handle.close({ timeoutMs: 15000 }).catch(() => {});
      }
      entry.rounds.push(record);
    }
  } catch (error) {
    entry.fatal = publicError(error);
  } finally {
    engine?.dispose();
  }
  log(entry);
  metrics.arms.push(entry);
  return entry;
}

// One arm body for every positive arm: select a range, prove it is a range,
// dispatch, record.  The proof is what makes the arm a check rather than a
// re-run of A3.
function positiveArm(spec, anchors) {
  return async (handle, client, record) => {
    const anchor = anchors[spec.anchorKey];
    if (!anchor) {
      record.void = `anchor not found: ${spec.anchor}`;
      return;
    }
    const [x1, x2] = spec.reverse ? [spec.xEnd, spec.xStart] : [spec.xStart, spec.xEnd];
    const [y1, y2] = spec.spanY
      ? [anchor.yTop, anchor.yBottom]
      : [anchor.y, anchor.y];
    record.range = { x1, y1, x2, y2, reverse: Boolean(spec.reverse) };
    record.selectStatus = "pending";
    try {
      await rangeSelect(handle, x1, y1, x2, y2);
      record.selectStatus = "completed";
    } catch (error) {
      record.selectStatus = "failed";
      record.selectError = publicError(error);
      return;
    }
    record.selectionBeforeDispatch = await readSelection(handle);
    const before = await handle._engine._request("editorGetStateV1", {
      documentHandle: handle.handle,
    }, { timeoutMs: stepTimeoutMs }).catch(() => null);
    record.rectanglesBeforeDispatch = rectanglesOf(before);
    record.rectangleGeometryBeforeDispatch = rectangleGeometry(before);
    record.collapsedBeforeDispatch = before?.selection?.collapsed ?? null;

    try {
      record.action = await client.action(spec.action, { timeoutMs: stepTimeoutMs });
      record.actionStatus = "completed";
    } catch (error) {
      record.actionStatus = "failed";
      record.actionError = publicError(error);
      // The barrier's own fields ride on the error payload; the diagnostic
      // profile's worker forwards them (the product one does not -- SPEC E2-B
      // section 5 item 5).
      record.formatBarrier = error?.details?.formatBarrier
        ?? error?.formatBarrier ?? null;
    }
    record.selectionAfterDispatch = await readSelection(handle);
    const after = await handle._engine._request("editorGetStateV1", {
      documentHandle: handle.handle,
    }, { timeoutMs: stepTimeoutMs }).catch(() => null);
    record.collapsedAfterDispatch = after?.selection?.collapsed ?? null;
  };
}

const LIST_FIXTURE = "list-contexts.odt";
const MULTI_FIXTURE = "multi-paragraph.odt";
const WRAP_FIXTURE = "wrapped-paragraph.odt";

// Fixture construction is not measurement.  Whether wrapped-paragraph.odt
// actually wraps at this build's page width is a property of the FIXTURE, and
// finding out costs a span select -- which is also the first half of arm G1.
// Running the gate to answer it would mean the same run both tuned the fixture
// and produced the verdict.  So `?geometryOnly=1` selects the spans, records
// the rectangles, dispatches nothing and saves nothing.
const geometryOnly = params.get("geometryOnly") === "1";
metrics.geometryOnly = geometryOnly;

void (async () => {
  let engine = null;
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    metrics.artifact = {
      profile,
      capabilities: engine.manifest?.capabilities ?? null,
      editorContract: engine.manifest?.editorContract ?? null,
      diagnostic: engine.manifest?.diagnostic ?? null,
    };
    if (!geometryOnly) {
      metrics.setup[LIST_FIXTURE] = await surveyFixture(engine, LIST_FIXTURE);
      metrics.setup[MULTI_FIXTURE] = await surveyFixture(engine, MULTI_FIXTURE);
    }
    metrics.setup[WRAP_FIXTURE] = await surveyFixture(engine, WRAP_FIXTURE);
  } finally {
    engine?.dispose();
  }

  const listRows = metrics.setup[LIST_FIXTURE] || [];
  const multiRows = metrics.setup[MULTI_FIXTURE] || [];
  const wrapRows = metrics.setup[WRAP_FIXTURE] || [];
  const anchors = {
    isolated: findAnchor(listRows, "E1-LC-ISOLATED"),
    bulletOne: findAnchor(listRows, "E1-LC-BULLET-ONE"),
    heading: findAnchor(listRows, "E1-LC-HEADING"),
    // G1WRAP is on every visual line of the wrapped paragraph, so the sweep
    // recognises it line by line and findSpan gets a real top and bottom.
    wrapped: findSpan(wrapRows, "G1WRAP"),
    // The control: a paragraph in the same document that does not wrap.
    wrapControl: findAnchor(wrapRows, "E2B-WRAP-HEAD"),
    multiStart: findAnchor(multiRows, "E1-MULTI-START"),
  };
  metrics.anchors = anchors;
  log({ anchors });

  const SPAN = { xStart: 1450, xEnd: 9000 };

  if (geometryOnly) {
    metrics.geometry = [];
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    try {
      for (const probe of [
        { name: "wrapped", span: anchors.wrapped, expect: "more than one rectangle" },
        { name: "control", span: anchors.wrapControl, expect: "exactly one rectangle" },
      ]) {
        const entry = { probe: probe.name, expect: probe.expect };
        if (!probe.span) {
          entry.void = "anchor not found in the sweep";
          metrics.geometry.push(entry);
          continue;
        }
        const handle = await openDocument(engine, WRAP_FIXTURE);
        try {
          const yTop = probe.span.yTop ?? probe.span.y;
          const yBottom = probe.span.yBottom ?? probe.span.y;
          entry.range = { x1: SPAN.xStart, y1: yTop, x2: SPAN.xEnd, y2: yBottom };
          await rangeSelect(handle, SPAN.xStart, yTop, SPAN.xEnd, yBottom);
          entry.selection = await readSelection(handle);
          const state = await handle._engine._request("editorGetStateV1", {
            documentHandle: handle.handle,
          }, { timeoutMs: stepTimeoutMs }).catch(() => null);
          entry.rectangles = rectanglesOf(state);
          entry.rectangleGeometry = rectangleGeometry(state);
          entry.collapsed = state?.selection?.collapsed ?? null;
        } catch (error) {
          entry.failed = publicError(error);
        } finally {
          await handle.close({ timeoutMs: 15000 }).catch(() => {});
        }
        log(entry);
        metrics.geometry.push(entry);
      }
    } finally {
      engine?.dispose();
    }
    metrics.complete = true;
    log({ complete: true, geometryOnly: true });
    return;
  }

  // The comparison baseline, and it has to exist.
  //
  // The authored fixture is NOT the baseline: the engine's ODT export
  // normalises what the fixture leaves implicit (a paragraph with no
  // text:style-name comes back as "Standard"), so comparing a saved document
  // against the authored file reports every paragraph as changed and the
  // analyzer cannot see what the action actually did.  Same class of mistake as
  // task #50's first comparison, in the opposite direction.
  for (const fixture of [LIST_FIXTURE, MULTI_FIXTURE, WRAP_FIXTURE]) {
    await runArm(`BASELINE-${fixture}`, {
      expects: "open and save, no action: this is what the analyzer compares against",
      fixture,
    }, async () => {});
  }

  // Action dimension: geometry fixed at one paragraph, forward.
  await runArm("A1-bullet-from-range", {
    expects: "bridge arm: the 24 incidental records, this time pre-registered",
    fixture: LIST_FIXTURE,
  }, positiveArm({ ...SPAN, anchorKey: "isolated", anchor: "E1-LC-ISOLATED",
    action: "set-list-unordered" }, anchors));

  await runArm("A2-ordered-from-range", {
    expects: "DefaultNumbering from a range", fixture: LIST_FIXTURE,
  }, positiveArm({ ...SPAN, anchorKey: "isolated", anchor: "E1-LC-ISOLATED",
    action: "set-list-ordered" }, anchors));

  await runArm("A3-list-none-from-range", {
    expects: "RemoveBullets from a range, leaving an existing list",
    fixture: LIST_FIXTURE,
  }, positiveArm({ ...SPAN, anchorKey: "bulletOne", anchor: "E1-LC-BULLET-ONE",
    action: "set-list-none" }, anchors));

  await runArm("A4-heading-from-range", {
    expects: "StyleApply heading from a range", fixture: LIST_FIXTURE,
  }, positiveArm({ ...SPAN, anchorKey: "isolated", anchor: "E1-LC-ISOLATED",
    action: "set-paragraph-heading" }, anchors));

  await runArm("A5-body-from-range", {
    expects: "StyleApply body from a range, on a paragraph that IS a heading",
    fixture: LIST_FIXTURE,
  }, positiveArm({ ...SPAN, anchorKey: "heading", anchor: "E1-LC-HEADING",
    action: "set-paragraph-body" }, anchors));

  // Geometry dimension: action fixed at set-list-unordered.
  await runArm("G1-wrapped-line-range", {
    expects: "one paragraph, more than one selection rectangle",
    fixture: WRAP_FIXTURE,
  }, positiveArm({ ...SPAN, anchorKey: "wrapped", spanY: true,
    anchor: "G1WRAP", action: "set-list-unordered" }, anchors));

  // The control for G1, in the same document and the same run: a paragraph that
  // does not wrap, selected the same way, must report exactly one rectangle.
  // It cannot show that the count tracks visual lines -- only that it is not
  // stuck above one for this fixture and this build, which is the reading that
  // would make G1's result mean nothing.
  await runArm("G1c-single-line-control", {
    expects: "a non-wrapping paragraph in the same fixture: exactly one rectangle",
    fixture: WRAP_FIXTURE,
  }, positiveArm({ ...SPAN, anchorKey: "wrapControl", anchor: "E2B-WRAP-HEAD",
    action: "set-list-unordered" }, anchors));

  await runArm("G2-reverse-range", {
    expects: "END left of START", fixture: LIST_FIXTURE,
  }, positiveArm({ ...SPAN, anchorKey: "isolated", anchor: "E1-LC-ISOLATED",
    reverse: true, action: "set-list-unordered" }, anchors));

  // G3 is judged differently: see PREDICTION.md.  It spans two paragraphs, and
  // the question is not whether it refuses but whether it reports success while
  // verifying only one of them.
  await runArm("G3-cross-paragraph-range", {
    expects: "spans two paragraphs; predicted to report success while verifying one",
    fixture: MULTI_FIXTURE,
  }, async (handle, client, record) => {
    const anchor = anchors.multiStart;
    if (!anchor) {
      record.void = "anchor not found: E1-MULTI-START";
      return;
    }
    const secondY = anchor.y + 390;   // one paragraph down; verified by readback
    record.range = { x1: 1450, y1: anchor.y, x2: 9000, y2: secondY };
    try {
      await handle._engine._request("editorSelectRangeV1", {
        documentHandle: handle.handle,
        startXTwips: 1450, startYTwips: anchor.y,
        endXTwips: 9000, endYTwips: secondY,
      }, { timeoutMs: stepTimeoutMs });
      record.selectStatus = "completed";
    } catch (error) {
      record.selectStatus = "failed";
      record.selectError = publicError(error);
      return;
    }
    record.selectionBeforeDispatch = await readSelection(handle);
    const before = await handle._engine._request("editorGetStateV1", {
      documentHandle: handle.handle,
    }, { timeoutMs: stepTimeoutMs }).catch(() => null);
    record.rectanglesBeforeDispatch = rectanglesOf(before);
    record.collapsedBeforeDispatch = before?.selection?.collapsed ?? null;
    try {
      record.action = await client.action("set-list-unordered", { timeoutMs: stepTimeoutMs });
      record.actionStatus = "completed";
    } catch (error) {
      record.actionStatus = "failed";
      record.actionError = publicError(error);
      record.formatBarrier = error?.details?.formatBarrier ?? error?.formatBarrier ?? null;
    }
    record.selectionAfterDispatch = await readSelection(handle);
  });

  metrics.complete = true;
  log({ complete: true, arms: metrics.arms.length, saves: saves.length });
})().catch((error) => {
  metrics.error = publicError(error);
  metrics.complete = true;
  log({ fatal: metrics.error });
});
