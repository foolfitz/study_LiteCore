# Order-dependent native S5 saves: decision brief

Status at preparation: **decision pending; ruling 4 still applies and the cells remain NE**. The previous session's delegation to fable was explicitly session-scoped. The owner authorized consulting Astra for difficult decisions in this session; that authorizes advice, not an invented fable ruling.

## Forcing measurement and reproducible evidence

The ruling-4 witness reader derives two order-dependent cells from the full 336 native-capable deletion cells: `shift-Home@heading-mid/backspace-twice` and `shift-Home@list-mid/backspace-twice`. Both are non-empty-mark, `native-if-single-line` cells. Ruling 4 explicitly makes an applicable order-dependent native reference NE and says an unexpected count stops the work.

`../s5-order-prep-02/` records two cells in Chrome and Firefox, four complete NE observations under that rule. All four establish the single-line witness. For each cell, the candidate agrees with both the bound every-member-settled native save and its fresh settled-WASM arm, and disagrees with the queued-native save. Native equality means `strip_ffd(reduce_content(...))`; WASM equality means full `reduce_content` equality. The list cell has identical paragraph text but different structure, so a text-only comparison would miss its disagreement.

Reproduce the comparison from the repository root:

```bash
python3 -I findings/evidence/link-batch-v23/feature-protocol/s5-order-oracle-review/read-prep.py
```

`comparison.json` binds the input hashes and this reader's hash. The reader first runs the existing 336-cell native witness validation and the existing browser-arm evidence bindings; it then directly compares candidate original with each witness's own before-save, checks that reduction does not hide the edit, and verifies each native member's read completion before the next member's post. Both cells satisfy all of these checks. Setup/save lifecycle order is source-bound through the retained harness, not independently timestamped. Four browser observations share two native witnesses; they are not four native repetitions.

The exact native structural differences are retained in `nativeReducedDiff`:

- Heading: queued native merges the remainder into the previous paragraph (12 paragraphs); settled native retains a heading as a list header (13 paragraphs).
- List: queued native retains `text:list-item`; settled native changes it to `text:list-header`.

## Options presented to the owner

**A (recommended by Astra):** use each qualifying cell's bound every-member-settled native before/after pair. Retain ruling 2's original-document comparability, non-collapse guard and structural comparator, the browser single-line premise, and the existing overlap condition. Membership must be generated per cell from native evidence, never from these two IDs or from agreement with the product. An absent or invalid settled witness remains NE; it must not fall back to queued native or WASM to obtain a PASS. Label this distinct native schedule in records.

**B:** route these cells to settled-WASM and narrow their claim to ordering plus self-consistency. This discards available native parity and is therefore not Astra's recommendation.

**C:** retain NE and leave counted S5 blocked at these cells.

Any adoption must append the exact replacement to ruling 4 and S-CASES, preserve the old NE pages and counted-01 failure, begin a fresh complete S5 population, and keep the first-complete-clean-population cutoff. Preparation is never retroactively counted.

## Astra advice (summary, not a ruling)

Astra recommended A conditionally on a repeatable reader with red controls. The existing files suffice if the disclosed source-bound lifecycle is accepted; no additional native run is required. Every-member-settled native and Shift-only-settled WASM are different schedules; their agreement does not prove schedule equivalence. Two identical Backspaces cannot explain the difference merely by swapping them, so neither event reordering nor the responsible layer is established.

Required red controls before a gate change: missing witness/save, wrong hash, capped settle, wrong step operation or interleaved timing, wrong own-before, queued-native heading/list result used as candidate (FAIL, including list structure), empty-mark row sent to native (refusal), and a new generated member without its witness (refusal). Timing must be finite and non-boolean, exact posts must match the generated sequence, every key-up must precede its read, and every non-final read must finish strictly before the next key-down.

No gate amendment, S5 plan/judge change, new counted population or terminal acceptance is claimed by this brief.

## Appended decision and implementation status

The initial decision-pending status is superseded by the owner's explicit delegation to Astra and its binding A decision in `RULING.md`. New plans use explicit schema 2 and the certified own before/after pair for the generated disagreement partition. The original four preparation NE inspections and historical claims above are preserved. Current certification is `../s5-native/settled-reference-reader-04.json`; development certificates 01-03 are not current plan inputs. Guard controls and final-plan preparation still precede full counted execution; no S5 acceptance is implied by the decision.
