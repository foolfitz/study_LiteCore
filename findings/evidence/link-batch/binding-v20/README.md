# Binding v20 / host 0.2.23 (handoff 2026-10-15 Next 2; SPEC-M3-link-batch §17)

Main session (opus), 2026-10-15. No browser, no ddev, no make that builds. Three commits:

| commit | what |
|---|---|
| `4421df62` | The M3 runners' remaining pins moved from 0.2.14 / v63 to 0.2.23 / v72 (13 pin lines in six runners). §17.1. |
| `00903e29` | `V19Witness` also materialises `BINDING` at `b8324a85` (a test repair; §34.4 execution +1). |
| this commit | `run_merge_wasm_shakedown.py` `BINDING` set to v20; `test_bound_to_v19_after_v56` becomes `test_bound_to_v20_after_v72`. §17.2. |

## The nine bound values

Computed by the runner's own `bound_values()` along `main()`'s path, with no browser, by `findings/evidence/v19/post-link/compute_binding.py` (unchanged): `binding-v20.json`, `binding-v8.json` here. Each value was checked against a second source:

| key | value (16) | second source |
|---|---|---|
| `wasmSha256` | `313b08d5cb085897` | `sha256sum` of `dist/profiles/e2-editor-v20/probe.wasm` and of `build/archive/e2-editor-v20-313b08d5-worker-478d0da1/probe.wasm`; the v20 merge shakedown's recorded `bound` |
| `workerSha256` | `478d0da1dbfcf936` | the same three |
| `sessionSha256` | `f47c80ec955397c4` | `sha256sum` of the tree's and `dist/`'s `narrow-editor-v2-session.js`; `build/archive/host-0.2.23-engine-c3c22d9294de068a/MANIFEST.json` |
| `shellSha256` | `e7c4eefea5980359` | recomputed from the v72 manifest's own recorded module hashes (`e2/editor-shell-v2-bundle-v72.json`) with the runner's `digest()`; `bound_values()` reads the served files |
| `htmlSha256` | `b1185aaa4f77b892` | `sha256sum dist/e2-editor.html`; the v20 merge shakedown's `bound` |
| `pageSha256` | `ccb67a52a3fe4b73` | `sha256sum web/e2-editor-app.js`; `build_cutover_page.py --profile e2-editor-v20` without `--write` (`pin 313b08d5 -> 313b08d5`, `unchanged True`, `written no`); the archived host package's MANIFEST |
| `pageSourceSha256` | `ccb67a52a3fe4b73` | the same: the cutover source already points at v20, so the page is not repointed |
| `eshapeSha256` | `c3f9bbed6f21b435` | `sha256sum` of `findings/evidence/merge-native/r0c/eshape.json`; equal to the v19 binding and to the v20 shakedown's `bound` |
| `nativeSha256` | `2940a8410dc0a44d` | equal to the v19 binding and to the v20 shakedown's `bound` |

The red case (`--mode m2-1-red --candidate-profile e2-editor-v8`) differs from the binding in exactly `PROFILE_BOUND` (`wasmSha256`, `workerSha256`, `pageSha256`; v8's repointed page pin `313b08d5 -> 4a2710bb`), so it is still counted by `is_counted`.

Runner sha256[:16] after this commit: `365ceef64d45d59c`. Spec 34.1: the runner is not edited from this commit until the v20 count's verdict is read.

## The witness repair (`00903e29`)

`V19Witness` re-judges the committed v19 X7 reports at the run's commit. Part P (P2) materialised only the runner's identity (`RUNNER_SHA`); `BINDING` was still borrowed from the live runner module. Moving the live binding to v20 therefore made the judge's identity clause read NOT DONE on v19's reports, by construction: the same defect P2 fixed, one constant over.

- Before the fix, with the v20 binding in place: `v19witness-before-fix-with-v20-binding.txt`, `FAILED (failures=2)` (`test_a_the_witness_passes`: 3 != 0; `test_c_…`: an extra `NOT DONE: ['all identity']`).
- After: `v19witness-after-fix.txt`, 5/5 ok, none skipped; `unittest-merge-and-judge-after.txt`, 134 tests OK.

The judge is not edited. §34.4: repaired because of execution **+1** (witness: the v19 X7 reports); because of review 0.

## Observation: these two test files are in no Makefile target

`make test-e2-c-static` exited 0 with the v20 binding in place while `V19Witness` was red (`test-e2-c-static-after-binding.txt`). Neither `tests/test_judge_counted_m2.py` nor `tests/test_merge_wasm_clauses.py` is named in `wasm_sdk_probe/Makefile`. Part P's "red before, 5/5 after" and this file's results were run by hand. Not changed here (a Makefile change goes to the owner first); the count chain's preflight should run them by hand until then.

## What was not done here

- `judge_counted_m2.py --profile` still defaults to `e2-editor-v19`; the v20 count passes `--profile e2-editor-v20` (the chain script's job).
- The product-path net's per-release judge copy is count prep, not binding.
