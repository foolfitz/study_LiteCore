# M3 asset delivery — step 0

What the shipped editor pulls from the server when it is opened from Files in the
`litecore` app, and what it pulls again the next time. Host `litecore` `49cc4ab` (clean),
Nextcloud 34.0.2, Apache + PHP-FPM (ddev), page `e2-editor-app.js` `fbfb59a4…`, profile
`e2-editor-v8`. Nothing in the app, the product or `dist/` was changed by these probes.

## Files

| file | what |
| --- | --- |
| `assets-2026-09-28T155551+0000.json` | `probe_m3_assets.py`: closure, wire pass, browser pass (Chrome 151, Firefox 156; one profile each, **cache on**, two opens) |
| `browser-cache-2026-09-28T155905+0000.json` | `probe_m3_browser_cache.py`, **invalid**: every lab file 404'd (see "Instrument errors") |
| `browser-cache-2026-09-28T160045+0000.json` | same probe, **confounded**: second round in the same document |
| `browser-cache-2026-09-28T160212+0000.json` | same probe, the valid run: second round in a new document, positive controls |

## S0-1. The closure (tool-derived, and matched by the server log)

`probe_m3_assets.closure()` derives it from the sources that decide it: the page's static
module graph from `e2-editor-app.js` (13 files; no dynamic `import()` in any of them), the
one hard-coded `workerUrl`, and that worker's `sdk-manifest.json` — `artifactFiles` plus the
resource packs with `loadAtStartup === true` (the worker's own loader loads only those;
finding 085). Plus `e2-editor.html`, which the host re-wraps.

22 files, **169,617,155 bytes**: `probe.wasm` 115.3 MB, `base-r5….data` 34.2 MB,
`cjk-r5….data` 19.5 MB, everything else 0.6 MB. Declared but never loaded:
`fallback-fonts-r5` (49.1 MB data + metadata).

The server log of the first open lists exactly these paths under the app (plus the host's
own `litecore-editor.js`, `litecore-files.mjs`, and the 303 for the wasm), in both browsers.
`e1-fixtures/` is not requested: with a host present the page returns before its fixture
fetch.

## S0-2. What goes over the wire, and how

Wire pass (logged in, no browser), every closure file through `/apps/litecore/r/…`:

- every file except the wasm is served by PHP (`file_get_contents`, whole file in memory),
  `Cache-Control: no-cache`, **no ETag, no Last-Modified**;
- `.js` is compressed on the way (Apache `mod_deflate` on PHP's `text/javascript`);
  `.data`, `.metadata`, `.json` are not (`application/octet-stream` / `application/json`);
- the wasm is a 303 to the app directory's static file, which Apache serves uncompressed
  (115,297,503 bytes even with `Accept-Encoding: gzip, br, zstd`), `max-age=15778463`
  (no `immutable`: the URL has no `?v=`).

Offline compression of the closure's big files (bytes):

| file | raw | gzip -9 | zstd -19 |
| --- | ---: | ---: | ---: |
| `probe.wasm` | 115,297,503 | 40,990,537 | 30,688,739 |
| `base-r5….data` | 34,178,400 | 7,316,692 | 5,532,633 |
| `cjk-r5….data` | 19,484,784 | 15,553,191 | 12,171,653 |
| `base-r5….metadata` | 181,072 | 19,072 | 16,088 |
| `probe.js` | 143,998 | 36,205 | 33,642 |

The closure is 169.6 MB raw, about 64 MB gzip, about 49 MB zstd.

## S0-3. A second open downloads everything again — both browsers, cache on

Server log, requests under the app, per open (bytes = Apache `%O`, headers included):

| browser | open | app requests | bytes | seconds to host `done` |
| --- | --- | ---: | ---: | ---: |
| Chrome 151 | first | 32 | 169,603,663 | 2.50 |
| Chrome 151 | second | 30 | 169,577,836 | 2.52 |
| Firefox 156 | first | 32 | 169,603,665 | 3.23 |
| Firefox 156 | second | 30 | 169,577,838 | 3.17 |

The second open re-fetches every closure file with a 200 and a full body, **including the
115 MB wasm that Apache sends with `max-age=15778463`**. `probe.js` is fetched 8 times per
open (the worker and each of the 7 pthreads). The seconds do not show the cost: this is a
loopback connection. At 50 Mbit/s, 169.6 MB is about 27 s (derived, not measured).

Every M3 counted run so far used `cold` sessions (cache disabled), so none of them could
have seen this.

## S0-4. X1: which responses the browsers' HTTP caches keep (the valid run, `…160212`)

Lab files in the app's `js/cachetest/` (untracked, removed after the run; the report
records `labRemoved: true`), each fetched as `<file>?v=1`, so Nextcloud's own `.htaccess`
sends `Cache-Control: max-age=15778463, immutable`. Per profile: fetch each file, go to a
new document, fetch each again. "second" = whether the second fetch reached the server.

| file (bytes on the wire) | Chrome, profile on /tmp (14 GB free) | Chrome, profile on /home (88 GB free) | Firefox, /home |
| --- | --- | --- | --- |
| ctrl-1k, ctrl-5m (controls) | cached | cached | cached |
| rand-20m, rand-45m | cached | cached | cached |
| rand-60m | cached | cached | **refetched** |
| rand-80m, rand-100m | cached | cached | **refetched** |
| rand-120m | **refetched** | cached | **refetched** |
| `raw.wasm` = shipped `probe.wasm`, 115.3 MB | **refetched** | cached | **refetched** |
| `enc-gzip.wasm`: 41.0 MB gzip, `Content-Encoding: gzip`, decodes to 115.3 MB | cached | cached | cached |
| `enc-zstd.wasm`: 30.7 MB zstd, `Content-Encoding: zstd`, decodes to 115.3 MB | cached | cached | cached |

Every first fetch was 200 with the right decoded length (the encoded ones decoded to
115,297,503 bytes in the page).

Read:

- **Firefox keeps nothing above a cap between 45 and 60 MB**, and the cap applies to the
  **encoded** size: the 115 MB wasm is never kept as served today, and is kept when sent as
  41 MB of gzip.
- **Chrome's cap follows the free space of the profile's disk** — or its filesystem: `/tmp` is
  **tmpfs** on this machine and `/home` is ext4, so the pair changes both (review item 8): the
  same file is kept with 88 GB free (ext4) and not with 14 GB free (tmpfs). The shipped wasm, as served today, falls on the wrong
  side on the smaller disk. Where exactly the cap sits for a given disk was not measured.
- So the second-open re-download in S0-3 has two causes: the size of the wasm (both
  browsers here — Chrome's step-0 profile was on /tmp) and `no-cache` without a validator
  on everything PHP serves.

Browser defaults as documented upstream (Firefox `browser.cache.disk.max_entry_size`
51200 KiB; Chrome's cache size following free disk) are consistent with this; they were
not read from the browsers' source here.

## Instrument errors (kept, not hidden)

- `…155905`: the lab directory was a new top-level entry of the app repo; `nc-link`
  symlinks each top-level entry into `apps-extra/litecore/` once, so it was never served
  and every file 404'd. The summary line printed `REFETCH` for them — a verdict without its
  payload. The raw statuses in the report showed the 404s. Fixed: lab under `js/` (linked),
  positive controls added, the summary prints the statuses.
- `…160045`: the second round ran in the same document, where a repeated fetch can be
  answered without the HTTP cache. It said Chrome keeps 60 MB and Firefox keeps 45 MB but
  not 60 MB; it could not say anything about reopening the editor. Fixed: a navigation
  before each round. The valid run differs from it only for sizes it did not include.

# After step 0: the packaged host, shakedowns, and finding 105

Spec: `specs/SPEC-M3-asset-delivery.md`. Host commits in `~/Projects/Nextcloud_Apps/litecore`:
`7a11a4b` (serve the packaged engine), `c296d2a` (unlock at beforeunload too; version 0.2.0),
`8075b48` (ETag on every packaged file). Packaged by `wasm_sdk_probe/tools/package_m3_engine.py`:
buildId `9076b0b425222c0e`, 22 files, 169,617,155 → 63,855,360 bytes.

## Shakedowns (`check_m3_assets.py`, `shakedown/`)

| report | host | outcome |
| --- | --- | --- |
| `2026-09-28T161410+0000.json` | `49cc4ab` + an uncommitted tree equal in content to `7a11a4b` (committed after this run), before the redirect fix | Chrome fatal: the Files row was not found before the click (not seen again; the runner now records the Files page when it happens). Firefox passed K0–K2 as then written, but its second open's `LOCK` was 423: the first open's lock had not been released → finding 105. |
| `2026-09-28T161628+0000.json` | same | aborted at setup: the upload was 423 (that lock, still held). |
| `2026-09-28T164501+0000.json` | `c296d2a` | Firefox clean. Chrome K2-3 red: on the second open `sdk-manifest.json` came back 200 with its body. The worker fetches it with `cache: "no-cache"` (shipped `sdk-worker.js:513`); without a validator the revalidation can only resend it. → ETag (`8075b48`), K2-3 rewritten and K1-6 added (spec §7, before any counted run). |
| `2026-09-28T164739+0000.json` | `8075b48` | clean, Chrome 1/1, Firefox 1/1; `--red-cases`: 60 cases, every one red in its own clause. |
| `2026-09-28T172209+0000.json` | `5e53362` (after the review) | clean, Chrome 1/1, Firefox 1/1; address `9076b0b425222c0e-566647db`; the no-cache list derived from the sources is `profiles/e2-editor-v8/sdk-manifest.json`; `--red-cases`: 84 cases, every one red in its own clause. |

In the clean one: first open 25 app rows, 63.9 MB sent (both browsers); second open 303 + the
document + (Chrome only) a 304 for the manifest — about 18 KB; each leave released the lock in
1.3–1.9 s.

The first redirect fix (in the same working tree as `161410`): `linkTo('', 'index.php')` is
`/` with pretty URLs on, so the Location was `//apps/litecore/r/…` — scheme-relative, a browser
would take `apps` for a host. Caught by the first HTTP check, before any browser run.

## Leave-unlock probe (`probe_m3_leave_unlock.py`, `leave-unlock-*.json`) — finding 105

Per run: fresh profile, open from Files, host `done`, optionally the smoke edit, then back to
Files and poll the server's lock for 10 s; a `pagehide` listener added to the page records
whether the event fired and `persisted` into localStorage; the access log gives the UNLOCKs.

| report | host | arms (unlocked within 10 s) |
| --- | --- | --- |
| `…161945` | `49cc4ab` + uncommitted tree equal to `7a11a4b` | Firefox warm edit 0/2, warm none 1/2, cold edit 2/2; Chrome warm edit 2/2, none 2/2 |
| `…162401` | `49cc4ab` (old host, checked out for the A/B, then back) | Firefox warm edit 3/4, warm none 4/4 |
| `…162726` | `7a11a4b` | Firefox warm edit 3/4, warm none 2/4 |
| `…163344` | `7a11a4b` + the fix (then committed as `c296d2a`) | Firefox warm edit 6/6, warm none 6/6, cold edit 6/6; Chrome warm edit 6/6, none 6/6 |
| `…154412` | `369e6ed` (0.2.4), page `fc80050c…`; shakedown of the leave recorder (SPEC-M3-page-honesty §7.8 condition 9) | Firefox warm edit 1/1 (guard `page`), warm none 1/1 (no guard) |
| `…154506` | `369e6ed` (0.2.4), page `fc80050c…`; **condition 9** | Firefox warm edit **12/12** (every leave guarded, reason `page`), warm none **12/12** (none guarded); 0 instrument failures |

`pagehide` fired in every run, always `persisted: false`. Every run that kept the lock has no
UNLOCK in the access log at all. With the fix, 2–4 UNLOCKs arrive per leave. ~~(the beforeunload
pair every time; the pagehide pair not always)~~ — the log has method, status and one-second
time only, so which pair arrived cannot be told (review item 17). `releasedBy` in the printed summary is `None`
because the probe reads the host's record at open, before leaving.

**Condition 9 (`…154506`, 2026-09-29).** The guarded leave — the host asks at `beforeunload`, does not
release there, and only its `pagehide` UNLOCK is left — released the lock within 10 s in 12/12 (lock gone
1.31–1.55 s after the navigation, 2 UNLOCKs in the access log every time); the unguarded control 12/12
(1.38–1.88 s, 2–4 UNLOCKs). `secondsDoneToLeave` 1.47–1.50 s in the edit arm (the smoke edit comes first),
0.14–0.25 s in the none arm. `pagehide` fired every time, `persisted: false`. Before the fix this was the
path that lost the lock 7 times in 13; 0/12 now, 95% upper bound about 26%. Why the pagehide UNLOCK now
arrives when it used to not is not attributed (finding 105).

The first `…161945` attempt died before any run: the probe's stale-lock release sent the bare
uuid from `nc:lock-token`; the header needs `<opaquelocktoken:uuid>` (500 otherwise). Fixed
before the arms ran; the report is the fixed run.

## K4: the release archive (measured, registered, not pass/fail)

Host `8075b48`, engine buildId `9076b0b425222c0e`. What a release would carry (spec §4 K4):

    tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-09-29 00:00Z' \
        -czf litecore-0.2.0.tar.gz litecore/appinfo litecore/lib litecore/templates litecore/js litecore/engine

**63,416,048 bytes (60.5 MiB)**, 47 entries; `engine/` is 63,861,611 bytes of it before tar.
The App Store's source default `MAX_DOWNLOAD_SIZE` is 30 MiB (roadmap §5.3); the live store
has published a 269 MB `richdocumentscode`. zstd for the wasm (about 49 MB for the closure,
step 0) would not bring it under 30 MiB either, so the store question does not depend on the
compression choice. The archive was built in the session scratchpad, not kept.
