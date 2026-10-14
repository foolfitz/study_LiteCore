# Task 2026-10-14k: 129-B witness on the second-pass v68 candidate (finding 140, `a60456a6`), before the freeze

This task repeats task 10-14g (`handoff/tasks/TASK-2026-10-14g-pre-v68-witness.md`; read it and its red evidence `findings/evidence/link-batch/v68-witness/README.md`). The steps are the same; only the bytes and one added clause differ.

- **Bytes.** Since v67, `editor-shell-v2/narrow-editor-v2-session.js` differs: it is now `f47c80ec955397c44d7638da63ed6837a3dea47125f6e279192298c20ed62ba9`. That is finding 140's second pass. A click made while a range is open takes v67's polling path; a click on a collapsed selection asks the engine with rounded twips. `narrow-editor-v2-client.js` is `aaceb555…`, unchanged since 10-14g. The page is `7815e16c…`, unchanged, so it needs no re-pin.
- **Criterion.** It is criterion C2 of task 10-14h (`handoff/tasks/TASK-2026-10-14h-finding-140-second-pass.md`), written before any run:
  - **Unchanged from 10-14g:**
    - 54/54 cells, with 0 differing from the four reference rounds: `round-20261012T092119Z`, `round-20261012T235136Z`, `round-20261013T063013Z` and `round-20261014T022210Z` (the v67 witness);
    - 0 toasts;
    - every toolbar `collapsed`;
    - the red control red;
    - Chrome equal to Firefox;
    - the analyzer's key-to-move clauses (moving keys < 200 ms, non-moving keys < 400 ms) pass as they did on v67.
  - **Added before this run:** in each browser, every `定位游標` latency record of a succeeded click is **< 100 ms**, and their median is **≤ 40 ms**. For reference:
    - v67 Chrome: 26.1–31.7 ms, median 27.95;
    - v67 Firefox: 27.8–32.0 ms, median 29.15;
    - the red candidate: 253.4–268.3 ms.

## Steps

- **W0.**
  - Run `make -n e2-c-assets` and check that it prints only `cp` lines (or nothing to do). Then run `make e2-c-assets`.
  - Record the sha256 of the five source/dist pairs; each pair must be equal and the session must be `f47c80ec…`.
  - `check_e1_c_bundle_intact.py` must print `"intact": true`.
  - The page must load `e2-editor-v19`.
- **W1.** Run `tools/run_probe_129_final.sh ../findings/evidence/129/final/round-20261012T092119Z/docs 4 1`, Chrome then Firefox, as 10-14g did. Then run `analyze_129_m4.py` against each of the four reference rounds.
- **W2.** Extract every `定位游標` latency record per browser from the new round's `arms-*.jsonl`. Report the count, min, max and median, and judge the added clause. Write the extraction as a short script in the evidence directory and commit it with its output.

## Rules

The rules are 10-14g's:
- The only `make` allowed is `e2-c-assets`.
- Do not edit `web/`, `editor-shell*/`, `sdk/`, `src/` or the `Makefile`.
- No host, no freeze, no `--write`.
- One browser job at a time.
- Before each browser step:
  - check that the KWallet `Locked` property is not `b true`;
  - record `pgrep -c chrome`;
  - check that nothing of ours is running.
- A red cell is recorded and the run goes on; no check is changed.

Other fables are editing `tools/judge_v20_shakedown.py`, `tools/run_v20_shakedown.py`, `tools/check_m3_new_document.py` and their evidence directories. They run no browser. Do not touch their files.

Commit only your own paths (`git commit -- <paths>`). If `.git/index.lock` exists, wait and retry. Commit messages are in zh-TW and end with your model's `Co-Authored-By` line; never a `Claude-Session` line. Do not push.

## Output

- `findings/evidence/link-batch/v68-witness-2/README.md` (English): the verdict per step, the clause table (10-14g's table plus the latency row), any differing cell verbatim, and the desk state.
- Final reply: a `## SUMMARY` of at most 15 lines.
