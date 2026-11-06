# Calc copy (SPEC-P-calc-copy): evidence

Spec: `specs/SPEC-P-calc-copy.md`. Criteria were pinned before `n-01`. The trial that informed them ran in a scratchpad and does not count.

| Path | What |
|---|---|
| `native-build-01/` | `tools/build_calc_undo_native.py` receipt. `copy` = v6's defines + `OXSDK_ODS_COPY`; `control` = v6's defines, the same source bytes |
| `n-01/` | `tools/check_calc_copy_native.py`: **N_HOLDS**. N-C1..N-C6 hold, the red case (endRow read as exclusive) is red in N-C1, and the control refuses op 15 with `INVALID_ARGUMENT`. N-C7: B1:C2 1.0 ms, column A 220 ms, the whole sheet 205 ms |
| `pre-link-syntax/` | `tools/check_v7_syntax.py`, first run: **red because of the tool, not the code**. It parsed `make -n` line by line, and the bridge's recipe has backslash continuations, so the bridge was never compiled (`taskset: failed to execute -DOXSDK_ODS_STRUCTURE`). Fixed in the tool, and the check was run again |
| `pre-link-syntax-02/` | Same tool after the fix: the four objects of `make ods-editor-v7-dev` pass em++ `-fsyntax-only`, and both positive controls (an `#error` inside the `OXSDK_ODS_COPY` block of `calc_cell_bridge.cpp` and of `sdk_api.cpp`) fail with it |
| `link/link.sh` | The owner-run link of the development profile `build/ods/editor-v7/profile`; writes `link-01.*` and `profile-SHA256SUMS` |

Measured on the native core (n-01): the text is the core's own copy text. Formulas give their displayed value. Hidden rows are included. A newline or tab inside a cell becomes a space, and `"` is not quoted. A single cell has no trailing newline. Whole columns and rows are cut to the used area. An empty range returns null from `getTextSelection` (`COPY_UNAVAILABLE`). Copy leaves the cell cursor and the undo list as they were.
