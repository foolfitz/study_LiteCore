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
