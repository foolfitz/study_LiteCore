# Ruling: fixes for findings 171/172 and K cells 7 and 9 (fable, 2026-10-29)

Requested by the owner's plan (ask fable, then specify v25). The adjudicator worked read-only. This
file records the ruling as delivered, condensed, plus the main session's verification. Nothing is
implemented by this file.

## Q1 (finding 172): adopt (a′)

Always dispatch. At the poll, a `success:false` UNO result with **no** `.uno:X` state item in this
flush is a verified no-op iff `<x>Known && cache == requested`. It is answered with the **same reply
as a change** (`changed:true`, `completion:"uno-command-result"`, revision+1) plus an additive field
`witness` in {`uno-success`, `on-time-item`, `state-noop`}. This restores finding 059 under the
on-time premise; it is not new machinery.

- Why not `changed:false`: the E1-C-frozen client `editor-shell/editor-client.js:84-90` requires every
  mutation to return `changed === true`, `revision === expected+1`, `completion ===
  "uno-command-result"`, else `EDITOR_RESULT_INVALID`, which is in `RECOVERY_ERRORS`; the queue would
  block as in 171. `documented-state-noop` was removed after finding 022 (comment at `:79-83`).
- Premise measured: `link-batch-v23/native/ordered-commands/out-n1b/on-time-list.json` has
  `U.uno:Bold/Italic/Underline/Strikeout` -> the same key, rounds 5, late 0; none of the four keys is
  in `lateOrMixed` (that list holds `.uno:Undo`/`.uno:DocumentRepair` for those ops).
- Soundness: a false SUCCESS needs cache == requested, no broadcast and truth != requested, but then
  core changes state and broadcasts on time. A stale cache only produces false FAILURES, except
  stale cache plus a refused dispatch (protected section), which exists identically on v22: register
  **L-noop-trusts-last-state-item**. Owed, not blocking: a native N=5 arm "click from bold into plain
  text; is `.uno:Bold` there before the first poll" (no `(move op, .uno:X)` pair is on the list).
- Rejected: (b) a synchronous state read (`getCommandValues` does not serve `.uno:Bold`; html
  readback would be new machinery, CLAUDE.md section 4); (c) page-only clear-format continuation as
  the fix (hides a wrong engine answer; may be a separate later item).
- Spec amendment (append-only, `SPEC-M3-ordered-commands.md`): amends section 15.2 (`:295`, "the
  reply reads this flush's state item") and section 16.4 (`:395`, "run 059's check on the cache after
  the flush"): the in-flush item decides the change case; the no-op case is decided by (on-time list
  and no item and Known and cache == requested); reply fields unchanged, `witness` added; section 5.8
  vocabulary untouched; section 16.5 proof-absent count unaffected. Site:
  `ordered_engine_reply.inc:71-76` / `probe_engine.cpp:2209-2212`.
- Red cases: **R1** engine test, ordered path, plain text, `set-bold false` ->
  `editor-action-completed`, `witness:"state-noop"`; red on the shipped gate (would have caught 172);
  positive control `set-bold true` -> `on-time-item`. **R2** cache != requested, no item ->
  `LOK_COMMAND_FAILED`. **R3** product: clear-format on plain text -> four `ok` (the existing
  clear-format check turns all four on first and never exercises a no-op); add the check and a
  mutation restoring the gate that reds it; re-run `diag_format.py` on v25 expecting `MKAFTERCLEAR`
  not italic. **R4** worker: unknown `witness` -> null.

## Q2 (finding 171): confirmed, with an addition

Set `barrier.stage = AwaitingResult` before `postUnoCommand` in `startOrderedFormatAction` (the
legacy path does so at `probe_engine.cpp:6215`; the worker documents this premise at
`v24-feature-worker.js:349-352`), **and** serialise the boolean the ordered path already holds
(`deferOrderedFormatReply(barrier, dispatched)`) as `"dispatched"` in `appendFormatBarrierDetails`
(precedents `:3864`, `:6621`). The v25 worker reads `value.dispatched` when boolean, else derives
from stage. Contract owner: the engine's barrier record. Red cases: engine pair (blank paragraph ->
`multi-block-readback` with `dispatched:true`; `gesture-not-permitted` -> `dispatched:false`);
worker unit test on both shapes; product cell bulleting 3/3 x 2 browsers, `diag_format.py` as witness.

## Q3 (cell 7): instrument limit; the hidden product change is finding 038 no longer reproducing

On v24, `recovery-returns-what-the-product-promised` (checks[40]) has `finding038Reproduced:false`,
`stateAfterNextOperation:"ready"`, and its fallback inducer FIRED on the v24 worker; on v21/v22 038
reproduces and no fallback is used. `induce_worker_failure`'s `Target.setAutoAttach` harvest only
yields `attachedToTarget` on the first call per CDP connection, so the boundary check's second call
gets `attachedTypes: []`.

Named limit **I-worker-inducer-single-shot**: "`induce_worker_failure` fires once per CDP connection;
on a profile where `finding038Reproduced` is false the recovery check spends it and B4 of
`a-boundary-arrow-press-does-not-cost-the-work` is unmeasurable (`fired:false`, that exact `why`,
`attachedTypes:[]`)." K reading (form 1, per report): the cell PASSES only if B1-B3 are true in every
round AND the inducer record has exactly that shape; any other FAIL is product RED. Default if not
registered: RED. No in-process patch for this K; a successor runner with a red case (two inducers in
one connection on v22 both fire) is later work. Finding candidate: "038's wedge does not reproduce
on the ordered engine" -- whether the read now answers correctly is unknown.

## Q4 (cell 9): N = K's own three rounds per browser, pinned now

PASS if all three arms `seconds <= 1.0` and `revisionAdvanced: true`. A FAIL counts as
**I-ink-trigger-race** only if exactly one arm has `seconds < 0.08` AND `revisionAdvanced: false` while
the other two pass (the T4 run-02 signature: 0.061 vs 0.112-0.114). At most one such FAIL in three
rounds per browser -> cell PASS by limit; any other FAIL, or two signature FAILs -> product RED.
Forced by `t4/run-02/chrome/report.json` and DISPOSITIONS row 9; closes at the first clean K. Default
if never run: RED, nominal stays 0.2.26. Reader red cases: FAIL with `seconds 0.5` and
`revisionAdvanced false` -> RED; two signature FAILs -> RED; missing check -> STOP.

## Q5: premises corrected

1. The brief cited "section 16.3, lines 293-297"; those lines are section 15.2 (`:287-297`).
2. Candidate (a) `changed:false` is refused by the frozen client; finding 172's fix direction omitted this.
3. DISPOSITIONS row 7 said the inducer "does not reach" the v24 worker: false. It reached and killed it at
   checks[40]; the second call fails, and the cause (`finding038Reproduced:false`) is a product change
   hiding under a PASS.
4. The worker comment at `v24-feature-worker.js:349-352` states a premise true only of the legacy path;
   no test holds it.

## Verification by the main session

Read, not inferred: `editor-client.js:78-90` (validChange and the 022 comment); legacy
`barrier.stage = FormatBarrierStage::AwaitingResult` at `probe_engine.cpp:6215`; the on-time list
entries above (four `(op, same key)` pairs 5/5 late 0; `lateOrMixed` holds only `.uno:Undo` and
`.uno:DocumentRepair` for those ops -- a first coarse string match wrongly suggested otherwise); the
recovery check in `h2/h4/h3-{chrome,firefox}.json` at index 40: v21 and v22 `finding038Reproduced: true`,
`stateAfterNextOperation: "recoverable-error"`, no fallback; v24 `false`, `"ready"`, fallback fired
(Firefox target shows the `e2-editor-v24/sdk-worker.js` worker). fixed-by-review: 1 (DISPOSITIONS row 7).
