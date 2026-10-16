# Item 1 smoke (Chrome, N=1): a development run, NOT evidence

Task: `handoff/tasks/TASK-2026-10-16d-v21-shakedown-phase-b.md` ("Where to stop"). Arms: `../../ARMS-item1.md` (rulings §8), `../../ARMS.md`. This is one pass of every item-1 arm in Chrome only, under the S-9 lock, with `--smoke`. **It is never judged as evidence**: the judge refuses smoke reports unless `--smoke-preview`, and then labels every line "SMOKE (not evidence)" and exits 3 [source: `wasm_sdk_probe/tools/judge_v21_shakedown_item1.py`, `judge_reports`]. The evidence runs (N=3, Chrome then Firefox) have not started; the main session reviews this first.

## Files

- `report-chrome-d1-…-d6-20261017T010731.json`: the runner's report (`wasm_sdk_probe/tools/run_v21_shakedown_item1.py`, `smoke: true`, `counted: false`). Identity block per page variant (`pages`), pre-run checks, foreign-CPU samples, every arm's raw logs.
- `docs/chrome-20261017T010731/`: every saved document the judge reads.
- `judge-preview.txt`: `judge_v21_shakedown_item1.py --dir . --expect-page 3d511216… --rounds 1 --smoke-preview` (exit 3 by design).
- `../item1-d2/`: D2's no-host predictor (page v21) and its 0.2.24 red case (dist/'s page), `run_v21_d2.py --smoke`.

## Identity

Page served `3d5112161b23b060…` (= `build_cutover_page.py --profile e2-editor-v21`, no `--write`), shell digest over the mirror `e0252c0b22d37a20…` (= ARMS.md §1), profile `e2-editor-v21` hashes as ARMS.md §1, `identityOk: true` for the v21 variants; the v20 page (D5-w) and the 0.2.24 page (D8's red case) carry their own identities in `pages` [observed: the report's `pages`]. Chrome 151 headless, window 1400×1000.

## Per arm (one line each; preview verdicts, labelled smoke)

| arm | outcome (smoke) | what it showed |
|---|---|---|
| D1 | PASS 38/38 + both controls | every landing equals the native one; selection observed 104–208 ms after `ready` (D-6); controls at body 1 off 5 and body 5 off 2 |
| D4 | PASS 6/6 | **arm-text deviation**: on an open range the page's place-caret request is `click` (v67's path, `narrow-editor-v2-session.js:734-737`), not `editorPlaceCaretV2` as `ARMS-item1.md` D4 names it; the judge accepts either and prints `DEVIATION-D4-op` for the main session |
| D7 | 58 presses PASS, 6 NOT_ESTABLISHED (foreign CPU), 0 FAIL | cursor presses 33–50 ms `documented-callback-*`, silent presses 250.6–251.2 ms `verified-move-readback`, every +500 ms read posted 500.1–500.9 ms after the reply, reply caret = read caret in all 58 |
| D2′ | PASS | witness Z at body 1 off 0; the Backspace-alone control turned P2 into a list-header (`verified-key-undo`); back to back: the Backspace keydown 3.8 ms after Ctrl+Home's, before the move's reply; move `documented-callback-visible-cursor`, Backspace `verified-boundary-noop`, P2 unchanged |
| D5-w | PASS | v20 page: no chord prevented, no move posted; v21 page: Ctrl/Cmd+Home/End prevented with one move each, Shift+Ctrl+Home not taken |
| D8 | **FAIL on (e) — a product red** (a)–(d) pass; 0.2.24 red case red as required | see "Product red" below |
| D9 | 3 of 4 sub-arms done, 1 NOT_ESTABLISHED (foreign CPU) | flagged hold: 1 move, ready 0 ms after release; unflagged bursts: 3 moves, ready 28–29 ms after release |
| D10 | NOT_ESTABLISHED (foreign CPU) | measured anyway: Ctrl+End `documented-callback-visible-cursor`, `第 60 頁，共 60 頁` at both reads, 60 rectangles |
| D11a | PASS | view-only through the host shim: the move completed, the caret moved, `hasUnsavedWork` false before and after, no save |
| D11b | PASS | clean: no save, 「無」; dirty: one checkpoint `save` before the first move, 「有（r1）」, none before the second, dirty stays true |
| D11c | PASS | both stale-revision moves dispatched by the engine; the SDK reports `EDITOR_RESULT_INVALID` for both (spec §12.2 (f) observation); `insert-paragraph-break` → `STALE_REVISION` |
| D12 | PASS | on both ranges 22 and 23 refused `EDITOR_FORMAT_GESTURE_UNSUPPORTED`, selection and revision unchanged; on a caret the move completed |
| R-xlc (record) | 3/3 recorded | Backspace after Ctrl+Home: `verified-boundary-noop` (waited 2252–2256 ms), document unchanged — Writer would have changed the list or the indent (L-C-number-or-indent) |
| R-table (record) | recorded | Ctrl+Home to B2's start, Backspace refused `EDITOR_BOUNDARY_UNSUPPORTED`, reopened (generation 2), document unchanged |
| D6 (record) | recorded, **marker absent** | see "Observations" |

## Product red (kept, described, not fixed)

**D8 (e)**: from «Bravo|», Backspace @0, Backspace @20, Ctrl+End @40, Delete @60. Expected P2 «Bra second paragraph» with the Delete a no-op at the end; got «Bra scond paragraph»: the Delete removed a character in P2 [observed: the saved document]. The request order in the log [observed]: `delete-backward`, `delete-backward`, `editorGetStateV2`, `editorPlaceCaretV2`, `delete-forward`, `save` (checkpoint), `move-document-end`. Reading of the log [inferred, from `web/e2-editor-app.js:3322-3337` and `:3276-3294`]: when Ctrl+End was pressed a delete was in flight, and the page's state showed the delete barrier's one-character selection, so `sendDocumentMove` took `moveFromPoint`; that enqueues the click first and enqueues the move only after the click resolves, so the Delete pressed meanwhile was enqueued between the click and the move and ran at the click point. The same in the development run before the smoke (scratchpad, not kept). This is what D8 exists to catch; the §11 default for D8 is 「頁面保留今天的扣住規則，具名 L-142-held-after-move」.

## Observations (not verdicts)

- **D6**: the 64 KiB paste completed (revision 1, dialog closed after 1,526 ms), a checkpoint `save` ran before the move, and `move-document-end` completed `verified-move-readback`. The `Z` keydown reached the sink 3 ms after Ctrl+End's (not prevented), but no `beforeinput` and no `insertText` were recorded, and the saved document has no marker [observed]. Not investigated further (a record arm).
- **A document move right after a checkpoint save completes by readback.** In D8 (e) the `move-document-end` reply came 253 ms after the request, `verified-move-readback`, with the caret still in P2 [observed]; D6 and the development run of D11b dirty show the same completion after a checkpoint save. None of these presses is in D7's population (D7's arms are clean documents). This is the shape spec §9.1 names L-142-readback-overtaken.
- **Foreign load** (ARMS.md §2, D-18 A′): the gate marked 6 D7 presses, one D9 sub-arm and D10 NOT_ESTABLISHED. Over the limit [observed: the samples kept in the report]: another session's Python script (`pop_mut.py`, 99.5 %), the owner's desktop Chrome with an extension relay (66–126 %), and the owner's Zen browser (60 %). None is ours; the evidence runs need a quiet desk.

## Runner errors (§34.4)

Two development runs lost d11a/d12/d11c to the page's leave prompt; witnesses in `../witness-item1/` (committed before the fix). The smoke itself lost nothing to the runner. Tally: modified because of execution 1 (the leave-prompt fix, after one ineffective attempt); modified because of review 0.
