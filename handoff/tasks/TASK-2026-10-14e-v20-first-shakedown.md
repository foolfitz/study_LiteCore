# Task 2026-10-14e: the first v20 shakedown on WASM (RUNBOOK-relink-v20 §4.1)

**State.**
- **Engine:** v20 is linked and archived (`0e7f7f64`, wasm `313b08d5…`, worker `478d0da1…`, `dist/profiles/e2-editor-v20/`; post-link checks in `findings/evidence/link-batch/v20-post-link/`).
- **Shell:** generation v67 is frozen (`ac6267c8`, page `web/e2-editor-app.js` `7815e16c…`). It carries part 2's page number and ruling 6 conditions 45, 47 and 48.
- **Binding:** nothing is bound to v20 yet. This task is a shakedown, not a count.

**Read first.**
- `specs/SPEC-M3-link-batch.md`:
  - §5 and §7 (the arms), as reduced by §13.3 (Shift+Arrow and arrows on a range are OUT of this batch);
  - §10.5 (C and C1), §10.7 (existing arms to re-expect), §10.8 and §12.3 (the page-number mechanism, and P2);
  - §15 (ruling 6, including finding 138 and L-C-number-or-indent).
- `handoff/RUNBOOK-relink-v20.md` §4.
- `findings/evidence/link-batch/review/review-6-engine-code.md` §3 and §4. P2 decides two things: whether a lone `DOCUMENT_SIZE_CHANGED` flush exists on WASM (which would make finding 138 BLOCKING-grade before the count; it is already fixed in v67), and whether lazy layout at load exists.
- `findings/evidence/link-batch/page-rectangles/` (native rounds, `MIXED.md`) and `tools/create_mixed_page_document.py`.
- The repo's CLAUDE.md (criteria form, §6 "let it red first") and the stop rule `specs/SPEC-M3-paragraph-merge.md` §34.

## Part A (fable, designer and executor): the arms with no runner yet

1. **Write the arm list before any run.** Put it in `findings/evidence/link-batch/v20-shakedown/ARMS.md` (English) and commit it before running anything.
   - Cover P1, P2, P3, C1, E2, E3 and K, as §5/§7 define them after the reductions in §10 and §13.3.
   - For each arm give:
     - the criterion (form one or two);
     - the prediction;
     - the red case;
     - the default if it is never run.
   - Decide, and record why, which of §10.1's three counted product-path arms survive the reduction. All three needed Shift+Arrow.
   - P1 runs on the 60-page fixture and on the mixed-page fixture (10-13m).
   - A runner that maps a point to a page must state whether it uses "inside a rectangle" or "nearest rectangle".
   - P2 asserts from the `lok` event log. Its result is `NOT_ESTABLISHED` if no product-reachable edit produces a lone size-change flush (§12.3).
2. **Write the runner(s) and judge(s).** Put them under `wasm_sdk_probe/tools/` and reuse the existing harness patterns: `repointed_page`, `--profile`, and the merge shakedown's `--candidate-profile`.
   - The page under test is the v67 page **repointed to `e2-editor-v20`**. Use `build_cutover_page.py --profile e2-editor-v20` to obtain its sha256. **Never `--write`.** The runner must record the served page's sha256 and the profile's four hashes.
   - Every new judge gets red cases that are made to go red first.
   - §34.3 applies: a new judge is reviewed once by two seats before its first **counted** use. This task is not counted, so write the review brief but do not run the review.
3. **Run.** Every arm, in both browsers (Chrome, then Firefox), on v20 with the repointed v67 page. Each first run is its own §34.4 witness.
   - Before each browser run:
     - `busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked` must not be `b true`;
     - record `pgrep -c chrome`;
     - `pgrep -af "probe_|check_m3|run_e2_c|run_merge"` must show nothing of ours. Another executor is building the host's new-document feature and runs browsers too. If something of ours is running, wait and re-check every 2–3 minutes; never run in parallel.
4. **Report.**
   - Write `findings/evidence/link-batch/v20-shakedown/README.md` with each arm's verdict and what it printed.
   - A red product cell is a finding candidate. Report it; do not fix product code.
   - A red that is the judge's own error follows §34.4: commit the witness first, then make the fix, then re-judge.

## Part B (sonnet, after Part A has committed ARMS.md): the existing merge shakedown on v20

Run `tools/run_merge_wasm_shakedown.py` with `--candidate-profile e2-editor-v20` in shakedown mode, in both browsers, exactly as v19's shakedown ran it; read the precedent in `findings/evidence/v19/`. Record what it prints against v19's last shakedown. Under C, an arm that expected a `nothing-selected` refusal at a document end now expects `verified-boundary-noop`. Report such an arm verbatim; do not edit it.

## Out of scope here (later, separate tasks)

- §10.7's held-into-refusal arms and `restore-window`. They need a host carrying v20 and v67, which means a new host version after the new-document feature's 0.2.19.
- Binding, the count chain, the release text, and the Writer stack sweep.

## Limits

- No `make`, no link, no `--write`, no freeze.
- Do not edit `web/`, `editor-shell*/`, `sdk/`, `src/`, the `Makefile`, `dist/profiles/*` or the host repo.
- New files go under `wasm_sdk_probe/tools/`, `wasm_sdk_probe/tests/` and `findings/evidence/link-batch/v20-shakedown/` only.
- Commit only your own paths (`git commit -- <paths>`), with your model's `Co-Authored-By` line.
- Report a `## SUMMARY` of at most 30 lines.
