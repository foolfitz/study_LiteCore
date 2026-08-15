import type {
  AbortableOptions,
  DocumentHandle,
  RevisionOptions,
} from "../sdk/document-sdk.js";

export type EditorV1Action =
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

export interface EditorRectangle {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface EditorSelectionState {
  observed: boolean;
  collapsed: boolean;
  start: EditorRectangle | null;
  end: EditorRectangle | null;
  rectangles: EditorRectangle[];
}

export interface EditorState {
  documentHandle?: number;
  revision?: number;
  sourceSequence: number;
  documentChangeSequence: number;
  visible: boolean;
  caret: EditorRectangle | null;
  selection: EditorSelectionState;
  selectionType?: "none" | "text" | "complex" | "unknown";
  selectionTextMissing?: boolean;
  selectionText?: string;
  format: { bold: boolean | null; italic: boolean | null };
}

export interface EditorActionResult {
  action: EditorV1Action;
  beforeRevision: number;
  revision: number;
  changed: boolean;
  completion: string;
  callbackSequenceBefore: number;
  callbackSequenceAfter: number;
  state: EditorState;
}

export interface EditorActionOptions extends RevisionOptions {
  extendSelection?: boolean;
  enabled?: boolean;
}

export const EDITOR_V1_ACTIONS: readonly EditorV1Action[];

export class NarrowEditorClient {
  readonly document: DocumentHandle;
  constructor(document: DocumentHandle);
  action(action: EditorV1Action, options?: EditorActionOptions): Promise<EditorActionResult>;
  moveCharacter(direction: "left" | "right", options?: EditorActionOptions): Promise<EditorActionResult>;
  delete(direction: "backward" | "forward", options?: RevisionOptions): Promise<EditorActionResult>;
  insertBreak(kind: "paragraph" | "line", options?: RevisionOptions): Promise<EditorActionResult>;
  setInlineFormat(format: "bold" | "italic" | "underline" | "strikethrough", enabled: boolean, options?: RevisionOptions): Promise<EditorActionResult>;
  getState(options?: AbortableOptions): Promise<EditorState>;
}
