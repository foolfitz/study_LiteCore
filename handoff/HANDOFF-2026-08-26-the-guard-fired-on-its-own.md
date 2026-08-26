# Handoff: the dead-session guard, and it fired on a run nobody arranged

Written 2026-08-26, continuing
[`HANDOFF-2026-08-24-the-link-and-the-core-that-showed-it.md`](HANDOFF-2026-08-24-the-link-and-the-core-that-showed-it.md).

## State

`e2-editor-v8` still ships, and its **artifact** is untouched: no relink, no
change to `dist/profiles/e2-editor-v8`.

**Shell generation v42** was frozen — `paragraph-editor-client.js` and
`web/e2-editor-app.js` both changed for finding 083 — and the shipped
`e2-editor-v8` was re-measured against it: **38 PASS / 2 NOT_ESTABLISHED,
`ok: true`**, its best. The engine change below is inert on a build without
accessibility.

**One link was taken, on the accessibility lineage and under a new name**:
`e2-editor-v10`, carrying finding 082's fix. It relinks nothing — `make -n` on
the target was checked to touch only `build/e2/e2-editor-v10/` and
`dist/profiles/e2-editor-v10/` — and it is archived at
`build/archive/e2-editor-v10-4ec1e389-worker-070229cd-manifest-d57de339/` with
its attribution. Runbook and the prediction written before the measurement:
`handoff/RUNBOOK-relink-v10-a11y-identity.md`.

| queue item | before | now |
|---|---|---|
| `queue-a11y-path-drives-a-dead-session` | absent | **present** — the guard is in, measured four ways |
| `queue-cut-refusal-lost-its-inducer` | absent | **present** — the route built 2026-08-22 was finally driven, both ways |
| `queue-abort-margins-are-unexplained` | present, with two debts | **both paid** — eleven rounds, and the two fields it asked for turned out not to exist for it |
| `queue-canvas-grew-arm-abstains-intermittently` | — | **new, absent** |
| `queue-a11y-prefix-swallows-the-paragraph` | absent, since 2026-08-22 | **present** — the decision it was waiting for, forced by 082 |
| `queue-a11y-caret-does-not-move-on-the-first-commit` | — | **new, absent** — finding **084**, characterised and unfixed; only visible because 082 was fixed |
| `queue-a11y-stage-deadline-awaiting-selection` | — | **new, present** — finding 083, filed and fixed the same day |
| `p1-3b-empty-readback` | withdrawn 2026-08-16 | still `absent`, but its stated reason is now known to be **true of one core and not the other** |

**Three findings filed today and two of them fixed the same day**: 082 (the
identity gate comparing the hash of the empty string) and 083 (an empty
selection called a stall) are fixed and measured; 084 (the caret skipping a
commit) is characterised and open. Between them the accessibility lineage went
from **dying at check 17 of 40** to **two runs in three completely clean**.

**Finding 082 filed AND FIXED, same day.** On the accessibility core an ordinary
paragraph format was refused by the barrier as "a different paragraph" — 4 runs
of 4 — and the refusal took the session down with no checkpoint. The mutation
had in fact worked; the gate was comparing a fingerprint that was the hash of the
**empty string**. Fixed in the engine, linked as **`e2-editor-v10`**, and the
product path there now runs all 40 checks with that arm passing six of six,
three rounds of three. See §3 and `findings/evidence/082/RESULT.md`.

**`queue-a11y-prefix-swallows-the-paragraph` closed** with it: it had been
waiting since 2026-08-22 for "our side to decide what to do about it", and 082
is what made the decision unavoidable.

Shipped-profile product path, chrome, `e2-editor-v8`: **38 PASS / 2
NOT_ESTABLISHED, `ok: true`** on the runs where the long-document arm's
precondition held, **37 / 3** on the runs where it did not — see the new queue
item. `tools/check_usable_editor.py` now reconciles the whole checklist **green**
against a real run. Before today it did not resolve at all — see §7.

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
a11y as a product". The answer, on four runs:

**`e2-editor-v9` is not shippable as it stands, and `e2-editor-v10` is the
answer to why.** An ordinary paragraph format — body ← heading, through the
product's own toolbar button — took the session to `recoverable-error` with **no
checkpoint**, the state whose notice tells the user their unsaved work will not
come back. A user-visible failure on the first document the product opens.

**It was a false refusal**, and the fix is measured: see §3b. On `e2-editor-v10`
that arm passes six of six, three rounds of three, and the lineage runs to the
end of the net for the first time.

**Four runs, four times, identical.** Filed as **finding 082**. Every run dies
after the same check, with `recorded: 17/40`, `pending: 0`, `checkpoint: 無`,
and the same two arms: `set-paragraph-heading` on line 1 PASSES, and
`set-paragraph-body` on line 0 fails with `readback-is-a-different-paragraph`.

The typed payload — kept by `--barrier-details-diagnostic` on rounds 2–4 — rules
out the easy explanations:

```json
{ "failureShape": "readback-is-a-different-paragraph",
  "dispatched": true, "route": "collapsed",
  "paragraphIdentity": { "checked": true, "dispatchKnown": true, "readbackKnown": true },
  "readbackParsed": true, "readbackBlockCount": 1,
  "containment": { "checked": true, "held": true } }
```

Both reads succeeded, the gate ran, the readback is **one** block (so not the
`multi-block-readback` family), and **containment held** — the selection did
cover the caret the action was dispatched from. And the fingerprints still
differ.

Also measured on that run, and both are new:

* `bulleting-a-blank-line-does-not-demand-a-rollback` **FAILS** with the *other*
  `failureShape`, `stage-deadline` — the one recorded on 2026-08-23. So the
  accessibility core produced **two distinct barrier failures in one run**, both
  terminal for the session.
* `notice-action-recovers-the-session` **PASSES** on v9. The recovery notice was
  offered, pressed, and the session came back. That check has abstained on the
  shipped profile since 2026-08-17 and it is **not dead** — see §5.

**And this arm had never actually run on the accessibility lineage before.**
The last stored v5 report (`findings/evidence/075/pp-v5-product.json`) has all
five of its arms NOT_ESTABLISHED with the same reason: *"the canvas shows 7
bands for 9 lines, so this arm cannot say WHICH paragraph"* — finding 075, the
off-page garbage that merged two lines. Today's v9 report reads `bands: 9,
lines: 9`. So 076's `calloc` fix is what let this arm reach its own dispatch for
the first time, and the first thing it found was arm 2 refusing. **A fix that
restores a measurement is how the next defect becomes visible**, and it is worth
saying out loud that nobody had been looking at this arm — it had been abstaining,
not passing.

**What is still unmeasured on v9**: the 23 checks after arm 17, including
`an-inline-format-reaches-a-selection`, which the previous handoff expected to
be meaningful there. Nothing has driven them, because the session dies first.

## 3b. Finding 082, fixed: the gate was comparing the hash of the empty string

The prediction that got it wrong is worth reading first
(`findings/evidence/082/PREDICTION-which-paragraph-was-read.md`, unedited): it
said the barrier's restore point had gone stale and the readback had landed on
the next paragraph. **`readback.html` refuted it in one line** — the read
described `<p>E1-LC-HEADING</p>`, the right paragraph, already restyled. The
mutation had worked.

**The answer was in the engine's payload all along and JavaScript was throwing
it away.** `productFormatBarrier` in `sdk-worker.js` is an allowlist whose own
comment says "this allowlist is where engine fields go to be forgotten"; it drops
`readback.html` and the containment geometry. `--barrier-details-diagnostic` now
widens it in a mirror. No engine change was needed to find the cause.

The cause, from a trace of `editorState.caretParagraph` on every state
transition:

| listPrefixLength | contentLength | fingerprint | text |
|---:|---:|---|---|
| 0 | 20 | `76f09d751bb341f7` | `E1-LC-END甲一乙二丙三插入鈕標記` |
| 2 | 22 | `76f09d751bb341f7` | `• ` + the same text |
| **13** | **13** | **`cbf29ce484222325`** | **`E1-LC-HEADING`** |
| **2** | **2** | **`cbf29ce484222325`** | **`• `** |

Both things at once. **The prefix stripping works** — a paragraph and the same
paragraph with a bullet share one fingerprint, which is exactly why it exists.
And **a thirteen-character heading and an empty bulleted paragraph are the same
number**, which is the FNV-1a offset basis: the value that means *nothing was
hashed*. `listPrefixLength == contentLength` on both, which is finding 074,
upstream, `getListPrefixSize()` returning the end of the first ATTRIBUTE RUN.

**The fix**: the gate DECLINES the comparison when either end's fingerprint is
degenerate, instead of failing it — the same fail-open the surrounding comment
already argued for, extended from "the value is absent" to "the value is present
and meaningless". The alternative is a false refusal prescribing a rollback,
which is worse than the defect the gate exists to catch.

* `src/a11y_paragraph_identity.hpp` holds the rule **beside the hash**, so there
  is one implementation and a host compiler can drive it.
* `tests/a11y_paragraph_identity_test.cpp` reproduces **six fingerprints the
  accessibility engine really reported** — a cross-implementation check, not a
  restatement — and four mutations of the rule are each detected by it. It runs
  in `make test-e2-b-static`.
* The editor state gains `a11y.fingerprintUsable`; the barrier payload gains
  `dispatchUsable`, `readbackUsable` and `declined`, so `checked: false` no
  longer has three causes and one appearance.
* **Inert on the product core**: accessibility off ⇒ `dispatchParagraphKnown` was
  already false ⇒ the gate already declined. `e2-editor-v8` needs no relink.

Measured on `e2-editor-v10`, against the prediction written before the run — all
five points held, and the run reaches the end of the net:

| round | verdict | the paragraph-format arm | `caret-follows-the-text-you-type` |
|---|---|---|---|
| 1 | 35 PASS / 2 FAIL / 3 NE | **PASS**, 6 of 6 | FAIL |
| 2 | 37 PASS / 1 FAIL / 2 NE | **PASS**, 6 of 6 | PASS |
| 3 | 37 PASS / 1 FAIL / 2 NE | **PASS**, 6 of 6 | PASS |

No round stopped early; no round produced a `readback-is-a-different-paragraph`;
the one page error in each is the *other* defect,
`stage-deadline:awaiting-selection` on the bulleting cell, untouched as
predicted.

**What it bought, and it is the point of fixing it**: the 23 checks after the
seventeenth got their first reading on this lineage, and one of them is
intermittently red — `caret-follows-the-text-you-type`, 1 run in 3, filed as
`queue-a11y-caret-does-not-move-on-the-first-commit`. Nobody could have seen it
while the session was dying at check 17.

**What it does NOT fix**: finding 074 upstream (the number is still wrong, and
every other consumer of `listPrefixLength` is still exposed), and the fingerprint
as an identity in general (22% of the r7-compat corpus collides on text alone).

## 3c. Finding 083, also fixed: an empty selection is an answer, not a stall

With 082 gone, `stage-deadline:awaiting-selection` was the only consistent red
left on the a11y lineage — `bulleting-a-blank-line-does-not-demand-a-rollback`,
3 rounds of 3. Same recipe and same cell on both cores, and the payloads say the
whole thing:

| | `e2-editor-v8` | `e2-editor-v10` |
|---|---|---|
| `stage` | `awaiting-restore` | **`awaiting-selection`** |
| `selectionType` | 1 (`LOK_SELTYPE_TEXT`) | **-1** |
| `readback.blockCount` / `bytes` | 2 / 592 | **0 / 0** |
| `selectionResultSeen` | true | **true** |
| what the user gets | **review** | **rollback** |

`.uno:SelectText` on the blank paragraph selects **two paragraphs** on the
product core — finding 046's overshoot — and **nothing at all** on the
accessibility one. `maybeAdvanceFormatBarrierSelection()` needs the select
command's result *and* non-empty rectangles, so the barrier waits out 5000 ms
and calls an answer a stall. The action itself is identical on both cores.

**Why the cores differ is NOT established** and no layer is named: two build
differences, one measurement. It is not even obvious which behaviour is right —
not overshooting into the neighbour is arguably the better one.

**Our side's defect is independent of that**, and it needed no engine change and
no link: the disposition already lives in JavaScript.

* the **worker** forwards `selectionResultSeen` — the engine always sent it, the
  allowlist dropped it, and without it nobody can tell "the engine never
  answered" from "it answered and nothing was selected";
* the **client** adds a branch narrowed on four conditions (dispatched,
  collapsed route, that shape, and the select command having come back). Three
  mutations of the narrowing each turn the test red. A stall nobody can
  attribute keeps its rollback — the same reasoning finding 059's branch uses;
* the **page** gets its own sentence, because `review` with the multi-block
  explanation would tell the user the check "covered more than one paragraph"
  about a paragraph where nothing was selected. That is finding 061's shape and
  this tree has filed it once already.

**Shell generation v42, frozen once.** The first freeze was premature — the page
half was still to come — and was **withdrawn rather than forced over**, which is
the tree's own lesson from v28.

**The acceptance condition moved with the prescription, deliberately.**
`bulleting-a-blank-line-does-not-demand-a-rollback` pinned the multi-block
sentence and would have gone red on a product that had just been fixed. It now
takes either sentence, still pins the promise they share, still refuses
`請回到檢查點` — and **records which sentence it saw**, so the two cores' routes
to `review` stay visible instead of being flattened.

### `e2-editor-v11`: the first clean product path the a11y lineage has produced

v10's artifact repackaged — same wasm, same loader, only `workerSha256` moves
(`070229cd` → `03f5b69a`), **no link**. All four points of the prediction held:

| round | verdict | `bulleting-…` | caret check |
|---|---|---|---|
| 1 | **37 PASS / 3 NE, `ok: true`** | PASS, `empty-selection` | PASS |
| 2 | 36 PASS / 1 FAIL / 3 NE | PASS, `empty-selection` | FAIL |
| 3 | **37 PASS / 3 NE, `ok: true`** | PASS, `empty-selection` | PASS |

**Two of three are clean runs with no FAIL at all** — the first the accessibility
lineage has ever produced. The one red is the intermittent caret defect, which is
not this finding's and which nobody could see before 082 was fixed.

**And the shipped product, with the same shell served to it**: `e2-editor-v8`,
no profile flag, **38 PASS / 2 NOT_ESTABLISHED, `ok: true`** — its best. Its
`bulleting-…` still records `unverifiedSentence: "multi-block"`, so the two
cores keep reaching `review` by different routes and the harness keeps saying
which. `servedShell` matches the declared v42 digest, so that is the new shell
and not a stale copy.

**Declared cost, and `finish()` caught it in the same run**:
`notice-action-recovers-the-session` goes back to NOT_ESTABLISHED on the a11y
lineage, because the cell no longer blocks the queue. Same trade as 2026-08-17
on the product core; `recoveryPairing.held: true`.

## 3d. Finding 084: the caret skips a commit, and the instrument change is what proved it

With 083 gone, one red was left anywhere in the tree:
`caret-follows-the-text-you-type`, 2 runs in 6 on the a11y lineage.

**The geometry pointed one way and it was wrong.** Nineteen runs, both cores,
every one ending at the same position — 163, 278, 393, 509, per-mark deltas
115/115/116. The failing ones read 163, **163**, 393, 509: deltas 0, **230**,
116, and 230 is 115 + 115. Only one reading differs and the totals are
identical, so the movement was not lost, it was **deferred**. My reading was
that the harness had read too early: the arm waited for the revision and then
slept a fixed **1.2 s** — the same wall-clock shape removed from the abort arm
that morning, and this check's own comment records that the defect it covers was
originally a race.

**So the sleep became a poll** on the check's own predicate, 8 s deadline, with
the wait recorded per commit. The property that made this safe is the one to ask
for before replacing any sleep: **nothing is typed while it waits**, so a caret
that only catches up on the next commit runs the deadline out and the check
still fails.

**It still fails, and now it has a number.**

```
v11 round 4   163->278 (1 ms)    278->393 (1 ms)     393->509 (1 ms)    PASS
v11 round 5   163->278 (1 ms)    278->278 (8013 ms)  278->509 (1 ms)    FAIL
v11 round 6   163->278 (1 ms)    278->393 (1 ms)     393->509 (1 ms)    PASS
v8  (poll)    163->278 (0 ms)    278->393 (0 ms)     393->509 (0 ms)    PASS
```

**0 or 1 ms when it works, 8013 — the deadline — when it does not, and nothing
in between.** That is not latency; it is a dropped update, and the caret catches
up only when the next commit arrives.

| core | commits measured | dropped |
|---|---|---|
| product `e2-editor-v8` | **42** | **0** |
| a11y `e2-editor-v10` / `v11` | **27** | **3** |

**Not established and not to be named**: why only on that core (two build
differences, one measurement — findings 040 and 048), and which layer drops it.
The next question is one measurement: record the **engine's** caret state beside
`#sink` in the same round, which separates "the cursor callback never arrived"
from "it arrived and the page did not use it".

**What the instrument change was worth** — and it is not "it went green": it
turned an intermittent red with no number into a red with 8013 ms in the record,
and it **eliminated the competing explanation** that I had believed.

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

## 4b. The abort check: eleven rounds, and the sleeps are gone

`queue-abort-margins-are-unexplained` was left open on 2026-08-23 with its own
sentence: *"this is ONE run each way. An intermittent margin measured once gives
a confident and wrong answer, and that is the whole history of this check."*

**Eight consecutive PASS and three consecutive detections**, one machine, one
sitting. Every one of the eleven rounds aimed at the same line and selected the
same strings: control `E1-LC-ISOLATED 前後都不是清單的`, reference
`E1-LC-ISOLAT`, both abort arms 12 code points on every green round. The three
detections are the oracle's own reason each time — the arm whose `pointercancel`
listener the mutation removes ran to **23**, byte-identical to the control,
while the still-wired `blur` arm stopped at 12.

**The two fields the item asked to synchronise on do not exist for it**, and
that was measured rather than assumed: `revision` is the *document's* and a
selection is not an edit, so it never advances on a `selectRange`; and
`callbackSequenceBefore/After` never leave the page's closure — `pumpDrag`
publishes only `#toolbar[data-selection-shape]`. Publishing them is a product
change and a shell generation for a field only a harness would read. What the
page *does* publish is the answer, so both sleeps became polls on it, and both
waits are now in every arm's record:

| wait | was | measures |
|---|---|---|
| caret settles before the drag | `sleep(0.8)` | 0–1 ms |
| the copy path answers | `sleep(1.5)` | 201–203 ms (200 ms poll granularity) |

A fourth queue check pins `copyAnsweredMs` into the record, because putting the
sleep back would leave every string in this check identical and every round
still green — the only thing that would change is a number nobody was keeping.

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
  (a loaded machine) and `EDITOR_BOUNDARY_UNSUPPORTED` (the selection barrier
  correctly declining a Writer unit, which **is** a verdict on the product
  path) both arrive at this state — the second by a different route, see
  open work 3.

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

1. **Finding 084's next measurement**, and it is a single one: record the
   ENGINE's caret state beside `#sink` in the same round. That separates "the
   cursor callback never arrived" from "it arrived and the page did not use
   it", and until it is taken no layer may be named. Everything else about 084
   is characterised — 3 of 27 against 0 of 42, bimodal at 0 ms / never.

2. **Consider one revival on death, rather than stopping.** Worth less than it
   was this morning — 082's fix removed the death that made it urgent — but the
   argument stands for the next one. Raised by the review: `openDocument()` constructs a **brand-new
   session** on every open, so `recoverable-error` is terminal for a session
   object, not for the page — and this runner re-opens five times. A death at
   check 17 currently costs 23 checks, of which the ones behind a later re-open
   were structurally reachable. **Not built**, deliberately: it changes the
   guard's contract, a revived run's later checks are measured on a session with
   a different history, and it needs its own positive control. Build it with one,
   or not at all.
3. **A refusal that reaches `restart-required` IS a verdict on the product
   path, and the guard would call it the opposite.**
   `EDITOR_BOUNDARY_UNSUPPORTED` is the selection barrier declining a Writer
   unit that will not produce a safe single-line selection
   (`src/probe_engine.cpp:3246`, `:3280`) — one of its branches reports nothing
   dispatched — and `editor-session.js:319` blocks the queue with
   `restart-required` for it specifically, ahead of `RECOVERY_ERRORS`. The
   runner presses `delete-backward` at a **geometry-aimed** caret, and this file
   is full of notes about earlier checks reflowing the document under geometric
   aims. The day that caret lands at a paragraph start, the product refuses
   **correctly** and the run stops saying "this is not a verdict on the product
   path" — when it is exactly one, finding 063's shape a level up. The verdict
   now quotes the toast so a reader can tell; the branch that turns it into a
   named check failure is **not written**, deliberately, because nobody has
   seen it happen and an unexercised classifier is the thing this tree distrusts
   most. Write it with the run that produces it.
4. **`queue-canvas-grew-arm-abstains-intermittently`** — 3 of 8 runs on one
   machine in one hour, and it is wired into the acceptance checklist, so a run
   passes or fails the gate by coin flip. The arm now records which precondition
   failed; nobody has read one yet.
5. **`queue-a11y-caret-does-not-move-on-the-first-commit`** — 1 run in 3 on
   `e2-editor-v10`, and the first reading that check has ever had on this
   lineage. Bound it before writing it up: 1 of 3 is a rate nobody has measured,
   and the same check passes on `e2-editor-v8`.
6. **Whether `e2-editor-v10` is a cutover.** It is a candidate: three rounds
   with one consistent red (item 1) and one intermittent (item 5). The shipped
   `e2-editor-v8` is untouched and needs no relink — 082's change is inert
   without accessibility — so this is a decision about the a11y product line,
   not a repair to the current one.

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
* **The engine sends more than the product keeps.** `productFormatBarrier` in
  `sdk-worker.js` is an allowlist and drops `readback.html` and the containment
  geometry. Finding 082's cause was in the payload the whole time.
  `--barrier-details-diagnostic` widens it in a mirror; no relink is needed to
  read a barrier.
* **A fingerprint equal to `cbf29ce484222325` is not an answer.** It is the
  FNV-1a offset basis — what the hash returns when nothing was fed to it. The
  engine now says so itself (`a11y.fingerprintUsable`).
* **Before replacing a sleep with a poll, ask whether the poll can mask the
  defect the check exists for.** Three sleeps went today and each survived that
  question for a different reason. The one in `caret-follows-the-text-you-type`
  survived it because nothing is typed while it waits — and it then proved the
  defect was real, against my own reading.
* **A number beats a rate.** "2 runs in 6" became "0 ms or 8013 ms, nothing in
  between", and only the second one says *dropped update* rather than *slow*.

## Commands

```sh
cd wasm_sdk_probe

# the shipped baseline
python3 tools/run_e2_c_product_path.py --browser chrome --out <path>

# the guard's positive control -- EXPECTED to stop inside the endnote inducer
python3 tools/run_e2_c_product_path.py --browser chrome --liveness-control --out <path>

# the accessibility candidate as it now stands: 082's engine fix and 083's worker
python3 tools/run_e2_c_product_path.py --browser chrome --profile e2-editor-v11 --out <path>

# the same, with the barrier's typed
# payload kept -- `engineRaw` carries what the product's allowlist drops
python3 tools/run_e2_c_product_path.py --browser chrome \
    --profile e2-editor-v11 --barrier-details-diagnostic --out <path>

# what a link would ship, measured rather than read
python3 tools/what_the_link_ships.py --variant a11y --since c82a642

# the refusal pair, now also in `make test-e2-c-product-path`
python3 tools/run_e2_c_product_path.py --browser chrome --refusal-diagnostic --out <path>
python3 tools/run_e2_c_product_path.py --browser chrome --refusal-diagnostic \
    --mutate cut-swallows-the-refusal --out <path>
```

## The push

Nothing was pushed. `github/main` is where the previous handoff left it.

## The profiles that exist now

| profile | wasm | worker | what it is |
|---|---|---|---|
| `e2-editor-v8` | unchanged | unchanged | **ships**; re-measured against shell v42, 38/2, `ok: true` |
| `e2-editor-v9` | `b60cc46f` | `070229cd` | the a11y candidate before 082; dies at check 17 |
| `e2-editor-v10` | `4ec1e389` | `070229cd` | + finding 082's engine fix; 40 checks, one consistent red |
| `e2-editor-v11` | `4ec1e389` | `03f5b69a` | + finding 083's worker; **first clean a11y run** |

v11 is v10's artifact with one manifest field moved — no link, the same
relationship v7 has to v4's artifact.

**`e2-editor-v8` does NOT carry finding 083's worker.** The shell half reaches
it (served from `dist/`), the worker half does not, and it does not need it:
that core never produces the shape. If it ever should, the repackaging is a
manifest rebuild, not a link.

## The link that WAS taken

`e2-editor-v10`, 2026-08-26 21:02, under a new name. It relinks nothing;
`make -n` on the target was checked to touch only its own two directories.

| | |
|---|---|
| wasm | `4ec1e389aaab3b03` |
| loader | `96f18d0c1f6b9b11` |
| worker | `070229cd10bda4a0` (byte-identical to v8's and v9's) |
| manifest | `d57de339939bfbc9` |
| archive | `build/archive/e2-editor-v10-4ec1e389-worker-070229cd-manifest-d57de339/` |

Its `soffice.data` is the shared accessibility core image, declared through
`--core-data` and not copied into the archive — the reason is in that
directory's `ATTRIBUTION.md`.
