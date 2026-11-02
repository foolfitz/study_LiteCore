# Demo batch 3 (SPEC-P-demo-batch-3)

The owner's hand test of 0.2.49 reported four points. State at the end of this session:

| Point | State | Evidence |
|---|---|---|
| 1. Writer Shift+Up/Down refused | **Fixed on the host, 0.2.50** (finding 179) | `shift-lines/`, `../host-0.2.50/` |
| 2. Does Calc autosave? | Yes; measured on 0.2.50: 30.5 s after a committed cell, trigger `auto` | `../host-0.2.50/host-shift-03/report.json` |
| 3. Calc text colour and cell fill | **Done on the host, 0.2.51** | `p2/`, `../host-0.2.51/` |
| 4. Alignment, Writer and Calc | **Done on the host, 0.2.51** | `p1/`, `p2/`, `../host-0.2.51/` |

## Generation 85 on `e2-editor-v30`

v29's wasm and loader byte for byte, the worker's extend gate no longer naming a profile. No link.

| Read | Result |
|---|---|
| S1, `shift-lines/red-on-v29` | `S1_RED`, 13 of 25 cells |
| S1, `shift-lines/on-v30`, `live-page` | `S1_HOLDS`, 25/25 on both browsers |
| S2, `make test-v30-extend-gate-static` | v29 alone is red in the census; the self-test separates the two workers under an unknown name |
| Z, `writer-zoom/run-01` | `Z_HOLDS` |
| F4, `f4-85/` | 24/24 |
| F3, `f3-85/` | `F3_83_EQUAL`, self-test `ALL_RED` |
| V0', `v0/` | **`V0_PRIME_RED`, read below** |
| V0', `v0-02/` | `V0_PRIME_HOLDS` |

`v0/` is red on the put-back alone: every stage re-read byte-identical. Two new worker sources (`sdk/ods-editor-v3-worker.js`, `sdk/v31-alignment-worker.js`) appeared in the bundle's scope while the chain ran, so the bundle line at the end was red. `v0-02/` ran with both set aside. The run that failed stays.

## Before the link

| Read | Result |
|---|---|
| N1 Writer, `native-writer-align/` | 32 arms: `align=` on the block, `fo:text-align` in the ODT, one undo |
| N2 Writer caret, `native-writer-align-caret/` | Coordinate restore 16 of 33 wrong; the read that steps one character and back 33 of 33 right, 35 of 35 with the blank document |
| N1 Calc, `native-calc-style/run-02` | 30/30 |
| E1, `pre-link/syntax.json` | `E1_HOLDS`, five controls |
| Same text, `pre-link/preprocess-same.json` | `SAME_HOLDS`: v29's and ods-editor-v2's lines preprocess to the same text as before this batch |
| M1-1, `pre-link/m1-1.*` | Exit 0 with the two new carriers |
| Contract dry run, `pre-link/make-n-owner-line.txt` | `v31 preconditions hold` |
| Review, `review/` | Codex found three defects; all are fixed (spec section 6) |

Not run, because they need the link: `tools/check_writer_align.py` and `tools/check_calc_style.py`. Neither has ever run against an engine.

`calc-preview/` is a layout preview on a doctored manifest; the buttons do nothing there.

`list-caret-product/` is finding 180, the shipped list and heading buttons, not changed here.

## After the link (2026-11-02, 2026-11-03)

The agent ran the link on the owner's word: `link-3/`, 5 min 7 s, exit 0. Archives `build/archive/e2-editor-v31-809893a9-worker-54352fad`, `build/archive/ods-editor-v3-e6593b2c-worker-6df70322`.

| Read | Result |
|---|---|
| P1, `p1/final-86` | `P1_HOLDS`, 108/108 per browser: alignment saved, one undo, reopened, the caret on the product path |
| P1 red cases | `red-no-undo`, `red-swap-worker`: `P1_RED`. `red-swap`, swapping the attribute in the HTML, held: the attribute is both the tool's selector and the page's action, kept as a dead mutation |
| P2, `p2/final-dist` | 33/33 per browser on the final bytes |
| P2 red cases | `red-wrong-fill`, 8 cells; `red-engine-v2`, red at setup |
| Calc regression, `calc-regression/` | cell 31, range 40, autosave 18, per browser, on v3 |
| S1 `shift-lines/live-page-86`, Z `writer-zoom/run-86`, C `calc-sheet-view/run-86` | `S1_HOLDS`, `Z_HOLDS`, 4 runs green |
| F4, `f4-86/` | 24/24 |
| F3, `f3-86/` | `F3_83_MOVED` on the pinned tool, one Firefox cell; `F3_83_EQUAL`, 46/46, through the clear wait. Read below |
| V0', `v0-86/` | `V0_PRIME_HOLDS`, nine stages |
| Units, `post-link/` | shell 569/569, Calc 104/104, format entry 15/15, range 7/7 |

P2's reds in order, kept: `run-01` the sample landed on a glyph; `run-03`, `run-04` the range and the row count were the tool's; `run-05` a real gap, a refused control said nothing, fixed in the page, `run-06` green.

**F3.** Firefox `every-inline-format-reaches-the-document` moved in one of four runs of the pinned tool. It is finding 178's open race: the runner presses into the page's clear loop, seen in the request order in `f3-86/race/natural-v31-firefox.json`. Rate on one shell, two engines: v31 1/120, v30 3/120. Loop width 53 and 56 ms. The four clear-wait runs alone would prove nothing at that rate; the request order does. `PREDICTION.md` was committed first.
