# Adversarial review of `specs/SPEC-M3-page-honesty.md` (opus, read-only), 2026-09-29

Target: the spec at commit `6b77bf1a`, before any implementation, runner or browser run. The
reviewer read the page, both shell layers, the host, the lock spec and runner; it edited nothing.
Its SUMMARY is kept verbatim; DETAILS are condensed to the evidence each item rests on. The
disposition table at the end is the main session's, written after reading the cited source for
items 1–4 (verified: `e2-editor-app.js:900-905` awaits `renderDocument()` before returning to
`saveOnce`; the host's `beforeunload` is registered at IIFE time and the page is imported later
in `run()` at `litecore-editor.js:470`; v8's `editorContract` has no paragraph-text key and
`#a11y-para` then holds the constant `profile` sentence, `e2-editor-app.js:161,174`; the K9/K10
predicates at `check_m3_locks.py:869-889` and the wire-order exemption at `:731`).

## SUMMARY (verbatim)

1. [BLOCKING] U's definition leaves a gap where nobody asks: `save()` finalize clears `dirty`, then `run()` awaits `renderDocument()` before `HOST.save()` is ever called — in that window nothing is dirty, nothing is "handed", and the host guard is idle. Same in download mode. The wrong fix "ask iff `snapshot.dirty`" passes U0–U6.
2. [BLOCKING] The host's `beforeunload` listener runs before the page's and releases the lock whenever it is not itself guarding; the page's new guard then cancels the leave, so U1/U3's "取消後留在頁面" leaves a page holding no lock (per the host's own comment, the next save goes to a conflict copy). No cell checks this, and §3's host scope does not allow the fix.
3. [BLOCKING] V4 cannot pass on the profile that ships (v8): `#a11y-para` is a constant "profile" sentence there (and "" on a11y profiles). Separately 「定位游標」 matches the failure text 「定位游標 失敗」.
4. [BLOCKING] "K9′/K10′ 期望與原 K9/K10 相同" contradicts the scorer: 4 of K9's predicates and 1 of K10's cannot hold once the file is writable at open; the wire-order exemption and the "sent a LOCK" red cases invert. The runner will be rewritten without a written list of which predicates/red cases change.
5. [BLOCKING] The recorder counts a missing value as "didn't ask", and the spec defines no per-arm key: negative cells (U2/U4/U5/U6b/V6) can be vacuously green, and a stale `true` from U0 in the same tab can make U1 green. U0 is a different arm, so it is not a presence check.
6. [CRITERION] Recorder is listener-order-dependent and misses `returnValue`-only asking; "added last" cannot be guaranteed against a lazily added page listener, and it cannot attribute page vs host. Wrapping the prototype methods with a stack capture fixes all three.
7. [CRITERION] U0 includes an edit: once U lands, the page's own guard satisfies U0 even if the runner's listener never ran. Run U0 on an unedited document, paired per browser per round.
8. [CRITERION] `dirty` only becomes true after the operation and a `getState` round trip succeed; a first edit still in flight (route-C paragraph action, up to the 5 s barrier) can be lost on leave without a question. No cell.
9. [CRITERION] U1 does one leave; a `{once:true}` or self-removing listener passes every U cell. Add K10's leave2 pattern.
10. [CRITERION] U3 is passed by a "revision ≠ last-saved revision" predicate, which is wrong across a Worker rollback (revisions restart — the 099 class). Add a cell across rollback or pin the predicate to `dirty`/content stamp.
11. [CRITERION] "Kept" is not observable by the page: `HOST.save()` rejects with the same codes whether the copy landed or the bytes are stranded, and 0.2.3 adds no signal. Also `tokenOnServer`'s `.text()` can throw → neither copy nor strand. Redefine as "settled" and register the unguarded rejection.
12. [CRITERION] K10′ can no longer attribute the leave dialog to the host's stranded guard (the page may ask too). Require `out.guarded` to increment on leave1 and leave2.
13. [CRITERION] K-held is passed by a keyboard-only time debounce and by a "serialize every repeat, PUT once" coalescer. Add two separate Ctrl+S with an edit between them, count session-level saves, and wait out a quiet period.
14. [CRITERION] K-two does not pin "立刻": "ignore Ctrl+S while a save is in flight" passes if the key arrives after the first save settles. Record host `inFlight>0` or session `pending>0` at dispatch.
15. [CRITERION] Nothing checks §3's "disabled" promise: the session gate keeps V2 green with every control enabled, and `updateGestureAffordance()` re-enables action buttons on every state update — the likely bug.
16. [CRITERION] V2 selector `button[data-action]` is a hand filter: `#clear-format` mutates and has no `data-action`. Not form two.
17. [CRITERION] V2 silently exempts items that don't advance in the writable control (Ctrl+V/Ctrl+X via CDP, insert-text with empty `#text`, undo/redo ordering). Require each to advance, or list by name as not exercised.
18. [CRITERION] V2 measures revision (a proxy). Compare content.xml from a runner-invoked `session.save()` at census start vs end.
19. [CRITERION] "沒有 `失敗` 以外的錯誤狀態" names no observable (pill? toast? per-keystroke 「輸入未送出」?) — decided by whoever runs it (§2).
20. [CRITERION] V3 tests the source-tree file, not the packaged bytes (bind sha256s); also assert no state/pending change on refusal and that view-only survives `restart()`.
21. [CRITERION] Regression "只更新綁定（PAGE_SHA256、HOST_COMMIT 等）" is an open list: enumerate the constants per runner and require the runner diff to touch only them.
22. [CRITERION] "在 shakedown 找出來" relies on a future judgement: Firefox classic auto-accepts `beforeunload` and Chrome shows no dialog without activation, so "卡" only surfaces in Chrome-with-activation. Use a static census.
23. [NOTE] V2 cell mixes a hard pass line with the hand-enumerated keyboard half; state that only the button half gates.
24. [NOTE] Download mode: switching `#fixture`/`#open-file` discards unsaved edits without asking (same class as 107); not in §5.
25. [NOTE] `placeCaret` → `document.click` is `mutation:false`, but LOK clicks can change content (checkbox content controls) — inference, not measured.
26. [NOTE] Checked and fine: §2's citations, no page path bypasses the queue, all input paths are `mutation:true`, the 084 state-update wrapper keeps `dirty`, the product-path mutation harness refuses unmatched patterns, existing runners' Ctrl+S is `repeat:false`, bfcache is not a factor, the spec states a never-done default, and K9′'s "403 or stop" rule is sound.

## DETAILS (condensed)

1. `editor-shell/editor-session.js:565-577` (finalize `dirty:false`, then resolve :312-314); `web/e2-editor-app.js:1052` → `run()` :904-905 `await renderDocument()`; `HOST.save` only at :1059; host `inFlight++` at `litecore-editor.js:337`, guard `stranded || inFlight > 0` at :234. Proposed cell: a MutationObserver on `#s-latency` that navigates when 「儲存 N ms」 appears while `out.saves.length` is unchanged.
2. Host `addEventListener('beforeunload')` at IIFE time (:232) vs page import in `run()` (:470); `release('beforeunload')` (:241) sends UNLOCK and nulls the token; :242-250 "the next save goes to a copy", `lostBy: 'stayed-after-beforeunload'`. "Skip release if `defaultPrevented`" regresses finding 105 in Firefox (auto-accept, then only the pagehide UNLOCK).
3. `e2-editor-app.js:1598` loads `profiles/e2-editor-v8`; v8 manifest has no `caretParagraphText`/`documentOutline`; `projectFocusedParagraph` → `reason = "profile"` (:174) → constant sentence (:161). `run()` writes `${label} 失敗` (:908). Proposed: `#s-latency` matches `/^定位游標 \d+ ms$/` and `/^下移一行 \d+ ms$/`, caret y strictly increases, `ready`.
4. `check_m3_locks.py:870-872` (no LOCK sent), :873 (「唯讀」 notice at open), :875 and :885 (`attempts == [(403, False)]`), :731 (wire-order exemption by arm name), :1009-1010 (red cases "sent a LOCK"). Proposed additions: lock `held` at revoke; the PUT carried the token; red case "revoke not applied (share perms still 3)"; keep "403 else stop" per run (a permission change that moves the ETag would give 412 → a copy by another path).
5. Recorder must always write `{nonce, prevented, returnValue, at}`; negatives require presence with `prevented:false`; per-arm nonce. The editor route is COOP same-origin (`EditorController.php:164`) and Files is not — a browsing-context-group switch; per HTML, sessionStorage is keyed to the top-level traversable and should survive (unmeasured).
6. Firefox prompts on `DefaultPrevented() || !returnValue.IsEmpty()`; Chrome also on non-empty `returnValue`. Proposal: wrap `Event.prototype.preventDefault` and the `BeforeUnloadEvent.prototype.returnValue` setter for `type==='beforeunload'`, recording `new Error().stack` (attributes `litecore-editor.js` vs `e2-editor-app.js`).
8. `_drain` awaits the operation and `getState` (:299-302) before `dirty: … || item.mutation` (:309); the error path never sets dirty.
10. "Document revisions restart at zero with every Worker" (`editor-session.js:118-122`); `restart()` sets `dirty: useCheckpoint` (:193).
11. Copy landed: `unstrand('copy'); throw failure(code, …)` (:453-454); copy failed: `strand(…); throw failure(code, …)` (:456-457); `tokenOnServer` `.text()` at :138 outside any try.
13–14. Wrong fixes: a 1 s keyboard debounce; "session.save() per request, PUT only the last". Additions: two `repeat:false` Ctrl+S < 300 ms apart with a text commit between → 2 PUTs, second contains the marker; ≥ 5 s quiet period; record queue state at dispatch. `dispatchEvent`'s return value does catch an early `return` before `preventDefault` (checked).
15–16. `updateGestureAffordance()` sets `button.disabled = !offered` for every `EDITOR_V2_ACTIONS` button on each state update (`e2-editor-app.js:621-629`); `<button id="clear-format">` (`e2-editor.html:277`) calls four `session.action(set-*)` (:1017-1021).
17. CDP Ctrl+V/X needs `commands` or a clipboard; Ctrl+X needs a range; insert-text with empty `#text` only toasts (:1026); undo/redo can never advance in read-only.
18. The drain writes `revision` only for queued operations (:308); `failFormatBarrier` never calls `advanceRevision` (`narrow-editor-v2-session.js:341-345`).
19. `onInputTrace` → 「輸入未送出：…」 toast per refused keystroke (`e2-editor-app.js:1641-1643`).
20. `editor-shell-v2/tests/*.test.mjs` import the tree copy; the product runs the packaged copy; `_openFresh` calls `input.setBlocked(false)` (:190).
22. `SPEC-M3-locks-and-permissions.md:88` records Firefox classic auto-accepting `beforeunload`.
24. `openDocument` calls `session.close()` unchecked (`e2-editor-app.js:1622-1625`); pickers disabled only with a host (:1706).

## Disposition (main session, 2026-09-29, before any implementation)

Written into the spec as §7 (append-only amendment); the cell names below are §7's.

| # | Disposition |
|---|---|
| 1 | Accepted. The condition becomes `dirty || pending > 0 || a save requested and not yet settled` (§7.1); new cell **U-window** enters the window with the proposed MutationObserver. |
| 2 | Accepted; host scope widened. The host becomes the only listener that decides in host mode: 0.2.3 adds `liteCoreHost.watchUnsaved(fn)`, guards on `stranded || inFlight > 0 || fn()`, releases only otherwise, and records each guard's reasons (§7.1). U1 now checks the lock after "stay" and that the next save lands on the original (204). The Firefox cost (a leave after a prompt releases only at `pagehide`, finding 105's unfixed path) is registered in §7.5, not engineered around. |
| 3 | Accepted. V4 rewritten with the proposed latency patterns and `#sink` (which rides the caret) as the caret's y; §1's 「報讀照常」 limited to profiles that offer paragraph text. |
| 4 | Accepted. K9′/K10′ predicates and red cases written out in §7.4 before any runner change. |
| 5 | Accepted. Per-arm nonce; a missing record fails the cell (§7.2). |
| 6 | Accepted. Prototype wrapping with stack attribution is the recorder (§7.2). |
| 7 | Accepted. U0 on an unedited document, gating per browser per round. |
| 8 | Accepted through `pending > 0` in the condition; new cell **U7** (action and navigation in one task). |
| 9 | Accepted. U1 in Chrome leaves twice (leave1, leave2) before saving. |
| 10 | Accepted as a design constraint (the predicate is `dirty`-based, never revision-based) plus a unit test; no rollback cell this round (registered, §7.5). |
| 11 | Accepted. "Kept" → "settled" (§7.1); the `tokenOnServer` throw is registered as a host gap, not fixed (a fix nobody can walk is 059 again). |
| 12 | Accepted. K10′ requires a guard record with reason `stranded` on leave1 and leave2. |
| 13 | Accepted. K-held counts page-level save completions and waits 5 s quiet; new cell **K-sep**. |
| 14 | Accepted. K-two records `#s-pending` right after dispatch (> 0 required). |
| 15 | Accepted. New cell **V7** (every toolbar control's `disabled` matches the page's own `data-mutates`, after ≥ 1 state update). |
| 16 | Accepted. Census = every `#toolbar button` plus `#text`. |
| 17 | Accepted. Each writable-control item must advance, except a named list with reasons (§7.3). |
| 18 | Not adopted as written: the runner has no handle to `session` (module scope), and adding a debug handle to the product for a test is a product change for the test's sake. Registered as a named limit (§7.5) with why revision suffices here: the gate refuses before enqueue, and content-without-revision paths (`failFormatBarrier`) run only inside mutation operations. |
| 19 | Accepted. Observable: pill `ready` and `#toast` empty or containing 「唯讀」; the page maps `EDITOR_VIEW_ONLY` to one sentence in both toasts. |
| 20 | Accepted. |
| 21 | Accepted. Four constants enumerated (§7.6). |
| 22 | Accepted. A read-only static census of every runner's leave points runs before any shakedown; its result is appended to the spec. |
| 23 | Accepted (§7.3). |
| 24 | Registered in §7.5 (download mode only; the M3 product disables both pickers). |
| 25 | Registered in §7.5 (inference). |
| 26 | Noted. |
