# Runbook: the first link of `ods-viewer-v2` (**the link command is the owner's to run**)

Written 2026-10-21, before the v2 core exists. It rests on `specs/SPEC-M4-viewer-v2.md` §2 (the core, K-1/K-2/F), §3 (engine, shell, profile, static checks) and §4 (the v2 criteria), all pinned before any v2 link or run; and on the core build of [`RUNBOOK-ods-viewer-v2-core-build.md`](RUNBOOK-ods-viewer-v2-core-build.md).

**This link mints a new identity and touches no existing one.** It writes only `build/ods/viewer-v2/` and `dist/profiles/ods-viewer-v2/`. `ods-viewer-v1`, the ODT editor `e2-editor-v22`, shell v75, host 0.2.31 and package `1b4d6a1fc905fb8a` are not rebuilt, repacked or re-pinned.

## What this link ships

- **Engine:** today's `src/` in v1's shape (`-DOXSDK_READER_PROFILE -DOXSDK_ODS_VIEWER`) plus `-DOXSDK_ODS_VIEWER_V2`: `part_info` (157), part_text's 10 s wait and its three fields (160), the `form-controls` bit read from the core's own `config_features.h` (158-B). Under v1's defines the sources preprocess to v1's tokens (spec §3.1).
- **Core:** `wasm-lite/build-ods-viewer-v2` (159's bridge signatures, 158-B's DB connectivity). Fallback F: the same rule with `ODS_VIEWER_V2_CORE=../wasm-lite/build-a11y-gate0` (159 applied incrementally there first; spec §2.5).
- **Link line:** v1's, token for token, with the core paths following `ODS_VIEWER_V2_CORE`.
- **Export list:** v1's plus `_oxsdk_document_part_info`; the recipe refuses save or any editor symbol.
- **Worker:** `sdk/sdk-worker.js`, sha256 `9c85043ac7618e38062c1d0168a982708a16c930bdf8a422a67190222a888d84`.
- **Packs:** base = `classify()`'s base group of the v2 core's image minus `35-lang-normalize.conf` (procedure checked against `9901e9be` on gate0 at every build); `cjk-sub-e10` and `fallback-fonts-r5` by path.

## 0. Gates before the link

1. ✅ Criteria pinned before any v2 execution: spec §2 (`17c5d50b`), §3–§4 (`99d06192`), §3.8 (`b042461c`).
2. ✅ Syntax: `em++ -fsyntax-only` on `probe_engine.cpp` and `sdk_api.cpp` with v1's and with v2's defines, exit 0; V2 alone → `#error`.
3. ✅ v1's tokens unchanged (`findings/evidence/m4-ods/viewer-v2/pre-link/v1-preprocessed-against-17c5d50b.txt`).
4. ✅ Unit tests and red cases (spec §3.7, §3.8); Phase E selftest 43/43; the new shell and harness exercised on v1 (`pre-link/v1-shakedown-new-shell/`).
5. ✅ **K-1 and K-2 green** (2026-10-22 01:19; spec §5.1) on `wasm-lite/build-ods-viewer-v2` (`findings/evidence/m4-ods/viewer-v2/core/k1-configure.json`, `k2-built.json`) — or fallback F taken and recorded.
6. ✅ **`make -k test-e2-c-static` exit 0** (`pre-link/test-e2-c-static-green-v2-core-built.txt`) with the v2 core configured (red until then: `pre-link/test-e2-c-static-red-v2-not-declared-core-not-configured.txt`).
7. ✅ **The builder's check on the v2 core** (base `07ef15cd`, 9 changed files read in spec §5.2; a report-writing bug fixed first, §5.4): `python3 tools/build_ods_viewer_v2_profile.py --check --report …/pre-link/base-pack-check.json` ok (positive control 9901e9be), and the diff against v1's base **read and written into spec §5** before §2 is handed over.
8. ✅ **The core provides Calc:** `check_core_build_provides.py --build ../wasm-lite/build-ods-viewer-v2 --capability calc-spreadsheet` exit 0.
9. ✅ **Link line vs v1's** (`pre-link/link-token-diff-v1-v2.txt`) (`make -n` of both rules, diffed): only the core paths, the define, the object/export paths and the one export differ.
10. ✅ **The frozen set before the link:** `pre-link/frozen-set-before.sha256`, 1,517 files, taken 2026-10-22 right before §2 was handed over.

## 1. Do not run any other make target

The Makefile changed, so make treats every older profile target as out of date (finding 042). Their links refuse without `ALLOW_FROZEN_RELINK=1`; **never pass that flag for any other target.**

## 2. The link (**the owner's step**, once §0 is all ✅)

```
cd ~/LibreOffice/study_LiteCore/wasm_sdk_probe
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX
make ALLOW_FROZEN_RELINK=1 dist/profiles/ods-viewer-v2/sdk-manifest.json 2>&1 | tee build/link-ods-viewer-v2.log
```

- Expected: about as long as v1's (a few minutes). One job at a time.
- The last line it prints is the wasm's gzip size against 52,428,800 (estimated about 49.1 MB, spec §5.3). **`OVER -- fallback F-2`** there means stop and tell the main session.
- If it stops with an error, stop there; do not re-run with other flags.

## 3. Right after the link (the main session, the same day)

1. The frozen set unchanged; no new file outside `dist/profiles/ods-viewer-v2/`.
2. `check_pthread_stack_literal.py` VERDICT PASS; Calc in the bytes (`ScDocShell`); the forms in the bytes when K-1 said DB connectivity (`OFormsCollection`); `check_e1_c_bundle_intact.py` intact.
3. The manifest declares `part-info`, and `form-controls` exactly when the core's `config_features.h` says 1.
4. Archive at once into `build/archive/ods-viewer-v2-<wasm sha8>-worker-9c85043a/` with `SHA256SUMS` and `ATTRIBUTION.md`.
5. Witnesses under `findings/evidence/m4-ods/viewer-v2/post-link/`.

## 4. After that

Phase E on v2 on the mirror (`run_ods_viewer_phase_e.py --profile ods-viewer-v2`): first the ladder plus finding 157/158/159's files, then the full corpus ×3 for V2-160; E6's B measured again on v2 first. Then a new package and Phase H in an ddev slot the owner names.

## Done (2026-10-22)

Linked by the owner; §3 items 1–5 done the same night (spec §6, `findings/evidence/m4-ods/viewer-v2/post-link/`): probe.wasm `a6390eef…`, archived at `build/archive/ods-viewer-v2-a6390eef-worker-9c85043a/`, gzip 49,153,029. The make's closing `Error 1` was the gzip print line's quoting bug, after every check; fixed in the Makefile.

