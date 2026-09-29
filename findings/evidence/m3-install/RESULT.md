# Result: `INSTALLS ELSEWHERE` (2026-09-29)

Counted window report: `runs/2026-09-29T012339+0000.json`. Criteria:
`specs/SPEC-M3-install-elsewhere.md` §4 (I0–I4), last revised after the third adversarial
review and before this run. Scored at run time and again from the stored report
(`--score`: `INSTALLS ELSEWHERE samples=6806 problems=[]`); red cases against it, re-run at
scoring time: **111 of 111 red, 0 skipped, 0 failed**.

**What it means.** M3's completion criterion (roadmap §5.5) holds on a Nextcloud whose `litecore`
app was installed from the release archive, not linked in from the host repo: open an ODT from
Files, edit, save back, versions correct, locks correct — the four counted M3 runners, each
reaching its own counted verdict against that instance — while no process on the web container
became a document server, and nothing read study_LiteCore's `dist/`.

**Two qualifiers travel with the verdict** (spec §4, end):

1. **The instance is not fresh.** It is `litecoreprobe`, the gate-0 probe instance, taken as it
   was (spec §2: the probe app enabled with its Files listeners off, a read-only mount of
   `dist/`, the same `debug`/`loglevel` as the dev instance, `firstrunwizard` off). What keeps
   each difference from deciding the result is I1-3, I1-4, I2-3, I2-4. A truly fresh instance
   needs a new ddev project, which rebuilds the shared router; the owner did not choose it.
2. **"No server-side document process" was measured on the web container's processes and on the
   host's container lifecycle.** A service that was already running before the window and is
   reached over the network is outside it (spec §5); so are processes rooted in a `docker
   exec` (registered, not gated — review 2, item 8).

## The window

01:23:46–02:21:36 UTC (3470.0 s). Before it: the release archive rebuilt
(`849f29f7…`, equal to the record and to both earlier builds); the installed tree read against
the release record (clean) and the binding self-test (clean reads clean; the seven drifts each
named); `app:getpath` = `/var/www/html/nextcloud/apps-extra/litecore`; the dev instance quiet
for 570.9 s; `wasm_sdk_probe/` at tree `d5df1dd3…` (last commit `b30b58b7`), nothing
uncommitted, equal to the equivalence check's and, at the end, still equal.

| clause | what the report holds |
| --- | --- |
| **I0** archive | 30 members = the source commit's tracked files under `appinfo/ lib/ templates/ js/` ∪ `engine/MANIFEST.json` ∪ the manifest's `.gz` files; each tracked member is its git blob, each engine member the host's; `buildId 9076b0b425222c0e`; rebuilt at the window with the same sha256; no link, no `..`. |
| **I1** install | Reinstall 3 (`install.json`): `litecore`'s leftover app config deleted after `app:remove`, so the install ran on the branch a never-installed instance takes (review 3, item 4); `app:enable` exit 0, `litecore 0.2.1 enabled`; the installed tree equals the release both ways, no symlink, no empty directory or special file; `system` config identical across the install; the probe app's switches `off`/`off` at install, window start, window end. |
| **I2-1** dev instance untouched | The dev log's 59 new lines inside the window are all `127.0.0.1 … GET /phpstatus` (≥ ⌊3470/60⌋ − 1 = 56); read 63.8 s after the window. |
| **I2-2** | All four runner reports ran against `https://litecoreprobe.ddev.site:8443`. |
| **I2-3** mount | No process held a file under `/mnt/litecore-dist` in any of the 6,806 samples, except controls 2 and 4, both seen. Reach is statistical (a read shorter than 0.5 s is caught with probability ≈ its length / 0.5). |
| **I2-4** probe app | 47,941 litecoreprobe access-log lines in the window, 2,096 of them engine-route requests; none under `/apps/litecoreprobe/`. |
| **I3-1** assets | `ASSETS DELIVERED`, Chrome 3/3, Firefox 3/3 (`../m3-assets/runs/2026-09-29T012410+0000.json`). |
| **I3-2** versions | `VERSIONS CORRECT`, Chrome 3/3, Firefox 3/3 (`../m3-versions/runs/2026-09-29T012641+0000.json`). |
| **I3-3** locks | `LOCKS LAND`, 22 cells, 52/52 runs (`../m3-locks/runs/2026-09-29T013546+0000.json`). |
| **I3-4** host entry | `LANDS`: Chrome open-save 3/3, conflict 3/3, broken 1/1, broken-no-save 1/1; Firefox open-save 3/3, conflict 3/3; H3 on the lock-token branch (`../m3-host-entry/runs/2026-09-29T013030Z.json`). |
| **I3-5** | All four reports bound to the release (`hostDirty` empty, commit `5e53362…`), made inside the window. |
| **I3-6** | Each runner's red cases all red at run time and again at scoring; report sha256s unchanged. |
| **I3-7** | Host entry on the **dev** instance, counted, `LANDS`, red cases all red, started 18 s after the equivalence check and finished before the window (`../m3-host-entry/runs/2026-09-29T010833Z.json`). |
| **I3-8** | Equivalence (`equivalence.json`): 6/6 earlier counted reports score and red-case the same under the tools at `9748b714` and now; the dev recording path equal old vs new; the old expressions found verbatim in `9748b714`'s runners. Runner and module shas equal at the check, window start and end; tree binding equal at all three. |
| **I4-1** processes | In every sample: nothing below a php-fpm that is not php-fpm, no php-fpm below a worker, no descendant of PID 1 but `(8, 45762911, cat)` — except the controls, each seen within its own span: control 1's `sleep` under a fake php-fpm and its `lcorphan` under PID 1; **control 4 in a real `php-fpm: pool www` worker (pid 54588, request 5.09 s): `lcfg` below it, `lcorphan4` (pid 55353) a direct child of PID 1, the worker holding `e2-editor.html`**. The web container ran one lifetime from the baseline to the window. |
| **I4-2** sampler | 6,806 good samples over 3470 s, no errored sample, no sampler stderr; widest gap 0.535 s (p99 0.513, none above 0.75); php-fpm in every sample. |
| **I4-3** containers | `docker ps -a` the same 25 containers at start and end; the live event stream carried exactly the four control events (`create`/`destroy` of `litecore-ctl-events` and `…-end`) and was alive when stopped. |

**Registered, not gated.** The installed PHP has no program-execution function
(`execFamilyScan` empty, `pcntl_fork` included). Roots with ppid 0 seen in the window
(`registered.execRoots`, by samples): the service tree's `bash -c …start.sh` (6,806), ddev's
health check (6,692), the controls' execs, `runc init` (2), and `php occ status` /
`php occ config:system:get debug` (1 each — the runners' `Instance.describe()`).

## How it got here

Two adversarial reviews and a ruling before the tools were final, and a third review after:
review 1 (19 items), fable's H3 ruling, review 2 (17 items), fable's ruling on control 4 / the
subreaper sentence / the tree binding, review 3 (15 items). Each is in this directory with its
dispositions. The three that changed what a counted run would have said:

- Review 1: "a document server started by the app is a php-fpm descendant" was false — a
  backgrounded process is adopted by PID 1 (I4-1b). The fpm-path measurement later showed it
  happens at once and that I4-1a alone never sees it.
- Review 2: I4-1b keyed on names and PID 1's direct children only; the reinstall had been a
  re-enable of known config.
- Review 3: `lstart` moves with clock steps (btime's fraction was 0.80, NTP on, three suspends
  this boot) — a 0.2 s step would have turned every sample of this hour-long window red. It
  keys on start ticks now.

Shakedowns: `shakedown/` (five windows; the last, `…011402+0000.json`, took `--strict
--red-cases` to 111/111 before this run was started).

## Re-check

    python3 wasm_sdk_probe/tools/check_m3_install_elsewhere.py --score     findings/evidence/m3-install/runs/2026-09-29T012339+0000.json
    python3 wasm_sdk_probe/tools/check_m3_install_elsewhere.py --red-cases findings/evidence/m3-install/runs/2026-09-29T012339+0000.json

Both read only stored reports (the runners' own red cases are re-run in process).
