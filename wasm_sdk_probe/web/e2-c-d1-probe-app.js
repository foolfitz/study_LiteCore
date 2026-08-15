// SPEC E2-C D1 pre-flight: is an inline format at a collapsed caret visible in
// the saved document at all?
//
// The question is not academic.  Codex's review demanded that D1 judge each
// inline format against its own anchor in the saved ODT, because all four
// return the same completion and a mapping error would report the action asked
// for.  That is right -- but `.uno:Bold` at a COLLAPSED caret conventionally
// sets the typing attribute rather than changing any existing text, and the
// manifest declares `collapsed` for the ten.  If the document does not change,
// then "this anchor became bold" is a criterion no run can ever satisfy, and
// writing it into the frozen matrix would freeze four cells that must fail.
//
// So: measure first.  Four observations per format, saved as documents for an
// offline judge:
//
//   before        the fixture as opened, caret placed, nothing dispatched
//   after-action  the format dispatched at the collapsed caret
//   after-insert  text committed at that caret afterwards
//   after-range   the format dispatched on a RANGE covering the anchor
//
// The last one is characterisation only (SPEC E2-C 2.5): the contract declares
// collapsed for these ten and this round does not change that.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Client } from "./editor-shell-v2/narrow-editor-v2-client.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const fixture = params.get("fixture") || "d1-anchors.odt";

const metrics = {
  schemaVersion: 1,
  release: "spec-e2c-d1-preflight",
  phase: "D1-preflight",
  profile,
  fixture,
  browser: navigator.userAgent,
  cells: {},
  anchors: {},
  complete: false,
  error: null,
};
globalThis.__e2c_d1_probe = metrics;
globalThis.__probe_metrics = metrics;

const saves = [];
globalThis.__e2c_d1_probe_save_count = () => saves.length;
globalThis.__e2c_d1_probe_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: String(error?.message || error).slice(0, 300),
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

const FIXTURE_DIR = "./e2-fixtures";

async function openFixture(engine) {
  const bytes = await fetch(`${FIXTURE_DIR}/${fixture}`, { cache: "no-cache" })
    .then((response) => response.arrayBuffer());
  return engine.open(bytes.slice(0), { name: fixture, timeoutMs: 180000 });
}

/** Sweep for an anchor by reading the selection back at each step. */
async function findAnchor(handle, client, anchor) {
  const hits = [];
  for (let y = 1300; y <= 12000; y += 130) {
    try {
      await client.selectRange({ xTwips: 1450, yTwips: y },
                               { xTwips: 9000, yTwips: y },
                               { timeoutMs: 30000 });
      const selection = await handle.getSelection({ timeoutMs: 30000 });
      if ((selection.text || "").includes(anchor)) hits.push(y);
    } catch { /* a step that cannot select tells us nothing; keep sweeping */ }
  }
  return hits;
}

// Surveyed in a THROWAWAY document, never in the one being measured.  The sweep
// selects, and a selection made by the setup is exactly the state the
// measurement is about; the gate learned this the hard way and the E2-B matrix
// carries the same note.
async function survey(anchors) {
  const engine = await createDocumentEngine({
    workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
  });
  const handle = await openFixture(engine);
  const client = new NarrowEditorV2Client(handle);
  const found = {};
  for (const anchor of anchors) {
    const hits = await findAnchor(handle, client, anchor);
    found[anchor] = { first: hits[0] ?? null, last: hits[hits.length - 1] ?? null,
                      steps: hits.length };
  }
  await handle.close({ timeoutMs: 30000 }).catch(() => {});
  engine.dispose();
  return found;
}

// Why does `set-paragraph-body` get refused before dispatch at one anchor while
// five other collapsed cells pass?  D1 saw it six times out of six, both
// browsers, shape `routing-selection-not-readable` -- the finding 037 type guard
// firing on a selection whose type is not TEXT.  The pair below asks the engine
// directly, at an anchor that fails and at one that passes, and reads the
// selection type BEFORE dispatching anything.
const TYPE_CASES = [
  { name: "body-target-alone", anchor: "E2-D1-BODY-TARGET",
    action: "set-paragraph-body" },
  { name: "head-target-alone", anchor: "E2-D1-HEAD-TARGET",
    action: "set-paragraph-heading" },
  // The D1 sequence: a paragraph action at ANOTHER anchor immediately before.
  // If the refusal follows the sequence rather than the anchor, this
  // reproduces it and the isolated case above does not -- which is the whole
  // difference between "this anchor is special" and "the previous action left
  // something behind" (findings 043 and 049 territory).
  { name: "head-then-body", anchor: "E2-D1-BODY-TARGET",
    action: "set-paragraph-body",
    precursor: { anchor: "E2-D1-HEAD-TARGET", action: "set-paragraph-heading" } },
];

const CASES = [
  { format: "set-bold", anchor: "E2-D1-BOLD-ON", marker: "BOLDPROBE" },
  { format: "set-italic", anchor: "E2-D1-ITALIC-ON", marker: "ITALICPROBE" },
];

// The second question, and it came out of D1's first smoke round: after
// `set-bold(enabled: false)` at a caret in PLAIN text, the text typed next came
// out bold.  Three readings fit -- the flag is not transmitted, the engine
// toggles instead of setting, or the typing attribute from an earlier
// `set-bold(true)` survived the caret move.  They are told apart by asking in a
// FRESH document, where no earlier dispatch exists to leak.
const OFF_CASES = [
  { name: "off-in-plain-fresh-document",
    steps: [{ action: "set-bold", enabled: false, marker: "OFFONLY" }] },
  { name: "on-then-off-same-document",
    steps: [{ action: "set-bold", enabled: true, marker: "ONFIRST" },
            { action: "set-bold", enabled: false, marker: "OFFSECOND" }] },
];

void (async () => {
  try {
    // Every piece of evidence names the artifact it ran on, including a
    // pre-flight probe: the runner compares this against the hashes it computed
    // from the profile on disk, and a probe that skipped it would file its
    // result under an artifact nobody checked (finding 027).
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
    metrics.anchors = await survey(CASES.map((item) => item.anchor));
    log({ step: "survey", anchors: metrics.anchors });

    for (const spec of CASES) {
      const span = metrics.anchors[spec.anchor];
      const entry = { anchor: spec.anchor, y: span?.first ?? null, steps: [] };
      if (span?.first == null) {
        entry.error = { code: "ANCHOR_NOT_FOUND" };
        metrics.cells[spec.format] = entry;
        continue;
      }
      // A fresh engine per case: the previous case mutated its document, and a
      // probe that measured the leftovers of the one before would be measuring
      // the order it happened to run in.
      const engine = await createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
      });
      const handle = await openFixture(engine);
      const client = new NarrowEditorV2Client(handle);
      try {
        // Collapsed caret: the same point twice is a range of zero width.
        await client.selectRange({ xTwips: 2000, yTwips: span.first },
                                 { xTwips: 2000, yTwips: span.first },
                                 { timeoutMs: 30000 });
        await snapshot(handle, `${spec.format}-before`);

        const applied = await client.action(spec.format, { enabled: true });
        entry.steps.push({ step: "action", revision: applied.revision,
                           changed: applied.changed,
                           completion: applied.completion });
        await snapshot(handle, `${spec.format}-after-action`);

        const inserted = await handle.insertText(spec.marker, { timeoutMs: 30000 });
        entry.steps.push({ step: "insert", marker: spec.marker,
                           revision: inserted?.revision ?? null });
        await snapshot(handle, `${spec.format}-after-insert`);

        // Characterisation only: a range gesture the manifest does not declare
        // for this action (SPEC E2-C 2.5).
        try {
          await client.selectRange({ xTwips: 1450, yTwips: span.first },
                                   { xTwips: 9000, yTwips: span.first },
                                   { timeoutMs: 30000 });
          const onRange = await client.action(spec.format, { enabled: true });
          entry.steps.push({ step: "range-action", revision: onRange.revision,
                             changed: onRange.changed,
                             completion: onRange.completion });
        } catch (error) {
          entry.steps.push({ step: "range-action", error: publicError(error) });
        }
        await snapshot(handle, `${spec.format}-after-range`);
      } catch (error) {
        entry.error = publicError(error);
      } finally {
        await handle.close({ timeoutMs: 30000 }).catch(() => {});
        engine.dispose();
      }
      metrics.cells[spec.format] = entry;
      log({ cell: spec.format, ...entry });
    }

    for (const spec of OFF_CASES) {
      const span = metrics.anchors["E2-D1-BOLD-ON"];
      const entry = { name: spec.name, y: span?.first ?? null, steps: [] };
      const engine = await createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
      });
      const handle = await openFixture(engine);
      const client = new NarrowEditorV2Client(handle);
      try {
        for (const step of spec.steps) {
          await client.selectRange({ xTwips: 2000, yTwips: span.first },
                                   { xTwips: 2000, yTwips: span.first },
                                   { timeoutMs: 30000 });
          const result = await client.action(step.action,
                                             { enabled: step.enabled });
          await handle.insertText(step.marker, { timeoutMs: 30000 });
          entry.steps.push({ action: step.action, enabled: step.enabled,
                             marker: step.marker, revision: result.revision,
                             changed: result.changed,
                             completion: result.completion });
        }
        await snapshot(handle, `off-${spec.name}`);
      } catch (error) {
        entry.error = publicError(error);
      } finally {
        await handle.close({ timeoutMs: 30000 }).catch(() => {});
        engine.dispose();
      }
      metrics.cells[spec.name] = entry;
      log({ cell: spec.name, ...entry });
    }

    for (const spec of TYPE_CASES) {
      const hits = await (async () => {
        const engine = await createDocumentEngine({
          workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
        });
        const handle = await openFixture(engine);
        const client = new NarrowEditorV2Client(handle);
        const entry = { anchor: spec.anchor, steps: [] };
        try {
          if (spec.precursor) {
            const before = await findAnchor(handle, client, spec.precursor.anchor);
            await client.selectRange({ xTwips: 2000, yTwips: before[0] },
                                     { xTwips: 2000, yTwips: before[0] },
                                     { timeoutMs: 30000 });
            const first = await client.action(spec.precursor.action);
            entry.steps.push({ step: "precursor", action: spec.precursor.action,
                               completion: first.completion });
          }
          const found = await findAnchor(handle, client, spec.anchor);
          entry.y = found[0] ?? null;
          if (entry.y == null) throw new Error("anchor not found");
          await client.selectRange({ xTwips: 2000, yTwips: entry.y },
                                   { xTwips: 2000, yTwips: entry.y },
                                   { timeoutMs: 30000 });
          const selection = await handle.getSelection({ timeoutMs: 30000 });
          const state = await client.getState({ timeoutMs: 30000 });
          entry.steps.push({
            step: "read-before-dispatch",
            selectionType: selection.selectionType,
            selectionText: (selection.text || "").slice(0, 40),
            stateSelectionType: state.selectionType,
            collapsed: state.selection?.collapsed ?? null,
            rectangles: (state.selection?.rectangles || []).length,
          });
          const result = await client.action(spec.action);
          entry.steps.push({ step: "dispatch", ok: true,
                             completion: result.completion });
        } catch (error) {
          entry.steps.push({ step: "dispatch", ok: false,
                             error: publicError(error) });
        } finally {
          await handle.close({ timeoutMs: 30000 }).catch(() => {});
          engine.dispose();
        }
        return entry;
      })();
      metrics.cells[spec.name] = hits;
      log({ cell: spec.name, ...hits });
    }

    metrics.complete = true;
    log({ complete: true, saves: saves.length });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  }
})();
