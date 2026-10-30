// SPEC-M3-v27-finding-176 (U1): finding 176's shell item -- what the page's run() writes into the status strip
// (`#s-latency`, the visible 「上次操作」, e2-editor.html:365) when an action ends in each disposition.
//
// Owner, host 0.2.42, hand test (a): a bullet on an empty line worked, the toast said "dispatched, cannot be
// verified separately, look at the result ... not a document fault" -- and the strip under it said
// `• 項目符號 失敗`, because run() wrote `${label} 失敗` before it looked at the disposition and the `review`
// branch never wrote it again (S2 run-02: all 48 records).  A `review` is not a failure by the page's own
// comment; the fable ruling of 2026-10-30 §3.2: write something true there instead.  Every other disposition is
// unchanged: success shows the time, view-only says 唯讀, rollback / restart / none say 失敗.
//
// Same cut as page-review-presentation.test.mjs (U3 of SPEC-M3-select-all-v26), with the strip read back.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { EMPTY_SELECTION_SHAPES } from "../paragraph-editor-client.js";

const PAGE = readFileSync(fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url)), "utf8");

function slice(pattern, what) {
  const match = PAGE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const fn = (name) => slice(new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`);

const LABEL = "• 項目符號";
const REVIEW_STRIP = `${LABEL}：待確認`;

async function stripAfter(operation) {
  const el = { s: { latency: { textContent: "" } } };
  const session = { restartAvailable: () => true };
  const realWarn = console.warn;
  console.warn = () => {};
  try {
    // eslint-disable-next-line no-new-func
    const run = new Function("el", "session", "toast", "reopenAfterBoundaryRefusal", "renderDocument",
                             "publishWindow", "describeError", "VIEW_ONLY_TEXT", "EMPTY_SELECTION_SHAPES", `
      let changes = 0;
      ${fn("deleteUnverified")}
      ${fn("reopensAfterRefusal")}
      ${fn("run")}
      return run;`)(
      el, session, () => {}, () => {}, async () => {}, () => {},
      (e) => `${e?.code ? `${e.code}：` : ""}${e?.message || String(e)}`, "唯讀", EMPTY_SELECTION_SHAPES);
    try {
      await run(LABEL, operation);
    } catch {
      // the rejection itself is U3's subject; this test reads the strip
    }
  } finally {
    console.warn = realWarn;
  }
  return el.s.latency.textContent;
}

const failing = (fields) => () => Promise.reject(Object.assign(new Error("engine message"), fields));
const review = (failureShape, code = "MUTATION_OUTCOME_UNKNOWN") => failing({
  code, recovery: "review",
  details: { formatBarrier: { dispatched: true, route: "collapsed", failureShape, selectionResultSeen: true } },
});

for (const [name, operation] of [
  ["083/173 empty paragraph", review("select-text-returned-none")],
  ["046 several paragraphs", review("multi-block-readback")],
  ["059 core reply", review("select-text-returned-none", "LOK_COMMAND_FAILED")],
]) {
  test(`U1: review (${name}) -- the strip says ${REVIEW_STRIP}, not 失敗`, async () => {
    const strip = await stripAfter(operation);
    assert.ok(!strip.includes("失敗"), `the strip still says failed: ${strip}`);
    assert.equal(strip, REVIEW_STRIP);
  });
}

for (const [name, operation] of [
  ["rollback", failing({ code: "MUTATION_OUTCOME_UNKNOWN", recovery: "rollback" })],
  ["restart", failing({ code: "WORKER_CRASHED", recovery: "restart" })],
  ["no disposition", failing({ code: "STALE_REVISION", recovery: "none" })],
]) {
  test(`U1: ${name} is unchanged -- the strip says 失敗`, async () => {
    assert.equal(await stripAfter(operation), `${LABEL} 失敗`);
  });
}

test("U1: view-only is unchanged -- the strip says 唯讀", async () => {
  assert.equal(await stripAfter(failing({ code: "EDITOR_VIEW_ONLY" })), `${LABEL}：唯讀`);
});

test("U1: success is unchanged -- the strip shows the time", async () => {
  assert.match(await stripAfter(async () => ({ ok: true })), /^• 項目符號 \d+ ms$/);
});
