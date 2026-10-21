// Unit test for the viewer's SDK, viewer-shell/ods-document-sdk.js
// (specs/SPEC-M4-ods-in-nextcloud.md §3.3, D3 = A): the shipped DocumentEngine
// subclassed, run against a fake worker through the shipped `workerFactory`
// option.  The fake speaks the worker protocol (request / response) and keeps
// an engine-side part that the SDK can only learn by asking.
//
// Red cases: tests/ods_document_sdk_mutations.py breaks a scratch copy of
// viewer-shell/ one way at a time (VIEWER_SHELL_DIR) and requires the named
// test to fail.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const shellDir = path.resolve(process.env.VIEWER_SHELL_DIR || path.join(here, "..", "viewer-shell"));
const { OdsViewerEngine } = await import(pathToFileURL(path.join(shellDir, "ods-document-sdk.js")).href);
const { OdsViewerSession } = await import(pathToFileURL(path.join(shellDir, "ods-viewer-session.js")).href);

const VIEWER_CAPABILITIES = ["open-odt", "rgba-tile", "cancel-queued", "search",
                             "open-ods", "part-switch", "part-text"];
// SPEC-M4-viewer-v2 3.1: ods-viewer-v2 adds part-info.
const VIEWER_V2_CAPABILITIES = [...VIEWER_CAPABILITIES, "part-info"];

class FakeWorker {
  constructor(options = {}) {
    this.capabilities = options.capabilities ?? VIEWER_CAPABILITIES;
    this.part = options.initialPart ?? 0;
    this.names = options.names ?? ["Alpha", "Beta", "Gamma"];
    this.ignoreSetPart = options.ignoreSetPart ?? false;
    this.openReply = options.openReply ?? { documentType: "spreadsheet", inputSuffix: ".ods" };
    // part-info: LOK's string for each part, or a function (part) -> reply / error body.
    this.visible = options.visible ?? this.names.map(() => true);
    this.partInfo = options.partInfo ?? null;
    // part-text's v2 fields, sent only when given (v1's engine sends none).
    this.waitFields = options.waitFields ?? null;
    this.operations = [];
    this.payloads = [];
    this.listeners = new Set();
  }

  addEventListener(type, listener) { if (type === "message") this.listeners.add(listener); }
  terminate() { this.terminated = true; }

  reply(requestId, ok, body) {
    const data = { protocolVersion: 1, kind: "response", requestId, ok,
                   ...(ok ? { result: body } : { error: body }) };
    queueMicrotask(() => { for (const listener of this.listeners) listener({ data }); });
  }

  postMessage(message) {
    if (message.kind !== "request")
      return;
    const { requestId, operation, payload } = message;
    this.operations.push(operation);
    this.payloads.push({ operation, payload });
    switch (operation) {
      case "init":
        return this.reply(requestId, true, { profile: "fake", capabilities: this.capabilities });
      case "open":
        return this.reply(requestId, true, { documentHandle: 9, revision: 0, parts: this.names.length,
                                             width: 26593, height: 13005, tileMode: 1, viewReady: true,
                                             ...this.openReply });
      case "currentPart":
        return this.reply(requestId, true, { part: this.part, revision: 0 });
      case "partName":
        return this.reply(requestId, true, { part: payload.part, name: this.names[payload.part], revision: 0 });
      case "setPart":
        if (!this.ignoreSetPart)
          this.part = payload.part;
        return this.reply(requestId, true, { part: this.part, width: 1000 * (this.part + 1),
                                             height: 500, revision: 0 });
      case "partText":
        return this.reply(requestId, true, { part: payload.part, text: `${this.names[payload.part]}\n`,
                                             textNull: false, selectAllConfirmed: true,
                                             partBefore: this.part, partAfter: this.part, revision: 0,
                                             ...(this.waitFields || {}) });
      case "partInfo": {
        if (this.partInfo) {
          const { ok, body } = this.partInfo(payload.part);
          return this.reply(requestId, ok, body);
        }
        const info = `{ "visible": ${this.visible[payload.part] ? 1 : 0}, "rtllayout": 0, "protected": 0, "selected": 0 }`;
        return this.reply(requestId, true, { part: payload.part, info, revision: 0 });
      }
      case "close":
        return this.reply(requestId, true, {});
      default:
        return this.reply(requestId, false, { code: "UNSUPPORTED_OPERATION", message: operation });
    }
  }
}

async function started(options = {}) {
  const worker = new FakeWorker(options);
  const engine = new OdsViewerEngine({ workerFactory: () => worker, timeoutMs: 2000 });
  await engine._initialize();
  return { engine, worker };
}

function corpusBuffer(relative) {
  const buffer = readFileSync(path.join(here, "..", "test-docs", "ods", relative));
  return buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength);
}

test("viewer profile: the handle carries the engine's type, suffix, names and part, all asked for", async () => {
  const { engine, worker } = await started({ initialPart: 2 });
  const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
  assert.equal(handle.documentType, "spreadsheet");
  assert.equal(handle.inputSuffix, ".ods");
  assert.deepEqual(handle.partNames, ["Alpha", "Beta", "Gamma"]);
  assert.equal(handle.currentPart, 2, "the part the engine is on, read at open");
  assert.deepEqual(worker.operations, ["init", "open", "currentPart", "partName", "partName", "partName"]);
  assert.deepEqual(worker.payloads.filter((p) => p.operation === "partName").map((p) => p.payload),
                   [0, 1, 2].map((part) => ({ documentHandle: 9, part })));
});

test("setPart: the handle follows the engine's read-back, not the request", async () => {
  {
    const { engine, worker } = await started();
    const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
    const result = await handle.setPart(1);
    assert.deepEqual(worker.payloads.at(-1), { operation: "setPart", payload: { documentHandle: 9, part: 1 } });
    assert.equal(handle.currentPart, 1);
    assert.deepEqual(result, { part: 1, widthTwips: 2000, heightTwips: 500 });
    assert.equal(handle.widthTwips, 2000, "the new part's width");
  }
  {
    const { engine } = await started({ ignoreSetPart: true });
    const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
    const result = await handle.setPart(2);
    assert.equal(handle.currentPart, 0, "an engine that stayed on part 0 is believed");
    assert.equal(result.part, 0);
  }
});

test("a profile without part-switch gets the plain handle and no query is sent", async () => {
  const { engine, worker } = await started({ capabilities: ["open-odt", "rgba-tile"] });
  const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
  for (const member of ["setPart", "partNames", "currentPart", "partText", "readCurrentPart"])
    assert.equal(member in handle, false, `${member} is on a handle whose profile has no part-switch`);
  assert.deepEqual(worker.operations, ["init", "open"]);
});

test("partText exists only with part-text, and says which part the engine ended on", async () => {
  {
    const { engine } = await started({ capabilities: VIEWER_CAPABILITIES.filter((c) => c !== "part-text") });
    const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
    assert.equal("partText" in handle, false);
  }
  {
    const { engine, worker } = await started();
    const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
    const result = await handle.partText(1);
    assert.deepEqual(worker.payloads.at(-1), { operation: "partText", payload: { documentHandle: 9, part: 1 } });
    assert.deepEqual(result, { part: 1, text: "Beta\n", textNull: false, selectAllConfirmed: true,
                               partBefore: 0, partAfter: 0 });
    assert.equal(handle.currentPart, 0);
  }
});

test("a part that is not a non-negative integer is refused before any request", async () => {
  const { engine, worker } = await started();
  const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
  const sent = worker.operations.length;
  for (const part of [-1, 1.5, "1", undefined]) {
    await assert.rejects(handle.setPart(part), { code: "INVALID_ARGUMENT" }, `setPart(${part})`);
    await assert.rejects(handle.partText(part), { code: "INVALID_ARGUMENT" }, `partText(${part})`);
  }
  assert.equal(worker.operations.length, sent);
});

test("an open reply without documentType leaves the handle without one", async () => {
  const { engine } = await started({ openReply: {} });
  const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
  assert.equal("documentType" in handle, false, "the adapter must see it as unknown, not as a default");
  assert.equal("inputSuffix" in handle, false);
});

test("through the session: real names, every tab enabled, nothing stood in for, and the switch is read back", async () => {
  const { engine } = await started({ capabilities: VIEWER_V2_CAPABILITIES });
  const session = new OdsViewerSession({ engineFactory: async () => engine,
                                         tileOptions: { tileSizePx: 256, prefetchTiles: 0, maxInFlight: 1 } });
  await session.open({ bytes: corpusBuffer("ladder/three-sheets-distinct.ods"), name: "three-sheets-distinct.ods" });
  const state = session.state;
  assert.equal(state.documentType, "spreadsheet");
  assert.equal(state.nameSpoofed, false, "the profile lists open-ods: the name goes through as it is");
  assert.deepEqual(state.tabs.map((tab) => tab.label), ["Alpha", "Beta", "Gamma"]);
  assert.equal(state.namesFromEngine, true);
  assert.deepEqual(state.tabs.map((tab) => tab.enabled), [true, true, true]);
  assert.deepEqual(state.adapterFallbacks, []);
  assert.equal(state.evidenceClass, "unbound");
  await session.showPart(2);
  assert.equal(session.state.currentPart, 2);
  assert.equal(session.state.currentPartReadBack, 2);
  await session.close();
});


// SPEC-M4-viewer-v2 3.2 (finding 157).
test("v2: part-info is asked once per part after the names, and the handle carries what core said", async () => {
  const { engine, worker } = await started({ capabilities: VIEWER_V2_CAPABILITIES, visible: [true, false, true] });
  const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
  assert.deepEqual(handle.partVisible, [true, false, true]);
  assert.equal("partInfoProblem" in handle, false);
  assert.deepEqual(worker.operations, ["init", "open", "currentPart", "partName", "partName", "partName",
                                       "partInfo", "partInfo", "partInfo"]);
  assert.deepEqual(worker.payloads.filter((p) => p.operation === "partInfo").map((p) => p.payload),
                   [0, 1, 2].map((part) => ({ documentHandle: 9, part })));
});

test("v2: without part-info (v1's viewer) nothing is asked and the session says visibility was assumed", async () => {
  const { engine, worker } = await started();
  const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
  assert.equal("partVisible" in handle, false);
  assert.equal(worker.operations.includes("partInfo"), false);
  const session = new OdsViewerSession({ engineFactory: async () => (await started()).engine,
                                         tileOptions: { tileSizePx: 256, prefetchTiles: 0, maxInFlight: 1 } });
  await session.open({ bytes: corpusBuffer("ladder/three-sheets-distinct.ods"), name: "three-sheets-distinct.ods" });
  assert.deepEqual(session.state.adapterFallbacks, ["part-visibility-unknown"]);
  assert.equal(session.state.evidenceClass, "diagnostic");
  await session.close();
});

test("v2: a part-info that fails or is not 0/1 does not fail the open; the handle says why", async () => {
  const cases = [
    [() => ({ ok: false, body: { code: "LOK_ERROR", message: "getPartInfo returned an empty string" } }),
     "LOK_ERROR: getPartInfo returned an empty string"],
    [(part) => ({ ok: true, body: { part, info: "not json", revision: 0 } }), /^PART_INFO_UNPARSEABLE: part 0: getPartInfo is not JSON/],
    [(part) => ({ ok: true, body: { part, info: '{ "visible": 2 }', revision: 0 } }), /^PART_INFO_UNPARSEABLE: part 0: .*visible is 2/],
    [(part) => ({ ok: true, body: { part, info: '{ "rtllayout": 0 }', revision: 0 } }), /^PART_INFO_UNPARSEABLE: part 0: .*visible is undefined/],
  ];
  for (const [partInfo, problem] of cases) {
    const { engine } = await started({ capabilities: VIEWER_V2_CAPABILITIES, partInfo });
    const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
    assert.equal("partVisible" in handle, false, String(problem));
    if (typeof problem === "string")
      assert.equal(handle.partInfoProblem, problem);
    else
      assert.match(handle.partInfoProblem, problem);
    assert.deepEqual(handle.partNames, ["Alpha", "Beta", "Gamma"], "the rest of the open is intact");
  }
});

test("v2: the string form of visible is read too (\"0\"/\"1\"), nothing else is guessed", async () => {
  const { engine } = await started({ capabilities: VIEWER_V2_CAPABILITIES,
    partInfo: (part) => ({ ok: true, body: { part, info: `{ "visible": "${part === 1 ? 0 : 1}" }`, revision: 0 } }) });
  const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
  assert.deepEqual(handle.partVisible, [true, false, true]);
});

test("v2: partText passes the engine's wait fields through when it sends them, and only then", async () => {
  {
    const { engine } = await started({ capabilities: VIEWER_V2_CAPABILITIES,
                                       waitFields: { selectAllWaitMs: 37, selectAllDeadlineMs: 10000,
                                                     lateSelectAllResults: 0 } });
    const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
    const result = await handle.partText(2);
    assert.equal(result.selectAllWaitMs, 37);
    assert.equal(result.selectAllDeadlineMs, 10000);
    assert.equal(result.lateSelectAllResults, 0);
  }
  {
    const { engine } = await started();
    const handle = await engine.open(new ArrayBuffer(8), { name: "book.ods" });
    assert.deepEqual(Object.keys(await handle.partText(0)).sort(),
                     ["part", "partAfter", "partBefore", "selectAllConfirmed", "text", "textNull"]);
  }
});
