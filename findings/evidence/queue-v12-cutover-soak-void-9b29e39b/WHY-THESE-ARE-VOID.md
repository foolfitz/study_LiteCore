# Six clean runs on page `9b29e39b…`, void twice over: the page moved and the predicate moved

Runs 03–08 of the cutover soak, all clean, all taken on candidate profile
`e2-editor-v12` and candidate page
`9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`, served
shell `cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`
(generation v47, the cutover generation), taken 2026-09-07 local time between
07:19 and 16:02 CST.

They are **void for the count and retained untouched**, the same disposition
the seven runs in `../queue-v12-cutover-soak-void-3dfdcfef/`, the ten in
`../queue-v12-cutover-soak-void-20f09cc9/`, the two in
`../queue-v12-cutover-soak-void-pre-r1/` and the five unsplit-v11 runs in
`../queue-v11-cutover-soak-not-started/` received before them.

Nothing about them was wrong. Every one is `ok: true`, `complete: true`,
38 PASS / 2 NOT_ESTABLISHED with the fixed NE pair and no FAIL, each reconciled
`ok: true` as `candidate-cutover` on `e2-editor-v12`:

| run | `completedAt` (local) | UTC day | composition | run `ok` |
|---|---|---|---|---|
| `soak-run-03-candidate.json` | 2026-09-07T07:19:35+08:00 | 2026-09-**06** | 38 PASS / 2 NE | true |
| `soak-run-04-candidate.json` | 2026-09-07T08:55:57+08:00 | 2026-09-07 | 38 PASS / 2 NE | true |
| `soak-run-05-candidate.json` | 2026-09-07T09:03:43+08:00 | 2026-09-07 | 38 PASS / 2 NE | true |
| `soak-run-06-candidate.json` | 2026-09-07T15:04:45+08:00 | 2026-09-07 | 38 PASS / 2 NE | true |
| `soak-run-07-candidate.json` | 2026-09-07T15:54:45+08:00 | 2026-09-07 | 38 PASS / 2 NE | true |
| `soak-run-08-candidate.json` | 2026-09-07T16:02:18+08:00 | 2026-09-07 | 38 PASS / 2 NE | true |

(Run 03's UTC day is 2026-09-**06**; only 04–08 fall on UTC 2026-09-07. The
distinction mattered for the calendar clause and is preserved here rather than
rounded into "the six 09-07 runs".)

## What voided them — two causes, and both would have been enough

**1. The count was zeroed by adjudication, before either mechanism fired.** On
2026-09-08 the owner ruled **D-c** on finding 093 (`ed1ea02a`): fix the
accessibility projection regardless of how it is classified, accepting D-b's
written cost — *the soak count restarts at zero*. Finding 093 records
explicitly that **the restart was not mechanically forced**: finding 094 means
these six would have survived an edit to `web/e2-editor.html` untouched. The
count went to zero because the adjudication says the change counts, not because
a guard saw it. The two mechanical causes below arrived afterwards and made the
same answer checkable.

**2. The page moved.** The owner ran step 4 of
`handoff/RUNBOOK-operator-093-engine-geometry.md` on 2026-09-09 and the relink
minted **`e2-editor-v13`** (`probe.wasm` `0fe25650bec1bac5…` — a real link, not
a repackage: v10 and v12 both carry `4ec1e389aaab3b03`). A candidate page
pinning a different wasm hash and pointing at a different worker is different
bytes, so `candidateCutover.pageSha256` moved
`9b29e39b…` → `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a`,
and the page is the shell bundle's own entrypoint, so
`servedShell.servedSha256` moved with it,
`cf7f9233…` → `ea69984c8ad25c4048de0313a49f3db9e7c4ab3fc6ded0f4cebc84a1a5b0fe52`.
This is §6.1 of the runbook, in the words it was written in: *five of the six
pins fall at once.*

**3. The clean-run predicate moved.** The forty-first check
`the-projection-is-placed-where-the-document-is` landed on 2026-09-08 under the
amendment of `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` (2026-09-08,
append-only), which states its own count semantics: the clean composition
becomes **39 PASS / 2 NE**, NE set unchanged. These six are 38 PASS / 2 NE.
They were measured against a net that had forty checks in it.

Either cause alone is disqualifying, and the judge says so independently. Each
of the six fails on exactly four clauses, measured with them still in the
directory (`JUDGE-OUTPUT-before-the-move.txt`):

    reconciled-profile, pass-count, page-sha, one-served-shell

`run-ok`, `run-complete`, `reconciled-ok`, `reconciled-as-candidate`,
`ne-set-exact` are all still **true** on every one of them. That is the shape
of a run superseded rather than a run that failed.

## Why they had to leave the counting directory

`tools/check_soak_bank.py` enumerates by glob, not by list. Its clean clauses
are

    "every-run-clean": len(clean) == len(runs) and bool(runs),
    "one-page-sha":    len(shas) == 1 and shas[0] == expect_sha,

taken over every `soak-run-*.json` in the bank directory. Left in place, both
are false forever — no number of new clean runs can make `every-run-clean` true
while a superseded run sits in the glob, and the twelfth would have landed on
`cleanRuns: 12, totalRuns: 18, every-run-clean: false`. §6.3 of the runbook
names this in advance: *"the voided runs must physically leave the counting
directory, otherwise `every-run-clean` is false forever."*

## Why the move came AFTER the first new clean run, and not before

`--self-test` builds its day-clause fixtures and its two served-shell fixtures
from **live bank reports the judge itself calls clean** (`clean_sources()`), and
raises `SystemExit` when there are none rather than passing by measuring
nothing. So the order is forced, and it was measured rather than reasoned
about:

* constants moved, no new run banked → `check_soak_bank.py --self-test` exits 1
  with `self-test has no clean report to build from: it would otherwise pass by
  measuring nothing`;
* run 09 banked → self-test back to 12 red cases red and the green control
  green;
* these six moved out → self-test still green, because run 09 is the clean
  source it now builds from.

Emptying the bank first would have left the tree with a judge that could not
prove it can say no. The 2026-09-08 amendment predicted exactly this ("So the
void move must come after the first post-relink clean run is banked, not before
it"), and the sequence above is the measurement, not a re-narration of the
prediction.

Measured immediately before this move: `cleanRuns: 1, totalRuns: 7,
every-run-clean: false, one-page-sha: false, ok: false`.
Measured immediately after: `cleanRuns: 1, totalRuns: 1, every-run-clean: true,
one-page-sha: true, count-reached: false, day-spread: false, ok: false`.
Both outputs, and both `--self-test` runs, are recorded verbatim beside this
file in `JUDGE-OUTPUT-before-the-move.txt` and
`JUDGE-OUTPUT-after-the-move.txt`. The judge was not modified by this move; no
criterion text was relaxed; nothing was re-judged; nothing was deleted.

## The numbering gap in the bank is deliberate

`../queue-v12-cutover-soak/` now holds `soak-run-09-candidate.json` and nothing
else in the `soak-run-*` namespace. **The surviving run is not renumbered to
01.** Its name is cited by its own RUNS.md section and by its reconciliation in
`../queue-v12-cutover-soak-checklists/check-usable-editor-run09.json`, and the
bank has never renumbered: 01/02 left for `-void-pre-r1` and 03–08 stayed 03–08.
The next run is 10. The gap *is* the record that a restart happened here, and a
bank whose file names are edited after the fact is what the membership rule and
the `interrupted-2026-08-29-0050-partial.json` rename exist to prevent.

## What did NOT move, and why each one stayed

**The six `check_usable_editor.py` reconciliations
(`check-usable-editor-run03.json` … `run08.json`) stay in
`../queue-v12-cutover-soak-checklists/`.** Nothing globs that directory — it
exists precisely because `check_soak_bank.py` refused a reconciliation banked
inside the bank as an unclassified file (2026-09-07 08:50 CST) — so their
location changes no clause and the move is not mechanically forced, which means
it has to be argued rather than assumed. They are cited in place by the RUNS.md
sections for runs 03–08, which are append-only and stay where they are; and the
numbering never repeats, so no future `check-usable-editor-run03.json` can
collide with the one already there. This is the same reasoning
`-void-pre-r1` applied to the `VERDICT-soak-*` family, reaching the same answer
for a different file class.

**The three `diagnostic-*.json` stay in the bank.** They are gate condition 2's
evidence, not condition 1's, and `check_soak_bank.py` lists them under
`conditionTwoFiles_NOT_JUDGED_HERE` without judging them. They are void too —
`check_caret_diagnostics.py`'s own identity term pins them to page `9b29e39b…`
and that constant has moved to the new page, so condition 2 has to be re-earned
per §6.2 of the runbook — but that is condition 2's business and its judge globs
them out of this directory, so moving them would make the re-take permanently
red. This is exactly the disposition the 2026-09-05 void section of RUNS.md
already recorded for the same file class, and it is unchanged here.

**The four `VERDICT-*.json` and `SELFTEST-2026-09-07-run03.txt` stay.** A
`VERDICT-soak-*.json` is not a verdict *on a run*; it is the judge's census **of
the bank directory** and says so in its own `bank` field, so filing one inside a
void lineage would misdescribe it. `VERDICT-condition-2.json` is condition 2's
verdict and follows condition 2's evidence, which is staying.
`SELFTEST-2026-09-07-run03.txt` is not `*.json` and is invisible to the glob. Same convention
as `-void-pre-r1`, same answer, and for `VERDICT-condition-2.json` the opposite
answer to `-void-3dfdcfef` / `-void-20f09cc9` only because those two moved the
diagnostics and this one does not.

## Why they are kept

Evidence in this tree is not destroyed. These six are the only record of the
product path measured clean, six times, on the page the 088-residue fix and the
R-1 amendment produced — the run of clean days that made it possible to say the
gate's remaining cost was calendar rather than defects. They are also the
measurement that condition 1's clauses were satisfiable at all under the amended
region check. Nothing about them was wrong; the artifact they measured has been
replaced, and the net they were measured against has one more check in it.

## Authority

* `findings/093-the-accessibility-projection-sits-at-the-bottom-of-the-paper-because-it-never-got-069s-fix.md`, section 「擁有者的裁定：B」 and section 「步驟 5」
  (2026-09-08 / 2026-09-09, append-only) — the fix shape, the relink, and the
  candidate identity these runs no longer carry.
* The owner's **D-c** ruling on finding 093 (`ed1ea02a`, 2026-09-08) — the
  count restarts at zero, by adjudication, with the restart explicitly not
  mechanically forced.
* `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, amendment of 2026-09-08
  ("a forty-first check"), sections "Count semantics — stated, not implied" and
  "The re-freeze this obliges, and its ORDER" — 38 PASS / 2 NE → 39 PASS / 2 NE,
  the constants that move together, and the ordering constraint above.
* `handoff/RUNBOOK-operator-093-engine-geometry.md` §6.1 (the identities that
  move), §6.2 (the evidence that dies), §6.3 (why a voided run must physically
  leave the directory), and the 2026-09-09 correction appended to it (§5 step
  5.3's repoint is the cutover and must not be performed).
