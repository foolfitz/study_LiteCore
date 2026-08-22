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
import { ParagraphEditorClient, EDITOR_V2_PARAGRAPH_ACTIONS }
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
// relink.
export const EDITOR_V3_APPENDED_ACTIONS = Object.freeze([
  "move-line-up",
  "move-line-down",
  "move-line-home",
  "move-line-end",
  "delete-selection",
]);

export const EDITOR_V2_ACTIONS = Object.freeze([
  ...EDITOR_V2_INHERITED_ACTIONS,
  ...EDITOR_V2_PARAGRAPH_ACTIONS,
]);

export const EDITOR_V3_ACTIONS = Object.freeze([
  ...EDITOR_V2_ACTIONS,
  ...EDITOR_V3_APPENDED_ACTIONS,
]);

const INHERITED = new Set(EDITOR_V2_INHERITED_ACTIONS);
const APPENDED = new Set(EDITOR_V3_APPENDED_ACTIONS);
const PARAGRAPH = new Set(EDITOR_V2_PARAGRAPH_ACTIONS);
const MOVE_ACTIONS = new Set(["move-character-left", "move-character-right"]);
// Movement by line takes the SAME postcondition as movement by character --
// revision unchanged, `changed: false`, a documented callback -- because it
// takes the same route through the engine: a posted key event with
// `mutation = false`, not a UNO dispatch.  Sharing the postcondition is the
// point: these inherit one somebody measured instead of getting a new one
// nobody has.
//
// They are NOT in MOVE_ACTIONS, and that is deliberate rather than an
// oversight: MOVE_ACTIONS is also what permits `extendSelection`, and the ABI
// refuses that flag for anything but the two character moves
// (editor_api.cpp:159).  A shift+Up that the client accepts and the engine
// rejects is worse than one the client refuses.
const LINE_MOVE_ACTIONS = new Set([
  "move-line-up", "move-line-down", "move-line-home", "move-line-end",
]);
const DELETE_ACTIONS = new Set(["delete-backward", "delete-forward"]);
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
    if (MOVE_ACTIONS.has(action) || LINE_MOVE_ACTIONS.has(action)) {
      if (result.revision !== expectedRevision || result.changed !== false
          || !String(result.completion || "").startsWith("documented-callback-")) {
        throw invalidResult(
          "character movement did not satisfy its typed postcondition",
          { result });
      }
    } else if (DELETE_ACTIONS.has(action)) {
      if (result.completion !== "verified-selection-delete"
          || result.changed !== true
          || result.revision !== expectedRevision + 1) {
        throw invalidResult(
          "delete did not satisfy the verified-selection postcondition",
          { result });
      }
    } else if (MUTATION_ACTIONS.has(action)) {
      const validChange = result.changed === true
        && result.revision === expectedRevision + 1
        && result.completion === "uno-command-result";
      if (!validChange) {
        throw invalidResult(
          "editor mutation did not satisfy its revision postcondition",
          { result });
      }
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
    if (typeof extendSelection !== "boolean"
        || (!MOVE_ACTIONS.has(action) && extendSelection)) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "extendSelection is a boolean restricted to character movement",
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

  selectRange(start, end, options = {}) {
    return this.paragraph.selectRange(start, end, options);
  }
}
