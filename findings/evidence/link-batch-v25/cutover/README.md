# v25 page cutover (2026-10-29)

Spec `specs/SPEC-M3-link-batch-v25.md` 4.4 and section 8 step 6. Generation 78 is NOT frozen yet (4.4: freeze only after every shell change of this batch).

- `python3 -I tools/build_cutover_page.py --profile e2-editor-v25` (no `--write`, `--out` to a scratch file) printed pin `276158084a602178` -> `44cb15ea8d36f0e0` and `pageSha256 6e66c930fe3d861903cfa6dfd16d000523298e934fae444385d4fe37d484c7cb`; its diff against the live page was exactly two lines (the pin, line 50; the worker URL, line 3749). Then `--write --expect-sha256 6e66c930…` performed it. Page `b15a6d8e…` (v24) -> `6e66c930…`. `node --check` passes. `git diff` shows only those two lines; the `typedInsert` requirement added in v24 is unchanged (4.4).
- `make e2-c-assets`: its `make -n` printed exactly **one** `cp` line (the page). v24 printed two because v24 also changed `sdk/document-sdk.js`; v25 does not (4.3). `dist/e2-editor-app.js` `6e66c930…`, `dist/sdk/document-sdk.js` `afdff2d4…`, both `cmp`-equal to their sources.

## V0′ for the carried-over v24 counts (`v0/`)

Spec v25 names no V0′. Decided here: **needed**, because section 9 carries the v24 counts over instead of re-running them, so those counts must stay re-readable, and both v24 readers bind the live shell digest. Measured, not assumed:

1. **Before the cutover** (live tree, page `b15a6d8e`): `tools/read_v24_remaining_cohort.py --cohort ../findings/evidence/link-batch-v24/remaining-counted-01/cohort.json` exit 0, `V24_SELECTION_COUNTS_HOLD`, output byte-identical to the committed `remaining-counted-01/completion-read-01.json` (`pre-cutover-live.*`, 86 s).
2. **After the cutover** (live tree, page `6e66c930`): red by construction. The selection reader exits 1 with `NOT_ESTABLISHED`, `ValueError: candidate shell digest differs: 550b68bf…` (`post-cutover-live.*`); `tools/judge_v24_product_four_arms.py` exits 1 with all 24 rows `NOT_ESTABLISHED`, reason `shell digest differs: 550b68bf…` (`post-cutover-a4.*`). `550b68bf…` is the generation-77 candidate digest computed over the live shell, which now contains the v25 page.
3. **Only the declared shell file restored** (source and `dist/` page back to `b15a6d8e`, `restored-hashes*.txt`): the selection reader exits 0 and its output is byte-identical to `completion-read-01.json` (`restored-selection.*`); the four-arm judge exits 0, all four arms PASS, and its output is byte-identical to `four-arms-counted-01/aggregate-judge.json` (`restored-a4.*`).
   The first four-arm re-read (`restored-a4.relative-argv.json`) differed from the committed aggregate only in the two `runs[].dir` fields, because it was given relative report paths while the recorded run (`aggregate-reread-01.receipt.json`) used absolute ones; the judge echoes its argv there. Re-run with the receipt's absolute argv -> byte-identical. An instrument (argv) difference, not a verdict difference.
4. **Put back** each time with the same tool (`--write --expect-sha256 6e66c930…`, `put-back-cutover*.txt`) and `make e2-c-assets`: source and `dist/` page `6e66c930…` (`put-back-hashes*.txt`).
5. E1-C after the cutover: `check_e1_c_bundle_intact.py` exit 0, `intact: true`, bundle `187706b2dcb07d2b`, the same report as `post-link/e1-c.txt` (`e1-c-after-cutover.txt`).

So the cutover moved no byte that the v24 counts bind except the declared page, and the carried-over counts re-read to their recorded results with that page restored. On the live v25 tree the v24 readers are red by construction; this restore-and-reread is the only form in which they can be read. Re-run step 3 after generation 78 is frozen and record it there (the freeze changes files of its own).
