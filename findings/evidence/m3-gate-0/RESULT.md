# M3 gate 0 — result (counted run, 2026-09-28)

```
$ python3 wasm_sdk_probe/tools/check_m3_gate0_report.py findings/evidence/m3-gate-0/runs/2026-09-28T065153Z-apache-fpm.json
VERDICT E1h shapes=E1h,E3 failing={}
```

The verdict is that line (PREDICTION.md Amendment 1), not the runner's
`provisionalGate`. Every predicate a–h of RULING.md CONDITION 3 returned no failure
(`--json`: `blocking: []`, all of `a b c d e f h` empty). The reader was committed and
made red before this run existed (`a9759513`; `reader-red-cases/SUMMARY.json`: base
green, strict red on (a), 24/24 copies red on the predicate they name).

## Gate 0 passes. Recommended shape: E1h

**Shape E1h: the shipped editor (the seven hashes below) boots, places a caret and
applies one paragraph action 3/3 in Chrome 151 and Firefox 156, cross-origin isolated,
inside a clean Nextcloud 34.0.2 on Apache with pretty URLs, with every engine script
(module JS, `sdk-worker.js`, `probe.js` incl. pthreads) served with COEP by PHP,
`.wasm` static, data files via PHP.**

E3 (same, `base` layout, no Nextcloud header) also passes 3/3 in both; E1h is the more
integrated of the two and its own Nextcloud header was read on every E1h run
(predicate f), not inferred from A1.

The E pages are the product page **re-wrapped** by the probe app (its `<style>`,
`<body>` and module inside Nextcloud's template), so the served HTML is not the product
bytes (`wire` `r/php/e2-editor.html…` → `6429930d…`); what ties it to the product is
`probe.config.editor.sourceSha256 == product["e2-editor.html"]` (`f7e47799…`), checked
per passing run by predicate b. The product's `<style>` also restyles Nextcloud's
`body`, `*`, `button`, `select`, `input[type=text]` on that page (RULING F2) — a
confound only in the fail direction.

### Named limits (RULING.md CONDITION 6, carried verbatim)

- **App-directory static engine files FAIL (E1).** 0/3 in both browsers, at boot.
  Chrome, every run: `r/static/profiles/e2-editor-v8/sdk-worker.js` →
  `net::ERR_BLOCKED_BY_RESPONSE`, `blockedReason: coep-frame-resource-needs-coep-header`
  (the 303 target in the app directory carries no COEP). Firefox, every run: the
  product's own toast `WORKER_CRASHED：document worker emitted an error`; no network
  reason is recorded there (no CDP), so in Firefox the cause is inferred from Chrome's
  reason plus the browser rule, not observed. The probe's own W-static worker (no COEP)
  answers `error-event` on every COEP `require-corp` page in both browsers (C6) — it
  follows COEP on the document, not isolation: in Chrome's A4d iframe, isolated by
  `Document-Isolation-Policy` without COEP, W-static reached `atomics-ok`.
- **nginx unmeasured.** The passing shapes' headers are set by PHP; C7 and W-htaccess
  differ there (nginx ignores `.htaccess`, and its `try_files` would serve the files
  Apache's whitelist rejects — inference from DDEV's generic PHP config
  `.ddev/nginx_full/nginx-site.conf:28`, not from Nextcloud's documented nginx config).
- **Third-party apps.** Clean instance only. Two directions, neither measured here.
  (1) Setting COOP/COEP on pages other apps own breaks those apps: that is
  nextcloud/richdocuments#4103 (opened 2024-10-08, still open; Maps tiles, Memories
  previews and Mail's embedded HTML reported broken once Nextcloud Office is enabled —
  its listener adds COOP + COEP to every app-framework page when the Collabora server
  advertises WASM support, shipped since `v8.4.0`, 2024-04; see
  `external/richdocuments-listener.md`). This is why the recommended shape isolates
  **the app's own routes only**. (2) On our own isolated route, an app that injects a
  cross-origin no-CORS subresource into every page would be blocked there; A1's canary
  models that on a controlled origin, and no clean-instance app does it.
- **Safari / WebKit** not measured.
- **Interactions beyond the smoke sequence** not exercised (boot, place caret,
  `set-paragraph-heading`; plus one app-menu open on the header). COOP `same-origin`
  also severs `window.opener` for popups; nothing here exercises that.

### What this does not license

The headers reach the engine scripts through PHP in this run. How they get there in
the product is an M3 item (CONDITION 7): four routes — **PHP** (as measured); **app
`.htaccess`** (Apache only; W-htaccess `atomics-ok` in both browsers on every isolated
page); **blob-URL workers** (a product change, plus `worker-src blob:` in the CSP);
**a COEP service worker**. Each must pass E1h's sequence 3/3 in both browsers before
it replaces PHP.

## Identity

| what | value |
| --- | --- |
| report | `runs/2026-09-28T065153Z-apache-fpm.json`, sha256 `3b31b3d9e4a69aed7eb5ee89764cd4bea878647651c450441d43448a0969a98e` |
| window | `2026-09-28T06:51:53Z` → `07:01:21Z`, label `counted`, repeats 3, action `set-paragraph-heading` |
| runner | `probe_m3_gate0_coep.py` sha256 `0be9f5516e0e…` (same bytes as shakedown 4) |
| probe app | `litecoreprobe` `f837937`, tree clean |
| instance | Nextcloud 34.0.2 (official tarball; `occ integrity:check-core` output empty — the saved file is 0 bytes — and exit 0 when captured right after the run, exit code not stored in a file), `apache-fpm`, `debug: false`, `htaccess.RewriteBase: /` — `runs/*.occ-*.txt` |
| browsers | Chrome 151.0.7922.169 (headless, CDP), Firefox 156.0 (headless, WebDriver) |

Product (`wasm_sdk_probe/dist`, re-hashed by the reader after the run — predicate d):

| file | sha256 |
| --- | --- |
| `e2-editor.html` | `f7e477998385c28390aaa6e77f8907ca15b0e0f1003e0d2ee469ed1f785236e0` |
| `e2-editor-app.js` | `1ec7baf9fb53c808cf127476346d69d56cf93a802f6c72680fa84416f7599ecc` |
| `sdk/document-sdk.js` | `11c0b1c14c30e1d0c24f92bc9eaaa25864c45daf6a1760021e63a40875936a12` |
| `profiles/e2-editor-v8/sdk-worker.js` | `070229cd10bda4a006200bfc9412862339518215db768f4d38ce61f2524ef52d` |
| `profiles/e2-editor-v8/probe.js` | `c382b834aa768b9118ee1e6a9bc832414481407f1139fcb35b36cfb540a43aab` |
| `profiles/e2-editor-v8/probe.wasm` | `4a2710bba1ef07d9364f02bd07905f0e95e92f805d97eab37dfb262e2a28b47f` |
| `profiles/e2-editor-v8/sdk-manifest.json` | `d70481cb1be5b1f963458a090a8b2b23e48ef68a4d07f3ebd934e566f03efa0d` |

## Measured, per criterion

Same in both browsers unless a column says otherwise.

| criterion | Chrome 151 | Firefox 156 |
| --- | --- | --- |
| **C1** instrument (A0 not isolated, A1 isolated, canary loads under A0, reported failed under A1) | holds | holds |
| **C2** E1 | 0/3, boot | 0/3, boot |
| **C2** E1h | 3/3 | 3/3 |
| **C2** E3 | 3/3 | 3/3 |
| **C2** E0 (negative control) | fails at boot, `stopped`, not isolated, no SAB, module imported; log attributes it: `DataCloneError … SharedArrayBuffer transfer requires self.crossOriginIsolated` | fails at boot, `stopped` (toast `TIMEOUT：init timed out after 120000 ms`), not isolated, no SAB, module imported; **no attribution field** in Firefox — the link to isolation is correlation plus Chrome's log |
| **C3** A1 vs A0: new Nextcloud failures / A0 failures / noisy / differing fields | `[]` / `[]` / `[]` / `[]` | `[]` / `[]` / `[]` / `[]` |
| **C3** header fingerprint A0 = A0b = A1 | 167 elements, 22 ids, 8/8 images, 7 buttons, 10 links, app menu opens with 6 entries | same |
| **C4** A4 (plain iframe in a non-isolated page) | not isolated | not isolated |
| **C4** A4d (`Document-Isolation-Policy`) | **isolated** | not isolated |
| **C5** A5 (Files isolated by an app listener) | isolated; toggle verified on the wire `[true, true]`; new failures `[]`; noisy `[]`, differs `[]` | same |
| **C6** W-static / W-htaccess / W-php on isolated pages (A1, A2, A5, A6) | `error-event` / `atomics-ok` / `atomics-ok` | same |
| A2 (`COEP: credentialless`) | isolated, canary loads | **isolated**, canary loads |
| A6 (Files → `location.assign` → A1 route) | isolated | isolated |

E1h/E3 timings over all 12 passing runs: place caret 32–41 ms, heading 29–67 ms;
revision 0 → 1 on every one. No zero-size canvas on any run (E1/E0 show the default 300×150
because boot stopped before layout; E1h/E3 725 px wide in Chrome, 900 in Firefox).

**C3 scope (CONDITION 9):** clean instance only. Firefox's detector = `<img>`/`<script>`/`<link>`
element failures, Chrome = CDP `Network.loadingFailed`. In Firefox that is narrower
than it reads: the capture-phase `error` listener is attached when the probe's own
script runs (`js/probe.js:15`), so `<script>`/`<link>` failures before that are missed;
`<img>` is caught regardless by scanning `document.images`. A blocked font, CSS `url()`
background, `fetch` or iframe is invisible to Firefox's detector. The header
fingerprint compares the **number** of ids (`idCount`), not their values (the values
carry random suffixes).

**C5 (CONDITION 9):** the Files page *can* be isolated by an app with no new failure
**on a clean instance**, at page load. That is the shape of
nextcloud/richdocuments#4103: its reported costs come from other apps' cross-origin
loads (Maps tiles; the bundled `photos` app already allows
`https://*.tile.openstreetmap.org` in `img-src` on every page — CSP permits it, COEP
would block it) and from COOP (the issue's title; Mail's embedded HTML). The editor was
never run inside Files, so an in-place editor there is neither shown feasible nor
infeasible; "own routes only" is the ruling's choice, for #4103's reason. The A5
listener (`BeforeTemplateRenderedEvent` + `addHeader`, filtered to
`getApp() === 'files'`) is a probe arm and **never a product mechanism**.
Instrument note: on A5 and A5-control the page's resource-timing list holds exactly
250 entries (the browser's default buffer), so it is truncated there; no criterion reads
it (failed loads come from CDP and element events, the canary from its own element).

### C7 — static serving (observation)

Apache with pretty URLs, files requested from the app directory
(`apps-extra/litecoreprobe/dist/…`):

| file | status | served the file on disk |
| --- | --- | --- |
| `e2-editor-app.js` | 200 `text/javascript` | yes |
| v8 `sdk-worker.js` | 200 `text/javascript` | yes |
| v8 `probe.wasm` (115 MB) | 200 `application/wasm` | yes |
| v8 `sdk-manifest.json` | 404 `text/html` | no |
| `e1-fixtures/list-contexts.odt` | 404 | no |
| v14 `sdk-manifest.json`, `.data` (40 MB), `.metadata` | 404 | no |

**Consequence (CONDITION 8), for roadmap §5.3:** the Apache `.htaccess` extension
whitelist with pretty URLs (`nextcloud/.htaccess:207`; the ruling says the official
image is the same — not checked in this tree) serves the whitelisted extensions
(`css|js|mjs|svg|…|woff2?|map|…|wasm|tflite`) from an app directory and rewrites every
other extension to `index.php`. v14's split packaging (`.data`/`.metadata`) and every `.json` must come
through PHP or another route. nginx's `try_files` would serve them — unmeasured.

## Predictions vs outcome

Every prediction in PREDICTION.md held: A0 false / A1 true; A1's delta empty in both;
A2 isolated in both with the canary loading; W-static blocked, W-php and W-htaccess
start; E1 fails, E1h passes; A4 not isolated; A4d isolated in Chrome only; A5
isolated with an empty delta; A6 isolated (its delta is not measured); E1h and E3 3/3;
E0 fails at boot in both. The roadmap's "`credentialless` 只有 Chrome" is wrong (A2
isolates in Firefox 156), and "壞掉一片" is wrong for a clean 34.0.2 instance **within
what was measured**: A1's delta is empty in both browsers at page load plus one
app-menu open, with the C3 detector scope above.

## Re-run the verdict

```bash
python3 wasm_sdk_probe/tools/check_m3_gate0_report.py \
    findings/evidence/m3-gate-0/runs/2026-09-28T065153Z-apache-fpm.json
```

Predicate d re-hashes `wasm_sdk_probe/dist` and reads the DDEV bind mount, so it goes
red if the product bytes on disk change after today; the report itself carries the
hashes above.

## Correction — 2026-09-28, later the same day (appended; nothing above is edited)

**"The shipped editor (the seven hashes)" binds less than it reads.** The seven
`PRODUCT_FILES` include the page and `sdk/document-sdk.js`, but not the other eleven
JavaScript modules of the shell bundle the page imports (`editor-shell-v2/*`,
`editor-shell/*`, `input/*`, `reader-shell/tile-scheduler.js`). Nothing in the report
hashes them. By inference — `dist/` is untracked — they were **shell generation v52's**
bytes (`e2/editor-shell-v2-bundle-v52.json`, `bundleSha256 7a1e8815…`): every one of
them hashes to v52's manifest today, and every mtime predates the counted run
(06:51:53Z; the latest is `narrow-editor-v2-session.js` at 04:01Z, v52's own change).
That is **not** the declared shipping generation (v48). So the PASS sentence is read
as: the seven hashes **plus shell v52's eleven other modules**, not "what users get
today". This does not change the verdict, because gate 0 is about headers and
isolation, not shell behaviour. It is a gap in the identity the report records, and
the ruling's D8 did not name it.

**Predicate d goes red from here on, by design.** The same day, the M3 host entry
changed `web/e2-editor-app.js` and was staged into `dist/`
(`1ec7baf9…` → `77276b4d…`; specs/SPEC-M3-host-entry.md). Re-running the reader on
this counted report now fails (d): the page on disk is no longer the page that ran.
The page that ran is `git show a9759513:wasm_sdk_probe/web/e2-editor-app.js`
(sha256 `1ec7baf9fb53c808…`).
