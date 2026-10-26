## SUMMARY

- **No path to a false PASS found for a counted S5 type cell.** Every counted reference is either a run-03 save that the pinned `reader-03.json` marks witnessed, or the fresh settled-WASM arm. Why: the judge's `main()` requires `report.config == config()` (judge:723); the live `s5()` binds type cells only from `reader-03.json` (pin `30530678…0706`; re-read at HEAD, byte-identical), only with status `NATIVE_SAVE_AVAILABLE` plus a witness, and never reads run-01 for a type cell (cases:149–155, asserted by a test); the judge uses native only when the row has a save, and otherwise requires the `s5ref` arm (judge:540–544).
- **The witness holds on the actual data (run-03, 56 cells).** In all 47 `selection-before-x` cells the between-read text differs from this run's pre-Shift text. So the synchronous `getTextSelection` tells "Shift applied" apart from "not applied". The bound source posts x after that read, so x cannot come before the Shift effect that was observed. In 55/56 cells the after-save equals the before-save with exactly the between-read selection replaced by x. The 56th, `shift-Right@cell-end`, follows Writer's rule for a table-cell selection (A1 emptied, x in B1). run-02 and run-03 after-texts agree in 56/56.
- **`settle-only` (9 cells) is labelled honestly.** 8 of the 9 do not move: the between caret equals the pre-Shift caret, and Shift produced no selection or caret callback. So the witness says nothing about order there. But for those cells the type comparator gives the same result in either order: Shift changes no text and does nothing to the pre-x state. They therefore cannot give a false PASS. `range-one` does discriminate (synchronous selection type 1→0, caret 2725→2565). It is labelled weaker than it is, which does no harm.
- **The strict timestamp clause (reader:48) checks where a record came from; it measures nothing.** In any record from the bound harness, readEnd < x.atMs holds by statement order (the gap is 0.26–0.46 µs). It can fail only on precision (run-02) or on a record from another code path. What actually guarantees cause and effect is the source order (tested) together with the receipt binding.
- **The red cases, applied in memory to every actual run-03 row:** swapped timestamps give 56/56 NE for exactly the timestamp reason; between text replaced by the post-x selection gives NE for the 47 strong cells (text reason), while the 9 `settle-only` cells stay `settle-only`, which is inherent to them; the whole between-state replaced by the post-x state sends those 9 to NE on the caret; run-01 records give 56/56 NE; run-01 records with run-03's between fields grafted in give 56/56 NE on the timestamp.
- **Caveat on the reds.** The text clause alone would not catch a read taken after x in the reordered run-01 world. In 13 non-silent run-01 cells the post-x selection equals the Shift text. Only code order and the timestamp cover that case.
- **Deletion families and S1–S4 are unchanged.** The 504 deletion plan rows are identical to `13981a0d^` apart from two new keys set to None; `cases` is identical and the `interactions` code is untouched; the judge's logic for non-type rows behaves as before. Tests: selection 40/40, native type 6/6.
- **Issues found. None gives a false PASS on the bound data:**
  - **A. Procedure.** run-03 replaced the ruling's run-02 wholesale after a harness change. The ruling sends a cell without witness (ii) to fallback A, and says "no retry until green". The effect on texts is nil (56/56 equal), but 46 cells moved from settled-WASM to native. This needs the ruling authority's explicit acknowledgement; today it is recorded only by the implementer.
  - **B. Test gap (could give a false PASS for a future binding).** Five reader mutations survive the tests:
    - ignoring the issues from `validate_cell`;
    - dropping the before==fixture check;
    - dropping the discovery-cursor binding;
    - dropping the three-rounds-agree guard;
    - taking the status from the witness issues only.
  - **C. The judge never checks `nativeOrderWitness` (judge:540–541).** `inspect()` run on a pre-`13981a0d` config would use run-01 type saves as native. Counted verdicts cannot reach this (judge:723, runner:172); ad-hoc re-inspection would give a wrong record.
  - **D. The strong label can be over-claimed later.** `selection-before-x` does not require the between text to differ from the pre-Shift text (reader:49–51). No run-03 cell is affected (0/47).
  - **E. Records:**
    - `reader-01.json` still marks the 56 type entries `NATIVE_SAVE_AVAILABLE`. The only guards are the branch order plus a test.
    - Finding 166's 影響 section names run-02, but the bound run is run-03.
    - Any per-cell failure goes to fallback A, which is wider than the ruling's trigger.
    - The S5 group verdict does not count `settle-only` cells.

---

## Scope and method

The review covers commits `de68de56`, `77e4caad` and `13981a0d`, against `../RULING.md`. I read the harness, builder, runner, reader, plan `s5()`, judge `inspect_s5()`, the shared helpers they call (`settle`, `snap`, `nowMs`, `validate_cell`, `derive`), both test files, and the run-02/run-03 evidence.

Everything I ran was read-only or wrote only to the scratchpad. The working tree is unchanged apart from this file.
- `python3 -m unittest tests.test_v23_native_s5_type`: 6/6 OK. `python3 tests/test_v23_feature_selection.py`: 40/40 OK. Both at `nice -n 19`.
- `read_v23_native_s5_type.py …/run-03` to stdout, at `nice -n 19 ionice -c3`. The output sha256 was `305306785509764f1130709650ca44c8a6c0cc320b0d79bb632bbe0817870706`, identical to the pinned `reader-03.json`. (It is a reader, not a `run_*` or `build_*` tool. It hashed the 482 MiB of bound libraries once.)
- In-memory analyses of `run-03/native.jsonl`, `run-01/native.jsonl`, the saves, `reader-02.precision-defect.json`, and old-vs-new `s5()` output (the old module came from `git show 13981a0d^:…`).
- In-memory reader mutations, made by `exec` of a modified copy of the reader source, with the test module run against each copy. No tracked file was edited.
- A read of `s5-prep-03/report.json`, the browser preparation that has now finished: its config binds run-03 for all 56 native type rows.

## 1. Can a counted type cell PASS against anything else?

**Plan construction** (`v23_feature_selection_cases.py:112–167`):
- For `referencePolicy != settled-wasm` and family `type`, the only source is `reader-03.json`. Its file hash is pinned (line 112); its verdict must be `NATIVE_S5_TYPE_SAVES_READ` and its problems `[]`.
- A cell gets a save only when it is `NATIVE_SAVE_AVAILABLE` with a witness in `{selection-before-x, settle-only}`. An NE cell with reasons becomes `nativeFallback`. Anything else raises.
- Saves are re-rooted under the literal `run-03/saves/` and checked by sha256 (`native_saves`). So even a `reader-03.json` produced from another directory could not bind other bytes.
- The type branch is tested first (line 149), so `reader-01.json`'s type entries are unreachable. `S5TypeOracleControls` asserts that the string `run-01` never appears in a type row.
- Old-vs-new diff: only the type rows' `native` and `nativeOrderWitness` changed. All 56 previously bound run-01 type saves are gone. The population is now:

  | Policy | Witness | Cells | `settledReference` |
  | --- | --- | ---: | --- |
  | native | `selection-before-x` | 25 | False |
  | native | `settle-only` | 3 | False |
  | Home/End | `selection-before-x` | 22 | True |
  | Home/End | `settle-only` | 6 | True |
  | settled-wasm | — | 28 | True |

**Judge** (`judge_v23_feature_selection.py:526–555`):
- `need(...)` at line 540 refuses a row with no save unless the policy is settled-wasm or the row is a type row with a reasoned fallback.
- Line 541 uses native only when a save is present, and for Home/End only with the candidate's single-line witness. Otherwise `ref['final']` from the `s5ref` arm, which still carries the existing ≥500 ms settled witness, is required (line 544).
- Since `settledReference` is True for every Home/End row and every fallback row, those pages must contain the settled arm.

**Stale or mis-bound plans:**
- `main()` (line 723) refuses any report whose config is not the live `config()`.
- The runner aborts on drift (`run_v23_feature_selection.py:172`) and judges inline with the live plan (line 184).
- An old config therefore cannot reach a counted verdict (but see issue C for ad-hoc use).

**Home/End `native-if-single-line`:**
- The browser-side single-line rule is unchanged and was retained by the ruling.
- On the native side, every caret-shape Home/End between-read equals the paragraph-bound `expectedShiftHome` / `expectedShiftEnd` from the setup. Range shapes carry no such expectation.
- The 6 Home/End `settle-only` cells do not move, so the order-invariance argument below covers them.

## 2. Does `order_witness` establish (i)–(iii)?

**(i) Posts in declared order.** `validate_cell` checks this: the exact `(type, character, key)` list and monotone timestamps. `order_witness` also requires exactly two Shift posts and one x INPUT.

**(ii), strong branch: can it read `selection-before-x` before Writer finished the Shift step?**
- `getTextSelection` and `getSelectionType` are synchronous LOK calls taken under the SolarMutex. A text equal to the rounds' Shift-only selection is therefore the core's state at the moment of the read.
- In run-03, all 47 strong cells have a between text different from `beforePost.getTextSelection`, so the read discriminates.
- The bound source posts x after the read: the call order is asserted by `test_harness_settles_and_reads_only_between_the_two_members`, and the binary is bound to that source by receipt and identity. So the selection effect of Shift had been applied before x existed in the queue.
- The read does not witness the Shift KEYUP or deferred state updates (for example `.uno:StateWordCount` at ~623 ms in the `range-kbd` cells). None of them changes text, and the 800 ms quiet settle covered them all (read start − Shift UP return − `shiftSettleMs` ∈ [0.54, 0.91] µs).
- Positive cross-check, which the ruling does not require: in 55/56 cells the after-save equals the before-save with exactly the between-read selection replaced by x. The remaining cell, `shift-Right@cell-end`, has a two-cell table selection: A1 is emptied and x lands in B1, which is Writer's behaviour. Nothing changed the selection between the read and x.

**(ii), strict timestamp.** Both values come from `nowMs()` (steady_clock) on the same thread: `readEnd` after `snap()`/`getSelectionType`, and `atMs` inside the post lambda before `postKeyEvent`. For any record of the bound binary the order is guaranteed, so the comparison adds no information about Writer. Its value is limited to two things:
- it rejects records that did not come from this code path (swapped fields, run-01);
- it exposed run-02's print precision.

That is a faithful implementation of the ruling's words, provided nobody reads it as an independent measurement.

**(ii), `settle-only` branch** (reader:51–61):
- "Settled" is `shiftSettleMs ≥ 0`. "Collapsed" is `betweenSelectionType == 0` plus the empty text, and both are synchronous. "Caret at the moving point" is the between `INVALIDATE_VISIBLE_CURSOR` equal to the three rounds' after-caret, with the rounds' before-caret equal to this run's `beforePost` caret.
- Note that the caret is the **last callback payload**, not a synchronous query.
- For the 8 cells that do not move, the before and after caret are the same value. The check therefore passes even if Shift had never been processed. That is exactly why the name is weaker, and it is not an over-claim: the witness claims only "settled, collapsed, at the point".
- These 8 cells also cannot give a false PASS. Shift on them changes no text and does nothing to the pre-x state, so both orders produce "x at the caret". The finding-166 census agrees: 7 derivable cells equal x typed over the pre-Shift shape, and the 8th is `wrap-line-end`, which cannot be derived.
- `shift-Left@range-one` does discriminate (selection type 1→0 by the synchronous read, caret moved to the anchor), yet is labelled `settle-only`. That understates it, which is harmless.

**(iii) A cap or a missing read gives NE.** Both are implemented (reader:35–41) and tested. On "no retry until green", see issue A.

## 3. The ruling's red cases

The test-suite reds use synthetic records built from the rounds' states (`test_v23_native_s5_type.py:19–35, 50–76`). I also applied each red to the 56 actual run-03 rows:

| Red | Result on run-03 | Only the stated reason? |
| --- | --- | --- |
| 1. Swap `betweenReadEndMs` and x `atMs` | 56/56 NE | Yes, `between-read does not complete before the x post` only |
| 2. Between text := post-x selection | 47/47 strong NE; 9/9 `settle-only` unchanged | Yes, the text reason only |
| 2′. Whole between := post-x state | 47 NE on text; 9 NE on `silent member caret not at the moving point` | Yes |
| 3. run-01 records | 56/56 NE | `missing between-read`, plus the incidental `missing Shift settle` |
| 3′. run-01 records + run-03 between fields grafted | 56/56 NE on timestamp (x posted ~0.01 ms after Shift) | Yes |

- Red 2 survives for the silent members by construction. The test names this limit for `range-one` and shows the caret catches the whole-state swap.
- Red 2 is a red only because post-x selections are empty when the order is Shift-then-x. That holds for all 56 run-03 rows, and the synthetic test row also uses `''`.
- In the reordered world it would not hold: 13 non-silent run-01 records have a post-x selection equal to the rounds' Shift text (for example `shift-Right@caret-mid`, `T`). Against a harness that read after x, only the timestamp and the code order protect. Red 1 covers exactly that, so the set of reds is sufficient, but red 2 by itself is not.
- The "nine reader mutations" in the commit message: the eight I reconstructed (text, `<`→`<=`, collapsed, cap, caret, `settle-only` label, comparability, read-after-Shift) all turn a test red. Issue B lists those that survive.

## 4. Sample of `run-03/native.jsonl` and `reader-03.json`

- **`shift-Right@caret-mid/type`** (strong, native). Pre `''`, between `'T'` (type 1), after `''`; after-text `P2 ALPHA BExA`. The Shift callbacks come at 0.56 ms; the read ends at 1143.553757 and x is posted at 1143.554208.
- **`shift-Left@range-one/type`** (`settle-only`, native). Pre `'B'` (type 1), between `''` (type 0), caret 2725→2565 = rounds' after-caret.
- **`shift-End@cell-end/type`** (`settle-only`, Home/End). Pre, between and rounds carets are all `2537, 4618`. Nothing came back for the Shift except `CURSOR_VISIBLE` at 0.097 ms. This is the vacuous-but-order-invariant case.
- **`shift-Home@heading-mid/type`** (strong, Home/End). Between `Heading`; after `x one for the test`.
- **`shift-End@wrap-line-end/type`** (`settle-only`, Home/End). Doesn't move. In the browser the paragraph wraps, so the single-line witness should normally send it to settled-WASM.

Other properties of the run as a whole:
- Every `beforeFile` / `afterFile` equals the id-derived stem.
- No callback falls inside the read window.
- No cap: `shiftSettleMs` is 807–1446 ms.

Nothing was accepted that should not have been.

## 5. Deletion families and S1–S4

- Old-vs-new `s5()`: all 504 non-type rows are identical apart from `nativeOrderWitness` / `nativeFallback`, both None.
- `cases(table)` is identical. `interactions()` and the judge's non-S5 path are untouched.
- In `inspect_s5`, the new `need` and `native` predicates are equivalent for deletion rows, because the plan guarantees a save whenever the policy is not settled-wasm. The S5 group now carries two extra record keys.
- The config digest changed, which makes older reports unjudgeable through `main()`. That was already true since `4907bb57`/`4a06317e`, which came after the counted S1–S4 run `7f31795d`, so nothing new is lost.

## Issues

**A. run-03 substitutes for run-02 without a ruling.** Can it produce a false PASS? No measured outcome effect; this is about procedure and governance.
- Where: `RULING.md`'s appended section, `../s5-native/run-02.README.md`, and `v23_feature_selection_cases.py:153` (hard-coded `run-03`).
- The ruling names run-02 as the oracle. It sends a cell that cannot produce witness (ii) to fallback A, and forbids retrying until green.
- run-02 produced witness (ii) in 10 cells; 46 failed on six-digit printing. The implementer fixed the print, re-ran all 56, and bound run-03. The only record of that is the implementer's own note ("instrument changes forced by execution: 1").
- What I measured: run-02 and run-03 after paragraphs are equal in 56/56, so no oracle text changed. 46 cells moved from settled-WASM to native reference.
- This is defensible as a forced instrument fix (the ruling's (iii) names caps and missing reads, not print precision). It is still a departure from the ruling's letter decided by the implementer's judgement alone (CLAUDE.md §8), so it should be acknowledged by the ruling authority before S5 counts. No new mechanism is needed.

**B. The reader's per-cell validity wiring is not tested.** Can it produce a false PASS? Not now; it could for a future binding.
- These mutations leave `tests.test_v23_native_s5_type` green:
  - reader:113 — ignoring `validate_cell`'s issues (`_,outputs=validate_cell(…);issues=[]`);
  - reader:116–117 — dropping the before==fixture check;
  - reader:114–115 — dropping the discovery-cursor binding;
  - reader:33–34 — dropping the three-rounds-agree guard;
  - reader:120 — taking status from the witness issues only.
- Scenario: a future run in which one cell's pre-key selection differs from the declared shape, or whose posts were reordered. Under the first mutation it reads `NATIVE_SAVE_AVAILABLE` with a witness. A re-pinned plan would then bind a save of a different input as a native oracle.
- Today there is no effect: `reader-03.json` is pinned and reproduces at HEAD, and all 56 cells have empty reasons.
- Fix: tests only, for example a boundary-test variant with a wrong pre-key selection, a missing save, and disagreeing rounds. Under §34 that would count as forced by review.

**C. The judge's native predicate does not check the witness.** Can it produce a false PASS? Not in counted runs; ad-hoc re-inspection gives a wrong record.
- Where: `judge_v23_feature_selection.py:540–541`. A type row with a save and no `nativeOrderWitness` is used as native.
- Scenario: `inspect(page, prep02_config, 'chrome')` on a pre-`13981a0d` config. The new test does exactly this, mutating rows first. It uses run-01's x-then-Shift save. A product that applied x before Shift would PASS there.
- Counted verdicts cannot reach it because of judge:723 and runner:172.
- Optional fix, a check rather than a mechanism: for a type row with a save, require `nativeOrderWitness in ('selection-before-x','settle-only')`.

**D. The strong label is not tied to discrimination.** Wrong record only.
- Where: reader:49–51. `selection-before-x` is given whenever the rounds' text is non-empty and equals the between text.
- A member whose Shift leaves a non-empty selection textually unchanged would get the strong name while being as weak as `settle-only`.
- run-03: 0/47 affected. By the same order-invariance argument as in section 2, the text oracle would still be correct. This is only something to watch when a new run is bound.

**E. Records.** Wrong records only; none affects a verdict.
1. `reader-01.json` still says `NATIVE_SAVE_AVAILABLE` for the 56 type entries. The ruling asked for a consumer note in that file, but the note went to `run-01.README.md` because the plan pins `reader-01.json`'s hash (done in `4a06317e`). Within `wasm_sdk_probe/tools`, the only consumer is `s5()`, which skips those entries.
2. `findings/166-…md:40` says "run-02 以逐格順序見證取代", but the bound oracle is run-03.
3. The type reader does not raise per-cell failures to run-level problems. So a malformed cell (missing save, setup mismatch) goes to fallback A with reasons and is counted as `fallbackSettledWasm`. That is wider than the ruling's trigger ("cannot produce witness (ii)"). It is still never "native without witness". 0 such cells today.
4. `groups['S5']` in `judge()` does not split PASS cells by `nativeOrderWitness`. The weaker witness is therefore visible per cell but not in the S5 group verdict. Recording it per cell meets the ruling's "not silently equal"; an aggregate count would make it visible.

## Explicitly ruled out

- No run-01 type save is reachable from the live plan, the counted judge, or the runner's inline inspection.
- No mis-bound save: names match the id stems, shas are re-checked by both the plan and the judge, and `reader-03.json` reproduces byte for byte.
- No cap, no missing read, and no read window containing a callback in run-03.
- No change to deletion or S1–S4 judgement.
- The 15-digit fix touches only output precision, and the source test enforces it before `measured()`.
