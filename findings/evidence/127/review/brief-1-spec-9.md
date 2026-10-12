# Review brief 1 — adversarial review of SPEC-M3-autosave §9 (the freeze draft), before any implementation

Repository: `/home/jiajun/LibreOffice/study_LiteCore` (read only for you: do not edit, do not commit, do not run browsers or ddev). The spec is `specs/SPEC-M3-autosave.md` (zh-TW); §9 is the draft to freeze. Its inputs: §4.1–§4.2 (measurements; evidence under `findings/evidence/127/m2/`, `127/m3/`, `130/m1/`, `130/m1b/`), §8.1 (fable's earlier research and dispositions), §8.2 (the owner's decisions of 2026-10-12: O1 = B "after a copy, the session saves to that copy", O2 = show 「上次儲存：HH:MM（自動）」, Calc = B), and finding 129's native point-click section in `findings/evidence/129/README.md`.

Product code you may need: the page `wasm_sdk_probe/web/e2-editor-app.js` (`saveDocument` ~1868, `saveOnce`, `run()` ~1704, keydown ~2290, B1 rescue ~1585–1702); the session `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js` (`hasUnsavedEdits` ~630) and `wasm_sdk_probe/editor-shell/editor-session.js` (`save` ~558, `placeCaret` ~394); the input adapter `wasm_sdk_probe/input/input-adapter.js`; the host `~/Projects/Nextcloud_Apps/litecore/js/litecore-editor.js` (0.2.12: `save`, `saveOnce`, `put`, `saveCopy`, lock, leaving). Existing counted runners: `wasm_sdk_probe/tools/check_m3_*.py`. Project rules: `CLAUDE.md` at the repo root (especially §1 forms of a criterion, §2 no criterion quantified over a future judgement, §4 withdraw a claim rather than build machinery to keep it), and the checks-stop rule in `specs/SPEC-M3-paragraph-merge.md` §34 (checks only guard against honest accidents; no new machinery to defend checks; changing a counted check needs a witness report).

## What to attack (in this order)

1. **Each criterion of §9.4, one by one**: construct a concrete implementation that is wrong for the user but makes the criterion pass (a "broken but green" scenario), or say "no defect found" for that criterion. Be concrete: name the code path and the observable.
2. **The premises I state as facts** — check each against the source and say true / false / unverifiable:
   - §9.1: withdrawing B-2 is needed because `check_m3_locks.py` K12, `check_m3_same_second.py` and `check_m3_versions.py` require the lock to be held (same token) after a conflict copy; and 0.2.12 holds the lock until leaving after a copy.
   - §9.3 B-3: keeping the first copy's outcome as a thrown `CONFLICT`/`HOST_SAVE_FAILED` leaves every existing runner's `page_failed_with(..., "CONFLICT", copy_name)` expectation unchanged; and no existing counted runner performs a SECOND save after a conflict copy (so B does not change any counted cell). If you find a runner arm that saves again after a copy, name it.
   - §9.2: the host's GET/PUT does not hold the session queue (input is not blocked during the host segment).
   - The K5, K6, K10′ shapes used by AS-3/AS-4/AS-7 exist in `check_m3_locks.py` as described (K10′ = writable at open, then revoked, copy also fails → stranded).
3. **Interactions the design may have missed**: the 1.1 s spacing and read-back (findings 103/104/108), the page's `savesUnsettled` and `hostSaves` queue, the leaving guard (`watchUnsaved`, finding 107), the B1 rescue at the Worker generation limit, finding 109's reopen after a boundary refusal, the browser-side checkpoint, view-only, the lock refresh after the target switch, a manual save racing an autosave, `visibilitychange` when the page is being unloaded (pagehide/bfcache), Firefox vs Chrome timer behaviour in hidden tabs. For each real problem: what happens to the user, and the smallest change to the spec.
4. **The 129 decision** (§9.1, L-129): keep "click at the visible cursor" and ship a named limit for Down at a wrap-end point, versus alternatives. Attack the reasoning, not just the conclusion.
5. **Anything in §9 that is new machinery** (CLAUDE.md §4, §34) that should be withdrawn instead.

Do not propose more checks of checks. Do not ask for more measurements unless a criterion cannot be judged without one; if so, name it.

## Output

Write your review to `findings/evidence/127/review/review-1-spec-9.md` (English). Start with `## SUMMARY` (≤ 30 lines): numbered findings, each tagged BLOCKING (the spec must change before freezing) / SHOULD / NOTE, each with the smallest spec change you propose; then the per-criterion "no defect found" list. Then details with file:line references.
