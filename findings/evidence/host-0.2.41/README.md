# Host 0.2.41 preparation: Writer v25 with shell generation 79 (finding 173 page fix)

Declared before packaging, 2026-10-29 (spec `specs/SPEC-M3-shell-v79-finding-173.md` 5.7; work order `handoff/WORKORDER-173-blank-document-bullet-page-fix.md`).

**Live predecessor** (verified 2026-10-29 ~23:35 +0800, read-only): host `/home/jiajun/Projects/Nextcloud_Apps/litecore` on `main` at **ae1f9db** (0.2.40), clean; its `engine/` equals `wasm_sdk_probe/build/archive/host-0.2.40-engine-a08bc6ecb7241448` file by file (93 files; the archive's own `archive.sha256` checks).

**Candidate scope**: isolated worktree `wasm_sdk_probe/build/host-0.2.41/litecore`, branch **host-0.2.41**, commit **2bb5718** (only `appinfo/info.xml` 0.2.40 -> 0.2.41). Package the current three-page closure from `dist/` with the canonical packager. The editor page is generation 79's (`9cb6ea1f…`, profile still `e2-editor-v25`); viewer v3, Calc v2 and the 0.2.38 dark-theme HTML retained. **Expected delta against 0.2.40: exactly two changed records** (`e2-editor-app.js`, `editor-shell-v2/paragraph-editor-client.js`), nothing added or removed; `prepare-release.py` refuses anything else.

**Evidence gate** (`prepare-release.py` refuses otherwise): 0.2.40's gate unchanged (carried-over v24 counts; v25 F1, F2, F3 `read-02`, F4, section 9 reader) plus spec v79's: U1 and U2 (red before, green after), all shell tests green, B1 `B1_HOLDS`, F3-79 by both readings (`F3_HOLDS` under spec v25 16/16.1, `F3_79_EQUAL` against v25 F3 run-02), F4-79 24/24, V0′ `V0_PRIME_HOLDS`, E1-C intact after the V0′ put-back.

**Scripts** (each derived from its 0.2.40 counterpart, which is not edited; the closed list of differences is in each docstring): `prepare-release.py`, `offline-package-check.py`, `install-0.2.41.py`, `rollback-package.sh` (exact 0.2.40 engine, label stays 0.2.41), `capture-after.py`. Files workflow: the unchanged `wasm_sdk_probe/tools/run_calc_editor_host.py`.

**DDEV**: not touched by any step before the install. The install needs a NEW owner slot with an explicit no-site answer (`slot.json`); fgp-nc and nc-bridge stay stopped by the owner's choice of 2026-10-29.

After install: the Files workflow and `capture-after.py` as for 0.2.40, then the owner's own hand test (Files "+ New -> New document" -> bullet -> type -> save), which is the route B1 does not take (spec section 6, L-mirror-open-route).

Not in this package: K. Nominal shipped host stays 0.2.26.

## Offline results (2026-10-29 ~23:40 +0800)

- `prepare-release.py` (`package-run-01.*`, exit 0; canonical packager 159.2 s): engine **829a988e199ebc43**. Against the live 0.2.40 predecessor: **44 records identical, exactly two changed** (`e2-editor-app.js`, `editor-shell-v2/paragraph-editor-client.js`), nothing added or removed; editor page `9cb6ea1f…`, profile `e2-editor-v25`; viewer/Calc page identities and HTML unchanged; both codings decode to the exact current `dist/` bytes. Evidence gate (`release.json`): `v25Gates` all hold and `v79Gates` all hold (U1, U2, shell tests, B1, F3-79 both readings, F4-79, V0′, E1-C).
- Archive `wasm_sdk_probe/build/archive/host-0.2.41-engine-829a988e199ebc43` (not in git), MANIFEST sha256 `535a9ca5…`, all 94 members bound by `archive.sha256`.
- `check-delta.py` -> `check-delta.json`: **DELTA_HOLDS**, re-derived from the two archived MANIFEST files; five red cases (one more changed record, one fewer, a changed profile file, an added record, a removed record) each red.
- `offline-package-check.json`: **PACKAGE_HOLDS**, zero problems, **22/22** red cases red.
- `offline-install-preflight.json`: **OFFLINE_INSTALL_READY** (parent ae1f9db, candidate 2bb5718, `liveMutation: false`).

Next: an owner slot with an explicit no-site answer (`slot.json`), then `install-0.2.41.py --preflight-only`, `install-0.2.41.py`, the Files workflow, `capture-after.py`, and the owner's hand test.

## Live installation (owner slot 23:51:55 2026-10-29 - 00:30 2026-10-30 +0800, `slot.json`)

The owner answered the slot question "A: install now" (no-site during the install); only litecore and the router ran throughout (`ddev-before.json`, `ddev-after-slot.json`); fgp-nc and nc-bridge stay stopped by the owner's earlier choice.

- `install-0.2.41.py --preflight-only` -> **LIVE_PREFLIGHT_READY** (`install-20261029T235201+0800/`): protected documents 24674/24920/25391 read 200; `oc_files_lock` **zero rows**.
- `install-0.2.41.py` -> **CANDIDATE_INSTALLED** (`install-20261029T235218+0800/`): fast-forward ae1f9db..2bb5718 (info.xml only), exact engine rsync, `occ upgrade` to 0.2.41; protected documents and full lock rows equal before/after; e2-editor/ods-viewer/ods-editor unauthenticated routes all **401**.
- **Files workflow** `files-workflow-01/` (unchanged `run_calc_editor_host.py`, Chrome + Firefox): **52/52 PASS**; cleanup: no owned unlocks, share and user removed, folder DELETE 204; every entry landed on `/r/829a988e199e…`. Same stated limit as 0.2.40's run: the Writer arm inserts through the page's insert-text field; finding 173's fix is established on the mirror (B1, real input), not re-measured on this host -- the owner's hand test is that measurement.
- `capture-after.py install-20261029T235218+0800 files-workflow-01` -> `post-install-identity.json` **holds: true** (host 2bb5718 clean, installed_version 0.2.41, buildId 829a988e199ebc43, engine equals the archive, documents and lock rows equal the installer's after-state, owned folder 404, temporary user absent). The first invocation omitted the two positional arguments and died on `sys.argv[1]` (`post-install-identity.missing-args.stderr.txt`), an operator slip.
- Red cases (`post-install-red/`), built as 0.2.40's were: one flipped workflow check with the report's `ok` as the runner computes it (`run_calc_editor_host.py:290`, `ok = all(checks)`) -> exit 1 (`failed: ['owned-folder']`); the predecessor build id in one Writer entry -> exit 1 (`buildIdInEveryEntry: false`).
- **Named limit, found by the first red-case construction** (`post-install-red/flipped-check-only-the-cell/`, exit 0, `holds: true` with `failed: ['owned-folder']`): `capture-after.py` (an exact copy of 0.2.40's, which is itself a copy of 0.2.39's) gates on the runner's summary `report['ok']` and lists failed cells without gating on them. A report whose cells and summary disagree is not one the runner writes, so the installed 0.2.41 read is not affected; recorded rather than patched (the derived script may differ only in its docstring). A successor that re-derives `ok` from the cells is a candidate for the next host's scripts.

Status: **0.2.41 is installed as the daily uncounted candidate**, superseding 0.2.40. Nominal shipped host stays **0.2.26**; K has not run. Rollback, if needed: `rollback-package.sh` (exact 0.2.40 engine; needs a slot).

## Owner's hand test (2026-10-30, appended)

Files "+ New -> New document", bullet pressed on the blank paragraph: **the bullet is applied and no 「引擎需要重新開啟」
notice appears** -- finding 173's fix holds on the host route (spec v79 section 6, L-mirror-open-route, now
measured by a person). The toast that appears is the run() error style: red, prefixed `項目符號：MUTATION_OUTCOME_UNKNOWN：
the synchronous selection read did not provide readable text; the format mutation outcome is unknown`, then 083's
sentence. The owner read it as a warning. That presentation is pre-existing for every `review` disposition
(`web/e2-editor-app.js` run() catch, ~2144-2181) and is filed as finding 174. Typing and saving after the bullet
were not reported by the owner.

