# Calc zoom anchor: the active cell's top-left, else the view's top-left (SPEC-P-calc-zoom append 5)

The owner's hand test of 0.2.60 (`../host-0.2.60/handtest-2026-11-07/`) asked for one change. Zooming kept the view's centre, and
the centre is empty when the data fills only the top rows. The owner chose C: anchor on the active cell's top-left corner while it
is in view (as Collabora does), otherwise on the view's top-left corner (as desktop LibreOffice Calc does, not Collabora's fallback
to the selection's centre and then the view's centre). The criteria were committed before any run of the new page (`2a5abb1a3`).

Page only, no link: `web/ods-editor-app.js` `zoomAnchor()` and `zoomTo()`. The code comment names the difference from Collabora in
English, as the owner asked. The engine is the frozen `dist/profiles/ods-editor-v8` (wasm `61e2a069`).

| Run | Result |
|---|---|
| `units/` | node 1070/1070 (the same 97 files); the three Calc mutation tools pass |
| `p-anchor-01` (Chrome 156, Firefox 157) | `P_HOLDS`, 51/51 per browser: P-Z1..P-Z4, P-Z6..P-Z9 as before, P-Z5 on every press of P-Z1 (fresh document, A1, scroll 0,0: the owner's case) and of the walk, P-Z10 on - and + with F100 below the view |
| `p-anchor-red-centre-anchor` (Chrome) | `MUTATION_RED`: 0.2.60's centre anchor turns P-Z5 red on every zoom-in from the fresh document (`home-in-*`), on the back-to-100 press and on every press of the walk. The zoom-outs from scroll 0,0 stay green: the scroll is clamped at 0, which the criterion allows. P-Z10 `out-150` is red too |
| `p-anchor-red-fallback-centre` (Chrome) | `MUTATION_RED`: Collabora's fallback to the view's centre turns only P-Z10 red (`out-150`, `in-200`); P-Z5 stays green. So the check tells C from Collabora's behaviour |

`chain-anchor.log` records `dirty 2` at start: the page and the P tool were uncommitted while they ran. They are committed with
this folder, unchanged. `p-anchor-01/report.json` records the mirror's page as `7f25906e...`, which is `web/ods-editor-app.js` with
the tool's own engine-URL replacement (`./profiles/ods-editor-v8/` -> `under-test`). Recomputed after the run, it is equal. The
other four page files and the tool (`797410eb...`) are equal as well.

Not released: release waits for a hand-test slot the owner names (CLAUDE.md, cadence 1). Item 7 of the 0.2.60 hand-test script
("中央不跑掉") describes the old behaviour, so the next script replaces it.
