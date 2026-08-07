import assert from "node:assert/strict";
import test from "node:test";

import { HostInputAdapter } from "../input-adapter.js";
import {
  ClipboardAdapterError,
  PlainTextClipboardAdapter,
} from "../clipboard-adapter.js";

function harness(options = {}) {
  const mutations = [];
  const inputAdapter = new HostInputAdapter({
    commit: async (text) => {
      mutations.push(text);
      return { revision: mutations.length };
    },
  });
  const adapter = new PlainTextClipboardAdapter({
    inputAdapter,
    secureContext: true,
    ...options,
  });
  return { adapter, inputAdapter, mutations };
}

test("copy uses public plain-text selection and a browser write", async () => {
  const writes = [];
  const { adapter, mutations } = harness({
    clipboard: { writeText: async (text) => writes.push(text) },
    getSelection: async () => ({
      text: "臺灣😀", mimeType: "text/plain;charset=utf-8", revision: 4,
    }),
  });
  const result = await adapter.copySelection();
  assert.deepEqual(writes, ["臺灣😀"]);
  assert.equal(result.revision, 4);
  assert.equal(result.utf8Bytes, 10);
  assert.deepEqual(mutations, []);
});

test("denied clipboard read is typed and causes zero mutation", async () => {
  const denied = Object.assign(new Error("denied"), { name: "NotAllowedError" });
  const { adapter, mutations } = harness({
    clipboard: { readText: async () => { throw denied; } },
  });
  await assert.rejects(
    adapter.pasteFromClipboard({ userGesture: true }),
    (error) => error instanceof ClipboardAdapterError && error.code === "CLIPBOARD_DENIED",
  );
  assert.deepEqual(mutations, []);
});

test("paste requires a user gesture and empty reads cause zero mutation", async () => {
  const { adapter, mutations } = harness({ clipboard: { readText: async () => "" } });
  await assert.rejects(
    adapter.pasteFromClipboard(),
    (error) => error.code === "CLIPBOARD_DENIED",
  );
  const empty = await adapter.pasteFromClipboard({ userGesture: true });
  assert.equal(empty.committed, false);
  assert.deepEqual(mutations, []);
});

test("plain text wins over HTML and commits exactly once", async () => {
  const { adapter, mutations } = harness();
  const event = {
    isTrusted: true,
    preventDefault() {},
    clipboardData: {
      types: ["text/html", "text/plain"],
      getData(type) {
        return type === "text/plain" ? "R7-臺灣😀" : "<b>ignored</b>";
      },
    },
  };
  await adapter.pasteEvent(event);
  assert.deepEqual(mutations, ["R7-臺灣😀"]);
});

test("non-text clipboard is rejected without mutation", async () => {
  const { adapter, mutations } = harness();
  await assert.rejects(
    adapter.pasteEvent({
      preventDefault() {},
      clipboardData: { types: ["image/png"], getData: () => "" },
    }),
    (error) => error.code === "UNSUPPORTED_CLIPBOARD_TYPE",
  );
  assert.deepEqual(mutations, []);
});

