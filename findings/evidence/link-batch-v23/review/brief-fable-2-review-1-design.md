# Brief for fable, ruling 2 (v23): the design holes two-seat review 1 found in spec §5, before any engine code

**Authority.** The owner, in the conversation on 2026-10-20 (~15:45). Asked how to settle the design holes the review found, the owner chose **"A: 叫 fable 裁決"**. The owner is present and will read §1.

**Language.** §1 is plain-language zh-TW for the owner. The rest is English.

**Constraints:**
- Read-only. No ddev, no browser, no make, no native LibreOffice run.
- Targeted reads only. No search of the whole repository, and never `cd` into `libreoffice-26-8/`.
- Use absolute paths. `R` = `/home/jiajun/LibreOffice/study_LiteCore`, `lo/` = `R/libreoffice-26-8/`, `ev/` = `R/findings/evidence/link-batch-v23/`.

## Since addendum 1

- **The spec is pinned.** `R/specs/SPEC-M3-ordered-commands.md` was pinned at `b9080313`. §14 was appended later: the model in two modes.
- **N1-HOLDS** (`0ecec9a0`).
- **The model** (`76fe206f`, `ev/model/README.md`):
  - in its threaded mode it still prints 27,744 / 2,448 / 5,474 / 3,868;
  - its new mode C has 0 Writer-divergent runs and 0 forged replies in all eight shapes;
  - two red cases remove a §5.2 rule each and print forged replies.
- **Two-seat review 1** (`ef673ecc`). The brief is `ev/review/REVIEW-BRIEF-two-seat-1.md`. The seats, verbatim:
  - `ev/review/codex-review-1.md`;
  - `ev/review/opus-review-1.md`, with its experiments in `ev/review/opus-experiments-1/`.
- **The main session's checks** (`ev/review/disposition-1/`):
  - `n1-outside-window.txt`: the committed N1 run has 0 reply-type callbacks beyond each op's 1500 ms window, with a positive control.
  - **`grouping/README.md`, measured natively:**
    - under `uni1` (C's drive), ops 20–25 of 25 Backspaces, and of 25 Deletes, through `Name: ` + 30 `_` return a `.uno:Undo` payload byte-identical to the previous one, while each deleted a character;
    - the saved text is `Name: _____`;
    - `seq` shows the same from op 21.
    - The cause is Writer's grouping into one `SwUndoDelete`, whose comment saturates through `ShortenString(…, 20, …)`. The source lines are in the README.

## Questions (each answered with its form, per CLAUDE.md §1, and its default if never done, per §2)

- **Q1. What proves a caret delete under C?**
  - What the spec says: §5.4 moves every caret Backspace/Delete to the user's own key, with "undo changed → `verified-key-undo`". §5.5 adds "undo, caret and selection unchanged → `verified-boundary-noop`".
  - What is wrong with it:
    - the grouping measurement breaks the first;
    - for forward Delete, all three are unchanged after a real deletion, so the spec answers a no-op with the wrong meaning;
    - for Backspace, neither branch applies;
    - opus also notes that "the caret unchanged at return" has no named synchronous source: the caret cache refreshes only in the flush. The one synchronous read the engine has is the a11y focused paragraph (`R/wasm_sdk_probe/src/probe_engine.cpp:1958-1980`).
  - The constraints are the frozen client's tuples (`R/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js:146-148`, `:161-166`, `:355-391`):
    - `verified-key-undo` needs `changed:true`, revision +1 and `keyUndo.actionsAfter ≥ 1`;
    - `verified-boundary-noop` needs `changed:false` and an unchanged revision;
    - the names stay (addendum §2.2).
  - What witness, or what change, makes the delete's answer true? Candidates the main session sees, none recommended:
    - (a) a synchronous content read beside the undo payload, such as the focused paragraph's text and length, or some other read you name;
    - (b) turning off undo grouping for the engine's keys. That changes Writer's undo granularity for the user;
    - (c) the barrier kept for caret deletes. Addendum §2.2 withdrew it.
  - Also say how the meaning of a completion, not only its string, gets tested. Opus showed that the model's C mode chooses completions from its own oracle: 174,672 mislabelled deletions still exit `ok` (`ev/review/opus-experiments-1/model/E6_lying_noop.summary.txt`). The §5.8 form-one table checks strings only.
- **Q2. The inline format at a collapsed caret, and the claim that "`STATE_CHANGED` is timer class".**
  - §5.2 and §5.3 A7 forbid reply fields taken from the `STATE_CHANGED`-fed cache.
  - In d4, Writer answers `.uno:Bold` at a collapsed caret with `success:false`. Today's engine rescues that through 059's check of that cache (`probe_engine.cpp:2827-2841`).
  - N1's own data, measured:
    - `.uno:Bold=true` and `.uno:ModifiedStatus=true` arrive in the command's own flush, before the first poll, 5/5 (`opus-experiments-1/native/a9_bold_state.out`);
    - the table and clipboard states arrive late (`a10_state_split.out`).
  - What does the reply for a collapsed-caret format read? Is the type-level claim (and L-timer-class-callbacks, §11) withdrawn in favour of the measured split?
- **Q3. An object click under C.**
  - A click that selects a frame or a drawing object sets `g_bNoInterrupt` (`lo/sw/source/uibase/docvw/edtwin.cxx:3289`, `:3874-3880`).
  - `SwView::AttrChangedNotify` then defers `SelectShell` to a 120 ms timer (`lo/sw/source/uibase/uiview/view.cxx:567-587`, `:600-622`, `:844`).
  - Under C, the page's next command can arrive about two ticks later and run against the pre-click shell stack. Slots resolve per shell.
  - §7 Q3's default is "照 Writer". Which Writer: settled (seq), or within two ticks? Does the click's completion wait for the shell switch, or is this a named limit plus a §9.3 arm?
- **Q4. Content that changes after the reply.**
  - `SwDocIdle` updates fields after a command returns (`lo/sw/source/core/doc/DocumentTimerManager.cxx:142-151`, `:184-214`). This is unmeasured.
  - Opus also notes that spelling, smart tags, autocomplete and word count run as scheduler tasks that never consult LOK's `anyInput`.
  - Codex (Q8) adds that `CheckTimeout()` runs one scheduler task before the `anyInput` test, so a reply can wait behind it. A task can also post a user event, and the poll then runs without a second user-event check (`lo/vcl/headless/svpinst.cxx:442-481`).
  - Which of these are named limits, which need a §9.2 cell, and what is the default?
- **Q5. Two places where the spec points at nothing.**
  - N1a's `INVALIDATE_TILES` clause is empty natively: the harness never sets a visible area, and 0 tile callbacks occur in any native run (`opus-experiments-1/native/a11_tiles_anywhere.out`). Is the clause withdrawn, or moved to §9.2?
  - The model's README and §14 say "one command per poll" is checked "in the engine (§9.2)", but §9.2 has no such cell. Should it be an engine unit red case in the diagnostic code (the next step), or a §9.2 cell (CLAUDE.md §9's four conditions)?

## The main session's proposed disposition of everything else (flag only what you disagree with)

These rules are as the v20 precedent (`R/findings/evidence/link-batch/v20-shakedown/review/DISPOSITION.md`):
- **Fixed**, only where an honest run of the committed harness can produce the misjudged report, or where the tool's own stated claim is not checked;
- **Claim corrected**: appended, the original kept;
- **Registered** otherwise.

This is the readers' one review (§34.3). Their fixes count as repaired because of review.

| item | seats | proposed |
|---|---|---|
| F1: the D7 (records-only) cells never gate the verdict. A missing or unfired D7 cell still prints C-HOLDS, D8 silently skips it, and D7's "5/5" is printed from round 1 | codex Q3, Q4; opus Q3, Q4 | **Fixed** in `read_results.py`: every cell of every arm must be clean, and every D8 observation present, or the verdict is NOT-ESTABLISHED. Red cases first |
| F2: the readers ignore `run-log.jsonl`. A reused output directory, a duplicate execution or a non-zero child exit goes unnoticed | codex Q4 | **Fixed** in both readers: each cell needs exactly one run-log entry, with exit 0. The committed directories have 165 and 70 entries, one per cell, all exit 0 |
| F3: D8 and N1a judge unclean cells and print `C-FAILS`/`N1-FAILS` with exit 0 | opus Q4 | **Fixed**: an unclean cell gives NE, never a FAIL |
| exit 0 "iff complete" | codex Q4 | **Claim corrected** (docstrings): exit 0 iff a verdict was reached |
| "the X step fired" is constant `true` outside q (`oc_native.cpp:371`) | opus Q3 | **Claim corrected** (native README) |
| N1a's window is bounded (1500 ms, or the step's quiet window) | codex Q1; opus Q1 | **Claim corrected** (spec §9.1). The committed run has 0 outside it (checked) |
| N1c is a timing effect: a broken `anyInput` could separate by chance, and noise can give NE or FAIL | codex Q1, Q2 | **Registered**. The engine's `anyInput` term gets a direct red case in the diagnostic code |
| a broken core could drop d1's Backspace or d4's Bold and land as seq (Writer's no-ops); 15 of 100 N1 ops have no reply-type callback | opus Q1, Q3 | **Registered** (arm design) |
| the coverage census: 5 of 25 and 7 of 18 rules have a red case | codex Q5; opus Q5 | **Registered**, except that every fix gets its red case |
| §1 says `postUnoCommand` is synchronous, but `.uno:Escape` without a listener stays posted (it is `Asynchron`); it completes before the next poll | codex Q6; opus Q6 | **Claim corrected** (spec §1): only with a listener, or for a non-`Asynchron` slot |
| §5.8 says "within one flush tick". One scheduler task per tick runs before the poll | codex Q8; opus Q8 | **Claim corrected**: at the first poll after return, with no fixed tick count (Q4 for the rest) |
| `EditorDrainScheduler` (`ProcessEventsToIdle`) under `OXSDK_FINDING_016_SCHEDULER_PROBE` | opus Q6 | **Registered**: the diagnostic profile must not define that macro (§5.7 rule 1) |
| `.uno:Delete` on empty table cells answers `changed:true` with no change. Pre-existing, not C | opus Q7.4 | **Registered** as a §9.3 table arm |
| the model's zero comes from the loop shape and from completions chosen by an oracle; "forged" compares rectangles only; its printed run counts are 22–135× the distinct scenarios | codex Q9; opus Q9 | **Claim corrected** (`ev/model/README.md`, spec §14). The completion-meaning test is Q1 |
| `smoke-n1/NOTES.md` named by the brief does not exist | both | recorded: the brief's error |

## Shape

Follow ruling 1:
- `## 1. 裁決（白話，給擁有者）`;
- `## 2. Answers (English)`, numbered, each with its form and its default;
- `## 3. Facts checked`;
- `## 4. What the main session does next`.

Cite every line you rely on, re-read by you.
