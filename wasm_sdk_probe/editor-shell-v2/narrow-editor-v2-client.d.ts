// SPEC E2-C 2.2: types for the fifteen-action v2 product client.
//
// Guarded by editor-shell-v2/tests/declaration-drift.test.mjs.  The v1 pair
// lost two actions here for two shipped artifacts, so the declaration is
// compared to the runtime rather than trusted.

import type { AbortableOptions, DocumentHandle, RevisionOptions }
  from "../sdk/document-sdk.js";
import type { EditorV2Gesture, EditorV2ParagraphAction,
              EditorV2ActionResult } from "./paragraph-editor-client.js";

/** v1's ten, carried into the v2 contract unchanged. */
export type EditorV2InheritedAction =
  | "move-character-left"
  | "move-character-right"
  | "delete-backward"
  | "delete-forward"
  | "insert-paragraph-break"
  | "insert-line-break"
  | "set-bold"
  | "set-italic"
  | "set-underline"
  | "set-strikethrough";

export type EditorV2Action = EditorV2InheritedAction | EditorV2ParagraphAction;

/**
 * ABI 4's append, under the e2-editor-v4 successor identity.  Five, not six:
 * the contract carries one more id whose gesture list is empty, so the engine
 * refuses it every time and naming it here would declare a control that cannot
 * work.
 */
export type EditorV3AppendedAction =
  | "move-line-up"
  | "move-line-down"
  | "move-line-home"
  | "move-line-end"
  | "delete-selection";

export type EditorV3Action = EditorV2Action | EditorV3AppendedAction;

export const EDITOR_V2_INHERITED_ACTIONS: readonly EditorV2InheritedAction[];
export const EDITOR_V2_ACTIONS: readonly EditorV2Action[];
export const EDITOR_V3_APPENDED_ACTIONS: readonly EditorV3AppendedAction[];
export const EDITOR_V3_ACTIONS: readonly EditorV3Action[];

/**
 * The result shape of an inherited action -- v1's, unchanged.  `changed` is a
 * boolean here and null for the five paragraph actions, and that difference is
 * the contract, not an inconsistency: route C does not read the precondition.
 */
export interface EditorV2InheritedResult {
  action: EditorV2InheritedAction;
  beforeRevision: number;
  revision: number;
  changed: boolean;
  completion: string;
  state: unknown;
}

export class NarrowEditorV2Client {
  readonly document: DocumentHandle;
  constructor(document: DocumentHandle);

  action(action: EditorV2InheritedAction,
         options?: RevisionOptions & { extendSelection?: boolean;
                                       enabled?: boolean })
    : Promise<EditorV2InheritedResult>;
  action(action: EditorV2ParagraphAction,
         options?: RevisionOptions): Promise<EditorV2ActionResult>;
  /**
   * `extendSelection` is absent on purpose: the ABI refuses that flag for
   * anything but the two character moves, so offering it here would type a
   * call the engine rejects.
   */
  action(action: EditorV3AppendedAction,
         options?: RevisionOptions): Promise<EditorV2InheritedResult>;

  moveCharacter(direction: "left" | "right",
                options?: RevisionOptions & { extendSelection?: boolean })
    : Promise<EditorV2InheritedResult>;
  moveLine(direction: "up" | "down" | "home" | "end",
           options?: RevisionOptions): Promise<EditorV2InheritedResult>;
  delete(direction: "backward" | "forward",
         options?: RevisionOptions): Promise<EditorV2InheritedResult>;
  /** The caller makes the selection; this removes it.  No direction, no arity. */
  deleteSelection(options?: RevisionOptions): Promise<EditorV2InheritedResult>;
  insertBreak(kind: "paragraph" | "line",
              options?: RevisionOptions): Promise<EditorV2InheritedResult>;
  setInlineFormat(format: "bold" | "italic" | "underline" | "strikethrough",
                  enabled: boolean,
                  options?: RevisionOptions): Promise<EditorV2InheritedResult>;

  setList(kind: "none" | "unordered" | "ordered",
          options?: RevisionOptions): Promise<EditorV2ActionResult>;
  setParagraphStyle(style: "heading" | "body",
                    options?: RevisionOptions): Promise<EditorV2ActionResult>;

  getState(options?: AbortableOptions): Promise<unknown>;
  selectRange(start: { xTwips: number; yTwips: number },
              end: { xTwips: number; yTwips: number },
              options?: AbortableOptions): Promise<unknown>;
  gesturesFor(action: EditorV3Action): EditorV2Gesture[] | null;
  limitsFor(action: EditorV3Action): string[];
}
