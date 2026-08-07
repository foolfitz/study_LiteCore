import assert from "node:assert/strict";
import test from "node:test";

import {
  EDITOR_V1_ACTIONS,
  NarrowEditorClient,
} from "../editor-client.js";

function fixture(overrides = {}) {
  const requests = [];
  const engine = {
    manifest: {
      profile: "e1-editor-v1",
      capabilities: ["narrow-editor-v1"],
      editorContract: { version: 1 },
    },
    async _request(operation, payload) {
      requests.push({ operation, payload });
      if (operation === "editorSelectRangeV1")
        return { method: "text-handles-unstable", completion: overrides.selectCompletion
          ?? "documented-callback-text-selection" };
      if (operation === "editorGetStateV1") {
        if (overrides.state)
          return { documentHandle: 9, revision: document.revision, format: {}, ...overrides.state };
        return {
          documentHandle: 9,
          revision: document.revision,
          sourceSequence: 3,
          documentChangeSequence: 1,
          visible: true,
          caret: null,
          selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
          selectionType: "none",
          selectionTextMissing: false,
          selectionText: "",
          format: { bold: false, italic: false },
        };
      }
      // The engine used to answer set-bold / set-italic with
      // `documented-state-noop` when the cached value already matched.  Finding
      // 022 showed it could only produce that from a stale cache, so both the
      // shortcut and the client's acceptance of it were removed on 2026-08-06.
      // Every mutation now changes the document and says so.
      const mutation = !payload.action.startsWith("move-");
      return {
        action: payload.action,
        beforeRevision: payload.expectedRevision,
        revision: payload.expectedRevision + (mutation ? 1 : 0),
        changed: mutation,
        completion: payload.action.startsWith("delete-")
          ? "verified-selection-delete"
          : payload.action.startsWith("move-")
            ? "documented-callback-visible-cursor"
            : "uno-command-result",
        state: { selection: { collapsed: true }, format: { bold: false, italic: false } },
      };
    },
    ...overrides.engine,
  };
  const document = {
    _engine: engine,
    handle: 9,
    revision: 4,
    _assertUsable() {},
    ...overrides.document,
  };
  return { client: new NarrowEditorClient(document), document, requests };
}

// Underline and strikethrough were added on 2026-08-07.  This list is frozen on
// purpose: widening it is a contract change, so the test is meant to fail until
// someone edits it deliberately -- which is exactly what it did.
test("product action list is frozen and contains only the approved actions", () => {
  assert.equal(Object.isFrozen(EDITOR_V1_ACTIONS), true);
  assert.deepEqual(EDITOR_V1_ACTIONS, [
    "move-character-left", "move-character-right",
    "delete-backward", "delete-forward",
    "insert-paragraph-break", "insert-line-break",
    "set-bold", "set-italic", "set-underline", "set-strikethrough",
  ]);
});

test("closed movement request carries no key code or UNO escape hatch", async () => {
  const { client, requests } = fixture();
  const result = await client.moveCharacter("left", { extendSelection: true });
  assert.equal(result.revision, 4);
  assert.deepEqual(requests[0], {
    operation: "editorActionV1",
    payload: {
      documentHandle: 9,
      expectedRevision: 4,
      action: "move-character-left",
      extendSelection: true,
      enabled: false,
    },
  });
  assert.equal("keyCode" in requests[0].payload, false);
  assert.equal("unoCommand" in requests[0].payload, false);
});

test("delete requires the verified-selection completion and advances revision once", async () => {
  const value = fixture();
  await value.client.delete("forward");
  assert.equal(value.document.revision, 5);

  const bad = fixture({
    engine: {
      manifest: value.document._engine.manifest,
      async _request(_operation, payload) {
        return {
          action: payload.action,
          beforeRevision: payload.expectedRevision,
          revision: payload.expectedRevision + 1,
          changed: true,
          completion: "dispatch-return-only",
          state: {},
        };
      },
    },
  });
  await assert.rejects(() => bad.client.delete("forward"), { code: "EDITOR_RESULT_INVALID" });
});

test("format requires an explicit boolean and always reports a change", async () => {
  // Until 2026-08-06 this asserted the opposite for enabled:false -- a typed
  // no-op with changed:false and an unmoved revision.  Finding 022 showed that
  // reply was only ever produced from a stale cache, so it no longer exists:
  // the command dispatches either way and the revision advances.
  const { client, document } = fixture();
  await assert.rejects(() => client.action("set-bold"), { code: "INVALID_ARGUMENT" });
  const result = await client.setInlineFormat("bold", false);
  assert.equal(result.changed, true);
  assert.equal(result.completion, "uno-command-result");
  assert.equal(document.revision, 5);
});

test("unsupported capabilities and malformed options fail before dispatch", async () => {
  const { client, requests } = fixture();
  await assert.rejects(() => client.action("redo"), { code: "EDITOR_ACTION_UNSUPPORTED" });
  await assert.rejects(
    () => client.action("delete-forward", { extendSelection: true }),
    { code: "INVALID_ARGUMENT" },
  );
  assert.equal(requests.length, 0);

  const unavailable = fixture();
  unavailable.document._engine.manifest.capabilities = [];
  await assert.rejects(() => unavailable.client.getState(), { code: "UNSUPPORTED_OPERATION" });
});

test("typed state readback updates the document revision", async () => {
  const { client, document, requests } = fixture();
  const state = await client.getState();
  assert.equal(state.selectionType, "none");
  assert.equal(document.revision, 4);
  assert.deepEqual(requests[0], {
    operation: "editorGetStateV1",
    payload: { documentHandle: 9 },
  });
});

test("a documented-state-noop reply is rejected: finding 022 must not come back", () => {
  // The silent no-op this replaces was not a hypothetical -- it shipped, and it
  // left the document unchanged while reporting success.  If the engine ever
  // emits that completion again the client has to refuse it rather than pass it
  // through as a successful edit.
  const { client } = fixture({
    engine: {
      async _request(_operation, payload) {
        return {
          action: payload.action,
          beforeRevision: payload.expectedRevision,
          revision: payload.expectedRevision,
          changed: false,
          completion: "documented-state-noop",
          state: { selection: { collapsed: true }, format: { bold: true, italic: false } },
        };
      },
    },
  });
  assert.rejects(
    () => client.setInlineFormat("bold", true),
    (error) => error.code === "INVALID_RESULT" || /postcondition/.test(error.message),
  );
});

test("selectRange reports what the engine read back, not that the call returned", async () => {
  const { client, requests } = fixture({
    state: {
      selection: {
        observed: true, collapsed: false, start: null, end: null,
        rectangles: [{ x: 1418, y: 1807, width: 1426, height: 275 }],
      },
      selectionType: "text",
      selectionText: "ASCII abc XY",
      caret: { x: 2844, y: 1807, width: 0, height: 276 },
    },
  });
  const result = await client.selectRange({ xTwips: 1418, yTwips: 1944 },
    { xTwips: 2844, yTwips: 1944 });
  assert.equal(result.collapsed, false);
  assert.equal(result.text, "ASCII abc XY");
  assert.equal(result.rectangles.length, 1);
  // the postcondition is a readback, so the state must actually be re-read
  assert.ok(requests.some((entry) => entry.operation === "editorGetStateV1"));
  // and the method must never cross the boundary as a parameter
  const select = requests.find((entry) => entry.operation === "editorSelectRangeV1");
  assert.equal(Object.hasOwn(select.payload, "method"), false);
});

test("a range that selects nothing is a reported outcome, not an error", async () => {
  const { client } = fixture({ selectCompletion: "verified-selection-readback" });
  const result = await client.selectRange({ xTwips: 10, yTwips: 20000 },
    { xTwips: 900, yTwips: 20000 });
  assert.equal(result.collapsed, true);
  assert.equal(result.text, "");
  assert.deepEqual(result.rectangles, []);
});

test("a readback that contradicts itself is rejected", async () => {
  const { client } = fixture({
    state: {
      // says collapsed while carrying selection rectangles
      selection: { observed: true, collapsed: true, start: null, end: null,
        rectangles: [{ x: 1, y: 2, width: 3, height: 4 }] },
      selectionType: "text",
      selectionText: "x",
    },
  });
  await assert.rejects(
    () => client.selectRange({ xTwips: 1, yTwips: 2 }, { xTwips: 3, yTwips: 4 }),
    (error) => error.code === "EDITOR_RESULT_INVALID",
  );
});

test("selectRange rejects non-integer and negative twips before dispatch", async () => {
  const { client, requests } = fixture();
  for (const [start, end] of [
    [{ xTwips: -1, yTwips: 0 }, { xTwips: 1, yTwips: 1 }],
    [{ xTwips: 0, yTwips: 0 }, { xTwips: 1.5, yTwips: 1 }],
    [{ xTwips: 0 }, { xTwips: 1, yTwips: 1 }],
  ]) {
    await assert.rejects(() => client.selectRange(start, end),
      (error) => error.code === "INVALID_ARGUMENT");
  }
  assert.equal(requests.filter((e) => e.operation === "editorSelectRangeV1").length, 0);
});
