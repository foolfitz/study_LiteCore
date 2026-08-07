import assert from "node:assert/strict";
import test from "node:test";

import {
  EDITOR_DISCOVERY_ACTIONS,
  EditorDiscoveryClient,
} from "../editor-discovery-client.js";

function fixture() {
  const requests = [];
  const engine = {
    manifest: {
      diagnostic: { scope: "e1-odt-editing-discovery" },
      capabilities: ["editor-discovery-closed-actions"],
    },
    async _request(operation, payload) {
      requests.push({ operation, payload });
      return operation === "editorDiscoveryGetState"
        ? { revision: document.revision, sourceSequence: 1 }
        : { revision: document.revision + (payload.action === "delete-forward" ? 1 : 0) };
    },
  };
  const document = {
    _engine: engine,
    handle: 7,
    revision: 3,
    _assertUsable() {},
  };
  return { client: new EditorDiscoveryClient(document), document, requests };
}

function schedulerFixture() {
  const value = fixture();
  value.document._engine.manifest.capabilities.push("finding-016-scheduler-probe");
  return value;
}

test("closed action request never carries key codes or UNO commands", async () => {
  const { client, document, requests } = fixture();
  const result = await client.action("delete-forward");
  assert.equal(result.revision, 4);
  assert.equal(document.revision, 4);
  assert.deepEqual(requests[0], {
    operation: "editorDiscoveryAction",
    payload: {
      documentHandle: 7,
      expectedRevision: 3,
      action: "delete-forward",
      extendSelection: false,
      option: false,
    },
  });
  assert.equal("keyCode" in requests[0].payload, false);
  assert.equal("unoCommand" in requests[0].payload, false);
});

test("unknown actions and malformed selection coordinates fail closed", async () => {
  const { client } = fixture();
  await assert.rejects(() => client.action(".uno:Bold"), { code: "EDITOR_ACTION_UNSUPPORTED" });
  await assert.rejects(
    () => client.select("mouse-drag", {
      startXTwips: 0,
      startYTwips: 0,
      endXTwips: -1,
      endYTwips: 10,
    }),
    { code: "INVALID_ARGUMENT" },
  );
});

test("format state is explicit and the candidate action list is frozen", async () => {
  const { client, requests } = fixture();
  await assert.rejects(() => client.action("set-bold"), { code: "INVALID_ARGUMENT" });
  await client.action("set-bold", { enabled: true });
  assert.equal(requests[0].payload.option, true);
  assert.equal(EDITOR_DISCOVERY_ACTIONS.length, 19);
  assert.equal(Object.isFrozen(EDITOR_DISCOVERY_ACTIONS), true);
});

test("manual delete observation remains a closed diagnostic action", async () => {
  const { client, requests } = fixture();
  await client.action("delete-forward", { manualObservation: true });
  assert.deepEqual(requests[0], {
    operation: "editorDiscoveryAction",
    payload: {
      documentHandle: 7,
      expectedRevision: 3,
      action: "delete-forward",
      extendSelection: false,
      option: true,
    },
  });
  assert.equal("keyCode" in requests[0].payload, false);
  assert.equal("unoCommand" in requests[0].payload, false);
  await assert.rejects(
    () => client.action("insert-line-break", { manualObservation: true }),
    { code: "INVALID_ARGUMENT" },
  );
  await assert.rejects(
    () => client.action("delete-forward", { manualObservation: "yes" }),
    { code: "INVALID_ARGUMENT" },
  );
});

test("scheduler drain is capability-gated and carries only the document handle", async () => {
  const regular = fixture();
  await assert.rejects(() => regular.client.drainScheduler(), {
    code: "UNSUPPORTED_OPERATION",
  });

  const { client, requests } = schedulerFixture();
  await client.drainScheduler();
  assert.deepEqual(requests[0], {
    operation: "finding016DrainScheduler",
    payload: { documentHandle: 7 },
  });
});
