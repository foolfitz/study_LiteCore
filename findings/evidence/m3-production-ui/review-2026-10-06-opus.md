# Adversarial review (opus), 2026-10-06 — SPEC-M3-production-ui, before any counted run

Brief: `handoff/tasks/REVIEW-2026-10-06-production-ui.md`. Reviewed state: study_LiteCore `04bf9346`
(spec with §7, runner after the shakedown fixes), host `fa08307`. The reviewer changed no repo file;
its scratch test `ceiling.test.mjs` (real session class + recovery-notice) lived in the session
scratchpad and is not kept.

Main-session check (B′ rule: a subagent's diagnosis is a hypothesis until the source is read):
**B1 confirmed by reading** — `editor-shell/editor-session.js:81` `maxWorkerGenerations ?? 3`, the page
passes none; `restart()` (:587–594) disposes the runtime before `_openFresh` checks
`_generation >= _maxWorkerGenerations` (:148) and throws `WORKER_GENERATION_LIMIT`. Not yet measured
in a browser.

## SUMMARY (as returned)

BLOCKING
1. **B1. The generation ceiling turns the third boundary refusal in one page load back into 109, and
   this time there is no way out.** `reopenAfterBoundaryRefusal` (web/e2-editor-app.js:1009-1025)
   restarts whenever `restartKeepsContent()` is true and never checks the ceiling. `restart()` disposes
   the live engine (editor-shell/editor-session.js:590-592) before `_openFresh` checks
   `_generation >= 3` (:148). The session ends in `recoverable-error` with `WORKER_GENERATION_LIMIT`
   and `engine === null`. The work exists only in `_checkpointBytes`, save is refused with
   `EDITOR_NOT_READY`, and the notice offers 「回到檢查點」 with the button disabled. Reloading loses
   everything since the last save. recovery-notice.js:35-39 prescribes a download for exactly this
   state, and e2-editor-app.js has none. Reproduced with the real session class. Spec §7 makes these
   refusals routine (Tab, the Shift+Enter break, U+FFFC), and any earlier rollback lowers the count to two.

NON-BLOCKING
2. Keys typed during refusal → checkpoint (0.84 s in shake1) → reload are dropped
   (editor-session.js:342-347, input-adapter.js:286-297), yet the toast says 「尚未儲存的修改都還在」
   (e2-editor-app.js:1022).
3. After the reload nothing refocuses `#sink` (setBlocked disabled it, input-adapter.js:296-297), and
   the caret is at the document start. Typing after the reload is unmeasured.
4. The rescue save has a 5 s budget (`_selectionTimeoutMs`, editor-session.js:478-481). A larger
   document, or a 038-type engine state, falls back to the 109 loss (reported honestly). Not registered.
5. Checkpoint failed while an older checkpoint exists: the notice shows the dispatched-unverified
   sentence (e2-editor-app.js:635), and its 「回到檢查點」 drops the edits made since. The page's
   `restartKeepsContent()===false` branch (:1014-1017) has never been red at any level.
6. Ctrl+Z, Ctrl+Y and Ctrl+S bypass the new guard (e2-editor-app.js:1540, 1550, 1562) and still toast
   `EDITOR_NOT_READY` during the reload. Spec :58 overstates.
7. Q2, Q3 and Q5 found no defect.
8. @scope browser floor: a browser without @scope drops the entire product sheet (#notice, #expired,
   the a11y projection and #sink become visible). Not registered. Confirm on Firefox ESR 140.
9. `scopedStyle` (EditorController.php:196-203) only counts rules that follow `}` or the start of the
   sheet; a nested `@media … { :root {` would be left unrewritten instead of refused.
10. Nothing guards the inside of the container: a `scopedStyle` that skipped `:root` would leave every
    `var(--…)` unresolved and still pass A2-1 and A3-1.
11. A2-1's 18 properties (check_m3_production_ui.py:71-74) are a hand enumeration (CLAUDE.md §1).
12. A3-2 (:442-447): "revision +1" cannot tell Backspace from Delete, or Enter from Shift+Enter; the
    recorded `latency` label would.
13. A3-2's clock (:323-334) now starts ≥1.1 s after the key, so `shown` is 0.0 by construction; a host
    poll of 2500 ms stays green.
14. The A1-2 scorer (:412) never requires `report.doc.marks == 0` (recorded at :574).
15. A2-3 (:457) tests only a file at the root (`dir=/`); a wrong `dir` for a subfolder makes Files
    redirect with `openfile=true` (ViewController.php:153-165, :294), which reopens the editor.
16. A2-3's dirty close: in Firefox the arm measures leaving, not staying (:472-473).
17. Red-first provenance: reports carry no runner sha256, and the runner changed after the prefix run.
    A1-2's marker predicate has never been red independently of the generation check.
18. `counted_bindings` (:492-501) does not bind shell generation v55 or the document sha256 (spec §4).
19. Spec row A1-1 has "—" as its never-done default (CLAUDE.md §2).
20. R prediction: a toolbar `.click()` outside ready/busy is now a silent no-op; e.g. `capture_save` in
    run_e2_c_product_path.py:3926-3936 would wait out its timeout. Name this before counting.
21. The A3 hide list is positional (`.sep:nth-of-type(1/3/5)`), and A3-1 ignores `title` tooltips;
    disabled buttons show 「manifest 沒有為「…」宣告這個動作」 (e2-editor-app.js:682-683).

## Options the reviewer gave for B1

- **A.** Before restarting, check the generation against the ceiling. When the next restart would
  exceed it, hand `session.checkpointBytes()` to `HOST.save()` (the current content when
  `restartKeepsContent()` holds and the document is dirty); without a host, offer a download (as
  recovery-notice.js:35 already prescribes); then tell the user to reload. The check must happen
  before `restart()`, which disposes the engine first.
- **B.** For refusals that leave nothing behind (the deadline refusal with `viewRecoveryRequired=false`,
  and the a11y semantic check), resolve and rethrow outside the drain (the `DISPATCHED_UNVERIFIED`
  pattern) — avoids `restart-required` and saves a generation. Reduces B1's frequency; does not fix it.
- **C.** Scope the claim in the spec ("the first N refusals per page load") and add a three-refusal arm
  with its expected result written down.

Reviewer's recommendation: A, with C's wording. Raising `maxWorkerGenerations` is probably unsafe given
Firefox's worker reclamation (finding 024).

## Details worth keeping (abridged from the report)

- Q1: all four engine refusal sites stop before dispatch (probe_engine.cpp:3392-3399, :3423-3431,
  :3434-3445, :3811-3815); the checkpoint runs while the drain owns the engine; rejection reactions run
  after `restart-required`; the first `restart()` moves to `loading` before its first await, so later
  calls return early. shake1's timeline shows exactly this (checkpoint at 9448 ms, restart-required
  9452, loading 9457, ready gen 2 at 10674). A third mutation (checkpoint after the rethrow, outside
  the drain) also turns a unit test red. Save in flight to the host: no loss. View-only: unreachable.
  Backspace at the document start is itself a deadline refusal (probe_engine.cpp:3423-3431).
- Q2: `restartKeepsContent()` is the same expression over the same four fields as `_openFresh`
  (editor-session.js:163-167); nothing can write them between the check and the reopen.
- Q3: `applySessionAvailability` leaves nothing disabled for good and re-enables nothing wrongly.
- Q4: the regex matches exactly one `:root` and one `body` on the shipped page; inside `@scope` the
  page's rules behave as before (the root itself is no longer matched by `*`, harmless).
- Q5: `linkToRoute` is right with pretty URLs on and off; closing goes through the host's
  `beforeunload` and cannot bypass the guard.
- Red-first: B-del/B-bs/S/P were red for the right reasons on 0.2.5, but 0.2.5 never reopens, so the
  "restart reopens older bytes" half was never exercised there. Suggested: re-score the stored prefix
  JSON with the final scorer and `--expect-red`; add the runner's sha256 to every report.
