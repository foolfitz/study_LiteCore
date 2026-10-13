# Task 2026-10-13e — the 136 guard chain, run 2 (the first run's Chrome halves were not measured: locked KWallet)

Written by the main session **before** run 2 starts. Run 1 (`TASK-2026-10-13d-136-guard-chain.md`, evidence `findings/evidence/136/guard/`) completed every step, but every Chrome half died at its first `Page.navigate`. The cause is environmental and verified: the KDE wallet `kdewallet` was locked after the owner's reboot, and headless Chrome waits for it before a profile's first network request (`findings/evidence/136/guard/README.md`, last section; `chrome-wallet-diagnosis.txt`). The probes, judges and page were not the cause and are not changed.

Run 2 is the same chain, G0–G6, as written in `TASK-2026-10-13d-136-guard-chain.md`, with the differences below. Read that task, its two precedents, and run 1's README first; run 1's README records every exact command.

## What run 2 is, and how it counts (fixed before it runs)

- **Run 2 is the verdict of record** for every step: each judge reads one report holding both browsers, as the judges are built to do. Run 1 stays in the tree as "Chrome not measured (environment)".
- Run 1's Firefox halves are an **extra sample**. They are reported beside run 2's Firefox halves, and they **do not overrule** run 2. If run 2's Firefox half of a cell is red and run 1's is green, the cell is red.
- No other reruns. The one exception is the G1 host-segment disposition in the 13d task (`--arms hostseg,hostseg-red` once, if `NOT_JUDGED` because of two PUTs).
- If the Chrome health check below fails at any point, **stop the whole chain there**. Record it and report. Do not run the remaining steps Firefox-only.

## Differences from 13d

1. **Precondition (new, before G0, recorded in the README):**
   - `busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked` must print `b false`.
   - Chrome health check: `timeout 30 google-chrome --headless=new --user-data-dir="$(mktemp -d)" --dump-dom https://litecore.ddev.site:8443/login`. It must exit 0 within the limit and print a DOM that contains `Nextcloud`. Use default flags only: no `--password-store`. (The main session checked the command's shape at 05:40Z with `--password-store=basic`, since the wallet was still locked then: rc 0, 738,274 bytes, `Nextcloud` 328 times.)
   - Run the health check again before every browser step.
   - If either check fails: STOP and report.
2. **Pins:** G3's `FINAL_PAGE_SHA256` (`1b5efdbb`) and G4's two judge `PAGE` pins (`a0ed713f`) already point at `b24d754a…`. Verify them with `grep`; there are no pin commits in this run.
3. **Output locations:**
   - G0, G1, G4, G5 and G6 write under `findings/evidence/136/guard-r2/`, using the same subdirectory names as run 1 (`132-b/`, `131b-128b/`, `131b-128b-hostseg-rerun/` if needed, `c2/`, `restore-window/`, `c2-extra/`). The `chain-c2.sh` and `repeat.sh` copies change only `E=` and nothing else; run 1's copies already carry `PAGE=b24d754a426706bb`.
   - G2 uses the file prefix `0.2.18-136-r2` (binding file `findings/evidence/121/0.2.18-136-r2-binding.txt`).
   - G3 goes to a new `findings/evidence/129/final/round-*`, created by the driver as before.
4. **README:** `findings/evidence/136/guard-r2/README.md` (English), in the shape of run 1's.
   - Add one table: per cell, run 2's Chrome verdict, run 2's Firefox verdict, run 1's Firefox verdict.
   - State plainly that run 2 is the verdict of record.
5. Everything else is as in 13d: candidate checks, hard rules (no `make`, no edits to `web/` or `dist/`, the host repo untouched, never two browser jobs at once, no `--write` mode), one commit per step, zh-TW commit messages ending with the `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` line and never a `Claude-Session:` line, and the final `## SUMMARY` (≤ 30 lines).
