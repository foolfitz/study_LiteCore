# Opus seat: review of `judge_v20_shakedown.py` before its first counted use (§34.3)

Read against HEAD `3b818514` (judge, runner and test files unchanged against HEAD; the merge runner, which another agent is editing, was read at HEAD). Every demonstration ran on a scratch copy (`git archive HEAD`) of the committed tools and on copies of the six committed reports. Scripts and their outputs are in this directory: `demos.py` / `demos-output.txt`, `p1_slack.py` / `p1-slack-output.txt`, `detector.py` / `detector-output.txt`, `census.py` / `census-output.txt`.

Scope note (§34.2). Each counterexample is tagged with whether the committed runner can produce its input in an honest run (**in-model**) or not (**out-of-model**: a NOTE at most). **No finding below changes the verdict of any committed report.** On the six reports the judge's PASS cells stay PASS when each fix is applied: `selectionType` is `"none"` 12/12, `toastsAfterKey` holds only open toasts, all 6 E2 instances were judged, and there are no duplicate cells. Every finding is about the first counted use.

## Summary

| Q | Verdict | One line |
|---|---|---|
| 1 Broken product, judge passes | **COUNTEREXAMPLE** | C1's "no selection at +500 ms" reads the engine's callback cache, not the fresh `readSelection()` that ARMS cites. The fresh read's field (`selectionType`) is recorded and no clause reads it. Also: C1's "no toast" only rejects reopen toasts; P1 can derive M=1 for a 60-page document from the page's own stale reply; a read on every `documentChangeSequence` passes both P2 and P3; no E2 instance can tell "caret before the key" from "caret at refusal". |
| 2 Passing product, judge fails | **COUNTEREXAMPLE** (E2), rest NONE or SHOULD | E2's reference is the last push the page *received* before posting. A caret callback that lands between the post and K1 makes the engine's correct P differ from it, so the judge reads FAIL. P1's strict `<` and the fractional paper height: NONE at the generated positions (slack ≥ 2,385 twips against a ≤ 1-row difference). C1's `generationStays1` and a partial placement-mismatch: SHOULD. |
| 3 Non-vacuity | **COUNTEREXAMPLE** | E2 reads PASS when the hold raised, when 4 of 5 cases were not placed, when the hold crossed no merge, or when the runner died after 2 cases (all demonstrated). P1 has no completeness check against the native page count. P2-c's population never includes a scroll (README claims one) and drops the click/End window. |
| 4 Two implementations | **NONE** | `span_of` ≡ `pageSpanOf` on every input the product path can deliver. They differ only on malformed strings, which the SDK parser rejects first. Both deviate from Writer in the same two ways (margins, never "no page"). `region_of` ≡ `visibleRegionTwips(visibleDocRows())` up to ≤ 1 device row outward, provided the page's `heightTwips` equals the reply's `docH` (unrecorded). |
| 5 Lone-flush detector | **COUNTEREXAMPLE** | ±25 ms classifies review 6's own scripted counterexample (lone 13 at 3 ms, click acknowledgement at 25 ms) as *flanked*. Acknowledgements at 26–28 ms read lone, so the reading depends on which half of finding 048's 22–28 ms distribution the click lands in. `NOT_LONE_IDS` matches the wording but not the hazard: 0 (tiles) bumps the sequence without moving the caret. 8 and 14 must not count as company. |
| 6 Exit rule | **COUNTEREXAMPLE** | Duplicate (browser, arm) cells: the judge prints `[chrome] p1-60: FAIL` and then `VERDICT PASS … exit 0`. A runner killed during E2 passes. `--expect-page` is optional. Loader, worker and manifest identity are never compared (the page sha binds only the profile name and the manifest's declared wasm hash). `counted: true` does not block. |
| 7 Red-case coverage | **COUNTEREXAMPLE** (census) | 10 of 28 judge rules have no dedicated red case (6 none at all, 4 collateral only). 11 of 13 runner predicates the judge depends on have none. The 8 C1 clauses, the 4 E2 clauses and P3's trigger arithmetic are only ever exercised as pre-set booleans. |

---

## Q1. A broken product this judge passes: COUNTEREXAMPLE

### 1a. C1: the +500 ms read checks the callback cache, not the engine's fresh read (in-model; the most important finding)

- ARMS.md:62 says the engine answers `editorGetStateV2` "after a fresh `readSelection()` … the projection carries `selection.collapsed` and `selection.rectangles` … on the v2 contract the same fact is `collapsed && rectangles.length === 0`."
- **It is not the same fact.** `handleEditorGetState` (`probe_engine.cpp:5937-5955`) uses the fresh `readSelection()` for `selectionType` and `selectionText` only. `selection` comes from `appendEditorState` (`probe_engine.cpp:1263-1274`), which serialises `gEditorState.selectionRectangles`. That is the TEXT_SELECTION callback cache (`probe_engine.cpp:2601-2606`). `readSelection()` (`3320-3341`) writes nothing into `gEditorState`.
- The worker passes `selection` through unchanged (`sdk-worker.js` `productEditorState`, HEAD:366-379, worker sha `478d0da1…`).
- The clause `noSelectionAt500ms` (`run_v20_shakedown.py:834`) reads `sel.collapsed` and `sel.n` only. The observer records `selectionType` (`run_v20_shakedown.py:189`), and no clause or judge rule reads it (`judge_v20_shakedown.py:101-123` iterates the runner's clauses).
- **Broken product that passes:** K1's selection exists in core at +600 ms but its TEXT_SELECTION has not reached the cache. That is L-C-late-K1, the case the read exists for. The fresh read says `"text"`; the cache says collapsed.
- **Mis-judged fields:** `engineRead.result = {"sel": {"collapsed": true, "n": 0, "observed": true}, "selectionType": "text"}`. The runner's own expression gives `noSelectionAt500ms: true`, and the round passes.
- **Demonstrated** (`demos.py` D6): `VERDICT PASS … exit 0`.
- **Fix:** add `result.selectionType == "none"` to the clause. It is the §10.5 wording, and the 12 committed reads already say `"none"`.

### 1b. C1: "no toast" is implemented as "no reopen toast among the last three toasts" (in-model)

- ARMS.md:62 asks for "no toast". The clause `noReopenToast` (`run_v20_shakedown.py:824, 835-836`) takes `toasts(session)[-3:]`. Those are the last three toasts of the whole page, which in the committed rounds are the three *open* toasts from before the key. It rejects only `已重新載入` and `，正在重新載入…`.
- An error toast after a noop (for example `EDITOR_BOUNDARY_UNSUPPORTED：…` without a reopen, or any "nothing to delete" message) passes.
- **Demonstrated** (D7): `toastsAfterKey = ["已開啟 p2-long60.odt", "已開啟 c1-C29-r1.odt", "EDITOR_BOUNDARY_UNSUPPORTED：游標已在文件開頭"]` gives clause value `True` and `VERDICT PASS`.
- This also regresses against the merge runner's own reviewed rule (`run_merge_wasm_shakedown.py` HEAD:684-685, codex B5: "from the key to the end of the case, nothing but the case's own saves").

### 1c. P1: the expectation is built from the page's own reply, so a stale M is self-consistent (in-model)

- `settle_rects` (`run_v20_shakedown.py:562-569`) returns the latest pageRectangles reply *to the page's own request*. P1's positions and M come from it (`:580-602`). `partsEqualsCount` (`:615`) compares two fields of the same reply.
- P2-c measured lazy layout on exactly this fixture: the first reply has 1 part, the settled reply 60, and the only re-read was the paint reply's `documentSizeChanged` (README §4).
- **Broken product:** a page whose `sizeChangeReported` path is removed (for example by trusting the spec's "the counter is the trigger" wording). It shows `第 1 頁，共 1 頁` on a 60-page document. The runner builds 1 centre position with expectation `第 1 頁，共 1 頁`, so P1-60 reads PASS.
- **Mis-judged fields:** `reply {parts 1, count 1}`, `positions` = 1 entry, `partsEqualsCount true`, `nativePages 60` (recorded, never compared; `judge_v20_shakedown.py:39-55`).
- **Demonstrated** (D8): `VERDICT PASS`.
- In a full run the exit code would be rescued by P2, but only by accident: P2's base also becomes 1, its target 2 never appears, and it fails as "expected 2, got 61". P1 itself is green.
- **Fix:** compare `reply.count` with `nativePages`, or have the runner ask the engine itself over the existing ask channel (`ASK`, `run_v20_shakedown.py:283`) for an independent count.

### 1d. A read on every `documentChangeSequence` passes P2 and P3 (in-model)

- The brief asks whether P3 catches it. **No, and the 2 s window is not the reason.** A pure scroll changes no `documentChangeSequence`, so such a page posts nothing during P3 (`pageRectanglesRequestsInWindow 0`, `untriggeredRequests 0`, giving PASS). P2 gets the right M (one read per Enter is still a read) and never counts reads per press (`run_v20_shakedown.py:629-666` records only `triggerBeforeIt` for the first matching reply).
- The trigger §10.8 forbids is therefore judged by no arm.
- **Fix:** in P2, count `rq/pageRectangles` per press against the size-change triggers, using P3's own rule applied to the edit window.

### 1e. P2-a "reads once, never re-reads": NONE

- `countAt2s` is the engine's reply to the *page's* request, as seen by the observer (`run_v20_shakedown.py:692-696`). It falls back to the last such reply during the presses.
- A page that never re-reads therefore yields `countAt2s` None or 60, and the text says `共 60 頁`, so lines 72 and 74 fire and the result is FAIL.
- Two weaker points:
  - (i) N at +2 s is unjudged, although the runner holds the geometry `g` and the reply to compute it (`:694`).
  - (ii) In the committed runs P2-b's page change happened at **press 1 of 16** (`remove.firstReplyWithTarget.press = 1`). Its "+2 s" is therefore ≥ 5 s after the change, so P2-b does not test the 2 s promise.

### 1f. E2: no instance distinguishes "the caret before the key" from "the caret at refusal" (in-model, code-read)

- The engine captures the cache at barrier start (`probe_engine.cpp:4213-4214`) and reports P when the attribution has it (`3388-3415`). P is `lastCaret_` at K1's non-empty TEXT_SELECTION (`merge_key_undo.hpp:138-145`).
- In C15, C16 and the hold (all `key-deadline`), K2 and Escape #2 return the caret to P before the key is posted, so the caret at refusal equals the caret before the key.
- In C17, F01 and F02 (`anchor-mismatch`), the refusal is raised from the TEXT_SELECTION branch (`probe_engine.cpp:3959`, `3775`). Writer queues the caret callback *after* START/END/TEXT_SELECTION in the same flush (`merge_key_undo.hpp:193`), so the cache still holds the pre-K1 caret.
- Hence in all 12 observed instances, the barrier-start cache, P and the cache at refusal are the same rectangle. An engine that captured `caretBefore` at the wrong moment would pass E2.
- The only discriminating class (a stage error after K1 moved the caret) is E3's, which is registered as unreachable. E2's PASS establishes "caretBefore equals the caret before the key in instances where every candidate definition coincides", which is narrower than the arm's name.
- **SHOULD:** say so in the README, or record the first push after the request as a negative control.

### 1g. P1's discrimination (in-model; a characterisation, minor)

- The generated positions sit at the maximum distance from every decision edge. `p1_slack.py` on the committed regions:
  - a constant offset of the region goes undetected up to **88 CSS px** (Firefox, mixed), 99 (Chrome, mixed), 276/297 (60-page);
  - a scale error goes undetected up to **0.38 %** (60-page) or 2.2–3.4 % (mixed).
- Any wiring error below roughly 88 px passes. Examples: measuring from the desk's border box, or counting a horizontal scrollbar or an overlaid header as visible.
- `hidden` is the DOM attribute (`GEOMETRY`, `run_v20_shakedown.py:293`). An element made invisible by CSS (the host already hides `.statusbar` with `display: none`, `e2-editor-app.js:240-243`) passes.

## Q2. A passing product this judge fails: COUNTEREXAMPLE (E2), rest NONE or SHOULD

- **E2 reference race (in-model class, not observed).**
  - The reference is the last `editor-state` caret the page *received* before *posting* the request (`run_v20_shakedown.py:876-880`).
  - The engine's `rect` is P, "where the caret was when K1 ran" (`probe_engine.cpp:3376-3383`). If a caret callback is processed after the page posted but before K1's selection, P is newer than the reference. Review 6 §4.3 documents that "the insert reply leaves before its caret callback", and the hold posts the next repeat 0.3 ms after the previous answer.
  - **Mis-judged fields:** `caretBefore {rect: C_new, sourceSequence: S}`, `referenceCaret {caret: C_old, seq: S}`, with a push `{caret: C_new, seq: S+1}` arriving at `t_request + δ`. `rectEqualsReference` is false and E2 reads FAIL, though the engine is right by §10.6.
- **E2 `sequenceNotAfterReference` when the source is P.**
  - The engine never sends P's sequence. `sourceSequence` is `caretBeforeSequence`, the barrier-start cache, in both sources (`probe_engine.cpp:3379-3383, 3412`), and the attribution keeps rectangles only.
  - With `source: "attribution-P"` (12/12 instances) the clause compares the barrier-start cache against the page's last push. It says nothing about the rectangle it sits beside.
  - It cannot false-FAIL in the race above (the barrier-start cache is not newer than the page's last push), but it adds no check on `rect` either.
- **P1 strict `<` at a coinciding edge; fractional `#paper` height: NONE.**
  - The page's region is `[floor(top·s), ceil(bottom·s)]` rows times `heightTwips/docRows` (`e2-editor-app.js:1278-1287`, `narrow-editor-v2-session.js:245-250`). Its net scale is `heightTwips/paper.height`, the same as the runner's `docH/paperHeight` (`run_v20_shakedown.py:462`), plus at most one row outward.
  - The page's region therefore contains the runner's, so the only possible error is a false FAIL. It needs a view edge within about 14 twips of a page edge, while the minimum slack at the generated positions is 2,385 twips.
  - `paperHeightPx` is an integer (74,142; 4,484) in all four reports anyway.
- **C1 `generationStays1` (SHOULD).** `rec["generationAfter"] == gen_before == "1"` (`run_v20_shakedown.py:832`) fails a round whose *open* consumed a generation, though the key consumed none. It is unreachable in the committed run (C1 reloads when the generation is not 1, and 6/6 rounds stayed at 1). Comparing `generationAfter == gen_before` is the property ARMS states.
- **C1 partial placement-mismatch (SHOULD).** One mismatch out of six gives "rounds judged 5 < 6", which is FAIL (`judge_v20_shakedown.py:120-122`). A harness flake is reported as a product failure. ARMS defines only the all-mismatch case.

## Q3. Non-vacuity: COUNTEREXAMPLE

All of these are in-model; each is demonstrated in `demos-output.txt`.

| input (what the committed runner writes) | rule that should stop it | judge |
|---|---|---|
| hold raised inside `arm_e2`, which catches it: `hold = {"error": "TimeoutError: …"}` (`run_v20_shakedown.py:983-984`); 5 cases judged | §10.6's hold is part of E2 (ARMS.md:72) | **PASS** (D2) |
| runner killed after case 2 (the last `FLUSH` at `:951`): `cases[:2]`, `hold: null`, no `completedAt` | none; `judge_e2` counts what it finds (`judge_v20_shakedown.py:131`) | **PASS** (D3) |
| 4 of 5 cases `placement-mismatch`, hold `hold-reached-no-refusal` | notes only (`:132-135`) | **PASS** (D4) |
| hold's first press refused, `merges: 0` | "按住跨過一次併段" needs ≥ 1 merge before the refusal; nothing reads `merges` | **PASS** (D5) |
| P1 from a 1-part reply (Q1c) | no `count == nativePages` or `len(positions) == 2·count−1` | **PASS** (D8) |

- **P2-c's population.**
  - ARMS.md:48 lists "open, settle, Enter, Backspace, scroll", and README §SUMMARY repeats "scroll". `arm_p2c` (`run_v20_shakedown.py:1027-1083`) never scrolls.
  - The click and End before the edits are drained and discarded (`:1049-1054`, a bare `drain(session)`). The click is the trigger in review 6's scenario.
  - `NOT_ESTABLISHED` therefore covers open, settle, Enter and Backspace only. The README's "scroll" is not measured.
- **Out-of-model (NOTE).** A runner revision that stops writing one C1 clause, with a selection present, reads PASS (D11): the judge iterates whatever keys exist (`judge_v20_shakedown.py:111`). The six committed reports come from three runner versions (README §1), and the judge never compares `runnerSha256` or the clause set.

## Q4. The two independent implementations: NONE

- **`span_of` against `pageSpanOf`.**
  - Same strict test on both axes (`run_v20_shakedown.py:439-440` vs `narrow-editor-v2-session.js:208-211`).
  - Same string order, first and last hit (`:443` vs `:229-235`).
  - The difference is malformed input. The page skips a bad entry for N and L and counts it in M; `parse_rects` refuses the whole string. Neither path is reachable: the SDK's `parsePageRectangles` (`document-sdk.js:106-130`) throws on any malformed or zero-area entry and on `count ≠ parts`, so the page never holds such a list. In that case the page hides the line and the runner reads NE. Neither is PASS.
  - `parse_rects` accepts negative numbers and zero areas that the SDK rejects. That would give an expectation against a hidden line, i.e. FAIL, the safe direction.
- **Which one is Writer's? Neither, identically.**
  - `SwViewShell::GetFirstLastVisPageNumbers` (`libreoffice-26-8/sw/source/core/view/viewsh.cxx:2964-2996`) subtracts the bottom margin for N and the top margin for L (L-page-margin, named). It also never returns "no page"; it falls back to the last or first frame.
  - `SwRect::Overlaps` on closed integer rectangles equals strict `<` on half-open ones, so the edge rule agrees.
  - At every generated position Writer's rule gives the same text. Margins are smaller than the 4,730-twip overlap at the boundaries, so L-page-margin is invisible to P1 by construction.
- **`region_of` against `visibleRegionTwips(visibleDocRows())`.** Same quantity up to:
  - (i) at most one device row outward on the page side (about 13.9 twips at these windows);
  - (ii) the height source: the page uses the session document's `heightTwips`, the runner the reply's `docH`. They agree once the paint reply has updated the size, but neither value is recorded per position;
  - (iii) when paper and desk do not overlap, the page falls back to the top rows and the runner to `None`.
- **Untested:** `span_of`'s string-order property has no red case. Every fixture is y-monotone, and the census mutation `min(hits)/max(hits)` survives.

## Q5. The lone-flush detector: COUNTEREXAMPLE

- **The window.**
  - Review 6's counterexample (`review-6-engine-code.md:115, 123`, appendix A) is a lone 13 at 3 ms followed by the click's own `INVALIDATE_VISIBLE_CURSOR` at 25 ms, so Δ = 22 ms.
  - `lok_summary` (`run_v20_shakedown.py:991-1010`) counts *any* id in `NOT_LONE_IDS` within ±25 ms as company. **Demonstrated** (`detector-output.txt`): acknowledgement at +22/+24/+25 ms gives *flanked*; at +26/+28 ms gives *lone*.
  - The detector is therefore blind to its own design case for about half of finding 048's 22–28 ms distribution. The bias is toward `NOT_ESTABLISHED`, the less severe grade for finding 138.
  - P2-c's question is flush membership. The right unit is the flush, which the worker-side `tw` (the patch stamps on the worker's handling, `build_merge_trace_profile.py:47-49`) can only approximate. A caret callback *after* the 13 is the hazard's completion, not company.
  - **SHOULD:** record each neighbour's Δ (the committed reports keep only names). As it stands, nobody can re-check whether the two observed size changes shared a flush with their tiles and cursor callbacks.
- **`NOT_LONE_IDS = (0, 1, 2, 3, 4)`.**
  - It matches the wording "no caret, selection or tiles callback". It does not match the hazard in review 6 §4: a `sourceSequence` advance with the caret unmoved.
  - In the engine's switch (`probe_engine.cpp:2590-2674`), 0 (`INVALIDATE_TILES`), 5 (`CURSOR_VISIBLE`), `A11Y_FOCUS_CHANGED` and 13 each bump `sourceSequence` without moving the caret. A flush of 13 + 0 with no 1 carries the same `placeCaret` false acknowledgement, but `lok_summary` calls it flanked (demonstrated).
  - 5 and the a11y callback push editor-state too, yet do not count as company.
- **8 and 14 must not count as company.**
  - `STATE_CHANGED` (8) only updates the format cache and sets no `editorStateChanged` (`probe_engine.cpp:2625-2637`). `SET_PART` (14) falls to `default`. Neither advances `sourceSequence` or moves the caret, so neither can pre-empt or confirm a click.
  - Counting 8 would mark almost every layout flush as flanked: 185 of the 202 open events are id 8.

## Q6. The exit rule: COUNTEREXAMPLE

1. **Duplicate cells: the last file in sort order wins** (`judge_v20_shakedown.py:197`, `load_reports` `:213`). In-model: an honest re-run left beside the failing report.
   - **Demonstrated** (D1): `report-chrome-main.json` with a P1 FAIL, plus `report-chrome-p1rerun.json` (green).
   - Output: `[chrome] p1-60: FAIL (33.9 s)`, then `VERDICT PASS (0 criterion cells not PASS, 0 missing) exit 0`.
   - The control with the order reversed reads FAIL.
   - **Fix:** refuse a second report for a (browser, arm) cell, or FAIL if any copy is not PASS.
2. **A runner killed during E2 passes** (D3, Q3). E2 is the last default arm, so every other cell is present. The judge does not read `completedAt`, `abortedAfter` or `observerAtEnd`. The other arms are protected: P1 by `partsEqualsCount` being written last, P2 by "remove: not run", C1 by "< 6".
3. **`--expect-page` is optional** (`:180`, `:433`). Without it no identity is checked at all (D9: a report about another page reads PASS). For a counted use it should be required, or read from ARMS.
4. **Identity beyond the page sha is never compared.**
   - The page sha binds the profile *name* and the manifest's declared `wasmSha256[:16]` (`run_e2_c_product_path.py:457-469`).
   - `profileHashes` and `workerServedSha256` are recorded (`run_v20_shakedown.py:1127, 1152-1153`) and never compared with ARMS.md's identity table.
   - A stale or edited `dist/profiles/e2-editor-v20/sdk-worker.js` or `probe.js` is "dist/ 過期", which §34.2 lists. It gives the same page sha and reads PASS (D10).
5. **`counted: true` prints a line and does not block** (`:184-185`; D12). The first counted use inverts this check's meaning either way.
6. **SHOULD:** `p1-mixed` run without `--window` (a wrong flag, §34.2) makes the view taller than every page. The arm then passes without testing a single-page reading on mixed page sizes; `singlePageViewPossible` is recorded and not read.

## Q7. Red-case coverage: COUNTEREXAMPLE (census)

Method (`census.py`): disable one rule at a time in a copy of the committed judge (and of the runner predicates the judge depends on), then run `--self-test` and the 6 unit tests.

**Judge, 28 rules, 10 with no dedicated red case:**

| rule | red case |
|---|---|
| P1 non-vacuity, hidden, text, `M ≠ parts` | `p1_no_reply`, `p1_hidden`, `p1_off_by_one`, `p1_parts` |
| P1 `expected is None` | **none** |
| P2 no press → NE | `p2_no_press` |
| P2 text M ≠ expected / count ≠ expected / text ≠ count | **collateral only**: each survives alone, and the pair (72 + 76) is killed by `p2_text_stale`. Line 76 is implied by 72 and 74 |
| P2 `hiddenAt2s`, `partsAt2s`, "remove: not run" | **none** |
| P3 non-vacuity, untriggered | `p3_no_paint`/`p3_no_bottom`, `p3_untriggered` |
| C1 NE, clause loop, < 6 | `c1_all_mismatch`, `c1_refused`/`c1_selection`/`c1_no_waited`, `c1_short` |
| E2 NE, clause loop, hold included | `e2_no_refusal`, `e2_differs`/`e2_null_rect`, `e2_absent` |
| P2-c lone → ESTABLISHED | `p2c: one lone size change` |
| P2-c "no lok events seen" | **none**: the red case checks the reading only, so ARMS.md:49's "never a quiet NOT_ESTABLISHED" is untested |
| runnerError → NE (all six arms) | **none**. For E2 this rule is the only guard against a partial run whose exception escaped |
| exit: page sha, no rule, trace worker, missing | unit tests and `criterion_on_trace_worker` |
| exit: duplicate cells, identity hashes, `counted` | **no rule exists** (Q6) |

**Runner predicates, 13 tried, 11 with no red case:**

- `caret_equal` reduced to x and y.
- `reference_caret` without the generation filter.
- `reference_caret` without "before the request".
- `sequenceNotAfterReference` removed.
- `LONE_WINDOW_MS` set to 39, and set to 3. The two detector red cases (+3 ms, +40 ms) pin nothing in between.
- `NOT_LONE_IDS` reduced to `(0,)`.
- P3's 2,000 ms window raised to 60,000.
- P3 `nonVacuous` without `reached_bottom`.
- `span_of` string order replaced by min/max.
- `parse_rects` accepting more than four numbers per piece.
- Only the strict `<` of `span_of` and `region_of`'s scale are killed.
- Not mutable offline at all, so there are 0 red cases by construction: the 8 C1 clauses (`run_v20_shakedown.py:827-837`), which live inline in `arm_c1`, and P3's trigger set (`:761-767`).

**Structural point:** every C1, E2 and P3 mutation in `mutations()` writes the runner's boolean (`clauses[…] = False`, `nonVacuous = False`) together with the raw field. The judge reads only the boolean, so these red cases test the judge's plumbing, never the predicate. That is how 1a and 1b went unnoticed: the predicates that decide C1 live in the runner and were never made red. Under §34.2 a hand-edited report is out of scope, but a predicate with no red case is in scope.
