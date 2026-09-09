# 096's forty-second check, on the product path

Two runs of `tools/run_e2_c_product_path.py` on 2026-09-09, both against the
**shipping** profile (`e2-editor-v8`, the page as it ships) and shell generation
**v51** (`servedSha256 == declaredSha256 == 2ffbec81…`, `differingPaths: []` in
the plain run).

| file | run | composition |
| --- | --- | --- |
| `plain-e2-editor-v8.json` | no mutation | **40 PASS / 2 NE**, `ok: true` |
| `mutate-boundary-move-takes-no-checkpoint.json` | `--mutate boundary-move-takes-no-checkpoint` | **39 PASS / 1 FAIL / 2 NE** |

The FAIL is `a-boundary-arrow-press-does-not-cost-the-work` and nothing else.
The NE pair is the registered one (`notice-action-recovers-the-session`,
`a-refused-action-is-reported-and-changes-nothing`), unchanged in both runs.

## What each run measured on the check

**Plain.** `#s-checkpoint` `無` before the arrow key and `有（r1）` after it;
the press was NOT answered (`stateAfterPress: recoverable-error`); the notice
offered `rescue: "checkpoint"`; pressing the product's own button returned a
ready session and the product's own save produced an ODT **containing** the
typed sentinel. `clausesExercised: ["B1","B3","B4"]` — B2 absent, because no
artifact in this tree answers the press.

**Mutated.** Same seven steps, two lines of
`editor-shell-v2/narrow-editor-v2-session.js` removed. `#s-checkpoint` `無`
before AND after; `rescue: "none"`; the notice reproduces the owner's sentence
character for character; pressing 「重新開啟」 returned a ready session and a
document that does **not** contain what was typed. `servedShell.differingPaths`
names the mutated file, so the run's own honesty flag shows the shell moved.

## Two earlier runs are not banked here, and that is deliberate

Four product-path runs were taken this evening. The first two were on
intermediate versions of the check — before the `defaultPrevented` control was
added, and before the arm pressed the recovery notice on a failed B1 — and they
are superseded rather than evidence: a report is only evidence about the bytes
that produced it. What the second of them showed and what it forced is recorded
in the finding: with the mutation, the arm used to leave the session dead, so
the liveness guard stopped the run and the round reported a STOPPED run instead
of one red check. Pressing the notice in both worlds fixed that and made the
arm's correctness independent of being last in the file.
