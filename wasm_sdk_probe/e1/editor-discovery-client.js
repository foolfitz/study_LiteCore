import { DocumentSdkError } from "../sdk/document-sdk.js";

export const EDITOR_DISCOVERY_ACTIONS = Object.freeze([
  "move-character-left",
  "move-character-right",
  "move-line-up",
  "move-line-down",
  "move-line-home",
  "move-line-end",
  "delete-backward",
  "delete-forward",
  "insert-paragraph-break",
  "insert-line-break",
  "undo",
  "redo",
  "set-bold",
  "set-italic",
  "set-paragraph-body",
  "set-paragraph-heading",
  "set-list-none",
  "set-list-unordered",
  "set-list-ordered",
]);

export const EDITOR_DISCOVERY_SELECTION_METHODS = Object.freeze([
  "mouse-drag",
  "text-handles-unstable",
  "selection-reset-unstable",
]);

const ACTION_SET = new Set(EDITOR_DISCOVERY_ACTIONS);
const MOVE_ACTIONS = new Set(EDITOR_DISCOVERY_ACTIONS.slice(0, 6));
const DELETE_ACTIONS = new Set(["delete-backward", "delete-forward"]);
const BOOLEAN_OPTION_ACTIONS = new Set(["set-bold", "set-italic"]);
const SELECTION_METHOD_SET = new Set(EDITOR_DISCOVERY_SELECTION_METHODS);

function integerTwips(value, name) {
  if (!Number.isInteger(value) || value < 0)
    throw new DocumentSdkError("INVALID_ARGUMENT", `${name} must be non-negative integer twips`);
  return value;
}

export class EditorDiscoveryClient {
  constructor(documentHandle) {
    if (!documentHandle?._engine || typeof documentHandle._assertUsable !== "function") {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "EditorDiscoveryClient requires a Document SDK handle",
      );
    }
    const manifest = documentHandle._engine.manifest;
    if (manifest?.diagnostic?.scope !== "e1-odt-editing-discovery"
        || !manifest?.capabilities?.includes("editor-discovery-closed-actions")) {
      throw new DocumentSdkError(
        "UNSUPPORTED_OPERATION",
        "editor discovery client requires the isolated E1 diagnostic profile",
      );
    }
    this.document = documentHandle;
  }

  async action(action, options = {}) {
    this.document._assertUsable();
    if (!ACTION_SET.has(action)) {
      throw new DocumentSdkError(
        "EDITOR_ACTION_UNSUPPORTED",
        `unsupported closed editor action: ${String(action)}`,
      );
    }
    const extendSelection = options.extendSelection === true;
    if (extendSelection && !MOVE_ACTIONS.has(action)) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "extendSelection is valid only for move actions",
      );
    }
    if (BOOLEAN_OPTION_ACTIONS.has(action) && typeof options.enabled !== "boolean") {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        `${action} requires an explicit enabled boolean`,
      );
    }
    const manualObservation = options.manualObservation === true;
    if (options.manualObservation !== undefined
        && typeof options.manualObservation !== "boolean") {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "manualObservation must be boolean",
      );
    }
    if (manualObservation && !DELETE_ACTIONS.has(action)) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "manualObservation is restricted to the two closed delete actions",
      );
    }
    const expectedRevision = options.expectedRevision ?? this.document.revision;
    if (!Number.isInteger(expectedRevision) || expectedRevision < 0) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "expectedRevision must be a non-negative integer",
      );
    }
    const result = await this.document._engine._request("editorDiscoveryAction", {
      documentHandle: this.document.handle,
      expectedRevision,
      action,
      extendSelection,
      option: BOOLEAN_OPTION_ACTIONS.has(action) ? options.enabled : manualObservation,
    }, options);
    if (Number.isInteger(result.revision))
      this.document.revision = result.revision;
    return result;
  }

  async select(method, range, options = {}) {
    this.document._assertUsable();
    if (!SELECTION_METHOD_SET.has(method)) {
      throw new DocumentSdkError(
        "EDITOR_ACTION_UNSUPPORTED",
        `unsupported closed selection method: ${String(method)}`,
      );
    }
    const result = await this.document._engine._request("editorDiscoverySelect", {
      documentHandle: this.document.handle,
      method,
      startXTwips: integerTwips(range?.startXTwips, "startXTwips"),
      startYTwips: integerTwips(range?.startYTwips, "startYTwips"),
      endXTwips: integerTwips(range?.endXTwips, "endXTwips"),
      endYTwips: integerTwips(range?.endYTwips, "endYTwips"),
    }, options);
    return result;
  }

  async getState(options = {}) {
    this.document._assertUsable();
    return this.document._engine._request("editorDiscoveryGetState", {
      documentHandle: this.document.handle,
    }, options);
  }

  async drainScheduler(options = {}) {
    this.document._assertUsable();
    if (!this.document._engine.manifest?.capabilities
        ?.includes("finding-016-scheduler-probe")) {
      throw new DocumentSdkError(
        "UNSUPPORTED_OPERATION",
        "scheduler drain is restricted to the isolated Finding 016 profile",
      );
    }
    return this.document._engine._request("finding016DrainScheduler", {
      documentHandle: this.document.handle,
    }, options);
  }
}
