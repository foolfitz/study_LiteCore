# V0′ and E1-C for generation 81 (spec 7.3)

`run_v0_prime.py` is in this directory. It is derived from `../../select-all-v26/v0/run_v0_prime.py`; the closed list of differences is in its docstring. It was committed `5db6827dc` before its run and run once on 2026-10-30, after F3-81/F4-81 finished and with nothing serving `dist/`. Result: **`V0_PRIME_HOLDS`** (`v0-prime.json`, `run.*`), 1.5 min.

**Live tree (generation 81), before any restore.**
- The four four-arm readers (v24 A4, v25 F4, v79 F4, v80 F4) are NOT_ESTABLISHED in all four arms, exit 1 each, by construction (`live-red-*.json`): they bind the live shell digest.
- The file readers each exit 0 with output byte-identical to the committed result (`live-*.json`): the B1 self-test, the F3-79 readings (`read-01`, `equal-01`) and the F3-80 clipboard readings (`read-01`, `equal-01`).

**Stages.** Each restores its generation's declared files in source and `dist/`, then re-reads:

| Stage | Files | Re-read, each exit 0 and byte-identical to the committed result |
| --- | --- | --- |
| v24 (generation 77) | page `b15a6d8e`, client `4616ae17`, narrow `34378dec`/`a4cf3105` | the v24 selection cohort (85 s); the v24 A4 judge |
| v25 (78) | page `6e66c930`, same others | the v25 F4 judge |
| v79 (79) | page `9cb6ea1f`, client `7d1c1eb2`, same narrow | the v79 F4 judge; B1 self-test; F3-79 x2; F3-80 x2 |
| v80 (80) | page `3b6c023e`, client `7d1c1eb2`, narrow `50f5a2ac`/`d037eaa4` (git `7745a26e9`) | the v80 F4 judge; B1 self-test; F3-79 x2; F3-80 x2 |

**Put back.** `git checkout HEAD --` the four files, then `make e2-c-assets`. Afterwards:
- source and `dist/` are generation 81: page `b63d8ee5`, client `7d1c1eb2`, narrow `50f5a2ac`/`d037eaa4`;
- the v81 bundle line exits 0;
- E1-C is `intact: true` (`e1-c-after-put-back.json`);
- no tracked file is modified (`git status`).

So generation 81 moved no byte that the carried-over counts or the generation-79/80 readings bind, except the declared page. Each of those readings re-reads to its recorded result with its own generation's files in place.
