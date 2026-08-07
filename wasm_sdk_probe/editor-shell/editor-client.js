import { DocumentSdkError } from "../sdk/document-sdk.js";

export const EDITOR_V1_ACTIONS = Object.freeze([
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

const ACTION_SET = new Set(EDITOR_V1_ACTIONS);
const MOVE_ACTIONS = new Set(["move-character-left", "move-character-right"]);
const DELETE_ACTIONS = new Set(["delete-backward", "delete-forward"]);
const FORMAT_ACTIONS = new Set([
  "set-bold", "set-italic", "set-underline", "set-strikethrough",
]);
const MUTATION_ACTIONS = new Set([
  ...DELETE_ACTIONS,
  "insert-paragraph-break",
  "insert-line-break",
  ...FORMAT_ACTIONS,
]);

function unsignedRevision(value, label = "expectedRevision") {
  if (!Number.isInteger(value) || value < 0 || value > 0xffffffff)
    throw new DocumentSdkError("INVALID_ARGUMENT", `${label} must be an unsigned 32-bit integer`);
  return value;
}

function invalidResult(message, details = {}) {
  return new DocumentSdkError("EDITOR_RESULT_INVALID", message, details);
}

export class NarrowEditorClient {
  constructor(document) {
    if (!document || typeof document._assertUsable !== "function" || !document._engine)
      throw new TypeError("NarrowEditorClient requires a DocumentHandle");
    this.document = document;
  }

  _assertAvailable() {
    this.document._assertUsable();
    const manifest = this.document._engine.manifest;
    if (!manifest?.capabilities?.includes("narrow-editor-v1")
        || manifest?.editorContract?.version !== 1) {
      throw new DocumentSdkError(
        "UNSUPPORTED_OPERATION",
        "the active profile does not provide narrow-editor-v1",
      );
    }
  }

  _validateResult(action, expectedRevision, result) {
    if (!result || result.action !== action
        || result.beforeRevision !== expectedRevision
        || !Number.isInteger(result.revision)
        || result.revision < 0
        || !result.state) {
      throw invalidResult("editor action returned a malformed or mismatched result", {
        action, expectedRevision, result,
      });
    }
    if (MOVE_ACTIONS.has(action)) {
      if (result.revision !== expectedRevision || result.changed !== false
          || !String(result.completion || "").startsWith("documented-callback-")) {
        throw invalidResult("character movement did not satisfy its typed postcondition", { result });
      }
    } else if (DELETE_ACTIONS.has(action)) {
      if (result.completion !== "verified-selection-delete"
          || result.changed !== true || result.revision !== expectedRevision + 1) {
        throw invalidResult("delete did not satisfy the verified-selection postcondition", { result });
      }
    } else if (MUTATION_ACTIONS.has(action)) {
      // `documented-state-noop` was accepted here until 2026-08-06.  Finding
      // 022 showed the engine could only produce it from a stale cache, so it
      // was removed engine-side; accepting it here as well would let the same
      // silent no-op return unnoticed.  Every mutation must now change the
      // document and say so.
      const validChange = result.changed === true
        && result.revision === expectedRevision + 1
        && result.completion === "uno-command-result";
      if (!validChange)
        throw invalidResult("editor mutation did not satisfy its revision postcondition", { result });
    }
  }

  async action(action, options = {}) {
    this._assertAvailable();
    if (!ACTION_SET.has(action)) {
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
      options.expectedRevision ?? this.document.revision,
    );
    const result = await this.document._engine._request("editorActionV1", {
      documentHandle: this.document.handle,
      expectedRevision,
      action,
      extendSelection,
      enabled,
    }, options);
    this._validateResult(action, expectedRevision, result);
    this.document.revision = result.revision;
    return result;
  }

  moveCharacter(direction, options = {}) {
    if (direction !== "left" && direction !== "right")
      throw new DocumentSdkError("INVALID_ARGUMENT", "direction must be left or right");
    return this.action(`move-character-${direction}`, options);
  }

  delete(direction, options = {}) {
    if (direction !== "backward" && direction !== "forward") {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT", "delete direction must be backward or forward",
      );
    }
    return this.action(`delete-${direction}`, options);
  }

  insertBreak(kind, options = {}) {
    if (kind !== "paragraph" && kind !== "line")
      throw new DocumentSdkError("INVALID_ARGUMENT", "break kind must be paragraph or line");
    return this.action(`insert-${kind}-break`, options);
  }

  setInlineFormat(format, enabled, options = {}) {
    if (!FORMAT_ACTIONS.has(`set-${format}`)) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT", "format must be bold, italic, underline or strikethrough",
      );
    }
    return this.action(`set-${format}`, { ...options, enabled });
  }

  /**
   * Select a range between two document points (SPEC E1-D).
   *
   * The completion the engine returns is deliberately *not* trusted as proof a
   * selection exists -- SPEC E1-D section 2.1 recorded the other selection path
   * reporting exactly that while selecting nothing, which is the finding 022
   * shape.  The postcondition here is the selection readback: whatever this
   * returns has been read back out of the engine after the fact.
   *
   * Selecting nothing is a legitimate outcome (an empty range, or a drag in the
   * margin), reported as `{ collapsed: true, text: "" }`.  It is not an error
   * and callers must not retry it into one.
   */
  async selectRange(start, end, options = {}) {
    this._assertAvailable();
    const points = { startXTwips: start?.xTwips, startYTwips: start?.yTwips,
      endXTwips: end?.xTwips, endYTwips: end?.yTwips };
    for (const [name, value] of Object.entries(points)) {
      if (!Number.isInteger(value) || value < 0) {
        throw new DocumentSdkError(
          "INVALID_ARGUMENT", `${name} must be a non-negative integer in twips`,
        );
      }
    }
    await this.document._engine._request("editorSelectRangeV1", {
      documentHandle: this.document.handle, ...points,
    }, options);

    const state = await this.getState(options);
    const rectangles = state.selection?.rectangles || [];
    const collapsed = state.selection?.collapsed !== false;
    if (collapsed !== (rectangles.length === 0)) {
      throw invalidResult("selection readback disagrees with itself", {
        collapsed, rectangles: rectangles.length,
      });
    }
    if (!collapsed && state.selectionType !== "text") {
      throw invalidResult("a non-collapsed selection did not read back as text", {
        selectionType: state.selectionType,
      });
    }
    return {
      collapsed,
      text: collapsed ? "" : (state.selectionText ?? ""),
      rectangles,
      caret: state.caret ?? null,
      revision: state.revision,
    };
  }

  async getState(options = {}) {
    this._assertAvailable();
    const result = await this.document._engine._request("editorGetStateV1", {
      documentHandle: this.document.handle,
    }, options);
    if (!result || result.documentHandle !== this.document.handle
        || !Number.isInteger(result.revision)
        || !result.selection || !result.format) {
      throw invalidResult("editor state result is malformed", { result });
    }
    this.document.revision = result.revision;
    return result;
  }
}
