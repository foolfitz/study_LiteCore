# Task 10-16c: v21 WASM shakedown — phase A, the arms (draft only, no runs)

Repo: `/home/jiajun/LibreOffice/study_LiteCore`. Source of truth: `specs/SPEC-M3-link-batch-v21.md` **§11** (the only criteria table, pinned at `523871fa`) plus **§12.1** (appended). §11.0 holds the general rules. Context: `handoff/HANDOFF-2026-10-16b-v21-linked-shakedown-next.md`, "Next" item 1.

Two agents run this task in parallel, one per item:

- **Agent D** owns item 1 (Ctrl+Home/End): §11.1 D1–D13 and the record arms (D6, x-lc, table Ctrl+Home then Backspace). Output: `findings/evidence/link-batch-v21/shakedown/ARMS-item1.md`.
- **Agent M** owns item 2 (paste as Markdown): §11.2 M1–M11 and the record arm (click a pasted task checkbox). M0 is done (part E); say so with its evidence path and stop there. Output: `findings/evidence/link-batch-v21/shakedown/ARMS-item2.md`.

Write only your own output file. Phase B (writing the runner) comes later, after the main session has reviewed and committed the arms.

## What an arms file is

It is the operational translation of the pinned criteria. It is committed **before** any browser run, and it is never edited after that; corrections get appended to the results README. The precedent to imitate in shape and level of detail is `findings/evidence/link-batch/v20-shakedown/ARMS.md` (read it whole). Also read that folder's `README.md` and the runner `wasm_sdk_probe/tools/run_v20_shakedown.py` with its judge `judge_v20_shakedown.py`, to see what a runner of ours can already do and where it went wrong (README §6).

For **every** criterion in your item, write one section containing the following.

1. **The criterion**, quoted from §11, with its form and its default "if not done or red", both copied verbatim.
2. **Where it runs.** Pick one:
   - (a) WASM in a browser: Chrome and Firefox, N=3 each, a pass is N/N;
   - (b) the host: it needs host 0.2.25, so it runs after the freeze; say why the no-host page cannot carry it;
   - (c) a node or Python unit test that **is already committed**. Name the file and the test, and the part-S or part-E mutation that showed it red (`findings/evidence/link-batch-v21/part-s-red/mutations.json`, `part-e-red/`). **Check that the test actually covers the criterion as written.** If it covers only part of it, say exactly which part is left and give that part an arm;
   - (d) native, already done: give the path.

   If an arm cannot be run as written, say so and say why. Do not invent a substitute: a substitute is a DECISION (see below).
3. **Fixture.** Its path or generator, its sha256 (computed now, or "per run" if the generator is not deterministic), and the native reference it is compared with: the path and the field. The product page opens `.odt` through its file input. If a native fixture is `.fodt`, say how it becomes `.odt` and what proves the conversion kept the structure the comparison reads.
4. **Steps**, as the product path takes them:
   - real keys go through CDP `Input.dispatchKeyEvent` or geckodriver actions, never a synthetic `KeyboardEvent`;
   - dialog use is real clicks and typing into the real textarea;
   - "direct SDK" is the page's SDK object, and say how the runner reaches it;
   - "direct to worker" or "direct to the engine" is a raw worker message, and say which message, which bypasses which limit, and how the runner sends it.
   
   Name the existing helper functions you would reuse (file:line), and the new instrument you would need.
5. **What is read, and the exact pass condition.**
   - Ask for state; do not count pixels.
   - Read the engine side (`editor-get-state`, the saved ODT) rather than the page's snapshot when the criterion is about the document.
   - Every "X did not happen" arm needs a positive control in the same run that shows the mechanism ran (CLAUDE.md §6; e.g. M5: the worker's own `probe.wasm` fetch in the same network log).
6. **The judge's red cases**, made red before the first run, and the non-vacuity case: zero instances must give NOT_ESTABLISHED, never PASS.
7. **Prediction**, with numbers where the native evidence gives them. A missed prediction is reported; it does not move the criterion.
8. **Identity** the report carries (§11.0): the wasm, worker, page, shell, input and reference hashes.

End the file with:

- a table: criterion | where | N | default if not done;
- a list headed **DECISIONS** (see below);
- a list of the new instruments and fixtures phase B must build, with a rough size for each.

## Fixed by the main session (do not re-decide)

- **The served page.** `tools/build_cutover_page.py --profile e2-editor-v21` with **no `--write`**: the tree's page (`web/e2-editor-app.js`), repointed to v21.
- **The served shell.** `dist/` still holds 0.2.24's shell copies: `shell_lagging_source(dist)` lists `narrow-editor-v2-client.js`, `narrow-editor-v2-session.js`, `paragraph-editor-client.js`, `sdk/document-sdk.js` and `web/e2-editor.html`. The v21 runner serves the **tree's source bytes** for every lagging shell file through `build_mirror` overrides. That is what the v74 freeze will copy into `dist/`. The report records each served file's sha256 and the shell digest computed over the mirror. Never run `make` or `make e2-c-assets`, and never write to `dist/`.
- **The profile** is `dist/profiles/e2-editor-v21/` (wasm `db3408f5…`, worker `0d55bcfa…`). It is read-only.
- **Order of runs.** Chrome, then Firefox, never in parallel with another runner of ours (timing bounds: D7 < 500 ms, D9 ≤ 500 ms, M6 ≤ 10 s).
- **What counts as not done.** Missing, NE or no reply counts as "not done" and takes the row's default (§11.0). That includes the side arms (cancel, bookkeeping, refusal).

## DECISIONS

Wherever the spec leaves a choice open, or you would need to deviate from its wording, or two readings of a criterion lead to different arms, write a **DECISION** entry. Give the options as A/B/C, your recommendation and the evidence for it (file:line). **Do not resolve it silently in the arm text.**

Expected candidates:

- D2 is marked 「宿主」.
- D11's read-only document: how does the no-host page open one, if at all?
- M11's autosave: does it exist without the host?
- Whether `hf-home-hdr-click` stays OUT of D1 (the d1-marker README, option A or B).
- M5 on Firefox: how is the network log captured?
- M3's "direct to the engine at 65,536 / 65,537": what bypasses the SDK limit?

## Hard rules

- **Read-only** except your one output file. No `make`, no build, no `--write`, no browser run, no `ddev`. Do not touch `web/`, `editor-shell*/`, `sdk/`, `src/`, `Makefile`, `dist/`, `e2/`, `tests/`.
- Do not commit. The main session reviews and commits.
- Facts carry a label:
  - **[source] file:line** for something read in code;
  - **[observed] path** for something read from an existing evidence file;
  - **[inferred]** for your own reasoning.
  
  A claim with no label is a defect. "The page has X" without a file:line is not a fact.
- English. One paragraph is one line (no hard wrapping at 72 or 80 columns).
- Your final reply to the main session: a `## SUMMARY` of at most 30 lines. Give the arms count by where they run (a/b/c/d), the DECISIONS list with one line each, and anything in the spec you found wrong or contradictory.
