# ods-viewer-v2 on the fallback core, before the link (2026-10-22)

SPEC-M4-viewer-v2 §7.1 step 2 and `handoff/RUNBOOK-link-ods-viewer-v2.md` §0, redone against `wasm-lite/build-a11y-gate0` after the fallback rebuild (`../fallback-core/`). Commands run from `wasm_sdk_probe/`.

| file | what it shows |
| --- | --- |
| `dist-and-objects-before-delete.txt` | Before the deletion: the six files of `dist/profiles/ods-viewer-v2/` and the four non-object files of `build/ods/viewer-v2/` are byte-identical to `build/archive/ods-viewer-v2-a6390eef-worker-9c85043a/`, whose `SHA256SUMS` all check OK; the sha256 of the three objects (compiled against `build-ods-viewer-v2`'s headers, `HAVE_FEATURE_DBCONNECTIVITY 1`; not archived). The owner then deleted both directories (`rm -rf` by hand; it was refused to the session). |
| `default-core.txt` | The Makefile's `ODS_VIEWER_V2_CORE` default is now `../wasm-lite/build-a11y-gate0` (was the v2 tree), and the object rule's expansion reads gate0's headers. Reason: a link or a `test-e2-c-static` run that forgets the variable must not pick the core that cannot ship (F-3). |
| `base-pack-check-gate0.json` | `build_ods_viewer_v2_profile.py --check --core ../wasm-lite/build-a11y-gate0`: positive control 9901e9be reproduced on the rebuilt gate0 image; base `6f7424a1c1427ad7` (v1's own base pack), 1,488 files; against v1's base 0 added / 0 removed / 0 changed. |
| `syntax-gate0.txt` | `em++ -fsyntax-only` with v2's defines against gate0's headers: `sdk_api.cpp`, `probe_engine.cpp`, `unoembind_stub.cpp` exit 0; `sdk_api.cpp` sees `HAVE_FEATURE_DBCONNECTIVITY 0`, so the engine reports no form-controls bit. |
| `test-e2-c-static-gate0-default.txt` | `make -k test-e2-c-static` exit 0 (39 s) with the new default; the carrier check judges ODS_VIEWER_V2's objects against gate0 and refuses merge-key-undo in them. |
| `core-provides-calc-gate0.txt` | `check_core_build_provides.py --build ../wasm-lite/build-a11y-gate0 --capability calc-spreadsheet` exit 0. |
| `link-token-diff-v1-v2-gate0.txt` | `make -n -B` of both link rules, one token per line: only the three object paths, the export list path and the output path differ. The core paths are now v1's (on the v2 core they differed in three tokens: `pre-link/link-token-diff-v1-v2.txt`). |
| `compile-token-diff-v1-v2-gate0.txt` | `make -n -B` of each object, v1 against v2: only `-DOXSDK_ODS_VIEWER_V2` and the object path. |
| `frozen-set-before.sha256` | The frozen set right before the link is handed over: 1,527 files under `dist/profiles/` and `build/archive/`. |
| `frozen-set-old-vs-new.txt` | The 01:3x snapshot (`pre-link/frozen-set-before.sha256`, 1,517 files) still checks after the deletion; the new snapshot adds exactly the ten files of the a6390eef archive and loses none. |

Unchanged since the a6390eef link (`git log b4048fd6^..HEAD` empty for `src/`, `sdk/` and the three builder tools; worker sha256 `9c85043a…`), so §0 items 3 and 4 carry over (item 2, syntax, is redone above against gate0).
