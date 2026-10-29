// FINDING 150 (SPEC-M3-link-batch-v21 §12.3 (a); fable ruling 1, Q1, condition 1).
//
// A move key pressed while a delete this page sent was still out read the
// delete barrier's one-character selection as the user's range, took finding
// 129's click-then-move path (`moveFromPoint`), clicked at a caret read before
// the delete answered, and the Delete pressed next ran at that click instead of
// after the move (findings/evidence/link-batch-v21/shakedown/diag-dirty-move/:
// V6e with ArrowRight and D8 (e) with Ctrl+End on v21's page; V6e on 0.2.24's
// page as well, 6/6).  The fix is finding 131's rule A -- while a delete is out,
// the engine's range is not the user's -- in ONE predicate both move paths
// decide by, so the arrows' path and `sendDocumentMove` cannot drift again.
//
//   * the predicate itself, as a table;
//   * each path (an arrow, Ctrl+End), through the page's own keydown listener:
//     the barrier's range with a delete out -> no click, the move goes straight
//     out; a real range with no delete out -> click, then move; a caret ->
//     straight out;
//   * D8 (e) (Backspace, Backspace, Ctrl+End, Delete) and V6e (the same with
//     ArrowRight) as timed sequences: the keys act in the order pressed.
//
// The keydown listener, `takeDocumentKey`, `sendDocumentMove`, `moveFromPoint`
// and the delete path (`beforeinput`, `dispatchDelete`, the holds) are sliced
// from the page source and run against the REAL NarrowEditorV2Session, its
// queue and its `beforeEnqueue` hook, over a fake engine that keeps a
// ten-character paragraph and -- like the v21 engine -- announces the delete
// barrier's one-character selection as editor state while the delete is out
// (`editor-state`, the session's `_handleEngineEvent`).  Mocked time.
//
// `PAGE_SOURCE=<path>` runs the same cases against another page.  On the page
// before this change (HEAD e25ccc15) the predicate is absent and every
// barrier case and both sequences are red: the witness the ruling requires,
// kept in findings/evidence/link-batch-v21/fixes-ruling-1/.

import assert from "node:assert/strict";
import { mock, test } from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorV2Session, selectionShapeOf } from "../narrow-editor-v2-session.js";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const SOURCE = readFileSync(process.env.PAGE_SOURCE || here("../../web/e2-editor-app.js"), "utf8");
const V21 = JSON.parse(readFileSync(here("../../dist/profiles/e2-editor-v21/sdk-manifest.json"), "utf8"));

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const optional = (pattern) => (SOURCE.match(pattern) || [""])[0];
const fn = (name) => new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m");
const KEYDOWN = /^el\.sink\.addEventListener\("keydown", \(event\) => \{[\s\S]*?\n\}\);$/m;

const WINDOW_MS = 2250;      // C: 250 + 2,000 ms at a document boundary (SPEC-M3-link-batch §10.5)
const DELETE_MS = 66;        // a verified delete inside text (finding 132)
const BARRIER_MS = 5;        // the barrier's selection is announced before the delete answers
const READBACK_MS = 250;     // a move with nowhere to go (finding 096)
const MOVE_MS = 5;
const CLICK_MS = 25;
const SAVE_MS = 5;
const REPAINT_MS = 10;
const TEXT = "ABCDEFGHIJ";
const twipsOf = (index) => 1000 + index * 100;

class InputEvent {
  constructor(type, init = {}) { this.type = type; this.inputType = init.inputType; this.defaultPrevented = false; }
  preventDefault() { this.defaultPrevented = true; }
}

/**
 * The fake engine: a ten-character paragraph, a caret index, an optional
 * selection [start, end), and the v21 answers.  A delete inside text first
 * selects the character it removes -- the barrier -- and announces that
 * selection, then answers collapsed.
 */
function engineFor(model) {
  const listeners = [];
  const caretRect = () => ({ x: twipsOf(model.caret), y: 1000, width: 0, height: 300 });
  const selectionOf = () => (model.range === null
    ? { observed: true, collapsed: true, start: null, end: null, rectangles: [] }
    : { observed: true, collapsed: false, start: null, end: null,
        rectangles: [{ x: twipsOf(model.range[0]), y: 1000, width: (model.range[1] - model.range[0]) * 100, height: 300 }] });
  const stateOf = () => ({
    documentHandle: 1, revision: model.revision, sourceSequence: model.sequence,
    documentChangeSequence: model.revision, caret: caretRect(), selection: selectionOf(),
    selectionType: model.range === null ? "none" : "text", selectionTextMissing: false, selectionText: "",
    format: { bold: false, italic: false },
  });
  const announce = () => {
    model.sequence += 1;
    const state = stateOf();
    for (const listener of listeners) listener({ event: "editor-state", ...state });
  };
  model.announce = announce;
  const later = (ms, answer) => new Promise((resolve) => setTimeout(() => resolve(answer()), ms));
  const document = {
    handle: 1, revision: 0, widthTwips: 12000, heightTwips: 16000,
    _assertUsable() {},
    async render() { return { pixels: new ArrayBuffer(4), revision: model.revision }; },
    save() { model.saves += 1; return later(SAVE_MS, () => new ArrayBuffer(8)); },
    // The click on an open range (the session's polling path): collapses it at the point.
    click(xTwips) {
      model.requests.push("click");
      return later(CLICK_MS, () => {
        model.range = null;
        model.caret = Math.max(0, Math.min(model.text.length, Math.round((xTwips - 1000) / 100)));
        model.sequence += 1;
      });
    },
    async close() {},
  };
  const moved = (payload, at) => () => {
    const stays = model.caret === at;
    model.caret = at;
    model.range = null;
    if (!stays) model.sequence += 1;
    return { action: payload.action, beforeRevision: payload.expectedRevision, revision: model.revision,
             changed: false, completion: stays ? "verified-move-readback" : "documented-callback-visible-cursor",
             state: stateOf() };
  };
  const noop = (payload) => () => ({
    action: payload.action, beforeRevision: payload.expectedRevision, revision: model.revision, changed: false,
    completion: "verified-boundary-noop", boundaryNoop: { waitedMs: WINDOW_MS }, state: stateOf() });
  const deleted = (payload, at) => {
    setTimeout(() => { model.range = [at, at + 1]; announce(); }, BARRIER_MS);
    return later(DELETE_MS, () => {
      model.text.splice(at, 1);
      model.caret = at;
      model.range = null;
      model.revision += 1;
      model.sequence += 1;
      return { action: payload.action, beforeRevision: payload.expectedRevision, revision: model.revision,
               changed: true, completion: "verified-selection-delete", state: stateOf() };
    });
  };
  const engine = {
    manifest: V21,
    onEvent(listener) { listeners.push(listener); return () => {}; },
    async open() { document.revision = model.revision; return document; },
    async _request(operation, payload) {
      if (operation === "editorGetStateV2") return stateOf();
      if (operation === "editorPlaceCaretV2") {
        model.requests.push("place-caret");
        return later(CLICK_MS, () => {
          model.range = null;
          model.caret = Math.max(0, Math.min(model.text.length, Math.round((payload.xTwips - 1000) / 100)));
          model.sequence += 1;
          return { revision: model.revision, completion: "documented-callback-visible-cursor", state: stateOf() };
        });
      }
      assert.equal(operation, "editorActionV2");
      const { action } = payload;
      model.requests.push(action);
      const end = model.text.length;
      const step = (to) => later(model.caret === to ? READBACK_MS : MOVE_MS, moved(payload, to));
      if (action === "move-document-start") return step(0);
      if (action === "move-document-end") return step(end);
      if (action === "move-character-right") return step(Math.min(end, model.caret + 1));
      if (action === "move-character-left") return step(Math.max(0, model.caret - 1));
      if (action === "delete-backward")
        return model.caret === 0 ? later(WINDOW_MS, noop(payload)) : deleted(payload, model.caret - 1);
      if (action === "delete-forward")
        return model.caret === end ? later(WINDOW_MS, noop(payload)) : deleted(payload, model.caret);
      throw new Error(`the fake engine does not do ${action}`);
    },
    dispose() {},
  };
  document._engine = engine;
  return engine;
}

/** The page's key and delete paths, compiled from the page source, over the real session. */
async function page(caret) {
  const model = { text: [...TEXT], caret, range: null, revision: 0, sequence: 1, saves: 0, requests: [] };
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
  // The page's editorAction, as far as these paths can see it: the session's
  // action, `onResult` at the engine's answer, the repaint after.
  const editorAction = (action, options = {}) => {
    if (!["ready", "busy"].includes(session.state.snapshot.state)) return Promise.resolve();
    return session.action(action, {})
      .then((result) => { options.onResult?.(result); return result; })
      .then((result) => new Promise((resolve) => setTimeout(() => resolve(result), REPAINT_MS)));
  };
  const run = (label, operation) => operation();
  // eslint-disable-next-line no-new-func
  const api = new Function("el", "session", "selectionShapeOf", "editorAction", "paint", "run", "saveDocument",
                           "updateGestureAffordance", `
    ${slice(/^const DELETE_INPUT_TYPES = \{[\s\S]*?\n\};$/m, "DELETE_INPUT_TYPES")}
    let lastSelectionShape = "collapsed"; let deletesInFlight = 0; let deleteRefusedThisHold = false;
    let pointMovesInFlight = 0;
    ${optional(/^let deletesUnanswered = 0;$/m)}
    ${slice(/^const heldDeletes = \{[^\n]*\};$/m, "heldDeletes")}
    ${slice(fn("deleteActionFor"), "deleteActionFor()")}
    ${["deleteStateOf", "boundaryNoopStands", "holdsDelete", "dropHeldDeletes", "releaseHeldDelete",
       "releaseHeldDeletesBeforeEnqueue", "settleDelete", "dispatchDelete"]
      .map((name) => optional(fn(name))).join("\n")}
    ${slice(/^el\.sink\.addEventListener\("beforeinput", \(event\) => \{[\s\S]*?\n\}\);$/m, "the beforeinput handler")}
    ${slice(/^const SESSION_ACCEPTS = new Set\([^\n]*\);$/m, "SESSION_ACCEPTS")}
    ${slice(/^const KEY_ACTIONS = \{[\s\S]*?\n\};$/m, "KEY_ACTIONS")}
    ${slice(/^const DOCUMENT_KEY_ACTIONS = \{[^\n]*\};$/m, "DOCUMENT_KEY_ACTIONS")}
    ${slice(/^const documentMovesUnanswered = new Map\(\);$/m, "documentMovesUnanswered")}
    ${optional(fn("clicksBeforeMove"))}
    ${slice(fn("moveFromPoint"), "moveFromPoint()")}
    ${["documentKeyAction", "dropsDocumentMove", "sendDocumentMove", "takeDocumentKey"]
      .map((name) => slice(fn(name), `${name}()`)).join("\n")}
    ${/* SPEC-M3-select-all-v26 4.4: the handler takes Ctrl+A first (no key here is Ctrl+A);
         optional, so a generation-79 page restored for V0' still assembles. */ ""}
    ${optional(/^const SELECT_ALL_NOTHING_TEXT = [^\n]*;$/m)}
    ${optional(/^const SELECT_ALL_UNOBSERVED_TEXT = [^\n]*;$/m)}
    ${["selectAllKey", "selectAllResult", "takeSelectAllKey"].map((name) => optional(fn(name))).join("\n")}
    ${slice(KEYDOWN, "the keydown handler")}
    return { hook: typeof releaseHeldDeletesBeforeEnqueue === "function" ? releaseHeldDeletesBeforeEnqueue : null,
             held: () => heldDeletes.count, inFlight: () => deletesInFlight, pointMoves: () => pointMovesInFlight };
  `)({ sink }, session, selectionShapeOf, editorAction, () => {}, run, async () => {}, () => {});
  hook = api.hook;
  const input = (inputType) => () => sink.dispatchEvent(new InputEvent("beforeinput", { inputType }));
  const key = (name, ctrl = false) => () => sink.dispatchEvent({
    type: "keydown", key: name, ctrlKey: ctrl, metaKey: false, shiftKey: false, altKey: false,
    isComposing: false, repeat: false, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } });
  return {
    model, session, api,
    backspace: input("deleteContentBackward"),
    del: input("deleteContentForward"),
    arrowRight: key("ArrowRight"),
    ctrlEnd: key("End", true),
    /** A drag that selected [start, end), the caret at its end, announced as the engine does. */
    drag: (start, end) => () => { model.range = [start, end]; model.caret = end; model.announce(); },
    text: () => model.text.join(""),
    clicks: () => model.requests.filter((r) => r === "place-caret" || r === "click"),
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
  assert.equal(p.api.pointMoves(), 0, "a point move still queued after everything settled");
  assert.equal(p.session.state.snapshot.state, "ready");
}

async function withTimers(caret, body) {
  const p = await page(caret);
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    await body(p);
  } finally {
    mock.timers.reset();
  }
}

// ------------------------------------------------------------ the predicate

test("finding 150: one predicate, and both move paths decide by it", () => {
  const predicate = slice(fn("clicksBeforeMove"), "clicksBeforeMove()");
  // eslint-disable-next-line no-new-func
  const clicksBeforeMove = new Function(`${predicate}\nreturn clicksBeforeMove;`)();
  const offered = ["collapsed"];
  for (const [shape, gestures, pointMoves, deletes, expected, why] of [
    ["range-single", offered, 0, 0, true, "a real range the move is not offered on: click, then move"],
    ["range-cross", offered, 0, 0, true, "the same across paragraphs"],
    ["range-single", offered, 0, 1, false, "rule A: a delete is out, its barrier's range is not the user's"],
    ["range-cross", offered, 0, 3, false, "rule A, more than one delete out"],
    ["collapsed", offered, 0, 0, false, "a caret: straight out"],
    ["collapsed", offered, 0, 1, false, "a caret with a delete out: straight out"],
    ["range-single", offered, 1, 0, false, "a point move already queued: behind it, on its caret (finding 129)"],
    ["range-single", ["collapsed", "range-single"], 0, 0, false, "a profile that offers the move on a range"],
    ["range-single", null, 0, 0, false, "a profile that does not say"],
  ]) assert.equal(clicksBeforeMove(shape, gestures, pointMoves, deletes), expected, why);
  const keydown = slice(KEYDOWN, "the keydown handler");
  const send = slice(fn("sendDocumentMove"), "sendDocumentMove()");
  for (const [where, body] of [["the arrows' path", keydown], ["sendDocumentMove", send]]) {
    assert.match(body, /clicksBeforeMove\(shape, gestures, pointMovesInFlight, deletesInFlight\)/,
                 `${where} does not decide by the shared predicate`);
    assert.doesNotMatch(body, /pointMovesInFlight === 0/, `${where} still carries its own copy of the decision`);
  }
});

// ------------------------------------------------- each path, three shapes

for (const [label, press, action] of [["an arrow", "arrowRight", "move-character-right"],
                                      ["Ctrl+End", "ctrlEnd", "move-document-end"]]) {
  test(`finding 150 (${label}): the barrier's range with a delete out -- no click, the move goes straight out`, () =>
    withTimers(5, async (p) => {
      await sequence(p, [[0, p.backspace], [20, () => {
        assert.equal(selectionShapeOf({ state: p.session.state.snapshot.editorState }), "range-single",
                     "the fixture did not put the barrier's range in the snapshot");
        p[press]();
      }]]);
      assert.deepEqual(p.clicks(), [], `requests: ${p.model.requests.join(", ")}`);
      assert.deepEqual(p.model.requests, ["delete-backward", action]);
      assert.equal(p.text(), "ABCDFGHIJ");
    }));

  test(`finding 150 (${label}): a real range with no delete out -- click at the point, then move (finding 129 kept)`, () =>
    withTimers(2, async (p) => {
      await sequence(p, [[0, p.drag(2, 6)], [20, p[press]]]);
      assert.deepEqual(p.model.requests, ["click", action]);
      assert.equal(p.text(), TEXT);
    }));

  test(`finding 150 (${label}): a caret -- straight out`, () =>
    withTimers(5, async (p) => {
      await sequence(p, [[0, p[press]]]);
      assert.deepEqual(p.model.requests, [action]);
    }));
}

// ------------------------------------------------------------ the sequences

test("finding 150, D8 (e): Backspace, Backspace in text, Ctrl+End, Delete -- in key order, the Delete at the end a no-op", () =>
  withTimers(5, async (p) => {
    await sequence(p, [[0, p.backspace], [20, p.backspace], [40, p.ctrlEnd], [60, p.del]]);
    assert.deepEqual(p.clicks(), [], `requests: ${p.model.requests.join(", ")}; text: ${p.text()}`);
    assert.equal(p.text(), "ABCFGHIJ", `requests: ${p.model.requests.join(", ")}`);
    assert.deepEqual(p.model.requests, ["delete-backward", "delete-backward", "move-document-end", "delete-forward"]);
  }));

test("finding 150, V6e: Backspace, Backspace in text, ArrowRight, Delete -- in key order", () =>
  withTimers(5, async (p) => {
    await sequence(p, [[0, p.backspace], [20, p.backspace], [40, p.arrowRight], [60, p.del]]);
    assert.deepEqual(p.clicks(), [], `requests: ${p.model.requests.join(", ")}; text: ${p.text()}`);
    // ABCDEFGHIJ, caret after E: -E, -D, right of F, then G is deleted.
    assert.equal(p.text(), "ABCFHIJ", `requests: ${p.model.requests.join(", ")}`);
    assert.deepEqual(p.model.requests,
                     ["delete-backward", "delete-backward", "move-character-right", "delete-forward"]);
  }));

test("finding 150, range control: a drag, then ArrowRight and Delete -- still click, move, delete", () =>
  withTimers(2, async (p) => {
    await sequence(p, [[0, p.drag(2, 6)], [20, p.arrowRight], [400, p.del]]);
    assert.deepEqual(p.model.requests, ["click", "move-character-right", "delete-forward"]);
    // The click collapses at the point (6), the move goes to 7, Delete removes H.
    assert.equal(p.text(), "ABCDEFGIJ");
  }));
