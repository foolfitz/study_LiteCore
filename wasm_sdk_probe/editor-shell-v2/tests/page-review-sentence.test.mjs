// SPEC-M3-shell-v79-finding-173 5.2 (U2): which sentence the page's run() says for a `review` disposition.
//
// Finding 173.  The disposition half (paragraph-editor-client.js) keeps the queue open for the ordered
// engine's `select-text-returned-none`; this is the other half.  The toast for `review` picks its
// explanation by failure shape, and a shape the page does not know falls to "the check covered more than one
// paragraph" -- false about a blank document, which has no other paragraph (finding 061's precedent:
// a sentence that is true of a different case is misleading attribution).
//
// Judged by the phrase that tells the sentences apart, not by the whole sentence.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// A namespace import on purpose: before the fix the module has no such export, and the test must then fail
// at its first assertion (the witness), not at link time.
import * as client from "../paragraph-editor-client.js";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const PAGE = readFileSync(here("../../web/e2-editor-app.js"), "utf8");

function slice(pattern, what) {
  const match = PAGE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const fn = (name) => slice(new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`);

const EMPTY = "這一段是空的";
const MULTI = "不只一個段落";
const ROLLBACK = "回到檢查點";
const CORE_REPLY = "核心的回覆";

/** The page's run() with its collaborators stubbed; returns the toasts it raised for one failing operation. */
async function toastFor(error, { shapes = client.EMPTY_SELECTION_SHAPES } = {}) {
  const toasts = [];
  const el = { s: { latency: { textContent: "" } } };
  const session = { restartAvailable: () => true };
  // eslint-disable-next-line no-new-func
  const run = new Function("el", "session", "toast", "reopenAfterBoundaryRefusal", "renderDocument",
                           "publishWindow", "describeError", "VIEW_ONLY_TEXT", "EMPTY_SELECTION_SHAPES", `
    let changes = 0;
    ${fn("deleteUnverified")}
    ${fn("reopensAfterRefusal")}
    ${fn("run")}
    return run;`)(
    el, session, (message, bad) => toasts.push({ message, bad }), () => {}, async () => {}, () => {},
    (e) => e?.code ?? String(e), "唯讀", shapes);
  const thrown = Object.assign(new Error("failed"), error);
  await assert.rejects(() => run("• 項目符號", () => Promise.reject(thrown)), thrown);
  assert.equal(toasts.length, 1, "run() must raise exactly one toast for a review error");
  return toasts[0].message;
}

const review = (failureShape, code = "MUTATION_OUTCOME_UNKNOWN") => ({
  code, recovery: "review",
  details: { formatBarrier: { dispatched: true, route: "collapsed", failureShape, selectionResultSeen: true } },
});

test("the ordered engine's empty select gets finding 083's sentence", async () => {
  const message = await toastFor(review("select-text-returned-none"));
  assert.ok(message.includes(EMPTY), `no empty-paragraph sentence: ${message}`);
  assert.ok(!message.includes(MULTI), `told a blank document its check covered several paragraphs: ${message}`);
  assert.ok(!message.includes(ROLLBACK), message);
});

test("finding 083's own shape still gets its sentence", async () => {
  const message = await toastFor(review("stage-deadline:awaiting-selection"));
  assert.ok(message.includes(EMPTY) && !message.includes(MULTI) && !message.includes(ROLLBACK), message);
});

test("finding 046's overshoot keeps the several-paragraphs sentence", async () => {
  const message = await toastFor(review("multi-block-readback"));
  assert.ok(message.includes(MULTI) && !message.includes(EMPTY), message);
});

test("finding 059's LOK_COMMAND_FAILED keeps its own sentence", async () => {
  const message = await toastFor(review("select-text-returned-none", "LOK_COMMAND_FAILED"));
  assert.ok(message.includes(CORE_REPLY) && !message.includes(EMPTY) && !message.includes(MULTI), message);
});

test("one list: the page's sentence and the disposition read the same two names", () => {
  assert.deepEqual([...client.EMPTY_SELECTION_SHAPES].sort(),
                   ["select-text-returned-none", "stage-deadline:awaiting-selection"]);
  assert.ok(fn("run").includes("EMPTY_SELECTION_SHAPES"), "run() does not consult the shared list");
});

test("the assertion has teeth: a page given only 083's name says the wrong sentence", async () => {
  const message = await toastFor(review("select-text-returned-none"),
                                 { shapes: Object.freeze(["stage-deadline:awaiting-selection"]) });
  assert.ok(message.includes(MULTI) && !message.includes(EMPTY),
            `the mutated list did not change the sentence, so the first test proves nothing: ${message}`);
});
