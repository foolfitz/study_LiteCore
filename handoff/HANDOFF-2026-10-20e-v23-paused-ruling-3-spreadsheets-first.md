# Handoff, 2026-10-20e: v23 paused after ruling 3 and its red cases; the owner put spreadsheets first

**First line:**
- **The owner chose A at ~18:30: spreadsheets first.** v23 (ordered commands, candidate C) is paused at a clean point. Nothing of it is wired into the engine, and nothing is linked.
- **The shipping core has neither Calc nor accessibility.** v8–v22 link `wasm-lite/build-headless-probe` (`--with-wasm-module=writer`, `ENABLE_WASM_STRIP_CALC=TRUE`, `ENABLE_WASM_STRIP_ACCESSIBILITY 1`). Only `build-a11y-gate0` (`writer calc`, a11y on) has either. `e2-editor-v12` was built on it.
- ddev still runs host 0.2.28 (`0870695`), the uncounted candidate for daily use; the nominal shipped version is still 0.2.26.

This continues `HANDOFF-2026-10-20d-review-1-ruling-2-native-arms.md`. Its Next 1 and Next 2 are done; its Next 3 was replaced by ruling 3 and then paused. The main session was opus.

## What happened (commits in order)

1. **Ruling 3 brief** (`b86c8277`; `findings/evidence/link-batch-v23/review/brief-fable-3-diagnostic-scope.md`). The owner chose "送 fable 裁決" for the diagnostic profile's scope.
2. **The object-click counted run** (`ad8d1e6a`; `native/object-click/README.md`):
   - VERDICT O-RECORDED: every arm lands as seq, 5/5;
   - the command came 0.1–0.2 ms after the click, inside Writer's 120 ms shell-switch timer;
   - the first run was cut at 72/80 by the session restart and is kept as `out-interrupted-1726/`.
3. **Ruling 3 with its §5 addendum, and spec §16** (`00aa108d`):
   - the diagnostic carries v23's delete path, not option B;
   - **§5 (after the main session found the core fact):** §15.1's precondition was wrong for the shipping line. The paired decider is compiled only on a core with a11y. On the current core the caret delete is the barrier in C's shape, in one command: K1, then `readSelection()` at return. NONE gives noop; a unit gives `.uno:Delete`; a separator gives a RESET restore and the user's key, judged by undo. The RESET restore must be measured natively first. L-C-number-or-indent is open again on the shipping core;
   - staging withdrawn means one command; replies are composed only at the poll (§5.7 rule 5); a proof absent at the poll is a typed refusal there;
   - ruling 2's source check is corrected by appending.
4. **The N1 second run** (`d85f13fc`; `native/ordered-commands/README.md`, last section):
   - N1-HOLDS under the format-state rule, with no tile clause;
   - the on-time list carries `.uno:Bold`, `.uno:Italic`, `.uno:Underline` and `.uno:Strikeout` on time 5/5.
5. **v23 red cases, unwired** (`2266b090`):
   - `src/ordered_poll.hpp` with its test and four mutations;
   - `src/caret_delete_witness.hpp` (a11y core only), with its G-run fixture, its generator `tools/make_caret_delete_fixture.py --check`, and five red cases;
   - `src/reply_state_reads.hpp` with `tests/test_reply_state_reads.py`, held against the on-time list;
   - `tools/check_v23_diagnostic_build.py`: self-test 11/11. It is **red against the Makefile by design** until the diagnostic rule exists.

## v23: what remains when it resumes (ruling 3 §5.4, in order)

1. **The tool's additions** (`tools/check_v23_diagnostic_build.py`):
   - the `probe.wasm` byte read (`core-built-without-accessibility` present, `lok-lacks-setAccessibilityState` absent; spec §16.5);
   - a feature-link mode asserting that the diagnostic define is absent;
   - red cases first for both.
2. **The native RESET-restore arm** (spec §16.2):
   - K1 Shift+Left at a P2 start (plain, numbered, first-line-indented), RESET at the pre-K1 caret rect, `readSelection()` NONE, then Backspace, compared against Backspace with no K1;
   - red case: a RESET one line off;
   - N = 5.
   - The harness needs a new op (setTextSelection RESET at a recorded point). Pin its `ARMS.md` before the count.
3. **The rest of the red cases:**
   - rule 5: a cursor-then-selection flush; the reply must carry both;
   - the proof-absent refusal, both branches;
   - the caret delete's three K1 branches against a synthetic `readSelection()` oracle;
   - the format barrier as one command: SelectText selecting nothing is refused at the poll;
   - the V23 routing check: no action reaches `startSelectionBarrierDelete`'s old stage machine or `startMergeKeyUndo`; `engineLoop` is not compiled.
4. **Then the wiring.** Write it under `OXSDK_E2_V23_LINK_BATCH`, with `OXSDK_MAINLOOP_ENGINE` and one diagnostic-only define. Then the Makefile rule `E2_V23D_*` with `link_v23_diagnostic` (`link_product_stack_1m` plus `-sSTACK_OVERFLOW_CHECK=2`). Then the runbook. **The owner links.**
5. **ABI 5** for the diagnostic. The core stays `build-headless-probe` (one variable). A core switch is its own link.

## Hazards

- **Never `cd` in shell commands.** It slipped once this stretch, while running `unittest`, and was reverted at once. Use absolute paths, and `python3 -m unittest` with `-s` or with full paths.
- **The native harness binary lives in the scratchpad.** Rebuild it from `native/object-click/build.txt` (sha `cdda2f0f…`) and check the sha.
- **The spec is append-only.** Any new criterion needs CLAUDE.md §9's four conditions.

## §34.4

- **This stretch:**
  - because of execution: +0;
  - because of review: +0.
- **Running total since 10-14b: 33 / 27.**
- **New tools, not yet reviewed:**
  - `tests/caret_delete_witness_test.cpp` and its mutations;
  - `tests/ordered_poll_test.cpp` and its mutations;
  - `tests/test_reply_state_reads.py`;
  - `tools/check_v23_diagnostic_build.py`;
  - `tools/make_caret_delete_fixture.py`.
- **Carried over, also not yet reviewed:** `read_g.py`, `read_oc.py`, the harness modes `OC_A11Y`, `uni1f` and `I<ms>`, and `+dx`.

## Owner decisions still open (registered, not urgent)

- **Whether the product line moves to the writer+calc+a11y core.** This is now the spreadsheet track's question. Memory records an 08-23 decision for that core that never reached the shipping line.
- **A3** (spec §16.2): close L-C on the shipping core without a11y. It needs a native arm first, and belongs to the feature link only.

## Next (the spreadsheet track)

The investigation is in progress at the time of writing:
- why the line left the calc core after v12;
- the state of `PLAN-2026-09-03-ods-reading.md` and finding 089;
- the shortest path to the owner opening an `.ods` in a browser page.

Its result, and the plan built from it, go in the next handoff.
