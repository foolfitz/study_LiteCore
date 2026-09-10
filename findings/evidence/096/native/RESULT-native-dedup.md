# RESULT — arm U (native): the boundary silence is the flush handler dropping an unchanged cursor callback

Protocol: `handoff/tasks/TASK-2026-09-10-096-why-the-core-is-silent-at-a-boundary.md`,
section "Arm U is runnable today". Criteria were pinned before the harness existed.

Harness `tools/f096_native_dedup.cpp`, run by `tools/run_f096_native_dedup.sh`
against the existing native core `native-lok-26-8/build/instdir`
(`ENABLE_SAL_LOG=TRUE`), `SAL_LOG="+INFO.lok"`, fixture
`test-docs/e1/a11y-audible.odt`. Three rounds, directories `round-*/` here, each
with its verbatim `sal.log` and per-press `presses.jsonl`.

## The gesture and what each press delivered (3/3 identical)

| press | rect | `INVALIDATE_VISIBLE_CURSOR` (type 1) delivered to the callback | `Skipping duplicate [1]` in this press's SAL window |
|---|---|---|---|
| setup Ctrl+Home | to doc start | no (only the STATE_CHANGED init burst) | — setup |
| setup End | to line end (changes) | **yes** | no |
| **A** Home | end → line start (changes) | **yes** | **no** |
| **B** Home | already at start (unchanged) | **no** | **yes** — `Skipping duplicate [1]: [1418, 1418, 0, 280]` |

Per-press attribution is by a `>>>MARK <press>` line written to stderr
immediately before each key; `SAL_LOG` also writes to stderr, so the
`Skipping duplicate [1]` that follows the `B-home-rect-unchanged` marker belongs
to press B. Across all three rounds, the only scored press whose window carries
`Skipping duplicate [1]` is B; A never does.

## Verdict — M2 CONFIRMED, directly

This is the observation the browser could not make. On press B the caret's
rectangle is unchanged (`[1418, 1418, 0, 280]`, identical to press A's result),
so core **did** enqueue an `INVALIDATE_VISIBLE_CURSOR` (the gate
`if (bRet) UpdateCursor()` opened and `SwVisibleCursor::SetPosAndShow` notified
— it has no rect-unchanged guard), and `CallbackFlushHandler` dropped it as a
duplicate (`desktop/source/lib/init.cxx:2535`) before it reached the client
callback. That is exactly the browser's "no type 1 delivered + the session
wedges": the engine's move-path contract waits for a cursor callback that
LibreOfficeKit's own duplicate suppression, working as designed, never lets out.

**The source premise the browser verdict rested on ("UpdateCursor ran on the
silent press") is now an observation, not an inference**: the dedup log line
names the type it dropped, which can only be logged if the notification was
enqueued.

## Instrument red cases (both held, 3/3)

* Press A changed the rect and its window has **no** `Skipping duplicate [1]`
  (the marker attribution is not mis-crediting a stray skip to A).
* Presses that genuinely moved the caret (setup End, press A) delivered type 1
  — the log is not reporting "duplicate" for real changes.

## Scope

This confirms the mechanism for a same-position cursor move. It is not an
upstream defect: the suppression is deliberate; the defect was the engine's
move-path contract, repaired by half A (the 250 ms deadline). The 096 boundary
ArrowDown (T10 arm C: zero callbacks, index frozen) is the same mechanism — a
lone enqueued id 1 with an unchanged rect, dropped — with no surrounding
activity to emit other types.
