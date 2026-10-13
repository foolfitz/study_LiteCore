# Review brief — ruling-3 condition 9: one adversarial pass over the two probes' new arms/readers and the judge

You are the one review these get (§34: each reading tool reviewed once). Look for "broken but green" first: a page that still has finding 136, or the restore flash, or B/D broken, for which the judge exits 0. Then look for a correct page the judge would FAIL for a reason unrelated to the fix.

Read:
- `findings/evidence/134/ruling/ruling-3.md` (conditions 3, 4, 9 and addenda 1–3) — the specification.
- `handoff/tasks/TASK-2026-10-13c-136-probes-and-judge.md` — the task as given (note the start-press exception).
- The code: `findings/evidence/132/held-into-refusal/probe_held_into_refusal.py`, `findings/evidence/134/table/probe_table_refusal.py`, `findings/evidence/132/held-into-refusal/judge_held_into_refusal.py`. Diff from `5901681c^` for what changed.
- `findings/evidence/136/judge/` (README and the three red cases) and `findings/evidence/136/baseline-0.2.16/` (the pre-fix run: every arm matched its prediction).
- The page fix under test: `git diff 53db5422 b2b488c0 -- wasm_sdk_probe/web/e2-editor-app.js`.

Questions:
1. Concrete reports or page behaviours for which the judge exits 0 while 136 is unfixed, or the flash remains, or the caret is put back at a wrong offset in the right paragraph. Is each reachable with these probes?
2. The `scrollTop` rule: the window definition (first `restart-required` up to the first 「已重新載入」 toast), the 0.5× threshold, the "pre > 0" precondition, the scroll-event sampling the implementer added. Can the window miss the jump, or close early?
3. The rules beyond the literal ruling text named in `136/judge/README.md`: the untyped-mark-must-count-0 rule and the run-3 fallback. Are they sound? Is the fallback reachable for new reports?
4. Tool-closure over both probes' ARMS and non-vacuity per browser.

Output `findings/evidence/136/review/review-1.md`: BLOCKING / SHOULD / NOTE, each with file:line and the concrete case. Do not edit anything else. Do not run browsers, the probes, or anything touching the ddev host: an acceptance run is in progress on it. Do not commit. Reply with the path and a ≤20-line summary.
