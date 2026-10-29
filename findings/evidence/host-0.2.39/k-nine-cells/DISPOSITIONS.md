# Dispositions of the nine K cells (K ruling revision 1)

Each cell was PASS 3/3 for v21 at the 0.2.26 count and is not PASS on v24. Evidence: this
directory (H2 v21 / H4 v22 / H3 v24 with identical tools and browsers; `diag-format/run-01,02`).
A cell with a product disposition stays RED against the 0.2.26 anchor until fixed; a cell with an
instrument disposition needs its own ruling before K. Nothing here is a K result.

| # | Browser | Check | Disposition | Status |
| --- | --- | --- | --- | --- |
| 1 | chrome | bulleting-a-blank-line-does-not-demand-a-rollback | **product**, finding 171 (ordered barrier stays `idle`; worker projects `dispatched: false`; v22 `true`, v24 `false` measured in `diag-format/run-02`) | RED until fixed |
| 2 | firefox | bulleting-a-blank-line-does-not-demand-a-rollback | **product**, finding 171 (same mechanism; H3 firefox `recoverable-error`) | RED until fixed |
| 3 | chrome | every-inline-format-reaches-the-document | **product**, finding 172 (normalising clear-format stops at its first no-op `LOK_COMMAND_FAILED`; precondition never established) | RED until fixed |
| 4 | firefox | every-inline-format-reaches-the-document | **product**, finding 172 (same; H3 firefox arms identical in shape) | RED until fixed |
| 5 | chrome | clear-format-removes-every-inline-format | **product**, finding 172 (button answers `LOK_COMMAND_FAILED`; "all four on" never established) | RED until fixed |
| 6 | chrome | an-inline-format-reaches-a-selection | **product, downstream of 172**: v22's drag selected `KITAL` (not bold), v24's selected `KBOLD` (already bold, `wasBoldBefore: true`) on a different line (y 0.389 vs 0.342) because the earlier format arms left a different document. Bold-on-a-range itself is **not** shown to fail. Re-measure after 172's fix | RED until 172 fixed and re-measured |
| 7 | chrome | a-boundary-arrow-press-does-not-cost-the-work | **instrument, needs a ruling**: on v24 B1, B2, B3 are true; B4 is null because "the second inducer never fired ... auto-attach delivered no session for a document worker" (H3, T4). On v22 (H4) the same inducer fired and B4 was true. The v23 ruling (`link-batch-v23/review/ruling-fable-1-addendum-1.md` section 2.1 item 5: "B4 remains driven by the second inducer as today") assumed the inducer still reaches the worker; on v24 it does not. Re-cited, not assumed: that ruling does not cover an unreachable inducer | needs a named instrument limit with its own ruling |
| 8 | chrome | the-enter-key-reaches-the-document | **instrument, named limit I-enter-raw-substring** (spec v24 sections 17.3 / ruling 1 addendum 1): v24 typed text carries rsid spans; the frozen oracle's raw substring cannot see the break; `check_v24_shift_enter.py` 3/3 and the span-aware replay hold | covered by an existing ruling; the K reader must apply it explicitly |
| 9 | chrome | editing-a-long-document-stays-responsive | **instrument, intermittent**: PASS on v21, v22 and v24 here (H2, H4, H3) and in T4 run-01/03; FAIL once in T4 run-02 (`t4/README.md:83`, ink trigger race). One observation is not a rate | N runs still owed before a disposition |

Findings 171 and 172 were first shipped by host 0.2.39 (v23 was never packaged); the owner's
host engine was rolled back to exact 0.2.38 bytes on 2026-10-29 (`../rollback-20261029T104705+0800/`).
Both fixes change the engine (and 172 possibly the page), i.e. a new successor identity and link.
