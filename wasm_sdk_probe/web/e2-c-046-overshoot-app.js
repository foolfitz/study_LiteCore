// 046: how far does the barrier's selection overshoot go?
//
// The readback round measured the defect on ONE position of ONE fixture: on an
// empty paragraph, `.uno:SelectText` selects into the paragraph below, so a
// mutation that succeeded is refused.  One position is not a characterisation.
//
// The discriminator is `text-end`.  Finding 034 replaced the OLD selection pair
// because it escaped to a neighbour "whenever the caret already sat at a
// paragraph edge", and an empty paragraph is one where the caret is at both
// edges at once.  So: does a caret at the END of a paragraph WITH text overshoot
// too?  If it does, this is an ordinary gesture and a much larger defect.
//
// Frozen engine throughout: the diagnostic profile's probe.wasm is byte-identical
// to the shipped one; only the worker's projection differs.
//
// Criteria: findings/evidence/046/overshoot/PREDICTION.md

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";
import { placeCaretVerified, caretOf } from "./e2-c-caret.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-readback-diagnostic";
const stepTimeoutMs = Number(params.get("stepTimeout") || 60000);

const FIXTURES = {
  empty: { dir: "e1-fixtures", name: "empty-paragraph.odt" },
  lists: { dir: "e1-fixtures", name: "list-contexts.odt" },
};

// `where` is resolved against the anchor's own rectangle, which is core's
// geometry rather than a constant of ours.
const CELLS = [
  { id: "text-mid", fixture: "empty", anchor: "E1-EMPTY-BEFORE", where: "mid" },
  { id: "text-start", fixture: "empty", anchor: "E1-EMPTY-BEFORE", where: "start" },
  { id: "text-end", fixture: "empty", anchor: "E1-EMPTY-BEFORE", where: "end" },
  { id: "empty-mid", fixture: "empty", anchor: "E1-EMPTY-BEFORE", where: "below" },
  { id: "isolated-mid", fixture: "lists", anchor: "E1-LC-ISOLATED", where: "mid" },
  { id: "isolated-end", fixture: "lists", anchor: "E1-LC-ISOLATED", where: "end" },
  { id: "between-mid", fixture: "lists", anchor: "E1-LC-BETWEEN", where: "mid" },
  { id: "bullet-one-mid", fixture: "lists", anchor: "E1-LC-BULLET-ONE", where: "mid" },
];

const metrics = {
  schemaVersion: 1,
  release: "finding-046-overshoot",
  profile,
  browser: navigator.userAgent,
  cells: {},
  complete: false,
  error: null,
};
globalThis.__f046_overshoot = metrics;
globalThis.__probe_metrics = metrics;

const saves = [];
globalThis.__f046_overshoot_save_count = () => saves.length;
globalThis.__f046_overshoot_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: String(error?.message || error).slice(0, 300),
  formatBarrier: error?.details?.formatBarrier ?? error?.formatBarrier ?? null,
});

async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}

async function fixtureBytes(which) {
  const spec = FIXTURES[which];
  const response = await fetch(`./${spec.dir}/${spec.name}`, { cache: "no-cache" });
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  return response.arrayBuffer();
}

function rectangleOf(found) {
  const values = (found?.selections?.[0]?.rectangles || "")
    .split(";")[0].split(",").map((v) => Number.parseInt(v.trim(), 10));
  if (values.length !== 4 || values.some((v) => !Number.isFinite(v))) return null;
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

async function openSession(which) {
  const session = new NarrowEditorV2Session({
    engineFactory: () => createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    }),
    secureContext: globalThis.isSecureContext,
    clipboard: navigator.clipboard,
  });
  await session.open({ bytes: (await fixtureBytes(which)).slice(0),
                       name: FIXTURES[which].name, timeoutMs: stepTimeoutMs });
  session.attachInput(document.querySelector("#sink"));
  return session;
}

/** Where to click, and which line box the caret gate should accept.
 *
 *  `end` clicks well past the last character on the same line: core clamps to
 *  the end of the line, which is the paragraph edge finding 034 named.  The
 *  caret's reported x is recorded so "did it really land at the end" is a
 *  measurement rather than an assumption.
 */
function target(rectangle, where) {
  const midY = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  switch (where) {
    case "start":
      return { point: { x: rectangle.x + 1, y: midY }, box: rectangle };
    case "end":
      return { point: { x: rectangle.x + rectangle.width + 2000, y: midY },
               box: rectangle };
    case "below": {
      // The paragraph after the anchor: its line box starts where the anchor's
      // ends.  Height borrowed from the anchor, and the caret gate refuses the
      // cell if that estimate is wrong.
      const box = { x: rectangle.x, y: rectangle.y + rectangle.height,
                    width: rectangle.width, height: rectangle.height };
      return { point: { x: box.x + Math.max(1, Math.floor(box.width / 2)),
                        y: box.y + Math.max(1, Math.floor(box.height / 2)) },
               box };
    }
    default:
      return { point: { x: rectangle.x + Math.max(1, Math.floor(rectangle.width / 2)),
                        y: midY }, box: rectangle };
  }
}

async function runCell(cell) {
  const entry = { cell: cell.id, fixture: cell.fixture, anchor: cell.anchor,
                  where: cell.where };
  const session = await openSession(cell.fixture);
  try {
    const rectangle = rectangleOf(
      await session.document.search(cell.anchor, { timeoutMs: stepTimeoutMs }));
    if (!rectangle)
      throw Object.assign(new Error(`anchor not found: ${cell.anchor}`),
                          { code: "ANCHOR_NOT_FOUND" });
    entry.anchorRect = rectangle;
    const { point, box } = target(rectangle, cell.where);
    entry.clickedAt = point;
    entry.lineBox = box;
    const placed = await placeCaretVerified(session, point.x, point.y,
                                            { caretTimeoutMs: stepTimeoutMs,
                                              anchorRect: box });
    entry.caret = placed.caret;
    // For `end`, whether the caret really sits past the text is the whole
    // premise of the cell, so it is measured, not assumed.
    entry.caretPastText = placed.caret?.x != null
      ? placed.caret.x >= rectangle.x + rectangle.width - 20 : null;
    const result = await session.action("set-list-unordered")
      .then((value) => ({ ok: true, value }), (error) => ({ ok: false, error }));
    entry.accepted = result.ok;
    entry.result = result.ok
      ? { completion: result.value?.completion,
          formatBarrier: result.value?.formatBarrier ?? null }
      : publicError(result.error);
    entry.sessionState = session.state?.snapshot?.state ?? null;
    if (entry.sessionState === "recoverable-error")
      entry.rollback = await session.rollback()
        .then(() => "ok", (error) => publicError(error));
    if (["ready", "busy"].includes(session.state?.snapshot?.state)) {
      const { bytes } = await session.save({ timeoutMs: stepTimeoutMs });
      entry.savedBytes = bytes.byteLength ?? bytes.length ?? null;
      saves.push({ label: `${cell.id}.odt`, b64: await toBase64(bytes) });
    }
  } catch (error) {
    entry.error = publicError(error);
  } finally {
    await session.close().catch(() => {});
  }
  metrics.cells[cell.id] = entry;
  log({ cell: cell.id, accepted: entry.accepted,
        blockCount: entry.result?.formatBarrier?.readback?.blockCount ?? null,
        shape: entry.result?.formatBarrier?.failureShape ?? null,
        caretX: entry.caret?.x ?? null, pastText: entry.caretPastText });
  return entry;
}

void (async () => {
  try {
    {
      const engine = await createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
      });
      const contract = engine.manifest?.editorContract || {};
      metrics.inventory = {
        profile: engine.manifest?.profile,
        abiVersion: contract.abiVersion,
        wasmSha256: contract.wasmSha256,
        loaderSha256: contract.loaderSha256,
        workerSha256: contract.workerSha256,
      };
      engine.dispose();
    }
    for (const cell of CELLS)
      await runCell(cell);
    metrics.complete = true;
    log({ complete: true, cells: Object.keys(metrics.cells).length });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  }
})();
