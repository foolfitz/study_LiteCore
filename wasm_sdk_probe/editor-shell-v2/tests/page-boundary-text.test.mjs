// SPEC-M3-paragraph-merge M1-5 (as corrected in 10.2 and 10.1(h)): what the
// product page tells the user after a boundary refusal.
//
// An engine that presses the user's own key can refuse AFTER the key went out
// (`details.mergeKey.keyPosted`), and then "文件沒有被改動" would be a lie.
// The functions are taken from the page source and run with stubs, so these
// test the page's own code, not a copy of it: `boundaryText` with its stage
// set, and `reopenAfterBoundaryRefusal` through every exit.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const PAGE = fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url));
const SOURCE = readFileSync(PAGE, "utf8");
const UNCHANGED = "沒有被改動";

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}

const BOUNDARY_TEXT_DECL = slice(/^const BOUNDARY_TEXT = .*;$/m, "BOUNDARY_TEXT");
const STAGES_DECL = slice(/^const MERGE_KEY_UNCHANGED_STAGES = new Set\(\[[\s\S]*?\]\);$/m,
                          "MERGE_KEY_UNCHANGED_STAGES");
const UNCERTAIN_FN = slice(/^function boundaryKeyUncertain\(error\) \{[\s\S]*?\n\}$/m,
                           "boundaryKeyUncertain()");
const BOUNDARY_FN = slice(/^function boundaryText\(error\) \{[\s\S]*?\n\}$/m, "boundaryText()");
const REOPEN_FN = slice(/^async function reopenAfterBoundaryRefusal\(error\) \{[\s\S]*?\n\}$/m,
                        "reopenAfterBoundaryRefusal(error)");

// eslint-disable-next-line no-new-func
const { boundaryText, boundaryKeyUncertain } = new Function(
  `${BOUNDARY_TEXT_DECL}\n${STAGES_DECL}\n${UNCERTAIN_FN}\n${BOUNDARY_FN}\n`
  + "return { boundaryText, boundaryKeyUncertain };")();

const refusal = (mergeKey) => ({ code: "EDITOR_BOUNDARY_UNSUPPORTED",
                                 details: mergeKey === undefined ? {} : { mergeKey } });

test("M1-5: an engine without B (no mergeKey) keeps the old, true sentence", () => {
  assert.match(boundaryText(refusal(undefined)), /段落交界/);
  assert.ok(boundaryText(refusal(undefined)).includes(UNCHANGED));
});

test("M1-5: keyPosted true is never told 'not changed', whatever the stage", () => {
  for (const stage of ["key-deadline", "restore", "nothing-selected", "", "anything"])
    assert.ok(!boundaryText(refusal({ keyPosted: true, stage })).includes(UNCHANGED), stage);
});

test("M1-5: keyPosted missing or not false is never told 'not changed'", () => {
  for (const keyPosted of [undefined, null, "false", 0])
    assert.ok(!boundaryText(refusal({ keyPosted, stage: "restore" })).includes(UNCHANGED),
              String(keyPosted));
});

// The engine's stage table, read from the header the engine compiles
// (src/merge_key_undo.hpp kStages), not listed here: a stage the engine
// gains without the page deciding its sentence turns this red.
const ENGINE_STAGES = (() => {
  const header = readFileSync(new URL("../../src/merge_key_undo.hpp", import.meta.url), "utf8");
  const table = header.match(/constexpr Stage kStages\[\] = \{([\s\S]*?)\};/);
  assert.ok(table, "kStages not found in merge_key_undo.hpp");
  const stages = [...table[1].matchAll(/\{"([a-z-]+)",\s*(true|false)\}/g)]
    .map(([, name, posted]) => ({ name, keyPosted: posted === "true" }));
  assert.ok(stages.length >= 8, `only ${stages.length} stages parsed`);
  return stages;
})();

test("M1-5: before-the-key stages say 'not changed'; unknown and restore-mutated do not", () => {
  // restore-mutated is before the key but means the payload moved: uncertain.
  for (const { name, keyPosted } of ENGINE_STAGES) {
    const says = boundaryText(refusal({ keyPosted, stage: name })).includes(UNCHANGED);
    assert.equal(says, !keyPosted && name !== "restore-mutated", name);
  }
  for (const stage of ["a-stage-added-later", ""])
    assert.ok(!boundaryText(refusal({ keyPosted: false, stage })).includes(UNCHANGED), stage);
});

test("M1-5: the page's 'not changed' set holds only stages the engine has", () => {
  const names = new Set(ENGINE_STAGES.map(({ name }) => name));
  for (const stage of eval(`new Set(${STAGES_DECL.match(/new Set\(([\s\S]*)\)/)[1]})`))
    assert.ok(names.has(stage), `page lists ${stage}, which the engine never sends`);
});

test("M1-5: 'nothing selected' does not claim a document end", () => {
  const text = boundaryText(refusal({ keyPosted: false, stage: "nothing-selected" }));
  assert.ok(!/開頭|結尾|兩端/.test(text), text);
});

/** Run the page's reopenAfterBoundaryRefusal with stubs; returns the toasts. */
async function reopen(error, { state = "restart-required", restartAvailable = true,
                               keeps = true, dirty = true, restartThrows = false } = {}) {
  const toasts = [];
  const session = {
    state: { snapshot: { state, dirty } },
    restartAvailable: () => restartAvailable,
    restartKeepsContent: () => keeps,
    async restart() { if (restartThrows) throw new Error("no"); },
  };
  const names = ["session", "toast", "run", "rescueAtGenerationLimit", "el", "boundaryText",
                 "boundaryKeyUncertain"];
  // eslint-disable-next-line no-new-func
  const fn = new Function(...names, `${REOPEN_FN}\nreturn reopenAfterBoundaryRefusal;`)(
    session, (message) => toasts.push(message),
    async (_label, operation) => operation(),
    async () => {}, { sink: { focus() {} } }, boundaryText, boundaryKeyUncertain);
  await fn(error).catch(() => {});
  return toasts;
}

const EXITS = [
  ["generation limit", { restartAvailable: false }],
  ["checkpoint not kept", { keeps: false }],
  ["restarted, dirty", {}],
  ["restarted, clean", { dirty: false }],
  ["restart failed", { restartThrows: true }],
];

test("M1-5: every exit of reopenAfterBoundaryRefusal, keyPosted true, never says 'not changed'",
     async () => {
  let toasts = 0;
  for (const [label, options] of EXITS) {
    for (const message of await reopen(refusal({ keyPosted: true, stage: "key-deadline" }), options)) {
      toasts += 1;
      assert.ok(!message.includes(UNCHANGED), `${label}: ${message}`);
    }
  }
  assert.ok(toasts >= EXITS.length, "the exits produced no toasts; the stubs reached nothing");
});

test("M1-5: after a restart with the key's effect uncertain, the user is told to look", async () => {
  for (const [label, options] of [["restarted, dirty", {}], ["restarted, clean", { dirty: false }]]) {
    const messages = await reopen(refusal({ keyPosted: true, stage: "key-deadline" }), options);
    assert.match(messages.at(-1), /那個位置/, `${label}: ${messages.at(-1)}`);
  }
});

test("M1-5: the same exits for an engine without B still use its sentence", async () => {
  for (const [label, options] of EXITS) {
    const messages = await reopen(refusal(undefined), options);
    assert.ok(messages.length > 0, label);
    assert.ok(messages.every((m) => m.includes("段落交界")), `${label}: ${messages}`);
  }
});

test("M1-5: the page hands the error to the reopen path", () => {
  assert.match(SOURCE, /void reopenAfterBoundaryRefusal\(error\);/);
  assert.ok(!/reopenAfterBoundaryRefusal\(\)/.test(SOURCE),
            "a call without the error cannot see mergeKey");
});
