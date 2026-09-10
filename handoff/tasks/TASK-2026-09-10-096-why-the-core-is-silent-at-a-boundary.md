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
