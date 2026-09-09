# 096 — RESULT: the engine thread is alive, and the completing callback was never broadcast

Measured 2026-09-09 against
`handoff/tasks/TASK-2026-09-09-096-does-the-engine-thread-still-answer.md`,
registered and committed (`ed7568dd`) before the probe was written. Its
`## Execution record` carries the three changes shakedown 1 forced, all of them
before the first counted attempt. This document reads the registered table back
rather than composing a new one.

**No build, no relink, no product byte moved.**

## The matrix — every attempt, not only the agreeable ones

**20 counted attempts. 20 REPRODUCED. 0 NOT_REPRODUCED, 0 DIED_WITH_CHECKPOINT,
0 VOID.** Nothing was intermittent, and no attempt is left out.

| arm | wasm | dir | attempts | §2.1 cell | §2.2 cell | LOK ids in the window |
|---|---|---|---|---|---|---|
| **C — `e2-editor-v8`** (**the shipping bytes**) | `4a2710bba1ef07d9` | up | 5/5 | `C_EXCLUDED` | **`A`** | *(none)* |
| | | down | 5/5 | `C_EXCLUDED` | `B` | `8, 8, 8` |
| **A — `e2-editor-v13`** (candidate) | `0fe25650bec1bac5` | up | 5/5 | `C_EXCLUDED` | **`A`** | *(none)* |
| | | down | 5/5 | `C_EXCLUDED` | `B` | `8, 8, 8` |

Arm C's page sha256 is `1ec7baf9fb53c808…`, byte-identical to the shipped
`dist/e2-editor-app.js`. Arm A's is `31787584290e42bd…`, the number the owner's
T4 round was banked against. Every attempt used the owner's own document
(`63bf89cb…`), reproduced the owner's sentence character for character
(`noticeMatchesOwnerQuote: true`, 20/20), spent 7 presses with the boundary
press at press 2, and reached its verdict after 12.0 s of polling.

## 1. (c) is excluded — the engine thread is popping and executing commands

In **all 20 attempts**, after the session had gone `recoverable-error`:

| injection | answer | seconds |
|---|---|---|
| **C** `f096ControlNoSuchOperation` (the injection-route control; never touches the engine) | `UNKNOWN_OPERATION: unknown worker operation: f096ControlNoSuchOperation` | 0.0 |
| **G** `editorGetStateV2` (engine command queue → `handleEditorGetState`) | **answered**, `ok: true`, with a full state object | 0.0–0.3 |
| **P** `editorActionV2`, same action as the arrow (the positive control) | **`BUSY`** — *"another callback-correlated editor operation is in flight"*, `operation: "editor-action"` | 0.0 |

`getStateDispatchReturned: true` in all 20, so §2.1's "the dispatch itself did
not return" cell never fired: the call into wasm returns.

**The positive control answered `BUSY` in 20 of 20.** So the run is not void by
§2.1's rule, and the engine is in exactly the state the static trace predicts:
`gEditorPending.requestId != 0` (`src/probe_engine.cpp:4624-4628`), a slot no
cancel can clear.

The worker's own `pending` map held exactly one entry in every attempt — the
wedged `editorActionV2`, payload
`{documentHandle: 1, expectedRevision: 0, action: "move-line-up"|"move-line-down",
extendSelection: false, enabled: false}` — and that payload is what **G** and
**P** were built from, so nothing here came from the page.

## 2. The load-bearing observation: no callback that could complete it ever arrived

`gEditorPending.requiredCallback` on this path is
`EditorCaretOrSelectionCallback` (`= -2`, `src/probe_engine.cpp:975`), and
`completePendingEditorOperation` (`:2062-2075`) accepts it only for
`LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` (**id 1**) or `LOK_CALLBACK_TEXT_SELECTION`
(**id 2**).

**In 20 of 20 attempts, zero callbacks of id 1 or id 2 arrived between the
boundary press and the verdict.** The LOK ids seen in that window are: *none*
(up arm, 10/10) and `8, 8, 8` (down arm, 10/10), where **8 is
`LOK_CALLBACK_STATE_CHANGED`**.

`sourceSequence` is **identical** before the boundary press and after the
verdict in all 20 — v8: `11 → 11` (up), `14 → 14` (down); v13: `11 → 11` (up),
`16 → 16` (down). The engine's editor state did not move.

### The instrument's own positive comparison

The press *before* the boundary press moved the caret, in every attempt, and it
is in the same capture:

```
lok  id=1  payload='1418, 1658, 0, 521'              <- LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR
editor-state  source=visible-cursor  sourceSequence 10 -> 11
editor-action-completed  requestId=15  completion="documented-callback-visible-cursor"
```

**37–39 ms** from the press to the completion, 20/20. So the capture is not
blind: the same wrapper, the same session, the same key, one press earlier —
one id 1 and a completed request. One press later: nothing.

### Why the separation needs no engine change (a correction to the protocol)

`onLokCallback` (`src/probe_engine.cpp:2372-2381`) is the function
`registerCallback` hands to LOK (`:2801`). Its first act — **unconditional,
before the type switch, outside every `#ifdef`** — is to emit one
`{"type":"lok","id":<type>,"payload":"<verbatim>"}` line. The protocol's §2.3
said a trampoline counter would be needed and would cost an engine edit, a
relink and the decision doc's row A; **the counter already ships**. The
execution record records that correction.

## 3. What arrived on the down arm, verbatim, and what it does not license

The three `lok id=8` in the down window carried, in all 10 down attempts, on
both engines:

```
.uno:LanguageStatus=English (USA);en-US
.uno:CharFontName=Liberation Serif
.uno:FontHeight=12
```

None of them is `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` or
`LOK_CALLBACK_TEXT_SELECTION`; none is a payload
`updateEditorFormatState` watches, which is why `sourceSequence` did not move
and `completePendingEditorOperation` — reached only inside
`if (editorStateChanged)` (`:2459-2486`) — was never called for them.

**And this instrument cannot say they are a response to the boundary press at
all.** The measured latencies, per attempt:

| reference | v8 | v13 |
|---|---|---|
| caret click's own id 1 → its `STATE_CHANGED` burst | 296–299 ms | 293–296 ms |
| **press 1's** id 1 → the burst in the boundary window | **305–306 ms** | **302–304 ms** |
| boundary press → the burst in the boundary window | 184–186 ms | 183–185 ms |

The burst sits 302–306 ms after the *previous* press's cursor callback, against
the same attempt's own click→burst reference of 293–299 ms — agreeing to within
about 7 ms, 10/10, on two different engines. **The timing is what a delayed tail
of press 1 looks like**; it is not what a 184 ms reply to press 2 would look
like against any reference this capture contains. But the probe attributes by
mark index and **does not correlate a callback to the command that caused it**,
so this is reported as the measurement it is, and the registered `B` cell stands
as registered.

Either reading gives the same answer to the question that matters: **nothing
that could complete the wedged request was broadcast.**

## 4. Which of (a), (b), (c) survive

| explanation | status | on what |
|---|---|---|
| **(c)** the engine thread is not running the code that would broadcast | **EXCLUDED**, 20/20 | the control answered, `editorGetStateV2` answered with a full state, and `editorActionV2` answered `BUSY` — all after the verdict, all in ≤0.3 s |
| **(b)** core broadcast something and the match test rejected it | **EXCLUDED in its load-bearing form**, 20/20 | no id 1 and no id 2 in the window in any attempt. The down arm's `STATE_CHANGED` is a type `completePendingEditorOperation` is never even reached for, and by §3 it is most likely the previous press's tail |
| **(a)** core broadcast nothing that could complete the operation | **SURVIVES** | zero completing callbacks, `sourceSequence` unmoved, while the press one earlier produced one id 1 and completed in 37–39 ms |

**Three explanations are now one**, and the two engines agree exactly.

By the decision doc's §2.3 table, the surviving cell licenses: *"the fix has to
supply a completion the callback cannot; that is an **engine** fix or a
capability withdrawal."* **That is a licence, not a decision** — which row of
that document is chosen belongs to the adjudicator (AGENTS.md §8), and this
measurement does not choose it.

## 5. What this instrument could NOT separate, and what would

1. **Whether the down arm's three `STATE_CHANGED` are a response to the boundary
   press or the tail of the press before it.** §3 gives the timing; it does not
   give a correlation. What would settle it: an engine-side correlation of
   callback to command (an engine edit, therefore a relink, therefore row A's
   cost), **or** the browser-free route the decision doc already named —
   `native-lok-26-8/` is a built tree and `wasm_sdk_probe/tools/f059_native_*.cpp`
   are existing harnesses that post key events and log callbacks. It needs no
   wasm relink.
2. **Why core did not broadcast.** A zero count says core did not invoke the
   registered callback; it does not say what inside core decided that. The same
   native harness is the cheapest route to the reference implementation's
   answer.
3. **A callback delivered after the window closes.** The window ends at the
   verdict, ~30 s after the press.
4. **Home / End.** Finding 018 measured `End`; 096 and this measurement measure
   Up and Down. Whether all four line-move actions behave the same way is
   **unmeasured in both directions**, and finding 018's caution against merging
   them stands.
5. **A physical keyboard.** Keys are injected at the renderer, as in the earlier
   probe.

## 6. Two things recorded and deliberately not merged

- **The up arm saw no `LOK_CALLBACK_STATE_CHANGED` at all**, anywhere in the
  attempt, while the down arm saw bursts after both the click and press 1. The
  two arms click on different paragraphs of the owner's document, so this is a
  difference between two positions in one file and nothing here says what it
  means. **Registered, not explained.**
- Finding 096's separate 「畫面沒有跟著」 note and finding 095 are not measured
  here and are not merged with this.
