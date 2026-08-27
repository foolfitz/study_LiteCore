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
clock at zero** and is written up as a finding before the count resumes.

**Soak run 1 of 12 is done** (2026-08-28): 38 PASS / 2 NE, `ok: true`, the
checklist reconciling as a candidate-cutover with `problems: []`.
`soak-run-01-candidate.json` in the evidence directory.

Known already to be capable of restarting it: `clear-format-removes-every-inline-format`
abstained once on a shipped-profile run and once on the post-cutover rehearsal
run — one occurrence on each side, so it is an intermittent that predates this
work and belongs to neither profile. When it lands inside the soak the clock
restarts anyway. That is the criterion working, not a reason to carve an
exception. A
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

## The size decision was made on a smaller number than the real one

The 2026-08-20 ruling that brought accessibility forward accepted the
writer+calc core at **+19.9 MB**. That figure is the **wasm alone**, and the
wasm is not what an institution downloads.

Counted 2026-08-28 from every file each manifest actually references:

| | `e2-editor-v8` | `e2-editor-v11` | delta |
|---|---|---|---|
| `probe.js` + `probe.wasm` | 110.1 MB | 129.1 MB | +19.0 |
| `soffice.data` (core filesystem image) | **32.6 MB** | **103.5 MB** | **+70.9** |
| `cjk-r5` pack | 18.6 MB, at startup | — folded in | |
| `fallback-fonts-r5` pack | 46.8 MB, **on demand** | — folded in | |
| total bytes | 208.3 MB | 232.8 MB | +24.5 |
| **required before the editor is usable** | **161.4 MB** | **232.8 MB** | **+71.4 MB, +44%** |

Two structural differences, not one:

1. v11's core filesystem image is **three times** v8's — that is the
   writer+calc core the ruling accepted, and the ruling's number did not include
   it.
2. **v8 defers a 46.8 MB font pack to on demand; v11 has no resource packs at
   all.** Everything is in the startup blob, so the lazy loading v8 has is gone.

Neither of these is an argument against the cutover on its own — the second may
even be a packaging choice that can be undone. **But the user's confirmation
must be against +71.4 MB at startup, not against +19.9 MB**, and if the 08-20
ruling was made on the wasm figure then it was made on an incomplete one. That
is for the user to judge; recording it is not.

**Owed, and cheap**: ask whether v11 can carry resource packs the way v8 does.
If it can, most of the second difference goes away and the comparison becomes
+70.9 MB of core image against a 32.6 MB one, which is the honest subject of the
decision.

## The cutover itself, and the revert that must be armed first

The chicken-and-egg — non-diagnostic evidence requires the cutover, the cutover
requires non-diagnostic evidence — is resolved by measuring the **candidate
page**: the page as it will ship, carrying its own pin and its own worker URL,
with its sha256 written into every report. The cutover is then a flip to bytes
already measured.

**The cutover is four steps, not two lines** — step 3 was missing from the first
draft of this plan and the revert rehearsal is what found it. The product page
is the shell bundle's own **entrypoint** and is in its `included` list, so
rewriting two of its lines moves the bundle digest; a run after the cutover
carries no `candidateCutover` stamp and is therefore **refused by
`check_usable_editor`** — measured, not reasoned.

```
# 1  write the page
python3 tools/build_cutover_page.py --profile e2-editor-v11 --write \
        --expect-sha256 <the sha256 every soak report carries>
# 2  stage it where the product is served from
cp web/e2-editor-app.js dist/e2-editor-app.js
# 3  FREEZE THE NEW GENERATION, and point MANIFEST at it
python3 tools/build_e2_c_shell_bundle.py \
        --manifest e2/editor-shell-v2-bundle-v44.json \
        --frozen-date <the day> --write
#    then edit MANIFEST in tools/build_e2_c_shell_bundle.py
```

A revert undoes **all three**, or the tree ships v8 while declaring a generation
whose entrypoint points at v11.

As of this writing that page is
`c8c71ac530c4815aa431c04e2f2e001c34bd025f9b77744bb8fbe6881240a472`. The tool
refuses to write if the produced bytes differ from what was measured, because a
mismatch means the tree moved between the measurement and the cutover and the
honest answer is to measure again.

**Four things make the revert cheap enough to rely on. All four, not some.**

1. **v8's five identities archived with checksums and an `ATTRIBUTION.md`** that
   names what each file is — a profile is five bound identities, not one
   artifact, and an archive named after the wrong hash has already cost this
   tree once. **Checked 2026-08-28**:
   `build/archive/e2-editor-v8-4a2710bb-worker-070229cd-manifest-d70481cb/`
   exists, its `SHA256SUMS` verifies OK for all four files it holds, and all
   four are byte-identical to the live `dist/profiles/e2-editor-v8/`.
   **But it holds four, not five.** The fifth identity — the core data — is not
   in it: v8's `soffice.data` and its two resource packs live in the SHARED
   `dist/profiles/resources/`, which twelve other profiles also reference. A
   cutover does not endanger them (v11 references none of them), so the revert
   is still a flip — but the archive **cannot restore v8 on its own**, and its
   ATTRIBUTION says "the five identities" while listing four. Owed: say so in
   that file, or archive the core data beside it.
2. **No forward-incompatible state.** ABI 4 on both sides, the same 21 actions,
   and the two new manifest fields are additive — but the question that makes a
   revert expensive has to be *measured*, not assumed: does anything v11 writes
   fail to be read by v8? Grepped 2026-08-28: the shell uses no `localStorage`,
   `sessionStorage` or `indexedDB`, and the checkpoint is in-memory, so the only
   cross-version artifact is the **saved ODT**. **Measured 2026-08-28 and it
   round-trips both ways**: a document saved on the candidate opens on v8, and
   one saved on v8 opens on the candidate; in both directions the sentinel text
   survives, the structure is intact and a re-save from the other core is a
   valid ODT. See
   `findings/evidence/queue-v11-cutover-soak-not-started/RESULT-2026-08-28-the-saved-odt-crosses-both-ways.md`.
   **Condition satisfied.**
3. **Rehearse it.** Perform the revert once against the staged setup and run the
   net on the reverted page. A revert that has never been executed is a hope.
   **Done 2026-08-28**: the cutover was performed for real, the net run against
   the real page, the revert performed with the same tool, and the net run
   again — 38 PASS / 2 NE both before and after, the page byte-identical to its
   baseline `28e03e5bc9fcb8c4`, `git status` clean, and the post-revert run
   reconciling `ok: true`. The revert was wired to a `trap … EXIT` so a run
   dying in the middle could not strand the tree. **The rehearsal is what found
   step 3 above**, and step 3 has not itself been rehearsed.
   See `findings/evidence/queue-v11-cutover-soak-not-started/RESULT-2026-08-28-the-revert-rehearsal.md`.
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
