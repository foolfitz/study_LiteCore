# TASK — finding 096: after the session dies, does the engine thread still answer?

Pre-registered measurement protocol for
`findings/096-arrow-key-at-a-document-boundary-kills-the-session-with-no-checkpoint.md`.
It executes the measurement named as the cheapest next step in
`handoff/DECISION-2026-09-09-which-layer-can-carry-096s-fix-and-what-each-costs.md`
§2.3.

**Written and committed before the probe that runs it existed.** Nothing below
may be edited after the first attempt that counts; corrections go in an appended
`## Execution record` section that names what it supersedes (AGENTS.md §10).

**No build, no relink, no product byte.** The probe is a new file under
`findings/evidence/096/`. Nothing under `src/`, `sdk/`, `web/`, `dist/`,
`editor-shell*/` is edited, no `make` of any kind is run, and
`build_cutover_page.py --write` is not run.

---

## 0. The question, and why it is not "why does 096 happen"

096 is measured: four arms, 40/40, including the shipping bytes. The engine
arms `gEditorPending` with `requiredCallback = EditorCaretOrSelectionCallback`
and posts the key (`src/probe_engine.cpp:4870-4890`); the only exit is
`completePendingEditorOperation` (`:2062-2127`), which runs only from a matching
LOK callback; this path arms **no** deadline, while the select and place-caret
paths do (`readbackDeadlineArmed` at `:4941` and `:5069`); `probe::cancel`
returns `NotCancellable` for anything in `asynchronousRequests` (`:6198-6209`),
so afterwards every action and every caret placement answers `BUSY`.

**Why the callback never arrives is not determined**, and three explanations
lead to three different fixes:

* **(a)** core broadcast nothing at all;
* **(b)** core broadcast something and the match test rejected it;
* **(c)** the engine thread is not running the code that would broadcast.

**This protocol may not choose between them by plausibility.** It may only
report which the observations exclude. Narrowing three to two is a result.
Naming one because it reads well is the finding-040 mistake with a bigger
invoice (the decision doc's row A is a relink).

---

## 1. The instrument, and what is new in it

The base is `findings/evidence/096/probe_096_boundary_arrow.py`, which already
reproduces 096 40/40 and already attaches a CDP session to the **live** document
worker (the attach route — `Target.setAutoAttach` with `flatten`, re-enabled
after the open because opening a document replaces the worker — is in that
file's execution record). The new probe reuses it and adds three things, all of
which live **inside the worker's own realm**:

1. **A wrapper on `globalThis.__probe_on_event`**, installed after the document
   opens and before any arrow press. That global is the engine's only route
   into JavaScript: `emitJson` (`src/probe_engine.cpp:1032-1045`) does
   `MAIN_THREAD_EM_ASM(... globalThis.__probe_on_event(eventJson) ...)`, looked
   up **at call time**, so a wrapper installed later is called. It receives the
   raw JSON **string**, which is banked verbatim (AGENTS.md §7: payloads, not
   summaries of payloads). The buffer index is marked before every press, so
   emissions are attributable to the press that preceded them.

2. **A wrapper on `self.postMessage`**, pass-through, so the worker's replies
   are visible from inside the worker. Responses to the injected requests carry
   ids the SDK never issues, and `document-sdk.js:_handleMessage` drops a
   response with an unknown requestId (`if (!entry) return;`), so forwarding
   them is inert.

3. **Three injected requests**, delivered by dispatching a `MessageEvent` on the
   worker's own global — the worker listens with
   `self.addEventListener("message", …)` (`sdk/sdk-worker.js:1571`), so
   `self.dispatchEvent(new MessageEvent("message", {data}))` reaches
   `handleRequest` exactly as a real post would.

**Nothing is injected through the page, the shell or the SDK**: those are the
layers the evidence already shows are blocked.

### 1.1 The three injections, in order, after the verdict

| tag | request | why this one |
|---|---|---|
| **C** | `{operation: "f096ControlNoSuchOperation"}` | The **injection-route control**. It reaches `handleRequest`'s `default` branch and is answered `UNKNOWN_OPERATION` by the worker **without touching the engine at all** (`sdk/sdk-worker.js` switch default). It separates "the engine did not answer" from "my injection never arrived", which are otherwise the same silence. |
| **G** | `editorGetStateV2` | Goes through the engine's command queue (`probe::editorGetState` → `submit()`, `src/probe_engine.cpp:6177-6184`) and is executed by `handleEditorGetState` (`:5083-5104`), which answers synchronously and **does not touch `gEditorPending`**. Its reply carries `sourceSequence` (`appendEditorState`, `:1127-1128`). |
| **P** | `editorActionV2`, same action as the arrow that wedged it | The **positive control**. `handleEditorAction`'s first test after `requireDocument` and the barriers is `if (gEditorPending.requestId != 0)` → `BUSY`, "another callback-correlated editor operation is in flight" (`:4624-4628`). It must answer `BUSY`. |

`documentHandle` and `expectedRevision` for **G** and **P** are read out of the
worker's own `pending` map — the wedged `editorActionV2`'s payload — not from
the page. That is authoritative, and reading it also records that the wedged
request is still pending in the worker.

Request ids are `4000000000` (C), `4000000001` (G), `4000000002` (P). The SDK
issues ids from 1 upward (`document-sdk.js:_nextId`), so they cannot collide.

### 1.2 One observation the previous evidence could not make

`callStatus` runs the `ccall` on the worker's **JavaScript** thread, and
`submit()` takes `gState.mutex` (`:2264-2284`). The banked
`workerLiveness` evaluate (0.0 s, 40/40) proves the worker's JS thread runs its
event loop; it does **not** prove that a call into wasm returns. So the
`Runtime.evaluate` that dispatches **G** is itself bounded, and whether it
returned is recorded. A dispatch that does not return is a distinct
observation and gets its own cell in §2.

---

## 2. What each observation licenses — written before anything runs

Per attempt, after the attempt has reproduced 096 (dead state + notice +
`data-rescue: "none"`, the same predicate as the earlier protocol, unchanged).

### 2.1 Which of (a), (b), (c) the injections select

| observation | licenses | does **not** license |
|---|---|---|
| **C** answers `UNKNOWN_OPERATION`, **G** answers with a `sourceSequence`, **P** answers error code `BUSY` | The engine thread is popping and executing commands after the verdict. **(c) is excluded.** The wedge is where the static trace says it is: `gEditorPending` set and cleared by nothing. | Anything about (a) vs (b). That is §2.2. |
| **C** answers; **neither G nor P** answers within the wait | **(c) survives, and is the only one of the three this instrument can still reach.** (a) and (b) are downstream of a loop that is not running, so they become undecidable here, not excluded. | It does not say *why* the loop is not running, and must not be written as "the engine crashed" — the banked evidence has no crash of any kind. |
| **C** answers; the `Runtime.evaluate` that dispatches **G** does not return within its bound | **A new observation**: the worker's JS thread blocks inside the wasm submit path. Same family as (c), and it is reported as its own shape, not folded into it. | It does not name which lock or which frame. |
| **C** answers; exactly one of **G**/**P** answers | **No cell.** Reported as a split answer of the instrument; names no cause. | Everything. |
| **P** answers with any code other than `BUSY` | **VOID by construction.** The instrument is not measuring what this protocol assumes. The code and message are reported **verbatim** and the attempt is not reinterpreted. | Everything. |
| **C** does not answer | **VOID (instrument).** The injection route did not reach `handleRequest`; nothing about the engine is licensed by anything else in the attempt. | Everything. |
| the attempt does not reproduce 096 | Outcome `NOT_REPRODUCED`, reported as its own row. The injections are still recorded and license nothing about 096. | Everything. |

### 2.2 (a) versus (b), from the engine-event capture

The wrapper on `__probe_on_event` sees every string `emitJson` produced. The
press loop presses until the caret stops moving, so **the presses that did move
the caret are the instrument's own non-emptiness check** (AGENTS.md §6: a probe
that cannot print a different value is not a probe).

| observation | licenses | does **not** license |
|---|---|---|
| emissions for the moving presses, and **zero** emissions between the boundary press and the verdict | The engine emitted nothing in that window. **Consistent with (a)**, and it excludes (b) *in the form* "a callback arrived, this build turned it into a state change, and the match test rejected it". | It does **not** license "core broadcast nothing" outright — see §2.3. |
| emissions after the boundary press, none of them an `editor-action-completed` for the wedged request id | **(b)**: something arrived and did not complete the request. The `type`/`source` field of the emission names what did arrive. | It does not say which LOK callback type, unless the emission spells it. |
| an `editor-callback-parse-error` after the boundary press | **(b), the parse half**: a callback in the `INVALIDATE_VISIBLE_CURSOR … CURSOR_VISIBLE` range arrived and this build could not read it (`src/probe_engine.cpp:2487-2495`), so `completePendingEditorOperation` was never called. Its `callbackId` is the payload. | It does not merge with the match-test half; they are different fixes. |
| **no** emissions for the moving presses either | **VOID for the (a)/(b) question.** The wrapper is not seeing engine events. | Everything about (a)/(b). |
| an `editor-action-completed` for the wedged request id **does** appear | **Selects none of (a)/(b)/(c)**: the engine answered and the answer was lost above it. Registered here so that it is a recognised outcome and not a surprise. | It does not say which hop lost it. |
| **G**'s `sourceSequence` exceeds the last `sourceSequence` any emission carried before the boundary press, while no emission appeared after it | An anomaly: the sequence advanced without an emission. **No cell.** Reported, no cause named. | Everything. |

### 2.3 The limit on the (a) cell, stated now rather than discovered later

The engine emits only when its own callback handler sets `editorStateChanged`
(`src/probe_engine.cpp:2459-2486`), or when a callback whose type is in the
`LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR … LOK_CALLBACK_CURSOR_VISIBLE` range
fails to parse. A LOK callback of **any other type**, or one this build's switch
ignores, produces no emission at all.

So "zero emissions" separates

* *core broadcast nothing*, from
* *core broadcast something this build turns into state or into a parse error*,

and it does **not** separate the first from *core broadcast a callback type this
engine build does not watch*. **This instrument cannot close that gap**, and the
report must say so rather than round (a) up to "core broadcast nothing".

**What would close it**, named here so the report does not have to invent it:

1. a counter or log in the engine's LOK callback trampoline **before** the type
   switch — an engine edit, therefore a relink, therefore the decision doc's
   row A cost; or
2. the browser-free route the decision doc already named: `native-lok-26-8/` is
   a built tree and `wasm_sdk_probe/tools/f059_native_*.cpp` are existing
   harnesses that post key events and log callbacks. Asking native LOK which
   callbacks `ArrowUp` emits at the first line of a Writer document answers the
   same question in the reference implementation, and needs no wasm relink.

### 2.4 The default conclusion if this task is never run

096's three explanations stay undiscriminated, and the owner's ruling two
("fix now") has to pick a layer without knowing which half of the defect the
engine actually has. The decision doc's §5 already says what that costs: row A
is the only option that answers the press and it is the most expensive one.
**Written here because AGENTS.md §2 requires every criterion to carry one.**

### 2.5 If the measurement can never be taken

If **C** never answers in any attempt, or no attempt reaches a dead state, the
result written down is: *the §2.3 measurement of the decision doc was attempted
N times and could not be taken, because X*; finding 096 gets that appended, and
§2.3's second measurement (native LOK) is named as the remaining route. **No
fix may be chosen on a guess between (a), (b) and (c).**

---

## 3. Repeats, fixed here before any of them

**5 attempts per direction per arm, on two arms** — `e2-editor-v13` (the
candidate, the arm the owner pressed) and `e2-editor-v8` (**the shipping
bytes**, the arm the owner's ruling two is about). 5 up + 5 down × 2 arms =
**20 counted attempts.**

Two arms rather than one because the engines differ (`0fe25650bec1bac5` vs
`4a2710bba1ef07d9`) and a disagreement between them about (a)/(b)/(c) would
itself be the result. Five per direction because that is what the earlier
protocol registered and it makes the two matrices readable side by side.

**Every attempt is reported, including the ones that fail and the ones that are
void.** Finding 084 is the precedent: 27 runs dropped 3, and a single run gives
a confident answer in either direction.

Shakedown attempts are permitted before the counted ones, are labelled
`shakedown`, **count toward nothing**, and are reported in the execution record
with what they forced.

**Do not stop at the first agreeable answer**: all 20 are run even if the first
answers cleanly, and the report gives the distribution, not the mode.

---

## 4. Constraints on the executor

- **Do not fix anything.** If the cause becomes visible, write it down; do not
  patch it. No edits to `src/`, `sdk/`, `web/`, `dist/`, `editor-shell-v2/`,
  `editor-shell/`.
- Write **only** (a) files under `findings/evidence/096/`, (b) one appended
  section at the end of finding 096, (c) one appended `## Execution record` at
  the end of this file.
- **Never a bare `make`.** Every `.o` in this tree is stale and only
  `refuse_unasked_relink` holds the artifacts still. No relink, no
  `build_cutover_page.py --write`.
- **Count Chrome processes before starting and after finishing**, by browser
  main + `crashpad-handler-pid`. The owner has one Chrome and their own servers,
  including port 8765; both are theirs. Never `pkill -f` / `pgrep -f`; kill
  nothing you did not start; leave nothing running.
- The probe serves from a **scratch mirror** of `dist/` on a port obtained from
  the kernel. Port 8765 is not assumed free.
- **Name no cause you did not measure.**

---

## Execution record

*(appended after the run; nothing above this line is edited)*
### 2026-09-09 — shakedown 1, and the three changes it forced (before any counted attempt)

One shakedown attempt was run on `e2-editor-v8`, `--direction up`,
`--label shakedown-1`, **before any attempt that counts**. It reproduced 096
(`REPRODUCED`, notice matching the owner's quote) and answered §2.1's first row
cleanly — control `UNKNOWN_OPERATION`, `editorGetStateV2` answered,
`editorActionV2` answered `BUSY`. It also forced three changes. Each is named
with the measurement that forced it (AGENTS.md §9); none of them moves §2.1,
and the second one **narrows** §2.2 rather than widening it.

1. **§2.2's window ended in the wrong place, and the first shakedown was a
   false `B` because of it.** The implementation took every emission from the
   boundary-press mark to the end of the buffer. That buffer ends with the
   replies to **this probe's own injections** — an `editor-state-result` at
   ms 31747 and the `BUSY` `error` at ms 32049, against a verdict at ms 31743.
   The attempt was classified `B` by two events the instrument itself caused.
   **The window is now `[press-N … after-verdict]`**, both ends read from marks
   the probe places in the worker's realm.

2. **The discriminator is `lok`, not "any engine emission".** §2.2 said
   "emissions", which admits `tile`, `clicked` and `editor-state-result` —
   answers to commands, not core broadcasts. The (a)/(b) question is about what
   **core** invoked, so the count is now of `{"type":"lok"}` lines only.

3. **§2.3's limit was wrong, and it is corrected here rather than edited above
   (AGENTS.md §10).** §2.3 said "zero emissions" cannot separate *core broadcast
   nothing* from *core broadcast a callback type this build does not watch*, and
   that closing that gap needs a counter in the LOK callback trampoline, i.e. an
   engine edit, a relink, and the decision doc's row A cost.

   **That counter already ships.** `onLokCallback`
   (`src/probe_engine.cpp:2372-2381`) is the function `registerCallback` hands to
   LOK (`:2801`), and its first act — unconditional, before the type switch,
   outside every `#ifdef` — is
   `emitJson("{\"type\":\"lok\",\"id\":<type>,\"payload\":\"<verbatim>\"}")`.
   Every LOK callback of every type therefore already produces one line, and the
   §1 wrapper on `globalThis.__probe_on_event` reads them. **The separation is
   complete at the LOK boundary and needs no engine change.** This supersedes
   §2.3's first two paragraphs and its route (1); route (2), the native LOK
   harness, is unaffected and still answers a different question (what the
   reference implementation does).

   **The limit that actually remains**, stated in place of the one that was
   wrong: a `lok` count of zero says core did not invoke the registered callback
   in the window. It does **not** say why core did not, and it does not exclude
   a callback delivered after the window closes. Neither is required to
   separate (a) from (b).

**Shakedown 1 is reported because §3 says every attempt is reported.** It counts
toward nothing: it was run with the pre-change classifier, and its stored cell
(`B`) is the instrument defect above, not a result. Its raw capture is banked
with the counted runs.

### 2026-09-09 — the counted matrix

Run to completion. **20 counted attempts, 20 REPRODUCED**, no other outcome and
no void attempt. Full result: `findings/evidence/096/RESULT-engine-side.md`; raw
per-attempt evidence in `findings/evidence/096/engine-side-e2-editor-v8.json`
and `…-v13.json`.

| arm | up | down | §2.1 | §2.2 |
| --- | --- | --- | --- | --- |
| C — `e2-editor-v8` (shipping bytes) | 5/5 | 5/5 | `C_EXCLUDED` ×10 | `A` ×5 (up), `B` ×5 (down) |
| A — `e2-editor-v13` (candidate) | 5/5 | 5/5 | `C_EXCLUDED` ×10 | `A` ×5 (up), `B` ×5 (down) |

§3's attempt count was met exactly; both arms were run; no criterion in §2 was
edited.

**§2.1's first row, 20/20**: the control answered `UNKNOWN_OPERATION`,
`editorGetStateV2` answered with a full state, and `editorActionV2` answered
`BUSY` — **the positive control held in every attempt**, so no attempt is void
by §2.1's rule and **(c) is excluded**.

**§2.2, and the finer reading that the registered cells do not carry.** The
registered rows key on "did the engine emit in the window", and by that key the
down arm is `B`. The ids say more, and they are what the fix depends on:
`gEditorPending.requiredCallback` here accepts only LOK id **1**
(`INVALIDATE_VISIBLE_CURSOR`) or id **2** (`TEXT_SELECTION`), and **zero of
either arrived in any of the 20 attempts**. The down arm's window carries three
id **8** (`STATE_CHANGED`) whose payloads are `.uno:LanguageStatus`,
`.uno:CharFontName`, `.uno:FontHeight` — a type `completePendingEditorOperation`
is never even reached for. `sourceSequence` is identical before the boundary
press and after the verdict in all 20.

**A gap in this protocol's own registration, named rather than smoothed over.**
§2.2 was written in terms of "emissions", not "emissions of a completing type".
Splitting by id is a *finer* reading than the registered rows and it is reported
as a measurement beside them, not as a re-classification: the cells above are
what the registered table produced.

**What the run could not separate**, and it is in RESULT §5: whether the down
arm's three `STATE_CHANGED` answer the boundary press or trail the press before
it. Measured latencies — 302–306 ms after the previous press's id 1, against
that same attempt's click→burst reference of 293–299 ms, agreeing to ~7 ms 10/10
on two engines — look like a tail, but this probe does not correlate a callback
to a command. Named remedies: an engine-side correlation (relink), or the native
LOK harness (`tools/f059_native_*.cpp` against `native-lok-26-8/`, no relink).

**Process hygiene.** Chrome count before: one browser main (pid 320605, crashpad
320612) plus the owner's `serve.py --port 8765` (pid 209888) and
`serve_candidate_page.py` (pid 314373). After: identical — one browser main,
both owner servers still up, no headless Chrome, no probe server, nothing killed.
