# RESULT — why core is silent at a boundary (T10, Supersession 2)

Protocol: `handoff/tasks/TASK-2026-09-10-096-why-the-core-is-silent-at-a-boundary.md`.
Three sections exist in that file (`## 1`-`## 6`, "Supersession 1", "Supersession 2");
**this result is read against Supersession 2**, which is operative wherever it
disagrees with the earlier sections. Nothing in the arms or the verdict rule was
widened to produce this result.

Instrument: the raw `lok` stream captured inside the live document worker's own
realm (`probe_096_engine_side.py`'s `INSTALL_WORKER`/`mark`/`COLLECT`), **not**
`sourceSequence` (withdrawn by Supersession 2). Profile `e2-editor-v8` throughout
(`pageSha256 1ec7baf9fb53c808…`, `wasmSha256 4a2710bba1ef07d9…` — the shipping
bytes, matching `dist/e2-editor-app.js`). Fixture `wasm_sdk_probe/test-docs/e1/a11y-audible.odt`
(`fixtureSha256 76ad12c1f0f28d42…`). Probe: `probe_096_flag_reset.py`. Three
attempts per arm plus one earlier shakedown attempt of P′ (identical result,
banked separately, not counted toward the "3").

`answered` = a raw lok id 1 or 2 in the press's window **and** the pill returned
to `ready`. `silent` = no id 1/2 in the window **and** the session reached
`recoverable-error`. Both held on every press below; no press produced the
"third thing" (a raw id 1/2 with the session still wedging) or the mirror case
(a resolved press with no raw callback).

## Per-arm, per-attempt cells

All times are seconds from key dispatch to resolution (`ready` or
`recoverable-error`). `sinkLeft` is `#sink.offsetLeft` before → after the press.
`bandScan.bandCount` was 10 on every one of the 13 attempts below (matching the
fixture's 10 `text:h`/`text:p` elements — no wrapping), and `lastLineEvidence.
rowsBelowCount` was 0 on every attempt (the click really lands on the last
painted band, nothing lies below it) — both checked, not assumed, per the T9
lesson.

### P′ — plain line, same-position Home (band index 6, click inside the ink at 42% of its span, not the margin)

| attempt | press | key | lokIds | verdict | seconds | sinkLeft |
|---|---|---|---|---|---|---|
| shakedown-1 | 1 | Home | [1] | **answered** | 0.201 | 268→100 |
| shakedown-1 | 2 | Home | [5] | **silent** | 30.38 | 100→100 |
| 1 | 1 | Home | [1] | **answered** | 0.202 | 268→100 |
| 1 | 2 | Home | [5] | **silent** | 30.41 | 100→100 |
| 2 | 1 | Home | [1] | **answered** | 0.202 | 268→100 |
| 2 | 2 | Home | [5] | **silent** | 30.223 | 100→100 |
| 3 | 1 | Home | [1] | **answered** | 0.201 | 268→100 |
| 3 | 2 | Home | [5] | **silent** | 30.206 | 100→100 |

First Home answered **4/4** (incl. shakedown), second Home silent **4/4**, all
with `sinkLeft` **literally unchanged** on the second press (100→100) — the
rect the flush handler sees really is identical to the stored state.
`noticeRescue: "checkpoint"` on all 4; content typed earlier in the run came
back after recovery (not separately re-verified here — out of this task's scope).

### G — numbered item, three Homes (band index 7, flag-reset control)

| attempt | press | key | lokIds | verdict | seconds | sinkLeft | sinkTop |
|---|---|---|---|---|---|---|---|
| 1 | 1 | Home | [1] | **answered** | 0.201 | 268→112 | 326→326 |
| 1 | 2 | Home | [1, 5] | **answered** | 0.603 | 112→**100** | 326→**330** |
| 1 | 3 | Home | [8] | **silent** | 30.007 | 100→100 | 330→330 |
| 2 | 1 | Home | [1] | **answered** | 0.201 | 268→112 | 326→326 |
| 2 | 2 | Home | [1, 5] | **answered** | 0.604 | 112→100 | 326→330 |
| 2 | 3 | Home | [8] | **silent** | 30.198 | 100→100 | 330→330 |
| 3 | 1 | Home | [1] | **answered** | 0.201 | 268→112 | 326→326 |
| 3 | 2 | Home | [1, 5] | **answered** | 0.603 | 112→100 | 326→330 |
| 3 | 3 | Home | [8] | **silent** | 30.172 | 100→100 | 330→330 |

First Home answered 3/3. **Second Home answered 3/3 and its `sinkLeft` moved
further LEFT than the first Home's landing point (112→100)** — the "in front
of the label" flag-reset path was reached, exactly as Supersession 2's flag
control requires (`sinkLeft` after press 2 < `sinkLeft` after press 1: 100 <
112, 3/3). Third Home silent 3/3, with `sinkLeft`/`sinkTop` unchanged.

### C — control, `past` fraction on the last line (band index 9, single press)

| attempt | press | key | lokIds | verdict | seconds | sinkLeft |
|---|---|---|---|---|---|---|
| 1 | 1 | ArrowDown | [] | **silent** | 30.17 | 356→356 |
| 2 | 1 | ArrowDown | [] | **silent** | 30.17 | 356→356 |
| 3 | 1 | ArrowDown | [] | **silent** | 30.163 | 356→356 |

Silent 3/3, and the window carries **zero raw lok lines of any type** — not
even id 5 or id 8 (contrast P′/G/N below).

### N — tdf#150457, `near` fraction on the last line (band index 9, two presses)

| attempt | press | key | lokIds | verdict | seconds | sinkLeft |
|---|---|---|---|---|---|---|
| 1 | 1 | ArrowDown | [1] | **answered** | 0.202 | 133→356 |
| 1 | 2 | ArrowDown | [5] | **silent** | 30.371 | 356→356 |
| 2 | 1 | ArrowDown | [1] | **answered** | 0.201 | 133→356 |
| 2 | 2 | ArrowDown | [5] | **silent** | 30.174 | 356→356 |
| 3 | 1 | ArrowDown | [1] | **answered** | 0.201 | 133→356 |
| 3 | 2 | ArrowDown | [5] | **silent** | 30.173 | 356→356 |

First ArrowDown answered 3/3, with `sinkLeft` jumping from near the line's
start (133) to its end (356) — the tdf#150457 jump branch, matching T9's
shakedown reading. Second ArrowDown silent 3/3, `sinkLeft` unchanged.

## Positive controls (protocol: "must hold or the instrument is suspect first")

- **C's press wedges: 3/3.** **N's second press wedges: 3/3.**
- **P′'s first Home answered: 4/4** (incl. shakedown). **G's first two Homes
  answered: 3/3 and 3/3.**

All positive controls held, in the same batch as the cells they license. The
instrument is not suspect.

## Verdict, read against Supersession 2's rule

> **M2 confirmed**: P′'s second Home silent 3/3 **and** G's third Home silent
> 3/3 (with G's second answered and shifted left 3/3), C and N as predicted.

Every clause of that rule is met exactly, 3/3 (P′ additionally 4/4 counting the
shakedown):

- P′'s second Home: silent 3/3. ✓
- G's third Home: silent 3/3, with G's second Home answered and shifted left
  (`sinkLeft` 112→100 < first Home's 112) 3/3. ✓
- C: silent 3/3, as predicted. ✓
- N: first answered / second silent 3/3, as predicted. ✓

**M2 is CONFIRMED.** No press showed the "third thing" (a raw id 1/2 with the
session still dead) that would have forced a different reading, and no cell
came back "not established."

By Supersession 2's licensing, this means: core **did** run its cursor update
on every one of these presses — the gate `if (bRet) UpdateCursor()` is open
(source-confirmed for both the Home path, `SwTextFrame::LeftMargin` returning
unconditionally true, and the arrow path, `SwCursor::UpDown`'s tdf#150457
branch calling `UpdateCursor()` before setting `bRet = false`). What is silent
is the **flush-time dedup**: `CallbackFlushHandler` (`desktop/source/lib/init.cxx:1592-1600,
2529-2537`) drops an `INVALIDATE_VISIBLE_CURSOR` payload that is identical to
the one already stored in `m_states`. A client that waits for a cursor
callback after a no-op move (same rect, before and after) waits forever — not
because core failed to notice, but because LibreOfficeKit's own duplicate
suppression, working as designed, never lets the notification out.

This is a source-supported inference from the browser arms, not a direct
observation of the `SAL_INFO("lok", "Skipping duplicate …")` log line itself
(`init.cxx:2533`) — the browser instrument cannot see an enqueue the dedup
already dropped, only that the gate was open (rect changed on the answered
sibling press in the same attempt) and the payload was unchanged (same
`sinkLeft`/`sinkTop`) on the silent one. Arm U (below) is the only thing that
closes that last gap directly.

## Arm U (native) — not run, and why "not run" rather than "no core build"

Per the task's instruction, `$(LOBUILD)` was read from `wasm_sdk_probe/Makefile`
(`LOBUILD ?= ../wasm-lite/build-headless-probe`) and `$(LOBUILD)/instdir/program`
does exist — but it is the **Emscripten/WASM cross-build** used to link the
product's own probe artifacts (`soffice.wasm`, `soffice.js`; no native ELF
binary), not something a native LOK harness can run against.

A **native** LibreOffice core build does exist on this machine at
`native-lok-26-8/build/instdir/program/soffice.bin` (a real dynamically-linked
x86-64 ELF binary), and this tree has a long history of one-off native LOK
harnesses built against it for specific earlier findings (`wasm_sdk_probe/tools/
f0*_native_*.cpp`, `queue_native_block_identity.cpp`, `e2_a_native_*.cpp`, …).
**None of them is a harness for this question.** Each existing binary drives a
different finding's specific command (059's parameterised inline-format
arguments, 048's click latency, 046's empty readback, …); none dispatches
`.uno:GoDown`/`.uno:GoToStartOfLine` at a document boundary with
`bNotifyWhenFinished` or reads `LOK_CALLBACK_UNO_COMMAND_RESULT`/the
`Skipping duplicate` `SAL_INFO` line. Building one would mean writing new C++
and compiling it, both forbidden for this task.

**Arm U: not run — no pre-existing native harness answers this question on
this machine; compiling one is out of this task's scope.** The 2026-09-10 cost
correction to the protocol (commit `5dc012a2`, landed by the main session
while this task was running) downgrades arm U from "near-infeasible optional"
to "a reasonable next step, teed up for the owner" — building
`native-lok-26-8`-class harness is ~1-2 h, not a relink-class cost — but
running or building it remains outside T10's mandate (`do not compile
anything`).

## Observed, not explained (recorded per AGENTS.md §3, not folded into the verdict)

1. **The three "silent" windows are not all the same shape.** All satisfy
   "silent" by the id-1/2 rule, but the *other* ids differ: C's silent window
   is **empty** (`lokIds: []`, no raw line of any type); P′'s and N's silent
   windows each carry exactly `[5]` (`LOK_CALLBACK_CURSOR_VISIBLE`); G's carries
   exactly `[8]` (`LOK_CALLBACK_STATE_CHANGED`). "Zero callbacks" and "id 8
   only" (and "id 5 only") are three distinct cells here, as the protocol
   anticipated they might be — and this task does not explain why the shape
   differs by arm.
2. **`noticeRescue` differs between C and the other three arms on the very
   same shipping bytes.** C — a single ArrowDown, the first and only key press
   dispatched in that session — reproduces the *original* zero-checkpoint
   notice (`noticeRescue: "none"`, text character-identical to the owner's
   quote) on all 3 attempts. P′, G, and N — each with at least one earlier key
   press (an answered Home/ArrowDown) already dispatched in the same session
   before the wedging one — all get `noticeRescue: "checkpoint"` on all of
   their attempts. This task's arms do not test half C (the checkpoint-before-
   gesture mechanism landed for finding 096's data-loss half) and this result
   does not name a cause for the difference; it is recorded because C's shape
   — one boundary press, nothing dispatched before it — is exactly the shape
   of the owner's original report, and the checkpoint not showing up there on
   the current shipping bytes seems worth a follow-up look, separate from
   this task's M1/M2 question.
3. **G's second Home also moves `sinkTop` (326→330), not only `sinkLeft`.**
   3/3, exactly 4px, only on the press that lands "in front of the label."
   Not predicted, not required by any pinned cell, and not explained here.

## What this does not establish

- **Home and ArrowDown only.** End and the two-character moves (tdf#150457's
  sibling branches) are untested by this task, as `findings/096-*.md` already
  notes as unmeasured for other reasons.
- **The dedup itself was never observed directly** — see "Arm U" above; the
  verdict rests on the source premise (`LeftMargin`/`UpDown` provably calling
  `UpdateCursor`) plus the payload being unchanged, not on reading
  `init.cxx`'s own `SAL_INFO` line.
- **This says nothing about whether 250ms readback (half A) is sufficient** —
  that is a different, already-closed question (`findings/096-*.md`'s "connected
  after the link" section).
