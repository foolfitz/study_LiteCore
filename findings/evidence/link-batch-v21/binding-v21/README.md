# BINDING v21 (2026-10-17)

`run_merge_wasm_shakedown.py`'s `BINDING` moves from e2-editor-v20 (host 0.2.24's page) to **e2-editor-v21** on shell generation v74 and host 0.2.26. The precedent is `findings/evidence/link-batch/binding-v20/` (`22e8c900`). The re-pin of the other runners is a separate commit (`a643de39`, `findings/evidence/host-0.2.26/repin_0226.py`).

Computed by `bound_values()` as `main()` calls it, with no browser: `cd wasm_sdk_probe && python3 -B ../findings/evidence/v19/post-link/compute_binding.py e2-editor-v21` (`binding-v21.json`; v8's red case in `binding-v8.json`). `lagging` is `[]`, and the cutover source already points at v21 (`pinBefore = pinAfter = db3408f55316bf67`).

| key | value | was (v20 / 0.2.24) | second source |
|---|---|---|---|
| wasmSha256 | `db3408f55316bf67…` | `313b08d5…` | `sha256sum` of `dist/profiles/e2-editor-v21/probe.wasm` and `build/archive/e2-editor-v21-db3408f5-worker-0d55bcfa/probe.wasm`; host 0.2.26 `engine/MANIFEST.json` |
| workerSha256 | `0d55bcfa2ee0e4dd…` | `478d0da1…` | same three places (`sdk-worker.js`) |
| sessionSha256 | `f1509ff22e6e2d8d…` | `f47c80ec…` | tree and `dist/` copies; package MANIFEST; the v74 manifest's module hash |
| shellSha256 | `e35923a08107662d…` | `e7c4eefe…` | `v21_shakedown_common.EXPECTED_SHELL_DIGEST` (S-1 over `dist/`); the D2 host identity's `hostShellDigest`, computed from the package MANIFEST |
| htmlSha256 | `1d15814949c633ce…` | `b1185aaa…` | `sha256sum dist/e2-editor.html`; package MANIFEST; the 12 item-1 reports' `htmlSourceSha256` |
| pageSha256 = pageSourceSha256 | `605cf24b3dff5a2d…` | `901dd6a6…` | `web/` and `dist/` copies; package MANIFEST; HTTP-served under gzip and zstd (`host-0.2.26/http-served.txt`) |
| eshapeSha256 | `c3f9bbed6f21b435…` | unchanged | `sha256sum findings/evidence/merge-native/r0c/eshape.json` |
| nativeSha256 | `2940a8410dc0a44d…` | unchanged | equal to the v20 binding |

- **Nine keys, as before** (v21 spec §9.10: no tenth key is needed).
- **v8's red case stays counted:** wasm `4a2710bb…`, worker `070229cd…`, repointed page `ea3b6bad…`; it differs from v21 only in the profile's own three values.
- **Red first:** `BINDING` moved, test not renamed → 134 tests, exactly 1 failure, `test_bound_to_v20_after_v72` (`unittest-red-first-binding-moved-test-not-renamed.txt`). After the rename to `test_bound_to_v21_after_v74`: 134 OK (`unittest-merge-and-judge-after.txt`). `make test-e2-c-static` exit 0 (`test-e2-c-static-after-binding.txt`).
- **No witness class breaks** (unlike `00903e29`): `V19Witness` restores `BINDING` from `b8324a85`, and `V20Witness` judges uncounted, keyed on its own wasm. What does change: re-judging `release-0.2.24/merge-m2` on the live tree now reads NOT DONE (identity) by construction. To re-judge it, use the runner as of `a8b5ff33`.
- **Runner sha256:** `f9008207…` (the 0.2.24 count's) → `aaee0cda5be5ad84…`.
- **§34.1:** the 0.2.24 count's verdict was read before this edit (`RESULT-0.2.24.md`: merge VERDICT PASS). From this commit until the 0.2.26 count's verdict is read, the runner is not edited.
- A binding, not a repair: §34.4 0/0.
