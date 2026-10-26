# Native S5 type references, run 03 (the bound type oracle)

Executed 2026-10-27 06:57:52–07:04:44 (+0800), 6 min 52 s, runner exit 0, under fable ruling 3 (`../s5-type-oracle-ruling/RULING.md`) and the owner's in-session authorization ("如果需要編譯或長時程建置，一律替我處理"). Harness build `type-build-02/` (binary `acd9a9c1…7e41b`, harness source `2c53df92…`), built at 06:57 after `uptime` (load 0.14) and `pgrep -a make` (none). It differs from run 02's build only by `std::cout.precision(15)` (see `run-02.README.md`). No browser measurement overlapped it.

Per cell (56 native-capable type cells, once each): fresh document, run-01's setup (archived signature source `1e29f73b…ef17`, unchanged), Shift INPUT/UP, settle (800 ms quiet / 8000 ms cap), selection and selection-type read, x (character 120, key 0) INPUT/UP, settle, after-save. Runtime: `native-lok-26-8/build/instdir/program`, `SAL_USE_VCLPLUGIN=svp`, `SAL_LOK_OPTIONS` and `OC_A11Y` removed, `nice -n 10`.

## Reading

`python3 -I wasm_sdk_probe/tools/read_v23_native_s5_type.py …/run-03 --output …/reader-03.json`, exit 0, `reader-03.json` sha256 `30530678…0706`:

- verdict `NATIVE_S5_TYPE_SAVES_READ`, 0 run-level problems;
- 56/56 cells `NATIVE_SAVE_AVAILABLE`: 47 `selection-before-x`, 9 `settle-only`, 0 settled-WASM fallbacks;
- the 9 `settle-only` cells are exactly the members whose three native rounds have an empty Shift selection (`shift-End@{cell-end,doc-end,empty-para,wrap-line-end}`, `shift-Home@{doc-start,empty-para}`, `shift-Left@{doc-start,range-one}`, `shift-Right@doc-end`); each was collapsed at the between-read with the caret at the rounds' after-caret;
- between-read end to x post: 0.26–0.46 µs in every cell; longest Shift settle 1446 ms, no cap.

`census_f166_native_type_order.py run-03` (finding 166): 7 of 52 derivable cells equal "x typed over the pre-Shift shape" (the silent members that move nothing), 0 of 14 shapes give one after-text across their four Shift keys, the same as run 02.

## How it is consumed

`v23_feature_selection_cases.py` binds `reader-03.json` by hash (`NATIVE_S5_TYPE_READER_SHA256`) and each cell's before/after save by sha256. For the S5 plan: 25 Left/Right type cells are native `selection-before-x`, 3 Left/Right native `settle-only`; the 28 Home/End type cells carry a native save (22 `selection-before-x`, 6 `settle-only`) that applies only with the browser single-line witness, otherwise their settled-WASM arm; the 28 Up/Down type cells stay settled-WASM. No run-01 type save is bound anywhere in the plan. Deletion families still bind run-01 under fable ruling 2.

Scope: native reference availability with an order witness. Not browser parity, no Up/Down parity, no overlap witness. `settle-only` is the ruling's weaker, named witness: for those members the between-read shows the state Shift leaves, which is also the state before Shift for all but `shift-Left@range-one`.

## Appended 2026-10-27: correction

The between-read-to-x gap is 0.26–0.74 µs, not 0.26–0.46 µs as written above (0.46 was the median; 29/56 cells exceed it; maximum `shift-End@range-cross/type`, 0.742 µs). `readEnd < xPost` holds in 56/56. Fable ruling 3 Addendum 1 confirms run 03 as the type oracle and the last type run under ruling 3.
