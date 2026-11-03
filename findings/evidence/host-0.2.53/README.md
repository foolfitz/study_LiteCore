# Host 0.2.53: Enter over a selection, the empty-copy sentence

Spec `specs/SPEC-P-demo-batch-5.md`. Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. Installed 2026-11-03 13:40 +0800.

- Host `6b1660c`, branch `host-0.2.53`, parent `c657aba` (0.2.52); the only source change is `appinfo/info.xml`. Engine `89860962782b3a21`, archive `build/archive/host-0.2.53-engine-89860962782b3a21` (not in git).
- Writer on `e2-editor-v32`, generation 88. Calc on `ods-editor-v3` and the viewer do not move.
- Delta against 0.2.52: `e2-editor-app.js` alone. No profile moves; 45 files unchanged.

| Read | Result |
|---|---|
| `h5-red-on-0252` | `H5_RED` on both browsers, before the install, on the cells it should be red on: `H5/copy-on-a-caret-says-a-sentence` (the toast prints `CLIPBOARD_EMPTY_SELECTION`), `H5/no-red-toast` (`EDITOR_FORMAT_GESTURE_UNSUPPORTED` on Enter), `H5/enter-replaced-the-word` (Enter refused, `q` replaced the word). No fatal |
| `prepare-release.py --gate-only` (`gate-only.*`) | K 0.2.45, S1, P1, P4 and its three red cases, P5 and its red on generation 87, P2, Calc regression, T6, layout, Z10, C, Z, F3-88 with no cell moved, F4-88, V0', E1-C |
| `prepare-release.py` (`package-run-01.*`) | packaged in 162 s, `release.json` |
| `check-delta.py`, `offline-package-check.py` | `DELTA_HOLDS` with 10 red cases, `PACKAGE_HOLDS` with 22 |
| `install-0.2.53.py` | `CANDIDATE_INSTALLED`, documents and locks preserved |
| `host_batch5.py`, `host-features-02` | `H5_HOLDS`, Chrome 5/5, Firefox 5/5: the caret copy says the sentence, Enter over five selected characters leaves an empty paragraph and `q plain paragraph two`, read back over WebDAV after Save |
| `host_calc_theme.py`, `host-calc-theme` | `T6_HOLDS`, 94 controls |
| Files workflow | 52/52 |
| `host_batch.py`, `host_layout.py` | `HOST_BATCH_HOLDS`, `LAYOUT_HOLDS` |
| `capture-after.py` | `holds: true` |

Read by eye: `host-features-02/chrome-after.png`.

## The first `host-features` run was the tool's red

`host-features` (from `h5.sh`) read `H5_RED` on `H5/no-red-toast` only, both browsers, with `actual: ''`; every other cell held. The page's caret-copy refusal is a `.bad` toast; the tool then cleared the toast with `run_e2_c_product_path.CLEAR_TOAST`, which empties the text and leaves the class; `RED` returns the text of any toast that has `.bad`, so it read the empty string. Enter posted no toast at all (an empty text can only come from the clear: every `toast()` call writes a message). `host_batch5.py` now clears with its own `CLEAR`, which also drops `.bad` and `.error` (docstring). The red on 0.2.52 is untouched by this: there Enter itself posts a `.bad` toast after the clear. `host-features-02` is the run on the fixed tool, logged in `h5-log.txt`; `host-features` is kept.

Section 34.4: fixed-by-execution +1.

**Pending:** the owner's hand test, on 0.2.54 (handoff). Rollback: `rollback-package.sh` with `host-stack/bin` first on PATH restores 0.2.52's engine bytes.
