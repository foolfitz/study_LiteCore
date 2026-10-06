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
