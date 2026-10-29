# Host 0.2.41 preparation: Writer v25 with shell generation 79 (finding 173 page fix)

Declared before packaging, 2026-10-29 (spec `specs/SPEC-M3-shell-v79-finding-173.md` 5.7; work order `handoff/WORKORDER-173-blank-document-bullet-page-fix.md`).

**Live predecessor** (verified 2026-10-29 ~23:35 +0800, read-only): host `/home/jiajun/Projects/Nextcloud_Apps/litecore` on `main` at **ae1f9db** (0.2.40), clean; its `engine/` equals `wasm_sdk_probe/build/archive/host-0.2.40-engine-a08bc6ecb7241448` file by file (93 files; the archive's own `archive.sha256` checks).

**Candidate scope**: isolated worktree `wasm_sdk_probe/build/host-0.2.41/litecore`, branch **host-0.2.41**, commit **2bb5718** (only `appinfo/info.xml` 0.2.40 -> 0.2.41). Package the current three-page closure from `dist/` with the canonical packager. The editor page is generation 79's (`9cb6ea1f…`, profile still `e2-editor-v25`); viewer v3, Calc v2 and the 0.2.38 dark-theme HTML retained. **Expected delta against 0.2.40: exactly two changed records** (`e2-editor-app.js`, `editor-shell-v2/paragraph-editor-client.js`), nothing added or removed; `prepare-release.py` refuses anything else.

**Evidence gate** (`prepare-release.py` refuses otherwise): 0.2.40's gate unchanged (carried-over v24 counts; v25 F1, F2, F3 `read-02`, F4, section 9 reader) plus spec v79's: U1 and U2 (red before, green after), all shell tests green, B1 `B1_HOLDS`, F3-79 by both readings (`F3_HOLDS` under spec v25 16/16.1, `F3_79_EQUAL` against v25 F3 run-02), F4-79 24/24, V0′ `V0_PRIME_HOLDS`, E1-C intact after the V0′ put-back.

**Scripts** (each derived from its 0.2.40 counterpart, which is not edited; the closed list of differences is in each docstring): `prepare-release.py`, `offline-package-check.py`, `install-0.2.41.py`, `rollback-package.sh` (exact 0.2.40 engine, label stays 0.2.41), `capture-after.py`. Files workflow: the unchanged `wasm_sdk_probe/tools/run_calc_editor_host.py`.

**DDEV**: not touched by any step before the install. The install needs a NEW owner slot with an explicit no-site answer (`slot.json`); fgp-nc and nc-bridge stay stopped by the owner's choice of 2026-10-29.

After install: the Files workflow and `capture-after.py` as for 0.2.40, then the owner's own hand test (Files "+ New -> New document" -> bullet -> type -> save), which is the route B1 does not take (spec section 6, L-mirror-open-route).

Not in this package: K. Nominal shipped host stays 0.2.26.
