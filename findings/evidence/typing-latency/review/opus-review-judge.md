# opus review of judge.py (2026-10-10; subagent, read-only; same prompt as review-prompt.md). Final report, verbatim. Its mutated copies are in `opus-mutations/`; `opus-mutations/judge-on-opus-mutations.txt` is the main session's own run of the reader on them.

Review of findings/evidence/typing-latency/judge.py (read-only. I ran judge.py on the committed reports and got PASS. Mutated copies are in scratchpad/opus-review/: m1–m4.)

BLOCKING: none. I could not build an honest probe run that this reader would judge PASS when §15.8/§15.6/§15.2 say FAIL, or the other way round.

Q1, cells. Every gated cell is present and the comparators are right:
- (a) max < 2×gap, strict: judge.py:108
- (b) median < gap: :111
- on-screen median < 70 Chrome / < 90 Firefox, both owner gaps: :43, :103
- on-screen max < 150: :105
- (ii) not None: :117
- boundaries median <= 10: :114
The page, runner, browser, document, gap and chars are all bound (:85-90). The runner is the full 16-hex string, which matches probe:123.
On-screen is computed from `rows`, not from `summary` as condition 2 says. For a complete run the two are identical (probe:179-181, 203). For an incomplete run, reading rows is stricter.
Extras, which can only add FAILs: "every key committed / on screen" on all three slots (:95-98); (ii) on boundaries; Chrome gap-200 max < 150. That last one is not in §15.2's Chrome cells, but ruling condition 2 asks for "max both gaps". All extras pass on the six reports.
Median is the upper median (:48-50). That matches the spec's own numbers (65.3, not 65.25). It is conservative: in m4, sorted[9]=78 and sorted[10]=81 give FAIL at 81, where a conventional median of 79.5 would pass.

Q2, honest-run accidents (none flips a verdict):
- Page drops one insert (the finding-119 class). I recomputed the rows from raw with the probe's own logic (probe:157-177) and the recompute reproduces the committed rows exactly. m1, Chrome, key 15 lost:
  - keys 15-18 read 140.7-148.7 ms commit and up to 135.8 ms on screen;
  - (a), (b) and the on-screen median/max all PASS;
  - only the every-key gates catch it (19 of 20), and in a real run so would (ii), because final = base+len(keys) is never reached (probe:186).
  Note that when `commits` is empty, the (a)/(b) and on-screen lines are skipped silently (:101, :106). The verdict then rests on the every-key gates alone.
- Probe crash or partial run (m2: header only, written in probe's `finally`). The reader exits 1 (FAIL: 0 of 20, (ii) None), not 2. That is still a non-pass, but §34.1(a) routes a crash to "rerun that step", while a FAIL routes to the stop rule. Register one line; no code change.
- A truncated JSON file gives REFUSED (:81). The probe always writes a dict, so a traceback path is not reachable.

NON-BLOCKING:
1. Premise note for the owner/fable (not a reader bug). The probe's gap is release-to-next-press (probe_111_overtake.py:108, 116-122).
   - Measured press-to-press medians: "gap 80" = 98.1 ms Chrome / 108.6 ms Firefox; "gap 200" = 217.1 / 231.6.
   - Thresholds built from the nominal 80 are stricter than the cells' own meaning ("two behind", "keeps up"), so there is no false PASS.
   - But the run is lighter than 80 ms typing, and the ruling's "utilisation ≈0.8" (fable-ruling.md:142) is really ≈0.60 Firefox / 0.46 Chrome.
   - The reader computes b_i from this spacing (:126) but never prints it. Register it; under §34.4/§9 it is not a code change without a witness.
2. The ruling's red-case list is all present, with these gaps:
   - Every-key gates: no red case at all, yet they carry §34.2's partial-run / crash / missing-key accidents. I showed them red (m1, m2); file that as the evidence, no code change.
   - Boundaries median: no red case. I checked the boundary: 10.0 passes, 10.1 fails (m3, m3b).
   - On-screen and (ii): red only inside R1, which exits 2 (REFUSED). Never red on a bound report, never at gap 200, never at Firefox's 90 threshold. A swapped per-browser threshold dict would pass base and R1 alike. That is a constant, outside §34's threat model, so it does not matter.
3. Q4, R2 handling. Running the ruled case verbatim and recording that it trips (a) too is right: 82.6+80 = 162.6 ≥ 160 at key 9 (judge-red-cases.txt:77-78). Isolating (b) per browser with R2′ (max 134.8 / median 125.2) and R2″ (97.6 / 80.3) is also right. Two remarks:
   - The correction exists only in commit abddfe38 and the docstring at judge_red_cases.py:9-11. SPEC-M3-production-ui.md:644 still says "+80 → 只有 (b)" with no appended correction. Per CLAUDE.md §10, append a correction line there.
   - R1 shows (a)+(b) red but exits 2, not 1. Exit 1 with both red is shown only by R2.
4. Named limits, register only:
   - `page` hashes dist/e2-editor-app.js alone (probe:122), so other dist files and e2-editor.html going stale is invisible (finding 094's class).
   - The owner document (build/scratch-m3-production-ui/PMPC指南.odt, untracked, mtime Oct 6) is not hashed. Canvas heights are the only fingerprint: 17929 Chrome / 22257 Firefox, the same within each browser's owner runs.

I edited nothing in the repo and did not run judge_red_cases.py.
