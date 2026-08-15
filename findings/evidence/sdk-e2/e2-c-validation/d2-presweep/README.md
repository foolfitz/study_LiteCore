# E2-C phase D2 — pre-relink defect sweep

**Artifact**: `e2-editor-v2`, wasm `572035ac…` (ABI 2 — the build the round-two
fixes have not reached). **Date**: 2026-08-15. **Browsers**: Chrome and Firefox,
one round each. **12 cells, both browsers identical, all pass.**

## What this is, and what it is not

It is **not** round-one evidence. Round one is closed: it issued
`E2_STOP_OR_RESCOPE` with D2–D5 recorded as `NOT_RUN`, and adding phase evidence
to a closed round afterwards would rewrite what that verdict was made from. That
is why this lives in `d2-presweep/` rather than `d2/`, where
`tools/validate_e2_c.py` would pick it up.

It is a **defect sweep run before the relink**, on the adversarial review's
argument: D2 exercises failure paths, so it is the phase most likely to produce
another engine change, and finding one after the link means a second link — the
most expensive object in this repo.

**The argument was right.** The sweep produced
[finding 046](../../../../046-an-empty-readback-is-reported-as-the-document-being-in-the-wrong-state.md),
an engine-side defect now in the relink queue.

## Cells

| cell | what it shows |
|---|---|
| `d2-stale-revision` | refused, disposition `refused-no-mutation`, `<office:body>` unchanged |
| `d2-stale-handle` | a handle whose engine is gone is rejected |
| `d2-refused-no-mutation-client` | three bad arguments, all refused before any request, body unchanged |
| `d2-unknown-rollback-fallback` | fail-closed survives: an error with no barrier still resolves to rollback |
| `d2-refused-no-mutation-engine` | **finding 046** — on this build an empty paragraph answers `EDITOR_FORMAT_POSTCONDITION_FAILED` / `postcondition-not-met`; after the fix it must answer `MUTATION_OUTCOME_UNKNOWN` / `empty-readback` |
| `d2-dispatched-rollback` | dirty first, checkpoint confirmed, then `MUTATION_OUTCOME_UNKNOWN` / `footnote-apparatus-readback` with `dispatched: true` |
| `d2-boundary-restart-required` | `EDITOR_BOUNDARY_UNSUPPORTED` → `restart-required` → the next operation is refused `EDITOR_NOT_READY` |
| `d2-crash-unsaved-edit` | crash → `recoverable-error` → restart → `ready` |
| `d2-crash-after-save` | saved authority survives the crash |
| `d2-crash-after-checkpoint` | restart comes back dirty, with the checkpoint still held |
| `d2-crash-queued-mutation` | both queued operations rejected `WORKER_CRASHED`, neither replayed |
| `d2-generation-ceiling` | generations 2, 3, then `WORKER_GENERATION_LIMIT` with `requiresPageReload` |

## The judge is build-aware, deliberately

`tools/analyze_e2_c_d2.py` reads the ABI version out of the evidence and applies
the expectation for **that** build. `d2-refused-no-mutation-engine` has one
expectation for ABI 2 (with the finding reference) and another for ABI 3. A cell
that "fails" because it is measuring an artifact the fix has not reached yet is
not a finding, and reporting it as one teaches people to ignore the report.

## Four things the sweep caught, two of them mine

| | |
|---|---|
| `STALE_REVISION` was classified as `unknown-rollback` | **product**, fixed in the shell: it is raised before the action switch, so a rollback discards work for a caller's typo |
| an empty readback is reported as the document being in the wrong state | **product**, finding 046, engine fix queued for the relink |
| `EditorSession.save()` returns `{bytes, …}`, not an ArrayBuffer | **mine**: every snapshot silently produced an empty base64 and the zero-mutation cells had nothing to compare |
| two cells used the wrong fixture | **mine**: a delete in a **heading** is not a structural boundary, and a fixture with no notes cannot produce a note failure. **Both cells came back green having measured nothing** — the exact trap the spec warns about |

A fifth thing, found while choosing a fixture: **a paragraph holding an as-char
frame cannot be located by an anchor sweep**, because locating it needs the very
selection read finding 037's guard exists to prevent. A refusal you cannot
navigate to is a refusal you cannot measure.

## The analyzer says no when it should

`--self-test` applies eight mutations — six to the recorded result, two to the
expectation table — and requires each to change the verdict. The two
expectation mutations exist because the zero-mutation predicate reads **saved
documents**, not fields: mutating the result alone never exercised it, and the
first version of that test passed while proving nothing. 8/8 change the verdict.
