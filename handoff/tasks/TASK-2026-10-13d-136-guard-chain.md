# Task 2026-10-13d — the 136 page: the "must not break" set on the final bytes (SPEC-M3-held-key §16; ruling-3 conditions 5–6)

Mechanical runs of existing instruments on a new page. You run, record and summarise; you do not redesign anything. The criteria are already written; if a cell is red, **stop that step, record it, and go on to the next step** — do not change any check, judge or instrument except the pin lines named below. This is the same chain as `handoff/tasks/TASK-2026-10-13-134-guard-chain.md` and its precedent `TASK-2026-10-13-132-guard-chain.md` (read both: their commands are the precedent; the 134 run's evidence is `findings/evidence/136/guard/`), retargeted to a new page, plus G5 and G6 below. 130-U is done by the main session; it is not in this task.

## The candidate (verify before G0, and record)

- `wasm_sdk_probe/dist/e2-editor-app.js` sha256 must be `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678` (= `web/`). If not, STOP and report.
- The ddev host `~/Projects/Nextcloud_Apps/litecore` serves it: engine package buildId `d6d04880f56e31da`, `appinfo/info.xml` 0.2.18 (uncommitted on purpose — do not commit, do not revert, do not run `package_m3_engine.py`, do not run `ddev occ upgrade`).
- What changed from 0.2.16 (`6470dec0…`): finding 136 (`updateState` notes the last caret the engine pushed with no range selected; the reopen puts the caret back there — ruling-3 addendum 4) and the restore flash (`updateState` does not follow the caret while the page reopens). Every state write now notes the caret, so 132-B, 131-B and 128-B are the witnesses that holds and presses read exactly as before.
- Hard rules: do **not** run `make` (any target), do not edit `wasm_sdk_probe/web/` or `dist/`, do not touch the host repo, never run two browser jobs at the same time, and do not run anything with a `--write` mode. Before each browser step, check that no other probe is running (`pgrep -af "probe_|check_m3|run_e2_c"` must show nothing of ours). The owner's own Firefox may be open; leave it alone.

## Steps (in this order, sequential)

**G0 — 132-B.** As the precedent's G0, with output `findings/evidence/136/guard/132-b/` and judge `--page b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678`. Criterion: the judge's exit code 0 (12/12 holds, both wash controls). README in the shape of `findings/evidence/132/132-b-final/README.md`.

**G1 — 131-B and 128-B, one probe run.** As the precedent's G1, output `findings/evidence/136/guard/131b-128b/`, `judge_131b.py … --page b24d754a…`. Same criteria (every burst `deleted 20`, `refused 0`, `other []`, four arms `persistent.differing == 0`; 128-B single presses ≤ 40 ms, host-segment cell holds, its red control red). If the host-segment cell reads `NOT_JUDGED` because of two PUTs, the precedent's disposition applies: rerun **only those two arms once** (`--arms hostseg,hostseg-red`), instrument and judge unchanged, into `…/131b-128b-hostseg-rerun/`; say so in the README.

**G2 — 121-B.** As the precedent's G2, file prefix `0.2.18-136` (binding file `findings/evidence/121/0.2.18-136-binding.txt`). Same criterion (§9.13); compare with the `0.2.16-134-*` reports.

**G3 — 129-B.** Re-pin `wasm_sdk_probe/tools/probe_129_m4_wasm.py`'s `FINAL_PAGE_SHA256` from `6470dec0…` to `b24d754a…`, old value kept in the comment above it (precedent commits `d049b534`, `d2349d03`). Commit that one change alone. Then run exactly as the precedent's G3 (same docs dir, same arguments). `preflight.final` must show `b24d754a…` and the red control `8909564e…`. Same criterion.

**G4 — 122-B / C2.** Re-pin both judges' page pins (`findings/evidence/c-prime/c2/judge_c2.py` and `findings/evidence/typing-latency/judge_p2.py`) from `6470dec0…` to `b24d754a…`, old value in a comment (precedent `e3b9cbfd`); commit that alone. Copy `chain-c2.sh` to `findings/evidence/136/guard/c2/chain-c2.sh` changing only its output directories; clean desk as the C2 README requires (record `pgrep -c chrome` and `/proc/loadavg` at start); run detached, wait, run both judges as before into `judge-output.txt`.

**G5 — restore-window on the new page (ruling-3 condition 5).** `python3 findings/evidence/134/restore-window/probe_restore_window.py --out findings/evidence/136/guard/restore-window` (default 3 rounds per browser). Criterion: every round 1 refusal, generations `['1','2']`, `marks == 1`, mark in paragraph 210, rest unchanged; report the caret-back time and whether `scrollTop` ever went to 0 (expected: it no longer does).

**G6 — the C2 cell twice more (ruling-3 condition 6).** After G4, run the Chrome ratio-2 gap-80 cell two more times exactly as `findings/evidence/134/c2-cell-repeat/repeat.sh` runs it, into `findings/evidence/136/guard/c2-extra/run-01.json`, `run-02.json` (clean desk recorded), and read them with `python3 findings/evidence/134/c2-cell-repeat/read_repeat.py findings/evidence/136/guard/c2-extra`. Report-only: G4's judged run is the verdict of record; G6's counts go to finding 135.

## Output

- Evidence under `findings/evidence/136/guard/` (G0, G1, G4), `findings/evidence/121/` (G2), `findings/evidence/129/final/round-*` (G3). Add `findings/evidence/136/guard/README.md` (English): conditions (page, buildId, host version, times UTC), each step's command, criterion, what was read, PASS/FAIL per cell, anything odd. Facts only; mark anything not checked as unverified.
- One commit per completed step; the two pin changes are their own commits. Commit messages in Traditional Chinese (zh-TW), like the repository's recent ones, ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; never a `Claude-Session:` line.
- Final reply: `## SUMMARY` (≤ 30 lines): per step the verdict, judges' exit codes, commits, and anything red with the exact line the judge printed.
