// SPEC E2-C, phase D5: the manual round, and the machine half that proves the
// harness can reject a fake gesture.
//
// D5's whole subject is `isTrusted`, so the product page has to be the thing the
// operator touches.  It is also one of the twelve modules the E2-C shell bundle
// binds -- editing it to add a recorder would change the digest every other
// phase is filed under.  So the product page is hosted UNMODIFIED in a
// same-origin iframe and observed from outside.
//
// Three observation points, all runtime, none of them an edit to a file:
//   * capture-phase listeners on the iframe document, recording isTrusted;
//   * a declared shim on the iframe's URL.createObjectURL, because the product
//     saves by handing a Blob to a download link and nothing outside can read a
//     download;
//   * the product's own status strip, read from the iframe DOM.
//
// Criteria: findings/evidence/sdk-e2/e2-c-validation/d5/PREDICTION.md

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const machineHalf = params.get("machine") === "half";

const CELLS = [
  { id: "d5-pointer-drag-single",
    instruction: "用滑鼠在**同一段**文字上拖曳選取，放開，然後按工具列的「項目符號」。" },
  { id: "d5-pointer-drag-cross",
    instruction: "用滑鼠**跨兩段**拖曳選取，放開，然後按「項目符號」。" },
  { id: "d5-ime-commit",
    instruction: "用 Fcitx5 新酷音在游標處輸入一次中文並確定；再選取一段文字後輸入一次取代它。" },
  { id: "d5-clipboard",
    instruction: "用真的 Ctrl+C 複製一段文字，把游標移到別處，用真的 Ctrl+V 貼上。" },
];

const metrics = {
  schemaVersion: 1,
  release: "spec-e2c-d5",
  phase: "D5",
  profile,
  browser: navigator.userAgent,
  mode: machineHalf ? "machine-half" : "operator",
  // Declared, not discovered.  A harness that patches something in the page it
  // observes says so where the evidence can see it.
  shims: ["URL.createObjectURL"],
  cells: {},
  events: [],
  saves: [],
  complete: false,
  error: null,
};
globalThis.__e2c_d5 = metrics;
// The runners' load condition, same as every other E2-C page.
globalThis.__probe_metrics = metrics;

const saves = [];
globalThis.__e2c_d5_save_count = () => saves.length;
globalThis.__e2c_d5_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };

let current = null;   // the cell being recorded, or null

function record(type, event, extra = {}) {
  const entry = {
    cell: current,
    type,
    // The only property this phase exists to establish.  Recorded for every
    // event, including the ones nobody asked for, so a cell cannot be backed by
    // a mixture nobody looked at.
    isTrusted: event?.isTrusted === true,
    atMs: Math.round(performance.now()),
    ...extra,
  };
  metrics.events.push(entry);
  if (metrics.events.length % 25 === 0) log({ events: metrics.events.length });
  return entry;
}

async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}

function attach(frameWindow) {
  const doc = frameWindow.document;
  const point = (event) => ({ x: event.clientX, y: event.clientY });

  for (const type of ["pointerdown", "pointermove", "pointerup"])
    doc.addEventListener(type, (event) => {
      // Moves are sampled: a drag produces hundreds and the question is whether
      // any moves happened at all, not their exact number.
      if (type === "pointermove" && metrics.events.length
          && metrics.events.at(-1)?.type === "pointermove"
          && metrics.events.at(-1)?.cell === current
          && Math.round(performance.now()) - metrics.events.at(-1).atMs < 40)
        return;
      record(type, event, point(event));
    }, true);

  for (const type of ["keydown", "copy", "paste"])
    doc.addEventListener(type, (event) => record(type, event, {
      key: event.key ?? null, ctrlKey: event.ctrlKey ?? null,
    }), true);

  for (const type of ["compositionstart", "compositionupdate", "compositionend"])
    doc.addEventListener(type, (event) => record(type, event, {
      data: typeof event.data === "string" ? event.data.slice(0, 40) : null,
    }), true);

  // The save interception.  Declared in `metrics.shims`.
  const nativeCreate = frameWindow.URL.createObjectURL.bind(frameWindow.URL);
  frameWindow.URL.createObjectURL = (blob) => {
    const url = nativeCreate(blob);
    void (async () => {
      try {
        const bytes = await blob.arrayBuffer();
        const label = `${current || "unassigned"}-${saves.length + 1}`;
        saves.push({ label, b64: await toBase64(bytes) });
        metrics.saves.push({ label, bytes: bytes.byteLength, cell: current });
        log({ saved: label, bytes: bytes.byteLength });
      } catch (error) {
        metrics.error = { code: "SAVE_CAPTURE_FAILED", message: String(error) };
      }
    })();
    return url;
  };

  // The product's own status strip, read rather than inferred.
  const strip = () => ({
    state: doc.querySelector("#s-state")?.textContent ?? null,
    revision: doc.querySelector("#s-revision")?.textContent ?? null,
    generation: doc.querySelector("#s-generation")?.textContent ?? null,
  });
  return strip;
}

function beginCell(id, strip) {
  current = id;
  metrics.cells[id] = {
    cell: id,
    startedAtMs: Math.round(performance.now()),
    stripBefore: strip(),
    eventIndex: metrics.events.length,
  };
  log({ began: id });
}

function endCell(id, strip) {
  const cell = metrics.cells[id];
  if (!cell) return;
  cell.endedAtMs = Math.round(performance.now());
  cell.stripAfter = strip();
  cell.events = metrics.events.slice(cell.eventIndex)
    .filter((entry) => entry.cell === id);
  cell.trustedEvents = cell.events.filter((entry) => entry.isTrusted).length;
  cell.syntheticEvents = cell.events.filter((entry) => !entry.isTrusted).length;
  current = null;
  log({ ended: id, events: cell.events.length,
        synthetic: cell.syntheticEvents });
}

void (async () => {
  const frame = document.querySelector("#product");
  frame.src = `./e2-editor.html?profile=${encodeURIComponent(profile)}`;
  await new Promise((resolve) => frame.addEventListener("load", resolve,
                                                        { once: true }));
  const strip = attach(frame.contentWindow);
  metrics.productUrl = frame.contentWindow.location.pathname;

  // The operator UI: one button per cell, begin and end.
  const panel = document.querySelector("#cells");
  for (const cell of CELLS) {
    const row = document.createElement("div");
    row.className = "cell";
    row.innerHTML = `<b>${cell.id}</b><p>${cell.instruction}</p>`;
    const begin = document.createElement("button");
    begin.textContent = "開始這一格";
    const end = document.createElement("button");
    end.textContent = "這一格做完了";
    end.disabled = true;
    begin.addEventListener("click", () => {
      beginCell(cell.id, strip);
      begin.disabled = true; end.disabled = false;
    });
    end.addEventListener("click", () => {
      endCell(cell.id, strip);
      end.disabled = true;
    });
    row.append(begin, end);
    panel.append(row);
  }

  const finish = document.createElement("button");
  finish.textContent = "全部做完，送出證據";
  finish.addEventListener("click", () => { metrics.complete = true;
                                           log({ complete: true }); });
  panel.append(finish);

  // The operator drives a real browser window, not a WebDriver session, so
  // nothing can reach in and read `globalThis.__e2c_d5` afterwards.  Without
  // this button the round ends with "now open the console and copy a variable",
  // which is a step that gets done wrong at 1am or not at all.
  //
  // One file, everything in it: the metrics and every captured document, so the
  // hand-back is a single path rather than a folder the operator has to
  // assemble.  Added 2026-08-16, after the machine half was recorded; it
  // touches no measurement path.
  // Exposed as well as wired to the button, so the export can be checked
  // without a human and without a download: a button nobody can test is a
  // button that fails on the night it is needed.
  globalThis.__e2c_d5_export_payload = () => ({ ...metrics,
                                                capturedSaves: saves });

  const download = document.createElement("button");
  download.textContent = "把證據存成一個檔案";
  download.addEventListener("click", () => {
    const payload = globalThis.__e2c_d5_export_payload();
    const blob = new Blob([JSON.stringify(payload)],
                          { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `e2c-d5-operator-${metrics.mode}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    log({ exported: link.download, cells: Object.keys(metrics.cells).length,
          saves: saves.length });
  });
  panel.append(download);

  globalThis.__e2c_d5_begin = (id) => beginCell(id, strip);
  globalThis.__e2c_d5_end = (id) => endCell(id, strip);
  globalThis.__e2c_d5_finish = () => { metrics.complete = true; };
  globalThis.__e2c_d5_frame = () => frame.contentWindow;
  metrics.ready = true;
  log({ ready: true, mode: metrics.mode });
})();
