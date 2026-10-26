// v23 product four arms: observation-only core.
//
// Installed by `v23-product-four-arms-observer.js`, which the product runner serves in a
// DECLARED mirror in place of the page's module entry; that entry then imports the unchanged
// product app.  Nothing here changes product, SDK or worker bytes.  It wraps, at runtime and as
// pass-through:
//   * window.Worker            raw request / cancel / response / event records, per generation;
//   * NarrowEditorV2Session    open (bytes hash, handle), and the page's admissions into the
//                              session (action, deleteKey, commitText, save);
//   * window key listeners     trusted keydown / keyup / beforeinput with flags and times.
// It is DORMANT until `__fourArmsControl.begin()`: before that only Worker generations and the
// current session are tracked, so the runner's earlier checks run against a pass-through.
//
// Request ownership for the instrument's own reads is the half-open request-array window of the
// SYNCHRONOUS invocation of a client/document method: those methods post their one request
// before returning, so [requestStart, requestEnd) holds exactly that request whatever else is in
// flight.  Paint bitmaps are kept as length + SHA-256 (a full bitmap per paint made records
// exceed V8's string limit in selection-prep-04).
//
// Three sets are recorded at every measured trusted input, in the capture phase (before the
// page reacts) and after dispatch:
//   admitted     the page's admissions into the session in this cell (ids);
//   unposted     admitted, not settled, and not yet matched FIFO, per category, to a posted
//                product request -- the session's queued / held-behind-typing work;
//   pageRetained trusted keydowns the page took (defaultPrevented) with no admission during
//                their dispatch, since the last admission: the page's held repeat or a
//                depth-refused one.  Which of the two is not observable without editing the page,
//                so these are CANDIDATES and never enter a wire bound;
//   wirePending  product requests posted without a response or cancel.
// The reader recomputes all of them from the raw arrays; these snapshots are a cross-check.

export const OBSERVER_SCHEMA = 1;
export const DEAD_STATES = ["recoverable-error", "restart-required", "expired"];
const LINKED_OPERATIONS = new Set(["editorActionV2", "insertText"]);
const DELETE_ACTIONS = new Set(["delete-backward", "delete-forward", "delete-selection"]);

/** The linking category of a session admission (null: not linked to a wire request). */
export function admissionCategory(admission) {
  if (admission.method === "commitText") return "text";
  if (admission.method === "deleteKey") return "delete";
  if (admission.method === "action") {
    if (DELETE_ACTIONS.has(admission.action)) return "delete";
    if (String(admission.action).startsWith("move-"))
      return `move:${admission.action}:${admission.extendSelection === true}`;
    return `action:${admission.action}`;
  }
  return null;
}

/** The linking category of a raw request record (null: not a linked operation). */
export function requestCategory(request) {
  const message = request.message || {};
  if (!LINKED_OPERATIONS.has(message.operation)) return null;
  if (message.operation === "insertText") return "text";
  const payload = message.payload || {};
  if (DELETE_ACTIONS.has(payload.action)) return "delete";
  if (String(payload.action).startsWith("move-"))
    return `move:${payload.action}:${payload.extendSelection === true}`;
  return `action:${payload.action}`;
}

export const keyOf = (generation, requestId) => `${generation}:${requestId}`;

/**
 * The three sets at sequence boundary `boundary` for `cell`, from the raw arrays only.
 * Mirrored by `release_sets` in tools/judge_v23_product_four_arms.py.
 */
export function releaseSets(record, cell, boundary) {
  const generation = cell.generation;
  const inCell = (item) => item.seq >= cell.armSeq && item.seq < boundary;
  const admissions = record.admissions.filter((a) => a.issuer === "product" && a.generation === generation && inCell(a));
  const requests = record.requests.filter((r) => r.issuer === "product" && r.generation === generation && inCell(r));
  const terminals = new Set();
  for (const item of [...record.responses, ...record.cancels])
    if (item.generation === generation && item.seq < boundary) terminals.add(keyOf(generation, item.message.requestId));
  const byCategory = new Map();
  for (const request of requests) {
    const category = requestCategory(request);
    if (category === null) continue;
    if (!byCategory.has(category)) byCategory.set(category, []);
    byCategory.get(category).push(request);
  }
  const used = new Map();
  const unposted = [];
  for (const admission of admissions) {
    const category = admissionCategory(admission);
    if (category === null || category === "save") continue;
    const index = used.get(category) || 0;
    used.set(category, index + 1);
    const posted = (byCategory.get(category) || [])[index];
    const settled = Number.isInteger(admission.settledSeq) && admission.settledSeq < boundary;
    if (!posted && !settled) unposted.push(admission.id);
  }
  const lastAdmission = admissions.reduce((max, a) => Math.max(max, a.seq), -1);
  const pageRetained = record.inputs.filter((i) => i.type === "keydown" && i.isTrusted === true
      && inCell(i) && i.seq > lastAdmission && Number.isInteger(i.afterSeq) && i.afterSeq < boundary
      && i.defaultPrevented === true && Array.isArray(i.admissions) && i.admissions.length === 0)
    .map((i) => i.seq);
  const allRequests = record.requests.filter((r) => r.issuer === "product" && r.generation === generation && r.seq < boundary);
  const wirePending = allRequests.filter((r) => !terminals.has(keyOf(r.generation, r.message.requestId)))
    .map((r) => [r.generation, r.message.requestId, r.message.operation, requestCategory(r)]);
  const extensionKeys = new Set(requests.filter((r) => requestCategory(r) === "move:move-character-right:true")
    .map((r) => keyOf(r.generation, r.message.requestId)));
  let latest = null;
  for (const response of record.responses) {
    if (response.generation !== generation || response.seq >= boundary) continue;
    if (!extensionKeys.has(keyOf(response.generation, response.message.requestId))) continue;
    if (latest === null || response.seq > latest.seq) latest = response;
  }
  return {
    admitted: admissions.map((a) => a.id),
    unposted,
    pageRetained,
    wirePending,
    latestExtensionTerminal: latest ? [latest.generation, latest.message.requestId] : null,
  };
}

export function installFourArmsObserver(win, { Session }) {
  const doc = win.document;
  const subtle = win.crypto?.subtle;
  const now = () => win.performance.now();
  const R = {
    schema: OBSERVER_SCHEMA, instrument: "v23-product-four-arms",
    userAgent: win.navigator?.userAgent ?? null,
    recording: false, seq: 0, begunAt: null, identity: null,
    workers: [], requests: [], responses: [], events: [], cancels: [], workerErrors: [],
    inputs: [], admissions: [], calls: [], opens: [], cells: [], snapshots: [], failures: [],
    orphanResponses: 0, orphanCancels: 0,
  };
  const pendingHashes = [];
  const paintKeys = new Set();
  const postedKeys = new Set();
  let generation = 0;
  let current = null;
  let instrumentDepth = 0;
  let activeCall = null;
  let dispatching = null;
  let activeCell = null;
  const next = () => ++R.seq;

  const bytes64 = (buffer) => {
    const bytes = new Uint8Array(buffer);
    let text = "";
    for (let i = 0; i < bytes.length; i += 8192) text += String.fromCharCode(...bytes.subarray(i, i + 8192));
    return win.btoa(text);
  };
  const hex = (digest) => [...new Uint8Array(digest)].map((x) => x.toString(16).padStart(2, "0")).join("");
  const hashBytes = async (bytes) => hex(await subtle.digest("SHA-256", bytes));
  const copyView = (value) => (ArrayBuffer.isView(value)
    ? new Uint8Array(value.buffer, value.byteOffset, value.byteLength).slice()
    : new Uint8Array(value).slice());
  const snap = (value) => {
    if (value instanceof ArrayBuffer) return { encoding: "base64", bytes: value.byteLength, data: bytes64(value) };
    if (ArrayBuffer.isView(value)) return snap(copyView(value).buffer);
    if (Array.isArray(value)) return value.map(snap);
    if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, snap(v)]));
    return value;
  };
  // Results kept on admissions: never the saved bytes (the wire response already has them).
  const lite = (value) => {
    if (value instanceof ArrayBuffer || ArrayBuffer.isView(value)) return { byteLength: value.byteLength };
    if (Array.isArray(value)) return value.map(lite);
    if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, lite(v)]));
    return value;
  };
  const errorRecord = (error) => ({ code: error?.code ?? null, message: String(error?.message || error) });
  function paintResponse(data) {
    const pixels = data?.result?.pixels;
    if (!(pixels instanceof ArrayBuffer || ArrayBuffer.isView(pixels))) return snap(data);
    const copy = copyView(pixels);
    const message = snap({ ...data, result: { ...data.result, pixels: undefined } });
    message.result.pixels = { encoding: "sha256", bytes: copy.byteLength, sha256: null };
    pendingHashes.push(hashBytes(copy).then((h) => { message.result.pixels.sha256 = h; }));
    return message;
  }
  // The engine keeps its Worker private; the latest constructed generation is the fallback,
  // which is the same thing whenever no restart is in flight (every open spawns one Worker).
  const workerGeneration = (session) => session?.engine?._worker?.__fourArmsGeneration ?? (generation || null);

  // ------------------------------------------------------------------ Worker
  const NativeWorker = win.Worker;
  class ObservedWorker extends NativeWorker {
    constructor(url, options) {
      super(url, options);
      const gen = ++generation;
      const record = { generation: gen, url: String(url), createdAt: now(), seq: next() };
      Object.defineProperty(this, "__fourArmsGeneration", { value: gen });
      Object.defineProperty(this, "__fourArmsRecord", { value: record });
      R.workers.push(record);
      this.addEventListener("message", (event) => {
        if (!R.recording) return;
        const data = event.data;
        if (data?.kind === "event") {
          R.events.push({ seq: next(), generation: gen, at: now(), message: snap(data) });
        } else if (data?.kind === "response") {
          const key = keyOf(gen, data.requestId);
          if (!postedKeys.has(key)) { R.orphanResponses += 1; return; }
          const message = paintKeys.delete(key) ? paintResponse(data) : snap(data);
          R.responses.push({ seq: next(), generation: gen, at: now(), message });
        }
      });
      this.addEventListener("error", (event) => {
        if (R.recording) R.workerErrors.push({ seq: next(), generation: gen, at: now(), message: String(event?.message ?? "") });
      });
    }
    postMessage(message, ...rest) {
      if (R.recording && message?.kind === "cancel" && !postedKeys.has(keyOf(this.__fourArmsGeneration, message.requestId))) {
        // Same rule as responses: a cancel of a request posted before begin() has no
        // recorded request, so it is counted, never recorded beside the stream.
        R.orphanCancels += 1;
      } else if (R.recording && (message?.kind === "request" || message?.kind === "cancel")) {
        const item = { seq: next(), generation: this.__fourArmsGeneration, at: now(),
          issuer: instrumentDepth > 0 ? "instrument" : "product",
          callId: instrumentDepth > 0 && activeCall ? activeCall.id : null, message: snap(message) };
        if (message.kind === "request") {
          R.requests.push(item);
          postedKeys.add(keyOf(item.generation, message.requestId));
          if (message.operation === "paint") paintKeys.add(keyOf(item.generation, message.requestId));
        } else {
          R.cancels.push(item);
        }
      }
      return super.postMessage(message, ...rest);
    }
    terminate() {
      this.__fourArmsRecord.terminatedAt = now();
      if (R.recording) this.__fourArmsRecord.terminatedSeq = next();
      return super.terminate();
    }
  }
  win.Worker = ObservedWorker;

  // ------------------------------------------------------- session prototype
  const openOriginal = Session.prototype.open;
  Session.prototype.open = async function open(input, ...args) {
    current = this;
    if (!R.recording) return openOriginal.call(this, input, ...args);
    const record = { serial: R.opens.length + 1, name: input?.name ?? null, seq: next(), startedAt: now(),
      fixtureSha256: null };
    R.opens.push(record);
    if (input?.bytes) record.fixtureSha256 = await hashBytes(copyView(input.bytes));
    try {
      const value = await openOriginal.call(this, input, ...args);
      Object.assign(record, { ok: true, finishedAt: now(), finishSeq: next(),
        generation: workerGeneration(this) ?? generation, documentHandle: this.document?.handle ?? null });
      return value;
    } catch (error) {
      Object.assign(record, { ok: false, finishedAt: now(), finishSeq: next(), error: errorRecord(error) });
      throw error;
    }
  };
  const currentInput = () => (dispatching && dispatching.event.eventPhase !== 0 ? dispatching.record : null);
  for (const method of ["action", "deleteKey", "commitText", "save"]) {
    const original = Session.prototype[method];
    if (typeof original !== "function") continue;
    Session.prototype[method] = function admitted(...args) {
      if (!R.recording) return original.apply(this, args);
      const input = currentInput();
      const record = { id: R.admissions.length + 1, seq: next(), at: now(), method,
        issuer: instrumentDepth > 0 ? "instrument" : "product", inputSeq: input ? input.seq : null,
        generation: workerGeneration(this), documentHandle: this.document?.handle ?? null,
        cellId: activeCell ? activeCell.cellId : null, requestIndex: R.requests.length };
      if (method === "action" || method === "deleteKey") {
        record.action = args[0];
        record.extendSelection = args[1]?.extendSelection === true;
      }
      if (method === "commitText") record.text = typeof args[0] === "string" ? args[0] : null;
      R.admissions.push(record);
      if (input) input.admissions.push(record.id);
      let promise;
      try { promise = original.apply(this, args); } finally { record.syncRequestEnd = R.requests.length; }
      if (promise && typeof promise.then === "function") {
        promise.then(
          (value) => { record.settledSeq = next(); record.settledAt = now(); record.ok = true; record.result = lite(value); },
          (error) => { record.settledSeq = next(); record.settledAt = now(); record.ok = false; record.error = errorRecord(error); });
      }
      return promise;
    };
  }

  // ------------------------------------------------------------------ inputs
  const sink = () => doc.querySelector("#sink");
  const sinkSnapshot = () => {
    const el = sink();
    return { id: el?.id ?? null, active: doc.activeElement === el && !!el, disabled: el?.disabled ?? null,
      readOnly: el?.readOnly ?? null, connected: el?.isConnected ?? null,
      documentHandle: current?.document?.handle ?? null, generation: workerGeneration(current) };
  };
  function snapshot(phase, input) {
    if (!activeCell || !activeCell.measuring) return;
    const at = next();
    R.snapshots.push({ seq: at, phase, inputSeq: input.seq, cellId: activeCell.cellId, type: input.type,
      key: input.key ?? null, ...releaseSets(R, activeCell, at) });
  }
  for (const type of ["keydown", "keyup", "beforeinput", "input"]) {
    win.addEventListener(type, (event) => {
      if (!R.recording) return;
      const record = { seq: next(), type, at: now(), timeStamp: event.timeStamp, isTrusted: event.isTrusted,
        key: event.key ?? null, code: event.code ?? null, repeat: event.repeat ?? null,
        shiftKey: event.shiftKey ?? null, ctrlKey: event.ctrlKey ?? null, altKey: event.altKey ?? null,
        metaKey: event.metaKey ?? null, inputType: event.inputType ?? null, data: event.data ?? null,
        targetId: event.target?.id ?? null, cellId: activeCell ? activeCell.cellId : null,
        sink: sinkSnapshot(), admissions: [] };
      R.inputs.push(record);
      dispatching = { event, record };
      if (type !== "input" && event.isTrusted === true) snapshot("capture", record);
    }, true);
    win.addEventListener(type, (event) => {
      if (!R.recording || dispatching?.event !== event) return;
      const record = dispatching.record;
      record.afterSeq = next();
      record.defaultPrevented = event.defaultPrevented;
      if (type !== "input" && event.isTrusted === true) snapshot("after", record);
    });
  }

  // ------------------------------------------------------- instrument calls
  async function call(name, fn) {
    const entry = { id: R.calls.length + 1, name, seq: next(), cellId: activeCell ? activeCell.cellId : null,
      generation: workerGeneration(current), documentHandle: current?.document?.handle ?? null,
      startedAt: now(), requestStart: R.requests.length };
    R.calls.push(entry);
    let promise;
    instrumentDepth += 1;
    activeCall = entry;
    try { promise = fn(); } finally {
      instrumentDepth -= 1;
      activeCall = null;
      entry.requestEnd = R.requests.length;
    }
    try {
      const value = await promise;
      entry.ok = true;
      entry.result = snap(value);
      return value;
    } catch (error) {
      entry.ok = false;
      entry.error = errorRecord(error);
      throw error;
    } finally {
      entry.finishedAt = now();
      entry.finishSeq = next();
    }
  }
  const state = (name) => call(name, () => current.editor.getState());
  const selection = (name) => call(name, () => current.document.getSelection());
  const point = (caret) => ({ xTwips: caret.x, yTwips: caret.y + Math.floor(caret.height / 2) });
  function singleRectangle(found) {
    const rows = found?.selections;
    if (!Array.isArray(rows) || rows.length !== 1 || ![0, "0"].includes(rows[0]?.part)
        || typeof rows[0].rectangles !== "string") throw new Error("search match is not unique");
    const boxes = rows[0].rectangles.split(";");
    if (boxes.length !== 1 || !/^\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\s*$/.test(boxes[0]))
      throw new Error("search match is not one line");
    const r = boxes[0].split(",").map(Number);
    if (!r.every(Number.isSafeInteger) || r[2] <= 0 || r[3] <= 0) throw new Error("invalid search rectangle");
    return r;
  }
  async function caretAt(prefix, query) {
    const found = await call(`${prefix}-search`, () => current.document.search(query));
    const r = singleRectangle(found);
    await call(`${prefix}-place`, () => current.editor.placeCaret(r[0], r[1] + Math.floor(r[3] / 2)));
    const start = await state(`${prefix}-start-state`);
    if (start?.caret?.x !== r[0] || start?.caret?.y !== r[1] || start?.selection?.collapsed !== true)
      throw new Error("actual text-start caret differs from the search rectangle");
    return { rectangle: r, start };
  }
  const cellOf = (cellId) => {
    const cell = R.cells.find((c) => c.cellId === cellId);
    if (!cell) throw new Error(`unknown cell ${cellId}`);
    return cell;
  };
  const failed = (where, error) => {
    const failure = { where, seq: next(), ...errorRecord(error) };
    R.failures.push(failure);
    return { ok: false, ...failure };
  };
  const quietFor = (cell) => {
    const reasons = [];
    const unsettled = R.admissions.filter((a) => a.issuer === "product" && a.seq >= cell.armSeq && !Number.isInteger(a.settledSeq));
    if (unsettled.length) reasons.push(`unsettled admissions ${unsettled.map((a) => a.id).join(",")}`);
    const sets = releaseSets(R, cell, R.seq + 1);
    const pending = sets.wirePending.filter((p) => !["paint", "pageRectangles"].includes(p[2]));
    if (pending.length) reasons.push(`wire pending ${pending.map((p) => p.slice(0, 3).join(":")).join(",")}`);
    const depth = current?.input?.state?.queueDepth;
    if (typeof depth === "number" && depth > 0) reasons.push(`input adapter queue ${depth}`);
    const downs = R.inputs.filter((i) => i.seq >= cell.armSeq && i.type === "keydown" && i.isTrusted === true);
    const ups = R.inputs.filter((i) => i.seq >= cell.armSeq && i.type === "keyup" && i.isTrusted === true);
    if (downs.length && (!ups.length || ups[ups.length - 1].seq < downs[downs.length - 1].seq))
      reasons.push("a measured key is still down");
    return { quiet: reasons.length === 0, reasons, generation: workerGeneration(current) };
  };

  // ---------------------------------------------------------------- control
  win.__fourArms = R;
  win.__fourArmsPending = pendingHashes;
  win.__fourArmsControl = {
    async begin(config) {
      try {
        R.recording = true;
        R.begunAt = now();
        const served = {};
        for (const path of config.served || []) {
          const response = await win.fetch(`./${path}`, { cache: "no-store" });
          if (!response.ok) throw new Error(`served source HTTP ${response.status} ${path}`);
          served[path] = await hashBytes(await response.arrayBuffer());
        }
        R.identity = { profile: config.profile ?? null, served, configured: config, seq: next() };
        return { ok: true, identity: R.identity };
      } catch (error) { return failed("begin", error); }
    },
    openStatus(name, afterSerial) {
      const record = [...R.opens].reverse().find((o) => o.serial > afterSerial && o.name === name);
      if (!record) return { found: false };
      return { found: true, done: Number.isInteger(record.finishSeq), ok: record.ok === true, serial: record.serial,
        generation: record.generation ?? null, documentHandle: record.documentHandle ?? null,
        error: record.error ?? null, pageState: current?.state?.snapshot?.state ?? null };
    },
    async prepare(spec) {
      const cell = { ...spec, seq: next(), openSerial: R.opens.length, generation: workerGeneration(current),
        documentHandle: current?.document?.handle ?? null, setup: {}, measuring: false };
      R.cells.push(cell);
      try {
        const open = R.opens[R.opens.length - 1];
        if (!open || open.ok !== true || open.name !== spec.openName)
          throw new Error("the cell's fresh open is not the latest successful open");
        cell.generation = open.generation;
        cell.documentHandle = open.documentHandle;
        const plan = spec.setup;
        const located = await caretAt(spec.cellId, plan.query);
        cell.setup.rectangle = located.rectangle;
        cell.setup.start = located.start;
        if (plan.kind === "select") {
          const states = [located.start];
          for (let i = 0; i < plan.end; i += 1) {
            await call(`${spec.cellId}-right-${i}`, () => current.editor.action("move-character-right"));
            states.push(await state(`${spec.cellId}-right-${i}-state`));
          }
          const a = states[plan.start].caret;
          const b = states[plan.end].caret;
          await call(`${spec.cellId}-select`, () => current.editor.selectRange(point(a), point(b)));
          const chosen = await selection(`${spec.cellId}-selected-text`);
          if (chosen?.text !== plan.selectedText) throw new Error("public selection differs from the planned text");
          cell.setup.selectedText = chosen.text;
          cell.setup.states = states;
        }
        cell.setup.before = await state(`${spec.cellId}-before-state`);
        return { ok: true, cellId: spec.cellId };
      } catch (error) { return failed(`prepare ${spec.cellId}`, error); }
    },
    arm(cellId) {
      try {
        const cell = cellOf(cellId);
        const el = sink();
        el?.focus();
        Object.assign(cell, { armSeq: next(), armedAt: now(), inputStart: R.inputs.length,
          requestStart: R.requests.length, sinkAtArm: sinkSnapshot(),
          dirtyAtArm: current?.state?.snapshot?.dirty ?? null,
          pageStateAtArm: current?.state?.snapshot?.state ?? null,
          generationAtArm: workerGeneration(current), measuring: true });
        activeCell = cell;
        return { ok: true, sink: cell.sinkAtArm };
      } catch (error) { return failed(`arm ${cellId}`, error); }
    },
    quiet(cellId) {
      try { return quietFor(cellOf(cellId)); } catch (error) { return { quiet: false, reasons: [String(error)] }; }
    },
    async finish(cellId) {
      const cell = R.cells.find((c) => c.cellId === cellId);
      try {
        if (!cell) throw new Error(`unknown cell ${cellId}`);
        cell.measuring = false;
        cell.measureEndSeq = next();
        cell.quietAtFinish = quietFor(cell);
        cell.final = { state: await state(`${cellId}-final-state`),
          selection: await selection(`${cellId}-final-text`) };
        cell.pageStateAtFinish = current?.state?.snapshot?.state ?? null;
        cell.generationAtFinish = workerGeneration(current);
        return { ok: true };
      } catch (error) { return failed(`finish ${cellId}`, error); } finally { activeCell = null; }
    },
    // Steps first..last only: the runner drives the reference in bounded chunks, so no single
    // awaited execute approaches geckodriver's default 30 s script timeout.
    async reference(cellId, first, last) {
      const cell = R.cells.find((c) => c.cellId === cellId);
      try {
        if (!cell) throw new Error(`unknown cell ${cellId}`);
        cell.reference ||= [];
        if (first !== cell.reference.length + 1) throw new Error("reference steps out of order");
        for (let i = first; i <= last; i += 1) {
          const reply = await call(`${cellId}-step-${i}`,
            () => current.editor.action("move-character-right", { extendSelection: true }));
          const text = await selection(`${cellId}-text-${i}`);
          cell.reference.push({ step: i, revision: reply?.revision ?? null, text: text?.text ?? null });
        }
        return { ok: true, steps: cell.reference.length };
      } catch (error) { return failed(`reference ${cellId}`, error); }
    },
    closeCell(cellId, save) {
      try {
        const cell = cellOf(cellId);
        // A cell that aborted between arm and finish stops measuring here, so no later
        // input is ever attributed to it.
        if (cell.measuring) { cell.measuring = false; cell.aborted = true; }
        if (activeCell === cell) activeCell = null;
        cell.generationAtClose = workerGeneration(current);
        cell.pageStateAtClose = current?.state?.snapshot?.state ?? null;
        cell.save = save ?? null;
        cell.endSeq = next();
        return { ok: true };
      } catch (error) { return failed(`close ${cellId}`, error); }
    },
    end() {
      R.recording = false;
      R.endedSeq = R.seq;
      activeCell = null;
      return { ok: true, seq: R.seq };
    },
    async exportBegin() {
      let count;
      do { count = pendingHashes.length; await Promise.all(pendingHashes.slice()); } while (pendingHashes.length !== count);
      const bytes = new win.TextEncoder().encode(JSON.stringify(R));
      win.__fourArmsExport = bytes;
      return { length: bytes.length, sha256: await hashBytes(bytes) };
    },
    exportChunk(start, end) { return bytes64(win.__fourArmsExport.subarray(start, end)); },
    exportDone() { delete win.__fourArmsExport; return true; },
  };
  return R;
}
