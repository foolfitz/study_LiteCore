// SPEC-M3-link-batch-v21 §11.1 D5, as ARMS-item1.md §8 ruling D-11 B reads it: the binding axis of
// the matrix is GENERATED from the page's own `DOCUMENT_KEY_ACTIONS` (form two, 「工具封閉」), not listed
// by hand.  page-document-keys.test.mjs keeps its hand-listed rows; this file adds the generated ones:
//
//   every key of DOCUMENT_KEY_ACTIONS x {Ctrl, Cmd} x the action's state in the profile
//     absent   (the REAL v20 manifest, which does not carry the action)
//     withheld (present, gestures [])
//     declared (gestures ["collapsed"])
//   -> the key is taken (and preventDefault'ed) exactly when the action is declared;
//   and with Shift, Alt or during an IME composition it is never taken, even when declared.
//
// A key added to DOCUMENT_KEY_ACTIONS joins every row without an edit here.  Red first: a scratch page
// whose `documentKeyAction` takes a fictional key whatever the profile offers turns this file red while
// the hand-listed file stays green (findings/evidence/link-batch-v21/shakedown/d5-gen-red/).
//
//   PAGE_SOURCE=<page> node --test editor-shell-v2/tests/page-document-keys-generated.test.mjs

import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorV2Client } from "../narrow-editor-v2-client.js";
import { selectionShapeOf } from "../narrow-editor-v2-session.js";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const SOURCE = readFileSync(process.env.PAGE_SOURCE || here("../../web/e2-editor-app.js"), "utf8");
const V20 = JSON.parse(readFileSync(here("../../dist/profiles/e2-editor-v20/sdk-manifest.json"), "utf8"));

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const fn = (name) => slice(new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`);
const TABLE_SOURCE = slice(/^const DOCUMENT_KEY_ACTIONS = \{[^\n]*\};$/m, "DOCUMENT_KEY_ACTIONS");
// eslint-disable-next-line no-new-func
const DOCUMENT_KEY_ACTIONS = new Function(`${TABLE_SOURCE}; return DOCUMENT_KEY_ACTIONS;`)();
const IDS = { "move-document-start": 22, "move-document-end": 23 };

/** v20's real manifest with `action` set to `how` (absent leaves v20's manifest as it is). */
function manifest(action, how) {
  const m = structuredClone(V20);
  if (how !== "absent")
    m.editorContract.actions[action] = { id: IDS[action] ?? 99, gestures: how === "withheld" ? [] : ["collapsed"],
                                         limits: ["no-extend-selection"] };
  return m;
}

function press(m, init) {
  const client = new NarrowEditorV2Client({ handle: 1, revision: 0, _assertUsable() {},
                                            _engine: { manifest: m, async _request() { return null; } } });
  const sent = [];
  const session = { offers: (a) => client.offers(a), gesturesFor: (a) => client.gesturesFor(a),
                    state: { snapshot: { editorState: { selection: { collapsed: true } } } } };
  const editorAction = (action) => { sent.push(action); return new Promise(() => {}); };
  const moveFromPoint = (action) => editorAction(action);
  // eslint-disable-next-line no-new-func
  const api = new Function("session", "editorAction", "moveFromPoint", "selectionShapeOf", "pointMovesInFlight", `
    let lastSelectionShape = "collapsed";
    ${TABLE_SOURCE}
    ${slice(/^const documentMovesUnanswered = new Map\(\);$/m, "documentMovesUnanswered")}
    ${fn("documentKeyAction")}
    ${fn("dropsDocumentMove")}
    ${fn("sendDocumentMove")}
    ${fn("takeDocumentKey")}
    return { takeDocumentKey };
  `)(session, editorAction, moveFromPoint, selectionShapeOf, 0);
  const event = { ctrlKey: false, metaKey: false, shiftKey: false, altKey: false, isComposing: false, repeat: false,
                  ...init, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
  const taken = api.takeDocumentKey(event);
  return { taken, prevented: event.defaultPrevented, sent };
}

const ROWS = Object.entries(DOCUMENT_KEY_ACTIONS).flatMap(([key, action]) =>
  [["Ctrl", { ctrlKey: true }], ["Cmd", { metaKey: true }]].map(([mod, init]) => [`${mod}+${key}`, { key, ...init }, action]));

test("D5-gen: the matrix is generated from the page's own table, and the table is not empty", () => {
  assert.ok(ROWS.length >= 4, `${ROWS.length} generated rows`);
  for (const action of Object.values(DOCUMENT_KEY_ACTIONS))
    assert.equal(Object.hasOwn(V20.editorContract.actions, action), false, `${action} is in the real v20 manifest`);
});

for (const [name, init, action] of ROWS) {
  for (const how of ["absent", "withheld", "declared"]) {
    test(`D5-gen ${name} (${action} ${how}): taken exactly when declared`, () => {
      const { taken, prevented, sent } = press(manifest(action, how), init);
      const offered = how === "declared";
      assert.equal(taken, offered, "taken");
      assert.equal(prevented, offered, "preventDefault");
      assert.deepEqual(sent, offered ? [action] : [], "sent");
    });
  }
  test(`D5-gen ${name}: Shift, Alt and an IME composition are never taken, even when declared`, () => {
    for (const extra of [{ shiftKey: true }, { altKey: true }, { isComposing: true }]) {
      const { taken, prevented, sent } = press(manifest(action, "declared"), { ...init, ...extra });
      assert.equal(taken, false, JSON.stringify(extra));
      assert.equal(prevented, false, JSON.stringify(extra));
      assert.deepEqual(sent, []);
    }
  });
}
