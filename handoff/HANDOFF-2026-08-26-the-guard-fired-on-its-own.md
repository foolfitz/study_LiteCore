# Handoff: the dead-session guard, and it fired on a run nobody arranged

Written 2026-08-26, continuing
[`HANDOFF-2026-08-24-the-link-and-the-core-that-showed-it.md`](HANDOFF-2026-08-24-the-link-and-the-core-that-showed-it.md).

## State

`e2-editor-v8` still ships and **nothing about the product changed today**. No
link, no shell generation, no `dist/` write. Everything here is harness, queue,
checklist and evidence.

| queue item | before | now |
|---|---|---|
| `queue-a11y-path-drives-a-dead-session` | absent | **present** — the guard is in, measured four ways |
| `queue-cut-refusal-lost-its-inducer` | absent | **present** — the route built 2026-08-22 was finally driven, both ways |
| `queue-abort-margins-are-unexplained` | present, with two debts | one debt paid (the wall-clock sleeps), one measured (N rounds) |
| `queue-canvas-grew-arm-abstains-intermittently` | — | **new, absent** |

Shipped-profile product path, chrome, `e2-editor-v8`: **38 PASS / 2
NOT_ESTABLISHED, `ok: true`** on the runs where the long-document arm's
precondition held, **37 / 3** on the runs where it did not — see the new queue
item. `tools/check_usable_editor.py` reconciles the whole checklist **green**
against a real run for the first time.

## 1. The guard, and the only run that mattered

`queue-a11y-path-drives-a-dead-session` is finding 081's prescription: the
runner used to keep driving a session that had entered `recoverable-error`, so
every remaining arm spent its own timeout on a session refusing everything.
20–50 minutes, and no report at all, because `--out` was written only at the end.

Three parts, all in `tools/run_e2_c_product_path.py`:

* **`class Liveness`** — one state read after every recorded check. A dead state
  stops the run, names the check after which it noticed, lists in **source
  order** the checks it never reached, and forces `ok: false`.
* **Two arms hold it off** — finding 047's recipe and finding 038's endnote
  inducer drive that state deliberately and press the product's recovery notice.
  Each region is read once more on the way out, and names the check **last
  recorded inside it**.
* **`--out` is written after every check**, stamped `complete: false`.

### Four runs, and only one of them could not have been arranged

| run | what it establishes |
|---|---|
| v8, guard armed, no flag | **no false positive, and the guard ran**: `liveness.probes: 39`, which is 40 declared checks − 3 recorded inside the held-off regions + 2 region-exit reads. A predicted number, not a tally. |
| v8, `--liveness-control`, first attempt | **the control could not fire** — both inducing arms recover *before* they record their check, so nothing at a check boundary ever meets the state they induce. It went green end to end. |
| v8, `--liveness-control`, after the fix | **it fires**: stopped inside finding 038's arm, `recoverable-error`, `pending: 0`, `checkpoint: 有（r2）`, toast `TIMEOUT：editorGetStateV2 timed out after 30000 ms`, `recorded: 39/40`, `ok: false`. |
| **`--profile e2-editor-v9`, no flag, no mutation** | **it earns its keep.** The session died on its own after `format-a-paragraph-changes-that-paragraph` — the arm finding 081 named — with the page state identical **field for field** to the CDP read taken off the live stalled run on 2026-08-24. `recorded: 17/40`, 23 arms never driven, **322.3 s instead of 20–50 minutes**, and a readable report. |

Evidence, with a prediction written before any control run and left unedited:
`findings/evidence/queue-a11y-path-drives-a-dead-session/`.

**The first control run is worth reading before designing the next control.**
It was built on the check boundaries, which is where the guard lives, and it
was green — because the only two arms that reach the state get out of it before
the boundary arrives. A positive control needs its own positive control.

## 2. Finding 081's open question is answered, and the answer is not the save

081 recorded that the first failure's cause was **not established**: `latency`
keeps only the last entry and a save is refused in `recoverable-error` anyway,
so `儲存 失敗` might be consequence rather than cause. The v9 run's per-arm
record settles it:

| arm | action | outcome |
|---|---|---|
| 1 | `set-paragraph-heading` | PASS |
| 2 | `set-paragraph-body` | **FAIL** — `MUTATION_OUTCOME_UNKNOWN`: *the postcondition read describes a different paragraph from the one this action was dispatched on*, disposition rollback |
| 3–5 | three list actions | NOT_ESTABLISHED — `定位游標 失敗` |
| after | save | `EDITOR_NOT_READY` → `latency: 儲存 失敗` |

`MUTATION_OUTCOME_UNKNOWN` is in `RECOVERY_ERRORS`
(`editor-shell/editor-session.js:15`), so arm 2 is what blocked the queue. The
save is the consequence, and the consequence is what was visible.

**And the branch that killed it cannot run on the shipped core at all.**
`readback-is-a-different-paragraph` (`src/probe_engine.cpp:4237`) is gated on
`dispatchParagraphKnown && readbackParagraphKnown`, both of which come from
accessibility. On a build without it the gate fails open and never fires. So
turning accessibility on turns on a comparison that has never run in production,
and its first real exercise refuses an ordinary `set-paragraph-body`.

Which of *"the read really was of another paragraph"* and *"the fingerprints are
derived wrongly on this core"* is true is **not established**. Do not indict
either.

## 3. What this says about a11y as a product

The handoff asked for "the v9 product path, which is the real question about
a11y as a product". The answer, on one run and with the guard's own limits:

**`e2-editor-v9` is not shippable as it stands.** An ordinary paragraph format —
body ← heading, through the product's own toolbar button — takes the session to
`recoverable-error` with **no checkpoint**, which is the state whose notice tells
the user their unsaved work will not come back. That is a user-visible failure on
the first document the product opens, not a harness artefact.

Also measured on that run, and both are new:

* `bulleting-a-blank-line-does-not-demand-a-rollback` **FAILS** with the *other*
  `failureShape`, `stage-deadline` — the one recorded on 2026-08-23. So the
  accessibility core produced **two distinct barrier failures in one run**, both
  terminal for the session.
* `notice-action-recovers-the-session` **PASSES** on v9. The recovery notice was
  offered, pressed, and the session came back. That check has abstained on the
  shipped profile since 2026-08-17 and it is **not dead** — see §5.

**What is still unmeasured on v9**: the 23 checks after arm 17, including
`an-inline-format-reaches-a-selection`, which the previous handoff expected to
be meaningful there. Nothing has driven them, because the session dies first.

## 4. The refusal pair: a route built four days ago and never driven

`queue-cut-refusal-lost-its-inducer` said, in its own words, "ROUTE BUILT
2026-08-22, NOT YET MEASURED -- and the item stays open for exactly that reason."
It is measured now, both ways, on the shipped v8:

* `--refusal-diagnostic` (one manifest field narrowed to `gestures: []` in a
  symlink mirror; `dist/` never written, `probe.wasm` byte-identical): **all four
  of finding 063's properties held** — the toast named
  `EDITOR_FORMAT_GESTURE_UNSUPPORTED`, the document was unchanged, the session
  stayed `ready`, and the save afterwards produced a readable ODT.
* `--refusal-diagnostic --mutate cut-swallows-the-refusal`: the check goes
  **RED on the term the mutation moves** (`refusalReported: false`) while the
  other three stay true, and the product **said it had cut** (`已剪下 …`) over an
  action that removed nothing. Finding 063's user-facing shape, on demand.

Both are now in `make test-e2-c-product-path`, because a route nobody drives is
a route nobody has measured, and four days is how long that took to notice.

The 2026-08-22 prediction is unedited below its status line:
`findings/evidence/queue-cut-refusal-lost-its-inducer/`.

## 5. What the adversarial review changed, and it was right about the important one

An adversarial reviewer was given the change, the tests, the evidence and the
queue items, and asked to refute two positions. Both of mine needed correcting.

**`notice-action-recovers-the-session` is not a standing abstention — it is half
of an anti-correlated pair.** `blocked` and `empty_cell_state` are two reads of
one moment: finding 046's cell either blocks the queue or it does not.

| 046's cell blocks? | `bulleting-a-blank-line…` | `notice-action…` |
|---|---|---|
| no | **PASS** | NOT_ESTABLISHED |
| yes | **FAIL** | **PASS** |

Measured on five runs the same day: v8 gave PASS/NE four times and v9 gave
FAIL/PASS. I had been about to re-point the notice check at finding 038's
inducer, which would have destroyed the only automatic sentinel on 046's
disposition and put both checks on one upstream defect on one browser. Instead:

* `finish()` now holds the pair to two implications on every run —
  `bulleting PASS` → the notice check must not be PASS; `bulleting FAIL` → it
  must not be NOT_ESTABLISHED. A red notice check beside a green cell stays
  legal, because that is "047's recipe dispatched nothing", a product failure.
* the abstention text now says the pairing out loud;
* `recovery-returns-what-the-product-promised` now asserts the notice was
  **shown and not disabled** — it never did. `recovery["pressed"]` cannot stand
  in: `CLICK_NOTICE` returns true whenever `#notice-action` is in the DOM, which
  it always is. `disabled is False` is finding 054's own regression net.

Also fixed, all from the same review:

* a held-off region names the check **last recorded inside it**, not its own
  label. Region 1 is named for the notice check and encloses the bulleting cell
  — which is the check that kills the session on the accessibility core.
* `READ_STATE` answering `state: null` (the page navigated; there is no pill) is
  a **read failure**, not a live session. It used to count as a satisfied probe.
* read failures are counted and clear `lastState`, which used to leave a stale
  `ready` standing in every later report.
* `expired` joined the dead states: `showExpired` writes the pill directly and
  leaves the paper hidden with every control disabled, and this runner re-opens
  five times, each of which re-checks the pin.
* the `--range-delete-diagnostic` block — the one block with no checks in it and
  therefore no probes, and the one whose own comment records this shape ending
  in `recoverable-error` — now probes per shape.
* the stopped-run verdict quotes what the product last said, because `TIMEOUT`
  (a loaded machine) and `EDITOR_BOUNDARY_UNSUPPORTED` (a refusal that
  dispatched nothing, and **is** a verdict on the product path) both arrive at
  this state.

## 6. Three new kinds of file that nothing would have rejected

`--out` is now written mid-run, so partial reports exist. `check_usable_editor.py`
refuses three things it used to accept:

* a report that is not `complete: true` (missing counts as not complete);
* a report carrying `sessionDied`;
* a report carrying `profileDiagnostic` — **which was already possible before
  today**. `--profile` mirrors the page to load a different engine and the
  runner has always stamped "must not be quoted as the product's"; nothing
  enforced it, and the served-shell digest cannot catch it because the mirror
  serves the *same shell* with a different engine underneath.

Each has a negative control in `--self-test`.

## 7. Two checklist rows that claimed `done` and named no check

`check_usable_editor.py --self-test` had been failing — at HEAD, before any of
today's work — on `redo` and `move-by-line`: both `done`, both citing only a
queue item. The link shipped both and both have a green check that can fail
(`product-redo-button-restores-what-undo-removed`,
`the-vertical-arrows-move-the-caret`). The rows now cite them, with the reason
written into the row. The self-test is 24/24 and the checklist reconciles green
against a real run.

## Open work, in the order I would take it

1. **Why the a11y barrier says "a different paragraph".** This is the thing
   standing between the a11y lineage and any product decision. Three v9 repeats
   with `--barrier-details-diagnostic` are queued (see below); that flag mirrors
   the page so `run()` keeps each rejection's **typed** payload — `failureShape`
   and the two fingerprints the barrier compared — instead of only the message
   the user is shown. Read those before forming a hypothesis.
2. **Consider one revival on death, rather than stopping.** Raised by the
   review and it is a good point: `openDocument()` constructs a **brand-new
   session** on every open, so `recoverable-error` is terminal for a session
   object, not for the page — and this runner re-opens five times. A death at
   check 17 currently costs 23 checks, of which the ones behind a later re-open
   were structurally reachable. **Not built**, deliberately: it changes the
   guard's contract, a revived run's later checks are measured on a session with
   a different history, and it needs its own positive control. Build it with one,
   or not at all.
3. **A refusal that reaches `restart-required` is a verdict on the product
   path.** `EDITOR_BOUNDARY_UNSUPPORTED` dispatches nothing and still blocks the
   queue (`editor-session.js:319`), and the runner presses `delete-backward` at a
   geometry-aimed caret. Today that would stop the run reporting "not a verdict
   on the product path", which is exactly backwards. The verdict now quotes the
   toast; the branch that turns it into a named check failure is not written.
4. **`queue-canvas-grew-arm-abstains-intermittently`** — 2 of 5 runs on one
   machine in one hour, and it is wired into the acceptance checklist, so a run
   passes or fails the gate by coin flip. The arm now records which precondition
   failed; nobody has read one yet.
5. The v9 checks after arm 17, which no one has driven.

## Things a new session should not re-derive

* **A control that lives where the guard lives can be green for the wrong
  reason.** Control run 1 is the worked example and it is in the evidence.
* **`liveness.probes` is a predicted number.** 40 declared checks − the checks
  recorded inside held-off regions + one read per region exit. If it does not
  add up, something moved.
* **The two recovery checks are one measurement read twice.** `finish()` holds
  them to it now; the table is in §5.
* **`--profile` runs are not acceptance evidence** and are refused as such.
* **The engine's paragraph-identity gate is a11y-only.** It fails open on a
  build without accessibility, so the shipped product has never exercised it.

## Commands

```sh
cd wasm_sdk_probe

# the shipped baseline
python3 tools/run_e2_c_product_path.py --browser chrome --out <path>

# the guard's positive control -- EXPECTED to stop inside the endnote inducer
python3 tools/run_e2_c_product_path.py --browser chrome --liveness-control --out <path>

# the accessibility candidate, with the barrier's typed payload kept
python3 tools/run_e2_c_product_path.py --browser chrome \
    --profile e2-editor-v9 --barrier-details-diagnostic --out <path>

# the refusal pair, now also in `make test-e2-c-product-path`
python3 tools/run_e2_c_product_path.py --browser chrome --refusal-diagnostic --out <path>
python3 tools/run_e2_c_product_path.py --browser chrome --refusal-diagnostic \
    --mutate cut-swallows-the-refusal --out <path>
```

## The push

Nothing was pushed. `github/main` is where the previous handoff left it.
