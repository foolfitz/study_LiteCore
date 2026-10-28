# v24 link day (2026-10-28): L1, I1-v24 and archive

The owner ran `bash tools/link_v24_feature_owner.sh` (log written 10:51–10:54 +0800) and reported its final JSON: `e2-editor-v24`, `abiVersion: 6`, `typedInsert: "document-sdk-insert-typed-text"`, wasm `27615808…`, loader `64aaa8dc…`, worker `41041fe7…`, manifest `f9554e8c…`, exports `f5b21630…`, 23 actions, `withheld: ["select-all"]`. Every hash was recomputed here from `dist/profiles/e2-editor-v24/` and `build/e2/editor-v24/exports.txt` and matches. Spec: `specs/SPEC-M3-link-batch-v24.md` section 6.2.

## L1 (the real log)

- `link-v24-feature-01.log` is the owner's complete make stream (copied unchanged).
- `build-log-check.txt`: `check_v24_feature_contract.py --build-log` → `v24 preconditions hold` (four v24 units compiled once each, both `-DOXSDK_E2_V23_FEATURE_ABI6` and `-DOXSDK_E2_V24_TYPED_INSERT` on every compile line, exactly one link line, no diagnostic define or stack-overflow flag).
- `manifest-check.txt`: `check_v24_feature_contract.py --manifest … --exports …` → `v24 preconditions hold` (contract = v23 plus the declaration, bindings, worker bytes, export list, and the loader's public exports resolved to actual binary functions).
- The loader binds `Module["_oxsdk_document_insert_typed_text"]` to a binary export; the link line is v23's (`-sDEFAULT_PTHREAD_STACK_SIZE=1048576`, `-sASSERTIONS=0`).

## I1-v24 (`i1/`)

- `x1.txt` (command in `x1.command.txt`): `VERDICT PASS`. Moved leaves exactly `loaderSha256`, `typedInsert`, `wasmSha256`, `workerSha256`, `profile`, `sdkVersion`; `abiVersion` unchanged at 6; no `--declared-changed-leaf`.
- Red cases on scratch copies of the profile, same flags: (a) manifest `abiVersion: 7` → `VERDICT FAIL: ['manifest']`; (b) leaf removed → `['declared-leaf']`; (b) candidate export list = v23's → `['exports']`. Each fails only its own clause.
- Frozen set: `frozen-set-check.txt` — all 2,348 files of `pre-link/frozen-set-before.sha256` verify (`sha256sum -c --quiet`, exit 0, no output); `frozen-set-new-files.txt` — the only new files under `dist/profiles/` and `build/archive/` are the four of `dist/profiles/e2-editor-v24/` (measured before archiving). A first attempt with `comm` printed unrelated `e2-editor-v2-*` paths because the two sides were sorted under different collations; the set difference above replaces it.
- `scdocshell.txt`: `ScDocShell` occurs 0 times in `probe.wasm`. `e1-c.txt`: `intact: true`.

## Archive (`archive/`)

`wasm_sdk_probe/build/archive/e2-editor-v24-27615808-worker-41041fe7/` (not in git): the five artifacts, `SHA256SUMS` (5/5 OK, the four profile files `cmp` equal to `dist/profiles/e2-editor-v24/`) and `ATTRIBUTION.md`. Copies of `SHA256SUMS`, `ATTRIBUTION.md`, the manifest and the export list are in `archive/`.

## Next (spec 8)

Cutover: page worker URL, wasm pin and the `typedInsert` requirement; remaining shell changes; generation 77. Then section 6.3 before any count.
