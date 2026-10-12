# Disposition of review 1 (opus) — finding 133's SDK fix and 133-U

Review: `review-1.md` (brief `brief-review-1.md`). 0 BLOCKING, 4 SHOULD, 7 NOTE. The main session read the code behind each SHOULD and reproduced every mutation in the review's table that the dispositions rely on (`../unit/mutants-after-review.txt`).

| # | Level | Disposition |
|---|---|---|
| R1-1 | SHOULD | **Adopted.** X3 (production clock and production L; only the grace injected) and X4 (the defaults) committed in `sdk/tests/document-sdk.test.mjs`. Red on M1, M1b, M11 (X3) and M2, M15 (X3/X4). |
| R1-2 | SHOULD | **Adopted.** X1 (late 0 / 1000 / 2000 ms → plain TIMEOUT, no extension keys, the pre-fix message, < 1 s, 1 cancel). Red on M3 (×3), M10 (2000), M19 (1000, 2000). |
| R1-3 | SHOULD | **Adopted.** X2 (a second stop inside the grace → second extension, `extendedMs` adds up). Red on M4, M5, M9. U1/U2 got `{ timeout: 5000 }` (M13 must fail, not hang). |
| R1-4 | SHOULD | **Option A.** Registered as L-133-grace (spec §9.22); the two comments in `sdk/document-sdk.js` reworded to say what the code does (a fixed 10 s grace, not the budget left). Not B (`max(G, timeoutMs)`): G is the ruled value (§9.20); changing it is a ruling, not a review disposition. B is recorded as an option for the post-release spec. Exposure: measured saves 0.16–0.72 s on the owner's document; larger documents unmeasured. |
| R1-5 | NOTE | Registered as L-133-long-task (§9.22): a main-thread task > 2 s in a visible page also extends once; benign (one extra grace before a real TIMEOUT). Measured by the reviewer in Node only. |
| R1-6 | NOTE | Accepted as a correction (§9.22): in a long-hidden Chrome tab the re-arm is a chained timer, so L-133-hidden-verdict is the expected outcome under intensive throttling, not a possibility. From Chrome's published rules; unmeasured. |
| R1-7 | NOTE | Registered as L-133-engine-deadline (§9.22): the engine's own `steady_clock` stage deadlines (`probe_engine.cpp:993`, `:4386-4410`) can still yield `MUTATION_OUTCOME_UNKNOWN` across a stop > 5 s during a format barrier; the SDK fix cannot reach them; fable-ruling §1's "covers editorAction" holds for SDK deadlines only. Read from code, unmeasured. |
| R1-8 | NOTE | Recorded. Same-clock assumption (timer vs `performance.now()`) unverified; suspend stays L-133-suspend. |
| R1-9 | NOTE | Recorded; work item for the post-release spec (an extension that ends in a reply leaves no trace outside the probe; the error carries the grace, not the measured lateness). |
| R1-10 | NOTE | Recorded: no spec↔code divergence; extension details only when extended is consistent with U3; tests/`.d.ts` outside the bundle glob, so v63's one-file condition holds. |
| R1-11 | NOTE | Recorded: M7/M18 equivalent mutants; M6 visible only to an active-timer count; same-turn reply/grace race = L-133-band. |

**Ledger (§34.4).** The added tests strengthen 133-U, the unit criterion of a product change written this session; no runner or reader (the check machinery §34 governs) changed. Main session's reading: 因審核而修 stays **6**, 因執行而修 stays **11**; stated here so it can be disputed. Their evidential value is not that they pass on the fix (the reviewer's scratch copies already did) but that each is red on a named wrong fix.

**After the dispositions:** SDK `e4c3fe92…` (comments only changed since `ec59e609`), tests 31/31 (`../unit/green-after-review.txt`), E1-C intact.
