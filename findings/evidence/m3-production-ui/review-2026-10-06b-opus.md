# Adversarial review (opus), 2026-10-06b — the B1 fix, before any counted run

Reviewed: spec `74cbbfed` (§9), implementation `ec951c41`, host `fa08307`. Read-only; the reviewer ran
the unit suite and mutations in a scratch copy, no browser, ddev or M3 runner. Returned verbatim below
(the SUMMARY and the per-question details as returned). Dispositions are in
`specs/SPEC-M3-production-ui.md` §10.

## SUMMARY (as returned)

I found nothing BLOCKING in the implementation. There is no remaining path that disposes the engine and is then refused, and with a host there is no window where the work is unguarded. Two criterion problems should be fixed before any counted run (items 1 and 2).

NON-BLOCKING
1. **A1-5 can pass on a wrong result.** Mutation P16 sets `limit.state="saved"` before `await saveDocument(...)`. All 130 unit tests stay green, and reading the runner it passes A1-5 too, because the markers are read seconds later. Fix: when `saved` is first seen, require the host's `saves[-1]` to be `settled && outcome==='saved'` in the same read. Also add `hostAfter.lock.state==='held'` after the reload (unmeasured).
2. **Mutation census (reproduced, 130/0 baseline).** A1-4's tests cover exactly what its row lists. But §9.1 claims outside that row have no guard: S1 (no hand-over from `recoverable-error`), P2 (the pending button reloads), P4 (the button is live while saving), P5/P5b (`limitState` swaps pending and lost). All four survive A1-4, and by reading the runner they survive A1-5. The pending route works today (reproduced at unit level) but nothing protects it. `rescueAtGenerationLimit` re-derives `limitState()` instead of calling it; P5 shows the two can drift.
3. **`failed` text is wrong when the host wrote a conflict copy** (host :544-550 `unstrand('copy')`; the download button is hidden, :122). The text sends the user to a 「下載這份內容」 button that does not exist. The copy's name was only in a 4-second toast. The reload is unguarded and opens the original file without the work.
4. **The toast 「按這一鍵之前的修改都還在」 and §9.2's 「零損失」 still overclaim (reproduced at unit level).** The input adapter commits one key at a time (input-adapter.js:397), while Delete/Backspace go straight to the session queue (page :1600-1605). A key typed before the refused Delete can therefore be queued behind it and rejected: the checkpoint held "M", and "2" was lost. The same applies to the rescued bytes at the ceiling. How often this happens is unmeasured.
5. **`limit` is per page load, not per session** (:1077; `openDocument` at :1895-1900 never resets it). In the standalone page, a second document that reaches the ceiling is not rescued, and the notice says `saved` (reproduced at compile level). In host mode the pickers are disabled (:1990-1992), so the product cannot reach this.
6. **Without a host, `saved` only means `anchor.click()` returned** (:1320-1328). If the download is cancelled or blocked, the work is lost: the reload is unguarded and there is no retry (save is refused and the button reloads).
7. **At the ceiling an older checkpoint is reported `lost` and never offered** (reproduced). Below the ceiling, 「回到檢查點」 would reopen it. At the same moment `data-rescue="checkpoint"` sits beside `data-limit="lost"` (:631 vs :653).
8. **`clean` says 「沒有尚未儲存的修改」 even when the last ordinary save went to a copy or was stranded.** The session marks itself clean when the bytes are produced (editor-session.js:565-583). The host still guards the stranded case, but its bar contradicts the notice.
9. **The item-3 and item-6 comments contradict each other.** If the disabled sink loses focus (:1044-1046), the item-6 guard (:1636) is unreachable in stopped states, and Ctrl+S falls through to the browser's Save Page As. That happens exactly where the notice says 「存回」. The comment "the key is still TAKEN" (:1632-1635) is then false. Neither comment is measured.
10. **`el.sink.focus()` (:1047) has no `preventScroll`, unlike :1361 and :1492.** It likely jumps the view to the document start (finding 069's class). It also runs only after `renderDocument`, so keys typed between `ready` and the focus go to the body. Unverified; it may also make the B3x arm flaky, since `keyed()` waits only 0.5 s of `ready`.
11. **The A1-5 red case is confounded.** On page d41ae604, 「伺服器沒有 M3」 is overdetermined: there is no rescue, no save is pressed, and focus is not restored, so M2 and M3 are never typed. Only `recoverable-error` plus `WORKER_GENERATION_LIMIT` discriminates B1, but `--expect-red` (:703) accepts a red for any reason. The spec's 「out.guards 沒多一筆」 cannot be read after a reload; the runner uses the localStorage recorder instead, and the spec should say so in an appended note.
12. **Wording:**
    - Pending and no-host states say 存回 but download.
    - At the ceiling the rollback toast still says 「請回到檢查點」 (:1136), and no such button exists there.
    - In `rescueAtGenerationLimit`'s catch, the comment "run() has already said why" is false for `RESCUE_UNAVAILABLE`; that path is unreachable today.

## Method and evidence labels (as returned)

- Reviewed `ec951c41` and `74cbbfed`, and host `fa08307`. `tools/check_m3_production_ui.py` was modified in the working tree at the time (the main session's work in progress); the reviewer read what was on disk and did not run it.
- In-tree run: `node --test editor-shell-v2/tests/*.test.mjs` gave 130/0.
- Scratch copy of the modules with its own 130/0 baseline; a mutation harness and reproductions (real session class plus page functions compiled from source) in the session scratchpad (not kept).
- No tracked file was changed, and no browser, ddev or `check_m3_*`/`probe_m3_*` runner was started.
- The three red cases the commit claims reproduce exactly: R1 (page check removed) 4 red, R2 (not marked clean) 2 red, R3 (no state check) 1 red.

## Q1. restart/rollback at the ceiling (as returned)

Read from source. The only call sites in the page or its HTML: `session.restart()` in `reopenAfterBoundaryRefusal`, guarded synchronously by the `restart-required` check, `restartAvailable()` (goes to the rescue at the ceiling) and `restartKeepsContent()`, with no await between the checks and the call; concurrent calls from rejected queued items are cut off by `restart()` moving to `loading` synchronously (editor-session.js:591). `session.rollback()` (which is `restart()`) in the `#notice-action` handler, guarded at the ceiling: `pending` triggers the rescue; every other state calls `location.reload()`. There is no other route to `_openFresh`, and the host never calls restart. Ceiling entries that do not come from a refusal (a restart whose `engine.open` fails at generation 3, or a crash at generation 3) land in `recoverable-error` with the limit notice, and neither calls restart. Reproduced (unit): no dispose at the third refusal; the click handler had no unit test (P1 survived), though A1-5 would catch P1 by reading the runner.

## Q2. takeContentForRescue and the host (as returned)

Bytes: the same checkpoint-or-authority choice as `_openFresh`, gated on `restartKeepsContent()` and a stopped state; reproduced that the third refusal hands out its checkpoint and a second call returns the same content as authority. The bytes equal the engine's content at the refusal, not every key pressed before it (item 4). Host, read from source: `save()` increments `inFlight` synchronously; an unexpected throw strands exactly those bytes; a refused PUT goes to `saveCopy`; if the copy also fails the bytes are stranded and leaving is guarded with reason `stranded`; if the copy succeeds nothing is stranded and leaving is not guarded (correct for the data; the page's `failed` text was wrong, item 3). Window: `savesUnsettled` is incremented before `take()` marks the session clean; between the end of `take()` and `HOST.save`'s `inFlight++` there are only microtasks; `settle` runs after the host has saved, copied or stranded. With a host, no moment where `hasUnsavedWork()` is false while the bytes are nowhere; without a host there is (item 6).

## Q3. Notice and limit rendering (as returned)

No TDZ: `LIMIT_TEXT`, `limit` and `takeSavedContent` are module-level consts reached only after the module has evaluated; `limitState()` returns only keys present in `LIMIT_TEXT`. The `pending` frame computed inside `_blockQueue` is never painted. What a user sees on the boundary route with a host: about 0.94 s of `busy`; a red toast plus the notice at `saving` with a disabled button (the pill says 「需要重新開啟」, which does not match the notice); 「已存回…」 then `saved` with 「重新整理頁面」; an unguarded reload with the caret at the document start. The pending route (generation 3, an edit, a move checkpoint, `WORKER_CRASHED`) reproduced at unit level ends in `saved`, unguarded by any test. Reload guarding by state: `saved` no (correct); `failed` stranded yes; `failed` copy no (text wrong); `lost` yes (dirty); `clean` only through `inFlight` or a stranded copy (text may be wrong, item 8); `saving`/`pending` yes. Unguarded where it should be guarded: the no-host `saved` after a cancelled download (item 6).

## Q4. Mutation census (as returned)

Baseline 130/0. Red: S4 (`<=` in `restartAvailable`) 5; P12 (focus deferred) 1; R1/R2/R3 4/2/1. Survive A1-4 and, by reading the runner, A1-5: S1 (`recoverable-error` dropped from the hand-over), P2 (pending reloads), P4 (button live while saving), P5/P5b (pending↔lost in `limitState`), P16 (`saved` before the write lands). Survive A1-4, A1-5 catches: P1 (handler guard removed), P3 (limit block off), P14 (final repaint dropped), P15 (`saveOnce` ignores `take`). No criterion by design or equivalent: P10/P11 (items 2 and 6 reverted), P13, S2 (`busy` allowed), S6 (checkpoint not cleared). Why they survive: the page harness stubs `saveDocument`, `updateState` and `run`; the click handler is anonymous; `limitState()`'s computed branch was never read in tests. Cheap closures: a named click handler with each state tested; a test for the hand-over from `recoverable-error`; asserting `limitState()` before any rescue; `rescueAtGenerationLimit` calling `limitState()`.

## Q5. Items 2, 3 and 6 (as returned)

Item 2 (reproduced, unit, 20 ms engine): FIFO holds in the session queue but not in key-press order; the adapter queue holds later keys while one commit is in flight, and Delete bypasses it. Item 3 (read from source): focus is restored only after `run()` has awaited `renderDocument()`; without `preventScroll` the view probably scrolls to the sink. Adjacent hypothesis, pre-existing from A1: if an IME composition starts during the ~1 s checkpoint, disabling the sink can leave committed text in `#sink.value`, which `cancelComposition` does not clear, and every later composition would fail with `INPUT_COMPOSITION_MISMATCH` (finding 050's shape); clearing `el.sink.value` on restart would remove the risk. Unverified. Item 6 (read from source): see item 9; no regression for ready/busy.

## Q6. A1-5 (as returned)

Measurable and non-vacuous for the happy path (generations, `restart-required`, markers absent before and present after, the recorder's `fired` entry, the reload fetched the rescued sha). It can pass on a wrong result (P16, item 1) and has no lock check after the reload. Scope: only the boundary route's `saved` state and only slow typing, so it cannot see items 2, 3, 4, 7 or 8. Prediction 1–3 s from key to `saved` is plausible (0.94 s checkpoint, no spacing wait for a first PUT, one GET and one PUT of about 570 KB); not measured. Red case confounded (item 11).
