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

## Exact C1 replay against the previous reader

`check-stale-controls.py` additionally replays the four C1 scenarios literally: the candidate reply carries the actual pre-move caret (rather than merely an arbitrary changed coordinate); the candidate reply carries its actual pre-move range selection; the control reply carries its actual pre-move caret; and the candidate reply lacks state. Public-call results and raw wire replies are edited consistently. The clean model must first pass on the archived reader at `2b561678`.

```bash
python3 -I findings/evidence/link-batch-v23/feature-protocol/r1-source/check-stale-controls.py
```

`stale-controls.ruling-1.output.json` records **FOUR_PREVIOUS_FALSE_PASSES_REJECTED**: all four malformed model pages PASS on the previous reader; the current reader gives FAIL, FAIL, NOT_ESTABLISHED, NOT_ESTABLISHED respectively, with the prescribed reasons. The output binds both reader versions, the model and the control script by sha256. These are model controls, not browser observations. The current reader and test file are unchanged, so the 62-mutation census above retains its exact input hashes.


## Shared S5 oracle amendment: refreshed bindings before counted R1

The shared judge changed for the owner-delegated S5 ruling; R1's criterion did not change. `reader-mutation-sweep.settled-native.output.json` refreshes the full-file binding to reader SHA-256 `865651357970a0a9080b8f5f79c8b58ae4493a208350cf2be6a925c209a76a67` and the unchanged R1 test SHA-256 `bcd9421592e50e097f33c10bbebeb505a4b2d49ec5e4f5ae1a238607db4a4560`. All 62 mutations are killed. These exact hashes were checked again after the final settled-native reader/certificate-05 change; neither file changed. `stale-controls.settled-native.output.json` again records FOUR_PREVIOUS_FALSE_PASSES_REJECTED.

Under the final certificate-05 plan, all 50 R1 tests pass (31.105 s), including all 72 model cells, exact C1 red controls and every retained R1 prep-01 page; all 50 selection tests pass (46.564 s). The new settled reader has 18 passing tests and its consumer pages have 11. The independent 14-cell historical prep-05 re-read preserves complete inspections without field ignores. None of these controls is counted browser evidence. Counted R1 remains contingent on its pre-red prerequisite and full fresh population.
