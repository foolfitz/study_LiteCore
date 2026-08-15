// SPEC E2-C, phase D2: recovery and no-replay.
//
// This is the phase that exercises FAILURE paths, which is why it is written
// before the round-two relink rather than after it: an engine defect that only
// shows up when something goes wrong is exactly the kind that turns one planned
// relink into two.
//
// Every cell drives the PRODUCT session (`NarrowEditorV2Session`), and the
// caret is formed the way the product page forms it -- click, then poll until
// the engine confirms a collapsed caret.  Round one drove twenty-seven cells
// with a zero-width `selectRange` instead, and that turned out to be a
// different gesture with a different outcome (SPEC E2-C 9.5.6).
//
// The page judges nothing.  tools/analyze_e2_c_d2.py applies the frozen
// criteria offline.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";
import { formatFailureDisposition }
  from "./editor-shell-v2/paragraph-editor-client.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const fixture = params.get("fixture") || "d1-anchors.odt";
const only = params.get("only");
const stepTimeoutMs = 30000;

const metrics = {
  schemaVersion: 1,
  release: "spec-e2c-d2",
  phase: "D2",
  profile,
  fixture,
  browser: navigator.userAgent,
  cells: {},
  workers: { created: 0, terminated: 0, intentionalCrashes: 0 },
  complete: false,
  error: null,
};
globalThis.__e2c_d2 = metrics;
globalThis.__probe_metrics = metrics;

const saves = [];
globalThis.__e2c_d2_save_count = () => saves.length;
globalThis.__e2c_d2_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: String(error?.message || error).slice(0, 300),
  recovery: error?.recovery ?? null,
  disposition: (() => {
    try { return formatFailureDisposition(error); } catch { return null; }
  })(),
  formatBarrier: error?.details?.formatBarrier ?? null,
});

async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}

// ---------------------------------------------------------------- the worker
//
// A factory that can kill its worker on demand, the same shape E1-C used: the
// crash barriers need a worker that dies the way one really dies, and a
// synthetic ErrorEvent followed by terminate() is what the SDK sees when one
// does.
let activeWorker = null;

function workerFactory(url) {
  const worker = new Worker(url, { name: `e2-c-d2-${metrics.workers.created + 1}` });
  metrics.workers.created += 1;
  let terminated = false;
  activeWorker = {
    terminate() {
      if (terminated) return;
      terminated = true;
      metrics.workers.terminated += 1;
      worker.terminate();
    },
    crash(label) {
      metrics.workers.intentionalCrashes += 1;
      worker.dispatchEvent(new ErrorEvent("error", {
        message: `intentional E2-C D2 ${label} worker crash`,
      }));
      this.terminate();
    },
  };
  return {
    addEventListener: (...args) => worker.addEventListener(...args),
    removeEventListener: (...args) => worker.removeEventListener(...args),
    postMessage: (...args) => worker.postMessage(...args),
    terminate: () => activeWorker.terminate(),
  };
}

async function fixtureBytes() {
  const response = await fetch(`./e2-fixtures/${fixture}`, { cache: "no-cache" });
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  return response.arrayBuffer();
}

function newSession() {
  return new NarrowEditorV2Session({
    engineFactory: () => createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`,
      workerFactory, timeoutMs: 60000,
    }),
    secureContext: globalThis.isSecureContext,
    clipboard: navigator.clipboard,
  });
}

async function openSession() {
  const session = newSession();
  await session.open({ bytes: (await fixtureBytes()).slice(0), name: fixture });
  session.attachInput(document.querySelector("#sink"));
  return session;
}

async function snapshot(session, label) {
  // `EditorSession.save()` resolves to {bytes, revision, contentStamp}, not to
  // the bytes.  The first version treated it as an ArrayBuffer, so every
  // snapshot silently produced an empty base64 string and the runner filed
  // nothing -- the zero-mutation cells would have had no documents to compare
  // and would have failed for a reason that had nothing to do with the engine.
  const { bytes } = await session.save();
  saves.push({ label, b64: await toBase64(bytes) });
  return bytes.byteLength;
}

/** Anchor sweep, in a document that is then thrown away. */
async function surveyAnchor(anchor) {
  const engine = await createDocumentEngine({
    workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
  });
  const handle = await engine.open((await fixtureBytes()).slice(0),
                                   { name: fixture, timeoutMs: 180000 });
  let found = null;
  for (let y = 1300; y <= 14000; y += 130) {
    try {
      await engine._request("editorSelectRangeV2", {
        documentHandle: handle.handle, startXTwips: 1450, startYTwips: y,
        endXTwips: 9000, endYTwips: y,
      }, { timeoutMs: stepTimeoutMs });
      const selection = await handle.getSelection({ timeoutMs: stepTimeoutMs });
      if ((selection.text || "").includes(anchor)) { found = y; break; }
    } catch { /* keep sweeping */ }
  }
  await handle.close({ timeoutMs: stepTimeoutMs }).catch(() => {});
  engine.dispose();
  return found;
}

const anchors = new Map();
async function anchorY(anchor) {
  if (!anchors.has(anchor)) anchors.set(anchor, await surveyAnchor(anchor));
  const y = anchors.get(anchor);
  if (y == null) throw Object.assign(new Error(`anchor ${anchor} not found`),
                                     { code: "ANCHOR_NOT_FOUND" });
  return y;
}

/** The product's own caret gesture (SPEC E2-C 9.5.6). */
async function caretAt(session, y) {
  await session.placeCaret(2000, y);
}

// ------------------------------------------------------------------- cells

const CELLS = {
  "d2-stale-revision": async () => {
    const session = await openSession();
    const entry = {};
    try {
      await caretAt(session, await anchorY("E2-D1-LIST-UNORDERED"));
      const before = await snapshot(session, "stale-revision-before");
      const error = await session.action("set-list-unordered",
                                         { expectedRevision: 9999 })
        .then(() => null, (e) => e);
      entry.error = error ? publicError(error) : null;
      entry.accepted = error === null;
      entry.savedBytes = { before, after: await snapshot(session, "stale-revision-after") };
      entry.state = session.state.snapshot.state;
    } finally { await session.close().catch(() => {}); }
    return entry;
  },

  "d2-stale-handle": async () => {
    const session = await openSession();
    const entry = {};
    try {
      const stale = session.document;
      const before = await snapshot(session, "stale-handle-before");
      await session.close();
      const error = await stale._engine._request("editorActionV2", {
        documentHandle: stale.handle, expectedRevision: stale.revision,
        action: "set-list-unordered", extendSelection: false, enabled: false,
      }, { timeoutMs: stepTimeoutMs }).then(() => null, (e) => e);
      entry.error = error ? publicError(error) : null;
      entry.accepted = error === null;
      entry.savedBytes = { before };
    } catch (error) {
      entry.setupError = publicError(error);
    }
    return entry;
  },

  "d2-refused-no-mutation-client": async () => {
    const session = await openSession();
    const entry = { attempts: [] };
    try {
      await caretAt(session, await anchorY("E2-D1-LIST-UNORDERED"));
      const before = await snapshot(session, "client-refusal-before");
      for (const [label, call] of [
        ["bad kind", () => session.setList("bulleted")],
        ["bad style", () => session.setParagraphStyle("h2")],
        ["unknown action", () => session.action("set-superscript")],
      ]) {
        const error = await call().then(() => null, (e) => e);
        entry.attempts.push({ label, error: error ? publicError(error) : null });
      }
      entry.savedBytes = { before,
                           after: await snapshot(session, "client-refusal-after") };
      entry.state = session.state.snapshot.state;
    } finally { await session.close().catch(() => {}); }
    return entry;
  },

  "d2-unknown-rollback-fallback": async () => {
    // No engine involved: this is the fail-closed rule itself, checked on an
    // error with the barrier field stripped.  It is in D2 rather than a unit
    // test because SPEC E2-C 4.1 requires all three dispositions to have a
    // measured cell, and a rule nobody exercises in the round is a rule that
    // can rot between rounds.
    const shaped = Object.assign(new Error("no barrier field"),
                                 { code: "MUTATION_OUTCOME_UNKNOWN" });
    return {
      disposition: formatFailureDisposition(shaped),
      code: shaped.code,
    };
  },

  "d2-refused-no-mutation-engine": async () => {
    const session = await openSession();
    const entry = {};
    try {
      // A paragraph carrying an as-char frame: the finding 037 type guard
      // refuses it BEFORE dispatch, which is the clean shape.
      await caretAt(session, await anchorY("E2-D1-LIST-ORDERED"));
      const before = await snapshot(session, "engine-refusal-before");
      // Ask for a gesture the manifest does not offer for this action: on this
      // profile the ten inherited actions are collapsed-only, so a range is a
      // pre-dispatch refusal with nothing dispatched.
      await session.selectRange({ xTwips: 1450, yTwips: await anchorY("E2-D1-LIST-ORDERED") },
                                { xTwips: 9000, yTwips: await anchorY("E2-D1-LIST-ORDERED") });
      const error = await session.action("set-bold", { enabled: true })
        .then(() => null, (e) => e);
      entry.error = error ? publicError(error) : null;
      entry.accepted = error === null;
      entry.savedBytes = { before,
                           after: await snapshot(session, "engine-refusal-after") };
      entry.state = session.state.snapshot.state;
    } finally { await session.close().catch(() => {}); }
    return entry;
  },

  "d2-dispatched-rollback": async () => {
    // The full assertion list from SPEC E2-C D2: dirty first, confirm the
    // checkpoint exists, select a range that covers the note reference, then
    // require dispatched:true with the exact failure shape, a fresh worker, and
    // a rolled-back document byte-identical to the checkpoint.
    const session = await openSession();
    const entry = {};
    try {
      const y = await anchorY("E2-D1-INTERLEAVE");
      await caretAt(session, y);
      await session.commitText("D2DIRTY");
      entry.dirty = session.state.snapshot.dirty;
      await session.selectRange({ xTwips: 1450, yTwips: y },
                                { xTwips: 9000, yTwips: y });
      entry.hasCheckpoint = session.state.snapshot.hasCheckpoint;
      entry.checkpointRevision = session.state.snapshot.checkpointRevision;
      await snapshot(session, "dispatched-rollback-before");
      const error = await session.setParagraphStyle("heading")
        .then(() => null, (e) => e);
      entry.error = error ? publicError(error) : null;
      entry.stateAfterFailure = session.state.snapshot.state;
      if (error) {
        const rolled = await session.rollback().then(() => "ok", (e) => publicError(e));
        entry.rollback = rolled;
        entry.stateAfterRollback = session.state.snapshot.state;
        if (rolled === "ok")
          await snapshot(session, "dispatched-rollback-after");
      }
    } catch (error) {
      entry.setupError = publicError(error);
    } finally { await session.close().catch(() => {}); }
    return entry;
  },

  "d2-boundary-restart-required": async () => {
    const session = await openSession();
    const entry = {};
    try {
      // A delete at a structural boundary: the engine refuses with
      // EDITOR_BOUNDARY_UNSUPPORTED and the session must enter restart-required
      // rather than carrying on.
      await caretAt(session, await anchorY("E2-D1-HEADING"));
      const error = await session.action("delete-backward")
        .then(() => null, (e) => e);
      entry.error = error ? publicError(error) : null;
      entry.state = session.state.snapshot.state;
      // Anything queued behind it must be rejected, not run.
      const queued = await session.action("set-italic", { enabled: true })
        .then(() => null, (e) => e);
      entry.queuedAfter = queued ? publicError(queued) : null;
    } finally { await session.close().catch(() => {}); }
    return entry;
  },

  "d2-crash-unsaved-edit": async () => {
    const session = await openSession();
    const entry = {};
    try {
      await caretAt(session, await anchorY("E2-D1-INSERT"));
      await session.commitText("D2UNSAVED");
      entry.dirtyBeforeCrash = session.state.snapshot.dirty;
      activeWorker.crash("unsaved-edit");
      await new Promise((resolve) => setTimeout(resolve, 500));
      entry.stateAfterCrash = session.state.snapshot.state;
      const restarted = await session.restart().then(() => "ok", (e) => publicError(e));
      entry.restart = restarted;
      entry.stateAfterRestart = session.state.snapshot.state;
      if (restarted === "ok")
        await snapshot(session, "crash-unsaved-after-restart");
    } catch (error) {
      entry.setupError = publicError(error);
    } finally { await session.close().catch(() => {}); }
    return entry;
  },

  "d2-crash-after-save": async () => {
    const session = await openSession();
    const entry = {};
    try {
      await caretAt(session, await anchorY("E2-D1-INSERT"));
      await session.commitText("D2SAVED");
      await snapshot(session, "crash-after-save-authority");
      entry.dirtyAfterSave = session.state.snapshot.dirty;
      activeWorker.crash("after-save");
      await new Promise((resolve) => setTimeout(resolve, 500));
      const restarted = await session.restart().then(() => "ok", (e) => publicError(e));
      entry.restart = restarted;
      if (restarted === "ok")
        await snapshot(session, "crash-after-save-restored");
    } catch (error) {
      entry.setupError = publicError(error);
    } finally { await session.close().catch(() => {}); }
    return entry;
  },

  "d2-crash-after-checkpoint": async () => {
    const session = await openSession();
    const entry = {};
    try {
      const y = await anchorY("E2-D1-INSERT");
      await caretAt(session, y);
      await session.commitText("D2CHECKPOINT");
      await session.selectRange({ xTwips: 1450, yTwips: y },
                                { xTwips: 9000, yTwips: y });
      entry.hasCheckpoint = session.state.snapshot.hasCheckpoint;
      activeWorker.crash("after-checkpoint");
      await new Promise((resolve) => setTimeout(resolve, 500));
      const restarted = await session.restart().then(() => "ok", (e) => publicError(e));
      entry.restart = restarted;
      entry.dirtyAfterRestart = session.state.snapshot.dirty;
      entry.hasCheckpointAfterRestart = session.state.snapshot.hasCheckpoint;
      if (restarted === "ok")
        await snapshot(session, "crash-after-checkpoint-restored");
    } catch (error) {
      entry.setupError = publicError(error);
    } finally { await session.close().catch(() => {}); }
    return entry;
  },

  "d2-crash-queued-mutation": async () => {
    const session = await openSession();
    const entry = {};
    try {
      await caretAt(session, await anchorY("E2-D1-LIST-UNORDERED"));
      // Queue two without awaiting the first, then kill the worker underneath.
      const first = session.action("set-list-unordered").then(() => "ok",
                                                             (e) => publicError(e));
      const second = session.action("set-list-ordered").then(() => "ok",
                                                             (e) => publicError(e));
      activeWorker.crash("queued-mutation");
      entry.first = await first;
      entry.second = await second;
      entry.state = session.state.snapshot.state;
      const restarted = await session.restart().then(() => "ok", (e) => publicError(e));
      entry.restart = restarted;
      if (restarted === "ok")
        await snapshot(session, "crash-queued-after-restart");
    } catch (error) {
      entry.setupError = publicError(error);
    } finally { await session.close().catch(() => {}); }
    return entry;
  },

  "d2-generation-ceiling": async () => {
    const session = await openSession();
    const entry = { restarts: [] };
    try {
      for (let attempt = 0; attempt < 4; attempt += 1) {
        activeWorker.crash(`ceiling-${attempt + 1}`);
        await new Promise((resolve) => setTimeout(resolve, 400));
        const result = await session.restart().then(
          () => ({ ok: true, generation: session.state.snapshot.generation }),
          (error) => ({ ok: false, error: publicError(error),
                        requiresPageReload:
                          error?.details?.requiresPageReload ?? null }));
        entry.restarts.push(result);
        if (!result.ok) break;
      }
    } catch (error) {
      entry.setupError = publicError(error);
    } finally { await session.close().catch(() => {}); }
    return entry;
  },
};

void (async () => {
  try {
    {
      const engine = await createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
      });
      const contract = engine.manifest?.editorContract || {};
      metrics.cells["d0-inventory"] = {
        profile: engine.manifest?.profile,
        wasmSha256: contract.wasmSha256,
        loaderSha256: contract.loaderSha256,
        workerSha256: contract.workerSha256,
      };
      engine.dispose();
    }

    const names = only ? only.split(",") : Object.keys(CELLS);
    for (const name of names) {
      const cell = CELLS[name];
      if (!cell) { log({ cell: name, skipped: "no such cell" }); continue; }
      let entry;
      try {
        entry = await cell();
      } catch (error) {
        entry = { fatal: publicError(error) };
      }
      metrics.cells[name] = entry;
      log({ cell: name, ...entry });
    }

    metrics.complete = true;
    log({ complete: true, cells: Object.keys(metrics.cells).length,
          saves: saves.length, workers: metrics.workers });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  }
})();
