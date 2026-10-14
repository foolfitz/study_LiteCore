# Runbook: the v20 link — the link batch (page number, C, caretBefore) (**the link command is the owner's to run**)

Written 2026-10-14, before shell generation v67 is frozen. This runbook follows [`RUNBOOK-relink-v19.md`](RUNBOOK-relink-v19.md). It rests on two documents:

- `specs/SPEC-M3-link-batch.md`: §13.3 (scope) and §15 (ruling 6 and its amendments 1–2);
- `findings/evidence/link-batch/review/ruling-6.md`, condition 54 (the order of the gates).

A link mints a new identity. v8, v15, v18 and v19 stay as they are, because v20 has its own build and dist directories. v20 binds nothing until its `BINDING` commit, which comes after the link.

## What this link ships

- **Engine:** `probe.wasm` / `probe.js` linked from the tree, with the v19 defines plus `-DOXSDK_E2_V20_LINK_BATCH`. The engine source is final at `543a5566` (ruling 6 amendment 2). For v20 it is identical in preprocessed form to `82af92ca` (part 1), which review 6 read.
  - C: a Backspace or Delete at a document end completes as `verified-boundary-noop` after the 2000 ms window, instead of a refusal that reopens the engine.
  - `caretBefore` on both kinds of refusal.
  - The `DOCUMENT_SIZE_CHANGED` counter, pushed.
  - The `page-rectangles` document query, with its new C export `_oxsdk_document_page_rectangles`.
  - ABI stays 4.
- **Worker:** the tree's `sdk/sdk-worker.js`, sha256 `478d0da1…`. It is not v15's archive copy: part 1 added nine hunks. The recipe refuses any other bytes.
- **Export list:** v19's recipe plus `_oxsdk_document_page_rectangles`.
- **Packing:** v19's, meaning v18's three resource packs and `--inline-range-gestures all`, plus `--page-rectangles`, which declares `editorContract.pageRectangles = "document-sdk-page-rectangles"`.
- **Not in the profile:** the page and shell changes (part 2's page number; ruling 6 conditions 45, 47 and 48). They ship in shell generation v67.
- **Named residuals in the release text** (spec §15.1, §14):
  - L-C-late-K1;
  - L-C-number-or-indent;
  - finding 137's three effects, on both releases;
  - finding 138, fixed on the page in v67.

## 0. Gates before the link

Run these from `wasm_sdk_probe/`, in condition 54's order. Each is marked with its state on 2026-10-14.

1. **Makefile block applied.** ✅ `d7d62039`; the comment was amended in `543a5566`.
2. **M1-1.** ✅ Evidence: `findings/evidence/link-batch/v20-part3/m1-1/after-56/` and `rerun-after-56/`. Both runs must exit 0:
   - `python3 tools/check_merge_key_undo_scope.py --base 5d77dc84 --carrier E2_V15 --carrier E2_V19 --carrier E2_V20=probe_engine,sdk_api,editor_api`
   - `python3 tools/check_merge_key_undo_scope.py --base 82af92ca^ --carrier E2_V20=probe_engine,sdk_api,editor_api`

   `editor_api.o` differs by two declarations only (`v20-part3/m1-1-witness/editor_api-define-diff.txt`).
3. **X1, the v20 mode.** ✅ The tool is written and tested (`v20-part3/x1/`). It is run after the link (§3).
4. **What the link compiles differently from v19's source.** ✅ `python3 tools/what_the_link_ships.py --since c0337ae3 --variant link-batch-v20 --shipped-profile dist/profiles/e2-editor-v19`:
   - `ok: true` and `configurationDrift: []`;
   - `probe_engine` and `sdk_api` changed; `unoembind_stub` and `editor_api` identical;
   - worker `00882139` → `478d0da1`.

   Named limit: the tool reads only `.cpp` files under the tree's headers. That is why `editor_api` reads identical; M1-1 covers the headers. Any other changed unit stops the link.
5. **Page and shell fixes (conditions 45, 47, 48).** ✅ `aeaf92c0`, `a6ecb7fd`, `bcf3f747`. `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs` gives 412/412, and `python3 tools/check_e1_c_bundle_intact.py` prints `"intact": true`.
6. **Browser witness on the v67 bytes, before the freeze.** ⏳ Task 10-14c: 129-B in both browsers, and restore-window if it runs without the host. Evidence goes to `findings/evidence/link-batch/v67-witness/`.
7. **Shell generation v67 frozen.** ⏳ Follow v66's freeze (`60819c4a`). Afterwards `make test-e2-c-static` must exit 0; until then it is red only on `test_the_real_manifest_matches_the_real_tree`.
8. **Archive.** ✅ The frozen profiles that the link must leave alone are already archived under `build/archive/`:
   - `e2-editor-v8-4a2710bb-worker-070229cd-manifest-d70481cb`;
   - `e2-editor-v15-ad3f68bb-worker-00882139`;
   - `e2-editor-v18-ad3f68bb-worker-00882139-cjk-e10-06976180`;
   - `e2-editor-v19-1aafd4f9-worker-00882139`.

   Check that v19's archive equals its dist copy: `(cd build/archive/e2-editor-v19-1aafd4f9-worker-00882139 && for f in probe.wasm probe.js sdk-worker.js sdk-manifest.json; do cmp -s $f ../../../dist/profiles/e2-editor-v19/$f && echo same $f || echo DIFF $f; done)`. It must print four `same` lines; it did on 2026-10-14.
9. **Remaining gates:**
   - `python3 tools/check_engine_lock_scopes.py`: exit 0, `gState.mutex 12, gMergeMutex 13`.
   - Both model tests end `ok`:
     - `c++ -std=c++17 -O2 -Isrc -o build/merge_key_undo_model_test tests/merge_key_undo_model_test.cpp && build/merge_key_undo_model_test`
     - `c++ -std=c++17 -O2 -Isrc -o build/extend_completion_model_test tests/extend_completion_model_test.cpp && build/extend_completion_model_test`
   - `python3 -m unittest tests.test_merge_key_undo_scope tests.test_profile_identity tests.test_e2_editor_v4_profile` passes.
   - On 2026-10-14 the unit tests passed, the lock scopes read 12/13 and both model tests printed `ok`.
   - The core link inputs have not changed since v19's link (2026-10-08 19:42):

     `L=../wasm-lite/build-headless-probe; find $L/instdir/program $L/workdir/LinkTarget $L/workdir/CustomTarget/static/emscripten_fs_image ../libreoffice-26-8/static/emscripten/environment.js -newer build/e2/editor-v19/probe.wasm -type f | wc -l`

     It must print `0`; it did on 2026-10-14. Run it in the owner's shell right before the link.

## 1. Before the link: record v8, v15, v18, v19

```
sha256sum dist/profiles/e2-editor-{v8,v15,v18,v19}/{probe.wasm,probe.js,sdk-worker.js,sdk-manifest.json}
```

Expected values, first 16 hex, measured 2026-10-14:

| profile | probe.wasm | probe.js | sdk-worker.js | sdk-manifest.json |
|---|---|---|---|---|
| e2-editor-v8 | `4a2710bba1ef07d9` | `c382b834aa768b91` | `070229cd10bda4a0` | `d70481cb1be5b1f9` |
| e2-editor-v15 | `ad3f68bb85f94589` | `46b2f40ac24b6a78` | `00882139cd0b2e58` | `2a98050cfec967ca` |
| e2-editor-v18 | `ad3f68bb85f94589` | `46b2f40ac24b6a78` | `00882139cd0b2e58` | `456e9a72ab26a3f8` |
| e2-editor-v19 | `1aafd4f9da42fd83` | `46b2f40ac24b6a78` | `00882139cd0b2e58` | `902111faaed3430c` |

Do **not** run any make target that names v8, v15, v18 or v19. The Makefile changed, and every rule lists it as a prerequisite (finding 042), so make now treats those targets as out of date. Their links refuse without `ALLOW_FROZEN_RELINK=1`. **Never pass that flag for any of them.**

## 2. The link (**this step is the owner's to run**)

```
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
env | grep -E '^(LOSRC|LOBUILD|EMSDK_ROOT|EXTRA_DEFINES|EXTRA_OBJECTS|HOST_CXX)='   # must print nothing
env -u LOSRC -u LOBUILD -u EMSDK_ROOT -u EXTRA_DEFINES -u EXTRA_OBJECTS -u HOST_CXX \
    make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v20/sdk-manifest.json
```

- **Why `env -u`.** Those six variables are `?=` in the Makefile. A value left in the shell would silently replace the core tree, the toolchain or the defines, and no gate after the link would see it (v19 review, opus S1). If the `grep` prints anything, say so before linking.
- **Why `ALLOW_FROZEN_RELINK=1` on a first link.** The v20 rule is guarded from its first link, like every product artifact before it. The flag goes on **this one target only**.
- **What it does:**
  - builds `build/e2/editor-v20/{sdk_api,probe_engine,unoembind_stub,editor_api}.o` with the define on all four compile lines;
  - regenerates `build/r5/writer-review/exports.txt`. That is a text file, not a frozen artifact; today it is `f80e8998…`;
  - writes `build/e2/editor-v20/exports.txt` and links `build/e2/editor-v20/probe.{js,wasm}`;
  - checks the worker pin (`sha256sum -c` against `478d0da1…`) and the two packs (`--check`);
  - packs `dist/profiles/e2-editor-v20/`.

  v19's link took about two minutes; expect the same order.

## 3. Immediately after the link

Report back the output of:

```
sha256sum dist/profiles/e2-editor-{v20,v8,v15,v18,v19}/{probe.wasm,probe.js,sdk-worker.js,sdk-manifest.json}
grep -c '_oxsdk_document_page_rectangles"\]=_oxsdk_document_page_rectangles=wasmExports\[' build/e2/editor-v20/probe.js
grep -a -o ScDocShell dist/profiles/e2-editor-v20/probe.wasm | wc -l
python3 tools/check_profile_identity.py --candidate dist/profiles/e2-editor-v20 \
    --reference dist/profiles/e2-editor-v19 --candidate-exports build/e2/editor-v20/exports.txt \
    --reference-exports build/archive/e2-editor-v19-1aafd4f9-worker-00882139/exports.txt \
    --declared-worker 478d0da1dbfcf93615a00025c3c2f9b72c3cfa486d04746f03dea5fcf757b099 \
    --declared-new-leaf .editorContract.pageRectangles=document-sdk-page-rectangles \
    --declared-export _oxsdk_document_page_rectangles
```

- **v8, v15, v18 and v19.** Their sixteen hashes must equal §1's. If any differs, stop; nothing else runs.
- **The new export.** The `grep -c` on the glue must print `1`. The wasm export names are minified: in v19's glue, `_oxsdk_document_redo` maps to `wasmExports["Ra"]`. So the glue's mapping line is where the export shows up.
- **Writer only.** The `ScDocShell` count must be `0`, as it is for v19. The profile is Writer only; v12 and v14 had 18.
- **X1 (condition 49).** It must print `VERDICT PASS` and exit 0, with exactly the three declared deltas and nothing undeclared. v20's wasm must differ from `1aafd4f9…`. The `loader … equal / differs` line is a one-time record, not a criterion.
- **Archive at once.** The main session then archives v20 (finding 036: the wasm is not a function of the source) into `build/archive/e2-editor-v20-<wasm sha8>-worker-478d0da1/`. The directory holds `probe.wasm`, `probe.js`, `sdk-worker.js`, `sdk-manifest.json`, `exports.txt`, `SHA256SUMS` and an `ATTRIBUTION.md` that says the worker comes from the tree and the packs are v18's under `dist/profiles/resources/`.
- **M1-1 again.** Run both commands from §0 item 2 again. The tool reads sources, so the results must be the same.

## 4. After the link (the main session's)

1. **First v20 shakedown on WASM**, from handoff 10-13g Next 4. Every run named here is its own §34.4 witness the first time it runs on v20.
   - **Merge.** The merge shakedown, and P1 on the 60-page fixture and on the mixed-page fixture (10-13m). A runner that maps a point to a page must say which rule it uses: inside a rectangle, or nearest rectangle.
   - **Page rectangles.** P2's discriminating arm (§12.3). It decides whether review 6's Q4 precondition, a lone `DOCUMENT_SIZE_CHANGED` flush, occurs on WASM. If it does, finding 138 was BLOCKING before the count, and condition 45 has already fixed it in v67.
   - **§10.7's arms, before counting.** Run `judge_held_into_refusal.py:266–282` (`start-press`, `start-hold`, `end-hold`, `end-press-type`, `cell-start-hold`) and `restore-window` in the 136 judges. Under C they expect 0 refusals, generations `['1']`, the document unchanged and the marker at the caret.
2. **Bind.** `BINDING` for v20 is set in its own commit.
3. **The full count chain**, run overnight and detached from the session (the owner's 2026-10-12 rule: the count is batched with the next engine change). This is the batched count for every uncounted change since 0.2.12: 0.2.13–0.2.18, and v20 with v67.
4. **The Writer stack sweep** (ruling 6 condition 52): two diagnostic directories, removed afterwards. Never run it at the same time as a counted run.
