export const PROVIDER_CONTRACT_VERSION: "1.0";
export const PROVIDER_WORKER_PROTOCOL_VERSION: 1;
export const DEFAULT_MAX_OPERATION_TEXT_BYTES: number;

export interface ProviderEndpointDescriptor {
  id: string;
  capability: "text.translate";
  input: "selection.text";
  outputOperations: readonly ["replaceSelection"] | readonly "replaceSelection"[];
}

export interface ProviderDescriptor {
  contractVersion: "1.0";
  id: string;
  version: string;
  displayName: string;
  capabilities: readonly "text.translate"[];
  endpoints: readonly ProviderEndpointDescriptor[];
}

export interface SelectionTextInput {
  kind: "selection.text";
  text: string;
  revision: number;
  parameters: Readonly<Record<string, string | number | boolean>>;
}

export interface ReplaceSelectionOperation {
  type: "replaceSelection";
  text: string;
  expectedRevision: number;
}

export interface ProviderProgress {
  fraction: number;
  message?: string;
}

export interface ProviderInvocation {
  providerId: string;
  endpointId: string;
  input: SelectionTextInput;
}

export interface ProviderInvocationContext {
  signal?: AbortSignal;
  reportProgress(progress: ProviderProgress): void;
}

export interface ProviderImplementation {
  invoke(
    invocation: ProviderInvocation,
    context: ProviderInvocationContext,
  ): Promise<ReplaceSelectionOperation> | ReplaceSelectionOperation;
}

export interface ProviderAdapter {
  readonly kind?: string;
  readonly runtimeInfo?: Readonly<Record<string, unknown>> | null;
  ready?(): Promise<unknown>;
  invoke(
    invocation: ProviderInvocation,
    options?: { signal?: AbortSignal; onProgress?: (progress: ProviderProgress) => void },
  ): Promise<ReplaceSelectionOperation>;
  dispose?(): void;
}

export interface ProviderDocumentAdapter {
  readonly binding: "web" | "desktop" | string;
  snapshotSelection(options?: { signal?: AbortSignal }): Promise<{ text: string; revision: number }>;
  applyValidatedOperation(
    operation: ReplaceSelectionOperation,
    options?: { signal?: AbortSignal },
  ): Promise<unknown>;
}

export class ProviderSdkError extends Error {
  readonly code: string;
  readonly details: Record<string, unknown>;
}
export class ProviderAbortError extends ProviderSdkError {}
export class ProviderWorkerCrashedError extends ProviderSdkError {}

export class ProviderRegistry {
  register(descriptor: ProviderDescriptor, adapter: ProviderAdapter): Readonly<ProviderDescriptor>;
  unregister(providerId: string): boolean;
  listProviders(): readonly Readonly<ProviderDescriptor>[];
  get(providerId: string): { descriptor: Readonly<ProviderDescriptor>; adapter: ProviderAdapter };
  dispose(): void;
}

export class ProviderHost {
  constructor(options: { registry: ProviderRegistry; maxTextBytes?: number });
  readonly registry: ProviderRegistry;
  readonly maxTextBytes: number;
  invokeSelection(options: {
    providerId: string;
    endpointId: string;
    documentAdapter: ProviderDocumentAdapter;
    parameters?: Record<string, string | number | boolean>;
    signal?: AbortSignal;
    onProgress?: (progress: ProviderProgress) => void;
  }): Promise<{
    providerId: string;
    endpointId: string;
    inputRevision: number;
    operation: ReplaceSelectionOperation;
    result: unknown;
  }>;
}

export class WorkerProviderAdapter implements ProviderAdapter {
  constructor(options: {
    workerUrl?: string | URL;
    workerFactory?: (url?: string | URL) => Worker;
    providerId?: string;
    contractVersion?: string;
    readyTimeoutMs?: number;
  });
  readonly kind: "worker";
  readonly runtimeInfo: Readonly<Record<string, unknown>> | null;
  ready(): Promise<unknown>;
  invoke(
    invocation: ProviderInvocation,
    options?: { signal?: AbortSignal; onProgress?: (progress: ProviderProgress) => void },
  ): Promise<ReplaceSelectionOperation>;
  dispose(): void;
}

export function validateProviderDescriptor(descriptor: ProviderDescriptor): Readonly<ProviderDescriptor>;
export function validateSelectionTextInput(input: SelectionTextInput): Readonly<SelectionTextInput>;
export function validateProviderOperation(
  operation: ReplaceSelectionOperation,
  options: {
    descriptor: ProviderDescriptor;
    endpointId: string;
    input: SelectionTextInput;
    maxTextBytes?: number;
  },
): Readonly<ReplaceSelectionOperation>;
export function createInProcessProviderAdapter(provider: ProviderImplementation): ProviderAdapter;
export function createWebDocumentAdapter(documentHandle: {
  getSelection(options?: { signal?: AbortSignal }): Promise<{ text: string; revision: number }>;
  replaceSelection(
    text: string,
    options: { expectedRevision: number; signal?: AbortSignal },
  ): Promise<unknown>;
}): ProviderDocumentAdapter;
export function createDesktopDocumentAdapter(binding: {
  readSelection(options?: { signal?: AbortSignal }): Promise<{ text: string; revision: number }>;
  replaceSelection(
    text: string,
    options: { expectedRevision: number; signal?: AbortSignal },
  ): Promise<unknown>;
}): ProviderDocumentAdapter;
export function installProviderWorkerRuntime(
  scope: DedicatedWorkerGlobalScope,
  provider: ProviderImplementation & { descriptor: ProviderDescriptor },
): void;
