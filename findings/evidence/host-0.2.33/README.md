# Host 0.2.33: v3 viewer package and installation evidence

Spec: `specs/SPEC-M4-viewer-v3.md` section 16. V3-SEE was confirmed by the owner on 2026-10-24 (exact words in `m4-ods/viewer-v3/phase-e/human-preview/owner-confirmation.md`).

## Candidate prepared before installation

- Host branch `host-0.2.33`, commit **4f7f870** on **bffc7dc**: only `appinfo/info.xml` changes, 0.2.32 -> 0.2.33. The isolated worktree is recorded in `release.json`; the live main remains untouched at preparation time.
- `make ods-viewer-assets` copied only the viewer source module to dist (`stage-assets.txt`), compiling/relinking nothing. The packager was invoked with an explicit isolated `--app`; see `package.txt`.
- Schema `litecore-engine/3`, buildId **a67beefefebe57d6**: **35** decoded files, **345,292,248 B**, gzip **118,065,155 B**, zstd **85,087,410 B**. Page table: editor e2-editor-v22 / f7a40bcc, viewer ods-viewer-v3 / ebb7e0cb.
- Against package 80349a1a24cecb17: **28 identical**, only `ods-viewer-app.js` changed among common paths, six v2 profile paths removed and six v3 paths added (`manifest-diff.json`). The entire derived editor closure (**22 files**, including coding/hash metadata) is identical. No editor behavior change is claimed.
- Largest gzip: viewer wasm **49,530,696 B** (cap 52,428,800); largest zstd: **37,177,361 B** (cap 45,000,000). Existing frame-window checks pass.
- Archive: `wasm_sdk_probe/build/archive/host-0.2.33-engine-a67beefefebe57d6/`. **71 files** copied, compared to the isolated package, then checked with `archive.sha256`; output `archive-verification.txt`. Only ATTRIBUTION.md is extra in the archive.

## Offline checks

- Packager self-test **13/13**.
- `offline-package-check.py <isolated-worktree>`: K0/Z0/H5-1 **0 problems**, **22/22** package red cases red.
- Same script on live 0.2.32: exit **1**, **16** problems against the new closure/binding (`offline-package-check-control-live-0.2.32.txt`). The live package itself was not modified.
- `check_m3_assets.BUILD_ID` now binds the measured new package. This is a package binding, not a judge change. Section 34.4 +0 / +0, cumulative 46 / 27.

## Scripts and functional rollback

`install-0.2.33.sh` validates the recorded live/candidate commits and parent, clean main, old live engine against the 0.2.32 archive, new archive checksums, an open owner-named window, and only litecore running **before** changing anything. Then fast-forward merge, copy the archived package, occ upgrade and route smoke checks. `--preflight-only` stops before mutation.

`chain-phase-h.sh`: unchanged H1/H2/H3/H6 viewer criteria, H4's two-browser three-round H-154c/H-154o/H-155 and host-entry. Each step checks the time window, ddev running set and wallet. The new chain captures each return code before timestamping and stops on nonzero; it does not change any criterion. Raw H reports use the existing shakedown namespace with unique timestamps, H155 writes into this directory.

`script-guards.json`: synthetic ddev-list fixtures verify that stopped litecore and another running project refuse; a valid preflight performs no live mutation. The closed-window Phase H control exits 3. All three scripts pass `bash -n`. **These controls run no real ddev command or Phase H.** Actual ddev observations are recorded separately.

If a Phase H criterion is red, read its raw data before taking the specified rollback: `bash findings/evidence/host-0.2.33/rollback-package.sh`. This restores only the engine from **host-0.2.32-engine-80349a1a24cecb17**; leave the host version at 0.2.33, with no reset/downgrade/occ. Both archives remain available.

Installation/Phase H results will be appended after execution. H7 remains the owner's Files-path observation; the completed mirror V3-SEE does not replace it. Full count chain K remains batched and nominal shipped host remains 0.2.26.
