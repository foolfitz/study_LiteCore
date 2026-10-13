## SUMMARY

Run `run-20261013T095104Z` (UTC 09:51-10:26): native LibreOffice 26.8 (LOK, `SAL_USE_VCLPLUGIN=svp`), 3 rounds as 3 separate processes run one after the other under `nice -n 10`, every arm a fresh document load. Per round 120 measured arms: 3 controls, 84 Shift+key (14 shapes x 6 keys), 24 plain key on a range (4 range shapes x 6 keys), 9 interaction arms. Window = 1500 ms after the KEYINPUT post; shapes settled for 800 ms of quiet first.

- Window control: 0 callbacks in the 1500 ms window and 0 in the 500 ms before the post, for all 3 controls (`caret-mid`, `range-fwd`, `range-kbd`, no key) in 3/3 rounds. No settle change was needed. Every measured arm's pre-key selection text and cursor rectangle matched the discovered expectation; Shift+Home/End from the caret shapes selected the expected text; the settle cap was never hit.
- INTERMITTENT: none. For all 111 cells the callback type sequence (all types, and SEL/CUR/SS/SE only) is identical in the 3 rounds.
- P-a HELD: the selection text changed in 74 of the 84 Shift cells; each of those emitted exactly 1 TEXT_SELECTION (74/74, 3/3). No cell changed the selection without one.
- P-b HELD: Shift+Left@doc-start, Shift+Right@doc-end, Shift+Up@doc-start, Shift+Down@doc-end emit no callback of ANY type in 3/3 rounds (selection text and cursor rectangle unchanged). Same for Shift+Home@doc-start and Shift+End@doc-end.
- P-c HELD: Shift+Left@range-one = `SEL0 CUR`: the TEXT_SELECTION payload is the empty string "" (not the word EMPTY), 3/3; `getTextSelection` 'B' -> ''.
- P-d HELD: 9 interaction arms x 3 rounds = 27/27 pass. After Shift+Right, Shift+Down or Shift+End: (a) product click at P3 -> selection '' , cursor rectangle = the click's, Shift+Home reads 'P3 plain p'; (b) product drag over ALPHA -> 'ALPHA'; (c) setTextSelection RESET+START+END over DELTA -> 'DELTA'.
- ORDER: in ALL 98 cells that have both callbacks (74 Shift + 24 plain-on-range), 3/3 rounds, the last INVALIDATE_VISIBLE_CURSOR comes AFTER the last TEXT_SELECTION. No cell has it before. SS/SE (TEXT_SELECTION_START/END), when present, come before TEXT_SELECTION.
- Sequences (SEL0 = TEXT_SELECTION with empty payload): `SS SE SEL CUR` in 71 cells; `SEL CUR` (no SS/SE) in 2 cells, `shift-Right@cell-end` and `shift-Down@cell-end` (selection leaves the cell); `SEL0 CUR` in 25 cells = all 24 plain keys on the 4 range shapes + `shift-Left@range-one`; no callback in 10 cells.
- More than one TEXT_SELECTION: no cell (every cell has 0 or 1; same for CUR).
- NO callback of any type (10 Shift cells, all with the selection unchanged, 3/3): shift-Left@doc-start, shift-Up@doc-start, shift-Home@doc-start, shift-Right@doc-end, shift-Down@doc-end, shift-End@doc-end, shift-Home@empty-para, shift-End@empty-para, shift-End@wrap-line-end, shift-End@cell-end.
- Plain key on a range (item 3): all 24 cells = `SEL0 CUR`; the selection text goes to '' in all 24.
- Timing: first callback 0.35-1.10 ms after the KEYINPUT post (the two post calls return in 0.0-0.7 ms, median 0.015 ms, i.e. the callbacks arrive after the post returned); the last SEL/CUR/SS/SE is at <= 1.10 ms in every cell; none later than 300 ms. Later callbacks are other types only: STATE_CHANGED at ~300-330 ms (most cells), up to 767 ms in 4 cells together with CONTEXT_CHANGED and RULER_UPDATE (shift-Down@heading-mid, shift-Down@list-mid, shift-Up@list-mid, shift-Up@doc-end), 622 ms in 3 `range-kbd` cells.
- Source trees: `native-lok-26-8/src` and `libreoffice-26-8` are at the SAME commit `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`. `native-lok-26-8/src` is clean; `libreoffice-26-8` has 6 tracked modified files (configure.ac, two emscripten/gbuild .mk files, the emscripten exports .mk, the fs-image .mk, vcl/qt5/QtFrame.cxx; none under sw/, sfx2/ or desktop/source/lib). The native install `libmergedlo.so` is dated 2026-08-03.
- Commit: see `git log -- findings/evidence/link-batch/extend-signatures` (this README is committed together with the tool, runner, analyser, fixture and the run).

## Predictions, as written before the run

- P-a: every Shift+key that changes the selection emits >= 1 `TEXT_SELECTION`. -> held.
- P-b: Shift+Left at `doc-start`, Shift+Right at `doc-end`, Shift+Up on the first line and Shift+Down on the last line emit nothing (the 096 shape). -> held.
- P-c: Shift+Left on `range-one` emits `TEXT_SELECTION` with an EMPTY payload (it collapses). -> held.
- P-d: interaction arms (a)-(c) all pass. -> held.
- No prediction about order (question 3).

## How this was measured

- Tool: `wasm_sdk_probe/tools/link_native_extend_signatures.cpp` (as run: `run-20261013T095104Z/tool-source-as-run.cpp`), runner `wasm_sdk_probe/tools/run_link_native_extend_signatures.sh`, fixture `wasm_sdk_probe/test-docs/link-batch/extend-signatures.fodt` (generator `gen_extend_signatures.py`; the runner refuses to run if the fixture's paragraphs differ from the tool's `--paragraphs`). Hashes of all inputs: `inputs.sha256`.
- Shapes are made the way the product makes them. A caret = one click (`postMouseEvent` DOWN+UP, count 1, button 1). A range = a mouse drag (DOWN at A, MOVE to B, UP at B). `range-kbd` = click at `caret-mid` then Shift+Right x3. `wrap-line-end` = click at the paragraph start, then End. The points are NOT hard-coded: each process first walks the fixture with keys (Ctrl+Down to the paragraph, Right/End to each offset) and stores the `INVALIDATE_VISIBLE_CURSOR` rectangle; the click point is (rect.x, rect.y + rect.h/2). The discovery rows (`discover-*` lines in `arms-r*.jsonl`) carry the rectangles and the text that Shift+Home / Shift+End select at the last position of each walk.
- Offsets in the P2 paragraph `P2 ALPHA BETA GAMMA DELTA`: `caret-mid` = 11 (inside BETA), `range-fwd`/`range-bwd` = 9..19 (`BETA GAMMA`), `range-one` = 9..10 (`B`), `range-kbd` = 11..14 (`TA `), `range-cross` = P2 offset 11 to P3 offset 10. The wrapped paragraph has at least 3 displayed lines (line starts at cursor y 2522, 2798, 3074; Shift+End at the start of line 3 selects up to `...longer before`, so the tail `it finally stops here` is on a 4th line), the table is 2x2, the heading is a `text:h` outline level 1, the list item has a bullet.
- Per arm the raw record has: every callback (numeric type, name, payload <= 400 bytes, tMs since the KEYINPUT post; callbacks up to 500 ms before the post have negative tMs), and before / after the window `getTextSelection`, the last TEXT_SELECTION / INVALIDATE_VISIBLE_CURSOR / TEXT_SELECTION_START / TEXT_SELECTION_END payloads.
- Callback order is the order the callback function was entered (one list under a mutex); the tMs of consecutive callbacks differ by < 1 ms, so the order, not the time stamp, is what the tables use.
- Analyser: `wasm_sdk_probe/tools/analyze_link_native_extend.py` reads only `arms-r*.jsonl`; command in `run-20261013T095104Z/analysis-command.txt`. It exits non-zero on zero rounds, on a round with zero measured arms, on a round missing arms another round has, and on a probe `fatal` line. It was made red before the run was trusted, on copies of round 1 in a scratch directory: empty directory (exit 2), a round holding only discovery rows (exit 2), a TEXT_SELECTION removed from `shift-Right@caret-mid` (P-a FAILED), a TEXT_SELECTION injected into `shift-Left@doc-start` (P-b FAILED), a non-empty payload in `shift-Left@range-one` (P-c FAILED), a wrong `afterStep` text in `inter-Shift+End-b` (P-d FAILED), a second TEXT_SELECTION in `shift-Home@caret-mid` (listed under "more than one SEL"), and a swapped CUR/SEL order in one round of `shift-Down@list-mid` (listed as INTERMITTENT).
- Limits: native build, VCL plugin `svp`, Writer only (no Calc/Impress), one fixture, default page style. The callbacks here arrive on the core's thread after the post call has returned; how the WASM engine's own loop interleaves them with its pending-operation logic is not measured here. `libreoffice-26-8` is the WASM core's source tree; the WASM build itself was not run in this step.

## Tables (verbatim from `run-20261013T095104Z/tables.md`)

Rounds: 3 (arms-r1.jsonl, arms-r2.jsonl, arms-r3.jsonl).  Window: 1500 ms after the key's KEYINPUT post.
Abbreviations: SEL=TEXT_SELECTION (SEL0 = empty payload), CUR=INVALIDATE_VISIBLE_CURSOR, SS/SE=TEXT_SELECTION_START/END, STATE=STATE_CHANGED, TILES=INVALIDATE_TILES.
`seq` = SEL/CUR/SS/SE callbacks in arrival order; `others` = counts of the other types in the window.
`order` = whether the LAST CUR comes after the LAST SEL.  `last ms` = last SEL/CUR/SS/SE callback / last callback of any type.
Per-round values are joined with `/` when they differ.

## Table 1. Shift+key on every shape

| shape | key | seq | #SEL | #CUR | order | last ms (core / any) | selection changed | others |
|---|---|---|---|---|---|---|---|---|
| caret-mid | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323 | text | STATEx3 |
| caret-mid | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/323 | text | STATEx3 |
| caret-mid | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 324/323/322 | text | STATEx3 |
| caret-mid | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322 | text | STATEx3 |
| caret-mid | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| caret-mid | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| range-fwd | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0 / 322 | text | STATEx1 |
| range-fwd | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 322/323/322 | text | STATEx1 |
| range-fwd | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx1 |
| range-fwd | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx1 |
| range-fwd | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx1 |
| range-fwd | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 321/323/323 | text | STATEx1 |
| range-bwd | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/0/1 / 322/322/323 | text | STATEx1 |
| range-bwd | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 0/1/1 | text | - |
| range-bwd | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/322/323 | text | STATEx1 |
| range-bwd | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 323/323/322 | text | STATEx1 |
| range-bwd | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx1 |
| range-bwd | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 322/321/322 | text | STATEx1 |
| range-one | Left | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 0 / 323/323/322 | text | STATEx3 |
| range-one | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 1 | text | - |
| range-one | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx1 |
| range-one | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx1 |
| range-one | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 322/323/322 | text | STATEx1 |
| range-one | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 322 | text | STATEx1 |
| range-cross | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 1 | text | - |
| range-cross | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 0/1/1 | text | - |
| range-cross | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx1 |
| range-cross | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/0 / 322 | text | STATEx1 |
| range-cross | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx1 |
| range-cross | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 322/321/322 | text | STATEx1 |
| range-kbd | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0 / 622 | text | STATEx1 |
| range-kbd | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0 / 0 | text | - |
| range-kbd | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/1/0 / 322/323/322 | text | STATEx1 |
| range-kbd | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 322 | text | STATEx1 |
| range-kbd | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0 / 623 | text | STATEx1 |
| range-kbd | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 0/0/1 / 622/623/623 | text | STATEx1 |
| doc-start | Left | `-` | 0 | 0 | n/a | - / - | none | - |
| doc-start | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx3 |
| doc-start | Up | `-` | 0 | 0 | n/a | - / - | none | - |
| doc-start | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| doc-start | Home | `-` | 0 | 0 | n/a | - / - | none | - |
| doc-start | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/322/321 | text | STATEx3 |
| doc-end | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322 | text | STATEx3 |
| doc-end | Right | `-` | 0 | 0 | n/a | - / - | none | - |
| doc-end | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 765/766/764 | text | CONTEXT_CHANGEDx1,RULER_UPDATEx1,STATEx5 |
| doc-end | Down | `-` | 0 | 0 | n/a | - / - | none | - |
| doc-end | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| doc-end | End | `-` | 0 | 0 | n/a | - / - | none | - |
| empty-para | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/302 | text | STATEx2 |
| empty-para | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 302 | text | STATEx2 |
| empty-para | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx3 |
| empty-para | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/301 | text | STATEx2 |
| empty-para | Home | `-` | 0 | 0 | n/a | - / - | none | - |
| empty-para | End | `-` | 0 | 0 | n/a | - / - | none | - |
| wrap-line-end | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| wrap-line-end | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 323/322/321 | text | STATEx3 |
| wrap-line-end | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| wrap-line-end | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| wrap-line-end | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| wrap-line-end | End | `-` | 0 | 0 | n/a | - / - | none | - |
| cjk-mid | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| cjk-mid | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 323/323/322 | text | STATEx3 |
| cjk-mid | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/321 | text | STATEx7 |
| cjk-mid | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 324/323/322 | text | STATEx9 |
| cjk-mid | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| cjk-mid | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| heading-mid | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| heading-mid | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| heading-mid | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx12 |
| heading-mid | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 766/765/762 | text | CONTEXT_CHANGEDx1,RULER_UPDATEx1,STATEx7 |
| heading-mid | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx3 |
| heading-mid | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/321 | text | STATEx3 |
| list-mid | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 323/322/322 | text | STATEx3 |
| list-mid | Right | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/322 | text | STATEx3 |
| list-mid | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 767/766/763 | text | CONTEXT_CHANGEDx1,RULER_UPDATEx1,STATEx7 |
| list-mid | Down | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 765/766/764 | text | CONTEXT_CHANGEDx1,RULER_UPDATEx1,STATEx6 |
| list-mid | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 322/323/322 | text | STATEx3 |
| list-mid | End | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/322/321 | text | STATEx3 |
| cell-end | Left | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| cell-end | Right | `SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 404/404/403 | text | STATEx10 |
| cell-end | Up | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 323/323/322 | text | STATEx3 |
| cell-end | Down | `SEL CUR` | 1 | 1 | CUR-after-SEL | 1 / 404/404/401 | text | STATEx10 |
| cell-end | Home | `SS SE SEL CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 321/323/322 | text | STATEx3 |
| cell-end | End | `-` | 0 | 0 | n/a | - / - | none | - |

## Table 2. Plain key on a range (item 3)

| shape | key | seq | #SEL | #CUR | order | last ms (core / any) | selection changed | others |
|---|---|---|---|---|---|---|---|---|
| range-fwd | Left | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 301 | text | STATEx3 |
| range-fwd | Right | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/301/301 | text | STATEx3 |
| range-fwd | Up | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/301/301 | text | STATEx3 |
| range-fwd | Down | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 301 | text | STATEx3 |
| range-fwd | Home | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/0 / 302/302/301 | text | STATEx3 |
| range-fwd | End | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/301/301 | text | STATEx3 |
| range-bwd | Left | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/301 | text | STATEx3 |
| range-bwd | Right | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301 | text | STATEx3 |
| range-bwd | Up | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 301/302/301 | text | STATEx3 |
| range-bwd | Down | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/301 | text | STATEx3 |
| range-bwd | Home | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/301 | text | STATEx3 |
| range-bwd | End | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/302/301 | text | STATEx3 |
| range-cross | Left | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 302/301/301 | text | STATEx3 |
| range-cross | Right | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/302/301 | text | STATEx3 |
| range-cross | Up | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/302/301 | text | STATEx3 |
| range-cross | Down | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301/302/301 | text | STATEx3 |
| range-cross | Home | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 301/302/301 | text | STATEx3 |
| range-cross | End | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 300/301/300 | text | STATEx3 |
| range-kbd | Left | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/0 / 302/301/301 | text | STATEx3 |
| range-kbd | Right | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 301 | text | STATEx3 |
| range-kbd | Up | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/1/0 / 301/302/301 | text | STATEx3 |
| range-kbd | Down | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1/0/1 / 301 | text | STATEx3 |
| range-kbd | Home | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 1 / 302/302/301 | text | STATEx3 |
| range-kbd | End | `SEL0 CUR` | 1 | 1 | CUR-after-SEL | 0/1/1 / 301 | text | STATEx3 |

## Table 3. Window control (no key)

| arm | callbacks in the 1500 ms window per round | callbacks in the 500 ms before the post | shape settle ms per round |
|---|---|---|---|
| control-caret-mid | [0, 0, 0] | [0, 0, 0] | [809, 809, 810] |
| control-range-fwd | [0, 0, 0] | [0, 0, 0] | [1263, 1263, 1261] |
| control-range-kbd | [0, 0, 0] | [0, 0, 0] | [810, 809, 810] |

## Table 4. Interaction arms (question 7)

| arm | round | pass | selection after the first key | selection after the step | cursor after the step | expected |
|---|---|---|---|---|---|---|
| inter-Shift+Down-a | r1 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Down-a | r2 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Down-a | r3 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Down-b | r1 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Down-b | r2 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Down-b | r3 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Down-c | r1 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+Down-c | r2 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+Down-c | r3 | PASS | 'TA GAMMA DELTA\nP3 plain paragr' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+End-a | r1 | PASS | 'TA GAMMA DELTA' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+End-a | r2 | PASS | 'TA GAMMA DELTA' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+End-a | r3 | PASS | 'TA GAMMA DELTA' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+End-b | r1 | PASS | 'TA GAMMA DELTA' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+End-b | r2 | PASS | 'TA GAMMA DELTA' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+End-b | r3 | PASS | 'TA GAMMA DELTA' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+End-c | r1 | PASS | 'TA GAMMA DELTA' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+End-c | r2 | PASS | 'TA GAMMA DELTA' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+End-c | r3 | PASS | 'TA GAMMA DELTA' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+Right-a | r1 | PASS | 'T' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Right-a | r2 | PASS | 'T' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Right-a | r3 | PASS | 'T' | '' | 2391, 1970, 0, 276 | '', cursor 2391, 1970, 0, 276, Shift+Home text 'P3 plain p' |
| inter-Shift+Right-b | r1 | PASS | 'T' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Right-b | r2 | PASS | 'T' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Right-b | r3 | PASS | 'T' | 'ALPHA' | 2505, 1694, 0, 276 | 'ALPHA' |
| inter-Shift+Right-c | r1 | PASS | 'T' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+Right-c | r2 | PASS | 'T' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |
| inter-Shift+Right-c | r3 | PASS | 'T' | 'DELTA' | 4957, 1694, 0, 276 | 'DELTA' |

## Table 5. Findings lists (cells; `rN` = rounds in which it held)

- **last CUR comes AFTER the last SEL** (98): plain-Down@range-bwd [r1,2,3]; plain-Down@range-cross [r1,2,3]; plain-Down@range-fwd [r1,2,3]; plain-Down@range-kbd [r1,2,3]; plain-End@range-bwd [r1,2,3]; plain-End@range-cross [r1,2,3]; plain-End@range-fwd [r1,2,3]; plain-End@range-kbd [r1,2,3]; plain-Home@range-bwd [r1,2,3]; plain-Home@range-cross [r1,2,3]; plain-Home@range-fwd [r1,2,3]; plain-Home@range-kbd [r1,2,3]; plain-Left@range-bwd [r1,2,3]; plain-Left@range-cross [r1,2,3]; plain-Left@range-fwd [r1,2,3]; plain-Left@range-kbd [r1,2,3]; plain-Right@range-bwd [r1,2,3]; plain-Right@range-cross [r1,2,3]; plain-Right@range-fwd [r1,2,3]; plain-Right@range-kbd [r1,2,3]; plain-Up@range-bwd [r1,2,3]; plain-Up@range-cross [r1,2,3]; plain-Up@range-fwd [r1,2,3]; plain-Up@range-kbd [r1,2,3]; shift-Down@caret-mid [r1,2,3]; shift-Down@cell-end [r1,2,3]; shift-Down@cjk-mid [r1,2,3]; shift-Down@doc-start [r1,2,3]; shift-Down@empty-para [r1,2,3]; shift-Down@heading-mid [r1,2,3]; shift-Down@list-mid [r1,2,3]; shift-Down@range-bwd [r1,2,3]; shift-Down@range-cross [r1,2,3]; shift-Down@range-fwd [r1,2,3]; shift-Down@range-kbd [r1,2,3]; shift-Down@range-one [r1,2,3]; shift-Down@wrap-line-end [r1,2,3]; shift-End@caret-mid [r1,2,3]; shift-End@cjk-mid [r1,2,3]; shift-End@doc-start [r1,2,3]; shift-End@heading-mid [r1,2,3]; shift-End@list-mid [r1,2,3]; shift-End@range-bwd [r1,2,3]; shift-End@range-cross [r1,2,3]; shift-End@range-fwd [r1,2,3]; shift-End@range-kbd [r1,2,3]; shift-End@range-one [r1,2,3]; shift-Home@caret-mid [r1,2,3]; shift-Home@cell-end [r1,2,3]; shift-Home@cjk-mid [r1,2,3]; shift-Home@doc-end [r1,2,3]; shift-Home@heading-mid [r1,2,3]; shift-Home@list-mid [r1,2,3]; shift-Home@range-bwd [r1,2,3]; shift-Home@range-cross [r1,2,3]; shift-Home@range-fwd [r1,2,3]; shift-Home@range-kbd [r1,2,3]; shift-Home@range-one [r1,2,3]; shift-Home@wrap-line-end [r1,2,3]; shift-Left@caret-mid [r1,2,3]; shift-Left@cell-end [r1,2,3]; shift-Left@cjk-mid [r1,2,3]; shift-Left@doc-end [r1,2,3]; shift-Left@empty-para [r1,2,3]; shift-Left@heading-mid [r1,2,3]; shift-Left@list-mid [r1,2,3]; shift-Left@range-bwd [r1,2,3]; shift-Left@range-cross [r1,2,3]; shift-Left@range-fwd [r1,2,3]; shift-Left@range-kbd [r1,2,3]; shift-Left@range-one [r1,2,3]; shift-Left@wrap-line-end [r1,2,3]; shift-Right@caret-mid [r1,2,3]; shift-Right@cell-end [r1,2,3]; shift-Right@cjk-mid [r1,2,3]; shift-Right@doc-start [r1,2,3]; shift-Right@empty-para [r1,2,3]; shift-Right@heading-mid [r1,2,3]; shift-Right@list-mid [r1,2,3]; shift-Right@range-bwd [r1,2,3]; shift-Right@range-cross [r1,2,3]; shift-Right@range-fwd [r1,2,3]; shift-Right@range-kbd [r1,2,3]; shift-Right@range-one [r1,2,3]; shift-Right@wrap-line-end [r1,2,3]; shift-Up@caret-mid [r1,2,3]; shift-Up@cell-end [r1,2,3]; shift-Up@cjk-mid [r1,2,3]; shift-Up@doc-end [r1,2,3]; shift-Up@empty-para [r1,2,3]; shift-Up@heading-mid [r1,2,3]; shift-Up@list-mid [r1,2,3]; shift-Up@range-bwd [r1,2,3]; shift-Up@range-cross [r1,2,3]; shift-Up@range-fwd [r1,2,3]; shift-Up@range-kbd [r1,2,3]; shift-Up@range-one [r1,2,3]; shift-Up@wrap-line-end [r1,2,3]
- **last CUR comes BEFORE the last SEL** (0): none
- **more than one SEL** (0): none
- **more than one CUR** (0): none
- **no SEL at all** (10): shift-Down@doc-end [r1,2,3]; shift-End@cell-end [r1,2,3]; shift-End@doc-end [r1,2,3]; shift-End@empty-para [r1,2,3]; shift-End@wrap-line-end [r1,2,3]; shift-Home@doc-start [r1,2,3]; shift-Home@empty-para [r1,2,3]; shift-Left@doc-start [r1,2,3]; shift-Right@doc-end [r1,2,3]; shift-Up@doc-start [r1,2,3]
- **no SEL/CUR/SS/SE at all** (10): shift-Down@doc-end [r1,2,3]; shift-End@cell-end [r1,2,3]; shift-End@doc-end [r1,2,3]; shift-End@empty-para [r1,2,3]; shift-End@wrap-line-end [r1,2,3]; shift-Home@doc-start [r1,2,3]; shift-Home@empty-para [r1,2,3]; shift-Left@doc-start [r1,2,3]; shift-Right@doc-end [r1,2,3]; shift-Up@doc-start [r1,2,3]
- **no callback of any type** (10): shift-Down@doc-end [r1,2,3]; shift-End@cell-end [r1,2,3]; shift-End@doc-end [r1,2,3]; shift-End@empty-para [r1,2,3]; shift-End@wrap-line-end [r1,2,3]; shift-Home@doc-start [r1,2,3]; shift-Home@empty-para [r1,2,3]; shift-Left@doc-start [r1,2,3]; shift-Right@doc-end [r1,2,3]; shift-Up@doc-start [r1,2,3]
- **a SEL/CUR/SS/SE callback later than 300 ms** (0): none
- **INTERMITTENT (core sequence differs between rounds)** (0): none
- **all-types sequence differs between rounds, core sequence identical** (0): none
- **SEL payload kind (empty vs not) differs between rounds, type sequence identical** (0): none
- shape not as expected before the key: none; Shift+Home/End selection not as expected: none; settle cap hit: none

## Table 6. Prediction verdicts

- P-a: HELD; selection text changed in 74 of 84 Shift cells; failing: none; cursor changed but selection text same: none
- P-b: no SEL/CUR/SS/SE in the four edge cells: HELD; no callback of any type: HELD
  - shift-Left@doc-start: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
  - shift-Right@doc-end: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
  - shift-Up@doc-start: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
  - shift-Down@doc-end: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
  - shift-Home@doc-start: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
  - shift-End@doc-end: core ['', '', ''], all ['', '', ''], selection text changed [False, False, False], cursor changed [False, False, False]
- P-c: HELD; cell shift-Left@range-one: {'coreSeqPerRound': ['SEL0 CUR', 'SEL0 CUR', 'SEL0 CUR'], 'selPayloadsPerRound': [[''], [''], ['']], 'selBefore': ['B', 'B', 'B'], 'selAfter': ['', '', '']}
- P-d: HELD; interaction arms per round 9; failing: none

## Files

- `run-20261013T095104Z/arms-r1..3.jsonl` raw per-arm records (+ `.stderr`, `.exit`); `analysis.json`, `tables.md` derived; `source-commits.txt`, `inputs.sha256`, `build-command.txt`, `tool-source-as-run.cpp`, `fixture-as-run.fodt`, `tool-paragraphs.txt`, `ended-utc.txt`, `analysis-command.txt`.
- The `.stderr` files hold core warnings (e.g. `no explicit viewshell set`, `Flavor text/plain;charset=utf-16 is not supported`); they were not looked into.
