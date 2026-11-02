# Host 0.2.49: the whole Calc page stays light under any theme

Spec `specs/SPEC-P-demo-batch-2.md` append 2. Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. Installed 2026-11-02 15:47 +0800.

- Host `7782714`, branch `host-0.2.49`, parent `0411329` (0.2.48); the only source change is `appinfo/info.xml`. Engine `dd6159b571d9b966`, archive `build/archive/host-0.2.49-engine-dd6159b571d9b966` (not in git).
- Delta against 0.2.48: `ods-editor.html` alone. Writer did not change, so Z, F3, F4 and V0' were not repeated.

| Read | Result |
|---|---|
| `check-delta.py`, `offline-package-check.py` | `DELTA_HOLDS`, `PACKAGE_HOLDS` |
| `install-0.2.49.py` | `CANDIDATE_INSTALLED` |
| Mirror C (`demo-batch-2/calc-sheet-view/run-02`) | Editor 14/14, viewer 11/11, both browsers |
| Files workflow | 52/52 |
| `host_batch.py` | `HOST_BATCH_HOLDS` |
| `host_layout.py` | `LAYOUT_HOLDS` |
| `host_calc_theme.py` (`calc-theme/`) | `T6_HOLDS`: 15 controls equal under light and dark, none below 4.5, red on 0.2.48 (`demo-batch-2/t6-red-on-0248`) |
| `capture-after.py` | `holds: false` on the lock table only |

`capture-after.py`: same shape as 0.2.48, L-capture-after-live-lock-refreshed. The rows are equal once `ttl` is left out; file 29431, the owner's open `.ods`, moved. Documents, engine and tree hold.

The faded `I` was a colour, not an opacity: Nextcloud colours `<em>`, contrast 2.85 in the dark theme.

**Pending:** the owner's hand test.
