// SPEC-P-ms-formats 5.2, the session's half: every save of a document is in
// the format the engine opened it as, and Save As is a copy that changes
// nothing in the session.
//
// `NarrowEditorV2Session.save()` and `_checkpointBeforeSelection()` are the
// base class's methods with the format token changed (the base is bound by
// E1-C and passes "odt").  So the first two tests run the BASE's method and the
// override side by side on an ODT document and require the same requests and
// the same state; the rest show the override doing what the base cannot, and
// the base failing it (the causal control: without the override a DOCX would
// be saved, checkpointed and rescued as ODT).

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorV2Session, documentFormatOf } from "../narrow-editor-v2-session.js";
import { EditorSession } from "../../editor-shell/editor-session.js";
import { DocumentHandle } from "../../sdk/document-sdk.js";

const V2_MANIFEST = JSON.parse(readFileSync(fileURLToPath(
  new URL("../../dist/profiles/e2-editor-v2/sdk-manifest.json", import.meta.url)), "utf8"));

const text = (buffer) => new TextDecoder().decode(new Uint8Array(buffer));

function editorState(revision) {
  return { documentHandle: 1, revision, caret: null,
           selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
           selectionType: "none", selectionTextMissing: false, selectionText: "",
           format: { bold: false, italic: false } };
}

// The v2 worker's answers, as narrow-editor-v2-session.test.mjs models them; a
// save returns its own format and the revision it saw, so a test can tell
// which save produced which bytes.
function fixture({ format } = {}) {
  const saves = [];
  const opens = [];
  let revision = 0;
  const document = {
    handle: 1, revision: 0, widthTwips: 1000, heightTwips: 2000, format,
    _assertUsable() {},
    async render() { return { pixels: new ArrayBuffer(4), revision }; },
    async save(formatOptions, requestOptions) {
      saves.push({ formatOptions: { ...formatOptions }, timeoutMs: requestOptions?.timeoutMs });
      return new TextEncoder().encode(`${formatOptions.format}@${revision}`).buffer;
    },
    async getSelection() { return { text: "", selectionType: "text", revision }; },
    async close() {},
  };
  const engine = {
    manifest: V2_MANIFEST,
    onEvent() { return () => {}; },
    async open(bytes, options) {
      opens.push({ name: options?.name, bytes: text(bytes) });
      revision = 0; document.revision = 0;
      return document;
    },
    async _request(operation, payload) {
      if (operation === "editorGetStateV2") return editorState(revision);
      if (operation === "editorSelectRangeV2") return { revision };
      document.revision = ++revision;
      return { action: payload.action, beforeRevision: payload.expectedRevision, revision,
               changed: true, completion: "uno-command-result", state: editorState(revision) };
    },
    dispose() {},
  };
  document._engine = engine;
  const session = new NarrowEditorV2Session({
    engineFactory: async () => engine,
    secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } },
  });
  return { session, document, saves, opens };
}

async function opened(options = {}) {
  const f = fixture(options);
  await f.session.open({ bytes: new TextEncoder().encode("original").buffer,
                         name: options.name ?? "d.odt" });
  return f;
}

// What a save or a checkpoint leaves behind, everything the base touches.
function after(f) {
  const s = f.session;
  const snap = s.state.snapshot;
  return {
    saves: f.saves,
    dirty: snap.dirty, hasSavedBytes: snap.hasSavedBytes, hasCheckpoint: snap.hasCheckpoint,
    checkpointRevision: snap.checkpointRevision, checkpointError: snap.checkpointError,
    authority: s._authorityBytes && text(s._authorityBytes), authorityStamp: s._authorityStamp,
    checkpoint: s._checkpointBytes && text(s._checkpointBytes), checkpointStamp: s._checkpointStamp,
  };
}

test("the SDK handle keeps the open reply's format, and only a non-empty string", () => {
  const engine = { _generation: 0 };
  const handle = (metadata) => new DocumentHandle(engine, 0, { documentHandle: 1, revision: 0, ...metadata });
  assert.equal(handle({ format: "docx" }).format, "docx");
  assert.equal(handle({}).format, null);
  assert.equal(handle({ format: "" }).format, null);
  assert.equal(handle({ format: ["docx"] }).format, null);
  assert.equal(documentFormatOf({ format: "docx" }), "docx");
  assert.equal(documentFormatOf({ format: null }), "odt");
  assert.equal(documentFormatOf(null), "odt");
});

test("ODT: the override's save is the base's save -- same request, same state", async () => {
  const base = await opened();
  const mine = await opened();
  // A checkpoint first (the base's own), so the save has one to clear.
  for (const f of [base, mine]) {
    await f.session.action("insert-line-break");
    await EditorSession.prototype._checkpointBeforeSelection.call(f.session, f.session.document);
    await f.session.action("insert-line-break");
    assert.equal(f.session.state.snapshot.hasCheckpoint, true);
  }
  await EditorSession.prototype.save.call(base.session);
  await mine.session.save();
  assert.deepEqual(after(mine), after(base));
  assert.deepEqual(mine.saves.at(-1), { formatOptions: { format: "odt" }, timeoutMs: 180000 });
  assert.equal(mine.session.state.snapshot.dirty, false);
  assert.equal(after(mine).checkpoint, null);
});

test("ODT: the override's checkpoint is the base's checkpoint -- same request, same state", async () => {
  const base = await opened();
  const mine = await opened();
  for (const f of [base, mine]) await f.session.action("insert-line-break");
  await EditorSession.prototype._checkpointBeforeSelection.call(base.session, base.session.document);
  await mine.session._checkpointBeforeSelection(mine.session.document);
  assert.deepEqual(after(mine), after(base));
  assert.equal(after(mine).hasCheckpoint, true);
  // and a failed one is reported the same way
  const failing = async () => { throw Object.assign(new Error("no"), { code: "SAVE_FAILED" }); };
  for (const f of [base, mine]) { f.document.save = failing; await f.session.action("insert-line-break"); }
  await EditorSession.prototype._checkpointBeforeSelection.call(base.session, base.session.document);
  await mine.session._checkpointBeforeSelection(mine.session.document);
  assert.deepEqual(mine.session.state.snapshot.checkpointError, base.session.state.snapshot.checkpointError);
  assert.equal(mine.session.state.snapshot.checkpointError.code, "SAVE_FAILED");
});

test("DOCX: save, checkpoint and the generation-ceiling rescue are all DOCX; the base's are not", async () => {
  const f = await opened({ format: "docx", name: "report.docx" });
  assert.equal(f.session.documentFormat(), "docx");
  await f.session.action("insert-line-break");
  await f.session._checkpointBeforeSelection(f.session.document);
  assert.equal(f.saves.at(-1).formatOptions.format, "docx");
  await f.session.action("insert-line-break");
  const saved = await f.session.save();
  assert.equal(text(saved.bytes), "docx@2");
  // A checkpoint newer than the save, then a stopped session: the rescue hands
  // the host the checkpoint, and it is the document's format.
  await f.session.action("insert-line-break");
  await f.session._checkpointBeforeSelection(f.session.document);
  f.session.state.transition("recoverable-error", { error: { code: "TIMEOUT" } });
  assert.equal(text(f.session.takeContentForRescue()), "docx@3");

  // Causal control: the base's methods on the same kind of document write ODT.
  const control = await opened({ format: "docx", name: "report.docx" });
  await control.session.action("insert-line-break");
  await EditorSession.prototype._checkpointBeforeSelection.call(control.session, control.session.document);
  await EditorSession.prototype.save.call(control.session);
  assert.deepEqual(control.saves.map((s) => s.formatOptions.format), ["odt", "odt"]);
});

test("DOCX: a recovery reopen reads the checkpoint under the document's own name", async () => {
  const f = await opened({ format: "docx", name: "report.docx" });
  await f.session.action("insert-line-break");
  await f.session._checkpointBeforeSelection(f.session.document);
  f.session.state.transition("recoverable-error", { error: { code: "TIMEOUT" } });
  await f.session.restart();
  assert.deepEqual(f.opens.at(-1), { name: "report.docx", bytes: "docx@1" });
});

test("Save As is a copy: the chosen format, and the session's state and bytes untouched", async () => {
  const f = await opened({ format: "docx", name: "report.docx" });
  await f.session.action("insert-line-break");
  const before = after(f);
  const copy = await f.session.saveCopy("odt");
  assert.equal(copy.format, "odt");
  assert.equal(text(copy.bytes), "odt@1");
  const { saves, ...rest } = after(f);
  const { saves: savesBefore, ...restBefore } = before;
  assert.deepEqual(rest, restBefore);
  assert.equal(f.session.state.snapshot.dirty, true, "a copy is not a save of this document");
  assert.equal(f.session.hasUnsavedEdits(), true);
  // The next save is still the document's own format.
  await f.session.save();
  assert.equal(f.saves.at(-1).formatOptions.format, "docx");
  await assert.rejects(f.session.saveCopy(""), { code: "INVALID_ARGUMENT" });
});

test("a copy waits its turn in the queue behind the edit before it", async () => {
  const f = await opened({ format: "docx", name: "report.docx" });
  const edit = f.session.action("insert-line-break");
  const copy = f.session.saveCopy("odt");
  await edit;
  assert.equal(text((await copy).bytes), "odt@1");
});
