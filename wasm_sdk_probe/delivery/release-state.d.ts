export class ReleaseStateError extends Error {
  code: string;
  details: Record<string, unknown>;
}

export function createReleaseState(options?: { retentionLimit?: number }): Record<string, unknown>;
export function validateReleaseState(state: Record<string, unknown>): {
  errors: string[];
  pass: boolean;
};
export function transitionReleaseState(
  state: Record<string, unknown>,
  event: Record<string, unknown>,
): { state: Record<string, unknown>; actions: Array<Record<string, unknown>> };
export function planReleaseEviction(state: Record<string, unknown>): {
  protectedReleaseIds: string[];
  evictReleaseIds: string[];
  excess: number;
  boundedAfterPlan: boolean;
};
