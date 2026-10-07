# Product-path net, v8 vs v17 (spec 26.3 V6, judged by spec 23)

Run 2026-10-07 23:12:46 to 2026-10-08 00:31:42 (+08:00) by `chain.sh` (interleaved, one run at a time, 3 rounds x Chrome then Firefox), per `PREDICTION.md` (committed `f4bcda37` before the run). Runner `tools/run_e2_c_product_path.py` sha256 `b52779e4…` at chain start and end (`chain.log`). Reader `judge.py` (committed `d6db60ea` before the run, red cases in `judge-selftest.txt`); its full output is `judge-output.txt`. The reports do not record browser versions; none was read for this run.

Chain note: the chain's "is another runner present" check matched a stale monitor loop of mine (its own command line contained the pattern it was waiting for) and waited 23:11:45-23:12:46 before the first run; no run overlapped another (`chain.log` WAIT lines, `overlap-sampler.log` absent = no overlap sampled).

## Result

- **P1 HIT**: 12 of 12 reports `complete: true`, `liveness.lastState: ready`, `pageErrors: null`. Chrome runs exit 0; Firefox runs exit 1 because of the one check below that fails on both profiles.
- **P2 HIT**: v8 reports serve `e97d6e03…`; v17 reports serve and name `4c0088c7a518bc36b9cc999d2e67796d20a58525355b68ae67881228dc95b498`, `candidateSource.page` `web/e2-editor-app.js`, `sha256BeforeRepoint` `a3fd9ac1…`, `distPageWasTheSame` false, `restOfShellEqualsSource` true.
- **P3 HIT: 0 red cells of 84** (42 checks x 2 browsers, spec 23 per cell).
- **P4 (descriptive)**: 82 of 84 cells have equal counts. The two that differ are both Firefox:
  - `clear-format-removes-every-inline-format`: v8 2 PASS + 1 NE, v17 1 PASS + 2 NE. Predicted (its precondition `allOnWhenTyped` varied per round on both profiles before).
  - `recovery-returns-what-the-product-promised`: v8 2 PASS + 1 NE, v17 3 PASS. **Not covered by P4's wording** (which allowed differences only on CJK-font cells and the clear-format cell); registered as a miss of the wording. The NE is v8 round 2, whose check says neither inducer put the session into the state where the product offers its recovery button; it is an induction that did not happen on the control arm, not a difference the candidate shows.
- Firefox `an-inline-format-reaches-a-selection`: FAIL 3 of 3 on v8 and on v17 (Chrome PASS 3 of 3 on both), as on v16. Not a v17 effect; cause not looked at.
- Chrome: every round 40 PASS + 2 NE on both profiles, cell for cell equal.

## P4's fixture list (from the fixtures, after the run)

`fixture_cjk_fonts.py` (population = the page's own picker manifest, `dist/e1-fixtures/manifest.json`, 16 fixtures; output `fixture-cjk-fonts.txt`): 6 fixtures carry CJK text and name no Asian font in the pack (5 name none at all; `r7-t2-styled.odt` names Noto Serif CJK SC). None of the 84 cells changed in a way attributable to them: the only count differences are the two Firefox cells above, whose checks do not measure line positions. So on this net, v17's line-height change (V4) did not move any check.

## Not established here

Anything about the owner's document (V5, `../v5/`), the merge runner on Firefox (`../merge/`), or the corpus (`../layout-corpus/`).
