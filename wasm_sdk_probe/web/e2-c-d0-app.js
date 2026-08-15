// SPEC E2-C, phase D0: entry inventory and surface.
//
// A harness, not a product page, and the difference matters twice over.  It
// publishes `globalThis.__e2c_d0` so a runner can read the observations, and it
// judges NOTHING -- the criteria live in e2/validation-matrix-v1.json, frozen
// before this file ran, and tools/analyze_e2_c_d0.py applies them without a
// browser.
//
// The one thing it is careful about is what it drives.  The reachability cell
// uses NarrowEditorV2Client ON ITS OWN, because the check that missed the gap
// for a whole release took the union of every shell in the tree.  The
// zero-mutation cells go through `engine._request` directly, which the product
// never does: they are testing gates that sit BELOW the client, and reaching
// them through a client that refuses first would prove only that the client
// refuses.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Client, EDITOR_V2_ACTIONS }
  from "./editor-shell-v2/narrow-editor-v2-client.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const fixture = params.get("fixture") || "list-contexts.odt";

const metrics = {
  schemaVersion: 1,
  release: "spec-e2c-d0",
  phase: "D0",
  profile,
  fixture,
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  cells: {},
  complete: false,
  error: null,
};
globalThis.__e2c_d0 = metrics;
globalThis.__probe_metrics = metrics;

const saves = [];
globalThis.__e2c_d0_save_count = () => saves.length;
globalThis.__e2c_d0_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const record = (id, value) => { metrics.cells[id] = value; log({ cell: id, ...value }); };

const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: String(error?.message || error).slice(0, 300),
  formatBarrier: error?.details?.formatBarrier ?? null,
});

async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}

async function snapshot(handle, label) {
  const bytes = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
  saves.push({ label, b64: await toBase64(bytes) });
  return bytes.byteLength;
}

// Wrap the engine's request path so the exact envelope of every dispatch is on
// the record.  "A request went out" is not the claim being checked -- a wrong
// `enabled` is a bold button that unbolds, and it would look identical.
function recordingEngine(engine) {
  const sent = [];
  const original = engine._request.bind(engine);
  engine._request = (operation, payload, options) => {
    sent.push({ operation, payload: { ...payload } });
    return original(operation, payload, options);
  };
  return sent;
}

const FORMAT_ACTIONS = new Set(["set-bold", "set-italic", "set-underline",
  "set-strikethrough"]);

/** Click, then wait for the engine to confirm a collapsed caret. */
async function placeCaret(handle, client, xTwips, yTwips) {
  await handle.click(xTwips, yTwips, { timeoutMs: 30000 });
  const deadline = Date.now() + 30000;
  do {
    const state = await client.getState({ timeoutMs: 30000 });
    if (state.selectionType === "none" && state.selection?.observed === true
        && state.selection?.collapsed === true)
      return state;
    await new Promise((resolve) => setTimeout(resolve, 20));
  } while (Date.now() < deadline);
  throw Object.assign(new Error("no callback-confirmed collapsed caret"),
                      { code: "EDITOR_STATE_UNAVAILABLE" });
}

void (async () => {
  let engine = null;
  let handle = null;
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    const manifest = engine.manifest || {};
    const contract = manifest.editorContract || {};
    const declared = Object.keys(contract.actions || {});

    record("d0-inventory", {
      profile: manifest.profile,
      capabilities: manifest.capabilities,
      contractVersion: contract.version,
      abiVersion: contract.abiVersion,
      crossParagraphDisposition: contract.crossParagraphDisposition,
      declaredActions: declared,
      wasmSha256: contract.wasmSha256,
      loaderSha256: contract.loaderSha256,
      workerSha256: contract.workerSha256,
      coreCommit: manifest.coreCommit,
      userAgent: navigator.userAgent,
      crossOriginIsolated: globalThis.crossOriginIsolated,
    });

    // The diagnostic surface, asked of the profile rather than assumed from
    // its name.  editorActionV1 must be refused by the capability gate: this
    // profile declares narrow-editor-v2 and nothing else.
    const bytes = await fetch(`./e1-fixtures/${fixture}`, { cache: "no-cache" })
      .then((response) => response.arrayBuffer());
    handle = await engine.open(bytes.slice(0), { name: fixture, timeoutMs: 180000 });
    const sent = recordingEngine(engine);
    const client = new NarrowEditorV2Client(handle);

    let v1 = null;
    try {
      await engine._request("editorActionV1", {
        documentHandle: handle.handle, expectedRevision: handle.revision,
        action: "set-bold", extendSelection: false, enabled: true,
      }, { timeoutMs: 30000 });
      v1 = { refused: false };
    } catch (error) {
      v1 = { refused: true, error: publicError(error) };
    }
    record("d0-no-diagnostic-surface", {
      capabilities: manifest.capabilities,
      diagnosticCapabilities: (manifest.capabilities || [])
        .filter((name) => /discovery|diagnostic/.test(name)),
      editorActionV1: v1,
    });

    // ---- reachability, one client, every declared action --------------------
    const anchorTwips = { xTwips: 2200, yTwips: 1600 };
    const reach = [];
    for (const action of declared) {
      const before = sent.length;
      const entry = { action, dispatched: false, envelope: null,
                      result: null, error: null };
      try {
        await placeCaret(handle, client, anchorTwips.xTwips, anchorTwips.yTwips);
        const options = FORMAT_ACTIONS.has(action) ? { enabled: true } : {};
        const result = await client.action(action, options);
        entry.result = {
          action: result.action,
          beforeRevision: result.beforeRevision,
          revision: result.revision,
          changed: result.changed ?? null,
          completion: result.completion,
        };
      } catch (error) {
        entry.error = publicError(error);
      }
      const dispatches = sent.slice(before)
        .filter((item) => item.operation === "editorActionV2");
      entry.dispatched = dispatches.length === 1;
      entry.envelope = dispatches[0] || null;
      reach.push(entry);
    }
    record("d0-reachability-single-client", {
      client: "editor-shell-v2/narrow-editor-v2-client.js",
      declared,
      attempts: reach,
    });

    // The controls.  Without them a client that let everything through and a
    // client that satisfied the contract look the same.
    // Counted on editorActionV2 only.  The first version counted every
    // request, and the snapshot saves in between made an action that dispatched
    // nothing report two -- a number that measures something other than what it
    // claims is worse than no number.
    const dispatchCount = () =>
      sent.filter((item) => item.operation === "editorActionV2").length;
    const undeclaredBefore = dispatchCount();
    let undeclared = null;
    try {
      await client.action("set-superscript");
      undeclared = { refused: false };
    } catch (error) {
      undeclared = { refused: true, error: publicError(error) };
    }
    record("d0-reachability-control-undeclared", {
      action: "set-superscript",
      ...undeclared,
      actionsDispatched: dispatchCount() - undeclaredBefore,
    });

    const unknownBefore = dispatchCount();
    let unknown = null;
    const bodyBeforeUnknown = await snapshot(handle, "before-unknown-action");
    try {
      await client.action("set-blink");
      unknown = { refused: false };
    } catch (error) {
      unknown = { refused: true, error: publicError(error) };
    }
    const bodyAfterUnknown = await snapshot(handle, "after-unknown-action");
    record("d0-unknown-action", {
      action: "set-blink",
      ...unknown,
      actionsDispatched: dispatchCount() - unknownBefore,
      savedBytes: { before: bodyBeforeUnknown, after: bodyAfterUnknown },
      zeroMutationBy: "saved document comparison",
    });

    // ---- forbidden fields, below the client --------------------------------
    for (const field of ["keyCode", "unoCommand", "command"]) {
      const before = await snapshot(handle, `before-forbidden-${field}`);
      let outcome = null;
      try {
        await engine._request("editorActionV2", {
          documentHandle: handle.handle,
          expectedRevision: handle.revision,
          action: "set-list-unordered",
          extendSelection: false,
          enabled: false,
          [field]: field === "keyCode" ? 42 : ".uno:DefaultBullet",
        }, { timeoutMs: 30000 });
        outcome = { refused: false };
      } catch (error) {
        outcome = { refused: true, error: publicError(error) };
      }
      const after = await snapshot(handle, `after-forbidden-${field}`);
      record(`d0-forbidden-${field.toLowerCase()}`, {
        field, ...outcome,
        savedBytes: { before, after },
        zeroMutationBy: "saved document comparison",
      });
    }

    await handle.close({ timeoutMs: 30000 });
    handle = null;
    engine.dispose();
    engine = null;

    // ---- the product session, on the profile it is for ---------------------
    // A separate engine on purpose: this cell is about open() succeeding from
    // nothing, which is the thing the shipped EditorSession cannot do here.
    let session = null;
    try {
      session = new NarrowEditorV2Session({
        engineFactory: () => createDocumentEngine({
          workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
        }),
        secureContext: globalThis.isSecureContext,
        clipboard: navigator.clipboard,
      });
      await session.open({ bytes: bytes.slice(0), name: fixture });
      record("d0-session-opens", {
        session: "editor-shell-v2/narrow-editor-v2-session.js",
        state: session.state.snapshot.state,
        clientReplacements: session.clientReplacements,
        generation: session.state.snapshot.generation,
      });
    } catch (error) {
      record("d0-session-opens", {
        session: "editor-shell-v2/narrow-editor-v2-session.js",
        state: session?.state?.snapshot?.state ?? null,
        error: publicError(error),
      });
    } finally {
      try { await session?.close(); } catch { /* a dead session must not block */ }
    }

    metrics.complete = true;
    log({ complete: true, cells: Object.keys(metrics.cells).length,
          saves: saves.length });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  } finally {
    try { await handle?.close({ timeoutMs: 30000 }); } catch { /* closing down */ }
    try { engine?.dispose(); } catch { /* closing down */ }
  }
})();
