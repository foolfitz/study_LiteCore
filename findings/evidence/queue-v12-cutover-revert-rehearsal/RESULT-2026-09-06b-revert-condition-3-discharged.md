# Revert condition 3, discharged on `20f09cc9…`: the post-revert run reconciles

Ruling **E-3** of the 2026-09-06 adjudication. The 2026-09-06 take (this
directory's earlier `RESULT-…-with-step-3.md`) satisfied step 3 but left the
post-revert reconciliation failing, because the state the revert returns to was
undeclared. **E-1 froze v44 for that state**; this is the re-run that shows it
closed.

Script: `rehearse_revert_v45.sh` — `rehearse_revert.sh` with `NEWGEN` = v45 and
nothing else changed, `trap` intact. Transcript: `rerun-2026-09-06.log`.

## The criterion, term by term

| E-3 requires, on the **post-revert** run | measured |
|---|---|
| `check_usable_editor` `ok` | **true** |
| `reconciledFor.kind` | **`shipped-page`** |
| `servedShell.bundle` | **`e2/editor-shell-v2-bundle-v44.json`** |
| `declaredSha256 == servedSha256` | **true**, `f89d7bb9d1438ef2…` |
| `servedShell.differingPaths` | **`[]`** |

`restore()` runs `git checkout -- tools/build_e2_c_shell_bundle.py`, so the
post-revert run could only declare v44 because the E-1 freeze was **committed**.
That is what makes this a measurement of the freeze rather than of the script.

## The cutover half, and E-4's positive control

The post-cutover run: 38 PASS / 2 NE, `candidateCutover: null`, bundle
**v45**, `declaredSha256 == servedSha256 == 78c2368403e16af1…`,
`differingPaths: []`, reconciled `ok: true`.

That digest is the value ruling E-4 pins as `one-served-shell`. So this run is
the **positive control for that clause**: the generation the cutover actually
freezes declares exactly the digest the twelve banked runs served. E-4's record
obligation (R6) — "the cutover record quotes v45's `bundleSha256` and E-4's
pinned value side by side, equal" — is satisfiable, and satisfied here.

## The post-revert run was 37 PASS / 3 NE, and that is registered, not new

The third NOT_ESTABLISHED is `clear-format-removes-every-inline-format`. The
plan already registers it (lines 100-107): *"abstained once on a shipped-profile
run and once on the post-cutover rehearsal run — one occurrence on each side, so
it is an intermittent that predates this work and belongs to neither profile."*
This is a **third occurrence, on the shipped side**, making the tally 2 shipped /
1 post-cutover.

It does not touch the count: this is not a counted run — it carries no
`candidateCutover` and `check_soak_bank.py` never sees it. It does not affect
E-3 either, whose terms are the five reconciliation values above and not the
composition; `check_usable_editor` returned `ok: true` on 37/3 because the
shipped-page predicate is not the soak's clean-run predicate.

**What it does do is raise the prior.** The plan's own arithmetic — "a defect
that fires in a quarter of runs survives twelve of them with probability ~3%" —
is about the counted runs, and this check has now abstained three times across
this work's shipped-page runs while never abstaining in any of the ten banked
candidate runs. Recorded so the asymmetry is visible if it ever lands inside the
soak, where it restarts the clock by the rule already in force.

## The tree afterwards

`web/` and `dist/` both `5aeae0e1…`, `MANIFEST` v44, `e2/…-v45.json` deleted,
`git status` empty — verified by the explicit revert and again by the trap on
exit.

## Two kills first, and they are banked beside this

Attempts 1 and 2 were killed by the harness for low memory, both during the
first net run after the cutover. The `trap` restored the tree both times; see
`THE-TRAP-WAS-TESTED-FOR-REAL.md`, `rerun-KILLED-attempt1.log` and
`rerun-KILLED-attempt2.log`. The kernel's own metrics showed no memory pressure
at any point (`si/so` zero, PSI `some avg10=0.00`, `MemAvailable` 17-19 GB), so
the failures were a harness threshold rather than a machine limit — which is why
a third attempt was reasonable rather than stubborn.
