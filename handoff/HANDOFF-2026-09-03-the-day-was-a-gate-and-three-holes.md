# Handoff: the gate advanced, and three checks that could not have caught anything

Written 2026-09-03. Continues
[`HANDOFF-2026-08-29-the-candidate-changed-under-the-gate.md`](HANDOFF-2026-08-29-the-candidate-changed-under-the-gate.md).
The five days between them were idle; nothing had moved.

**In one line.** The cutover gate went from "8 of its conditions written down"
to **everything a machine can settle being settled** — conditions 2, 4a, both
revert conditions, and W-3/W-4 discharged, soak at 8 of 12 — and the day's real
yield was three separate places where a claim was true and **nothing would have
told anyone when it stopped being true**.

## State

`e2-editor-v8` still ships; `web/` and `dist/` both hash `28e03e5bc9fcb8c4`.
**53 commits unpushed**, tree clean, shell generation still **v43**. No relink,
no engine change, no profile repackage.

| | |
|---|---|
| candidate | `e2-editor-v12`, page sha `3dfdcfef4abfe6b7…` |
| soak (condition 1) | **8 / 12**; 2 in-band-dated on UTC 2026-09-03, 6 dayless |
| diagnostics (condition 2) | **DISCHARGED** — 36/36 commits, 0 dropped, guard fired 11/7/6 |
| condition 4a | discharged 2026-08-29 |
| revert condition 2 (ODT both ways) | **re-earned on v12** |
| revert condition 3 (rehearsal **incl. step 3**) | **DISCHARGED** |
| W-3 (mutation coverage) | **DISCHARGED**, and the census it came from was wrong |
| W-4 (soak aggregator) | **DISCHARGED** |
| gates | queue 62 items 0 drifted, E1-C intact |

Two new judges, both with red cases and a green control:
`tools/check_soak_bank.py` (condition 1's counting clauses) and
`tools/check_caret_diagnostics.py` (condition 2).

## 1. The calendar-day clause had no witness, and the ruling went against me

Soak criterion 1 requires runs across ≥3 calendar days. `RUNS.md` defined the
day as "the day of the report's completion timestamp" — and **no report carried
a wall-clock timestamp of any kind**; `run_e2_c_product_path.py` recorded only
`performance.now()`. So the day was knowable only from filesystem mtime (not
evidence; a clone replaces it) or from my narration.

Adjudicated 2026-09-03. **My proposed disposition was overruled in part**: I
wanted to freeze mtime into `RUNS.md` and let the aggregator consume it "labelled
by source". The ruling: mtime and narration are a **§3 registration, not a
source**, and the judgement path may not read them.

What landed:

* the runner writes `startedAt` and `completedAt`; **`snapshot()` writes
  neither**, so a partial from an interrupted run is dayless by construction;
* the day is derived in **UTC**, from a stamp carrying an explicit numeric
  offset. A naive stamp is **RED**, not dayless;
* every report banked before the field existed stays clean, **counts toward the
  twelve, and contributes no day**. The count did not restart;
* runs 7-12 must therefore span ≥3 UTC days by themselves. **The UTC day rolls
  at 08:00 CST**; earliest close is after 08:00 CST on **2026-09-05**.

§4 does not apply, and the test that says so is worth keeping: the new field can
never *change* whether a run happened on a day, only reveal it. Machinery
sustains a claim by changing the world; an instrument reveals whether it holds.

The adjudication also found that **the clause's own motivating example was
uncorroborated**: `RUNS.md` says the voided lineage's run 3 "finished at 00:01";
its mtime is 00:06:23.

## 2. Step 3 rehearsed — and the rehearsal's safety net was tested by an accident

The cutover is four steps. Step 3 (freeze a generation, repoint `MANIFEST`) was
*discovered* by the 2026-08-28 rehearsal and never rehearsed. Now it has been.

Measured, not reasoned — cut over with **nothing frozen**:

```
run ok: True | checklist ok: FALSE
served 14bf3c391c001efb, declared 7e99d3a3b8ba789b
 -- differing paths ['web/e2-editor-app.js']
```

The run is green and the gate refuses it. After freezing `v44` and repointing:
`declared == served`, 38 PASS / 2 NE, `ok: true`. After reverting all three:
back to `28e03e5bc9fcb8c4`, 38 / 2, `v44` gone, `MANIFEST` at `v43`.

**The revert must delete the generation file.** `build_e2_c_shell_bundle.py`
refuses to rewrite an existing manifest whose digest would change, so a `v44`
left behind blocks the next freeze. And **`dist/e2-editor-app.js` is not tracked
by git** (the allowlist excludes `wasm_sdk_probe/dist`), so a revert plan that
assumes `git checkout` can undo the staging step leaves the *served* copy cut
over.

**The trap fired for real.** The first attempt was killed mid-run by the harness
— the script needs ~25 minutes, the background task had a shorter limit. Both
page copies returned to baseline, `MANIFEST` to `v43`, `v44` removed, `git
status` clean; verified before anything else was done. Relaunched under
`setsid`. *A revert that has never been executed is a hope*, and a trap that has
never fired is the same sentence one layer down.

## 3. Three claims that nothing was watching

This is the part worth reading. All three have the same shape: **the claim was
true, and no instrument would have gone red when it stopped being true.**

**The cutover queue item's check was pinned to a superseded candidate.** It
asserted `absent("profiles/e2-editor-v11/sdk-worker.js")` in the product page —
still true after a cutover to *v12*. Measured by building the v12 candidate page
and testing both strings: old check passes before AND after; replaced by
`contains("profiles/e2-editor-v8/sdk-worker.js")`, which goes false on a cutover
to **any** candidate, named or not.

**A new shell generation inherits the wrong ancestor's exclusions.** Freezing
`v44` reported `exclusionsInheritedFrom: v40`. `FROZEN_MANIFESTS` ends at v40
while v41-v43 exist; adding a generation to that tuple is a manual step and it
has lagged three generations. No difference this time — v40 through v43 carry
identical exclusions — **and that is luck rather than mechanism**. The builder
reports the field honestly and no check reads it. Registered as
`queue-shell-generation-inherits-a-stale-ancestor`; not fixed mid-gate, and the
acceptance condition is fixed now: such a freeze must be **refused or reported
as a problem**, not recorded in a field nobody reads.

**W-3's own census was too strong.** It said five checks carry no mutation, four
of them inline-format. Asking instead *has this check ever gone red, and under
what*, over 160 product-path reports: three of the four have gone red **in the
field with no mutation applied** (3, 2 and 2 times), and two of those also go red
as collateral of existing mutations. "Has no mutation" was true only of
*dedicated* ones. **The hole was one check, not four** —
`clear-format-removes-every-inline-format`, 104 passes, 10 abstentions, never
once red. It now has `clear-format-leaves-one-format-on`, measured FAIL with a
**measured-empty** blast radius.

## 4. Two mutations that did not fire, and what they share

Kept in the record. A mutation that fails to fire is worth more in than out.

**`format-success-reported-as-failure`** — finding 059's shape, written to fire
**once** to keep the radius small. It fired in the wrong place:
`the-keyboard-reaches-the-document` presses **Ctrl+B** long before the check under
test, and the page routes the accelerator through the same `editorAction` as the
button, deliberately, with a comment saying so. `THE MUTATION WAS NOT DETECTED`.
**Withdrawn rather than widened**: the check it targets already has two unmutated
field FAILs and two collateral reds, so widening would be machinery sustaining a
claim that is no longer true.

**`clear-format-skips-strikethrough`** — made the target **abstain**, not fail.
`#clear-format` is both the button under test *and* the normaliser `format_arm`
runs before each of its eight arms, so a clear that leaves a format on inverts
the next arm's toggle polarity and MKALLON never got all four.

**The shape both share: a check whose precondition is established by the
mechanism under test cannot be reddened by breaking that mechanism — it
abstains.** Both times I inferred a narrow radius from reading and was wrong in
a direction reading does not reveal. The third version conditions on **state**
(skip only when all four formats are already on) rather than on a count or a
single shot; a count would pass today and go silently inert the moment an arm is
added.

## 5. The double announcement is on the profile that would ship

`queue-list-prefix-read-twice`, characterised 2026-08-23 and never checked
against a candidate. **Present on v12: 4 of 4 list items**, three runs agreeing.
Every list paragraph is `role="listitem"` (from which an AT speaks the marker)
**and** its text begins with that same marker.

Answered **without a new run**, from the AX trees already banked as 4a's
evidence on the same page. The shipped control has neither: `documentTextInTree:
false`, zero listitems — **v8 has no double announcement because it has no
announcement.**

Two instrument errors caught doing it, both mine: a bullet-prefix pattern
counted the *toolbar's own buttons* (`• 項目符號`, `1. 編號`) as document text,
6 instead of 4 — fixed by resolving each listitem through `childIds`, structure
rather than a string that looks like a bullet; and a reproducibility check that
compared `nodeId` declared the three runs in disagreement, when AX node ids are
per-session. *An instrument that reports a difference the product does not have
is the same defect as one that hides a difference it does.*

Not fixed: the obvious remedy slices on `listPrefixLength`, the field finding 074
is about, and any fix is a shell change that restarts the soak.

## What is left, in order

1. **Four more clean soak runs**, and they are blocked on the calendar, not on
   work: ≥2 on UTC 2026-09-04 and ≥2 on UTC 2026-09-05. The UTC day rolls at
   08:00 CST.
2. **The human round with 4b folded in.** Needs the user. `/usr/bin/orca` is
   installed. Expect to hear the double announcement of §5 rather than discover
   it.
3. **The owner's confirmation against +24.5 MiB (+15.2%)**.
4. **53 unpushed commits.** Pushing is the user's step.
5. `queue-shell-generation-inherits-a-stale-ancestor` — post-cutover.

## The direction after this

The owner reordered the roadmap on 2026-09-03: **reading ODS comes before M3
(the Nextcloud app)**. That is the first third of M4 in
`research/ROADMAP-2026-08-20-milestones.md`; ODP and ODG were not asked for.

**One fact reshapes that milestone and was measured today.** M4's gate 0 asks
whether a core with the spreadsheet module builds and loads. It already does —
as a side effect of the accessibility work. `wasm-lite/build-a11y-gate0/
autogen.input` line 3 is `--with-wasm-module=writer calc`, and the candidate's
binary carries Calc while the incumbent's does not:

| literal string, `grep -a -o -F … \| wc -l` over `probe.wasm` | `e2-editor-v12` | `e2-editor-v8` |
|---|---|---|
| `com.sun.star.sheet` | **398** | 16 |
| `ScDocument` | **53** | 1 |
| `ScDocShell` | **18** | 0 |
| `SdDrawDocument` | **0** | 0 |

**Corrected 2026-09-03, same day, by the adjudication that reviewed it.** The
first version of this table said `com.sun.star.sheet` 582 / 21 and named
`grep -a -c -o` as the command. That command reproduces 582 — and it is
measuring the wrong thing: the dots are regex wildcards, so `com_sun_star_sheet`
and every other one-character variant is counted too. `-F` gives the literal
count, 398 / 16. The direction is unchanged and the conclusion does not move,
but a number published with the command that produced it should survive being
re-run by a reader, and this one only survived re-running the mistake.

`SdDrawDocument` is in the table because of what it rules out: the core is
`writer calc`, **not** the `calc impress writer` M4 as written asks for
(`config_host.mk` has `ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS=TRUE`). So gate
0 is paid for **for ODS only**; ODP and ODG still need an owner rebuild, and
`configure.ac` offers no `draw` value — ODG cannot be had without Impress and
Basic.

So the expensive half of that gate — a core rebuild, which is the owner's job —
is already paid for by an artifact that has 8 clean runs on it. The risk moves
to roadmap §6.2 (memory) and to §6.3 (finding 013: the public `open()` rejects
by extension before content detection, verified still true today).

**The memory framing in the roadmap is misleading and was corrected the same
day.** "A single Writer document is `sbrk` 290.8 MB" reads as though the
document costs that. The D4 stage events say `open.begin` is **287,248,384** and
`open.documentLoad-returned` is 290,983,936: **boot costs 287.2 MB and the
document costs 3.7 MB.** It was also measured on `e2-editor-v2`, a writer-only
core; **v12's boot `sbrk` has never been recorded** — no `sbrk` appears in any
v12 evidence. That unrecorded number, not the document size, is what the
headroom calculation actually depends on.

A plan for it was commissioned the same day and is not in this document.

## The push

Nothing has been pushed. `git log --oneline github/main..HEAD` is 53.
