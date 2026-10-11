# `make test-e2-c-static` on the main tree after the C′ page came in (2026-10-11)

Rule ddd: run the static suite before anything counted. Three outputs, in order:

| File | Tree | Result |
|---|---|---|
| `static-on-main-cprime-only.txt` | `90242ebc` (C′ only, `f5121fd4…`), runners at HEAD | exit 2: shell manifest out of date; mutation `gesture-abort-not-wired` 0 hits; `--caret-source-diagnostic`'s `CARET_SOURCE_ANCHOR` and `CARET_ANNOUNCE_ANCHOR` 0 hits (two anchor tests and the patch-parses test) |
| `static-on-main-final-page-two-anchors-fixed.txt` | final page `8909564e…` (124, 125, `13f91117` cherry-picked), those two diagnostic anchors re-anchored | exit 2: manifest; `PAGE_STATE_ANCHOR` 0 hits (finding 125 turned `updateState`'s first statement into a multi-line `showState(...)` call), so the caret-source patch refuses. **Reproduced** after the fact: the first run's output was overwritten in the scratchpad, so this file was re-run with the runner holding only the first two re-anchors (sha256 `05b046244e71ac91`; it differs from that first intermediate, `dce93d4892d42dd7`, by comment lines only). |
| `static-on-main-final-page-after-reanchor.txt` | final page, all three diagnostic anchors re-anchored (`run_e2_c_product_path.py` `bd6fc0caf677ee9c`) | exit 2, **one failure only**: the shell manifest (v60) is out of date because the page changed — expected until shell v61 is frozen (finding 091's shape). Node tests pass; the caret-source patch now parses (`node --check`). |

The three diagnostic anchors are re-anchors only: the inserted code reads `snapshot`, `session` and
`#s-latency`, never `#canvas` or `#paper` geometry; `PAGE_STATE_ANCHOR` is now the opening line of `updateState`
alone, so both of its insertions (caret-source's `caretBelieved`, barrier-details' `paragraphs`) land at
function entry, one statement earlier than before; that statement (`showState`) writes only the state pill.
The handoff's "50 of 51 mutation anchors match" covered `MUTATIONS` only, not these diagnostic mirrors.
