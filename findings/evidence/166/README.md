# Finding 166 evidence: Shift+arrow then a character, posted back to back, applies the character first

Native LibreOfficeKit 26.8 (`native-lok-26-8/build/instdir/program`, default non-unipoll mode, `SAL_USE_VCLPLUGIN=svp`), Writer, the retained S5 fixture. All runs are under `../link-batch-v23/feature-protocol/s5-native/`.

| Run | Sequence posted | Type cells | after-text = x typed over the pre-Shift shape (of 52 derivable) | shapes with one after-text across Left/Right/Home/End (of 14) |
| --- | --- | --- | --- | --- |
| run-01 | Shift INPUT/UP, x INPUT/UP back to back (0.015 ms) | 56 | 52 | 14 |
| run-02 | Shift INPUT/UP, settle, read, x INPUT/UP | 56 | 7 | 0 |
| run-03 | same as run-02, timestamps at 15 digits | 56 | 7 | 0 |

`census.json` is the full per-cell output of:

```bash
python3 -I wasm_sdk_probe/tools/census_f166_native_type_order.py run-01 run-02 run-03 --output findings/evidence/166/census.json
```

Reading: with the four posts back to back, every type cell's saved text is what x typed before the Shift step would give, and the Shift extension is visible after x (for example `shift-Right@caret-mid/type`: `P2 ALPHA BExTA` with `T` still selected). With the Shift step settled first, only the 7 silent members (Shift moves nothing there) still match that prediction, and the four keys of every shape give different texts. In run-03 every one of the 56 cells' between-read selection equals the three archived native rounds' Shift selection (`../link-batch-v23/feature-protocol/s5-native/reader-03.json`).

A "derivable" cell is one whose caret or range offsets follow from the retained setup point names (`pN.M`, `pN.end`); the four `wrap-line-end` cells use a named wrap point and count only in the cross-key column.

Not established: which layer reorders the two KEYINPUT events. Both reach `SfxLokHelper::postKeyEventAsync` in posting order; the finding records a source-reading hypothesis (asynchronous accelerator dispatch outside unipoll) that no measurement here distinguishes.
