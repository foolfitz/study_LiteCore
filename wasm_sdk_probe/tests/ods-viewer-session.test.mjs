// Unit test for the read-only ODS viewer draft (plan W9, gate G9).
//
// A fake engine and fake handles stand in for the real worker.  Two handles are
// exercised throughout: a PRE-W7 one (what the SDK hands out today: `parts`,
// `render`, `close`, nothing else) and a W7-SHAPED one that also has
// `documentType`, `partNames`, `setPart` and `currentPart`.  The W7-shaped one is
// a guess at W7's surface (see viewer-shell/w7-adapter.js), not a record of it.
//
// Every assertion here was shown to go red once against a deliberately broken
// copy of the session (findings/evidence/m4-ods/W9-viewer-draft/red-cases.py);
// the README there says which assertion caught which break.
//
// VIEWER_SHELL_DIR points the test at another copy of viewer-shell/ (the red-case
// runner uses that); by default it tests the real one.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const shellDir = path.resolve(process.env.VIEWER_SHELL_DIR || path.join(here, "..", "viewer-shell"));
const { OdsViewerSession } = await import(
  pathToFileURL(path.join(shellDir, "ods-viewer-session.js")).href);

const VIEWPORT = { scrollLeft: 0, scrollTop: 0, width: 256, height: 256 };
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// What part an engine was on is visible in the pixels: every byte is
// (part + 1) * 10.  A tile painted for the wrong sheet is a wrong number.
function fillFor(part) { return (part + 1) * 10; }

class FakeHandle {
  constructor(options = {}) {
    this.handle = 1;
    this.revision = 0;
    this.parts = options.parts ?? 3;
    this.widthTwips = 15360;
    this.heightTwips = 15360;
    this.tileMode = "rgba";
    this._enginePart = options.initialPart ?? 0;
    this._renderDelay = options.renderDelay ?? 0;
    this.renders = [];
    this.closed = false;
  }

  async render(region) {
    this.renders.push({ enginePart: this._enginePart, region });
    if (this._renderDelay)
      await wait(this._renderDelay);                 // deliberately ignores the abort signal
    const width = region.canvasWidthPx;
    const height = region.canvasHeightPx;
    const pixels = new ArrayBuffer(width * height * 4);
    new Uint8Array(pixels).fill(fillFor(this._enginePart));
    return { pixels, width, height, revision: this.revision };
  }

  async close() { this.closed = true; }

  // Things a viewer must never reach.  They exist so that a call is observable.
  async click() {}
  async insertText() {}
  async save() { return new ArrayBuffer(1); }
  async replaceSelection() {}
  async undo() {}
  async redo() {}
}

class FakeW7Handle extends FakeHandle {
  constructor(options = {}) {
    super(options);
    this.documentType = options.documentType ?? "spreadsheet";
    this.partNames = options.partNames
      ?? ["Alpha", "Beta", "Gamma", "Delta"].slice(0, this.parts);
    this._ignoreSetPart = options.ignoreSetPart ?? false;
    this._setPartDelay = options.setPartDelay ?? (() => 0);
    this.setPartCalls = [];
  }

  async setPart(k) {
    this.setPartCalls.push(k);
    await wait(this._setPartDelay(k));
    if (!this._ignoreSetPart)
      this._enginePart = k;                          // engine-side state; the reply says nothing
    return {};
  }

  get currentPart() { return this._enginePart; }
}

class FakeEngine {
  constructor(handle, options = {}) {
    this.handle = handle;
    this.manifest = { profile: "fake", capabilities: options.capabilities ?? [] };
    this.openCalls = [];
    this.listeners = new Set();
    this.disposed = false;
    this._openError = options.openError ?? null;
  }

  onEvent(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  emit(event) { for (const listener of this.listeners) listener(event); }

  async open(bytes, options) {
    this.openCalls.push(options);
    if (this._openError)
      throw this._openError;
    return this.handle;
  }

  dispose() { this.disposed = true; }
}

// Like the page's real factory: the listener goes on BEFORE initialisation, and
// the engine speaks during it.
function factoryFor(engine, initEvents = []) {
  return async ({ onEvent } = {}) => {
    if (onEvent)
      engine.onEvent(onEvent);
    for (const event of initEvents)
      engine.emit(event);
    return engine;
  };
}

// Logs every member that is called, so a test can state what was NOT called.
function recorded(target, log) {
  return new Proxy(target, {
    get(object, property) {
      const value = Reflect.get(object, property, object);
      if (typeof value !== "function")
        return value;
      return (...args) => {
        log.push(String(property));
        return value.apply(object, args);
      };
    },
  });
}

function bytesOf(size = 16) { return new ArrayBuffer(size); }

async function openViewer({ handle, engineOptions = {}, name = "book.ods",
                            initEvents = [], tiles = [], states = [], events = [] }) {
  const engine = new FakeEngine(handle, engineOptions);
  const session = new OdsViewerSession({
    engineFactory: factoryFor(engine, initEvents),
    tileOptions: { tileSizePx: 256, prefetchTiles: 1, maxInFlight: 2 },
    onTile: (entry) => tiles.push({
      key: entry.key,
      part: entry.key.split(":")[2],
      generation: entry.generation,
      fill: new Uint8Array(entry.tile.pixels)[0],
    }),
    onState: (snapshot) => states.push(snapshot),
    onEvent: (event) => events.push(event),
  });
  await session.open({ bytes: bytesOf(), name });
  return { session, engine, handle, tiles, states, events };
}

const W7_ENGINE = { capabilities: ["open-ods"] };

test("pre-W7 handle: one tab per part, names synthesised and flagged, only the current tab enabled", async () => {
  const { session } = await openViewer({ handle: new FakeHandle({ parts: 3 }) });
  const state = session.state;
  assert.equal(state.state, "ready");
  assert.equal(state.parts, 3);
  assert.equal(state.tabs.length, 3);
  assert.deepEqual(state.tabs.map((tab) => tab.label), ["工作表 1", "工作表 2", "工作表 3"]);
  assert.equal(state.namesFromEngine, false);
  assert.equal(state.canSwitchParts, false);
  assert.deepEqual(state.tabs.map((tab) => tab.enabled), [true, false, false]);
  assert.equal(state.tabs[0].disabledReason, null);
  assert.ok(state.tabs[1].disabledReason && state.tabs[2].disabledReason);
  assert.equal(state.documentType, "unknown (pre-W7)");
  assert.equal(state.documentTypeKnown, false);
  assert.equal(state.currentPart, 0);
  assert.equal(state.currentPartReadBack, null);
  assert.equal(state.evidenceClass, "diagnostic");
  for (const fallback of ["document-type-unknown", "part-names-synthesised",
                          "part-switch-unavailable", "part-readback-unavailable"])
    assert.ok(state.adapterFallbacks.includes(fallback), fallback);
});

test("W7-shaped handle: tabs carry the engine's names, all enabled, the current part is READ at open", async () => {
  const handle = new FakeW7Handle({ parts: 3, initialPart: 2 });
  const { session } = await openViewer({ handle, engineOptions: W7_ENGINE });
  const state = session.state;
  assert.deepEqual(state.tabs.map((tab) => tab.label), ["Alpha", "Beta", "Gamma"]);
  assert.equal(state.namesFromEngine, true);
  assert.equal(state.canSwitchParts, true);
  assert.deepEqual(state.tabs.map((tab) => tab.enabled), [true, true, true]);
  assert.equal(state.documentType, "spreadsheet");
  assert.equal(state.documentTypeKnown, true);
  assert.equal(state.currentPart, 2);
  assert.equal(state.currentPartReadBack, 2);
  assert.deepEqual(state.tabs.map((tab) => tab.current), [false, false, true]);
  assert.deepEqual(state.adapterFallbacks, []);
  assert.equal(state.evidenceClass, "unbound");
});

test("showPart(k): the engine is switched, read back, and the scheduler paints part k", async () => {
  const handle = new FakeW7Handle({ parts: 3 });
  const { session, tiles } = await openViewer({ handle, engineOptions: W7_ENGINE });
  for (const k of [1, 2, 0]) {
    tiles.length = 0;
    const state = await session.showPart(k);
    assert.equal(state.currentPart, k);
    assert.equal(state.currentPartReadBack, k);
    assert.equal(handle.currentPart, k);
    session.scheduleViewport(VIEWPORT);
    await session.drain();
    assert.ok(tiles.length >= 1, `part ${k} produced tiles`);
    for (const tile of tiles) {
      assert.equal(tile.part, String(k), "the scheduler's tile key carries part k");
      assert.equal(tile.fill, fillFor(k), "the pixels are part k's, not another sheet's");
    }
  }
  assert.deepEqual(handle.setPartCalls, [1, 2, 0]);
});

test("an engine that ignores set_part: the state follows the read-back, not the request", async () => {
  const handle = new FakeW7Handle({ parts: 3, ignoreSetPart: true });
  const { session, tiles } = await openViewer({ handle, engineOptions: W7_ENGINE });
  await assert.rejects(session.showPart(1), (error) => {
    assert.equal(error.code, "PART_READBACK_MISMATCH");
    assert.equal(error.details.requested, 1);
    assert.equal(error.details.readBack, 0);
    return true;
  });
  const state = session.state;
  assert.equal(state.currentPart, 0);
  assert.equal(state.currentPartReadBack, 0, "the engine said 0; the request (1) is not echoed");
  assert.equal(state.lastRefusal.code, "PART_READBACK_MISMATCH");
  session.scheduleViewport(VIEWPORT);
  await session.drain();
  assert.ok(tiles.length >= 1);
  for (const tile of tiles) {
    assert.equal(tile.part, "0");
    assert.equal(tile.fill, fillFor(0));
  }
});

test("pre-W7: showPart(1) is refused with a typed error and nothing repaints; part 0 is not an engine confirmation", async () => {
  const handle = new FakeHandle({ parts: 3 });
  const { session, tiles } = await openViewer({ handle });
  session.scheduleViewport(VIEWPORT);
  await session.drain();
  const before = {
    tiles: tiles.length,
    renders: handle.renders.length,
    generations: session.scheduler.metrics.generations,
    dropped: session.droppedTiles,
  };
  assert.ok(before.tiles >= 1 && before.renders >= 1, "the first paint happened");

  await assert.rejects(session.showPart(1), (error) => {
    assert.equal(error.code, "PART_SWITCH_UNAVAILABLE");
    return true;
  });
  await wait(20);
  const state = session.state;
  assert.equal(state.currentPart, 0);
  assert.equal(state.currentPartReadBack, null);
  assert.equal(state.lastRefusal.code, "PART_SWITCH_UNAVAILABLE");
  assert.equal(state.lastRefusal.requested, 1);
  assert.equal(tiles.length, before.tiles, "no tile was delivered by the refused switch");
  assert.equal(handle.renders.length, before.renders, "the engine was not asked to paint again");
  assert.equal(session.scheduler.metrics.generations, before.generations);
  assert.equal(session.droppedTiles, before.dropped);

  const again = await session.showPart(0);
  assert.equal(again.currentPart, 0);
  assert.equal(again.currentPartReadBack, null, "no engine said anything, so nothing is read back");
});

test("a part outside 0..parts-1 is refused before the engine is asked", async () => {
  const handle = new FakeW7Handle({ parts: 3 });
  const { session } = await openViewer({ handle, engineOptions: W7_ENGINE });
  for (const k of [3, -1, 1.5, "1"]) {
    await assert.rejects(session.showPart(k), { code: "PART_OUT_OF_RANGE" });
  }
  assert.deepEqual(handle.setPartCalls, []);
  assert.equal(session.state.currentPart, 0);
});

test("a known non-spreadsheet document is refused, released, and paints nothing", async () => {
  const handle = new FakeW7Handle({ parts: 3, documentType: "text" });
  const engine = new FakeEngine(handle, W7_ENGINE);
  const session = new OdsViewerSession({ engineFactory: factoryFor(engine) });
  await assert.rejects(session.open({ bytes: bytesOf(), name: "letter.ods" }), (error) => {
    assert.equal(error.code, "DOCUMENT_TYPE_REFUSED");
    assert.equal(error.details.documentType, "text");
    return true;
  });
  const state = session.state;
  assert.equal(state.state, "refused");
  assert.equal(state.error.code, "DOCUMENT_TYPE_REFUSED");
  assert.equal(handle.closed, true, "the document was handed back");
  assert.equal(engine.disposed, true, "the engine was disposed");
  assert.equal(handle.renders.length, 0, "nothing was painted");
  assert.equal(session.scheduler, null);
  assert.throws(() => session.scheduleViewport(VIEWPORT), { code: "NOT_READY" });
});

test("refusal needs a KNOWN wrong type: spreadsheet and unknown are both accepted", async () => {
  const known = await openViewer({ handle: new FakeW7Handle({ documentType: "spreadsheet" }),
                                   engineOptions: W7_ENGINE });
  assert.equal(known.session.state.state, "ready");
  const unknown = await openViewer({ handle: new FakeHandle() });
  assert.equal(unknown.session.state.state, "ready");
  assert.equal(unknown.session.state.documentType, "unknown (pre-W7)");
});

test("the spoof flag is set only when the adapter rewrote the name", async () => {
  const cases = [
    { label: "pre-W7 engine, .ods", engine: {}, name: "book.ods",
      openedAs: "book.odt", spoofed: true },
    { label: "pre-W7 engine, upper-case .ODS", engine: {}, name: "BOOK.ODS",
      openedAs: "BOOK.odt", spoofed: true },
    { label: "W7 engine (lists open-ods), .ods", engine: W7_ENGINE, name: "book.ods",
      openedAs: "book.ods", spoofed: false },
    { label: "pre-W7 engine, a real .odt", engine: {}, name: "legacy.odt",
      openedAs: "legacy.odt", spoofed: false },
    { label: "pre-W7 engine, .xlsx is left for the engine to refuse", engine: {}, name: "sheet.xlsx",
      openedAs: "sheet.xlsx", spoofed: false },
  ];
  for (const item of cases) {
    const { session, engine } = await openViewer({
      handle: new FakeHandle({ parts: 1 }), engineOptions: item.engine, name: item.name });
    assert.equal(engine.openCalls.length, 1, item.label);
    assert.equal(engine.openCalls[0].name, item.openedAs, item.label);
    const state = session.state;
    assert.equal(state.nameSpoofed, item.spoofed, item.label);
    assert.equal(state.adapterFallbacks.includes("name-spoofed"), item.spoofed, item.label);
    assert.equal(state.openName, item.openedAs, item.label);
  }
});

test("a tile of the previous part never reaches onTile", async () => {
  const handle = new FakeW7Handle({ parts: 3, renderDelay: 30 });
  const { session, tiles } = await openViewer({ handle, engineOptions: W7_ENGINE });
  session.scheduleViewport(VIEWPORT);              // part 0 renders are now in flight
  await session.showPart(1);                       // reconfigure under them
  await wait(80);                                  // they finish, ignoring their abort
  assert.equal(tiles.length, 0, "no part-0 tile was delivered under part 1");
  assert.ok(session.droppedTiles >= 1, "the late tiles were seen and dropped");
  session.scheduleViewport(VIEWPORT);
  await session.drain();
  assert.ok(tiles.length >= 1);
  for (const tile of tiles)
    assert.equal(tile.part, "1");
});

test("the event listener is attached before initialisation", async () => {
  const events = [];
  const initEvents = [{ event: "diagnostic", message: "preRun echo" }];
  await openViewer({ handle: new FakeHandle({ parts: 1 }), initEvents, events });
  assert.deepEqual(events.map((event) => event.message), ["preRun echo"]);
});

test("read-only: only render / setPart / close reach the document, only open / onEvent / dispose the engine", async () => {
  const handleLog = [];
  const engineLog = [];
  const handle = recorded(new FakeW7Handle({ parts: 3 }), handleLog);
  const engine = recorded(new FakeEngine(handle, W7_ENGINE), engineLog);
  const session = new OdsViewerSession({
    engineFactory: async ({ onEvent }) => { engine.onEvent(onEvent); return engine; },
    tileOptions: { tileSizePx: 256 },
  });
  await session.open({ bytes: bytesOf(), name: "book.ods" });
  session.scheduleViewport(VIEWPORT);
  await session.drain();
  await session.showPart(1);
  session.scheduleViewport(VIEWPORT);
  await session.drain();
  await session.showPart(2);
  await session.close();

  const handleCalls = new Set(handleLog);
  const engineCalls = new Set(engineLog);
  for (const call of ["render", "setPart", "close"])
    assert.ok(handleCalls.has(call), `exercised: ${call}`);
  for (const call of ["open", "onEvent", "dispose"])
    assert.ok(engineCalls.has(call), `exercised: ${call}`);
  const allowedHandle = new Set(["render", "setPart", "close"]);
  const allowedEngine = new Set(["open", "onEvent", "dispose"]);
  assert.deepEqual([...handleCalls].filter((call) => !allowedHandle.has(call)), []);
  assert.deepEqual([...engineCalls].filter((call) => !allowedEngine.has(call)), []);
});

test("W7 vocabulary appears only in the adapter (the directory is scanned, not listed)", () => {
  const files = readdirSync(shellDir).filter((file) => file.endsWith(".js"));
  assert.ok(files.length >= 3, `scan saw ${files.length} files`);
  assert.ok(files.includes("w7-adapter.js"));
  const tokens = [/pre-W7/, /\.odt/, /open-ods/, /工作表/];
  const adapter = readFileSync(path.join(shellDir, "w7-adapter.js"), "utf8");
  for (const token of tokens)
    assert.ok(token.test(adapter), `the adapter holds ${token}; a stale token would scan nothing`);
  for (const file of files.filter((name) => name !== "w7-adapter.js")) {
    const source = readFileSync(path.join(shellDir, file), "utf8");
    for (const token of tokens)
      assert.ok(!token.test(source), `${file} must not contain ${token}: that knowledge is the adapter's`);
  }
});

test("switches are serialised: the last request is the one the engine and the state end on", async () => {
  const handle = new FakeW7Handle({ parts: 3, setPartDelay: (k) => (k === 1 ? 25 : 1) });
  const { session } = await openViewer({ handle, engineOptions: W7_ENGINE });
  const results = await Promise.allSettled([session.showPart(1), session.showPart(2)]);
  assert.deepEqual(results.map((result) => result.status), ["fulfilled", "fulfilled"]);
  assert.equal(handle.currentPart, 2);
  assert.equal(session.state.currentPart, 2);
  assert.equal(session.state.currentPartReadBack, 2);
});

test("a worker crash takes the session to a typed error and stops scheduling", async () => {
  const handle = new FakeW7Handle({ parts: 2 });
  const { session, engine } = await openViewer({ handle, engineOptions: W7_ENGINE });
  engine.emit({ event: "worker-crashed", error: { code: "WORKER_CRASHED", message: "boom" } });
  assert.equal(session.state.state, "error");
  assert.equal(session.state.error.code, "WORKER_CRASHED");
  assert.throws(() => session.scheduleViewport(VIEWPORT), { code: "NOT_READY" });
  await assert.rejects(session.showPart(1), { code: "NOT_READY" });
});

test("an open that fails is typed, and the engine is given back", async () => {
  const failure = Object.assign(new Error("not a spreadsheet container"), { code: "LOK_ERROR" });
  const engine = new FakeEngine(new FakeHandle(), { openError: failure });
  const session = new OdsViewerSession({ engineFactory: factoryFor(engine) });
  await assert.rejects(session.open({ bytes: bytesOf(), name: "broken.ods" }), (error) => {
    assert.equal(error, failure);
    return true;
  });
  assert.equal(session.state.state, "error");
  assert.equal(session.state.error.code, "LOK_ERROR");
  assert.equal(engine.disposed, true);
});

test("partNames that disagree with parts are not used and the disagreement is recorded", async () => {
  const handle = new FakeW7Handle({ parts: 3, partNames: ["Only", "Two"] });
  const { session } = await openViewer({ handle, engineOptions: W7_ENGINE });
  const state = session.state;
  assert.equal(state.tabs.length, 3, "still one tab per part");
  assert.equal(state.namesFromEngine, false);
  assert.ok(state.partNamesProblem, "W7 being wrong is not recorded as W7 being absent");
  assert.deepEqual(state.tabs.map((tab) => tab.label), ["工作表 1", "工作表 2", "工作表 3"]);
});

test("a close() that arrives while the document is opening is not undone: what arrives late is given back", async () => {
  // Phase 0: closed while the package is still being read -- no engine is asked for.
  {
    let factoryCalls = 0;
    const session = new OdsViewerSession({
      engineFactory: async () => { factoryCalls += 1; return new FakeEngine(new FakeHandle()); },
    });
    const opening = session.open({ bytes: bytesOf(), name: "slow.ods" });
    await session.close();
    await assert.rejects(opening, { code: "CLOSED_DURING_OPEN" });
    assert.equal(factoryCalls, 0, "no engine was started after the close");
    assert.equal(session.state.engineRequested, false);
    assert.equal(session.state.state, "closed");
  }
  // Phase 1: closed while the engine is still starting.  The close waits for the
  // factory to be CALLED, so it lands in the engine's start and not in the
  // package read before it.
  {
    const handle = new FakeHandle({ parts: 1 });
    const engine = new FakeEngine(handle);
    let factoryCalled;
    const called = new Promise((resolve) => { factoryCalled = resolve; });
    const session = new OdsViewerSession({
      engineFactory: async () => { factoryCalled(); await wait(20); return engine; },
    });
    const opening = session.open({ bytes: bytesOf(), name: "slow.ods" });
    await called;
    await session.close();
    await assert.rejects(opening, { code: "CLOSED_DURING_OPEN" });
    assert.equal(engine.disposed, true, "the engine that finished starting was disposed");
    assert.equal(engine.openCalls.length, 0, "no document was opened on it");
    assert.equal(session.state.state, "closed");
  }
  // Phase 2: closed while the engine is opening the document.
  {
    const handle = new FakeHandle({ parts: 1 });
    const engine = new FakeEngine(handle);
    const realOpen = engine.open.bind(engine);
    // The close waits for the document open to be ASKED, as phase 1 waits for
    // the factory: a fixed delay would land in whatever came before it.
    let openCalled;
    const called = new Promise((resolve) => { openCalled = resolve; });
    engine.open = async (bytes, options) => {
      openCalled();
      await wait(20);
      return realOpen(bytes, options);
    };
    const session = new OdsViewerSession({ engineFactory: factoryFor(engine) });
    const opening = session.open({ bytes: bytesOf(), name: "slow.ods" });
    await called;
    await session.close();
    await assert.rejects(opening, { code: "CLOSED_DURING_OPEN" });
    assert.equal(handle.closed, true, "the document that opened late was closed");
    assert.equal(engine.disposed, true);
    assert.equal(session.state.state, "closed");
    assert.equal(session.scheduler, null, "no scheduler was built for a closed session");
  }
});

// ---------------------------------------------------------------------------
// The package probe (SPEC-M4-ods-in-nextcloud §5.2; review C6): an encrypted
// file is refused BEFORE the engine queue, and a package the probe cannot read
// is the engine's to judge.
const CORPUS = path.join(here, "..", "test-docs", "ods");

function fixtureBuffer(relative) {
  const buffer = readFileSync(path.join(CORPUS, relative));
  return buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength);
}

// A zip whose entries are all STORED (method 0), so the probe's other path is
// exercised: the corpus manifests are all deflated.  CRCs stay 0 -- the probe
// does not read them.
function storedZip(entries) {
  const encoder = new TextEncoder();
  const parts = [];
  const centrals = [];
  let offset = 0;
  for (const [name, text] of entries) {
    const nameBytes = encoder.encode(name);
    const data = encoder.encode(text);
    const local = new Uint8Array(30 + nameBytes.length + data.length);
    const lv = new DataView(local.buffer);
    lv.setUint32(0, 0x04034b50, true);
    lv.setUint16(4, 20, true);
    lv.setUint32(18, data.length, true);
    lv.setUint32(22, data.length, true);
    lv.setUint16(26, nameBytes.length, true);
    local.set(nameBytes, 30);
    local.set(data, 30 + nameBytes.length);
    const central = new Uint8Array(46 + nameBytes.length);
    const cv = new DataView(central.buffer);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(4, 20, true);
    cv.setUint16(6, 20, true);
    cv.setUint32(20, data.length, true);
    cv.setUint32(24, data.length, true);
    cv.setUint16(28, nameBytes.length, true);
    cv.setUint32(42, offset, true);
    central.set(nameBytes, 46);
    parts.push(local);
    centrals.push(central);
    offset += local.length;
  }
  const directorySize = centrals.reduce((sum, entry) => sum + entry.length, 0);
  const end = new Uint8Array(22);
  const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, entries.length, true);
  ev.setUint16(10, entries.length, true);
  ev.setUint32(12, directorySize, true);
  ev.setUint32(16, offset, true);
  const all = new Uint8Array(offset + directorySize + end.length);
  let at = 0;
  for (const piece of [...parts, ...centrals, end]) {
    all.set(piece, at);
    at += piece.length;
  }
  return all.buffer;
}

const MIMETYPE = ["mimetype", "application/vnd.oasis.opendocument.spreadsheet"];
const ENCRYPTED_MANIFEST = ["META-INF/manifest.xml",
  '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">'
  + '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml">'
  + '<manifest:encryption-data manifest:checksum-type="SHA1" manifest:checksum="AA=="/>'
  + "</manifest:file-entry></manifest:manifest>"];
const PLAIN_MANIFEST = ["META-INF/manifest.xml",
  '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">'
  + '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
  + "</manifest:manifest>"];

function countingViewer(handle = new FakeW7Handle({ parts: 1 })) {
  const engine = new FakeEngine(handle, W7_ENGINE);
  const calls = { factory: 0 };
  const session = new OdsViewerSession({
    engineFactory: async (options) => { calls.factory += 1; return factoryFor(engine)(options); },
  });
  return { session, engine, calls };
}

test("an encrypted package is refused before any engine is asked", async () => {
  const { session, engine, calls } = countingViewer();
  await assert.rejects(session.open({ bytes: fixtureBuffer("upstream/password.ods"), name: "book.ods" }),
    { code: "ENCRYPTED_DOCUMENT" });
  const state = session.state;
  assert.equal(state.state, "refused");
  assert.equal(state.error.code, "ENCRYPTED_DOCUMENT");
  assert.equal(calls.factory, 0, "no engine was started for an encrypted file");
  assert.equal(state.engineRequested, false);
  assert.deepEqual(state.packageProbe, { readable: true, encrypted: true, reason: null });
  assert.equal(engine.openCalls.length, 0);
});

test("the probe reads a STORED manifest as well as a deflated one", async () => {
  const refused = countingViewer();
  await assert.rejects(refused.session.open({ bytes: storedZip([MIMETYPE, ENCRYPTED_MANIFEST]), name: "book.ods" }),
    { code: "ENCRYPTED_DOCUMENT" });
  assert.equal(refused.calls.factory, 0);

  const plain = countingViewer();
  await plain.session.open({ bytes: storedZip([MIMETYPE, PLAIN_MANIFEST]), name: "book.ods" });
  assert.equal(plain.session.state.state, "ready");
  assert.deepEqual(plain.session.state.packageProbe, { readable: true, encrypted: false, reason: null });
});

test("a plain package opens, and the state says what the probe saw", async () => {
  const { session, calls } = countingViewer(new FakeW7Handle({ parts: 3 }));
  await session.open({ bytes: fixtureBuffer("ladder/three-sheets-distinct.ods"), name: "book.ods" });
  assert.equal(session.state.state, "ready");
  assert.equal(calls.factory, 1);
  assert.equal(session.state.engineRequested, true);
  assert.deepEqual(session.state.packageProbe, { readable: true, encrypted: false, reason: null });
});

test("a package the probe cannot read goes to the engine: the probe is not a second format check", async () => {
  // Zero bytes of zip, and an encrypted file cut short (its end record gone).
  const cut = fixtureBuffer("upstream/password.ods");
  for (const bytes of [bytesOf(), cut.slice(0, cut.byteLength - 100)]) {
    const { session, calls } = countingViewer();
    await session.open({ bytes, name: "book.ods" });
    assert.equal(session.state.state, "ready", "the fake engine opened what the probe could not read");
    assert.equal(calls.factory, 1);
    assert.equal(session.state.packageProbe.readable, false);
    assert.equal(session.state.packageProbe.encrypted, null);
    assert.ok(session.state.packageProbe.reason, "the reason the probe gave up is recorded");
  }
});
