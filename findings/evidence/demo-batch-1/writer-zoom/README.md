# Writer toolbar zoom (SPEC-P-demo-batch-1 section 3)

Tool: `wasm_sdk_probe/tools/check_writer_zoom.py`. Mirror of `dist/` with the live page sources and an observer on the Worker, document `test-docs/t3-long.odt` (22 pages), real pointer and keys.

| Run | Result |
|---|---|
| `run-01` (`run-01.log`) | `Z_HOLDS`. Chrome 156 wide 34/34, narrow 4/4, DPR 2 16/16. Firefox 157 wide 34/34, narrow 4/4. |
| `mutation-no-side-follow` | `MUTATION_CAUGHT`: Z4/end |
| `mutation-no-centre` | `MUTATION_CAUGHT`: Z5, 8 cells |
| `mutation-no-flex-none` | `MUTATION_CAUGHT`: Z6, and Z1/Z2 at 200 because the flex item shrank |
| `mutation-stretched` | `MUTATION_CAUGHT`: Z2, 8 cells |

Screens read by eye: `chrome-narrow-narrow-left-edge.png` (200 percent, 900 px window, paper's left edge inside the desk, text sharp), `firefox-wide-200-end.png` (page 22 of 22 painted at 200 percent).

One-off, not a gate (spec section 3). Chrome, DPR 1, 30 real keys with `insertText` request to reply:

| Level | Typed median | Paint median |
|---|---|---|
| fit | 6.1 ms (6.7 in the earlier uncommitted trial) | 5.9 ms |
| 200 percent | 9.9 ms (7.2 in the earlier trial) | 8.0 ms |

The desk was not gated for time, and the owner's Firefox and zen were open. These numbers say the cost is of this order, not what the gate of 16 ms would read.

The controls sit after the toolbar's spacer, so on the mirror's full toolbar at 1400 px they wrap to a second row; the host hides most of those buttons.

Named reds that are not this batch's: `editor-shell-v2/tests/page-select-all.test.mjs` "U2 wiring" pins `e2-editor-v26` while the page has been on later profiles since generation 81; red at the commit before this batch too. Left as it is.
