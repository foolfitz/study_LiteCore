# v19 before the link (2026-10-08)

Spec `SPEC-M3-paragraph-merge.md` §31.3 (v19's composition and order), §32.1 (X1 corrected), §32.4 (M1-1 extended). Runbook `handoff/RUNBOOK-relink-v19.md`. Nothing here was linked or run in a browser.

| File | What |
|---|---|
| `m1-1/run.sh`, `run.log`, `<name>.{json,stdout.txt,stderr.txt}` | M1-1 with the extended checker (`tools/check_merge_key_undo_scope.py`, default carriers `E2_V15`, `E2_V19`), BASE `5d77dc84`. **green** rc 0: 25 rules, 100 objects, the two that differ are `build/e2/editor-v15/probe_engine.o` and `build/e2/editor-v19/probe_engine.o`; both guard variants fail on both carriers; `FINDING_012_DIAGNOSTIC` unbuildable on both sides (as in v15's runbook). **red-only-v15** rc 1 (`E2_V19 … differs from 5d77dc84`: the checker sees v19). **red-inject-v8** rc 1. **red-v8-as-carrier** rc 1 (no B in v8, guards do not fail there). Every stderr empty. The first run of the same four was in a wrong directory and was removed; this is the rerun with the same commands. |
| `x1-tool-selftest-output.txt` | `tests/test_profile_identity.py`, 11 tests OK: X1's checker (`tools/check_profile_identity.py`) green on a SYNTHETIC v19 (v18's directory copied, a stand-in wasm and loader, the manifest's name, version and two link hashes rewritten), red on v16 against v18 (real), on v18's own wasm, a manifest hash that is not the file, one worker byte, another pack, a new manifest field, the old version string, another export list, an extra file; NOT DONE on a missing file. |
| `gates.txt` | `check_engine_lock_scopes.py` rc 0 (`gState.mutex` 12, `gMergeMutex` 11: the same counts as v15's runbook, so the poll added no lock scope); `merge_key_undo_model_test` ends `ok`, rc 0; `node --test editor-shell-v2/tests/*.test.mjs` 155 pass, 0 fail; the v15 and v19 compile commands for `probe_engine.o` are identical up to the directory name (`make -n -B`). |

Read, not run: `make -n dist/profiles/e2-editor-v19/sdk-manifest.json` compiles four objects with v15's defines, regenerates `build/r5/writer-review/exports.txt`, makes v19's export list by v15's recipe, links behind `refuse_unasked_relink`, then runs the v15 archive's `sha256sum -c`, `build_base_no35_pack.py --check`, `build_cjk_subset_mono_pack.py --check`, and packs with `sdk/v18-writer-review-manifest.json` and the v15 archive's worker. `make -n` on v18's manifest says up to date; on v15's manifest it reaches the relink refusal. The v15 recipe's export list reproduces v18's (`d6c22670…`), computed from today's `build/r5/writer-review/exports.txt`.

Hashes before the link (first 16 hex of sha256; `dist/profiles/<p>/{probe.wasm,probe.js,sdk-worker.js,sdk-manifest.json}`):

| profile | probe.wasm | probe.js | sdk-worker.js | sdk-manifest.json |
|---|---|---|---|---|
| e2-editor-v8 | `4a2710bba1ef07d9` | `c382b834aa768b91` | `070229cd10bda4a0` | `d70481cb1be5b1f9` |
| e2-editor-v15 | `ad3f68bb85f94589` | `46b2f40ac24b6a78` | `00882139cd0b2e58` | `2a98050cfec967ca` |
| e2-editor-v18 | `ad3f68bb85f94589` | `46b2f40ac24b6a78` | `00882139cd0b2e58` | `456e9a72ab26a3f8` |

## Added after the review (2026-10-08, `../review/DISPOSITION.md`)

| File | What |
|---|---|
| `m1-1-after-review/` | M1-1 rerun with the per-object carrier rule (only a carrier's `probe_engine.o` may differ): green rc 0, 25 rules / 100 objects, `different` 2; the three red cases rc 1; stderr empty. Same commands as `m1-1/run.sh`. |
| `what-the-link-ships.txt` | `tools/what_the_link_ships.py --since 1990bb64 --variant merge-v15 --shipped-profile dist/profiles/e2-editor-v18`, exit 0: `sdk_api`, `unoembind_stub`, `editor_api` preprocess identically; `probe_engine` changed by exactly `66e5c0af`'s hunk; `sdk-worker.js` the same as v18's (`00882139cd0b2e58`). `1990bb64` is the last commit before v15's link (read: `git log --before='2026-10-07 10:22'`); `src/` changed since only in `66e5c0af`. |

Also measured: `find` on the core link inputs (`$LOBUILD/instdir/program`, `workdir/LinkTarget`, `workdir/CustomTarget/static/emscripten_fs_image`, `environment.js`) newer than `build/e2/editor-v15/probe.wasm` (2026-10-07 10:24:04): 0 files. The command is a gate in the runbook.
