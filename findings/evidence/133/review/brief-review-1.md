# Adversarial review 1 — the finding-133 SDK fix and its unit tests (SPEC-M3-autosave §9.20 step 4)

Repository `/home/jiajun/LibreOffice/study_LiteCore`. Read-only except the one output file. Do not run browsers or touch the ddev host. You may run `node --test wasm_sdk_probe/sdk/tests/*.test.mjs` and scratch copies of the SDK/tests under `/tmp` to try mutations; do not edit tracked files.

**Scope (only this; §34.3: one review, product change, no check is under review):**
- The diff `git show ec59e609 -- wasm_sdk_probe/sdk/document-sdk.js` (the fix).
- The tests `git show 47840e70 -- wasm_sdk_probe/sdk/tests/document-sdk.test.mjs` (133-U1, 133-U2; U3 is the existing `timeout rejects and emits a best-effort cancel`).
- Red/green outputs: `findings/evidence/133/unit/red-on-641843c9.txt`, `green-after-fix.txt`.

**Context to read first:** `findings/133-a-save-in-flight-across-a-page-freeze-is-declared-dead.md`; `findings/evidence/133/ruling/fable-ruling.md` §2 (behaviour) and §6 (= spec §9.20: criteria 133-U/133-B, named limits L-133-band/suspend/hidden-verdict/firefox); `findings/evidence/m3-locks/k8-recoverable-2026-10-12/README.md` (the measured mechanism). The session treats `TIMEOUT` as "engine dead" (`wasm_sdk_probe/editor-shell/editor-session.js:15-22`, `:315-326`); that file is bound by E1-C and is deliberately not changed.

**Attack (find a concrete failure; say file:line and the input that breaks it):**
1. Correctness of the late-deadline logic: timer bookkeeping across re-arms (`entry.timer` replaced; `_cleanupPending`, `_rejectPending` on crash/dispose/restart, `signal` abort during a grace, a reply arriving exactly as the grace timer fires, `_recoverTimedOutClose` and the close path's own timeout), orphan timers, double reject, cancel sent or not sent when it should be.
2. Can the fix hide a genuinely dead or wedged engine in a **visible** page? E.g. a main-thread long task (> 2 s) straddling the deadline, Chrome/Firefox timer throttling of hidden pages (intensive wake-up throttling aligns chained timers to 1 min after 5 min hidden — is the re-arm a chained timer?), repeated extensions with no bound. Which of these are covered by the registered limits (L-133-*) and which are new?
3. Clock: `performance.now()` in a page vs a Worker, during CDP freeze and OS suspend; the `Date.now()` fallback.
4. The tests: do U1/U2 test the claim, or could they pass with a wrong fix (find a mutation of the fix that keeps U1–U3 green)? Are the injected options a seam the page could pass by accident? Is U1's red for the right reason?
5. Anything in the spec text §9.20 that the code does not do, or does differently (e.g. extension details only when extended).

**Output:** write `findings/evidence/133/review/review-1.md`: findings numbered, each BLOCKING / SHOULD / NOTE with file:line, the failing input, and (for mutations) the exact mutation and test result. End with a ≤30-line SUMMARY, which is also your final message. English.
