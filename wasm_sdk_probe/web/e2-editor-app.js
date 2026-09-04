// SPEC E2-C 2.4: the product page for the v2 contract.
//
// It exists because a client and a session are not a product.  Until this file,
// nothing a user could open drove NarrowEditorV2Client, and `demo-structure`
// offered five of the fifteen actions with no drag selection at all -- so D5's
// "select with a real pointer drag, then press a format button" had no product
// path to run on, and measuring it in a harness would have measured the
// harness.
//
// Three things this page is careful about, each of them a rule from evidence
// rather than a preference:
//
//   * Format buttons follow a SELECTION gesture.  SPEC E2-B 5.13 makes a failed
//     dispatch recoverable by rolling back to the checkpoint that
//     `_checkpointBeforeSelection` writes before a range selection.  Press a
//     format button with no gesture in front of it and the rollback reaches
//     further back than the one action.
//
//   * The toolbar never shows what the paragraph currently IS.  Route C does
//     not read the precondition (finding 022), so an "active" button would only
//     report what this page last asked for.  What the buttons DO reflect is the
//     manifest's gesture declaration for the current selection shape, which is
//     a statement about the contract rather than about the document.
//
//   * A dispatched failure is recovered by rolling back, not by undo: undo goes
//     through the queue that the failure has just blocked, so the user would
//     get EDITOR_NOT_READY.  The page offers the rollback explicitly.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session, selectionShapeOf, selectionShapeEvidence }
  from "./editor-shell-v2/narrow-editor-v2-session.js";
// Finding 061: this page used to re-derive the recovery notice from
// `hasCheckpoint` alone, and that two-way branch told a user whose checkpoint
// SAVE FAILED that there had never been one.  The shell decides this already,
// and its own spec revision (SPEC-E1-C 4.1 v8) says the third case exists
// precisely so nobody is left silent about a failed rescue.  Taking the
// decision instead of re-deriving it also retires the second defect the same
// re-derivation produced: finding 054, a flag nothing wrote.
import { recoveryNotice } from "./editor-shell/recovery-notice.js";
import { EDITOR_V2_ACTIONS } from "./editor-shell-v2/narrow-editor-v2-client.js";

// The artifact this page is for.  A page that runs on whatever build happens to
// be in dist/ is a page that can show behaviour no evidence covers.
//
// Moved to the ABI 4 successor on 2026-08-22, with the profile below.  The two
// move together or the page pins one artifact and loads another -- and the
// expiry screen exists to make exactly that mismatch loud, so a half-move
// would look like a broken build rather than a mistake.
const PINNED_WASM_SHA256 = "4a2710bba1ef07d9";

const $ = (selector) => document.querySelector(selector);
const el = {
  canvas: $("#canvas"), paper: $("#paper"), desk: $("#desk"), sink: $("#sink"),
  toolbar: $("#toolbar"), fixture: $("#fixture"), text: $("#text"),
  openFile: $("#open-file"), file: $("#file"),
  clearFormat: $("#clear-format"),
  statePill: $("#state-pill"), toast: $("#toast"), expired: $("#expired"),
  notice: $("#notice"), noticeText: $("#notice-text"),
  noticeAction: $("#notice-action"),
  pinnedHash: $("#pinned-hash"), expectedHash: $("#expected-hash"),
  actualHash: $("#actual-hash"),
  a11yDoc: $("#a11y-doc"), a11yPara: $("#a11y-para"),
  a11yStructure: $("#a11y-structure"),
  s: { state: $("#s-state"), revision: $("#s-revision"), pending: $("#s-pending"),
       generation: $("#s-generation"), checkpoint: $("#s-checkpoint"),
       latency: $("#s-latency"), doc: $("#s-doc") },
};

const MAX_BACKING_WIDTH = 2400;
const MOVE_ACTIONS = new Set(["move-character-left", "move-character-right"]);
const FORMAT_ACTIONS = new Set(["set-bold", "set-italic", "set-underline",
  "set-strikethrough"]);

let session = null;
let documentName = "—";
let rendering = false;
let renderAgain = false;
let lastSelectionShape = "collapsed";
// The last tile the engine painted, kept so a caret move can be drawn without
// asking for pixels again (finding 058).  Cleared on resize, where the canvas
// changes size and the cached pixels stop describing it.
let lastTiles = [];

// Finding 062: the engine will not paint a tile taller than this.  Above it, it
// returns a correctly sized buffer it never drew into AND reports success --
// measured at two widths whose buffers differ by a factor of two (45 MB paints
// at 32,767 and 45 MB is blank at 32,768), so it is the height and not the
// memory.  Asking for one is therefore the PAGE's mistake: nothing forces this
// page to want the whole document in a single bitmap, and splitting the request
// needs no engine change and no link.
const MAX_TILE_HEIGHT = 32767;

function toast(message, bad = false) {
  el.toast.textContent = message;
  el.toast.classList.toggle("bad", bad);
  el.toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.toast.classList.remove("show"), 4000);
}

function describeError(error) {
  const code = error?.code ? `${error.code}：` : "";
  return `${code}${error?.message || String(error)}`;
}

/* ------------------------------------------------------------------ state */

/* ------------------------------------------------- roadmap 3.4: the projection
 *
 * A screen reader cannot read a canvas, and this whole document is one canvas.
 * Measured 2026-08-22 on the core that DOES provide accessibility: 171
 * accessibility-tree nodes and not one carrying a character of the document
 * (findings/evidence/aria-projection/BASELINE.md). So what the engine knows --
 * which paragraph the caret is in and what it says -- has to be put somewhere
 * the browser will build a tree from.
 *
 * SCOPE, named here rather than discovered in testing: this projects the
 * FOCUSED paragraph, because that is what the engine hands over. It is not a
 * browsable document; browse mode would need every paragraph and the engine
 * gives exactly one.
 *
 * The honesty rules are the point, not the decoration:
 *
 *   * a profile that does not carry the text SAYS SO. An empty region reads to
 *     a screen reader as "document, blank" -- a confident wrong answer about
 *     the user's own file, and the same defect the engine already refuses one
 *     layer down by reporting `core-built-without-accessibility` instead of
 *     `enabled: true`.
 *   * `fresh` is checked, not just `enabled`. `fresh` is the bit that says the
 *     last read succeeded, and until 2026-08-22 the engine reported it true on
 *     a build where no read can succeed -- so a projection that trusted
 *     `enabled` alone would read out the hash of an empty string as if it were
 *     a paragraph.
 *   * `dataset.reason` records WHY the region says what it says, so a run can
 *     tell "the projection is off" from "the projection ran and had nothing".
 */
// One reason per CAUSE, not one per user-visible sentence.
//
// The first run of this projection came back with two of three placements
// saying `engine`, and `engine` covered four different things at once -- so
// the reading was "something upstream is unhappy" and the run could not say
// which. A diagnosis that cannot name the layer is the defect this tree writes
// down every time (040, 048, 062); here it was in the instrument rather than
// in a conclusion, which is the cheap place for it to be.
//
// Several map to the same sentence on purpose: a screen reader user does not
// need to hear the difference between an absent block and a disabled one.
// `dataset.reason` carries it for the run; the text does not.
const A11Y_REASONS = {
  paragraph: null,
  profile: "這一版引擎沒有提供段落文字，所以無法朗讀文件內容。",
  noDocument: "尚未開啟文件。",
  noParagraph: "無障礙資訊目前不可用。",
  disabled: "無障礙資訊目前不可用。",
  stale: "尚未讀到游標所在的段落。",
  noText: "尚未讀到游標所在的段落。",
};

function projectFocusedParagraph(snapshot) {
  const para = snapshot?.editorState?.caretParagraph;
  let reason = "paragraph";
  let text = null;
  if (!session?.document) reason = "noDocument";
  else if (!session.offersCaretParagraphText?.()) reason = "profile";
  else if (!para) reason = "noParagraph";
  else if (para.enabled !== true) reason = "disabled";
  else if (para.fresh !== true) reason = "stale";
  else if (typeof para.text !== "string") reason = "noText";
  else text = para.text;

  const next = text ?? A11Y_REASONS[reason];
  // Compared before assigning, because an aria-live region announces when its
  // text CHANGES. updateState runs on every snapshot, and reassigning the same
  // string would be a repeat announcement of a paragraph the user is still
  // sitting in -- the projection would be talking over them.
  if (el.a11yPara.textContent !== next) el.a11yPara.textContent = next;
  el.a11yPara.dataset.reason = reason;
  el.a11yDoc.dataset.offers = session?.offersCaretParagraphText?.() ? "1" : "0";
}

/* ----------------------------------------- roadmap 3.4: the structure half
 *
 * WCAG 2.1 1.3.1 is Level A: information and relationships conveyed through
 * presentation must be programmatically determinable. A canvas conveys "this
 * is a heading" by drawing it larger; the DOM has to say it in roles.
 *
 * Everything below is driven by data that was MEASURED first
 * (findings/evidence/aria-projection/TREE-SHAPE.md):
 *
 *   role        AccessibleRole -- an enum. NOT the paragraph style name, which
 *               is a localised UI string (finding 031: `標題 1` under zh-TW),
 *               so a role derived from it passes in en-US and fails silently
 *               in the market this is for.
 *   level       numberingLevel + 1 == the ODT outline-level. Measured across
 *               seven levels including a gap.
 *   list item   isNumbered, read AFTER role, because a heading also reports
 *               numbered (outline numbering is numbering).
 *   order       child index at depth 1. 133 of 133 on a long document.
 *
 * IT IS A CONTRACT FIELD NOW. It was `a11y.tree` -- the engine's diagnostic
 * dump -- while the shape was being measured, and `documentOutline` since
 * e2-editor-v5: the worker's named projection of the same walk, carrying role,
 * level, focus and text and none of the depths, child counts or state bits
 * E1-B forbids promoting. The manifest declares it, so a page can tell an
 * absent outline from an empty document before reading one.
 *
 * Designed from a measurement rather than ahead of one: the shape came from
 * TREE-SHAPE.md, and "emit it on every state read" is what the diagnostic
 * build had already been doing without trouble on a 133-paragraph document.
 */
// FINDING 088. What the projection looked like last time, so an unchanged
// document is not rebuilt under a screen reader's feet.
//
// The FOCUS FLAG IS DELIBERATELY NOT IN THE SIGNATURE. It changes on every
// caret move, which is exactly when the rebuild must NOT happen -- putting it
// in would leave the guard technically present and permanently useless, which
// is worse than no guard because it looks like one.
let lastStructureSignature = null;
let lastFocusedElement = null;

function projectStructure(snapshot) {
  // THE CONTRACT FIELD, not the diagnostic tree.
  //
  // This read `a11y.tree` while the outline was being measured, and that field
  // carries depths, child counts and state bits -- diagnostic internals E1-B
  // forbids promoting. `documentOutline` is the worker's named projection of
  // the same walk: role as a product word, level, focus, text, and nothing
  // else. The manifest declares it, so the page can tell an absent outline
  // from an empty document before it reads one.
  const outline = snapshot?.editorState?.documentOutline;
  const nodes = Array.isArray(outline?.paragraphs) ? outline.paragraphs : null;
  // A TRANSIENT IS NOT AN EMPTINESS, and this is the measured reason for it:
  // two readings on 2026-08-23 came back with no tree at all, both immediately
  // after a keystroke, and both recovered on the next one. Blanking here would
  // announce an empty document in the middle of typing.
  if (!nodes) {
    el.a11yStructure.dataset.state = outline ? "transient" : "unavailable";
    // OUT OF THE TREE ENTIRELY when there is nothing to project.
    //
    // Measured: without this the shipped profile's accessibility tree went
    // 175 -> 176 -- one empty, unroled container. Inert, and still a change to
    // what a screen reader is handed on a profile this increment is not
    // supposed to touch. `aria-hidden` is the difference between "the shipped
    // page is unchanged" being true and being nearly true.
    //
    // NOT `hidden` and NOT `display:none`: those would also work here, but the
    // container has to come BACK when a profile does carry the data, and the
    // clip pattern above exists precisely because the display properties
    // remove a node from the tree permanently in ways that are easy to get
    // wrong. One mechanism for hiding, one for absence.
    el.a11yStructure.setAttribute("aria-hidden", "true");
    el.a11yStructure.replaceChildren();
    // The projection is absent or empty; the sink must not keep pointing into
    // a structure that is no longer there.
    el.sink.removeAttribute("aria-activedescendant");
    lastStructureSignature = null;
    lastFocusedElement = null;
    return;
  }
  el.a11yStructure.removeAttribute("aria-hidden");
  const paragraphs = nodes;
  // FINDING 088. `replaceChildren` on every snapshot destroyed and recreated
  // the list containers and the very node `aria-activedescendant` points at,
  // so Orca announced "leaving list", "List with 2 items" and the item again
  // -- measured 2026-09-05: each paragraph spoken 2-6 times, `leaving list`
  // nine times and `List with 2 items` ten times, for a document with two
  // lists. The owner heard it before any instrument reported it.
  //
  // The live region has carried this guard since it was written
  // (`projectFocusedParagraph`, "reassigning the same string would be a repeat
  // announcement of a paragraph the user is still sitting in"). This is that
  // reasoning applied to the half that did not have it.
  const signature = JSON.stringify(
    paragraphs.map((node) => [node.role ?? null, node.level ?? null,
                              node.text ?? ""]));
  const fragment = document.createDocumentFragment();
  let list = null;
  let focusedId = null;
  let index = -1;
  for (const node of paragraphs) {
    index += 1;
    const text = node.text ?? "";
    const isList = node.role === "listItem";
    if (!isList) list = null;
    let element;
    if (node.role === "heading") {
      element = document.createElement("div");
      element.setAttribute("role", "heading");
      // The engine already returns a 1-based level (NumberingLevel + 1),
      // measured to equal the document's own ODT outline-level across seven
      // levels including a gap. ARIA levels are 1-based too, so it passes
      // straight through -- no arithmetic here, which is the point: the
      // conversion lives once, next to the measurement that justified it.
      element.setAttribute("aria-level", String(node.level ?? 1));
    } else if (isList) {
      if (!list) {
        list = document.createElement("div");
        list.setAttribute("role", "list");
        fragment.appendChild(list);
      }
      element = document.createElement("div");
      element.setAttribute("role", "listitem");
    } else {
      element = document.createElement("p");
    }
    element.textContent = text;
    // FINDING 087. Every projected node gets a stable id so the sink can point
    // at one of them; without an id there is nothing for
    // `aria-activedescendant` to name.
    element.id = `a11y-node-${index}`;
    if (node.focused === true) {
      element.dataset.focused = "1";
      focusedId = element.id;
    }
    (isList ? list : fragment).appendChild(element);
  }
  if (signature === lastStructureSignature) {
    // Same document, same shape: move the focus marker and the pointer, and
    // leave every node where the accessibility tree already has it.
    if (lastFocusedElement) delete lastFocusedElement.dataset.focused;
    const kept = focusedId ? document.getElementById(focusedId) : null;
    if (kept) kept.dataset.focused = "1";
    lastFocusedElement = kept;
  } else {
    el.a11yStructure.replaceChildren(fragment);
    lastStructureSignature = signature;
    lastFocusedElement = focusedId ? document.getElementById(focusedId) : null;
  }
  // FINDING 087, and the reason it is HERE rather than on the live region.
  //
  // The live region announces text; it does not announce the role on its own
  // node. MEASURED with Orca 2026-09-03
  // (findings/evidence/087/RESULT-mechanisms.md): `role="heading"` plus
  // `aria-level` placed on the live region produced speech carrying the text
  // and no role, twice, for two different roles. The obvious one-attribute fix
  // does not work, and its silence is not evidence of anything -- the
  // `paragraph` role already sitting there is one Orca never speaks either.
  //
  // What DOES work, measured in the same session: pointing the focused
  // textbox at a node that carries the role. Orca then announced "heading 1"
  // on the heading and "List with 2 items" on entering the list, announcing
  // the container once rather than on every item.
  //
  // `aria-owns` is required: `aria-activedescendant` may only name a
  // descendant of the element carrying it, or of something it owns, and the
  // projection is not inside the textarea.
  if (focusedId) {
    if (el.sink.getAttribute("aria-owns") !== el.a11yStructure.id)
      el.sink.setAttribute("aria-owns", el.a11yStructure.id);
    if (el.sink.getAttribute("aria-activedescendant") !== focusedId)
      el.sink.setAttribute("aria-activedescendant", focusedId);
  } else {
    // No focused paragraph in this projection: point at nothing rather than at
    // a stale node. A DANGLING activedescendant is worse than none -- it names
    // a node that no longer exists and an AT may announce the wrong paragraph.
    el.sink.removeAttribute("aria-activedescendant");
  }
  el.a11yStructure.dataset.state = "projected";
  el.a11yStructure.dataset.paragraphs = String(paragraphs.length);
  // The cap travels to the DOM too. A projection that silently stops at the
  // engine's limit would look like a short document; `truncated` is how a run
  // tells those apart without reading the engine's source.
  const count = outline?.paragraphCount;
  el.a11yStructure.dataset.truncated =
    (typeof count === "number" && count > paragraphs.length) ? "1" : "0";
}

function updateState(snapshot) {
  el.statePill.dataset.state = snapshot.state;
  el.statePill.textContent = {
    idle: "未開啟", loading: "載入中", ready: "就緒", busy: "處理中",
    "recoverable-error": "需要回復", "restart-required": "需要重新開啟",
    stopped: "已停止",
  }[snapshot.state] ?? snapshot.state;
  el.s.state.textContent = snapshot.state;
  el.s.revision.textContent = snapshot.revision ?? "—";
  el.s.pending.textContent = snapshot.pending ?? "—";
  el.s.generation.textContent = snapshot.generation ?? "—";
  el.s.checkpoint.textContent = snapshot.hasCheckpoint
    ? `有（r${snapshot.checkpointRevision ?? "?"}）`
    : snapshot.checkpointError ? "寫入失敗" : "無";
  projectFocusedParagraph(snapshot);
  projectStructure(snapshot);
  const notice = recoveryNotice(snapshot);
  el.notice.dataset.show = notice.visible ? "1" : "0";
  // The decision, stamped where a reader can see it: hosts may differ in
  // wording, they may not differ in whether they claim work was preserved.  A
  // check that asserts the wording would go green the day somebody rephrases
  // the sentence; this is the thing that must not change.
  el.notice.dataset.rescue = notice.canRescue ? "checkpoint"
    : notice.checkpointFailed ? "failed" : "none";
  if (notice.visible) {
    el.noticeText.textContent = notice.canRescue
      ? "這一步可能已經改到文件，而且無法驗證。回到選取手勢前的檢查點。"
      : notice.checkpointFailed
      ? "引擎需要重新開啟。我們試著先保住你的工作，那次存檔失敗了——自上次儲存以來的內容不會回來。"
      : "引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。";
    el.noticeAction.textContent = notice.canRescue
      ? "回到檢查點" : "重新開啟";
    // Finding 054 was this line reading a flag nothing writes.  It now comes
    // from the same module as everything else about this notice, which is the
    // point: one place decides, and re-deriving it here is what produced both
    // 054 and 061.
    el.noticeAction.disabled = !notice.restartPossible;
  }
  updateGestureAffordance();
  updateRedoAffordance();
  // Finding 058.  The caret arrives as a state update, not as a document
  // change, so redrawing only on render would leave it a gesture behind.
  paint();
}

/**
 * Grey a button out when the manifest does not offer that action for the shape
 * of selection currently in front of it.
 *
 * SPEC E2-C 2.5: the declaration for the ten inherited actions is `collapsed`
 * only, and the engine does not enforce it -- the mask is read on the paragraph
 * route alone.  The honest place to surface a narrowing nothing enforces is the
 * button, not a failure after the fact.
 */
function updateGestureAffordance() {
  // THE PAGE'S BELIEF, SAID OUT LOUD.
  //
  // `lastSelectionShape` is a module local, so until now the only way to read
  // it from outside was to infer it from which buttons went grey -- and that
  // inference broke the moment `e2-editor-v7` offered the four inline formats
  // for ranges, because `an-aborted-gesture-stops-selecting` used exactly that
  // proxy ("are the format buttons disabled?") to mean "is a range selected?".
  // Widening the manifest silently disarmed a check.  A belief a check has to
  // guess at is a belief that will be guessed at wrongly.
  el.toolbar.dataset.selectionShape = lastSelectionShape;
  if (!session?.editor) return;
  for (const button of el.toolbar.querySelectorAll("button[data-action]")) {
    const action = button.dataset.action;
    if (!EDITOR_V2_ACTIONS.includes(action)) continue;
    const gestures = session.gesturesFor(action);
    const offered = !Array.isArray(gestures) || gestures.includes(lastSelectionShape);
    button.disabled = !offered;
    button.title = offered ? "" :
      `manifest 沒有為「${lastSelectionShape}」宣告這個動作`;
  }
  // `aria-pressed` is set only when the answer is KNOWN: a button that renders
  // a state it is guessing at is the trap the toggle bug already was, one layer
  // up.  All four now, because since the 2026-08-19 relink the engine keeps a
  // cache for underline and strikethrough too -- they were always in core's
  // GetKitUnoCommandList and always broadcast; nobody had written the cache,
  // and this list was hard-coded to the two that had one.
  for (const action of ["set-bold", "set-italic", "set-underline",
                        "set-strikethrough"]) {
    const button = el.toolbar.querySelector(`[data-action="${action}"]`);
    if (!button) continue;
    const state = formatStateFor(action);
    if (state === null) button.removeAttribute("aria-pressed");
    else button.setAttribute("aria-pressed", state ? "true" : "false");
  }
}

/**
 * Show 重做 only on a profile that carries redo.
 *
 * HIDDEN rather than DISABLED, and the difference is the point: a disabled
 * button says "this exists but not right now", which is a promise about a
 * later moment that will never arrive on this profile. Redo is absent from the
 * contract until the ABI 4 artifact, so on anything older there is nothing to
 * say.
 *
 * The same rule kept Ctrl+A unbound and kept Up/Down out of the key map until
 * the manifest carried their action.
 */
function updateRedoAffordance() {
  const button = el.toolbar.querySelector('[data-action="redo"]');
  if (!button) return;
  button.hidden = !session?.offersRedo?.();
}

/* ----------------------------------------------------------------- canvas */

function layoutCanvas() {
  if (!session?.document) return;
  const available = Math.max(320, el.desk.clientWidth - 40);
  const cssWidth = Math.min(available, 900);
  const ratio = session.document.heightTwips / session.document.widthTwips;
  const backingWidth = Math.min(MAX_BACKING_WIDTH,
                                Math.round(cssWidth * (globalThis.devicePixelRatio || 1)));
  el.canvas.width = backingWidth;
  el.canvas.height = Math.round(backingWidth * ratio);
  el.canvas.style.width = `${cssWidth}px`;
  el.canvas.style.height = `${Math.round(cssWidth * ratio)}px`;
  // Setting width/height clears the canvas AND invalidates the cached tile,
  // which is sized in device pixels for the old dimensions.
  lastTiles = [];
}

async function renderDocument(retriesLeft = 6) {
  if (!session?.document
      || !["ready", "busy"].includes(session.state.snapshot.state))
    return;
  if (rendering) { renderAgain = true; return; }
  rendering = true;
  try {
    // One request per strip, none of them taller than the engine will paint.
    // A document short enough to fit takes exactly one strip covering the whole
    // canvas, which is the request this page has always made -- so nothing
    // changes for the common case.
    const strips = [];
    let documentResized = false;
    const total = el.canvas.height;
    const documentHeight = session.document.heightTwips;
    for (let top = 0; top < total; top += MAX_TILE_HEIGHT) {
      const rows = Math.min(MAX_TILE_HEIGHT, total - top);
      // The twips edges are derived from the PIXEL edges rather than by
      // multiplying a per-strip height, so rounding cannot accumulate into a
      // seam or leave the last strip short.
      const yTwips = Math.round((top / total) * documentHeight);
      const endTwips = Math.round(((top + rows) / total) * documentHeight);
      const tile = await session.document.render({
        xTwips: 0, yTwips,
        widthTwips: session.document.widthTwips,
        heightTwips: endTwips - yTwips,
        canvasWidthPx: el.canvas.width,
        canvasHeightPx: rows,
      }, { timeoutMs: 60000 });
      if (!tileWasPainted(tile)) {
        throw Object.assign(
          new Error("引擎回了一張沒有畫進去的圖"),
          { code: "TILE_NOT_PAINTED" });
      }
      // Finding 062's second half: until the engine started reporting it, a
      // document that grew a page left this canvas sized from the height it
      // had when it was opened, and nothing could tell.  The SDK has already
      // updated the handle by the time this returns, so re-laying out picks up
      // the new height.
      if (tile.documentSizeChanged) documentResized = true;
      strips.push({
        image: new ImageData(new Uint8ClampedArray(tile.pixels),
                             tile.width, tile.height),
        y: top,
      });
    }
    lastTiles = strips;
    paint();
    if (documentResized) {
      // Through `renderAgain` rather than by recursing here: that is the
      // path this function already uses to coalesce a repaint, and the
      // `finally` below is what runs it.  It terminates because the engine
      // reports a CHANGE, so the next reply for an unchanged document says
      // false.
      layoutCanvas();
      renderAgain = true;
    }
  } catch (error) {
    // A repaint that lands while a barrier is still settling comes back BUSY.
    // The canvas is a frame behind; the document is fine.
    // TILE_NOT_PAINTED is not transient: the same request will come back
    // unpainted every time, so retrying it would only make the user wait
    // longer for the same silence.
    if (error?.code === "BUSY" && retriesLeft > 0) {
      await new Promise((resolve) => setTimeout(resolve, 120));
      rendering = false;
      return renderDocument(retriesLeft - 1);
    }
    toast(`重繪失敗：${describeError(error)}`, true);
  } finally {
    rendering = false;
    if (renderAgain) { renderAgain = false; void renderDocument(); }
  }
}

/**
 * Finding 058: draw the caret and the selection.
 *
 * The engine has always sent both -- `caret` and `selection.rectangles` reach
 * the page in `editorState`, and the page used the rectangles only to COUNT
 * them for gesture shape.  Its one drawing call pasted the tile.  LOK does not
 * paint the text cursor or the selection into tiles; they arrive as callback
 * rectangles for the client to draw, and the client never did.  So a user
 * clicked and saw nothing move, dragged and saw nothing highlight.
 *
 * Nine product-path checks were green throughout, because every one of them
 * reads the DOM or the saved ODT -- and all of those pass on a page that draws
 * nothing at all.
 *
 * The tile is cached so the overlay can be repainted on a caret move without
 * asking the engine for pixels again: a caret arriving as a state update must
 * not cost a full document render.
 */
/**
 * Did the engine actually draw into this buffer?
 *
 * Finding 062: above a certain height it returns a correctly sized buffer,
 * never draws into it, and reports success -- so the return value cannot be
 * trusted and the page has no other way to tell.  It can tell from the pixels,
 * cheaply, because an UNPAINTED buffer is all zeros including its alpha channel
 * while a page that is merely blank is opaque white.  So this asks about alpha
 * only, at a few hundred sample points: a bounded number of reads on a buffer
 * that can be a hundred megabytes.
 *
 * Deliberately not a colour test.  "Is there any dark pixel" would call a
 * genuinely blank page a failure, and a blank page is a thing documents have.
 *
 * And deliberately a MAJORITY, not "any opaque pixel".  The first version
 * returned true on the first non-zero alpha it found, and an unpainted buffer
 * is not uniformly zero -- measured, 88 of 2,105,340 sampled points are not,
 * and one of them near the start defeats the whole test.  A painted tile is
 * about 90% opaque and an unpainted one is 0%, so half is a threshold with two
 * orders of magnitude of room on either side.
 */
function tileWasPainted(tile) {
  const pixels = new Uint8Array(tile.pixels);
  if (pixels.length === 0) return false;
  const samples = 512;
  const step = Math.max(4, Math.floor(pixels.length / 4 / samples) * 4);
  let seen = 0;
  let opaque = 0;
  for (let index = 3; index < pixels.length; index += step) {
    seen += 1;
    if (pixels[index] > 128) opaque += 1;
  }
  return seen > 0 && opaque * 2 >= seen;
}

function paint() {
  if (!lastTiles.length) return;
  const context = el.canvas.getContext("2d");
  for (const strip of lastTiles) context.putImageData(strip.image, 0, strip.y);
  const editorState = session?.state?.snapshot?.editorState;
  if (!editorState || !session?.document) return;

  // Rectangles are twips in document space; the canvas is the whole document.
  const scaleX = el.canvas.width / session.document.widthTwips;
  const scaleY = el.canvas.height / session.document.heightTwips;
  const box = (r) => [r.x * scaleX, r.y * scaleY,
                      Math.max(1, r.width * scaleX),
                      Math.max(1, r.height * scaleY)];

  const rectangles = editorState.selection?.rectangles;
  if (Array.isArray(rectangles) && rectangles.length) {
    context.save();
    // Multiply keeps the glyphs readable under the wash instead of covering
    // them, which a filled rectangle at any useful opacity would do.
    context.globalCompositeOperation = "multiply";
    context.fillStyle = "#b7d3f2";
    for (const rectangle of rectangles) context.fillRect(...box(rectangle));
    context.restore();
  }

  // The caret last, so it is never washed over by the selection it sits in.
  // Drawn only when the selection is collapsed: LOK keeps sending a cursor
  // rectangle during a range selection, and painting a caret in the middle of
  // a highlight says something about the document that is not true.
  const caret = editorState.caret;
  if (caret && editorState.selection?.collapsed !== false) {
    // The sink rides the caret.  Two reasons, and the second is the one that
    // was reported: an IME's candidate window opens next to the focused
    // element, so a sink parked elsewhere puts the candidates in the wrong
    // place; and the browser scrolls the focused element into view when
    // composition starts, which is harmless only if the sink is already where
    // the user is looking.  Parked at the bottom of the document, as it was
    // until 2026-08-22, that scroll dragged the whole desk down on every
    // Chinese keystroke.
    //
    // CSS pixels, from the canvas's DISPLAYED size -- `box()` above works in
    // BACKING pixels, which differ by devicePixelRatio, and positioning a DOM
    // element with those would put the sink at roughly twice the offset on a
    // HiDPI screen.
    moveSinkToCaret(caret);
    const [x, y, , height] = box(caret);
    context.save();
    context.fillStyle = "#1a1a1a";
    context.fillRect(x, y, Math.max(1, Math.round(scaleX * 15)), height);
    context.restore();
  }
}

function moveSinkToCaret(caret) {
  const width = el.canvas.clientWidth;
  const height = el.canvas.clientHeight;
  if (!width || !height || !session?.document) return;
  const scaleX = width / session.document.widthTwips;
  const scaleY = height / session.document.heightTwips;
  el.sink.style.left = `${Math.round(caret.x * scaleX)}px`;
  el.sink.style.top = `${Math.round(caret.y * scaleY)}px`;
  // Matching the caret's height rather than staying 1px tall: an IME places
  // its candidate window against the focused element's box, so a sink the
  // height of the text line puts the candidates on the line instead of
  // clipping them to a single pixel row.
  el.sink.style.height = `${Math.max(1, Math.round(caret.height * scaleY))}px`;
}

function pointToTwips(event) {
  const rectangle = el.canvas.getBoundingClientRect();
  return {
    xTwips: Math.max(0, Math.round(
      (event.clientX - rectangle.left) / rectangle.width
      * session.document.widthTwips)),
    yTwips: Math.max(0, Math.round(
      (event.clientY - rectangle.top) / rectangle.height
      * session.document.heightTwips)),
  };
}

/* ---------------------------------------------------------------- actions */

async function run(label, operation) {
  const started = performance.now();
  try {
    const result = await operation();
    el.s.latency.textContent = `${label} ${Math.round(performance.now() - started)} ms`;
    await renderDocument();
    return result;
  } catch (error) {
    el.s.latency.textContent = `${label} 失敗`;
    // The disposition is a field, not a guess from the message (E2-B 5.13).
    const recovery = error?.recovery;
    toast(`${label}：${describeError(error)}` +
          (recovery === "rollback" ? "（可能已經改到文件：請回到檢查點）"
           : recovery === "restart" ? "（需要重新開啟文件）"
           // Finding 046's residual.  Says dispatched-and-unverified, and does
           // NOT say it worked -- the barrier did not verify it.  Undo is
           // named because "review" leaves the queue open, which is the only
           // reason that advice is honest.
           // Two different reasons reach `review`, and telling the user the
           // wrong one is worse than saying less.  The disposition is still
           // read from the field (E2-B 5.13); only the EXPLANATION is chosen
           // by code.
           : recovery === "review"
             ? (error?.code === "LOK_COMMAND_FAILED"
                // Finding 059.
                ? "（動作已送出，引擎收到了核心的回覆但無法據以判定成敗，"
                  + "所以這裡不敢說它成功了。請看一下結果，不是你要的就按「復原」）"
                // FINDING 083.  Its own sentence, and it needs one: this shape
                // reaches `review` because NOTHING was selected, so telling the
                // user the check "covered more than one paragraph" would be
                // literally false about their document.  Finding 061 is the
                // precedent -- a sentence that is true of a different case is
                // misleading attribution, and this tree has filed that as a
                // defect once already.
                : error?.details?.formatBarrier?.failureShape
                    === "stage-deadline:awaiting-selection"
                ? "（動作已送出，但這一段是空的，檢查要用的選取取不到任何內容，"
                  + "所以無法核對。請看一下結果，不是你要的就按「復原」。"
                  + "這是檢查的極限，不是文件壞了）"
                : "（動作已送出，但這一格的檢查涵蓋了不只一個段落，無法單獨核對你的段落。"
                  + "請看一下結果，不是你要的就按「復原」。這是檢查的極限，不是文件壞了）")
           : ""), true);
    throw error;
  }
}

// Finding 045, the product half.  The ENGINE has taken an explicit boolean
// since the v3 link -- `inlineFormatArgument` builds
// {"Bold":{"type":"boolean","value":...}} from it -- and this line sent `true`
// unconditionally, so from a user's seat bold could be turned on and never off.
// The fix shipped in the artifact and the page never used it.
//
// Bold and italic are decided from state: the worker already projects
// `format: {bold, italic}` as a tri-state (null = the engine does not know).
// Underline and strikethrough have no state to read -- OUR engine keeps no
// cache for them.  The reason probe_engine.cpp gives (that neither is in core's
// GetKitUnoCommandList) is false: both are in it
// (sfx2/source/control/unoctitm.cxx:1165ff) and both were measured broadcasting
// on 2026-08-18, findings/evidence/059/native/predicate/.  The cache is missing,
// not impossible -- so they
// stay one-way here and get their off path from 清除格式 below, which claims
// nothing about the current state.
//
// Note what the 045 fix buys beyond correctness: an explicit set is ROBUST
// under a stale read.  Guess wrong and the user presses again and it is right,
// because the second dispatch names the value it wants.  A toggle would turn a
// stale read into a silent no-op.
function formatStateFor(action) {
  const format = session?.state?.snapshot?.editorState?.format;
  // All four, since the 2026-08-19 relink gave underline and strikethrough the
  // state cache they never had.  `?? null` and not `||`: the engine says null
  // when it does not know, and "I do not know" must not read as "off".
  if (action === "set-bold") return format?.bold ?? null;
  if (action === "set-italic") return format?.italic ?? null;
  if (action === "set-underline") return format?.underline ?? null;
  if (action === "set-strikethrough") return format?.strikethrough ?? null;
  return null;
}

// The name to put in front of a failure, for actions that have no button.
//
// `editorAction` used to read the label straight off the toolbar button, which
// held only while every dispatchable action had one. The ABI 4 profile made
// four movements and delete-selection reachable from the keyboard with no
// button behind them, and `querySelector(...).textContent` on a null threw a
// TypeError BEFORE `run()` -- so the key was swallowed by preventDefault,
// nothing dispatched, and the call site's `.catch(() => {})` ate the evidence.
// A key that looks bound and does nothing, arrived at through a label lookup.
const ACTION_LABELS = {
  "move-line-up": "上移一行",
  "move-line-down": "下移一行",
  "move-line-home": "移到行首",
  "move-line-end": "移到行尾",
  "delete-selection": "刪除選取",
};

async function editorAction(action) {
  const button = el.toolbar.querySelector(`[data-action="${action}"]`);
  const label = button ? button.textContent.trim()
                       : (ACTION_LABELS[action] ?? action);
  const options = FORMAT_ACTIONS.has(action)
    // `=== true` and not truthiness: null means the engine has no answer, and
    // the honest response to that is to ask for ON, which is what the button
    // says it does.
    ? { enabled: formatStateFor(action) !== true }
    : {};
  await run(label, () => session.action(action, options));
}

// Every inline format turned off in one press.  It is honest precisely because
// it asserts nothing about what was on: it asks for off.
//
// It used to say this was the ONLY off path for underline and strikethrough,
// "which have no readable state".  As of the 2026-08-19 relink the engine keeps
// a cache for both -- they were always in core's GetKitUnoCommandList and
// always broadcast; nobody had written the cache.  Whether the page can SEE
// them is a separate question from whether the engine knows them.
async function clearInlineFormatting() {
  for (const action of ["set-bold", "set-italic", "set-underline",
                        "set-strikethrough"]) {
    await run("清除格式", () => session.action(action, { enabled: false }));
  }
  toast("已清除粗體、斜體、底線、刪除線");
}

async function insertText() {
  const text = el.text.value;
  if (!text) { toast("先在欄位裡輸入要插入的文字", true); return; }
  await run("插入文字", () => session.commitText(text));
}

async function saveDocument() {
  // `EditorSession.save()` resolves to {bytes, revision, contentStamp}, not to
  // the bytes.  Taking the whole result made `new Blob([result])` stringify it,
  // so every save from this button wrote 15 bytes of "[object Object]" and the
  // toast below reported NaN KB -- finding 049, found by an operator pressing
  // the button, because every harness in this tree calls session.save() itself
  // and destructures.
  const { bytes } = await run("儲存", () => session.save());
  const url = URL.createObjectURL(
    new Blob([bytes], { type: "application/vnd.oasis.opendocument.text" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = documentName.replace(/\.odt$/i, "") + "-v2.odt";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  toast(`已存出 ${(bytes.byteLength / 1024).toFixed(1)} KB`);
}

// FINDING 066.  A mouse click on a toolbar button moves the keyboard onto the
// button -- ordinary <button> behaviour -- and this page never gave it back.
// `el.sink.focus()` appeared exactly ONCE in this file, inside the canvas
// pointerdown handler, so the only way a user could type again was to click the
// canvas -- and that click MOVES THE CARET, which discards the inline format
// they had just set.  Measured 2026-08-22, both halves: press B and type and
// nothing reaches the document at all (the keystrokes go to the button); click
// first and the text arrives without the format.  findings/evidence/066/.
//
// Two lines and both are load-bearing:
//
//   * `preventDefault` on mousedown stops the button taking the keyboard in the
//     first place, which is what every editor toolbar does.  `click` still
//     fires, so nothing about the action changes.
//   * focusing the sink covers the case the first line cannot: a user whose
//     FIRST act is pressing B, before ever clicking the document, has focus on
//     <body> and preventing the button from taking it does not help.
//
// Focusing the sink does NOT move the caret -- only a canvas pointerdown does
// that -- so this cannot itself become the defect it repairs.
//
// Buttons only, deliberately: `#fixture` and `#text` live in this toolbar too
// and a user must still be able to click into them.
//
// The keyboard-activated path is NOT covered and that is on purpose: someone who
// tabs to a button and presses Space keeps focus there, which is what keyboard
// navigation is supposed to do.
el.toolbar.addEventListener("mousedown", (event) => {
  if (!event.target.closest("button")) return;
  event.preventDefault();
  if (session) el.sink.focus({ preventScroll: true });
});

el.toolbar.addEventListener("click", (event) => {
  const action = event.target.closest("button")?.dataset.action;
  if (!action || !session) return;
  const handler =
    action === "undo" ? () => run("復原", () => session.undo())
    : action === "redo" ? () => run("重做", () => session.redo())
    : action === "insert-text" ? () => insertText()
    : action === "save" ? () => saveDocument()
    : EDITOR_V2_ACTIONS.includes(action) ? () => editorAction(action)
    : null;
  if (handler) void Promise.resolve(handler()).catch(() => {});
});

el.noticeAction.addEventListener("click", () => {
  void run("回到檢查點", () => session.rollback())
    .then(() => renderDocument())
    .catch(() => {});
});

/* ------------------------------------------------------------------- drag */

// A real pointer drag through this page's own handler.  Coordinates, not
// synthesised mouse events: SPEC E1-D 2.1 measured the synthesised path
// reporting a selection it had not made.
const drag = { active: false, start: null, latest: null, inFlight: false,
  pointerId: null };

async function pumpDrag() {
  if (drag.inFlight || !drag.latest || !session?.editor) return;
  const end = drag.latest;
  drag.latest = null;
  drag.inFlight = true;
  try {
    const result = await session.selectRange(drag.start, end);
    // What the engine read back, not what we asked for -- AND FROM WHERE IT
    // ACTUALLY IS.
    //
    // FINDING 079.  This read `result.collapsed` and `result.rectangles`, which
    // is the shape `editor-shell/editor-client.js` BUILDS for the v1 path.  The
    // v2 client does not build anything: `ParagraphEditorClient.selectRange`
    // returns the worker's envelope verbatim, and its keys are
    // `method, revision, completion, callbackSequenceBefore,
    // callbackSequenceAfter, state` -- the selection is one level down, at
    // `state.selection`.  So both reads were `undefined`, `undefined === false`
    // is false, `undefined?.length ?? 0` is 0, and this expression returned
    // "collapsed" for EVERY drag, unconditionally.
    //
    // That is why 079 looked like staleness and is not: there was never a value
    // to go stale.  Nothing needed to arrive late or be reset; the shape was
    // manufactured from two fields that are not there.
    //
    // Measured 2026-08-23 on the shipped e2-editor-v7, both branches, with the
    // engine's own answer recorded in the same arm
    // (tools/probe_079_selection_shape.py --capture-result):
    //   drag inside one line    state.selection.collapsed=false, 1 rectangle,
    //                           engine copy path returns 12 characters
    //   drag across two lines   state.selection.collapsed=false, 3 rectangles,
    //                           engine copy path returns 34 characters
    // and the page reported `collapsed` for both.
    // THE DERIVATION LIVES IN ONE PLACE AND HAS ITS OWN TESTS.
    //
    // Deriving it here was the defect's shape as much as its content: an
    // inline read, with nothing under test, of a field layout some other layer
    // assembles.  A DOM flag catches the NEXT drift in this one reader; it does
    // nothing about a second reader looking in a second wrong place.
    // `selectionShapeOf` is in editor-shell-v2 with the recorded envelopes as
    // its fixtures, and one of its cases IS finding 079 -- a v1-shaped object
    // must come back unknown rather than `collapsed`.
    const shape = selectionShapeOf(result);
    if (shape === null) {
      // AN UNREADABLE RESULT IS NOT AN EMPTY SELECTION, and saying it is was
      // the whole of 079.  The previous value is kept rather than replaced by
      // a guess: guessing `collapsed` is the defect being fixed, and guessing a
      // range would grey out the two deletes and both breaks after an ordinary
      // click, which is the worse of the two failures.
      //
      // DEGENERATE CASE, stated rather than left to be discovered: if the FIRST
      // result of a session is unreadable, the value kept is the initial one,
      // `collapsed` -- so this policy degrades into the option it rejects, and
      // the only thing separating them is that the flag below is up.  That is
      // the point of the flag, and it is why the flag rather than the shape is
      // what the regression check reads.
      el.toolbar.dataset.selectionUnreadable = "1";
      // WHAT IT ACTUALLY GOT.  A flag that says only "this happened" sends the
      // next reader to a browser to find out what the object looked like; the
      // key names answer it from the report.  Names only -- `state` can carry
      // the focused paragraph's text on a profile that projects it, and a
      // public DOM attribute is no place for a user's paragraph.
      el.toolbar.dataset.selectionEvidence = selectionShapeEvidence(result);
    } else {
      delete el.toolbar.dataset.selectionUnreadable;
      delete el.toolbar.dataset.selectionEvidence;
      lastSelectionShape = shape;
    }
    updateGestureAffordance();
  } catch {
    // A refused range must not abort the gesture.
  } finally {
    drag.inFlight = false;
    if (drag.latest) void pumpDrag();
  }
}

function endDrag(event) {
  if (!drag.active) return;
  drag.active = false;
  if (drag.pointerId !== null) {
    try { el.canvas.releasePointerCapture(drag.pointerId); } catch { /* gone */ }
    drag.pointerId = null;
  }
  if (!session?.document || !event) return;
  const end = pointToTwips(event);
  if (end.xTwips === drag.start.xTwips && end.yTwips === drag.start.yTwips)
    return;   // a click is a zero-length drag; leave the caret where it landed
  drag.latest = end;
  void pumpDrag();
}

el.canvas.addEventListener("pointerdown", (event) => {
  if (!session?.document || event.button !== 0) return;
  event.preventDefault();
  const point = pointToTwips(event);
  el.sink.focus({ preventScroll: true });
  drag.active = true;
  drag.start = point;
  drag.latest = null;
  drag.pointerId = event.pointerId;
  try { el.canvas.setPointerCapture(event.pointerId); }
  catch { drag.pointerId = null; }
  lastSelectionShape = "collapsed";
  void run("定位游標", () => session.placeCaret(point.xTwips, point.yTwips))
    .then(() => updateGestureAffordance())
    .catch(() => {});
});

// Ctrl+C.  The document is a canvas, so the browser's default copy has no DOM
// selection to take and puts nothing on the clipboard -- which is why four
// operator rounds of the D5 clipboard cell pasted either nothing or whatever
// had been copied from some other application earlier.  The shell has always
// had `copySelection()`, which asks the ENGINE for the selected text; nothing
// called it.
el.sink.addEventListener("copy", (event) => {
  if (!session?.document) return;
  event.preventDefault();
  void run("複製", () => session.copySelection())
    .then((result) => toast(`已複製 ${result?.codePoints ?? "?"} 字`))
    .catch(() => {});
});

// NO paste listener here, deliberately, and it is not an oversight.
//
// Ctrl+V looks like the copy defect above -- `session.pasteEvent()` exists and
// nothing calls it -- and on 2026-08-17 a handler was written on exactly that
// reasoning.  The mutation round measured it: the marker landed in the saved
// document TWICE (markOccurrences 2, revision +2).  Paste already arrives, as
// `beforeinput` with inputType insertFromPaste, which the input adapter
// attached to this sink already commits.  Adding a page-level handler makes a
// second commit of the same text.
//
// The two cases are not the same shape after all: the canvas has no DOM
// selection for the browser to copy FROM, so copy needed the engine asked; the
// sink is a real editable target, so paste arrives on its own.  `pasteEvent()`
// is for hosts without an input sink.  `ctrl-v-reaches-the-document` in the
// product-path runner now requires EXACTLY ONE occurrence, so re-adding a
// handler here goes red rather than looking like success.

// Backspace and Delete.  NOT a keyboard shortcut -- this is the primary way
// anybody corrects a typo, and until now the product had none: the input
// adapter drops `deleteContentBackward`/`deleteContentForward` into
// `ignored-input-type` (input-adapter.js) and does not preventDefault, so the
// keys did nothing and the user had to reach for the toolbar's ⌫ button.
//
// Handled HERE and not in the adapter, deliberately: the adapter's job is to
// commit text, and deleting is an editor action with its own contracted wire
// id. Checked before writing, after the paste episode: the adapter really does
// leave these alone, so this is not a second handler for the same event.
const DELETE_INPUT_TYPES = {
  deleteContentBackward: "delete-backward",
  deleteContentForward: "delete-forward",
};

// FINDING 073: show the user what they are part way through typing.
//
// The sink is one transparent pixel by design, and the browser draws an IME's
// preedit INSIDE it -- so composing 台 with 新酷音 wrote ㄊㄞˊ into a box
// nobody can see, and the first thing the user saw was the committed
// character. There are no compositionstart/update handlers anywhere else in
// this file: composition is entirely the browser's until `beforeinput`
// delivers the result, which is why nothing had to be undone to add this.
//
// The measuring context is a detached canvas, not the document's: this asks
// how wide the preedit is, and borrowing the drawing surface for that would
// make a text measurement depend on the render state.
const compositionRuler = document.createElement("canvas").getContext("2d");

function showComposition(text) {
  const style = getComputedStyle(el.sink);
  // The font size comes from the CARET's own height, which
  // `moveSinkToCaret` already set from the engine's cursor rectangle -- so the
  // preedit is about the size of the line it will land on rather than a
  // constant that is wrong at every zoom level. 0.75 is the usual ratio of an
  // em to a line box; the floor is legibility, not geometry.
  const line = el.sink.offsetHeight || 16;
  el.sink.style.fontSize = `${Math.max(11, Math.round(line * 0.75))}px`;
  compositionRuler.font = `${el.sink.style.fontSize} ${style.fontFamily}`;
  const width = compositionRuler.measureText(text || "").width;
  // A floor, because compositionstart arrives with nothing composed yet and a
  // zero-width box would flash. The padding is for the caret the browser draws
  // at the end of the preedit.
  el.sink.style.width = `${Math.max(14, Math.ceil(width) + 10)}px`;
  el.sink.dataset.composing = "1";
}

function hideComposition() {
  delete el.sink.dataset.composing;
  // Cleared rather than set back to 1px: the stylesheet owns the resting size,
  // and an inline width would silently outrank a later change to it.
  el.sink.style.width = "";
  el.sink.style.fontSize = "";
}

el.sink.addEventListener("compositionstart", () => showComposition(el.sink.value));
el.sink.addEventListener("compositionupdate", (event) => showComposition(event.data));
// BOTH endings. `compositionend` is the ordinary one; `blur` is the one that
// gets forgotten -- an IME abandoned by clicking away never fires
// compositionend in every browser, and a sink left visible sits on top of the
// document with stale text in it.
el.sink.addEventListener("compositionend", hideComposition);
el.sink.addEventListener("blur", hideComposition);

el.sink.addEventListener("beforeinput", (event) => {
  const action = DELETE_INPUT_TYPES[event.inputType];
  if (!action || !session?.document) return;
  event.preventDefault();
  void editorAction(action).catch(() => {});
});

// Arrow keys produce no `beforeinput` at all, so they need keydown.
//
// All six are listed, and the PROFILE decides which of them bind. Until the
// ABI 4 link, `move-line-*` exist in the engine but are not in the v3
// contract, and `offers()` reports them absent -- so on that profile Up/Down/
// Home/End fall through untouched, exactly as when they were not listed here
// at all. The rule this file already states twice stays intact: a key that
// cannot dispatch must not be taken.
//
// Listing them now rather than after the link means the binding is not a
// second thing to remember on the day the artifact changes; it lights up
// because the manifest says the action exists, which is the same question
// `updateGestureAffordance` asks for the toolbar.
const KEY_ACTIONS = {
  ArrowLeft: "move-character-left",
  ArrowRight: "move-character-right",
  ArrowUp: "move-line-up",
  ArrowDown: "move-line-down",
  Home: "move-line-home",
  End: "move-line-end",
};

el.sink.addEventListener("keydown", (event) => {
  if (!session?.document) return;
  const accel = event.ctrlKey || event.metaKey;
  if (accel && event.key.toLowerCase() === "z" && !event.shiftKey) {
    // Ctrl+Z, and it earns its place: finding 046's review disposition tells
    // the user to press 復原, and until now the only way to do that was to find
    // the button.
    event.preventDefault();
    void run("復原", () => session.undo()).catch(() => {});
    return;
  }
  if (accel && ((event.key.toLowerCase() === "z" && event.shiftKey)
                || event.key.toLowerCase() === "y")) {
    // Both spellings, because both are in the muscle memory this editor is
    // competing with. Gated like the button: on a profile without redo the key
    // is left alone rather than taken and dropped.
    if (!session.offersRedo?.()) return;
    event.preventDefault();
    void run("重做", () => session.redo()).catch(() => {});
    return;
  }
  if (accel && event.key.toLowerCase() === "s") {
    // Without preventDefault this opens the BROWSER's save dialog, which saves
    // the page rather than the document -- an answer to the user's request that
    // is worse than no answer.
    event.preventDefault();
    void saveDocument().catch(() => {});
    return;
  }
  // The inline formats, on the keys everybody already knows.  Deliberately NOT
  // wired until 2026-08-19: under finding 059 all four of these failed on the
  // shipped engine, and binding them to the keyboard would only have copied one
  // defect onto a second path.  With 059 fixed they go through `editorAction`,
  // the same function the toolbar buttons call, so the shortcut and the button
  // cannot drift apart -- including the `enabled` it derives from the engine's
  // own state.
  if (accel && !event.shiftKey) {
    const formatAction = { b: "set-bold", i: "set-italic",
                           u: "set-underline" }[event.key.toLowerCase()];
    if (formatAction) {
      event.preventDefault();
      void editorAction(formatAction).catch(() => {});
      return;
    }
    // Ctrl+A is deliberately NOT bound.  Select-all is not one of the fifteen
    // actions, and expressing it as a geometric range -- (0,0) to the
    // document's width and height -- was tried and MEASURED on 2026-08-19:
    // `selectRange` reports success in about half a second, the engine reports
    // the selection still collapsed, and the canvas shows no selection wash at
    // all.  A shortcut that looks like it worked and selected nothing is worse
    // than no shortcut, which is the same rule that put `preventDefault` on
    // Ctrl+S.  A real one needs a select-all ACTION in the contract
    // (queue-no-select-all-action).
  }
  // FINDING 067.  Enter did nothing, and the revision counter said it worked.
  //
  // The frozen input adapter turns `beforeinput` with `insertParagraph` or
  // `insertLineBreak` into `commitText("\n")` -- a text insert of a newline --
  // and the engine's `paste` ACCEPTS that newline, does nothing with it, and
  // increments the revision anyway (measured: method "paste", revision 1 -> 2,
  // content.xml byte-identical, findings/evidence/067/).  Meanwhile the toolbar
  // buttons for both breaks work and are covered every run: only the user's
  // keyboard was broken.
  //
  // WHY HERE AND NOT AT THE ADAPTER'S COMMIT BOUNDARY.  Measured on this page:
  // a plain Enter and Shift+Enter BOTH arrive as `insertLineBreak`, because
  // this sink is a <textarea> -- `insertParagraph` is what a contenteditable
  // reports, so that branch of the adapter is dead code here.  The two keys are
  // therefore indistinguishable at `commit(text, metadata)`, and no routing
  // decision taken there can offer both breaks.  `keydown` carries `shiftKey`;
  // `InputEvent` does not, and the adapter does not listen for keydown at all.
  //
  // `preventDefault` here means the browser generates NO `beforeinput`, so the
  // adapter's branch never fires and the two paths are disjoint by
  // construction -- no ordering dependency, and none of the double-commit the
  // paste handler was measured doing when it duplicated the adapter's work.
  //
  // `isComposing` is not optional: during an IME composition Enter COMMITS the
  // composition, and preventing it there would break Chinese input -- finding
  // 050's neighbourhood, and that file is frozen so a mistake here cannot be
  // repaired there.
  //
  // Ctrl/Cmd+Enter is swallowed rather than passed on. The contract has no
  // page-break action, and letting it fall through would reproduce 067 on that
  // chord -- the same rule that put `preventDefault` on Ctrl+S and left Ctrl+A
  // unbound: offering a key that cannot dispatch is worse than offering none.
  if (event.key === "Enter" && !event.isComposing) {
    event.preventDefault();
    if (!accel) {
      void editorAction(event.shiftKey ? "insert-line-break"
                                       : "insert-paragraph-break").catch(() => {});
    }
    return;
  }
  if (accel) return;
  const action = KEY_ACTIONS[event.key];
  // `offers()`, not `gesturesFor()`: the latter answers null both for a
  // v1-shaped manifest and for an action the profile does not carry, and
  // taking the key on the second would be the "looks like it worked" trap that
  // Ctrl+A is unbound to avoid.
  if (!action || !session.offers(action)) return;
  event.preventDefault();
  void editorAction(action).catch(() => {});
});

// Cut = copy, then delete what was copied.  Two dispatches rather than one
// because the contract has no cut action; the ORDER matters, since a failed
// copy must not still remove the text.
el.sink.addEventListener("cut", (event) => {
  if (!session?.document) return;
  event.preventDefault();
  // BOTH halves inside `run`, so the delete's failure is reported with its
  // disposition like every other action.  It used to sit in a `.then` whose
  // `.catch` swallowed it, and that hid finding 063 completely: with a working
  // clipboard the copy succeeds, the delete fails, the session lands in
  // recoverable-error, and the only thing the user saw was a notice telling
  // them to restart -- no word about what had failed.  "A rejection the user
  // cannot see is a rejection nobody reports" is already written in this file,
  // three handlers down, for finding 050.
  void run("剪下", async () => {
    const copied = await session.copySelection();
    // `delete-selection` when the profile carries it.
    //
    // `delete-backward` is declared caret-only in every manifest up to v3, and
    // a cut is a range BY DEFINITION -- so the delete half is refused every
    // time and cut has been effectively copy (finding 063,
    // queue-cut-cannot-remove-text). The remedy measured out as a distinct
    // action rather than a widening: widening delete-backward's gestures would
    // have discarded the one characterisation this pair has behind it, and the
    // run that tried it hit the selection barrier instead.
    //
    // On a profile without it this falls back to today's behaviour rather than
    // to a new one: the fallback is the defect, and replacing a known defect
    // with an untested path on the day of a link is how a link acquires a
    // second cause.
    await session.action(session.offers("delete-selection")
                         ? "delete-selection" : "delete-backward", {});
    return copied;
  })
    .then((copied) => toast(`已剪下 ${copied?.codePoints ?? "?"} 字`))
    .catch(() => {});
});

el.canvas.addEventListener("pointermove", (event) => {
  if (!drag.active || !session?.document) return;
  if ((event.buttons & 1) === 0) { endDrag(event); return; }
  drag.latest = pointToTwips(event);
  void pumpDrag();
});

el.canvas.addEventListener("pointerup", endDrag);
el.canvas.addEventListener("pointercancel", () => endDrag(null));
globalThis.addEventListener("blur", () => endDrag(null));
globalThis.addEventListener("resize", () => {
  layoutCanvas();
  void renderDocument();
});

/* ------------------------------------------------------------------- boot */

// REVERTED TO e2-editor-v4 ON 2026-08-23, hours after the cutover, because the
// product path went RED on v5: the format barrier stopped advancing on a
// bulleted blank line, bold did not reach the document, and the band scan saw
// 7 bands for 9 lines. The accessibility tree was perfect on v5 -- 205 nodes,
// nine paragraphs with roles -- and that is not worth a product that cannot
// apply bold. See findings/evidence/aria-projection/ and the v5 finding.
//
// CUT OVER TO e2-editor-v7 ON 2026-08-23, and this is the first cutover where
// the pin does NOT move with the worker URL -- because the artifact did not
// move. v7 is v4's loader, wasm and worker byte for byte (`f923cfa5...` /
// `e6ee92ca...`) with one difference in the manifest: the four inline formats
// are offered for range selections as well as for a caret. No relink. That is
// what "a later profile can grant on the strength of a measurement" means, and
// this is the first time it has been used.
//
// Why: finding 078. Selected text could not be emboldened -- the manifest
// offered the inline formats for `collapsed` only, honestly, because range
// dispatch had never been characterised for them. The characterisation is now
// done: all four formats, both range shapes, the formatted text equal to the
// selected text, on this identity itself, with native LibreOffice writing the
// same shapes; and the operator confirmed it with a real mouse. Both range bits
// are granted because the engine requires both for a range it has not
// classified (granting one alone admits nothing -- measured three ways).
//
// The v5 identity is minted and archived; it is not shipped. v6 is minted and
// inert; see its SUPERSEDED.md. The two lines below still move together
// WHENEVER THE ARTIFACT MOVES: the worker URL says which profile, the pinned
// hash says which build of it, and a page that got one without the other would
// run an engine its evidence does not describe.
//
// THAT PARAGRAPH WAS ABOUT v5 AND SAT UNDER v7'S HEADING. It read "the core
// now has accessibility compiled in ... the contract gained caretParagraphText
// and documentOutline ... paragraphFresh no longer claims a successful read".
// None of it was true of v7: v7 is v4's wasm byte for byte, so no core, no
// contract field and no engine fix arrived with it. Left in place it would have
// told the next reader that this page was running an accessibility core.
// Corrected 2026-08-24 while cutting over to v8, which is where two of those
// three actually arrive.
//
// CUT OVER TO e2-editor-v8 ON 2026-08-24, and this time BOTH LINES MOVE,
// because the artifact does. `4a2710bba1ef07d9` / worker `070229cd10bda4a0`,
// from `f923cfa5aba30749` / `e6ee92ca290b7966`. The loader is unchanged
// (`c382b834aa768b91`), which is exactly why a page must not identify its
// engine by the loader.
//
// Why: finding 076. `paintTile` draws only the page and `putImageData` blits
// the whole buffer, so the tile's `malloc`'d remainder -- this process's heap,
// and this process's heap holds the user's document -- was being drawn onto a
// canvas the user can screenshot. The operator confirmed seeing it. The buffer
// is `calloc`'d now.
//
// What this link ships was MEASURED before it was taken, by preprocessing the
// product's own translation units with the product's own defines at the shipped
// commit and at the tree (`tools/what_the_link_ships.py`). Three things, not
// one, and reading the `#ifdef`s would have found only the first:
//
//   1. finding 076's `calloc`;
//   2. `refreshCaretParagraph()` returning early so `a11yParagraphFresh` is
//      false on a build where no accessibility read can succeed -- gated on a
//      RUNTIME flag, deliberately, so it is behind no `OXSDK_A11Y_*`;
//   3. 21 code lines in the worker forwarding `a11y.paragraphText` and
//      `a11y.outline`. Additive and presence-guarded, and inert here: this core
//      emits neither field and v8's manifest declares neither
//      `caretParagraphText` nor `documentOutline`, so nothing below reads them.
//
// SPEC E2-C section 11: round two's product is the v3 artifact.
//
// Hard-coded, not a query parameter.  A product page that takes its engine from
// the URL is a page whose evidence does not say which engine it measured, and
// round one bound four hashes precisely because that had been left implicit.
// The harness pages (`e2-c-d*-app.js`) do take `?profile=`; they are harnesses.
function engineFactory() {
  return createDocumentEngine({
    workerUrl: "./profiles/e2-editor-v8/sdk-worker.js",
    timeoutMs: 30000,
  });
}

function showExpired(details) {
  el.expired.style.display = "block";
  el.paper.style.display = "none";
  el.expectedHash.textContent = details?.expected ?? PINNED_WASM_SHA256;
  el.actualHash.textContent = details?.actual ?? "（manifest 沒有提供）";
  el.statePill.dataset.state = "expired";
  el.statePill.textContent = "已過期";
  for (const button of el.toolbar.querySelectorAll("button"))
    button.disabled = true;
  el.fixture.disabled = true;
  // The hidden input is unreachable once its button is disabled, but a control
  // that is only unreachable by layout is not disabled -- say it outright.
  el.file.disabled = true;
}

// The bytes are the only thing that ever differed between a bundled sample and
// a document the user chose: both end at the same `session.open({bytes, name})`.
// Splitting the fetch off is the whole of "open a real file" -- there is no
// engine side to it, which is why it does not need a link.
async function openDocument(bytes, name) {
  if (session) {
    try { await session.close(); } catch { /* a dead session must not block */ }
    session = null;
  }
  session = new NarrowEditorV2Session({
    engineFactory,
    clipboard: navigator.clipboard,
    secureContext: globalThis.isSecureContext,
    onState: updateState,
    onEvent(event) {
      if (event.event === "document-invalidated")
        queueMicrotask(() => void renderDocument());
    },
    // Finding 050 was invisible for as long as it existed because these two
    // callbacks were never wired: the input adapter rejected every commit after
    // the first, said so in its trace, and the trace went nowhere.  A rejection
    // the user cannot see is a rejection nobody reports.
    //
    // Only failures surface -- a toast per keystroke would be its own defect.
    onInputTrace(entry) {
      if (entry?.action === "composition-rejected" || entry?.status === "failed")
        toast(`輸入未送出：${entry.reason || entry.code || entry.action}`, true);
    },
    onClipboardTrace(entry) {
      if (entry?.status === "failed" || entry?.status === "rejected")
        toast(`剪貼簿未完成：${entry.code || entry.status}`, true);
    },
  });
  await session.open({ bytes, name });
  session.attachInput(el.sink);
  const actual = session.engine.manifest?.editorContract?.wasmSha256 ?? "";
  if (!actual.startsWith(PINNED_WASM_SHA256)) {
    showExpired({ expected: PINNED_WASM_SHA256, actual: actual.slice(0, 16) });
    throw Object.assign(new Error("this build is not the one this page describes"),
                        { code: "PAGE_BUILD_MISMATCH" });
  }
  documentName = name;
  el.s.doc.textContent = name;
  layoutCanvas();
  await renderDocument();
  updateGestureAffordance();
}

async function openFixture(id) {
  const name = `${id}.odt`;
  const response = await fetch(`./e1-fixtures/${name}`, { cache: "no-cache" });
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  await openDocument(await response.arrayBuffer(), name);
}

el.fixture.addEventListener("change", () => {
  void openFixture(el.fixture.value)
    .catch((error) => toast(describeError(error), true));
});

el.openFile.addEventListener("click", () => el.file.click());

el.clearFormat.addEventListener("click", () => {
  if (!session?.document) return;
  void clearInlineFormatting().catch(() => {});
});

el.file.addEventListener("change", () => {
  const file = el.file.files?.[0];
  // Clearing the input is what lets the same file be re-opened; without it a
  // second pick of the same path fires no change event at all.
  el.file.value = "";
  if (!file) return;
  // The fixture select must stop naming a document that is no longer open --
  // a control that reports the wrong document is the shape of finding 054.
  el.fixture.value = "";
  void file.arrayBuffer()
    .then((bytes) => openDocument(bytes, file.name))
    .then(() => toast(`已開啟 ${file.name}`))
    .catch((error) => toast(describeError(error), true));
});

void (async () => {
  el.pinnedHash.textContent = PINNED_WASM_SHA256;
  if (!globalThis.crossOriginIsolated)
    toast("此頁需要 cross-origin isolation：請以 web/serve.py 提供", true);
  const manifest = await fetch("./e1-fixtures/manifest.json", { cache: "no-cache" })
    .then((value) => value.json());
  el.fixture.replaceChildren(...manifest.fixtures.map((fixture) => {
    const option = document.createElement("option");
    option.value = fixture.id;
    option.textContent = fixture.id;
    return option;
  }));
  el.fixture.value = "list-contexts";
  await openFixture(el.fixture.value);
  toast("點一下放游標，或拖曳選一段，再按動作");
})().catch((error) => {
  if (error?.code === "PAGE_BUILD_MISMATCH") return;
  el.statePill.dataset.state = "stopped";
  el.statePill.textContent = "錯誤";
  toast(describeError(error), true);
});
