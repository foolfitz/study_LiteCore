# v19 after the link (runbook RELINK-v19 §3 and §4.1)

The owner linked `e2-editor-v19` on 2026-10-08 (objects 19:40, link 19:42, packed 19:43 +0800) at tree `c0337ae3`, shell generation v56 frozen in `baea3540`. The make target's last output, as pasted by the owner: profile `e2-editor-v19`, ABI 4, wasm `1aafd4f9…`, manifest `902111fa…`, 21 actions, `withheld: ["select-all"]`.

## §3: hashes, X1, archive, M1-1 (measured by the main session)

First 16 hex of sha256, after the link:

```
1aafd4f9da42fd83 dist/profiles/e2-editor-v19/probe.wasm
46b2f40ac24b6a78 dist/profiles/e2-editor-v19/probe.js
00882139cd0b2e58 dist/profiles/e2-editor-v19/sdk-worker.js
902111faaed3430c dist/profiles/e2-editor-v19/sdk-manifest.json
4a2710bba1ef07d9 dist/profiles/e2-editor-v8/probe.wasm
c382b834aa768b91 dist/profiles/e2-editor-v8/probe.js
070229cd10bda4a0 dist/profiles/e2-editor-v8/sdk-worker.js
d70481cb1be5b1f9 dist/profiles/e2-editor-v8/sdk-manifest.json
ad3f68bb85f94589 dist/profiles/e2-editor-v15/probe.wasm
46b2f40ac24b6a78 dist/profiles/e2-editor-v15/probe.js
00882139cd0b2e58 dist/profiles/e2-editor-v15/sdk-worker.js
2a98050cfec967ca dist/profiles/e2-editor-v15/sdk-manifest.json
ad3f68bb85f94589 dist/profiles/e2-editor-v18/probe.wasm
46b2f40ac24b6a78 dist/profiles/e2-editor-v18/probe.js
00882139cd0b2e58 dist/profiles/e2-editor-v18/sdk-worker.js
456e9a72ab26a3f8 dist/profiles/e2-editor-v18/sdk-manifest.json
```

- v8's, v15's and v18's twelve hashes equal the runbook's §1 table (and `../pre-link/gates-after-v56.txt`, taken before the link).
- v19: wasm `1aafd4f9…` (115,307,325 bytes) differs from v15's `ad3f68bb…` (115,307,269); loader `46b2f40a…` equal to v15's and v18's; worker `00882139…`.
- X1 `tools/check_profile_identity.py` (candidate v19, reference v18, exports v19 vs the v15 archive's): exit 0, `VERDICT PASS`; the manifests differ in exactly `.editorContract.wasmSha256`, `.profile`, `.sdkVersion` (`x1-check-profile-identity.txt`). As registered in spec §33.4, the wasm clause proves "another file", not "the fix".
- Archived at once (finding 036): `build/archive/e2-editor-v19-1aafd4f9-worker-00882139/` (not in git): probe.wasm, probe.js, sdk-worker.js, sdk-manifest.json, exports.txt (`d6c22670…`, written 19:40:50, the link's input), `SHA256SUMS`, `ATTRIBUTION.md`. The packs are v18's and are not copied.
- M1-1 `check_merge_key_undo_scope.py --base 5d77dc84` again: exit 0, its JSON line identical to the pre-link run (`m1-1-after-link.txt`).

## §4.1: the binding

`compute_binding.py` (kept here) calls the runner's own `bound_values()` the way `main()` does, with no browser and nothing written: the cutover source `web/e2-editor-app.js` repointed to the profile, `dist/e2-editor.html` before the instrument, the shell digest over v56's twelve non-entrypoint modules as served. `binding-v19.json` is what was written into `BINDING`; `shell_lagging_source` was empty.

Each value checked against a second source:

| key | value (16) | second source |
|---|---|---|
| wasmSha256 | `1aafd4f9da42fd83` | `sha256sum dist/profiles/e2-editor-v19/probe.wasm`; the archive's SHA256SUMS |
| workerSha256 | `00882139cd0b2e58` | `sha256sum` of the profile's sdk-worker.js |
| sessionSha256 | `ee3e53a24fb20a25` | `sha256sum` of the dist and the source session (equal); v56 manifest |
| shellSha256 | `c28578b7c056b370` | recomputed from the v56 manifest's own module hashes (12 modules); the v18 runner-shakedown reports |
| htmlSha256 | `f7e477998385c283` | `sha256sum dist/e2-editor.html` |
| pageSha256 | `e00ab76a550dc12f` | `build_cutover_page.py --profile e2-editor-v19` (no `--write`; printed "written no") |
| pageSourceSha256 | `a7d8ffa1adc60a9a` | `sha256sum web/e2-editor-app.js`; v56 manifest's entrypoint |
| eshapeSha256 | `c3f9bbed6f21b435` | `sha256sum` of `findings/evidence/merge-native/r0c/eshape.json`; v18 runner-shakedown reports |
| nativeSha256 | `2940a8410dc0a44d` | the six v18 runner-shakedown reports (same native files) |

With `BINDING` set: `is_counted("counted", bound(v19), BINDING)` True; `is_counted("m2-1-red", bound(v8), BINDING)` True, differing in exactly wasm, worker and page (`binding-v8.json`); `is_counted("counted", bound(v8), BINDING)` False. The four unit-test modules: 115 tests OK after the change (`test_nothing_is_bound_before_v56` became `test_bound_to_v19_after_v56` in the same commit).

**Spec §34.1 starts with the bind commit:** `tools/run_merge_wasm_shakedown.py`, `tools/judge_counted_m2.py`, `tools/check_profile_identity.py`, `tools/check_merge_key_undo_scope.py` and the product-path runner are not edited until the X7 verdict is read. The runner's sha256[:16] after the bind is `73b2e9ff4b1e6fbe` (the reader's `RUNNER_SHA`); every counted report must carry it.
