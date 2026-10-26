# Feature 01 pre-change profile and archive baseline

Captured before ABI 6 feature source work. The manifest records every regular file under `wasm_sdk_probe/dist/profiles/` and `wasm_sdk_probe/build/archive/`, using the repository-relative `path`, `bytes`, and `sha256` rows from the earlier diagnostic-r2 frozen inventory. It contains 322 profile files and 2,015 archive files, 2,337 files total. The inventory does not include unrelated build trees.

The capture records Git HEAD `5f7c2ac22a2978044ae9b401da01577163af1d87` and the shared SDK worker `wasm_sdk_probe/sdk/sdk-worker.js` at SHA256 `0bed22bdb979138f1f0c23bd41bc05896e14f69e29fba10d4e42ccbcda5e1de9`. These values identify the baseline capture; the file rows are the byte-level comparison data.

The existing feature boundary did not provide a separately enumerated protected host-source path list. The SDK and core input manifests in the diagnostic-r2 pre-link evidence describe other input sets, so they are not presented here as host-source paths.

The E1-C bundle guard was run from `wasm_sdk_probe/` with `python3 -I tools/check_e1_c_bundle_intact.py`. It exited 0. Its captured stdout reports `intact: true`, `includedFiles: 5`, `availableModules: 6`, no declared divergences, and no problems; stderr was empty. The exact argv, exit code, and stdout/stderr files are preserved in `commands/`.

This is a baseline only. It makes no claim that later profile or archive contents are unchanged; compare later inventories against `frozen-before.json` and account for additions under the governing feature boundary.
