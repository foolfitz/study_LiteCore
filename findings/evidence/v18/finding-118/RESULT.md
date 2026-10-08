# Finding 118: result (red cases, page fix, verification on v18)

Predictions: `PREDICTION.md` (committed `f4f5d973`, before any run). **P1 HIT, P2 HIT, P3 HIT, P4 HIT, P5 HIT.** Not counted (nothing here is bound; spec §31).

## Runs

| Chain | Runner(s) | Page (`web/e2-editor-app.js` sha256 prefix) | Exit codes |
|---|---|---|---|
| `attempt1/` (12:19-12:26) | shrink `0d7fb1da…` | `a3fd9ac1…` (before the fix) | **NOT MEASURED** ×4: the fixture was never served (`attempt1/README.md`); logged `exit=0` by the broken `$?` capture |
| `chain-red.sh` (12:35:51-12:36:47) | shrink `66c1fdf6…` | `a3fd9ac1…` | captured with `rc=$?` first: 1, 1, 1, 1 |
| `chain-verify.sh` (12:37:27-12:48:18) | shrink `66c1fdf6…`, merge `0e00aa4c…` | `a7d8ffa1…` (the fix, `840794af`) | 0, 0, 0, 0 |

Every stderr is empty. The v18 candidate page served in P2-P4 is `repointed_page(web/e2-editor-app.js, e2-editor-v18)`: `b3ad0f64…` after the fix (P3/P4 reports' `pageSha256`, equal to `build_cutover_page.py --profile e2-editor-v18`); before the fix the candidate was `cfc8ba1d…`.

## P1, P2: red before the fix (HIT)

The 52-paragraph fixture opens at 12,474 × 17,406 (one page), the toolbar's paragraph break grows it to 34,528 (the first paint after it asks the old height, comes back `documentSizeChanged` true and 0.926 painted, and the page re-lays out to two pages' rows), and the toolbar's Undo shrinks it back:

| Report | Page | First paint after Undo (h asked, rows, reply docH, changed, painted) | Toast | Every later paint |
|---|---|---|---|---|
| `p1-v8-dist-chrome.json` | shipped v8 | 34,528, 2,007, 17,406, true, **0.47** | TILE_NOT_PAINTED | 17,406 into **2,007** rows |
| `p1-v8-dist-firefox.json` | shipped v8 | 34,528, 2,491, 17,406, true, **0.47** | TILE_NOT_PAINTED | 17,406 into **2,491** rows |
| `p2-v18-cutover-chrome.json` | cutover, before fix | as P1 Chrome | TILE_NOT_PAINTED | 2,007 rows |
| `p2-v18-cutover-firefox.json` | cutover, before fix | as P1 Firefox | TILE_NOT_PAINTED | 2,491 rows |

**The shipped page has 118 (measured).**

## P3: green after the fix (HIT)

| Report | First paint after Undo | Next paint | Toast |
|---|---|---|---|
| `p3-v18-cutover-fixed-chrome.json` | 34,528, 2,007 rows, 17,406, true, 0.47 (not judged) | 17,406 into **1,012** rows, 0.926 | none |
| `p3-v18-cutover-fixed-firefox.json` | 34,528, 2,491 rows, 17,406, true, 0.47 (not judged) | 17,406 into **1,256** rows, 0.928 | none |

The growth step still re-lays out (two-page rows 2,007 / 2,491 found), so finding 062's half is intact.

## P4: M2-4 with the fixed page, plain v18 (HIT)

| Report | `pass` | False clauses | Toasts | Fast presses | Max runner latency | Paints after press 55 | Final document |
|---|---|---|---|---|---|---|---|
| `p4-m2-4-fixed-chrome.json` | **true** | none | none | 1, 3, 55 | 2,097.1 ms | all 17,406 into 1,012 rows | reduced bytes and text equal native press 105 |
| `p4-m2-4-fixed-firefox.json` | **true** | none | none | 1, 3, 55 | 2,103.1 ms | all 17,406 into 1,256 rows | same |

Press 55 in both: the stale strip (0.47) and then the re-laid-out paint. Latency is unchanged, as predicted: 102 presses still wait the 2000 ms deadline, because the engine fix (`66e5c0af`) is not linked. Under spec §31.2 these two reports are still **red on latency**; they are evidence for the page fix only.

## P5: static (HIT)

The fixed page holds `      if (tile.documentSizeChanged) documentResized = true;` exactly once (the product-path mutation `ignore-a-document-that-grew` finds it), and `node --check` passes on it (copied as `.mjs`).

## Limits

- Not looked at on screen: "the document is drawn about twice as tall" before the fix is inference from the canvas rows.
- The product-path net has no "document got shorter" cell; this fix is watched by M2-4 (press 55) and `tools/run_shrink_repaint.py` only.
- v8's page is not fixed separately; the fix ships with the cutover (spec §31.3).
