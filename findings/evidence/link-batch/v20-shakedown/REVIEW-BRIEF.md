# Review brief: `judge_v20_shakedown.py` before its first counted use (§34.3)

Written 2026-10-14 with the judge. **Not run**: task 10-14e is a shakedown, not a count, and §34.3 asks for the two-seat review before the first **counted** use only. When a counted run of these arms is scheduled, send this brief to two seats (opus and codex, B′ form) and dispose of the findings in an appended section of `README.md` before the count.

## What to review

- `wasm_sdk_probe/tools/judge_v20_shakedown.py` (the rules `judge_p1`, `judge_p2`, `judge_p3`, `judge_c1`, `judge_e2`, `judge_p2c`, the exit rule in `judge_reports`, and `mutations()` / `p2c_red_cases()`), read against `ARMS.md`.
- `wasm_sdk_probe/tools/run_v20_shakedown.py`: the fields the judge reads (`positions[*].expected/text/hidden`, `add/remove.textAt2s/countAt2s/partsAt2s`, `untriggeredRequests`, `clauses` on C1 rounds and E2 refusals, `lokEventsSeen/loneSizeChanges`), and the two independent implementations the runner carries: `span_of`/`status_text`/`region_of` (P1's expectation) and `lok_summary` (P2-c's lone-flush detector).
- `wasm_sdk_probe/tests/test_v20_shakedown_judge.py`.

## Fixed questions (answer each with COUNTEREXAMPLE, NONE, or SHOULD)

1. **Find a broken product that this judge passes.** For each criterion arm, name a product defect in the page number, C, or `caretBefore` whose report would read PASS. Candidates to try: a page that shows the right text but computes it from `documentChangeSequence` (P3 is meant to catch it — does it, given the 2 s trigger window?); a page that reads the rectangles once and never re-reads (P2-a catches it only if the +2 s text is stale — is `countAt2s` read from the engine's reply or from the page?); a `caretBefore` that equals the reference by coincidence (the caret before the key is also the caret after a failed K1 at a true boundary — does any E2 instance distinguish "the caret before the key" from "the caret now"?).
2. **Find a passing product that this judge fails.** In particular: P1's strict `<` at a view edge that coincides with a page edge to the twip; P1 on a browser whose `#paper` height is fractional (the runner converts with `paperHeight`, the page with integer `docRows`); C1's `generationStays1` when the fixture open itself produced a reopen; E2's `sequenceNotAfterReference` when the engine's `caretBefore.sourceSequence` is the P's sequence rather than the cache's.
3. **The non-vacuity rules.** P1 without a rectangles reply, P2 without a press, P3 without a paint or without reaching the bottom, C1 with every round `placement-mismatch`, E2 without a refusal — each reads `NOT_ESTABLISHED`. Find a vacuous run that reads PASS instead.
4. **The two independent implementations.** Is `span_of` the same rule as the page's `pageSpanOf` (whole rectangles, strict overlap on both axes, string order, malformed entries skipped for N/L and counted in M)? If they differ, which one is Writer's? Is `region_of` the same quantity as `visibleRegionTwips(visibleDocRows())` up to the row rounding?
5. **The lone-flush detector.** Is ±25 ms the right window for review 6 Q4's counterexample (the click's acknowledgement arrives 22–28 ms after the click)? Does `NOT_LONE_IDS = (0, 1, 2, 3, 4)` match "no caret, selection or tiles callback beside it"? Should `SET_PART` (14) or `STATE_CHANGED` (8) count as company?
6. **The exit rule.** A criterion arm that ran on the instrumented worker fails; an arm with no rule fails; a missing browser fails. Find a report that should fail the count and does not.
7. **Red-case coverage.** For each rule in the judge, name the red case in `mutations()` that exercises it, or say it has none (the census of the product-path net found 5 of 40 checks with no mutation; do the same here).

## What the reviewers do not need to decide

Whether the arms are the right arms (that is ARMS.md and the spec); whether v20 passed (that is the README); the host arms of §10.7 (a later task).
