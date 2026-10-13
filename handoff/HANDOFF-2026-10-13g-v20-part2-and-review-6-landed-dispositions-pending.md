# Handoff, 2026-10-13g — v20 part 2 (the page) and review 6 (the §6 engine-code review) landed; five dispositions and the owner's Makefile answer are pending; nothing linked, no product byte built

This round continues `HANDOFF-2026-10-13f-shift-arrow-deferred-137-registered-v20-part1.md` (read its "Part 1 result"). Authority is unchanged: the owner said 「有疑議的地方皆可發給fable，我授權他待我裁決」. **This round sent nothing to fable**: the owner stopped the session early because usage was running out (「兩條回來之後就告一段落，因為usage快用完了」), so every doubt it raised is listed under "Pending dispositions" for the next session to send. 10 commits, `c34f7b89..ba1e5256`, all 2026-10-13, about 22:20–23:20 +0800.

## Commits (`c34f7b89..ba1e5256`, oldest first)

| commit | what |
|---|---|
| `c34f7b89` | Brief 6 (`findings/evidence/link-batch/review/brief-6-engine-code.md`): the §6 review, four fixed questions (10-13f's proposal, Q1 and Q4 sharpened; §12.7's two flag questions are moot). Task `handoff/tasks/TASK-2026-10-13l-v20-page-number-on-the-page.md` (part 2). |
| `b273c98d` | Part 3, builder: `tools/build_e2_editor_v4_profile.py --page-rectangles` declares `editorContract.pageRectangles = "document-sdk-page-rectangles"`, refused unless the export list carries `_oxsdk_document_page_rectangles`; off by default (every existing invocation unchanged). 6 tests in `tests/test_e2_editor_v4_profile.py`, red first (1 failure, 7 errors), then 17/17. **Also** `findings/evidence/link-batch/v20-part3/makefile-v20.patch`: the v20 Makefile block, **not applied** (below). |
| `25a73406` | Task `handoff/tasks/TASK-2026-10-13m-mixed-page-fixture-native.md`. |
| `9a8fdd20`, `7c4ce074`, `7693435b` | Task 10-13m (sonnet): `tools/create_mixed_page_document.py` (8 pages: A4, A4L, A4L, A5, Letter, A4, A3L, A4; deterministic, sha256 `e7f7611f…`, reproduced by the main session), native runner and analyzer, predictions committed before the run, `findings/evidence/link-batch/page-rectangles/MIXED.md` and `mixed-round-20261013T145218Z/`. |
| `3fd2a1d9`, `3ff15b0c`, `bbc7cc84` | Task 10-13l (fable executor): part 2, the page. README `findings/evidence/link-batch/v20-part2/README.md`. |
| `ba1e5256` | Review 6 (opus) as delivered, not dispositioned: `findings/evidence/link-batch/review/review-6-engine-code.md`; the reviewer's scratch artifacts copied to `review-6-artifacts/` (native K1 probe source and raw output, the Q4 harness, lock-checker mutants as patches; `SHA256SUMS`). |

## State

| item | state |
|---|---|
| Releases | Unchanged. Nominal shipped, counted: **0.2.12**. Uncounted candidate: **0.2.18** (page `b24d754a…`, shell v66, host `96a87d8`). |
| Product bytes | **Source only, nothing built or linked.** Since 10-13f: `web/e2-editor-app.js`, `web/e2-editor.html`, `editor-shell-v2/narrow-editor-v2-session.js` (part 2), `tools/build_e2_editor_v4_profile.py` (builder flag). `dist/`, profiles, `Makefile`, pins, bindings, the host: untouched. |
| Tests (main session re-ran) | `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs`: **386/386** (344 at 10-13f). `node --check web/e2-editor-app.js`: OK. `python3 -m unittest tests.test_e2_editor_v4_profile`: 17/17. |
| Expected red pin | `tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree`, by design until the shell-generation freeze; it now names four dist copies (client, session, `document-sdk.js`, the page). |
| **Makefile** | **Waiting for the owner (finding 042).** The block is `findings/evidence/link-batch/v20-part3/makefile-v20.patch` (96 lines). It contains v19's compile rule plus `-DOXSDK_E2_V20_LINK_BATCH`; v19's export recipe plus `_oxsdk_document_page_rectangles`; the guarded link (`refuse_unasked_relink`); v19's packing with the tree's `sdk/sdk-worker.js` (the recipe checks sha256 `478d0da1…`) and `--page-rectangles`. `make -n` on a scratch copy printed the expected commands. The owner was offered **A** apply as drafted (main session's lean), **B** apply after the review is dispositioned, **C** amend it. **No answer yet. Do not apply without one.** If a disposition below changes the worker (none is expected to), the pinned sha in the patch moves. |

### Part 2 (the page), as reported and spot-checked

- `<div id="page-status" hidden>` after `#desk`, before `.statusbar` (the host hides `.statusbar` entirely, `templates/editor.php:51`). Not a live region. 「第 N 頁，共 M 頁」 / 「第 N–L 頁，共 M 頁」.
- Pure functions exported from the session module: `pageSpanOf`, `visibleRegionTwips`, `pageStatusText`. `PageRectanglesScheduler` (clock-free, injected `read`): reads once per opened document (keyed on the document object, so a reopen or restart reads again), on a `documentSizeChangedCount` change, and on a paint reply's `documentSizeChanged`. It never reads on `documentChangeSequence`, scroll, resize, zoom or caret moves. One read in flight; triggers during it collapse into one follow-up; a failure hides the line and consumes its trigger.
- Gated on `session.offersPageRectangles()` (new passthrough), so on v8 and v19 nothing changes.
- `editorState` has three writers (open, drain, push); all three now carry `documentSizeChangedCount`. The push's allowlist line is `narrow-editor-v2-session.js:498` (main session checked).
- `verified-boundary-noop` produces no toast and no reopen; no page change was needed.
- §34: the executor modified two existing tests (`page-paint-overlay.test.mjs`, `page-render-bands.test.mjs`: sandbox stub names only, assertions untouched). The witness is its first full run (9 failures, `ReferenceError: updatePageStatus is not defined`).
- Mixed-page measurement (10-13m): pages are **left-aligned** (x = 284 on every page) and the gap between pages is always 284. The page's span function intersects both axes over the full document width, so left alignment does not affect it. A v20 runner that maps a point to a page must say whether it uses "inside a rectangle" or "nearest rectangle": a point right of a narrow page lies in no rectangle.

### Review 6, as delivered (no BLOCKING)

- **Q1, C's window: COUNTEREXAMPLE for clause (c), not BLOCKING.** Measured natively 3/3 (§1.2). There are three positions where K1 changes nothing the barrier sees but Writer's own key changes the document:
  - (i) Delete with the caret in front of a numbering label (`crsrsh.cxx:341–347`; reachable from the product);
  - (ii) Backspace at the document start, first paragraph bulleted;
  - (iii) the same with a first-line indent.

  v19 refused these (`nothing-selected`, reopen, toast). v20 completes `verified-boundary-noop` after about 2.25 s, silently. `changed:false` is literally true and no selection is left, so C1 cannot see it. The reviewer offers **A** (a named residual) or **B** (case (i) only: refuse when the caret moved during the window, about three engine lines). README §2.1's "later, never different" is slightly wrong, in a harmless direction (§1.4).
- **Q2, locks: NONE.** Side note (not a defect today): `check_engine_lock_scopes.py` would not see a re-entrant `gMergeMutex` or a `gMergeMutex`→`gState.mutex` nesting. Two mutants exit 0 and the control exits 1 (patches in `review-6-artifacts/lockcheck/`). Under §34 this is "register only" unless a witness appears.
- **Q3, page-rectangles staleness: NONE in the engine.** Every stale reply the reviewer could build is followed by a `DOCUMENT_SIZE_CHANGED` sent after the request. The one path with no trigger is core's CalcLayout after an incomplete layout at load. It was complete natively and was never measured on WASM; P2's discriminating arm (§12.3) targets it. Requirement on the page: re-read on any push that arrives after the request was sent, **and after a BUSY failure**. **Check against part 2:** the scheduler collapses in-flight triggers into a follow-up (which covers the push case), but a failed read consumes its trigger. So a BUSY failure with no later trigger leaves the line hidden until the next trigger. The main session has not decided whether that meets the reviewer's requirement.
- **Q4, the `sourceSequence` bump: COUNTEREXAMPLE, SHOULD.**
  - The consumer is the base `EditorSession.placeCaret` (`editor-shell/editor-session.js:401–437`; called from `web/e2-editor-app.js:2280, 2694, 1728`). It takes `sourceSequence !== before` as the engine acknowledging the click.
  - A lone `DOCUMENT_SIZE_CHANGED` in the 22–28 ms before a same-line click lands satisfies the check. In the harness (3/3): v19 returned at 26–28 ms with x = 5000; v20 returned at 5–6 ms with x = 1000. A synchronous paste or format after that lands at the old x.
  - BLOCKING-grade only if a flush holding nothing but a size change exists on WASM, which is P2's arm.
  - The reviewer says the fix is in the page and needs no relink. **Before touching `editor-shell/editor-session.js`, run `check_e1_c_bundle_intact.py`.** That directory may be E1-C-bound; finding 068 was fixed with a subclass override for exactly this reason.

## Pending dispositions (send to fable together, per the owner's authority; numbers and file:line are in the files named)

1. **Review 6 Q1:** A (named residual, e.g. `L-C-number-or-indent`) or B (refuse when the caret moved; covers (i) only; it is an engine change, so it re-enters the define and moves nothing else). Also whether (ii)/(iii) need anything beyond a residual: Writer's Backspace at the document start of a bulleted or indented paragraph is a real edit the product now silently drops. Under v19 the product refused and reopened, which also did not do Writer's edit.
2. **Review 6 Q4:** where to fix `placeCaret`'s acknowledgement test (subclass override in `NarrowEditorV2Session` vs the base class), and whether the fix lands before the freeze (it is page/shell, no relink).
3. **Part 2 §4:** a `verified-boundary-noop` delete counts as a mutation. The measured chain: dirty, then a content stamp, then a checkpoint on the next boundary move, then an autosave of unchanged bytes on the host. The smallest change is part 2 README §4 (about ten lines, the operation flips its own queue item's `mutation`), not applied. Related precedent: findings 098/099.
4. **§34 questions on part 3's checks** (main session's reading, not yet ruled):
   - **X1** (`tools/check_profile_identity.py`) is v19-shaped. It requires the worker equal to the reference, equal export lists, and no new manifest leaf, so a correct v20 against v19 is red on `manifest`, `worker` and `exports`. The proposal is optional declared deltas (`--declared-worker SHA`, `--declared-new-leaf PATH=VALUE`, `--declared-export SYMBOL`); with none given the behaviour is identical.
   - **M1-1** (`tools/check_merge_key_undo_scope.py`): once the v20 rule exists, E2_V20 must be a carrier. Its `sdk_api.o` legitimately differs from base, but the tool requires a carrier's other objects to be equal, so it will be red. The proposal is per-carrier object sets, plus a run with base = the commit before part 1, to show the v20 define reaches only v20's objects. Part 1's README claims v15/v19 "preprocess byte-identically", but its run used base `5d77dc84` and so does not establish that.
   - **Question:** are these new uses for a new identity, or "repairs" that need a witness? The M1-1 witness exists as soon as the Makefile block is applied and the tool run.
   - `tools/what_the_link_ships.py` needs a `link-batch-v20` variant (data only; `--since c0337ae3`, the tree v19 was linked at); its `configurationDrift` needs the Makefile block first.
5. **10-13f Next 7 (Writer stack sweep, pre-W8, no link):** how to apply the 256 KB patch without touching a bound byte or a check. Main session's lean: a separately named diagnostic profile directory (a copy of the shipped Writer profile with the `probe.js` stack literal patched and its manifest's `profile` and `loaderSha256` rewritten), run through the unmodified product-path runner's `--profile`. Open: how to show the patch took effect without `probe_ods_on_profile.py`'s echo.

## Next (in order)

1. Ask the owner for the Makefile answer (A/B/C) if it is still missing; send pending dispositions 1–5 to fable in one brief.
2. Apply the dispositions. For a Q1 B, the engine change goes under the define with a red case. Then apply the Makefile block. Then the M1-1 run (the witness), X1's v20 mode and the `what_the_link_ships` variant, as ruled.
3. Write `handoff/RUNBOOK-relink-v20.md` in the shape of `RUNBOOK-relink-v19.md`:
   - archive first;
   - `env -u …` and `ALLOW_FROZEN_RELINK=1` on `dist/profiles/e2-editor-v20/sdk-manifest.json` only;
   - post-link checks: wasm hash; the export table has `oxsdk_document_page_rectangles`; `ScDocShell` 0; v8, v15, v18, v19 untouched; X1 in its v20 mode.

   **The link is the owner's.**
4. After the link: 10-13f Next 5, unchanged.
   - It adds P1 on the 60-page and the mixed fixture (10-13m).
   - Before counting, it adds §10.7's arm list. Its judge is `findings/evidence/132/held-into-refusal/judge_held_into_refusal.py:266–282` (`start-press`, `start-hold`, `end-hold`, `end-press-type`, `cell-start-hold`), plus `restore-window` in the 136 judges. Under C these expect 0 refusals, generations `['1']`, the document unchanged, and the marker at the caret. `cell-start-hold`'s `stage_is("nothing-selected")` also changes, because a cell start is a no-op under C.
   - Each one's first v20 shakedown is its §34.4 witness.
5. Still standing from 10-13f: the release text obligation (finding 137's three effects, both releases), the ordered-commands spec, the count chain's abort rule and 135's C2 semantics.

## §34.4

- This segment: repaired because of execution **2** (part 2's two test sandboxes; witness above), repaired because of review **0** (review 6 is recorded, nothing repaired).
- Session total, counted from 10-13e (10-13e and 10-13f segments plus this one): execution **3**, review **0**.

## Subagents (roles only; not reachable from a new session)

- **opus, adversarial reviewer:** review 6 (`ba1e5256`).
- **fable, executor:** part 2 (commits `3fd2a1d9..bbc7cc84`, trailer `Claude Fable 5.1`).
- **sonnet, executor:** 10-13m (commits `9a8fdd20..7693435b`, trailer `Claude Sonnet 5.5`).
- **Main session (opus 5.5):** briefs, the builder flag, the Makefile patch, this handoff. No fable ruling this round.
