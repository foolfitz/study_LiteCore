# Owner-only v24 link (typed text through `.uno:InsertText`, finding 168)

Spec: `specs/SPEC-M3-link-batch-v24.md` (pinned `ceaa2770`, corrections in section 14). Rulings: `findings/evidence/link-batch-v23/feature-protocol/s5-type-route-ruling/RULING.md` (route A, T1–T5) and `RULING-2-abi.md` (editor ABI stays 6; declaration leaf `typedInsert`; init presence check; the v24 page guards "no silent paste"). This is one fresh product link of a new identity, `e2-editor-v24`. It does not touch DDEV, a host, LibreOffice core, any frozen profile or the count chain.

## 0. Before handing over (agent)

All of these must be green and committed first:

- [x] Spec pinned before any implementation (`ceaa2770`).
- [x] `make test-v24-feature-static`: T3/U1, W1, W2/(d′)/(viii)/init presence, E1, identity reds in advance — with their red cases (`findings/evidence/link-batch-v24/pre-link/`).
- [x] S3-v24 dry-run diff and the build-log reader over the dry run.
- [x] V0′: v23's completion re-read green with only the declared shell file restored; native run-03 re-read identical; E1-C intact.
- [x] Frozen set recorded (`pre-link/frozen-set-before.sha256`, 2,348 files).
- [x] v23 archive re-verified: `build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/` 5/5 OK, equal to `dist/profiles/e2-editor-v23/`.
- [x] C++ syntax-only compile of the four v24 units, with a positive control (`pre-link/em-checks/`).
- [x] M1-1 (`check_merge_key_undo_scope.py`): red naming only `E2_V24`'s three objects, then green after `--carrier E2_V24=probe_engine,sdk_api,editor_api` was added to `test-e2-c-static`.
- [x] `what_the_link_ships.py --since dcffd17d --variant link-batch-v24`: `ok: true`, no drift, only `sdk_api` and `probe_engine` changed.

Re-verify on the day: `cd wasm_sdk_probe/build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6 && sha256sum -c SHA256SUMS`.

## 1. Owner command

From Bash, about 3–10 minutes (v23's same-shaped link: four small objects, one full WASM link, packaging; one make job):

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe && bash tools/link_v24_feature_owner.sh
```

The helper refuses an existing `build/e2/editor-v24`, `dist/profiles/e2-editor-v24` or log; unsets the build overrides; runs exactly `make -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v24/sdk-manifest.json` with the full stream in `build/link-v24-feature-01.log` (pipefail); then checks the real log, the manifest/exports/binary bindings, and prints the artifact hashes. **Report that final JSON**, or the complete error with the log. Expected: `profile: "e2-editor-v24"`, `abiVersion: 6`, `typedInsert: "document-sdk-insert-typed-text"`, 23 actions, `withheld: ["select-all"]`.

On failure: do not clean, retry or rerun an old target; preserve the partial directory and log. `ALLOW_FROZEN_RELINK=1` is for this one target only; never for v8, v15, v18–v23.

## 2. After the link (agent, spec 6.2 and 8)

1. L1: the real log — four fresh v24 compilations with both defines, one link; loader exports `_oxsdk_document_insert_typed_text`.
2. I1-v24: `check_profile_identity.py` v24 vs v23 with exactly `--declared-worker`, `--declared-new-leaf .editorContract.typedInsert="document-sdk-insert-typed-text"`, `--declared-export _oxsdk_document_insert_typed_text`, no changed leaf; red cases (a) `abiVersion: 7` and (b) declared-but-absent. Frozen set unchanged except the new profile; `ScDocShell` 0; E1-C intact.
3. Archive at once: `build/archive/e2-editor-v24-<wasm sha8>-worker-<worker sha8>/` (five files, `SHA256SUMS`, `ATTRIBUTION.md`).
4. Cutover: `web/e2-editor-app.js` worker URL and wasm pin to v24, plus the `typedInsert` requirement at open; finish all shell changes; then mint generation 77 (v76 preserved).
5. Spec 6.3 before any count: (vi) stale-wasm init refusal, (vii) page refusal with its positive control, J-red, M2 over 84 type cells × 2 browsers, T5 with real CDP keys (169 control), (i), T4.
