# Calc copy (SPEC-P-calc-copy): evidence

Spec: `specs/SPEC-P-calc-copy.md`. Criteria were pinned before `n-01`. The trial that informed them ran in a scratchpad and does not count.

| Path | What |
|---|---|
| `native-build-01/` | `tools/build_calc_undo_native.py` receipt. `copy` = v6's defines + `OXSDK_ODS_COPY`; `control` = v6's defines, the same source bytes |
| `n-01/` | `tools/check_calc_copy_native.py`: **N_HOLDS**. N-C1..N-C6 hold, the red case (endRow read as exclusive) is red in N-C1, and the control refuses op 15 with `INVALID_ARGUMENT`. N-C7: B1:C2 1.0 ms, column A 220 ms, the whole sheet 205 ms |
| `pre-link-syntax/` | `tools/check_v7_syntax.py`, first run: **red because of the tool, not the code**. It parsed `make -n` line by line, and the bridge's recipe has backslash continuations, so the bridge was never compiled (`taskset: failed to execute -DOXSDK_ODS_STRUCTURE`). Fixed in the tool, and the check was run again |
| `pre-link-syntax-02/` | Same tool after the fix: the four objects of `make ods-editor-v7-dev` pass em++ `-fsyntax-only`, and both positive controls (an `#error` inside the `OXSDK_ODS_COPY` block of `calc_cell_bridge.cpp` and of `sdk_api.cpp`) fail with it |
| `link/` | The owner-run link (`link.sh`, 2026-11-06 11:57): exit 0, real 2 m 52 s. Profile `build/ods/editor-v7/profile`, wasm `36d0e1b8`, worker `8b49b46e` (= the derivation). Archived read-only as `build/archive/ods-editor-v7-dev-36d0e1b8` (SHA256SUMS checked) |
| `p-01/` | `tools/check_calc_copy.py` on v7, Chrome and Firefox: **P_RED**, in P-C3 only, because of the spec, not the product. The clause "the undo button stays disabled" assumed something the page never does (it does not disable undo by stack depth). Spec append 1 withdraws it and measures the undo instead. P-C1, C2, C4 and C5 passed |
| `p-02/` | The same tool after append 1: **P_HOLDS**, 6/6 in each browser. One undo after the copy says 「沒有可以復原的動作。」 and the revision stays 0. `undoDisabledAtOpen: false` is the measured evidence that the withdrawn clause's premise was false |
| `p-red-anchor-only/` | Red case, Chrome (`p-chain-v7.sh`): copying the active cell whatever the selection is **MUTATION_RED** in P-C1, and in P-C2, which also copies the selection |
| `v7-regression/` | The Calc page criteria already held on v6, rerun on v7: sheets **P_HOLDS** 9/9 in each browser; headers **P_HOLDS** (Chrome 145/145, Firefox 121/121, the v6 counts); structure **P_HOLDS** 18/18 in each browser |

Measured on the native core (n-01): the text is the core's own copy text. Formulas give their displayed value. Hidden rows are included. A newline or tab inside a cell becomes a space, and `"` is not quoted. A single cell has no trailing newline. Whole columns and rows are cut to the used area. An empty range returns null from `getTextSelection` (`COPY_UNAVAILABLE`). Copy leaves the cell cursor and the undo list as they were.

A named limit of P-C: Chrome is granted clipboard permission and Firefox runs with `dom.events.testing.asyncClipboard`, so the run cannot show that a real Ctrl+C's user activation survives the engine round trip. That is for the owner's hand test.
