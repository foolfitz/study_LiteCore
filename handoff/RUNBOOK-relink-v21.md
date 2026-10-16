# Runbook: the v21 link — Ctrl+Home/End (finding 142) and Markdown paste (**the link command is the owner's to run**)

Written 2026-10-16. It follows [`RUNBOOK-relink-v20.md`](RUNBOOK-relink-v20.md) and rests on:

- `specs/SPEC-M3-link-batch-v21.md`. Criteria pinned at `523871fa`; §11 is the criteria table; §12.1 is the valid-UTF-8 rule.
- Implementation commits:
  - `bc6534e0` (part S: worker, SDK, shell, page);
  - `516e53e4` (part E: engine, ABI 5, v5 builder, X1, Makefile block);
  - `497aa9f7` (worker pin, static M1-1 carrier, `what_the_link_ships` variant).

A link mints a new identity. v8, v15, v18, v19 and v20 keep their own build and dist directories, so they stay as they are. v21 binds nothing until its `BINDING` commit, which comes after the link and the WASM shakedown.

## What this link ships

- **Engine:** `probe.wasm` / `probe.js`, linked from the tree with v20's defines plus `-DOXSDK_E2_V21_LINK_BATCH`.
  - `move-document-start` / `move-document-end`: wire ids 22/23, internal ids 24/25, `Key::HOME|Mod1` / `Key::END|Mod1` on the key path, non-mutating.
  - Editor ABI 5.
  - The `paste-markdown` document export, with the md4c pre-scan in `src/markdown_paste.hpp` and the `.uno:Undo` payload judge.
  - `md4c.c` is **not** compiled into the engine: the scan calls the core's `md_parse`, which is already in the link.
- **Worker:** the tree's `sdk/sdk-worker.js`, sha256 `0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350`. The recipe refuses any other bytes.
- **Export list:** v20's plus `_oxsdk_document_paste_markdown`, appended last.
- **Packing:** v20's (resource packs, `--inline-range-gestures all`, `--page-rectangles`), through the new **v5 builder** with `--paste-markdown`. It writes:
  - ABI 5;
  - the two actions with `["collapsed"]` / `["no-extend-selection"]`;
  - `editorContract.pasteMarkdown = "document-sdk-paste-markdown"`.
- **Not in the profile:** the page and shell changes. They ship in shell generation v74, which is frozen **after** the WASM shakedown (spec §9.2: the fallbacks may change the shell).

## 0. Gates before the link (state on 2026-10-16)

1. ✅ **Criteria pinned before implementation**: `523871fa`. The M0 fixture was committed before any scanner code: `975343c2`.
2. ✅ **Unit and model tests** (the main session re-ran them):
   - `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs`: 561/561.
   - The M0 model test: 65 items, 478 checks, `ok`. `python3 tests/markdown_paste_mutations.py`: every mutation red, final `ok`.
   - `python3 -m unittest tests.test_merge_key_undo_scope tests.test_profile_identity tests.test_e2_editor_v4_profile tests.test_e2_editor_v5_profile`: 94 OK.
   - `tests/editor_abi_header_test.cpp` exits 0 both with and without the v21 define.
3. ✅ **E1-C**: `python3 tools/check_e1_c_bundle_intact.py` gives `"intact": true`.
4. ✅ **M1-1** (part E's run; `findings/evidence/link-batch-v21/part-e-red/m1-1-*`). Both exit 0:
   - `python3 tools/check_merge_key_undo_scope.py --base 523871fa --carrier E2_V21=probe_engine,sdk_api,editor_api`
   - `python3 tools/check_merge_key_undo_scope.py --base 5d77dc84 --carrier E2_V15 --carrier E2_V19 --carrier E2_V20=probe_engine,sdk_api,editor_api --carrier E2_V21=probe_engine,sdk_api,editor_api`
5. ✅ **What the link compiles differently**: `python3 tools/what_the_link_ships.py --since 543a5566 --variant link-batch-v21 --shipped-profile dist/profiles/e2-editor-v20` (`findings/evidence/link-batch-v21/pre-link/`).
   - Result: `ok: true`, `configurationDrift: []`.
   - Changed: `probe_engine`, `sdk_api`, `editor_api`. Identical: `unoembind_stub`.
   - Worker: `478d0da1…` → `0d55bcfa…`.
   - Because there is no drift, no md4c object is among ours.
6. ✅ **`make -k test-e2-c-static`** is red only where expected (`pre-link/README.md`):
   - the shell bundle check, because v74 is not frozen;
   - `check_gesture_offers.py`, because there is no v21 manifest before the link.
7. ✅ **v20 is archived** at `build/archive/e2-editor-v20-313b08d5-worker-478d0da1/`. Its four files equal the dist copy (`cmp`, four `same`).
8. ✅ **The core link inputs** have not changed since v20's link. The `find … -newer build/e2/editor-v20/probe.wasm` from RUNBOOK-relink-v20 §0 printed `0`. **Run it again in your shell right before the link** (§2).
9. ✅ **The frozen set before the link**: `findings/evidence/link-batch-v21/pre-link/frozen-set-before.sha256`. It holds 1,306 files under `dist/profiles/` and `build/archive/`.

## 1. Do not run any other make target

The headers changed (`sdk_api.h`, `probe_engine.hpp`, `editor_api.h`), and every rule lists the Makefile as a prerequisite (finding 042). make now treats **every** older profile target as out of date. M1-1 shows their preprocessed output is unchanged, so this is make's view, not a real change.

- Their links refuse without `ALLOW_FROZEN_RELINK=1`.
- **Never pass that flag for v8, v15, v18, v19 or v20.**

## 2. The link (**the owner's step**)

```
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
L=../wasm-lite/build-headless-probe; find $L/instdir/program $L/workdir/LinkTarget $L/workdir/CustomTarget/static/emscripten_fs_image ../libreoffice-26-8/static/emscripten/environment.js -newer build/e2/editor-v20/probe.wasm -type f | wc -l   # must print 0
env | grep -E '^(LOSRC|LOBUILD|EMSDK_ROOT|EXTRA_DEFINES|EXTRA_OBJECTS|HOST_CXX)='   # must print nothing
env -u LOSRC -u LOBUILD -u EMSDK_ROOT -u EXTRA_DEFINES -u EXTRA_OBJECTS -u HOST_CXX \
    make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v21/sdk-manifest.json 2>&1 | tee build/link-v21.log
```

- **`ALLOW_FROZEN_RELINK=1` on this one target only.** The v21 rule is guarded from its first link, like v20's.
- **What it does:**
  1. Compiles `build/e2/editor-v21/{sdk_api,probe_engine,unoembind_stub,editor_api}.o`. The define and the md4c `-I` are on those four compile lines only.
  2. Regenerates `build/r5/writer-review/exports.txt` (a text file, not frozen).
  3. Writes `build/e2/editor-v21/exports.txt`, then links `build/e2/editor-v21/probe.{js,wasm}`.
  4. Checks the worker pin (`sha256sum -c` against `0d55bcfa…`) and the packs.
  5. Packs `dist/profiles/e2-editor-v21/` with the v5 builder.
- **Expected time:** four compiles plus the link. v20's link alone took about two minutes; with the compiles, allow about 10 minutes. Load stays at one compile at a time, because the rule is not run with `-j`.
- **If the `find` prints anything other than 0, or the `env` check prints anything, stop and tell the main session before linking.**

## 3. Right after the link: what to send back

Send the last 20 lines of `build/link-v21.log` and the output of:

```
sha256sum dist/profiles/e2-editor-v21/{probe.wasm,probe.js,sdk-worker.js,sdk-manifest.json}
```

The main session then does the rest itself:

- **The frozen set:** every file under `dist/profiles/` and `build/archive/`, except `dist/profiles/e2-editor-v21/`, must equal `pre-link/frozen-set-before.sha256`. If any differs, stop. Nothing else runs.
- **The new export:** `grep -c '_oxsdk_document_paste_markdown"\]=_oxsdk_document_paste_markdown=wasmExports\[' build/e2/editor-v21/probe.js` must print `1`.
- **Writer only:** `grep -a -o ScDocShell dist/profiles/e2-editor-v21/probe.wasm | wc -l` must print `0`.
- **X1 (spec §11.3 I1):** `VERDICT PASS`, exit 0.

  ```
  python3 tools/check_profile_identity.py --candidate dist/profiles/e2-editor-v21 \
      --reference dist/profiles/e2-editor-v20 \
      --candidate-exports build/e2/editor-v21/exports.txt \
      --reference-exports build/archive/e2-editor-v20-313b08d5-worker-478d0da1/exports.txt \
      --declared-worker 0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350 \
      --declared-export _oxsdk_document_paste_markdown \
      --declared-new-leaf .editorContract.pasteMarkdown=document-sdk-paste-markdown \
      --declared-new-leaf .editorContract.actions.move-document-start.id=22 \
      --declared-new-leaf '.editorContract.actions.move-document-start.gestures[0]=collapsed' \
      --declared-new-leaf '.editorContract.actions.move-document-start.limits[0]=no-extend-selection' \
      --declared-new-leaf .editorContract.actions.move-document-end.id=23 \
      --declared-new-leaf '.editorContract.actions.move-document-end.gestures[0]=collapsed' \
      --declared-new-leaf '.editorContract.actions.move-document-end.limits[0]=no-extend-selection' \
      --declared-changed-leaf .editorContract.abiVersion 4 5
  ```

  If the v20 archive has no `exports.txt`, use v20's `build/e2/editor-v20/exports.txt` and say so.
- **Archive at once** into `build/archive/e2-editor-v21-<wasm sha8>-worker-0d55bcfa/`: `probe.wasm`, `probe.js`, `sdk-worker.js`, `sdk-manifest.json`, `exports.txt`, `SHA256SUMS`, `ATTRIBUTION.md`. Finding 036: the wasm is not a function of the source.
- **M1-1 again:** both §0 item 4 commands. The tool reads sources, so the results must be the same.

## 4. After the link (the main session)

1. **The v21 WASM shakedown on the no-host page:** spec §11 D1–D13 and M1–M11, N=3 per browser, with the runners written first and red first.
   - The page is pointed at v21 with `tools/build_cutover_page.py --profile e2-editor-v21`.
   - If a fallback fires (spec §9.2, §11 defaults), the shell is changed **before** the freeze.
2. **Freeze shell generation v74.**
3. **Host 0.2.25:** ask the owner before installing. Then `BINDING` for v21, in its own commit.
4. **The full count chain**, in the owner's window, detached from the session.
