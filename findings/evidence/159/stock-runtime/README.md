# Finding 159 on a stock upstream WASM build (2026-11-18)

Question: does the defect of finding 159 (Calc add-in functions give `#VALUE!` on WASM because the gcc3_wasm bridge's signature table lacks scaddins' methods) happen on an unpatched upstream build, at run time, and is the signature table what decides?

## Build under test

`wasm-lite/upstream-master/build-186-R`: upstream master `ac53621f754f` plus finding 186's configure fix (`4847e69dd326`, changes only `configure.ac`; without it master does not configure for WASM at all). `--with-distro=LibreOfficeWASM32 --disable-symbols`, emsdk 4.0.10, Qt 5.15.2. Nothing touches `bridges/` or `scaddins/`. `soffice.wasm` sha256 `41749425416d7f4f…`. Built 2026-11-18 for finding 186 (`findings/evidence/186/build/`).

## The test

The mechanism makes a prediction that "add-ins are broken on WASM" does not: an add-in method whose signature happens to be in the table (because some udkapi/offapi method has the same one) must work.

- `addin_signatures.py` computes every scaddins method's bridge signature with the rule of `uno2cpp.cxx` `call()` and looks it up in a build's `generated-cxx.cxx`. On build-186-R: `sig-stock-186R.tsv`, 57 of 114 methods IN_TABLE, 57 ABSENT.
- `cases.json`: 5 core functions, 10 add-in functions with IN_TABLE signatures (Analysis, DateFunctions and its Misc interface), 8 with ABSENT signatures (Analysis and Pricing), and 6 direct calls (3 IN_TABLE, 3 ABSENT).
- `oracle_native.py` → `oracle-native.json`: desktop LibreOffice 26.8.1.1 computes all 23 cells without error.
- `PREDICTIONS.txt`: written and committed (`d71d500b2`) before the first run. Its method counts were wrong (corrected at the end of the file, the per-case predictions unchanged).
- `probe_159.js` via `run_159_probe.sh`: opens `qt_soffice.html`, creates a Calc document from the Start Center, types each formula into column A (en-US UI, `,` separator), sets the same formulas into column B with `XCell.setFormula`, reads both back through Embind UNO in the LO main thread's worker (formula, error code, value, string), and calls the add-in methods directly through `css.script.Invocation`, catching the UNO exception with `Module.catchUnoException`. Screenshots after each step.
- `read_159.py` judges the runs. The expected outcome of every case is derived from the oracle and the signature TSV, not written by hand. `red_cases.sh` → `reader-red-cases.txt`: four doctored runs turn red in exactly the doctored case, and the unmodified stock run judged against an all-IN_TABLE table turns red in exactly A1–A8 and D4–D6.

## Result

`verdict-stock-186R.txt`: three runs (`run-01`, `run-02` with locale en-US, `run-03` with the browser default zh-TW), every case as predicted, `not as expected: 0`.

| | typed and API path | direct call |
| --- | --- | --- |
| core C1–C5 | error 0, desktop value | — |
| add-in, signature in table: FACTDOUBLE, SQRTPI, EOMONTH, EDATE, WORKDAY, BIN2DEC, IMABS, DAYSINMONTH, ISLEAPYEAR, ROT13 | error 0, desktop value | getFactdouble, getSqrtpi, getRot13 return the desktop value |
| add-in, signature absent: MULTINOMIAL, SERIESSUM, YEARFRAC, COUPDAYS, QUOTIENT, MROUND, BESSELI, OPT_PROB_HIT | error 519 `#VALUE!` | getQuotient, getBesseli, getOptProbHit throw `InvocationTargetException` wrapping `RuntimeException("Wasm bridge cannot call virtual function with signature didd" / "didi" / "didddddd")` |

The direct calls read the bridge's own message, so the link from "signature not in the table" to "exception" is observed, not inferred. The link from that exception to `#VALUE!` in a cell is read from `addincol.cxx` (`ExecuteCallWithArgs` maps `uno::Exception` and wrapped non-IllegalArgument exceptions to `FormulaError::NoValue`).

## The fix, offline

`bridgegen-offline/`: build-186-R's own build-side `wasmbridgegen` run by hand on its own rdbs (0.1 s, no compile). Without scaddins the three outputs are byte-identical to build-186-R's (positive control, `outputs.sha256`); with `+scaddins.rdb` the table has 77 signatures, a strict superset of the 52, `exports` unchanged, and `sig-patched-offline.tsv` has all 114 methods IN_TABLE.

Commands (from the repository root):

```bash
B=wasm-lite/upstream-master/build-186-R
G=$B/workdir_for_build/LinkTarget/Executable/wasmbridgegen
U=$B/workdir/UnoApiTarget
O=findings/evidence/159/stock-runtime/bridgegen-offline
export LD_LIBRARY_PATH=$B/instdir_for_build/program
$G $O/base/generated-cxx.cxx $O/base/generated-asm.s $O/base/exports +$U/udkapi.rdb +$U/offapi.rdb
$G $O/scaddins/generated-cxx.cxx $O/scaddins/generated-asm.s $O/scaddins/exports +$U/udkapi.rdb +$U/offapi.rdb +$U/scaddins.rdb
```

## Not shown here

- The fix at run time on master. `rebuild_159_fix.sh` rebuilds build-186-R with the change (owner runs it); its products before are in `wasm-lite/upstream-master/archive-186-R-products-before-159/`.
- Documents that carry cached values (the corpus files of finding 159): Calc recalculating at load on WASM is a separate question; here every formula is entered fresh.
- Functions other than the 18 add-in functions tested. The other 95 are classified by `addin_signatures.py` only.
- Creating `com.sun.star.sheet.addin.Analysis` through the remote service manager of desktop 26.8 ended that soffice process (`oracle_native.py` docstring); not looked into, the oracle uses cells only.
