# M3: the release archive, installed into another Nextcloud

Criteria: `specs/SPEC-M3-install-elsewhere.md` §4 (I0–I4), written before any tool or run.
Tools: `wasm_sdk_probe/tools/build_m3_release.py` (the archive) and
`wasm_sdk_probe/tools/check_m3_install_elsewhere.py` (install, equivalence, the window, scoring).

The instance is `litecoreprobe` (`~/Projects/Nextcloud_Apps/litecoreprobe`,
`https://litecoreprobe.ddev.site:8443`), taken as it was: Nextcloud 34.0.2 tarball, apache-fpm,
PHP 8.4, `admin` only, the gate-0 probe app enabled with its Files listeners switched off, a
read-only bind mount of study_LiteCore's `dist/` at `/mnt/litecore-dist`. It is **not a fresh
install** — spec §2 lists each difference and what keeps it from deciding a result. The owner
chose this instance on 2026-09-29 over a new ddev project (which would rebuild the shared router).

## Files

| file | what |
| --- | --- |
| `release.json` | The release record: source commit `5e53362…`, archive sha256 and bytes, the second build's sha256, every member's sha256. Runners bind an installed tree to this list (`check_m3_skeleton_open.host_binding`). The archive itself is `wasm_sdk_probe/build/release/litecore-0.2.1.tar.gz`, not in git. |
| `install.json` | The install on litecoreprobe (the **reinstall**, see below): `occ app:list`, `config:list system`, `config:list` (all apps), `user:list` and the probe app's two switches before and after; 120 s of process samples taken before unpacking (I4-1b's baseline); `app:enable` output; `app:getpath`; the installed tree (every file, every symlink). |
| `review-2026-09-29-opus.md` | The adversarial review (19 items) and the main session's disposition of each. |
| `ruling-2026-09-29-fable-h3.md` | fable's ruling (on the owner's authority) to keep host entry's H3, its fact check and conditions. |
| `review-2026-09-29-opus-2.md` | The second adversarial review (17 items), its dispositions, and (appended) what was done with each. |
| `review-2026-09-29-opus-3.md` | The third adversarial review (15 items): `lstart` moves with clock steps (I4-1b now keys on start ticks), the baseline could whitelist an earlier orphan, unpinned branches; verification and disposition of each. |
| `fpm-path-measurement-2026-09-29.md` | One-off: a real php-fpm worker driven over FastCGI; its background child lands on PID 1 at once and inherits the worker's open file. |
| `ruling-2026-09-29-fable-controls.md` | fable's ruling (on the owner's authority) on review 2's items 4, 12, 14: control 4, the subreaper sentence, the tree binding; thirteen conditions and where each landed. |
| `equivalence.json` | Every counted report of the four runners that existed at `9748b714`, scored and red-cased by the runners at `9748b714` and by the runners now; the dev-instance recording path old vs new, the old side's expressions found verbatim in `9748b714`'s runners; the tree binding of `wasm_sdk_probe/` (I3-8). |
| `shakedown/` | Window runs with `--label shakedown` (fewer repeats, locks on a subset of arms). |
| `runs/` | Counted window runs. |

## Reproduce

    python3 wasm_sdk_probe/tools/build_m3_release.py                  # archive + release.json
    python3 wasm_sdk_probe/tools/check_m3_install_elsewhere.py install [--reinstall]
    python3 wasm_sdk_probe/tools/check_m3_install_elsewhere.py equivalence
    python3 wasm_sdk_probe/tools/check_m3_host_entry.py --label counted          # on the dev instance (I3-7)
    python3 wasm_sdk_probe/tools/check_m3_install_elsewhere.py run --label counted \
        --dev-host-entry findings/evidence/m3-host-entry/runs/<that report>.json
    python3 wasm_sdk_probe/tools/check_m3_install_elsewhere.py --score  findings/evidence/m3-install/runs/<report>.json
    python3 wasm_sdk_probe/tools/check_m3_install_elsewhere.py --red-cases findings/evidence/m3-install/runs/<report>.json
    python3 wasm_sdk_probe/tools/check_m3_install_elsewhere.py --strict --red-cases findings/evidence/m3-install/shakedown/<r>.json

`run` executes the four runners one after another with `--ddev-root` pointing at litecoreprobe
(assets, versions, host entry, locks), each writing its own report into its own evidence
directory; the window report points at them by path.

## Install (2026-09-29, before any window run)

**First install** (06:2x +0800): `app:enable litecore` exit 0 (`litecore 0.2.1 enabled`); 30 files, no
symlink; `config:list system` identical before and after; the only app config that changed is
`litecore`'s own, created from nothing (`enabled`, `installed_version`, `types`); probe switches
`off`/`off` before and after. Its `install.json` was later overwritten by the reinstall; the
record survives verbatim inside the first shakedown report
(`shakedown/2026-09-28T223255+0000.json`, key `install`).

**Reinstall** (after the review, for I4-1b's pre-install baseline): the tool first checked the
installed tree against the release record (clean), then `occ app:remove litecore` (exit 0,
`Removed app 'litecore' (version 0.2.1)`, directory gone), sampled the web container for 120 s
(240 good samples, no error; PID 1's children: only `cat`), unpacked and enabled: exit 0,
`app:getpath` = `/var/www/html/nextcloud/apps-extra/litecore`, 30 files, no symlink, `system`
config identical, users `admin` only. **`app:remove` left `litecore`'s app config behind**
(`enabled: no`, `installed_version: 0.2.1`), so the reinstall's `app:enable` enabled a known
version rather than installing a new one; the first install above is the from-nothing one.
The bytes are identical to the first install's (same archive sha256).

**Reinstall 2** (after review 2, item 1; tool at `5a4bc239`): tree checked clean against the
release, `occ app:remove litecore` (exit 0, `Removed app 'litecore' (version 0.2.1)`), then
each of `litecore`'s app-config keys deleted (`enabled`, `installed_version`, `types`, each exit
0; read back `{}`). `install.before.apps` has no `litecore`; after `app:enable` (exit 0,
`litecore 0.2.1 enabled`) the three keys exist again, created from nothing — the same record as
the first install's. Baseline: 236 good samples over 120 s with the one-exec sampler (`lstart`
per row), no error; PID 1's descendants: only `(8, Mon Sep 28 13:50:31 2026, cat)`. Web
container `StartedAt 2026-09-28T05:50:31.655867945Z`. 30 files equal to the release, no
symlink, no empty directory or special file; `app:getpath` =
`/var/www/html/nextcloud/apps-extra/litecore`; `system` config identical; users `admin` only;
probe switches `off`/`off`; the only app config that differs across the install is `litecore`'s.

**Reinstall 3** (after review 3; tool at `b30b58b7`), the one `install.json` now holds and the
counted window binds to: the same steps and the same outcome as reinstall 2 (three config keys
deleted, read back `{}`; no `litecore` config before; `litecore 0.2.1 enabled`; 30 files equal
to the release; `system` identical), plus the start ticks review 3 asked for: `hz` 100, 236
good samples, PID 1's descendants only `(8, 45762911, cat)` — 0.22 s after PID 1, so nothing
in the baseline started after the container. Equivalence re-run after it: 6/6 score and
red-case the same, recording paths equal, old expressions found in `9748b714`, tree clean.

## Shakedowns

**`shakedown/2026-09-28T223255+0000.json`** (the first window; runners at 1 repeat, locks on
`hold,foreign-lock,broken-then-written`). All four runners clean on litecoreprobe; 773 good
samples over a 386 s window, the positive control seen, no other process under php-fpm. Red on
three clauses, none of them the product:

- **I2-1**: two lines `172.24.0.5 - - [29/Sep/2026:06:33:13 +0800] "-" 408 0 "-" "-"` in the
  dev instance's log inside the window. The dev instance's last real request was the host-entry
  shakedown's final reset (06:32:33–34, `Python-urllib`), exactly 40 s earlier: Apache's
  `mod_reqtimeout` (`header=20-40`) closing backend connections the router had opened and not
  used. Debris of the run before the window, landing inside it. The criterion is right to call
  it red; the change is to the window's start, not the criterion: `run` now waits until the dev
  instance's last non-loopback request is ≥ 60 s old and records the wait (`window.devQuiet`;
  spec §4 I2-1, revision of 2026-09-29).
- **I3-6** locks: its red cases need arms this shakedown did not run (`MISSING unlock-refused …`).
- **I3-7**: the dev host-entry report passed in was a shakedown and was scored strictly; the
  scorer now scores it in the window report's own mode.

Also seen on the dev instance, from the adapted host-entry runner
(`../m3-host-entry/shakedown/2026-09-28T223038Z.json`, 1 repeat): every arm clean; the
conflict intruder's token PUT 204, then both of the page's saves `(412, tokenOnServer true)`;
every arm's leave ended with `nc:lock` empty; no stale lock at any reset.

**`shakedown/2026-09-29T003935+0000.json`** (tool at `5a4bc239`, after review 2 and the ruling;
reinstall 2's baseline; equivalence at 00:39Z; runners at 1 repeat, locks on
`hold,foreign-lock,broken-then-written`; dev host entry = the older dev shakedown
`../m3-host-entry/shakedown/2026-09-28T230636Z.json`). Red on two clauses, both expected: I3-6
locks (its red cases need arms not run) and I3-7 (that dev report predates the equivalence
check). Everything new worked: 776 good samples over 395.4 s, widest gap 0.533 s, no sampler
error or stderr; all four controls seen — control 4's worker (pid 38723) holding
`e2-editor.html`, `lcfg` below it, `lcorphan4` under PID 1 — both container controls streamed,
the stream alive at stop; no probe-app request; the dev log had 7 lines, all health checks;
`execFamilyScan` empty; tree binding equal at start and end. `--strict --red-cases`: 88/90,
the two GREEN being I3-7 cases whose messages were constant strings that the old dev report
already produced; with the sha and time in the message, 90/90. Review 3 then found that
`lstart` moves with clock steps, among others; this shakedown's rows have no start ticks, so it
cannot score against reinstall 3's baseline.

## Counted run: rules fixed before it started

The four rules of `../m3-locks/README.md` ("Counted run: rules fixed before it started") apply
to the window run as a whole, and to the dev host-entry counted run. In addition: nothing is
run against the dev instance between the start of `run` and its end, and the dev host-entry
counted run is finished before `run` is started.
