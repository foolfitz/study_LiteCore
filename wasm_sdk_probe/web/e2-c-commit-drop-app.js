// The Firefox operator round committed four IME sequences and the document
// advanced ONE revision, with one of the four texts in the saved file.  Before
// calling that a dropped commit, drive the same shell call directly and count.
//
// Not the IME: this is `session.commitText`, the call an IME commit reaches
// after the input adapter is done with it.  If commits are lost here, the loss
// is below the IME.
import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";
import { placeCaretVerified } from "./e2-c-caret.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const gapMs = Number(params.get("gap") || 0);
const FIXTURE = { dir: "e1-fixtures", name: "list-contexts.odt" };
const ANCHOR = "E1-LC-SPACER";
const metrics = { schemaVersion: 1, release: "d5-commit-drop", profile, gapMs,
                  browser: navigator.userAgent, commits: [], complete: false, error: null };
globalThis.__commit_drop = metrics;
globalThis.__probe_metrics = metrics;
const saves = [];
globalThis.__commit_drop_save_count = () => saves.length;
globalThis.__commit_drop_save = (i) => saves[i] || null;
const log = (v) => { document.querySelector("#log").textContent += JSON.stringify(v) + "\n"; };
async function b64(bytes) { let s = ""; const v = new Uint8Array(bytes);
  for (let i = 0; i < v.length; i += 0x8000) s += String.fromCharCode(...v.subarray(i, i + 0x8000));
  return btoa(s); }

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
    const r = (found.selections?.[0]?.rectangles || "").split(";")[0].split(",").map(Number);
    await placeCaretVerified(session, r[0] + Math.floor(r[2] / 2), r[1] + Math.floor(r[3] / 2),
                             { caretTimeoutMs: 30000, anchorRect: { x: r[0], y: r[1], width: r[2], height: r[3] } });
    for (const [index, text] of ["AA", "BB", "CC", "DD"].entries()) {
      const before = session.state?.snapshot?.revision ?? session.document?.revision ?? null;
      const started = performance.now();
      const outcome = await session.commitText(text)
        .then(() => "ok", (e) => ({ code: e?.code, message: String(e?.message).slice(0, 120) }));
      const after = session.state?.snapshot?.revision ?? session.document?.revision ?? null;
      metrics.commits.push({ index, text, before, after, outcome,
                             ms: Math.round(performance.now() - started),
                             advanced: before !== after });
      log(metrics.commits.at(-1));
      if (gapMs) await new Promise((r2) => setTimeout(r2, gapMs));
    }
    const { bytes: saved } = await session.save({ timeoutMs: 180000 });
    saves.push({ label: "after-four-commits.odt", b64: await b64(saved) });
    metrics.savedBytes = saved.byteLength;
    metrics.complete = true;
  } catch (error) {
    metrics.error = { code: error?.code || "ERROR", message: String(error?.message || error).slice(0, 200) };
    metrics.complete = true; log({ fatal: metrics.error });
  } finally { await session?.close().catch(() => {}); }
})();
