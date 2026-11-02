// SPEC-M3-select-all-v26 5.5 (U3): finding 174 -- how the page's run() shows a `review` disposition.
//
// Owner, host 0.2.41, a bullet in a new blank document: the bullet was applied, and a RED box said
// `MUTATION_OUTCOME_UNKNOWN：the synchronous selection read did not provide readable text; …` before 083's
// Chinese sentence.  `review` means dispatched, the queue open, "look at the result" -- not a failure.  For
// all three review cases (059, 083/173, 046; owner chose B) the toast is now the label and the sentence only,
// not in the error style; the code and the engine's message go to console.warn.  Every other disposition is
// unchanged: red, with the code.
//
// Same cut as page-review-sentence.test.mjs (v79's U2), with the toast's style and the console captured.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { EMPTY_SELECTION_SHAPES, FALLBACK_REFUSED_SHAPES, PARAGRAPH_READ_SHAPES } from "../paragraph-editor-client.js";

const PAGE = readFileSync(fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url)), "utf8");

function slice(pattern, what) {
  const match = PAGE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const fn = (name) => slice(new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`);

const ENGINE_MESSAGE = "the synchronous selection read did not provide readable text; the format mutation outcome is unknown";
const LABEL = "• 項目符號";

async function toastFor(error) {
  const toasts = [];
  const warned = [];
  const el = { s: { latency: { textContent: "" } } };
  const session = { restartAvailable: () => true };
  const realWarn = console.warn;
  console.warn = (...args) => warned.push(args.map(String).join(" "));
  try {
    // eslint-disable-next-line no-new-func
    const run = new Function("el", "session", "toast", "reopenAfterBoundaryRefusal", "renderDocument",
                             "publishWindow", "describeError", "VIEW_ONLY_TEXT", "EMPTY_SELECTION_SHAPES",
                             "FALLBACK_REFUSED_SHAPES", "PARAGRAPH_READ_SHAPES", `
      let changes = 0;
      ${fn("deleteUnverified")}
      ${fn("reopensAfterRefusal")}
      ${fn("run")}
      return run;`)(
      el, session, (message, bad = false) => toasts.push({ message, bad }), () => {}, async () => {}, () => {},
      (e) => `${e?.code ? `${e.code}：` : ""}${e?.message || String(e)}`, "唯讀", EMPTY_SELECTION_SHAPES, FALLBACK_REFUSED_SHAPES, PARAGRAPH_READ_SHAPES);
    const thrown = Object.assign(new Error(ENGINE_MESSAGE), error);
    await assert.rejects(() => run(LABEL, () => Promise.reject(thrown)), thrown);
  } finally {
    console.warn = realWarn;
  }
  assert.equal(toasts.length, 1, "run() must raise exactly one toast");
  return { ...toasts[0], warned };
}

const review = (failureShape, code = "MUTATION_OUTCOME_UNKNOWN") => ({
  code, recovery: "review",
  details: { formatBarrier: { dispatched: true, route: "collapsed", failureShape, selectionResultSeen: true } },
});

const REVIEW_CASES = [
  ["083/173 empty paragraph", review("select-text-returned-none"), "這一段是空的"],
  ["046 several paragraphs", review("multi-block-readback"), "不只一個段落"],
  ["059 core reply", review("select-text-returned-none", "LOK_COMMAND_FAILED"), "核心的回覆"],
];

for (const [name, error, phrase] of REVIEW_CASES) {
  test(`U3: ${name} -- the label and the sentence, not the error style, no code, no engine message`, async () => {
    const { message, bad, warned } = await toastFor(error);
    assert.equal(bad, false, `a review is shown as an error: ${message}`);
    assert.ok(message.startsWith(`${LABEL}：`), message);
    assert.ok(message.includes(phrase), message);
    assert.ok(!message.includes(error.code), `the code is still shown: ${message}`);
    assert.ok(!message.includes("selection read"), `the engine's English is still shown: ${message}`);
    assert.ok(!message.startsWith(`${LABEL}：（`), `the sentence is still wrapped in its old parentheses: ${message}`);
    assert.ok(warned.some((line) => line.includes(error.code) && line.includes("selection read")),
              `the code and the engine message were not kept on the console: ${JSON.stringify(warned)}`);
  });
}

for (const [name, error, suffix] of [
  ["rollback", { code: "MUTATION_OUTCOME_UNKNOWN", recovery: "rollback" }, "請回到檢查點"],
  ["restart", { code: "WORKER_CRASHED", recovery: "restart" }, "需要重新開啟文件"],
  ["no disposition", { code: "STALE_REVISION", recovery: "none" }, null],
]) {
  test(`U3: ${name} is unchanged -- red, with the code`, async () => {
    const { message, bad } = await toastFor(error);
    assert.equal(bad, true, message);
    assert.ok(message.includes(error.code), message);
    if (suffix) assert.ok(message.includes(suffix), message);
  });
}
