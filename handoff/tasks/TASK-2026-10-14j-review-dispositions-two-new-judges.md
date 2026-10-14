# Task 2026-10-14j: dispose of the §34.3 reviews of the two new judges

Two parts, one fable each, run in parallel. They share the rules below and touch disjoint files.

- **J1:** `wasm_sdk_probe/tools/judge_v20_shakedown.py` (and the runner predicates it reads in `run_v20_shakedown.py`).
  - Brief: `findings/evidence/link-batch/v20-shakedown/REVIEW-BRIEF.md`.
  - Seats: `findings/evidence/link-batch/v20-shakedown/review/{opus-review.md,codex-review.md}`; opus's demos are in `review/opus-experiments/`.
- **J2:** `wasm_sdk_probe/tools/check_m3_new_document.py`.
  - Brief: `findings/evidence/new-document/REVIEW-BRIEF.md`.
  - Seats: `findings/evidence/new-document/review/{opus-review.md,codex-review.md}`, plus `review/opus-experiments/`.

**Authority.** You rule the dispositions on the owner's behalf; this follows the owner's standing pattern of handing these rulings to fable. Each item needs a plain-language reason in the disposition table. Read `AGENTS.md` (= `CLAUDE.md`) on criteria form, and `specs/SPEC-M3-paragraph-merge.md` §34, before ruling anything.

## Rules for ruling an item (§34, applied)

This review is each tool's one §34.3 review. Fixes from it are counted as **repaired because of review**. That is within budget for these two tools only; after this, the number must stay 0.

Give every item exactly one disposition:

- **Fixed.**
  - Use it only when one of two things is true:
    - an honest execution can produce the mis-judged report (a failed command, a missing field, a re-run in the same directory, a callback timing that occurs on WASM); or
    - the criterion claims to catch a product defect class that it demonstrably does not catch.
  - Each fix needs a red case: the old code passes it and the new code fails it (shown by construction or by reverting in place). Keep fixes small. Use one condition where one condition does.
- **Registered.**
  - Use it when the item needs a forged or hand-edited report (§34's threat model excludes those), when it is outside the criterion's claim, or when it is a SHOULD you decline.
  - A registered item gets one line, no code.
- **Claim corrected.**
  - Use it when a README, ARMS or spec sentence states something the tool does not do. Append the correction and name what it replaces; never rewrite the original.
- **Stop.**
  - Use it when the right answer is new machinery, not a test, a condition or a sentence (AGENTS.md §4's self-check).
  - Do not build it. Write it as a work item and report it.

Every seat item is checked against the source by you before it is ruled; a seat's reading is a hypothesis until you have read the lines it cites. Two items the main session already checked and found true: J1's `noSelectionAt500ms` (`run_v20_shakedown.py:834`) reads the TEXT_SELECTION callback cache (`appendEditorState`, `probe_engine.cpp:1263`), while only `selectionType` comes from the fresh `readSelection()`; J2's `user_setting()` returns `None` both for "not set" and for any `occ` failure, so a failed first read makes the restore delete the owner's `core/lang` and record `ok: true`.

## Specific questions you must answer

- **J2, N9 and the 0.2.19 bindings.** The next host is 0.2.20 (engine v20, shell v68). Decide what of this tool runs in the count chain on 0.2.20 and what stays as 0.2.19's acceptance only. Rebinding must not silently change a rule's meaning (both seats show how `CONTROL_HOST_COMMIT = HEAD` makes the diff a tautology). State the rule set the count uses, with a default if it is never decided.
- **J2, settings restore.** The tool runs against the owner's daily instance. The main session's leaning is **Fixed**: refuse to start, or refuse to restore, on an unreadable setting rather than delete it. Rule it.
- **J1, the exit rule.** Both seats show a FAIL report followed by a green re-run in the same directory exiting 0. Rule it.
- **Both, red-case census.** Both seats counted rules with no dedicated red case. Do not add a red case per rule by default (§34 forbids growing guards for their own sake). Add one only for a rule you fix, or a rule whose silent loss would flip a counted verdict, and say which.

## Limits

- **No browser, no ddev, no Nextcloud, no make, no link, no host.** J2 must never run the tool against the instance; `--red-cases` and unit tests on committed reports only.
- No committed verdict may change silently. Re-judge the committed reports with the changed tool. If a verdict moves, that is a finding for your report, not something to hide.
- **J1 edits only:**
  - `wasm_sdk_probe/tools/judge_v20_shakedown.py`;
  - `wasm_sdk_probe/tools/run_v20_shakedown.py`;
  - `wasm_sdk_probe/tests/test_v20_shakedown_judge.py`;
  - `findings/evidence/link-batch/v20-shakedown/{review/DISPOSITION.md, README.md (append), ARMS.md (append)}`.
- **J2 edits only:**
  - `wasm_sdk_probe/tools/check_m3_new_document.py`;
  - `wasm_sdk_probe/tests/test_new_document_templates.py` or a new `tests/test_check_m3_new_document.py`;
  - `wasm_sdk_probe/tools/make_new_document_templates.py`, only if N6's reader must change;
  - `findings/evidence/new-document/{review/DISPOSITION.md, README.md (append)}`;
  - `specs/SPEC-M3-new-document.md` §7 (append only).
- **Do not touch:**
  - `editor-shell*/`, `web/`, `sdk/`, `src/`, the `Makefile`;
  - `run_merge_wasm_shakedown.py`, `judge_counted_m2.py`, `findings/140-*`, `findings/evidence/paste-latency/`.
  - A parallel fable is working on finding 140, and the M2 judge is the binding step's.
- Commit only your own paths (`git commit -- <paths>`). If `.git/index.lock` exists, wait and retry. End messages with your model's `Co-Authored-By` line; never a `Claude-Session` line; no push.

## Output

- `review/DISPOSITION.md`, in the shape of `findings/evidence/v19/review/DISPOSITION.md`: one row per seat item, with where, disposition and red case. Add a closing line with the §34.4 numbers for your part: repaired because of review = N, because of execution = 0.
- Final reply: a `## SUMMARY` of at most 20 lines with:
  - counts per disposition;
  - the three or four fixes that matter, each in one line;
  - J2's count-chain rule set, or J1's exit rule;
  - test counts before and after;
  - whether any committed verdict moved.
