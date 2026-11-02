# Demo batch 2 (SPEC-P-demo-batch-2)

| Item | Evidence | Result |
|---|---|---|
| The red on 0.2.47 | `red-on-0247/` | As predicted: Close right gap 17, 640, 15; Save left gap 731 against 12; dark Writer bold contrast 1.51 |
| Zoom again | `writer-zoom/run-01` | `Z_HOLDS` |
| Each sheet's view again | `calc-sheet-view/run-01` | Editor 14/14, viewer 11/11, both browsers |
| F4, F3, V0' on these pages | `chain.log`, `f4-84/`, `f3-84/`, `v0/` | 24/24, `F3_83_EQUAL`, `V0_PRIME_HOLDS` in 97 s |

The host side is `../host-0.2.48/`, with T1 to T5 in `host-layout/`. Tool: `host_layout.py`.

Numbers after the change: Close right gap 17 on all three pages; Save left gap 14 and 32 x 34 on both; dark contrast 14.47 and 11.53 on Writer, 13.59 on Calc.

The zoom mutations were not repeated: they prove the tool, and `check_writer_zoom.py` did not change.
