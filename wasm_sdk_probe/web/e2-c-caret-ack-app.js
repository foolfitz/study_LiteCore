// finding 048 -- can the product tell that a click has been processed?
//
// The fix has to replace a predicate that is true before the click with one
// that depends on it.  `sourceSequence` is the engine's count of callbacks that
// changed editor state, and it IS in the product's `editorGetStateV2` result --
// unlike the `editor-state` push event, which carries the callback's `source`
// but is forwarded only on discovery profiles.
//
// The question this page answers is the one that decides the design: does a
// click that does NOT move the caret still advance the sequence?  If it does,
// the fix needs no geometry.  Predictions are in
// findings/evidence/048/PREDICTION-ack.md, written before this file.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const idleMs = Number(params.get("idle") || 1500);
const watchMs = Number(params.get("watch") || 1500);

const metrics = {
  schemaVersion: 1, release: "finding-048-ack", phase: "probe", profile,
  browser: navigator.userAgent, cells: {}, complete: false, error: null,
};
globalThis.__e2c_ack = metrics;
globalThis.__probe_metrics = metrics;
const saves = [];
globalThis.__e2c_ack_save_count = () => saves.length;
globalThis.__e2c_ack_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };

const read = async (session) => {
  const state = await session.editor.getState();
  return {
    sequence: state?.sourceSequence ?? null,
    caretY: state?.caret?.y ?? null,
    caretHeight: state?.caret?.height ?? null,
    visible: state?.visible ?? null,
  };
};

/** Click, then watch the sequence and the caret for `windowMs`, sampling every
 *  5 ms.  Records the FIRST sample at which each changed, and the totals -- a
 *  probe that only reported "it changed" could not tell one callback from a
 *  stream of them. */
async function clickAndWatch(session, x, y, windowMs) {
  const before = await read(session);
  const started = performance.now();
  await session.placeCaret(x, y);
  const afterCall = { at: Math.round(performance.now() - started),
                      ...await read(session) };
  let sequenceMovedAt = null;
  let caretMovedAt = null;
  let last = before;
  while (performance.now() - started < windowMs) {
    const now = await read(session);
    const at = Math.round(performance.now() - started);
    if (sequenceMovedAt === null && now.sequence !== before.sequence)
      sequenceMovedAt = at;
    if (caretMovedAt === null && now.caretY !== before.caretY) caretMovedAt = at;
    last = now;
    await new Promise((resolve) => setTimeout(resolve, 5));
  }
  return {
    asked: { x, y }, before, afterCall, last,
    sequenceMovedAt, caretMovedAt,
    sequenceDelta: last.sequence === null || before.sequence === null
      ? null : last.sequence - before.sequence,
    caretMoved: last.caretY !== before.caretY,
  };
}

void (async () => {
  const session = new NarrowEditorV2Session({
    engineFactory: () => createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    }),
    secureContext: globalThis.isSecureContext,
    clipboard: navigator.clipboard,
  });
  try {
    const response = await fetch("./e1-fixtures/list-contexts.odt", { cache: "no-cache" });
    await session.open({ bytes: await response.arrayBuffer(),
                         name: "list-contexts.odt" });
    session.attachInput(document.querySelector("#sink"));

    {
      const engine = await createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
      });
      const contract = engine.manifest?.editorContract || {};
      metrics.cells["d0-inventory"] = {
        profile: engine.manifest?.profile, abiVersion: contract.abiVersion,
        wasmSha256: contract.wasmSha256, loaderSha256: contract.loaderSha256,
        workerSha256: contract.workerSha256,
      };
      engine.dispose();
    }

    // P-A3 first, and before any click: if the sequence moves on its own, an
    // advance is not evidence of anything and the rest of this page is moot.
    const idleStart = await read(session);
    await new Promise((resolve) => setTimeout(resolve, idleMs));
    const idleEnd = await read(session);
    metrics.cells["idle-before-any-click"] = {
      windowMs: idleMs, start: idleStart, end: idleEnd,
      advanced: idleEnd.sequence !== idleStart.sequence,
    };
    log({ cell: "idle-before-any-click", ...metrics.cells["idle-before-any-click"] });

    // P-A1: a click that lands somewhere else.
    metrics.cells["click-moves"] = await clickAndWatch(session, 2000, 3640, watchMs);
    log({ cell: "click-moves", ...metrics.cells["click-moves"] });

    // P-A2, the one that decides the design: click the SAME line again.
    metrics.cells["click-same-line"] = await clickAndWatch(session, 2000, 3640, watchMs);
    log({ cell: "click-same-line", ...metrics.cells["click-same-line"] });

    // And once more a few twips away but on the same line, because "the same
    // line" and "the same pixel" are different claims and a product click is
    // never the same pixel twice.
    metrics.cells["click-same-line-offset"] =
      await clickAndWatch(session, 2600, 3660, watchMs);
    log({ cell: "click-same-line-offset", ...metrics.cells["click-same-line-offset"] });

    // Back to a different line, to show the signal still works after the
    // no-move clicks rather than having been consumed by them.
    metrics.cells["click-moves-again"] = await clickAndWatch(session, 2000, 1950, watchMs);
    log({ cell: "click-moves-again", ...metrics.cells["click-moves-again"] });

    // P-A3 again, AFTER the clicks: background traffic that only starts once
    // something has happened would break the predicate just as thoroughly.
    const tailStart = await read(session);
    await new Promise((resolve) => setTimeout(resolve, idleMs));
    const tailEnd = await read(session);
    metrics.cells["idle-after-clicks"] = {
      windowMs: idleMs, start: tailStart, end: tailEnd,
      advanced: tailEnd.sequence !== tailStart.sequence,
    };
    log({ cell: "idle-after-clicks", ...metrics.cells["idle-after-clicks"] });

    metrics.complete = true;
    log({ complete: true });
  } catch (error) {
    metrics.error = { code: error?.code || error?.name || "ERROR",
                      message: String(error?.message || error).slice(0, 300) };
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  } finally {
    await session.close().catch(() => {});
  }
})();
