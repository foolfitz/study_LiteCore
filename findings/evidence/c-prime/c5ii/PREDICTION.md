# C5 (ii): every product-path mutation on the final C′ page — prediction and reading rule (2026-10-11, before any run)

Spec §17.4 C5 (ii): on the C′ page every mutation goes red (the withdrawn one excepted, §17.3); §17.9 (g) S5: run
`a11y-projection-at-its-static-position` and record it as surviving (equivalent on C′), not withdrawn in advance;
§17.10: the "red" of `caret-ignores-x`. Page `dist/e2-editor-app.js` = `web/` = `8909564eb2316afa…`; runner
`run_e2_c_product_path.py` `bd6fc0caf677ee9c`; Chrome; one full `--mutate` run per mutation, 51 runs
(`chain-c5ii.sh`, progress `chain.txt`).

## Flags (decided here, before the runs)

The runner declares `requiresFlag` on four mutations but does not enforce it; without the flag those mutations are
dead and a run reports "the product survived it" (the runner's own comment at `MUTATIONS`). So each runs with its
flag: `structure-names-nothing-while-the-region-defers`, `the-region-defers-with-a-reason-it-owed-the-user`,
`geometry-declared-but-not-delivered` with `--candidate-profile e2-editor-v14` (the accessibility candidate, the only
lineage whose structure channel speaks); `cut-swallows-the-refusal` with `--refusal-diagnostic`. Every other
mutation runs on dist as served (the v19 arm).

## Reading rule (read from each run's own report; no new reader, as registered)

- **red** = the mutation's declared `check` has outcome FAIL in its run. The runner's own `ok` / `verdict` is NOT the
  reading: it also requires every other check to pass, so a mutation with collateral reds reads "NOT DETECTED" while
  its owning check is red (0.2.11's `caret`).
- `caret-ignores-x` (§17.10): red = declared check FAIL, or declared check NOT_ESTABLISHED and its declared also-red
  `the-caret-is-drawn-where-it-was-placed` FAIL.
- `expectedToBeDetected: false` (`checkpoint-write-fails`, `copy-lies`): read as declared — the run's verdict says
  whether the declaration held; listed apart, neither red nor a miss.
- `a11y-projection-at-its-static-position`: recorded (survives or not), not counted either way.
- A run with no report, or with `complete` not true: **not judged**, listed, and re-run once alone after the chain.

## Predicted

All 46 ordinary mutations red; `caret-ignores-x` red by its rule (NE + also-red FAIL, as on the P page);
`checkpoint-write-fails` and `copy-lies` not detected as declared; `a11y-projection-at-its-static-position` survives.
`gesture-abort-not-wired` (re-anchored to `#paper`, `13f91117`): red. The three accessibility mutations on v14: red.
Duration about 5.5 h (51 × about 6.5 min).

If any ordinary mutation is not red: C5 (ii) does not hold; stop before the release step and diagnose (a mutation
that no longer bites on C′ is either an anchor that moved without the static suite noticing, or a check C′ made
unable to fail).

**Correction (before the chain started):** "All 46 ordinary mutations" above is a miscount; 51 − 1 (`caret-ignores-x`) − 2 (declared undetectable) − 1 (`a11y-projection-at-its-static-position`) = **47** ordinary mutations, all predicted red. Nothing else changes.

**Correction 2 (2026-10-11 ~09:35Z, after the chain's run of `geometry-declared-but-not-delivered`, before its re-run):** the flag chosen above for that mutation, `--candidate-profile e2-editor-v14`, makes it **dead**, and this is read from the profiles, not inferred from the result. The mutation replaces `contract?.documentOutlineGeometry === "accessible-paragraph-geometry"` with `Boolean(contract)` (`e2-editor-app.js:374`). `dist/profiles/e2-editor-v14/sdk-manifest.json` (`9943b064d4e18515…`) declares `"documentOutlineGeometry": "accessible-paragraph-geometry"`, so on v14 the original and the replacement are both `true` and the page can never reach `declared-but-missing`. The chain's run shows exactly that: `geometry: "present"`, 24 carried / 24 placed, check PASS. The mutation's own red case when it landed (`72f8de7f`, `probe_093_placement_red_cases.py`, default `--profile e2-editor-v12`) used a profile that declares the outline and **not** the geometry: `dist/profiles/e2-editor-v12/sdk-manifest.json` (`2734229351dac1da…`) has `documentOutline` and no `documentOutlineGeometry`. "The only lineage whose structure channel speaks" above was the right reason to need a candidate profile and the wrong reason to pick v14 for this mutation.

So the v14 run is recorded as **not judged (dead by the flag)**, and the mutation is re-run once, alone, after the chain, with `--candidate-profile e2-editor-v12`. **Predicted:** the owning check `the-projection-is-placed-where-the-document-is` FAIL on clause C1 with `geometry: "declared-but-missing"`. v12 is older than the page's lineage (v15–v19 added actions), so collateral FAILs in other checks are expected and not read; if the run does not complete, it is recorded as such and not judged. The reading rule is unchanged. Whether the v12 run then counts for C5 (ii) is put to the owner together with `inline-format-rollback` — this correction does not decide it.
