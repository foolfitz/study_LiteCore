# ABI 6 feature pre-link input capture

`capture_build_inputs.py` is prepared for the coordinator's later final capture. It is read-only and requires an explicit mode. `--selftest` exercises its empty/missing-input guards on temporary synthetic paths. `--capture` emits a JSON snapshot to stdout and writes no file; do not run it until the coordinator schedules the final capture.

Run from the repository root:

```sh
python3 -I findings/evidence/link-batch-v23/pre-link/feature-01/capture_build_inputs.py --selftest
python3 -I findings/evidence/link-batch-v23/pre-link/feature-01/capture_build_inputs.py --capture
```

The final snapshot schema is `v23-feature-build-inputs-v1` and contains:

- `allSourceFilesUnderSrc`: every regular file recursively under `wasm_sdk_probe/src/`, sorted and hashed. This includes `.inc` implementation fragments as well as C++ sources/headers; it is a source-tree inventory, not a claim that each file is in the compiled include graph.
- `explicitFeatureAndBaseInputs`: the current Makefile, isolated `sdk/v23-feature-worker.js`, feature recipe's `sdk/v18-writer-review-manifest.json`, and frozen v22 archive `sdk-worker.js`, `exports.txt`, and `sdk-manifest.json`; it records and checks the Makefile's base-worker path and SHA pin.
- `localPackagingPython`: the exact stdout JSON from adjacent `capture_tooling_inputs.py`, including its actual Makefile recipe roots, recursively resolved local Python import files/edges, and declared unresolved import/dynamic-execution limits. The adjacent collector is invoked as a subprocess and is not modified.
- `frozenR2CoreInputs`: each of the exact 189 paths in `diagnostic-r2-01/core-inputs.json`, with expected and current byte counts/SHA256 and per-row equality, plus the source manifest identity and `soffice.js.linkdeps` raw identity, ordered token sequence, token-sequence SHA256, and direct absolute archive references.
- `collector`: this collector's own path/byte count/SHA256. It is included in the final reread, alongside the adjacent AST collector.
- `reread`: a final full-content pass over the union of selected paths. The capture fails if group captures disagree, any file changes before the final pass, any frozen core row is missing/different, or a direct absolute linkdeps archive is outside/missing from the established core rows.

The old core manifest's paths are repository-relative; all 42 absolute `.a` references found in the current linkdeps token file resolve within this repository and are members of those 189 frozen rows. The current token file has 300 shell-style tokens. The manifest has no independent LibreOffice/core Git commit identifier: “same established core” in this capture means byte identity for all 189 files from the accepted r2 resolved input set, including linkdeps, linker archives, Emscripten pre-JS/settings/linker tools, and filesystem-image link source. It does not claim identity for omitted implicit compiler libraries, which the r2 manifest explicitly excludes.

The collector does not invoke `make`, a compiler, linker, browser, packer, or service, and does not write profiles/build outputs. The final capture JSON is not created until the coordinator authorizes it.
