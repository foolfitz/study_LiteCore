# Finding 159: the bridge generator run offline, with and without scaddins (2026-10-21)

No compile, no make. The build-side `wasmbridgegen` that `build-a11y-gate0` already built was run by hand on the rdbs that tree already has, writing into a scratch directory. The question: does feeding scaddins' internal API to the generator put the add-in methods' call signatures into the table?

## Commands

```bash
B=wasm-lite/build-a11y-gate0
G=$B/workdir_for_build/LinkTarget/Executable/wasmbridgegen
U=$B/workdir/UnoApiTarget
export LD_LIBRARY_PATH=$B/instdir_for_build/program
$G base/generated-cxx.cxx base/generated-asm.s base/exports +$U/udkapi.rdb +$U/offapi.rdb
$G scaddins/generated-cxx.cxx scaddins/generated-asm.s scaddins/exports +$U/udkapi.rdb +$U/offapi.rdb +$U/scaddins.rdb
```

The first line is what `bridges/CustomTarget_gcc3_wasm.mk` runs today; the second is what it runs with the patch in `wasm-lite/patches/libreoffice-26.8-wasm-bridge-scaddins-signatures.patch`.

## Result

- **Positive control:** `base/` is byte-identical to the core's own `workdir/CustomTarget/bridges/gcc3_wasm/{generated-cxx.cxx,generated-asm.s,exports}` (`inputs-and-core-outputs.sha256` against `outputs.sha256`). The generator is deterministic on these inputs, and the hand-run is the build's run.
- `base/`: 55 distinct `callVirtualFunction_*` signatures (`signatures-base.txt`). `scaddins/`: 80 (`signatures-scaddins.txt`), a strict superset: 25 added, none removed.
- `exports` is the same file in both runs.

The four add-in functions of the 159 probe sheet, with their signatures read off `scaddins/idl/com/sun/star/sheet/addin/XAnalysis.idl` (return type first, then `this`, then each parameter; `long` and every reference/interface/sequence/any parameter is `i`):

| function | IDL | signature | in base | in scaddins |
| --- | --- | --- | :---: | :---: |
| SERIESSUM | `double getSeriessum(double, double, double, sequence<sequence<double>>)` | `didddi` | no | **yes** |
| MULTINOMIAL | `double getMultinomial(XPropertySet, sequence<sequence<long>>, sequence<any>)` | `diiii` | no | **yes** |
| YEARFRAC | `double getYearfrac(XPropertySet, long, long, any)` | `diiiii` | no | **yes** |
| COUPDAYS | `double getCoupdays(XPropertySet, long, long, long, any)` | `diiiiii` | no | **yes** |

## A correction this forced

Finding 159 named the SERIESSUM signature `didddd` and wrote the post-build check as "`callVirtualFunction_didddd` appears in `generated-cxx.cxx`". Both are wrong: the fourth parameter is a sequence, passed by pointer, so the signature is `didddi`. And a substring search for `didddd` **is satisfied** by the new table anyway, because `callVirtualFunction_didddddd` (another add-in method) starts with it — the check would have passed for the wrong reason. The post-build check is now an exact-token comparison against `signatures-scaddins.txt` (SPEC-M4-viewer-v2 §2).

## What this does not show

That the add-in calls then return numbers in the browser. The table is the one link in the chain the diagnosis found missing; the call still goes through `uno2cpp.cxx`, the generated trampolines, and the add-in code on wasm. Only the probe sheet on the rebuilt core says whether `#VALUE!` goes away.
