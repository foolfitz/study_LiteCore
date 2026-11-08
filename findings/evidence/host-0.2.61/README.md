# Host 0.2.61: the Calc zoom anchor

Released for the hand-test slot the owner chose on 2026-11-08 (option A, "現在發 0.2.61"; CLAUDE.md, the section on cadence,
item 1). This is an uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. It was installed 2026-11-08
12:14 +0800.

- The host commit is `c308961` (a version bump only) on `8619e05` (0.2.60), branch `host-0.2.61`. The branch was made in a
  temporary worktree under `wasm_sdk_probe/build/` (removed afterwards), never in the host repo's working copy. The engine is
  `4216ebb22d4d98fc`, archived in `build/archive/host-0.2.61-engine-4216ebb22d4d98fc` (not in git).
- **One served file changed**: `ods-editor-app.js`, the Calc page's module, changed in place on profile `ods-editor-v8`
  (0.2.60's frozen engine, wasm `61e2a069`). The zoom now keeps the active cell's top-left in place while it is in view, else the
  view's top-left (SPEC-P-calc-zoom append 5, the owner's choice C after the 0.2.60 hand test; `../calc-zoom-anchor/`). The served
  delta was measured with the packager's closure against 0.2.60's MANIFEST before the inputs were written: 1 changed, 0 added,
  0 removed, 45 the same.
- **Writer is byte for byte 0.2.60's**: `e2-editor-v33`, shell generation 91. Its nets were not re-run (cadence item 5). The gate
  reads 0.2.58's generation-91 records, and `writerIdentity` generation 91 was verified when packaging.

| Read | Result |
|---|---|
| `../calc-zoom-anchor/` (units, first P, reds) | node 1070/1070, the three Calc mutation tools pass; `p-anchor-01` `P_HOLDS` 51/51 in Chrome 156 and Firefox 157; `centre-anchor` red at P-Z5, `fallback-centre` red only at P-Z10 |
| `../release-0.2.61/` (Calc release regression) | `chain-0261.sh`, the 0.2.60 nets with names suffixed -0261, on dist v8 with this page, tree `1c406c65f`, 11:51-12:11: C, CU, cell, range, autosave, P2, headers, structure, sheets, copy `--html` (10/10) and zoom (51/51) hold in both browsers |
| `gate` | 30 of 30: the anchor's first P and its two reds, Writer's generation-91 records, and the Calc release regression |
| `candidate`, `package`, `delta`, `offline` | packaged in 165 s; `DELTA_HOLDS` with 7 red cases; `PACKAGE_HOLDS` |
| `offline-install-preflight`, `live-preflight`, `install` | `OFFLINE_INSTALL_READY`, `LIVE_PREFLIGHT_READY`, `CANDIDATE_INSTALLED`; documents and locks preserved; unauthenticated routes 401 |
| `files-workflow-01/` | 52/52, both browsers and the read-only user; no owned unlocks, share and user removed, folder 204 |
| `capture-after` | `holds: true` (0.2.60's lock-row difference does not recur: that expired row was already gone) |
| `calc-host-arm/run-01` | `tools/calc_host_arm.py --arms zoom` (unchanged since 0.2.60) gives `H_CALC_HOLDS`: zoom 51/51 in each browser, on the user's path; cleanup: no owned unlocks, folder 204 |

## Hand test

The script is `HANDTEST-2026-11-08-host-0.2.61.md` (repo root, zh-TW, 5 items: the zoom anchor's three cases, a quick look at
0.2.60's other zoom behaviour, and an optional Writer check). The fixtures are in admin's `手測-0.2.61/`
(`handtest-fixtures/put.json`): `1-calc.ods` is the 0.2.59 and 0.2.60 hand-test file, byte for byte (its first sheet has data in
rows 1-5 and row 1000, the owner's case), and `2-writer.odt` is `test-docs/t1-plain-zh.odt`. Both were read back equal.

Rollback: `host_release.py rollback findings/evidence/host-0.2.61`, with `host-stack/bin` first on PATH, restores 0.2.60's engine
bytes (the centre anchor). The host label stays 0.2.61.
