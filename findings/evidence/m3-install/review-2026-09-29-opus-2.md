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
