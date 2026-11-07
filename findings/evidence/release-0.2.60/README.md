# Release 0.2.60: ods-editor-v8 frozen, the Calc release regression

The owner named the hand-test slot on 2026-11-07 at about 23:24 ("我現在可以手測了"). The release carries the two Calc features built
on dev that night (`handoff/HANDOFF-2026-11-07-calc-v8-copy-html-zoom.md`): copy writes `text/html` beside `text/plain`
(SPEC-P-calc-copy 9-12) and Calc zoom (SPEC-P-calc-zoom), both on the v8 link. The host release itself is `../host-0.2.60/`.

## Calc: ods-editor-v8 frozen (`calc-v8-freeze/`)

`freeze.sh` copies `build/ods/editor-v8/profile` (wasm `61e2a069`, worker `91d514f1`; `../calc-v8/link/`) to
`dist/profiles/ods-editor-v8`. Three copies are equal file for file: the source, dist, and the read-only archive
`build/archive/ods-editor-v8-dev-61e2a069`. The archive also passes its own SHA256SUMS, and the link's four-file receipt agrees
(`FROZEN_EQUAL`). In the same commit (`5bc2dcf01`), `web/ods-editor-app.js` points at v8, and seven mirror tools learn v8's URL:
`check_calc_sheet_view.py`, `check_calc_style.py`, `check_calc_undo_cu.py`, `run_calc_editor_browser.py`, `check_calc_headers.py`,
`check_calc_structure.py` and `check_calc_sheets.py`. `make ods-editor-assets ods-viewer-assets`, which only copies, put the page,
the two Calc shell files and `viewer-shell/ods-viewer-session.js` into dist.

## Writer: not moved

Shell generation 91 on `e2-editor-v33`, byte for byte 0.2.59's (and 0.2.58's). Nothing under `sdk/` or `editor-shell-v2/`
changed, and the Writer page's graph has none of the five changed served files. Neither V0' nor the Writer nets were re-run
(cadence items 3 and 5). The gate reads `../release-0.2.58/gen-91/`.

`viewer-shell/ods-viewer-session.js` did change: it gained `setScale` for the Calc zoom. The read-only viewer page imports it too.
Its scale stays 1 unless an editor sets it, and the C net (`check_calc_sheet_view.py`) drives the viewer page.

## Units before the chain (`units/`)

The node suite passes 1070/1070 (every `*.test.mjs` outside build/ and dist/, the same 97 files as `../calc-v8/units/`). The three
Calc mutation tools pass.

## The release regression (`chain-0260.sh`, `chain-0260.log`)

Serial, both browsers, on dist v8, tree `5bc2dcf01`, 23:28-23:48 +0800, nothing else building. Every step exits 0, and the gate
(`../host-0.2.60/gate.stdout.txt`) reads each verdict:

| Net | Result |
|---|---|
| C, CU | `all_pass`, `CU_HOLDS` |
| cell, range, autosave, P2 | `all_pass` each |
| Calc headers, structure, sheets P on dist v8 | `P_HOLDS` each |
| Calc copy with `--html` P on dist v8 (new) | `P_HOLDS`, 10/10 per browser (P-C1..P-C5, P-H1..P-H4) |
| Calc zoom P on dist v8 (new) | `P_HOLDS`, 41/41 per browser |

`probe_calc_autosave.py` runs the page on `dist/profiles/ods-editor-v1` with a host double, as it did for v5 to v7. It measures
the page's autosave, not v8.
