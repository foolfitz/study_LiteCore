# Handoff, 2026-09-28 (b) — 099 is reproduced in both modes on the real engine, and 098 is measured on the shipped shell

Entry points, in order: this file, then `findings/099-*.md` and `findings/098-*.md`
(the sections dated 2026-09-28 later in the day), then `findings/evidence/099/README.md`
and section 5 of `findings/evidence/098/README.md`.
`handoff/HANDOFF-2026-09-28-098-and-099-are-fixed-on-shell-v52.md` is the previous
entry point; its gate section still holds and its open list is superseded below.

Tree clean after this file's commit, nothing pushed. Commits this round: `975900f1`,
`29844cbb`, and this handoff. **No product byte, engine, profile, shell generation or
page changed** — every addition is a probe, its reports and finding text.

## What was done — the two measurable items on the open list

The previous open list had five items; three are owner- or cutover-bound. The other two
were measurement gaps, and both are closed.

### Item 3: 099 at browser level — both modes reproduced

| mode | probe | profile | prefix (v51) | a-only (098 half only) | landed | premise measured |
| --- | --- | --- | --- | --- | --- | --- |
| within-Worker | `probe_099_within_worker_review_path.py` | v8 | lost 3/3 | lost 3/3 | kept 3/3 | review path leaves revision 2→2, 18/18 |
| within-Worker | same, `--profile e2-editor-v14` | v14 | lost 3/3 | lost 3/3 | kept 3/3 | 2→2, 9/9 |
| cross-Worker | `probe_099_cross_worker_revision_coincidence.py` | v8 | lost 3/3 | lost 3/3 | kept 3/3 | revision 0 after recovery, 18/18 |

Both probes use only the product's controls, a fresh browser per attempt, criteria
written into the docstring before the first run, a positive control that fixes WHICH
checkpoint was restored, and three arms whose served session files differ only in two
exact-text pairs (`a-only` vs `landed` is the one comparison that is 099's fix).

- The within-Worker inducer is finding 046's residual: 「• 項目符號」 on an empty
  paragraph takes the review path from the product's buttons, on both profiles.
- The cross-Worker probe is the finding's own trigger sentence: death one by
  `induce_worker_failure`, then the new Worker's revision is made to equal the old
  checkpoint's, and the skipped press is the v8 boundary press that causes death two.
- In every arm the checkpoint label reads the same before and after the press under
  test (有（r2） / 有（r1）): the new checkpoint carries the same revision. The latency is
  the second witness (0.46 s with the save, 0.15 s without).
- **Named limit left**: cross-Worker is not reproduced on v14 — half A answers the
  boundary press, so death two would need a second worker failure, and that inducer
  works once per browser. The guard is profile-independent session code with unit
  coverage.

### Item 5: 098 on the shipped shell v48 — the inference holds

`findings/evidence/098/probe_098_v48_arrow_then_drag.py` rebuilds v48 from `2d319677`
file by file and refuses to measure unless the served bundle digest equals the declared
`ecfb6866…` (it did). v48: one ArrowRight then a drag on an untouched document banks
有（r0） 3/3; drag alone 無 3/3; type-then-drag 有（r1） 3/3. v52: the same three give
無 / 無 / 有（r1）. So today's shipped product banks a checkpoint of the opened bytes
after an arrow key and a drag — not data loss, a misleading label and one redundant
save. v52 fixes it through the base class's selection checkpoint as well as half C.

## Instrument lessons this round (all written into the evidence)

1. **`induce_worker_failure` works once per browser.** The second call after a
   navigation found no worker, 6 of 6 (within-Worker run 1, kept). Mechanism not
   isolated. The product-path runner has two call sites and fires only one per run today;
   if it ever needs both, check 42 goes loudly red (`B4: null`, its accepted cost), not
   silently green. Not changed.
2. **A positive control I wrote was wrong** (cross-Worker run 1, kept): the click after
   recovery is derived from ink that the first mark had lengthened, so the second mark
   was typed *inside* the first — `E1-FF099GENTWO099GENONEMULTI-START` — and "is MARK1
   in the text" voided the landed arm 3/3. Corrected (look for MARK1 with MARK2 removed),
   the reason written beside the predicate, run 2 taken with the same recipe. It was
   caught only because the report stores the paragraphs the classifier read.
3. **One ArrowUp on the first line is not a boundary press**: it moves the caret to the
   start of the document and is answered; the second one wedges. check 42's loop already
   knew this; my first draft did not.

## Observations, registered and not pursued

- **v14 takes the multi-block route on the blank-line bullet**, the same as v8 — not the
  empty-selection route finding 083 measured on v10's accessibility core. The
  product-path runner's own cell has said `multi-block` on v14 since at least 09-10, so
  it is not this fixture. Which link changed the core's answer is unmeasured; 083's fix
  is still right for the shape it handles, v14 just does not exercise it on this cell.
- **The notice wording (open item 1) was seen in every recovery of every probe**: after a
  worker crash or a boundary wedge, with a checkpoint banked by an arrow key, the notice
  said 「這一步可能已經改到文件，而且無法驗證。回到選取手勢前的檢查點。」 Nothing new —
  that is 061's shape, the owner's ruling stands.

## Open list now

1. **The wrong-gesture wording (061's shape)** — owner's ruling, unchanged. Cheapest in
   the next page move.
2. **094 / 097** — bind / revisit at cutover, unchanged.
3. **099 cross-Worker on v14** — named limit (above). Not worth an inducer of its own
   unless the guard changes.
4. **Work item, not a gate criterion**: a product-path check that a caret move banks
   nothing on a clean document (fable ruled against adding it now). The seeds are now
   two probes: `probe_098_a_caret_move_banks_a_checkpoint.py` and
   `probe_098_v48_arrow_then_drag.py`.
5. ~~v48 inference~~ — measured, holds.

## The gate

Unchanged: soak 0 of 12, at the end of development, full run on the final identity
before any cutover, floor of three calendar days; T4 re-earned on the final identity, the
owner's evening. The shipping page still points at v8 on shell v48. **No cutover has
been performed.**

## What is next — the owner's call

Nothing on the open list can move without the owner. The choices, with my inclination:

- **A. Start the cutover path now** (recommended if no more development is planned
  before shipping v14): fold item 1's wording into the page, freeze the final identity
  (v14 + shell v52 or its successor + the page), bind 094's HTML, then T4 (owner's
  evening) and the 12-run soak over ≥ 3 UTC days. The shipped v48 carries 098 today;
  cutover is the only way v52 reaches users.
- **B. More development first** (the soak waits either way): the roadmap's next
  unstarted gate is M3's gate 0, COOP/COEP inside Nextcloud (`research/ROADMAP-2026-08-20-milestones.md`
  §5.1) — it decides what the app looks like. The only measurement on record is a grep
  of Nextcloud 31's PHP finding no COOP/COEP at all
  (`research/RESEARCH-2026-08-20-product-route-and-competitors.md`); the roadmap marks
  all three candidate workarounds as unverified.
- **C. Close the remaining instrument debt**: isolate why the worker-failure inducer
  works once per browser and make it re-armable. Small, but only worth it if a future
  check needs two inductions.
