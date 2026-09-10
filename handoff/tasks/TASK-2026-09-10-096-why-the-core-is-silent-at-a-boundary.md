# TASK — finding 096: why the core broadcasts nothing at a boundary, read from the source and made falsifiable

Pre-registered protocol. Written by the main session under form B′
(`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, "Form B′"): the
diagnosis below is a **reading of the source**, and by B′'s own rule it stays a
hypothesis until the arms below have run. Nothing under `## 1`–`## 6` may be
edited after the first attempt that counts; corrections go in the appended
`## Execution record` and name what they supersede (AGENTS.md §10).

**No build, no relink, no product byte.** Browser arms use the shipping page
(`e2-editor-v8`), the machinery of `findings/evidence/096/probe_096_boundary_arrow.py`,
and real keys through `Input.dispatchKeyEvent`. The optional native arm uses a
harness binary only if one already exists; it is never built here.

---

## 0. What is already measured, and what this task adds

Measured (finding 096, `findings/evidence/096/RESULT-engine-side.md`): at a
document boundary an arrow key leaves the engine's move path waiting forever
because **no LOK callback of any type arrives** — the engine thread is alive,
the count of callbacks delivered to the registered handler is zero. The
three-way discrimination left "(a) the core broadcast nothing" standing and
stated explicitly that *why* the core is silent was not determined.

This task names the place in core where the silence is decided, and tests that
reading with a prediction only that reading makes.

## 1. The reading

The engine posts the arrow as a key event (`src/probe_engine.cpp`,
`postKeyEvent`) and arms `requiredCallback = EditorCaretOrSelectionCallback`,
satisfied by `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` or
`LOK_CALLBACK_TEXT_SELECTION` (`completePendingEditorOperation`,
`probe_engine.cpp:2098-2110`).

In core (`libreoffice-26-8`), the visible-cursor callback is emitted from
`SwVisibleCursor::SetPosAndShow` (`sw/source/core/crsr/viscrs.cxx:222-262`),
reached from `SwCursorShell::UpdateCursor` via `m_pVisibleCursor->Show()`
(`crsrsh.cxx:1820`). `SetPosAndShow` has **no** "rect unchanged → skip" guard;
the page-number notify beside it is change-guarded, the cursor notify is not.
`CallbackFlushHandler::enqueueUpdatedType` (`desktop/source/lib/init.cxx`)
fetches the payload at flush time and does not compare it with the previous
one. So there is **one gate**, and it is upstream of all of these:

* `SwCursorShell::UpDown` (`crsrsh.cxx:511-535`):
  `bRet = pTmpCursor->UpDown(bUp, nCnt); bRet |= SetInFrontOfLabel(false); …
  if (bRet) { … UpdateCursor(…); }`
* `SwCursorShell::LeftRight`: same shape, `if (bRet) UpdateCursor();`
* `SwCursorShell::LRMargin` (Home/End): same shape.
* `SwWrtShell::SimpleMove` (`sw/source/uibase/wrtsh/move.cxx`): `MoveCursor()`
  only `if (bRet)`; nothing else on the failed path.

**A boundary press is `bRet == false` — the cursor could not travel — so
`UpdateCursor` is never called and nothing reaches LOK.** Core is not failing
to deliver a signal; the key path has no "handled, nothing changed" signal at
all. The engine's contract (wait for a change-driven callback) cannot be met
by a no-op move, which is what half A's deadline repairs.

**The one exception the source contains, and the prediction it forces.**
`bRet |= SetInFrontOfLabel(false)` returns true when the cursor was flagged
"in front of the label" of a numbered/bulleted paragraph and the flag is now
cleared (`SetInFrontOfLabel` returns true iff the flag changed). The flag is
set by `LRMargin` when Home is pressed on a paragraph with visible numbering
while the cursor is *already* at the left margin (`bWasAtLM && bRet &&
HasVisibleNumberingOrBullet()`). Therefore: **on a document whose last
paragraph is a numbered item, Home, Home, ArrowDown at the last line must be
answered — the press still cannot travel, but the flag reset makes `bRet`
true, `UpdateCursor` runs, the cursor callback fires, and the session does not
wedge.** On a plain last paragraph the same three keys wedge. No other reading
of the silence predicts that difference.

A second consequence that separates this reading from the naive one ("no
change → no broadcast"): `SwCursor::LeftRightMargin` returns true whenever the
frame's `LeftMargin` succeeds, including when the cursor is already there, so
**Home at the start of a line is answered even though nothing moved** — it is
`bRet`, not movement, that opens the gate.

## 2. Arms and pinned cells

All browser arms: shipping page `e2-editor-v8` (the profile with no half A, so
a wedge is observable), viewport 1920x1080, file handed to `#file`, caret
placed by canvas pointerdown on the last ink band at its `past` fraction (the
line's last character — the T9 lesson: `near` plus one press moves within the
line), keys via `Input.dispatchKeyEvent` (rawKeyDown/keyUp with
`windowsVirtualKeyCode` 36 for Home, 40 for ArrowDown), a 60 s watch after the
final press, and the RAW CDP buffer, worker console, toast observer and
state-pill trace banked as the 096 probe banks them. Three attempts per arm.
Before any press each attempt records `lastLineEvidence` as T9's probe does
**and** the fixture's content.xml tail (the T9 lesson: ink finds the last
painted line, not the document boundary; the fixture's last element must be a
non-empty paragraph).

Per press the probe records: the `#s-latency` text after it, whether the
sink moved and its x/y before and after, the state pill, and the time to a
dead state relative to the **final** press.

| arm | fixture | keys | predicted | red for the reading |
|---|---|---|---|---|
| **F** flag | `a11y-audible-ends-numbered.odt` (a11y-audible with its final plain paragraph removed, so the document ends with the second numbered item; derived, sha256 recorded, content.xml tail banked) | Home, Home, ArrowDown | every press answered within 1 s (state `ready`, `#s-latency` non-empty); after the second Home the sink x is **left of** where it was after the first Home (the cursor sits in front of the label); after ArrowDown the sink x is back at or right of the first-Home x; no dead state in 60 s | ArrowDown leaves `#s-latency` empty and the session reaches `recoverable-error` (any time), **or** the second Home does not move the sink left (the flag was never set: then F is NOT_ESTABLISHED for the flag path, not red for the reading — say which) |
| **C** control | same fixture | ArrowDown only | wedge: `#s-latency` empty, dead state at 29–31 s, `rescue: none` | answered — then the fixture's last line is not a boundary and F proves nothing |
| **P** plain | `a11y-audible.odt` (ends with a plain paragraph) | Home, Home, ArrowDown | both Home presses answered within 1 s (nothing moves on the second: `bRet` from `LeftRightMargin`, not movement); ArrowDown wedges, dead at 29–31 s, `rescue: none` | ArrowDown answered — then Home-Home un-wedges for a reason that is not the flag and F's green may not be attributed to the reading; **or** the second Home is not answered — then "answered without movement" is false and §1's second consequence is retracted |

**Positive controls inside the batch**: C must wedge and P's ArrowDown must
wedge, or the instrument is suspect before the reading is.

**Optional arm U (native, separate, does not enter the verdict)**: if a
browser-free LOK harness binary from `tools/f059_native_*.cpp` already exists
on this machine, dispatch `.uno:GoDown` via `postUnoCommand` with
`bNotifyWhenFinished = true` at the boundary of the same fixture and record
whether `LOK_CALLBACK_UNO_COMMAND_RESULT` arrives (and its payload). It
measures remedy R2 in §5, nothing about §1. If no binary exists, record "not
run" and do not build one.

## 3. Verdict rule

The reading is **confirmed** iff F is green 3/3 (all three cells), C wedges
3/3 and P wedges 3/3 with both Home presses answered 3/3.

The reading is **refuted** iff C and P wedge as predicted **and** F wedges 3/3
with the second Home having moved the sink left 3/3 — the flag was set, the
reset happened, and still nothing was broadcast.

Anything else is **not established**, with the cell that failed named. In
particular F wedging while the second Home did not move the sink left means
the flag path was not reached in this product and the reading is untested,
not wrong.

Counts are the measurement: 2/3 is a result to bank, not a rounding.

## 4. Default conclusion if never run

The silence stays "measured, not explained" as finding 096 records it. The
reading in §1 may be quoted only as a reading of the source, never as the
cause.

## 5. What a confirmation licenses, and what it does not

* It names the mechanism: core's cursor-travel functions update and broadcast
  only when `bRet` is true; a no-op move is silent **by design**. It closes
  "why the core broadcasts nothing" in 096.
* It does **not** make this an upstream defect. LibreOfficeKit has no
  "key handled, nothing changed" signal; the defect was the engine's contract,
  and half A already repairs it. An upstream note, if ever written, would be
  a feature observation, not a bug.
* Remedies it ranks: **A** (landed, deadline) stands. **R2** — dispatch caret
  moves as `.uno:GoUp/GoDown/…` through `postUnoCommand` with
  `bNotifyWhenFinished`, and complete on `LOK_CALLBACK_UNO_COMMAND_RESULT`
  regardless of outcome — would give a real completion instead of a deadline,
  at the cost of a relink; arm U says whether the result arrives at a boundary.
  R2 is not started by this task.

## 6. Constraints on the executor (sonnet, main tree, headless Chrome)

* Probe: `findings/evidence/096/probe_096_flag_reset.py`, importing the 096
  probe's machinery; new fixture written under `findings/evidence/096/` (never
  `test-docs/` or `e1-fixtures/`), derived from `a11y-audible.odt` by editing
  content.xml and re-zipping with `mimetype` first and stored; sha256 and the
  content.xml tail recorded in the JSON. Shakedown of one F attempt banked as
  `flag-reset-shakedown-1.json`; a probe fix forced by the shakedown is
  recorded in the execution record and is not a criterion change.
* Reports: `flag-reset-F.json`, `flag-reset-C.json`, `flag-reset-P.json`,
  optional `flag-reset-U.json`; `RESULT-why-silent.md` (English) with the
  per-attempt cells, the verdict by §3, and observed-but-unexplained items
  under their own heading, recorded not explained.
* Forbidden: `build_cutover_page.py --write`; any `make`; any edit under
  `src/`, `sdk/`, `web/`, `editor-shell*/`, `dist/`, `wasm_sdk_probe/tools/`;
  editing `findings/096-*.md` (the main session appends); naming a cause the
  cells do not force; killing the user's desktop Chrome; `git push`; amend.
* Commit per unit, zh-TW messages, trailer
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`, no
  `Claude-Session:` line. Report `## SUMMARY` ≤30 lines.

## Execution record

*(appended by the executor after the runs; nothing above this line is edited)*

### Main-session source trace, before any run (2026-09-10, append-only; not a criterion)

The Home key's path to `LRMargin`, read after §1 was written and recorded so
the executor and the reviewer do not have to re-derive it:

* `officecfg/registry/data/org/openoffice/Office/Accelerators.xcu:2587-2590`
  (and `:4131-4134`): `HOME` → `.uno:GoToStartOfLine` for Writer text.
* `sw/sdi/swriter.sdi:2144`: `GoToStartOfLine` is slot `FN_START_OF_LINE`.
* `sw/source/uibase/shells/txtcrsr.cxx:130-132`: `case FN_START_OF_LINE:
  bRet = rSh.LeftMargin(false, false);`
* `sw/source/uibase/wrtsh/move.cxx:176-190`: `SwWrtShell::LeftMargin` →
  `SwCursorShell::LeftMargin()` (unless the cursor is read-only, which this
  document is not).
* `sw/inc/crsrsh.hxx:402`: `LeftMargin() { return LRMargin(true); }`, with
  `bAPI` defaulting to `false` (`:293`) — the branch that can call
  `SetInFrontOfLabel(true)` is therefore reachable from a real Home key.
* The fixture's numbered list style is
  `<text:list-level-style-number text:level="1" style:num-format="1"
  style:num-suffix="."/>` (a11y-audible.odt content.xml), i.e. a visible
  number, which `HasVisibleNumberingOrBullet()` requires.

Under LOK the key arrives through `postKeyEvent` → `SwEditWin::KeyInput` →
the accelerator table; whether that table is the one above on this build is
what arm P's "both Home presses answered" cell measures, so it is not assumed.

---

## Supersession 1 — the reading in §1 is wrong in two places; arms and verdict replaced before any run (2026-09-10, append-only)

**What forced this.** The codex review seat (B′ second review seat, thread
`01a08917-3840-7782-8150-60cc2989e434`) attacked §1 on two points; the main
session then read the cited lines and confirms both:

1. `SwCursor::UpDown` (`sw/source/core/crsr/swcrsr.cxx:2108-2125`, tdf#150457
   branch): on the first/last line, if the cursor is **not** already at the
   line's start/end offset it jumps there (`bRet = true`); if it **is**, it
   calls `pSh->UpdateCursor()` explicitly **and then** sets `bRet = false`.
   So at the boundary `UpdateCursor` *is* called. §1's "a boundary press is
   `bRet == false` so `UpdateCursor` is never called" is false for the arrow
   path. (The jump branch also explains T9's shakedown: a `near` click plus
   one ArrowDown moved within the line — it jumped to the line end.)
2. `CallbackFlushHandler` (`desktop/source/lib/init.cxx:1592-1600`) registers
   `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` (and `TEXT_SELECTION`,
   `CURSOR_VISIBLE`, …) in `m_states`, and at flush (`:2529-2537`) **skips the
   callback when the payload equals the stored state** — "Skipping duplicate".
   §1's "there is one gate and it is `bRet`" missed this second, downstream
   one; §1 read `enqueueUpdatedType` and not the flush loop.

**The corrected question.** Two mechanisms can produce "zero callbacks reach
the engine" at a boundary:

* **M1 (gate)** — `UpdateCursor` is not called, nothing is enqueued.
  Refuted at the source for the arrow path by (1); still the shape of
  `LeftRight`/`LRMargin`'s `if (bRet) UpdateCursor();`.
* **M2 (state dedup)** — `UpdateCursor` runs, `SetPosAndShow` notifies, the
  payload is fetched at flush and is identical to `m_states[type]`, so it is
  dropped. Silence is then a property of the flush handler, not of the cursor
  shell.

They predict differently for one cheap gesture: **a press that runs
`UpdateCursor` without changing the cursor rect.** Under M1 it is answered
(a callback is emitted because `bRet` is true); under M2 it is silent (the
payload is a duplicate). Home at a position already at the left margin is
exactly that press: `SwCursor::LeftRightMargin` returns true whenever the
frame's `LeftMargin` succeeds (`swcrsr.cxx`), so `LRMargin` calls
`UpdateCursor()` (`crsrsh.cxx:555-558`) with the rect unchanged.

Arm F of §2 does **not** discriminate: the flag reset changes the rect, so
both M1 and M2 predict "answered". It is withdrawn as a discriminator and kept
only as the E-cell check (does the in-front-of-label position move the rect).

**"Answered" is now measured at the engine, not from `#s-latency`.** The
engine stamps every completion with `callbackSequenceBefore/After`
(`probe_engine.cpp:2157-2160`) and the page carries the engine's callback
counter as `sourceSequence` (the 084 guard reads it). Per press the probe
records `sourceSequence` before and after; **answered = the counter advanced
and the state pill returned to `ready` within 1 s; silent = the counter did
not advance and the session reaches `recoverable-error` at 29–31 s** (on v8).
`#sink` x stays as a secondary cell only. The RAW CDP buffer and the worker
console are banked as before.

### Arms (replace §2; three attempts each; `e2-editor-v8`; fixture `a11y-audible.odt` unless stated; each arm ends at its last listed press and watches 60 s)

| arm | where | keys | M2 predicts | M1 predicts |
|---|---|---|---|---|
| **P′** plain, same-position Home | click mid-line on the plain line 「夾在中間的這一行不是清單 只是普通內文」 (its `near`+0.3 of ink width) | Home; Home | 1st Home answered (rect moved to margin); **2nd Home silent → wedge, dead 29–31 s, `rescue: none`** | 2nd Home answered, counter advanced, no wedge |
| **G** numbered, three Homes | click mid-line on 「編號的部分開始…」 (a numbered item) | Home; Home; Home | 1st answered; 2nd answered **and** sink x moves left (in front of the label); **3rd silent → wedge** | 3rd answered |
| **C** control | `past` on the last line (as T9) | ArrowDown | silent → wedge 29–31 s (both) | same |
| **N** tdf#150457 | `near` on the last line | ArrowDown; ArrowDown | 1st answered, caret x moves to the line end; **2nd silent → wedge** (both) | same |

**Positive controls**: C and N's second press must wedge, and P′/G's first
Home must be answered, in the same batch — else the instrument is suspect
first. G's second Home not moving the sink left is recorded as "flag path not
reached" and makes G's third press uninformative, not red.

### Verdict (replaces §3)

* **M2 confirmed**: P′'s second Home silent 3/3 **and** G's third Home silent
  3/3 (with G's second answered and shifted left 3/3), C and N as predicted.
* **M1 confirmed**: P′'s second Home answered 3/3 **and** G's third Home
  answered 3/3, C and N as predicted.
* Anything else: not established, cell named. 2/3 is banked as 2/3.

A silent press must show **counter not advanced**; a press where the counter
advanced but the session still wedged is a third thing (a callback the engine
rejected — 096's explanation (b)) and is banked under its own heading.

### What a confirmation licenses (replaces §5's first bullet)

* **M2**: core did run its cursor update; LibreOfficeKit's flush handler
  suppresses unchanged `INVALIDATE_VISIBLE_CURSOR` state by design
  (`init.cxx:1592-1600`, `2529-2537`), so a client that waits for a cursor
  callback after a no-op move waits forever. Not an upstream defect; a
  contract mismatch on the engine side, repaired by A. R2
  (`postUnoCommand` + `LOK_CALLBACK_UNO_COMMAND_RESULT`) becomes the principled
  remedy because `UNO_COMMAND_RESULT` is **not** in `m_states` and is delivered
  every time; the optional native arm U stands as its measurement.
* **M1**: §1 as written stands for the Home path only; the arrow path is
  explained by (1) above and M2 must then be re-attacked with another gesture.

Default conclusion and constraints (§4, §6) are unchanged; the new fixture of
§6 is **not needed** (no arm uses a document that ends in a numbered item) and
is not created. Report files: `flag-reset-P.json`, `-G.json`, `-C.json`,
`-N.json`, shakedown `flag-reset-shakedown-1.json`, `RESULT-why-silent.md`.

---

## Supersession 2 — the instrument is the raw lok stream, not sourceSequence; M1 is refuted at source, P′ isolates the dedup (2026-09-10, append-only)

**What forced this.** The codex review seat's second pass (same thread) landed
one fatal hit and one caveat; the main session read every line it cited and
confirms them:

1. **The "answered = sourceSequence advanced" cell of Supersession 1 is not
   usable.** `sourceSequence` increments only when `editorStateChanged` is true
   (`src/probe_engine.cpp:2562-2587`); `LOK_CALLBACK_STATE_CHANGED` (id 8)
   bumps a *separate* counter `stateChangedTotal` (`:2521-2534`) and does **not**
   move `sourceSequence`. `callbackSequenceAfter` is emitted only on a
   completion (`:2157-2163`), so a silent press produces none. And the product
   page writes only state/revision/pending/checkpoint to the DOM
   (`web/e2-editor-app.js`), so the counter is not readable from the page at
   all without injecting an `editor.getState()` probe (the 084 route). So
   "counter advanced" cannot be measured and, worse, could not separate "zero
   callbacks" from "id 8 arrived, not accepted."

2. **Read-only and ActionPend are silence causes outside M1/M2** (caveat).
   `SwWrtShell::LeftMargin(false,false)` scrolls and returns without touching
   `LRMargin`/`UpdateCursor` when `IsCursorReadonly()` (`move.cxx:176-189`) —
   excluded here because the fixture is editable. `UpdateCursor` early-returns
   under `ActionPend()` (`crsrsh.cxx:1971-1981`) — controlled inside P′ itself
   (see below), not assumed away.

**The instrument (replaces Supersession 1's counter).** Reuse
`findings/evidence/096/probe_096_engine_side.py`'s raw capture: it attaches to
the document worker and records, per press-window, every raw
`{"type":"lok","id":N,"payload":…}` line `onLokCallback` emits
(`probe_engine.cpp:2474-2483`) and every `editor-action-completed`. Per press
the new probe records `lokIds` (the set of raw ids in the window), whether a
completion for the press's request arrived, and the state pill / dead-state.
This is the instrument the engine-side round already used to bank "id 1 → 37 ms
completion" for the moving press and "none / 8,8,8" for the boundary press.

* **answered** = a raw `lok` id **1** (`INVALIDATE_VISIBLE_CURSOR`) or **2**
  (`TEXT_SELECTION`) arrived in the window **and** the press's request
  completed / the pill returned to `ready`.
* **silent** = no id 1 or 2 in the window **and** the session reaches
  `recoverable-error` at 29–31 s. The window's `lokIds` still shows any id 8,
  so "zero callbacks" and "id 8 only" are distinct cells, not merged.

**Why M1 is refuted at source for both paths, and what P′ then proves.**

* The gate `if (bRet) UpdateCursor()` is **open** for the boundary arrow:
  `SwCursor::UpDown`'s tdf#150457 branch calls `pSh->UpdateCursor()`
  explicitly **before** `bRet = false` (`swcrsr.cxx:2117-2125`). It is open for
  a same-position Home: `SwTextFrame::LeftMargin` returns **true
  unconditionally** (`sw/source/core/text/frmcrsr.cxx:672-696`), so
  `SwCursor::LeftRightMargin` is true, so `LRMargin` calls `UpdateCursor()`
  (`crsrsh.cxx:553-558`). So M1 ("UpdateCursor not called") is false wherever
  the rect is unchanged; the only remaining cause of silence is the flush-time
  dedup of the unchanged `INVALIDATE_VISIBLE_CURSOR` payload
  (`init.cxx:1592`, `2529-2537`), which is downstream of `onLokCallback`, so a
  deduped id 1 never even emits a raw line.

* **P′ is the isolation, not a direct observation of the dedup.** The dedup is
  internal and never surfaces a raw line; the argument is source + observation:
  the gate is *provably* open (LeftMargin→true), the rect is unchanged (same
  position), so P′'s second Home being **silent** leaves the dedup as the only
  explanation. Its own **first** Home (mid-line → margin, rect changes) being
  **answered** in the same attempt is the ActionPend/global-suppression control:
  it shows `UpdateCursor`'s emission does reach the engine in this gesture, so a
  silent second Home is the payload being a duplicate, not the pipe being shut.

### Verdict (replaces Supersession 1's verdict)

* **Confirmed — the silence is the unchanged-payload dedup**: P′ first Home
  answered 3/3 and second Home silent 3/3; G answered on all three presses with
  the second moving the sink left 3/3 (rect-change delivers); C and N wedge as
  predicted. The boundary arrow shares the mechanism because it too runs
  `UpdateCursor` with an unchanged rect (tdf#150457).
* **Refuted**: P′'s second Home answered 3/3 (a raw id 1 arrives despite the
  unchanged rect) — then the dedup is not operative and the boundary silence
  needs another cause; re-open with the native arm.
* **Not established**, cell named, otherwise. A press with a raw id 8 but no
  id 1/2 and a wedge is banked under its own heading (096 explanation (b),
  "a callback the engine rejected"), not read as either verdict.

### The native arm U is the only thing that separates dedup from a closed gate directly

Since the raw stream cannot see an enqueue that the dedup dropped, the direct
observation ("UpdateCursor ran, SetPosAndShow enqueued, flush skipped it") lives
only in core's `SAL_INFO("lok", "Skipping duplicate …")` (`init.cxx:2533`). That
needs a native LOK harness **with a built core** (`f059_native_*` link against
`$(LOBUILD)/instdir`, which is not present on this machine) — it is the
user's core build, not a browser arm. So U stays optional and, if no `instdir`
exists, is recorded "not run"; the browser verdict rests on the source premise
above, stated as a premise.

### §6 amendment

Probe base changes from `probe_096_boundary_arrow.py` to
`probe_096_engine_side.py` (the worker-attached raw-lok capture). File name
`probe_096_flag_reset.py` still stands. The `sourceSequence` cell is removed
everywhere; `lokIds` per press replaces it. No product change, no getState
injection (that would be new machinery for a cell the raw stream already gives).

---

## Cost correction on arm U (2026-09-10, append-only)

The owner corrected the cost framing: a native LibreOffice core build is ~1-2 h at most, not a relink-class obstacle. So arm U -- the native LOK harness that observes core's `SAL_INFO("lok", "Skipping duplicate ...")` (`init.cxx:2533`) **directly**, removing the reliance on the source premise (LeftMargin->true) the browser verdict rests on -- is a **reasonable planned step, not a last resort.** Supersession 2's "it is the user's core build" still holds (the owner runs it), but its framing of arm U as merely optional is downgraded: the browser verdict rests on a source premise, and this protocol has already spent two review rounds correcting the main session's source readings, so the direct observation is worth the build. Whether to spend it is the owner's call, offered with the browser result in hand; the exact build + run commands are teed up once T10 confirms the instrument and whether an `instdir` already exists.

---

### 2026-09-10 — T10 (append-only; the executor's run)

**Shakedown.** One P′ attempt, `findings/evidence/096/flag-reset-shakedown-1.json`. It measured exactly what Supersession 2 names on the first try (first Home answered, `lokIds=[1]`; second Home silent, `lokIds=[5]`, dead at 30.38s) -- **no probe fix was forced**; `probe_096_flag_reset.py` is committed as written.

**Twelve counted attempts, zero VOID, zero deviation from Supersession 2's prediction.** `flag-reset-P.json` (3), `-G.json` (3), `-C.json` (3), `-N.json` (3). Full detail and the per-press table are in `findings/evidence/096/RESULT-why-silent.md`; summary:

- P′: first Home answered 3/3 (`lokIds=[1]`), second Home silent 3/3 (`lokIds=[5]`, `sinkLeft` unchanged, dead 30.2-30.4s).
- G: first two Homes answered 3/3/3, second Home's `sinkLeft` left of the first's (112 < first's landing, matching "in front of the label") 3/3; third Home silent 3/3 (`lokIds=[8]`).
- C: the single press silent 3/3 (`lokIds=[]` -- the emptiest of the three silent shapes).
- N: first ArrowDown answered 3/3 (`sinkLeft` jumps 133→356, the tdf#150457 branch), second silent 3/3 (`lokIds=[5]`).

All positive controls held in the same batch (C/N wedge; P′/G's leading Homes answered).

**Verdict: M2 CONFIRMED**, by Supersession 2's rule read literally -- every clause met 3/3 (P′ 4/4 counting the shakedown), no cell not-established, no "third thing" (a raw id 1/2 with the session still dead) observed on any of the 12+1 attempts.

**Arm U: not run.** `$(LOBUILD)/instdir/program` (`wasm-lite/build-headless-probe/instdir/program`) exists but is the Emscripten/WASM cross-build (`soffice.wasm`/`soffice.js`), not a native harness. A native core build does exist (`native-lok-26-8/build/instdir/program/soffice.bin`, a real ELF binary) and this tree has several one-off native LOK harnesses built against native cores for *other* findings (059, 048, 046, ...), but none tests this question (dispatching a boundary move via `postUnoCommand`/`bNotifyWhenFinished` and reading `LOK_CALLBACK_UNO_COMMAND_RESULT` or the `Skipping duplicate` `SAL_INFO` line). Building one is compiling a new harness, which this task does not do. Recorded "not run -- no pre-existing native harness answers this question," not "no core build on this machine" -- the latter would have been false and is not what blocked arm U.

**Observed, not explained (see RESULT-why-silent.md for detail, not folded into the verdict):** the three arms' "silent" windows carry three different non-1/2 shapes (`[]` for C, `[5]` for P′/N, `[8]` for G); `noticeRescue` is `"none"` (the original zero-checkpoint notice) for C -- whose single press is the first and only key dispatched in that session -- and `"checkpoint"` for P′/G/N, each of which had a preceding answered press first; G's second Home also moves `sinkTop` by 4px. None of these bear on M1/M2 and none is explained here.

Evidence: `findings/evidence/096/probe_096_flag_reset.py`, `flag-reset-shakedown-1.json`, `flag-reset-{P,G,C,N}.json`, `RESULT-why-silent.md`.

---

## Arm U is runnable today — no build needed; pinned criteria before the harness (2026-09-10, append-only)

The owner chose to run arm U for the direct observation. It needs **no core
build**: `native-lok-26-8/build/instdir/program/libmergedlo.so` is
`ENABLE_SAL_LOG=TRUE` and already contains the string `Skipping duplicate [`,
so the flush handler's `SAL_INFO("lok", "Skipping duplicate [%d] …")`
(`desktop/source/lib/init.cxx:2533`) prints under `SAL_LOG="+INFO.lok"`. The
native harness pattern is `tools/run_f059_native_predicate.sh` + a `.cpp` that
`dlopen`s the core (`g++ -std=c++17 -I libreoffice-26-8/include … -ldl`), so
arm U is a new harness, not a build.

**What it observes that the browser cannot.** The dedup drops the enqueued id 1
upstream of `onLokCallback`, so the browser sees only "no id 1 + wedge." The SAL
log line `Skipping duplicate [1]` is emitted *by the dedup itself*, naming the
type it dropped — it is the enqueue the browser cannot see. Its presence after a
same-position Home proves id 1 **was** enqueued (gate open) and **was** dropped
(M2), removing the source premise the browser verdict rests on.

### The gesture (pinned)

Open `test-docs/e1/a11y-audible.odt` natively, register the callback, then, with
a stderr marker printed immediately before each key so the interleaved SAL log
is attributable per press:

1. `Ctrl+Home` (to document start),
2. `End` (caret to the first line's end — rect now away from the margin),
3. **press A** `Home` (caret to line start — rect CHANGES),
4. **press B** `Home` (already at line start — rect UNCHANGED).

After each key, pump the LOK main loop / sleep long enough for the flush handler
to run (model the wait on `f059_native_*`), and record every callback type
delivered to `onCallback` in that window.

### Criteria (AGENTS.md §1 form two — the log lines are generated by the core, not enumerated here)

* **CONFIRMED (M2 direct)**: press A delivers `INVALIDATE_VISIBLE_CURSOR`
  (type 1) to the callback **and** its SAL window has **no** `Skipping
  duplicate [1]`; press B delivers **no** type 1 **and** its SAL window **has**
  `Skipping duplicate [1]`. 3 runs, all three agree.
* **REFUTED**: press B's window has **no** `Skipping duplicate [1]` **and** no
  type 1 delivered — id 1 was never enqueued, so the silence is not the dedup;
  re-open the question (gate/`SetPosAndShow` not reached).
* **NOT ESTABLISHED**: no `lok` SAL lines appear at all (logging not wired as
  expected), or press A itself logs `Skipping duplicate [1]` (the stderr-marker
  correlation is wrong — an instrument red, not a product result), or the caret
  never reaches a line start (press A delivers no type 1).

### Instrument red cases (must be shown before the verdict is read)

* Press A changed the rect, so it must NOT log `Skipping duplicate [1]`; if it
  does, the per-press attribution is broken.
* A genuine caret move in the same run (the `End` in step 2, or a `Down`) must
  deliver type 1 and log no skip — the log is not emitting "duplicate" for
  real changes.

### Constraints

Harness `tools/f096_native_dedup.cpp` + `tools/run_f096_native_dedup.sh`
(modeled on `run_f059_native_predicate.sh`, adding `SAL_LOG="+INFO.lok"`).
Evidence under `findings/evidence/096/native/`: the raw `sal.log` **verbatim**
(not summarised — AGENTS.md §7, the payload not its summary), the per-press
callback capture as JSONL, and `RESULT-native-dedup.md`. No core build, no edit
to `libreoffice-26-8/**` or `dist/ src/ sdk/ web/ editor-shell*/`, no
`build_cutover_page.py --write`. The main session reads `sal.log` itself.

### Execution record — arm U (2026-09-10)

Ran against the existing `native-lok-26-8/build` (no build). M2 CONFIRMED
directly, 3/3: press B (same-position Home, rect unchanged) delivered no type 1
and logged `Skipping duplicate [1]: [1418, 1418, 0, 280]`; press A (rect
changed) delivered type 1 and logged no skip-[1]. Instrument red cases held.
Evidence: `findings/evidence/096/native/round-*/` (verbatim `sal.log` +
`presses.jsonl`), `RESULT-native-dedup.md`. Nothing above this line was edited.
