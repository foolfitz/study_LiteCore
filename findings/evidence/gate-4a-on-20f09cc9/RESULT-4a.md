# Condition 4a, re-taken on page `20f09cc9…` with the corrected instrument

**2026-09-06.** All eight terms pass.

This directory exists because two things moved after the previous 4a take, and
the plan requires the take to be re-earned on both counts:

* **The judge changed.** The amendment of 2026-09-05 ("term 4's 'reading' is
  defined, and terms 4 and 8 get an expectation that neither channel can
  supply") added term 8 and defined what term 4 reads. Its count semantics say:
  *"The 4a runs on the current page are re-taken with the corrected instrument
  (three runs, one mutation, one control) before they count as '4a on the new
  sha'."*
* **The page moved.** The previous take is on `3dfdcfef4abfe6b7…`
  (`../gate-4a/candidate-v12-run1.json`), which the human round of 2026-09-04
  moved. Its term 1 pins that sha, so it is void by its own criterion.

The previous take is **left where it is**, unedited and unmoved. Nothing there
is wrong for the page it measured; it is simply not about this page. Reading the
two directories side by side is how the delta stays visible.

## The terms

| term | verdict |
|---|---|
| **1 identity** | all three runs `pageSha256` **`20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95`**, profile `e2-editor-v12`, `shim: null`. Equal to the sha the ten banked soak reports carry. |
| **2 text** | 9 of 9 fixture paragraphs found in `getFullAXTree`, `missing: []`, on each of the three runs. |
| **3 structure** | 1 heading node, AX `level: 1`, matching the ODT `outline-level: 1`; 2 `list` containers, 4 `listitem` nodes. Identical on all three runs. |
| **4 focus follows the caret** | 3 placements, 3 readings, 3 distinct, `matchedTheParagraphAimedAt: 3`, `established: true`. The expectation comes from the fixture keyed by placement index, not from the reading. |
| **5 repetition** | 3 runs, `distinctSignatures: 1`. |
| **6 the instrument can fail** | see below |
| **7 delta** | v8's shipped page: `documentTextInTree: false`, region carrying `reason: "profile"` and the sentence *「這一版引擎沒有提供段落文字，所以無法朗讀文件內容。」* Node counts: candidate 206, control 176 — recorded, not thresholded. |
| **8 structure on the caret path** | the heading placement's focused node carries `role: heading` where the fixture says `heading`; the other two carry no role where the fixture says none. `established: true` on all nine rows. |

## Term 6 — exactly one check moved

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --mutate projection-not-wired
```

| | PASS | NE | FAIL |
|---|---:|---:|---:|
| clean run (soak run 3, same page) | 38 | 2 | 0 |
| mutated | 37 | 2 | **1** |

Diffed **per check id** against soak run 3, not by tally: the set of ids whose
`outcome` or `ok` differs is exactly `["the-document-region-says-why-it-is-empty"]`,
PASS → FAIL, observing `{present: true, text: ""}` — the region present and
empty, which is what a screen reader reads as "document, blank".

The run is stamped `mutation: projection-not-wired` and carries
`verdict: "the mutation was detected by the check that owns it"`, so it can
never be banked as a clean run. **The page was restored** — both
`web/e2-editor-app.js` and `dist/e2-editor-app.js` hash
`5aeae0e1dbfe492d7de478962ac15bffd22aa6cfcdeea89737f529b6aa8d2de7` before and
after the mutation run, the baseline value.

A note on reading that run's own `ok` field: it is `true`, and that is the green
it should be. Under `--mutate` the runner does not report "no check failed"; it
reports "exactly the declared check went red and nothing else did". A mutation
run showing `ok: false` would mean the mutation was *not* detected.

## The judge's red cases

Not re-derived here. The corrected judge's red cases were exhibited before it
landed, over held records, in `../gate-4a-reading-rule/`: name-only reading red
on a green record; the reorder replay red under the old rule and green under the
new; the mispoint replay red in both terms; silenced-and-detached red in both.
Those are the cases that establish this judge can say no. This directory is what
it says about this page.
