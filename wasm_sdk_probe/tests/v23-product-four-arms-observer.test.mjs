// Drives web/v23-product-four-arms-observer-core.js -- its actual Worker wrapper, session
// wrappers, key listeners and release sets -- with a fake Worker, a fake session and a
// dispatcher that runs capture listeners, then the page's handler, then bubble listeners.
//
//   node --test tests/v23-product-four-arms-observer.test.mjs
//   V23_FOUR_ARMS_EMIT=1 node tests/v23-product-four-arms-observer.test.mjs   (prints the record)
import {installFourArmsObserver, releaseSets} from "../web/v23-product-four-arms-observer-core.js";

const RECT = "1000, 500, 1400, 240";
const START = {x: 1000, y: 500, height: 240};

function makeWindow() {
  let clock = 0;
  const listeners = {};
  class FakeWorker {
    constructor(url) { this.url = String(url); this.posted = []; this.postedRest = []; this.handlers = {message: [], error: []}; }
    addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); }
    postMessage(message, ...rest) { this.posted.push(message); this.postedRest.push(rest); return "native-post"; }
    terminate() { this.terminated = true; }
    emit(data) { for (const fn of this.handlers.message) fn({data}); }
  }
  const sink = {id: "sink", disabled: false, readOnly: false, isConnected: true, focus() { doc.activeElement = sink; }};
  const doc = {activeElement: null, querySelector: (selector) => (selector === "#sink" ? sink : null)};
  const win = {
    document: doc, navigator: {userAgent: "Mozilla/5.0 (X11; Linux x86_64) HeadlessChrome/139.0.0.0 Safari/537.36"},
    performance: {now: () => (clock += 0.25)}, crypto: globalThis.crypto, btoa: globalThis.btoa, TextEncoder,
    Worker: FakeWorker, NativeWorker: FakeWorker,
    fetch: async (url) => ({ok: true, arrayBuffer: async () => new TextEncoder().encode(`served ${url}`).buffer}),
    addEventListener(type, fn, capture) { (listeners[type] ||= []).push({fn, capture: capture === true}); },
  };
  win.dispatch = (fields, page) => {
    const event = {isTrusted: true, repeat: false, shiftKey: false, ctrlKey: false, altKey: false, metaKey: false,
      ...fields, eventPhase: 0, defaultPrevented: false, timeStamp: clock, target: sink,
      preventDefault() { this.defaultPrevented = true; }};
    event.eventPhase = 1;
    for (const l of listeners[event.type] || []) if (l.capture) l.fn(event);
    event.eventPhase = 2;
    if (page) page(event);
    event.eventPhase = 3;
    for (const l of listeners[event.type] || []) if (!l.capture) l.fn(event);
    event.eventPhase = 0;
    return event;
  };
  return win;
}

function makeSession(win) {
  const AUTO = {
    open: () => ({documentHandle: 1, revision: 0}),
    search: () => ({selections: [{part: 0, rectangles: RECT}], revision: 0}),
    editorPlaceCaretV2: () => ({revision: 0, state: collapsed()}),
    editorGetStateV2: () => collapsed(),
    getSelection: () => ({text: "", revision: 0}),
    save: () => ({buffer: new TextEncoder().encode("saved").buffer, revision: 0}),
  };
  function collapsed() {
    return {documentHandle: 1, revision: 0, caret: {...START},
      selection: {observed: true, collapsed: true, start: {x: START.x, y: START.y}, end: {x: START.x, y: START.y}}};
  }
  class Engine {
    constructor() {
      this._worker = new win.Worker("./profiles/e2-editor-v23/sdk-worker.js");
      this.nextId = 1;
      this.pending = new Map();
      this._worker.addEventListener("message", ({data}) => {
        const entry = data?.kind === "response" ? this.pending.get(data.requestId) : null;
        if (!entry) return;
        this.pending.delete(data.requestId);
        if (data.ok) entry.resolve(data.result); else entry.reject(new Error("refused"));
      });
    }
    _request(operation, payload) {
      const requestId = this.nextId++;
      return new Promise((resolve, reject) => {
        this.pending.set(requestId, {resolve, reject});
        this._worker.postMessage({protocolVersion: 1, kind: "request", requestId, operation, payload});
        if (AUTO[operation]) queueMicrotask(() => this.respond(requestId, AUTO[operation]()));
        else if (operation === "editorActionV2" && this.autoActions)
          queueMicrotask(() => this.respond(requestId, ext(collapsed())));
      });
    }
    respond(requestId, result, ok = true) {
      this._worker.emit({protocolVersion: 1, kind: "response", requestId, ok, result});
    }
  }
  class Session {
    async open({bytes, name}) {
      this.engine = new Engine();
      await this.engine._request("open", {buffer: bytes.slice(0), name});
      const request = (operation, payload = {}) => this.engine._request(operation, {documentHandle: 1, ...payload});
      this.document = {handle: 1, search: (query) => request("search", {query}),
        getSelection: () => request("getSelection")};
      this.editor = {getState: () => request("editorGetStateV2"),
        placeCaret: (xTwips, yTwips) => request("editorPlaceCaretV2", {xTwips, yTwips}),
        action: (action, options = {}) => request("editorActionV2", {action, extendSelection: options.extendSelection === true})};
      this.state = {snapshot: {state: "ready", dirty: false}};
    }
    action(action, options = {}) {
      const post = () => this.engine._request("editorActionV2",
        {documentHandle: 1, action, extendSelection: options.extendSelection === true});
      // Held behind typed text, the way the product session holds a non-text operation
      // (finding 111): admitted now, posted when the character's request has answered.
      return this.typing ? this.typing.then(post) : post();
    }
    deleteKey(action) { return this.engine._request("editorActionV2", {documentHandle: 1, action}); }
    commitText(text) {
      const typed = this.engine._request("insertText", {documentHandle: 1, text});
      this.typing = typed.then(() => { this.typing = null; });
      return typed;
    }
    save() { return this.engine._request("save", {documentHandle: 1, format: "odt"}); }
  }
  return Session;
}

const flush = async () => { for (let i = 0; i < 30; i += 1) await Promise.resolve(); };
const ext = (state) => ({action: "move-character-right", revision: 0, changed: false, completion: "selection-callback", state});

export async function scenario() {
  const win = makeWindow();
  const Session = makeSession(win);
  const R = installFourArmsObserver(win, {Session});
  const control = win.__fourArmsControl;
  const out = {win, R, control};

  // Dormant: the runner's earlier checks see a pass-through.
  const early = new Session();
  await early.open({bytes: new TextEncoder().encode("early").buffer, name: "early.odt"});
  out.dormant = {requests: R.requests.length, opens: R.opens.length, workers: R.workers.length};
  early.engine._worker.emit({protocolVersion: 1, kind: "response", requestId: 99, ok: true, result: {}});

  out.begun = await control.begin({profile: "e2-editor-v23", served: ["e2-editor.html"]});
  early.engine._worker.emit({protocolVersion: 1, kind: "response", requestId: 98, ok: true, result: {}});
  const session = new Session();
  await session.open({bytes: new TextEncoder().encode("fixture").buffer, name: "cell.odt"});
  out.prepared = await control.prepare({cellId: "c1", kind: "measured", arm: "held", round: 1, openName: "cell.odt",
    setup: {kind: "caret", query: "Paragraph 001."}});
  out.armed = control.arm("c1");

  // The page's depth-2 holding policy, reduced: one outstanding plus at most one retained repeat.
  const page = {outstanding: 0, held: false, active: true, sent: []};
  const send = () => {
    page.outstanding += 1;
    const promise = session.action("move-character-right", {extendSelection: true});
    page.sent.push(promise);
    promise.then(() => {
      page.outstanding -= 1;
      if (page.held && page.active) { page.held = false; send(); }
    });
  };
  const keydown = (event) => {
    event.preventDefault();
    if (!event.repeat || (page.outstanding === 0 && !page.held)) send();
    else if (page.outstanding + (page.held ? 1 : 0) < 2) page.held = true;
  };
  const down = (repeat) => win.dispatch({type: "keydown", key: "ArrowRight", repeat, shiftKey: true}, keydown);
  out.k1 = down(false);
  out.k2 = down(true);
  out.k3 = down(true);
  const posted = () => R.requests.filter((r) => r.issuer === "product" && r.message.operation === "editorActionV2");
  session.engine.respond(posted()[0].message.requestId, ext({...{documentHandle: 1, revision: 0},
    caret: {x: 1100, y: 500, height: 240}, selection: {observed: true, collapsed: false, start: {x: 1000, y: 500}, end: {x: 1100, y: 500}}}));
  await flush();
  out.k4 = down(true);
  out.up = win.dispatch({type: "keyup", key: "ArrowRight", shiftKey: true}, () => { page.active = false; page.held = false; });
  session.engine.respond(posted()[1].message.requestId, ext({documentHandle: 1, revision: 0,
    caret: {x: 1200, y: 500, height: 240}, selection: {observed: true, collapsed: false, start: {x: 1000, y: 500}, end: {x: 1200, y: 500}}}));
  await flush();

  // A paint answer keeps length + SHA-256, never the bitmap.
  const pixels = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]);
  const paint = session.engine._request("paint", {documentHandle: 1});
  const paintId = session.engine.nextId - 1;
  session.engine.respond(paintId, {pixels: pixels.buffer.slice(0), width: 2, height: 1});
  await paint;
  out.pixels = pixels;
  out.finished = await control.finish("c1");
  // A cancel of a posted request is recorded; one of a request posted before begin() is not.
  session.engine._worker.postMessage({protocolVersion: 1, kind: "cancel", requestId: paintId});
  early.engine._worker.postMessage({protocolVersion: 1, kind: "cancel", requestId: 1});
  control.closeCell("c1", null);

  // Queued work: Shift+Right admitted while the typed character is still on the wire.
  const typedSession = new Session();
  await typedSession.open({bytes: new TextEncoder().encode("fixture").buffer, name: "cell2.odt"});
  out.prepared2 = await control.prepare({cellId: "c2", kind: "measured", arm: "insert", round: 1,
    openName: "cell2.odt", setup: {kind: "caret", query: "abcd"}});
  control.arm("c2");
  out.typed = win.dispatch({type: "beforeinput", inputType: "insertText", data: "x"},
    () => { typedSession.commitText("x"); });
  out.shiftRight = win.dispatch({type: "keydown", key: "ArrowRight", shiftKey: true}, (event) => {
    event.preventDefault();
    out.queuedMove = typedSession.action("move-character-right", {extendSelection: true});
  });
  const typedRequest = R.requests.filter((r) => r.issuer === "product" && r.message.operation === "insertText").at(-1);
  typedSession.engine.respond(typedRequest.message.requestId, {revision: 1});
  await flush();
  const queued = R.requests.filter((r) => r.issuer === "product" && r.message.operation === "editorActionV2").at(-1);
  typedSession.engine.respond(queued.message.requestId, ext({documentHandle: 1, revision: 1,
    caret: {x: 1300, y: 500, height: 240}, selection: {observed: true, collapsed: false, start: {x: 1200, y: 500}, end: {x: 1300, y: 500}}}));
  await flush();
  win.dispatch({type: "keyup", key: "ArrowRight", shiftKey: true});
  await control.finish("c2");
  control.closeCell("c2", null);
  control.end();
  await Promise.all(win.__fourArmsPending);
  return out;
}

if (process.env.V23_FOUR_ARMS_EMIT) {
  const {R} = await scenario();
  process.stdout.write(JSON.stringify(R));
} else {
  const {default: test} = await import("node:test");
  const {default: assert} = await import("node:assert/strict");
  const {createHash} = await import("node:crypto");

  test("dormant until begin; orphan answers and cancels are counted, not recorded", async () => {
    const {R, dormant, begun} = await scenario();
    assert.deepEqual(dormant, {requests: 0, opens: 0, workers: 1});
    assert.equal(begun.ok, true);
    assert.equal(R.orphanResponses, 1);
    assert.equal(R.orphanCancels, 1);
    assert.deepEqual(R.workers.map((w) => w.generation), [1, 2, 3]);
    assert.ok(R.identity.served["e2-editor.html"].match(/^[0-9a-f]{64}$/));
  });

  test("a cancel of a posted request is recorded under that request's key", async () => {
    const {R} = await scenario();
    assert.equal(R.cancels.length, 1);
    const paint = R.requests.find((r) => r.message.operation === "paint");
    assert.deepEqual([R.cancels[0].generation, R.cancels[0].message.requestId],
      [paint.generation, paint.message.requestId]);
  });

  test("dormant wrappers pass arguments, this and return values through unchanged", async () => {
    const win = makeWindow();
    const seen = [];
    const sentinel = {sentinel: true};
    class Probe {
      action(...args) { seen.push(["action", this, args]); return sentinel; }
      deleteKey(...args) { seen.push(["deleteKey", this, args]); return sentinel; }
      commitText(...args) { seen.push(["commitText", this, args]); return sentinel; }
      save(...args) { seen.push(["save", this, args]); return sentinel; }
      async open(...args) { seen.push(["open", this, args]); return sentinel; }
    }
    installFourArmsObserver(win, {Session: Probe});
    const probe = new Probe();
    const options = {extendSelection: true};
    for (const [method, args] of [["action", ["move-character-right", options]], ["deleteKey", ["delete-backward", {}]],
      ["commitText", ["x", {metadata: {requestNumber: 3}}]], ["save", [{timeoutMs: 5}]]]) {
      assert.equal(probe[method](...args), sentinel, method);
      const [name, self, received] = seen.at(-1);
      assert.equal(name, method);
      assert.equal(self, probe);
      assert.equal(received.length, args.length);
      received.forEach((value, i) => assert.equal(value, args[i], `${method} argument ${i}`));
    }
    const input = {bytes: new ArrayBuffer(4), name: "a.odt"};
    assert.equal(await probe.open(input, "extra"), sentinel);
    assert.equal(seen.at(-1)[1], probe);
    assert.equal(seen.at(-1)[2][0], input);
    assert.equal(seen.at(-1)[2][1], "extra");
    const worker = new win.Worker("./w.js");
    const message = {kind: "request", requestId: 1, operation: "x", payload: {}};
    const transfer = [new ArrayBuffer(2)];
    assert.equal(worker.postMessage(message, transfer), "native-post");
    assert.equal(worker.posted.at(-1), message);
    assert.equal(worker.postedRest.at(-1)[0], transfer);
    assert.equal(win.__fourArms.requests.length, 0);
    assert.equal(win.__fourArms.admissions.length, 0);
  });

  test("while recording, the session wrappers still return the original promise object", async () => {
    const win = makeWindow();
    const promise = Promise.resolve("value");
    class Probe { action() { return promise; } }
    installFourArmsObserver(win, {Session: Probe});
    await win.__fourArmsControl.begin({profile: "p", served: []});
    assert.equal(new Probe().action("move-character-right", {}), promise);
    assert.equal(win.__fourArms.admissions.length, 1);
  });

  test("instrument calls own exactly their one synchronously posted request", async () => {
    const {R, prepared, prepared2} = await scenario();
    assert.equal(prepared.ok, true, JSON.stringify(prepared));
    assert.equal(prepared2.ok, true, JSON.stringify(prepared2));
    for (const call of R.calls) {
      const owned = R.requests.slice(call.requestStart, call.requestEnd);
      assert.equal(owned.length, 1, call.name);
      assert.equal(owned[0].issuer, "instrument");
      assert.equal(owned[0].callId, call.id);
    }
    const product = R.requests.filter((r) => r.issuer === "product").map((r) => r.message.operation);
    assert.deepEqual(product, ["open", "editorActionV2", "editorActionV2", "paint", "open", "insertText", "editorActionV2"]);
  });

  test("admissions are tied to the trusted key being dispatched, releases are not", async () => {
    const {R, k1, k2, k3} = await scenario();
    const moves = R.admissions.filter((a) => a.method === "action" && a.cellId === "c1");
    assert.equal(moves.length, 2);
    const [first, released] = moves;
    const input = (event) => R.inputs.find((i) => i.type === "keydown" && i.timeStamp === event.timeStamp);
    assert.equal(first.inputSeq, input(k1).seq);
    assert.equal(released.inputSeq, null);
    assert.deepEqual(input(k1).admissions, [first.id]);
    assert.deepEqual(input(k2).admissions, []);
    assert.equal(input(k2).defaultPrevented, true);
    assert.equal(input(k3).defaultPrevented, true);
    assert.ok(Number.isInteger(first.settledSeq) && Number.isInteger(released.settledSeq));
    assert.equal(first.extendSelection, true);
  });

  test("the release-time sets keep wire-pending, queued and retained candidates apart", async () => {
    const {R, up, k4} = await scenario();
    const keyup = R.inputs.find((i) => i.type === "keyup");
    const shot = R.snapshots.find((s) => s.inputSeq === keyup.seq && s.phase === "capture");
    const k4seq = R.inputs.find((i) => i.type === "keydown" && i.timeStamp === k4.timeStamp).seq;
    const moves = R.requests.filter((r) => r.issuer === "product" && r.message.operation === "editorActionV2");
    assert.deepEqual(shot.wirePending.filter((p) => p[2] === "editorActionV2"),
      [[moves[1].generation, moves[1].message.requestId, "editorActionV2", "move:move-character-right:true"]]);
    assert.deepEqual(shot.unposted, []);
    assert.deepEqual(shot.pageRetained, [k4seq]);
    assert.deepEqual(shot.latestExtensionTerminal, [moves[0].generation, moves[0].message.requestId]);
    assert.equal(up.defaultPrevented, false);
    const cells = Object.fromEntries(R.cells.map((c) => [c.cellId, c]));
    for (const s of R.snapshots) {
      const {seq, phase, inputSeq, cellId, type, key, ...sets} = s;
      assert.deepEqual(sets, releaseSets(R, cells[cellId], seq), `snapshot ${seq} ${phase}`);
    }
    const settled = R.snapshots.filter((s) => s.phase === "after" && s.cellId === "c1");
    assert.equal(settled.length, R.inputs.filter((i) => i.type !== "input" && i.cellId === "c1").length);
  });

  test("queued work behind typed text is unposted, not wire-pending", async () => {
    const {R, shiftRight} = await scenario();
    const keydown = R.inputs.find((i) => i.type === "keydown" && i.timeStamp === shiftRight.timeStamp);
    const after = R.snapshots.find((s) => s.inputSeq === keydown.seq && s.phase === "after");
    const move = R.admissions.find((a) => a.cellId === "c2" && a.method === "action");
    assert.equal(move.inputSeq, keydown.seq);
    assert.deepEqual(after.unposted, [move.id]);
    assert.deepEqual(after.wirePending.map((p) => p[2]), ["insertText"]);
    assert.deepEqual(after.pageRetained, []);
  });

  test("the reference runs in ordered bounded chunks", async () => {
    const win = makeWindow();
    const Session = makeSession(win);
    installFourArmsObserver(win, {Session});
    const control = win.__fourArmsControl;
    await control.begin({profile: "p", served: []});
    const session = new Session();
    await session.open({bytes: new TextEncoder().encode("ref").buffer, name: "ref.odt"});
    assert.equal((await control.prepare({cellId: "ref", kind: "reference", openName: "ref.odt",
      setup: {kind: "caret", query: "Paragraph 001."}})).ok, true);
    session.engine.autoActions = true;
    assert.equal((await control.reference("ref", 1, 3)).ok, true);
    assert.equal((await control.reference("ref", 5, 6)).ok, false);
    assert.equal((await control.reference("ref", 4, 5)).ok, true);
    const cell = win.__fourArms.cells.find((c) => c.cellId === "ref");
    assert.deepEqual(cell.reference.map((s) => s.step), [1, 2, 3, 4, 5]);
    control.closeCell("ref", null);
    assert.equal(cell.generationAtClose, 1);
    assert.equal(cell.pageStateAtClose, "ready");
  });

  test("a paint bitmap is kept as its length and SHA-256", async () => {
    const {R, pixels} = await scenario();
    const paint = R.responses.find((r) => r.message.result?.pixels);
    assert.deepEqual(paint.message.result.pixels, {encoding: "sha256", bytes: 8,
      sha256: createHash("sha256").update(pixels).digest("hex")});
  });

  test("the measured window carries no instrument read; finish reads after it", async () => {
    const {R, finished} = await scenario();
    assert.equal(finished.ok, true);
    const cell = R.cells.find((c) => c.cellId === "c1");
    const inside = R.calls.filter((c) => c.seq >= cell.armSeq && c.seq < cell.measureEndSeq);
    assert.deepEqual(inside, []);
    assert.deepEqual(R.calls.filter((c) => c.seq > cell.measureEndSeq && c.name.startsWith("c1-")).map((c) => c.name),
      ["c1-final-state", "c1-final-text"]);
    assert.equal(cell.sinkAtArm.active, true);
    assert.equal(cell.generationAtArm, 2);
  });
}
