# Adversarial review of the install-elsewhere protocol (opus, read-only, 2026-09-29)

Reviewed before any counted run: `specs/SPEC-M3-install-elsewhere.md` (first draft plus the
first shakedown's revisions), `build_m3_release.py`, `check_m3_install_elsewhere.py` (sha
`74bbd58c…` at review time), the `host_binding` change in `check_m3_skeleton_open.py`, the
`--ddev-root` changes in the assets / versions / locks runners, and the host-entry runner's "E"
changes. The reviewer mutated the stored shakedown `shakedown/2026-09-28T223255+0000.json` in
memory and called the tool's own `score()`; it ran no ddev, `docker exec` or occ command (one
read-only `docker ps -a`).

The reviewer's report is reproduced as delivered, then the main session's disposition of each
item. Every factual claim the dispositions rely on was re-checked by the main session against
the source first (the three heaviest are marked "checked").

## The report

**Counts:** REFUTED-CRITERION 5 · SPEC-FACT-WRONG 3 · TOOL-BUG 6 · NIT 9.

1. **REFUTED-CRITERION + SPEC-FACT-WRONG — I4-1: daemonized processes and the occ/CLI path
   escape.** A process backgrounded from PHP (`exec('soffice … &')`) is reparented to PID 1
   (`bash /pre-start.sh`), not a php-fpm descendant; app PHP also runs under `php occ` (every
   enabled app's `register()`), which the runners call during the window; a daemon started at
   `app:enable` would live through the whole window with no pre-install baseline. Injecting a
   persistent `soffice.bin` under PID 1, then under `php occ`, added 0 problems. Fix: a baseline
   comm-set rule taken before `app:enable`, plus a second positive control that orphans a
   uniquely named child; correct §3.5 and §5.
2. **SPEC-FACT-WRONG — §2's defence for `/mnt/litecore-dist`.** `dist/` has 117 `*.gz`, 30
   byte-identical to release members (including the base/cjk `.data.gz`), so K1-1's byte check
   cannot tell `engine/` from the mount. Also omitted: the probe app's ungated route
   `/r/{mode}/{path}` (`ProbeController.php:138`) serves the whole mount, including a page
   ending in the runners' ROUTE suffix `/e2-editor.html`. Fix: say the barrier is the source
   (`EditorController.php:297`); sample `/proc/*/fd` for the mount with a positive control; no
   request under the probe app's paths in the window.
3. **REFUTED-CRITERION — I4-2 has no gap bound.** At 2 samples/s a ~49 % blackout passes;
   removing the middle 190 s of the 386 s window added no problem; "half the samples" was GREEN
   and was retuned to a third instead of tightening the criterion. Fix: max gap ≤ 1.0 s.
4. **REFUTED-CRITERION — I4-3 misses container starts.** Name/Image/CreatedAt do not change on
   `docker start`; `oxool-dev` (an OxOOL server) exists, Exited; `docker run --rm` inside the
   window is invisible. The verdict wording does not carry §5's network exclusion. Fix: record
   container lifecycle events; optionally sample the web container's TCP peers.
5. **TOOL-BUG — `host_binding` untested, unbound, blind to two substitutions.** It is the one
   instrument behind I1-2, I3-5 and every counted-run refusal and has never been red on a real
   tree; its module's sha is recorded nowhere; a root that is itself a symlink reads clean
   (`rglob` follows the start path); `occ app:getpath` is not recorded. Fix: an offline
   self-test with byte flip / extra file / symlink / root symlink; record module shas; add
   `is_symlink`; record getpath.
6. **REFUTED-CRITERION — I3-8 cannot turn red for what §3.3 says it shows.** No `score()`
   changed, so re-scoring cannot differ; the changed recording path (dev branch of
   `host_binding`, `package_record(repo, rev)`, `describe()`) is never executed. The old tools
   do run from the archived tree. Fix: run old vs new recording functions on the dev repo.
7. **REFUTED-CRITERION — H3's reason to be kept is not enforced per run.** A failed LOCK
   makes the intruder PUT without `If`, gets 204, the host's tokenless PUT gets 412 → H3 passes
   without the claimed branch; if finding 102 were fixed the intruder would get 423 and H3 would
   go red with a product-looking message. Fix: require intruder 2xx with a token, and both saves
   `(412, withToken)` with `tokenOnServer` true.
8. **TOOL-BUG — runner reports bound by path only;** no sha256, no check that their times fall
   inside the window; the I3-6/I3-7 red-case results are exit codes decided at run time.
9. **TOOL-BUG — strict branches never red before counting** (STRICT_ONLY skips, missing dev
   report, omitted runners, strict verdict strings); `red_cases` needs a clean base. Fix: judge
   each mutation by the problems it adds to a non-clean base, strictly.
10. **TOOL-BUG — the registered exec-family source scan does not exist** although spec §4/§5
    lean on it.
11. **TOOL-BUG — opcache plus the constant MTIME** would keep stale bytecode after a reinstall
    of different bytes. Fix: reload php-fpm after `app:enable`.
12. **TOOL-BUG — spec and tool disagree:** I2-1 "at least one health check" vs "any line";
    I4-1 "its sleep" vs any child; I1-2 "a real directory" checked only at install.
13. **NIT — §3.4 reverses `SPEC-M3-locks-and-permissions.md:94` ("宿主入口的 H3 被 K6 取代")
    without citing it;** the revision table lagged the "2026-09-29 補" additions.
14. **NIT — I2-1 residue after the window:** the dev log is read ~5 s after the window ends.
15. **NIT — I0 limits:** `PARTS` is hand-enumerated (commit 5e53362 also tracks `src/`,
    `package*.json`, `.ddev`); I0-3 is not cross-environment reproducibility.
16. **NIT — the intruder is the same user as the page.**
17. **NIT — positive-control boundary can false-red** (sample `t` is taken before the exec).
18. **NIT — facts stated as observed but not in evidence:** "admin is the only user", "45 ms".
19. **NIT — in-process ODT parsing is invisible to I4 by construction; `run_runner` has no
    timeout; `leave_and_watch` records only the lock** (a failed PROPFIND looks released).

Checked by the reviewer with no finding: the leave step runs after every scored field, so
H-scores are unaffected; the host PUT carries both `If-Match` and `If: (<token>)`; mutagen is
off; no stray `litecore` under `nextcloud/apps/`.

## Disposition (main session)

| # | disposition |
| --- | --- |
| 1 | **Adopted, with a correction measured first.** The service tree is not under PID 1: PID 1 is `bash /pre-start.sh`, while supervisord / php-fpm / apache hang under a separate ppid-0 `bash -c …start.sh` (PID 9) — computed from the shakedown's own samples. So the rule is "a direct child of PID 1 whose name is not among PID 1's children before the install" (I4-1b), not "PID 1's lineage". Baseline: 120 s of samples before unpacking (hence one reinstall, `--reinstall`). Positive control: the fake php-fpm leaves `lcorphan` (a copy of sleep) to PID 1. §3.5 and §5 corrected with the false sentences struck through. Residual stated in §5: a child of our own `occ` calls that lives < 0.5 s and is not orphaned. |
| 2 | **Adopted; checked** (117 `.gz` in `dist/`, 30 identical to release members; `ProbeController.php:138` ungated). §2 corrected. New I2-3 (`find /proc/[0-9]*/fd -lname '*litecore-dist*'` each tick, docker exec runs as uid 1000 like the fpm workers and sees their fds — measured; positive control `lcfd` holding fd 3 on the mount, measured to show) and I2-4 (no request under `/apps/litecoreprobe/` or `/apps-extra/litecoreprobe/` in litecoreprobe's log during the window; non-vacuous by requiring engine-route requests in the same log). |
| 3 | **Adopted.** I4-2: adjacent good samples (and the window's ends) ≤ 1.0 s apart; the shakedown's measured maximum was 0.501 s. Red case: a 1.6 s blackout. |
| 4 | **Adopted, lifecycle part.** A live `docker events` stream of container lifecycle events during the window (a post-hoc query cannot work: the daemon keeps a bounded event buffer and the sampler alone makes about six exec events a second); none allowed except the positive control's `docker create`/`rm` of `litecore-ctl-events`, whose `create` must be streamed. `docker ps -a` now also compares State. **Not adopted:** TCP-peer sampling; instead the verdict carries the qualifier "not a service reached over the network that was already running before the window" (spec §4, §5). |
| 5 | **Adopted.** `host_binding` names "the app directory itself is a symlink"; a self-test on a scratch instance (clean, changed, extra, missing, symlink, root-symlink) runs at every window and is scored (I1-2); `occ app:getpath litecore` recorded at install and window; the sha256 of every `tools/` module loaded is recorded at the equivalence check, window start and window end (I3-8, strict). |
| 6 | **Adopted.** `equivalence` also runs the recording path on the dev instance with the tools at `9748b714` and now, and compares host binding fields, `package_record`, and `describe()["app"]`. |
| 7 | **Adopted, through fable's ruling** (`ruling-2026-09-29-fable-h3.md`). `h3()` pins the arm when the report says `intruder.mode = "lock-token"`; old reports (no mode) score as before, so #6 still holds; a new-runner report without the mode is red. Red cases `H3-intruder-refused`, `H3-lock-died`. The 102-risk in the item is void: the intruder is the page's own user. |
| 8 | **Adopted.** Each runner report's sha256 is recorded when its run ends and checked when scoring; its `startedAt`/`completedAt` must fall inside the window; each runner's red cases are re-run in-process at scoring time in addition to the recorded exit code. |
| 9 | **Adopted.** `--red-cases --strict` judges each mutation by the problems it adds to whatever the report already has; the counted run is preceded by a strict red-case pass on a shakedown with zero SKIP and zero GREEN (spec §4). Runner verdict messages now carry each runner's problems and tally, so a mutation changes the message even on an unclean base. |
| 10 | **Adopted** as registered (not scored): `archive.execFamilyScan` over the installed PHP with comments stripped. |
| 11 | **Not adopted as a check; stated.** This step's reinstall writes byte-identical files, so cached bytecode is the same bytecode; §5 says a build with different bytes needs a php-fpm reload. |
| 12 | **Adopted.** I2-1 needs ≥ ⌊window/60⌋−1 `GET /phpstatus` lines; the I4-1a control must show `sleep`, I4-1b `lcorphan`, I2-3 `lcfd`; I1-2 is re-measured at the window. |
| 13 | **Adopted, through fable's ruling.** `SPEC-M3-locks-and-permissions.md` gets an appended revision row (line 94 untouched); both spec revision tables updated. |
| 14 | **Adopted.** The dev log is read 60 s after the window ends; the scorer checks the read time. |
| 15 | **Adopted as registered:** `archive.excludedTopLevel`; I0-3's scope is stated. |
| 16 | **Stated** (§5); it is also the basis of the H3 ruling. |
| 17 | **Adopted:** control attribution window ±1 s. |
| 18 | **Adopted:** `occ user:list` recorded at the reinstall; each sample records its `docker exec` duration `d`. |
| 19 | **Adopted:** §5 states in-process parsing is invisible to I4; `run_runner` times out after 3 h; `leave_and_watch` records the PROPFIND status. |
