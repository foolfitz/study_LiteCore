# V0′ and E1-C for generation 82 (spec 7.3)

`run_v0_prime.py` is in this directory, derived from `../../v27-176/v0/run_v0_prime.py`; the closed list of differences is in its docstring (a fifth stage v81 from git `a9a04dc64`, F4-81 among the live reds and re-read in its stage, the F3-81 readings among the file readers with `read_v25_f3.py`'s recorded exit 1, put-back target generation 82). Committed `00e3f352f` before its first run; run with nothing serving `dist/`.

## run-01 (`run-01/`): V0_PRIME_RED, one cell, the runner's own argv

Everything held except the v81 stage's re-read of F4-81 (`run-01/restored-v81-f4.json`): exit 0, the same verdicts, but not byte-identical. The only difference is the two input paths the reader records: F4-81's committed `aggregate-judge.json` was made with `…/wasm_sdk_probe/../findings/evidence/v27-176/f4-81/…`, and this runner passed the normalised `…/findings/evidence/v27-176/f4-81/…`. The runner's rule is "the argv of the committed result", so the derivation was wrong, not F4-81.

**Fixed by execution (counted):** the `v81-f4` argv now spells the path as F4-81's did (comment in the runner). run-01's outputs are kept in `run-01/` as they were.

## run-02 (this directory): **V0_PRIME_HOLDS** (`v0-prime.json`, `run.*`)

**Live tree (generation 82), before any restore.**
- The five four-arm readers (v24 A4, v25 F4, v79 F4, v80 F4, v81 F4) are NOT_ESTABLISHED in all four arms, exit 1 each, by construction: they bind the live shell digest.
- The file readers each give output byte-identical to the committed result, with their recorded exit: the B1 self-test, the F3-79 readings, the F3-80 clipboard readings, and the F3-81 readings (`read-01` exit 1, F3_RED by design; `equal-01` exit 0).

**Stages.** Each restores its generation's declared files in source and `dist/`, then re-reads, each byte-identical:

| Stage | Files | Re-read |
| --- | --- | --- |
| v24 (generation 77) | page `b15a6d8e`, client `4616ae17`, narrow `34378dec`/`a4cf3105` | the v24 selection cohort; the v24 A4 judge |
| v25 (78) | page `6e66c930`, same others | the v25 F4 judge |
| v79 (79) | page `9cb6ea1f`, client `7d1c1eb2`, same narrow | the v79 F4 judge; every file reader |
| v80 (80) | page `3b6c023e`, client `7d1c1eb2`, narrow `50f5a2ac`/`d037eaa4` | the v80 F4 judge; every file reader |
| v81 (81) | page `b63d8ee5`, client `7d1c1eb2`, narrow `50f5a2ac`/`d037eaa4` (git `a9a04dc64`) | the v81 F4 judge; every file reader |

**Put back.** `git checkout HEAD --` the four files, then `make e2-c-assets`. Source and `dist/` are generation 82 (page `3b0a2ebb`, client `d07a58e0`, narrow `50f5a2ac`/`d037eaa4`); the v82 bundle line exits 0; E1-C `intact: true` (`e1-c-after-put-back.json`); no tracked file modified.

So generation 82 moved no byte that the carried-over counts or the generation-79/80/81 readings bind, except the declared page and client.
