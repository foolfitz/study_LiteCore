# Task 2026-10-14c: a browser witness on the v67 candidate bytes before the freeze (129-B, and restore-window if it runs without the host)

This is a set of mechanical runs of existing instruments on new page bytes. You run them, record what they print and summarise; you do not redesign anything.

The page and shell changes since shell generation v66 are:

- v20 part 1: client and SDK, gated on the profile;
- v20 part 2: the page number, gated on `offersPageRectangles()`;
- ruling 6 conditions 45, 47 and 48 (`aeaf92c0`, `a6ecb7fd`, `bcf3f747`).

On the shipped engine v19, the only paths that change are these:

- `placeCaret`, now an override on `NarrowEditorV2Session` that acknowledges a click only on caret or selection evidence (finding 138). The page calls it on pointer-down and when it puts the caret back after a reopen.
- The queue observer of condition 47.

The question this task answers: do the instruments that exercise those paths read on the new bytes exactly as they did on v66's?

## Hard rules

- From `wasm_sdk_probe/`, the only `make` allowed is `make e2-c-assets`. Run `make -n e2-c-assets` first and check that it prints only `cp` lines. If it prints anything else (`em++`, a link, a packing step), STOP and report.
- Do not edit `web/`, `editor-shell*/`, `sdk/`, `src/` or the `Makefile`.
- Do not touch the host repo, `~/Projects/Nextcloud_Apps/litecore`.
- Do not freeze a shell generation, and do not run any tool's `--write` mode.
- Never run two browser jobs at the same time. Before each browser step, `pgrep -af "probe_|check_m3|run_e2_c"` must show nothing of ours. The owner's own Firefox may be open; leave it alone.
- If a cell is red, stop that step, record it, and go on to the next step. Change no check, judge or instrument except the one pin named below.
- Commit only your own paths, with `git commit -- <paths>`. Commit messages are in Traditional Chinese (zh-TW), like the repository's recent ones, and end with your model's `Co-Authored-By` line. Never add a `Claude-Session:` line.

## Steps

- **W0, the candidate.**
  - Run `make e2-c-assets`.
  - Record the sha256 of the five copied files and of their sources: `web/e2-editor.html`, `web/e2-editor-app.js`, the two `editor-shell-v2/narrow-editor-v2-*.js`, and `sdk/document-sdk.js` against their `dist/` copies. Each pair must be equal.
  - Run `python3 tools/check_e1_c_bundle_intact.py` and confirm it prints `"intact": true`.
  - Record which profile `dist/e2-editor.html` / the page loads. Read it from the page source, not from memory. It is expected to be `e2-editor-v19`. If it is not, STOP and report.
- **W1, 129-B on both browsers.**
  - Re-pin `tools/probe_129_m4_wasm.py`'s `FINAL_PAGE_SHA256` from `b24d754a…` to the new `dist/e2-editor-app.js` sha256. Keep the old value in a comment above it (precedent `d049b534`, `d2349d03`, and the 10-13d chain's G3). Commit that one change alone.
  - Run the probe in `--final` mode exactly as `handoff/tasks/TASK-2026-10-13d-136-guard-chain.md` G3 and its precedent ran it: the same arguments, the docs directory, and a new output under `findings/evidence/129/final/` named for this round, for example `round-v67-candidate-<browser>`.
  - Run Chrome first, then Firefox.
  - Criterion, the same as G3: `preflight.final` shows the new sha, the red control behaves as before, and 54/54 with 0 cells different from both reference rounds. Report the differing cells verbatim if there are any.
- **W2, restore-window, only if it runs without the ddev host.**
  - Read `findings/evidence/134/restore-window/probe_restore_window.py` and decide from its source alone whether it needs the ddev host.
  - If it needs the host, skip this step and say so.
  - If it serves `dist/`, run it as the 10-13d chain's G5 into `findings/evidence/link-batch/v67-witness/restore-window/`. The criterion is G5's.

## Output

- Write `findings/evidence/link-batch/v67-witness/README.md` in English, covering:
  - W0's hashes and the profile;
  - each step's command, criterion, what it printed, and PASS or FAIL per cell;
  - anything odd.

  Mark anything you did not check as unverified.
- Final reply: a `## SUMMARY` of at most 20 lines, giving the verdict per step, the commits, and anything red with the exact line it printed.
