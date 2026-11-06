# Release 0.2.59: ods-editor-v7 frozen, the Calc release regression

The owner named the hand-test slot on 2026-11-06 (option A). The release carries two Calc features built on dev that day
(`handoff/HANDOFF-2026-11-06-calc-copy-and-sheets.md`): Ctrl+C (SPEC-P-calc-copy, on the owner's v7 link) and the sheet work
(SPEC-P-calc-sheets, page only). The host release itself is `../host-0.2.59/`.

## Calc: ods-editor-v7 frozen (`calc-v7-freeze/`)

`freeze.sh` copies `build/ods/editor-v7/profile` (wasm `36d0e1b8`, worker `8b49b46e`; linked 2026-11-06 11:57, `../calc-copy/link/`)
to `dist/profiles/ods-editor-v7`. Three copies are equal file for file: the source, dist, and the read-only archive
`build/archive/ods-editor-v7-dev-36d0e1b8`. The archive also passes its own SHA256SUMS, and the link's four-file receipt agrees
(`FROZEN_EQUAL`). In the same commit (`8f064145e`), `web/ods-editor-app.js` points at v7, and six mirror tools learn v7's URL:
`check_calc_sheet_view.py`, `check_calc_style.py`, `check_calc_undo_cu.py`, `run_calc_editor_browser.py`, `check_calc_headers.py`
and `check_calc_structure.py`. `make ods-editor-assets`, which only copies, put the page and the Calc shell into dist.

## Writer: not moved

Shell generation 91 on `e2-editor-v33`, byte for byte 0.2.58's: nothing under `sdk/`, `editor-shell-v2/`, `viewer-shell/` or the
Writer page changed, and the served delta has no Writer file. Neither V0' nor the Writer nets were re-run (cadence items 3 and 5).
The gate reads `../release-0.2.58/gen-91/`.

## Units before the chain (`units/`)

The node suite passes 1052/1052 (every `*.test.mjs` outside build/ and dist/). The three Calc mutation tools pass.

## The release regression (`chain-0259.sh`, `chain-0259.log`)

Serial, both browsers, on dist v7, tree `8f064145e`, 12:25-12:40 +0800, nothing else building. Every step exits 0, and the gate
(`../host-0.2.59/gate.stdout.txt`) reads each verdict:

| Net | Result |
|---|---|
| C, CU | `all_pass`, `CU_HOLDS` |
| cell, range, autosave, P2 | `all_pass` each |
| Calc headers P on dist v7 | `P_HOLDS` |
| Calc structure P on dist v7 | `P_HOLDS` |
| Calc sheets P on dist v7 (new) | `P_HOLDS`, 9/9 per browser |
| Calc copy P on dist v7 (new) | `P_HOLDS`, 6/6 per browser |

`probe_calc_autosave.py` runs the page on `dist/profiles/ods-editor-v1` with a host double, as it did for v5 and v6. It measures the
page's autosave, not v7.
