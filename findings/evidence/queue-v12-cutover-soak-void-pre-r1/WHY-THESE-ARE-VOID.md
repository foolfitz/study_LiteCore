# Two banked FAIL runs, taken under a criterion that no longer exists

Runs 1 and 2 of the `e2-editor-v12` cutover soak on the final page
`9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`, served
shell `cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`
(generation v47, the cutover generation), taken 2026-09-07 01:42–01:55 CST
(UTC day 2026-09-06) as task T2 of
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`.

They are **void for the count and retained untouched**, the same disposition
the seven runs in `../queue-v12-cutover-soak-void-3dfdcfef/`, the ten in
`../queue-v12-cutover-soak-void-20f09cc9/` and the five unsplit-v11 runs in
`../queue-v11-cutover-soak-not-started/` received before them.

Unlike all three of those, **these two are not void because the page moved.**
Their page identity is the current one — the same `9b29e39b…` every surviving
run in `../queue-v12-cutover-soak/` carries. What moved underneath them is the
criterion.

## What voided them

On 2026-09-07 the owner ruled disposition **A** on R-1 (finding 092): the
product check `the-document-region-says-why-it-is-empty` is amended to verify
the claim — *there is something to read* — rather than the proxy of one DOM
node's text, because finding 088's fix and that check's old oracle contradict
by design. The plan's section "R-1 = A, by the owner" (2026-09-07,
append-only) states the consequence in its own words:

> This changes the clean-run predicate, so the count restarts — it is at 0;
> runs 1–2 stay banked FAIL under the old wording and are not re-judged.

That is the whole of it. These two runs measured the product honestly against
the wording in force at 01:48 CST; the wording was replaced at ~07:00 CST the
same day; and a run judged under a superseded predicate cannot be counted
alongside runs judged under the current one, in either direction.

## Why they had to leave the counting directory

`tools/check_soak_bank.py` enumerates by glob, not by list. Its clean clause is

    "every-run-clean": len(clean) == len(runs) and bool(runs),

taken over every `soak-run-*.json` in the bank directory. "Not re-judged" and
"the count restarts at 0" are consistent **only** if the superseded lineage
leaves the glob. Left in place, the bank would have read
`cleanRuns: 12, totalRuns: 14, every-run-clean: false` on the day the twelfth
clean run landed — a gate standing on the finish line with a red judge, and a
condition 1 that could then only be reported by the drafting party narrating a
count around the judge's verdict.

Measured immediately before this move:
`cleanRuns: 6, totalRuns: 8, every-run-clean: false, ok: false`.
Measured immediately after:
`cleanRuns: 6, totalRuns: 6, every-run-clean: true, count-reached: false,
day-spread: false, ok: false`. Both outputs, and both `--self-test` runs, are
recorded verbatim beside this file in `JUDGE-OUTPUT-before-the-move.txt` and
`JUDGE-OUTPUT-after-the-move.txt`. The judge was not modified; no criterion
text was relaxed; nothing was re-judged; nothing was deleted.

## Authority

* `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, section
  **"R-1 = A, by the owner"** (2026-09-07, append-only) — the amendment, the
  restart, and the ruling that these two stay banked FAIL.
* The same document, section **"Two decisions by the owner, 2026-09-07
  evening"**, sub-section **"P-0 — the bank cannot report `ok: true` while runs
  01 and 02 sit in it"** — the owner's decision **A**: move them here, with a
  `WHY-THESE-ARE-VOID.md`, nothing deleted, nothing re-judged, the judge
  unmodified, no criterion text relaxed. Its stated default if it were never
  done: *"condition 1 could only be reported by the drafting party narrating a
  count — the exact failure W-4 exists to remove."*
* `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, the amendment of
  2026-09-07 that rewrote the check's oracle and registered the restart under
  `AGENTS.md` §9's four conditions.

## The FAIL is real, and it is not being hidden

Both runs recorded `37 PASS / 2 NOT_ESTABLISHED / 1 FAIL`, `ok: false`,
`complete: true`. The failing check is the same on both, with the same payload:

| run | `completedAt` | UTC day | failing check | observed |
|---|---|---|---|---|
| `soak-run-01-candidate.json` | 2026-09-07T01:48:32+08:00 | 2026-09-06 | `the-document-region-says-why-it-is-empty` | `{"present": true, "text": "", "reason": "paragraph", "offers": "1"}` |
| `soak-run-02-candidate.json` | 2026-09-07T01:55:35+08:00 | 2026-09-06 | `the-document-region-says-why-it-is-empty` | `{"present": true, "text": "", "reason": "paragraph", "offers": "1"}` |

That payload is what forced the amendment. It is the region deferring to the
structure channel — finding 088's *one paragraph, one voice* — read by a check
whose oracle had not learned that the silence is deliberate and marked
(`data-deferred-to-structure="1"`). The runs are the measurement that made
finding 092 possible; moving them out of the count does not retract a single
byte of them, and this file exists so that the count's drop is legible rather
than a directory that quietly shrank.

## The numbering gap in the bank is deliberate

`../queue-v12-cutover-soak/` now holds `soak-run-03-candidate.json` through
`soak-run-08-candidate.json` and no 01 or 02. **The surviving runs are not
renumbered.** Each banked report's name is cited by its own RUNS.md section, by
its `check_usable_editor.py` reconciliation in
`../queue-v12-cutover-soak-checklists/check-usable-editor-runNN.json`, by three
`VERDICT-soak-*.json` files, and by the plan's T3 ledger. Renumbering would
rewrite evidence to make a sequence look tidy — and a bank whose file names
have been edited after the fact is exactly the thing the membership rule and
the `interrupted-2026-08-29-0050-partial.json` rename exist to prevent. The gap
*is* the record that a restart happened here.

## Two things that did NOT move, and why

**No `check_usable_editor.py` output exists for runs 01 and 02.** Checked, not
assumed: `../queue-v12-cutover-soak-checklists/` holds `run03` through `run08`
only, and the git history of that path shows the first such file created for
run 03 (`feb11292`, written into the bank and moved to the sibling directory by
`94cf4be0` when the judge refused it as unclassified). The convention of saving
the reconciliation to a file began after these two runs; T2 ran
`check_usable_editor.py --report` on both and read its stdout, quoted in
RUNS.md. There is nothing to move.

**The three `VERDICT-soak-2026-09-07*.json` files stay in the bank.** Two of
them (`VERDICT-soak-2026-09-07.json`, `cleanRuns: 0, totalRuns: 2`, and
`VERDICT-soak-2026-09-07-r2-correction.json`, same) judge exactly these two
runs; the third (`VERDICT-soak-2026-09-07-run03.json`, `cleanRuns: 1,
totalRuns: 3`) judges them together with the surviving run 03. They stay, for
three reasons:

1. `check_soak_bank.py` classifies `VERDICT-*` as a third class, listed under
   `verdictFiles_NOT_EVIDENCE` and **never counted** — so their location
   changes no clause, before or after. This move is not mechanically forced,
   which means it has to be argued rather than assumed.
2. A `VERDICT-soak-*.json` is not a verdict *on a run*; it is the judge's
   census **of the bank directory**, and it says so in its own `bank` field
   (`findings/evidence/queue-v12-cutover-soak`). Filing a census of the live
   bank inside a void lineage would misdescribe it. What it records — that on
   2026-09-07 the bank stood at `cleanRuns: 0, totalRuns: 2` — is the live
   bank's own history, and RUNS.md cites it in place ("full record in
   `VERDICT-soak-2026-09-07.json`") in an append-only ledger.
3. Splitting the family would be arbitrary: `-run03` covers a surviving run as
   well, so a rule that moved verdicts with their subjects would have to move
   two of three and leave one behind.

This is a deliberate departure from the `-void-3dfdcfef` and `-void-20f09cc9`
precedents, both of which *did* take a `VERDICT-*` file with them. Those two
are distinguishable and the distinction is the reason: the file they took was
`VERDICT-condition-2.json`, the verdict of `check_caret_diagnostics.py` over
`diagnostic-*.json` reports — and that judge **globs `diagnostic-*.json` out of
the live bank directory**, so the evidence itself had to move or the re-take
would have been permanently red. The verdict followed its own evidence out, and
was renamed `-on-<sha>` so that it would still say which page it judged. Here
the evidence being moved is `soak-run-*.json`, the verdict is a census of the
directory those runs are leaving, and nothing globs it. Same convention, a
different file class, an opposite answer — stated rather than silently taken.

## Why they are kept

Evidence in this tree is not destroyed. These two runs are the only record of
the first measurement of `the-document-region-says-why-it-is-empty` against the
088 fix family — the measurement that produced finding 092, R-1, the
amendment, and every clean run banked since. They are also the only record that
the count went to 0 for a reason other than the page moving. Nothing about them
was wrong; they were judged by a sentence that has since been replaced.
