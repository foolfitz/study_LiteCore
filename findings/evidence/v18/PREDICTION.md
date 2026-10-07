# v18: W4 and W6 (before the runs)

Written 2026-10-08 after W1, W2, W3 and W5 passed (`w1-w2/`, `w3-w5/`), and before any of the runs below. The criteria are spec SPEC-M3-paragraph-merge §28.4 (`37525eec`); this file states the expected readings of each part and how they are read. Labels in this file: Q1-Q4 = product path, M1-M4 = merge, O1-O3 = owner's document, C1-C4 = corpus. They mirror v17's P/S/K labels (`../v17/{product-path,merge,layout-corpus}/PREDICTION.md`) and are not those labels.

Candidate page for v18: `cfc8ba1d54dc4bef52baebc34f9d5f60ffe9cc4af9bee8c7a326bb02b2221cda` (`build_cutover_page.py --profile e2-editor-v18`, read only; the same call gives `4c0088c7…` for v17, as recorded). v18 manifest `456e9a72…`.

## Order (`chain.sh`, one tool at a time, Chrome then Firefox where both)

1. Product-path net: v8 and v18 interleaved, 3 rounds × Chrome/Firefox.
2. Merge WASM shakedown: `--frame-cell --rounds 2` and `--control`, then `--pair`, per browser.
3. The owner's document: `--owner-document`, Chrome.
4. Counted corpus comparison: v18 against `e2-editor-v17-cjk-r5-ab`.

## Product path (W6) — reader `../v17/product-path/judge.py --dir product-path --candidate v18 --candidate-page cfc8ba1d…` (page red case in `product-path/selftest-output.txt`)

- **Q1.** 12 reports, `complete: true`, `liveness.lastState: ready`, `pageErrors: null`.
- **Q2.** The v18 reports read `candidateSource.page` `web/e2-editor-app.js` and `sha256BeforeRepoint` `a3fd9ac1…`, with `restOfShellEqualsSource` true. Served entrypoint = `candidateCutover.pageSha256` = `cfc8ba1d…`. v8 serves `e97d6e03…`.
- **Q3 (the criterion, §23).** 0 red cells of 84.
- **Q4 (descriptive).** The per-cell counts equal v17's run, except the cells that already varied between rounds there: Firefox `clear-format-removes-every-inline-format` and `recovery-returns-what-the-product-promised`. Reason: of the page manifest's 16 fixtures (`dist/e1-fixtures/manifest.json`, the same regex census as for the corpus), only `paragraph-content.odt` names a monospace font (`Preformatted`, `monospace`). On v17's run that document already resolved differently from v8, and still 82 of 84 counts were equal. v18 resolves it as v8 does (W3), so it is expected to move no cell away from v8. (I first wrote that no fixture names such a font, having checked only `test-docs/`. This census corrected it before the commit.) Firefox `an-inline-format-reaches-a-selection` is expected to FAIL 3 of 3 again, on both v8 and v18, as on v17.

## Merge (W6) — runner `tools/run_merge_wasm_shakedown.py` (sha256 recorded at chain start and end)

- **M1.** Every report: profile `e2-editor-v18`, page `cfc8ba1d…`, `restOfShellEqualsSource` true, boot ready, 56 case records, no `runner-error`.
- **M2.** Chrome and Firefox each: 56 of 56 pass, split as on v17 (40 `verified-key-undo`, 14 `refused`, 2 `verified-selection-delete`). The refusals:
  - C15/C16: `key-deadline` with `keyPosted:true`;
  - C17: `anchor-mismatch`;
  - C29/C30: `nothing-selected`;
  - F01/F02: `anchor-mismatch` with `keyPosted:false`.
  M2-0 is true on all three fixtures. Control 56 of 56.
- **M3.** `--pair`: 0 differ. The number of documents compared on each side is counted from the kept documents and reported with it (standing rule f). Expected: 42 + 42 + 14 per browser.
- **M4.** No toast outside the expected reopen sequences, and no 「重繪失敗」.

## Owner's document (W6, §26.3 V5's clauses) — Chrome, diagnostic

- **O1.** The engine's caret height equals native in all 11 cells, as on v17: E01 348, E02 521, E05 521, E10 348, T01 463, and E12/P27/E13/E15/P62/P63 348 twips. x and y equal native; `keyed` false in all 11; no `placement-mismatch`.
- **O2.** 26 of 26 synthetic cases pass. `reducedBytesEqual` true on all three fixtures.
- **O3 (descriptive, finding 115).** E02's `afterKeyBytes` stays red, with the same 4 of 15 soft page breaks. The document names no monospace or fixed-pitch font (its XML, read for 116), so the Mono faces are not expected to touch it. The report carries no paragraph text.

## Corpus (W4) — reader `layout-corpus/judge.py` (a copy of v17's; W4's not-measured clause is part of its verdict; red cases in `layout-corpus/selftest-output.txt`)

- **C1.** VERDICT PASS.
- **C2.** Not comparable: the same 5 in both arms.
- **C3.** Not measured: 23, the same set as v17's counted run; measured 48.
- **C4 (descriptive).** `paragraph-content.odt` differs by 0 px (W3's session already showed 0 at every band). The eight documents that differed by 1 px on v17 (`l0-t3-long`, `t3-long`, `r7-finding-012/t2-keep-*`) still differ by 1 px, since they name no monospace or fixed-pitch font. If they become 0, the Mono faces touched them, and that is recorded.

## What a miss means

- W4 red, or a §23 red cell: look at the request and the answer first (116's method). T and the criteria are not adjusted.
- A miss of a descriptive line (Q4, O3, C4) is recorded as a miss.
- A runner error or a missing report stops the chain (`chain.sh` aborts on a missing report). Nothing after it runs.

Note on names: the owner's-document run writes to `v5/shakedown-chrome-v18-v5.json`. The runner keeps that document's saves in `wasm_sdk_probe/build/merge-wasm-private/<stem>.docs` and refuses an existing directory, and v17's run already used the stem `shakedown-chrome-v5`.
