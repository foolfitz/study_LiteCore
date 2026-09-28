# M3 asset delivery — result

```
$ python3 wasm_sdk_probe/tools/check_m3_assets.py --score findings/evidence/m3-assets/runs/2026-09-28T172628+0000.json
ASSETS DELIVERED chrome=3/3 firefox=3/3 problems=[]
```

**The `litecore` app carries its own engine and delivers it compressed and cacheable**:
K0–K2 of `specs/SPEC-M3-asset-delivery.md` §4, Chrome 151 3/3 and Firefox 156 3/3, counted
run `runs/2026-09-28T172628+0000.json` (17:26:28Z–17:28:53Z).

| binding | value |
| --- | --- |
| host | `litecore` `5e533627d781…` (0.2.1), tree clean |
| engine | buildId `9076b0b425222c0e`, address `9076b0b425222c0e-566647db`, 22 files, 169,617,155 → 63,855,360 bytes |
| page | `e2-editor-app.js` `fbfb59a4…` in `dist/` and `web/` (unchanged); profile `e2-editor-v8` (unchanged) |
| runner | `check_m3_assets.py` `9e97044094f7…` |
| static | `make test-e2-c-static` exit 0 |
| re-scored from the stored report | same verdict |
| `--red-cases` against it | 84 cases — K0 11, K1 24, K2 24 per browser × 2, the static page case — each red in its own clause, exit 0 |
| other ddev projects | `docker ps` before and after identical |
| criteria | last changed in the post-review row of spec §7, before this run; none during it |

## What the six runs show (identical in shape in every run)

| | Chrome (profile on tmpfs, 14 GB free) | Firefox (profile on ext4, 88 GB free) |
| --- | --- | --- |
| first open: bytes sent by the server to the app paths | 63,911,774–63,911,782 | 63,911,765–63,911,771 |
| second open: the same | 18,296–18,309 (303, document, 304 for the manifest) | 17,471–17,480 (303, document) |
| seconds to the host's `done`, first / second open | 2.49–2.51 / 1.87 | 2.90–3.28 / 2.54–2.86 |
| lock gone from the server after leaving | 1.51–1.92 s | 1.34–1.53 s |

Before this step (step 0, same browsers, cache on): 169.6 MB on the first open **and on
every open after it**. The loopback times do not show the difference; the bytes do.

The Chrome 304 is the worker's own `cache: "no-cache"` fetch of `sdk-manifest.json`, the only
path the product revalidates by design (derived from the sources by the runner).

## What this settles

- The app no longer needs study_LiteCore's `dist/`: it reads only `engine/` (K0-4, K1-3(e),
  K1-5's `sourceSha256`, K1-1's gzip bytes that exist only in `engine/`).
- Roadmap §5.3's premise "served directly by the web server, not through PHP" is withdrawn
  (spec §3.3): the directly-served raw wasm was exactly the kind neither browser keeps
  reliably. "Immutable caching" now holds.
- Every `.json`, `.data` and `.metadata` that the Apache allow-list 404'd statically is served
  through the route; the allow-list no longer matters to the engine.

## What it does not settle (spec §5)

Install from the archive into another Nextcloud (not done — owner's decision); nginx and Safari;
PHP-FPM under slow clients and after every address change; Firefox's logout wiping the cache
(`Clear-Site-Data`); Firefox on a small disk; the guarded leave's pagehide-only unlock (finding
105). K3 is below: versions and locks hold on this host; host entry cannot run on any locking host.

## K3: the earlier M3 counted runs, repeated on this host

Run by a sonnet executor from `handoff/tasks/TASK-2026-09-29-assets-K3-rerun.md`; re-scored by
the main session from the stored reports. Host `5e53362`, clean, `make test-e2-c-static` exit 0,
`docker ps` identical before and after.

| runner | report | verdict | red cases |
| --- | --- | --- | --- |
| versions | `../m3-versions/runs/2026-09-28T173014+0000.json` (17:30–17:34Z) | `VERSIONS CORRECT` 3/3 + 3/3 | 68, all red |
| locks | `../m3-locks/runs/2026-09-28T174346+0000.json` (17:43–18:29Z) | `LOCKS LAND`, all 22 cells | 87, all red |
| host entry | none | **not runnable on any locking host** | — |

**Host entry did not run, and that is not this step's regression.** Its last counted run
(2026-09-28 09:51Z) was against host `0dcb745`, which took no lock; locks came in `4bd24e1` /
`49cc4ab`, and the runner was never repeated after that. The access log of the three attempts
shows the mechanism, the same each time: the runner's own HeadlessChrome opens the editor and
takes the token lock (`LOCK` 200, 01:34:26 +0800), saves twice, and the runner then closes the
browser without leaving the page (`check_m3_host_entry.py:275-276`); the lock stays until it
lapses (~306 s), so the runner's next reset upload is 423 (01:34:33) and the runner dies before
writing a report. The executor's reading ("something actively re-locking; an orphaned
geckodriver") was checked and is wrong: that geckodriver (started 2026-09-28 14:03 +0800) has
no browser under it. Its conflict arm (an intruder PUT while the page holds the lock) would be
refused by the lock too.

What host entry checked is now covered by the two runs above on this host — open (both), two
saves chaining with Ctrl+S (versions step 2), a conflict going to a copy (versions step 6,
locks' foreign-lock arms) — except its H5 (the page refusing a broken host), which is page
behaviour and the page is unchanged. Retiring or adapting the host-entry runner is left for
the next session (handoff).

## K4: the release archive

63,416,048 bytes (60.5 MiB), README "K4". Above the App Store's source default of 30 MiB.
