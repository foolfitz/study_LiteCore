# Demo batch 1 (SPEC-P-demo-batch-1)

| Item | Evidence | Result |
|---|---|---|
| Calc: each sheet keeps its view | `calc-sheet-view/` | Red before in the owner's shape; editor 14/14, viewer 11/11 on both browsers |
| Writer: toolbar zoom | `writer-zoom/` (`run-02` is the final HTML) | `Z_HOLDS`, four mutations caught |
| Generation 84 | `freeze-84/` | Differs from 83 in the page only; E1-C intact |
| Final-HTML regression | `chain-84b.log`, `f4-84-final/`, `f3-84-final/`, `v0-02/` | F4 24/24, `F3_83_EQUAL` with self-test `ALL_RED`, `V0_PRIME_HOLDS` |

`f4-84/`, `f3-84/`, `v0/` and `writer-zoom/run-01` are the same reads on the HTML before spec append 1. `writer-zoom/z10-red-before` is the mirror failing to go red: it is why Z10 is judged on the host.

The host side is `../host-0.2.46/` and `../host-0.2.47/`.
