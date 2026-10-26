# S5 preparation 02 (uncounted): first S5 cells, two findings

Chrome, eight S5 cells covering every reference policy, the type family, the prefix families and the click, drag and keyboard setups. Receipt `runner.command.json` (exit 1, 137 s, about 17 s per cell). Raw cells are stored as `.json.gz`, with file names `chrome-<case id, / replaced by __>`.

Runner's reader at execution:

- 5 PASS: `shift-Left@caret-mid/backspace` (native), `shift-Down@caret-mid/delete` (settled), `shift-Up@cell-end/backspace-twice` (settled), `shift-Right@range-fwd/delete` (native) and `shift-Left@range-kbd/delete-twice` (native). Each has a positive overlap witness: one posted, unanswered move/extend request at the continuation's `beforeinput`.
- 2 NE `missing/nonunique wire call s5cand-final-save`: the two prefix families.
- 1 FAIL: `shift-Right@caret-mid/type`.

1. **Prefix families, reader defect.** After the first Delete/Backspace dirties the document, the product saves a checkpoint before the move (request 114 in `shift-Home@caret-mid/delete-before-and-after`). The page's own final save is queued behind the sequence, so both saves fall in its call window. The reader now binds the last save in that window, byte-equal to the call's result and later than every other save there (`final_save`). Re-read with it, both cells PASS (one native, one settled), with overlap 0: the checkpoint separates the continuation from the move. The protocol reports such cells in the non-overlapping set.
2. **Type family, oracle defect.** The product gives `P2 ALPHA BExA` (Shift+Right selects `T`; x replaces it), while native run-01 gives `P2 ALPHA BExTA`. In 56 of 56 native type cells, the native harness processed the x before the earlier-posted Shift key. Fable ruling 3 (`../s5-type-oracle-ruling/RULING.md`) withdraws those saves as oracles and orders a native run-02 with a settle and a per-cell order witness. Until then the type cell stays FAIL under the old oracle, and that FAIL is not a product result.

`S5Controls` adds red cases from these pages; each pins its own reason:

- One character of the candidate's final save changed → FAIL, native and settled.
- Swapped sequence keys → NE.
- Extension flag removed → NE.
- Settled witness 450 ms early → NE.
- Final save moved before the checkpoint → NE.

38/38 selection tests pass.
