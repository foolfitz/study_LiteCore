# Demo batch 4 (SPEC-P-demo-batch-4)

H1 to H4 in a menu, heading and list on one button each way, finding 180. One link: `e2-editor-v32`. State at the end of this session: everything up to the link is done; the link has not been run.

## Measured before the design was pinned

| Read | Result |
|---|---|
| `cancel-today/` | The shipped buttons: a second press does nothing, a separate button takes it off |
| `cache-freshness/run-02` | `listBullet`, `listNumber`, `paragraphStyle` follow the caret, 144/144, slowest 0.355 s, Chrome and Firefox. Finding 021's staleness does not hold on the main loop. `formatStale` was true on 39 of those 144 steps with every value right, so it is not a validity bit. `listNumber` reads true on every heading (`run-01`) |
| `native-toggle/` (N3) | A one-character selection never shows the list. A range that starts inside a paragraph loses that paragraph's style in the HTML. `caret/` was stopped on purpose, see `caret/STOPPED.txt` |
| `native-caret-read/` (N4) | The read that selects nothing, `src/writer_caret_bridge.cpp`. Caret: read 168/168, equals the saved file 168/168, the saved file equals the no-read control 168/168, target met 164/168 (the four are numbering on a heading). `reading.txt` has every miss. All of them are inline headings (`widen/` shows the widened arms clean), numbering on headings, a selection across a table, or a list style that defines one level |
| `before-v31/run-01` | The shipped page, both browsers: a leading selection builds a frame (finding 181); a range from inside a paragraph ends in `recoverable-error` with save gone (finding 182) |
| `preview/run-01` | The new controls on the v31 engine with the page's `offers` test forced: T9 and T10, Chrome. Nothing about the actions |

`native-caret-read/range` was run twice. The first run read 84 arms, every command silently doing nothing and every read agreeing with the file: a harness I had stopped left a `.~lock` beside the fixture and the next run opened it read-only. It was deleted and `run.sh` now copies the fixtures per run.

## Before the link

| Read | Result |
|---|---|
| E1, `pre-link/syntax.json` | `E1_HOLDS`, five units, four controls |
| SAME, `pre-link/preprocess-same.json` | `SAME_HOLDS`: v31, v29 and ods-editor-v3 preprocess to the same text as `f3204745e` |
| M1-1, `pre-link/m1-1.*` | Exit 0 with the E2_V32 carrier |
| Dry run, `pre-link/make-n-owner-line.txt` | `check_v32_paragraph_contract.py --build-log`: `v32 preconditions hold` |
| W1, E2 | `make test-demo-batch-4-static` |

Not run, because they need the link: `tools/check_writer_toggle.py` (P4), `tools/check_writer_align.py` against v32 (P1'), the generation 87 chain, the host.
