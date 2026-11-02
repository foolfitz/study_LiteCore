# Demo batch 4 (SPEC-P-demo-batch-4)

H1 to H4 in a menu, heading and list on one button each way, finding 180. One link: `e2-editor-v32`. The owner linked it on 2026-11-03; `link/`. Reads after the link are in the last section.

## Measured before the design was pinned

| Read | Result |
|---|---|
| `cancel-today/` | The shipped buttons: a second press does nothing, a separate button takes it off |
| `cache-freshness/run-02` | `listBullet`, `listNumber`, `paragraphStyle` follow the caret, 144/144, slowest 0.355 s, Chrome and Firefox. Finding 021's staleness does not hold on the main loop. `formatStale` was true on 39 of those 144 steps with every value right, so it is not a validity bit. `listNumber` reads true on every heading (`run-01`) |
| `native-toggle/` (N3) | A one-character selection never shows the list. A range that starts inside a paragraph loses that paragraph's style in the HTML. `caret/` was stopped on purpose, see `caret/STOPPED.txt` |
| `native-caret-read/` (N4) | The read that selects nothing, `src/writer_caret_bridge.cpp`. Caret: read 168/168, equals the saved file 168/168, the saved file equals the no-read control 168/168, target met 164/168 (the four are numbering on a heading). `reading.txt` has every miss. All of them are inline headings (`widen/` shows the widened arms clean), numbering on headings, a selection across a table, or a list style that defines one level |
| `native-toggle-sequence/run-01` (N5) | 108 presses in 28 sequences through the v32 decision (`tools/n5_native_writer_toggle_sequence.cpp`): reversal on bullets, numbers and four heading levels, body, list and table caret, empty paragraphs, a blank document, ranges, mixed ranges, the whole document. 105 verified, 3 refused as designed, every saved file agrees with the read |
| `native-toggle-sequence/run-02-no-drain` | The same with the read straight after the post, as the engine does it. Same outcome, 105 and 3 |
| `before-v31/run-01` | The shipped page, both browsers: a leading selection builds a frame (finding 181); a range from inside a paragraph ends in `recoverable-error` with save gone (finding 182) |
| `preview/run-01` to `run-06` | The new controls on the v31 engine with the page's `offers` test forced: T9 and T10. `run-02` is red on one cell on the v31 worker, a body paragraph reached from a body paragraph, because a reply went through the old projection; `run-03` with the v32 worker is green. `run-05` is the first run with the keyboard press cells: Chrome's CDP key does not fire a button's default click, so the page now handles Enter itself. `run-06` holds 23/23 on both browsers. Nothing about the actions |
| `native-caret-read/large` | The read's cost: 8 ms for 100 paragraphs, 329 ms for 1,000, 7.9 s for 5,000, 157 s for 20,000, native. Hence the limit of 500. Nine arms in a paragraph with an as-char frame: target met 9/9, the saved files agree (`postMatchesFile` reads 0 only because the reader's text match trips on the frame's anchor character) |

`native-caret-read/range` was run twice. The first run read 84 arms, every command silently doing nothing and every read agreeing with the file: a harness I had stopped left a `.~lock` beside the fixture and the next run opened it read-only. It was deleted and `run.sh` now copies the fixtures per run.

## Before the link

| Read | Result |
|---|---|
| E1, `pre-link/syntax.json` | `E1_HOLDS`, five units, four controls |
| SAME, `pre-link/preprocess-same.json` | `SAME_HOLDS`: v31, v29 and ods-editor-v3 preprocess to the same text as `f3204745e` |
| M1-1, `pre-link/m1-1.*` | Exit 0 with the E2_V32 carrier; `m1-1-red-without-carrier.*` red on exactly its three objects |
| Symbols, `pre-link/symbols.json` | `SYMBOLS_HOLD`: `SfxLokHelper::getViewOfId` and `SfxViewShell::GetCurrentDocument` are defined in this core's archives (llvm-nm, no compile) |
| Dry run, `pre-link/make-n-owner-line.txt` | `check_v32_paragraph_contract.py --build-log`: `v32 preconditions hold` |
| W1, E2 | `make test-demo-batch-4-static` |

| Review, `review/` | Codex read-only, 15 points. Spec section 7 has the outcome of each. Fixed: the read's limit, three post-dispatch shapes to review, focus after a keyboard press, the menu on an unavailable session, seven acceptance cells |

Not run, because they need the link: `tools/check_writer_toggle.py` (P4), `tools/check_writer_align.py` against v32 (P1'), the generation 87 chain, the host.

## After the link

| Read | Result |
|---|---|
| `p4/run-01` | 106/117 on both browsers, the witness. Ten T4 cells were the tool's expectation; T12 was the fixture's PNG. `p4/diag-t12/` separates them; finding 183 |
| `p4/run-02` | `P4_HOLDS`, 126/126 on both browsers, with a control with nothing pressed at every T4 place |
| Red cases | `red-no-undo`, `red-no-second-press` read `P4_RED`. `red-swap-levels` read `P4_RED` on a fatal: the client's own check on the reply stopped the run, so it showed nothing about the reader. `red-swap-levels-02` puts the reply back and is red on exactly `T2/h2/on` and `T2/h3/on`, reading the swapped levels in the file |
| `p1/run-01` | `P1_HOLDS`, 108/108 on both browsers |
| `p4/read-cost-02` | The Wasm factor the runbook asked for, the page's own label. A press at a caret: 10 to 24 ms at 100, 250 and 500 paragraphs. All selected at 500: bullet on 257 and 366 ms, heading 273 and 380 ms, bullet off 1.33 and 1.41 s, Chrome and Firefox. `read-cost/` is the tool's failure: an unsaved page's `beforeunload` held the navigation |
