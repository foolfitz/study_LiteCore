# Host 0.2.50: Shift+Up/Down/Home/End on e2-editor-v30

Spec `specs/SPEC-P-demo-batch-3.md` section 2, finding 179. Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45, which carries the defect. Installed 2026-11-02 18:33 +0800.

- Host `350cc4c`, branch `host-0.2.50`, parent `7782714` (0.2.49); the only source change is `appinfo/info.xml`. Engine `7e3edb640c50d628`, archive `build/archive/host-0.2.50-engine-7e3edb640c50d628` (not in git).
- Delta against 0.2.49: `e2-editor-app.js`, and the four files of `profiles/e2-editor-v29` moving to `profiles/e2-editor-v30`, wasm and loader byte for byte. Generation 85.

| Read | Result |
|---|---|
| `prepare-release.py` gate | K 0.2.45, S1 red and green, C, Z, F3-85, F4-85, V0', E1-C |
| `check-delta.py`, `offline-package-check.py` | `DELTA_HOLDS` with nine red cases, `PACKAGE_HOLDS` |
| `install-0.2.50.py` | `CANDIDATE_INSTALLED`, documents and locks preserved |
| Files workflow | 52/52 |
| `host_batch.py`, `host_layout.py` | `HOST_BATCH_HOLDS`, `LAYOUT_HOLDS` |
| `capture-after.py` | `holds: true`, every clause |
| `demo-batch-3/host_shift.py`, `host-shift-03` | `HOST_SHIFT_HOLDS` |

`host-shift-03`: Chrome read `move-line-*` with `extend: true`, `ok: true` and a selection from the engine, through an observer on the Worker. Firefox can only be read for the absence of the refusal; its selection is S1's on the mirror. Calc autosave fired 30.5 s after a committed cell, trigger `auto`, status `自動儲存已開啟`.

`host-shift-01` and `-02` are the tool's own failures, kept: 01 read `selectionShape`, which only the pointer paths write; 02 clicked the page-number strip, so no key reached the page and the "no refusal" cells were empty greens.

**Pending:** the owner's hand test. Rollback: `rollback-package.sh` with `host-stack/bin` first on PATH restores 0.2.49's engine bytes.
