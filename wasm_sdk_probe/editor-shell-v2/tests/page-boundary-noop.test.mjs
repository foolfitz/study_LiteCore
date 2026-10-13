// SPEC-M3-link-batch §10.5 (task 2026-10-13l §4): C's second exit reaches the
// page as a RESOLVED delete -- `editor-action-completed`, completion
// `verified-boundary-noop`, `changed: false`, revision unchanged -- and the page
// must neither toast nor reopen on it.
//
// The page's `run()` is the only place a delete's outcome is turned into a
// toast or a reopen (`reopensAfterRefusal` in its catch), so it is taken from
// the page source and driven here with the completion the engine will send.
// Both halves need a control: the catch path is shown to toast and to reopen
// on the errors it exists for, and a MUTATED copy of `run()` that toasts on
// `changed === false` is shown to fail the same assertion -- the way the
// assertion can go red, since the unmodified page already passes it.
//
// The session's side is pinned too: on the v2 fixture a `delete-backward`
// answered this way resolves through `action()`, the queue stays open and no
// disposition is attached.  What the session does with the completion's
// `changed: false` beyond that (dirty, content stamp) is REPORTED in the
// part-2 README, not asserted here: changing it is a ruling, not this task's.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const PAGE = readFileSync(here("../../web/e2-editor-app.js"), "utf8");

function slice(pattern, what) {
  const match = PAGE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const fn = (name) => slice(new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`);

const NOOP = Object.freeze({
  action: "delete-backward", beforeRevision: 3, revision: 3, changed: false,
  completion: "verified-boundary-noop", boundaryNoop: { waitedMs: 2251 }, state: {},
});

/** The page's run() with every collaborator stubbed and counted. */
function pageRun({ runSource = fn("run") } = {}) {
  const toasts = [];
  const reopens = [];
  const repaints = [];
  const el = { s: { latency: { textContent: "" } } };
  const session = { restartAvailable: () => true };
  // eslint-disable-next-line no-new-func
  const made = new Function("el", "session", "toast", "reopenAfterBoundaryRefusal", "renderDocument",
                            "publishWindow", "describeError", "VIEW_ONLY_TEXT", `
    let changes = 0;
    ${fn("deleteUnverified")}
    ${fn("reopensAfterRefusal")}
    ${runSource}
    return { run, reopensAfterRefusal, changes: () => changes };`)(
    el, session, (message, bad) => toasts.push({ message, bad }), (error) => reopens.push(error),
    async () => repaints.push("repaint"), () => {}, (error) => error?.code ?? String(error), "唯讀");
  return { ...made, toasts, reopens, repaints, el };
}

test("verified-boundary-noop resolves through run(): no toast, no reopen, one repaint, the result returned",
     async () => {
       const page = pageRun();
       const result = await page.run("⌫ 刪除", () => Promise.resolve(NOOP));
       assert.equal(result, NOOP);
       assert.deepEqual(page.toasts, [], "the page toasted on a no-op");
       assert.deepEqual(page.reopens, [], "the page reopened on a no-op");
       assert.deepEqual(page.repaints, ["repaint"], "a completed operation repaints, as every other does");
       assert.equal(page.changes(), 1, "§17.9 (c): a completed operation counts as a change for the bands");
       assert.match(page.el.s.latency.textContent, /^⌫ 刪除 \d+ ms$/);
     });

test("reopensAfterRefusal() is asked about errors, and a noop result is not one", () => {
  const page = pageRun();
  assert.equal(page.reopensAfterRefusal(NOOP), false);
  assert.equal(page.reopensAfterRefusal({ code: "EDITOR_BOUNDARY_UNSUPPORTED" }), true);
  assert.equal(page.reopensAfterRefusal({ code: "EDITOR_STATE_UNAVAILABLE", recovery: "restart" }), true);
  assert.equal(page.reopensAfterRefusal({ code: "EDITOR_STATE_UNAVAILABLE" }), false);
});

test("control: the catch path still reopens on EDITOR_BOUNDARY_UNSUPPORTED and toasts on anything else",
     async () => {
       const page = pageRun();
       const boundary = Object.assign(new Error("boundary"), { code: "EDITOR_BOUNDARY_UNSUPPORTED" });
       await assert.rejects(() => page.run("⌫ 刪除", () => Promise.reject(boundary)), boundary);
       assert.deepEqual(page.reopens, [boundary]);
       assert.deepEqual(page.toasts, [], "a refusal that reopens is worded by the reopen, not here");
       const other = Object.assign(new Error("no"), { code: "LOK_COMMAND_FAILED", recovery: "review" });
       await assert.rejects(() => page.run("⌫ 刪除", () => Promise.reject(other)), other);
       assert.equal(page.toasts.length, 1);
       assert.equal(page.reopens.length, 1, "a review-disposition error must not reopen");
       assert.deepEqual(page.repaints, [], "a failed operation is not repainted by run()");
     });

test("the assertion has teeth: a run() that toasts on changed === false fails it", async () => {
  const original = fn("run");
  const mutated = original.replace(
    "    const result = await operation();\n",
    "    const result = await operation();\n"
    + "    if (result?.changed === false) toast(\"這一下沒有改動文件\");\n");
  assert.notEqual(mutated, original, "the mutation found nothing to change -- run() moved");
  const page = pageRun({ runSource: mutated });
  await page.run("⌫ 刪除", () => Promise.resolve(NOOP));
  assert.equal(page.toasts.length, 1, "the mutated page did not toast, so the test above proves nothing");
});

/* ------------------------------------------------ the session's side, v2 fixture */

const manifestOf = (profile) => JSON.parse(readFileSync(
  here(`../../dist/profiles/${profile}/sdk-manifest.json`), "utf8"));

function fixture() {
  let revision = 0;
  const editorState = () => ({
    documentHandle: 1, revision, sourceSequence: 1, documentChangeSequence: 0,
    documentSizeChangedCount: 0, caret: null,
    selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
    selectionType: "none", selectionTextMissing: false, selectionText: "",
    format: { bold: false, italic: false },
  });
  const document = {
    handle: 1, revision: 0, widthTwips: 12474, heightTwips: 1027604,
    _assertUsable() {},
    async render() { return { pixels: new ArrayBuffer(4), revision }; },
    async save() { return new ArrayBuffer(16); },
    async close() {},
  };
  const engine = {
    manifest: manifestOf("e2-editor-v2"),
    onEvent() { return () => {}; },
    async open() { revision = 0; document.revision = 0; return document; },
    async _request(operation, payload) {
      if (operation === "editorGetStateV2") return editorState();
      if (operation === "editorSelectRangeV2") return { revision };
      if (payload.action === "delete-backward" || payload.action === "delete-forward") {
        // C's second exit: the engine waited out the window and nothing was selected.
        return { action: payload.action, beforeRevision: payload.expectedRevision, revision,
                 changed: false, completion: "verified-boundary-noop",
                 boundaryNoop: { waitedMs: 2251 }, state: editorState() };
      }
      document.revision = ++revision;
      return { action: payload.action, beforeRevision: payload.expectedRevision, revision,
               changed: true, completion: "uno-command-result", state: editorState() };
    },
    dispose() {},
  };
  document._engine = engine;
  const session = new NarrowEditorV2Session({
    engineFactory: async () => engine, secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } },
  });
  return { session, document };
}

for (const action of ["delete-backward", "delete-forward"]) {
  test(`session: ${action} answered verified-boundary-noop resolves, the queue stays open, no disposition`,
       async () => {
         const { session } = fixture();
         await session.open({ bytes: new ArrayBuffer(8), name: "d.odt" });
         const result = await session.action(action, {});
         assert.equal(result.completion, "verified-boundary-noop");
         assert.equal(result.changed, false);
         assert.equal(result.boundaryNoop.waitedMs, 2251);
         assert.equal(session.state.snapshot.state, "ready", "the queue must not block");
         assert.equal(session.state.snapshot.revision, 0, "the revision must not move");
         assert.equal(session.state.snapshot.error, null);
         assert.equal(session.boundaryRefusalCheckpoints, 0, "no refusal checkpoint: nothing was refused");
         // And the next edit goes through: the session is alive.
         const next = await session.action("set-bold", { enabled: true });
         assert.equal(next.changed, true);
         assert.equal(session.state.snapshot.revision, 1);
       });
}
