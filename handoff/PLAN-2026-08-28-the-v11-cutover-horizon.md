# The v11 cutover: what is owed, written down before the runs that would satisfy it

Written 2026-08-28. This exists because the reason to wait had no exit
condition, and a gate that can only be satisfied by more waiting is not a gate.

## Why this document is dated and specific

The case for waiting was: *the defect discovery rate on the accessibility
lineage has not levelled off.* Three findings in two days — **082**, **083**,
**084** — each of which was invisible until the previous one was fixed. That
pattern is real: under serial masking, "zero reds today" is weak evidence of
"zero defects", because every previous zero-red day also had a defect hiding
behind the current one.

An adjudication on 2026-08-27 accepted the instinct and rejected the form:

> as written — "the rate has not levelled off" — it can only ever be refuted by
> more waiting, and every clean day makes it *feel* more true while proving
> nothing.

It also argued against the instinct harder than I had: **the burst is partly an
artifact of first measurability.** That lineage could not complete a run until
2026-08-26; findings clustering immediately after a net first runs is what this
tree's own memory says a first run *is*. `e2-editor-v8` had the same burst at
the same age — 049, 050, 051, 052, 053 all fell out of its first manual round.
So a post-measurability burst does not by itself imply v11's latent-defect
density is higher than v8's was.

**Therefore the criteria below are fixed now, before the runs that would satisfy
them.** When they complete clean, the gate opens; nobody gets to move it. When
they produce a finding, the clock restarts from zero and the finding gets a
number.

## Already satisfied — do not re-litigate these

**Characterise the extra callback** — done 2026-08-27, and it is read from the
engine's own dispatch rather than inferred from two build variables.

* The a11y core emits **two** `editor-state` announcements per commit on 24 of
  24 commits; the shipped core emits **one** on 12 of 12. Deterministically one
  extra, never three and never one.
* The extra one is `LOK_CALLBACK_A11Y_FOCUS_CHANGED` →
  `editorSource = "a11y-paragraph-changed"` (`src/probe_engine.cpp:2433`).
* **It carries a caret of its own, and it is the stale one** — the accessibility
  paragraph callback fires before the cursor has moved. Two announcements per
  commit both claiming to describe the caret is the window finding 084 lived in.
* Nothing here measures or claims anything about the *calc* half of the build
  difference, and nothing may be quoted as if it did.

**Prove the 084 guard order-independent, not merely currently winning** — done.
The invariant asserted is: *after any interleaving, the snapshot holds the
highest `sourceSequence` written and the caret that came with it*, driven over
all 24 permutations of four arrivals, plus duplicates in every position, plus a
hostile stream, plus the measured two-announcements-per-commit shape in all
three orders. Mutations: guard removed 6 red, installed-but-never-stripping 2
red, `>` 7 red, `<=` 2 red.

**Re-measure the drop rate at the pre-fix sample size** — done, and larger:
**60 commits post-fix on v11 against 48 pre-fix**, 0 dropped, the guard refusing
**28** stale writes. 24 commits on the shipped profile, 0 dropped, guard fired 0
times — which one-announcement-per-commit predicts.

**Name the NE delta** — done, and it was a defect in an NE costume.
`recovery-returns-what-the-product-promised` was NOT_ESTABLISHED on v11 in 5
runs of 5 because finding 038's inducer no longer wedges that core, so the
product's safety net for unsaved work was driven by nothing on the profile a
cutover would ship. **Closed 2026-08-28** by a second, defect-independent
inducer (an uncaught error inside the document worker). v11 now runs
**38 PASS / 2 NOT_ESTABLISHED**, matching the shipped profile.

## The soak — the gate itself

All of it against the **candidate page**, not a `--profile` mirror:

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v11 --out <report>.json
python3 tools/check_usable_editor.py --report <report>.json
```

**1. Twelve clean runs, across at least three calendar days, at least two runs
on each of those days.**

*Clean* means all of:

* the run reports `ok: true` and `complete: true`;
* `check_usable_editor.py` reconciles it `ok: true`, with
  `reconciledFor.kind == "candidate-cutover"` and the profile named;
* the composition is **38 PASS / 2 NOT_ESTABLISHED** and the NE set is exactly
  `{notice-action-recovers-the-session,
    a-refused-action-is-reported-and-changes-nothing}`.

**Any FAIL, any additional NE, or any different id in the NE set restarts the
clock at zero** and is written up as a finding before the count resumes. A
NOT_ESTABLISHED that is *not* one of those two is the shape this whole exercise
exists to stop hiding.

Twelve is not a ritual: a defect that fires in a quarter of runs survives twelve
of them with probability 0.75¹² ≈ **3%**. The three-day spread is for defects
that depend on machine state or elapsed time rather than on the run.

**2. Three diagnostic runs, additionally**, to keep bounding the 084 class:

```
--candidate-profile e2-editor-v11 --caret-source-diagnostic \
    --caret-rounds 12 --caret-engine-probe stalled
```

Required: **0 dropped commits in 36**, and `staleWritesRefusedTotal > 0` in at
least one — because a run whose guard never fired has only shown that the race
was not lost that time. These are diagnostic and do **not** count toward the
twelve.

**3. One manual round, by a human, in a real browser with a real keyboard.**
Non-negotiable and not substitutable by more automation: this tree retracted two
findings after a single manual pass, because a human is the only observer that
does not share the harness's instruments. Minimum cells: open a document, type
(including one IME commit), apply a paragraph format, apply an inline format to
a selection, undo/redo, save and reopen the saved file.

**4. The benefit, measured on the user's own path.** Everything above shows v11
is *no worse* than v8. The entire case for paying +19 MB is
`caretParagraphText` and `documentOutline` — and **nothing has yet shown those
two fields being consumed by an actual screen reader on v11's five bound
identities.** Gate-0 evidence predates this profile, and version is identity.
One session with Orca or NVDA on the candidate page, with what was announced
recorded. This is the condition most likely to embarrass us in front of the
institutional buyer the schedule was rearranged for, and it needs the user or a
machine with a screen reader.

## The size decision is already made — confirm it, do not reopen it

The 2026-08-20 ruling that brought accessibility forward accepted the
writer+calc core at **+19.9 MB** as the product core. Measured today: v8's
`probe.wasm` is **110.0 MB**, v11's is **129.0 MB**. Cite the ruling in the
cutover record and get one explicit confirmation from the user — as a
confirmation, not a reopened decision.

## The cutover itself, and the revert that must be armed first

The chicken-and-egg — non-diagnostic evidence requires the cutover, the cutover
requires non-diagnostic evidence — is resolved by measuring the **candidate
page**: the page as it will ship, carrying its own pin and its own worker URL,
with its sha256 written into every report. The cutover is then a flip to bytes
already measured.

```
python3 tools/build_cutover_page.py --profile e2-editor-v11        # prints the sha256
python3 tools/build_cutover_page.py --profile e2-editor-v11 --write \
        --expect-sha256 <the sha256 every soak report carries>
```

As of this writing that page is
`c8c71ac530c4815aa431c04e2f2e001c34bd025f9b77744bb8fbe6881240a472`. The tool
refuses to write if the produced bytes differ from what was measured, because a
mismatch means the tree moved between the measurement and the cutover and the
honest answer is to measure again.

**Four things make the revert cheap enough to rely on. All four, not some.**

1. **v8's five identities archived with checksums and an `ATTRIBUTION.md`** that
   names what each file is — a profile is five bound identities, not one
   artifact, and an archive named after the wrong hash has already cost this
   tree once.
2. **No forward-incompatible state.** ABI 4 on both sides, the same 21 actions,
   and the two new manifest fields are additive — but the question that makes a
   revert expensive has to be *measured*, not assumed: does anything v11 writes
   fail to be read by v8? Grepped 2026-08-28: the shell uses no `localStorage`,
   `sessionStorage` or `indexedDB`, and the checkpoint is in-memory, so the only
   cross-version artifact is the **saved ODT**. Owed: save a document on the
   candidate, open it on v8, and check it round-trips. **Not yet done.**
3. **Rehearse it.** Perform the revert once against the staged setup and run the
   net on the reverted page. A revert that has never been executed is a hope.
4. **A pre-written trigger, decided now.** The revert is forced by any of: a new
   FAIL class on the net; a caret drop at the counter (`staleWritesRefusedTotal`
   rising while `moved` goes false); any user-visible regression reported by a
   human. A revert that requires a judgement call under pressure gets argued
   with instead of executed.

## What must be said out loud in the cutover record

* **v11 is not "the a11y core's defect" territory.** 084's cause was shared
  JavaScript that both profiles run; the shipped core simply never loses that
  race. Half of what a cutover ships is already shipping.
* **The extra callback is the accessibility focus callback**, read from the
  engine's dispatch. It is *not* evidence about calc, and the sentence "the a11y
  build emits extra callbacks" must not be broadened into one.
* **"Not seen on the shipped profile" is a rate, not immunity.**

## If the soak produces a finding

Restart the count at zero, file the finding with a number, and add one sentence
to this file saying which criterion caught it. That sentence is the record of
whether this gate was worth setting — and if three consecutive soaks are broken
by findings, the honest conclusion is not "wait longer" but that the lineage
needs a different kind of attention, which is a decision for the user.
