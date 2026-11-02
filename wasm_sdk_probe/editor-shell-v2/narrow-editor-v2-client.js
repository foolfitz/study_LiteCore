// SPEC E2-C 2.2: the product client for the v2 profile -- all fifteen actions.
//
// The v2 manifest declares fifteen and the worker's `editorActionV2` accepts
// fifteen, but until this file existed no shell could reach ten of them:
// editor-shell/editor-client.js gates on `narrow-editor-v1` AND
// `editorContract.version === 1`, and paragraph-editor-client.js allowlists
// only the five paragraph actions.  So the manifest promised a surface no host
// could use.  Three ways out were on the table; this is the cheapest one that
// throws nothing away:
//
//   * editing editor-shell/editor-client.js -- refused, it is hash-bound by
//     E1-C's shell bundle and editing it unbinds E1_GO_ODT_EDITOR;
//   * removing the ten from the manifest -- refused, that is a rebuild, a new
//     artifact hash, and 132 measured runs losing the thing they are bound to;
//   * shipping two profiles -- refused, a document is open in one engine.
//
// The five paragraph actions are DELEGATED to ParagraphEditorClient rather than
// reimplemented: route C's rules (`changed: null`, verified-format-readback)
// exist in exactly one place and stay there.  The ten inherited actions are
// validated here, and narrow-editor-v2-client.test.mjs holds that validation
// against editor-shell/editor-client.js case by case -- this family's only
// recorded drift (underline and strikethrough reaching the runtime but not the
// declaration) survived two shipped artifacts because nothing compared them.

import { DocumentSdkError } from "../sdk/document-sdk.js";
import { ParagraphEditorClient, EDITOR_ALIGN_ACTIONS, EDITOR_TOGGLE_ACTIONS, EDITOR_V2_PARAGRAPH_ACTIONS }
  from "./paragraph-editor-client.js";

/**
 * v1's ten, carried into the v2 contract unchanged -- same names, same ids,
 * same postconditions.  "Inherited" is literal: SPEC E2-B 5.11 kept the v1 enum
 * untouched and gave v2 its own five, so these ten are the same engine path
 * reached through a different entry point.
 */
export const EDITOR_V2_INHERITED_ACTIONS = Object.freeze([
  "move-character-left",
  "move-character-right",
  "delete-backward",
  "delete-forward",
  "insert-paragraph-break",
  "insert-line-break",
  "set-bold",
  "set-italic",
  "set-underline",
  "set-strikethrough",
]);

// ABI 4 appends these under the e2-editor-v4 successor identity.  The four
// movements are a contract surface over behaviour the engine already had -- it
// has mapped them to arrow/Home/End key codes since the discovery ABI -- and
// the fifth is the one new behaviour.
//
// The v4 contract carries a SIXTH id that is not named here and must not be:
// its gesture list is empty, so the engine refuses it every time, and a client
// that names an action the engine always refuses is a client offering a control
// that cannot work.  It is withheld in the manifest rather than absent from the
// binary, which is what makes granting it later a measurement instead of a
// relink.  (2026-10-30: that measurement was made -- e2-editor-v26 grants it,
// and it is named below in EDITOR_SELECT_ALL_ACTIONS, not here.)
export const EDITOR_V3_APPENDED_ACTIONS = Object.freeze([
  "move-line-up",
  "move-line-down",
  "move-line-home",
  "move-line-end",
  "delete-selection",
]);

// ABI 5 (SPEC-M3-link-batch-v21 4.1) appends two under the e2-editor-v21
// successor identity: finding 142's document moves, wire ids 22 and 23.  The
// fourth append, so V4 -- the enums in src/editor_api.h count appends, not ABI
// versions (V3 is ABI 4's).  Posted as Ctrl+Home / Ctrl+End by the engine with
// `mutation = false`, the six moves' route, so they take the six moves'
// postcondition below.  Both are offered for `collapsed` only; on a range the
// page clicks at the point first (finding 129's moveFromPoint).
export const EDITOR_V4_APPENDED_ACTIONS = Object.freeze([
  "move-document-start",
  "move-document-end",
]);

export const EDITOR_V2_ACTIONS = Object.freeze([
  ...EDITOR_V2_INHERITED_ACTIONS,
  ...EDITOR_V2_PARAGRAPH_ACTIONS,
]);

export const EDITOR_V3_ACTIONS = Object.freeze([
  ...EDITOR_V2_ACTIONS,
  ...EDITOR_V3_APPENDED_ACTIONS,
]);

export const EDITOR_V4_ACTIONS = Object.freeze([
  ...EDITOR_V3_ACTIONS,
  ...EDITOR_V4_APPENDED_ACTIONS,
]);

// SPEC-M3-select-all-v26 4.3.  Select-all (wire id 21) is not an append -- the
// engine has carried it since ABI 4, withheld -- but a GRANT: e2-editor-v26's
// manifest gives it the three gestures on the strength of a measurement
// (findings/evidence/select-all-v25/).  Its own list, so V3 and V4 keep
// meaning "what each ABI appended".  EDITOR_ACCEPTED_ACTIONS is the ONE list of
// everything this client sends: the session's allowlist and the D13 census read
// it, so a later grant cannot reach one of them and not the other (review
// 2026-10-30 items 1 and 3).  Offered only where a manifest grants it
// (`offers`), like every other action.
export const EDITOR_SELECT_ALL_ACTIONS = Object.freeze(["select-all"]);

export const EDITOR_ACCEPTED_ACTIONS = Object.freeze([
  ...EDITOR_V4_ACTIONS,
  ...EDITOR_SELECT_ALL_ACTIONS,
  ...EDITOR_ALIGN_ACTIONS,
  ...EDITOR_TOGGLE_ACTIONS,
]);

const INHERITED = new Set(EDITOR_V2_INHERITED_ACTIONS);
const APPENDED = new Set([...EDITOR_V3_APPENDED_ACTIONS, ...EDITOR_V4_APPENDED_ACTIONS,
                          ...EDITOR_SELECT_ALL_ACTIONS]);
const PARAGRAPH = new Set([...EDITOR_V2_PARAGRAPH_ACTIONS, ...EDITOR_ALIGN_ACTIONS, ...EDITOR_TOGGLE_ACTIONS]);
const MOVE_ACTIONS = new Set(["move-character-left", "move-character-right"]);
// Movement by line takes the SAME postcondition as movement by character --
// revision unchanged, `changed: false`, a documented callback -- because it
// takes the same route through the engine: a posted key event with
// `mutation = false`, not a UNO dispatch.  Sharing the postcondition is the
// point: these inherit one somebody measured instead of getting a new one
// nobody has.
//
// Older ABIs permit extension only for character moves. ABI6 adds extension
// on these existing IDs only when the active contract grants it; the move
// postcondition is unchanged.
const LINE_MOVE_ACTIONS = new Set([
  "move-line-up", "move-line-down", "move-line-home", "move-line-end",
]);
// SPEC-M3-link-batch-v21 4.1: the same non-mutation move postcondition,
// and at a document boundary (where Ctrl+Home is silent,
// measured natively) the same `verified-move-readback` completion.  Not in
// MOVE_ACTIONS: document extension remains refused, including on ABI6.
// ABI6's ordered engine completes from its first poll rather than the legacy
// 250ms readback; the accepted completion names and postcondition stay the same.
const DOCUMENT_MOVE_ACTIONS = new Set(["move-document-start", "move-document-end"]);
// Select-all takes the moves' postcondition for the moves' reason: the engine
// posts it as a key (Key::A | Mod1) with `mutation = false`, and measured on
// v25 it answers `documented-callback-visible-cursor` from a caret and
// `verified-move-readback` from a range or a blank document, revision held,
// `changed: false` (SPEC-M3-select-all-v26 4.3).  NOT in MOVE_ACTIONS: that set
// decides whether `extendSelection` is legal, and select-all never extends.
const SELECT_ALL_ACTIONS = new Set(EDITOR_SELECT_ALL_ACTIONS);
// FINDING 096.  The two completions a movement is allowed to come back with,
// and the SECOND one is why this is a function rather than a prefix test.
//
// `documented-callback-*` says core broadcast the cursor callback and the
// engine correlated it.  `verified-move-readback` says the engine's own
// deadline fired and it answered from a readback of where the caret actually
// is -- which is what a movement at a document boundary produces, because
// there is nothing to move to, so core broadcasts nothing and the callback
// never comes (findings/evidence/096/RESULT-engine-side.md: zero id-1 and
// zero id-2 in the window, 20 of 20, on two engines, while the press one
// earlier produced one in 37-39 ms).
//
// WHY THIS HAD TO WIDEN AT ALL, said plainly: with the prefix test unchanged,
// the engine's fix would have made things WORSE rather than better.  The
// boundary press would be answered in 250 ms, this postcondition would reject
// the answer as EDITOR_RESULT_INVALID, and that code is in the base session's
// RECOVERY_ERRORS -- so the session would die exactly as it does today, just
// 29.75 seconds sooner.  A fix in one layer that the next layer converts back
// into the same failure is the 2026-08-22 shape, and it is the reason the
// decision document required this to be settled WITH the engine change and
// not after it.
//
// WHAT IS NOT RELAXED.  Both the other clauses stand: the revision must be the
// one the caller started from and `changed` must be false.  Those are the
// claims about the DOCUMENT, and the readback path makes them no weaker -- it
// reports where the caret is, and it never reports that a move happened.
const MOVE_COMPLETIONS = (completion) =>
  String(completion || "").startsWith("documented-callback-")
  || completion === "verified-move-readback";

const DELETE_ACTIONS = new Set(["delete-backward", "delete-forward"]);
// SPEC-M3-paragraph-merge 3.3 and 10.1(e).  At a paragraph boundary an engine
// built with OXSDK_MERGE_KEY_UNDO presses the user's own key and proves what it
// did from the .uno:Undo payload; it completes with `verified-key-undo` and a
// `keyUndo` record.  The check here is STRUCTURAL on purpose.  By the time this
// reply exists the key has already changed the document, and a rejection is
// EDITOR_RESULT_INVALID -> a recovery error -> rollback to an older checkpoint
// (editor-shell/editor-session.js RECOVERY_ERRORS) -- finding 109's loss again.
// So nothing here may depend on Writer's strings: an empty undo comment is not
// a reason to throw away what the user typed.  Engines without the macro never
// send this completion, so accepting it changes nothing for them.
const DELETE_COMPLETION = (result) =>
  result.completion === "verified-selection-delete"
  || (result.completion === "verified-key-undo"
      && result.keyUndo !== null && typeof result.keyUndo === "object"
      && Number.isInteger(result.keyUndo.actionsAfter)
      && result.keyUndo.actionsAfter >= 1);
const FORMAT_ACTIONS = new Set(["set-bold", "set-italic", "set-underline",
  "set-strikethrough"]);
// delete-selection belongs here and NOT in DELETE_ACTIONS, which is the
// distinction the postconditions turn on: DELETE_ACTIONS are the two
// caret-relative deletes that go through the selection barrier and complete
// with `verified-selection-delete`.  delete-selection dispatches .uno:Delete on
// a selection the caller already made, so it completes like any other UNO
// mutation.  Filing it with the barrier deletes would assert a completion
// string it never produces.
const MUTATION_ACTIONS = new Set([
  ...DELETE_ACTIONS, "insert-paragraph-break", "insert-line-break",
  ...FORMAT_ACTIONS, "delete-selection",
]);

/**
 * Which postcondition an action's reply is judged by, or null when it has none.
 *
 * SPEC-M3-link-batch-v21 9.7 / 11.1 D13: a CLOSED classification.  Every action
 * this client sends has exactly one class -- "move" (revision unchanged,
 * `changed: false`, a documented callback or the readback), "delete" (the
 * barrier deletes and C's no-op), "mutation" (a UNO command, revision + 1) or
 * "paragraph" (route C, judged by ParagraphEditorClient) -- and
 * `_validateInherited` refuses a reply for anything that has none, instead of
 * accepting it by falling off the end of its branches.  Exported so a test can
 * hold the session's BOUNDARY_CAPABLE_MOVES to the "move" class.
 */
export function postconditionClassOf(action) {
  if (MOVE_ACTIONS.has(action) || LINE_MOVE_ACTIONS.has(action)
      || DOCUMENT_MOVE_ACTIONS.has(action) || SELECT_ALL_ACTIONS.has(action)) return "move";
  if (DELETE_ACTIONS.has(action)) return "delete";
  if (MUTATION_ACTIONS.has(action)) return "mutation";
  if (PARAGRAPH.has(action)) return "paragraph";
  return null;
}

function unsignedRevision(value, label = "expectedRevision") {
  if (!Number.isInteger(value) || value < 0 || value > 0xffffffff) {
    throw new DocumentSdkError(
      "INVALID_ARGUMENT", `${label} must be an unsigned 32-bit integer`);
  }
  return value;
}

function invalidResult(message, details = {}) {
  return new DocumentSdkError("EDITOR_RESULT_INVALID", message, details);
}

export class NarrowEditorV2Client {
  constructor(document) {
    if (!document || typeof document._assertUsable !== "function"
        || !document._engine)
      throw new TypeError("NarrowEditorV2Client requires a DocumentHandle");
    this.document = document;
    this.paragraph = new ParagraphEditorClient(document);
  }

  _assertAvailable() {
    this.document._assertUsable();
    const manifest = this.document._engine.manifest;
    if (!manifest?.capabilities?.includes("narrow-editor-v2")
        || manifest?.editorContract?.version !== 2) {
      throw new DocumentSdkError(
        "UNSUPPORTED_OPERATION",
        "the active profile does not provide narrow-editor-v2",
      );
    }
  }

  gesturesFor(action) {
    const spec = this.document._engine.manifest?.editorContract?.actions?.[action];
    return Array.isArray(spec?.gestures) ? spec.gestures : null;
  }

  /** ABI6's six selection moves, for the actual advertised gesture only. */
  offersSelectionMove(action, gesture) {
    const contract = this.document._engine.manifest?.editorContract;
    return contract?.abiVersion === 6
      && (MOVE_ACTIONS.has(action) || LINE_MOVE_ACTIONS.has(action))
      && ["collapsed", "range-single", "range-cross"].includes(gesture)
      && this.gesturesFor(action)?.includes(gesture) === true
      && !this.limitsFor(action).includes("no-extend-selection");
  }

  /**
   * Whether this profile offers the action at all.
   *
   * `gesturesFor` cannot answer this and must not be used for it: it returns
   * `null` both for a v1-shaped manifest (a bare name list, no gesture map)
   * and for an action this profile simply does not carry.  Treating those
   * alike in either direction is a defect -- read as "offered" it binds a
   * control the engine refuses every time, and read as "withheld" it disables
   * every control on a v1 profile.
   *
   * An action PRESENT with an empty gesture list is withheld on purpose (the
   * manifest ships it dark), so it is not offered either.  Same rule as the
   * worker's own `manifestAllowsAction`, which is the authoritative one -- this
   * is the client-side half, and it exists so the UI can decline to draw a
   * control rather than draw one that always fails.
   */
  offers(action) {
    const actions = this.document._engine.manifest?.editorContract?.actions;
    if (!actions) return true;
    if (Array.isArray(actions)) return actions.includes(action);
    const spec = actions[action];
    if (!spec) return false;
    return !Array.isArray(spec.gestures) || spec.gestures.length > 0;
  }

  /**
   * Whether this profile carries `redo`.
   *
   * Deliberately NOT expressed through `offers()`: redo is not an editor
   * action, it has no wire id and no gesture, and it is declared on the
   * contract as `redo: "document-sdk-redo"` -- the same shape `undo` has.
   * Asking the action map about it would answer "absent" on every profile,
   * including the ones that have it.
   *
   * The gate matters because `oxsdk_document_redo` is a COMPILED EXPORT: on a
   * profile whose binary predates it the call does not fail politely, it
   * reaches for a symbol that is not there.
   */
  offersRedo() {
    const contract = this.document._engine.manifest?.editorContract;
    if (!contract) return false;
    return contract.redo === "document-sdk-redo";
  }

  /**
   * Whether this profile carries the focused paragraph's TEXT.
   *
   * Declared exactly like `redo` above, and for the same reason: the field is
   * emitted only by an engine built with OXSDK_A11Y_PARAGRAPH_TEXT, so a host
   * that just read `caretParagraph.text` could not tell "this profile does not
   * carry it" from "this paragraph is empty".  For roadmap 3.4's projection
   * that difference is the whole of its honesty: an empty document region
   * announces to a screen reader as "document, blank", which is a confident
   * wrong answer about the user's file.
   */
  offersCaretParagraphText() {
    const contract = this.document._engine.manifest?.editorContract;
    if (!contract) return false;
    return contract.caretParagraphText === "focused-paragraph-text";
  }

  /** Whether this profile carries the document's structure. Same shape, same
   * reason: an empty structure region and an absent one are different claims,
   * and only one of them is safe to announce. */
  offersDocumentOutline() {
    const contract = this.document._engine.manifest?.editorContract;
    if (!contract) return false;
    return contract.documentOutline === "accessible-document-outline";
  }

  /**
   * Whether this profile carries `page-rectangles` (SPEC-M3-link-batch 10.8,
   * S-11).  Declared exactly like `redo` above and for the same reason: it is
   * a compiled document-level export, not an action, so the action map can
   * never answer for it -- `offers("page-rectangles")` is false everywhere.
   */
  offersPageRectangles() {
    const contract = this.document._engine.manifest?.editorContract;
    if (!contract) return false;
    return contract.pageRectangles === "document-sdk-page-rectangles";
  }

  /**
   * Whether this profile carries the Markdown paste (SPEC-M3-link-batch-v21
   * 4.2).  Read from the contract like page rectangles: a compiled
   * document-level export, never an action -- `offers("paste-markdown")` is
   * false everywhere.
   */
  offersPasteMarkdown() {
    const contract = this.document._engine.manifest?.editorContract;
    if (!contract) return false;
    return contract.pasteMarkdown === "document-sdk-paste-markdown";
  }

  limitsFor(action) {
    const spec = this.document._engine.manifest?.editorContract?.actions?.[action];
    return Array.isArray(spec?.limits) ? spec.limits : [];
  }

  // The ten keep v1's postconditions verbatim.  Relaxing them here would be the
  // one thing SPEC E2-B 5.6 forbids: route C's `changed: null` is right for the
  // five because the engine stopped reading the precondition for them, and
  // accepting the same shape for delete would let finding 022's silent no-op
  // back in through the new door.
  _validateInherited(action, expectedRevision, result) {
    if (!result || result.action !== action
        || result.beforeRevision !== expectedRevision
        || !Number.isInteger(result.revision)
        || result.revision < 0
        || !result.state) {
      throw invalidResult(
        "editor action returned a malformed or mismatched result",
        { action, expectedRevision, result });
    }
    const postcondition = postconditionClassOf(action);
    if (postcondition === "move") {
      if (result.revision !== expectedRevision || result.changed !== false
          || !MOVE_COMPLETIONS(result.completion)) {
        throw invalidResult(
          "character movement did not satisfy its typed postcondition",
          { result });
      }
    } else if (postcondition === "delete") {
      // SPEC-M3-link-batch 10.5 (ruling 2 condition 8): C's second exit.  A
      // caret-relative delete at a document boundary whose K1 selected
      // nothing inside the engine's window completes as
      // `verified-boundary-noop` with `changed: false` and the revision
      // UNCHANGED.  Those two are the claims about the document and they are
      // REQUIRED, not relaxed: the same completion claiming a change, or an
      // advanced revision, is a malformed reply (boundary-noop.test.mjs, the
      // red cases).  Engines without OXSDK_E2_V20_LINK_BATCH never send it,
      // so accepting it changes nothing for them.
      const boundaryNoop = result.completion === "verified-boundary-noop"
        && result.changed === false
        && result.revision === expectedRevision;
      const verifiedDelete = DELETE_COMPLETION(result)
        && result.changed === true
        && result.revision === expectedRevision + 1;
      if (!boundaryNoop && !verifiedDelete) {
        throw invalidResult(
          "delete did not satisfy the verified-selection postcondition",
          { result });
      }
    } else if (postcondition === "mutation") {
      const validChange = result.changed === true
        && result.revision === expectedRevision + 1
        && result.completion === "uno-command-result";
      if (!validChange) {
        throw invalidResult(
          "editor mutation did not satisfy its revision postcondition",
          { result });
      }
    } else {
      // SPEC-M3-link-batch-v21 9.7 (opus S3): no class, no acceptance.  Until
      // now an action in none of the sets above fell off the end and its reply
      // was accepted unjudged -- so an action appended to the accepted list and
      // forgotten here would have been believed whatever it said.
      throw invalidResult(
        `no inherited postcondition applies to ${String(action)}`, { action, result });
    }
  }

  async action(action, options = {}) {
    if (PARAGRAPH.has(action)) return this.paragraph.action(action, options);

    this._assertAvailable();
    if (!INHERITED.has(action) && !APPENDED.has(action)) {
      throw new DocumentSdkError(
        "EDITOR_ACTION_UNSUPPORTED",
        `unsupported narrow editor action: ${String(action)}`,
      );
    }
    const extendSelection = options.extendSelection ?? false;
    const lineExtension = LINE_MOVE_ACTIONS.has(action)
      && ["collapsed", "range-single", "range-cross"]
        .some((gesture) => this.offersSelectionMove(action, gesture));
    if (typeof extendSelection !== "boolean"
        || (!MOVE_ACTIONS.has(action) && !lineExtension && extendSelection)) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        this.document._engine.manifest?.editorContract?.abiVersion === 6
          ? "extendSelection requires character movement or an advertised ABI6 line move"
          : "extendSelection is a boolean restricted to character movement",
      );
    }
    const enabled = FORMAT_ACTIONS.has(action) ? options.enabled : false;
    if (FORMAT_ACTIONS.has(action) && typeof enabled !== "boolean") {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "the inline format actions require an explicit enabled boolean",
      );
    }
    if (!FORMAT_ACTIONS.has(action) && options.enabled !== undefined) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "enabled is restricted to the inline format actions",
      );
    }
    const expectedRevision = unsignedRevision(
      options.expectedRevision ?? this.document.revision);
    const result = await this.document._engine._request("editorActionV2", {
      documentHandle: this.document.handle,
      expectedRevision,
      action,
      extendSelection,
      enabled,
    }, options);
    this._validateInherited(action, expectedRevision, result);
    this.document.revision = result.revision;
    return result;
  }

  moveLine(direction, options = {}) {
    if (!LINE_MOVE_ACTIONS.has(`move-line-${direction}`)) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT", "direction must be up, down, home or end");
    }
    return this.action(`move-line-${direction}`, options);
  }

  // The caller makes the selection; this removes it.  There is no arity here
  // and no direction: an action named for a selection that ran without one
  // would be delete-backward wearing a different name, which is why the v4
  // manifest withholds the collapsed gesture from it.
  deleteSelection(options = {}) {
    return this.action("delete-selection", options);
  }

  moveCharacter(direction, options = {}) {
    if (direction !== "left" && direction !== "right") {
      throw new DocumentSdkError("INVALID_ARGUMENT",
                                 "direction must be left or right");
    }
    return this.action(`move-character-${direction}`, options);
  }

  delete(direction, options = {}) {
    if (direction !== "backward" && direction !== "forward") {
      throw new DocumentSdkError("INVALID_ARGUMENT",
                                 "delete direction must be backward or forward");
    }
    return this.action(`delete-${direction}`, options);
  }

  insertBreak(kind, options = {}) {
    if (kind !== "paragraph" && kind !== "line") {
      throw new DocumentSdkError("INVALID_ARGUMENT",
                                 "break kind must be paragraph or line");
    }
    return this.action(`insert-${kind}-break`, options);
  }

  setInlineFormat(format, enabled, options = {}) {
    if (!FORMAT_ACTIONS.has(`set-${format}`)) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "format must be bold, italic, underline or strikethrough");
    }
    return this.action(`set-${format}`, { ...options, enabled });
  }

  // Delegated, not reimplemented -- see the header.
  setList(kind, options = {}) { return this.paragraph.setList(kind, options); }

  setParagraphStyle(style, options = {}) {
    return this.paragraph.setParagraphStyle(style, options);
  }

  getState(options = {}) { return this.paragraph.getState(options); }

  /** Finding 140: the engine's own answer to a click (see ParagraphEditorClient). */
  placeCaret(xTwips, yTwips, options = {}) { return this.paragraph.placeCaret(xTwips, yTwips, options); }

  selectRange(start, end, options = {}) {
    return this.paragraph.selectRange(start, end, options);
  }
}
