# Host 0.2.40 preparation: Writer v25 (findings 171/172 fixed), viewer and Calc retained

Declared before packaging, 2026-10-29 (spec v25 sections 8 step 7, 14-16; handoff 10-29f step 5).

**Live predecessor** (verified 2026-10-29 ~18:08 +0800): host `/home/jiajun/Projects/Nextcloud_Apps/litecore` on `main` at **4a8b3cd** (label 0.2.39), clean, with the **exact 0.2.38 engine** (`host-0.2.38-engine-5ad1f70a8c5f7d2f`, all 93 files equal) after this morning's rollback. So the candidate's parent is 4a8b3cd and its predecessor archive is the 0.2.38 one, not the 0.2.39 one.

**Candidate scope**: isolated worktree `wasm_sdk_probe/build/host-0.2.40/litecore`, branch **host-0.2.40**, commit **ae1f9db** (only `appinfo/info.xml` 0.2.39 -> 0.2.40). Package the current three-page closure from `dist/` with the canonical packager; the editor must be v25 (`e2-editor-v25`, page `6e66c930`, frozen shell 78), viewer v3, Calc v2 and the 0.2.38 dark-theme HTML retained. Archive exact bytes; keep the exact 0.2.38 rollback.

**Evidence gate** (`prepare-release.py` refuses otherwise): the carried-over v24 counts (`V24_SELECTION_COUNTS_HOLD`, A4-v24 24/24; owner's carry-over, spec v25 section 14) and v25's own checks by their recorded verdicts: F1 `F1_HOLDS`, F2 `F2_HOLDS`, F3 `F3_HOLDS` (**`read-02.json`**, spec 16.1), F4 24/24 PASS, section 9 reader `CONFINED_V25_HOLDS`.

**Scripts** (each derived from its 0.2.39 counterpart, which is not edited; the closed list of differences is in each docstring): `prepare-release.py`, `offline-package-check.py`, `install-0.2.40.py`, `rollback-package.sh` (exact 0.2.38 engine, label stays 0.2.40), `capture-after.py`. Files workflow: the unchanged `wasm_sdk_probe/tools/run_calc_editor_host.py`.

**DDEV**: the owner said at ~18:05 that DDEV can be used now and asked to stop the other DDEV containers; fgp-nc and nc-bridge were stopped at 18:06 (`ddev stop`), litecore left running. The installer additionally needs `slot.json` with the owner's no-site agreement and window; it is not written until the owner confirms those (the request to use DDEV is not, by itself, a no-site answer).

Not in this package: K (needs its own 8-10 h no-site window and the settled control protocol). Nominal shipped host stays 0.2.26.
