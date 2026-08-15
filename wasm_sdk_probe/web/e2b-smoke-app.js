// E2-B: does the v2 stack actually come up?
//
// Deliberately not a measurement and deliberately not a judge.  Everything it
// touches is wiring -- the capability gate, the editor ABI comparison, the
// 11-15 action mapping, the gesture mask push, the relaxed result validation --
// and wiring should fail here, not in the first cell of a 90-run matrix.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { ParagraphEditorClient, EDITOR_V2_PARAGRAPH_ACTIONS }
  from "./editor-shell-v2/paragraph-editor-client.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const fixture = params.get("fixture") || "list-contexts.odt";

const metrics = {
  schemaVersion: 1,
  release: "spec-e2b-v2-smoke",
  profile,
  fixture,
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  steps: [],
  complete: false,
  error: null,
};
globalThis.__e2b_smoke = metrics;
globalThis.__probe_metrics = metrics;

const logNode = document.querySelector("#log");
const log = (value) => {
  metrics.steps.push(value);
  logNode.textContent += `${JSON.stringify(value)}\n`;
};

const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: error?.message || String(error),
  details: error?.details ?? null,
});

void (async () => {
  let engine = null;
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    const manifest = engine.manifest || {};
    const contract = manifest.editorContract || {};
    log({
      step: "engine-up",
      profile: manifest.profile,
      capabilities: manifest.capabilities,
      contractVersion: contract.version,
      abiVersion: contract.abiVersion,
      actionCount: contract.actions ? Object.keys(contract.actions).length : null,
      crossParagraphDisposition: contract.crossParagraphDisposition,
      wasmSha256: (contract.wasmSha256 || "").slice(0, 16),
    });

    const bytes = await fetch(`./e1-fixtures/${fixture}`, { cache: "no-cache" })
      .then((response) => response.arrayBuffer());
    const handle = await engine.open(bytes.slice(0), {
      name: fixture, timeoutMs: 180000,
    });
    log({ step: "opened", revision: handle.revision });

    const client = new ParagraphEditorClient(handle);
    log({
      step: "manifest-read-through-client",
      gestures: client.gesturesFor("set-list-unordered"),
      headingLimits: client.limitsFor("set-paragraph-heading"),
    });

    // One collapsed-caret dispatch.  Collapsed on purpose: it is the gesture
    // every existing E2-A verdict already covers, so a failure here is the new
    // wiring and nothing else.
    for (const action of EDITOR_V2_PARAGRAPH_ACTIONS) {
      const before = handle.revision;
      try {
        const result = await client.action(action, { timeoutMs: 30000 });
        log({
          step: "dispatched", action, ok: true,
          beforeRevision: before, revision: result.revision,
          changed: result.changed, completion: result.completion,
          route: result.formatBarrier?.route ?? null,
          preBlocks: result.formatBarrier?.preBlocks ?? null,
        });
      } catch (error) {
        log({ step: "dispatched", action, ok: false, error: publicError(error) });
      }
    }

    const saved = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
    log({ step: "saved", bytes: saved.byteLength });
    await handle.close({ timeoutMs: 15000 }).catch(() => {});
  } catch (error) {
    metrics.error = publicError(error);
    log({ fatal: metrics.error });
  } finally {
    engine?.dispose();
    metrics.complete = true;
    log({ complete: true });
  }
})();
