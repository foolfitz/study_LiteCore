# Result: `INSTALLS ELSEWHERE` on 0.2.5 (2026-10-02)

**Browser limitation, first (owner's decision B, 2026-10-02):** dev verdicts on Firefox 156.0, litecoreprobe window on Firefox 157.0 (Chrome 151.0.7922.169 on both); if any window cell is red, the browser difference is an unexcluded explanation. No cell was red. Raw fields (`score.registered.browserVersions` of the window report): the dev baseline's per-run versions are `156.0` for assets, versions and locks and `156.0`, `157.0` for host entry (its second baseline report is the superseded I3-7 run of 15:41:30Z); every litecoreprobe report and the I3-7 dev host entry ran `157.0`; Chrome `151.0.7922.169` everywhere. Firefox was snap-refreshed 156.0 → 157.0 on 2026-10-01 10:42 CST; no existing counted verdict was re-run for it.

Counted window report: `runs/2026-10-02T162328+0000.json`. Criteria: `specs/SPEC-M3-install-elsewhere.md` §4 (I0–I4; I3-8 as revised and I3-9..I3-14 added on 2026-10-02, after two adversarial reviews and before any 0.2.5 window). Scored at run time and again from the stored report (`--score`: `INSTALLS ELSEWHERE samples=7172 problems=[]`); red cases against it, re-run at scoring time: **153 of 153 red, 0 skipped, 0 failed**.

**What it means.** The same as the 0.2.1 result (`RESULT.md`), for host `litecore` 0.2.5 (`7420418`, the zstd release) installed from its release archive by upgrading the 0.2.1 install in place (`install --reinstall --was release-0.2.1.json`): the four counted M3 runners each reach their counted verdict on litecoreprobe, no process on the web container became a document server, nothing read study_LiteCore's `dist/`. The two qualifiers of `RESULT.md` travel with it unchanged (the instance is not fresh; "no server-side document process" is measured on the web container's processes and the host's container lifecycle).

**What the comparison with the dev instance rests on.** Not on re-scoring PRE-era reports (that part of I3-8 was withdrawn; nothing checks it any more), but on a dev baseline selected by rule: the five counted dev-instance reports on `7420418` that started before the equivalence check, all recorded by the runner files that judged litecoreprobe, all reaching their verdicts with their red cases red, their recorded host binding / K0 package / release members / instance description exactly equal to the dev instance's at the check, and nothing under `wasm_sdk_probe/` changed since each ran except the orchestrator (I3-9..I3-11); the window's reports ran the same arms the same number of times on the same test document under the same criteria (I3-12, I3-13), and no other counted dev run happened between the check and the window (I3-14). Named limits: the dev runs' working-tree state was not recorded; libssl3 was upgraded twice after the 2026-09-29 dev reports (bound only from the check on); the browser line above.

## The window

16:23:36–17:24:29 UTC (3653.1 s). Before it: install 14:18:42–14:20:50Z into a web container started 14:16:50Z (one lifetime through the window); equivalence 16:06:54–16:07:01Z at `81856daa`; the I3-7 dev host entry 16:07:07–16:12:21Z; the dev instance quiet for 633.9 s; `wasm_sdk_probe/` at tree `006901fc…` (last commit `81856daa`), nothing uncommitted, equal at the check, the window start and the end, with python, node, make, `OpenSSL 3.5.5 27 Jan 2026` and `libssl3t64` `3.5.5-1ubuntu3.7` (amd64, i386). No apt activity after 2026-10-02 09:24; Firefox stayed at snap revision 8995.

| clause | what the report holds |
| --- | --- |
| **I0** archive | 52 members = the source commit's tracked files under `appinfo/ lib/ templates/ js/` ∪ `engine/MANIFEST.json` ∪ every coding the manifest names (`.gz` and `.zst`); each tracked member its git blob, each engine member the host's; `buildId 7f4f4e2204b4a9ec`; rebuilt at the window to the same sha256 `602fe6bb…`; no link, no `..`. |
| **I1** install | An upgrade: 0.2.1 verified against `release-0.2.1.json`, removed, app config deleted, 0.2.5 enabled (`litecore 0.2.5`); the installed tree equals the release both ways; binding self-test clean reads clean, the seven drifts each named; `app:getpath` = `/var/www/html/nextcloud/apps-extra/litecore`; system config identical across the install; probe switches `off`/`off` at install, window start, window end. |
| **I2-1** | The dev log's 61 new lines inside the window are all `127.0.0.1` health checks; read 63.7 s after the window. |
| **I2-2** | All four runner reports ran against `https://litecoreprobe.ddev.site:8443`. |
| **I2-3** | No process held a file under `/mnt/litecore-dist` in any of the 7,172 samples, except controls 2 and 4, both seen. |
| **I2-4** | 49,749 litecoreprobe access-log lines in the window, 2,402 engine-route requests; none under `/apps/litecoreprobe/`. |
| **I3-1** assets | `ASSETS DELIVERED`, Chrome 3/3, Firefox 3/3, Firefox without zstd 3/3 (`../m3-assets/runs/2026-10-02T162400+0000.json`). |
| **I3-2** versions | `VERSIONS CORRECT`, Chrome 3/3, Firefox 3/3 (`../m3-versions/runs/2026-10-02T162828+0000.json`). |
| **I3-3** locks | `LOCKS LAND`, 22 cells, 52/52 runs (`../m3-locks/runs/2026-10-02T163728+0000.json`). |
| **I3-4** host entry | `LANDS`: Chrome open-save 3/3, conflict 3/3, broken 1/1, broken-no-save 1/1; Firefox open-save 3/3, conflict 3/3 (`../m3-host-entry/runs/2026-10-02T163215Z.json`). |
| **I3-5** | All four reports bound to the release (`hostDirty` empty, commit `7420418…`), made inside the window. |
| **I3-6** | Each runner's red cases all red at run time and again at scoring; report sha256s unchanged. |
| **I3-7** | Host entry on the dev instance, counted, `LANDS`, red cases 23/23, started 6 s after the equivalence check, finished before the window (`../m3-host-entry/runs/2026-10-02T160707Z.json`). |
| **I3-8** | Runner and module shas equal at the check, window start and end; tree binding (now with `openssl`, `libssl`) equal at all three; the check started after the install; the old expressions found verbatim in `9748b714`'s runners. |
| **I3-9..I3-11** | Dev baseline: assets `2026-09-29T163517`, versions `2026-09-29T182723`, locks `2026-09-29T174033`, host entry `2026-09-29T183110Z` and `2026-10-02T154130Z` — the rule's whole selection, each a once-committed blob, re-scored and red-cased at scoring; recording equal to now; changed since its last `wasm_sdk_probe/` commit only in the orchestrator, which no runner imports and nothing under `wasm_sdk_probe/` names (closure and mentions re-derived from git while scoring). |
| **I3-12, I3-13** | Each window report's `criteria`, run shape and test document (`original.sha256` `3b6db004…`) equal its dev baseline's; the I3-7 report's too. |
| **I3-14** | The only counted dev-instance run between the check and the window is the I3-7 report passed in. |
| **I4-1** | In every sample: nothing below a php-fpm that is not php-fpm, no php-fpm below a worker, no descendant of PID 1 but `(8, 4976392, cat)` — except the controls, each seen within its span (control 4: real worker 16901, request 5.09 s, `lcfg` below it, `lcorphan4` pid 17923 a direct child of PID 1, the worker holding `e2-editor.html`). |
| **I4-2** | 7,172 good samples over 3653 s; widest gap 0.550 s (p99 0.513, none above 0.75); php-fpm in every sample. |
| **I4-3** | `docker ps -a` the same 25 containers at start and end; the stream carried exactly the four control events and was alive when stopped. |

**Registered, not gated.** `execFamilyScan` empty. Roots with ppid 0 (`registered.execRoots`, by samples): the service tree's `bash -c …start.sh` (7,172), the health check (7,052), the controls' execs, `runc init` (5), `php occ status` (2) and `php occ config:system:get debug` (1). PRE-vs-now recording differences in `equivalence.json` (`recording.preDifferences`): 88, all `zst*` fields.

## How it got here

`README.md`, section "0.2.5 (J, 2026-10-02)": the failed I3-8, two adversarial reviews (`review-2026-10-02-opus-i3-8-prime.md`, `review-2026-10-02-opus-i3-9-12.md`), the owner's decision B, runs made under the first new tool and superseded, and the shakedown that took `--strict --red-cases` to 153/153 before this run.

## Re-check

This verdict is bound to the tools of its day, as the 0.2.1 one is (see the correction at the end of `RESULT.md`). From the repo root, in a worktree at the commit that added this file (its `wasm_sdk_probe/` is that of `81856daa`, the window's tool commit):

    C=$(git log --diff-filter=A --format=%H -- findings/evidence/m3-install/RESULT-0.2.5.md)
    git worktree add --detach ../m3-install-0.2.5 "$C"
    ln -s "$PWD/wasm_sdk_probe/dist" ../m3-install-0.2.5/wasm_sdk_probe/dist
    cd ../m3-install-0.2.5
    python3 wasm_sdk_probe/tools/check_m3_install_elsewhere.py --score     findings/evidence/m3-install/runs/2026-10-02T162328+0000.json
    python3 wasm_sdk_probe/tools/check_m3_install_elsewhere.py --red-cases findings/evidence/m3-install/runs/2026-10-02T162328+0000.json

Both read stored reports and git only (the runners' own red cases are re-run in process).
