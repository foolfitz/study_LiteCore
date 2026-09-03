// The decisive measurement of the ODS milestone, §5 of
// `handoff/PLAN-2026-09-03-ods-reading.md`.
//
// ONE QUESTION: does the a11y+calc core, as linked into the cutover candidate,
// actually load and render a spreadsheet through LOK -- services, static
// constructor map, type detection, headless Calc view, the `view-ready`
// handshake, and `setAccessibilityState` at open, all at once?
//
// This page is written ONLY into a scratch mirror of `dist/`. Nothing under
// `dist/`, `web/` or `sdk/` is touched by a run, because the v12 cutover gate
// is mid-soak and a change to any of the thirteen bundle paths refuses every
// run after it.
//
// THE NAME IS SPOOFED, AND THAT IS DECLARED. `oxsdk_document_open` rejects any
// name not ending `.odt` before the engine queue (finding 013), while content
// detection then reads the zip's own `mimetype`. So the bytes are handed over
// as `<stem>.odt`. Every report carries `nameSpoofed: true` and is diagnostic
// evidence only -- it can never be quoted as the product opening an ODS,
// because the product refuses to.
//
// The controls are half the measurement:
//   * an ODT through the same path   -- if IT fails, the instrument is broken,
//                                       not the core.
//   * an empty one-sheet ODS         -- its tile is what "painted nothing"
//                                       looks like, so a blank canvas cannot
//                                       read as success.
//   * a truncated ODS                -- a typed refusal with the worker still
//                                       alive; without it, "did not open" and
//                                       "died" look the same.
import { createDocumentEngine } from "./sdk/document-sdk.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v12";
const NS = "__odsProbe";

const report = {
  schemaVersion: 1,
  release: "m4-ods-decisive",
  profile,
  nameSpoofed: true,
  evidenceClass: "diagnostic",
  why: "finding 013: the public open() rejects by extension before content "
       + "detection, so an ODS cannot be handed to the product path at all. "
       + "This bypasses the check by name only; the bytes are unmodified and "
       + "content detection reads the zip mimetype.",
  cases: [],
  done: false,
};
window[NS] = report;

function errorValue(error) {
  if (!error) return null;
  return {
    name: error.name || null,
    code: error.code || null,
    message: String(error.message || error),
  };
}

async function sha256Hex(bytes) {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0")).join("");
}

// A tile, and two numbers about it: its hash, and how many pixels are not the
// paper colour. The hash alone cannot tell two blank tiles apart from two
// identical drawn ones, and the count alone cannot tell two different drawings
// apart. Both, or neither answers G4.
// `render`, not `paintTile`, and part 0 only.
//
// CHECKED BEFORE THE FIRST RUN rather than after it: `DocumentHandle` has no
// `setPart` and no `paintTile` -- its painting call is `render(region, options)`
// and there is no part-switching call at all. That is not a surprise, it is the
// plan's W7: `set_part`/`part_name` need engine exports and a relink. So this
// probe paints part 0 and reads the SHEET COUNT from `handle.parts`, which the
// open reply already carries. The count is the discriminator; switching parts
// is the next milestone's measurement, not this one's.
async function paintFirstPart(handle, entry) {
  const px = 1024;
  try {
    const result = await handle.render({
      xTwips: 0, yTwips: 0, widthTwips: 15360, heightTwips: 15360,
      canvasWidthPx: px, canvasHeightPx: px,
    }, { timeoutMs: 120000 });
    const raw = result?.bytes ?? result?.pixels ?? result?.data ?? null;
    if (raw == null) {
      entry.tile = { ok: false, reason: "render returned no pixel field",
                     keys: Object.keys(result || {}) };
      return;
    }
    const view = raw instanceof Uint8Array
      ? raw : new Uint8Array(raw.buffer || raw);
    // BOTH numbers, and neither alone. A hash cannot tell two blank tiles from
    // two identical drawn ones; a count cannot tell two different drawings
    // apart.
    let nonPaper = 0;
    for (let i = 0; i + 3 < view.length; i += 4) {
      if (view[i] !== 255 || view[i + 1] !== 255 || view[i + 2] !== 255)
        nonPaper += 1;
    }
    entry.tile = {
      ok: true, bytes: view.length, nonPaperPixels: nonPaper,
      sha256: await sha256Hex(view),
      documentWidthTwips: result?.documentWidthTwips ?? null,
      documentHeightTwips: result?.documentHeightTwips ?? null,
    };
  } catch (error) {
    entry.tile = { ok: false, error: errorValue(error) };
  }
}

async function runCase(spec) {
  const entry = {
    name: spec.name, file: spec.file, kind: spec.kind,
    handedOverAs: spec.file.replace(/\.[^.]+$/, "") + ".odt",
    stages: [], opened: null, viewReady: null, error: null,
  };
  report.cases.push(entry);
  let engine = null;
  let handle = null;
  const started = performance.now();
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`,
      debug: true, timeoutMs: 60000,
    });
    report.manifest ||= engine.manifest;
    engine.onEvent((event) => {
      // EVERY stage line, not a summary: they carry `sbrk`, and the whole
      // memory question of the milestone is read from them. A summary here is
      // a number nobody can re-derive.
      if (event?.event === "diagnostic" || event?.stage)
        entry.stages.push(event);
      if (String(event?.event || "").includes("view-ready"))
        entry.viewReady = { atMs: Math.round(performance.now() - started) };
      if (String(event?.event || "") === "worker-crashed")
        entry.workerCrashed = true;
    });

    const response = await fetch(spec.file);
    if (!response.ok) throw new Error(`fetch ${spec.file}: ${response.status}`);
    const bytes = await response.arrayBuffer();
    entry.inputBytes = bytes.byteLength;
    entry.inputSha256 = await sha256Hex(new Uint8Array(bytes));

    handle = await engine.open(bytes.slice(0), {
      name: entry.handedOverAs, transfer: true, timeoutMs: 180000,
    });
    entry.opened = {
      atMs: Math.round(performance.now() - started),
      parts: handle?.parts ?? null,
      tileMode: handle?.tileMode ?? null,
      // THE DISCRIMINATOR, and it is readable today: `DocumentHandle` already
      // carries `parts`, `widthTwips`, `heightTwips` and `tileMode` from the
      // open reply. A Writer document reports its page count; a spreadsheet
      // reports its sheet count. The three-sheet fixture is one page's worth of
      // nothing as a Writer document, so `parts == 3` is the single number that
      // says Calc answered.
      partsFromHandle: handle?.parts ?? null,
      widthTwips: handle?.widthTwips ?? null,
      heightTwips: handle?.heightTwips ?? null,
    };

    if (spec.paint !== false)
      await paintFirstPart(handle, entry);
  } catch (error) {
    entry.error = errorValue(error);
  } finally {
    entry.elapsedMs = Math.round(performance.now() - started);
    try { if (handle) await handle.close({ timeoutMs: 30000 }); } catch (e) {}
    try { if (engine) await engine.dispose(); } catch (e) {}
  }
}

(async () => {
  // THE CASE LIST COMES FROM A FILE, not the query string. A sweep over three
  // hundred fixtures does not fit in a URL, and a list silently truncated by a
  // URL limit would report a clean sweep over whatever survived -- a census
  // that measured a prefix and said nothing.
  let specs = [];
  try {
    const inline = params.get("cases");
    if (inline) {
      specs = JSON.parse(inline);
    } else {
      const response = await fetch("./ods-cases.json");
      if (!response.ok) throw new Error(`cases.json: ${response.status}`);
      specs = await response.json();
    }
  } catch (error) {
    report.fatal = errorValue(error);
    report.done = true;
    return;
  }
  report.caseCount = specs.length;
  for (const spec of specs) {
    try { await runCase(spec); }
    catch (error) { report.cases.push({ name: spec.name, fatal: errorValue(error) }); }
  }
  report.done = true;
})();
