// Finding 046: why core and the shipped build disagree about an empty
// paragraph's readback.  Relink queue item 3b is blocked on this.
//
// Same fixture as the native round (`e1-fixtures/empty-paragraph.odt`), same
// paragraph, same action.  What is new here is the caret: every recorded
// browser round of this cell predates finding 048's fix, so its click was
// confirmed by a condition that was already true before the click.
//
// The control arm is the load-bearing one.  If a paragraph WITH text also reads
// back zero blocks, `preBlocks` is not describing content and nothing else in
// the round means anything.
//
// Criteria: findings/evidence/046/browser-vs-native/PREDICTION.md

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";
import { placeCaretVerified, caretOf } from "./e2-c-caret.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const stepTimeoutMs = Number(params.get("stepTimeout") || 60000);

const FIXTURE = { dir: "e1-fixtures", name: "empty-paragraph.odt" };
const BEFORE = "E1-EMPTY-BEFORE";
const AFTER = "E1-EMPTY-AFTER";

const metrics = {
  schemaVersion: 1,
  release: "finding-046-browser-vs-native",
  profile,
  browser: navigator.userAgent,
  fixture: FIXTURE.name,
  geometry: null,
  arms: {},
  complete: false,
  error: null,
};
globalThis.__f046_browser = metrics;
globalThis.__probe_metrics = metrics;

// The runner's save-extraction contract.  Kept because the native round's
// strongest single fact came from a saved document -- the empty paragraph
// really did become a list item, so "the bullet did nothing" was never on the
// table.  The browser side has to be able to say the same thing.
const saves = [];
globalThis.__f046_browser_save_count = () => saves.length;
globalThis.__f046_browser_save = (index) => saves[index] || null;

async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: String(error?.message || error).slice(0, 300),
  // The whole reason this round exists rides in here on a failure: the product
  // reports the barrier record on the error, not on success.
  formatBarrier: error?.details?.formatBarrier
    ?? error?.formatBarrier ?? null,
  details: error?.details ? { ...error.details, formatBarrier: undefined } : null,
});

async function fixtureBytes() {
  const response = await fetch(`./${FIXTURE.dir}/${FIXTURE.name}`,
                               { cache: "no-cache" });
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  return response.arrayBuffer();
}

function newSession() {
  return new NarrowEditorV2Session({
    engineFactory: () => createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    }),
    secureContext: globalThis.isSecureContext,
    clipboard: navigator.clipboard,
  });
}

async function openSession() {
  const session = newSession();
  await session.open({ bytes: (await fixtureBytes()).slice(0),
                       name: FIXTURE.name, timeoutMs: stepTimeoutMs });
  session.attachInput(document.querySelector("#sink"));
  return session;
}

function rectangleOf(found) {
  const values = (found?.selections?.[0]?.rectangles || "")
    .split(";")[0].split(",").map((v) => Number.parseInt(v.trim(), 10));
  if (values.length !== 4 || values.some((v) => !Number.isFinite(v))) return null;
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

/** Where the empty paragraph is, measured rather than assumed.
 *
 *  D2's cell used `anchorY + 390`, a constant taken from one measurement of one
 *  corpus.  Here the empty line box is the GAP between the two paragraphs that
 *  bracket it, which is core's own geometry -- the same lesson the D3 corpus
 *  round paid for with three cells refused by a 195-twip constant.
 */
async function geometry(session) {
  const before = rectangleOf(
    await session.document.search(BEFORE, { timeoutMs: stepTimeoutMs }));
  const after = rectangleOf(
    await session.document.search(AFTER, { timeoutMs: stepTimeoutMs }));
  if (!before || !after) return null;
  const top = before.y + before.height;
  const height = after.y - top;
  return {
    before, after,
    empty: { x: before.x, y: top, width: before.width, height },
    // The fixture's fourth paragraph is empty too, and there is no anchor below
    // it to bound its box.  Estimated as one line of the paragraph above --
    // declared, and self-checking: if the estimate is wrong the caret gate
    // refuses the arm rather than the arm reporting about the wrong line.
    lastEmpty: { x: after.x, y: after.y + after.height,
                 width: after.width, height: after.height,
                 estimated: true },
    // Recorded so a reader can see whether the gap is a plausible line box at
    // all: a negative or absurd height means the two anchors are not adjacent
    // in the way this round assumes, and the PREDICTION calls that void.
    plausible: height > 0 && height < 4 * (before.height || 1),
  };
}

function midpoint(rectangle) {
  return {
    x: rectangle.x + Math.max(1, Math.floor(rectangle.width / 2)),
    y: rectangle.y + Math.max(1, Math.floor(rectangle.height / 2)),
  };
}

async function runArm(name, place, target) {
  const entry = { arm: name, target };
  const session = await openSession();
  try {
    const geo = metrics.geometry;
    entry.geometry = geo?.[target] ?? null;
    const point = midpoint(entry.geometry);
    entry.clickedAt = point;
    entry.caretBefore = await place(session, point, entry.geometry);
    const state = await session.editor.getState().catch(() => null);
    entry.stateBeforeAction = {
      caret: caretOf(state),
      selection: state?.selection ?? null,
    };
    const result = await session.action("set-list-unordered")
      .then((value) => ({ ok: true, value }), (error) => ({ ok: false, error }));
    entry.accepted = result.ok;
    entry.result = result.ok
      ? { completion: result.value?.completion, revision: result.value?.revision,
          formatBarrier: result.value?.formatBarrier ?? null }
      : publicError(result.error);
    entry.sessionState = session.state?.snapshot?.state ?? null;
    if (entry.sessionState === "recoverable-error") {
      entry.rollback = await session.rollback()
        .then(() => "ok", (error) => publicError(error));
      entry.sessionStateAfterRollback = session.state?.snapshot?.state ?? null;
    }
    if (["ready", "busy"].includes(session.state?.snapshot?.state)) {
      const { bytes } = await session.save({ timeoutMs: stepTimeoutMs });
      entry.savedBytes = bytes.byteLength ?? bytes.length ?? null;
      saves.push({ label: `${name}.odt`, b64: await toBase64(bytes) });
    }
  } catch (error) {
    entry.error = publicError(error);
  } finally {
    await session.close().catch(() => {});
  }
  metrics.arms[name] = entry;
  log(entry);
  return entry;
}

// The product's confirmed click (finding 048's fix), gated on the measured line
// box rather than on a constant.
const byClick = async (session, point, rectangle) => {
  const { caret, arrivedAfterMs, confirmedBy } = await placeCaretVerified(
    session, point.x, point.y,
    { caretTimeoutMs: stepTimeoutMs, anchorRect: rectangle });
  return { caret, arrivedAfterMs, confirmedBy, gesture: "click-verified" };
};

// SPEC E2-C 9.5.6's other gesture: a zero-width selectRange.  Declared as NOT
// the product's gesture -- it is here because the recorded rounds show the two
// gestures reaching different failure shapes, and this round has to be able to
// say whether they also differ in what was read.
const bySelectRange = async (session, point) => {
  await session.selectRange({ xTwips: point.x, yTwips: point.y },
                            { xTwips: point.x, yTwips: point.y },
                            { timeoutMs: stepTimeoutMs });
  const state = await session.editor.getState().catch(() => null);
  return { caret: caretOf(state), gesture: "selectrange-zero-width" };
};

// A5: a RANGE inside one text paragraph, to find out whether preBlocks is ever
// non-zero at all.  Added after the smoke run showed the control arm reporting
// zero blocks on a SUCCESSFUL barrier; registered in the PREDICTION's addendum
// A1 before any round was recorded.
async function runRangeArm(name) {
  const entry = { arm: name, target: "before", gesture: "selectrange-text" };
  const session = await openSession();
  try {
    const rectangle = metrics.geometry.before;
    entry.geometry = rectangle;
    const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
    // Start and end inside the same paragraph: this is the range-single route
    // by construction, not by hope, and the route the engine reports is
    // recorded so the claim can be checked rather than assumed.
    await session.selectRange({ xTwips: rectangle.x + 20, yTwips: y },
                              { xTwips: rectangle.x + rectangle.width - 20,
                                yTwips: y },
                              { timeoutMs: stepTimeoutMs });
    const state = await session.editor.getState().catch(() => null);
    entry.stateBeforeAction = {
      caret: caretOf(state), selection: state?.selection ?? null,
    };
    const result = await session.action("set-list-unordered")
      .then((value) => ({ ok: true, value }), (error) => ({ ok: false, error }));
    entry.accepted = result.ok;
    entry.result = result.ok
      ? { completion: result.value?.completion, revision: result.value?.revision,
          formatBarrier: result.value?.formatBarrier ?? null }
      : publicError(result.error);
    entry.sessionState = session.state?.snapshot?.state ?? null;
  } catch (error) {
    entry.error = publicError(error);
  } finally {
    await session.close().catch(() => {});
  }
  metrics.arms[name] = entry;
  log(entry);
  return entry;
}

void (async () => {
  try {
    {
      const session = await openSession();
      try {
        metrics.geometry = await geometry(session);
        const engine = session.engine;
        const contract = engine?.manifest?.editorContract || {};
        metrics.inventory = {
          profile: engine?.manifest?.profile,
          abiVersion: contract.abiVersion,
          wasmSha256: contract.wasmSha256,
          loaderSha256: contract.loaderSha256,
          workerSha256: contract.workerSha256,
        };
      } finally { await session.close().catch(() => {}); }
    }
    log({ geometry: metrics.geometry });
    if (!metrics.geometry?.plausible)
      throw Object.assign(new Error("the empty paragraph's line box is not "
                                    + "between the two anchors"),
                          { code: "GEOMETRY_IMPLAUSIBLE" });

    // The control first, on purpose: if it fails, the rest is uninterpretable
    // and the evidence should show that it was checked before, not after.
    await runArm("A3-text-click", byClick, "before");
    await runArm("A1-empty-click", byClick, "empty");
    await runArm("A2-empty-selectrange", bySelectRange, "empty");
    // The fixture's last paragraph is also empty; the native round measured it
    // separately (2585 → 2196) and got the same behaviour.
    await runArm("A4-last-empty-click", byClick, "lastEmpty");
    await runRangeArm("A5-text-range");

    metrics.complete = true;
    log({ complete: true, arms: Object.keys(metrics.arms).length });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  }
})();
