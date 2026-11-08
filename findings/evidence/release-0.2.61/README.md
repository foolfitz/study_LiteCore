# Release 0.2.61: the Calc page's zoom anchor, the Calc release regression

The owner chose to release on 2026-11-08 (option A). Only the Calc page moved: `zoomTo` anchors on the active cell's top-left,
else the view's top-left (SPEC-P-calc-zoom append 5; `../calc-zoom-anchor/`). Nothing is frozen: the engine is 0.2.60's
`dist/profiles/ods-editor-v8` (`../release-0.2.60/calc-v8-freeze/`). `make ods-editor-assets`, which only copies, put the page
into dist; the other Calc and viewer shell files were already equal. Writer is byte for byte 0.2.60's (shell generation 91). The
host release itself is `../host-0.2.61/`.

Units were not re-run here: `../calc-zoom-anchor/units/` (node 1070/1070, the three Calc mutation tools pass) ran on these page
bytes, and nothing under `web/`, `spreadsheet-shell/` or `tests/` changed since.

## The release regression (`chain-0261.sh`, `chain-0261.log`)

The 0.2.60 chain with names suffixed -0261. Serial, both browsers, on dist v8, tree `1c406c65f`, 11:51-12:11 +0800, nothing else
building. Every step exits 0, and the gate (`../host-0.2.61/gate.stdout.txt`) reads each verdict:

| Net | Result |
|---|---|
| C, CU | `all_pass`, `CU_HOLDS` |
| cell, range, autosave, P2 | `all_pass` each |
| Calc headers, structure, sheets P on dist v8 | `P_HOLDS` each |
| Calc copy with `--html` P on dist v8 | `P_HOLDS`, 10/10 per browser |
| Calc zoom P on dist v8 (append 5's P-Z5 and P-Z10) | `P_HOLDS`, 51/51 per browser |
