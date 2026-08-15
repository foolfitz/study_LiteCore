// SPEC E2-B: the v2 editor client.
//
// A new directory rather than five more methods on NarrowEditorClient, and the
// reason is mechanical, not stylistic: `editor-shell/editor-client.js` and
// `editor-session.js` are hash-bound by the E1-C shell bundle
// (`e1/editor-shell-bundle-v1.json`, digest f9b1a52f...), and
// `E1_GO_ODT_EDITOR` holds only while both the source and dist copies still
// hash to the registered values.  Editing either file unbinds a shipped
// verdict.  Adding a file beside them does too -- validate_e1_c.py requires
// `available - included - excluded` to be empty over `editor-shell/*.js`.
//
// So: new directory, outside that glob and outside the import graph the E1-C
// entry point traces.  Importing v1 from here is fine; imports do not change
// the bytes of what they import.
//
// It is also the same rule the ABI and the profile builder follow: the version
// of an allowlist is an identity, not a setting.

import { DocumentSdkError } from "../sdk/document-sdk.js";

export const EDITOR_V2_PARAGRAPH_ACTIONS = Object.freeze([
  "set-list-none",
  "set-list-unordered",
  "set-list-ordered",
  "set-paragraph-heading",
  "set-paragraph-body",
]);

const PARAGRAPH_ACTIONS = new Set(EDITOR_V2_PARAGRAPH_ACTIONS);

// SPEC E2-B 5.6.  Route C reports `changed: null` and completes with
// `verified-format-readback`; the v1 validator requires `changed === true` and
// `uno-command-result`, and applying that here would reject every successful
// paragraph action.
//
// The relaxation is per ACTION, never global.  `changed: null` means "the
// precondition was not read", which is finding 022's deliberate design -- the
// cached precondition answered questions about wherever the caret used to be.
// What replaces it is a postcondition the engine verified, which is what
// `verified-format-readback` names.  Accepting the same shape for delete would
// bring finding 022's silent no-op straight back, and delete's postcondition is
// frozen in E1-B.
const FORMAT_COMPLETION = "verified-format-readback";

function unsignedRevision(value) {
  if (!Number.isInteger(value) || value < 0 || value > 0xffffffff) {
    throw new DocumentSdkError("INVALID_ARGUMENT",
                               "expectedRevision must be an unsigned 32-bit integer");
  }
  return value;
}

export class ParagraphEditorClient {
  constructor(document) {
    if (!document || typeof document._assertUsable !== "function"
        || !document._engine)
      throw new TypeError("ParagraphEditorClient requires a DocumentHandle");
    this.document = document;
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

  /** What the profile says this action accepts, or null when unrestricted. */
  gesturesFor(action) {
    const spec = this.document._engine.manifest?.editorContract?.actions?.[action];
    return Array.isArray(spec?.gestures) ? spec.gestures : null;
  }

  /** The narrowings the profile declares for this action (SPEC E2-B 5.7). */
  limitsFor(action) {
    const spec = this.document._engine.manifest?.editorContract?.actions?.[action];
    return Array.isArray(spec?.limits) ? spec.limits : [];
  }

  _validateResult(action, expectedRevision, result) {
    if (!result || result.action !== action
        || result.beforeRevision !== expectedRevision) {
      throw new DocumentSdkError(
        "EDITOR_RESULT_INVALID",
        "the result does not describe the action that was requested",
        { result },
      );
    }
    // Every paragraph action is a mutation, and the equation is the same one
    // the engine implements: a completed action advances the revision by
    // exactly one, INCLUDING one that changed nothing.  Route C does not read
    // the precondition, so it cannot report a no-op, and pretending otherwise
    // would be the finding 022 cache all over again.
    const valid = result.changed === null
      && result.revision === expectedRevision + 1
      && result.completion === FORMAT_COMPLETION;
    if (!valid) {
      throw new DocumentSdkError(
        "EDITOR_RESULT_INVALID",
        "the paragraph action did not satisfy its verified-readback postcondition",
        { result },
      );
    }
  }

  async action(action, options = {}) {
    this._assertAvailable();
    if (!PARAGRAPH_ACTIONS.has(action)) {
      throw new DocumentSdkError(
        "EDITOR_ACTION_UNSUPPORTED",
        `${action} is not a v2 paragraph action`,
      );
    }
    // Neither flag has a meaning for these, so both are sent explicitly false
    // rather than omitted: the worker requires them typed, and a flag that is
    // absent is a flag somebody will later assume defaults the other way.
    if (options.extendSelection !== undefined || options.enabled !== undefined) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT",
        "the paragraph actions take neither extendSelection nor enabled",
      );
    }
    const expectedRevision = unsignedRevision(
      options.expectedRevision ?? this.document.revision,
    );
    const result = await this.document._engine._request("editorActionV2", {
      documentHandle: this.document.handle,
      expectedRevision,
      action,
      extendSelection: false,
      enabled: false,
    }, options);
    this._validateResult(action, expectedRevision, result);
    this.document.revision = result.revision;
    return result;
  }

  // async, so that an invalid argument arrives as a REJECTION like every other
  // failure on this client.  Throwing synchronously here would mean
  // `client.setList(...).catch(...)` never sees it -- a caller would have to
  // wrap the call in try/catch as well, and the one that forgets finds out in
  // production.  Caught by the test, which is why the test calls it the same
  // way a caller would.
  async setList(kind, options = {}) {
    const action = kind === "none" ? "set-list-none"
      : kind === "unordered" ? "set-list-unordered"
      : kind === "ordered" ? "set-list-ordered" : null;
    if (!action) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT", "kind must be none, unordered or ordered");
    }
    return this.action(action, options);
  }

  async setParagraphStyle(style, options = {}) {
    // Two states, and only two: narrowing 2 promises H1 only, so there is no
    // level parameter to pass.  Adding one that is ignored would be a field
    // claiming a capability the evidence does not have.
    const action = style === "heading" ? "set-paragraph-heading"
      : style === "body" ? "set-paragraph-body" : null;
    if (!action) {
      throw new DocumentSdkError(
        "INVALID_ARGUMENT", "style must be heading or body");
    }
    return this.action(action, options);
  }

  getState(options = {}) {
    this._assertAvailable();
    return this.document._engine._request("editorGetStateV2", {
      documentHandle: this.document.handle,
    }, options);
  }

  selectRange(start, end, options = {}) {
    this._assertAvailable();
    return this.document._engine._request("editorSelectRangeV2", {
      documentHandle: this.document.handle,
      startXTwips: start.xTwips, startYTwips: start.yTwips,
      endXTwips: end.xTwips, endYTwips: end.yTwips,
    }, options);
  }
}

// SPEC E2-B 5.13: what a host should do about a failure, decided from the
// failure rather than from its message.
//
// The distinction that matters is whether the uno command was dispatched.  A
// pre-dispatch refusal leaves the document provably untouched; anything after
// it may have changed the document, and the response to that is a rollback to
// the last checkpoint -- NOT a prompt to undo, because undo goes through the
// very queue the failure blocks.
// Codes that cannot be post-dispatch, whatever else is missing from the error.
//
// SPEC E2-C 2.5.  The barrier field is the primary signal, but it only exists
// once the engine has a barrier to report; a failure raised BEFORE the request
// reaches the engine has no barrier and used to fall through to the
// fail-closed default, so a caller who passed a bad argument was told to roll
// the document back.  Fail-closed is right when "was it dispatched" is
// genuinely unknown.  For these three it is known:
//
//   INVALID_ARGUMENT           the client's own option checks, and the worker's
//                              typed-argument gate, both of which return before
//                              `accept()` -- E2-B 9.10 measured the worker half
//                              on the shipped artifact: three forbidden fields,
//                              INVALID_ARGUMENT each, `<office:body>` unchanged
//                              byte for byte
//   EDITOR_ACTION_UNSUPPORTED  the action is not in the client's closed set
//   UNSUPPORTED_OPERATION      the capability/contract gate, client or worker
//
// A rollback here is not a harmless extra step: it reopens the document from
// the last checkpoint and discards everything since, which for a typo in a
// caller's argument is a strictly worse outcome than the typo.
const PRE_DISPATCH_CODES = new Set([
  "INVALID_ARGUMENT",
  "EDITOR_ACTION_UNSUPPORTED",
  "UNSUPPORTED_OPERATION",
]);

export function formatFailureDisposition(error) {
  const barrier = error?.details?.formatBarrier ?? error?.formatBarrier ?? null;
  if (barrier && barrier.dispatched === false)
    return "refused-no-mutation";
  if (barrier && barrier.dispatched === true)
    return "dispatched-rollback";
  // Checked after the barrier, never before: if the engine ever did attach a
  // barrier saying `dispatched: true` alongside one of these codes, the
  // barrier wins.  The code list is a fallback for errors that never got far
  // enough to have a barrier, not an override for ones that did.
  if (PRE_DISPATCH_CODES.has(error?.code))
    return "refused-no-mutation";
  // No barrier field at all: the profile may be one that does not forward it,
  // and guessing would be worse than saying so.  Fail closed -- treat it as
  // possibly-mutated, because the cost of a needless rollback is one action and
  // the cost of a missed one is a document the host believes is clean.
  return "unknown-rollback";
}
