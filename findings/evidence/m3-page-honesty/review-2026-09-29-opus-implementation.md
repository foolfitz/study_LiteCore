# Adversarial review of the page-honesty implementation and runners (opus, read-only), 2026-09-29

Scope given to the reviewer: page `f42e0227…` / session `747eea71…` / host
`c740d2f` (0.2.3) / runners at `1dc85602`; spec `specs/SPEC-M3-page-honesty.md`
§4 + §7. The reviewer ran nothing but the v2 session unit suite in a scratch
copy. The orchestrator verified every item it acts on against the source
before acting (subagent diagnoses are hypotheses until the source is read).

The review text follows verbatim, then the disposition table.

---

## SUMMARY (reviewer)

Scope: page f42e0227 / session 747eea71 / host c740d2f / runners at 1dc85602 (honesty runner in the tree is 67aff468, which is the one that produced shakedown 095133). All read-only. The only thing I executed was the v2 session unit suite, in a scratch copy: 42/42 pass, plus one mutant (item S4).

Counts: 2 BLOCKING, 4 SHOULD, 11 NOTE.
- BLOCKING 1: Host (pre-existing since 0.2.0) calls `tokenOnServer(token)` after a 412, but a refresh that finishes during the PUT can set `token` to null first. The call then throws a TypeError, so the save rejects with no copy and no stranded state. The page counts the save as settled and the session is already clean, so leaving is never asked about. This is a real data-loss path and a counterexample to §7.1's premise that "every rejection is a copy or stranded".
- BLOCKING 2: U3's "a revision-comparison mutation must go red" is only enforced on the session's `hasUnsavedEdits()`. The page's own `hasUnsavedWork()` has no test. If the page switched to a revision comparison, every U cell and all unit tests would stay green (no cell crosses a Worker restart). That is the 099 class of data loss, and it would still be declared PAGE HONEST.
- SHOULD: V7 never checks the moves by name ("move-character-left/right 可按"). V2's writable control checks `data-mutates` in one direction only. K-sep's marker cannot discriminate because save #1 already contains it. V3 misses a gate mutant that blocks non-mutations called with default options (I ran it: 42/42 pass).
- NOTE: U7's `pending>0` and K-two's `secondAt` are true by construction. The recorder misses the `onbeforeunload` return-value channel. Several red cases use a substring that is too broad or target a shape the product cannot produce, and several clauses have no red case. The V2 keyboard half measures the adapter's Enter path (finding 067), not the page's. Some clauses pass vacuously when a field is missing. §7.8 condition 10 and the K9′/K10′ shakedown are still outstanding.
- D: K2 (§7.8 conditions 2–6) and K9′/K10′ (§7.4) match the spec line by line. Every premise is read back per run, and a 412 or a missed cut goes red (it can never go green), so I found no path where the premise silently fails. Both are unexercised: there is no m3-assets shakedown after 1dc85602, and K9′/K10′ have had no shakedown ("未 shakedown").

## A. Implementation (reviewer)

[BLOCKING] ~/Projects/Nextcloud_Apps/litecore/js/litecore-editor.js:451-452 with :139-147, :191-209
- Sequence: (1) A save's `put()` records `withToken: true` and sends the PUT with `If: (token)`. (2) While that PUT is in flight, the 60 s `refreshLock()` gets a LOST status (the lock was removed externally, e.g. from Files) and `loseLock()` sets `token = null`. (3) The PUT returns 412, so `saveOnce` calls `tokenOnServer(token)` with null. (4) The PROPFIND succeeds, then `held.replace` throws a TypeError. (5) `saveOnce` throws before both `saveCopy` and `strand`, so `host.save` rejects. (6) On the page, `.finally(settle)` brings `savesUnsettled` to 0. `session.save()` already cleared `dirty`. (7) On leave, the host has `stranded` null, `inFlight` 0 and the page answers false, so it releases the lock without asking. The edits are gone.
- Window: roughly the PUT's round trip (about 100 ms) per 60 s refresh, and only after the lock has died. Read from source, not measured.
- This is a sibling of the §7.5 `.text()` throw, but reachable, so the "走不到的修法不寫" reasoning does not apply.
- Fixes that would close it: guard `if (!token)` before the call, or a catch-all in `saveOnce` that strands the bytes. A unit-level red case would be a stubbed host whose `token` is nulled between the PUT and the 412 branch.

[NOTE] wasm_sdk_probe/web/e2-editor-app.js:80-82, :98-99
- `session?.hasUnsavedEdits?.() ?? false` fails open. If the page and shell are out of step, the fix for 107 is disabled with no signal, whereas the host treats a *throw* as "yes" (`page-error`).
- The fallback branch (host without `watchUnsaved`) does not write the "在宿主紀錄旁記下" note that §7.1 requires.

[NOTE] e2-editor-app.js:1194-1204 (scope)
- A keyboard user who tabs to 「儲存 ODT」 and holds Enter gets one click per key repeat, i.e. N chained saves. That is 106 again through the button, which K does not cover.

View-only: no mutation path that bypasses `_enqueue` was found, and I agree with the earlier review's item 26. Paste, cut (copy happens, then delete is refused), undo/redo, Enter and IME all reach the gate. The only unknown is the LOK click (already registered).

## B. Runner census (reviewer)

[BLOCKING] specs §7.3 U3 / editor-shell-v2/tests/narrow-editor-v2-session.test.mjs:979; e2-editor-app.js:80
- The only guard against "uses revision" sits on the session layer.
- Mutation that passes everything: `hasUnsavedWork = () => rev !== savedRev || pending>0 || savesUnsettled>0`. U1, U3, U-window and U7 still ask; U2, U4, U5 and U6b still stay quiet; no unit test reads `e2-editor-app.js`'s predicate (grep confirms).
- To turn it red: a static test in `product-page-calls.test.mjs` asserting that `hasUnsavedWork` reads only `hasUnsavedEdits` and `savesUnsettled`, or a rollback cell.

[SHOULD] tools/check_m3_page_honesty.py:846-850, RED_CASES :1033-1034; e2-editor-app.js:699
- V7 compares `disabled` against `data-mutates`, and both are produced by the same expression. Page regression example: the lookup becomes `button.id`, so the moves (which have no id) get `actionMutates("")` → true, `data-mutates="1"` and disabled. V7 stays consistent; V3: the session is untouched; V4 uses the keyboard path; V2 read-only removes `disabled` before clicking. So everything is green while the moves are unclickable. The "moves stay usable" red case flips only `disabled`, a shape the product cannot produce.
- To turn it red: assert `mutates=="0"` and `disabled==False` for `move-character-left/right` by name.

[SHOULD] check_m3_page_honesty.py:831-835 (V2 writable)
- The exemption `mutates != "1"` is never checked in the other direction. A mutating control mislabelled `"0"` is exempt in the writable arm, enabled in view-only (V7 consistent) and refused by the gate (V2 read-only green).
- To turn it red: require every control whose revision advanced in Vrw to carry `mutates=="1"`.

[SHOULD] check_m3_page_honesty.py:127-134, :794-796 (K-sep)
- Key 1 queues `saveOnce` as a microtask (e2-editor-app.js:1126). The marker's `commitText` is enqueued synchronously in the same script, so save #1's `session.save()` queues after the marker. Both saves therefore contain "LC2", and "the last bytes contain the marker" holds even if save #2 re-sent stale bytes. The host records no text per save, so the evidence cannot confirm this. Read from source.
- To turn it red: yield one task between key 1 and the insert, then also require the two saves' `sha256` to differ.

[SHOULD] editor-shell-v2/narrow-editor-v2-session.js:489 vs tests :907-950 (V3)
- Mutant: `options?.mutation !== false`, verified in scratch at 42/42 pass. It refuses every default-option `_enqueue` in view-only: `placeCaret`, `selectRange`, `copySelection`, `save`. V4 catches `placeCaret` in the browser; nothing catches drag-select or copy.
- To turn it red: add `session.placeCaret`/`selectRange` under view-only to the "moves still run" test.

Criteria where I found no uncaught mutation: U1, U-window, U2, U4, U5, U6a/b, K-held, V1, V5, V6. Caveat for U2, U4, U-window and K*: they never check that `edit()` landed (`check_m3_locks.edited()` exists but is unused). A failed edit makes these cells vacuous rather than red. U1 and U3 would go red in that case.

§7.4 K9′/K10′: none found. §7.8 K2: none found that affects the premise. Condition (b) ignores page-stack asks and accepts `guards: None`; neither matters for K2-5.

## C. Red cases (reviewer)

- [NOTE] U7: in a freshly opened document, with click and navigation in the same task, `dirty` is necessarily false and `pending` necessarily ≥1 whenever the click reached the queue. So the §7.10 addition cannot discriminate.
- [NOTE] K-two: `secondAt` is taken *before* the second press, in the same script, so `< respondedAt` is always true. Neither K-two nor K-sep puts press #2 while save #1 is in flight (the spec review's item 14). A debounce keyed on host `inFlight` passes all K cells.
- [NOTE] Substrings too broad: "V7" (:1031-1035); "copy" (:1002); check_m3_assets "K2 instrument" is shared by three clauses; check_m3_locks.py:1126 counts *any* problem as red.
- [NOTE] V2 census `missing` (:827-830) cannot fire, because the names come from the same `controls` list and `census_step` never skips. Its red case edits a shape the runner never produces. Dedup by key also hides a duplicate button.
- [NOTE] Clauses with no red case: Chrome dialog in `asked_by` (U1, U3, U7, U-window, U6a) and in `not_asked`; U-window missing `page`; V2 read-only `pending`; V5 `ctrlS` prevented; K-sep `first`/`second`; K-held never settled; `opened_ready`; V3 has no dedicated mutant for "state/pending unchanged" or "restart keeps view-only".

## Other runner notes (reviewer)

- [NOTE] :70-104 The recorder misses `window.onbeforeunload = () => "x"`: its return value asks without calling `preventDefault` or the `returnValue` setter. In Firefox the negative cells are blind to that channel.
- [NOTE] :535-551 The V2 keyboard half omits typing, Delete, Ctrl+X, Ctrl+I/U and IME, which §4 lists. Its "Enter" is `beforeinput` into the adapter's `commitText("\n")`, the finding-067 path, not the page's keydown Enter.
- [NOTE] Vacuous when a field is missing: V1 accepts `afterOpen.lock is None`; V7 `textField={}` passes `all()`; V5 host saves pass when the host record is unreadable; V4 never scores pill `ready`; U1 in Firefox leaves `pathAfter` unscored.
- [NOTE] Bindings: the host is bound by the version string only; `SESSION_SHA256` excludes `editor-session.js`, `input-adapter.js` and the client; "served" is the MANIFEST's claim; e2-editor.html (finding 094) is unbound.
- [NOTE] Outstanding: §7.8 condition 10; K9′/K10′ shakedown; UNVERIFIED risk: K2's second-open smoke sets a heading on a last paragraph that is already a heading.

---

## Disposition (orchestrator, after reading the source for each)

| Item | Verified? | Disposition |
|---|---|---|
| A BLOCKING 1 (host `tokenOnServer(null)`) | **Confirmed by source**: `save()` has `try/finally`, no `catch`; `loseLock()` sets `token = null`; `put()` records `withToken` at send time. | Measure first: `probe_m3_save_throw.py` holds the PUT (CDP Fetch), deletes the lock row, lets the refresh lose the lock, releases the PUT. Then host 0.2.4: ask about the token that was sent (`sentToken`), and any unexpected throw strands the bytes (every save ends saved / copy / stranded by construction; also closes the §7.5 `.text()` item). Result and finding number: see spec §7.11. |
| B BLOCKING 2 (page predicate untested) | **Confirmed** (`e2-editor-app.js:80-82`; no test reads it). | Page predicate fail-closed (`session ? session.hasUnsavedEdits() : false`); new `editor-shell-v2/tests/page-unsaved-work.test.mjs` compiles the page's function with only `session` and `savesUnsettled` in scope. Four page mutants (revision > 0; revision vs a saved revision — the review's example; the optional call; unsettled saves dropped) all red: `unit-red-cases/2026-09-29-page-red-cases.json`. |
| A NOTE fail-open optional call | Confirmed. | Fixed with BLOCKING 2; the optional-chain call had also escaped `product-page-calls.test.mjs` (its pattern matches `session.x(` only). |
| A NOTE fallback branch not noted | Confirmed (§7.1 non-conformance). | Page sets `data-litecore-page-guard="own"` when a host lacks `watchUnsaved`. |
| A NOTE held Enter on the save button | Not measured. | Registered, not fixed: a click from a repeating Enter carries no `repeat` flag, and telling it from quick distinct presses would be the debounce K-sep/K-two forbid. |
| SHOULD V7 moves by name | Confirmed. | Runner checks `move-character-left/right` by name (`mutates=="0"`, `disabled==False`); two red cases in the product's shape. |
| SHOULD V2 writable other direction | Confirmed. | Runner: a control whose revision advanced must be labelled `mutates=="1"`; red case. |
| SHOULD K-sep | Confirmed by source (`run()` calls the operation synchronously; the first save's `saveOnce` is a microtask). | Presses in two evaluates (a task between); save #1 read back from the file's Nextcloud versions must NOT carry the marker; the server's bytes must be save #2's; red cases. |
| SHOULD V3 gate mutant | **Reproduced**: 42/42 with `mutation !== false`. | Unit test adds `selectRange` and `copySelection` under view-only (the fixture engine has no `click`); mutant now red ("select-range would change the document"). |
| NOTE U7 true by construction | Agreed. | Kept as a consistency check; recorded as by construction in the spec, not claimed as a discriminator. |
| NOTE K-two true by construction | Confirmed. | Second press now fires when the page shows 「儲存 N ms」 (save #1's bytes taken, the host's PUT not yet answered); `secondAt < respondedAt` now discriminates; red case for a missing/unprevented press. |
| NOTE broad substrings | Confirmed. | Page-honesty: V7 and U4 substrings narrowed. `check_m3_assets` shared `K2 instrument` prefix and `check_m3_locks` any-problem judging: outside those runners' diff limits this round (§7.6, §7.8) — registered. |
| NOTE V2 `missing` cannot fire | Agreed (the census is built from the same list). | The coverage check stays as the empty-census guard (its empty-census red case is a real shape); registered that it cannot catch a skipped control. |
| NOTE clauses without a red case | Confirmed. | Added: U1 Chrome dialog, U1 Firefox left, U1 edit landed, U2 Chrome dialog, U2 handler property, U3 Chrome dialog, U-window reason, K-held settled, K-held edit landed, K-sep presses/versions/server bytes, K-two press, V2 pending, V5 Ctrl+S, opened. |
| NOTE `onbeforeunload` property channel | Confirmed. | Recorder records `handlerProperty`; `asked_by`/`not_asked` fail on it; red case. |
| NOTE V2 keyboard half | Agreed. | Registered: the keyboard half is a one-time measurement (§7.3), and its "Enter advanced" row is the adapter path of finding 067, not evidence about the page's keydown Enter. |
| NOTE vacuous on missing fields | Confirmed for V1, V7, U1 Firefox. | V1 needs `status 207` and `lock == ""`; V7 needs both text-field flags `True`; U1 Firefox needs the leave to reach `/apps/files`; all with red cases. V5/V4 registered (compensated downstream). |
| B caveat `edited()` unused | Confirmed. | Every arm that edits now requires the edit to land (`EDITS`); red cases. |
| NOTE bindings | Confirmed. | `HOST_COMMIT` added to the runner and required for a counted run. The session's other files are bound by the shell generation freeze (v54); e2-editor.html is finding 094 (known). |
| NOTE outstanding shakedowns | Done after the review started. | `m3-assets/shakedown/2026-09-29T101213+0000.json` (condition 10, both browsers clean, red cases 90/90) and `m3-locks/shakedown/2026-09-29T101313+0000.json` (K9′/K10′: 403 with the token in all four). |
| NOTE UNVERIFIED second-open heading | Measured. | In `101213` the second open's heading on the saved document advanced the revision in both browsers (K2-4 clean). |
