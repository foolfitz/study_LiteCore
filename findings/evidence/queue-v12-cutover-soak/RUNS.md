# The v12 soak — the bank

Criteria: `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, the soak section
as amended 2026-08-29 (candidate `e2-editor-v12`, page sha `3dfdcfef…`).

A run counts only if: `ok: true` and `complete: true`; `check_usable_editor.py`
reconciles `ok: true` with `reconciledFor.kind == "candidate-cutover"` and
`profile == "e2-editor-v12"`; the composition is 38 PASS / 2 NOT_ESTABLISHED
with the NE set exactly `{notice-action-recovers-the-session,
a-refused-action-is-reported-and-changes-nothing}`; and the report carries
`candidateCutover.pageSha256 == 3dfdcfef…`.

**Which calendar day a run belongs to**: the day of the report's completion
timestamp. Written down because run 3 of the void v11 lineage started at 23:54
and finished at 00:01, and a criterion with an undefined boundary is the shape
this gate exists to stop.

| # | date | report | composition |
|---|---|---|---|
| 1 | 2026-08-29 | `../queue-v11-split-probe/criterion-2-net-v12.json` | 38 PASS / 2 NE, reconciled |
| 2 | 2026-08-29 | `soak-run-02-candidate.json` | 38 PASS / 2 NE, reconciled |
| 3 | 2026-08-29 | `soak-run-03-candidate.json` | 38 PASS / 2 NE, reconciled |
| 4 | 2026-08-29 | `soak-run-04-candidate.json` | 38 PASS / 2 NE, reconciled |

Run 1 is the split probe's criterion-2 run, banked in place rather than copied:
evidence in this tree is not moved. It satisfies every clean clause on the real
candidate page.

## The void lineage

Five clean runs on unsplit `e2-editor-v11` (2026-08-28 ×2, 2026-08-29 ×3) are
**void for this count** and retained, untouched, in
`../queue-v11-cutover-soak-not-started/`. They were voided by the candidate
changing identity, not by anything wrong with them.

## Interrupted, not banked

`interrupted-2026-08-29-0050-partial.json` is the **partial snapshot of an
interrupted run**, not a run. It carries `complete: false` and no `ok` and
stopped after 6 checks, so `check_usable_editor.py` refuses it — the guard
working.

It was written as `soak-run-02-candidate.json` and has been **renamed out of
the `soak-run-*` namespace**, kept rather than deleted. A file called
`soak-run-02-…` that is not run 2 is exactly what a later glob miscounts, and
the fix is a name that does not lie rather than a deletion that hides that the
interruption happened. Nothing about the product was measured by it.

**Superseded 2026-09-03** by the plan's amendment of that date: a run's day is
the UTC date of the report's own `completedAt`; reports without the field
(runs 1–6) count toward twelve and contribute no day. The dates in the table
above are the drafting party's assertion, corroborated only by mtime read before
any clone; the criterion does not consume them. The instrument now writes the
field, so runs 7–12 carry their own day.

## Voided 2026-09-05 — the candidate page moved, and the count is 0 of 12

The human round of 2026-09-04 forced two fixes into
`wasm_sdk_probe/web/e2-editor-app.js`, one of the shell bundle's thirteen
`included` paths. The candidate page's sha therefore moved from
`3dfdcfef…` to
**`20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95`**,
recomputed from source through `repointed_page()` against
`dist/profiles/e2-editor-v12/sdk-manifest.json`.

Every run banked above was taken on `3dfdcfef…` and is **void for this count**:

* Runs 2–8 moved, untouched, to `../queue-v12-cutover-soak-void-3dfdcfef/`,
  with `WHY-THESE-ARE-VOID.md` alongside them.
* Run 1 — the split probe's criterion-2 run, banked in place at
  `../queue-v11-split-probe/criterion-2-net-v12.json` — stays where it is,
  because it is that probe's evidence as well, and is dropped from this
  checker's `--also` list.
* `interrupted-2026-08-29-0050-partial.json` stays. It is a declared non-run and
  makes no sha claim; nothing about the page voids it.
* `diagnostic-01..03` stay in this directory and are **also void**, by
  `check_caret_diagnostics.py`'s own identity term (`pageShaMatches`), which
  pins them to the same sha. That is condition 2's business, not condition 1's;
  `check_soak_bank.py` continues to list them under
  `conditionTwoFiles_NOT_JUDGED_HERE` without judging them.

`check_soak_bank.py`'s `--expect-page-sha256` default is updated to the new sha
in the same change. **Until run 1 on the new page is banked, `--self-test`
aborts** with "self-test has no complete report to build from: it would
otherwise pass by measuring nothing" — the refusal that was written for exactly
this state, not a broken tool. It returns to normal with the first banked run.

Counting: **0 of 12**, no dayless runs, no carry-over. The 2026-09-03 amendment
(a run's day is the UTC date of its own `completedAt`) applies from run 1, and
every run from here carries the field, so the ≥3 UTC days clause is judged
entirely in-band for the first time. Earliest possible close from a 2026-09-05
start: **2026-09-07 UTC**.

### Run 1 on `20f09cc9…` — 2026-09-05 01:31–01:37 CST (UTC day **2026-09-04**)

`soak-run-01-candidate.json`. 40 checks, `ok: true`, the two standing
NOT_ESTABLISHED sentinels and nothing else.

**Correction to the paragraph above.** It said "earliest possible close from a
2026-09-05 start: 2026-09-07 UTC", reading the local date. The criterion counts
**UTC** days, and this run's `completedAt` is `2026-09-05T01:37:10+08:00`, which
is UTC **2026-09-04**. With ≥2 runs on each of 09-04, 09-05 and 09-06 the
earliest close is **2026-09-06 UTC**. The earlier sentence is left in place per
the append-only rule; this is what supersedes it.

**Read this before the next run.** Run 1 was taken twice. The first attempt was
clean, `ok: true`, and measured the **wrong page**: `run_e2_c_product_path.py`
builds its mirror from `dist/`, and `dist/e2-editor-app.js` was still the
2026-09-03 copy, carrying neither the 087 nor the 088 fix. It self-reported
`pageSha256: 3dfdcfef…` and this bank's `page-sha` clause would have refused it.
`make dist/e2-editor-app.js` fixes it; finding 090 records the gap and that
nothing compares the two sources. **A run taken without that copy being current
is a run on the incumbent page wearing the candidate's name.**

### Run 2 on `20f09cc9…` — 2026-09-05 01:53–01:59 CST (UTC day **2026-09-04**)

`soak-run-02-candidate.json`. 40 checks, `ok: true`, the two standing
NOT_ESTABLISHED sentinels and nothing else. `dist/e2-editor-app.js` was checked
against `web/` before the run and was already the same bytes
(`5aeae0e1…`), per finding 090.

UTC day 2026-09-04 now carries **2 runs** and satisfies the ≥2 clause. Two UTC
days remain to be earned, and ten runs.
