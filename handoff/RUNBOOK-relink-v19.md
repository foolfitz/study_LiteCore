# Runbook: the v19 link — finding 117's fix on the merge product (**the link command is the owner's to run**)

Written 2026-10-08, before the adversarial review and before shell generation v56. Follows [`RUNBOOK-relink-v15.md`](RUNBOOK-relink-v15.md). Spec `specs/SPEC-M3-paragraph-merge.md` §31.3 (composition, order), §31.4 (X1-X7), §32 (X1 corrected, the reader, M1-1 extended). A link mints a new identity; v8, v15 and v18 stay as they are (v19 has its own build and dist directories), and v19 binds nothing until step 6 of §31.3.

## What this link ships

- **New:** `probe.wasm` / `probe.js` linked from the tree, whose engine differs from v15's by one commit, `66e5c0af` (inside `#ifdef OXSDK_MERGE_KEY_UNDO`): while a merge waits for its key (`MergeAwaitingKey`) the engine re-reads `.uno:Undo` every 15 ms instead of waiting only for a LOK callback; the 2000 ms deadline and its reading are unchanged; the Escape, K2 and Escape stages are not polled. Finding 117; diagnosis `findings/evidence/v18/diag-117/RESULT.md`.
- **v18's, byte for byte:** the three resource packs (`sdk/v18-writer-review-manifest.json`: `cjk-sub-e10`, `base-r5-no35`, `fallback-fonts-r5`), `sdk-worker.js` (taken from the v15 archive exactly as v18 takes it, `00882139…`), and the export list (v15's recipe; reproduces v18's `d6c22670…` from today's `build/r5/writer-review/exports.txt`).
- **No other engine change** (fable's ruling on 117 §2).
- The page fix for finding 118 (`840794af`, `web/e2-editor-app.js`) is not in the profile; it ships in shell generation v56 and in the cutover page.

## 0. Gates before the link

From `wasm_sdk_probe/`. State at `99475c4b`: all green **except the one marked open** (the review is done; see below).

- `python3 tools/check_merge_key_undo_scope.py --base 5d77dc84` — M1-1 (extended, §32.4; per object since the review, §33): exit 0, 25 rules, 100 objects, only `E2_V15`'s and `E2_V19`'s `probe_engine.o` differ from BASE and every other object of the two carriers is the same. Red cases in `findings/evidence/v19/pre-link/m1-1-after-review/` (the first run, before the per-object rule, in `m1-1/`).
- `python3 tools/what_the_link_ships.py --since 1990bb64 --variant merge-v15 --shipped-profile dist/profiles/e2-editor-v18` — what the link compiles differently from v15's source (1990bb64 = the last commit before v15's link, 2026-10-07 07:16; `src/` has changed since only in `66e5c0af`): `sdk_api`, `unoembind_stub`, `editor_api` identical; `probe_engine` changed by exactly `66e5c0af`'s hunk; `sdk-worker.js` the same as v18's (`00882139…`). Measured 2026-10-08 (`findings/evidence/v19/pre-link/what-the-link-ships.txt`); any other changed unit stops the link.
- `python3 tools/check_engine_lock_scopes.py` — exit 0, `gState.mutex` 12, `gMergeMutex` 11 (the poll adds no scope).
- `c++ -std=c++17 -O2 -Isrc -o build/merge_key_undo_model_test tests/merge_key_undo_model_test.cpp && build/merge_key_undo_model_test` — ends `ok`.
- `node --test editor-shell-v2/tests/*.test.mjs` — 155 pass (the glob form; `node --test editor-shell-v2/tests/` does not find them).
- `L=../wasm-lite/build-headless-probe; find $L/instdir/program $L/workdir/LinkTarget $L/workdir/CustomTarget/static/emscripten_fs_image ../libreoffice-26-8/static/emscripten/environment.js -newer build/e2/editor-v15/probe.wasm -type f | wc -l` — `0`: no core link input has changed since v15's link (2026-10-07 10:24; `soffice.js.linkdeps` and `soffice.data.js.link` are dated 2026-08-01). Measured 2026-10-08 (review 2026-10-08, opus S1). Run it in the owner's shell right before the link.
- `python3 -m unittest tests.test_merge_wasm_clauses tests.test_judge_counted_m2 tests.test_profile_identity tests.test_merge_key_undo_scope` — the runner's clauses, the counted reader, X1's checker, M1-1's per-object judgement.
- The adversarial review (§31.3 step 3): done 2026-10-08, opus and codex; every BLOCKING item dispositioned (spec §33, `findings/evidence/v19/review/DISPOSITION.md`).
- **Open: shell generation v56 frozen and `make` dist** (§31.3 step 4; it also binds the review's runner changes). Until then `make test-e2-c-static` is red on `test_the_real_manifest_matches_the_real_tree` (`web/e2-editor-app.js`, the v55 bundle's entrypoint, changed in `840794af`); after the freeze it must exit 0.

## 1. Before the link: record v8, v15, v18

```
sha256sum dist/profiles/e2-editor-{v8,v15,v18}/{probe.wasm,probe.js,sdk-worker.js,sdk-manifest.json}
```

Expected now (first 16 hex; also in `findings/evidence/v19/pre-link/README.md`):

| profile | probe.wasm | probe.js | sdk-worker.js | sdk-manifest.json |
|---|---|---|---|---|
| e2-editor-v8 | `4a2710bba1ef07d9` | `c382b834aa768b91` | `070229cd10bda4a0` | `d70481cb1be5b1f9` |
| e2-editor-v15 | `ad3f68bb85f94589` | `46b2f40ac24b6a78` | `00882139cd0b2e58` | `2a98050cfec967ca` |
| e2-editor-v18 | `ad3f68bb85f94589` | `46b2f40ac24b6a78` | `00882139cd0b2e58` | `456e9a72ab26a3f8` |

Do **not** run any make target that names v8 or v15 (`dist/profiles/e2-editor-v{8,15}/…`, `build/e2/editor-v{8,15}/…`). The Makefile changed, which every rule lists, so make considers them out of date; for v15 the objects would now compile the poll too (the v15 and v19 compile commands are identical up to the directory name). Both links refuse without `ALLOW_FROZEN_RELINK=1`; **never pass it for v8 or v15.**

## 2. The link (**this step is the owner's to run**)

```
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
env | grep -E '^(LOSRC|LOBUILD|EMSDK_ROOT|EXTRA_DEFINES|EXTRA_OBJECTS|HOST_CXX)='   # must print nothing
env -u LOSRC -u LOBUILD -u EMSDK_ROOT -u EXTRA_DEFINES -u EXTRA_OBJECTS -u HOST_CXX \
    make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v19/sdk-manifest.json
```

- Why the `env -u` (review 2026-10-08, opus S1): those six are `?=` in the Makefile, so a value left in the shell would silently replace the core tree, the toolchain or the defines, and no gate after the link sees them (M1-1 forces `EXTRA_DEFINES=`; X1 cannot see defines or the core). If the `grep` prints anything, say so before linking.

- Builds `build/e2/editor-v19/{sdk_api,probe_engine,unoembind_stub,editor_api}.o`, regenerates `build/r5/writer-review/exports.txt` (a text file, not a v8 artifact), writes `build/e2/editor-v19/exports.txt`, links `build/e2/editor-v19/probe.{js,wasm}`, checks the v15 archive (`sha256sum -c`) and the two packs (`--check`), and packs `dist/profiles/e2-editor-v19/`. v15's link took about two minutes from objects to packed profile (10:22 → 10:24); expect the same order.

## 3. Immediately after the link

Report back:

```
sha256sum dist/profiles/e2-editor-{v19,v8,v15,v18}/{probe.wasm,probe.js,sdk-worker.js,sdk-manifest.json}
python3 tools/check_profile_identity.py --candidate dist/profiles/e2-editor-v19 \
    --reference dist/profiles/e2-editor-v18 --candidate-exports build/e2/editor-v19/exports.txt \
    --reference-exports build/archive/e2-editor-v15-ad3f68bb-worker-00882139/exports.txt
```

- v8's, v15's and v18's twelve hashes must equal §1's. Any difference: stop, nothing else runs.
- X1 (§32.1): `VERDICT PASS`, exit 0. The line `loader … equal / differs` is a one-time record, not a criterion. v19's worker must be `00882139cd0b2e58…`; its wasm must differ from `ad3f68bb…`.
- Then the main session archives v19 at once (finding 036: the wasm is not a function of the source): `build/archive/e2-editor-v19-<wasm sha8>-worker-00882139/` with `probe.wasm`, `probe.js`, `sdk-worker.js`, `sdk-manifest.json`, `exports.txt`, `SHA256SUMS` and `ATTRIBUTION.md` (what the files are bound to, and that the packs are v18's under `dist/profiles/resources/`).
- `python3 tools/check_merge_key_undo_scope.py --base 5d77dc84` again (the objects now exist; the check reads sources, so it must still say the same).

## 4. After the link (spec §31.3 steps 6-9, the main session's)

1. **Bind** (§7, §32.3): `BINDING` in `run_merge_wasm_shakedown.py` (the nine `BOUND_KEYS`: wasm, worker, session, shell, html, page, page source, eshape, native; spec §33.2) and `test_nothing_is_bound_before_v56` change in **one** commit. The candidate page is the cutover source with the 118 fix, repointed to v19; its sha256 is computed by the runner (`bound_values`) and checked against `build_cutover_page.py --profile e2-editor-v19` (prints the sha; never `--write`).
2. **Predictions** for X2-X7 under `findings/evidence/v19/`, committed before the round (§31.4: M2-4 105/105 `verified-key-undo`, per-press engine latency < 300 ms, no toast, final = native; Y01/Y02 engine latency in the 28-49 ms band).
3. **The v19 round**: X2 (M1-1 again), X3 (W3, W5 probes), X4 (corpus v19 vs v18), X5 (product-path net v8 vs v19), X6 (owner document V5), X7 (the counted M2: per browser `counted`, `counted --control`, `m2-1b`, `m2-4`, `m2-1-red`, written as `counted-B.json`, `counted-control-B.json`, `m2-1b-B.json`, `m2-4-B.json`, `red-B.json`, then `tools/judge_counted_m2.py --dir DIR` without `--uncounted`: exit 0 and `VERDICT PASS`). One runner at a time; count `chrome` processes before each counted run (rule y).
4. If X7 is voided by a page or shell red: freeze v57, never overwrite v56 (§31.4).
5. Host 0.2.8 (`tools/check_m3_assets.py` pins `cjk-r5…`; move to the `cjk-sub-e10` pack, re-read before editing), then R.
