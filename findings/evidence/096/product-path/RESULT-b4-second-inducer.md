# T8b — the three red cases and the four plain runs for finding 096's second B4 inducer

Runner: `tools/run_e2_c_product_path.py --browser chrome`, run from
`wasm_sdk_probe/`. Protocol: `handoff/tasks/TASK-2026-09-10-096-b4-second-inducer.md`
(§4 red cases, §5 acceptance, §7 named limits, §8 constraints). Seven runs, one
Chrome instance at a time, in the order listed in the T8b brief. Headless
Chrome process count before the first run: **0** (two unrelated
`chrome_crashpad_handler` processes for other Electron apps — Codex desktop,
marktext — were running and are not the browser this runner drives; they were
left untouched throughout). After each run and after the seventh, the process
count returned to 0; no leftover headless Chrome was found or killed.

All seven reports and this file live under `findings/evidence/096/product-path/`.
`compare_b4_cells.py` in the same directory is the control-comparison script
referenced below.

## Run table

| # | file | composition | check outcome | clausesExercised | b4Inducer | B1 | B2 | B3 | B4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `mutate-boundary-move-takes-no-checkpoint-e2-editor-v14.json` | 39 PASS / 1 FAIL / 2 NE | FAIL | `[B1,B3,B2,B4]` | `worker-failure` | true | true | **false** | **false** |
| 2 | `mutate-worker-crash-throws-the-checkpoint-away-e2-editor-v14.json` | 39 PASS / 1 FAIL / 2 NE | FAIL | `[B1,B3,B2,B4]` | `worker-failure` | true | true | true | **false** |
| 3 | `mutate-worker-crash-is-never-noticed-e2-editor-v14.json` | 39 PASS / 1 FAIL / 2 NE | FAIL | `[B1,B3,B2]` (no B4) | `worker-failure` | true | true | true | **null** |
| 4 | `plain-e2-editor-v14-b4-01.json` | 40 PASS / 2 NE | PASS | `[B1,B3,B2,B4]` | `worker-failure` | true | true | true | true |
| 5 | `plain-e2-editor-v14-b4-02.json` | 40 PASS / 2 NE | PASS | `[B1,B3,B2,B4]` | `worker-failure` | true | true | true | true |
| 6 | `plain-e2-editor-v14-b4-03.json` | 40 PASS / 2 NE | PASS | `[B1,B3,B2,B4]` | `worker-failure` | true | true | true | true |
| 7 | `plain-e2-editor-v8-after-t8a.json` | 40 PASS / 2 NE | PASS | `[B1,B3,B4]` | `boundary-press` | true | true | true | true |

The NE pair is `notice-action-recovers-the-session` /
`a-refused-action-is-reported-and-changes-nothing` in all seven, unchanged
from every previously banked run in this directory.

`finding038Reproduced` (on `recovery-returns-what-the-product-promised`) is
`true` in all seven reports, and that check's own outcome is `PASS` in all
seven. This is the precondition the two new mutations' `alsoRed: []` claim
depends on (§4's closing paragraph): with 038 reproducing, `induce_worker_failure`'s
other call site does not reach its fallback, so the boundary arm's call is the
only one of the two call sites that fires in any of these seven runs, and
§7 limit 1 (order-dependence between the two call sites) is not in play here.

## Fuller cells (runs 1-3, the fallback path)

| field | run 1 (i) | run 2 (ii) | run 3 (iii) |
| --- | --- | --- | --- |
| `checkpointBeforeTheKey` / `checkpointAfterTheKey` | `無` / `無` | `無` / `有（r1）` | `無` / `有（r1）` |
| `theEngineAnsweredThePress` | true | true | true |
| `fallbackInducer.fired` | true | true | true |
| `stateAfterFallback` | `recoverable-error` | `recoverable-error` | `ready` |
| `declaredCheckpointAfterFallback` | `無` | `無` | *(none read — session stayed ready)* |
| `checkpointOnOfferIsThisGestures` | false | false | *(n/a)* |
| `noticeAfterFallback.rescue` / `.label` | `none` / `重新開啟` | `none` / `重新開啟` | *(n/a — notice never shown)* |
| `checkpointBeforeTheKey` reread after fallback | — | — | — |
| `stateAfterRecovery` | `ready` | `ready` | *(n/a)* |
| `workCameBack` | false | false | *(n/a)* |
| `why` | "the press was answered but the answer did not leave a usable session at the revision it started from, or the checkpoint was not this gesture's; ... The checkpoint on offer was NOT this gesture's" | "the gesture banked a checkpoint and the session was then killed a second way, and what came back does not carry the work: ... The checkpoint on offer was NOT this gesture's" | "the second inducer fired and the product never noticed: a real uncaught error inside the document worker left the session 'ready', so the dead state B4 needs was never reached" |

`presses[*].seconds` (timing, exempt from the "no cell moved" comparison; recorded for completeness):

| run | press 1 | press 2 |
| --- | --- | --- |
| 1 | 0.15 | 4.11 |
| 2 | 0.61 | 4.09 |
| 3 | 0.46 | 4.11 |
| 4 | 0.46 | 4.10 |
| 5 | 0.61 | 4.10 |
| 6 | 0.61 | 4.11 |
| 7 | 0.46 | 4.11 |

`revisionBeforeTyping` / `revisionAfterTyping` are `0` / `1` in all seven runs.

## Red case verdicts against §4

**(i) `boundary-move-takes-no-checkpoint` — PASS (matches the pinned cells exactly).**
`checkpointBeforeTheKey`/`checkpointAfterTheKey` both `無`; `theEngineAnsweredThePress: true`;
`fallbackInducer.fired: true`; `stateAfterFallback: "recoverable-error"`;
`declaredCheckpointAfterFallback: "無"`; `noticeAfterFallback.rescue: "none"`;
`checkpointOnOfferIsThisGestures: false`; `workCameBack: false`; `B3`/`B4`:
`false`/`false`; `clausesExercised` contains `B4`; `b4Inducer: "worker-failure"`;
composition 39 PASS / 1 FAIL / 2 NE, the FAIL being only this check. Every
pinned field matches.

**(ii) `worker-crash-throws-the-checkpoint-away` — PASS (matches the pinned cells exactly).**
`checkpointBeforeTheKey`/`checkpointAfterTheKey`: `無`/`有（r1）` — B3 stays
true, confirmed (`B3: true`); `fallbackInducer.fired: true`; `stateAfterFallback:
"recoverable-error"`; `declaredCheckpointAfterFallback: "無"`;
`noticeAfterFallback.rescue`/`.label`: `"none"`/`"重新開啟"`;
`checkpointOnOfferIsThisGestures: false`; `workCameBack: false`; `B4: false`;
`clausesExercised` contains `B4`; composition 39 PASS / 1 FAIL / 2 NE, the
FAIL being only this check. Every pinned field matches.

**(iii) `worker-crash-is-never-noticed` — PASS (matches the pinned cells exactly).**
`fallbackInducer.fired: true`; `stateAfterFallback: "ready"`; `B1`/`B2`/`B3`:
true/true/true; `B4: null` (JSON `null`, not `false`); `clausesExercised:
["B1","B3","B2"]` — no `B4`; `b4Inducer: "worker-failure"`; `why` names that
the product never noticed a real worker failure ("the second inducer fired
and the product never noticed..."); the run's `outcome: "FAIL"` (not
`NOT_ESTABLISHED`), composition 39 PASS / 1 FAIL / 2 NE. Every pinned field
matches, including the §3 decision (FAIL, not NE, for an unreachable B4 on a
profile where the press is answered).

**`alsoRed` for all three: `[]`, confirmed.** Baseline used:
`plain-e2-editor-v14-b4-01.json` (run 4 in this batch, the first plain v14 run
taken). Each mutated run's composition is 39 PASS / 1 FAIL / 2 NE with the
FAIL set = `{a-boundary-arrow-press-does-not-cost-the-work}`; the baseline's
composition is 40 PASS / 2 NE with an empty FAIL set and the identical NE
pair. FAIL(mutated) − FAIL(baseline) = `{}` for all three mutations, i.e.
`alsoRed: []` holds for (i), (ii), and (iii).

## Control comparison: v8 after T8a vs the banked `plain-e2-editor-v8.json`

`compare_b4_cells.py plain-e2-editor-v8.json plain-e2-editor-v8-after-t8a.json`
output (script diffs the check's `ok`/`outcome`/`why`/`oracle`/`observed`
fields, sorted, one leaf path per line):

```
3 differing path(s)

[EXEMPT] observed.savedBytes
    a: 12898
    b: 12899
[EXEMPT] observed.verdict.b4Inducer
    a: '<MISSING>'
    b: 'boundary-press'
[MOVED ] oracle
    a: "...LIMIT: B2 -- that an ANSWERED press leaves the session usable -- is vacuous..."
    b: "...WHICH INDUCER REACHED B4 is in `b4Inducer`: ... LIMIT: B2 -- ...is vacuous..."

non-exempt moved cells: 1
```

**Reading it against the brief's three exemptions:**

* (a) the new `b4Inducer: "boundary-press"` cell — present, exempt, expected.
* (b) timing cells — no `presses[*].seconds` value differed between these two
  particular reports (0.46/4.11 in both), so nothing to exempt there this
  time; timing did move between other pairs in this batch (see the table
  above), which is why it is a standing exemption rather than a coincidence.
* (c) `savedBytes` — moved by 1 byte (12898 → 12899). This is a byte count and
  the brief asks whether it legitimately varies: across the three plain-v14
  runs in this same batch it took three different values on an unmutated
  document (12897, 12899, 12895), so 1-byte drift on an otherwise-identical
  save is consistent with something inside the saved ODT (most plausibly a
  timestamp field) changing between runs rather than with a content
  difference. This run did not open the ODT to identify which byte moved, so
  that account is asserted from the size gap alone, not independently
  verified.

**The one non-exempt mover: the check's `oracle` string.** This field sits
outside `observed` (i.e. outside the "boundary" payload the §2.5 promise is
about — `B1`..`B4`, `clausesExercised`, `why`, and `boundary[...]` keys), and
the difference traces to a specific, already-landed T8a commit,
`ffb5c96a1510` (`oracle 也要說 B4 是誰逼出來的`, made before T8b started, tree
clean at that hash), which added exactly the `WHICH INDUCER REACHED B4 is in
b4Inducer...` and `B4 unexercised is a FAIL...` sentences to this string so a
reader would not mistake v14's `B4: true` for the gesture itself having
killed and revived the session. The same expanded oracle string appears
verbatim in all seven of this batch's reports, including the five that ran
the dying-branch-free v14 profile, so it is emitted by the check's own code
unconditionally rather than computed per branch or per profile. Inside
`observed`/`verdict` itself — the scope §2.5 actually promises — nothing
moved except the two exempt cells. Recorded here because the brief said to
compare the whole check object's cell-for-cell, and this is what widening the
scope to `oracle` turned up; it is an intentional, already-committed change,
not a T8b-discovered anomaly.

Every other key in `observed` (the "boundary" payload) and in `verdict` is
identical in value, key set, and key order between the two v8 reports:
`sentinel`, `offered`, `openedAs`, `reopened`, `stateAfterOpen`, `bands`,
`click`, `placed`, `revisionBeforeTyping`, `revisionAfterTyping`,
`checkpointBeforeTheKey`, `checkpointAfterTheKey`, `stateAfterPress`,
`theEngineAnsweredThePress`, `notice`, `pressedTheNotice`,
`stateAfterRecovery`, `savedIsOdt`, `workCameBack`, and `verdict.{B1,B2,B3,B4,
clausesExercised,ok,outcome,why}`. `servedShell` is byte-identical between
the two v8 runs (`declaredSha256 == servedSha256 == 2ffbec81…`, same bundle
`e2/editor-shell-v2-bundle-v51.json`, `differingPaths: []`, same
`entrypointSha256`), confirming the control ran against the same shell
generation the original `plain-e2-editor-v8.json` did, with no product byte
moved between the two runs — the only thing that changed in the tree between
them is the runner script itself (T8a).

## §5 acceptance, per clause

`--profile e2-editor-v14`, no mutation, three runs:

* **`clausesExercised` contains all of B1, B2, B3, B4 — MET**, 3/3 runs:
  `["B1","B3","B2","B4"]` each time.
* **`b4Inducer: "worker-failure"` 3/3 — MET.**
* **`fallbackInducer.fired: true`, `stateAfterFallback: "recoverable-error"`,
  `declaredCheckpointAfterFallback: "有（r1）"`,
  `noticeAfterFallback.rescue: "checkpoint"`,
  `checkpointOnOfferIsThisGestures: true`, `workCameBack: true`, `B4: true`
  — MET**, all seven cells, all 3 runs.
* **Composition unchanged at 40 PASS / 2 NE, `ok: true` — MET**, all 3 runs.

`e2-editor-v8`, no mutation, one run:

* **`clausesExercised` exactly `["B1","B3","B4"]`, `b4Inducer:
  "boundary-press"` — MET.**
* **Every other cell equal to `plain-e2-editor-v8.json` — MET inside
  `observed`/`verdict` (the two exempt cells aside); NOT MET if the
  comparison is widened to the check's `oracle` string**, which moved —
  attributable to the already-landed T8a commit `ffb5c96a1510`, not to
  anything run in T8b. The brief's own scope (§2.5: the branch's
  keys/values) is satisfied; a reader who wants the whole check object
  byte-identical minus only the three named exemptions will find one more
  line moved, and now knows which commit moved it.

**The worker-failure inducer fired on v14 in every run it was tried (6/6:
the three plain runs and the two mutations where the fallback path was
reached) — this is a result to bank per the brief's explicit framing, and it
is the affirmative case, not the "did not fire" case that framing
anticipated.**

## §7 named limits, checked against these seven runs

* **Limit 1 (call-site ordering).** Not in play: 038 reproduced (`true`) in
  all seven reports, so `recovery-returns-what-the-product-promised` did not
  reach its own fallback call to `induce_worker_failure`, leaving the
  boundary arm's call as the only one that fires per run — the precondition
  the limit describes as "today" held throughout this batch.
* **Limit 2 (worker generation budget of 3).** No report contains
  `WORKER_GENERATION_LIMIT` or an observed state of `restart-required`; the
  only occurrences of the string `restart-required` in any of the seven files
  are inside a different check's static explanatory text (documentation, not
  an observed value). No run in this batch hit the generation ceiling.
* **Limit 3 (harness path vs. user path).** Unchanged; not measured
  differently here than described in the protocol.
* **Limit 4 (B4 on v14 is weaker than B4 on v8).** Recorded as intended by
  the protocol: `b4Inducer` distinguishes the two and no run in this batch
  conflates them.

## Observed but not explained

* The check's `oracle` string moved between the pre-T8a and post-T8a
  `plain-e2-editor-v8.json` pair (see the control comparison above) even
  though it sits outside the `observed`/`verdict` scope the protocol's §2.5
  promise is written against.
* `savedBytes` for the target check took four different values across the
  four unmutated saves in this batch (v14: 12897, 12899, 12895; v8:
  12899) and two further values across the two mutated-but-still-saving runs
  (12223, 12222) — recorded, not opened, not attributed to a specific byte.
* `offPageInk.scans` varied by run (38 or 39) across otherwise-identical
  plain v14 runs; not investigated.

## What could not be done and why

Nothing in the T8b brief was left undone. All seven runs, the comparison
script, and this file are complete; the TASK execution-record append and the
README append are separate deliverables handled alongside this one.
