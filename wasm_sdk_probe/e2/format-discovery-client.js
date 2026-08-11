import { DocumentSdkError } from "../sdk/document-sdk.js";

// The five paragraph-level actions E2-A is measuring.  The list is closed here
// as well as in the engine: JS names an action, never a command.  The
// .uno:StyleApply arguments that finding 019 showed are required live in the
// engine and never cross this boundary.
export const E2_FORMAT_ACTIONS = Object.freeze([
  "set-list-none",
  "set-list-unordered",
  "set-list-ordered",
  "set-paragraph-body",
  "set-paragraph-heading",
]);

const ACTION_SET = new Set(E2_FORMAT_ACTIONS);

// Positive control only.  set-bold/set-italic are E1 capabilities whose state
// readback E1-C already validated in the browser, so they answer "does the
// state pipeline work in this profile at all" independently of anything E2 is
// measuring.  They are not E2 candidates and must never be reported as such.
const CONTROL_ACTIONS = new Set(["set-bold", "set-italic"]);

// Caret placement by keystroke rather than by geometry.  Finding 034 turns on a
// caret offset, and every existing placement path in this harness lands on
// offset Len(): caretAtAnchor uses rectangle.x + width, and a search leaves the
// caret after its match.  Nothing here could reach offset 0, which is why 375
// judged dispatches never did.
//
// HOME is a real product gesture -- click a line, press Home, press the format
// button -- so the discriminator uses the closed action rather than a
// coordinate this harness would have to argue is offset 0.  On a single-line
// paragraph line-home and paragraph offset 0 are the same place; the
// discriminator cases are written against single-line paragraphs for that
// reason and record the caret rectangle either side of the press.
const CARET_MOVE_ACTIONS = new Set([
  "move-line-home",
  "move-line-end",
  "move-line-up",
  "move-line-down",
  "move-character-left",
  "move-character-right",
]);

// Three isolated profiles use this client: the A2 measurement profile, the
// finding 021 attribution profile that adds the Finding 016 scheduler drain,
// and the finding 021 candidate-1 profile whose engine runs the upstream
// main loop (no drain capability -- freshness is expected to happen on its
// own there).
const E2_DIAGNOSTIC_SCOPES = new Set([
  "e2-paragraph-format-discovery",
  "e2-scheduler-attribution",
  "e2-mainloop-attribution",
  "e2-mainloop-pei-attribution",
  // Finding 031: the scheduler-attribution profile with a zh-TW UI language
  // compiled in, so the paragraph-style postcondition strings can be read in a
  // second locale.  Same capabilities, same code path -- only the language
  // asked for at documentLoad differs.
  "e2-locale-attribution",
]);

function integerTwips(value, name) {
  if (!Number.isInteger(value) || value < 0)
    throw new DocumentSdkError("INVALID_ARGUMENT", `${name} must be non-negative integer twips`);
  return value;
}

export class FormatDiscoveryClient {
  constructor(documentHandle) {
    if (!documentHandle?._engine || typeof documentHandle._assertUsable !== "function") {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "FormatDiscoveryClient requires a Document SDK handle",
      );
    }
    const manifest = documentHandle._engine.manifest;
    if (!E2_DIAGNOSTIC_SCOPES.has(manifest?.diagnostic?.scope)
        || !manifest?.capabilities?.includes("verified-format-state")) {
      throw new DocumentSdkError(
        "UNSUPPORTED_OPERATION",
        "format discovery client requires an isolated E2 diagnostic profile",
      );
    }
    this.document = documentHandle;
  }

  async action(action, options = {}) {
    this.document._assertUsable();
    if (!ACTION_SET.has(action)) {
      throw new DocumentSdkError(
        "EDITOR_ACTION_UNSUPPORTED",
        `unsupported closed format action: ${String(action)}`,
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
      extendSelection: false,
      option: false,
    }, options);
    if (Number.isInteger(result.revision))
      this.document.revision = result.revision;
    return result;
  }

  async controlAction(action, enabled, options = {}) {
    this.document._assertUsable();
    if (!CONTROL_ACTIONS.has(action)) {
      throw new DocumentSdkError(
        "EDITOR_ACTION_UNSUPPORTED",
        `not a state-pipeline control action: ${String(action)}`,
      );
    }
    if (typeof enabled !== "boolean") {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        `${action} requires an explicit enabled boolean`,
      );
    }
    const result = await this.document._engine._request("editorDiscoveryAction", {
      documentHandle: this.document.handle,
      expectedRevision: options.expectedRevision ?? this.document.revision,
      action,
      extendSelection: false,
      option: enabled,
    }, options);
    if (Number.isInteger(result.revision))
      this.document.revision = result.revision;
    return result;
  }

  // A2 moves the caret without mutating so the state broadcast can be observed
  // on its own.  Same closed selection method E1-A used.
  async placeCaret(xTwips, yTwips, options = {}) {
    this.document._assertUsable();
    return this.document._engine._request("editorDiscoverySelect", {
      documentHandle: this.document.handle,
      method: "selection-reset-unstable",
      startXTwips: integerTwips(xTwips, "xTwips"),
      startYTwips: integerTwips(yTwips, "yTwips"),
      endXTwips: integerTwips(xTwips, "xTwips"),
      endYTwips: integerTwips(yTwips, "yTwips"),
    }, options);
  }

  // Finding 034 discriminator.  Not folded into action(): the closed format set
  // is what E2-A is measuring and must not quietly grow a movement command.
  async moveCaret(action, options = {}) {
    this.document._assertUsable();
    if (!CARET_MOVE_ACTIONS.has(action)) {
      throw new DocumentSdkError(
        "EDITOR_ACTION_UNSUPPORTED",
        `not a caret movement action: ${String(action)}`,
      );
    }
    const result = await this.document._engine._request("editorDiscoveryAction", {
      documentHandle: this.document.handle,
      expectedRevision: options.expectedRevision ?? this.document.revision,
      action,
      extendSelection: false,
      option: false,
    }, options);
    if (Number.isInteger(result.revision))
      this.document.revision = result.revision;
    return result;
  }

  async getState(options = {}) {
    this.document._assertUsable();
    return this.document._engine._request("editorDiscoveryGetState", {
      documentHandle: this.document.handle,
    }, options);
  }

  // Finding 021 discriminating experiment 2: one real cursor dispatch (the
  // .uno: cursor-travel path through the full dispatch framework), to test
  // whether dispatch-driven caret movement schedules the status recompute
  // that API placement provably does not.  A single step keeps the caret
  // inside the same paragraph (placement is at the anchor text's end), so
  // the watched format values are unchanged by the nudge itself; only the
  // broadcast behaviour is being measured.
  async nudgeCaret(options = {}) {
    this.document._assertUsable();
    return this.document._engine._request("editorDiscoveryAction", {
      documentHandle: this.document.handle,
      expectedRevision: options.expectedRevision ?? this.document.revision,
      action: "move-character-left",
      extendSelection: false,
      option: false,
    }, options);
  }

  // Finding 021 attribution.  Runs the VCL scheduler to idle
  // (Scheduler::ProcessEventsToIdle) and reports how many state callbacks that
  // released.  If a drain produces the state that caret movement alone did not,
  // core computes it correctly and this build simply never runs the idle job --
  // which makes it our configuration, not core's behaviour.
  async drainScheduler(options = {}) {
    this.document._assertUsable();
    if (!this.document._engine.manifest?.capabilities
        ?.includes("finding-016-scheduler-probe")) {
      throw new DocumentSdkError(
        "UNSUPPORTED_OPERATION",
        "scheduler drain requires the isolated attribution profile",
      );
    }
    return this.document._engine._request("finding016DrainScheduler", {
      documentHandle: this.document.handle,
    }, options);
  }
}
