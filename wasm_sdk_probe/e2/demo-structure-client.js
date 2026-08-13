import { DocumentSdkError } from "../sdk/document-sdk.js";
import { FormatDiscoveryClient } from "./format-discovery-client.js";

/**
 * The narrow face of the E2 discovery profile, for the structure demo only.
 *
 * This demo exists because task #36 wanted headings and lists in the shipped
 * editor, and that turned out to be E2-B: SPEC E2-000 section 5 fixes the
 * order E2-A -> E2-B -> E2-C, forbids freezing a new ABI before E2-A is done,
 * and says the E2-B spec is not pre-authorised.  E2-A has no verdict (A6 and
 * A7's regression half are unrun), so contract v2 is not available -- but the
 * five paragraph actions themselves are measured, on this artifact, in two
 * browsers (A3/A4/A5, and A7's round-trip slice).  Showing them on the
 * artifact that carries their evidence claims exactly what was measured and
 * nothing more.
 *
 * Two rules follow from that, and both are enforced here rather than promised:
 *
 *   * **The demo is pinned to one artifact.**  The discovery profile is an
 *     experiment bench and has been rebuilt at least six times.  A demo that
 *     followed the newest build would be showing something no evidence
 *     describes; a demo that pinned nothing would break silently.  This one
 *     refuses to run against any other build and says so.  It is disposable by
 *     design: when the bench moves on, this expires rather than chases.
 *
 *   * **The surface is narrower than the ABI.**  The diagnostic ABI carries
 *     line navigation (finding 018), redo (fixed LOK_COMMAND_FAILED per SPEC
 *     E2-000 section 2), a mouse-drag selection method that reports selections
 *     it did not make (SPEC E1-D 2.1), and a scheduler drain.  Wiring any of
 *     them into a demo would be exhibiting known-broken behaviour.  They are
 *     named in FORBIDDEN below so that adding one has to be deliberate, and a
 *     test fails if the two lists ever overlap.
 *
 * It lives in `e2/` and not in `sdk/`: it is discovery-scoped code that must
 * never become part of the Document SDK's exported surface.  `web/` was the
 * first choice, but files there are written against the served `dist/` layout
 * (`./sdk/...`) and so cannot be imported by a unit test -- and an unverifiable
 * allowlist is not much of an allowlist.
 */

// A3/A4/A5 and the A7 round-trip slice all bind to this build.  Changing it
// without new evidence is the finding 027 mistake with extra steps.
export const PINNED_WASM_SHA256 =
  "c89f069e7c43e78e630e4f7d62ba5d016c7aaf434d9f4abf5a0e009e931f9d0f";

// The five E2-A actions, plus the E1 actions this profile's worker can reach.
// `set-underline` and `set-strikethrough` are absent on purpose: they exist in
// the product contract but the discovery worker's table stops at 19, so this
// profile cannot dispatch them at all.  Saying "not wired here" is honest;
// adding them would be a lie the engine would refuse anyway.
export const STRUCTURE_ACTIONS = Object.freeze([
  "set-paragraph-body",
  "set-paragraph-heading",
  "set-list-none",
  "set-list-unordered",
  "set-list-ordered",
]);
export const INLINE_ACTIONS = Object.freeze(["set-bold", "set-italic"]);
export const EDIT_ACTIONS = Object.freeze([
  "delete-backward",
  "delete-forward",
  "insert-paragraph-break",
  "insert-line-break",
  "move-character-left",
  "move-character-right",
]);

// Everything the diagnostic ABI offers that this demo must not reach.  Listed
// rather than merely omitted: an omission is invisible, and the next person to
// widen the toolbar should have to delete a line that says why not.
export const FORBIDDEN = Object.freeze({
  "move-line-up": "line navigation is finding 018, unsupported in the contract",
  "move-line-down": "line navigation is finding 018, unsupported in the contract",
  "move-line-home": "line navigation is finding 018, unsupported in the contract",
  "move-line-end": "line navigation is finding 018, unsupported in the contract",
  undo: "the diagnostic undo action is not the product undo path;"
    + " this demo uses the Document SDK's own undo capability instead",
  redo: "redo returns LOK_COMMAND_FAILED in this build (SPEC E2-000 section 2)",
  "mouse-drag": "the synthesised-mouse-event selection method reports"
    + " selections it did not make (SPEC E1-D 2.1)",
  "drain-scheduler": "a diagnostic hook, never a product gesture",
});

const ALLOWED = new Set([...STRUCTURE_ACTIONS, ...INLINE_ACTIONS, ...EDIT_ACTIONS]);

export function assertPinnedArtifact(manifest) {
  const actual = manifest?.diagnostic?.wasmSha256;
  if (actual !== PINNED_WASM_SHA256) {
    throw new DocumentSdkError(
      "DEMO_ARTIFACT_EXPIRED",
      "this demo is pinned to the engine its evidence describes and the"
      + " profile being served is a different build",
      { expected: PINNED_WASM_SHA256, actual: actual ?? null },
    );
  }
  return actual;
}

export class StructureDemoClient {
  constructor(documentHandle) {
    assertPinnedArtifact(documentHandle?._engine?.manifest);
    // Reused rather than reimplemented: the wire shape for the five actions
    // is measured, and a second copy of it would be a second thing to get
    // wrong.  What is not reused is its reach -- moveCaret, nudgeCaret and
    // drainScheduler are harness instruments and stay behind this wall.
    this.format = new FormatDiscoveryClient(documentHandle);
    this.document = documentHandle;
  }

  static describes(action) {
    return ALLOWED.has(action);
  }

  async action(action, options = {}) {
    if (action in FORBIDDEN) {
      throw new DocumentSdkError(
        "EDITOR_ACTION_UNSUPPORTED",
        `${action} is deliberately not wired: ${FORBIDDEN[action]}`,
      );
    }
    if (!ALLOWED.has(action)) {
      throw new DocumentSdkError(
        "EDITOR_ACTION_UNSUPPORTED",
        `unsupported demo action: ${String(action)}`,
      );
    }
    if (STRUCTURE_ACTIONS.includes(action))
      return this.format.action(action, options);
    if (INLINE_ACTIONS.includes(action))
      return this.format.controlAction(action, options.enabled === true, options);
    this.document._assertUsable();
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

  /**
   * Put the insertion point on the line the user clicked.
   *
   * Not `placeCaret`, and not the Document SDK's `click`, because on this
   * profile neither one works for a click-driven UI (finding 039, measured on
   * this artifact):
   *
   *   * `selection-reset-unstable` completes once per freshly opened document
   *     and then hangs for ever, taking the handle with it -- it waits for a
   *     selection-change callback that core does not send when the selection
   *     is already empty.
   *   * The SDK `click` returns in under a millisecond and leaves the caret
   *     exactly where it was, 5 clicks out of 5.  Reporting success while
   *     doing nothing is worse than hanging, so it is not used here either.
   *
   * A range selection is the one path that is repeatable: three in a row, 19,
   * 9 and 10 ms.  So a click becomes a short selection across the clicked
   * line, which lands the format actions on the paragraph the user pointed at.
   *
   * The cost is named rather than hidden: A3/A4/A5 dispatched every one of
   * their 375 judged actions from a *collapsed* caret, so dispatching from a
   * non-collapsed selection is outside what they measured.  What that does to
   * the saved document is recorded with this demo's evidence.
   */
  selectLineAt(xTwips, yTwips, options = {}) {
    const start = Math.max(0, xTwips - 240);
    return this.document._engine._request("editorDiscoverySelect", {
      documentHandle: this.document.handle,
      method: "text-handles-unstable",
      startXTwips: start,
      startYTwips: yTwips,
      endXTwips: xTwips + 240,
      endYTwips: yTwips,
    }, options);
  }

  getState(options = {}) {
    return this.format.getState(options);
  }
}
