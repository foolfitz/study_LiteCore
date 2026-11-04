// SPEC-M3-link-batch §4.3, §10.8, §10.10 Q-A, §12.3 (task 2026-10-13l, part 2):
// the page number the page draws from `handle.pageRectangles()`.
//
// Three pure functions and one clock-free scheduler live in the session
// module, so that N, L, M and "when the page asks the engine" are decided by
// code node can run, and the page only wires them to the DOM.  The page's own
// `updatePageStatus()` is taken from its source and run against a model
// element, so "fifty recomputes cost zero engine calls" is asserted on the
// page's code, not on a copy of it.
//
// Nothing here has run in a browser: no engine answers `page-rectangles` until
// the v20 link.  These are the node half; the v20 shakedown is the other.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import {
  NarrowEditorV2Session, PageRectanglesScheduler, pageSpanOf, pageStatusText, visibleRegionTwips,
} from "../narrow-editor-v2-session.js";
import { parsePageRectangles } from "../../sdk/document-sdk.js";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const PAGE = readFileSync(here("../../web/e2-editor-app.js"), "utf8");
const HTML = readFileSync(here("../../web/e2-editor.html"), "utf8");

// A4 portrait pages the way core lays them out (findings/evidence/link-batch/
// page-rectangles/README.md): DOCUMENTBORDER 284 on every side, a 284 gap
// between pages, 11906 x 16838 each.
const A4 = (index, x = 284) => ({ x, y: 284 + index * (16838 + 284), width: 11906, height: 16838 });
const pages = (n) => Array.from({ length: n }, (_, i) => A4(i));
const region = (y, height, x = 0, width = 12474) => ({ x, y, width, height });

/* --------------------------------------------------------------- pageSpanOf */

test("span: one page -- a region inside page 1 of 3", () => {
  assert.deepEqual(pageSpanOf(pages(3), region(1000, 5000)), { first: 1, last: 1, count: 3 });
});

test("span: two pages -- a region across the gap between pages 1 and 2", () => {
  // Page 1 ends at 284 + 16838 = 17122; page 2 starts at 17406.
  assert.deepEqual(pageSpanOf(pages(3), region(16000, 3000)), { first: 1, last: 2, count: 3 });
});

test("span: touching an edge is not crossing it -- strict on both ends", () => {
  // The region's bottom lands exactly on page 2's top (17406): page 2 is not visible.
  assert.deepEqual(pageSpanOf(pages(3), region(10000, 7406)), { first: 1, last: 1, count: 3 });
  // The region's top lands exactly on page 1's bottom (17122): page 1 is not visible.
  assert.deepEqual(pageSpanOf(pages(3), region(17122, 1000)), { first: 2, last: 2, count: 3 });
  // One twip past each edge, and both count.
  assert.deepEqual(pageSpanOf(pages(3), region(10000, 7407)), { first: 1, last: 2, count: 3 });
  assert.deepEqual(pageSpanOf(pages(3), region(17121, 1000)), { first: 1, last: 2, count: 3 });
});

test("span: mixed portrait and landscape pages with different x", () => {
  // Page 2 is landscape and, as core would place it, starts at the same left
  // border but is wider and shorter; page 3 is portrait again, lower down.
  const mixed = [
    { x: 284, y: 284, width: 11906, height: 16838 },
    { x: 284, y: 17406, width: 16838, height: 11906 },
    { x: 284, y: 29596, width: 11906, height: 16838 },
  ];
  // The page measures the full document width, so x never excludes a page.
  assert.deepEqual(pageSpanOf(mixed, region(17000, 13000, 0, 17406)), { first: 1, last: 3, count: 3 });
  assert.deepEqual(pageSpanOf(mixed, region(18000, 5000, 0, 17406)), { first: 2, last: 2, count: 3 });
  // And the x axis is tested, not assumed: a region to the right of the
  // portrait pages' right edge (284 + 11906 = 12190) sees only the landscape one.
  assert.deepEqual(pageSpanOf(mixed, region(0, 60000, 12190, 5000)), { first: 2, last: 2, count: 3 });
  assert.equal(pageSpanOf(mixed, region(0, 60000, 17122, 5000)), null, "past every page's right edge");
});

test("span: no intersection is null, not a guess", () => {
  // Inside the gap between pages 1 and 2 (17122..17406), narrower than it.
  assert.equal(pageSpanOf(pages(3), region(17200, 100)), null);
  assert.equal(pageSpanOf(pages(3), region(0, 0)), null, "an empty region sees nothing");
  assert.equal(pageSpanOf(pages(3), region(-5000, 4000)), null, "above the first page");
  assert.equal(pageSpanOf(pages(3), region(1e9, 4000)), null, "below the last page");
});

test("span: string order is the page order, even when a later y is smaller", () => {
  // Core emits pages in page order; this function must never sort.  A list
  // whose third rectangle sits ABOVE the second still answers by position.
  const unsorted = [A4(0), A4(5), A4(1)];
  assert.deepEqual(pageSpanOf(unsorted, region(A4(1).y + 100, 100)), { first: 3, last: 3, count: 3 });
  assert.deepEqual(pageSpanOf(unsorted, region(A4(5).y + 100, 100)), { first: 2, last: 2, count: 3 });
  // A region that sees rectangles 2 and 3 (positions, not heights) spans 2..3.
  assert.deepEqual(pageSpanOf(unsorted, region(A4(1).y + 100, A4(5).y - A4(1).y)), { first: 2, last: 3, count: 3 });
});

test("span: never inferred from equal page heights -- a short page is still one page", () => {
  const list = [A4(0), { x: 284, y: 17406, width: 11906, height: 2000 }, { x: 284, y: 19690, width: 11906, height: 16838 }];
  assert.deepEqual(pageSpanOf(list, region(17500, 100)), { first: 2, last: 2, count: 3 });
  assert.deepEqual(pageSpanOf(list, region(19700, 100)), { first: 3, last: 3, count: 3 });
});

test("span: the function is total -- garbage in, null out", () => {
  assert.equal(pageSpanOf([], region(0, 100)), null);
  assert.equal(pageSpanOf(null, region(0, 100)), null);
  assert.equal(pageSpanOf(undefined, region(0, 100)), null);
  assert.equal(pageSpanOf("284, 284, 11906, 16838", region(0, 100)), null);
  assert.equal(pageSpanOf(pages(2), null), null);
  assert.equal(pageSpanOf(pages(2), undefined), null);
  assert.equal(pageSpanOf(pages(2), { x: 0, y: NaN, width: 1, height: 1 }), null);
  assert.deepEqual(pageSpanOf([null, A4(0)], region(300, 100)), { first: 2, last: 2, count: 2 },
                   "a malformed entry is skipped for N and L; the real page keeps its position and M counts both");
  assert.deepEqual(pageSpanOf([A4(0), null], region(300, 100)), { first: 1, last: 1, count: 2 },
                   "a malformed entry later in the list still counts in M");
  assert.equal(pageSpanOf([null, null], region(300, 100)), null, "no page at all is null");
});

test("span: 60 pages of the native shape, from the evidence file through the SDK parser", () => {
  // findings/evidence/link-batch/page-rectangles/round-20261012T030439Z/long60-r1.jsonl:
  // the first timed `getPartPageRectangles()` string of the 60-page document,
  // verbatim, parsed by the same function the handle uses.
  const lines = readFileSync(here("../../../findings/evidence/link-batch/page-rectangles/"
                                  + "round-20261012T030439Z/long60-r1.jsonl"), "utf8")
    .split("\n").filter(Boolean).map((line) => JSON.parse(line));
  const record = lines.find((entry) => entry.rec === "rects" && entry.phase === "timed" && entry.index === 0);
  assert.ok(record, "the evidence file has no timed rectangles record");
  const rectangles = parsePageRectangles(record.raw, 60);
  assert.equal(rectangles.length, 60);
  // The document is 12474 x 1027604 twips (README: getDocumentSize).
  const widthTwips = 12474;
  assert.deepEqual(pageSpanOf(rectangles, region(0, 20000, 0, widthTwips)), { first: 1, last: 2, count: 60 });
  assert.deepEqual(pageSpanOf(rectangles, region(1000, 10000, 0, widthTwips)), { first: 1, last: 1, count: 60 });
  // The middle of page 30: y = 284 + 29 * 17122 = 496822.
  assert.deepEqual(pageSpanOf(rectangles, region(496822 + 8000, 100, 0, widthTwips)), { first: 30, last: 30, count: 60 });
  // The last page: y = 1010482 (README, the last rectangle verbatim).
  assert.deepEqual(pageSpanOf(rectangles, region(1010482 + 100, 30000, 0, widthTwips)), { first: 60, last: 60, count: 60 });
  // A view 2.5 pages tall from the top of page 10 spans 10..12.
  assert.deepEqual(pageSpanOf(rectangles, region(284 + 9 * 17122, 42805, 0, widthTwips)), { first: 10, last: 12, count: 60 });
  // The whole document.
  assert.deepEqual(pageSpanOf(rectangles, region(0, 1027604, 0, widthTwips)), { first: 1, last: 60, count: 60 });
});

/* ------------------------------------------------------------ pageStatusText */

test("text: one page and a span, in the owner's wording with an en dash", () => {
  assert.equal(pageStatusText({ first: 3, last: 3, count: 18 }), "第 3 頁，共 18 頁");
  assert.equal(pageStatusText({ first: 3, last: 4, count: 18 }), "第 3–4 頁，共 18 頁");
  assert.equal(pageStatusText({ first: 1, last: 60, count: 60 }), "第 1–60 頁，共 60 頁");
  assert.equal(pageStatusText({ first: 1, last: 1, count: 1 }), "第 1 頁，共 1 頁");
});

test("text: null for anything that is not a span", () => {
  assert.equal(pageStatusText(null), null);
  assert.equal(pageStatusText(undefined), null);
  assert.equal(pageStatusText({}), null);
  assert.equal(pageStatusText({ first: 1.5, last: 2, count: 3 }), null);
  assert.equal(pageStatusText({ first: "1", last: 2, count: 3 }), null);
});

/* --------------------------------------------------------- visibleRegionTwips */

test("region: device rows of #paper scaled by heightTwips / docRows, at the full document width", () => {
  // 1000 rows for a 1027604-twip document: 1027.604 twips per row.
  const near = (actual, expected, what) =>
    assert.ok(Math.abs(actual - expected) < 1e-6, `${what}: ${actual} is not ${expected}`);
  const r = visibleRegionTwips(100, 350, 1000, 12474, 1027604);
  assert.equal(r.x, 0);
  assert.equal(r.width, 12474, "the full document width");
  near(r.y, 102760.4, "y");
  near(r.height, 250 * 1027.604, "height");
  const whole = visibleRegionTwips(0, 1000, 1000, 12474, 1027604);
  near(whole.y, 0, "y");
  near(whole.height, 1027604, "height");
});

test("region: null when there is nothing to scale by or nothing visible", () => {
  assert.equal(visibleRegionTwips(0, 100, 0, 12474, 1027604), null, "no rows");
  assert.equal(visibleRegionTwips(100, 100, 1000, 12474, 1027604), null, "empty view");
  assert.equal(visibleRegionTwips(200, 100, 1000, 12474, 1027604), null, "inverted view");
  assert.equal(visibleRegionTwips(0, 100, 1000, 0, 1027604), null, "no width");
  assert.equal(visibleRegionTwips(0, 100, 1000, 12474, undefined), null, "no height");
  assert.equal(visibleRegionTwips(NaN, 100, 1000, 12474, 1027604), null);
});

/* ---------------------------------------------------- PageRectanglesScheduler */

/** A scheduler whose reads the test resolves by hand. */
function scheduled({ offered = true } = {}) {
  const pending = [];
  const results = [];
  const scheduler = new PageRectanglesScheduler({
    offered: () => offered,
    read: (key) => new Promise((resolve, reject) => pending.push({ key, resolve, reject })),
    onResult: (key, result, error) => results.push({ key, result, error }),
  });
  const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
  return { scheduler, pending, results, settle };
}
const state = (documentSizeChangedCount, documentChangeSequence = 0) =>
  ({ documentSizeChangedCount, documentChangeSequence, caret: null });
const ANSWER = { rectangles: pages(3), parts: 3 };

test("scheduler: open -> exactly one read", async () => {
  const { scheduler, pending, results, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(0));
  assert.equal(pending.length, 1);
  assert.equal(pending[0].key, "doc-1");
  pending[0].resolve(ANSWER);
  await settle();
  assert.equal(scheduler.reads, 1);
  assert.deepEqual(results, [{ key: "doc-1", result: ANSWER, error: null }]);
});

test("scheduler: a counter change -> one read; the same counter again -> none", async () => {
  const { scheduler, pending, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(0));
  pending.shift().resolve(ANSWER);
  await settle();
  scheduler.stateObserved("doc-1", state(1));
  assert.equal(pending.length, 1, "the counter moved and nothing was asked");
  pending.shift().resolve(ANSWER);
  await settle();
  for (let i = 0; i < 20; i += 1) scheduler.stateObserved("doc-1", state(1, i));
  assert.equal(pending.length, 0);
  assert.equal(scheduler.reads, 2);
});

test("scheduler: documentChangeSequence alone is never a trigger (typing sends no INVALIDATE_TILES)", async () => {
  const { scheduler, pending, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(0, 0));
  pending.shift().resolve(ANSWER);
  await settle();
  for (let seq = 1; seq <= 50; seq += 1) scheduler.stateObserved("doc-1", state(0, seq));
  assert.equal(pending.length, 0);
  assert.equal(scheduler.reads, 1);
});

test("scheduler: a state without the counter is not a trigger either", async () => {
  const { scheduler, pending, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(2));
  pending.shift().resolve(ANSWER);
  await settle();
  scheduler.stateObserved("doc-1", { caret: null });
  scheduler.stateObserved("doc-1", state(null));
  scheduler.stateObserved("doc-1", state(undefined));
  scheduler.stateObserved("doc-1", null);
  assert.equal(pending.length, 0);
  // And once the counter is seen again at its old value, still nothing.
  scheduler.stateObserved("doc-1", state(2));
  assert.equal(pending.length, 0);
});

test("scheduler: three triggers during one in-flight read -> exactly one more read after it", async () => {
  const { scheduler, pending, results, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(0));
  assert.equal(pending.length, 1);
  scheduler.stateObserved("doc-1", state(1));
  scheduler.sizeChangeReported("doc-1");
  scheduler.stateObserved("doc-1", state(2));
  assert.equal(pending.length, 1, "a second read was issued while one was in flight");
  pending.shift().resolve(ANSWER);
  await settle();
  assert.equal(pending.length, 1, "the coalesced follow-up was not issued");
  assert.equal(results.length, 1, "the first read's answer was not delivered");
  pending.shift().resolve(ANSWER);
  await settle();
  assert.equal(pending.length, 0);
  assert.equal(scheduler.reads, 2);
  // The follow-up carried the latest counter: seeing 2 again asks nothing.
  scheduler.stateObserved("doc-1", state(2));
  assert.equal(pending.length, 0);
});

test("scheduler: a paint reply's documentSizeChanged -> one read, coalesced like the rest", async () => {
  const { scheduler, pending, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(0));
  pending.shift().resolve(ANSWER);
  await settle();
  scheduler.sizeChangeReported("doc-1");
  assert.equal(pending.length, 1);
  scheduler.sizeChangeReported("doc-1");
  scheduler.sizeChangeReported("doc-1");
  assert.equal(pending.length, 1);
  pending.shift().resolve(ANSWER);
  await settle();
  assert.equal(pending.length, 1, "two reports during the read collapse to one follow-up");
  pending.shift().resolve(ANSWER);
  await settle();
  assert.equal(scheduler.reads, 3);
  scheduler.sizeChangeReported("some-other-document");
  assert.equal(pending.length, 0, "a report for a document that is not current is ignored");
});

test("scheduler: a new document whose counter is back at 0 -> one read, keyed on the document", async () => {
  const { scheduler, pending, results, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(0));
  pending.shift().resolve(ANSWER);
  await settle();
  scheduler.stateObserved("doc-1", state(0));
  assert.equal(pending.length, 0);
  // A worker restart: a fresh engine, a fresh handle, the counter at 0 again.
  scheduler.documentOpened("doc-2", state(0));
  assert.equal(pending.length, 1);
  assert.equal(pending[0].key, "doc-2");
  pending.shift().resolve(ANSWER);
  await settle();
  assert.equal(results.at(-1).key, "doc-2");
  assert.equal(scheduler.reads, 2);
});

test("scheduler: a read that resolves for a document no longer current is dropped", async () => {
  const { scheduler, pending, results, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(0));
  const first = pending.shift();
  scheduler.documentOpened("doc-2", state(0));
  assert.equal(pending.length, 0, "a second read must wait for the first");
  first.resolve(ANSWER);
  await settle();
  assert.equal(results.length, 0, "the stale answer reached the page");
  assert.equal(scheduler.dropped, 1);
  assert.equal(pending.length, 1, "the new document's read did not follow");
  assert.equal(pending[0].key, "doc-2");
  pending.shift().resolve(ANSWER);
  await settle();
  assert.deepEqual(results.map((r) => r.key), ["doc-2"]);
});

test("scheduler: not offered -> zero reads, ever", async () => {
  const { scheduler, pending, results, settle } = scheduled({ offered: false });
  scheduler.documentOpened("doc-1", state(0));
  scheduler.stateObserved("doc-1", state(1));
  scheduler.stateObserved("doc-1", state(2));
  scheduler.sizeChangeReported("doc-1");
  scheduler.documentOpened("doc-2", state(0));
  await settle();
  assert.equal(pending.length, 0);
  assert.equal(scheduler.reads, 0);
  assert.equal(results.length, 0);
});

test("scheduler: a failed read reports null (the line hides) and the next trigger reads again", async () => {
  const { scheduler, pending, results, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(0));
  const failure = Object.assign(new Error("not declared"), { code: "UNSUPPORTED_OPERATION" });
  pending.shift().reject(failure);
  await settle();
  assert.deepEqual(results, [{ key: "doc-1", result: null, error: failure }]);
  assert.equal(scheduler.failures, 1);
  // Ruling 6 Q4 (condition 48): a failure no longer consumes its trigger.
  // This section used to assert the opposite ("same counter again -> no
  // read"); the three tests that follow this one carry the ruled contract.
  // Here: a second write with the same counter while the retry is in flight
  // adds nothing -- one read per state write while it fails, never a storm.
  scheduler.stateObserved("doc-1", state(0));
  scheduler.stateObserved("doc-1", state(0));
  assert.equal(pending.length, 1);
  pending.shift().reject(failure);
  await settle();
  assert.equal(scheduler.failures, 2);
  // The next trigger tries again.
  scheduler.stateObserved("doc-1", state(1));
  assert.equal(pending.length, 1);
  pending.shift().resolve(ANSWER);
  await settle();
  assert.equal(results.at(-1).result, ANSWER);
  // And so does a size report, and a reopen.
  scheduler.sizeChangeReported("doc-1");
  assert.equal(pending.length, 1);
  pending.shift().reject(failure);
  await settle();
  assert.equal(results.at(-1).result, null);
  scheduler.documentOpened("doc-1b", state(0));
  assert.equal(pending.length, 1);
});

// Ruling 6 Q4, condition 48.  Every command is BUSY while a barrier is in
// flight (probe_engine.cpp:6100-6106), so a size-change push during a merge
// issues a read that fails; the drain's state write after the merge carries
// the SAME counter.  Before the fix that write was ignored (the failure had
// recorded the counter as issued) and the line stayed hidden until the next
// counter change, reopen or paint-reported size change.
test("scheduler (48a): a failed read, then a state write with the same counter -> re-reads", async () => {
  const { scheduler, pending, results, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(3));
  assert.equal(scheduler.reads, 1);
  pending.shift().reject(Object.assign(new Error("busy"), { code: "EDITOR_BUSY" }));
  await settle();
  assert.equal(scheduler.failures, 1);
  assert.equal(results.at(-1).result, null);
  // The drain's write after the merge: same document, same counter.
  scheduler.stateObserved("doc-1", state(3));
  assert.equal(pending.length, 1, "a state write after a failed read must re-read");
  assert.equal(scheduler.reads, 2);
  pending.shift().resolve(ANSWER);
  await settle();
  assert.equal(results.at(-1).result, ANSWER, "the retry's answer reaches the page");
});

test("scheduler (48b) control: a successful read, then the same counter -> no re-read", async () => {
  const { scheduler, pending, results, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(3));
  pending.shift().resolve(ANSWER);
  await settle();
  assert.equal(results.at(-1).result, ANSWER);
  for (let i = 0; i < 5; i += 1) scheduler.stateObserved("doc-1", state(3, i));
  assert.equal(pending.length, 0, "an answered counter is not re-read");
  assert.equal(scheduler.reads, 1);
});

test("scheduler (48c): a failed read followed by no state write issues nothing", async () => {
  const { scheduler, pending, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(3));
  pending.shift().reject(Object.assign(new Error("busy"), { code: "EDITOR_BUSY" }));
  await settle();
  await settle();
  assert.equal(scheduler.reads, 1, "a retry is bounded by state writes; none came, none issued");
  assert.equal(pending.length, 0);
  assert.equal(scheduler.failures, 1);
});

test("scheduler: a read that throws synchronously is a failure, not an exception", async () => {
  const results = [];
  const scheduler = new PageRectanglesScheduler({
    read: () => { throw Object.assign(new Error("disposed"), { code: "ENGINE_DISPOSED" }); },
    onResult: (key, result, error) => results.push({ key, result, code: error?.code }),
  });
  scheduler.documentOpened("doc-1", state(0));
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.deepEqual(results, [{ key: "doc-1", result: null, code: "ENGINE_DISPOSED" }]);
  scheduler.stateObserved("doc-1", state(1));
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(scheduler.reads, 2);
});

test("scheduler: closed -> the in-flight answer is dropped and nothing reads again", async () => {
  const { scheduler, pending, results, settle } = scheduled();
  scheduler.documentOpened("doc-1", state(0));
  scheduler.closed();
  scheduler.stateObserved("doc-1", state(5));
  scheduler.sizeChangeReported("doc-1");
  pending.shift().resolve(ANSWER);
  await settle();
  assert.equal(results.length, 0);
  assert.equal(pending.length, 0);
});

/* ------------------------------------- the allowlist: every writer of editorState */

const manifestOf = (profile) => JSON.parse(readFileSync(
  here(`../../dist/profiles/${profile}/sdk-manifest.json`), "utf8"));

/** The v2 fixture of narrow-editor-v2-session.test.mjs, with the engine's listener kept. */
function fixture({ manifest = manifestOf("e2-editor-v2"), stateCounter = 0 } = {}) {
  let listener = null;
  let revision = 0;
  const editorState = (counter = stateCounter) => ({
    documentHandle: 1, revision, sourceSequence: 1, documentChangeSequence: 0,
    documentSizeChangedCount: counter, caret: null,
    selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
    selectionType: "none", selectionTextMissing: false, selectionText: "",
    format: { bold: false, italic: false },
  });
  const document = {
    handle: 1, revision: 0, widthTwips: 12474, heightTwips: 1027604,
    _assertUsable() {},
    async render() { return { pixels: new ArrayBuffer(4), revision }; },
    async save() { return new ArrayBuffer(16); },
    async close() {},
  };
  const engine = {
    manifest,
    onEvent(fn) { listener = fn; return () => { listener = null; }; },
    async open() { revision = 0; document.revision = 0; return document; },
    async _request(operation, payload) {
      if (operation === "editorGetStateV2") return editorState();
      if (operation === "editorSelectRangeV2") return { revision };
      document.revision = ++revision;
      // An action reply's `state`: the worker's `productEditorState` projection.
      return { action: payload.action, beforeRevision: payload.expectedRevision, revision,
               changed: true, completion: "uno-command-result", state: editorState() };
    },
    dispose() {},
  };
  document._engine = engine;
  const session = new NarrowEditorV2Session({
    engineFactory: async () => engine, secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } },
  });
  return { session, document, engine, push: (event) => listener?.(event),
           setCounter: (value) => { stateCounter = value; } };
}

test("writer 1 (open's getState) carries documentSizeChangedCount into snapshot.editorState", async () => {
  const { session } = fixture({ stateCounter: 7 });
  await session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  assert.equal(session.state.snapshot.editorState.documentSizeChangedCount, 7);
});

test("writer 2 (the drain's action reply state) carries documentSizeChangedCount", async () => {
  const { session, setCounter } = fixture({ stateCounter: 1 });
  await session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  assert.equal(session.state.snapshot.editorState.documentSizeChangedCount, 1);
  setCounter(2);
  await session.action("set-bold", { enabled: true });
  assert.equal(session.state.snapshot.editorState.documentSizeChangedCount, 2);
});

test("writer 3 (the engine's editor-state announcement, the subclass allowlist) carries it", async () => {
  const { session, push } = fixture({ stateCounter: 0 });
  await session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  assert.equal(session.state.snapshot.editorState.documentSizeChangedCount, 0);
  push({
    event: "editor-state", documentHandle: 1, revision: 0, source: "document-size-changed",
    sourceSequence: 9, documentChangeSequence: 0, documentSizeChangedCount: 3,
    visible: true, caret: { x: 1, y: 2, width: 0, height: 276 },
    selection: { observed: true, collapsed: true, rectangles: [] }, a11y: null,
    caretParagraph: null, documentOutline: null, format: { bold: false }, schedulerProbe: null,
  });
  const after = session.state.snapshot.editorState;
  assert.equal(after.sourceSequence, 9, "the announcement was not adopted at all");
  assert.equal(after.documentSizeChangedCount, 3,
               "the announcement was adopted but the counter was dropped by the allowlist");
  assert.equal(after.caret.x, 1);
});

test("writer 3: the stale-sequence guard still applies (a counter on an older sequence is dropped)", async () => {
  const { session, push } = fixture({ stateCounter: 0 });
  await session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  push({ event: "editor-state", documentHandle: 1, revision: 0, sourceSequence: 9,
         documentSizeChangedCount: 3, visible: true, caret: null, selection: { collapsed: true } });
  push({ event: "editor-state", documentHandle: 1, revision: 0, sourceSequence: 8,
         documentSizeChangedCount: 4, visible: true, caret: null, selection: { collapsed: true } });
  assert.equal(session.state.snapshot.editorState.documentSizeChangedCount, 3);
});

/* ---------------------------------------------- offersPageRectangles passthrough */

test("session.offersPageRectangles(): false before open, false on v2, true only with the contract field", async () => {
  const plain = fixture();
  assert.equal(plain.session.offersPageRectangles(), false, "before open");
  await plain.session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  assert.equal(plain.session.offersPageRectangles(), false, "the v2 manifest declares nothing");
  const declared = fixture({ manifest: { ...manifestOf("e2-editor-v2"),
    editorContract: { ...manifestOf("e2-editor-v2").editorContract,
                      pageRectangles: "document-sdk-page-rectangles" } } });
  await declared.session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  assert.equal(declared.session.offersPageRectangles(), true);
  const misspelt = fixture({ manifest: { ...manifestOf("e2-editor-v2"),
    editorContract: { ...manifestOf("e2-editor-v2").editorContract, pageRectangles: "yes" } } });
  await misspelt.session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  assert.equal(misspelt.session.offersPageRectangles(), false, "any other value is not the declaration");
});

/* ------------------------------------------------- the page: element and wiring */

function slice(source, pattern, what) {
  const match = source.match(pattern);
  assert.ok(match, `${what} not found`);
  return match[0];
}
const pageFn = (name) => slice(PAGE, new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`);
// The page's laid-out size (host 0.2.56 hand test, item 1): the functions under test map through it.
const LAYOUT = [PAGE.match(/^const RESIZE_TOLERANCE_PX = .*;$/m)[0], PAGE.match(/^let laidOut = null;$/m)[0],
  ...["layoutTwips", "sizeReportMovesLayout"].map((name) =>
    PAGE.match(new RegExp(`^function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"))[0])].join("\n");

test("html: #page-status is its own element after #desk and before .statusbar, hidden, not a live region", () => {
  const element = slice(HTML, /<div id="page-status"[^>]*>/, "#page-status");
  assert.match(element, /\bhidden\b/, "it must start hidden");
  assert.doesNotMatch(element, /aria-live/, "scrolling must not speak (findings 087/088)");
  assert.doesNotMatch(element, /\brole=/, "no role=status either");
  const desk = HTML.indexOf('<div class="desk" id="desk">');
  const statusbar = HTML.indexOf('<div class="statusbar">');
  const status = HTML.indexOf(element);
  assert.ok(desk > 0 && statusbar > 0, "the page's desk and statusbar moved");
  assert.ok(status > desk && status < statusbar, "#page-status must sit between #desk and .statusbar");
  // Not inside .statusbar: the host hides that whole bar (editor.php:51).
  const statusbarEnd = HTML.indexOf("</div>", statusbar);
  assert.ok(!(status > statusbar && status < statusbarEnd));
  // And its rule sets no `display`, or the `hidden` attribute would stop working.
  const rule = slice(HTML, /#page-status \{[^}]*\}/, "the #page-status rule");
  assert.doesNotMatch(rule, /display\s*:/);
});

test("page: pageRectangles() is called in exactly one place, the scheduler's read", () => {
  // Code only: the comments name the call too (product-page-calls' comment rule).
  const code = PAGE.replace(/^\s*\/\/.*$/gm, "");
  const calls = [...code.matchAll(/\.pageRectangles\(/g)];
  assert.equal(calls.length, 1, "the page must ask the engine from one place only");
  const scheduler = slice(PAGE, /^const pageRectangles = new PageRectanglesScheduler\(\{[\s\S]*?\n\}\);$/m,
                          "the page's scheduler");
  assert.match(scheduler, /read: \(document\) => document\.pageRectangles\(/);
  assert.match(scheduler, /offered: \(\) => session\?\.offersPageRectangles\?\.\(\) === true/);
  assert.match(PAGE, /^import \{[^}]*PageRectanglesScheduler[^}]*\}\s*\n?\s*from "\.\/editor-shell-v2\/narrow-editor-v2-session\.js";/m,
               "the scheduler must come from the session module (no new bundled file)");
});

test("page: open and state writes go through notePageRectangles; scroll, layout and a resized paint recompute or re-read", () => {
  assert.match(pageFn("updateState"), /notePageRectangles\(snapshot\);/);
  assert.match(pageFn("onDeskScroll"), /^  updatePageStatus\(\);/m, "scroll must recompute before any early return");
  assert.match(pageFn("layoutCanvas"), /updatePageStatus\(\);/);
  const resized = slice(PAGE, /if \(documentResized\) \{[\s\S]*?\n    \}/, "the documentResized block");
  assert.match(resized, /pageRectangles\.sizeChangeReported\(session\.document\)/);
  // No new listeners: the hooks ride the page's existing scroll and resize paths.
  assert.doesNotMatch(PAGE, /addEventListener\([^)]*updatePageStatus/);
  // The element is never made a live region or given a role from the page either.
  assert.doesNotMatch(PAGE, /el\.pageStatus[^\n]*(aria-live|setAttribute\("role"|\.role\b)/);
});

/** The page's updatePageStatus() against a model element and session. */
function pageStatusModel({ rectangles, top, bottom, docRows = 1000, widthTwips = 12474, heightTwips = 1027604 }) {
  const document = { widthTwips, heightTwips, pageRectanglesCalls: 0,
                     pageRectangles() { this.pageRectanglesCalls += 1; return Promise.resolve(); } };
  const el = { pageStatus: { hidden: true, textContent: "" } };
  const session = { document };
  const pageStatus = { document, rectangles };
  // eslint-disable-next-line no-new-func
  const made = new Function("el", "session", "pageStatus", "docRows", "visibleDocRows",
                            "pageSpanOf", "pageStatusText", "visibleRegionTwips", `
    ${LAYOUT}
    ${pageFn("hidePageStatus")}
    ${pageFn("updatePageStatus")}
    return updatePageStatus;`)(
    el, session, pageStatus, docRows, () => [top, bottom], pageSpanOf, pageStatusText, visibleRegionTwips);
  return { update: made, el, document };
}

test("page: fifty recomputes cost zero engine calls and give the right line", () => {
  const rectangles = pages(60);
  const m = pageStatusModel({ rectangles, top: 0, bottom: 30 });   // 30 rows = 30828 twips: pages 1-2
  for (let i = 0; i < 50; i += 1) m.update();
  assert.equal(m.document.pageRectanglesCalls, 0);
  assert.equal(m.el.pageStatus.hidden, false);
  assert.equal(m.el.pageStatus.textContent, "第 1–2 頁，共 60 頁");
});

test("page: no rectangles yet, or no intersection -> the line is hidden and says nothing", () => {
  const none = pageStatusModel({ rectangles: null, top: 0, bottom: 30 });
  none.el.pageStatus.hidden = false; none.el.pageStatus.textContent = "stale";
  none.update();
  assert.equal(none.el.pageStatus.hidden, true);
  assert.equal(none.el.pageStatus.textContent, "");
  // Rows 16.66..16.94 of 1000 fall in the gap between pages 1 and 2 (17122..17406 twips).
  const gap = pageStatusModel({ rectangles: pages(60), top: 16.7, bottom: 16.9 });
  gap.update();
  assert.equal(gap.el.pageStatus.hidden, true);
  const noRows = pageStatusModel({ rectangles: pages(60), top: 0, bottom: 30, docRows: 0 });
  noRows.update();
  assert.equal(noRows.el.pageStatus.hidden, true);
});

test("page: the line follows the view -- the same rectangles, a different scroll, a different page", () => {
  const rectangles = pages(60);
  // Row 496.822 is the top of page 30 (496822 twips at 1000 twips per row... 1027.604 per row).
  const row = (twips) => twips / 1027.604;
  const a = pageStatusModel({ rectangles, top: row(496822 + 2000), bottom: row(496822 + 6000) });
  a.update();
  assert.equal(a.el.pageStatus.textContent, "第 30 頁，共 60 頁");
  const b = pageStatusModel({ rectangles, top: row(1010482 + 100), bottom: row(1027604) });
  b.update();
  assert.equal(b.el.pageStatus.textContent, "第 60 頁，共 60 頁");
});
