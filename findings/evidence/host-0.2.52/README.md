# Host 0.2.52: the heading menu, list toggles, findings 180, 181, 182

Spec `specs/SPEC-P-demo-batch-4.md` sections 5 to 8. Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45, which carries findings 179 to 182. Installed 2026-11-03 09:27 +0800.

- Host `c657aba`, branch `host-0.2.52`, parent `1b8c667` (0.2.51); the only source change is `appinfo/info.xml`. Engine `21985315bc752e57`, archive `build/archive/host-0.2.52-engine-21985315bc752e57` (not in git).
- Writer on `e2-editor-v32` (wasm `54e50093`), generation 87 (`97c3da29`). Calc on `ods-editor-v3` and the viewer do not move.
- Delta against 0.2.51: the five Writer page and shell files, and the profile's four files. 37 files unchanged.

| Read | Result |
|---|---|
| `h4-red-on-0251` | `H4_RED` on both browsers on `H4/controls-shown`, before the install: the menu is hidden there |
| `prepare-release.py` gate | K 0.2.45, S1, P1, P2, P4 and its three red cases, Calc regression, C, Z, F3-87 with no cell moved, F4-87, V0', E1-C |
| `check-delta.py`, `offline-package-check.py` | `DELTA_HOLDS` with 10 red cases, `PACKAGE_HOLDS` with 22 |
| `install-0.2.52.py` | `CANDIDATE_INSTALLED`, documents and locks preserved |
| `host_batch4.py`, `host-features` | `H4_HOLDS`, Chrome 17/17, Firefox 14/14: open from Files, real keys and pointer, Save, the file read back over WebDAV holds the level, the q where the caret was, both toggles, findings 181 and 182; opened again, the menu names the level. T6 on the menu: every control the same under both themes, contrast above 4.5 |
| `host_calc_theme.py`, `host-calc-theme` | `T6_HOLDS`, 94 controls |
| Files workflow | 52/52 |
| `host_batch.py`, `host_layout.py` | `HOST_BATCH_HOLDS`, `LAYOUT_HOLDS` |
| `capture-after.py` | `holds: true` |

Read by eye: `host-features/chrome-menu.png`, `theme-dark.png`, `firefox-reopened.png`. The menu sits over the page, nothing covers it.

**Pending:** the owner's hand test, the list in `handoff/RUNBOOK-relink-v32.md`. Rollback: `rollback-package.sh` with `host-stack/bin` first on PATH restores 0.2.51's engine bytes.
