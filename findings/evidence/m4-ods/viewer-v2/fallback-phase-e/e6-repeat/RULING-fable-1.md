# RULING-fable-1: E6's leak half on `ods-viewer-v2` `e96e01ec` (2026-10-22)

External adjudication, read-only. Read: CLAUDE.md criteria-form sections 1-11; SPEC-M4 §4 E6 row, A6.1, A6.2, A7.1; SPEC-M4-viewer-v2 §4, §7.4, §7.5; this directory's README and `runs.txt`; `run_ods_viewer_e6_leak.py`; `ods-viewer-e6-harness-app.js`; `probe_engine.cpp` at `emitStage`, `closeDocument`, `handlePartInfo`, the open stages; the raw per-cycle stage lines of the B run, the counted run, three rising runs (two v1, one v2) and v1's two 10-20 reports. No measurement was run.

## 1. Rulings

**Q1 - v2 `e96e01ec`: proceed, conditional on one append-only spec addendum; no link, no engine change.**
- The counted run `e6-leak/report-2026-10-22T021502Z.json` stands as a red report. Commit it unchanged (it is still untracked). Its `E6 reopen bound` verdict is void because the criterion it judged is withdrawn; its `E6 reopen shape` and boots verdicts stand.
- A7.1's leak sentence ("from cycle 3 the series no longer rises") is **withdrawn** under CLAUDE.md §4. It is not replaced by another sbrk bound (no "allow 8 KB", no "run until flat", no "until explained").
- E6 for a viewer link becomes: peak half (unchanged, counted runs stand) + reopen shape (unchanged: 5 cycles on one engine, each with `document-destroy-enter`, peak < 939,524,096, tiles == parts) + reopen series **recorded, not judged** (the tool's existing `--bound`-absent path, `notJudged`). B is still measured per link as the boots' witness.
- Register limit `L-E6-leak-sbrk` for the engine family (both links) and a finding with the 14-run table. §3 kind: a real hole (behaviour with nothing guarding it), not "nothing to guard".
- Counting: nothing resets. B stays 0 (unchanged, so SPEC-M4 §4's "B changed" clause is not triggered). Peak-half runs stand (A7.1 already separates the halves). The leak bound has no counted run because it has no criterion.
- Never-done default: if the addendum is never written, 021502Z stands red and the E6 row's default ("stop") applies to v2 - and, by the same rule, to v1. Inaction is stop for both links; the addendum is the owner's act.
- Order: addendum first, then the E6 line in viewer-v2's tracking (§7.6), before Phase H on v2 starts. The other v2 criteria (V2-160 x3 etc.) are untouched by this ruling.

**Q2 - v1 `f6ab3cdb` and host 0.2.31: status unchanged, one record corrected.**
- v1's 10-20 leak-bound PASS (`phase-e/e6-leak/report-2026-10-20T135556Z.json`) is **void, not failed**: a pass of the withdrawn criterion, in the shape where that criterion cannot see growth (reason R2). Append one line: v1's E6 = peak half + shape; reopen series recorded; same limit. SPEC-M4's Phase H foundation line (~845) keeps citing 135556Z for shape and B only.
- 0.2.31 stays what it is: an uncounted daily candidate, never counted-passed, not recalled. H1-H7 never depended on the reopen series, and the product session disposes its engine on close (A6.2), so the reopen path does not exist in the host product. Nothing about 0.2.31 may become "counted" on leak-half evidence - that was already true.

**Q3 - diagnostics and criterion changes.**
- Option C is rejected by the repo's own rules: "red until explained" is a criterion quantified over a future judgement (§2), and keeping a criterion whose premise is falsified while the explanation is sought is the machinery §4 forbids. It would also hold the owner's daily candidate red over 8 KB per cycle on a path the product cannot take.
- Option B's instrument (`mallinfo().uordblks` on stage lines) is **not required and not now**: it is a new mechanism (§4 self-check), it needs a link, and - the A6.2 lesson, already broken once by A7.1 - its shape must be measured before any criterion is written on it (LOK's first-use caches will make live bytes rise over the first cycles too). If the owner wants the number, batch it with the next engine link and record one run before writing anything judged.
- Option A (20 cycles) is **allowed, optional, as the finding's measurement only**, after the full-corpus run has reported done. Readings are pinned in §3. No outcome of it changes Q1 or Q2.
- Form check: `E6 reopen shape` is form 1, unchanged. The limit and the finding are registrations. The intra-open growth item (reason R3) could be written as form 1 but has the same sbrk blindness, so it is a work item, not a gate entry (§9 condition 3). Nothing is added to the running gate.

**Q4 - the main session's reading.** Right: not a v2 regression; A7.1's premise fails under repetition; v1's PASS was one run; sbrk cannot separate live growth from allocator placement. Wrong or missing: see R1-R5. The decisive miss is R2 (the green never had detection power) and R3 (the stop is on the wrong question).

## 2. Reasons

- **R1. `HEAD_STEPS = 2` is the falsified premise written as code.** "The first two steps build the high-water mark" came from one run's shape. In 5 of 14 runs the tile-sized step arrives at cycle 4, cycle 5, or not at all. A 5-cycle series judges two steps of a process that 14 runs show is placement-dependent (boots are x5 identical on both links; one warm engine is not).
- **R2. In the common shape the criterion cannot see growth, so its green is not evidence.** Flat runs show exactly one 4,194,304-byte step at cycle 2 and then 0, 0; the two late-step runs show 4,190,208 and 4,186,112 - the tile minus the 4 KB / 8 KB extensions that preceded it. The reading that fits every row: when the cycle-2 tile buffer lands at the top, closing frees it back into the top region and anything smaller than that slack is absorbed; when it lands in an interior hole, the top is tight and the small steps show. So Δ_3 = Δ_4 = 0 means only "less than about one tile buffer of growth over two cycles". v1's 10-20 PASS and 9 of today's 14 greens say nothing finer. §6: the selftest's red cases were synthetic; the criterion was never shown to catch a real 8 KB per cycle, and in this shape it cannot.
- **R3. The stop is on the wrong question.** A6.2 declares that `OdsViewerSession._release` disposes the engine on close: reopen on one engine is unreachable from the product. The engine growth that can reach a user is intra-open - many tile paints while scrolling, repeated sheet switches on one document - and E6 measures none of it. The honest registration is: reopen growth recorded + limit; intra-open growth = unmeasured work item. Holding v2 and v1 red on the reopen series protects nobody.
- **R4. Where the growth is.** In all 14 runs, open.begin → open.query-metadata is flat from cycle 2 on (both links); every byte after cycle 1 lies between `open.query-metadata` and `document-destroy-enter` (setPart / render / close). Cycle 2 adds 28,672 or 32,768, later cycles 8,192 each. This doubly excludes v2's per-open part-info (v1 shows the identical series, and the growth is not in the open phase); the `handlePartInfo` free() reading was correct and unnecessary.
- **R5. Smaller points.** 3/7 vs 2/7 is not a rate difference at these counts; only the shape is comparable, and the session treated it so. The README's reading 1 ("stop and hand to the owner with the counts") was itself a judgement-shaped criterion; this ruling closes it. The tool's default `--out` is v1's counted directory (`phase-e/e6-leak`): diagnostic runs must always pass `--out`, as today's did.

## 3. Readings to pin before any further run (Option A, if run)

- Setup: `--profile` alternating v2 / v1, `--entries ladder/one-cell-a1.ods`, `--cycles 20`, **no `--bound`** (record-only), `--out .../e6-repeat/cycles-20/<profile>/`. Six runs per link, stop at six whatever they show (§2). Start only after the background full-corpus run has reported done.
- Classify each run by Δ_2..Δ_19: **tight** = no step ≥ 4,000,000; **slack@k** = first step ≥ 4,000,000 at cycle k. The informative segment is cycles 2..k-1 (tight: 2..20). **slack@2** is *uninformative* - label it so, never "flat" or "pass"; it bounds growth only by one tile buffer.
- **R-linear**: within an informative segment of ≥ 10 cycles, every step after cycle 2 is 8,192 (a single 0 tolerated) → finding wording "about 8 KB per open-close cycle on one engine, linear over 20 cycles; unreachable by the product session".
- **R-saturating**: steps after cycle 2 become 0 and stay 0 for ≥ 5 consecutive cycles inside the segment → "allocator drift that settles".
- **R-other**: any informative step > 65,536 outside [4,100,000, 4,300,000], or steps that grow cycle over cycle → record the series, reopen the finding; still not a gate (same path); the owner decides whether it is worth the mallinfo link.
- Yield rule: fewer than two informative segments of ≥ 10 cycles per link after six runs → record the yield and stop; do not run until it speaks.
- Default if never run: the finding stays "8 KB per cycle over 3 cycles, both links, linear-vs-drift undetermined". Nothing else changes.

The addendum must contain: (1) the withdrawal and its reason (R1, R2); (2) E6's new composition for a viewer link; (3) the limit, the finding number, the intra-open work item; (4) counting: nothing resets, 135556Z's and 021502Z's bound verdicts void, their shape verdicts stand, line ~845 reads 135556Z for shape and B; (5) the never-done default: stop, both links.

## 4. Not verified

- That the product session disposes the engine on close: taken from A6.2's text; the session source was not in my file list.
- Whether the v2 SDK issues part-info per sheet on the harness path: not read; irrelevant, since v1 shows the same series.
- The allocator placement account in R2 is an inference from the numbers (exact tile-sized steps; late steps equal to the tile minus the prior small extensions), not a reading of dlmalloc. The ruling rests only on the observed fact that flat runs show one tile-sized step and tight runs show the small steps, not on why.
- I did not run the selftest or any report-reading tool beyond printing the stage lines of the named reports.
