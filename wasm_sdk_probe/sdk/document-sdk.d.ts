export const PROTOCOL_VERSION: 1;
export const ABI_VERSION: 65537;

export interface AbortableOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

export interface DocumentEngineOptions {
  workerUrl?: string | URL;
  workerFactory?: (url: URL) => Worker;
  timeoutMs?: number;
  closeRecoveryTimeoutMs?: number;
  debug?: boolean;
}

export interface SdkManifest {
  sdkVersion: string;
  protocolVersion: number;
  abiVersion: number;
  abiVersionText: string;
  providerContractVersion: string;
  coreCommit: string;
  profile: string;
  capabilities: string[];
  capabilityBits: number;
  expectedCapabilityBits?: number;
  artifactFiles?: Record<string, string>;
  resourcePacks?: ResourcePackManifest[];
}

export interface ResourcePackManifest {
  id: string;
  data: string;
  metadata: string;
  bytes: number;
  sha256: string;
  loadAtStartup: boolean;
  purpose?: string;
}

export interface OpenOptions extends AbortableOptions {
  name?: string;
  /** When true, ownership transfers and the caller's ArrayBuffer becomes detached. */
  transfer?: boolean;
}

export interface RenderRegion {
  xTwips?: number;
  yTwips?: number;
  widthTwips?: number;
  heightTwips?: number;
  canvasWidthPx?: number;
  canvasHeightPx?: number;
}

export interface RenderedTile {
  pixels: ArrayBuffer;
  width: number;
  height: number;
  revision: number;
}

export interface InsertResult {
  method: "paste" | "postKeyEvent";
  revision: number;
}

export interface SaveOptions {
  format?: "odt";
}

export interface SearchOptions extends AbortableOptions {
  backward?: boolean;
}

export interface RevisionOptions extends AbortableOptions {
  expectedRevision?: number;
}

export interface CommentOptions extends RevisionOptions {
  author?: string;
}

export interface SearchResultSelection {
  part?: string | number;
  rectangles?: string;
  [key: string]: unknown;
}

export interface SearchResult {
  found: boolean;
  query: string;
  selections: SearchResultSelection[];
  revision: number;
}

/**
 * What kind of content is selected.
 *
 * `"none"` is a normal, successful result: it is what a collapsed caret
 * reports. LibreOfficeKit cannot distinguish a genuinely empty selection from
 * a selection whose plain-text flavor is missing, so both arrive as `"none"`.
 * Before treating `"none"` as proof that a selection was cleared, cross-check
 * the editor state's `selection.observed` and `selection.collapsed`, which are
 * derived from the callback path rather than from the transferable.
 * `"complex"` means the selection exists but is not representable as plain
 * text -- never treat it as empty.
 */
export type SelectionType = "none" | "text" | "complex" | "unknown";

export interface SelectionResult {
  selectionType: SelectionType;
  /** Empty string whenever `selectionType` is not `"text"`. */
  text: string;
  mimeType: "text/plain;charset=utf-8";
  revision: number;
}

export interface RevisionResult {
  revision: number;
}

export interface CommentListResult extends RevisionResult {
  comments: Array<Record<string, unknown>>;
}

export interface TrackedChangeListResult extends RevisionResult {
  changes: Array<Record<string, unknown>>;
}

export interface SdkEvent {
  protocolVersion: 1;
  kind: "event";
  event: string;
  documentHandle?: number;
  revision?: number;
  detail?: unknown;
  error?: { code: string; message: string };
}

export class DocumentSdkError extends Error {
  readonly code: string;
  readonly details: Record<string, unknown>;
}
export class SdkTimeoutError extends DocumentSdkError {}
export class SdkAbortError extends DocumentSdkError {}
export class WorkerCrashedError extends DocumentSdkError {}
export class WorkerRestartedError extends DocumentSdkError {}
export class StaleDocumentError extends DocumentSdkError {}
export class StaleRevisionError extends DocumentSdkError {}
export class DocumentClosedError extends DocumentSdkError {}

export class DocumentEngine {
  readonly manifest: SdkManifest | null;
  open(input: ArrayBuffer, options?: OpenOptions): Promise<DocumentHandle>;
  restart(): Promise<SdkManifest>;
  onEvent(listener: (event: SdkEvent) => void): () => boolean;
  dispose(): void;
}

export class DocumentHandle {
  readonly handle: number;
  revision: number;
  readonly parts: number;
  readonly widthTwips: number;
  readonly heightTwips: number;
  readonly tileMode: number;
  render(region?: RenderRegion, options?: AbortableOptions): Promise<RenderedTile>;
  click(xTwips: number, yTwips: number, options?: AbortableOptions): Promise<void>;
  insertText(text: string, options?: AbortableOptions): Promise<InsertResult>;
  search(query: string, options?: SearchOptions): Promise<SearchResult>;
  getSelection(options?: AbortableOptions): Promise<SelectionResult>;
  replaceSelection(text: string, options?: RevisionOptions): Promise<RevisionResult>;
  undo(options?: RevisionOptions): Promise<RevisionResult>;
  addComment(text: string, options?: CommentOptions): Promise<RevisionResult>;
  listComments(options?: AbortableOptions): Promise<CommentListResult>;
  setTrackChanges(enabled: boolean, options?: RevisionOptions): Promise<RevisionResult>;
  listTrackedChanges(options?: AbortableOptions): Promise<TrackedChangeListResult>;
  save(options?: SaveOptions, requestOptions?: AbortableOptions): Promise<ArrayBuffer>;
  close(options?: AbortableOptions): Promise<void>;
}

export function createDocumentEngine(options?: DocumentEngineOptions): Promise<DocumentEngine>;
