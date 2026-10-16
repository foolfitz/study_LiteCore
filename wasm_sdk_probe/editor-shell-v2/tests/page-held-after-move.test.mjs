// SPEC-M3-link-batch-v21 §10.3 / §11.1 D8: the held deletes, rewritten.
//
// With Ctrl+Home/End bound, "a delete of this key is out and unanswered" stopped
// meaning "this press is at the same place".  The rewrite (§10.3 items 1-4):
//   1. a press is held IFF the session's most recent enqueue is an unanswered
//      delete of the same key (the session's `enqueueCount`);
//   2. a held press belongs to the send it waits on, with its own key;
//   3. that send's answer decides them: a standing no-op drops them, anything
//      else releases them in order;
//   4. anything else about to be enqueued while presses are held sends them
//      first (`releaseHeldDeletesBeforeEnqueue`, the session's `beforeEnqueue`).
//
// D8's five sequences, driven through the page's own `beforeinput` listener and
// helpers (sliced from the page source) against the REAL NarrowEditorV2Session
// -- its queue, its enqueue counter, its hook -- over a fake engine that keeps a
// ten-character document and answers like the v21 engine: a delete inside text
// in 66 ms, a delete at a C boundary as `verified-boundary-noop` after its
// 250 + 2,000 ms window, a document move at once (or after its 250 ms readback
// when it is already there).  Mocked time.
//
// The move is sent as the page's `editorAction(...)` would send it for the key
// (`sendDocumentMove`); the key binding itself is page-document-keys.test.mjs's.
// That keeps this file about the HOLD, so `PAGE_SOURCE=<path>` runs the same
// five sequences against another page's hold logic: on the page before this
// change (0.2.24's, HEAD 07d01cf8) (c), (d) and (e) are red -- the witness the
// spec requires before these are called green.

import assert from "node:assert/strict";
import { mock, test } from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorV2Session, selectionShapeOf } from "../narrow-editor-v2-session.js";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const SOURCE = readFileSync(process.env.PAGE_SOURCE || here("../../web/e2-editor-app.js"), "utf8");
const V20 = JSON.parse(readFileSync(here("../../dist/profiles/e2-editor-v20/sdk-manifest.json"), "utf8"));
const V21 = structuredClone(V20);
V21.editorContract.abiVersion = 5;
for (const [action, id] of [["move-document-start", 22], ["move-document-end", 23]])
  V21.editorContract.actions[action] = { id, gestures: ["collapsed"], limits: ["no-extend-selection"] };

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const optional = (pattern) => (SOURCE.match(pattern) || [""])[0];
const fn = (name) => new RegExp(`^function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m");

const WINDOW_MS = 2250;      // C: 250 + 2,000 ms at a document boundary (SPEC-M3-link-batch §10.5)
const DELETE_MS = 66;        // a verified delete inside text (finding 132)
const READBACK_MS = 250;     // a move with nowhere to go (finding 096)
const MOVE_MS = 5;
const CLICK_MS = 25;
const SAVE_MS = 5;
const REPAINT_MS = 10;
const TEXT = "ABCDEFGHIJ";

class InputEvent {
  constructor(type, init = {}) { this.type = type; this.inputType = init.inputType; this.defaultPrevented = false; }
  preventDefault() { this.defaultPrevented = true; }
}

/** The fake engine: a ten-character paragraph, a caret index, and the v21 answers. */
function engineFor(model) {
  const caretRect = () => ({ x: 1000 + model.caret * 100, y: 1000, width: 0, height: 300 });
  const stateOf = () => ({
    documentHandle: 1, revision: model.revision, sourceSequence: model.sequence,
    documentChangeSequence: model.revision, caret: caretRect(),
    selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
    selectionType: "none", selectionTextMissing: false, selectionText: "",
    format: { bold: false, italic: false },
  });
  const later = (ms, answer) => new Promise((resolve) => setTimeout(() => resolve(answer()), ms));
  const document = {
    handle: 1, revision: 0, widthTwips: 12000, heightTwips: 16000,
    _assertUsable() {},
    async render() { return { pixels: new ArrayBuffer(4), revision: model.revision }; },
    save() { model.saves += 1; return later(SAVE_MS, () => new ArrayBuffer(8)); },
    async click() {},
    async close() {},
  };
  const moved = (payload, at) => () => {
    const stays = model.caret === at;
    model.caret = at;
    if (!stays) model.sequence += 1;
    return { action: payload.action, beforeRevision: payload.expectedRevision, revision: model.revision,
             changed: false, completion: stays ? "verified-move-readback" : "documented-callback-visible-cursor",
             state: stateOf() };
  };
  const noop = (payload) => () => ({
    action: payload.action, beforeRevision: payload.expectedRevision, revision: model.revision, changed: false,
    completion: "verified-boundary-noop", boundaryNoop: { waitedMs: WINDOW_MS }, state: stateOf() });
  const deleted = (payload, at) => () => {
    model.text.splice(at, 1);
    if (payload.action === "delete-backward") model.caret -= 1;
    model.revision += 1;
    model.sequence += 1;
    return { action: payload.action, beforeRevision: payload.expectedRevision, revision: model.revision,
             changed: true, completion: "verified-selection-delete", state: stateOf() };
  };
  const engine = {
    manifest: V21,
    onEvent() { return () => {}; },
    async open() { document.revision = model.revision; return document; },
    async _request(operation, payload) {
      if (operation === "editorGetStateV2") return stateOf();
      if (operation === "editorPlaceCaretV2") {
        model.requests.push("place-caret");
        return later(CLICK_MS, () => {
          model.caret = Math.max(0, Math.min(model.text.length, Math.round((payload.xTwips - 1000) / 100)));
          model.sequence += 1;
          return { revision: model.revision, completion: "documented-callback-visible-cursor", state: stateOf() };
        });
      }
      assert.equal(operation, "editorActionV2");
      const { action } = payload;
      model.requests.push(action);
      const end = model.text.length;
      if (action === "move-document-start") return later(model.caret === 0 ? READBACK_MS : MOVE_MS, moved(payload, 0));
      if (action === "move-document-end") return later(model.caret === end ? READBACK_MS : MOVE_MS, moved(payload, end));
      if (action === "delete-backward")
        return model.caret === 0 ? later(WINDOW_MS, noop(payload)) : later(DELETE_MS, deleted(payload, model.caret - 1));
      if (action === "delete-forward")
        return model.caret === end ? later(WINDOW_MS, noop(payload)) : later(DELETE_MS, deleted(payload, model.caret));
      throw new Error(`the fake engine does not do ${action}`);
    },
    dispose() {},
  };
  document._engine = engine;
  return engine;
}

/** The page's delete path, compiled from the page source, over the real session. */
async function page(caret) {
  const model = { text: [...TEXT], caret, revision: 0, sequence: 1, saves: 0, requests: [] };
  let hook = null;
  const session = new NarrowEditorV2Session({
    engineFactory: async () => engineFor(model),
    secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } },
    // The page passes `releaseHeldDeletesBeforeEnqueue` here (page-document-keys.test.mjs checks it does).
    beforeEnqueue: (label) => hook?.(label),
  });
  await session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
  const listeners = [];
  const sink = {
    addEventListener: (type, l) => listeners.push([type, l]),
    dispatchEvent(event) { for (const [type, l] of listeners) if (type === event.type) l(event); return !event.defaultPrevented; },
  };
  // The page's editorAction, as far as the hold can see it: the session's
  // action, `onResult` at the engine's answer, the repaint after.
  const editorAction = (action, options = {}) => {
    if (!["ready", "busy"].includes(session.state.snapshot.state)) return Promise.resolve();
    return session.action(action, {})
      .then((result) => { options.onResult?.(result); return result; })
      .then((result) => new Promise((resolve) => setTimeout(() => resolve(result), REPAINT_MS)));
  };
  // eslint-disable-next-line no-new-func
  const api = new Function("el", "session", "selectionShapeOf", "editorAction", "paint", `
    ${slice(/^const DELETE_INPUT_TYPES = \{[\s\S]*?\n\};$/m, "DELETE_INPUT_TYPES")}
    let lastSelectionShape = "collapsed"; let deletesInFlight = 0; let deleteRefusedThisHold = false;
    ${optional(/^let deletesUnanswered = 0;$/m)}
    ${slice(/^const heldDeletes = \{[^\n]*\};$/m, "heldDeletes")}
    ${slice(fn("deleteActionFor"), "deleteActionFor()")}
    ${["deleteStateOf", "boundaryNoopStands", "holdsDelete", "dropHeldDeletes", "releaseHeldDelete",
       "releaseHeldDeletesBeforeEnqueue", "settleDelete", "dispatchDelete"]
      .map((name) => optional(fn(name))).join("\n")}
    ${slice(/^el\.sink\.addEventListener\("beforeinput", \(event\) => \{[\s\S]*?\n\}\);$/m, "the beforeinput handler")}
    return { hook: typeof releaseHeldDeletesBeforeEnqueue === "function" ? releaseHeldDeletesBeforeEnqueue : null,
             held: () => heldDeletes.count, inFlight: () => deletesInFlight };
  `)({ sink }, session, selectionShapeOf, editorAction, () => {});
  hook = api.hook;
  const key = (inputType) => () => sink.dispatchEvent(new InputEvent("beforeinput", { inputType }));
  return {
    model, session, api,
    backspace: key("deleteContentBackward"),
    del: key("deleteContentForward"),
    move: (action) => void editorAction(action).catch(() => {}),
    click: (index) => void session.placeCaret(1000 + index * 100, 1150).catch(() => {}),
    text: () => model.text.join(""),
    deletes: () => model.requests.filter((r) => r.startsWith("delete-")),
  };
}

const flush = async () => { for (let i = 0; i < 4; i += 1) await new Promise((resolve) => setImmediate(resolve)); };
async function advance(ms, step = 5) {
  for (let left = ms; left > 0; left -= step) {
    mock.timers.tick(Math.min(step, left));
    await flush();
  }
}

/** Run `steps` -- [time ms, action] -- then let everything settle. */
async function sequence(p, steps, settleMs = 12000) {
  let at = 0;
  for (const [t, act] of steps) {
    await advance(t - at);
    at = t;
    act();
    await flush();
  }
  await advance(settleMs);
  assert.equal(p.api.held(), 0, "presses still held after everything settled");
  assert.equal(p.api.inFlight(), 0, "deletes still out after everything settled");
  assert.equal(p.session.state.snapshot.state, "ready");
}

async function withTimers(body) {
  const p = await page(body.caret);
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    await body.run(p);
  } finally {
    mock.timers.reset();
  }
}

test("D8 (a): Backspace at the start, Ctrl+End, Backspace -- the third deletes one character at the end", () =>
  withTimers({ caret: 0, run: async (p) => {
    await sequence(p, [[0, p.backspace], [100, () => p.move("move-document-end")], [200, p.backspace]]);
    assert.equal(p.text(), "ABCDEFGHI", `requests: ${p.model.requests.join(", ")}`);
    assert.deepEqual(p.model.requests, ["delete-backward", "move-document-end", "delete-backward"]);
  } }));

test("D8 (b): Backspace at the start, Ctrl+Home, then 18 unflagged Backspaces in one second -- at most 2 deletes reach the engine", () =>
  withTimers({ caret: 0, run: async (p) => {
    const presses = Array.from({ length: 18 }, (_, i) => [150 + 55 * i, p.backspace]);
    await sequence(p, [[0, p.backspace], [100, () => p.move("move-document-start")], ...presses]);
    assert.ok(p.deletes().length <= 2, `${p.deletes().length} deletes reached the engine: ${p.model.requests.join(", ")}`);
    assert.equal(p.text(), TEXT);
  } }));

test("D8 (c): Backspace at the start, Ctrl+End, two Backspaces -- two characters deleted at the end", () =>
  withTimers({ caret: 0, run: async (p) => {
    await sequence(p, [[0, p.backspace], [100, () => p.move("move-document-end")], [200, p.backspace], [300, p.backspace]]);
    assert.equal(p.text(), "ABCDEFGH", `requests: ${p.model.requests.join(", ")}`);
  } }));

test("D8 (d): Backspace at the start, a click in the middle, Backspace -- the delete is at the click", () =>
  withTimers({ caret: 0, run: async (p) => {
    await sequence(p, [[0, p.backspace], [100, () => p.click(5)], [200, p.backspace]]);
    assert.equal(p.text(), "ABCDFGHIJ", `requests: ${p.model.requests.join(", ")}`);
  } }));

test("D8 (e): Backspace, Backspace in text, Ctrl+End, Delete -- the two delete in place, the Delete at the end is a no-op", () =>
  withTimers({ caret: 5, run: async (p) => {
    await sequence(p, [[0, p.backspace], [20, p.backspace], [40, () => p.move("move-document-end")], [60, p.del]]);
    assert.equal(p.text(), "ABCFGHIJ", `requests: ${p.model.requests.join(", ")}`);
    assert.deepEqual(p.model.requests,
                     ["delete-backward", "delete-backward", "move-document-end", "delete-forward"],
                     "a held press went out after the move, or as the other key");
  } }));

test("D8 control (141 T1 kept): a held key at the start with nothing else enqueued is still ONE engine request", () =>
  withTimers({ caret: 0, run: async (p) => {
    const presses = Array.from({ length: 17 }, (_, i) => [500 + 30 * i, p.backspace]);
    await sequence(p, [[0, p.backspace], ...presses]);
    assert.equal(p.deletes().length, 1, p.model.requests.join(", "));
  } }));

test("D8 control (131 kept): presses held inside text are each delivered, in place, one per answer", () =>
  withTimers({ caret: 8, run: async (p) => {
    await sequence(p, [[0, p.backspace], [10, p.backspace], [20, p.backspace]]);
    assert.equal(p.text(), "ABCDEIJ");
    assert.equal(p.deletes().length, 3);
  } }));
