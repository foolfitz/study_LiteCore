# Host 0.2.60: Calc copy with text/html, Calc zoom

Released for the hand-test slot the owner named on 2026-11-07 ("我現在可以手測了"; CLAUDE.md, the section on cadence, item 1). This
is an uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. It was installed 2026-11-07 23:51 +0800.

- The host commit is `8619e05` (a version bump only) on `480ba6b` (0.2.59), branch `host-0.2.60`. The branch was made in a
  temporary worktree under `wasm_sdk_probe/build/` (removed afterwards), never in the host repo's working copy. The engine is
  `e231564f02f2db7d`, archived in `build/archive/host-0.2.60-engine-e231564f02f2db7d` (not in git).
- Calc moves from `ods-editor-v7` to **`ods-editor-v8`** (wasm `61e2a069`; `../release-0.2.60/calc-v8-freeze/`). Two features:
  copy writes the core's `text/html` beside `text/plain` (SPEC-P-calc-copy 9-12), and zoom at 50/75/100/125/150/200%
  (SPEC-P-calc-zoom).
- **Writer is byte for byte 0.2.59's**: `e2-editor-v33`, shell generation 91. Its nets were not re-run (cadence item 5). The gate
  reads 0.2.58's generation-91 records, and `writerIdentity` generation 91 was verified when packaging.
- The served delta was measured with the packager's closure against 0.2.59's MANIFEST before the inputs were written:
  **5 changed**, 6 added and 6 removed (v7 -> v8), 35 the same. The changed files are the Calc page's two files, its two shell
  files, and `viewer-shell/ods-viewer-session.js` (`setScale`). The viewer page imports that file too, so its bytes change, but its
  module and profile do not. The C net in the release regression drives the viewer page.

| Read | Result |
|---|---|
| `../release-0.2.60/` (freeze, units, Calc release regression) | v8 three copies equal (`FROZEN_EQUAL`); node 1070/1070, the three Calc mutation tools pass; C, CU, cell, range, autosave, P2, headers, structure, sheets, copy `--html` and zoom hold on dist v8 in both browsers (23:28-23:48) |
| `gate` | 36 of 36: the two features' first measurements and reds (N copy-html, N zoom, P copy-html, plain-only red, P zoom, four zoom reds), Writer's generation-91 records, and the Calc release regression |
| `candidate`, `package`, `delta`, `offline` | packaged in 149 s; `DELTA_HOLDS` with 7 red cases; `PACKAGE_HOLDS` |
| `offline-install-preflight`, `live-preflight`, `install` | `OFFLINE_INSTALL_READY`, `LIVE_PREFLIGHT_READY`, `CANDIDATE_INSTALLED`; documents and locks preserved; unauthenticated routes 401 |
| `files-workflow-01/` | 52/52, both browsers and the read-only user; no owned unlocks, share and user removed, folder 204 |
| `capture-after` | **`holds: false`**. The only red field is `lockRowsEqualInstallAfter`: see below |
| `calc-host-arm/run-01` | **the new arms, on the user's path**: `tools/calc_host_arm.py --arms zoom copy-html` gives `H_CALC_HOLDS`. Zoom 41/41 and copy-html 10/10 in each browser; cleanup: no owned unlocks, folder 204 |

## capture-after: one expired lock row was deleted by files_lock

Every field holds except `lockRowsEqualInstallAfter`. Between the install's after-state (23:51:26) and the capture, one row left
`oc_files_lock`: id 6626, file 32123, created 2026-11-07 00:48:45 with ttl 421 s, so it had expired about 23 hours earlier.
File 32123 is admin's `手測-0.2.59/1-calc.ods`, the owner's 0.2.59 hand-test file. The Files workflow's own browsers fetched its
preview from the Files home page (`GET /core/preview?fileId=32123`, first at 23:52:09 by HeadlessChrome 156, then by Firefox 157;
`capture-lock-row-32123-access.txt`). Reading a file makes files_lock delete that file's expired lock. This is the limit the
capture's docstring already names (inherited from host-0.2.41 and host-0.2.43): the check compares the whole lock table. No row
was added or changed, and `globalLockTableWrites` is false. The tool is left as it is, and the verdict is recorded as it came out.

## The new arms (`calc-host-arm/`)

`tools/calc_host_arm.py` gains two arms (cadence item 2: arms, not a new tool). `zoom` runs `check_calc_zoom.scenario` and
`copy-html` runs `check_calc_copy.scenario(run, True)`, both unchanged, on a page opened the owner's way. After the browsers close,
`copy-html` runs P-H4 as the mirror's `main()` does: each browser's read-back HTML of A1:C2 is pasted by the native core
(`--native-harness`, `../calc-v8/native-build-01/v8/calc-undo-native`). In both browsers, A1 stays `原始中文 Alpha` in one cell.
Neither tool reads a diagnostics-only field. Clipboard instrument and its named limit as in 0.2.59: user activation is relaxed.

A prediction written before the run (in the session, not committed) was wrong. It said P-H3 would be red on the host because
Nextcloud's CSP would block the inline `<script>` that P-H3 uses to remove `ClipboardItem` in the page's world. P-H3 passed in
both browsers: `ClipboardItem` read back as `undefined`, and the copy fell back to `text/plain` alone
(`lastCopy.formats == ["text/plain"]`). So the measured fallback is real. It is not established whether the host's CSP would block
the same script without the automation.

## Hand test

The script is `HANDTEST-2026-11-07-host-0.2.60.md` (repo root, zh-TW, 10 items). The fixtures are in admin's `手測-0.2.60/`
(`handtest-fixtures/put.json`): `1-calc.ods` is 0.2.59's hand-test file, byte for byte (`calc-sheets.ods`, nine sheets), and
`2-writer.odt` is `test-docs/t1-plain-zh.odt`. Both were read back equal.

Rollback: `host_release.py rollback findings/evidence/host-0.2.60`, with `host-stack/bin` first on PATH, restores 0.2.59's engine
bytes (Calc on v7). The host label stays 0.2.60.
