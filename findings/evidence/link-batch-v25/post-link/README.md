# v25 link day (2026-10-29): L1, I1-v25 and archive

The owner ran `bash tools/link_v25_feature_owner.sh` (log written 14:14-14:17 +0800) and reported its
final JSON: `e2-editor-v25`, `abiVersion: 6`, `typedInsert: "document-sdk-insert-typed-text"`, wasm
`44cb15ea...`, loader `ed1d9a55...`, worker `75557b22...`, manifest `e7780061...`, exports `f5b21630...`
(= v24's), 23 actions, `withheld: ["select-all"]`. Every hash was recomputed here from
`dist/profiles/e2-editor-v25/` and `build/e2/editor-v25/exports.txt`.

## L1 (the real log)

- `link-v25-feature-01.log`: the owner's complete make stream (copied unchanged).
- `build-log-check.txt`: `check_v25_feature_contract.py --build-log` -> `v25 preconditions hold` (four units
  once each, the v23 ABI6, v24 and v25 defines on every compile line). One link line with the 1 MiB stack.
- `manifest-check.txt`: `--manifest ... --exports ...` -> `v25 preconditions hold` (contract = v24 under the
  v25 name, bindings, worker bytes, v24 export list, public exports resolved to binary functions).

## I1-v25 (`i1/`)

- `x1.txt` (`x1.command.txt`): `VERDICT PASS` against v24 with `--declared-worker 75557b22...` only: no new
  leaf, no new export, `abiVersion` 6.
- Red cases on scratch copies, same flags: (a) `abiVersion: 7` -> `['manifest']`; (b) undeclared leaf
  `formatProof` -> `['manifest']`; (c) one undeclared export line -> `['exports']`. The first attempt at (a)
  and (b) also failed `profile` because the scratch directories were not named `e2-editor-v25` (the clause
  compares the manifest's profile with the directory name); kept as `*.run01-scratch-dir-misnamed.*`.
- `frozen-set-check.txt`: all 2,453 files of `pre-link/frozen-set-before.sha256` verify (exit 0, no output);
  `frozen-set-new-files.txt`: only the four files of `dist/profiles/e2-editor-v25/` are new.
- `scdocshell.txt`: 0 in the v25 wasm; positive control 11 in `ods-editor-v2` and `ods-viewer-v3`.
  `e1-c.txt`: `intact: true`.

## Archive (`archive/`)

`wasm_sdk_probe/build/archive/e2-editor-v25-44cb15ea-worker-75557b22/` (not in git, read-only): five
artifacts, `SHA256SUMS` (5/5 OK; the four profile files `cmp` equal to dist) and `ATTRIBUTION.md`. Copies
of `SHA256SUMS`, `ATTRIBUTION.md`, the manifest and the export list are in `archive/`.

## Next (spec v25 section 8)

Page cut-over (worker URL `e2-editor-v25`, `PINNED_WASM_SHA256` prefix `44cb15ea8d36f0e0`, typedInsert
requirement unchanged); freeze generation 78 after all shell changes; then section 6.3: F1-F4.
