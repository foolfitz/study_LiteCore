# Two-seat review 1 (v23): disposition (2026-10-20)

**Inputs:**

| what | where |
|---|---|
| brief | `REVIEW-BRIEF-two-seat-1.md` (`152949f5`). Both seats got the same text |
| seats, verbatim (`ef673ecc`) | `codex-review-1.md` (`codex exec -s read-only`), `opus-review-1.md` (an opus subagent; experiments in `opus-experiments-1/`, run on a `git archive HEAD` copy) |
| design questions | ruled by fable in `ruling-fable-2.md` (`18e961d0`), on the owner's choice A, with the main session's source check appended |
| spec | the appended `SPEC-M3-ordered-commands` §15 (`516390c7`) |

**The rules** follow the v20 precedent (`../../link-batch/v20-shakedown/review/DISPOSITION.md`):
- **Fixed**: an honest run of the committed harness can produce the misjudged report, or the tool's own stated claim was not checked;
- **Claim corrected**: appended, the original kept;
- **Registered**: everything else.

This is the one review (§34.3) of `read_results.py` and `read_n1.py`. Their fixes count as repaired because of review, and from now on those counts must stay 0.

## The main session's checks before disposing

These are in `disposition-1/`.

- **`n1-outside-window.txt`**: in the committed N1 run, 0 reply-type callbacks arrive later than the estimated first poll + 1500 ms, over the whole measured step. A positive control (one callback at +1700 ms) is found.
  - **The first version of the script was wrong.** It counted 115 callbacks "after the first poll". `returnedMs` is stamped when the LOK call returns, but `firstPollAfterReturnMs` is measured from a stamp taken after the at-return reads, so the estimate was early. The docstring keeps the account.
- **`grouping/`**: undo grouping, measured natively (see its README).
  - Under `uni1`, ops 20–25 of 25 Backspaces, and of 25 Deletes, return a `.uno:Undo` payload byte-identical to the previous op's, while each op deleted a character.
  - This moved the main question to the ruling.

## The readers: fixed, with red cases (`red-old-vs-new.txt`: each case judged by the reader at HEAD and by the fixed reader)

| # | what | reader | HEAD → fixed on its red case |
|---|---|---|---|
| F1 | The records-only D7 cells now gate the verdict; every D8 observation must be present; D7's records print per round (they had printed round 1 only) | `read_results.py` | missing D7 cell: C-HOLDS → NE; D7 q trigger unfired: C-HOLDS → NE |
| F2 | Each cell needs exactly one `run-log.jsonl` entry, with exit 0. This catches a reused directory, a re-run cell, and a child that crashed after writing its records | both | duplicate entry: HOLDS → NE (both readers); child exit −11 / −6: HOLDS → NE (both) |
| F3 | An unclean cell gives NE, never a FAIL (D8, N1a, N1c) | both | unclean cell failing D8: C-FAILS → NE; late cursor in an unclean cell: N1-FAILS → NE; N1c reversed on an unclean cell: N1-FAILS → NE |
| R2-a | d4 presence witness (ruling 2 §2.6): the step must hold `.uno:Bold=true`. Without it, "Bold dropped" lands exactly as Writer's order does. Every committed d4 cell has the witness (15/15) | `read_results.py` | witness removed: C-HOLDS → NE |
| R2-b | Fewer than 5 rounds is not a counted reading: N is printed, and the exit code is 2 | both | (CLI rule) |
| R2-c | `INVALIDATE_TILES` is removed from N1a's reply types (ruling 2 §2.5) | `read_n1.py` | late tile: N1-FAILS → N1-HOLDS (intended) |

**Coverage added in the same batch.** These cases are not fixes: they cover rules the readers already had.
- Ruling 1 §2.6 red case (b), "rounds disagree", was **never implemented** before: the committed (b) broke one landing on a one-round smoke. A two-round synthetic copy now carries it, with its own control. HEAD already judged it C-FAILS: the rule existed but had no red case.
- `read_n1.py` now has one synthetic late callback per reply type, five types.

**New function** (ruling 2 §2.2, form 2): `read_n1.py --on-time-list` generates the on-time and late `STATE_CHANGED` pairs from the records. Its red case: making Bold late moves it out of the list. On the committed N1 run (`on-time-list-out-n1.json`) it gives 8 on-time pairs, `(U.uno:Bold, .uno:Bold)` among them, and 44 late or mixed.

**Self-tests:** `read_results.py` 5 → 13, `read_n1.py` 6 → 17, all as required (`self-test-read_results.txt`, `self-test-read_n1.txt`). Each smoke-based case copies the committed smoke. The `read_results.py` control keeps the last run-log entry per cell, because the smoke's d7i was re-run after its placement was corrected (`smoke/NOTES.md:23-26`).

**Re-judged with the fixed readers, no committed verdict moved:**
- `rejudge-out-with-fixed-reader.txt`: C-HOLDS, D8 holds. The only differences from `out/reader-output.txt` are D7's per-round agreement (5/5 for every D7 record) and `N = 5 rounds`.
- `rejudge-out-n1-with-fixed-reader.txt`: N1-HOLDS, identical except for `N = 5 rounds`.

## Claims corrected (appended; originals kept)

- **Spec §15.2 (`516390c7`):**
  - `postUnoCommand` is synchronous only with a listener, or for a non-`Asynchron` slot;
  - §5.2: a tick with no user event **at entry**, and the reply goes before a queued command;
  - §5.8's "within one flush tick" is withdrawn;
  - "`STATE_CHANGED` is timer class" is withdrawn in favour of the generated list;
  - N1a's tile clause is withdrawn, and its window is bounded (the residual blind spot is named);
  - N1c's label;
  - §14's "0 forged" now means geometry only;
  - §4 rows 11 and 13.
- **Readers' docstrings:** the exit contract ("complete" became "a verdict was reached, N ≥ 5"); the window bound; "the X step fired" is a q-mode fact.
- **`../native/ordered-commands/README.md` and `../model/README.md`:** an appended section each.

## Registered

| item | seat | note |
|---|---|---|
| N1c is a timing effect: a broken `anyInput` could separate by chance, and noise can give NE or FAIL | codex Q1, Q2 | The engine's `anyInput` term gets a direct unit red case in the diagnostic code |
| d1's Backspace is a Writer no-op, so dropping it lands as seq | opus Q1 | No witness can exist (ruling 2 §2.6) |
| 15 of 100 N1 ops have no reply-type callback | opus Q3 | Under C the reply reads state at the poll |
| the coverage census (5/25, 7/18 before this batch) | codex Q5, opus Q5 | Every fix and the three named holes now have cases. The rest stay as a census |
| `EditorDrainScheduler` under `OXSDK_FINDING_016_SCHEDULER_PROBE` | opus Q6 | Now a §9.2 precondition read from the build record (spec §15.4) |
| `.uno:Delete` on empty table cells answers `changed:true` | opus Q7.4 | Pre-existing; a §9.3 table arm |
| the harness's native poll callback has no re-entrancy guard against `Reschedule` (HTML/Markdown import) | opus Q6 | A note for future native arms |
| the brief named `smoke-n1/NOTES.md`, which does not exist | both | The brief's error (main session) |

## Ruled (ruling 2), and what follows

- **Caret delete:** the undo payload is paired with the focused-paragraph read, guarded to mid-paragraph positions. It is **measured natively before any §5.4 code**: g1/g2 plus the a11y read, `uni1` and `seq`, N=5, three controls. The default is the barrier.
- **Collapsed-caret format:** the reply reads the item on the on-time list. 059's check stays.
- **Object click:** L-object-click-shell-switch, plus a native arm.
- **Content after the reply:** limits and records.
- **One command per poll:** an engine unit red case, plus a §9.2 cell with a depth ≥ 2 non-vacuity rule.

## §34.4

| | count |
|---|---|
| this disposition: repaired because of review | **+9**: `read_results.py` F1, F2, F3, R2-a, R2-b; `read_n1.py` F2, F3, R2-b, R2-c |
| this disposition: repaired because of execution | 0 |
| new | the on-time list (ruled function) |
| this stretch, because of execution | **+1** (the 0.2.28 chain's guard, v22 spec §14.5) |
| **running total since 10-14b** | **33 / 27** |
| these two readers from now on | repaired because of review must stay 0 |
