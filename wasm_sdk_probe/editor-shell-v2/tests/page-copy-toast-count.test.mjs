// SPEC-M3-select-all-v26 append 1, 5.10 (U4): finding 175 -- the copy and cut toasts say how many characters.
//
// `summarizeUnicode` (input/input-adapter.js) returns `codePoints` as an ARRAY of "U+XXXX" strings, and the page
// put that array straight into `已複製 ${…} 字` / `已剪下 ${…} 字`: since 2026-08-16 every successful copy said
// `已複製 U+0045,U+0031,… 字`, and after Ctrl+A that is the whole document.  The number must be the count of code
// points copied -- not UTF-16 units: the text below holds an astral character so the two differ.
//
// The two listeners are cut from the page's source and run with their collaborators stubbed; the copy result is
// the REAL summarizeUnicode of the text, so the shape the page reads is the adapter's own.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { summarizeUnicode } from "../../input/input-adapter.js";

const PAGE = readFileSync(fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url)), "utf8");
const TEXT = "E1 中文 😀\n第二段";
const COUNT = [...TEXT].length;

function listener(type) {
  const match = PAGE.match(new RegExp(`^el\\.sink\\.addEventListener\\("${type}", \\(event\\) => \\{[\\s\\S]*?\\n\\}\\);$`, "m"));
  assert.ok(match, `the ${type} listener not found in the page`);
  return match[0];
}

async function toastsOf(type) {
  const toasts = [];
  const handlers = {};
  const el = { sink: { addEventListener(name, fn) { handlers[name] = fn; } } };
  const session = { document: {}, copySelection: async () => summarizeUnicode(TEXT),
                    action: async () => ({}), offers: () => true };
  // eslint-disable-next-line no-new-func
  new Function("el", "session", "run", "toast", listener(type))(
    el, session, (label, operation) => operation(), (message, bad = false) => toasts.push({ message, bad }));
  handlers[type]({ preventDefault() {} });
  await new Promise((resolve) => setImmediate(resolve));
  return toasts;
}

test("U4: the text really has fewer code points than UTF-16 units (the fixture can tell them apart)", () => {
  assert.notEqual(COUNT, TEXT.length);
  assert.ok(Array.isArray(summarizeUnicode(TEXT).codePoints), "summarizeUnicode's shape changed; this test reads it");
});

for (const [type, verb] of [["copy", "複製"], ["cut", "剪下"]]) {
  test(`U4: the ${type} toast says how many characters, as a number`, async () => {
    const toasts = await toastsOf(type);
    assert.equal(toasts.length, 1, JSON.stringify(toasts));
    const { message, bad } = toasts[0];
    const match = message.match(new RegExp(`^已${verb} (\\d+) 字$`));
    assert.ok(match, `not 「已${verb} N 字」: ${message.slice(0, 80)}`);
    assert.equal(Number(match[1]), COUNT, message);
    assert.ok(!message.includes("U+"), message.slice(0, 80));
    assert.equal(bad, false);
  });
}
