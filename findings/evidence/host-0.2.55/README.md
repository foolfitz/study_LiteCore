# Host 0.2.55: Calc document undo

Spec `specs/SPEC-P-calc-undo.md`. Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. Installed 2026-11-03 18:25 +0800.

- Host `5db53ac`, branch `host-0.2.55`, parent `8c95b50` (0.2.54); the only source change is `appinfo/info.xml`. Engine `1d2608fca2f8509c`, archive `build/archive/host-0.2.55-engine-1d2608fca2f8509c` (not in git).
- Calc on `ods-editor-v4` (wasm `9f37ed5a`, frozen 2026-11-03, `findings/evidence/calc-undo/after-freeze/`). Writer on `e2-editor-v32`, generation 88, and the viewer do not move.
- Served delta against 0.2.54 (measured with the packager's closure before the tools were derived): the Calc page's four files changed (`ods-editor-app.js`, `ods-editor.html`, `spreadsheet-shell/calc-document-sdk.js`, `spreadsheet-shell/calc-editor-session.js`), `profiles/ods-editor-v4/` added and `profiles/ods-editor-v3/` removed (six files each); 36 unchanged.
- Release tools derived from 0.2.54's by `derive_host_0255.py`; the Calc checks are 0.2.51's form (the page's profile, wasm and module must be v4's).

| Read | Result |
|---|---|
| `h7-red-on-0254` | `H7_RED` on both browsers on 0.2.54, before the install: no undo button; `H7VALUE` written to D9 and still there after Ctrl+Z; A1 bold and still bold. No fatal |
| `prepare-release.py --gate-only` (`gate-only.*`) | 41 gates: 0.2.54's, plus CU on the frozen v4 and its red on v3, the field-guard mutation, C on v4, the cell, range, autosave and P2 arms on v4, NU-3, the pre-link syntax and export checks, the v4 manifest's capability bits 1046835 |
| `prepare-release.py` (`package-run-01.*`) | packaged in 149 s |
| `check-delta.py`, `offline-package-check.py` | `DELTA_HOLDS` with 11 red cases (new: `fewer`, `calc_still_v3`), `PACKAGE_HOLDS` with 22 |
| `install-0.2.55.py` | `CANDIDATE_INSTALLED`, documents and locks preserved |
| `host_batch7.py`, `host-features` | `H7_HOLDS`, Chrome 12/12, Firefox 12/12: an .ods opened from Files offers 復原 and 重做; D9 written, saved, Ctrl+Z, saved, read back over WebDAV: restored; Ctrl+Y: back; Ctrl+B on A1, the undo button: the file's A1 is not bold; no red toast, ready |
| `host_batch6.py`, `batch6-new-spreadsheet` | `H6_HOLDS` (New spreadsheet, upload-and-open, New document) |
| `host_calc_theme.py`, `host-calc-theme` | `T6_HOLDS`, 96 controls (94 + the two new buttons) |
| Files workflow | 52/52 |
| `host_batch.py`, `host_layout.py` | `HOST_BATCH_HOLDS`, `LAYOUT_HOLDS` |
| `capture-after.py` | `holds: true` |

Read by eye: `host-features/firefox-after.png` (the two icons after Save; A1 not bold after the button; D is the fixture's hidden column).

Fixed by execution while deriving: the gate read batch 6's static criteria from this folder instead of `host-0.2.54/static`; the Calc arm reports were read through a top-level `pass` they do not have (their `runs[].checks` are lists, read with `all_pass` as 0.2.51 did); the export-body check's output had been written under `wasm_sdk_probe/findings/` (a relative path from `tools/`) and was moved to `findings/evidence/calc-undo/pre-link-ships/`.

**Pending:** the owner's hand test. Rollback: `rollback-package.sh` with `host-stack/bin` first on PATH restores 0.2.54's engine bytes (Calc back on v3, no undo).
