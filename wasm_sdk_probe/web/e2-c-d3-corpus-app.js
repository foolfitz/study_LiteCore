// SPEC E2-C, phase D3: the corpus half.
//
// The list half (L1-L8) asked "does a list action do the right thing to a
// list".  This half asks the other question the matrix froze: **does an
// ordinary edit at a named anchor leave the rest of the document intact** --
// across seven ODT corpora, two of which are only carried here because the L
// cells already saved them.
//
// A separate file from `e2-c-d3-app.js` on purpose.  That one's bytes are part
// of the identity of `d3-lists/run-3` and `run-4-fixed-shell`; a page edited
// after its evidence was taken is a page the evidence can no longer be
// reproduced from.
//
// The page judges nothing.  `tools/analyze_e2_c_d3_corpus.py` applies the
// criteria registered in
// findings/evidence/sdk-e2/e2-c-validation/d3-corpus/PREDICTION.md, offline,
// to the saved bytes.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";
import { caretOf, placeCaretVerified } from "./e2-c-caret.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const only = params.get("only");
const stepTimeoutMs = Number(params.get("stepTimeout") || 120000);
// The 100-page corpus takes appreciably longer to open than the others, and a
// timeout is not a measurement -- it is the absence of one.  Measured per
// fixture rather than guessed at once for all of them.
const openTimeoutMs = Number(params.get("openTimeout") || 600000);

const metrics = {
  schemaVersion: 1,
  release: "spec-e2c-d3-corpus",
  phase: "D3",
  half: "corpus",
  profile,
  browser: navigator.userAgent,
  cells: {},
  complete: false,
  error: null,
};
globalThis.__e2c_d3c = metrics;
globalThis.__probe_metrics = metrics;

const saves = [];
globalThis.__e2c_d3c_save_count = () => saves.length;
globalThis.__e2c_d3c_save = (index) => saves[index] || null;

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
  "l0-t1": { dir: "r7-compat-fixtures", name: "l0-t1-plain-zh.odt" },
  "l0-t2": { dir: "r7-compat-fixtures", name: "l0-t2-styled.odt" },
  "l0-t3": { dir: "r7-compat-fixtures", name: "l0-t3-long.odt" },
  "l1-review": { dir: "r7-compat-fixtures", name: "l1-review.odt" },
  "l4-stress-100": { dir: "r7-compat-fixtures", name: "l4-stress-100.odt" },
};

async function fixtureBytes(which) {
  const spec = FIXTURES[which];
  const response = await fetch(`./${spec.dir}/${spec.name}`, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fixture fetch failed: ${spec.name} ${response.status}`);
  return response.arrayBuffer();
}

// One action across every cell, so a difference is attributable to the DOCUMENT
// rather than to the action; see PREDICTION.md for the other three reasons.
const ACTION = "set-list-unordered";

const CELLS = [
  { id: "c-l0-t1", fixture: "l0-t1",
    anchor: "Final line：ODT round-trip 完整性檢查。" },
  { id: "c-l0-t2", fixture: "l0-t2",
    anchor: "文件結尾：請確認表格、圖片、註解與標題樣式均保留。" },
  { id: "c-l0-t3-first", fixture: "l0-t3", anchor: "第 1 頁：長文件記憶體與效能測試" },
  // Page 11, and only after checking the corpus really carries a per-page
  // anchor for every page: the manifest names pages 1 and 22, so a "middle"
  // anchor had to be shown to exist before it could be aimed at.
  { id: "c-l0-t3-middle", fixture: "l0-t3", anchor: "第 11 頁：長文件記憶體與效能測試" },
  { id: "c-l0-t3-last", fixture: "l0-t3", anchor: "第 22 頁：長文件記憶體與效能測試" },
  { id: "c-l1-review", fixture: "l1-review", anchor: "Lorem ipsum" },
  { id: "c-l4-stress", fixture: "l4-stress-100", anchor: "R7 stress page 050 頁面錨點" },
  { id: "c-l4-stress-last", fixture: "l4-stress-100",
    anchor: "R7 stress page 100 頁面錨點" },
  // One control per fixture: open, save, dispatch nothing.
  //
  // The comparison a structural criterion needs is against a save of the SAME
  // document with no action, not against the fixture on disk.  The list half
  // learned this for L6 (a fixture written by this repo's generator and a save
  // written by LibreOffice's ODF export differ for reasons that have nothing to
  // do with the action), and 2026-08-16 measured a much larger case of it:
  // `l4-stress-100` carries 100 `<draw:frame text:anchor-type="as-char">`
  // directly under `<office:text>`, and BOTH LibreOffice builds on this machine
  // drop all of them on a plain ODT->ODT convert with no editing at all.
  // Comparing against the fixture would report that as content loss caused by
  // the edit.  It is a corpus defect, and the control is what tells them apart.
  { id: "c-l0-t1-control", fixture: "l0-t1", anchor: null },
  { id: "c-l0-t2-control", fixture: "l0-t2", anchor: null },
  { id: "c-l0-t3-control", fixture: "l0-t3", anchor: null },
  { id: "c-l1-review-control", fixture: "l1-review", anchor: null },
  { id: "c-l4-stress-control", fixture: "l4-stress-100", anchor: null },
];

/** Where is this anchor?  Search returns core's own rectangle, so the caret is
 *  aimed at a MEASURED position rather than a swept guess -- which is the only
 *  way to reach page 50 of a 100-page document at all. */
async function anchorRectangle(session, anchor) {
  const found = await session.document.search(anchor, { timeoutMs: stepTimeoutMs });
  if (!found.found)
    throw Object.assign(new Error(`anchor not found: ${anchor}`),
                        { code: "ANCHOR_NOT_FOUND" });
  const raw = found.selections?.[0]?.rectangles || "";
  const values = raw.split(";")[0].split(",")
    .map((value) => Number.parseInt(value.trim(), 10));
  if (values.length !== 4 || values.some((value) => !Number.isFinite(value)))
    throw Object.assign(
      new Error(`search returned no usable rectangle for ${anchor}`),
      { code: "ANCHOR_RECTANGLE_UNUSABLE" });
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

async function runCell(cell) {
  const entry = { cell: cell.id, fixture: cell.fixture, anchor: cell.anchor,
                  action: ACTION, fixtureFile: FIXTURES[cell.fixture].name };
  const session = new NarrowEditorV2Session({
    engineFactory: () => createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    }),
    secureContext: globalThis.isSecureContext,
    clipboard: navigator.clipboard,
  });
  const started = performance.now();
  try {
    await session.open({ bytes: (await fixtureBytes(cell.fixture)).slice(0),
                         name: FIXTURES[cell.fixture].name,
                         timeoutMs: openTimeoutMs });
    entry.openMs = Math.round(performance.now() - started);
    session.attachInput(document.querySelector("#sink"));

    if (cell.anchor === null) {
      const { bytes } = await session.save({ timeoutMs: openTimeoutMs });
      saves.push({ label: `${cell.id}-after`, b64: await toBase64(bytes) });
      entry.control = true;
      entry.savedBytes = bytes.byteLength ?? bytes.length ?? null;
      return entry;
    }

    const rectangle = await anchorRectangle(session, cell.anchor);
    entry.rectangle = rectangle;
    // The middle of the anchor's line, the way E1-C's corpus phase aims.
    const x = rectangle.x + Math.max(1, Math.floor(rectangle.width / 2));
    const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
    entry.target = { x, y };
    entry.caretBefore = caretOf(await session.editor.getState());

    // The product's click, and it has to be PROVED to have landed.  Search left
    // a selection covering the anchor; the click is what collapses it to the
    // caret the product would form, and finding 048 is why the landing cannot
    // be taken on trust.
    // The anchor's own rectangle goes with the click: acceptance is then "the
    // caret's line box overlaps the anchor's", which needs no constant.  The
    // first execution of this round refused three cells with a 520-twip
    // heading line box for exactly that missing argument -- both browsers,
    // identically, which is what made it a harness fact rather than a product
    // one (run-1, kept).
    const { arrivedAfterMs, confirmedBy } =
      await placeCaretVerified(session, x, y,
                               { caretTimeoutMs: 30000, anchorRect: rectangle });
    entry.caretArrivedAfterMs = arrivedAfterMs ?? null;
    entry.caretConfirmedBy = confirmedBy ?? null;
    entry.caretAfter = caretOf(await session.editor.getState());

    const result = await session.action(ACTION);
    entry.result = { action: result.action, changed: result.changed ?? null,
                     completion: result.completion,
                     beforeRevision: result.beforeRevision,
                     revision: result.revision };
    const { bytes } = await session.save({ timeoutMs: openTimeoutMs });
    saves.push({ label: `${cell.id}-after`, b64: await toBase64(bytes) });
    entry.savedBytes = bytes.byteLength ?? bytes.length ?? null;
  } catch (error) {
    entry.error = publicError(error);
    // No retry -- SPEC E2-C section 3.  A save is still attempted so a failed
    // cell says what the document looked like when it failed, which is the
    // difference between a finding and a shrug.
    try {
      const { bytes } = await session.save({ timeoutMs: openTimeoutMs });
      saves.push({ label: `${cell.id}-after`, b64: await toBase64(bytes) });
      entry.savedAfterFailure = true;
    } catch { /* the session may be past saving */ }
  } finally {
    entry.totalMs = Math.round(performance.now() - started);
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
