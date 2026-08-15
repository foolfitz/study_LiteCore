// SPEC E2-C, phase D3: the list target cells, L1-L8.
//
// Round one's D3 would have dispatched the list actions at E1-LC-ISOLATED --
// a paragraph with no list on either side -- so "D3 covered the list actions"
// would have meant "the list actions ran next to no lists".  Each cell here is
// bound to an anchor AND a pre-state, and the predictions were registered
// before this file existed.
//
// One fresh document per cell.  Two cells in one document would mean the second
// one's pre-state is whatever the first one left behind, which is the property
// these cells are about.
//
// The page judges nothing; tools/analyze_e2_c_d3.py reads the saved documents.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";
import { caretOf, caretCovers, placeCaretVerified, CARET_TOLERANCE_TWIPS }
  from "./e2-c-caret.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const only = params.get("only");
// A/B switch for one question: does the before-picture save poison the gesture
// that follows it?  Every cell in the first run came back
// `stage-deadline:awaiting-selection`, and a save before the caret is the only
// thing this phase does that D1 and D2 do not.
// `before`: save (default) | skip | delay -- `delay` waits as long as a save
// takes without doing one, which separates "the save leaves state behind" from
// "anything that takes time before the gesture races with it".
// `settle`: milliseconds to wait AFTER the caret is confirmed, before
// dispatching -- separates a state problem from a settling race.
// Default `skip`, and that is a measured decision rather than a convenience:
// finding 047 says a save immediately before a click-placed caret makes the
// next format action time out, and the whole first run of this phase died of
// it.  The before-picture does not need a save at all -- the FIXTURE ON DISK is
// what the document looked like before, byte for byte, and the analyzer already
// has it.  Taking a save here would measure 047 instead of the list actions.
//
// `save` and `delay` are kept because they are finding 047's arms.
const beforeMode = params.get("before") || "skip";
// `caret`: click (the product's gesture) | range (the zero-width selectRange
// D1 and D2 use).  The first `before=skip` run of this phase dispatched all
// eight cells at the document's FIRST paragraph rather than at their anchors,
// and three of them reported `verified-format-readback` for a no-op there.
// `EditorSession.placeCaret` polls until the engine reports a collapsed
// observed caret -- a condition the caret that is already there at open
// satisfies -- and never compares the click's coordinates against where the
// caret ends up.  See PREDICTION-caret.md in this phase's evidence directory.
const caretMode = params.get("caret") || "click";
// NOTE ON THE ARM NAMES: the runs recorded under
// findings/evidence/048/ used `caret=click` when that still meant the BARE
// gesture.  It now means the verified one, and the bare gesture is
// `click-unverified` -- the same spelling D2 uses.  Reproducing those runs
// means passing `caret=click-unverified`.
// `paint`: none (default) | page -- whether a tile is rendered before the
// gesture, the way the product page does on open.  The engine's click is
// `postMouseEvent` and it never calls `setClientVisibleArea`, so a click into a
// view that has never painted may have nowhere to land; that is a difference
// between this harness and the product, and it has to be a controlled variable
// rather than an assumption.
const paintMode = params.get("paint") || "none";
const settleMs = Number(params.get("settle") || 0);
// `settle=poll` measures the click's latency instead of assuming a delay:
// poll the caret until it reaches the requested line and record how long it
// took.  A ladder of fixed delays only ever answers "this much was enough".
const settleMode = params.get("settle") || "";
const stepTimeoutMs = 30000;

const metrics = {
  schemaVersion: 1,
  release: "spec-e2c-d3-lists",
  phase: "D3",
  profile,
  browser: navigator.userAgent,
  cells: {},
  anchors: {},
  complete: false,
  error: null,
};
globalThis.__e2c_d3 = metrics;
globalThis.__probe_metrics = metrics;

const saves = [];
globalThis.__e2c_d3_save_count = () => saves.length;
globalThis.__e2c_d3_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: String(error?.message || error).slice(0, 300),
  formatBarrier: error?.details?.formatBarrier ?? null,
});

async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}

const FIXTURES = {
  "list-contexts": { dir: "e1-fixtures", name: "list-contexts.odt" },
  "list-split": { dir: "e2-fixtures", name: "list-split.odt" },
};

async function fixtureBytes(which) {
  const spec = FIXTURES[which];
  const response = await fetch(`./${spec.dir}/${spec.name}`, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fixture fetch failed: ${spec.name} ${response.status}`);
  return response.arrayBuffer();
}

// The cells.  `action` is what is dispatched; the ORACLE is not here -- the
// analyzer applies the frozen criteria to the saved documents.
const CELLS = [
  { id: "L1", fixture: "list-contexts", anchor: "E1-LC-ISOLATED",
    action: "set-list-unordered" },
  { id: "L2", fixture: "list-contexts", anchor: "E1-LC-END",
    action: "set-list-ordered" },
  { id: "L3", fixture: "list-contexts", anchor: "E1-LC-BULLET-TWO",
    action: "set-list-none" },
  { id: "L4", fixture: "list-contexts", anchor: "E1-LC-NUMBER-TWO",
    action: "set-list-none" },
  { id: "L5", fixture: "list-contexts", anchor: "E1-LC-BULLET-ONE",
    action: "set-list-ordered" },
  { id: "L6", fixture: "list-contexts", anchor: "E1-LC-NUMBER-ONE",
    action: "set-list-ordered" },
  { id: "L7", fixture: "list-split", anchor: "E2-LS-MID",
    action: "set-list-none" },
  { id: "L8", fixture: "list-contexts", anchor: "E1-LC-BETWEEN",
    action: "set-list-unordered" },
  // The control L6 needs, and it has to run in the same round.  L6's
  // registered prediction is "`<office:body>` byte-identical", and the first
  // attempt to score it compared the saved document against the FIXTURE --
  // which fails for a reason that has nothing to do with idempotence, because
  // the fixture was written by this repo's corpus generator and the saved copy
  // by LibreOffice's ODF export (sequence-decls, style names, attribute
  // order).  The comparison that answers the prediction is against a save of
  // the same document with no action dispatched at all.
  { id: "L6C", fixture: "list-contexts", anchor: null, action: null },
];

/** Sweep for an anchor in a throwaway document, never in the measured one. */
async function surveyAnchor(anchor, which) {
  const engine = await createDocumentEngine({
    workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
  });
  const handle = await engine.open((await fixtureBytes(which)).slice(0),
                                   { name: FIXTURES[which].name,
                                     timeoutMs: 180000 });
  let found = null;
  for (let y = 1300; y <= 14000; y += 130) {
    try {
      await engine._request("editorSelectRangeV2", {
        documentHandle: handle.handle, startXTwips: 1450, startYTwips: y,
        endXTwips: 9000, endYTwips: y,
      }, { timeoutMs: stepTimeoutMs });
      const selection = await handle.getSelection({ timeoutMs: stepTimeoutMs });
      if ((selection.text || "").includes(anchor)) { found = y; break; }
    } catch { /* keep sweeping */ }
  }
  await handle.close({ timeoutMs: stepTimeoutMs }).catch(() => {});
  engine.dispose();
  return found;
}

async function anchorY(anchor, which) {
  const key = `${which}::${anchor}`;
  if (!(key in metrics.anchors))
    metrics.anchors[key] = await surveyAnchor(anchor, which);
  const y = metrics.anchors[key];
  if (y == null) throw Object.assign(new Error(`anchor ${anchor} not found`),
                                     { code: "ANCHOR_NOT_FOUND" });
  return y;
}

async function runCell(cell) {
  const entry = { cell: cell.id, fixture: cell.fixture, anchor: cell.anchor,
                  action: cell.action };
  const session = new NarrowEditorV2Session({
    engineFactory: () => createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    }),
    secureContext: globalThis.isSecureContext,
    clipboard: navigator.clipboard,
  });
  try {
    await session.open({ bytes: (await fixtureBytes(cell.fixture)).slice(0),
                         name: FIXTURES[cell.fixture].name });
    session.attachInput(document.querySelector("#sink"));
    if (cell.action === null) {
      const { bytes } = await session.save();
      saves.push({ label: `${cell.id}-after`, b64: await toBase64(bytes) });
      entry.control = true;
      return entry;
    }
    const y = await anchorY(cell.anchor, cell.fixture);
    entry.y = y;
    // The before-picture comes first, and BEFORE the caret gesture: a save
    // taken after the gesture disturbs the selection (SPEC E2-C 9.5.4).
    if (beforeMode === "save") {
      const started = performance.now();
      const { bytes: before } = await session.save();
      entry.saveMs = Math.round(performance.now() - started);
      saves.push({ label: `${cell.id}-before`, b64: await toBase64(before) });
    } else if (beforeMode === "delay") {
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    entry.beforeMode = beforeMode;
    // Where the caret is BEFORE the gesture, and whether the engine already
    // calls it observed -- that is what lets placeCaret return early.
    entry.caretBefore = caretOf(await session.editor.getState());
    entry.caretMode = caretMode;
    entry.paintMode = paintMode;
    if (paintMode === "page") {
      const tile = await session.document.render({
        xTwips: 0, yTwips: 0,
        widthTwips: session.document.widthTwips,
        heightTwips: session.document.heightTwips,
        canvasWidthPx: 512, canvasHeightPx: 512,
      }, { timeoutMs: 60000 });
      entry.painted = { width: tile.width, height: tile.height };
    }
    if (caretMode === "range") {
      await session.selectRange({ xTwips: 2000, yTwips: y },
                                { xTwips: 2000, yTwips: y },
                                { timeoutMs: stepTimeoutMs });
    } else if (caretMode === "range-then-click") {
      // Is the mouse path inert, or only ineffective from the state a freshly
      // opened document is in?  Put the caret on the anchor with the path that
      // works, then click two lines below it and look again.  If the caret
      // stays where selectRange put it, clicks do nothing at all.
      await session.selectRange({ xTwips: 2000, yTwips: y },
                                { xTwips: 2000, yTwips: y },
                                { timeoutMs: stepTimeoutMs });
      entry.caretAfterRange = caretOf(await session.editor.getState());
      entry.clickedY = y + 780;
      await session.placeCaret(2000, entry.clickedY);
    } else if (caretMode === "click-unverified") {
      // Finding 048's arm: the bare gesture, so the raw click stays measurable.
      // The `settle` arms ride on this one.
      await session.placeCaret(2000, y);
    } else {
      // The canonical gesture: the product's click, with the landing proved by
      // a readback rather than by the call returning.
      const { arrivedAfterMs, confirmedBy } =
        await placeCaretVerified(session, 2000, y)
          .catch((error) => { entry.caretError = error.code; return {}; });
      entry.caretArrivedAfterMs = arrivedAfterMs ?? null;
      entry.caretConfirmedBy = confirmedBy ?? null;
    }
    if (settleMs > 0) {
      entry.settleMs = settleMs;
      await new Promise((resolve) => setTimeout(resolve, settleMs));
    } else if (settleMode === "poll") {
      // How long does the click actually take?  A fixed-delay ladder answers
      // "250 ms is enough" and nothing about the real number; polling until the
      // caret arrives measures it.  Records the wait even when it never
      // arrives, so a cell that times out is distinguishable from one that
      // landed instantly.
      const started = performance.now();
      const deadline = started + 3000;
      let arrived = null;
      do {
        const seen = caretOf(await session.editor.getState());
        if (caretCovers(seen, y)) { arrived = performance.now() - started; break; }
        await new Promise((resolve) => setTimeout(resolve, 5));
      } while (performance.now() < deadline);
      entry.caretArrivedAfterMs = arrived === null ? null : Math.round(arrived);
      entry.caretPollGaveUpAfterMs =
        arrived === null ? Math.round(performance.now() - started) : null;
    }
    entry.caretAfter = caretOf(await session.editor.getState());
    // Fail closed.  A cell that dispatches somewhere other than its anchor
    // measures nothing, and the first run of this phase produced three
    // `verified-format-readback` results that way.  Refusing to dispatch is
    // the only outcome that cannot be mistaken for a list result later.
    entry.caretAtAnchor = caretCovers(entry.caretAfter, y);
    if (!entry.caretAtAnchor) {
      entry.error = { code: "CARET_NOT_AT_ANCHOR",
                      message: `asked for y=${y}, caret reported `
                               + `${JSON.stringify(entry.caretAfter)}`,
                      formatBarrier: null };
      return entry;
    }
    const result = await session.action(cell.action);
    entry.result = { action: result.action, changed: result.changed ?? null,
                     completion: result.completion,
                     beforeRevision: result.beforeRevision,
                     revision: result.revision };
    const { bytes: after } = await session.save();
    saves.push({ label: `${cell.id}-after`, b64: await toBase64(after) });
  } catch (error) {
    entry.error = publicError(error);
    try {
      const { bytes } = await session.save();
      saves.push({ label: `${cell.id}-after`, b64: await toBase64(bytes) });
    } catch { /* the session may be past saving */ }
  } finally {
    await session.close().catch(() => {});
  }
  return entry;
}

void (async () => {
  try {
    {
      const engine = await createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
      });
      const contract = engine.manifest?.editorContract || {};
      metrics.cells["d0-inventory"] = {
        profile: engine.manifest?.profile,
        abiVersion: contract.abiVersion,
        wasmSha256: contract.wasmSha256,
        loaderSha256: contract.loaderSha256,
        workerSha256: contract.workerSha256,
      };
      engine.dispose();
    }

    const wanted = only ? new Set(only.split(",")) : null;
    for (const cell of CELLS) {
      if (wanted && !wanted.has(cell.id)) continue;
      const entry = await runCell(cell);
      metrics.cells[cell.id] = entry;
      log(entry);
    }

    metrics.complete = true;
    log({ complete: true, cells: Object.keys(metrics.cells).length,
          saves: saves.length });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  }
})();
