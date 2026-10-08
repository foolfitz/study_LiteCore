# v18: W4 and W6 (spec SPEC-M3-paragraph-merge §28.4, §28.5): result

Per `PREDICTION.md` (committed `15eca506` before the chain; Amendment 1 in `c073478d`, after the review and before the merge, owner's-document and corpus steps started). Labels Q1-Q4, M1-M4, O1-O3, C1-C4 are that file's. Criteria: Q1-Q3, M1-M4, O1-O2, C1-C3; descriptive: Q4, O3, C4.

Run by `chain.sh`, one tool at a time, 2026-10-08 07:20:27 - 09:57:58 (+08:00); every step's start, end and exit code are in `chain.log`. Tool sha256 prefixes at chain start: product path `b52779e498ae33cf`, merge runner `c3f723b3be6eb4bf`, corpus tool `21f90c3161a38d34`. At chain end: the same three prefixes (`CHAIN DONE` line). The arm order is fixed, v8 before v18 in every product-path round (review item 16), so an order effect is not separated from a profile effect.

## Verdict

**W4 and W6 are met.** Every criterion line is HIT (Q1-Q3, M1-M4 on both browsers, O1-O2, C1-C3), and the identity hashes after the chain equal the archive's, so the runs are evidence about v18. Every descriptive line is as predicted (Q4, O3, C4); none missed. With W1-W3 and W5 (`w1-w2/`, `w3-w5/`), all six §28.4 criteria are met. **The never-done default of §28.4 no longer applies to v18.** The cutover itself still needs the owner's approval: it changes the product page and the host.

| part | criteria | reader | output |
|---|---|---|---|
| Product path (W6) | Q1 HIT, Q2 HIT, Q3 HIT (0 red cells of 84); Q4 HIT (descriptive) | `../v17/product-path/judge.py --dir product-path --candidate v18 --candidate-page cfc8ba1d…` (v17's reader, unchanged) | `product-path/judge-output.txt` |
| Merge (W6) | M1-M4 HIT on Chrome and on Firefox | `merge/judge.py` (new; written after the Chrome merge step had run and its stdout list of outcomes had been seen, before Firefox's step ended; expected values from `PREDICTION.md`; red cases on v17's run in `merge/selftest-output.txt`) | `merge/judge-output.txt` |
| Owner's document (W6) | O1 HIT, O2 HIT; O3 as predicted (descriptive) | `v5/judge.py` (new; written before the owner's-document step ran; red cases on v17's run in `v5/selftest-output.txt`) | `v5/judge-output.txt` |
| Corpus (W4) | C1 HIT (reader exit 0, VERDICT PASS), C2 HIT, C3 HIT; C4 HIT (descriptive) | `layout-corpus/judge.py` (committed `15eca506`) | `layout-corpus/judge-output.txt` |
| Identity (Amendment 1) | all four named files equal the archive (and three more, not named, too) | `sha256sum`, compared by hand with the archive's `SHA256SUMS` and `identity-during-chain.txt` | `identity-after-chain.txt` |

## Product path (W6)

- **Q1 HIT.** 12 reports, each `complete: true`, `liveness.lastState` `ready`, `pageErrors` null. Chain exit codes: Chrome 0 (6 of 6), Firefox 1 (6 of 6). The Firefox exit 1 is the predicted `an-inline-format-reaches-a-selection` FAIL, 3 of 3 on both arms.
- **Q2 HIT.** v18 reports: `candidateSource.page` `web/e2-editor-app.js`, `sha256BeforeRepoint` `a3fd9ac1…`, `restOfShellEqualsSource` true, served entrypoint = `candidateCutover.pageSha256` = `cfc8ba1d54dc4bef52baebc34f9d5f60ffe9cc4af9bee8c7a326bb02b2221cda`, `pinAfter` `ad3f68bb85f94589`. v8 reports serve `e97d6e03…`. Shell bundle v55 on both arms.
- **Q3 HIT.** 84 cells judged by spec §23, 0 red.
- **Q4 HIT (descriptive).** v8 and v18 counts are equal in 84 of 84 cells. Against v17's run (`../v17/product-path/judge-output.txt`), the per-cell counts are equal except in the two cells the prediction exempted, both Firefox:
  - `clear-format-removes-every-inline-format`: v17's run v8 2 PASS / 1 NE and v17 1 PASS / 2 NE; this run 3 NE on both arms. `allOnWhenTyped` varies per round on both arms (table in the judge output); the cell stays "ok" under §23 because both arms agree. Firefox established it in **0 of 6** runs this time, against 3 of 6 in v17's run (carried open item; not looked at here).
  - `recovery-returns-what-the-product-promised`: v17's run v8 2 PASS / 1 NE; this run 3 PASS on both arms.
  - Firefox `an-inline-format-reaches-a-selection` FAIL 3 of 3 on v8 and on v18, as predicted.

## Merge (W6)

Reports `merge/shakedown-{chrome,firefox}.json`, `merge/control-{chrome,firefox}.json`; `--pair` output `merge/pair-{chrome,firefox}.stdout.txt`. Every stderr is empty, and every step's exit code is 0.

- **M1 HIT (both browsers).** Every report has profile `e2-editor-v18`, `pageSha256` `cfc8ba1d…`, `workerSha256` `00882139…`, `restOfShellEqualsSource` true, boot `ready`, 56 records, no `runner-error`, and a `completedAt`.
- **M2 HIT (both browsers).**
  - 56 of 56 pass, split 40 `verified-key-undo` / 14 `refused` / 2 `verified-selection-delete`.
  - Every case's outcome, stage and `keyPosted` equal the prediction's table: C15/C16 `key-deadline`/`true`, C17 `anchor-mismatch`/`false`, C29/C30 `nothing-selected`/`false`, F01/F02 `anchor-mismatch`/`false`, G01 `verified-selection-delete`. The reader checks this itself and does not take the report's `pass` flag on trust (red case 3).
  - M2-0 `reducedBytesEqual` true on `boundaries`, `boundaries-indent`, `text-frame`. Control 56 of 56.
  - Not-established clauses are the same 14 per run as v17's: `noUnchanged` on refusals whose key was not posted, `afterKeyBytes` on Y01/Y02 (`typed-merge`).
- **M3 HIT (both browsers).** `--pair`: 56 pairs, 0 differ. **Documents compared, counted from the kept `.docs` (rule f):** on each browser, 42 after-key, 42 follow and 14 reopened documents on the instrumented side and the same 42 + 42 + 14 (case, round) set on the control side. Every kept document has at least one paragraph.
- **M4 HIT (both browsers).**
  - The `noToast` clause holds on all 42 cases per report that carry it.
  - `onlyTheReopenToasts` holds on all 14 per report that carry it.
  - 「重繪失敗」 appears nowhere in the four reports.
- Descriptive (`merge/descriptive.py`, output `merge/descriptive-output.txt`):
  - Paragraph text of the 101 kept documents per run is identical Chrome against Firefox, on both the instrumented and the control side.
  - It is identical to v17's run, document for document (4 x 101). The Mono faces did not change any merge outcome these fixtures can show.
  - `keyToResponseMs`, listed and not judged: Chrome min 38.9 / median 133.35 / max 2098.1 ms; Firefox 40.3 / 136.4 / 2101.7 ms. Both maxima are `key-deadline` refusals, which wait for their deadline.

## Owner's document (W6; §26.3 V5's clauses)

Report `v5/shakedown-chrome-v18-v5.json`, Chrome, one round, diagnostic, uncounted. Started 09:07:39, completed 09:12:32 (+08:00). Exit 0, stderr empty. The owner's saves are in `wasm_sdk_probe/build/merge-wasm-private/shakedown-chrome-v18-v5.docs/` (23 files, ignored by `.gitignore:34`). The 49 kept synthetic documents are in `v5/shakedown-chrome-v18-v5.docs/`; none of them is an owner case.

- **Precondition HIT.**
  - Profile `e2-editor-v18`, page `cfc8ba1d…`, worker `00882139…`, `pinAfter` `ad3f68bb85f94589`, boot `ready`, `ownerDocument` true, 11 owner rows.
  - **No paragraph text:** `search` is null in all 11 owner rows. The CJK strings in those rows are exactly v17's set of page UI words (儲存 刪除 前刪 定位游標 就緒 已存出 已開啟 無), with nothing outside it.
- **O1 HIT.**
  - The engine caret height equals native in all 11 cells: E01 348, E02 521, E05 521, E10 348, T01 463; E12, P27, E13, E15, P62, P63 348 twips.
  - Engine x and y equal native in all 11 cells. `keyed` is false in all 11, and no row is `placement-mismatch`.
- **O2 HIT.** 26 of 26 synthetic cases pass. M2-0 `reducedBytesEqual` is true on `boundaries`, `boundaries-indent` and `pmpc`.
- **O3 as predicted (descriptive, finding 115).**
  - E02 fails on `afterKeyBytes` only (`textEqual` true).
  - E02's after-key document against Writer's key arm r1: 15 against 15 soft page breaks; breaks 2, 3, 14 and 15 differ, the same 4 of 15.
  - E01 and the no-edit save have every break where Writer's are.
  - **E02's after-key document on v18 equals v17's** in its reduced `content.xml` tokens and in the context of all 15 breaks. The Mono faces did not touch this document, as predicted (it names no monospace or fixed-pitch font).
  - Key-to-response on the owner's cells: 132.2-153.5 ms (listed).

## Corpus (W4)

Run 09:12:32-09:57:58 (+08:00); UTC `2026-10-08T01:12:32Z` to `01:57:58Z` (`layout-corpus/run-{started,finished}-utc.txt`). `compare_layout_corpus.py --profiles e2-editor-v18 e2-editor-v17-cjk-r5-ab`, exit 0, stderr empty, `ps` before and after kept. Tool sha256 prefix `21f90c3161a38d34` at chain start and end, the same as v17's counted run. Both arms report wasm `ad3f68bb85f94589`, boot `ready`, 76 documents.

- **C1 HIT.** `layout-corpus/judge.py` exits **0** (`judge-exit.txt`) with **VERDICT: PASS**, which is what §28.5 requires (a STOP would have been "not done"). 48 measured documents, band count equal in all 48, maximum top difference 1 px, 0 over T = 2 px.
- **C2 HIT.** Not comparable: the same 5 in both arms (`recoverable-error`), and the same 5 as v17's counted run (`l3-bad-central-directory`, `l3-high-ratio`, `l3-too-many-entries`, `l3-truncated`, `r7-corrupt-truncated`).
- **C3 HIT.** Not measured: 23 in each arm, and the reader's W4 clause reads "v17's counted run (arm 0) not measured 23; this run 23; same set: True". Measured: 48 (21 with CJK characters).
- **C4 HIT (descriptive).**
  - `test-docs/e1/paragraph-content.odt`: 27 bands in both arms, `rowsSha` equal (0 px; band 10 at 209 in both, where v17 had 206 against the control's 209). The 116 red is gone.
  - The eight documents that differed by 1 px on v17 still differ by 1 px, and they are exactly those eight: `l0-t3-long`, `t3-long` and `r7-finding-012/t2-keep-{image-pagebreak,none,pagebreak,table-image-pagebreak,table-pagebreak,table}`. The Mono faces did not touch them. Their cause is still not looked at (open item, carried).
- Cross-check against the tool's own `comparison.json`: AGREE (71 comparable, 61 identical; v17's run had 60, the difference is `paragraph-content.odt`).

## Identity after the chain (Amendment 1)

`identity-after-chain.txt`, taken 09:58:10 (+08:00), 12 s after `CHAIN DONE`:

| file | after the chain | `identity-during-chain.txt` (08:02:08) | archive `SHA256SUMS` |
|---|---|---|---|
| `dist/profiles/e2-editor-v18/sdk-manifest.json` | `456e9a72…` | `456e9a72…` | `456e9a72…` |
| `dist/profiles/resources/cjk-sub-e10.06976180177c8bd2.data` | `06976180…` | `06976180…` | `06976180…` |
| `dist/profiles/resources/cjk-sub-e10.4144b2b2a44dd797.metadata` | `4144b2b2…` | `4144b2b2…` | `4144b2b2…` |
| `dist/profiles/e2-editor-v17-cjk-r5-ab/sdk-manifest.json` (control) | `584ba6b8…` | `584ba6b8…` | (not archived with v18; the value recorded in the handoff) |

Also hashed, not named by Amendment 1: the v18 profile's `probe.js` `46b2f40a…`, `probe.wasm` `ad3f68bb…` and `sdk-worker.js` `00882139…` equal the archive's. Hashing before and after does not prove the files were unchanged in between; that nothing in the chain writes them is inference (the runners read profiles through the served `dist/`; not checked by reading every tool). The merge and owner's-document reports also record `workerSha256` `00882139…` and `pinAfter` `ad3f68bb…` themselves.

## What this does and does not establish

- Established: v18 (manifest `456e9a72…`, page `cfc8ba1d…`) meets W4 and W6. Together with W1-W3 and W5 it meets every §28.4 criterion, read as amended by §28.5.
- The two new readers were not written before the chain. `merge/judge.py` was written after the Chrome merge step had run and its stdout (the list of outcomes) had been seen; `v5/judge.py` before the owner's-document step ran. The expected values in them are copied from `PREDICTION.md` (committed before the chain), not from any v18 report. Each was first shown to reproduce v17's recorded verdicts (`../v17/merge/RESULT.md` S1-S4; `../v17/v5/RESULT.md` clauses 1 and 2). Each was then shown to miss exactly what one changed input breaks: 7 and 9 red cases, `selftest-output.txt` in each directory.
- Not established, carried:
  - Anything counted for M2: 3 rounds x 2 browsers, and M2-1b, M2-2 and M2-4, which are not in the merge runner.
  - The owner's document on Firefox and on v8.
  - The cause of the eight 1 px documents and of the 23 not-measured documents.
  - Finding 115 (E02's pagination).
  - The §28.5 limits: monospace requests tagged `bin gn ig ko miq`; "like the control" is not "like v8" on fixed-pitch text; boot time and memory with e10.
- The product-path net, the merge shakedown and the owner's document ran on candidate pages with `--candidate-profile`, not on a cut-over product. The cutover chain (shell v56, pins, host 0.2.8 with the `cjk-sub-e10` pin, R) is not started and waits for the owner.
