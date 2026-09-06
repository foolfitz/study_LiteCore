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

---

# Voided again 2026-09-06 — the page moved a second time

Everything in the section above describes the take on page `20f09cc9…`. The
shipping shell changed twice on 2026-09-06 (finding 088's fix, shell
generation v45); the candidate page's sha moved to `39895d15…`. Per ruling 1
of `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, the count restarts on
the day the page changes, the same rule that voided the `3dfdcfef…` take
above.

`diagnostic-01-caret12.json`, `diagnostic-02-caret12.json`,
`diagnostic-03-caret12.json`, and the judge's verdict of that day (renamed
`VERDICT-condition-2-on-20f09cc9.json`) are now in
`../queue-v12-cutover-soak-void-20f09cc9/`; nothing in them was edited. Unlike
the `3dfdcfef…` void, this time the diagnostics moved with the verdict rather
than staying behind — see
`../queue-v12-cutover-soak-void-20f09cc9/WHY-THESE-ARE-VOID.md` for the
per-file page shas and the full account.

Condition 2 must be re-earned on `39895d15…`, under task T2 of
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`. This file stays where
it is, per the same disposition its `20f09cc9…` section already gave it: the
readable record of a discharged condition belongs beside the bank it describes,
not inside the void directory of the page that discharge no longer counts for.

---

# Re-taken on page `9b29e39b…` (shell generation v48) — DISCHARGED again (2026-09-07)

`39895d15…` itself moved twice more (finding 088's second fix, then the T1d
mistake and its v48 correction — see
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, "The page is final").
This is the current take, on the final page for this gate, task T2.

Same command, same profile, same flags:

```
python3 tools/run_e2_c_product_path.py --candidate-profile e2-editor-v12 \
    --caret-source-diagnostic --caret-rounds 12 --caret-engine-probe stalled
```

## Result — all four terms pass

| term | result |
|---|---|
| 1 identity | all three carry `caretSourceDiagnostic`, `engineProbeMode: stalled`, profile `e2-editor-v12`, page sha `9b29e39b…` |
| 2 count | **3 of 3** complete runs |
| 3 rounds | **36 committed rounds, 0 dropped**; each run reached 12 of 12 and `caret-follows-the-text-you-type` PASSes |
| 4 guard fired | `staleWritesRefusedTotal` = **3, 1, 3** — the guard refused a stale write in every run |

| run | completedAt | reached | dropped | staleWritesRefused |
|---|---|---|---|---|
| `diagnostic-01-caret12.json` | 2026-09-07T02:33:38+08:00 | 12 | 0 | 3 |
| `diagnostic-02-caret12.json` | 2026-09-07T02:49:52+08:00 | 12 | 0 | 1 |
| `diagnostic-03-caret12.json` | 2026-09-07T03:00:10+08:00 | 12 | 0 | 3 |

`check_caret_diagnostics.py`'s verdict: `"ok": true` over all four terms.
Banked as `VERDICT-condition-2.json` (this take overwrites the previous
`20f09cc9…` take's verdict file of the same name — that older verdict is
preserved unedited in `../queue-v12-cutover-soak-void-20f09cc9/` per its own
void disposition above).

## The raw runs are NOT clean soak runs, and that is a separate, already-recorded fact

All three diagnostic reports carry `ok: false` at the top level and a
composition of 37 PASS / 2 NE / 1 FAIL, the same `the-document-region-says-why-it-is-empty`
FAIL recorded in `RUNS.md`'s "Re-taken on `9b29e39b…` / v48" section and in
`../gate-4a-on-9b29e39b/RESULT-4a.md`. None of condition 2's four terms reads
the raw `ok` field or the full composition — they read `caretSourceDiagnostic`,
`caretOutcome` (the one caret-specific check) and per-round fields — so this
does not touch condition 2's discharge. It is not re-derived here; recorded so
a reader comparing this table against the raw files does not mistake the
absence of `ok: true` for a discrepancy in this judge's work.
