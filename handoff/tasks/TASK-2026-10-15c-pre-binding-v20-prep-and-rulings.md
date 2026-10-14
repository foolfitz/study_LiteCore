# Task 2026-10-15c: before binding v20 — part P (prep) and part J (three rulings)

**Authority.** The owner chose **A** on 2026-10-15: the mechanical prep goes to one fable, and the three judgment calls go to another fable, who rules them on the owner's behalf. The release-text draft is shown to the owner before it is used. Read `AGENTS.md` (= `CLAUDE.md`) and `specs/SPEC-M3-paragraph-merge.md` §34 first.

**State.**
- Host **0.2.23** is installed: commit `2ccf1a9`, buildId `c3c22d9294de068a`, page `ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e`, shell v72, engine v20.
- Every uncounted change, 0.2.13–0.2.23, is batched into one overnight count chain after v20 is bound (RUNBOOK-relink-v20 §4.2–§4.3).
- Context:
  - `handoff/HANDOFF-2026-10-14b-…` and its Addendum;
  - `handoff/HANDOFF-2026-10-13f-shift-arrow-deferred-137-registered-v20-part1.md` line ~50, the origin of the list below;
  - `handoff/HANDOFF-2026-10-13g-…`.

## Part P — prep (one fable; small, semantic where noted)

- **P1. `wasm_sdk_probe/tools/judge_counted_m2.py` learns C.**
  - Its `nothing-selected` row (`:112`) still expects a refusal.
  - Key it the way the merge runner does (`7e6c9acd`, `boundary_noop_declared`, the wasm fragment), so v19 reports keep their verdicts.
  - The witness is part B's reports (`findings/evidence/link-batch/v20-shakedown/merge/`). Re-judge them, and re-judge the committed v19 X7 reports: their verdicts must not change.
- **P2. `tests/test_judge_counted_m2.py::V19Witness`.** Its 2 tests have been red by construction since `7e6c9acd`. The frozen judge's `thisRunner` compares the live runner hash with the v19 reports' `73b2e9ff`.
  - Fix the **test**, not the judge's rule. The docstring says to re-judge at the run's commit; for example, materialise the runner as of the witness commit for that comparison.
  - Show the test red before and green after.
- **P3. `wasm_sdk_probe/tools/check_m3_new_document.py`:**
  - set `ENGINE_BUILD_ID = "c3c22d9294de068a"` and `PAGE_SHA256 = "ccb67a52…"`, plus the host bindings for 0.2.23 (`HOST_COMMIT 2ccf1a9`, `HOST_VERSION 0.2.23`), per J2's ruled rule set (`findings/evidence/new-document/review/DISPOSITION.md`, spec §7.5);
  - `--red-cases` must stay all red, with 0 MISS.
- **P4. Re-point the nine runners' page pins to `ccb67a52…`.** The nine are: the six M3 runners, the production-UI runner, the autosave runner, and the product-path net (10-13f's list).
  - Find each pin (`FINAL_PAGE_SHA256`, `PAGE`, `--page` defaults, binding constants). Make **one commit per pin line**, keeping the old value in a comment above. The precedents are `1b5efdbb`, `a0ed713f` and `e3b9cbfd`.
  - 129-B retires on v20 (§10.9 S-2). Say whether its pin moves or the runner is marked retired, and why.
  - List the nine with path, old and new values in the evidence README.
- **P5.** The `make test-e2-c-static` exit code, and every touched tool's own tests, after P1–P4.
- **§34.4.** P1 and P2 are "repaired because of execution", with the witnesses named. P3 and P4 are binding updates, not repairs. Write the counts in the README.

## Part J — rulings (another fable; rule, write, do not implement code)

- **J-a. The count chain's abort rule.** Choose: "abort only if load ≥ X at start", or "never abort a started chain", or something argued better.
  - Read the shape of `runs-0.2.13/chain-2026-10-12.sh` (find it under `findings/evidence/`), the desk history of this week, and memory-recorded hazards: the owner's Chrome running, KWallet locking after reboot, load 1.5–2.7 seen in 10-14p.
  - Give the rule, its default if never decided, and what a reader of the chain's output does on each outcome.
- **J-b. Finding 135's C2 repeat semantics** (`findings/135-…md`; C2 at 148.7 / 150 ms single-run).
  - The handoff's default is "single-run rule with a ratio beside".
  - Rule it with numbers from the committed C2 reports. Say whether a repeat count is needed, and what reads PASS, FAIL or NOT_ESTABLISHED.
  - Changing a judge is out of scope here. If the ruling needs a judge change, write it as a work item with its §34.4 witness requirement.
- **J-c. The release text draft** for the batched count: 0.2.13–0.2.23, in zh-TW, owner-facing.
  - It must include:
    - finding 137's three effects in both releases;
    - L-C-late-K1;
    - L-C-number-or-indent;
    - 138, 140, 141, 143 and 144 fixed;
    - 141's remaining cost: a held boundary key costs one ~2.25 s no-op;
    - the held-key tail inside text (≤ 2 characters again since 0.2.22);
    - the page number, bar and bubble;
    - new document (0.2.19);
    - Shift+Arrow not in this batch;
    - Ctrl+Home/End not supported (142);
    - `SPEC-M3-held-key.md` §3.2's stale owner-facing sentence, corrected.
  - Each claim cites its finding or spec. Mark anything not measured as such.
- **Output.** Write J's rulings to `handoff/RULING-2026-10-15-pre-binding.md` (English) and the release text to `handoff/RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md` (zh-TW). Commit both.

## Limits (both parts)

- No browser, no ddev, no make except what `test-e2-c-static` runs, no link, no freeze, no host change, no `--write`, and no binding of v20 itself. `BINDING` is set by the main session after both parts land.
- **P edits only:** `judge_counted_m2.py` and its test, `check_m3_new_document.py` and its tests, the nine pin lines, and a new `findings/evidence/link-batch/pre-binding/README.md`.
- **J edits only:** its two handoff files.
- Commit only your own paths (`git commit -- <paths>`). If `.git/index.lock` exists, wait and retry. End messages with your model's `Co-Authored-By` line; never a `Claude-Session` line; no push.
- Final reply: a `## SUMMARY` of at most 20 lines.
