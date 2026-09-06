# Gate condition 2 — the caret diagnostic runs — DISCHARGED

Judged 2026-09-03 by `wasm_sdk_probe/tools/check_caret_diagnostics.py`, whose
verdict is banked beside this file as `VERDICT-condition-2.json`. Re-runnable:

```bash
cd wasm_sdk_probe && python3 tools/check_caret_diagnostics.py
```

## The criterion, verbatim

Three diagnostic runs, additionally, to keep bounding the finding 084 class:

```
--candidate-profile e2-editor-v12 --caret-source-diagnostic \
    --caret-rounds 12 --caret-engine-probe stalled
```

Required: **0 dropped commits in 36**, and `staleWritesRefusedTotal > 0` in at
least one — because a run whose guard never fired has only shown that the race
was not lost that time. These are diagnostic and do **not** count toward the
twelve. (The plan's soak section names `e2-editor-v11`; the 2026-08-29
amendment moved the candidate to `e2-editor-v12` and the re-earn list carries
this item forward unchanged except for the profile.)

## Result — all four terms pass

| term | result |
|---|---|
| 1 identity | all three carry `caretSourceDiagnostic`, `engineProbeMode: stalled`, profile `e2-editor-v12`, page sha `3dfdcfef…` |
| 2 count | **3 of 3** complete runs |
| 3 rounds | **36 committed rounds, 0 dropped**; each run reached 12 of 12 and `caret-follows-the-text-you-type` PASSes |
| 4 guard fired | `staleWritesRefusedTotal` = **11, 7, 6** — the guard refused a stale write in every run |

| run | completedAt | reached | dropped | staleWritesRefused |
|---|---|---|---|---|
| `diagnostic-01-caret12.json` | 2026-09-03T12:44:36+08:00 | 12 | 0 | 11 |
| `diagnostic-02-caret12.json` | 2026-09-03T12:51:45+08:00 | 12 | 0 | 7 |
| `diagnostic-03-caret12.json` | 2026-09-03T12:58:29+08:00 | 12 | 0 | 6 |

## Two things the judge refuses, and why they are terms rather than footnotes

**`engineProbeMode` is part of the identity term.** The first three-layer caret
probe asked the engine for its caret before every commit; under it 24 of 24
commits followed the caret, while the identical configuration without the probe
dropped 10 of 48 (Fisher exact p = 0.012). The instrument suppressed the defect
it was built to measure. A run taken with `--caret-engine-probe every-round` is
therefore not weaker evidence for this condition — it is evidence about a
different system — so the judge refuses it rather than counting it.

**Term 3 requires ≥36 committed rounds AND zero dropped, both.** A run that
committed nothing drops nothing; checking only the second half would pass it.

## The judge was made to say no first

Eight red cases, all red, plus a green control (`--self-test`): nothing given at
all; two runs where three are required; one dropped commit in 36; clean but the
guard never fired; a plain run offered as a diagnostic; the engine probed every
round; the wrong page sha; and no commits at all. The green control exists
because three red cases built from a broken fixture would all be red without the
judge working at all.

---

# Re-taken on page `20f09cc9…` — DISCHARGED again (2026-09-06)

Everything above describes the take on page `3dfdcfef…`, which the human round
of 2026-09-04 moved. Those three runs and that verdict are now in
`../queue-v12-cutover-soak-void-3dfdcfef/`; nothing in them was edited. This
section is the current take, on the page the ten banked soak runs measured.

Same command, same profile, same flags:

```
python3 tools/run_e2_c_product_path.py --candidate-profile e2-editor-v12 \
    --caret-source-diagnostic --caret-rounds 12 --caret-engine-probe stalled
```

## Result — all four terms pass

| term | result |
|---|---|
| 1 identity | all three carry `caretSourceDiagnostic`, `engineProbeMode: stalled`, profile `e2-editor-v12`, page sha `20f09cc9…` |
| 2 count | **3 of 3** complete runs |
| 3 rounds | **36 committed rounds, 0 dropped**; each run reached 12 of 12 and `caret-follows-the-text-you-type` PASSes |
| 4 guard fired | `staleWritesRefusedTotal` = **0, 9, 4**; max 9, and the term requires >0 in at least one |

| run | completedAt | reached | dropped | staleWritesRefused |
|---|---|---|---|---|
| `diagnostic-01-caret12.json` | 2026-09-06T19:36:25+08:00 | 12 | 0 | **0** |
| `diagnostic-02-caret12.json` | 2026-09-06T19:42:36+08:00 | 12 | 0 | 9 |
| `diagnostic-03-caret12.json` | 2026-09-06T19:48:48+08:00 | 12 | 0 | 4 |

## A run with a guard that never fired, and what it is not

Run 01 refused **zero** stale writes and still committed 12 of 12 with the caret
following every time. On the 2026-09-03 take every run fired (11, 7, 6), so this
is the first banked diagnostic run where the race was simply never contended.

That is what the criterion's "in **at least one**" clause is for, and it is why
that clause is not "in every run": the guard fires when there is a race to lose,
and demanding that there always be one would make the criterion an assertion
about scheduling rather than about the guard. Run 01 is a clean run whose caret
was correct without the guard's help, not a run where the guard was absent.

## The self-test went red, and it was red at itself

Running `--self-test` after banking these three reported

```
RED (WRONG)     control: three unmodified diagnostic runs
  control failed on: ['4-guard-fired']
```

with all eight red cases still red. **The red was in the self-test's fixture
selection, not in the judge and not in the product.** The green control is three
copies of one real report, and the base was taken as `sources[0]` — which is
`diagnostic-01`, the run whose guard never fired. So the control asserted term 4
against a fixture that cannot satisfy it. The judge's verdict on the real bank
was `ok: true` throughout, correctly.

Fixed by making the base a **choice rather than a take**: the self-test now
selects the first complete report whose guard actually fired, and if no banked
report qualifies it **refuses** with a message saying so, in the same shape as
the existing "no complete report to build from" refusal. A control that is red
for a reason outside the judge teaches nothing, and silently accepting one would
have been worse than the red.

The selector is not vacuous on this bank — it rejects `diagnostic-01`
(`staleWritesRefusedTotal: 0`) and accepts `diagnostic-02` (9) and
`diagnostic-03` (4). After the fix: 8 red cases all red, green control green.
