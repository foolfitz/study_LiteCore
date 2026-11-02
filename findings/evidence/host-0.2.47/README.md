# Host 0.2.47: the toolbar zoom and each sheet's own view

Spec `specs/SPEC-P-demo-batch-1.md`. Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. Installed 2026-11-02 13:51 +0800.

- Host `d6cbbd9`, branch `host-0.2.47`, parent `b9d33d7` (0.2.46); the only source change is `appinfo/info.xml`. Engine `268e3009dbf33a5a`, archive `build/archive/host-0.2.47-engine-268e3009dbf33a5a` (not in git).
- Writer on `e2-editor-v29`, shell generation 84 (digest `3998f606`), page `c377b9f2`, HTML `6800b2d5`. No engine changed.
- Delta against 0.2.46: `e2-editor.html` alone. Against 0.2.45 it is the same five page files as 0.2.46.

| Read | Result |
|---|---|
| `prepare-release.py` gate | K 0.2.45 `K_HOLDS`, the Z10 red on 0.2.46, C, Z and four mutations, F3-84, F4-84, V0', E1-C, all on the final HTML |
| `check-delta.py` | `DELTA_HOLDS`, six red cases |
| `offline-package-check.py` | `PACKAGE_HOLDS`, 22 red cases |
| `install-0.2.47.py` | `CANDIDATE_INSTALLED`, documents and locks preserved |
| Files workflow | 52/52, `ok: true`, cleanup clean |
| `capture-after.py` | `holds: true` |
| `host_batch.py`, Chrome 780 px, Firefox 1366 px | `HOST_BATCH_HOLDS`, 11/11 each: Z9, Z10, C1 to C3 on the editor page |

The host batch reads C1 to C3 on `ods-editor.html` only. The viewer arm of C ran on the mirror (`../demo-batch-1/calc-sheet-view/green-01`); it was not driven on the host.

Screens read by eye: `host-batch/chrome-writer-rest.png` (controls in the toolbar, no side scrollbar), `host-batch/firefox-calc-back-to-sheet1.png` (表一, P159, row 148 on).

**Owner's hand test, 2026-11-02:** the Writer zoom and the Calc tab steps from the handoff, answered 「測試皆通過」. 0.2.47 stays installed as the daily uncounted candidate; the nominal shipped host stays 0.2.45. Rollback: `rollback-package.sh` with `host-stack/bin` first on PATH restores 0.2.46's engine bytes, which carry the regression above; to go further back use 0.2.45's archive.
