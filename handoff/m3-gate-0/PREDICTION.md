# M3 gate 0 — COOP/COEP inside Nextcloud: criteria and predictions

Written 2026-09-28, **before any counted run**. This file is append-only once the
first counted run exists (CLAUDE.md §10): corrections go at the end and name what
they replace.

## The question (roadmap §5.1)

The shipped editor needs `SharedArrayBuffer` (`PTHREAD_POOL_SIZE=7`), so its page
must be cross-origin isolated. Nextcloud 31.0.13, 33.0.8 and 34.0.2 contain zero
lines of COOP/COEP/CORP (grep over `*.php`, `*.js`, `*.ts`, `.htaccess`, re-run
2026-09-28). The roadmap lists three workarounds, all unverified, and one
inference: *"掛在標準 Nextcloud 介面上會壞掉一片"* — COEP on the standard UI breaks a
swath of it. Gate 0 decides **what shape the app can take**. It is not an app.

## Setup (fixed before the first counted run)

- The owner's DDEV scaffold (`~/Projects/ddev-nextcloud-app`, add-on installed from
  the local path), project `~/Projects/Nextcloud_Apps/litecoreprobe` — its own git
  repo; every report records its commit and the sha256 of every tracked file, and a
  counted run refuses a dirty tree. Web server `apache-fpm`, PHP 8.4, MariaDB 11.4.
- **Core = the official `nextcloud-34.0.2.tar.bz2`** (sha256 checked against
  download.nextcloud.com), not the scaffold's default git clone: a git clone of
  `server` lacks the apps the release tarball ships (notifications, activity, viewer,
  text, firstrunwizard, recommendations …) — exactly the apps that inject code into
  every page's header and into Files, which C3/C5 are about. 50 apps enabled by the
  installer, plus the probe.
- Served at `https://litecoreprobe.ddev.site:8443` (DDEV router, mkcert certificate;
  Chrome trusts it through `~/.pki/nssdb`, Firefox through a per-run profile with the
  mkcert CA imported). The canary's origin is `https://litecoreprobe-xo.ddev.site:8443`
  — the same server, a different host.
- Deviations from a default install, each for a stated reason: `firstrunwizard`
  disabled (its once-per-user modal would make the first arm's DOM differ from the
  second's for a reason that is not COEP); `debug` forced `false` and `loglevel` 2 by
  `config/zz-m3gate0.config.php` (the scaffold sets development values).
- Probe app `litecoreprobe` in `apps-extra/`; `wasm_sdk_probe/dist` bind-mounted
  read-only at `/mnt/litecore-dist`, reached through the app's `dist` symlink.
- Chrome 151 (headless=new, CDP) and Firefox 156 (headless, WebDriver). Browser
  caches disabled.
- Headers are set by the **controller** (server-independent) unless an arm says
  otherwise. The runner re-reads every arm's headers off the wire (`report.wire`).

## Arms

| id | page | headers |
| --- | --- | --- |
| A0 | `user` layout (full Nextcloud chrome) | none — the control |
| A1 | same | COOP `same-origin` + COEP `require-corp` |
| A2 | same | COOP `same-origin` + COEP `credentialless` |
| A4 | A0 page embedding a bare probe iframe, `allow="cross-origin-isolated"` | iframe: COOP+COEP require-corp |
| A4d | same | iframe: `Document-Isolation-Policy: isolate-and-require-corp` |
| A5 | the **Files** page, isolated by an app listener calling `header()` | COOP+COEP require-corp; control = same page, listener off |
| A6 | Files page → `location.assign()` → A1 route | as A1 |
| A0b | A0 again, last — the noise control for C3's fingerprint | none |
| E1 | the shipped page (v8, re-wrapped: its `<style>` + `<body>` + its module) in the `user` layout | as A1; product assets reached via a redirect route to the static mount (Apache, **no** COEP on them) |
| E1h | same | as A1; `*.js`/`*.json` product assets **served by PHP with COEP**; `.wasm` still static |
| E3 | as E1h but `base` layout (no Nextcloud header) | as A1 |
| E0 | as E1h | **none** — negative control: the sequence must fail here, or it cannot tell isolation from its absence |

A0, A1, A2, A5 and A6 load a canary: one `<img>` from the canary origin (cross-origin,
no CORP), allowed by the page's CSP so that only COEP can block it. Loads by the probe
itself (canary, workers) are kept out of C3/C5's Nextcloud-failure sets.

## Observations per page

`crossOriginIsolated`; a 1 GiB shared `WebAssembly.Memory`; three dedicated workers
— **W-static** (app `js/`, Apache, no COEP), **W-php** (controller, with COEP),
**W-htaccess** (app `js/coep/` with an app-shipped `.htaccess` setting COEP) — each
must receive a `SharedArrayBuffer` and answer an `Atomics` round trip; failed loads
(Chrome: CDP `Network.loadingFailed` incl. `blockedReason`; both: `<img>` complete
with `naturalWidth == 0`, element `error` events); a structural fingerprint of the
Nextcloud header read after the element count holds still for 1.5 s (element, id,
button, link and image counts, images loaded, app-menu and user-menu present, Files
rows) and then **one interaction**: the app menu (a waffle popover in 34, whose
entries do not exist until opened) is clicked open and its entries counted. E arms: the page-smoke sequence of
`run_e2_c_page_smoke.py` — boot to `ready`, place caret, `set-paragraph-heading`,
revision +1.

## Criteria

- **C1 instrument:** A0 reports `crossOriginIsolated == false`, A1 `true`; the canary
  loads under A0 and is reported **failed** under A1, in each browser. If C1 fails in a
  browser, the failed-load detector is unproven there and that browser's C3/C5 are
  **VOID** (C2, C4, C6 do not use the detector and are still read).
- **C2 route shape works:** an E arm passes the page-smoke sequence **3/3 in Chrome
  and 3/3 in Firefox**, AND the negative control E0 fails in both. Gate 0 **passes**
  iff that holds for at least one of E1 / E1h / E3; the recommended shape is the most
  integrated one that passes (E1 > E1h > E3). None passes → **stop** (M3 as designed
  does not start). E0 passing anywhere → verdict `INSTRUMENT`, nothing is concluded.
  A failure at `place-caret` with a zero-size canvas is recorded as layout, not
  isolation, and is reported as such beside the count.
- **C3 Nextcloud chrome survives:** in A1, the set of Nextcloud's failed loads (the
  probe's own canary and workers excluded) is a subset of A0's; the header fingerprint
  equals A0's on every field that is equal between A0 and A0b (a field that differs
  between two loads of the same page is noise, reported and not judged); and A0's
  opened app menu shows ≥ 1 entry (else the interaction check is dead and C3 is not
  met). In each browser. C3 false ⇒ the app must use E3's shape (no Nextcloud header);
  list what broke.
- **C4 in-place in a non-isolated page:** A4 isolated in a browser ⇒ in-place possible
  there. A4d is recorded per browser (Chrome-only feature).
- **C5 in-place by isolating Files:** A5 isolated + A5's failed-load delta vs its
  control. Reported, **not decided here** — isolating Files is a product trade-off for
  the owner.
- **C6 asset headers:** which of W-static / W-php / W-htaccess start, per browser.
  Decides whether the app needs server configuration.
- **C7 static serving (observation, not a criterion):** for the files a profile needs
  (`.js`, `.wasm`, `.json`, `.odt`, and v14's `.data` / `.metadata`), does the web
  server hand out the app-directory file (status 200 and the bytes on disk)? Read off
  the wire, so it stays true if Nextcloud changes its list. Feeds roadmap §5.3.

Repetition: A arms once per browser (header policy is deterministic; a disagreement
between the two browsers is reported, not re-run away). E arms three times per browser,
fresh browser each time.

**If this is never run:** the app's shape stays undecided and M3 does not start.

### Shaped by the shakedown (2026-09-28, three runs, none counted)

Each change above that was not in the first draft is named here with what forced it.
None moves a threshold; each makes a field mean what its name says.

- The app-menu entry count read 0 on every page (Chrome shakedown 1): 34's app menu
  is a popover. → count after opening it; a dead check fails C3 instead of passing it.
- The raw header ids differed between two loads of A0 (random suffixes such as
  `trigger-menu-qtfdd`, shakedown 3). → compare their number; add A0b and the
  "noise is reported, not judged" rule.
- All editor arms failed at boot on `fixture fetch failed: 404` (shakedown 1): `.odt`
  and `.json` are outside Nextcloud's static whitelist. → data files through PHP in
  both modes, only `*.js` / `*.wasm` decide static vs php; the whitelist itself became
  C7.
- A5 read "not isolated" though the listener was on (shakedown 1): Nextcloud 34
  caches app config in the web server's APCu for 3 s and `occ` cannot clear it. → the
  runner believes a toggle only once the Files response on the wire shows it.
- Snap-packaged Firefox could not see a profile under `/tmp` (shakedown 2). → scratch
  under `wasm_sdk_probe/build/`; a browser that dies is recorded, not lost.

## Predictions (for calibration; not criteria)

- A0 false / A1 true in both. **A1's delta vs A0 empty** in both — i.e. the roadmap's
  "壞掉一片" is wrong for a clean instance, because every subresource of a clean
  Nextcloud page is same-origin.
- A2 isolated in **both** (the research note says "Chrome only"; I believe Firefox
  shipped `credentialless`). Canary loads under A2.
- W-static **blocked in both** (a dedicated worker's own response must carry a
  compatible COEP); W-php and W-htaccess start. ⇒ E1 fails, E1h passes.
- A4 not isolated in either browser; A4d isolated in Chrome only.
- A5 isolated in both, empty delta. A6 isolated in both.
- E1h and E3 3/3 in both. E0 fails at `boot` in both (no `SharedArrayBuffer`).

## Named limits (declared now)

Safari/WebKit not measured. Nextcloud 34.0.2 only (31.0.13 and 33.0.8 carry the same
zero-hit grep; the 34.0.2 tarball itself, all bundled apps' JS included, has zero hits).
Apache only: controller headers are server-independent, `.htaccess` is not (nginx
ignores it). Clean instance only — a third-party app that injects a cross-origin
no-CORS subresource into every page would break A1's shape; C5's canary is the model
of that. Interactions beyond page load (menus, popups that rely on `window.opener`)
are not exercised, except the editor's own sequence.

---

## Amendment 1 — fable's ruling, 2026-09-28 (appended before the first counted run)

Source: `handoff/m3-gate-0/RULING.md` (verbatim). This append replaces nothing above;
where it is stricter, it wins. §9 of CLAUDE.md: written before any counted run; forced
and named (synthetic tests D1–D5 in the ruling showed the runner's `gate()` green on
false inputs; addendum F8 = richdocuments / nextcloud/richdocuments#4103); every
predicate is form 1 or 2; closed at the first counted run.

**The verdict is no longer the runner's.** `probe_m3_gate0_coep.py` writes a
`provisionalGate` that is not read. The verdict is one line from
`wasm_sdk_probe/tools/check_m3_gate0_report.py REPORT.json`, which recomputes from raw
fields (a pass from the recorded editor steps; C1/C3 by applying the runner's scorers
to the raw pages) and requires:

- **a** `label == counted`, `repeats == 3`, `action == set-paragraph-heading`, browsers
  exactly {chrome, firefox}, no `fatal`, every shape arm has `repeats` runs.
- **b** every E1/E1h/E3 run that passed read `crossOriginIsolated` and
  `SharedArrayBuffer` true, was on its own URL, imported the product module, and was
  re-wrapped from the hashed `e2-editor.html`; in Chrome the document response on the
  wire carried COOP `same-origin` + COEP `require-corp`.
- **c** E0, once per browser, failed at `boot` with state `stopped` (not a read error —
  a login page is not a negative result), not isolated, no `SharedArrayBuffer`, product
  module loaded; in Chrome its log attributes the failure (`requires
  self.crossOriginIsolated`).
- **d** the served bytes are the product: static `e2-editor-app.js`, v8 `sdk-worker.js`,
  `probe.wasm` and PHP-served v8 `sdk-worker.js`, `probe.js` hash to `report.product`;
  the seven `PRODUCT_FILES` on disk still hash to `report.product` when the reader runs;
  the container's bind mount is this `dist`.
- **e** C1 holds in both; A0 has no Nextcloud failures; **no noisy field** (A0 vs A0b —
  a noisy field makes C3 not established, it is no longer "reported, not judged"); C3
  holds; every page arm's `href` starts with its URL.
- **f** E1h's own Nextcloud chrome, read on E1h per run: no Nextcloud failures, header
  fields equal to A0's, app menu opens with ≥ 1 entry.
- **g** recommended shape by the reader: `E1h` iff E1h 3/3 in both ∧ e ∧ f; else `E3`
  iff E3 3/3 in both; else `STOP`. E1 is never a shape. Any of a, b, c, d, h failing →
  `NOT_ESTABLISHED`.
- **h** Nextcloud `34.0.2`, `debug` false, probe app tree clean, `apache-fpm`.

The reader is made red first: `--red-cases` builds one mutated copy of shakedown 4's
report per case (kept gzipped under `findings/evidence/m3-gate-0/reader-red-cases/`)
and requires shakedown 4 itself green under `--allow-shakedown`, red on (a) without it,
and every copy red on the predicate it names.

**Other amendments.**
- A5's headers come from `BeforeTemplateRenderedEvent` + `addHeader`, filtered to
  `getApp() === 'files'` (the API Nextcloud Office uses; it applies it to every page).
  The A5 listener is never a product mechanism. C5's report cites
  nextcloud/richdocuments#4103 as the known cost of isolating shared pages.
- Shakedown 4 runs on the post-ruling instrument (probe app `f837937`) before the counted
  run and must show: `noisy == []` in both browsers, `toggleVerified == [true, true]`,
  A5 isolated in both, and the reader green on E1h with E3 also passing.
- Saved beside the counted report: `occ integrity:check-core`, `occ config:list system`
  (secrets masked), `occ app:list`.
- C7's consequence is written as "Apache `.htaccess` extension whitelist with pretty
  URLs", not "Nextcloud"; nginx stays a named limit (its `try_files` would serve those
  files — unmeasured).
- What a PASS may say, and its named limits, are fixed in RULING.md CONDITIONS 6–9.

---

## Closed — 2026-09-28 (appended after the first counted run)

Counted run `findings/evidence/m3-gate-0/runs/2026-09-28T065153Z-apache-fpm.json`
(sha256 `3b31b3d9…a98e`), 06:51:53Z–07:01:21Z, on the instrument and reader committed
in `a9759513`. Reader: `VERDICT E1h shapes=E1h,E3 failing={}`. Gate 0 passes; the
recommended shape is E1h. Every prediction above held. The PASS sentence, the named
limits and the measured table are in `findings/evidence/m3-gate-0/RESULT.md`.
Amendment 1 closes here: nothing above is edited, and any later concern about this gate
becomes a finding or M3 work, not a new criterion.
