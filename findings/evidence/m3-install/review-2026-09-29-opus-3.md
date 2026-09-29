# Third adversarial review of the install-elsewhere protocol (opus, read-only, 2026-09-29)

Scope: `git diff 4bddaf8c 5a4bc239` — the implementation of review 2 and of fable's ruling on
control 4 / the subreaper sentence / the tree binding — plus an uncommitted edit that appeared
while it read (the two I3-7 messages now carry their sha and time). The reviewer wrote nothing.
It ran `--strict --red-cases` on `shakedown/2026-09-28T231953+0000.json` (HEAD's file: 74/90,
every non-red line explained by fields that report predates) and on
`shakedown/2026-09-29T003935+0000.json` (working-tree file: 90/90), 17 scorer mutants in memory
against `003935`, ps/btime arithmetic in the container, a host zombie and a zh_TW `ps`.
Counts: TOOL-BUG 2 · REFUTED-CRITERION 2 · SPEC-FACT-WRONG 2 · state 1 · NIT 7 · load 1.

The main session verified items 1 and 4 against the source before acting (subagent diagnoses
are hypotheses until then); both hold.

| # | item (reviewer's words, condensed) | verified | disposition |
| --- | --- | --- | --- |
| 1 | **TOOL-BUG that sinks the counted run.** I4-1b's identity keys on `lstart`; procps prints it as integer `/proc/stat` btime + starttime/HZ; btime is realtime − boottime truncated, its fraction .79; NTP is on, 3 suspends this boot. A forward clock step ≥ 0.21 s between the baseline and the window adds 1 s to every lstart: `(8, …13:50:31, cat)` leaves the baseline and "I4-1b cat (pid 8)" appears in every sample. `webStartedAt` cannot see it. | Yes: `btime 1790117002`; `date − uptime` = 1790117002.80; `btime + 45762911/100` = 13:50:31 +0800 = pid 8's lstart; `suspend_stats/success` 3; `NTP=yes`. | **Fixed.** The loop also prints `cat /proc/[0-9]*/stat`; each row carries field 22 (start, clock ticks since boot) and `identity()` keys on it. Rows without ticks never match rows with them (an old baseline turns a window red, not green). Retaken by reinstall 3. |
| 2 | **REFUTED-CRITERION (latent).** The baseline is taken after `app:remove`, not before the app ever existed (the container has run since 09-28 13:50); an orphan an earlier install or window left under PID 1 is whitelisted at the next `--reinstall`, and the tool's own message says "reinstall to retake it". | By reading; today's baseline is `{(8, cat)}` only. | **Adopted as a per-instance check:** every PID-1 descendant in the baseline must have started within 10 s of PID 1 (in ticks; the sampler records `getconf CLK_TCK` as `install.hz`). |
| 3 | **Branches no red case pins** (each mutant still 90/90): (a) `master[1] != 0`, `master[2] == "php-fpm"`, `via[0] == worker` in `control_label`; (b) `identity()` without start or without comm; (c) deleting `if not bad["control"]: return None` excuses anything inside a span — no case injects a non-control violation inside a span; (d) host entry's I3-5 `instance.app` dirty/commit and I3-8 `runner.sha256`; (e) the recording-error branch, the empty-`webStartedAt` branch. | — | **Adopted:** a case per branch (fake master with ppid 0; worker below `supervisord`; `lcfg` below another php-fpm; cat's ticks +1; cat renamed; a non-control violation inside control 1's span, inside control 4's span, and below control 4's worker; host entry dirty, other commit, unchecked runner; recording error on both sides; empty `webStartedAt`). |
| 4 | **SPEC-FACT-WRONG.** NC 34 `core/Command/App/Enable.php` always calls `Installer::installApp()` (`installAppLastSteps`: migrations, jobs, install repair steps, then `installed_version` and `enabled`); a leftover `installed_version` only adds the pre/post-migration repair steps. The earlier reinstall was already an install; the stated reason is false. | Yes: `Enable.php:93`; `Installer.php:538-550` (`previousVersion` gates pre/post-migration repair steps and `migrate('latest', $previousVersion === '')`, whose second parameter is `$schemaOnly`, `MigrationService.php:385`). | **Spec corrected** (§3.2, append). The config deletion and I1-1's condition are kept with the corrected reason: they put the install on the branch an instance that never had the app takes (it matters once the app has migrations), and make the database state before it a fresh instance's. |
| 5 | **SPEC-FACT-WRONG.** §3.5 and §5 say control 4's excuse lasts "約 5 秒（±1）"; the code excuses start…start+9 ±1 (≈ 11 s), while the FastCGI request returns at ≈ +5.3 s, after which the worker is an ordinary pool worker. | By reading. | **Fixed:** `fpm_control` records `returned`; the worker's fd (and a php-fpm fork of it, item 12) is accounted for only until `returned + 1`. Spec corrected. |
| 6 | I4-2 meets counted load first in the counted run (counted runners also run `make test-e2-c-static`; shakedowns use repeats 1). | Measured: `make test-e2-c-static` takes 2.5 s; the sampler's max gap during it 0.51 s. | **Registered** (spec §4 I4-2): the extra counted load is small; what only the counted run can show is the tail over its length. A red I4-2 there is the criterion working. |
| 7 | **TOOL-BUG.** `positive_controls()` runs before `try:`; if it raises, no `sampler.stop()`, the in-container loop runs forever, no report. | By reading. | **Fixed:** moved inside the `try`. |
| 8 | State: HEAD's constant I3-7 strings make two cases GREEN on any report that already has them; the uncommitted edit fixes it; committing it moves `HEAD:wasm_sdk_probe`, so re-run equivalence before the dev host-entry run. | Yes (the main session had found the same two GREENs on `003935`). | Committed with this batch; equivalence re-run after. |
| 9 | NIT: the old I4-1 **b** was still unstruck; the strike went on a copy. | Yes. | Struck in place. |
| 10 | NIT: condition 8 says "a direct child of PID 1", but the code accepted any control-lineage descendant and never compared `controls.fpm.orphan`. | Yes. | **Fixed:** the orphan controls count only with ppid 1, control 4's only with the reported pid; red cases for each. |
| 11 | NIT: equivalence rows without `redExit` compare equal. | Yes. | **Fixed:** a row missing `redExit` on either side is an I3-8 problem; red case. |
| 12 | NIT: the ≥2-php-fpm-ancestor branch flags the fork child of PHP's `exec()` in control 4 (microseconds). | By reading. | **Fixed:** a `php-fpm` whose parent is control 4's worker, while its request runs, is the control's own; outside the request it is a violation (red case). |
| 13 | NIT: §5 does not name new children of the service tree (supervisord, apache2, mailpit). | — | Named in §5. |
| 14 | NIT: the loop does not pin a locale; under zh_TW `PS_ROW` reads nothing (fails safe through I4-2). | Reviewer ran it. | **Fixed:** `export LC_ALL=C` at the top of the loop. |
| 15 | NIT: I2-3 reads only `/proc/*/fd`, not `cwd`/`maps`/`exe`; non-dumpable processes are skipped silently. | — | Named in §5. |

Also checked by the reviewer, no finding: procps keeps a zombie's comm bare (zombie workers do
not trip I4-1a); `[ \d]\d` handles day-of-month padding; the process and fpm spans were 1.2 s
apart in `003935`, and the fd↔fpm overlap is harmless (fd's rules are I2-3 only); pid 8 `cat`
cannot restart without the container going down (`pre-start.sh`'s `wait` trap runs `kill -- -1`).

Red cases: 90 → 111.
