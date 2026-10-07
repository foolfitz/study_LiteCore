# Merge (option B) WASM shakedown on v17, Chrome and Firefox: result

Per `PREDICTION.md` (committed `127775ee` before the run). Run by `../followon.sh` (one tool at a time, after the product-path chain), 2026-10-08 00:31:57-01:00:59 (+08:00); step log `../followon.log`. Runner `c3f723b3be6eb4bf` (sha256 at follow-on start, in the log). Uncounted.

| report | browser | cases | pass | outcomes |
|---|---|---|---|---|
| `shakedown-chrome.json` | Chrome | 56 (28 x 2 rounds) | 56 | 40 `verified-key-undo`, 14 `refused`, 2 `verified-selection-delete` |
| `control-chrome.json` | Chrome, `--control` | 56 | 56 | (control) |
| `shakedown-firefox.json` | Firefox | 56 | 56 | 40 `verified-key-undo`, 14 `refused`, 2 `verified-selection-delete` |
| `control-firefox.json` | Firefox, `--control` | 56 | 56 | (control) |

- **S1 HIT**: every report `e2-editor-v17`, `pageSha256` `4c0088c7a518bc36…`, `restOfShellEqualsSource` true, boot ready, 56 records, no `runner-error`, stderr empty.
- **S2 HIT (Chrome)**: the 20 M2-1 cases pass every clause in both rounds; G01 `verified-selection-delete`; C15/C16 refused `key-deadline` with `keyPosted:true`, C17 `anchor-mismatch`, C29/C30 `nothing-selected`; F01/F02 refused `anchor-mismatch`, `keyPosted:false`. M2-0 `reducedBytesEqual` true on all three fixtures (boundaries, boundaries-indent, text-frame). `--pair` (`pair-chrome.stdout.txt`): 56 pairs, 0 differ.
- **S3 HIT (Firefox, the first run of this runner on Firefox)**: the same outcomes, stages and clauses as Chrome, in both rounds. M2-0 the same. `--pair`: 56 pairs, 0 differ.
- **S4 HIT**: no toast outside the expected reopen sequences; no 「重繪失敗」.

Non-vacuity of the pairs (counted from the kept documents, the pair tool does not print it): on each browser 42 after-key, 42 follow and 14 reopened documents exist on both sides and were compared; no case has an empty generation on either side; 14 cases per run carry a toast sequence. Across browsers: the 101 documents that both instrumented runs kept have identical paragraph text, Chrome against Firefox.

Latency, listed and not judged (Firefox's includes WebDriver key dispatch, see the prediction): Firefox `keyToResponseMs` over 56 cases min 40.1, median 136.0, max 2100.6 ms (the maximum is a `key-deadline` refusal, which waits for its deadline by design).

Not established here: anything counted (M2's 3 rounds x 2 browsers, M2-1b, M2-2, M2-4 are not in this runner); the owner's document (V5, `../v5/`); the corpus (`../layout-corpus/`).
