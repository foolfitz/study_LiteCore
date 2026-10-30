# v27 link day (2026-10-30): P-v27 (spec 7.3) and archive

The owner ran `bash tools/link_v27_first_block_owner.sh` (log written 14:19-14:22 +0800) and reported its final JSON: `e2-editor-v27`, `abiVersion: 6`, `typedInsert: "document-sdk-insert-typed-text"`, `selectAll: ["collapsed","range-single","range-cross"]`, 23 actions, `withheld: []`.

Hashes:
- wasm `c089dfd6...`
- loader `0a73eb5a...`
- worker `8152448a...`, the bytes of `sdk/v27-first-block-worker.js`, as the pre-link dry run computed
- manifest `d5d07639...`
- exports `f5b21630...`, which is v26's (= v25's)

Every hash was recomputed here from `dist/profiles/e2-editor-v27/` and `build/e2/editor-v27/`.

## The real log

- `link-v27-first-block-01.log`: the owner's complete make stream, copied unchanged. It has four compiles (`-c src/`) and one link line with `-sDEFAULT_PTHREAD_STACK_SIZE=1048576`.
- `build-log-check.txt`: `check_v27_first_block_contract.py --build-log` -> `v27 preconditions hold`. The four units compile once each, with the v23 ABI6, v24, v25 and v27 defines on every compile line.
- `manifest-check.txt`: `--manifest ... --exports ...` -> `v27 preconditions hold`. It checks:
  - the contract is v26's under the v27 name: every leaf equal, select-all and typedInsert included;
  - the bindings and the worker bytes;
  - the v26 export list;
  - the public exports resolve to binary functions.
- `v27-literal-in-wasm.txt`: the serializer literal `,"undo":{"read":` exists only under `OXSDK_E2_V27_FIRST_BLOCK`. It occurs once in v27's wasm and 0 times in v26's and v25's. The control `multi-block-readback` occurs once in each. So the define was compiled in.

## I1 against v26 (`i1/`)

- `x1.txt` (`x1.command.txt`): `VERDICT PASS` against `dist/profiles/e2-editor-v26` with `--declared-worker 8152448a...` only.
  - 180 leaves each side; moved = the three bindings, `profile` and `sdkVersion`.
  - No new leaf, no new export, `abiVersion` 6.
- Red cases on scratch copies, each in a directory named `e2-editor-v27` (v25's run-01 lesson), the profile files symlinked:
  - (a) `abiVersion: 7` -> `['manifest']`;
  - (b) undeclared leaf `firstBlock` -> `['manifest']`;
  - (c) one undeclared export line -> `['exports']`.
- The first attempt at (c) did not mutate anything. The build leaves `exports.txt` read-only, and the copy kept that mode, so the append failed. The unmutated copy gave `VERDICT PASS`. It is kept as `red-c-undeclared-export.run01-copy-read-only-not-mutated.*`: in effect a control that the scratch setup itself passes.

## Frozen set, ScDocShell, E1-C

- `frozen-set-check.txt`: all 2,757 files of `pre-link/frozen-set-before.sha256` verify (exit 0, no output).
- `frozen-set-new-files.txt` (C-locale `comm`): the only new files are the four of `dist/profiles/e2-editor-v27/`, and none is absent.
- `scdocshell.txt` (`strings probe.wasm | grep -c ScDocShell`): 0 in v27's wasm; the positive control is 23 in `ods-editor-v2` and in `ods-viewer-v3`.
  - The counting method differs from v25's receipt, which recorded 11 with an unrecorded method. This one is stated.
- `e1-c.txt`: `intact: true`.

## Archive (`archive/`)

`wasm_sdk_probe/build/archive/e2-editor-v27-c089dfd6-worker-8152448a/` is not in git and is read-only.
- It holds the five artifacts, `SHA256SUMS` and `ATTRIBUTION.md`.
- `sha256sum-check.txt`: 5/5 OK; the four profile files are `cmp`-equal to `dist/`.
- Copies of `SHA256SUMS`, `ATTRIBUTION.md`, the manifest and the export list are in `archive/`.

## Next (spec 7.3)

- Page cutover: worker URL `e2-editor-v27`, `PINNED_WASM_SHA256` prefix `c089dfd699d646e3`.
- Then S3 and S2′, generation 81 frozen after every shell change, and F3-81, F4-81, V0′-81, E1-C.
