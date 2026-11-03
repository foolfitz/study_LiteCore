# Host 0.2.56: Word and Excel files

Spec `specs/SPEC-P-ms-formats.md`. Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. Installed 2026-11-04 01:37 +0800.
The release for the owner's next hand-test slot (CLAUDE.md, the section on cadence; `specs/PLAN-2026-11-04-measurement-after-cadence-reset.md`).

- Host `6def1da` (version bump) on `15abfff` (DOCX/XLSX Files action, controller mime sets, `documentFormat()` by mime, `saveAs()`), branch
  `host-0.2.56`, parent `5db53ac` (0.2.55). Engine `1b8dda1e17dd078c`, archive `build/archive/host-0.2.56-engine-1b8dda1e17dd078c` (not in git).
- Writer on `e2-editor-v33` (wasm `444519df`), shell generation 89; Calc on `ods-editor-v5` (wasm `4faad0af`); the viewer does not move.
- **The first release made with `wasm_sdk_probe/tools/host_release.py`**, one tool reading `release-inputs.json` here, instead of seven
  scripts derived from 0.2.55's. Every record it writes carries the tool's sha256 and argv. Witness: `tool-witness-0.2.55/` (on 0.2.55's
  archives the tool's delta reproduces the committed `DELTA_HOLDS` field for field; its offline reader gives the old tool's output on the
  same input).
- Served delta, measured with the packager's closure before the inputs were written: 7 files changed, Writer v32 -> v33 (4 files), Calc v4 -> v5
  (6 files), 29 the same.

| Read | Result |
|---|---|
| `host_release.py gate` (inside `package-run-01`) | 28 of 28: W both browsers and its red on v32/v4, W live on the frozen dist, F3 46/46 and its self-test, V0' 89, E1-C at the freeze and after the put-back, C on 89 and v5, CU, the cell, range, autosave and P2 arms on v5, the Writer nets re-run (P5, P4, S1, Z, P1, F4 24/24, `ms-formats/gen-89/rerun-01/`), H8 red on 0.2.55 |
| `h8-red-on-0255/` | `H8_RED` on 0.2.55, both browsers, before the install: the ODF controls open; `action-docx`, `action-xlsx`, `read-only-docx`, `read-only-xlsx` red (the row's name does not land in LiteCore); no fatal |
| `package-run-01` | packaged in 149 s |
| `delta`, `offline` | `DELTA_HOLDS` with 7 red cases; `PACKAGE_HOLDS` with 22 |
| `offline-install-preflight`, `live-preflight`, `install` | `OFFLINE_INSTALL_READY`, `LIVE_PREFLIGHT_READY`, `CANDIDATE_INSTALLED`; documents and locks preserved; unauthenticated routes 401 |
| `h8/` | run 01, the tool's witness: `save-as-taken` red because the tool's "taken" file (`w-<b>.odt`) was not the name the dialog offers (`d-<b>.odt`), so the first confirm saved; `save-as-odf-writer` red after it. Tool fixed (the taken file is `d-<b>.odt`) |
| `h8-02/` | Chrome 18/18. Firefox 17/18: `save-as-odf-writer`, the copy lacks `H8SAVEAS` |
| `h8-ff-r1..r3/` | Firefox, the same cell red 3 of 3 more |
| `diag-saveas-01/` | reader witness: read `LiteCore-batch8` instead of its own folder, every token false |
| `diag-saveas-02/`, `diag-taken-01..03/` | H8's order reproduced; the payload shows `H8SAVEA1`: the last two keys of ` H8SAVEAS ` missing, in the copy and in the original saved later, with or without the refusal |
| `diag-typing-01/` | no save anywhere: Firefox still loses the last two keys, 8 of 8 |
| `diag-burst-01/` | both browsers, real keys: 8 back to back whole; 10 lose 2; 14 keep 8; 10 at 150 ms apart whole. Finding 130's input queue (depth 8), not Save As. Finding 130 updated |
| `h8-03-firefox/` | H8 with Firefox typing one key per 150 ms: **`H8_HOLDS` 18/18**. With `h8-02`'s Chrome 18/18, H8 holds on both browsers |
| `files-workflow-01/` | 52/52, both browsers and the read-only user; no owned unlocks, share and user removed, folder 204 |
| `capture-after` | `holds: false` on one field only: `lockRowsEqualInstallAfter`. Host `6def1da` clean, installed 0.2.56, buildId `1b8dda1e`, engine equals the archive, protected documents equal the installer's after-state, owned folder 404, temporary user absent. The lock table has 5 rows more than at the install (none gone): admin token locks, ttl 300, all expired, on files deleted with their folders, created at 02:06:49 (diag-saveas-01), 02:11:48, 02:12:07, 02:13:13 (diag-saveas-02) and 02:49:40 (diag-taken-03). None in the windows of H8's five runs or the Files workflow. Open: whether the diagnostics left a page mid-save or a page path keeps its lock is not established |

Not run for this release (CLAUDE.md, cadence): `host_batch.py`, `host_layout.py`, `host_calc_theme.py`, `host_batch6.py`, and the earlier batches'
red cases in the gate. The owner's hand test covers the layout.

**Found on the way:** the live app directory is the host repo's working copy (the stack mounts `STACK_ROOT` as `/var/www/html`). It had been left
on `host-0.2.56` on 2026-11-03, so the live site served 0.2.56's PHP and JS with 0.2.55's engine under version 0.2.55 (the container's
`EditorController.php` carried `openxmlformats`). Switched back to `main` at 00:20 before H8's red case. Candidates now come from
`host_release.py candidate` (a clone under `build/host-X/`), never from the live working copy.

Rollback: `host_release.py rollback findings/evidence/host-0.2.56` with `host-stack/bin` first on PATH restores 0.2.55's engine bytes (Writer
v32, Calc v4: no DOCX/XLSX), the host label stays 0.2.56.

**Pending:** the owner's hand test (`HANDTEST-2026-11-04-host-0.2.56.md` at the repo root).
