# Adversarial review, 2026-09-29 (opus, read-only)

Reviewed: `specs/SPEC-M3-asset-delivery.md` (as of `d60f9c50`), host `49cc4ab..8075b48`,
`package_m3_engine.py`, `probe_m3_assets.py`, `check_m3_assets.py`, `probe_m3_leave_unlock.py`,
`probe_m3_browser_cache.py`, finding 105, this directory's README and JSON reports. The review
text below is the reviewer's, unedited; the disposition is at the end.

## SUMMARY

1. **HEAVY** — The buildId covers the decoded file bodies only. The headers the engine files are cached with (worker CSP, COEP, Content-Type) are not in it, so a host change to `serve()` never reaches warm browsers for up to a year.
2. **MEDIUM** — Finding 105's mechanism reading "新宿主（引擎全部從快取來）" is wrong: every failing run was a first open with an empty cache; the engine came from the network. The planned minimal repro likely omits the trigger.
3. **MEDIUM** — 105's statistics overclaim: "new host makes it more frequent" is p=0.038 only when pooling three instruments (p=0.11 within one); old host 9/10 includes one unrecorded UNLOCK; "30/30" includes 18 runs from arms that never failed — the failing arm is 12/12 (95% upper bound ≈26%).
4. **MEDIUM** — Nextcloud's logout sends `Clear-Site-Data: "cache","storage"` to every non-Chrome browser over HTTPS: Firefox users lose the engine cache at every logout. Not in §5.
5. **MEDIUM** — The rewritten K2-3 accepts a 304 for all 21 assets, so nothing checks that `immutable` is honoured any more; the second open also ignores 4xx on app paths and 200s under another build id (demonstrated in memory).
6. **MEDIUM** — K2-5 reads the host's self-reported `state` at open; `verified` is recorded but not required; a lock value of `None` counts as released. "Released on leave" and "never locked" are indistinguishable.
7. **MEDIUM** — The guarded leave (stranded / save in flight) still unlocks only at `pagehide` — the configuration that failed 7/13 in Firefox warm — and is not measured.
8. **MEDIUM** — Cache-cap evidence is confounded/thin: `/tmp` is tmpfs on this host, so the Chrome pair (14 GB vs 88 GB) also changes filesystem type; all K2 Chrome runs have their profile on tmpfs; Firefox measured only at 88 GB free, and its per-entry limit may also scale with free space (from memory; verify). No guard warns if the wasm .gz grows past ~45 MB.
9. **MEDIUM** — §3.3 asserts unmeasured costs: "same kind of cost as WebDAV" ignores that every buildId change makes every user's next open pull 63.9 MB through PHP (≈3 concurrent big streams per open, can exhaust PHP-FPM); "static wasm cannot be cached" was measured on Apache only; "一年" is the max-age ceiling, not observed retention.
10. **LIGHT** — "App reads only its own files" does not cover `e2-editor.html` (K1-1 skips it, K1-5 checks headers only); the old dist mount is still present, so a regression reading it would pass K0–K2. Code is fine today.
11. **LIGHT** — After an upgrade, any request under the old buildId is a bare 404 (reload, history, session restore; Chrome crash-restart in an old tab always fails because the worker revalidates the manifest).
12. **LIGHT** — The 3 s "stayed" check marks the lock `lost` during any navigation slower than 3 s; a hidden tab at 3 s stays `released` with no notice; a save in that window goes without the token and ends in a copy (no data loss).
13. **LIGHT** — Access-log instrument: unparsed lines are silently dropped by the runner (fail-open for K2-3); the UA filter is a substring; `%O` is Apache→router bytes; K2-2's 4096 B slack cannot see 3 of 21 files (measured headers 875–930 B).
14. **LIGHT** — Route is safe (checked). Side notes: K1-3(c) tests Apache's dot-segment normalisation, not the controller; on nginx, `engine/*.gz` and `MANIFEST.json` would be served statically without login; the MANIFEST ships a local absolute path.
15. **LIGHT** — PHP claims hold (checked streaming, 304, HEAD, Range). Minor: a missing manifest-listed `.gz` 404s with immutable headers; the engine swap in `package_m3_engine.py` is not atomic.
16. **LIGHT** — The §3.6 version-bump rule relies on memory; a cheap check could enforce it.
17. **LIGHT** — Labels/inferences: runs 161410 and 161945 were on `49cc4ab` with a dirty tree equal in content to `7a11a4b`; "the beforeunload pair arrives every time" is not attributable from the log; "the host called fetch twice" is inferred from a different listener firing.

Checked and fine: controller reads nothing outside `engine/`; manifest lookup is exact-key; per-representation ETag + Vary correct, no cross-representation 304; stale-token UNLOCK neither releases nor moves the ETag; If-Match still protects data after the beforeunload release and "releasing moved the ETag" is correct; "not bfcache" supported; session closed before streaming; closure regex fits current files; excluding `fallback-fonts-r5` safe for v8; README/finding tallies match the JSON; the 60 red cases re-run 60/60 red.

## Details

### 1. HEAVY: the immutable cache stores the headers too, and the buildId does not cover them

`EditorController.php:195-196` ("The address carries the build id: these bytes never change under it" → `cacheFor(31536000, false, true)`); `:202-210` add a worker CSP and, for `.js`, `COEP: require-corp`; `:175-180` Content-Type. `package_m3_engine.py:42-45`: buildId = `sha256({path: decoded sha256})[:16]` — nothing about how files are served. A cached response is body plus headers; for a worker script the CSP/COEP of the cached response are the ones that apply. Scenario: host 0.3.0 changes the worker CSP (e.g. `worker-src blob:`) or COEP; the buildId stays the same; Firefox never contacts the server for these URLs again (the shakedown's second open has none), Chrome revalidates only the manifest; `sdk-worker.js`/`probe.js` keep the 0.2.0 headers for up to a year in every warm profile. Every K run uses a fresh profile, so no criterion can see it. §3.6 covers only the host JS. Fix: put a serving-policy version (or a hash of the controller's header table, or the app version) into the address.

### 2. MEDIUM: finding 105's mechanism reading contradicts the probe design

`findings/105-…md:43`; `probe_m3_leave_unlock.py:83-86` start a new profile every run, open once, leave once; the shakedown case was the first open of a fresh profile. In every failing run the engine came over the network with the cache on. What separates the hosts is how much gets *written* into the cache: under the new host all 64 MB are cacheable and immutable; under the old host the 115 MB wasm is over Firefox's cap and not stored. The planned minimal repro (`:58`) should include a big cacheable download just before leaving.

### 3. MEDIUM: 105's statistics

Counts match the README and finding tables. Old host 9/10 includes step 0's second Firefox leave, whose UNLOCK was never recorded (`probe_m3_assets.summarize` keeps only `/litecore/` rows); only the second open's LOCK 200 proves the *first* leave — evidenced 8/9. One-sided Fisher: 1/10 vs 7/13 p=0.038 (three instruments pooled); same probe only 1/8 vs 6/12 p=0.11; dropping the unevidenced run 1/9 vs 7/13 p=0.052; 95% CI for the old rate 0.3–45%. "30/30": 18 of those are Firefox cold and Chrome, already 6/6 before the fix; the failing arm is 12/12 (vs 6/13 before, p=0.0036 — the fix clearly helps); Clopper-Pearson upper bound for 0/12 ≈26%, so a residual rate at the old host's ~10% is not excluded. The counted K2 run adds only 6 Firefox leaves.

### 4. MEDIUM: Firefox's cache is wiped at every logout

`nextcloud/core/Controller/LoginController.php:95-101`: HTTPS and a non-Chrome UA → logout adds `Clear-Site-Data: "cache", "storage"`. A Firefox user who logs out re-downloads 63.9 MB through PHP on the next open; Chrome/Edge are exempt. No K2 run logs out. §5 says only "瀏覽器快取可以被清掉、被逐出". It also weakens §3.3's "一年".

### 5. MEDIUM: rewritten K2-3 looser than the forcing case needed; the two opens checked unevenly

`check_m3_assets.py:369-376` accepts any 304 under the build prefix; the forcing case was one file fetched with `cache:"no-cache"` (`sdk-worker.js:513`). (A) 21 appended 304 rows on the second open → `score_run` returns `[]`: "immutable is honoured" is no longer tested (not a byte loosening, but a round-trip/PHP one). (D) a second-open 404 on `/apps-extra/litecore/js/missing.js` plus a host-JS re-download → `[]` (the 4xx and "neither entry nor this build" checks at `:357-364` run on the first open only). (E) a second-open 200 for the 41 MB wasm under another build id → `[]`. Fix: allow a 304 only for paths the product fetches with `cache: "no-cache"`, derived from source like `closure()`; apply the first-open checks to the second open too.

### 6. MEDIUM: K2-5 depends on host self-report and treats "no signal" as "released"

`:345-347` require `host.lock.state == "held"` and `status == 200` — host conclusions. `takeLock` sets `held` even when `verified` is `null` (PROPFIND failed) (`litecore-editor.js:155-161`); `verified: true` is in the reports but not required. `server_lock` (`:247-250`) returns `None` when `<nc:lock>` is absent; the loop (`:261`) and scorer (`:349`) treat anything other than `"1"` as released. (B) `leave=[{lock: None}]` with `verified=None` scores `[]`. Fix: runner PROPFIND after `done` requiring `"1"`; require `""` exactly after leaving; require `verified is True`.

### 7. MEDIUM: the guarded leave still unlocks only at pagehide

`litecore-editor.js:227-233`: with `stranded || inFlight > 0` the handler returns before `release`; only `pagehide` (`:244`) unlocks — the configuration that failed 7/13 in Firefox warm. Scenario: a save fails, content stranded, the user downloads it, confirms the leave prompt; in about half of Firefox cases the lock stays ~306 s; reopening gets 423 and copy mode. Not exercised (K3 locks runner has the cache off; K2 never strands). Finding 105 should state this residual.

### 8. MEDIUM: cache-cap evidence confounded or thin

`/tmp` is tmpfs (`findmnt /tmp`), `/home` on nvme: the X1 Chrome pair changes filesystem type and free space together; all K2 Chrome profiles are `tempfile.mkdtemp` → tmpfs (`check_m3_assets.py:301`). Firefox measured only at 88 GB free; from memory (verify): cache2 `EntryIsTooBig` also limits an entry to 1/8 of disk-cache capacity, and smart sizing scales capacity with free space — if so the 40.9 MB `.gz` may not be kept by Firefox on a small disk; §5 lists only Chrome as unmeasured. Margin: 40,878,530 bytes vs measured-kept 45 MB; ~10% growth of the wasm would silently remove the Firefox benefit; no packager warning.

### 9. MEDIUM: §3.3 costs asserted rather than measured

"WebDAV downloads already go through PHP, same kind of cost" (spec:69-71): this cost is per browser per buildId — every engine update makes every user's next open pull 63.9 MB through PHP, ≈3 concurrent large streams per open, each holding an FPM worker for the whole transfer (`output_buffering=0`, `.user.ini:9`); a handful of slow clients can exhaust `pm.max_children`. "Static raw wasm cannot be cached" measured on Apache; from memory (verify): Nextcloud's documented nginx config lists `application/wasm` in `gzip_types`. The lab's Content-Encoding came from an app `.htaccess` (acknowledged Apache-only). "一年" is a ceiling. The strongest reason for PHP — scripts need COEP (E1) — is only mentioned in passing.

### 10. LIGHT: "reads only its own files" misses the editor document

§5 (`spec:162-163`); K1-1 skips the document (`check_m3_assets.py:158`, `:191`), K1-5 checks only headers (`:228-235`); `editor()` does read the packed copy (`EditorController.php:103`), but with `/mnt/litecore-dist` still mounted a regression reading it would pass. Cheap fix: compare the document's initial-state `editor.sourceSha256` (`:112`) with the MANIFEST sha of `e2-editor.html`.

### 11. LIGHT: old-build URLs after an upgrade

`EditorController.php:89` 404s any non-current build id: reload/history/session restore of an old document URL shows a bare 404; in an old tab the SDK's crash-restart re-creates the worker at the old URL, Chrome revalidates the `no-cache` manifest, gets 404, recovery fails every time (Firefox recovers from cache). Suggestion: unknown build id + `e2-editor.html` → 303 to the current build.

### 12. LIGHT: the 3 s "stayed" timer (`litecore-editor.js:238-242`)

The old document stays alive until the new response commits, so any navigation slower than 3 s flips the state to `lost` and shows the notice while leaving. The check runs once; hidden at 3 s → stays `released` with no notice. A save in the window goes without the token (`:212`), 412 or 423, ends as a copy. Data safe; UX says the wrong thing.

### 13. LIGHT: the access-log instrument

Unparsed lines (`probe_m3_assets.py:197-199`) have no agent, so the runner's filter (`check_m3_assets.py:315-317`) drops them silently (the step-0 probe kept them) — fail-open for K2-3. UA filter is a substring ("Chrome"/"Firefox"): another Chrome on the instance would mix in (mostly fail-safe, except K2-1's set equality). `%O` counts Apache→router bytes (equivalent here). K2-2: headers measured 875–930 B, so 4096 B slack cannot see an uncompressed `state-machine.js`, `recovery-notice.js` or cjk metadata; works for the other 18 and the wasm.

### 14. LIGHT: route security (checked; safe)

URL path used only for exact `isset($engine['files'][...])` (`EditorController.php:89`); traversal, `%2e%2e`, double-decoding, NUL, numeric keys cannot reach `packed()`; `find engine -type l` empty; packager cannot emit `..` (pops from empty list raise); an absolute artifact path is silently re-rooted under dist rather than rejected. Login-required (not `PublicPage`); GET side-effect free so `NoCSRFRequired` fine; no XSSI (Lax cookies). Side notes: K1-3(c) is normalised by Apache before routing; on nginx `location / { try_files $uri … }` would serve `apps-extra/litecore/engine/**.gz` and `MANIFEST.json` statically without login (public content, but contradicts §5:170's reading); `MANIFEST.source.dist` ships `/home/jiajun/...`; the diff removed the old `..`/NUL guard (harmless while the MANIFEST is trusted, but defence in depth).

### 15. LIGHT: PHP delivery (checked; claims hold)

304 skips the body (`StreamResponse.php:44-53`, `App.php:184-199`); `readfile` maps the file, `stream_copy_to_stream` from `compress.zlib` is chunked, `output_buffering=0`; session closed early (`base.php:478`); HEAD matches GET routes, FPM discards the body; Range ignored, full 200 (legal); identity Content-Length correct when the gz is intact (K1-2). Minor: a manifest-listed but missing `.gz` becomes a 404 still carrying `immutable`, the ETag and `Content-Length = gzBytes` (`:184-201`); `package_m3_engine.py:82-85` deletes the old engine before renaming the new one (window of 500/404 or old manifest + new files).

### 16. LIGHT: rules nobody enforces

§3.6's bump rule (also applies to `litecore-files.mjs`) relies on memory; a cheap check: fail if the last commit touching `js/` is newer than the last commit changing `<version>`. The Firefox headroom guard from 8 is also missing.

### 17. LIGHT: labels and attributions

README:137/158 label runs 161410 and 161945 as `7a11a4b` (+ uncommitted fix); the JSON says HEAD `49cc4ab` with a dirty tree whose controller hash `10f4a752` equals `7a11a4b`'s (committed at 00:23 +0800, after both runs). "The beforeunload pair arrives every time" (finding :54, README:164-165) cannot be attributed: the log has method, status, one-second time; 5 of the 30 fixed runs had exactly 2 UNLOCKs. "有呼叫 fetch 兩次" (finding :16-17) is inferred from the probe's own listener firing.

### Checked and fine

Controller scope (only `engine/MANIFEST.json`, `engine/files/*.gz`, user file metadata; no `dist`/`/mnt` in `lib/ templates/ js/`). ETag/Vary (strong per-representation ETags; `NotModifiedMiddleware` compares with the chosen representation; multiple/weak If-None-Match fall through to 200 — fail-safe). UNLOCK/ETag (stale-token DAV UNLOCK fails `canUnlock` before `propagateEtag`, `LockService.php:214-219, 236-261`; successful UNLOCK moves it; after a beforeunload release If-Match cannot match again; 103 does not apply). bfcache (`persisted:false` is a property of the event; the page is no-store anyway). Closure (no side-effect or single-quoted imports, no `import()`; `e1-fixtures` never fetched with a host, `e2-editor-app.js:1728` after `return`; `loadResourcePack` only for `loadAtStartup` packs, `sdk-worker.js:600-602`). Red cases re-run 60/60 red on `164739`.

## Disposition (main session, 2026-09-29)

Each item checked against the source it cites before acting (`LoginController.php:96-100`,
`litecore-editor.js` `takeLock`, `findmnt /tmp` = tmpfs, `.user.ini` `output_buffering=0` read
directly). Host after the review: `5e53362` (0.2.1). Shakedown after: `shakedown/2026-09-28T172209+0000.json`,
84 red cases all red.

| # | disposition |
| --- | --- |
| 1 | **Adopted.** The controller builds every engine response from one `SERVE_POLICY` table; the address is `<buildId>-<sha256(policy)[:8]>`. K1-4 requires that form; red case "the address has no serving-policy hash". Headers Nextcloud adds itself are outside the table (named in spec §3.2). |
| 2 | **Adopted.** Finding 105's reading corrected: the failing runs wrote the engine into the cache, they did not read it from there. The planned minimal repro now says it must include a large cacheable download before leaving. |
| 3 | **Adopted.** Old host evidenced 8/9; "more frequent" is a suggestion (p≈0.11 within one probe); the fix is read per arm (12/12, upper bound ≈26%). Spec §3.5 and finding 105 rewritten. |
| 4 | **Adopted** as a named limit in spec §5 (read in source). Not measured. |
| 5 | **Adopted.** K2-3 allows a 304 only for paths the product fetches with `cache: "no-cache"`, derived from the closure's sources (`no_cache_fetches()`); the 4xx / other-address / one-document checks apply to both opens. Red cases A, D, E from the review added and red. |
| 6 | **Adopted.** The runner reads `nc:lock` itself after `done` (must be `"1"`), requires the host's `verified: true`, and requires exactly `""` after leaving. Red cases added. |
| 7 | **Named, not fixed.** Unlocking in the guarded branch would risk a save in flight or a user who stays. Stated as the unfixed path in finding 105 and spec §3.5. |
| 8 | **Adopted in part.** Packaging refuses any `.gz` over 45,000,000 bytes (K0-5 checks it); tmpfs/ext4 confound stated in README X1 and spec §2/§5; Firefox on a small disk named as unmeasured. The Firefox 1/8-of-capacity rule is the reviewer's recollection, not checked. |
| 9 | **Adopted.** Spec §3.3's cost paragraph struck and rewritten: per-address re-download for every user, concurrent streams and FPM exhaustion (inferred, unmeasured), "one year" as a ceiling, COEP as the hard reason; the nginx `gzip_types` point recorded as unchecked. |
| 10 | **Adopted.** K1-5 compares the document's initial-state `editor.sourceSha256` with the MANIFEST's `e2-editor.html`. |
| 11 | **Adopted** for the document (old address → 303 to the current one; K1-4 checks it). Old assets stay 404; the Chrome crash-restart case in an old tab named in §5. |
| 12 | **Adopted in part.** The hidden-tab skip is removed. The slow-navigation flip (>3 s) is left: it shows a notice on a page that is leaving anyway. |
| 13 | **Adopted.** Unparsed lines and other clients' app rows are recorded per open and make the run red ("K2 instrument"); K2-2 slack 4096 → 1500, the three blind small files named. `%O` = Apache→router bytes noted. |
| 14 | **Adopted in part.** `..`/NUL guard restored; MANIFEST source path made relative; K1-3(g) records the engine directory's static URL (404 on Apache); the nginx exposure named in §5; K1-3(c) annotated as testing Apache. |
| 15 | **Adopted.** Missing `.gz` → plain 404 without caching headers; engine swap is two renames then the delete. |
| 16 | **Adopted.** K0-6: the last commit touching `js/` must not be newer than the last commit changing `<version>`. |
| 17 | **Adopted.** Labels of `161410`/`161945` corrected in README and finding 105; "the beforeunload pair every time" and "the host called fetch twice" struck as unattributable / inferred. |
