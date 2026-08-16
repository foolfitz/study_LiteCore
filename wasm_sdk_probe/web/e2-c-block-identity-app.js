// Does the v3 engine ANSWER a click, and does the barrier stop verifying the
// wrong paragraph?
//
// Both changes rode the 2026-08-17 link.  The predictions they are judged
// against were registered before it, in
// research/DESIGN-2026-08-16-caret-by-block-and-offset.md -- section 4 (D-BI-1
// to D-BI-4) and the appendix, which records that the implementation's deadline
// is 250 ms while D-BI-1 asks for 200, and that the threshold was NOT moved to
// make the prediction pass.
//
// This page drives `editorPlaceCaretV2` through the SDK, NOT the shell's
// `placeCaret`.  The shell has not been changed to use the new call yet, and
// that is deliberate: if the engine cannot answer, changing the shell would be
// building on a premise this round exists to test.
//
// It measures.  It does not judge -- tools/analyze_block_identity_link.py does,
// offline, with its own self-test.

import { createDocumentEngine } from "./sdk/document-sdk.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v3";
const stepTimeoutMs = Number(params.get("step") || 60000);

const metrics = {
  schemaVersion: 1,
  release: "block-identity-after-link",
  profile,
  browser: navigator.userAgent,
  cells: {},
  complete: false,
  error: null,
};
globalThis.__e2c_bi = metrics;
globalThis.__probe_metrics = metrics;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };

// An ArrayBuffer, not a view: `engine.open` requires one and rejects a
// Uint8Array with INVALID_ARGUMENT.  The other harness pages hand it
// `bytes.slice(0)` on a Uint8Array, which produces a Uint8Array too -- they get
// away with it because they pass the buffer through their own helper first.
async function fixtureBytes(name) {
  const response = await fetch(`./e1-fixtures/${name}`, { cache: "no-cache" });
  if (!response.ok) throw new Error(`fixture ${name}: ${response.status}`);
  return await response.arrayBuffer();
}

/** One call to the new entry point, timed by the caller's clock.
 *
 *  The elapsed time is the whole point of D-BI-1: the old path could not answer
 *  a click that changed nothing, so the host waited out its own timeout.  What
 *  is recorded is the round trip AND what came back, because "it returned"
 *  is not the measurement -- the tree has a comment about that in the E1-D
 *  readback path, and it applies here word for word.
 */
async function placeCaret(engine, handle, xTwips, yTwips) {
  const started = performance.now();
  let result = null;
  let error = null;
  try {
    result = await engine._request("editorPlaceCaretV2", {
      documentHandle: handle.handle, xTwips, yTwips,
    }, { timeoutMs: stepTimeoutMs });
  } catch (thrown) {
    error = { code: thrown?.code ?? null, message: String(thrown?.message ?? thrown) };
  }
  const elapsedMs = Math.round(performance.now() - started);
  const paragraph = result?.state?.caretParagraph ?? null;
  return {
    asked: { xTwips, yTwips },
    elapsedMs,
    completion: result?.completion ?? null,
    caret: result?.state?.caret ?? null,
    paragraph,
    error,
  };
}

// The handle's own `revision` is bookkeeping the SDK does for the operations it
// wraps, and this page drives `_request` directly -- so after a placeCaret or a
// break it can be stale, and the next action comes back STALE_REVISION.  Asked
// for each time rather than tracked here: a second copy of somebody else's
// bookkeeping is a second thing that can be wrong.
async function currentRevision(engine, handle, timeoutMs) {
  const state = await engine._request("editorGetStateV2", {
    documentHandle: handle.handle,
  }, { timeoutMs });
  return state?.revision ?? handle.revision;
}

async function main() {
  const engine = await createDocumentEngine({
    workerUrl: `./profiles/${profile}/sdk-worker.js`,
    timeoutMs: 180000,
  });
  metrics.manifest = {
    profile: engine.manifest?.profile ?? null,
    wasmSha256: engine.manifest?.editorContract?.wasmSha256 ?? null,
    abiVersion: engine.manifest?.editorContract?.abiVersion ?? null,
  };
  log({ step: "manifest", ...metrics.manifest });

  const handle = await engine.open(await fixtureBytes("list-contexts.odt"),
                                   { name: "list-contexts.odt", timeoutMs: 180000 });

  // Find a line with text, the way every other harness here does: sweep a
  // range-select down the page until the anchor comes back.  No guessed twips.
  let anchorY = null;
  for (let y = 1300; y <= 14000; y += 130) {
    try {
      await engine._request("editorSelectRangeV2", {
        documentHandle: handle.handle, startXTwips: 1450, startYTwips: y,
        endXTwips: 9000, endYTwips: y,
      }, { timeoutMs: stepTimeoutMs });
      const selection = await handle.getSelection({ timeoutMs: stepTimeoutMs });
      if ((selection.text || "").includes("E1-LC-ISOLATED")) { anchorY = y; break; }
    } catch { /* keep sweeping */ }
  }
  metrics.cells.anchor = { anchorY };
  log({ step: "anchor", anchorY });

  // ---- D-BI-2: is the answer fresh, with no wait of the host's own? -------
  //
  // Four native rounds all read the a11y payload after a 700 ms drain, and the
  // design says in as many words that short-latency freshness was never
  // measured.  Here the paragraph comes back INSIDE the call's own reply, so if
  // it names the paragraph that was just clicked, the answer was fresh when it
  // was given.
  const onAnchor = await placeCaret(engine, handle, 2000, anchorY ?? 1430);
  const onAnother = await placeCaret(engine, handle, 2000, (anchorY ?? 1430) + 800);
  metrics.cells["d-bi-2-freshness"] = { onAnchor, onAnother };
  log({ step: "d-bi-2", onAnchor, onAnother });

  // ---- D-BI-1: the click that changes nothing ----------------------------
  //
  // Far below the last line.  The first one moves the caret (it is clamped to
  // the end of the document); the SECOND is the one finding 052's residual is
  // about -- nothing moves, core emits nothing, and the old path waited out
  // thirty seconds because no signal it looked at could ever arrive.
  const outsideY = 15500;
  const outsideFirst = await placeCaret(engine, handle, 2000, outsideY);
  const outsideSecond = await placeCaret(engine, handle, 2000, outsideY);
  const outsideThird = await placeCaret(engine, handle, 2000, outsideY);
  metrics.cells["d-bi-1-outside-twice"] = {
    outsideFirst, outsideSecond, outsideThird,
  };
  log({ step: "d-bi-1", outsideFirst, outsideSecond, outsideThird });

  // ---- D-BI-3: the barrier, on the cell finding 046 was measured on -------
  //
  // Control first, and it is the half that matters most: the fix compares the
  // dispatch paragraph against the readback paragraph, and if the comparison
  // were taken over the paragraph's whole a11y text it would differ on every
  // SUCCESSFUL list action -- the false positive that would make the fix worse
  // than the defect.  So a normal paragraph must still come back verified.
  const control = await (async () => {
    await placeCaret(engine, handle, 2000, anchorY ?? 1430);
    try {
      const result = await engine._request("editorActionV2", {
        documentHandle: handle.handle,
        expectedRevision: await currentRevision(engine, handle, stepTimeoutMs),
        action: "set-list-unordered", extendSelection: false, enabled: false,
      }, { timeoutMs: stepTimeoutMs });
      return { ok: true, completion: result?.completion ?? null,
               formatBarrier: result?.formatBarrier ?? null };
    } catch (error) {
      return { ok: false, code: error?.code ?? null,
               message: String(error?.message ?? error),
               formatBarrier: error?.details?.formatBarrier
                 ?? error?.formatBarrier ?? null };
    }
  })();
  metrics.cells["d-bi-3-control"] = control;
  log({ step: "d-bi-3-control", control });

  // Then the empty paragraph: break a line at its end, which leaves the caret
  // in a new empty one, and list THAT.
  const empty = await (async () => {
    await placeCaret(engine, handle, 9000, anchorY ?? 1430);
    try {
      await engine._request("editorActionV2", {
        documentHandle: handle.handle,
        expectedRevision: await currentRevision(engine, handle, stepTimeoutMs),
        action: "insert-paragraph-break", extendSelection: false,
        enabled: false,
      }, { timeoutMs: stepTimeoutMs });
    } catch (error) {
      return { reached: false, code: error?.code ?? null };
    }
    try {
      const result = await engine._request("editorActionV2", {
        documentHandle: handle.handle,
        expectedRevision: await currentRevision(engine, handle, stepTimeoutMs),
        action: "set-list-unordered", extendSelection: false, enabled: false,
      }, { timeoutMs: stepTimeoutMs });
      return { reached: true, ok: true, completion: result?.completion ?? null,
               formatBarrier: result?.formatBarrier ?? null };
    } catch (error) {
      return { reached: true, ok: false, code: error?.code ?? null,
               message: String(error?.message ?? error),
               formatBarrier: error?.details?.formatBarrier
                 ?? error?.formatBarrier ?? null };
    }
  })();
  metrics.cells["d-bi-3-empty-paragraph"] = empty;
  log({ step: "d-bi-3-empty", empty });

  await handle.close({ timeoutMs: stepTimeoutMs }).catch(() => {});
  engine.dispose();
  metrics.complete = true;
  log({ step: "complete" });
}

main().catch((error) => {
  metrics.error = String(error?.stack || error);
  metrics.complete = true;
  log({ step: "error", error: metrics.error });
});
