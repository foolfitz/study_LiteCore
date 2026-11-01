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

## Addendum (~21:20 +0800): T1 run, the stack cut over, ST2 running detached

This addendum supersedes "Next, in order" above.

**The host moved, on the owner's answer (both A).** ddev's `litecore` is stopped. The site is **`https://litecore.localhost:18443`**, stack `litecore-own` (`wasm_sdk_probe/host-stack/litecore.env`). The tree stays at `~/Projects/Nextcloud_Apps/litecore`, `data/` in place, the same admin password. The database was imported from a dump, `~/Projects/Nextcloud_Apps/litecore-own-state/db-before-cutover.sql` (not in git, sha in `findings/evidence/own-stack/cutover/db-dump-sha256.txt`). **ST1 identical** (`before.json`, `after.json`). Commands: `cd wasm_sdk_probe/host-stack && docker compose --env-file litecore.env up -d`; after a reboot it is down until that runs (`restart: "no"`). Bound tools reach it with `PATH="$PWD/wasm_sdk_probe/host-stack/bin:$PATH"`.

The host still runs **0.2.44** (v28). Rollback: `compose down`, `ddev start litecore`; ddev's volume has the pre-cutover database, so anything written since is not in it.

**ddev labels.** The web image carries ddev's labels and `ddev stop litecore` removed the rehearsal's web container. `compose.yaml` overrides them; `litecore-own-web-1` reads `own-stack`. ST4 still has to show this holds.

**T1** (`findings/evidence/v29-177/t1/`, spec section 14): C2 3 x PASS. `judge_p2`: PASS, then two FAILs, the only line Chrome `boundaries` commit 11.3 and 12.3 ms against <= 10. Firefox 9, 9.7, 8.7. Not a v29 failure by spec section 6. **Open for the owner: re-set the gate for the ordered engine or not.** K6 reads red until then.

**ST2 so far** (`findings/evidence/own-stack/st2/`, shakedowns, unedited runners, the adapter):
- `host_entry` LANDS, `page_honesty` clean, both with every cell 1/1.
- `locks`, `versions`, `same_second`: every cell 1/1, exit 1 on one problem: the runner's page pin. The tree is on v29 (`022d0cd0`), the live host on 0.2.44. Not the stack. Any tree after the cutover reads this.
- `assets`: chrome=0/1 firefox=0/1 firefox-nozstd=0/1 with that same page problem plus `K0-1 manifest`, the v29 profile being in `dist/` and not in the installed package. **Not yet read closely.** Compare with the baseline before calling it the same cause.

**Running detached** (`setsid`, survives this session): `st2/resume.sh`, `new_document`, production UI, Files workflow (ST3), autosave, about an hour. It writes to `st2/log.txt` and ends with `DONE`. Known reds to expect, from the 0.2.44 first contact: `same_second` premise, autosave `as5`. Baselines: `findings/evidence/k-0.2.44/first-contact/`, and for `locks` and `page_honesty` the ddev shakedowns of 2026-10-31 under `findings/evidence/m3-*/shakedown/`.

**Next, in order:**
1. Read ST2 and ST3 against the baselines, cell by cell. Close `assets`.
2. **ST4**: poll the stack while a ddev project starts and stops (`litecoreprobe` is ours, stopped); check `docker ps --filter label=com.ddev.platform=ddev` does not list the stack. Do not touch the owner's other projects.
3. Host **0.2.45** (v29, generation 83, the icon HTML) on the new stack: derive from `findings/evidence/host-0.2.44/`; those scripts gate on `ddev list -j` and `slot.json`, and the slot's reason is gone with ddev. First look at the icon toolbar inside Nextcloud. Owner hand tests: typing, the toolbar.
4. Spec section 7: AS-5, the production P arm, `FOREIGN_PHASE`.
5. The next K spec, after the owner's gate decision: the single-press replacement (finding 178), the clear wait on the toast, re-bind `htmlSha256`, the page pins, `DEFAULT_DDEV`-side URLs through the adapter.

**Cautions added.**
- A runner that waits for "other runners" matches on command lines: start chains from a command line that does not contain `check_m3` or `probe_`. A heredoc in the launching command counts. `new_document` waited 25 minutes for its own parent.
- `desk_gate.py` reads the 1-minute load, which a run's own browsers raise. Use `--wait` between rounds.
- `ddev occ` on an `unhealthy` project restarts it, without asking.
- The rehearsal tree `~/Projects/Nextcloud_Apps/litecore-rehearsal` and its volumes are disposable.
