// SPEC-M3-v28-last-line-fallback 4.3 item 3 (U-v28, page half): the sentence run() says for
// `fallback-readback-refused`.  Neither existing sentence is true there: 083's says nothing was selected, 046's
// names a multi-paragraph check as the cause.  The new one must not say "last paragraph" either: the fallback
// runs at every collapsed NONE (spec 3).  Judged by the phrases that tell the sentences apart (page-review-
// sentence.test.mjs's form), and by v26 U3's presentation: the ordinary style, no code or English in the toast.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import * as client from "../paragraph-editor-client.js";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const PAGE = readFileSync(here("../../web/e2-editor-app.js"), "utf8");
const fn = (name) => {
  const match = PAGE.match(new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"));
  assert.ok(match, `${name}() not found in the page`);
  return match[0];
};

const NEW = "往前多選一格";
const UNDO = "不是你要的就按「復原」";
const EMPTY = "這一段是空的";
const MULTI = "不只一個段落";

async function run(error) {
  const toasts = [];
  const warnings = [];
  const el = { s: { latency: { textContent: "" } } };
  const session = { restartAvailable: () => true };
  const realWarn = console.warn;
  console.warn = (...args) => warnings.push(args.join(" "));
  try {
    // eslint-disable-next-line no-new-func
    const page = new Function("el", "session", "toast", "reopenAfterBoundaryRefusal", "renderDocument",
                              "publishWindow", "describeError", "VIEW_ONLY_TEXT", "EMPTY_SELECTION_SHAPES",
                              "FALLBACK_REFUSED_SHAPES", "PARAGRAPH_READ_SHAPES", `
      let changes = 0;
      ${fn("deleteUnverified")}
      ${fn("reopensAfterRefusal")}
      ${fn("run")}
      return run;`)(
      el, session, (message, bad) => toasts.push({ message, bad }), () => {}, async () => {}, () => {},
      (e) => `${e?.code ? `${e.code}：` : ""}${e?.message || String(e)}`, "唯讀", client.EMPTY_SELECTION_SHAPES,
      client.FALLBACK_REFUSED_SHAPES ?? Object.freeze([]), client.PARAGRAPH_READ_SHAPES);
    const thrown = Object.assign(new Error("the fallback selection's readback does not provide a supported "
                                           + "structural proof; the format mutation outcome is unknown"), error);
    await assert.rejects(() => page("• 項目符號", () => Promise.reject(thrown)), thrown);
  } finally {
    console.warn = realWarn;
  }
  assert.equal(toasts.length, 1, "run() must raise exactly one toast for a review error");
  return { ...toasts[0], strip: el.s.latency.textContent, warnings };
}

const review = (failureShape) => ({
  code: "MUTATION_OUTCOME_UNKNOWN", recovery: "review",
  details: { formatBarrier: { dispatched: true, route: "collapsed", failureShape, selectionResultSeen: true } },
});

test("a refused fallback gets its own sentence, not 083's and not 046's", async () => {
  const { message } = await run(review("fallback-readback-refused"));
  assert.ok(message.includes(NEW), `no fallback sentence: ${message}`);
  assert.ok(message.includes(UNDO), message);
  assert.ok(!message.includes(EMPTY) && !message.includes(MULTI), message);
  assert.ok(!message.includes("最後一段"), `claims "last paragraph", false outside the document's end: ${message}`);
  assert.ok(!message.includes("回到檢查點"), message);
});

test("presented as a review: ordinary style, no code or English; both on the console; the strip says 待確認",
     async () => {
  const { message, bad, strip, warnings } = await run(review("fallback-readback-refused"));
  assert.equal(bad, false);
  assert.ok(!message.includes("MUTATION_OUTCOME_UNKNOWN") && !/[A-Za-z]{4,}/.test(message), message);
  assert.ok(warnings.some((w) => w.includes("[review]") && w.includes("MUTATION_OUTCOME_UNKNOWN")
                                 && w.includes("fallback-readback-refused")), warnings.join("\n"));
  assert.equal(strip, "• 項目符號：待確認");
});

test("run() consults the shared list", () => {
  assert.ok(fn("run").includes("FALLBACK_REFUSED_SHAPES"), "run() does not consult FALLBACK_REFUSED_SHAPES");
});
