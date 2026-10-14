# Task 2026-10-14h: finding 140's fix, second pass (integer twips, and the click back to v67's speed)

**Authority.** The owner chose B at the end of 10-14: a fresh fable does the second pass of finding 140's fix. You decide the design on the owner's behalf; write the reasons into `findings/140-…md` (a new append-only `裁決（第二輪）` section, zh-TW) and into `findings/evidence/paste-latency/README.md` (English).

**Read first.**
- `findings/140-a-click-below-the-first-line-of-a-blank-document-holds-the-queue-for-30-seconds.md` (the 裁決 section);
- `findings/evidence/paste-latency/README.md` (Ruling and Witness sections);
- `findings/evidence/link-batch/v68-witness/README.md` (the red witness);
- `handoff/HANDOFF-2026-10-14-v20-linked-v67-frozen-new-document-0.2.19.md`, Addendum 2;
- the first pass: `git show 6c761117 -- wasm_sdk_probe/editor-shell-v2/`.

## The two defects (from the red witness; the main session checked the source, not with a probe)

1. **Half-integer y.** The page calls `session.placeCaret(caret.x, caret.y + caret.height / 2)` (`web/e2-editor-app.js:1821` reopen, `:2787` `moveFromPoint`). With an odd caret height (`s3`: 277) y is x.5. `editorPlaceCaretV2` rejects non-integers (`sdk/sdk-worker.js:1552`), and `PLACE_CARET_FALLBACK_CODES` holds only BUSY and UNSUPPORTED_OPERATION, so the error reaches the user as a toast and a range selection is left. v67's `click` path took the same value into `ccall` with type `"number"` and an i32 parameter; that it was truncated toward zero (ToInt32), not rounded, is the main session's reading and unverified.
2. **Every collapse click waits for the engine's deadline.** In 129-B the click is `moveFromPoint` collapsing a range at the caret's own point. The caret does not move, so no `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` arrives (the engine's required callback, `src/probe_engine.cpp` `handleEditorPlaceCaret`), and the engine answers at `EditorPlaceCaretDeadlineMs = 250`. v67's polling path saw the selection change and returned in 26–32 ms. This is inferred: `completion` was not recorded in 129-B. Confirm it before you build on it.

Claims above that you find wrong are findings for your report, not things to work around.

## What to deliver

- A second-pass change in `wasm_sdk_probe/editor-shell-v2/` that fixes both. The design is yours; the handoff names two directions (v67's polling first and the engine only when the polling has not converged; or the reason the engine answers at its deadline). Things the main session sees as costs, to be checked, not assumed:
  - `web/e2-editor-app.js` is pinned (`FINAL_PAGE_SHA256` `7815e16c…`); a page change means a re-pin and a new page identity.
  - `editor-shell/` is E1-C-bound (`check_e1_c_bundle_intact.py`); the override pattern in `narrow-editor-v2-session.js` exists for that.
  - A second mouse click at the same point after v67's `document.click` may or may not be read by core as a double click (LOK passes `count` explicitly). Unverified.
  - While the engine's place-caret is pending it holds `gEditorPending`, so the next callback-correlated operation gets BUSY.
  - An engine change (e.g. completing on `TEXT_SELECTION` as well) needs a link. If you think it belongs in the next link batch, say so; do not make it.
- Unit tests, red first on the current bytes (session `fc5ac883…`), green on yours:
  - a half-integer y (odd caret height) does not end in `INVALID_ARGUMENT` or a toast;
  - a collapse click whose selection changes resolves without waiting the engine's deadline (model the engine's 250 ms answer in the fake);
  - `place-caret-blank-page.test.mjs` and `place-caret-acknowledgement.test.mjs` (138's arms) stay green, unchanged;
  - the whole `editor-shell-v2` suite stays green; report the count.
- `check_e1_c_bundle_intact.py`: `"intact": true` before and after.
- A browser witness of the blank-page click with `tools/probe_paste_latency.py`, as the first pass did, on v19 (`dist/`, after `make e2-c-assets`) and on v20 (`build_cutover_page.py --out`, never `--write`), Chrome and Firefox.

## Criteria (written before any run; the default if never met: v68 is not frozen, the host stays on 0.2.19 / shell v66, finding 140 stays open on shipped releases)

- **C1 (blank page, paste-latency probe).** Page-middle and 25 %-down clicks on a new blank document: no toast, and the paste's `insertText` is sent within **1,500 ms** of the click, in both browsers, on v19 and v20. First-line arms unchanged from the first pass's witness.
- **C2 (129-B, run afterwards by a separate task, 10-14g repeated).** Its criterion is unchanged: 54/54 cells, 0 differing from the four reference rounds including `round-20261014T022210Z`, 0 toasts, every toolbar `collapsed`, red control red. **Added before the run:** in each browser, every `定位游標` latency record of a succeeded click is **< 100 ms** and their median is **≤ 40 ms** (v67's round: Chrome 26.1–31.7, median 27.95; Firefox 27.8–32.0, median 29.15; the red candidate: 253.4–268.3). The analyzer's key-to-move clauses (moving keys < 200 ms, non-moving < 400 ms) pass as they did on v67.
- You run C1. You do **not** run C2; report when the bytes are ready for it.

## Limits

- The only `make` allowed is `e2-c-assets`. No link, no freeze (the main session freezes v68 after C2), no host, no packaging, no `--write` anywhere.
- Do not edit `web/`, `editor-shell/`, `sdk/`, `src/`, the `Makefile`, `dist/profiles/*`, or any check or judge. If the right fix needs one of them, stop and report.
- Before each browser run: the KWallet `Locked` property is not `b true`; record `pgrep -c chrome`; `pgrep -af "probe_|check_m3|run_e2_c|run_merge|run_v20"` shows nothing of ours. One browser job at a time.
- §34.4: this is a product change. If you change a probe or a check, it needs a committed witness and you report it as "repaired because of execution".
- Commit only your own paths (`git commit -- <paths>`). Commit messages in zh-TW or English as in this repo's recent history, ending with your model's `Co-Authored-By` line; never a `Claude-Session` line. Do not push.
- Final reply: a `## SUMMARY` of at most 25 lines: the design in two sentences, what you confirmed or refuted of the two defects above, test counts (red then green), C1's numbers, the session and client sha256 now in `dist/`, and anything you recommend for the next link batch.
