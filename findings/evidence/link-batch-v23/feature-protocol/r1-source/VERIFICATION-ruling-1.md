# R1 ruling 1: reader verification, 2026-10-27

This records conditions C1-C4 after the 27c handoff. It is not a counted R1 verdict. No product, profile, shell, runner or reader implementation changed in this checkpoint.

The old preparation re-read assertion was red on all 22 S5 pages because the current reader adds `emptyMark: null` and `emptyMarkWitness: null` to their old configurations. It now adds only those explicit defaults to the expected record and still compares every field. The independent native-deletion assertion skips witnessed empty-mark rows, whose missing native oracle is intentional under ruling 4; it previously raised a TypeError. Neither update suppresses a verdict, reason, reference or non-default record value.

`test_v23_feature_r1.py::PreservedPreparationRereads::test_r1_prep_01_only_adds_empty_stale_fields` verifies every report-listed page's retained decompressed sha256 and complete inspection. All 12 Chrome and 12 Firefox pages remain PASS with only `staleFields: []` added. The existing `test_stale_reply` passes its four C1 scenarios; `test_token_wrap_exposure_is_recorded_not_decided` is unchanged.

Commands from `wasm_sdk_probe/`, all exit 0:

```text
python3 -m unittest discover -s tests -p 'test_v23_feature_selection.py' -q
  Ran 50 tests in 37.240s; OK
python3 -m unittest discover -s tests -p 'test_v23_feature_r1.py' -q
  Ran 50 tests in 23.831s; OK
python3 -m unittest discover -s tests -p 'test_v23_native_s5*.py' -q
  Ran 12 tests in 1.308s; OK
```

Mutation census, from the repository root:

```bash
python3 -I findings/evidence/link-batch-v23/feature-protocol/r1-source/reader-mutation-sweep.py --out findings/evidence/link-batch-v23/feature-protocol/r1-source/reader-mutation-sweep.ruling-1.output.json
```

Result: **ALL_KILLED, 62/62**, comprising 56 AST-enumerated condition checks and 6 defining-expression mutations; no survivors; both unmutated baselines green. The new stale condition is present as `r1_arm:707:need` (`measured move reply stale`). Output sha256: `9a5004686580902cb2df02995e1a1294f2131df14876d46b3f2b325c53e133c6`. The output binds the current reader and test hashes. The previous `reader-mutation-sweep.output.json` is preserved as the earlier 61-mutation measurement rather than overwritten.

C5-C6 still govern a future counted invocation: full population, historical pre-red prerequisite, committed inputs and no concurrent measurement sharing the instrument closure. No counted R1 run has started here.
