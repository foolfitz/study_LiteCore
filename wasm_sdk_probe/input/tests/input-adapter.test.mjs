import assert from "node:assert/strict";
import test from "node:test";

import {
  HostInputAdapter,
  InputAdapterError,
  summarizeUnicode,
} from "../input-adapter.js";

function event(properties = {}) {
  return {
    cancelable: true,
    defaultPrevented: false,
    preventDefault() {
      this.defaultPrevented = true;
    },
    ...properties,
  };
}

test("composition commits exactly once and suppresses duplicate beforeinput", async () => {
  const mutations = [];
  const trace = [];
  const adapter = new HostInputAdapter({
    commit: async (text) => {
      mutations.push(text);
      return { revision: mutations.length };
    },
    onTrace: (entry) => trace.push(entry),
  });
  adapter.handleCompositionStart(event({ data: "" }));
  adapter.handleCompositionUpdate(event({ data: "臺" }));
  await adapter.handleBeforeInput(event({ inputType: "insertCompositionText", data: "臺" }));
  const end = adapter.handleCompositionEnd(event({ data: "臺灣" }));
  const duplicate = event({ inputType: "insertText", data: "臺灣" });
  const suppressed = await adapter.handleBeforeInput(duplicate);
  await end;

  assert.deepEqual(mutations, ["臺灣"]);
  assert.equal(adapter.state.requestCount, 1);
  assert.equal(suppressed.reason, "post-composition-duplicate");
  assert.equal(duplicate.defaultPrevented, true);
  assert.ok(trace.some((entry) => entry.action === "post-composition-duplicate-suppressed"));
});

test("cancel, empty composition and teardown cause zero mutation", async () => {
  let mutations = 0;
  const adapter = new HostInputAdapter({ commit: async () => { mutations += 1; } });
  adapter.handleCompositionStart(event());
  adapter.handleCompositionUpdate(event({ data: "未送出" }));
  adapter.cancelComposition("escape");
  await adapter.handleCompositionEnd(event({ data: "" }));
  adapter.handleCompositionStart(event());
  adapter.detach();
  await adapter.idle();
  assert.equal(mutations, 0);
  assert.equal(adapter.state.requestCount, 0);
});

test("plain text clipboard ignores HTML and preserves Unicode", async () => {
  const mutations = [];
  const adapter = new HostInputAdapter({ commit: async (text, metadata) => {
    mutations.push({ text, metadata });
    return { revision: 4 };
  } });
  const paste = event({
    clipboardData: {
      getData(type) {
        return type === "text/plain" ? "臺灣😀\n第二行" : "<b>不可送入</b>";
      },
    },
  });
  await adapter.handlePaste(paste);
  assert.equal(paste.defaultPrevented, true);
  assert.equal(mutations[0].text, "臺灣😀\n第二行");
  assert.equal(mutations[0].metadata.htmlPresent, true);
});

test("empty and oversized input generate no mutation", async () => {
  let mutations = 0;
  const adapter = new HostInputAdapter({
    maxUtf8Bytes: 4,
    commit: async () => { mutations += 1; },
  });
  const empty = await adapter.commitText("");
  assert.equal(empty.committed, false);
  await assert.rejects(
    adapter.commitText("臺灣"),
    (error) => error instanceof InputAdapterError && error.code === "INPUT_TOO_LARGE",
  );
  assert.equal(mutations, 0);
  assert.equal(adapter.state.requestCount, 0);
});

test("commits are serialized and Unicode summary distinguishes combining forms", async () => {
  const order = [];
  const adapter = new HostInputAdapter({ commit: async (text) => {
    order.push(`start:${text}`);
    await Promise.resolve();
    order.push(`end:${text}`);
    return { revision: order.length };
  } });
  await Promise.all([adapter.commitText("一"), adapter.commitText("二")]);
  assert.deepEqual(order, ["start:一", "end:一", "start:二", "end:二"]);
  assert.deepEqual(summarizeUnicode("e\u0301").codePoints, ["U+0065", "U+0301"]);
  assert.deepEqual(summarizeUnicode("é").codePoints, ["U+00E9"]);
  assert.deepEqual(summarizeUnicode("𠀀😀").codePoints, ["U+20000", "U+1F600"]);
});

test("bounded queue rejects newest input without dropping accepted commits", async () => {
  const gates = [];
  const mutations = [];
  const adapter = new HostInputAdapter({
    maxQueueDepth: 2,
    commit: async (text) => {
      mutations.push(text);
      await new Promise((resolve) => gates.push(resolve));
      return { revision: mutations.length };
    },
  });
  const first = adapter.commitText("一");
  const second = adapter.commitText("二");
  await assert.rejects(
    adapter.commitText("三"),
    (error) => error.code === "INPUT_BACKPRESSURE",
  );
  gates.shift()();
  await first;
  await Promise.resolve();
  gates.shift()();
  await second;
  assert.deepEqual(mutations, ["一", "二"]);
  assert.equal(adapter.state.requestCount, 2);
});

test("stale invalidation cancels queued input and does not replay it", async () => {
  let release;
  const mutations = [];
  const adapter = new HostInputAdapter({
    commit: async (text) => {
      mutations.push(text);
      if (text === "進行中")
        await new Promise((resolve) => { release = resolve; });
      return { revision: mutations.length };
    },
  });
  const inFlight = adapter.commitText("進行中");
  const queued = adapter.commitText("不得重送");
  adapter.invalidate("stale-document", { blocked: true });
  await assert.rejects(queued, (error) => error.code === "INPUT_CANCELLED");
  release();
  await inFlight;
  adapter.setBlocked(false);
  await adapter.commitText("恢復後新輸入");
  assert.deepEqual(mutations, ["進行中", "恢復後新輸入"]);
});

test("blocked state cancels composition and rejects commits", async () => {
  let mutations = 0;
  const adapter = new HostInputAdapter({ commit: async () => { mutations += 1; } });
  adapter.handleCompositionStart(event());
  adapter.handleCompositionUpdate(event({ data: "未提交 preedit" }));
  adapter.setBlocked(true, "worker-recovery");
  await adapter.handleCompositionEnd(event({ data: "" }));
  await assert.rejects(
    adapter.commitText("禁止"),
    (error) => error.code === "INPUT_BLOCKED",
  );
  assert.equal(mutations, 0);
  assert.equal(adapter.state.status, "blocked");
});

test("composition buffer disagreement is typed and causes zero mutation", async () => {
  let mutations = 0;
  const listeners = new Map();
  const target = {
    value: "候選文字不同",
    addEventListener(type, listener) { listeners.set(type, listener); },
    removeEventListener() {},
  };
  const adapter = new HostInputAdapter({ commit: async () => { mutations += 1; } });
  adapter.attach(target);
  adapter.handleCompositionStart(event());
  adapter.handleCompositionUpdate(event({ data: "候選" }));
  await assert.rejects(
    adapter.handleCompositionEnd(event({ data: "正式文字" })),
    (error) => error.code === "INPUT_COMPOSITION_MISMATCH",
  );
  assert.equal(mutations, 0);
  assert.equal(adapter.state.status, "recoverable-error");
});
