// What wedges a search on a reused engine?  (Relink queue item
// `queue-search-after-reopen-wedges`.)
//
// D4's heap follow-up recorded, without registering it as a prediction: on ONE
// engine, cycle 1 (open, search, click, insertText, save, close) succeeds and
// cycle 2's search times out at 30 s, after which every later search returns
// BUSY.  Both browsers, identically.  The same loop with no search runs 8/8, so
// a search is involved -- but three candidates were never separated: a second
// search at all, the reopen between them, and the click/insert/save cycle 1
// does after its search.
//
// Four arms, one variable at a time.  Criteria:
// findings/evidence/sdk-e2/e2-c-validation/search-wedge/PREDICTION.md
//
// SDK level and declared as such: the product session disposes its engine on
// close, so "one engine across opens" is not something the product does.  This
// characterises an SDK behaviour; it is not a claim about the product.

import { createDocumentEngine } from "./sdk/document-sdk.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const searchTimeoutMs = Number(params.get("searchTimeout") || 30000);
const openTimeoutMs = Number(params.get("openTimeout") || 180000);

const FIXTURE = { dir: "e2-fixtures", name: "d1-anchors.odt" };
const ANCHOR = "E2-D1-BODY-TARGET";

const ARMS = ["two-searches-one-open", "search-close-open-search",
              "full-cycle-then-search", "no-search-then-search"];
const arm = ARMS.includes(params.get("arm")) ? params.get("arm") : ARMS[0];

const metrics = {
  schemaVersion: 1,
  release: "e2-c-search-wedge",
  profile,
  arm,
  browser: navigator.userAgent,
  fixture: FIXTURE.name,
  searchTimeoutMs,
  inventory: null,
  steps: [],
  verdict: null,
  complete: false,
  error: null,
};
globalThis.__search_wedge = metrics;
globalThis.__probe_metrics = metrics;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };

function publicError(error) {
  return { code: error?.code || error?.name || "ERROR",
           message: String(error?.message || error).slice(0, 300) };
}

async function fixtureBytes() {
  const response = await fetch(`./${FIXTURE.dir}/${FIXTURE.name}`,
                              { cache: "no-cache" });
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  return response.arrayBuffer();
}

function firstRectangle(found) {
  const values = (found.selections?.[0]?.rectangles || "")
    .split(";")[0].split(",").map((v) => Number.parseInt(v.trim(), 10));
  if (values.length !== 4 || values.some((v) => !Number.isFinite(v)))
    throw Object.assign(new Error("search returned no usable rectangle"),
                        { code: "ANCHOR_RECTANGLE_UNUSABLE" });
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

/** Every step is timed and recorded whether it returns or throws.
 *
 *  A step that times out has to be distinguishable from a step that failed
 *  fast, because "hangs for the full 30 s" and "returns an error" are different
 *  answers to this page's question -- and the recorded rounds only ever saw the
 *  first. */
async function step(name, operation) {
  const started = performance.now();
  const entry = { step: name, startedAtMs: Math.round(started) };
  try {
    entry.result = await operation();
    entry.outcome = "returned";
  } catch (error) {
    entry.outcome = "threw";
    entry.error = publicError(error);
  }
  entry.tookMs = Math.round(performance.now() - started);
  // The recorded wedge is a timeout at the search's own timeoutMs, so a step
  // that took approximately that long and threw is called out by name rather
  // than left for a reader to notice in a number.
  entry.wedged = entry.outcome === "threw"
    && entry.tookMs >= searchTimeoutMs * 0.9;
  metrics.steps.push(entry);
  log(entry);
  return entry;
}

const searchOn = (handle) => step("search", async () => {
  const found = await handle.search(ANCHOR, { timeoutMs: searchTimeoutMs });
  return { rectangle: firstRectangle(found) };
});

// `engine.open` transfers the buffer, so each open needs its own copy.
let cachedBytes = null;
const fixtureCopy = () => cachedBytes.slice(0);

async function openOn(engine) {
  const entry = await step("open", () => engine.open(fixtureCopy(), {
    name: FIXTURE.name, timeoutMs: openTimeoutMs }));
  return entry.outcome === "returned" ? entry.result : null;
}

async function editAndSave(handle) {
  await step("insertText", () => handle.insertText("H"));
  await step("save", async () => {
    const saved = await handle.save({ format: "odt" },
                                    { timeoutMs: openTimeoutMs });
    return { bytes: saved?.byteLength ?? saved?.length ?? null };
  });
}

void (async () => {
  try {
    cachedBytes = await fixtureBytes();
    const engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`,
      timeoutMs: openTimeoutMs,
    });
    const contract = engine.manifest?.editorContract || {};
    metrics.inventory = {
      profile: engine.manifest?.profile, abiVersion: contract.abiVersion,
      wasmSha256: contract.wasmSha256, loaderSha256: contract.loaderSha256,
      workerSha256: contract.workerSha256,
    };
    log({ arm, inventory: metrics.inventory });

    // ONE engine for every arm.  That is the variable the recorded wedge was
    // seen under, and it is held fixed here so the four arms differ only in
    // what is done to it.
    let handle = await openOn(engine);
    if (!handle) throw new Error("the first open failed");

    if (arm === "two-searches-one-open") {
      await searchOn(handle);
      await searchOn(handle);            // no close, no reopen
    } else if (arm === "search-close-open-search") {
      await searchOn(handle);
      await step("close", () => handle.close());
      handle = await openOn(engine);
      if (handle) await searchOn(handle);
    } else if (arm === "full-cycle-then-search") {
      const found = await searchOn(handle);
      if (found.outcome === "returned") {
        const rectangle = found.result.rectangle;
        await step("click", () => handle.click(
          rectangle.x + Math.max(1, Math.floor(rectangle.width / 2)),
          rectangle.y + Math.max(1, Math.floor(rectangle.height / 2))));
      }
      await editAndSave(handle);
      await step("close", () => handle.close());
      handle = await openOn(engine);
      if (handle) await searchOn(handle);
    } else if (arm === "no-search-then-search") {
      await editAndSave(handle);
      await step("close", () => handle.close());
      handle = await openOn(engine);
      if (handle) await searchOn(handle);
    }

    const searches = metrics.steps.filter((entry) => entry.step === "search");
    metrics.verdict = {
      searches: searches.length,
      // "The LAST search" is the one every arm is built to ask about.
      lastSearchOutcome: searches.at(-1)?.outcome ?? null,
      lastSearchTookMs: searches.at(-1)?.tookMs ?? null,
      lastSearchWedged: searches.at(-1)?.wedged ?? null,
    };
    await handle?.close().catch(() => {});
    engine.dispose();
    metrics.complete = true;
    log({ complete: true, verdict: metrics.verdict });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  }
})();
