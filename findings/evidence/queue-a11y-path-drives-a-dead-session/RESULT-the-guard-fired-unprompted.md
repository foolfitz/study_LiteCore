# The guard fired on a session nobody induced, and that is the measurement

Run 2026-08-26 18:49–18:55, chrome, `--profile e2-editor-v9`, **no control
flag**, no mutation. This is the run the guard was written for, and it is the
only one of the four that could not have been arranged.

## What happened

```
132.1s PASS             a-failed-format-does-not-block-the-session
322.3s NOT_ESTABLISHED  format-a-paragraph-changes-that-paragraph
322.3s NOT_ESTABLISHED  the-run-stopped-because-the-session-was-dead
```

```json
{ "noticedAfter": "format-a-paragraph-changes-that-paragraph",
  "where": "after this check was recorded",
  "insideAnArmThatExpectedIt": null,
  "state": "recoverable-error", "pending": "0", "checkpoint": "無",
  "latency": "儲存 失敗",
  "toast": "儲存：EDITOR_NOT_READY：editor operation save is unavailable in recoverable-error",
  "recorded": 17, "declared": 40, "neverReached": [ 23 ids ] }
```

`ok: false`. 15 PASS, 1 FAIL, 2 NOT_ESTABLISHED recorded before it stopped.

## It is finding 081's page state, field for field

| field | CDP read off the live stalled run, 2026-08-24 | this report, 2026-08-26 |
|---|---|---|
| `state` | `recoverable-error` | `recoverable-error` |
| `pending` | `0` | `0` |
| `checkpoint` | `無` | `無` |
| `latency` | `儲存 失敗` | `儲存 失敗` |
| `toast` | `儲存：EDITOR_NOT_READY：… unavailable in recoverable-error` | identical |
| arm | `format-a-paragraph-changes-that-paragraph` | `format-a-paragraph-changes-that-paragraph` |

The 2026-08-24 reading needed somebody to notice a run was stalled, find the
debugging port and evaluate in the page. This one is in the report.

## The saving, measured

**322.3 s** against the 20–50 minutes the 2026-08-23 stalls cost, and 23 arms
that were not driven at a session refusing all of them. The run also produced
a report, which the stalls did not.

One thing this comparison is NOT: `e2-editor-v9` is not byte-identical to the
builds that stalled on 2026-08-23 (it is the same wasm as `a11y-calloc`,
`b60cc46f…`, which the 08-23 runs are not), so the timing figure is one profile
*family* rather than one artifact.

**And it is no longer one run.** Three repeats followed, with
`--barrier-details-diagnostic`: **4 of 4** die after the same check, with
`recorded: 17/40`, `pending: 0`, `checkpoint: 無` and the same two arms. Filed
as finding 082; the payloads are in `findings/evidence/082/`.

## And it answered finding 081's open question

081 recorded that the first failure's cause was **not established**, because
`latency` keeps only the last entry and a save is refused in `recoverable-error`
anyway — so the save might be consequence rather than cause. The per-arm record
in this report settles it for this run:

| arm | action | outcome |
|---|---|---|
| 1 | `set-paragraph-heading` | **PASS** (`標題 36 ms`, read back `Heading_20_1`) |
| 2 | `set-paragraph-body` | **FAIL** — `MUTATION_OUTCOME_UNKNOWN`: *the postcondition read describes a different paragraph from the one this action was dispatched on*, disposition rollback |
| 3–5 | three list actions | **NOT_ESTABLISHED** — `定位游標 失敗`, the caret cannot be placed |
| after | save | `EDITOR_NOT_READY` → `latency: 儲存 失敗` |

`MUTATION_OUTCOME_UNKNOWN` is in `RECOVERY_ERRORS`
(`editor-shell/editor-session.js:15`), so arm 2's failure is what blocked the
queue. The save is the consequence, and it is the consequence that was visible.

The engine branch is `readback-is-a-different-paragraph`
(`src/probe_engine.cpp:4237`), and it is gated on
`dispatchParagraphKnown && readbackParagraphKnown` — **both of which come from
accessibility**. On the shipped core that gate never fires at all. So the arm
that killed this run is a code path the shipped product cannot reach, taking
its first real exercise. Which of "the read really was of another paragraph" and
"the fingerprints are derived wrongly on this core" is true is **not
established**; three repeat runs with `--barrier-details-diagnostic` are queued
to record the fingerprints the barrier compared.

## Same run, two deaths

`bulleting-a-blank-line-does-not-demand-a-rollback` had already FAILED at
108.0 s with a *different* `failureShape` — `the format barrier stopped
advancing before it could read the paragraph` (`stage-deadline`, recorded
2026-08-23) — leaving `state: recoverable-error, queueStillOpen: false`. At
111.3 s `notice-action-recovers-the-session` **PASSED**: the product's recovery
notice was pressed and the session came back.

So the accessibility core produced two distinct barrier failures in one run,
both terminal for the session. The first was recovered from by the arm that
induces it on purpose — which is exactly what the held-off regions are for, and
had they not been there this run would have stopped at 111 s naming the wrong
thing.
