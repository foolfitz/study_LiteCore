# Finding 112 — evidence

The red run: `../m3-locks/runs/2026-10-06T035016+0000.json`, `runs[13]` (K5 foreign-lock, Chrome 151 headless, 04:15:30–04:16:35 UTC). Its record: reset upload 204, foreign lock 200, login 200 → dashboard, `filesRow` = `{timedOut: true, lastError: null}` after 60 s at `/apps/files/files?dir=/`, then `fatal` (the runner clicked a selector that was not there).

## `apache-access-2026-10-06T0415-0418Z.log`

Copied from `/var/log/apache2/access.log` inside `ddev-litecore-web` (timestamps **+0800**; 12:15:15–12:17:49 +0800 = 04:15:15–04:17:49 UTC), with `docker exec ddev-litecore-web grep -E '06/Oct/2026:12:1(5:(1[5-9]|[2-5][0-9])|6:[0-5][0-9]|7:[0-4][0-9])' /var/log/apache2/access.log`. It is the only record of 2xx responses: the ddev router logs status 300–510 only (`~/.ddev/traefik/.static_config.yaml`, `accessLog.filters.statusCodes`), `docker logs ddev-litecore-web` is empty and nginx's log is 0 bytes.

Line numbers below are 1-based in this file.

- Logins (`POST /login`): lines 36 (12:15:20, run 12), 495 (12:15:32, run 13 — the red run), 730 (12:16:37, run 14).
- Between lines 495 and 730: 234 lines = 217 from Chrome, 6 from the runner's Python, 10 `408` (Apache closing idle keep-alive connections, not requests), 1 `curl /phpstatus` (the container's health check, not through the router). 234 − 10 − 1 = **223**, equal to the router's request-counter gap between the two logins (129299 → 129523). Nothing was lost or in flight between router and backend.
- The red run's Files page (from `GET /apps/files/files` at 12:15:33): 188 requests, all within 12:15:33, among them the host's `apps/litecore/js/litecore-files.mjs`. Then no browser request until run 14's login page.
- The same arm's passing loads (run 12 and run 14, each from its `GET /apps/files/files` to its editor load): 418 requests each. Paths requested by both passes and not by the red run: 123, among them `/dist/files-init.js`, `/dist/files-main.js`, `/dist/files-reference-files.js`, `/dist/core-common.js`, `/dist/core-main.js`, 16 `l10n/zh_TW.js` files (`core`, `files`, `files_lock`, `files_sharing`, …; the red run did request 6 others: `user_status`, `profile`, `files_pdfviewer`, `theming`, `notifications`, `related_resources`), and every `PROPFIND`/`REPORT`. Paths the red run requested that neither pass did: none. (The pass windows include the editor's own load, which is why this count is larger than the 99 in the ruling's reading.)
- `nextcloud.log` (`~/Projects/Nextcloud_Apps/litecore/nextcloud/data/nextcloud.log`) has no entry in 04:15:30–04:16:40 UTC; the neighbours' expected `ConflictingLock` / `Locked` are at 04:15:24/27 and 04:16:41/45. The product route `/apps/litecore/r/e2-editor.html` was not requested in the red run.

Re-derive the comparison: take the Chrome lines (`AppleWebKit` user agent) of each run from its `GET /apps/files/files` onward, strip query strings, and compare the path sets.

## The runner change (m3-locks README rule 5.1) and its proofs

`wasm_sdk_probe/tools/check_m3_locks.py` sha256 `6e6b2fa4…` (pinned, the runner of the red report) → `1d3099a2…`. Instrument only: `open_from_files` records `filesRowSeconds` on every run, and on a row timeout `filesRowDiagnostic` = a DOM summary (`readyState`, title, URL, number of scripts, whether `[data-cy-files-list]` exists, number of `[data-cy-files-list-row]`, body text length and first 400 characters), on Chrome the drained CDP events (`summarize_cdp`, the number of requests, requests with neither a response nor a failure, every Script request), and a base64 PNG screenshot. Each part is kept if another fails. No scoring function changed.

### `scoring-equivalence/`

The pinned runner (`git show 4cf203b9:wasm_sdk_probe/tools/check_m3_locks.py`, run with `PYTHONPATH` at the tools directory) and the changed runner, `--score` and `--red-cases`, on `../m3-locks/runs/2026-10-06T035016+0000.json` and `../m3-locks/runs/2026-10-02T163728+0000.json`: `old-*` and `new-*` are byte-identical in all four pairs, with the same exit codes, and `new-red-cases-2026-10-06T035016+0000.txt` is byte-identical to the committed `../m3-locks/runs/red-cases-on-2026-10-06T035016.txt`. (The 10-02 report re-scores `LOCKS DO NOT LAND` under both runners, on one problem only: its page `fc80050c…` is no longer the bound page `e97d6e03…`. Its stored verdict, written by the runner of its day, is `LOCKS LAND`.)

### `capture-red/` — the capture made red once

`capture_red.py` imports the changed runner, points its evidence directory here, and wraps `open_from_files` so K5 looks for `M3 骨架 測試-absent.odt`, a row that does not exist; `--label shakedown --repeats 1 --arms foreign-lock --browsers chrome,firefox`. Report `shakedown/2026-10-06T052721+0000.json` (runner `1d3099a2…`), red in both browsers as intended, each with a non-empty diagnostic after 60.05 s / 60.04 s:

| | Chrome 151 | Firefox 157 |
|---|---|---|
| DOM | `complete`, 「所有檔案 - 檔案 - Nextcloud」, 67 scripts, files list present, **14 rows** | the same, 14 rows |
| CDP | 352 requests, 0 unanswered, 168 Script requests including `core-main.js` and `files-main.js`; 16 error logs, all ordinary (13 × 409 on `apps/text/session/73/sync`, 3 × 404 on `core/preview`) | — (no CDP on Firefox, by design) |
| screenshot | 106,124 base64 characters | 324,080 |

This is also the reference for reading a real recurrence: a normal Files page here has its list, its rows and its own bundles. The red run of 2026-10-06 04:15 UTC, read from the server, had none of the bundles.
