# V5 on v17 (spec 26.3): the owner's document, result

Run 2026-10-07 22:57:42-23:02:29 (+08:00), Chrome, one round, diagnostic and uncounted, per `PREDICTION.md` (committed `5f22c21a` before the run). Report `shakedown-chrome-v5.json`; stdout `shakedown-chrome-v5.stdout.txt`, stderr empty. Kept synthetic documents in `shakedown-chrome-v5.docs/`; the owner's document's saves are in `wasm_sdk_probe/build/merge-wasm-private/shakedown-chrome-v5.docs/` (not in the repository). The report carries no paragraph text of the owner's document (checked: the only CJK strings in its owner-document rows are the page's own UI words; `search` is null in all 11 rows).

## Preconditions

`candidate.profile` `e2-editor-v17`; `pageSha256` `4c0088c7a518bc36b9cc999d2e67796d20a58525355b68ae67881228dc95b498` (= `build_cutover_page.py --profile e2-editor-v17`, recomputed before the run); `pinAfter` `ad3f68bb85f94589`; `workerSha256` `00882139…`; `restOfShellEqualsSource` true; boot `ready`; runner `c3f723b3be6eb4bf`; `caseList` `tool` (26 synthetic cases + the owner's 11; no `--frame-cell`).

## V5

| case | native height | v16 (red case) | v17 engine height | engine x, y = native | outcome |
|---|---|---|---|---|---|
| E01 | 348 | 276 | 348 | yes | `verified-key-undo`, pass |
| E02 | 521 | 414 | 521 | yes | `verified-key-undo`, **not pass: `afterKeyBytes` only** (below) |
| E05 | 521 | 276 | 521 | yes | `verified-key-undo`, pass |
| E10 | 348 | 230 | 348 | yes | `verified-key-undo`, pass |
| E12 | 348 | 276 | 348 | yes | `verified-key-undo`, pass |
| T01 | 463 | 277 | 463 | yes | `verified-key-undo`, pass |
| P27 | 348 | 276 | 348 | yes | `verified-key-undo`, pass |
| E13 | 348 | 276 | 348 | yes | `verified-key-undo`, pass |
| E15 | 348 | 276 | 348 | yes | `verified-key-undo`, pass |
| P62 | 348 | 276 | 348 | yes | `verified-key-undo`, pass |
| P63 | 348 | 276 | 348 | yes | `verified-key-undo`, pass |

- **Clause 1 (heights): HIT, 11 of 11.** Every engine caret height equals the native one, including the rows the summary "276/414 -> 348/521" does not name (E10 from 230, T01 463, E05 from 276 to 521).
- **Clause 2 (class): HIT, 11 of 11.** No row is `placement-mismatch`. Every caret was placed by the click alone (`keyed` false in all 11: the engine's caret after the click already equalled the native x, y and height to the twip).
- Observed, as predicted: document height 308,480 twips (v16: 257,114), above T01's native caret y 275,530.
- Synthetic cases: 26 of 26 pass, the same outcomes as v16 run 3. M2-0: all three fixtures `reducedBytesEqual` true (the owner's document included).
- Key-to-response on the owner's document: 130.7-159.6 ms (listed, not judged).

## E02's bytes clause

Read with `e02_breaks.py` (re-runnable; prints tags, style names and text lengths only), output `e02-breaks.txt`:

- The merge is the same as Writer's: against the original, the WASM after-key document and Writer's key arm r1 have the same two hunks (the heading's 4 characters and the next paragraph's 209 become one 213-character paragraph).
- The reduced-byte difference is two other places where WASM's export has a `T4` span, a `<text:soft-page-break/>`, and another `T4` span; spec 24's reduction removes the break element and leaves two adjacent spans of one style, where Writer's document has one span. **The reduction is incomplete for page breaks inside a span.**
- Underneath it: after E02's merge, 4 of the 15 page breaks (2, 3, 14, 15) sit elsewhere than in Writer's key arm. Writer's three rounds are identical to each other. In the 10 other owner cells, in E01, and in the no-edit save, all 15 breaks sit where Writer's do. The follow documents (after a typed `Z`) differ as well (8 of 15), so this is not one side saving before its layout settled.
- E02 is the only cell that puts a long body paragraph into `Heading_20_1` (18 pt). Whether the different pagination comes from the v17 font set or from the WASM engine is the discriminator in `e02-discriminator/` (prediction committed before its run).

## What this does and does not establish

- V5 holds on this document in Chrome: v17 lays the owner's document out with native line heights and native caret positions in all 11 cells (finding 114's symptom is gone here).
- Not established: Firefox; more than one round; v8 on this document; whether the owner's document returns to M2-1 (spec 26.3 leaves that to a new appended section with reasons; if it does, E02's bytes clause would be red under the current reduction).

## Addendum (same day, after `e02-discriminator/`)

The discriminator read **H-wasm**, with one caveat recorded there (C1 missed as written: every native run also loads LibreOffice's own `share/fonts/truetype/fc_local.conf` and OpenSymbol, which the WASM packs lack). Native with v17's own font files and rules paginates E02's merge exactly as native with the system fonts; WASM differs at breaks 2, 3, 14, 15, and does so identically in a second run. Registered as finding 115 (`findings/115-…md`). V5's verdict above is unchanged by it.
