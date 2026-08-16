# Finding 046, native arm — registered before the probe was written

Written 2026-08-16, before `tools/f046_native_empty_readback.cpp` existed.

## The question, and why it is not yet answerable in the browser

Finding 046's remedy — report `MUTATION_OUTCOME_UNKNOWN` with its own
`empty-readback` shape instead of `EDITOR_FORMAT_POSTCONDITION_FAILED` — has a
criterion that is **not decided yet**, and the correction of 2026-08-15 says
why: the same empty paragraph produces two different outcomes depending on how
the caret was formed, both with `postBlocks: 0`, and the one that differs turns
on `itemCount`, which the shipped product does not project.

`itemCount` has since been added to the product projection
(`sdk/sdk-worker.js`), but that is queued for the v3 relink, so **no browser on
this artifact can answer the question today**.

Native can, and without touching anything: the engine's own parser can be
sliced out of `probe_engine.cpp` and run over markup captured natively
(`tools/test_format_readback_parser.py` already does exactly that, so the
classification comes from the shipped scanner rather than a reimplementation of
it).

**What is being measured**: the raw `text/html` readback for an empty paragraph,
under each of the two caret gestures, with and without the barrier's own
selection pair — and then what the engine's parser makes of each.

## The arms

Fixture `test-docs/e1/empty-paragraph.odt`: `E1-EMPTY-BEFORE`, an empty
paragraph, `E1-EMPTY-AFTER`, an empty paragraph.

| arm | caret formed by | selection |
|---|---|---|
| `click-empty-bare` | `postMouseEvent` on the empty line | none (what pre-dispatch routing reads) |
| `click-empty-pair` | the same, then `.uno:GoToStartOfPara` + `.uno:EndOfParaSel` | the barrier's own pair |
| `select-empty-bare` | `setTextSelection(RESET)` at the same point | none |
| `select-empty-pair` | the same, then the pair | the barrier's own pair |
| `click-text-pair` | the same on `E1-EMPTY-BEFORE`, which has text | **control** |

The control is not decoration: without it, "zero blocks everywhere" cannot be
told from a probe that captures nothing at all.

## Predictions

- **P-046-1** — on an empty paragraph, at least one arm produces markup the
  engine's parser reads as `parsed=true, blockCount=0`.  That is the state the
  remedy needs a name for.
- **P-046-2** — the control produces `blockCount >= 1`, so a zero is a
  measurement rather than a broken capture.
- **P-046-3** — **the two gestures differ**: the click and the zero-width
  selection do not produce the same parse on the same paragraph.  This is what
  SPEC E2-C 9.5.6 measured through the product, and 046's correction inferred;
  here it is read directly.
- **P-046-4** — at least one arm shows `itemCount > blockCount`, which is the
  combination that makes `multiBlock` true with no block in the readback, and
  is what made the shipped message ("covered more than one paragraph") say
  something the evidence contradicts.

## The criterion this round is supposed to settle

3b in `handoff/PLAN-E2-C-relink-v3.md`.  Registered in advance so the answer
picks between them rather than being written around whatever comes back:

| if the measurement shows | then `empty-readback` is defined as |
|---|---|
| `parsed && blockCount == 0 && itemCount == 0` occurs | exactly that — nothing was described |
| `parsed && blockCount == 0 && itemCount > 0` also occurs | `blockCount == 0` alone, with `itemCount` recorded in the payload: a readback with no block does not support a postcondition judgement whatever else it saw |
| `blockCount == 0` never occurs natively | the shape is not needed and 3b is withdrawn — the browser evidence would then need re-explaining, which is itself a finding |

**Nothing here describes the WASM artifact.**  Same rule as findings 016, 045
and 048's native arms: native says what core does, not what the build does.
