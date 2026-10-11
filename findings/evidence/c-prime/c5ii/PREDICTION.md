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
