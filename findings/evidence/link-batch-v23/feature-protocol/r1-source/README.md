# R1 collector: source unit (uncounted, unexecuted)

Executes `handoff/WORKORDER-2026-10-27-v23-r1-collector.md` against `handoff/PROTOCOL-2026-10-26-v23-r1-inputs.md`. Source and tests only. Nothing ran in a browser and nothing was built. No R1 cell has a verdict: every cell is still `NOT_ESTABLISHED_UNPERFORMED`.

## What was built

- **Plan** (`wasm_sdk_probe/tools/v23_feature_selection_cases.py`, `r1()`):
  - The population is `collect_v23_r1_inputs.collect()`. The live collection and the committed `r1/native-inputs.json` must both hash to `6e13c04d…6fdd`, or the plan refuses.
  - Each fixture is bound by its sha256 from the index. Each cell's fixture is *identified by content*: the unique fixture whose native text rendering equals the cell's native text with the marker removed.
  - The output is 72 cells: 42 main, 18 wrap-keys, 12 wrap-drag.
  - The partition is 36 literal and 36 layout-relative, under the protocol's rule. Left/Right are literal for every shape. Home/End are literal for the six nonwrap shapes. Everything else is layout-relative.
  - The control rule is `emuend` exactly for the cells listed in `collect()['wrongOldClickControls']`: `wrap-keys/m1e/Down`, `wrap-drag/m1d/Down` and `wrap-drag/s1d/Down`. Every other layout-relative cell uses `emu`. Those three cells also carry `wrongOldClickControl`, with the old emulated landing mapped to a logical position (`[0,270]`, `[0,270]`, `[0,199]`).
  - `config()` gains `r1` and `r1Fixtures`; the instrument closure now includes `collect_v23_r1_inputs.py`. The plan refuses overlapping population identifiers.
- **Page** (`wasm_sdk_probe/web/v23-feature-selection.js`): adds `r1PointPlan` (the same plan as Python), `r1Walk` and the controls `prepareR1`, `shapeR1`, `controlPointR1`, `finishR1` and `markerR1`. The existing functions are unchanged.
- **Runner** (`run_v23_feature_selection.py`): adds `--population r1`, `run_r1` and `actual_marker`. `fresh()` gains an optional served name; its default and predicate quoting are unchanged.
- **Reader** (`judge_v23_feature_selection.py`):
  - The R1 functions are `inspect_r1`, `r1_arm`, `r1_walk`, `r1_drag_end`, `r1_marker_witness` and `r1_literal_premise`. `judge(cells, plan, 'r1')` aggregates them.
  - `Evidence.opened()` takes an optional fixture sha (R1 arms open their own fixture).
  - `inspect()` dispatches R1 identifiers.
- **Tests**: `wasm_sdk_probe/tests/test_v23_feature_r1.py`, 48 tests.
- **Sweep**: `reader-mutation-sweep.py` (this folder), with its output `reader-mutation-sweep.output.json`.

## One cell, once per browser

1. **Readiness**, unchanged: the selection fixture `list-contexts.odt`, the typed `Z` and the two saves.
2. **Control arm** (`r1control`, layout-relative cells only):
   - It opens a fresh document of the cell's fixture and makes the shape in that document.
   - It takes the shape's rectangle from its own before-state:
     - `emu`: the visible cursor `caret`;
     - `emuend`: `selection.end`, which is `TEXT_SELECTION_END`.
   - It places the caret at `(x, y + floor(h/2))` and witnesses the result: collapsed, with the caret rectangle at that `(x, y)`.
   - Then it sends the same unshifted real product key.
   - It ends with the delayed readback, the `#` marker and the export.
3. **Candidate arm** (`r1cand`):
   - It opens a fresh document and makes the shape.
   - It sends the unshifted real product key from the range, with no collapse click.
   - It ends with the delayed readback, the marker and the export.

Comparison:

- **Literal cells:** the export's marker `(paragraph, code-point offset)` is compared with the native mapped landing.
- **Layout-relative cells:** the candidate's marker position *and* its readback caret `(x, y)` are compared with the control's.

## Choices left to the executor, with their evidence

### 1. Marker position form

- **Native side.** The native text (`.uno:SelectAll` text/plain) is the fixture paragraphs joined like this:
  - paragraphs by `\n`;
  - cells of one table row by `\t`;
  - a hard line break (U+2028 in the save) as `\n`.

  `r1_rendering()` builds that string from the fixture's own topology (`r1_layout()`, which refuses notes, frames, nested, covered, repeated or spanned cells). Each paragraph then has a span `[start, end]` in the string.

  Every marker index maps to the unique `(paragraph, offset)` whose span contains it. The spans are disjoint because separators lie between them. Each observation is then round-tripped: inserting `#` into the fixture paragraphs at that position must reproduce the native marked text exactly.
- **Browser side.** The marker is found in the product's own save, read with `paragraph_texts_from_xml`. The save must equal the fixture paragraphs with exactly one `#` added (`r1_saved_marker()`). Only logical positions are compared, never raw string indices.
- **Evidence.** `R1MarkerMapping` covers all 216 retained observations:
  - It reads each raw `ref` record from its own path and line.
  - Each maps to the cell's fixture and logical landing, and round-trips.
  - For every fixture, position mapping and index mapping are exact inverses over every index.
- **Typing the marker.** The marker goes through the product's typing path as a real trusted key, the same way readiness types `Z` (`actual_Z`):
  - Chrome: CDP `keyDown` with key `#`, code `Digit3`, VK 51 and text `#`, then `keyUp`.
  - Firefox: `v21_input.key(session, 'firefox', '#')`.

  The page binds no `#` key. The sink's default action produces `beforeinput insertText "#"` and the adapter's `insertText`. Chrome does not use the v21 one-character rule because for `#` it sends VK 35, which is End's virtual key code (asserted in `test_chrome_marker_avoids_the_end_virtual_key`).
- **Reader checks on the marker.** Within the marker window, the reader requires:
  - one trusted `#` keydown in the editable sink of this document, after the delayed read;
  - one trusted `beforeinput`;
  - exactly one `insertText {text: '#'}` in the arm's generation, inside the window, answered `ok`;
  - no other mutation;
  - a final save, after the insertion's terminal, that is bound to its wire bytes.

### 2. Shape materialization

Every shape setup starts from public search, placement and the six moves. Points are located with the existing `locate()`:

- search the paragraph's text up to its first hard break;
- click the first rectangle and verify the text start;
- make *n* public `move-character-right` moves, or a `move-line-end` for a line end;
- check the prefix with a public text-handle selection;
- restore the point and read it back.

The shape is then made through real product keys or a real pointer drag. No native coordinate or native wrap offset enters any browser input. The recipes (`R1_SHAPES`) restate the as-run `Shape` table logically. The plan cross-checks every recipe against the native records: with the native W=101 and B=89, taken from the as-run `discover-*` rows bound by `collect()`, each recipe reproduces the native selected text (`test_recipes_reproduce_native_semantics_with_native_wraps`).

| Shape | Browser setup | Readbacks that prove it (each NE when it fails) |
| --- | --- | --- |
| p2-forward / p2-backward | place at P2:9 / P2:19, then 10 product Shift+Right / Shift+Left | made text `BETA GAMMA`; range; caret = located P2:19 / P2:9; {start, end} = {P2:9, P2:19} |
| s1, m1r | discover W by the walk (below); place at W−10; 10 product Shift+Right | made text (native); caret = located W (line-2 start, from the walk's transition); {start, end} = {W−10, W} |
| s2 | place at 1:9; 11 Shift+Right | `visual line`; caret = 1:20, located with the hard-break segment query; {1:9, 1:20} |
| s3 | place at 2:25; 10 Shift+Right | `paragraph\n`; caret = 3:0, the existing empty-paragraph rule; {2:25, 3:0} |
| s4 | place at A1:3; 7 Shift+Right | `cell A1`; caret = A1:10; {A1:3, A1:10} |
| s5 | place at A1:11; 5 Shift+Right (crosses into B1) | the cell-selection witness is the made text `S4 cell A1 text\tS4 cell B1 text\n`, which no ordinary text range from A1:11 can produce; caret = B1:0; {start, end} = {A1:11, A1:15}, the native `TEXT_SELECTION_START/END` semantics, checked natively against s4's Right/End cursors; selection type recorded |
| s1e, m1e | place at W−10; one product Shift+End | made text; caret = the located line-1 end (End from the text start; first-line witness); {start, end} = {W−10, W−10+len(made)} by Right walk, so m1e's selection end is line-2 start while its caret is line-1 end (the two-location affinity) |
| s1d, m1d | real drag from the located caret at W−len(made) to the release point (below) | made text; caret on line 1 at or right of the located line-1 end; {start, end} = {W−len(made), W}, where W is line-2 start |

- **Wrap discovery.** A fresh Right walk in each arm's own fresh document: search, click the text start, then public Right moves, each followed by a state read. W is the first step whose caret y differs, bounded by the paragraph's code-point length (a closed bound, no open scan). The reader recomputes W from the raw walk. Both arms must agree on W.
- **Drag release point** ("past its right edge", from public geometry only). The point is the middle of the paper between the first displayed line's search-rectangle right edge and the document width (the open reply's `width`), at that line's height + h/2. The reader recomputes it from the raw search terminal and the open metadata, and requires `right < x < width`. Pointer events, the product's own click and the `editorSelectRangeV2` requests are bound with the existing `drag_witness`.
- **Selected text.** Every shape must reproduce the *native* selected text exactly (the protocol lists selected text first). The selection type must be `text` or `complex`, and is recorded.
- **Wrap mismatch.** If the browser wraps the S1 paragraph anywhere but 101, `scar papa ` cannot be reproduced: the occurrence is unique, so the setup is NE.

### 3. Literal premise for the twelve literal Home/End rows

The premise kind is derived from the point's paragraph:

| Kind | Rows |
| --- | --- |
| `single-visual-line` | p2-forward, p2-backward |
| `hard-break-line` | s2 |
| `empty-paragraph` | s3 |
| `table-cell-line` | s4, s5 |

The witness is the shape point's own located search: exactly one rectangle (one displayed line, up to the hard break for s2), and the setup caret on that rectangle's y. An empty paragraph is one line by construction; it is reached only by the existing empty-paragraph rule with its prefix witness. A failed premise is NE, never relabelled. Its red cases make P2, the A1 cell and the hard-break line wrap in the model.

### 4. Three fixtures in the existing machinery

- **Readiness and identity.** Readiness is unchanged. The page still boots `list-contexts.odt`, which is the selection fixture.
- **Served fixtures.** The mirror serves each original FODT under its own `.odt` alias, which the SDK's non-ODS suffix guard requires: `r1-arrow-selection.odt`, `r1-arrow-selection-shapes.odt` and `r1-arrow-selection-wrap.odt`. `verify_mirror()` checks them and returns them in the receipt.
- **Opening an arm.** `fresh(session, target, servedName)` opens each arm. The page refuses to prepare unless the current open has the cell fixture's name and sha256.
- **Reader bindings.** The reader binds each arm's open record, the wire open bytes and the original save to that fixture's sha256 and paragraphs (`fixtureSha256` per cell, via `plan['r1Fixtures'][row['fixture']]`).

### Other classifications, also choices

- **Order of checks.** All setup, control, key-ownership and timing witnesses come first and are NE. Then the candidate's accounting (changed/revision) and its collapse (readback collapsed, active selection `none` and empty) are FAIL. After that, the marker and export witnesses are NE. Last come the comparison FAILs.

  The candidate's FAIL checks deliberately precede the marker check. An uncollapsed result makes `#` replace the selection, and an export check placed first would mask that FAIL as NE.
- **Control outcomes.** The same control outcome is NE ("independent control outcome invalid").
- **Recovery.** Recovery events are FAIL, as in S3/S4/S5.
- **Delayed readback.** The delayed readback reuses the existing 500 ms S2 observation interval. No new timeout, tolerance, repetition or statistic is introduced.
- **Native/browser setup comparison.** Whether the browser setup sits at the native logical position is *recorded* on every literal cell (`setupAtNativePosition`) and in a FAIL reason, but never asserted. See Q1.

## Open questions for the root

1. **Q1: token wrap exposure on 6 literal cells.** These are the Left/Right rows of m1r, m1e and m1d.
   - The token's ten letters `insxchmrwb` occur at offsets 12, 79, 110, 141, 172, 208, 239, 270 and 301 (`test_made_text_alone_does_not_pin_the_token_wrap`).
   - If the browser wrapped the token at any B with B−10 in that set (B ∈ {22, 89, 120, …}) other than the native 89, the setup would reproduce every recorded semantic, including the native selected text.
   - The protocol's absolute literal comparison would then read **FAIL**. That would be a layout artifact.
   - The S1 shapes are not exposed: `scar papa ` is unique.
   - I first wrote an NE premise for this and removed it, because it is a criterion the protocol does not state. The reader now marks such a FAIL `(setup not at the native logical position)`.
   - Whether to add the premise is the root's decision (`test_token_wrap_exposure_is_recorded_not_decided` pins the current behaviour).
2. **Q2: pre-red report for a qualifying R1 run.** The runner requires `--pre-red-report` for any non-preparation run, inherited from S2. The R1 protocol does not mention the v19 pre-red. Is it a prerequisite for a counted R1 run?
3. **Q3: s5 selection type.** The reader accepts `text` or `complex` and records it. Requiring `complex` would be a predicate on an unmeasured browser value.
4. **Q4: drag release point.** I chose the middle of the margin right of the first line. Native used x 11400 / 11700, just past the 11390 text edge. Any public point right of the line edge satisfies "past its right edge".
5. **Q5: layout comparison.** I read "caret/logical marker" as requiring both the caret `(x, y)` and the logical marker. Same offset with a different affinity reads FAIL (`test_same_offset_other_affinity_fails`).
6. **Q6: causal controls.** The three wrong-old-click Down cells are distinguished (plan, per-cell record, aggregate list) and run only the protocol's `emuend` control. A browser causal arm with the old `emu` click for them would be a new arm, so it was not built.
7. **Q7: unexecuted public paths.** These are untested in any browser:
   - search with the full 463 and 330 code-point paragraphs;
   - text-handle prefix selection to a line-2 start;
   - restoring a line-1-end point by click;
   - Shift+Right across A1 into B1 (the cell selection);
   - the `#` key in both browsers.

   Any refusal is NE for the cells involved.

## Not executed

No browser, preparation, counted run, build or native run took place. The synthetic pages in the tests model a layout (`Doc` in the test file); they are not evidence of the browser's layout.

Cost indicator from those pages, not a timing: the public calls per arm are:

- wrap shapes: about 385–435 (walk, three located points);
- the other shapes: 47–67.

Layout-relative cells run two arms. No per-cell time has been measured.

## Results (worktree)

- **Tests.** The existing tests are unchanged and pass: `test_v23_feature_selection.py` 39 (1 skipped, the counted-05 raw cells, as before), `test_v23_r1_inputs.py` 8 and `test_v23_feature_s_cases.py` 7. The new `test_v23_feature_r1.py` passes 48 tests, including:
  - all 72 cells PASS on the model;
  - the aggregate over 144 pages, with the three wrong-old-click controls per browser;
  - red cases for every NE/FAIL clause of the protocol's last section;
  - JS/Python point-plan parity, the runner sequence and the mirror aliases;
  - a re-read of all 35 preserved pages of `selection-prep-07` and `s5-prep-03`, each with its own stored config, which gives the stored inspection exactly.
- **Mutation sweep.** `reader-mutation-sweep.output.json`: `ALL_KILLED`, 61 of 61. It binds the reader and test sha256 it ran against.
  - 55 are condition-disabled mutants. These are the census of every `need`/`contradict`/`check` in the six R1 reader functions, found by `ast`, so a new check is swept automatically.
  - 6 are text mutants: the emuend rule, the oracle branch, the caret rule, the premise branch, FAIL-vs-NE for the candidate, and the aggregate's control list.
  - The unmutated baseline is green.
- **Environment.** In the worktree, `wasm_sdk_probe/dist/profiles` and `wasm_sdk_probe/build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6` are read-only symlinks to the main tree. The 13 served v76 shell files under `wasm_sdk_probe/dist/` are copies checked against the bundle pins. All of these are git-ignored.

## Merge note

The changed tools, `web/v23-feature-selection.js` and the config are in the import closure of the counted S5 run (`s5-counted-01`). Merge only after that run ends. After the merge, new runs bind the new served-source and instrument hashes. Preserved pages keep reading with their own stored configs, which is tested.
