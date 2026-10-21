# ODS viewer v2, before the link (2026-10-21)

Measurements made while writing SPEC-M4-viewer-v2 §3, none of them on a linked engine (there is none yet).

| file | what it shows |
| --- | --- |
| `v1-preprocessed-against-17c5d50b.txt` | Under v1's defines (`-DOXSDK_READER_PROFILE -DOXSDK_ODS_VIEWER`, `build-a11y-gate0`'s headers, `em++ -E -P`), `sdk_api.cpp` preprocesses byte-identically to commit 17c5d50b and `probe_engine.cpp` differs by one blank line only (`diff -B` exit 0). All of v2's code is under `OXSDK_ODS_VIEWER_V2`. |
| `sdk-worker-mutations-red-anchor-drift.txt` | `tests/sdk_worker_ods_viewer_mutations.py` after the worker change and before the anchor update: `reply-forwarded-whole` matches 0 times (the part-text literal gained v2's wait fields). The witness for the one check change (section 34: because of execution +1). |
| `test-e2-c-static-red-v2-not-declared-core-not-configured.txt` | `make test-e2-c-static` with the new rule in the Makefile, before the carrier was declared and before `wasm-lite/build-ods-viewer-v2` was configured: 490 + 5 tests pass, then `check_merge_key_undo_scope.py` is red on exactly ODS_VIEWER_V2's objects (`config_features.h` not found; output differs from the base). |

Also measured (commands in SPEC-M4-viewer-v2 §3.5), not kept as files because they are reproducible in seconds:

- `build_r5_profiles.classify()` on `build-a11y-gate0`'s image: base 1,489 / cjk 1 / fallback-fonts 116, and the base group sliced into a pack is `9901e9be29c9ded2…` byte for byte -- e2-editor-v14's base pack, the one v1's came from.
- `build_ods_viewer_v2_profile.py --check --core ../wasm-lite/build-a11y-gate0`: base `6f7424a1c1427ad7` (v1's own base pack), diff against v1 0 added / 0 removed / 0 changed / 1,488 unchanged. `--red-drop /instdir/share/registry/main.xcd`: the diff shows it removed.
