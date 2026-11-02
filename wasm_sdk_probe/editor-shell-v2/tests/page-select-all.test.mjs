// SPEC-M3-select-all-v26 5.3 (U2): the page's Ctrl/Cmd+A.
//
//   * taken only where the profile grants select-all (`session.offers`), so the
//     reason it was unbound -- 2026-08-19 -- keeps holding on every profile that
//     withholds it: the work order's red case "a page that binds Ctrl+A on a
//     withholding profile";
//   * never with Shift or Alt, never during an IME composition; a held key is one
//     request (finding 106's rule);
//   * the reply becomes the page's selection shape (the drag's 079 rule: an
//     unreadable reply keeps the old shape and raises the flag);
//   * a reply that selected nothing says so, and the one refusal a granted
//     select-all meets (no selection observed yet) says what to do.
//
// The functions are cut from the page's source with their collaborators stubbed,
// as page-document-keys.test.mjs does.  Two mutations of that source prove the
// offer and repeat assertions have teeth.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { selectionShapeOf } from "../narrow-editor-v2-session.js";

const PAGE = readFileSync(fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url)), "utf8");

function slice(source, pattern, what) {
  const match = source.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const fn = (source, name) =>
  slice(source, new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`);
const konst = (source, name) => slice(source, new RegExp(`^const ${name} = [^\\n]*;$`, "m"), name);

function harness({ offered = true, composing = false, reply = null, source = PAGE } = {}) {
  const sent = [];
  const toasts = [];
  const dataset = {};
  const session = { offers: (name) => name === "select-all" && offered, input: { state: { composing } } };
  const editorAction = (action, { onResult } = {}) => {
    sent.push(action);
    if (reply instanceof Error) return Promise.reject(reply);
    if (reply && onResult) onResult(reply);
    return Promise.resolve(reply);
  };
  // eslint-disable-next-line no-new-func
  const api = new Function("session", "editorAction", "toast", "el", "selectionShapeOf", "selectionShapeEvidence",
                           "updateGestureAffordance", `
    let lastSelectionShape = "collapsed";
    ${konst(source, "SELECT_ALL_NOTHING_TEXT")}
    ${konst(source, "SELECT_ALL_UNOBSERVED_TEXT")}
    ${fn(source, "selectAllKey")}
    ${fn(source, "selectAllResult")}
    ${fn(source, "takeSelectAllKey")}
    return { takeSelectAllKey, shape: () => lastSelectionShape };
  `)(session, editorAction, (message, bad = false) => toasts.push({ message, bad }), { toolbar: { dataset } },
     selectionShapeOf, () => "evidence", () => {});
  const press = async (init) => {
    const event = { key: "a", ctrlKey: false, metaKey: false, shiftKey: false, altKey: false, isComposing: false,
                    repeat: false, ...init, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
    const taken = api.takeSelectAllKey(event);
    await new Promise((resolve) => setImmediate(resolve));
    return { taken, prevented: event.defaultPrevented };
  };
  return { press, sent, toasts, dataset, shape: api.shape };
}

const RANGE = { state: { selection: { observed: true, collapsed: false,
                                      rectangles: [{ x: 1418, y: 1418, width: 9000, height: 413 },
                                                   { x: 1418, y: 1831, width: 9000, height: 413 }] } } };
const NOTHING = { state: { selection: { observed: true, collapsed: true, rectangles: [] } } };

test("U2: offered -- Ctrl+A and Cmd+A are each taken once and send select-all once", async () => {
  for (const chord of [{ ctrlKey: true }, { metaKey: true }, { ctrlKey: true, key: "A" }]) {
    const h = harness({ reply: RANGE });
    assert.deepEqual(await h.press(chord), { taken: true, prevented: true }, JSON.stringify(chord));
    assert.deepEqual(h.sent, ["select-all"], JSON.stringify(chord));
  }
});

test("U2: not offered -- Ctrl+A is left to the browser, nothing is sent", async () => {
  const h = harness({ offered: false, reply: RANGE });
  assert.deepEqual(await h.press({ ctrlKey: true }), { taken: false, prevented: false });
  assert.deepEqual(h.sent, []);
});

test("U2: a held key is one request -- the repeat is taken and dropped", async () => {
  const h = harness({ reply: RANGE });
  assert.deepEqual(await h.press({ ctrlKey: true, repeat: true }), { taken: true, prevented: true });
  assert.deepEqual(h.sent, []);
});

test("U2: Shift, Alt, plain A and a composition are never taken", async () => {
  for (const [init, composing] of [[{ ctrlKey: true, shiftKey: true }, false], [{ ctrlKey: true, altKey: true }, false],
                                   [{}, false], [{ ctrlKey: true, isComposing: true }, false],
                                   [{ ctrlKey: true }, true]]) {
    const h = harness({ reply: RANGE, composing });
    assert.deepEqual(await h.press(init), { taken: false, prevented: false }, JSON.stringify([init, composing]));
    assert.deepEqual(h.sent, []);
  }
});

test("U2: a range reply becomes the page's shape, and nothing is toasted", async () => {
  const h = harness({ reply: RANGE });
  await h.press({ ctrlKey: true });
  assert.equal(h.shape(), selectionShapeOf(RANGE));
  assert.notEqual(h.shape(), "collapsed");
  assert.deepEqual(h.toasts, []);
});

test("U2: a reply that selected nothing says so and stays collapsed", async () => {
  const h = harness({ reply: NOTHING });
  await h.press({ ctrlKey: true });
  assert.equal(h.shape(), "collapsed");
  assert.equal(h.toasts.length, 1);
  assert.ok(h.toasts[0].message.includes("沒有選到任何內容"), h.toasts[0].message);
});

test("U2: an unreadable reply keeps the shape, raises the flag and says nothing", async () => {
  const h = harness({ reply: { revision: 1 } });
  await h.press({ ctrlKey: true });
  assert.equal(h.shape(), "collapsed");
  assert.equal(h.dataset.selectionUnreadable, "1");
  assert.deepEqual(h.toasts, []);
});

test("U2: the refusal before any selection report says to click first", async () => {
  const h = harness({ reply: Object.assign(new Error("no selection observed"),
                                           { code: "EDITOR_FORMAT_GESTURE_UNSUPPORTED" }) });
  await h.press({ ctrlKey: true });
  assert.ok(h.toasts.some((t) => t.message.includes("請先點一下文件")), JSON.stringify(h.toasts));
});

test("U2 teeth: without the offer check the not-offered assertion would fail", async () => {
  const body = fn(PAGE, "selectAllKey");
  const mutated = PAGE.replace(body, body.replace(/&& offered\("select-all"\) === true/, ""));
  assert.notEqual(mutated, PAGE, "the mutation did not apply: the offer check is not written where this looks");
  const h = harness({ offered: false, reply: RANGE, source: mutated });
  assert.deepEqual(await h.press({ ctrlKey: true }), { taken: true, prevented: true });
});

test("U2 teeth: without the repeat check a held key would send", async () => {
  const body = fn(PAGE, "takeSelectAllKey");
  const mutated = PAGE.replace(body, body.replace(/\n {2}if \(event\.repeat === true\) return true;/, ""));
  assert.notEqual(mutated, PAGE, "the mutation did not apply: the repeat check is not written where this looks");
  const h = harness({ reply: RANGE, source: mutated });
  await h.press({ ctrlKey: true, repeat: true });
  assert.deepEqual(h.sent, ["select-all"]);
});

test("U2 wiring: the handler takes Ctrl+A before `if (accel) return;`, with a label, on profile v26", () => {
  const handler = slice(PAGE, /^el\.sink\.addEventListener\("keydown", \(event\) => \{[\s\S]*?\n\}\);$/m, "the keydown handler");
  const take = handler.indexOf("if (takeSelectAllKey(event)) return;");
  assert.ok(take > 0, "the keydown handler does not call takeSelectAllKey");
  assert.ok(handler.indexOf("if (accel) return;") > take, "takeSelectAllKey runs after the accel bail-out");
  assert.match(slice(PAGE, /^const ACTION_LABELS = \{[\s\S]*?\n\};$/m, "ACTION_LABELS"), /"select-all": "全選"/);
  assert.match(PAGE, /workerUrl: "\.\/profiles\/e2-editor-v\d+\/sdk-worker\.js"/);
});
