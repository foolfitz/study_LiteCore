# Task 10-16d: v21 WASM shakedown, phase B (instruments, populations, judges, runners, one smoke)

Repo: `/home/jiajun/LibreOffice/study_LiteCore`. The arms are committed at `8f1dbf0a`, and they are what you implement:

- `findings/evidence/link-batch-v21/shakedown/ARMS.md` holds the shared rules, the instruments S-1 to S-11, file ownership and the order of work;
- `ARMS-item1.md` §8 and `ARMS-item2.md` §9 hold the main session's **rulings**. Where a ruling differs from the draft's recommendation, the ruling wins;
- spec §12.2 holds the readings.

Do not edit any of these files. If something in them turns out to be wrong or impossible, stop and report. Do not work around it.

## Who does what

- **Agent D** (item 1): S-1, S-4 (keys, pointer, drag), S-5, S-6, S-7 (the container adapter), S-8, S-9, the item-1 observer snippet, the D1/D7 population tool, the D5-gen node test, the D2 wrapper, the item-1 judge and the item-1 runner.
  - **Build S-9 (the lock and pre-run checks) and S-1 (the mirror) first, and keep their interfaces small.** Agent M imports them.
- **Agent M** (item 2):
  - the native pre-runs: DM-5, and DM-17 C. Put them in a new folder `findings/evidence/link-batch-v21/native/markdown-paste/round-3/` with a README and SHA256SUMS, as the earlier rounds have;
  - the instruments: S-3 (the page hook), S-4 (clipboard), S-10, S-11, the item-2 observer snippet;
  - the comparator on top of S-7;
  - the corpora and the M10 fixture generators;
  - the M1/M3/M4/M5 population tools, the item-2 judge and the item-2 runner.

**File ownership.** Each agent writes only the files it creates for its part. Name them as `ARMS.md` §3 does, or with an obvious `v21_` / `_item1` / `_item2` prefix.

Neither agent edits product files: `web/`, `editor-shell*/` (except one new test file for D5-gen, by Agent D), `sdk/`, `src/`, `input/`, `Makefile`, `dist/`, `e2/`. Committed evidence is not edited either.

**When you need the other agent's instrument and it is not there yet**, work on something else. If nothing else is left, end your turn with a report that says what you are waiting for. The main session relays. Read the other agent's files; do not edit them.

## Hard rules

- **No `make`**, no build, no `--write`, nothing written under `dist/`, no ddev.
  - The native probe for Agent M's pre-runs is built with `g++` as round 2 did. That is allowed; `make` is not.
  - The host arms (D2 on the host, M11-autosave) are **not** run in this task. Write their code paths, but do not run them.
- **Every browser run of ours holds the S-9 lock.** That includes smoke and development runs, Chrome and Firefox. Never two at once.
  - Before the first browser run, check KWallet: `busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`. If it reads `b true`, stop.
- **Red first.** Every judge has `--self-test` covering every red and non-vacuity case its arm file names. Every instrument with red cases in the arm files has a test. Commit them, showing red on the mutated input and green on the real one, **before** the first evidence run.
  - A tool that reports green has proved only that it returns green.
- **Commit only your own files**, with explicit paths (`git add <paths>`; never `-A` or `.`). Check `git status` first.
  - End the message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never add a `Claude-Session:` line.
  - If `.git/index.lock` exists, wait a few seconds and retry; the other agent may be committing.
- **§34.4.** When a runner or judge of yours misjudges or loses an honest run, commit the run's output as a witness **before** you fix the tool. Keep a tally.
- **Facts carry labels** ([source] / [observed] / [inferred]) in READMEs.
- **English** in all files. One paragraph is one line.

## Where to stop

Stop after **one smoke pass per item in Chrome only**, under the lock: all arms, N=1. It is a development run. Record it under `findings/evidence/link-batch-v21/shakedown/smoke/` and label it as a smoke. **Never judge it as evidence.**

Do **not** start the evidence runs (N=3, both browsers). The main session reviews the smoke first.

If the smoke shows a **product** red, keep it, describe it, and do not fix it: product fixes are not yours. If it shows a **runner** problem, fix it under §34.4 and smoke that arm again.

## Report

Your final reply starts with a `## SUMMARY` of at most 30 lines. It covers:

- what was built: the files, and their test and self-test results;
- the commits;
- the smoke results per arm, one line each: the outcome and anything surprising;
- the §34.4 tally;
- anything in the arms that turned out impossible or wrong;
- what the evidence runs will need: their duration estimate per browser, and the order.
