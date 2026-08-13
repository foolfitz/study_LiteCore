import assert from "node:assert/strict";
import test from "node:test";

import {
  EDIT_ACTIONS,
  FORBIDDEN,
  INLINE_ACTIONS,
  PINNED_WASM_SHA256,
  STRUCTURE_ACTIONS,
  StructureDemoClient,
  assertPinnedArtifact,
} from "../demo-structure-client.js";

// The demo's whole justification is that it shows only what has been measured,
// on the artifact the measurements bind to.  Both halves of that are checkable,
// so both are checked here rather than asserted in a comment.

function manifest(sha = PINNED_WASM_SHA256) {
  return {
    capabilities: ["verified-format-state", "open-odt", "save-odt"],
    diagnostic: { scope: "e2-paragraph-format-discovery", wasmSha256: sha },
  };
}

function handle(sha = PINNED_WASM_SHA256) {
  const requests = [];
  const document = {
    handle: 1,
    revision: 3,
    _assertUsable() {},
    _engine: {
      manifest: manifest(sha),
      async _request(operation, payload) {
        requests.push({ operation, ...payload });
        return { revision: document.revision + 1 };
      },
    },
  };
  return { document, requests };
}

test("the demo refuses any build but the one its evidence describes", () => {
  const other = "0".repeat(64);
  assert.throws(() => assertPinnedArtifact(manifest(other)), (error) => {
    assert.equal(error.code, "DEMO_ARTIFACT_EXPIRED");
    assert.equal(error.details.actual, other);
    assert.equal(error.details.expected, PINNED_WASM_SHA256);
    return true;
  });
  assert.throws(() => new StructureDemoClient(handle(other).document),
                { code: "DEMO_ARTIFACT_EXPIRED" });
});

test("a manifest with no hash at all is refused, not defaulted", () => {
  assert.throws(() => assertPinnedArtifact({ diagnostic: {} }),
                { code: "DEMO_ARTIFACT_EXPIRED" });
  assert.throws(() => assertPinnedArtifact(undefined),
                { code: "DEMO_ARTIFACT_EXPIRED" });
});

test("the pinned build is accepted", () => {
  assert.equal(assertPinnedArtifact(manifest()), PINNED_WASM_SHA256);
  assert.doesNotThrow(() => new StructureDemoClient(handle().document));
});

test("a forbidden action is refused with the reason it is forbidden", async () => {
  // Asserting only the error code would pass against a client with no
  // FORBIDDEN branch at all, because an unlisted action is rejected anyway.
  // What is being pinned is that the refusal *says why*, so that removing the
  // explanation is a test failure rather than a quiet loss.
  const client = new StructureDemoClient(handle().document);
  for (const [action, reason] of Object.entries(FORBIDDEN)) {
    await assert.rejects(() => client.action(action), (error) => {
      assert.equal(error.code, "EDITOR_ACTION_UNSUPPORTED");
      assert.ok(error.message.includes(reason),
                `${action} was refused without its reason: ${error.message}`);
      return true;
    }, `${action} must stay unreachable`);
  }
});

test("the allowed and forbidden lists cannot overlap", () => {
  // The failure this guards against is a later edit adding line navigation to
  // EDIT_ACTIONS and leaving the explanation of why it is excluded in place.
  const allowed = [...STRUCTURE_ACTIONS, ...INLINE_ACTIONS, ...EDIT_ACTIONS];
  for (const action of allowed)
    assert.equal(action in FORBIDDEN, false, `${action} is on both lists`);
  assert.equal(new Set(allowed).size, allowed.length, "an action is listed twice");
});

test("the diagnostic harness instruments are not on the client", () => {
  const client = new StructureDemoClient(handle().document);
  // FormatDiscoveryClient carries moveCaret / nudgeCaret / drainScheduler for
  // the sweeps.  The demo wraps that client, so the check that matters is that
  // the wrapper does not re-expose them.
  for (const instrument of ["moveCaret", "nudgeCaret", "drainScheduler"])
    assert.equal(typeof client[instrument], "undefined", instrument);
});

test("underline and strikethrough are absent because this profile cannot do them", async () => {
  // They are in the product contract but not in the discovery worker's table,
  // so a demo button for them would fail at the wire.  Better to not have one.
  const client = new StructureDemoClient(handle().document);
  for (const action of ["set-underline", "set-strikethrough"])
    await assert.rejects(() => client.action(action), { code: "EDITOR_ACTION_UNSUPPORTED" });
});

test("a structure action reaches the engine as a named action, never a command", async () => {
  const context = handle();
  const client = new StructureDemoClient(context.document);
  await client.action("set-list-unordered");
  assert.equal(context.requests.length, 1);
  assert.equal(context.requests[0].operation, "editorDiscoveryAction");
  assert.equal(context.requests[0].action, "set-list-unordered");
  assert.equal(context.requests[0].expectedRevision, 3);
  for (const field of ["unoCommand", "command", "keyCode"])
    assert.equal(field in context.requests[0], false, field);
});

test("an inline format carries the explicit boolean the contract requires", async () => {
  const context = handle();
  const client = new StructureDemoClient(context.document);
  await client.action("set-bold", { enabled: true });
  assert.equal(context.requests[0].option, true);
  await client.action("set-bold", { enabled: false });
  assert.equal(context.requests[1].option, false);
});

test("pointing at a line uses neither the mouse-drag nor the reset method", async () => {
  // mouse-drag reports selections it did not make (SPEC E1-D 2.1); the reset
  // method hangs the handle from its second call onwards (finding 039).  The
  // range method is the only one this demo may use, and it is worth pinning
  // because both alternatives are one word away.
  const context = handle();
  const client = new StructureDemoClient(context.document);
  await client.selectLineAt(1000, 2000);
  const request = context.requests[0];
  assert.equal(request.operation, "editorDiscoverySelect");
  assert.equal(request.method, "text-handles-unstable");
  assert.equal(request.startYTwips, 2000);
  assert.equal(request.endYTwips, 2000);
  assert.ok(request.startXTwips < request.endXTwips,
            "a degenerate range is a collapsed selection, which is the case that hangs");
});

test("a line near the left edge does not ask for a negative coordinate", async () => {
  const context = handle();
  const client = new StructureDemoClient(context.document);
  await client.selectLineAt(10, 500);
  assert.equal(context.requests[0].startXTwips, 0);
});
