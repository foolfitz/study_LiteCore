# Adversarial review of SPEC-M3-zstd (opus, read-only), 2026-09-30

Target: `specs/SPEC-M3-zstd.md` at `e2de7632`, with the in-progress (then uncommitted) zstd edits to
`check_m3_assets.py` and `package_m3_engine.py`; the host was still `369e6ed`. The dispositions are
in the spec's §7 revision entry of the same day. Verbatim below.

---

## SUMMARY

Review target: `specs/SPEC-M3-zstd.md` at e2de7632. While I was reviewing, `check_m3_assets.py` and `package_m3_engine.py` picked up uncommitted zstd edits (they were not in git HEAD). Where a finding depends on that in-progress code, I say so. The host repo is still clean at `369e6ed`, so no 0.2.5 PHP exists yet.

1. **BLOCKING**: The real release builder, `build_m3_release.py` (install-elsewhere §3.1), packs only `.gz`. The install-elsewhere I0 expectations also list only `.gz`. The spec doesn't say what the host does when the chosen `.zst` is missing. If the host follows the existing "listed but missing = 404" rule, a 0.2.5 release is dead in Chrome and Firefox. No Z/K clause looks at the release, and Z4 measures a hand-made tar that nobody ships.
2. **HEAVY**: §3.2 says the zstd response carries "the same header table (…CSP…)". No clause checks CSP, and `KEEP` doesn't record it, so a looser CSP on the zstd representation (the one browsers actually get) passes every clause.
3. **HEAVY**: The in-progress checker adds the Z clauses unconditionally. Scored read-only, the counted 0.2.4 report `m3-assets/runs/2026-09-29T151106` now comes out `ASSETS NOT DELIVERED`: 98 problems, all caused by Z clauses. `check_m3_install_elsewhere` re-scores through this module at scoring time (I3-1, I3-6) and expects the verdict string `ASSETS DELIVERED`, while the spec names the verdict `ZSTD DELIVERED`.
4. LIGHT: Z1-2 tests one path because "the selection logic is path-independent (**read from source**)", but that source doesn't exist yet. Running the 7 rows on every path costs little.
5. LIGHT: §3.1 says the frames carry content size **and checksum**. The library default has no checksum (I checked). X1's `enc-zstd.wasm` came from the CLI (`zstd -19 -T0`, multithreaded, checksum on, 30,688,739 B), not the packager's 30,670,578 B, so "X1 measured exactly the level-19 product" overstates it.
6. LIGHT: RFC 9659 never defines "MB" (I checked the text). The limit that actually applies is `ZSTD_d_windowLogMax = 23` in both Chromium and Firefox (checked in upstream source), i.e. 8,388,608. Z0-2's bound is right; its stated reason should change.
7. LIGHT: §5 says `new Worker` requests are not observed by Z2. That's wrong: the 7 pthreads are `new Worker(probe.js)`, and probe.js is in D. Only the page's `new Worker(sdk-worker.js)` is unobserved. P1 and §5 contradict each other.
8. LIGHT: Z2-2 only rules out identity if raw − gz ≥ 1500 for every file in D, and D's definition doesn't carry that (it holds today; the smallest is 60,167).
9. LIGHT: "The address changed" appears only as prediction P3. If the implementation adds zstd outside `SERVE_POLICY`, the address stays the same and everything is green. That's harmless in practice but breaks the invariant.
10. LIGHT: Apache mod_deflate ignores q-values (checked in httpd source). `gzip;q=0` on a `.js` gets gzipped by Apache anyway. The spec's q=0 rule holds only at the controller. Z1-2's body-sha check is what protects the table; say so.
11. LIGHT: After 0.2.5 nothing exercises Chrome with gzip. A Chrome fallback arm via CDP `Network.setAcceptedEncodings` would need worker targets attached (I inferred this); a Z2-2-style control would catch it if it only half-applies.
12. LIGHT: K2-2 is still anchored to `gzBytes` even though zstd is what's served. It's harmless today (state-machine.js is +3 B); it could false-red on a future engine.
13. LIGHT: Rule 7: Z2 infers the encoding from `%O`. The arithmetic holds (item C), but CDP response headers for page-level requests would give a direct reading at almost no cost; recording them (not scoring them) is enough.
14. LIGHT: The B string in §2 can go from "inferred" to "read from source". Chrome's `SetAcceptEncodingIfMissing` and Firefox 156's `greprefs.js` both give exactly `gzip, deflate, br, zstd`.

## DETAILS

### 1. BLOCKING: the release doesn't carry `.zst`, and the missing-`.zst` behaviour is unspecified

- **Verified by reading source.**
  - `wasm_sdk_probe/tools/build_m3_release.py:8-9, 67` collects `engine/MANIFEST.json` plus `engine/files/{path}.gz` only.
  - `check_m3_install_elsewhere.py:772-773` (`archive_records`) and `:988-997` (I0-1 and I0-2 expected members = git blobs plus `engineDir`, which is `.gz` only) share that assumption. So a `.gz`-only archive passes I0.
  - `check_m3_skeleton_open.host_binding` (lines 125-133) treats any installed file not in `release.json` members as "extra", i.e. dirty. You can't hand-add `.zst` on the other instance either.
- **In the spec:** §3's frozen scope ("only the packager, the host PHP and the scorer change") leaves out the release builder. Z4 says "build the tar.gz with asset-delivery K4's command". That is the ad-hoc `tar … litecore/engine`, not `build_m3_release.py`. §6 says J moves to the 0.2.5 archive.
- **How it fails:** 0.2.5 is counted `ZSTD DELIVERED` on the dev tree. Then `build_m3_release.py` produces an archive whose MANIFEST lists `zstSha256` for files that aren't in it.
  - The current controller answers "listed but missing" with 404 (`EditorController.php:217-220`). If 0.2.5 applies the same rule to the chosen representation, every engine request from Chrome or Firefox 404s on an installed release.
  - If it falls back to gzip instead, the release silently loses the benefit.
  - J would eventually fail at I3-1, because Z0-1 on the installed tree would find no `.zst`. But J is owner-scheduled; A (release channel) isn't.
- **Fix:**
  - Specify the host rule now, since it's 0.2.5 bytes. Either (a) fail closed with a no-cache 404, stated explicitly, or (b) fall back to `.gz` with the gzip ETag.
  - Bring `build_m3_release.py` and `archive_records` into scope. Build the member list tool-closed from the manifest: every representation field (`gzSha256`, `zstSha256`) implies a member, instead of a hard-coded `.gz` suffix.
  - Make Z4 measure the builder's archive.

### 2. HEAVY: CSP (and every header not listed) on the zstd representation is never observed

- **Verified:**
  - `fetch()` records only `KEEP = content-type, content-encoding, content-length, cache-control, vary, location, etag, COOP, COEP` (`check_m3_assets.py` KEEP). Z1-1 in the in-progress code checks the same subset. K1-1 never checked CSP either.
  - `CSPMiddleware::afterController` returns an `EmptyContentSecurityPolicy` untouched: no merge, no nonce (`nextcloud/lib/private/AppFramework/Middleware/Security/CSPMiddleware.php`). The worker CSP is therefore a deterministic string and can be compared directly between representations.
- **Mutation:** the zstd branch builds its policy with an extra `allowEvalScript(true)` or `script-src *`, or skips a directive. Workers still boot, so K2-4 stays green, and Z1 and Z2 stay green too. Only tightening shows up, through K2-4. §3.2 claims the headers are "the same table"; nothing checks that.
- **Fix:**
  - Record every response header in the report.
  - Z1-1: for each path, the zstd response's header set, minus `Content-Encoding`, `Content-Length`, `ETag` and `Date`, must equal the gzip response's. This is a per-path property and catches every future divergence, not just CSP.

### 3. HEAVY: the scorer change rewrites past verdicts and the verdicts its consumers read

- **Verified:** I ran `score()` read-only from the current working tree (`PYTHONDONTWRITEBYTECODE=1`) on `findings/evidence/m3-assets/runs/2026-09-29T151106+0000.json`, the 0.2.4 counted run.
  - Result: `ASSETS NOT DELIVERED`, 98 problems.
  - Every problem traces to a Z clause: Z0-1..4, Z1-1, Z1-2, plus `K2 chrome 0/3 of 3`, `K2 firefox 0/3 of 3` and `K2 firefox-nozstd 0/0 of 3`. The two K2 tallies are red because every run fails "Z2 D is []".
  - Cause: `score_package()` now returns `bad + score_zstd_package(pkg)`, `score_run()` returns `bad + score_zstd_run(...)`, and `PLAN` gained `firefox-nozstd`.
- **Who depends on it:** `check_m3_install_elsewhere.py:925-931` (`runner_verdict`) and `:911-922` (`red_cases_now`) call `check_m3_assets.score` and `red_cases` at scoring time. `RUNNERS["assets"][2] == "ASSETS DELIVERED"`, but spec §4 calls the pass `ZSTD DELIVERED`, so it's ambiguous which string the tool prints.
- **Context:** the older 09-28 and 09-29 reports were already red on `static: page` after the page rebinding, so there is precedent. But 151106 re-scored clean until now, and the spec doesn't mention the change.
- **Fix:**
  - Gate the Z clauses on a report field written by the runner (e.g. `spec: "SPEC-M3-zstd"`), and take `PLAN` from the report.
  - Don't gate on `manifest.schema`: that would let a schema-1 manifest switch off Z0-4, the very clause meant to catch it.
  - Pin the verdict string, and state that install-elsewhere's I3-1 and I3-8 equivalence must be redone before J.

### 4. LIGHT: Z1-2's single-path argument rests on source that doesn't exist yet

A path-dependent selection escapes Z1-2. Example: a fast path `if .wasm and str_contains(AE,'zstd') → zstd` that ignores `zstd;q=0`. Z1-1 (B), Z1-2 (document-sdk.js only), Z1-3 and Z2 all stay green. In practice the impact is small, because no real client sends `zstd;q=0`.

**Fix:** run the 7 rows on every non-document path. Identify the representation from `Content-Encoding`, ETag and Content-Length, and require the body sha on files under about 1 MB. For the big files you can close the connection after the headers.

### 5. LIGHT: the checksum claim, and what X1 actually measured

- **Verified:** `python3 -c "from compression import zstd; b=zstd.compress(os.urandom(1000)*50, level=19); ..."` gives descriptor `0b1100000`, i.e. checksum flag 0 and content-size flag set; libzstd is `(1, 5, 7)`.
- **Verified:** `probe_m3_browser_cache.py:103` built X1's file with `zstd -19 -T0 -q` (CLI, multithreaded, checksum on by default). It was 30,688,739 B (README S0-2); the packager's single-threaded library output is 30,670,578 B.
- No correctness risk, because the counted K2 runs load the real bytes. Fix the wording of §3.1 and §2.

### 6. LIGHT: the RFC wording versus the limit that actually applies (the bound itself is right)

- **Verified (WebFetch, rfc-editor RFC 9659):** "encoders MUST NOT generate frames requiring a Window_Size larger than 8 MB". The document doesn't define MB.
- **Verified in upstream main (not the exact Chrome 151 / Firefox 156 tags):**
  - Chromium `net/filter/zstd_source_stream.cc`: `window_log_max = 23` for plain zstd.
  - Firefox `nsHTTPCompressConv.cpp`: `ZSTD_DCtx_setParameter(mDStream, ZSTD_d_windowLogMax, 23 /*8*1024*1024*/)`.
- So ≤ 8,388,608 is exactly what both browsers accept, including single-segment frames, where the window is the frame content size. Cite the implementations instead of the RFC. The in-progress `zstd_frame()` parser matches RFC 8878 §3.1.1: FCS sizes, the +256 offset, dictionary-ID sizes and window = base + base/8·mantissa.

### 7. LIGHT: `new Worker` is observed

- **Verified:**
  - `dist/profiles/e2-editor-v8/probe.js` contains `var pthreadMainJs=_scriptName` / `pthreadMainJs=Module["mainScriptUrlOrBlob"]` and `worker=new Worker(pthreadMainJs,{…name:"em-pthread"})`.
  - `sdk-worker.js:612-621`: `importScripts(loaderUrl)` and `mainScriptUrlOrBlob: loaderUrl`, where loaderUrl is probe.js.
- So probe.js is fetched once by `importScripts` and 7 times as a classic nested `new Worker`, and all 8 rows are in D (a 2,645 B difference). Only the page-level `new Worker(sdk-worker.js)` (`sdk/document-sdk.js:67`, a 999 B difference) goes unobserved. Correct §5 and add "new Worker (nested)" to P1's list.

### 8. LIGHT: Z2-2 relies on a property D doesn't state

In Z2-2, `%O < gzBytes+1500` rejects identity only if `bytes − gzBytes ≥ 1500`. D is defined by `gzBytes − zstBytes ≥ 1500` alone. That holds today for all six members (smallest is e2-editor-app.js: 94,138 − 33,971 = 60,167), but a gzip-resistant pack with long-range redundancy could join D without it.

**Fix:** define the fallback arm's set as D ∩ {bytes − gzBytes ≥ 1500}, computed by the runner, with the same non-vacuity rule.

### 9. LIGHT: the address change is only a prediction

- K1-4 checks only the address format. P3 ("the policy hash changed") is registered, not scored.
- **Mutation:** keep `'encoding' => 'gzip'` in `SERVE_POLICY` and hard-code `'zstd'` in `serve()`. The address stays `7f4f4e2204b4a9ec-<0.2.4 hash>` and every clause is green.
- **Functional effect (reasoned from the controller and NotModifiedMiddleware):** browsers warm from 0.2.4 keep valid gzip entries; the `sdk-manifest.json` revalidation gets a 200 with zstd. So it's harmless, but the "headers come from `SERVE_POLICY`, so the address moves" invariant is silently broken.
- **Fix:** a one-shot clause saying the address differs from the 0.2.4 address recorded in `151106`.

### 10. LIGHT: q=0 at the Apache layer

- **Verified (httpd 2.4.x `mod_deflate.c`):**
  - The filter removes itself for any `Content-Encoding` token other than identity, 7bit, 8bit or binary, so zstd passes through untouched. That confirms the §5 claim by source, not just by analogy with gzip.
  - Its Accept-Encoding scan has `/* skip parameters, XXX: ;q=foo evaluation? */`, i.e. it ignores q-values.
- **Verified (container):** there is no mod_brotli (`apache2ctl -M`, `mods-enabled`), and `deflate.conf` covers `text/javascript`.
- **Consequence:** a client sending `gzip;q=0` alone gets identity from the controller, which Apache then gzips for `.js`.
- Z1-2 has no such row and is correct as written. And if the controller wrongly returned identity for `zstd;q=0, gzip`, Apache would gzip it on the fly and the body-sha rule would catch it, because Apache's bytes differ from the packaged ones. Write that down as the reason the table is sound.

### 11. LIGHT: the only fallback arm is Firefox

- **Verified (Chromium `http_request_headers.cc`):** zstd advertising also depends on `accepted_stream_types`, which is how CDP `Network.setAcceptedEncodings` restricts it.
- **Inferred:** for worker requests this needs the worker targets attached. The runner attaches only to the page.
- Optional: add `chrome-nozstd` with a positive control on the Z2-2 pattern.

### 12. LIGHT: K2-2's reference size

K2-2 compares against `gzBytes` although zstd is now served. Suggested form: `%O < bytes of the representation this arm should get + 1500`.

### 13. LIGHT: rule 7 (direct observation)

`EventChrome` already keeps `Network.responseReceived` events, but `run_browser` doesn't save them. Record `content-encoding` and `encodedDataLength` for page-level requests (e2-editor-app.js is in D) as a registered, unscored cross-check on the `%O` inference.

### 14. LIGHT: the B string can be upgraded from inferred

- **Verified:**
  - Chromium `SetAcceptEncodingIfMissing` gives `gzip, deflate, br, zstd` in that order, for every request without an explicit Accept-Encoding and without `Range`, when the scheme is HTTPS or localhost.
  - Firefox 156.0 (`/snap/firefox/current/.../omni.ja` → `greprefs.js:480`) has `pref("network.http.accept-encoding.secure", "gzip, deflate, br, zstd")`. The pref exists, so the `firefox-nozstd` arm's pref name is right.
  - Line 481, `accept-encoding.dictionary = "dcb, dcz"`, is appended only when a stored dictionary matches, and Nextcloud never sends `Use-As-Dictionary` (grep: none). So Vary won't split the first and second open.
- **Inferred:** Firefox applies the pref to worker, importScripts and pthread requests. The arm's gzip-size check (Z2-2) tests this on every run.

### Checked, not a problem

- **A. Traefik:** no compress middleware. `~/.ddev/traefik/config/litecore_merged.yaml` and `.ddev/traefik/config/litecore.yaml` only have `redirectHttps`, which is commented out; no retry middleware. The runner and the browsers both go through `https://litecore.ddev.site:8443`.
- **B. PHP and Nextcloud leave the zstd response alone:**
  - `zlib.output_compression` is Off (`php-fpm8.4 -i`).
  - There's no PHP zstd extension, which is why identity has to keep decoding the `.gz`.
  - `CompressionMiddleware` gzips only `BaseResponse`, `JSONResponse` and `TemplateResponse`; `StreamResponse` is untouched.
  - `NotModifiedMiddleware` gives a 304 only on an exact match `trim(If-None-Match) === '"'.etag.'"'` against the representation actually chosen, so another representation's validator gets a 200 (Z1-3 is consistent with this).
  - On 304, `App::main` skips the body and `StreamResponse::callback` skips `readfile`.
  - The Nextcloud `.htaccess` `FilesMatch` cache rules don't match `/index.php/...` (filename is index.php).
- **C. The 1500 slack is sound:**
  - zstd: `%O = H + zstBytes`, with H ≈ 875–930. It's the same header set, and "zstd" and "gzip" are the same length.
  - gzip: `%O ≥ gzBytes ≥ zst+1500`, so it always fails Z2-1.
  - identity: `%O ≥ bytes > gzBytes`, so it fails too.
  - A gzip or identity row can pass only as a truncated 200. The browser would then need a complete copy from some other logged row (which gets judged) or another URL (K2-1 forbids it). There's no retry middleware.
  - A zstd row fails Z2-2 only if Firefox actually advertised zstd, which is the intended red. The only false-red risk is H ≥ 1500.
- **D. zstd output isn't deterministic across libzstd versions:** no clause re-derives `.zst` from `dist/`. Z0 compares the files with the manifest and Z1 compares the wire with the files. The address depends on decoded content and policy only, so repackaging with another libzstd changes ETags under the same URL. The cost is one extra 200 instead of a 304 for the no-cache manifest; decoded bytes are identical. The manifest records level and libzstd, and the frame parameters are in the header that Z0-2 reads.
- **E. `state-machine.js`, where zstd is 3 B bigger:** Z1-1 checks its bytes, and K2-2 has room: 754 + H is well under 751 + 1500.
- **F. Z3's five runners:** no gzip, `Content-Encoding` or `.gz` references (grep on host_entry, locks, versions, page_honesty, same_second and skeleton_open). The only other importers of `check_m3_assets` are `probe_m3_leave_unlock.py` (`open_and_smoke`, `DONE_TO_LEAVE`) and install-elsewhere (item 3).
- **G. The Z0-2 bound matches both browsers exactly (item 6).** The 45,000,000 cap applies to encoded size, which is what X1 measured for Firefox.
