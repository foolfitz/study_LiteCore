# W-D reader intended wire mutation controls

Using a fresh synthetic page per mutation, all four intended controls returned `FAIL`: disabled bold input, false bold wire response, wrong caret point using the consumed `xTwips`/`yTwips` fields, and an unplanned extra click request. No case returned `PASS`.

This run follows the corrected work order. The earlier `x`/`y` alias-only result is preserved in `mechanical-02` as the record of the ambiguous original instruction. No source or criteria files were changed, and no build or inventory check was run. Exact mutations, verdicts, and raw output are in `results.json`.
