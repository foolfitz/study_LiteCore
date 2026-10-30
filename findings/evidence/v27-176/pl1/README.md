# PL-1: would v27's rule verify what v26's WASM engine records today? (2026-10-30)

SPEC-M3-v27-finding-176 7.2 PL-1, the relink gate (7.2 default: no relink hand-off unless every record "would verify"). Local mirror of `dist/` (generation 80, profile `e2-editor-v26`), no DDEV, nothing linked, nothing under `dist/` written.

## Result: **PL1_WOULD_VERIFY, 12/12** (`read-01.json`, exit 0)

| Browser | Recipe | Runs | Engine record (every run) | Would verify |
| --- | --- | --- | --- | --- |
| Chrome 156 | list-contexts (F3's cell) | 3 | `error`, `multi-block-readback`, collapsed, dispatched; blocks `['', 'E1-LC-END']`, `ul`, items 1, restoreConfirmed | 3/3 |
| Chrome 156 | s3 (S3's recipe) | 3 | same; blocks `['', 'E1-EMPTY-AFTER']` | 3/3 |
| Firefox 157 | list-contexts | 3 | same as Chrome | 3/3 |
| Firefox 157 | s3 | 3 | same as Chrome | 3/3 |

In every run the page shows finding 176 as the owner saw it on 0.2.42: pill `ready`, strip `• 項目符號 失敗`, the toast 「…這一格的檢查涵蓋了不只一個段落…」. The paragraph-identity gate's four inputs are all false in every record (the product core has no a11y), so under v27 it would not run; `hasUndo` is false (v26 has no `undo` field: the observer reads v26's own record, not a projection).

`read-01-self-test.json`: base `PL1_WOULD_VERIFY`; **68/68 mutations `PL1_RED`**: each of the 16 clauses mutated on the first run of every browser x recipe (64), plus one run dropped, one identity not ok, one run fatal, no runs. The spec's four required red cases are among them: `restoreConfirmed:false`, `listTag:""` (the `predicate-satisfied` mutation), `route:range-single`, one run fewer.

## Tools (committed `0be1119ac` before run-01)

- `run_v27_pl1.py`: the runner; its docstring holds the closed list. Two recipes:
  - `list-contexts`: F3's cell exactly as `host-0.2.39/k-nine-cells/diag-format/diag_format.py` `bullet` drives it (imported by path, not edited).
  - `s3`: S3's recipe up to the press. `../fixture-two-plain/build-01/two-plain.odt` through the page's file input; a real click past the end of the first line; a real Enter; a real click on the bullet button.
- **The observer.** One extraction function (`KEEP_JS`) over every engine `error` / `editor-action-completed` event. It keeps: route, failureShape, dispatched, selectionTypeReadable, paragraphIdentity's four inputs, and readback's flags, counts, tags, expectations, `restoreConfirmed` and `html`. Two transports:
  - **Chrome**: v25 F1's CDP `Target.setAutoAttach` + in-place `JSON.parse` wrap. No served byte changes (identity `observer-only`). Derived, not imported, so that it installs into every attached `sdk-worker.js` target, not only the last.
  - **Firefox**: CDP is Chrome-only, so the mirror serves a **diagnostic** worker. It is the archived v26 worker byte for byte, followed by `DIAG_SUFFIX`: the same `KEEP_JS`, posting on `BroadcastChannel("pl1-raw-engine")`, with the page listening. It is appended, not prepended, because the worker opens with `"use strict"`, which must stay its first statement. wasm, loader and manifest are the archive's. Identity `workerIsArchivePlusSuffixExactly: true`, `instrumentedWorker: true`, evidence class `diagnostic` (046's diagnostic-profile precedent). The product page and worker do not check the worker's hash at run time (grep: only the old diagnostic `e2-c-*` pages read `workerSha256`).
- **Identity checks** (`report.json` `products`; both ok):
  - generation 80's bundle file, all 13 members as served, and the page `3b6c023e` pointing at v26;
  - the HTML is `dist/`'s plus exactly the three snippets;
  - wasm/loader/manifest equal the v26 archive pins (`v80_four_arms_identity.ARTIFACT_PINS`);
  - the worker is the archive's (Chrome) or the archive's plus the suffix exactly (Firefox).
- `read_v27_pl1.py`: the verdict, from `report.json` only. v27's collapsed rule is applied in the order `finishOrderedFormatReadback` uses under `OXSDK_E2_V27_FIRST_BLOCK`, and the predicate is `formatBarrierReadbackSatisfied` re-read field by field. Two additions to the spec's list, both read from the source:
  - `selectionTypeReadable` is part of the predicate;
  - the identity gate must not run, because it compares fingerprints the record does not carry.
  The record must also be 046's cell (`error`, `multi-block-readback`, dispatched) and the recipe's cell (first block the empty dispatch paragraph, second the recipe's next paragraph). `CLAUSES` is the population: id, predicate, mutation.

## What this does not establish (named)

- **F vs G.** The records are v26's, which still restores before the select (op F). v27 drops that restore on the collapsed route (op G). That F and G read the same first block is the native arm's measurement (N-176 / N-Q63, G = F in every cell, 5/5), not this one's.
- **Readback inputs, not v27's judgement.** PL-1 predicts from v26's readback inputs. That v27's engine actually judges this way is E1/E2 (unit) and, after the link, S3 and F3-81.
- **Firefox's evidence class.** Firefox's records come through a served worker that is not the shipped one: diagnostic. Chrome's records come with no served byte changed.

## Shakedowns (scratch, not evidence)

- `pl1-shake-01` (1 repetition, both recipes and browsers): `s3` landed in the top margin. The first click fraction, 0.0757, left out the LOK document area's 284-twip border; `#paper` is 900 x 1256 px = 22 x 30.7 cm. The caret went to the start of `Plain first`, the bullet verified on that single block, and the reader judged both runs red (`is-046-cell`, `multi-block`, `recipe-cell`): the clause that exists for this case.
- `pl1-shake-02` (`s3` only, y = 0.0894): 046's cell in both browsers. The reader's self-test on it: 36/36 red.
- The fraction is fixed in the runner with its reason. Counted as fixed-by-execution (spec §12 / §34.4).
