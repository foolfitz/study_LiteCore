# Task 2026-10-13b — the 134 page: the "must not break" set on the final bytes (SPEC-M3-held-key §14; ruling-1 condition 4)

Mechanical runs of existing instruments on a new page. You run, record and summarise; you do not redesign anything. The criteria are already written; if a cell is red, **stop that step, record it, and go on to the next step** — do not change any check, judge or instrument except the pin lines named below. This is the same chain as `handoff/tasks/TASK-2026-10-13-132-guard-chain.md` (read it: its commands are the precedent), retargeted to a new page. 130-U is already done by the main session (`findings/evidence/130/replay-output-0.2.16-134.txt`); it is not in this task.

## The candidate (verify before G0, and record)

- `wasm_sdk_probe/dist/e2-editor-app.js` sha256 must be `6470dec0cb0e20db46d33d46bfc565893f542b79f7317fcbc421653a562bb94b` (= `web/`). If not, STOP and report.
- The ddev host `~/Projects/Nextcloud_Apps/litecore` serves it: engine package buildId `9352fae3aea68b5e`, `appinfo/info.xml` 0.2.16 (uncommitted on purpose — do not commit, do not revert, do not run `package_m3_engine.py`, do not run `ddev occ upgrade`).
- What changed from 0.2.15 (`abe93f45…`): finding 134's B (after a delete this page sent is refused, the rest of that Backspace/Delete hold is not sent) and D (after an automatic reopen the caret is put back). A mid-document hold has no refusal, so 132-B must read exactly as before; that is what this chain witnesses.
- Hard rules: do **not** run `make` (any target), do not edit `wasm_sdk_probe/web/` or `dist/`, do not touch the host repo, never run two browser jobs at the same time, and do not run anything with a `--write` mode. Before each browser step, check that no other probe is running (`pgrep -af "probe_|check_m3|run_e2_c"` must show nothing of ours). The owner's own Firefox may be open; leave it alone.

## Steps (in this order, sequential)

**G0 — 132-B.** As the precedent's G0, with output `findings/evidence/134/guard/132-b/` and judge `--page 6470dec0cb0e20db46d33d46bfc565893f542b79f7317fcbc421653a562bb94b`. Criterion: the judge's exit code 0 (12/12 holds, both wash controls). README in the shape of `findings/evidence/132/132-b-final/README.md`.

**G1 — 131-B and 128-B, one probe run.** As the precedent's G1, output `findings/evidence/134/guard/131b-128b/`, `judge_131b.py … --page 6470dec0…`. Same criteria (every burst `deleted 20`, `refused 0`, `other []`, four arms `persistent.differing == 0`; 128-B single presses ≤ 40 ms, host-segment cell holds, its red control red). If the host-segment cell reads `NOT_JUDGED` because of two PUTs, the precedent's disposition applies: rerun **only those two arms once** (`--arms hostseg,hostseg-red`), instrument and judge unchanged, into `…/131b-128b-hostseg-rerun/`; say so in the README.

**G2 — 121-B.** As the precedent's G2, file prefix `0.2.16-134` (binding file `findings/evidence/121/0.2.16-134-binding.txt`). Same criterion (§9.13); compare with the `0.2.15-132-*` reports.

**G3 — 129-B.** Re-pin `wasm_sdk_probe/tools/probe_129_m4_wasm.py`'s `FINAL_PAGE_SHA256` from `abe93f45…` to `6470dec0…`, old value kept in the comment above it (precedent commits `d049b534`, `d2349d03`). Commit that one change alone. Then run exactly as the precedent's G3 (same docs dir, same arguments). `preflight.final` must show `6470dec0…` and the red control `8909564e…`. Same criterion.

**G4 — 122-B / C2.** Re-pin both judges' page pins (`findings/evidence/c-prime/c2/judge_c2.py` and `findings/evidence/typing-latency/judge_p2.py`) from `abe93f45…` to `6470dec0…`, old value in a comment (precedent `1fa91903`); commit that alone. Copy `chain-c2.sh` to `findings/evidence/134/guard/c2/chain-c2.sh` changing only its output directories; clean desk as the C2 README requires (record `pgrep -c chrome` and `/proc/loadavg` at start); run detached, wait, run both judges as before into `judge-output.txt`.

## Output

- Evidence under `findings/evidence/134/guard/` (G0, G1, G4), `findings/evidence/121/` (G2), `findings/evidence/129/final/round-*` (G3). Add `findings/evidence/134/guard/README.md` (English): conditions (page, buildId, host version, times UTC), each step's command, criterion, what was read, PASS/FAIL per cell, anything odd. Facts only; mark anything not checked as unverified.
- One commit per completed step; the two pin changes are their own commits. Commit messages in Traditional Chinese (zh-TW), like the repository's recent ones, ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; never a `Claude-Session:` line.
- Final reply: `## SUMMARY` (≤ 30 lines): per step the verdict, judges' exit codes, commits, and anything red with the exact line the judge printed.
