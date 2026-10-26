# Brief for fable: ruling 3, addendum 1 — is run 03 the type oracle, or run 02 with fallback A?

Requested under the owner's authorization for this session ("難以決定的地方就發給fable，我授權他替我裁決"). This is a question about the reading of your own ruling 3 (`RULING.md` in this directory, quote block). Reply with a ruling text (to be appended verbatim as "Addendum 1") plus a plain-language rationale for the owner.

## What happened (all numbers reproduced by the coordinator)

1. **Run 02** (`../s5-native/run-02/`, `run-02.README.md`): the ruling's harness, 56 type cells, exit 0. The reader (`read_v23_native_s5_type.py`, written to the ruling's clauses) read 10 cells witnessed and **46 cells NE**, every one for the single reason `between-read does not complete before the x post`. Cause: the harness printed doubles with C++'s default six significant digits, so past 1000 ms the between-read end and the x post were printed as the same 0.01 ms value (e.g. 1141.75 / 1141.75). In the same 46 cells, the between-read selection text equalled all three native rounds; no other clause failed. Reading preserved as `../s5-native/reader-02.precision-defect.json`.
2. **Fix**: one line, `std::cout.precision(15)` (commit `77e4caad`). New build `type-build-02/`, fresh directory **run 03** with all 56 cells (not only the 46). Run 02 kept unchanged.
3. **Run 03** (`run-03.README.md`, `reader-03.json` `30530678…0706`): 56/56 witnessed, 47 `selection-before-x`, 9 `settle-only`, 0 fallback; between-read end to x post 0.26–0.46 µs.
4. **Run 02 vs run 03 after-save paragraph text: 56/56 identical.** So the oracle *content* is the same either way; what changes is the reference *kind* for 46 cells (native vs settled-WASM) and the counted run's length (settled arms for the 25 Left/Right of those cells; Home/End cells already run a settled arm).
5. The S5 plan (`v23_feature_selection_cases.py`, HEAD `ef0e6792`) binds run 03. An independent opus review (`implementation-review/REVIEW.md`) found no path to a false PASS on the bound data, and raised this as its item A: the ruling says "if run-02 cannot produce witness (ii) for a cell … that cell uses the fresh settled-WASM reference" and "(iii) a cap result or missing between-read is NE, no retry until green"; run 03 replaced run 02 wholesale after a harness change, which needs your explicit acknowledgement.

## The coordinator's position (attack it)

Run 03 should stand as the type oracle. Reasons, each a claim you can check:

- "No retry until green" forbids re-running a nondeterministic witness until a lucky pass. Here the defect was deterministic (output formatting), identical in kind for every cell, and independent of what Writer did; the fix is named and forced by a measurement (run 02), as CLAUDE.md §9 condition 2 asks; the re-run covered the complete population in a fresh directory, not the failing subset; run 02 is preserved.
- The ruling names run 02 as "native run-02", meaning the type-only native run it prescribes; run 03 is that run with the instrument repaired. The fallback A trigger ("the settle itself does not hold the Shift state") describes a product/Writer-side failure, which run 02 does not show (texts 56/56 equal rounds).
- Choosing run 02 + fallback would replace 46 Writer-parity references with self-consistency references for a reason unrelated to Writer, which the ruling itself calls the weaker oracle.

Counter-position worth weighing: the ruling's text is per cell and literal; a reader-measured NE was produced and then superseded by a new run, which is the shape the rule exists to stop, and the implementer chose the re-run.

## Second, smaller item (review item E3)

The plan sends **any** per-cell NE of the type reader to fallback A, not only witness-(ii) failures (e.g. a missing save or a setup mismatch would also fall back). The ruling's trigger is witness (ii). Run 03 has 0 fallbacks, so nothing is affected now. Options: (a) keep, recorded as a named widening; (b) narrow: a non-witness cell failure makes the plan refuse to build (S5 cannot count until resolved).

## What is not asked

The deletion families (ruling 2), S1–S4, and the reorder layer (finding 166) are out of scope. The other review items (test gaps, a judge check of `nativeOrderWitness`, record wording) are being fixed by the coordinator as instrument hardening; none changes a criterion.

## Sequencing

The counted S5 run (588 cells × 2 browsers, about 7.3 h) is ready and waits for this addendum. No counted S5 cell exists, so nothing resets.
