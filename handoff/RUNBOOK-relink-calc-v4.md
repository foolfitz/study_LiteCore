# Runbook: link ods-editor-v4 (Calc document undo)

Spec `specs/SPEC-P-calc-undo.md` (sections 4 to 6). Owner-run: it compiles and links the engine. No core build: v4 links on the v3 core (`wasm-lite/build-ods-viewer-v2`). Writer is not touched.

## Before

- The tree at or after `9e8b15e15`, clean (`git status` shows only untracked files outside `wasm_sdk_probe`).
- `wasm_sdk_probe/build/ods/editor-v4` does not exist. `dist/profiles/ods-editor-v4` does not exist (its rule refuses once it does).
- Nothing else compiling: `uptime`, `pgrep -a make`.
- Pre-link checks already green (`findings/evidence/calc-undo/`): em++ `-fsyntax-only` in v4 and v3 configurations with positive controls (`pre-link-syntax-03`), every v4 export has a body (`pre-link-ships/green.json`, red case `red-before-fix.json`), the lock-scope check, Calc unit tests 67/67, the v4 worker test, the three Calc mutation tools, the native NU-3 (`nu3-undo`: single-cell bold and italic are one undo), Codex's review handled (`review/README.md`).

## The command (one line, about 3 minutes)

```bash
cd ~/LibreOffice/study_LiteCore/wasm_sdk_probe && make build/ods/editor-v4/profile/sdk-manifest.json 2>&1 | tee build/link-ods-editor-v4-01.log
```

Report back: the exit, and the last block it prints (the profile builder's JSON). It must say `"profile": "ods-editor-v4"` and `"capabilityBits": 1046835`. If the link fails, keep `build/ods/editor-v4` and the log as they are and report; do not clean or retry.

## After (the agent)

1. Read the log: four objects with `-DOXSDK_ODS_UNDO`, the link with `-sERROR_ON_UNDEFINED_SYMBOLS=1` passed, `exports.txt` ends with `_oxsdk_document_undo _oxsdk_document_redo`; `sdk-worker.js` equals `tools/derive_ods_v4_worker.py`'s output (sha256 `4a06fbe4…`).
2. Freeze: copy `build/ods/editor-v4/profile` to `dist/profiles/ods-editor-v4` and to `build/archive/ods-editor-v4-<wasm8>`, with `ATTRIBUTION.md` (memory: an archive name must identify everything it binds).
3. Switch the page: `web/ods-editor-app.js` `ENGINE_OPTIONS.workerUrl` to `./profiles/ods-editor-v4/sdk-worker.js`; `make ods-editor-assets` (copies only).
4. Write the CU tool (spec 4.5 and CU-9) and run it on the v3 page first (it must be red on CU-1 and CU-2), then on v4. Then the regressions: C (`check_calc_sheet_view.py`), the cell, range and autosave arms, P2, on v4; the native NU-3 again is not needed (the bridge source is the one measured).
5. Host 0.2.55: the Calc page and the new profile; derive the release tools from 0.2.54's.

## If something is wrong after the link

The v3 profile and the v3 page are untouched until step 3; the page keeps loading v3 until its pointer moves. Nothing to roll back before that.
