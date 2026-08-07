import assert from "node:assert/strict";
import test from "node:test";

import { ReaderSession } from "../reader-session.js";

class FakeDocument {
  constructor(bytes) {
    this.bytes = bytes;
    this.handle = 1;
    this.revision = 0;
    this.parts = 1;
    this.widthTwips = 15000;
    this.heightTwips = 30000;
    this.closed = false;
    this.searchIndex = 0;
  }

  async render(region) {
    return {
      pixels: new ArrayBuffer(region.canvasWidthPx * region.canvasHeightPx * 4),
      width: region.canvasWidthPx,
      height: region.canvasHeightPx,
      revision: this.revision,
    };
  }

  async search(query) {
    if (query === "missing")
      return { found: false, query, selections: [], revision: this.revision };
    const positions = query === "duplicate" ? ["a", "b"] : ["a", "a"];
    const position = positions[this.searchIndex++ % positions.length];
    return {
      found: true,
      query,
      selections: [{ part: 0, rectangles: position }],
      revision: this.revision,
    };
  }

  async getSelection() {
    return { text: "unique", revision: this.revision };
  }

  async replaceSelection() {
    this.revision += 1;
    return { revision: this.revision };
  }

  async save() {
    return this.bytes.slice(0);
  }

  async close() {
    this.closed = true;
  }
}

class FakeEngine {
  constructor(record) {
    this.record = record;
    this.listeners = new Set();
    this.manifest = {
      profile: "writer-review",
      coreCommit: "core",
      sdkVersion: "sdk",
      providerContractVersion: "1.0",
    };
  }

  onEvent(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  async open(bytes) {
    this.document = new FakeDocument(bytes);
    this.record.documents.push(this.document);
    return this.document;
  }

  emit(event) {
    for (const listener of this.listeners)
      listener(event);
  }

  dispose() {
    this.record.disposals += 1;
  }
}

function setup() {
  const record = { engines: [], documents: [], disposals: 0 };
  const session = new ReaderSession({
    engineFactory: async () => {
      const engine = new FakeEngine(record);
      record.engines.push(engine);
      return engine;
    },
    tileOptions: { tileSizePx: 128, prefetchTiles: 0 },
  });
  return { record, session };
}

function snapshot(version = "v1") {
  return {
    documentId: "doc-1",
    version,
    etag: `\"${version}\"`,
    name: "fixture.odt",
    bytes: new ArrayBuffer(32),
  };
}

test("session opens, renders, saves, protects local bytes, and reloads with a new worker", async () => {
  const { record, session } = setup();
  await session.open(snapshot());
  assert.equal(session.state.snapshot.state, "ready");
  session.scheduleViewport({ scrollLeft: 0, scrollTop: 0, width: 100, height: 100 });
  await session.scheduler.drain();
  await session.saveLocal();
  assert.equal(session.state.snapshot.hasLocalBytes, true);
  session.markStale({ documentId: "doc-1", previousVersion: "v1", version: "v2" });
  await assert.rejects(() => session.reload(snapshot("v2")), /downloaded or explicitly discarded/);
  await session.reload(snapshot("v2"), { downloadedLocalBytes: true });
  assert.equal(session.state.snapshot.version, "v2");
  assert.equal(record.engines.length, 2);
  assert.equal(record.disposals, 1);
  assert.equal(record.documents[0].closed, true);
  await session.close();
  assert.equal(session.state.snapshot.state, "closed");
});

test("session maps worker crash to recoverable error and can reload", async () => {
  const { record, session } = setup();
  await session.open(snapshot());
  record.engines[0].emit({
    event: "worker-crashed",
    error: { code: "WORKER_CRASHED", message: "fixture crash" },
  });
  assert.equal(session.state.snapshot.state, "recoverable-error");
  assert.equal(session.state.snapshot.error.code, "WORKER_CRASHED");
  await session.reload(snapshot(), { discardLocalBytes: true });
  assert.equal(session.state.snapshot.state, "ready");
  assert.equal(record.engines.length, 2);
});

test("session classifies unique, missing, and ambiguous anchors conservatively", async () => {
  const { session } = setup();
  await session.open(snapshot());
  assert.equal((await session.classifyAnchor("unique")).classification, "unique");
  assert.equal((await session.classifyAnchor("missing")).classification, "not-found");
  const originalSelection = session.document.getSelection;
  session.document.getSelection = async () => ({ text: "duplicate", revision: 0 });
  assert.equal((await session.classifyAnchor("duplicate")).classification, "ambiguous");
  session.document.getSelection = originalSelection;
});
