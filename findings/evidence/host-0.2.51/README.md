# Host 0.2.51: alignment on both apps, Calc text colour and cell fill

Spec `specs/SPEC-P-demo-batch-3.md` sections 3, 8, 9. Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45, which carries finding 179. Installed 2026-11-03 00:19 +0800.

- Host `1b8c667`, branch `host-0.2.51`, parent `350cc4c` (0.2.50); the only source change is `appinfo/info.xml`. Engine `60fd728f61134b05`, archive `build/archive/host-0.2.51-engine-60fd728f61134b05` (not in git).
- Writer on `e2-editor-v31` (wasm `809893a9`), generation 86. Calc on `ods-editor-v3` (wasm `e6593b2c`). Viewer unchanged.
- Delta against 0.2.50: the nine page and shell files; both profiles move with every file new, the two Calc packs the same bytes under the new path.

| Read | Result |
|---|---|
| `prepare-release.py` gate | K 0.2.45, S1, P1, P2, their red cases, Calc regression, C, Z, F3-86, F4-86, V0', E1-C |
| `check-delta.py`, `offline-package-check.py` | `DELTA_HOLDS` with 11 red cases, `PACKAGE_HOLDS` with 22 |
| `install-0.2.51.py` | `CANDIDATE_INSTALLED`, documents and locks preserved |
| `host_batch3.py`, `host-features-02` | `P3_FEATURES_HOLD`, 23/23, Chrome and Firefox; the file read back over WebDAV holds the alignment, the colour and the fill, Calc opened again keeps them |
| `p3-red-on-0250` | `P3_FEATURES_RED`, on 0.2.50 before the install: the buttons are hidden there |
| `host_calc_theme.py`, `host-calc-theme-02` | `T6_HOLDS`, 94 controls with the palette open, 70 of them swatches |
| Files workflow | 52/52 |
| `host_batch.py`, `host_layout.py` | `HOST_BATCH_HOLDS`, `LAYOUT_HOLDS` |
| `capture-after.py` | `holds: true`, every clause |

`host-features/` and `host-calc-theme/` are the tools' own failures, kept. The first called a helper that lives in another module, so the page was never left, the lock stayed, and the next upload met 423. The second compared a swatch's `color`, which nothing paints.

**Pending:** the owner's hand test. Rollback: `rollback-package.sh` with `host-stack/bin` first on PATH restores 0.2.50's engine bytes.
