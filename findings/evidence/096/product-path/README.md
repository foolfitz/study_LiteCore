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

---

# Append (2026-09-09, after the owner's link): the same check on `e2-editor-v14`

`plain-e2-editor-v14.json` — `tools/run_e2_c_product_path.py --profile
e2-editor-v14`, no mutation, shell generation **v51**
(`differingPaths: ["web/e2-editor-app.js"]`, `differsOnlyInTheEntrypoint: true`
— the repointed page and nothing else).

**42 checks: 40 PASS / 2 NE / 0 FAIL, `ok: true`.** The NE pair is unchanged.
The composition is the one the amendment registered.

`a-boundary-arrow-press-does-not-cost-the-work` **PASS**, and for the first time
`clausesExercised` contains **B2**: `["B1", "B3", "B2"]`. The press was answered
(`theEngineAnsweredThePress: true`, `stateAfterPress: ready`), the page took the
key (`takenByThePage: [true]`), the revision stood at 1 before and after it, and
`#s-checkpoint` went `無` → `有（r1）`.

**B4 is not exercised on this profile.** The session never dies, so the recovery
notice is never pressed and "what comes back contains what was typed" is not
measured here. On the shipping profile the check runs B1/B3/B4; on v14 it runs
B1/B3/B2. No single run covers all four.

Full reading: `findings/evidence/096/RESULT-after-the-link.md`.

---

# Append (2026-09-10): B4 gets a second inducer — **no run in this directory yet**

The gap the v14 run above measured — `clausesExercised` `["B1","B3","B2"]` on the
fixed profile against `["B1","B3","B4"]` on the shipping one, so **no single run
covers all four clauses and the silent one is B4** — was put to the owner, who
ruled on 2026-09-10 for a **second inducer** rather than for writing B4 off as
shipping-side only.

What landed in the tree today is code and text, **not a measurement**:

* `handoff/tasks/TASK-2026-09-10-096-b4-second-inducer.md` — the protocol,
  committed before the runner was edited: the criteria, the three red cases with
  the field values that constitute red, the §3 decision and its reasoning, four
  named limits, and the default conclusions.
* the gate amendment of 2026-09-10 in
  `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` — append-only, and it
  names the bullet of the 2026-09-09 amendment it supersedes.
* `tools/run_e2_c_product_path.py` — on a run where the press is **answered**,
  after B2: `induce_worker_failure`, wait for the dead state, **read the
  declaration before pressing it**, press the product's own notice, save through
  the product's own button, and require the saved ODT to carry the sentinel. The
  declared checkpoint must name `r{revisionAfterTyping}`, by the same predicate
  B3 applies to `checkpointAfterTheKey`. The verdict gains `b4Inducer`
  (`"boundary-press"` / `"worker-failure"` / `null`).
* three `MUTATIONS` entries: `boundary-move-takes-no-checkpoint` (existing, which
  must now red B4 as well as B3), `worker-crash-throws-the-checkpoint-away` and
  `worker-crash-is-never-noticed`.

**The dying branch is unchanged** beyond one added cell. Its save-and-compare
tail was lifted into `press_the_notice_and_save` so both inducers ask one
question; the lift was proved output-identical by running the pre-lift code from
`ef93c4c4` beside it against the same stubs, in both worlds (recovery works /
recovery does not), and comparing `json.dumps` of the `boundary` dict, so key
order counted. Identical in both. The only addition in that branch is
`b4Inducer: "boundary-press"`; `plain-e2-editor-v8.json` stays the control.

## What would falsify the change, stated before the runs

T8b runs the three red cases once each on `--profile e2-editor-v14`, then three
plain v14 runs and one on v8. The change is in force only if:

* each red case reds `a-boundary-arrow-press-does-not-cost-the-work` **and
  nothing else**, with the cells the protocol's §4 pins — in particular
  `worker-crash-is-never-noticed` must render as `B4: null`, `clausesExercised`
  without `B4`, `outcome: "FAIL"` (**not** `NOT_ESTABLISHED`);
* the plain v14 runs show `clausesExercised` containing all four clauses,
  `b4Inducer: "worker-failure"` 3/3, `stateAfterFallback: "recoverable-error"`,
  `declaredCheckpointAfterFallback: "有（r1）"`,
  `checkpointOnOfferIsThisGestures: true`, `workCameBack: true`, `B4: true`, and
  a composition unchanged at 40 PASS / 2 NE;
* the v8 run reproduces `["B1","B3","B4"]` with the values already banked here.

**If `induce_worker_failure` does not fire on v14, that is a result to bank, not
a task failure** — and by design the run says so in red rather than in a green
that cannot be quoted for B4.

## What was NOT done here

No browser was started, no profile byte moved, no `make` target other than
`test-e2-c-static` (exit 0, 108 unit tests) was run, and
`build_cutover_page.py --write` was not run. Before landing, the four B4
renderings were driven through stubs with no browser — `B4` `true` / `false` /
`null` / `null`, the last two with `clausesExercised` omitting `B4` and
`ok: false` — which tests the **verdict composition, not the product**, and is
not evidence about any artifact.
