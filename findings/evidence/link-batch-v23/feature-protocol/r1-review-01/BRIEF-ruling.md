# Brief for fable: R1 ruling 1 — three readings to fix before the first counted R1 run

Requested under the owner's authorization for this session. Authority: `handoff/PROTOCOL-2026-10-26-v23-r1-inputs.md` (the R1 protocol). Implementation: commit `2b561678` (`--population r1` in the public selection collector), documented in `../r1-source/README.md`. Independent review: `REVIEW.md` in this directory (no path to a false PASS under the protocol's explicit NE/FAIL list, with one interpretive exception, item 1 below). Real data: `../r1-prep-01/` (12 cells × Chrome and Firefox, 24/24 PASS; the reviewer cross-checked all 24 against native `selectionState`, `cursorAfter` and the native logical landing). No counted R1 cell exists. Reply with ruling text to append verbatim as `RULING-1.md` here, any condition before counting, and a plain-language rationale for the owner.

## 1. What does "late" mean for R1? (review issue 1)

The protocol's last section: "No setup, missing control, a nonpublic candidate request, an uncollapsed result, changed revision, missing required marker/export or a **late**/error/recovery result cannot count as R1 PASS." The R1 reader treats "late" only as timing: the collapsed readback must come at least 500 ms after the move's terminal (the S2 interval) and the marker after the delayed reads. It never compares the move reply's own reported `state` with the delayed readback. The same collector's S2 group does exactly that comparison and FAILs a mismatch as `stale` (S2 contract: `compare: [caret, selection]`, `captureFullState`, minimum readback delay 500 ms). Under the current R1 reading, a reply that reports a stale caret but whose engine state later settles at the correct landing would PASS R1. On prep-01: 0 of 36 arms are stale.

Options: (a) keep timing-only; (b) adopt S2's comparison for R1 candidates (and, if you think it applies, controls), with S2's FAIL/NE classification. Coordinator's lean: (b), because "late" is the collector's own vocabulary for a stale reply, the same range moves are already held to it in S2's 24 plain-on-range cells, and it adds a check that cannot turn a FAIL into a PASS. It would be a criterion added before satisfaction, forced by the review (§9: before satisfaction, forced and named, per-instance form, cutoff = the first complete R1 population per browser).

## 2. Is the v19 pre-red a prerequisite for a counted R1 run? (executor Q2)

The runner (`run_v23_feature_selection.py:192`) and the reader's `main` (`judge_v23_feature_selection.py:921`) refuse any non-preparation report without `--pre-red-report`, a rule inherited from S1-S4. The R1 protocol does not mention the pre-red. `feature-pre-red/counted-05/report.json` re-judges EXPECTED_RED today and was used by `selection-counted-01`. Coordinator's lean: keep the requirement (pass counted-05): it cannot create a PASS, and removing a runner rule is a change with no forcing measurement.

## 3. Token-wrap exposure on six literal cells (executor Q1)

`m1r`, `m1e`, `m1d` × Left/Right. The ten letters selected before the mid-word wrap B occur nine times in the 330-letter token, so if a browser wrapped the token elsewhere, setup would reproduce every recorded semantic including the native selected text, and the absolute literal comparison would read FAIL (with the note "setup not at the native logical position"). The executor deliberately did not add an NE premise because the protocol states none. On this profile the exposure is moot: browser twips equal native twips, W = 101 and B = 89, in both browsers (review). Coordinator's lean: keep FAIL-with-note as the default and say so now, so it is not decided after a FAIL.

## Not asked

The other questions in `../r1-source/README.md` (Q3-Q7) the reviewer found safe and needing no ruling; review items 2-6 are records or false-FAIL/NE only.
