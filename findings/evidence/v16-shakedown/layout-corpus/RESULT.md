# Result: corpus layout dry run (noise and red case), not counted

Prediction file: `PREDICTION.md` (committed before the run). Spec: `specs/SPEC-M3-paragraph-merge.md` section 21.2 (T = largest same-profile top-edge difference + 2 px). This run sets T; it is not the counted comparison.

Verdict, in the prediction's own wording, computed by `judge.py` (output: `judge-output.txt`):

| Prediction | Result |
| --- | --- |
| L1 noise: v16 vs v16, every comparable document identical | **HIT** (M = 0 px) |
| L2 red case: v16 vs v15, at least one cjk>0 document differs by more than T or in band count, in both pairs | **HIT** (7 documents in each pair) |
| L3 one variable: v16 vs v15, every cjk==0 document identical | **HIT** (0 differ in either pair) |
| L4 not-comparable set the same in all three, includes the three non-zip documents | **HIT** |

**M = 0 px, so T = 0 + 2 = 2 px.**

See "Unexpected" below before reading these HITs as coverage: 23 of the 71 comparable documents have zero bands in all three measurements.

## Command and environment

```
cd wasm_sdk_probe
python3 tools/compare_layout_corpus.py --profiles e2-editor-v16 e2-editor-v16 e2-editor-v15 --out ../findings/evidence/v16-shakedown/layout-corpus
```

- Tool `wasm_sdk_probe/tools/compare_layout_corpus.py` sha256 before and after: `21f90c3161a38d34ce0143fd48a83fe60d6e7b18a4bae1fa5e723216aaed64a7` (both; matches the expected value; files `tool-sha-before.txt`, `tool-sha-after.txt`).
- Exit code 0. `run.stderr.txt` is empty (0 bytes). `run.stdout.txt` has the tool's three summary lines.
- All three measurements: wasm `ad3f68bb85f94589`, boot state `ready`, 76 documents each.
- No other `tools/run_*`, `compare_layout_corpus`, geckodriver or chromedriver process was running before the start (`ps-before.txt`). A Chrome of the owner's desktop session (pid 1090372, 26 process lines matching `/opt/google/chrome/chrome` in `ps-before.txt`) was running throughout; the tool starts its own session (`ChromeSession("cold")`). I did not test whether it matters. `ps-after.txt` shows 23 such lines; no process of the tool is left.
- `git status` showed no change outside this directory (nothing in `dist/`, `web/`, `tools/`, specs).

Timings (UTC; `run-started-utc.txt`, `run-finished-utc.txt`, file mtimes):

| Event | Time (UTC) | Elapsed |
| --- | --- | --- |
| start | 13:12:50 | |
| `layout-0-e2-editor-v16.json` written | 13:35:14 | 22 min 24 s |
| `layout-1-e2-editor-v16.json` written | 13:57:32 | 22 min 18 s |
| `layout-2-e2-editor-v15.json` written (and `comparison.json`) | 14:19:51 | 22 min 19 s |
| total | | 67 min 01 s |

## Where the numbers live

- `layout-N-<profile>.json`: one per measurement, `documents[<path>]` has `state`, `toast`, `cjkCharacters`, `canvas`, `page`, `unsettled`, `runs` (the bands as `[top, bottom]`), `rowsSha`. The comparable set is the documents that have `runs`.
- `comparison.json`: three pairs in order (0,1) v16 s1 vs v16 s2, (0,2) v16 s1 vs v15, (1,2) v16 s2 vs v15; each has `comparable`, `identical`, `differ` (only the differing documents), `notComparable`.
- `judge.py` recomputes every pair from the raw `runs` and cross-checks `comparison.json` (all three pairs AGREE). Non-vacuity check: 76 documents per measurement, 44 with cjkCharacters > 0, 27 with 0, 5 None, same split in all three, as predicted; the script stops with exit code 2 if not.

## L1: v16 session 1 vs v16 session 2

| | Count |
| --- | --- |
| comparable documents | 71 |
| band count equal | 71 |
| band count different | 0 |
| documents with `runs` not identical (tops or bottoms) | 0 |
| max top-edge difference M | 0 px |

T = M + 2 = **2 px**.

## L2: cjkCharacters > 0, v16 vs v15 (T = 2 px)

42 comparable documents with cjk > 0. Seven differ by more than T, in both pairs identically; band counts are equal in all seven (so every difference is a top-edge shift).

| Document | cjk chars | Band count (v16 / v15) | Max top diff, (v16 s1, v15) | Max top diff, (v16 s2, v15) |
| --- | --- | --- | --- | --- |
| `test-docs/e1/a11y-audible.odt` | 165 | 12 / 12 | 39 px | 39 px |
| `test-docs/e2/d1-anchors.odt` | 14 | 31 / 31 | 20 px | 20 px |
| `test-docs/e1/multi-paragraph.odt` | 14 | 7 / 7 | 12 px | 12 px |
| `test-docs/e1/list-contexts.odt` | 14 | 11 / 11 | 8 px | 8 px |
| `test-docs/e2/list-split.odt` | 14 | 12 / 12 | 8 px | 8 px |
| `test-docs/e1/plain-grapheme.odt` | 8 | 8 / 8 | 4 px | 4 px |
| `test-docs/e1/paragraph-content.odt` | 7 | 27 / 27 | 3 px | 3 px |

`test-docs/t1-plain-zh.odt`, the example named in the prediction ("tens of pixels"), is not in this list: it has cjk 177, settled normally with 10 bands, and its bands are identical between v16 and v15 in both pairs (same for `test-docs/r7-compat/l0-t1-plain-zh.odt`). The largest difference found is 39 px, on `a11y-audible.odt`.

## L3: cjkCharacters == 0, v16 vs v15

27 comparable documents with cjk == 0 in each pair; 0 differ at all (runs identical) in either pair.

## L4: not-comparable sets

Identical in all three measurements (5 documents; each was `recoverable-error` with `LOK_ERROR：loadComponentFromURL returned an empty reference`, and the page rebooted to `ready` afterwards):

| Document | cjkCharacters | Zip? |
| --- | --- | --- |
| `test-docs/r7-compat/l3-bad-central-directory.odt` | None | not a zip file |
| `test-docs/r7-compat/l3-truncated.odt` | None | not a zip file |
| `test-docs/r7/r7-corrupt-truncated.odt` | None | not a zip file |
| `test-docs/r7-compat/l3-high-ratio.odt` | 177 | readable zip |
| `test-docs/r7-compat/l3-too-many-entries.odt` | 177 | readable zip |

The three non-zip documents are in the set. (See Unexpected, item 2, for how the set differs from the prediction's description of the five None documents.)

## Unexpected (reported, not explained)

1. **23 of the 71 comparable documents have zero bands in all three measurements.** Each was flagged `unsettled: true` by the tool (the canvas never gave two identical reads with ink in 25 tries), has `page: [-1, -1]` and `runs: []`. They are counted as "comparable" and "identical" by the tool and by `judge.py`'s L1/L3 definitions, because an empty list equals an empty list. Breakdown: 21 of the 42 comparable cjk>0 documents, 2 of the 27 cjk==0 documents, 0 of the 2 cjk-None documents that opened. So the HITs above rest on 48 documents that had bands (21 cjk>0, 25 cjk==0, 2 cjk-None). `judge-output.txt` section "coverage" has the counts. L1 restricted to documents that have bands: 48 documents, max top difference 0 px (same M). The 23 are mostly `test-docs/r7-finding-012/t2-*.odt` plus `t2-styled.odt`, `r7-t2-styled.odt`, `l0-t2-styled.odt`, `l1-layout-table-image.odt`, `l1-review.odt`, `l2-qa-redlines-and-comments.odt`, `l4-stress-100.odt` (full list in `judge-output.txt`).
2. **The not-comparable set is not the five "None" documents.** The prediction described the 5 None documents as three non-zip and two without `content.xml`. The two without `content.xml` (`l3-docx-disguised-as-odt.odt`, `l3-missing-content-xml.odt`) opened and were measured (they have bands). The two additional not-comparable documents are `l3-high-ratio.odt` and `l3-too-many-entries.odt` (cjk 177 each, failed to open). L4's stated criterion (identical across the three, includes the three non-zip documents) is met.
3. **Canvas height differs between the two v16 sessions for 10 documents** (2 to 7 px: 2201/2208, 1472/1476, 744/742 and similar). All 10 are among the 23 zero-band documents, so the band criterion did not see them. Canvas size is not part of the 21.2 criterion.
4. No page errors or timeouts were recorded: `run.stderr.txt` is empty, every measurement booted `ready`, the only non-`ready` document states are the five above.

Not diagnosed. No `--write` was used, `make` was not run, nothing outside this directory was modified.
