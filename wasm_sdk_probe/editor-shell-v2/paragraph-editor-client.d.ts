// SPEC E2-B: types for the v2 paragraph editor.
//
// A separate declaration from editor-client.d.ts, matching the separate module:
// editor-shell/*.js is hash-registered by E1-C's shell bundle and v2 must not
// disturb it.
//
// editor-shell/tests/declaration-drift.test.mjs guards the v1 pair; the v2 pair
// is guarded by editor-shell-v2/tests/declaration-drift.test.mjs, added for the
// same reason -- the v1 declaration silently lost two actions for two shipped
// artifacts because nothing compared it to the runtime.

import type { AbortableOptions, DocumentHandle, RevisionOptions }
  from "../sdk/document-sdk.js";

export type EditorV2ParagraphAction =
  | "set-list-none"
  | "set-list-unordered"
  | "set-list-ordered"
  | "set-paragraph-heading"
  | "set-paragraph-body";

export const EDITOR_V2_PARAGRAPH_ACTIONS: readonly EditorV2ParagraphAction[];

/** The selection shapes an action may be dispatched on (SPEC E2-B 9.9). */
export type EditorV2Gesture = "collapsed" | "range-single" | "range-cross";

export interface EditorV2FormatBarrier {
  failureShape: string;
  /** false only for a pre-dispatch refusal, where the document is untouched. */
  dispatched: boolean;
  route: EditorV2Gesture | null;
  preBlocks: number | null;
  postBlocks: number | null;
  crossIdentityHeld: boolean | null;
  crossStateHeld: boolean | null;
}

export interface EditorV2ActionResult {
  action: EditorV2ParagraphAction;
  beforeRevision: number;
  revision: number;
  /**
   * Always null.  Route C does not read the precondition (finding 022), so it
   * cannot say whether the paragraph was already in the target state; what it
   * offers instead is a postcondition it verified.
   */
  changed: null;
  completion: "verified-format-readback";
  formatBarrier?: EditorV2FormatBarrier;
}

export class ParagraphEditorClient {
  readonly document: DocumentHandle;
  constructor(document: DocumentHandle);
  action(action: EditorV2ParagraphAction,
         options?: RevisionOptions): Promise<EditorV2ActionResult>;
  setList(kind: "none" | "unordered" | "ordered",
          options?: RevisionOptions): Promise<EditorV2ActionResult>;
  /** Two states only: narrowing 2 promises H1, so there is no level parameter. */
  setParagraphStyle(style: "heading" | "body",
                    options?: RevisionOptions): Promise<EditorV2ActionResult>;
  getState(options?: AbortableOptions): Promise<unknown>;
  selectRange(start: { xTwips: number; yTwips: number },
              end: { xTwips: number; yTwips: number },
              options?: AbortableOptions): Promise<unknown>;
  gesturesFor(action: EditorV2ParagraphAction): EditorV2Gesture[] | null;
  limitsFor(action: EditorV2ParagraphAction): string[];
}

export type EditorV2FailureDisposition =
  | "refused-no-mutation"
  | "dispatched-rollback"
  | "unknown-rollback";

export function formatFailureDisposition(error: unknown): EditorV2FailureDisposition;
