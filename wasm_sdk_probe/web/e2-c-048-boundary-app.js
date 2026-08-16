// Finding 048: which side of the worker boundary the 22 ms is on.
//
// The shipped worker cannot be instrumented -- it is one of the hashes the
// verdict binds -- and it does not need to be.  A click already produces two
// observable moments in the page:
//
//   t0            the page calls handle.click()
//   tResponse     the click's promise resolves      <- transport + the
//                                                      synchronous post
//   tInvalidated  document-invalidated arrives      <- core plus the
//                                                      Emscripten main loop
//
// plus a calibration, `getState`, which crosses the same boundary both ways and
// asks for a value the engine already holds: the transport floor, measured
// rather than assumed.
//
// SDK level, declared: the product's placeCaret sits on top of handle.click and
// waits for the caret (048's fix).  Waiting is the thing being taken apart, so
// this drives the layer underneath.
//
// Criteria: findings/evidence/048/boundary/PREDICTION.md

import { createDocumentEngine } from "./sdk/document-sdk.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const clicks = Number(params.get("clicks") || 10);
const calibrations = Number(params.get("calibrations") || 20);
const stepTimeoutMs = Number(params.get("stepTimeout") || 60000);

const FIXTURE = { dir: "e1-fixtures", name: "list-contexts.odt" };
// Two anchors, far apart, so every click moves the caret to a different line.
// A click on the line the caret is already on can produce no cursor callback at
// all -- three native arms did exactly that.
const ANCHORS = ["E1-LC-HEADING", "E1-LC-END"];

const metrics = {
  schemaVersion: 1,
  release: "finding-048-boundary",
  profile,
  browser: navigator.userAgent,
  fixture: FIXTURE.name,
  // Declared: nothing here is the product's gesture.  The product's click waits
  // for the caret; this one does not, because the wait is the subject.
  layer: "document-sdk",
  anchors: {},
  calibration: [],
  clicks: [],
  invalidations: [],
  complete: false,
  error: null,
};
globalThis.__f048_boundary = metrics;
globalThis.__probe_metrics = metrics;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: String(error?.message || error).slice(0, 300),
});
const now = () => performance.now();

async function fixtureBytes() {
  const response = await fetch(`./${FIXTURE.dir}/${FIXTURE.name}`,
                               { cache: "no-cache" });
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  return response.arrayBuffer();
}

function rectangleOf(found) {
  const values = (found?.selections?.[0]?.rectangles || "")
    .split(";")[0].split(",").map((v) => Number.parseInt(v.trim(), 10));
  if (values.length !== 4 || values.some((v) => !Number.isFinite(v))) return null;
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

void (async () => {
  let engine = null;
  try {
    engine = await createDocumentEngine({
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

    // Every invalidation, whole and stamped on arrival.  The worker forwards
    // LOK callback ids 0 and 1 unconditionally -- no debug mode, no diagnostic
    // profile -- which is why this measurement needs nothing changed.
    engine.onEvent((event) => {
      if (event?.event !== "document-invalidated") return;
      metrics.invalidations.push({
        atMs: now(), revision: event.revision ?? null,
      });
    });

    const handle = await engine.open(await fixtureBytes(),
                                     { name: FIXTURE.name,
                                       timeoutMs: stepTimeoutMs });

    for (const anchor of ANCHORS) {
      const rectangle = rectangleOf(
        await handle.search(anchor, { timeoutMs: stepTimeoutMs }));
      if (!rectangle)
        throw Object.assign(new Error(`anchor not found: ${anchor}`),
                            { code: "ANCHOR_NOT_FOUND" });
      metrics.anchors[anchor] = rectangle;
    }
    log({ anchors: metrics.anchors });

    // ---- the transport floor ---------------------------------------------
    // getState crosses the boundary both ways and asks the engine for a value
    // it already holds.  Taken BEFORE the clicks and again after, because a
    // floor measured only while the engine is idle is a floor measured under
    // conditions the clicks do not run in.
    async function calibrate(phase) {
      for (let index = 0; index < calibrations; index += 1) {
        const started = now();
        await engine._request("editorGetStateV2",
                              { documentHandle: handle.handle },
                              { timeoutMs: stepTimeoutMs });
        metrics.calibration.push({ phase, index,
                                   roundTripMs: now() - started });
      }
    }
    await calibrate("before");

    // ---- the clicks -------------------------------------------------------
    for (let index = 0; index < clicks; index += 1) {
      const anchor = ANCHORS[index % ANCHORS.length];
      const rectangle = metrics.anchors[anchor];
      const x = rectangle.x + Math.max(1, Math.floor(rectangle.width / 2));
      const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
      const seen = metrics.invalidations.length;
      const t0 = now();
      await handle.click(x, y, { timeoutMs: stepTimeoutMs });
      const tResponse = now();
      // Wait for the cursor invalidation the click should produce, bounded.
      const deadline = t0 + 5000;
      while (metrics.invalidations.length === seen && now() < deadline)
        await new Promise((resolve) => setTimeout(resolve, 1));
      const arrived = metrics.invalidations.length > seen
        ? metrics.invalidations[seen] : null;
      // Where the caret ended up, so a click that did not land can be excluded
      // rather than averaged in.
      const state = await engine._request("editorGetStateV2",
                                          { documentHandle: handle.handle },
                                          { timeoutMs: stepTimeoutMs })
        .catch(() => null);
      metrics.clicks.push({
        index, anchor, x, y,
        askedY: y,
        caretY: state?.caret?.y ?? null,
        caretHeight: state?.caret?.height ?? null,
        transportMs: tResponse - t0,
        invalidatedAfterMs: arrived ? arrived.atMs - t0 : null,
        engineSideMs: arrived ? arrived.atMs - tResponse : null,
        invalidations: metrics.invalidations.length - seen,
      });
      log(metrics.clicks.at(-1));
    }

    await calibrate("after");
    await handle.close({ timeoutMs: stepTimeoutMs }).catch(() => {});
    metrics.complete = true;
    log({ complete: true, clicks: metrics.clicks.length });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  } finally {
    engine?.dispose();
  }
})();
