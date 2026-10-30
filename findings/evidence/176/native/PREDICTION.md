# Finding 176, engine item C, native arm: criteria registered before the harness ran

Registered 2026-10-30 ~11:25 +0800, before `tool/f176_native.cpp` was compiled. Ruling: `../RULING-fable-2026-10-30.md` §3.3 step 1 ("a caret-paragraph-scoped observable that does not need a selection -- candidate: the caret paragraph's list state as the ordered engine can read it (e.g. the `.uno:DefaultBullet` / numbering state), stated as a candidate to measure, not a prescription").

## The question

Is there an observable that

1. the ordered engine already receives before it composes the reply (a callback delivered before the first poll after the command returns -- the engine's `gOrderedProof.stateItems` window),
2. is about the paragraph the list action was dispatched to, not about whatever `.uno:SelectText` covered, and
3. says whether the action applied?

## Candidate

**O-item**: the `.uno:DefaultBullet` STATE_CHANGED items in the bullet command's own window -- callback index from the op's start (`cbIndexAtStart`) to the first poll after it returned (`cbIndexAtFirstPoll`) -- and the **last** value among them (the engine's cache keeps the last one; `CallbackFlushHandler` may also have merged them).

Why it is plausible (read, not measured): `SwTextShell::GetState` answers `FN_NUM_BULLET_ON` from `SelectionHasBullet()` (sw/source/uibase/shells/textsh1.cxx:4238); at the dispatch the cursor is collapsed in the dispatch paragraph. Why it might fail (also read): `SelectionHasBullet()` iterates every paragraph of the selection (sw/source/core/edit/ednumber.cxx:183), so if a state update is computed while the overshooting selection exists, it describes the selection; and finding 030 measured that an unchanged value sends no item.

## Ground truth

The saved document, never the callbacks (finding 030's rule): after the measured step the harness saves FODT; the reader finds the target paragraph by its index among the body's `text:p`/`text:h` and reads whether it is inside a `text:list`, and that list style's kind (bullet or number).

## Cells (mode `uni1ai`, 5 rounds each, run-major; `tool/run_cells.py` is the table)

| cell | class | what |
|---|---|---|
| a1-text-mid | A | control: a paragraph with text |
| a2-empty-mid | A | finding 046's cell: an empty paragraph, a paragraph after it |
| a3-enter-mid | A | F3's recipe shape: End, Enter, bullet the new empty paragraph |
| a4-empty-last | A | 083's path: the empty paragraph is the last one |
| a5-blank-one | A | 083/173's path: the host's blank template (sha 7e6221b6...) |
| n1-sham-empty-mid | N | the engine's sequence with `On:false` on a plain empty paragraph: nothing applies |
| n2-sham-empty-before-list | N | the same; the overshoot reaches a bulleted paragraph |
| n3-sham-empty-after-list | N | the same; the paragraph above is a bullet |
| r1-r6 | R | recorded only: no-op on an empty bullet, dispatch without the readback, numbering, none, heading, an empty paragraph before a list item |

A clean round: exit 0, a `done` record, the env record has `SAL_LOK_OPTIONS=unipoll`, the init record `anyInputRegistered: true`, the measured record not capped, the op ran (`format` present for an F op), the file saved.

## Predicates

- **P0 (the cells are the browser's cells).** a2 and a3: the readback is TEXT and its markup has two or more block-level paragraphs (the 046 overshoot). a4 and a5: the selection type after `.uno:SelectText` is NONE (083/173's `select-text-returned-none`). a1: one block. A deciding cell that fails P0 in a clean round is NE for this question, not evidence either way.
- **P1 (it says applied when it applied).** Every clean round of every A cell: the saved target paragraph is in a bullet list, AND the window carries at least one `.uno:DefaultBullet` item before the first poll, AND the last such item is `.uno:DefaultBullet=true`.
- **P2 (it does not say applied when nothing applied).** Every clean round of every N cell: the saved target paragraph is not in a list, AND no `.uno:DefaultBullet=true` item arrives in the window before the first poll.

## Verdict (by `tool/read_cells.py`, from the records only)

- `WITNESS-HOLDS`: 5 clean rounds in every A and N cell, P0 in each, P1 in a1-a5, P2 in n1-n3.
- `WITNESS-HOLDS-MID-ONLY`: as above, except P1 fails in a4 or a5 (and holds in a1-a3): C would cover 046's cell and not 083's path, which then stays a toast (ruling §3.3 step 3 says to report exactly this).
- `WITNESS-FAILS`: P2 fails in any clean round, or P1 fails in a1, a2 or a3.
- `NOT-ESTABLISHED`: fewer than 5 clean rounds in a deciding cell, or P0 fails there.

Recorded, deciding nothing: on-time vs late per (cell, key) for every STATE_CHANGED key; the r cells' items and saved state; whether the item arrived during the call or in the flush.

## If this is never run

Ruling §3.5: the toast stays on every empty-line bullet and nothing in a spec may cite the 046 cell as verified.

## Amendment 1 (2026-10-30 ~11:30 +0800, after the smoke, before the counted run): recorded fields only

The smoke (`smoke/`, one round of a2, a5, n2, binary `build-01`) showed `.uno:DefaultBullet=true` arriving **after** the first poll in a2 and a5 -- the timer class N1b recorded for STATE_CHANGED. That predicts P1 fails; the criteria above are **not** changed by this, and the counted run judges them as registered.

Added, deciding nothing, so the run also records the inputs of the next candidates:

1. every F op records the whole `.uno:Undo` payload immediately before its first call (`format.undoAtStart`); `atReturn.undo` already had it after the last call;
2. op G = F without the restore before `.uno:SelectText` (the select runs from where the dispatch left the cursor), on every A and N cell, as class R cells `g-<cell>`.

The harness is rebuilt (`build-02`); `build-01` and `smoke/` stay as the smoke's record.

## Amendment 2 (2026-10-30 ~12:12 +0800, before any of these cells ran): ruling 3 Q6.3's cells and its stop rule

Ruling 3 (`../RULING-fable-2026-10-30-c.md`) accepts C (collapsed route; a multi-block readback judged by the existing first-block predicate; no restore before the select, op G) for all five paragraph actions **conditional on** these cells, and names the stop rule. Registered here before any of them ran. Same harness binary (`build-02`), same mode (`uni1ai`), 5 rounds each, run by `tool/run_cells_q63.py` into `out-q63/` with fixtures in `fixtures-q63/` (`tool/make_fixtures_q63.py`); `run_cells.py`, `make_fixtures.py` and `out/` are not touched. Every cell ends with the harness's `L` locator (Shift+End, Shift+Home from the caret) before the save, so where the caret is after the final restore is recorded.

| cell | op | fixture | what |
|---|---|---|---|
| b0-heading-control | F Heading 1 | empty-heading-mid | fixture control: the empty paragraph loads as a heading (saved `text:h`) |
| b1f-body-on-empty-heading | F Text body | empty-heading-mid | ruling Q2.1's hypothesis about F's restore after a heading shrinks |
| b1g-body-on-empty-heading | G Text body | empty-heading-mid | the same under G |
| a6f-empty-empty | F bullet | empty-empty-mid | an empty paragraph followed by another empty one |
| a6g-empty-empty | G bullet | empty-empty-mid | |
| n6f-sham-empty-empty | F sham (On:false) | empty-empty-mid | |
| n6g-sham-empty-empty | G sham | empty-empty-mid | |
| g-r3-number-empty-mid | G numbering | empty-mid | the G twin of r3 |
| g-r4-none-empty-bulleted | G RemoveBullets | empty-bulleted-mid | the G twin of r4 |
| g-r5-heading-empty-mid | G Heading 1 | empty-mid | the G twin of r5 |

**Stop rule (ruling 3 Q3), judged by `tool/read_q63.py`:** for every G cell (b1g, a6g, n6g, g-r3, g-r4, g-r5): 5 clean rounds, and in every round the first block's state (the same derivation as `read_cells.py`'s recorded comparison) equals the saved dispatch paragraph's state. A G cell that fails it -> its action is **out of C's scope** and a finding; fewer than 5 clean rounds or b0 not saved as a heading -> NOT-ESTABLISHED for that action. F cells are recorded only. The verdict lists, per action (bullet, number, none, heading, body), `IN-SCOPE`, `OUT-OF-SCOPE` or `NOT-ESTABLISHED`; bullet's G evidence also counts the first run's g-a2/g-a3/g-n1..n3.

Caveat carried from ruling 3 §2: the first-block state here is the reader's regex derivation, not the production parser; the production parser is pinned separately on the recorded HTML (ruling 3 Q6.2, a unit test in the v27 spec), and that test must include a6's and b1's HTML.
