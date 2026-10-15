# 0.2.23 count chain, stop 1 (2026-10-14T23:50:27Z) — same_second shakedown not clean, no counted run started

Chain `../chain-0.2.23.sh` from tree `2e9a433b`, host 0.2.23 `2ccf1a9`, page `ccb67a52…`, started 22:43:43Z (2026-10-15 06:43 Asia/Taipei) with the owner's window and the B3x confirmation in P5 (`chain.txt`, line 1). Preflight P0–P6 ok. Five shakedowns clean (`page_honesty` `VERDICT clean`; `locks`, `versions`, `assets` exit 0; `host_entry` `LANDS`). Shakedown `same_second` (`../../../m3-same-second/shakedown/2026-10-14T234640+0000.json`) **3 of 4 arms passed; `same-second` (R2) on Firefox 0/1** → `STOP`, as the chain is written to. Nothing counted ran. The log directory is `wasm_sdk_probe/build/m3-count-20261014T224305Z/` (copied here: `chain.txt`, `shakedown-same_second.log`).

## The red arm

Read from the report (`runs[2]`, arm `same-second`, browser `firefox`, started 23:48:30Z). Its only red clause is `fatal`; the scored problem is `fatal: urllib.error.URLError: <urlopen error [Errno 111] Connection refused>`.

- The product steps had all completed and been recorded: the open (2.75 s), the twelve presses, `Lb` (`mtime` 1792021770 = 23:49:30Z), `beforeRestore`, the restore (201), `serverAfterRestore` (200, 1,343 B), `Lc` (207).
- The exception was raised by the **harness's own cleanup listing** after `Lc`: `check_m3_same_second.py:162` `server.copies(...)` → `check_m3_locks.py:263` PROPFIND → `ConnectionRefusedError: [Errno 111]`. So the failure lies between 23:49:30Z (`Lb`) and 23:49:58Z (the next arm's start).
- The next arm (R3 Firefox, started 23:49:58Z) passed, so the host was reachable again within that window.

## What refused the connection

Another ddev project, `oxmsp`, was started on the same Docker host at that moment, and ddev recreated the **shared router** that fronts `litecore.ddev.site:8443`:

- `docker events`: the `oxmsp` start sequence (`GetExistingDBType-oxmsp`, `check-available-space`, `start-chown`, image tags `…-oxmsp-built`, `ddev-oxmsp-web`/`-db` recreated) begins at 23:49:37Z; `ddev-router` `rename` + `start` at **23:49:48Z**, `healthy` at 23:49:49Z.
- `docker ps` at the reading (`containers-at-reading.txt`): `ddev-router` created 2026-10-15 07:49:47 +0800, `ddev-oxmsp-web`/`-db` 07:49:41 +0800. The `litecore` containers were not restarted (up since 2026-10-14 11:17 +0800).
- While the router is being replaced nothing listens on 443/8443, which is a refused connection, not an HTTP error. The repo already knew this failure mode: the ruling's P2 precedent cites "another project's `ddev start` makes the router 404 briefly" (memory `nextcloud-work-uses-owner-ddev-scaffold`).
- A second interactive Claude session (`oxoffice-mcp`, started about 06:41 local) was busy on this machine at the time. Not established: which process issued the `ddev start`. Observed: the `oxmsp-stack-*` containers had also been restarted at about 07:16 local.

## Reading (ruling J-a.2, `STOP` row)

**(a) An honest execution accident** (§34.1(a)): the router that carries every request to the host went away for about ten seconds under a step's cleanup, because of a process outside the chain. It is not (b), a product red: every product clause of the arm was recorded and none was red. It is not (c), a judge error: `fatal` is the correct score for an arm the runner could not finish.

What follows, per the table: fix the environment and **run the whole chain again as a new file**. The partial log stays (this directory and the build directory). No runner, judge, chain or product byte changes.

The fix is an agreement, not a check. P5 already holds the owner to "not opening `litecore.ddev.site`"; the re-run's P5 text adds "no `ddev start`/`stop`/`restart`/`poweroff` of any ddev project on this machine during the window". No preflight item is added: an event in the middle of an eight-hour chain cannot be refused before `START`, and AGENTS.md §4 says not to build machinery for it.

## §34.4

Repaired because of execution 0; repaired because of review 0. Nothing was repaired: the remedy is a re-run.
