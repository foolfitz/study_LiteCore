# Runbook: the ODS viewer v2 core build (owner)

Written 2026-10-21. Spec: [`specs/SPEC-M4-viewer-v2.md`](../specs/SPEC-M4-viewer-v2.md) §2 (K-1, K-2 and the fallback F were pinned before this build).

This builds a **new** core tree, `wasm-lite/build-ods-viewer-v2`, carrying two fixes: finding 159 (Calc add-in functions `#VALUE!`: the wasm bridge's call-signature table now includes scaddins) and finding 158-B (DB connectivity on, so `com.sun.star.form.Forms` exists and sheets with form controls can paint). Nothing shipped is touched: `build-a11y-gate0` (viewer v1's core) and `build-headless-probe` (the editor's) are not rebuilt.

## Already done (do not redo)

| | |
|---|---|
| source patches | `libreoffice-26-8`: `bridges/CustomTarget_gcc3_wasm.mk` and `configure.ac` (two places); snapshotted as `wasm-lite/patches/libreoffice-26.8-wasm-bridge-scaddins-signatures.patch` and `…-wasm-explicit-database-connectivity.patch`; all eight patches pass `git apply --check --reverse` |
| 159 half-measured offline | the bridge generator run by hand: base output byte-identical to the core's, with scaddins 55 → 80 signatures, the four add-in signatures present (`findings/evidence/m4-ods/phase-e/159-diagnosis/bridgegen-offline/`) |
| build dir | `wasm-lite/build-ods-viewer-v2/` with `autogen.input` (gate0's 10 lines + 4) and `env.sh` (gate0's, `LO_BUILD` changed); copies in `handoff/ods-viewer-v2/` |
| checker | `wasm_sdk_probe/tools/check_ods_viewer_v2_core.py`; `--self-test` is red on gate0 where it must be (K-1a/K-1b, K-2a/K-2c); a fake tree built from the offline output is green |
| machine | 2026-10-21 10:12: load 0.57, 19 GB RAM available, 100 GB free on `/`; the two `make run` processes are container services (cwd `/project`, up for a day), not builds |

## The command

```bash
bash /home/jiajun/LibreOffice/study_LiteCore/handoff/ods-viewer-v2/build-core.sh
```

What it does, in order, stopping at the first red with a message saying where to look:

1. sources `env.sh` and refuses anything but emcc 4.0.10;
2. `autogen.sh` in the build dir (about 40 s; log `configure.log`);
3. **K-1** — the falsifier, before any compile: DB connectivity on, dbaccess and the three SDBC drivers off, Calc/a11y as in gate0, `autogen.input` differing by exactly the four lines;
4. `make -j12` (log `build.log`, also on screen). gate0's full build took 40 min; the DB connectivity modules add an unmeasured amount;
5. **K-2** — the bridge has the add-in signatures (whole symbols), the component list has the forms collection, the five link inputs exist.

Reports land in `findings/evidence/m4-ods/viewer-v2/core/` (`k1-configure.json`, `k2-built.json`, `timing.txt`).

**If `make` dies within seconds inside `workdir/UnpackedTarball/…`**, that is finding 003 (a directory race): run once more with `--make-only`. A second failure, or any failure later in the build, is a measurement — send me the end of `build.log`. If the failure is inside a DB connectivity module (`forms`, `connectivity`, `dbtools`…), that is fallback **F-1** in the spec: v2 goes ahead with 159 only, on gate0, in minutes.

## What to tell me

Just the last line it printed (`DONE: …` or `STOP: …`). I read the reports and the logs myself.

## Hazards

- Both patches change the **shared** source tree, and `config_host.mk` depends on `configure.ac` (`Makefile.in:48–56`). The next `make` in `build-headless-probe` or `build-a11y-gate0` will re-run autogen once on its own. Neither passes `--enable-database-connectivity`, so the configure result should not change — compare `config_host.mk` and `config_host/*.h` before going further there.
- The bridge patch does nothing to an already built tree unless the three files in `workdir/CustomTarget/bridges/gcc3_wasm/` are deleted (`scaddins.rdb` is older than them, and gbuild does not track the command line). That is the fallback route, not this one.
- Nothing I run during the build is a timing measurement, so the build does not disturb any of mine; heavy work of yours alongside it only makes it slower.

## After the build (mine)

1. Read K-2 and the logs; register sizes (K-2f) beside gate0's.
2. The viewer v2 link rule, profile builder and shell changes (spec §3 onward, appended before the link), then the link command for you.
3. Phase E on v2, including the 159 cells, the five form-control files (V2-158B) and the hidden-sheet tabs (157).
