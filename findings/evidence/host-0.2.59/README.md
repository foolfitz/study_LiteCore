# Host 0.2.59: Calc copy, and the Calc sheet work (lock, position, name box, pointed references)

Released for the hand-test slot the owner named on 2026-11-06 (option A, "現在發布給你手測"; CLAUDE.md, the section on cadence,
item 1). This is an uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. It was installed 2026-11-06 12:44 +0800.

- The host commit is `480ba6b` (a version bump only) on `0bf488a` (0.2.58), branch `host-0.2.59`. The branch was made in a
  temporary worktree under `wasm_sdk_probe/build/`, never in the host repo's working copy. The engine is `a2e67f216957f322`,
  archived in `build/archive/host-0.2.59-engine-a2e67f216957f322` (not in git).
- Calc moves from `ods-editor-v6` to **`ods-editor-v7`** (wasm `36d0e1b8`, the owner's link; `../release-0.2.59/calc-v7-freeze/`).
  Two features: Ctrl+C (SPEC-P-calc-copy) and the sheet work (SPEC-P-calc-sheets: a lock on a protected sheet's tab, the sheet's
  position, a name box that takes a sheet, pointed references across sheets).
- **Writer is byte for byte 0.2.58's**: `e2-editor-v33`, shell generation 91. Nothing under `sdk/`, `editor-shell-v2/` or
  `viewer-shell/` changed. Its nets were not re-run (cadence item 5: the gate is bound to the engine package's identity). The gate
  reads 0.2.58's generation-91 records, and `writerIdentity` generation 91 was verified when packaging.
- The served delta was measured with the packager's closure against 0.2.58's MANIFEST before the inputs were written: **4 changed**
  (the Calc page's two files and its two shell files), 6 added and 6 removed (v6 -> v7), 36 the same.

| Read | Result |
|---|---|
| `../release-0.2.59/` (freeze, units, Calc release regression) | v7 three copies equal (`FROZEN_EQUAL`); node 1052/1052, the three Calc mutation tools pass; C, CU, cell, range, autosave, P2, headers, structure, sheets and copy hold on dist v7 in both browsers (12:25-12:40) |
| `gate` | 32 of 32: the two features' first measurements and reds, Writer's generation-91 records, and the Calc release regression |
| `candidate`, `package`, `delta`, `offline` | packaged in 152 s; `DELTA_HOLDS` with 7 red cases; `PACKAGE_HOLDS` |
| `offline-install-preflight`, `live-preflight`, `install` | `OFFLINE_INSTALL_READY`, `LIVE_PREFLIGHT_READY`, `CANDIDATE_INSTALLED`; documents and locks preserved; unauthenticated routes 401 |
| `files-workflow-01/` | 52/52, both browsers and the read-only user; no owned unlocks, share and user removed, folder 204 |
| `capture-after` | `holds: true` |
| `calc-host-arm/run-01` | **the new arm, on the user's path**: `tools/calc_host_arm.py --arms sheets copy` gives `H_CALC_HOLDS`. Sheets 9/9 and copy 6/6 in each browser; cleanup: no owned unlocks, folder 204 |

## The new arm (`calc-host-arm/`)

`tools/calc_host_arm.py` is 0.2.58's arm made into one tool with `--arms` (cadence item 2). It runs the mirror tools' `scenario()`
unchanged on a page opened the owner's way: admin logs in, the arm's fixture is PUT into an owned folder, its row in Files is clicked,
and the host route opens it with its lock. 0.2.58's copy in its evidence folder is left as it was. Neither new tool reads a
diagnostics-only field, so no reader with a registered limit is needed (unlike 0.2.58's P-H5). For the copy arm, Chrome is granted
clipboard permission for the host origin and Firefox runs with `dom.events.testing.asyncClipboard`. That is the mirror tool's
instrument, with its named limit: user activation is relaxed, so whether a real Ctrl+C may write the clipboard after the engine
round trip is for the owner's hand test.

## Hand test

The script is `HANDTEST-2026-11-06-host-0.2.59.md` (repo root, zh-TW, 10 items). The fixtures are in admin's `手測-0.2.59/`
(`handtest-fixtures/put.json`): `1-calc.ods` is `tools/create_calc_sheets_fixture.py`'s output (nine sheets) and `2-writer.odt` is
`test-docs/t1-plain-zh.odt`. Both were read back equal.

Rollback: `host_release.py rollback findings/evidence/host-0.2.59`, with `host-stack/bin` first on PATH, restores 0.2.58's engine
bytes (Calc on v6). The host label stays 0.2.59.
