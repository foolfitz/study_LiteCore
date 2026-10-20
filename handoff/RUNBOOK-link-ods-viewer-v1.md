# Runbook: the first link of `ods-viewer-v1`, the read-only spreadsheet viewer (**the link command is the owner's to run**)

Written 2026-10-20. It rests on:

- `specs/SPEC-M4-ods-in-nextcloud.md`, criteria pinned at `d7ab2815`, addenda 1–4 after it. §4 is the criteria table; addendum 3 pins the names.
- O2, the engine source, worker half and SDK: `762296f8` (`findings/evidence/m4-ods/o2-engine-source/README.md`).
- O3, the Makefile block, the profile builder and the pre-link gates: the commit that adds this file (`findings/evidence/m4-ods/o3-pre-link/`).

**This link mints a new identity and touches no existing one.** It writes only `build/ods/viewer-v1/` and `dist/profiles/ods-viewer-v1/`. The ODT editor (`e2-editor-v22`, shell v75, host 0.2.28) is not rebuilt, repacked or re-pinned.

## What this link ships

- **Engine:** today's `src/` compiled in the reader shape (`-DOXSDK_READER_PROFILE`, no editor define) plus `-DOXSDK_ODS_VIEWER`, against the **a11y+calc core** `wasm-lite/build-a11y-gate0` (every core path in the rule names `$(E2_V5_CORE)`). Objects: `sdk_api`, `probe_engine`, `unoembind_stub` (no `probe_api`, no `editor_api`, no a11y bridge).
- **Link line:** `e2-editor-v14`'s (the last link on this core) with one token changed, `-sDEFAULT_PTHREAD_STACK_SIZE=65536` → `1048576` (finding 089), and its own objects and export list.
- **Export list:** the reader's without save, plus `set_part`, `current_part`, `part_name`, `part_text`. The recipe refuses save or any editor symbol.
- **Worker:** `sdk/sdk-worker.js` with the viewer's operations (`762296f8`) and part_text's two reply fields (spec A4.7), sha256 `cc2d6514cde27b63ac4f9ce3ae3ba286e3a894cc99d879f3983f5e33ee8c1b5b`. The recipe refuses any other bytes.
- **Packs:** base `base-a11y-no35.6f7424a1c1427ad7.data` (e2-editor-v14's `9901e9be` minus `35-lang-normalize.conf`, finding 114) in the profile's own directory; the shipping `cjk-sub-e10` and `fallback-fonts-r5` by path under `../resources/`.
- **Not in the profile:** anything of the host. The viewer page is staged by the mirror runs (O5) and the packager (O6), later.

## 0. Gates before the link (state on 2026-10-20)

1. ✅ Criteria pinned before any viewer execution: `d7ab2815`; addenda 1–3 before this file; nothing has run on `ods-viewer-v1` (it does not exist).
2. ✅ **Link line vs v14's** (`o3-pre-link/link-token-diff.txt`, from `make -n`): four differences only — the object list, the stack token, the export list's path, the output path.
3. ✅ **Undefined symbols** (`o3-pre-link/undefined-symbols.txt`; the three units compiled to a scratch directory with the rule's flags, 0.06–1.1 s each, nothing written in the tree): of what the viewer's objects need, three were not resolved from the core at v14's link — `condition_variable::notify_all`, `to_string(int)`, `tolower` — all three emscripten's own libc++ / libc.
4. ✅ **Syntax:** `em++ -fsyntax-only` on all three units with the viewer's defines, exit 0, 0 warnings; with `OXSDK_MERGE_KEY_UNDO` added, refused by the viewer's `#error` (`o2-engine-source/syntax-checks.txt`, `o3-pre-link/README.md`).
5. ✅ **The editor rules' objects did not move:** 28 rules, 112 objects, 0 different (`o2-engine-source/preprocess-identity-base-fe8722df.json`).
6. ✅ **`make -k test-e2-c-static`: exit 0** after the Makefile change (`o3-pre-link/test-e2-c-static-green.txt`). Its M1-1 line now declares `ODS_VIEWER_V1=probe_engine,sdk_api`; without it the line is red on exactly those two objects (`…-red-viewer-not-declared.txt`).
7. ✅ **The builder's check:** `tools/build_ods_viewer_profile.py --check` ok (the base pack from `9901e9be` and from the core's original image, same sha `6f7424a1…`); its red case `--red-drop` is red (`o3-pre-link/builder-*.txt`).
8. ✅ **The core provides Calc:** `check_core_build_provides.py --build ../wasm-lite/build-a11y-gate0 --capability calc-spreadsheet` exit 0; the writer core, exit 1.
9. ✅ **The core's link inputs are not newer than v14's link:** `find` over `build-a11y-gate0/instdir/program`, its export list and its FS image, `-newer dist/profiles/e2-editor-v14/probe.wasm`, printed `0`. **The main session runs it again right before handing you §2** and tells you what it printed.
10. ✅ **The frozen set before the link:** `o3-pre-link/frozen-set-before.sha256`, 1,430 files under `dist/profiles/` and `build/archive/`.

## 1. Do not run any other make target

The Makefile changed, and every rule lists it as a prerequisite (finding 042), so make treats **every** older profile target as out of date. Nothing in them changed. Their links refuse without `ALLOW_FROZEN_RELINK=1`; **never pass that flag for any other target.**

## 2. The link (**the owner's step**)

Three short lines, in your own terminal:

```
cd ~/LibreOffice/study_LiteCore/wasm_sdk_probe
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX
make ALLOW_FROZEN_RELINK=1 dist/profiles/ods-viewer-v1/sdk-manifest.json 2>&1 | tee build/link-ods-viewer-v1.log
```

- **`ALLOW_FROZEN_RELINK=1` on this one target only.** The rule is guarded from its first link, like every product artifact.
- **What it does:**
  1. compiles `build/ods/viewer-v1/{sdk_api,probe_engine,unoembind_stub}.o`;
  2. writes `build/ods/viewer-v1/exports.txt` and refuses it if it carries save or an editor symbol;
  3. links `build/ods/viewer-v1/probe.{js,wasm}` against the a11y+calc core;
  4. checks the worker pin and runs the builder's `--check`;
  5. packs `dist/profiles/ods-viewer-v1/` and greps the wasm: the positive control `search-result` present, the viewer's `partBefore` present, the editor's `verified-caret-readback` absent. Any failure removes the manifest.
- **Expected time:** v22's four compiles and link took about three minutes. Allow 10 minutes. One job at a time (no `-j`).
- **If it stops with an error, stop there** and tell the main session. Do not re-run with other flags.

## 3. Right after the link

**Send back only "done"** (or "failed"). The main session reads `build/link-ods-viewer-v1.log` and does, the same day, in this order:

1. **The frozen set:** `sha256sum -c --quiet` over `o3-pre-link/frozen-set-before.sha256` prints nothing, and `find dist/profiles build/archive -type f` lists no new file outside `dist/profiles/ods-viewer-v1/`. If either fails, stop.
2. **The stack:** `python3 tools/check_pthread_stack_literal.py dist/profiles/ods-viewer-v1/probe.js` prints `VERDICT PASS`.
3. **Calc is in the bytes:** `grep -a -c ScDocShell dist/profiles/ods-viewer-v1/probe.wasm` is not 0 (v22's is 0).
4. **E1-C:** `python3 tools/check_e1_c_bundle_intact.py` gives `"intact": true`.
5. **Archive at once** into `build/archive/ods-viewer-v1-<wasm sha8>-worker-cc2d6514/`: `probe.wasm`, `probe.js`, `sdk-worker.js`, `sdk-manifest.json`, the base pack and its metadata, `exports.txt`, `SHA256SUMS`, `ATTRIBUTION.md`. Finding 036: the wasm is not a function of the source.
6. Commit the witnesses under `findings/evidence/m4-ods/o4-post-link/`.

## 4. After that (the main session)

- **E2 is the link's first run**, on a mirror, no host: the viewer page (its worker literal already names `ods-viewer-v1`, so no rewrite and no stack patch) on the corpus entries, then E1–E9 as pinned (spec §4, addenda).
- **The owner's first visible result** comes after E2: the viewer on a mirror page, with the engine's sheet names and working tabs. The main session will say when to look.
- Host 0.2.29 (O6) and its install in the owner's ddev slot (O7) come after Phase E.
