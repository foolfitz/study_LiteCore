// D5 cell 3 asked the operator to "select a range, then type -- it should
// replace".  The operator reported it does not.  This measures it through the
// PRODUCT's own path: the shell's commit, the same one an IME commit reaches.
//
// Not a substitute for the operator round: this drives commitText directly,
// so it tests the commit semantics, not the IME.  That is exactly the half in
// question -- whether a commit over a selection replaces or inserts.
import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const FIXTURE = { dir: "e1-fixtures", name: "list-contexts.odt" };
const ANCHOR = "E1-LC-ISOLATED";
const metrics = { schemaVersion: 1, release: "d5-cell3-commit-semantics",
                  profile, browser: navigator.userAgent, steps: {},
                  complete: false, error: null };
globalThis.__ime_replace = metrics;
// The saved document goes back through the runner's extraction pair: searching
// a ZIP container for a plain string finds nothing whatever the content is,
// which is a check that always agrees with itself.
const saves = [];
globalThis.__ime_replace_save_count = () => saves.length;
globalThis.__ime_replace_save = (index) => saves[index] || null;
async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}
globalThis.__probe_metrics = metrics;
const log = (v) => { document.querySelector("#log").textContent += JSON.stringify(v) + "\n"; };

void (async () => {
  let session = null;
  try {
    session = new NarrowEditorV2Session({
      engineFactory: () => createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000 }),
      secureContext: globalThis.isSecureContext, clipboard: navigator.clipboard });
    const bytes = await (await fetch(`./${FIXTURE.dir}/${FIXTURE.name}`)).arrayBuffer();
    await session.open({ bytes: bytes.slice(0), name: FIXTURE.name, timeoutMs: 180000 });
    session.attachInput(document.querySelector("#sink"));
    const found = await session.document.search(ANCHOR, { timeoutMs: 30000 });
    const r = (found.selections?.[0]?.rectangles || "").split(";")[0]
      .split(",").map((v) => parseInt(v, 10));
    metrics.steps.anchorRect = r;
    const y = r[1] + Math.floor(r[3] / 2);
    // Select the anchor's own line, start to end -- a real range.
    await session.selectRange({ xTwips: r[0], yTwips: y },
                              { xTwips: r[0] + r[2], yTwips: y },
                              { timeoutMs: 30000 });
    const before = await session.document.getSelection({ timeoutMs: 30000 });
    metrics.steps.selectedText = (before.text || "").slice(0, 80);
    metrics.steps.selectedLength = (before.text || "").length;
    // The product's commit -- the same call an IME commit reaches.
    await session.commitText("ZZTESTZZ");
    const after = await session.document.getSelection({ timeoutMs: 30000 });
    metrics.steps.selectionAfter = (after.text || "").slice(0, 80);
    const { bytes: saved } = await session.save({ timeoutMs: 180000 });
    metrics.steps.savedBytes = saved.byteLength;
    saves.push({ label: "after-commit-over-selection.odt",
                 b64: await toBase64(saved) });
    log(metrics.steps);
    metrics.complete = true;
  } catch (error) {
    metrics.error = { code: error?.code || "ERROR", message: String(error?.message || error).slice(0, 300) };
    metrics.complete = true;
    log({ fatal: metrics.error });
  } finally { await session?.close().catch(() => {}); }
})();
