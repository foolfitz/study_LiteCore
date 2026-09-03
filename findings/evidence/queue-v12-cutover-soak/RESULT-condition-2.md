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
