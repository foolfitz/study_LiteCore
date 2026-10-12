# Review 2 — the 0.2.13 implementation against SPEC-M3-autosave §9 (frozen), adversarial, read-only

Reviewer: fable (Claude Fable 5.1), 2026-10-12. Brief: `brief-2-implementation.md`. Reviewed: page commits `c335f5cb` and `8c6b831a` (`wasm_sdk_probe/web/e2-editor-app.js`, two unit-test scope lines), host commit `84dc3da` (`js/litecore-editor.js`, `templates/editor.php`). Nothing was run. Line numbers are of the files as they stand after these commits. Tags: BLOCKING = fix before the shell generation is frozen; SHOULD = fix in the same release; NOTE = register.

## SUMMARY

No BLOCKING defect found. The code does what §9.2 / §9.3 say with the deviations listed; every §9.4 criterion is met by construction on the paths the criteria exercise; the pre-registered reds (host_entry `conflict`, locks K8) are the only counted cells this code changes.

1. SHOULD — Host: the version fallback after a successful PUT still asks the ORIGINAL (`litecore-editor.js:568`, `send(config.file.davUrl, { method: 'HEAD' })`). After a target switch a copy PUT whose answer carries no `OC-ETag`/`ETag` would take the original's version as `etag`; the next PUT to the copy is then a 412 and one more copy. Change: `send(saveUrl(), …)`. (The other eight uses of `config.file.davUrl` — lock, refresh, unlock, load, copy folder — are right; see §C.)
2. SHOULD — Page: `moveFromPoint` returns silently when the caret rectangle is not known or the session is not accepting (:2502–2504): the arrow key then does nothing and says nothing, the trap this file's own comments name (Ctrl+A). Change: fall through to `editorAction(action)` so the refusal is at least reported; and set `lastSelectionShape = "collapsed"` after the click resolves, not before (:2507), so a failed click does not leave the toolbar claiming a caret.
3. SHOULD — Page: after a save strands, the 5-minute clock is not reset (`autosaveLanded` is called only for `saved`/`copy`, :1980–1983). Spec-conformant to the letter (§9.2: reset on a file write), but the stranded bytes are banked in the host; an offline user whose first edit is > 5 min old then pays an engine-blocking save and two failing requests at every 3 s pause, until the network returns. Change: one line — reset `firstUnsavedAt` on any outcome that took the bytes (saved, copy, stranded) — with a one-line §9.10 append.
4. NOTE — Spec/code: §9.2 says the engine segment 「照舊走 `run("儲存")`」; the code labels it `自動儲存` (:1918) and the host segment `自動存回` (:1973). Keep the code (it is what lets page_honesty's `^儲存 \d+ ms$` count manual page saves only) and append the correction to §9.10.
5. NOTE — Host: `record.target` is set only on `saved`/`copy` (:574, :601); a stranded record has none. Set it at record creation (:452) to the target the attempt aimed at, so AS-7's judge reads it.
6. NOTE — 128 remedy B: no repaint is lost and nothing sticks. The give-up `return` (:1264–1267) runs `finally` with `retried` false, so `rendering` is cleared and a pending `renderAgain` runs; `busyLeftToAction` is cleared by any full pass (:1255) or by the last action's `finally` (:1877–1881). The branch is not exercised by the two render unit tests (both pin `engineActionsOut = 0`); 128-B is its only measurement.
7. NOTE — 130's toast now fires where it was silent: queue-full during a save (intended); a commit in flight rejected by a boundary refusal's `_blockQueue` (one toast, replaced by the reopen's own toast that follows); a commit in flight across a Worker restart (`STALE_EDITOR_GENERATION`); `input-too-large` on a > 16 KB paste and `blocked` via the clipboard (both were silent drops before). Cancelled queued characters trace `queue-invalidated` only (adapter :300–316) — no toast storm. No counted runner asserts toast text where any of these can fire; the merge judge's `toastsAtEnd` is frozen and outside the 0.2.13 count.
8. NOTE — An autosave whose ENGINE segment fails toasts `自動儲存：<code>：<message>` (:1735–1769, not quiet) — developer text for an event the user did not trigger; §9.2 asks for exactly this (「失敗照舊顯示」). Sibling of L-manual-conflict-toast; register.
9. NOTE — The host's O2 label is its own hidden element (:154–159), production_ui's P inventory runs at open (:523) and `#litecore-host-title` keeps the file name until a copy; no counted runner reads the title after a copy. The pre-registered reds (host_entry `conflict`, K8) are the only counted cells this code changes; K7's margin is unchanged.
10. NOTE — `visibilitychange` on close: the autosave starts `session.save()` and the page is gone before a fetch could leave (L-close holds in the code); a cancelled navigation fires no `visibilitychange`, so nothing double-saves.

No defect found, per area: §9.2 activity, triggers, cap and reset (traced key by key for AS-2c's three clauses), conditions from truth sources, hidden trigger, quiet host segment, 109 reopen (`_openFresh` restores `dirty`); §9.3 B-1 target switch (`withToken = token !== null && target === null`, :519; read-back and PUT to `saveUrl()`, :504/:530; `saveCopy` sets `lastAnswered`, :403; copy notice outranks a later LOST, :131), B-3 texts, `outcome`/`savedAs`/`{ name, target }`/`lockRefused`, re-strand with new bytes, O2 (a)–(e); AS-1…AS-7, O2-1, 128-B (host-segment cell passes by construction: saves never touch `engineActionsOut`), 129-B (toolbar cell via `lastSelectionShape` + `updateGestureAffordance()`, :2507–2509), 130-U; races: manual vs auto (serialised on `hostSaves`, `savesUnsettled` in the conditions), B1 rescue (`limit.state === "saving"`), Worker restart (revision used only for inequality), drag and composition (truth sources).

---

## A. §9.2 — the page, bullet by bullet

| §9.2 says | Code | Verdict |
|---|---|---|
| Only with a host | `armAutosave` returns without `HOST` (:2543); listeners inside `if (HOST)` (:2596–2608) | ✓ |
| Activity: sink `keydown`, composition events, paper `pointerdown`/drag `pointermove`/`pointerup` | :2597–2602 (`keydown` in capture, `pointermove` only while `drag.active`) | ✓ |
| Activity: any completed edit, whichever path | `noteAutosaveState` (:2567–2577): a changed `snapshot.revision` → `noteActivity()`. A format action that is "dispatched, unverified" sets `dirty` without advancing the revision (narrow-editor-v2-session.js:358–362) and is caught by the else-branch only if no timer is running — then the save comes 30 s after the previous activity, slightly early. Harmless. | ✓ (one benign edge) |
| Idle 30 s; cap 5 min → 3 s; reset to 30 s after a file write | `armAutosave` (:2542–2549) computes `capped` from `firstUnsavedAt`; `autosaveLanded` (:2560–2562) called on `saved` and on `outcome === "copy"` (:1980, :1983). Traced for AS-2c: last key T → completion T+0.1 arms 3 s → host `at` ≈ T+3.3–3.5; then `firstUnsavedAt = null`; next key arms 30 s (not yet dirty); completion sets `firstUnsavedAt`, arms 30 s; 10 s quiet → nothing. | ✓; see item 3 for the stranded case |
| Hidden: at once, when there is unsaved content | :2603–2607 (`hasUnsavedEdits()` only; `savesUnsettled` is in the conditions) | ✓ |
| One-shot `setTimeout` | ✓ | ✓ |
| Nothing unsaved → no save, no re-arm | `autosaveNow` :2581 | ✓ |
| Conditions fail → 3 s again if `ready`/`busy`, else wait for activity or `ready` | :2583–2588; the "return to ready" is the else-branch of `noteAutosaveState` (:2574–2576: `ready && timer === null && hasUnsavedEdits`) | ✓ |
| Conditions read from truth sources | `autosaveConditions` (:2522–2535): `session.input.state.composing/queueDepth`, `snapshot.state/pending`, `drag.active || drag.inFlight`, `savesUnsettled`, `limit.state === "saving"`, `viewOnly` | ✓ |
| `saveDocument` auto mode, same queue, `{ trigger: "auto", conditions }` | :1920–1948, :1951–1986; `HOST.save(bytes, { name, trigger, conditions })` | ✓ |
| Engine segment 「照舊走 `run("儲存")`」, failure shown | `run("自動儲存")` (:1918) — label differs (item 4); failure toasted (item 8) | deviation, doc-only |
| Host segment: no toast on success, copy or strand; manual unchanged | `run(…, { quiet: auto })` (:1973–1976; `run` :1763 rethrows before the toast); `if (!auto) toast(…)` (:1984) | ✓ |
| 109 reopen content is `dirty` | `_openFresh` (`editor-session.js:193`); the restart's revision change also re-arms (benign) | ✓ |

Broken-but-green, examined against this code (brief item 2):
- AS-1: the recorded `conditions` are the same object the decision used (`autosaveAllowed(conditions)`, :2583; stored :2591). Nothing to fake.
- AS-2 / AS-2h / AS-2c: traced above; the completion re-arm 50–100 ms after the key keeps the start inside [30, 35].
- AS-3, AS-4(a)(b): the host path is the same code for auto and manual; the only path AS-4 would not see is item 1 (needs a version-less PUT answer).
- AS-4(c): `withToken` false after the switch (:519), `If-Match` = the copy's version (`etag = copy.etag || null`, :599), read-back GET of the copy (:504). The lock on the original is untouched (`refreshLock`/`release` still address `config.file.davUrl`, :274/:306).
- AS-5: the toast text contains 「有字沒有輸入」 (:2820).
- AS-6(b): a thrown `CONFLICT` settles both counters (`turn.then(settle, settle)` :1947; host `finally` :471–475) and `dirty` is already false.
- AS-7: `strand(bytes, record.sha256)` replaces the kept bytes (:612); a network PUT still sets `lastAnswered` (:531) so the first online save does not skip the spacing wait. Item 3 (cap cadence) is invisible to AS-7, whose cadence is set by the runner's idles.
- O2-1: `noteSaved` only on `saved` (:577) and `copy` (:608); `（自動）` from `record.trigger` (:191); hidden until then (:158).
- 128-B: the new host-segment cell passes by construction — `saveDocument`/`saveOnce` never touch `engineActionsOut`, so a typed character's invalidation during `run("存回")` paints at once.
- 129-B: `lastSelectionShape = "collapsed"` + `updateGestureAffordance()` (:2507–2509) → `#toolbar[data-selection-shape]` is `collapsed` after the key. Item 2's silent return is invisible to 129-B (every measured shape has a caret rectangle).
- 130-U: `type` ∈ {commit-rejected, commit-error, composition-rejected} (:2818–2820), the three the adapter writes (adapter :191, :335/:340/:355, :417).

## B. §9.3 — the host, bullet by bullet

| §9.3 says | Code | Verdict |
|---|---|---|
| B-1: no `If` after the switch | `withToken = token !== null && target === null` (:519); `extra.If` only when `withToken` (:528); `sentToken` follows (:529), so the dead-token retry (:549–559) cannot trigger on a copy PUT | ✓ |
| B-1: `If-Match` = the copy's version; read-back unchanged | `etag = copy.etag \|\| null`, `lastSha = record.sha256` (:599–600); `saveUrl()` in the read-back and the PUT (:504, :530) | ✓ (item 1 for the HEAD fallback) |
| B-1: `saveCopy` writes `lastAnswered` | :403, on every attempt | ✓ |
| B-1: original's lock held and refreshed; LOST must not hide the copy notice | lock code untouched; `render()` shows `stranded ? … : (copyNotice \|\| lockNotice)` (:131) | ✓ |
| B-3: bar text with reason, copy name, 「之後的存檔都會存到這份」 | :602 | ✓ |
| B-3: `#litecore-host-title` = copy name; `#s-doc` untouched | :603–605; the host never touches `#s-doc`, the page keeps `documentName` | ✓ |
| B-3: first copy still throws `CONFLICT`/`HOST_SAVE_FAILED` with 「副本檔名」; `outcome`, `savedAs` | :609 (`你的內容另存為「${copy.name}」`, `{ outcome: 'copy', savedAs }`); stranded paths :469, :613–614 (`{ outcome: 'stranded' }`) | ✓ (`page_failed_with` needles unchanged) |
| B-3: success returns `{ name, target }` | :458 (`saveName()`, `record.target`) | ✓ |
| Stranded: retry every time, re-strand with the newest bytes | no pause anywhere; `strand()` replaces (:350–354 → :612) | ✓ |
| `load()` returns `lockRefused` | :435 | ✓ (the page records nothing from it; B-5 is withdrawn) |
| O2: own element, `respondedAt` + `started` in local time, 「（自動）」, file writes only, hidden until then, not live | `#litecore-host-saved` (:154–159, hidden); `noteSaved` (:185–197): `new Date(out.started + answeredAt)`; called with `attempts[last].respondedAt` (:577) and `copy.respondedAt` (:608); no `aria-live` | ✓ |
| Records: `trigger`, `conditions`, `target` | :450–453 (`trigger`, `conditions`), `attempt.target` (:520), `record.target` on saved/copy (:574, :601) | ✓ except item 5 |

## C. Regressions in what the counted runners rely on (brief item 3)

- **New toasts (130)**: see SUMMARY item 7. Where the counted runners read `#toast` — locks/same_second/versions/host_entry `page_failed_with` right after a save with no typing; production_ui records toasts in its TIMELINE and asserts none; page_honesty's view-only arm requires an empty toast or 「唯讀」 and types into a `readOnly` sink (no commit) — none can meet a 130 toast. The product-path net reads `pp.toasts` as a joined string for substring checks (:6462, :8873, :9484); extra toasts cannot break those.
- **Latency labels**: `自動儲存 N ms` / `自動存回 N ms` / `自動存回 失敗`. page_honesty's `COUNT_SAVES` (`^儲存 \d+ ms$`) and assets' `re.fullmatch(r"存回 \d+ ms")` match manual saves only — which is what they count. `startswith("存回")` waits in locks/host_entry/assets follow a manual press with no autosave in flight (the census of review 1 §C.1 stands: no counted arm idles 30 s after an edit except K8 and the K7 margin).
- **O2 label**: hidden at open; production_ui's inventory runs at open (:523) and asserts `#litecore-host-title == NAME` (:691) — unchanged until a copy, which the P arm never makes.
- **`run()` `quiet`**: a third, defaulted parameter; no caller passes it but `saveOnce`; the success path is unchanged.
- **128 give-up**: SUMMARY item 6. Also: during a long B′ merge (`engineActionsOut` 1 for up to ~8 s) every invalidation's repaint now gives up at once instead of spending up to 84 × 120 ms retries, and `run()` repaints when the merge returns — a BUSY paint never produced pixels anyway, so nothing visible is lost. A `placeCaret` click is not an `editorAction`, so the 120 ms retry path is unchanged there.
- **129 click**: `lastSelectionShape` set and the affordance refreshed (:2507–2509); key repeats while a pair is queued go straight to `editorAction` (:2495–2498) and run behind the click in the session FIFO — the engine's gate sees a caret by then. The product-path net presses arrows on a collapsed caret only (:5831, :7973–7976); its cut-on-a-range check reads a substring of all toasts (:6462). Shift+move returns before `preventDefault` (:2478), so the textarea's native Shift+move acts on an empty sink. Item 2 for the two silent returns.
- **Host `target` switch — every remaining `config.file.davUrl` / `config.file.name`**: `lockHolder` :197, `tokenOnServer` :212, `takeLock` :233, `refreshLock` :274, `release` :306 — the lock is the original's: right. `load()` :418, :435 — right. `saveCopy` :389–391 derives the copy's folder and stem from the original — right, and a second conflict on a copy then makes 「X（衝突副本 <stamp>）.odt」, not nested parentheses (B-6's 「疊兩層括號」 does not occur). `download()` :374 names the download after the original — acceptable. `saveOnce` :568 HEAD fallback — **wrong after a switch** (item 1). `until()` at open :634 — right.

## D. Races (brief item 4)

- **Autosave vs manual save**: both go through `saveDocument` → `hostSaves` (:1945–1947); the autosave's conditions refuse while `savesUnsettled > 0` (:2538); a manual press during the autosave's engine segment becomes a second save with identical bytes after the 1.1 s spacing — the shape Ksep already allows.
- **Autosave vs B1 rescue**: refused while `limit.state === "saving"` (:2534); at the ceiling the session is not `ready`, so no 3 s re-check loop (:2586).
- **Autosave vs 109's reopen**: refusal → `restart-required` → conditions fail, no re-arm; reopen → `ready` with `dirty` (`_openFresh`) → `noteAutosaveState` re-arms (revision changed) → the checkpointed content is saved 30 s later. ✓
- **Worker restart, revision from 0**: `autosave.revision` is compared for inequality only (:2569); the 099 class does not apply.
- **`visibilitychange` during unload**: the handler starts `saveDocument` (:2606); `session.save()` takes ≥ 150 ms and the document is torn down first, so no PUT leaves and no lock state is touched (`release` runs at `pagehide` as before). A `beforeunload` dialog that the user cancels fires no `visibilitychange`. L-close holds.
- **Autosave vs a 129 pair, a drag, or a composition**: `pending > 0`, `drag.active || drag.inFlight`, `input.state.composing` each refuse (:2522–2539).

## E. What this review did not verify

- That the engine never answers BUSY to a paint after an action's call has returned (the premise of remedy B's "run() repaints when it returns"); 128's trace says the action returns at ~45 ms and the BUSY was at ~40 ms. If it did, the `finally` repaint (:1880) and then the 120 ms retry path (now with `engineActionsOut` 0) still paint; nothing is lost, only delayed.
- Whether `editorState.caret` is ever absent during a range selection on WASM (item 2's silent return). The native round saw a cursor rectangle in all 12 shapes; 129-B's 42 cells are the measurement.
