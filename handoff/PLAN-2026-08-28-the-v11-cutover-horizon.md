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

---

# Addendum, 2026-08-28 — adjudicated amendments

**Append-only.** Nothing above this line is edited. Where this addendum
supersedes text above, it says so and the original stands. Filed here rather
than in a new document because gate criteria split across files invite the
question of which one binds.

Source: an adjudication of four decisions returned 2026-08-28, on a ticket that
asked for rulings rather than advice. Its reasoning is not reproduced; its
rulings and their acceptance criteria are.

## The rule this addendum obeys

Criteria may be **added** to a running gate — the prohibition is on **moving**
one after runs exist against it — but only under all four of:

1. **Fixed before satisfaction.** Written before any run that would count
   toward it.
2. **Forced, and named.** The addendum names the measurement or defect that
   forced it. "It occurred to me" does not qualify.
3. **Form-tested.** Each criterion must be a predicate a named run either
   satisfies or does not. Anything resting on a future judgement call, or on a
   hand-maintained enumeration, does not enter the gate; it goes to *Work
   items* below.
4. **A cutoff.** *No criterion may be added after the twelfth clean run banks.
   The gate opens on the criteria in force at that moment; later concerns become
   findings or post-cutover work.*

**Count semantics.** The twelve runs measure the **clean-run predicate** — the
three bullets under "Clean means all of". Additions that leave those three
bullets untouched do not restart the count. Any change to those three bullets
restarts it at zero.

## Amendments to gate conditions

### A-1 — Condition 4 is superseded by 4a and 4b

**Forcing facts.** (i) Condition 4 as written names no pass criterion: it says
to record what was announced, so the verdict falls to whoever is in the room.
(ii) The owner states they cannot supply a screen-reader session. (iii) All
existing §3.4 accessibility-tree evidence predates this profile and was taken
through `gate_mirror()` in `tools/probe_aria_projection.py` — a **fourth**
page-construction path, separate from the `repointed_page()` consolidation that
exists precisely so the page measured is the page that ships.

**Ruling.** The benefit has two links: engine → page → accessibility tree, and
tree → one AT's announcements. This tree has already ruled on the split
(`findings/evidence/aria-projection/RESULT.md`, Scope): *"'a11y needs a human'
is wrong; 'one AT's reading behaviour needs a human' is right, and it is a much
smaller claim."* Link one is machine-measurable and blocking. Link two is
recorded, not gating.

#### 4a — blocking, machine-checkable

**Precondition.** `tools/probe_aria_projection.py` must build its page as the
**fourth caller of `repointed_page()`**, not as a fourth implementation.
Keeping `gate_mirror()` for this measurement violates the consolidation it
would be relying on.

A 4a run passes iff **all** of:

1. **Identity** — built via `repointed_page()` with
   `--candidate-profile e2-editor-v11`; the report carries a `pageSha256` equal
   to the one the banked soak reports carry; profile and five bound identities
   named in the report.
2. **Text** — all 9 paragraphs of `list-contexts.odt` appear in
   `Accessibility.getFullAXTree`, compared **in code** against the fixture's
   `content.xml`.
3. **Structure** — the heading carries AX `level: 1` matching the ODT
   `outline-level`; 4 `listitem` nodes inside 2 `list` containers.
4. **Focus follows the caret** — three placements, three distinct readings,
   each matching the paragraph targeted, compared in code.
5. **Repetition** — three runs, identical on terms 2–4.
6. **The instrument can fail here** — one mutation run on the candidate path
   reddens exactly the projection term(s) and nothing else; the page is
   restored; the mutation run is stamped and never banked.
7. **The delta is measured, not inherited** — one run of the same instrument on
   the shipped v8 page shows `documentTextInTree: false` and the region
   carrying its reason sentence. Node counts recorded, not thresholded.

**If 4a is never run, the gate stays closed.** It is the only measurement of
what the size cost buys. Any term unmet: fix and re-run; the criterion does not
move.

*Clean-run predicate unchanged — the count does not restart. 4a is a separate
condition, satisfied by its own runs.*

#### 4b — folded into condition 3's manual round

During the human manual round: Orca on, arrow through the open document
(including one heading and one list item), Orca off, **with speech captured to
a log**. The record is the log, not memory.

* **Mechanical half — gating.** The log contains the words of the focused
  paragraphs as focus reaches them, and the heading announced as a heading with
  its level. If focus lands on a paragraph and its text never reaches the log,
  the cutover blocks until root-caused.
* **Judgement half — recording only.** Announcement order, verbosity,
  double-spoken list bullets (`queue-list-prefix-read-twice` predicts exactly
  one annoyance here — the log confirms or refutes it), browse-mode behaviour.
  **This is a criterion satisfied by human judgement, and it is created
  knowingly**: the residue is assigned to human observation by this tree's own
  scope ruling, it is non-blocking by construction, and its output is an
  observation record rather than a verdict.
* **The escape, named.** If the owner cannot or will not operate Orca at the
  manual round, that is recorded and 4b converts to a deferred obligation: one
  Orca session on the live page **before the institutional-buyer
  demonstration** — owner-run, or agent-driven with the owner's explicit
  consent to an agent driving their desktop session, since the log-based
  mechanical checks are equally valid however the keystrokes were produced.
* **If 4b never happens at all**, the cutover proceeds on 4a alone, with the
  deferral written into the record, and the existing revert trigger ("any
  user-visible regression reported by a human") carries the residual risk.

**Deferred residue, named rather than discovered later**: announcement order,
verbosity, and browse-mode behaviour of one AT; plus
`queue-list-prefix-read-twice` and the 4096-character `textHead` cap.

*Note on why the residue does not block*: the alternative to shipping v11 is
shipping v8, whose accessibility tree carries **zero** characters of document
text (`RESULT.md` baseline: 171 nodes, zero document text). Against a baseline
of nothing, a verified-correct tree is the benefit even before one AT's
rendering is assessed.

### A-2 — Revert-condition 1 is superseded

**Forcing fact.** Measured 2026-08-28: the fifth identity — v8's core data —
lives in `dist/profiles/resources/`, shared by **twelve** profiles, and the
cutover touches none of it.

**Superseded**: "v8's five identities archived with checksums" becomes **"five
identities pinned: four held as bytes, the fifth verified in place."**

Copying ~98 MB into the archive is rejected: it buys self-sufficiency against a
hazard the cutover cannot create, and the hazard it would insure against
(damage to the shared directory) breaks twelve profiles at once, for which a
per-profile archive is the wrong instrument.

But wording alone is insufficient. "A profile is five bound identities" is a
rule about **binding by hash**; the round this tree lost was lost to an archive
whose name claimed bytes it did not hold. An archive that merely *describes*
the fifth identity cannot verify at revert time that the shared bytes are still
the bytes v8 was measured on — the same failure mode in a new costume.

Acceptance criteria:

1. The archive gains `SHA256SUMS.shared` listing `soffice.data` and both
   resource packs with sha256 and live paths under `dist/profiles/resources/`.
2. `sha256sum -c` of that file against the live tree passes; the run is
   recorded in the archive directory.
3. `ATTRIBUTION.md` names all five identities, marks four held-as-bytes and one
   pinned-by-reference, states the fifth is shared by twelve profiles and
   untouched by the cutover, and says plainly: *this archive alone cannot
   restore v8 — restoring requires `dist/profiles/resources/` intact, verified
   against `SHA256SUMS.shared`.*

*Clean-run predicate unchanged — the count does not restart.*

### A-3 — The size figures above are corrected

**This is a factual correction, not a criterion.** The section "The size
decision was made on a smaller number than the real one" says v11's core
filesystem image is three times v8's and attributes that to the writer+calc
core. Measured 2026-08-28 by comparing file manifests
(`dist/profiles/e2-editor-v11/soffice.data.js.metadata`, 1,606 entries, against
`dist/profiles/resources/full-qa-r5.72dd2755c8cd8880.metadata`, 1,358):

* v11's image is a **strict superset** — 0 files present in the product image
  and absent from v11's.
* The 248 extra files are **Calc UI configuration**
  (`/instdir/share/config/soffice.cfg/modules/scalc/…`), **5,741,041 bytes ≈
  5.5 MiB**. Two common files differ in size, net +21,536 bytes.
* v11's image holds **130 font files, 73,153,982 bytes ≈ 69.8 MiB** — the same
  fonts v8 splits into `cjk-r5` (18.6 MiB, startup) and `fallback-fonts-r5`
  (46.8 MiB, **on demand**).
* `base-r5 + cjk-r5 + fallback-fonts-r5` = 102,765,226 bytes, which is
  `full-qa-r5` to the byte. v11's image is 108,527,803.

So the +71.4 MiB decomposes as **+19.0 loader/wasm, +5.5 Calc configuration,
+46.8 fallback fonts no longer deferred**. The writer+calc core costs 5.5 MiB
in the data image, not +70.9. **About 65% of the cost the owner is being asked
to approve is a packaging choice, not the accessibility core.**

`tools/build_r5_profiles.py:create_pack()` slices a pack out of an existing
`soffice.data` by byte ranges from its `.js.metadata` — post-processing, no core
rebuild, no relink. v11 carries both inputs. `resourcePacks: []` is hardcoded in
`tools/build_e2_editor_v4_profile.py` whenever `--core-data` is passed, and its
reason is sound (the existing packs are the *product* core's, and inheriting
them would link one core and load another) — but it does not forbid v11 having
packs sliced from its **own** image. Split that way, v11's
required-before-usable goes from 232.8 to about 186.0 MiB: **+24.6 MiB (+15%)**
against v8's 161.4, not +71.4 (+44%).

**Not verified**: the split has not been performed, no profile has booted from
packs, and the a11y core's font-resolution path has not been shown to match
v8's. The owner's confirmation is owed against the corrected decomposition
either way.

## Work items — not gate criteria

Each was form-tested. None enters the gate; the reason is given.

**W-1 — Close `notice-action-recovers-the-session`, at count zero only.**
Wiring `induce_worker_failure()` as that arm's fallback. **Not a criterion**:
the capability already has a live driver in every plain run, inside
`recovery-returns-what-the-product-promised`, which PASSES on both profiles.
The standing NE is the documented sentinel of finding 046's disposition —
`recoveryPairing.held: true` in every banked report — not an unmeasured
capability. Sequencing is mechanical: a successful close makes the composition
39 PASS / 1 NE, which changes the clean-run predicate and restarts the count.
**So it lands only when the count is at zero**, and the criterion re-freezes at
the new composition before the first counted run.

**W-2 — `a-refused-action-is-reported-and-changes-nothing` is diagnostic-only
by construction.** `refusal_induced = bool(args.refusal_diagnostic)`; the check
keys measurability off the flag, not off an observed refusal. No shipped
manifest withholds an action, so `withheldAction: null` is the manifest telling
the truth; and a manifest that did withhold one would surface in plain runs as
`cut-removes-the-selected-text` FAILing, never as this check being judged.
Mirrored diagnostic runs are excluded from the twelve by the identity rule.
**Not a criterion, and nothing to fix** — the obligation is on the record (see
below).

**W-3 — Four inline-format checks carry no mutation.** Census run 2026-08-28
over the 40 net checks against the 43 entries of `MUTATIONS`: 34 have a
dedicated mutation, 1 (`bold-can-be-turned-off-again`) is reddened only as
collateral, and **5 have none**:
`a-format-that-worked-is-not-reported-as-failed`,
`every-inline-format-reaches-the-document`,
`clear-format-removes-every-inline-format`,
`formatting-survives-the-next-paragraph-break`,
`caret-follows-the-text-you-type`. The last is not a gap — it went red in the
field, 10 of 48, before finding 084's fix, which is stronger evidence than a
synthetic mutation. The other four are all in one family.
**Form test**: a checker asserting every id in `report["checks"]` appears as a
`MUTATIONS` entry's `check` is *tool-closed* — adding a 41st check turns it red
— so this **could** be a gate criterion. **It is not made one**, because it
measures whether the net is honest, not whether v11 may ship; that question is
equally open for v8 and predates this gate. **The coupling is left explicit**:
if any of the four mutations turns out unwriteable because the check cannot
fail, that is a finding, and a finding restarts the soak under the rule already
in force.

**W-4 — A soak aggregator.** No tool reads the twelve reports;
`check_usable_editor.py` reconciles one at a time, so "the gate is open" would
rest on the drafting party's narration. A tool over the evidence directory
reporting count, calendar-day spread, runs per day, NE set per run, and whether
every `candidateCutover.pageSha256` is the same value makes the gate's opening
checkable by someone who was not here. **Not a criterion** — it changes who can
verify the gate, not what the gate demands.

**W-5 — Rehearse step 3.** Freezing a generation and repointing `MANIFEST`, and
un-freezing on revert, was discovered by the revert rehearsal and has not
itself been rehearsed.

## What the cutover record must contain

Beyond what "What must be said out loud in the cutover record" already
requires:

* **R1** For `notice-action-recovers-the-session`: that the NE is the sentinel
  of finding 046's disposition (citing the runner's own text), and that the
  capability is measured in plain runs by
  `recovery-returns-what-the-product-promised` — citing one banked report per
  profile in which it PASSES.
* **R2** For `a-refused-action-is-reported-and-changes-nothing`: that no
  shipped configuration withholds an action; that the check is judgeable only
  under `--refusal-diagnostic`, which is mirrored, diagnostic-stamped and
  excluded from the twelve; and the date and path of the most recent diagnostic
  run in which it PASSED, **per profile — or the explicit sentence that none
  exists.** Plus: *owed at the next manifest that withholds any action.*
* **R3** The deferred accessibility residue of 4b, in the words used above.
* **R4** The corrected size decomposition of A-3, and whether the owner's
  confirmation was taken against it.

---

# Addendum part 2, 2026-08-28 — the cost correction, adjudicated

Labelled **B-n** to avoid collision with part 1's A-n, which are different
items. Same append-only rule; part 1 is not edited.

Part 1's **A-3** recorded the corrected size decomposition. That correction was
independently re-derived by the adjudicator from the same two metadata files
before these rulings were issued, reproducing every figure. It then forced a
decision part 1 did not face.

## B-1 — The correction's required form

The plan's sentence *"v11's core filesystem image is three times v8's — that is
the writer+calc core the ruling accepted"* is **measured false**. Part 1 §A-3
carries the correction; it must also carry, and now does:

* both metadata paths — `dist/profiles/e2-editor-v11/soffice.data.js.metadata`
  (1,606 entries) and `dist/profiles/resources/full-qa-r5.72dd2755c8cd8880.metadata`
  (1,358);
* the reconciling arithmetic — `base-r5 + cjk-r5 + fallback-fonts-r5` =
  102,765,226 bytes = `full-qa-r5` **to the byte**;
* the sentence: **about 65% of the previously quoted cost is a packaging
  choice, not the accessibility core.**

| component of the +71.4 MiB | MiB | nature |
|---|---|---|
| loader + wasm | +19.0 | the a11y+calc core's code — irreducible without a relink |
| Calc configuration in the data image | +5.5 | content of the chosen core; removal would be an image edit, **not ordered**, recorded only |
| fallback-font pack no longer deferred | +46.8 | **packaging choice**, reversible by `create_pack` post-processing |

Factual correction, not a criterion change: the clean-run predicate is
untouched and the count does not restart on its account.

## B-2 — Which candidate the gate measures: a bounded split probe

The correction creates a decision: ship unsplit v11 at +71.4 MiB, or split its
image the way v8's is split and ship at ≈+24.6 MiB. Asking the owner to approve
+71.4 while +24.6 may be two days away invites exactly the re-litigation this
gate exists to prevent — the 2026-08-20 ruling accepted +19.9, and +24.6 is
near it while +71.4 is 3.6× it.

**Ruling.** Attempt the split **now, in parallel with the soak**, under a hard
bound of **2 calendar days from 2026-08-28**. The soak on unsplit v11 keeps
banking runs meanwhile. At the probe's verdict or the bound, whichever comes
first:

* **Verified** → the split profile (fresh five identities; its packs are its
  own files, referenced only by its own manifest, never placed where the
  product core could inherit them) becomes the gate's candidate by appended
  amendment. **The soak count restarts at zero** — forced by this tree's
  version-is-identity rule, not by judgement. Identity-bound evidence to
  re-earn, enumerated now: the twelve clean runs, the three diagnostic runs,
  the revert rehearsal (new hashes), the ODT round-trip both ways, the
  NE-composition confirmation, and 4a. The human manual round (condition 3)
  runs **once, on the final candidate only**. With ≤3 runs banked at the bound,
  a restart costs no more calendar than the ≥3-day spread the soak needs
  anyway.
* **Not verified by the bound** → unsplit v11 is the candidate, **frozen**: no
  split work may touch the candidate until after the cutover. A candidate that
  keeps improving under the gate never finishes soaking. The split becomes the
  first post-cutover profile, with its own gate.

**Probe pass criteria, fixed before the probe — all four:**

1. **Reconciliation** — `create_pack` splits v11's image into base plus packs
   whose file sets and bytes reunite to v11's image exactly, verified from the
   metadata.
2. **The net** — the split profile boots and one product-path run reconciles
   clean: 38 PASS / 2 NE, the same NE set.
3. **The lazy path, both directions** — startup does **not** fetch the deferred
   pack (observed in network requests; deferral is the point), and opening a
   document that requires a fallback font triggers the pack fetch and renders
   it, with no font regression on the CJK fixture. This is the named unverified
   item and it is the probe's reason to exist.
4. **The figure** — required-before-usable recomputed from every file the split
   manifest references, by the plan's own counting method.

Any criterion unmet, or the bound expiring, is **not verified**. No partial
credit, no extension. **If the probe is never run at all, the gate proceeds on
unsplit v11 at +71.4 MiB.**

## B-3 — What condition 4 weighs against, and the owner's confirmation

**4a and 4b are unchanged** — criteria, blocking status, escapes, all of it.
The benefit measurement does not get lighter because the cost got smaller:
even at +24.6 MiB, and independently of cost, the plan's own reason for
condition 4 stands.

What changes:

* The cutover record's cost sentence weighs the benefit against the cost of
  **the candidate that actually ships** — ≈+24.6 MiB (+15%) if the split
  profile ships, +71.4 MiB (+44%) if unsplit v11 ships — with B-1's
  decomposition table shown in either case.
* The owner's confirmation obligation is restated: **the confirmation is
  against the shipping candidate's measured figure, never against +19.9, and
  never against +71.4 if +71.4 is not what ships.** If unsplit v11 ships, the
  confirmation must be accompanied by the sentence that ~65% of the figure is a
  packaging choice with a named, already-probed or probe-expired follow-up — so
  the owner approves the number knowing which part of it is removable, and
  when.

Acceptance criterion: the record quotes one of the two figures, names that
candidate's five identities beside it, and carries the decomposition table; a
reader can recompute the figure from the shipped manifest's referenced files.

