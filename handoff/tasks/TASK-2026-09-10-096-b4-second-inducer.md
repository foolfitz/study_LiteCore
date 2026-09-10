# TASK — finding 096: give B4 a second inducer so it is reachable on a fixed profile

Pre-registered protocol for the T8a brief in
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, section "B4's coverage
gap: the owner rules A — a second inducer (2026-09-10, append-only)".

**Written and committed before the runner is edited.** Nothing below may be
edited after the first run that counts; corrections go in an appended
`## Execution record` that names what it supersedes (AGENTS.md §10).

**No build, no relink, no product byte.** The only file that changes behaviour is
`wasm_sdk_probe/tools/run_e2_c_product_path.py`. Nothing under `src/`, `sdk/`,
`web/`, `dist/`, `editor-shell*/` is edited, no `make` target other than
`test-e2-c-static` is run, and `build_cutover_page.py --write` is not run. The
browser runs are **T8b**, a separate task; T8a lands no measurement.

---

## 0. What forced this, measured rather than argued

On `e2-editor-v14` the forty-second check
(`a-boundary-arrow-press-does-not-cost-the-work`) reports

```
v14 (fixed)     clausesExercised = ["B1", "B3", "B2"]
v8  (shipping)  clausesExercised = ["B1", "B3", "B4"]
```

(`findings/evidence/096/product-path/plain-e2-editor-v14.json` and
`plain-e2-editor-v8.json`). **No single run covers all four clauses, and the one
that goes silent on the fixed profile is B4** — "what comes back contains what
was typed" — which is the entire reason half C exists. The logic was sound and
was written down in advance (the 2026-09-09 gate amendment's bullet "**B4 is
exercised only while the press wedges**"): half A answers the press, so the
session never dies, so there is no notice to press.

The consequence is the one 069 already taught: fix an element and the net that
guarded it stops being driven. The two options were (a) a second inducer, or (b)
writing down that B4 is meaningful only on the shipping side. **The owner chose
(a) on 2026-09-10.**

## 1. The second inducer, and why it is not a new invention

`induce_worker_failure` (`tools/run_e2_c_product_path.py:2640`) — an uncaught
error inside the document worker, induced from outside the product over CDP
(`Target.setAutoAttach`, sent by hand on the raw websocket because
`ChromeSession.call` discards the events). No product change, no test-only
affordance, no dependency on an unfixed defect.

It is already the second inducer of `recovery-returns-what-the-product-promised`
(wired at `:8810`), which lost finding 038 on the accessibility core and was
given this one rather than an NE. **The same helper, the same argument, one more
call site.**

**What is substituted is only the killing step.** The property under test is
unchanged: the checkpoint half C took *before this arrow key* brings the typed
text back. The gesture still happens first, still banks its checkpoint, and the
checkpoint that is then restored from is required to be that one (§2.3 below).
Registered under AGENTS.md §3 as a **designed sentinel, not a hole**: on a
profile carrying A the gesture *cannot* kill the session, which is what A is for.

**Not new machinery** in the §4 sense: no product byte, no engine change, no
link. The reach of one existing check changes.

## 2. The criteria

All four clauses keep their meaning. What follows fixes the new cells and the
order they are read in, before the code exists.

### 2.1 Which inducer, recorded in the verdict

The verdict dict gains `b4Inducer`:

| value | meaning |
| --- | --- |
| `"boundary-press"` | the gesture itself killed the session (the dying branch; the shipping profile today) |
| `"worker-failure"` | the press was answered, so B4 was reached by killing the session a second way |
| `null` | no attempt was made, because the press left no usable session to kill |

### 2.2 The order of operations in the answered branch

1. B2 is measured exactly as it is today, and **B1 stays the press's verdict**
   (`usable`). The induced failure is not the press and may not be read as one.
2. Only if the press left the session `ready`: `induce_worker_failure(session)`,
   banked verbatim as `fallbackInducer` (AGENTS.md §7 — the payload, not a
   summary of it).
3. Wait up to 90 s for `recoverable-error` / `restart-required` / `expired`
   (`dead_session`, the same predicate the guard and the dying branch use);
   record `stateAfterFallback`. 90 s is a **ceiling, not an expectation**: the
   worker's `error` event reaches `DocumentSdk._handleCrash` synchronously, so
   the observed transition is milliseconds. It also bounds red case (iii)'s cost.
4. **Read the declaration BEFORE pressing** — `declaredCheckpointAfterFallback`
   (the `#s-checkpoint` text) and `noticeAfterFallback` (the notice's decision,
   `rescue`, not its wording).
5. Press the product's own notice, wait `ready`, save through the product's own
   save button, and read `content.xml` for `BOUNDARY_MARK`.

### 2.3 The checkpoint on offer must be this gesture's

`checkpointOnOfferIsThisGestures` requires `declaredCheckpointAfterFallback` to
start with 「有」 and to contain `r{revisionAfterTyping}` — the **same form B3
already uses on `checkpointAfterTheKey`**, so the two cells cannot drift apart.

Without this, B4 would go green on a checkpoint some *other* gesture banked: the
induced failure is deliberately not the gesture, so "a checkpoint exists" is no
longer evidence that the arrow key took it. If it does not name that revision,
**B4 is False** and the `why` says the checkpoint offered was not this gesture's.

### 2.4 The notice is pressed either way

Unchanged from the dying branch's own rule, and for the same reason: the arm is
inside `liveness.expecting`, whose exit probe holds it to leaving a live session.
Pressing whatever the product offers restores a usable session in both worlds
(`回到檢查點` from the checkpoint, `重新開啟` from the authority bytes) and buys
the negative half of B4 as a measurement rather than an inference.

### 2.5 The dying branch's output does not move

On the shipping profile the result must stay cell-for-cell `["B1","B3","B4"]`
with the values banked in `plain-e2-editor-v8.json`: `B1..B4`,
`clausesExercised`, `why` and every `boundary[...]` key identical. The
save-and-compare tail is shared by both branches as one helper; the dying
branch's keys, their order and their values are unchanged by construction, and
the one addition anywhere in that branch is the new `b4Inducer:
"boundary-press"` cell the brief asks for. T8b measures this as the control.

## 3. "B4 could not be exercised" is a FAIL, not a NOT_ESTABLISHED

The decision, with its reason, because §3 demands that the two registrations not
be written as one sentence.

**Decision: on a profile where the press is answered, a run that cannot exercise
B4 reports the check FAIL**, with `B4: null` (never `false`), `clausesExercised`
without `B4`, and a `why` that names which side could not deliver — the
inducer's own `why` when it did not fire, the product when it fired and the dead
state never arrived.

Why not NOT_ESTABLISHED, against the precedent's rule that NE is reserved for
"no inducer could reach the state at all":

* That sentence is **exactly the coverage gap the owner has just ruled must not
  be accepted**. On v14 this check reported **PASS** with B4 silent; demoting
  that to NE keeps the run green (`report["ok"]` ignores NE) and hides the same
  hole one notch quieter. The 2026-08-27 adjudication called that shape "a
  finding wearing an NE costume" on the very check whose inducer is reused here.
* The check is **not** unestablished: B1, B2 and B3 were driven and reported. It
  is established and short of its own requirement, which is what FAIL means.
* The preconditions that are genuinely unreachable are already NE **upstream of
  this code**: no CDP, or a profile that does not offer `move-line-up`. A
  Firefox run cannot produce this red.
* `B4: null` rather than `false` keeps the two sentences apart: the run never
  claims the work failed to come back, only that nothing asked.

**Consequence accepted in advance**: if `induce_worker_failure` stops working
for an instrument reason, this check goes red on every fixed-profile run until
somebody looks. That is the intended cost — the alternative is a green run that
cannot be quoted for B4 and does not say so.

## 4. Red cases, named before the code exists (§6)

Three, all registered in `MUTATIONS`, each run on `--profile e2-editor-v14`.
Exact field values that constitute red, so that "it went red" cannot be decided
after the fact:

### (i) `boundary-move-takes-no-checkpoint` — existing, must now red B4 as well

The two lines of half C removed. Today on v14 it reds B3 alone; after this
change it must red B3 **and** B4, which is the measurable proof that B4 is back
in reach on a fixed profile.

| field | required value |
| --- | --- |
| `checkpointBeforeTheKey` / `checkpointAfterTheKey` | `"無"` / `"無"` |
| `theEngineAnsweredThePress` | `true` |
| `fallbackInducer.fired` | `true` |
| `stateAfterFallback` | `"recoverable-error"` |
| `declaredCheckpointAfterFallback` | `"無"` |
| `noticeAfterFallback.rescue` | `"none"` |
| `checkpointOnOfferIsThisGestures` | `false` |
| `workCameBack` | `false` |
| `B3` / `B4` | `false` / `false` |
| `clausesExercised` | contains `"B4"` |
| `b4Inducer` | `"worker-failure"` |
| the run | that check FAIL, nothing else red |

### (ii) `worker-crash-throws-the-checkpoint-away` — the notice offers reopen

New. In `dist/editor-shell/editor-session.js`, the `worker-crashed` branch of
`_handleEngineEvent` discards the checkpoint before entering recovery, so the
notice offers 「重新開啟」 on a session that *had* a checkpoint. This is the
regression a reader would not otherwise believe is possible, and it touches
**only the crash path** — 038's drain path, which is what
`recovery-returns-what-the-product-promised` still uses on both profiles
(`finding038Reproduced: true`, measured on v8 and v14), is untouched.

| field | required value |
| --- | --- |
| `checkpointBeforeTheKey` / `checkpointAfterTheKey` | `"無"` / `"有（r1）"` — **B3 stays true** |
| `fallbackInducer.fired` | `true` |
| `stateAfterFallback` | `"recoverable-error"` |
| `declaredCheckpointAfterFallback` | `"無"` |
| `noticeAfterFallback.rescue` / `.label` | `"none"` / `"重新開啟"` |
| `checkpointOnOfferIsThisGestures` | `false` |
| `workCameBack` | `false` |
| `B4` | `false` |
| `clausesExercised` | contains `"B4"` |
| the run | that check FAIL, nothing else red |

### (iii) `worker-crash-is-never-noticed` — the inducer's effect is discarded

New, and it is the red case for §3's decision rather than for the product: the
same `worker-crashed` branch is disabled, so the induced failure reaches
nothing. The session stays `ready`, the dead state B4 needs never arrives, and
the run must render that as **B4 unexercised and the check FAIL** — not as a
PASS with three clauses.

| field | required value |
| --- | --- |
| `fallbackInducer.fired` | `true` |
| `stateAfterFallback` | `"ready"` (no dead state inside 90 s) |
| `B1` / `B2` / `B3` | `true` / `true` / `true` |
| `B4` | `null` |
| `clausesExercised` | `["B1","B3","B2"]` — **no `"B4"`** |
| `b4Inducer` | `"worker-failure"` |
| `why` | names that the product never noticed a real worker failure |
| the run | that check FAIL (`outcome: "FAIL"`, not `"NOT_ESTABLISHED"`), nothing else red |

`fired: false` renders through the same two cells (`B4: null`,
`clausesExercised` without `B4`) with the inducer's own `why` instead. Red case
(iii) is the reachable half of that pair: no product byte can stop CDP from
attaching, so the non-firing half cannot be mutated into existence and is
covered by reading the same code path.

### Why each of the three can only red this check

The two new mutations live in the `worker-crashed` branch, which no other arm
reaches: `induce_worker_failure` has exactly one other call site and it runs
only when finding 038 stops reproducing, which it does not on either profile
today. Both are declared `alsoRed: []`, and a run that reds anything else
falsifies that declaration rather than confirming the mutation.

## 5. What the plain runs must show (T8b's acceptance, restated in fields)

`--profile e2-editor-v14`, no mutation, three runs:

* `clausesExercised` contains all of `B1`, `B2`, `B3`, `B4`;
* `b4Inducer: "worker-failure"` 3/3;
* `fallbackInducer.fired: true`, `stateAfterFallback: "recoverable-error"`,
  `declaredCheckpointAfterFallback: "有（r1）"`,
  `noticeAfterFallback.rescue: "checkpoint"`,
  `checkpointOnOfferIsThisGestures: true`, `workCameBack: true`, `B4: true`;
* composition unchanged at **40 PASS / 2 NE**, `ok: true`.

`e2-editor-v8`, no mutation, one run: `clausesExercised` exactly
`["B1","B3","B4"]`, `b4Inducer: "boundary-press"`, every other cell equal to
`plain-e2-editor-v8.json`.

**If the worker-failure inducer does not fire on v14, that is a result to bank,
not a task failure** — and by §3 above the run will say so in red.

## 6. Default conclusions, written beside the criteria

* **If this task is never finished**: B4 — "what comes back contains what was
  typed", the property half C exists for — **is unwatched on every profile
  carrying A**, and every future fixed profile ships with the check reporting
  PASS on three clauses out of four without the reader being able to see which
  one is missing unless they open the JSON.
* **If T8b runs it and the inducer never fires**: the reach is not there, the
  check is red on the fixed profile, and the decision returns to the owner
  between option (b) (B4 is meaningful only on the shipping side, written down)
  and a third inducer. **T8a does not get to choose (b) by leaving the red in
  place**, and the red may not be waived by editing this protocol (§10).
* **If the notice's declaration is right but the save comes back without the
  sentinel**: that is a product defect in the rollback path, a finding, not a
  reason to relax §2.3.

## 7. Named limits, recorded now rather than discovered later

1. **The two call sites of `induce_worker_failure` are order-dependent.**
   `Target.setAutoAttach` delivers `attachedToTarget` for targets that already
   exist *when auto-attach is turned on*; a second call in the same CDP session
   may be answered with no attachments and report "auto-attach delivered no
   session for a document worker". Today only one of the two sites ever fires in
   a run (038 reproduces on v8 and v14, so the recovery arm does not reach its
   fallback), and the boundary arm is **last** in the file. On a core where 038
   stops reproducing, both sites fire in one run and the second may be starved.
   **Not measured here.**
2. **Worker generations.** `maxWorkerGenerations` defaults to 3 and the page does
   not override it; the arm opens its own fixture (generation 1) and the new
   rollback takes it to 2, the same number the dying branch already spends on the
   shipping profile. A third rollback inside this arm would throw
   `WORKER_GENERATION_LIMIT`, so this arm may not grow another recovery.
3. **The harness's path is not the user's.** A user cannot induce a worker crash
   on purpose. What this arm measures is the product's behaviour *after* a real
   crash class it already handles; the gesture half is the user's path and is
   unchanged.
4. **B4 on a fixed profile is no longer a statement about the gesture's own
   death.** It is a statement about the checkpoint the gesture banked surviving a
   death from another cause. That is weaker than the shipping profile's B4 and is
   the price of option (a); it is recorded here so nobody quotes a v14 run for
   the stronger claim.

## 8. Constraints on the executor

* `handoff/**` and `findings/evidence/**` in English; `findings/096-*.md` in
  zh-TW. Commit messages zh-TW, one per brief step, `Co-Authored-By: Claude
  Fable 5.1 <noreply@anthropic.com>` and no `Claude-Session:` line.
* `make test-e2-c-static` green (it holds every mutation pattern to exactly one
  occurrence) and `tools/check_usable_editor.py` resolving, both before the
  finding is appended to.
* No `git push`, no amending of existing commits, no edit to a banked report.

---

## Execution record

Reserved. Appended to, never edited: T8a adds what the static checks said once
the code is landed, T8b adds the runs.

### 2026-09-10 — T8a, static only. Nothing above was edited.

Eight commits, `fdc51c10` through `54d2b7df` plus this one: this protocol, the gate amendment, the
shared `press_the_notice_and_save` tail (proved output-identical to the inline
code it replaced, in both worlds, `json.dumps` so key order counted), the second
inducer, the FAIL-not-NE rendering, the three `MUTATIONS` entries, the finding's
disposition and the evidence README's.

* `make test-e2-c-static` **exit 0** (108 unit tests, which include
  `test_product_path_mutations.py` holding all three patterns to exactly one
  occurrence in `dist/`). `tools/check_usable_editor.py` exit 0,
  `tools/audit_product_path_coverage.py` exit 0.
* Each mutated file was handed to `node --check`: all three parse.
* The four B4 renderings were driven through stubs with no browser — `B4` `true`
  / `false` / `null` / `null`, the last two with `clausesExercised` omitting
  `B4` and `ok: false`. That exercises the verdict composition and is **not**
  evidence about any artifact; the red cases are T8b's.
* **No browser was started and no measurement was banked.** Until T8b has turned
  all three red cases red, the narrowing this protocol registers is not in force
  (gate amendment of 2026-09-10, last section).

One deviation from the brief's numbering, recorded rather than left to be
noticed: its item 4 ("the dying branch is not edited") was landed **before** item
3, as the refactor commit, so that the commit adding the inducer could not be the
one that moved the shipping profile's cells. Its item 8 is a constraints list and
has no commit. Item 3's `b4Inducer` requirement does add one cell to the dying
branch — `"boundary-press"` — which is the only way that value can ever be
produced, and no `B1..B4`, `clausesExercised`, `why` or `boundary[...]` cell
moved.

### 2026-09-10 — T8b, the runs. Nothing above was edited.

Seven `tools/run_e2_c_product_path.py --browser chrome` runs, sequential, one
Chrome instance at a time, from `wasm_sdk_probe/`: the three red cases on
`--profile e2-editor-v14` (§4 (i)/(ii)/(iii)), three plain runs on
`--profile e2-editor-v14`, and one plain run on the shipping profile (no
`--profile`). All seven banked under
`findings/evidence/096/product-path/`, full field-level reading in
`findings/evidence/096/product-path/RESULT-b4-second-inducer.md`.

* **All three red cases went red exactly as §4 pins them, and nothing else
  went red** (`alsoRed: []`, confirmed against `plain-e2-editor-v14-b4-01.json`
  as the baseline): (i) `boundary-move-takes-no-checkpoint` reds B3 and B4
  together; (ii) `worker-crash-throws-the-checkpoint-away` reds B4 alone with
  B3 staying true; (iii) `worker-crash-is-never-noticed` renders `B4: null`,
  `clausesExercised` without `B4`, `outcome: "FAIL"` (not `NOT_ESTABLISHED`) —
  the §3 decision holds under an actual run, not only under the stubs T8a
  drove.
* **§5's acceptance is met**: all three plain `e2-editor-v14` runs show
  `clausesExercised` containing B1-B4, `b4Inducer: "worker-failure"` 3/3, and
  every pinned fallback cell (`fallbackInducer.fired`, `stateAfterFallback`,
  `declaredCheckpointAfterFallback`, `checkpointOnOfferIsThisGestures`,
  `workCameBack`, `B4`) at its required value, composition unchanged at 40
  PASS / 2 NE. **The worker-failure inducer fired on every attempt in this
  batch (6/6)** — the brief's "if it does not fire, that is a result to bank"
  contingency did not arise.
* **The v8 control reproduces `["B1","B3","B4"]`** with `b4Inducer:
  "boundary-press"` and the same `servedShell` (shell generation v51,
  `declaredSha256 == servedSha256 == 2ffbec81…`, `differingPaths: []`) as the
  original `plain-e2-editor-v8.json`. Inside the check's `observed`/`verdict`
  payload — the scope §2.5 promises unchanged — nothing moved beyond the new
  `b4Inducer` cell and a 1-byte `savedBytes` drift consistent with
  run-to-run variance already seen among the plain v14 runs. Widening the
  comparison to the check's `oracle` string (outside that scope) finds one
  more line moved, traced to the already-landed T8a commit `ffb5c96a1510`
  rather than to anything T8b ran.
* `finding038Reproduced: true` on all seven reports, confirming the
  precondition the two new mutations' `alsoRed: []` claim (§4, closing
  paragraph) depends on.
* No report contains `WORKER_GENERATION_LIMIT` or an observed
  `restart-required` state (the string appears only inside a different
  check's static explanatory text in these reports); §7 limit 2's ceiling was
  not approached in this batch.
* Headless Chrome process count was 0 before the first run and 0 after the
  last; no leftover process was found or killed.

**Supersedes nothing.** This entry adds the measurement T8a's entry above
explicitly deferred ("no browser was started and no measurement was banked
... until T8b has turned all three red cases red, the narrowing this
protocol registers is not in force") — with this entry, the narrowing is in
force.
