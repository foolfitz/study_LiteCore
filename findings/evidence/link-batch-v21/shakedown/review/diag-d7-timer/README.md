# A0: D7's timer in Firefox, mapped with sentinels (diagnostic, not evidence)

Fable ruling 2, Q1 conditions 2–4; spec `SPEC-M3-link-batch-v21.md` §12.4 (b), (c). **Diagnostic, not evidence**: the report is labelled `smoke: true`, no judge reads it, and no criterion counts it.

## What ran

- **Tool**: `wasm_sdk_probe/tools/diag_v21_d7_timer.py run` (`70c55853`). It imports the unchanged runner (`runnerSha256` `4fba3d19…`) and replaces the item-1 observer's `SNIPPET` in memory with a copy.
  - The copy adds three silent sentinels (+440, +455, +470) and paint-reply stamps, carried inside the real `ask7` entry.
  - The real ask stays at +500.
  - Identities are in `a0-identity.json`. The patched snippet `02891a71…` equals the report's `pages.v21.snippetSha256[1]`, so the patch reached the served page. The page served is `605cf24b…` and the shell digest `e35923a0…`, both as in the evidence runs.
- **Run**: Firefox 157.0.1 headless, D1's 12 `t-*` arms plus the paired control, N=3 (39 rounds, 72 Ctrl presses), 2026-10-17 11:21–11:32, under the browser lock.
- **Desk**:
  - The owner's desktop Chrome was closed first (SIGTERM to its browser process, at the owner's request; clean exit, 0 processes left).
  - Load at the start 0.27 (`desk-at-start.txt`). KWallet unlocked. Foreign CPU over the limit: 0 of 39 rounds.
  - The owner's desktop Firefox (running since boot) stayed open, as it was during both earlier Firefox D1 runs.
- **Read**: `read-a0.txt`, from `diag_v21_d7_timer.py read` (the §12.4 (c) rule as pinned; self-test 9/9, red 7/9 under a mutation, refuses an unpatched report).

## Result

`DECISION {"presses": 72, "late500": 0, "max470": 471.7, "max455": 455.7, "max440": 447.9, "differential": 0, "informative": false, "constant": 455, "note": "premise unmeasured, maximum slack chosen"}`

- **No lateness reproduced.** All 72 +500 reads were posted at 500.1–501.5 ms. In the two D1 runs, 16 of 72 `t-*` reads were later than +505 in each run, and up to +560.3.
- The sentinels fired on time: +470 at 470.1–471.7 and +455 at 455.0–455.7. The +440 sentinel was 6–8 ms late five times (441.8–447.9).
- **Paint stamps work** (non-vacuous): every press carried 1–2 paint replies, 141 in all, at +0.8 to +12.8 ms after the move reply, with a median of +6.3. None came near +500. In this run there was no paint at +500 for the timer to wait behind.
- Caret equal in 72/72.
- **By §12.4 (c), A0 is uninformative (0 < 3 late presses), so the constant is 455**, recorded as 「premise unmeasured, maximum slack chosen」. The differential control (a press late at +500 and on time at +470) could not print, because nothing was late. The rule names this case and its outcome in advance.

## What this does not separate (recorded, not judged)

- In the D1 runs the late reads began at the session's 8th round (positions 8–102 of 120 in the first run, 8–97 in the re-run), so the age of the session does not explain them.
- **A0 differs from the D1 runs in three ways at once**, and this run cannot tell which one mattered:
  1. **The desktop Chrome was closed.** It was open during both D1 runs, and it voided cells by foreign CPU (79 % and 75 % samples). The runner samples foreign CPU for 2 s before each arm, not during the press.
  2. **The sentinel timers themselves.** Ruling 2 refused a 5 ms heartbeat because waking the main thread could hide the phenomenon (Firefox runs GC in idle periods). Three wake-ups at +440, +455 and +470 are a much weaker version of the same perturbation.
  3. **Arm order.** A0 runs only the `t-*` arms, back to back. D1 interleaves them with the other 28 arms.
- The evidence re-run at 455 has no sentinels and keeps the desktop Chrome closed, so it removes confound 2 and keeps 1.
