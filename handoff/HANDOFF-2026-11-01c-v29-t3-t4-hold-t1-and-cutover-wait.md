# Handoff: v29 cut over, generation 83 frozen, T3 and T4 hold, icon toolbar in; T1 and the stack cutover wait for the owner

Checkpoint **2026-11-01 ~19:00 +0800**. Supersedes `HANDOFF-2026-11-01b-v29-linked-t2-holds-cutover-next.md` for what is next.

## State

- **K has not run. No counted step exists.** Nominal shipped stays **0.2.26**, **0.2.44** stays the daily uncounted candidate.
- **`dist/` serves v29** (wasm `e61e5890`), page `022d0cd0`, HTML `ca58f40f` (icon toolbar), shell generation 83 `607b280d`, manifest file `98371d7f`.
- **ddev:** untouched. `litecore` still running and idle. Do not use it without asking.
- Rehearsal stack `litecore-rehearsal` is stopped, its tree at `~/Projects/Nextcloud_Apps/litecore-rehearsal`, unrelated to ddev.
- Results table: `specs/SPEC-M3-v29-tick-pacing.md` section 13.

## Done this session

| Item | Result | Evidence |
|---|---|---|
| Cutover, generation 83 | page only differs from 82 | `v29-177/cutover/`, `freeze-83/` |
| Gap typing | 24/24 | `t3/typing-gap/` |
| Merge | 26/26 x2, control/pair equal, m2-1b, m2-4 | `t3/merge/` |
| T4 | holds x3, after append 3 fixed a clause of mine | `t4/` |
| S4 | holds, six mutations caught | `s4/` |
| F4-83 | 24/24 on the final page | `f4-83/final-page/` |
| F3-83 | `F3_83_EQUAL` single-press; the pinned runner is red on Firefox (finding 178) | `f3-83/` |
| V0'-83 | holds, six stages | `v0/` |
| Icon toolbar | both browsers hold by real pointer | `toolbar-icons/` |
| Own stack | draft spec, rehearsed on a fresh install | `specs/SPEC-M3-own-stack.md`, `wasm_sdk_probe/host-stack/` |

## Next, in order

1. **T1**, once the desk is clean: `bash findings/evidence/v29-177/t1/chain.sh` (about 15 minutes, nothing else may run; it stops itself on a dirty desk). The gate is blocked by the owner's desktop Chrome and zen; never touch them. Read by J-b.2. The `boundaries` commit gate is the owner's open decision (spec section 6).
2. **Stack cutover**, on the owner's word: spec `SPEC-M3-own-stack` section 5, then ST1-ST4. Needs `ddev stop litecore`, a real env file (`litecore.localhost`, port 18443), the `nc-link` step, and the admin password from `.ddev/config.local.yaml`.
3. **Host 0.2.45**, on the new stack: first look at the icon toolbar inside Nextcloud. Then spec section 7 (AS-5, the P arm, `FOREIGN_PHASE`).
4. **The next K spec** must carry: the single-press replacement (finding 178, or K7 goes red for no product reason), the clear wait on the toast, re-binding `htmlSha256`, the C2 gate decision, plus what the earlier handoff listed.

## Cautions that cost time this session

- **A repro you retype is a claim about the procedure, not the procedure.** Mine dropped the one line that held the defect: 720 arms green. Logging inside the real runner showed it on the first run.
- **A conclusion that fits is not one that is proven.** "Not a v29 regression" was committed on the wrong reason, then corrected. State the prediction, then run the experiment that can fail it (`7aca664aa`).
- `web/e2-editor.html` is outside the shell bundle but inside the four-arm identity (`originalHtmlSha256`). Changing it costs an F4 re-run, and V0' must restore it.
- A foreign `cc1plus` (the owner's OxOffice build) refuses browser runs through the runner's own guard. Not a product result; re-run when quiet.
- Print the size of a report before printing the report.

## Section 34.4

- **Fixed-by-execution: 6.** T4's `grows` clause; the toolbar check's start state; V0' restoring the HTML; `repro.py` reading styles; `repro.py` missing the caret and arms; the derivation's replacement counts.
- **Fixed-by-review: 0. Fable rulings: 0.**
- Wrong conclusions, corrected in the evidence: 2 (finding 178).

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English; specs and findings in zh-TW. Linking and compiling `make` stay the owner's. Commit messages: `Co-Authored-By` yes, `Claude-Session` never.
