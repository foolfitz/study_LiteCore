# Second adversarial review of the install-elsewhere protocol (opus, read-only, 2026-09-29)

Scope: only the revisions made after the first review (`review-2026-09-29-opus.md`): the
revised spec, the rewritten `check_m3_install_elsewhere.py` (including the one-exec sampler
loop), `host_binding`'s root-symlink check, the H3 pin, the reinstall `install.json`,
`equivalence.json`, and the shakedowns that appeared while it read. Everything was run in
memory; nothing was written. Counts: REFUTED-CRITERION 4 · SPEC-FACT-WRONG 4 · TOOL-BUG 6 · NIT 5.

**Status when this session stopped (context limit): items 5 and 6(d) are fixed; every other
item is adopted and left for the next session, before any counted run.** No counted run of
this step exists.

| # | item (reviewer's words, condensed) | disposition |
| --- | --- | --- |
| 1 | **I1 is scored on a re-enable, not an install.** `app:remove` left `litecore`'s app config (`enabled: no`, `installed_version: 0.2.1`), so the reinstall's `app:enable` skipped Nextcloud's install path; the from-nothing record survives only inside `shakedown/…223255` and is not scored. | Adopt: `--reinstall` deletes `litecore`'s app config after `app:remove`; I1 requires `before.apps` to have no `litecore` key. Reinstall again (this also re-takes the baseline with the new sampler, item 6c). |
| 2 | **I4-1b is keyed by comm, checks PID 1's direct children only, and its whitelist was taken ~40 min after a first install.** An orphan whose comm is in the baseline set escapes with its subtree. The spec's reason for rejecting a lineage rule ("it would count the whole service tree") is contradicted by the samples: PID 1's descendants are only pid 8 `cat` (plus the control); the service tree hangs under PID 9 (ppid 0). | Adopt: flag any descendant of PID 1 whose pid (plus start time) is not among the baseline's PID-1 descendants; correct the spec sentence (it was my inference from the PID 9 finding, and it is wrong). |
| 3 | **I4-3 proves the event stream alive only at ~+13 s;** a stream that dies later reads as "no events". | Adopt: `poll() is None` before `terminate()`; a second create/rm control just before `window["end"]`, also required in the stream. |
| 4 | **I2-3's limit sentence is refuted by the repo's own measurement:** the 41 MB gz was served in 0.096 s (`m3-assets/runs/2026-09-28T172628+0000.json`, `wire.files[…probe.wasm].gzip`). Catch chance per fetch ≈ 20 % for the largest file, less for the rest; `e2-editor.html` effectively invisible. | Adopt: restate I2-3's reach (statistical over ~80 cold opens, large files only). Decide next session whether to add a php-fpm-faithful control (a large file fetched through the probe app's route inside an excused span). |
| 5 | **Host-entry `--red-cases` crashed on every pre-lock report** (KeyError `attempts`) and `H3-intruder-refused` stayed GREEN on them; the counted `095100Z` and the README's `094839Z` "21/21 red" no longer reproduced. | **Fixed:** the two lock-token cases are skipped (printed as SKIP with the reason) when the report's `intruder.mode` is not `lock-token`; both reports are 21/21 red again, exit 0. Still to do: put `--red-cases` exit codes into the equivalence rows. |
| 6 | Sampler residuals: (a) the ps→find race is fixed for one missing level only; (b) control 1's `lcorphan 6 &` keeps the exec's stdio (that exec took ~4 s and stalled a concurrent exec); (c) the stored baseline was taken with the old per-exec sampler, so "the same sampler as §3.5" is false; (d) every stored shakedown crashed the scorer (2-tuple fds). | (d) **Fixed:** the scorer reads 2-tuple fds. (a) adopt: `find` before `ps` in the loop; (b) adopt: `</dev/null >/dev/null 2>&1`; (c) resolved by item 1's reinstall. |
| 7 | Red-case coverage gaps: no mutation for I2-1 `devLogRead`, the I3-7 runner-sha / red-case-exit / baseUrl-commit / missing-report branches, the I3-8 coverage set, `label`, the install-side I1-2 branches and four of the five self-test drift cases, I0-2 `buildId`; I4-1b "control not seen" and I0-2 git-blob caught only incidentally. | Adopt: one mutation per branch; I3-7 runner-sha and `label` into `STRICT_ONLY`. |
| 8 | **I4-1 does not cover processes rooted in a `docker exec`** (ppid-0 roots: health check, `php occ`, `runc init`); a document process started with `docker exec -d` in the window is unseen, and exec events are filtered out of I4-3. | Adopt as registered (record the ppid-0 roots per sample) and state it in §5. |
| 9 | The event control creates a container from the project-labelled web image (`com.ddev.site-name=litecoreprobe`, compose service `web`); an interrupted create/rm would leave a stopped container that ddev/compose label lookups treat as litecoreprobe's web container. I4-3 watches every container on the host, not only ddev projects. | Adopt: use `ddev/ddev-utilities:latest` (present locally); state that any container activity on the host during the window turns I4-3 red. |
| 10 | The equivalence recording test is weak: `OLD_RECORDING` is a transcription byte-identical to `host_binding`'s dev branch; `NEW_RECORDING` hard-codes `package_record(DEFAULT_DDEV)`. Only `package_record` and `describe()["app"]` discriminate. | Adopt: check the transcribed lines against `git show 9748b714:` text; factor each runner's record step into one callable both sides invoke. |
| 11 | Spec says the scoring functions were never changed; false since §3.4 point 4 changed `check_m3_host_entry.score`. | Adopt: correct the spec (the host-entry equivalence row is meaningful and passes). |
| 12 | `module_shas` misses lazily imported modules (`build_e2_c_shell_bundle`, `validate_e1_c`); `make test-e2-c-static` is bound by nothing. | Adopt (next session chooses: runners record their own module shas at exit, or hash every `tools/*.py`). |
| 13 | NIT: I4-1a exempts a php-fpm-named child of a php-fpm worker (`pcntl_fork`); the scan omits `pcntl_fork`. | Adopt. |
| 14 | NIT: "no subreaper in the container" is inferred, not measured. | Adopt: mark it as inference, or measure it. |
| 15 | NIT: `ps` cut at 80 columns (use `ps -ww`); `/proc/<pid>/stat` field 4 is wrong when comm has a space; `devLogRead` stamped after the read; the sampler's stderr pipe is never drained; an exception in `red_cases_now` crashes `score()`. | Adopt. |
| 16 | NIT: §3.5 still describes one exec per sample (with `d`) without strike-through; "0.509–0.515 s" has no evidence file. | Adopt: strike the old text; cite `shakedown/2026-09-28T231953+0000.json` (max in-window gap 0.515 s). |
| 17 | NIT: `tree_listing` ignores sockets, FIFOs and empty directories. | Adopt. |

Also confirmed by the reviewer: the stored counted host-entry report scores identically under
the tools at `9748b714` and now; the H3 pin is sound for the ruling's scenarios; the ruling's
commit times check out; `shakedown/…230921` was red only because of the instrument.

## Done (2026-09-29, the next session, before any counted run)

Every "Adopt" row above is implemented. Three rows the table left to "next session decides"
(4, 12, 14) went to fable on the owner's authority after a measurement
(`fpm-path-measurement-2026-09-29.md`); the ruling and its thirteen conditions are in
`ruling-2026-09-29-fable-controls.md`. Spec §6 has the revision row.

| # | what was done |
| --- | --- |
| 1 | `install --reinstall` deletes every `litecore` app-config key after `app:remove` (`occ config:app:delete`), records the keys and a read-back (`removedFirst.configDeleted`, `configAfter`); I1-1 now requires `install.before.apps.apps` to have no `litecore`. The app has no migrations, jobs or repair steps (`appinfo/info.xml`). |
| 2 | I4-1b flags any descendant of PID 1 whose (pid, `lstart`, comm) is not among the baseline's PID-1 descendants; `ps` now emits `lstart`. The baseline holds only within one container lifetime, so install and window record `docker inspect … State.StartedAt` and I4-1b is red when they differ. Spec sentence struck and corrected. |
| 3 | `Lifecycle.stop()` records `poll() is None` (`window.lifecycleAlive`, must be true); a second container control `litecore-ctl-events-end` runs just before `window.end` and its `create` must be streamed. |
| 4 | Ruling Q1 C: I2-3's reach restated as statistical (spec §4 I2-3, citing the 0.096 s); new in-window **control 4** over FastCGI in a real `php-fpm: pool www` worker. |
| 5 | (fixed in the earlier session) plus: equivalence rows now carry each side's `--red-cases` exit (`redExit`), compared with the rest of the row. |
| 6 | (a) `find` runs before `ps` in the loop; (b) control 1's orphan has `</dev/null >/dev/null 2>&1`; (c) resolved by the reinstall; (d) fixed earlier. |
| 7 | Every red case now names a substring the added problem must carry, pinning it to its branch. Added: I0-2 buildId and member list; I1-1 re-enable; I1-2 root symlink, file differs, FIFO, getpath at install, clean-reads-dirty, one per self-test drift (7); I2-1 `devLogRead`; I3 no report; I3-7 baseUrl, commit, red-case exit, missing report, runner sha; I3-8 red-case exit, coverage, transcription; `label`; I4-1a php-fpm under a worker; I4-1b baseline name under a new pid, grandchild of PID 1, orphan control not seen, container restarted; I4-1 short baseline; I4-3 end control, dead stream; plus control 4 (7) and the tree binding (5) from the ruling. 45 → 90 cases. |
| 8 | Registered, not gated: `score()["registered"]["execRoots"]` counts every ppid-0 root other than PID 1 per in-window sample; spec §5 says a `docker exec -d` process is unseen by I4-1. |
| 9 | The event control uses `ddev/ddev-utilities:latest`; spec §4 I4-3 states that any container activity on the host during the window turns I4-3 red. |
| 10 | The old side evaluates `OLD_EXPRESSIONS`, and `transcription()` checks each (whitespace-squashed) at its site in `git show 9748b714:` of the three runners; the new side calls `binding_fields` / `package_for` / `Instance.describe`, which the runners now call too. Red first: changing `--short` to `--porcelain` or naming a non-existent PRE made the check false. |
| 11 | Spec §3.3 corrected: host entry's `score` changed (§3.4 point 4); its equivalence rows are meaningful and pass. |
| 12 | Ruling Q3 C (amended): `tree_binding()` at the equivalence check, window start and window end — tree of `wasm_sdk_probe`, last commit touching it, `--untracked-files=all` porcelain (must be empty; a dirty tree refuses a counted run), `sys.version`, `node --version`, `make --version`. `module_shas` kept. |
| 13 | I4-1a also flags a `php-fpm` with two or more `php-fpm` ancestors; `pcntl_fork` added to the registered scan. |
| 14 | Ruling Q2 C: control 4's backgrounded child must be seen under PID 1 in every window; the spec states the measured sentence (two paths), not "no subreaper in the container". |
| 15 | `ps -ww`; ppid from the second field after the last `") "` of `/proc/<pid>/stat` (a holder named `lc sp` read correctly, live); `devLogRead` stamped before the read; the sampler's stderr drained by a thread (last 50 lines kept); `red_cases_now` returns -2 on an exception instead of crashing `score()`. |
| 16 | §3.5's per-exec text struck; the 0.515 s max gap cited to `shakedown/2026-09-28T231953+0000.json`. |
| 17 | `tree_oddities()` names empty directories and non-regular files; `host_binding` and the install record use it; the self-test adds `fifo` and `empty-dir` (eight cases). |
