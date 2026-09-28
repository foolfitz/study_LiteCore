# M3 gate 0 — ruling request (before the first counted run)

The owner is away and has authorised you (fable) to decide on their behalf for this
round. Your WHY section is what they will read when they come back: write it in
plain Traditional Chinese (台灣正體中文), no jargon they would have to look up.

## What gate 0 must decide

Roadmap `research/ROADMAP-2026-08-20-milestones.md` §5.1: the editor needs
`SharedArrayBuffer`, so its page must be cross-origin isolated (COOP + COEP);
Nextcloud ships zero lines of COOP/COEP. Which shape can the Nextcloud app take?
Criteria, arms and predictions: `handoff/m3-gate-0/PREDICTION.md` (read all of it).

## What exists

- Probe app (its own repo, commit `e13cb83`): `~/Projects/Nextcloud_Apps/litecoreprobe/`
  — `lib/Controller/ProbeController.php` (arms, headers: `page` :52, `bare` :87,
  `worker` :119, `asset` :139, `editor` :164, `serve` :205), `js/probe.js` (the page
  probe: `tryWorker` :61, `loadCanary` :115, `settle` :135, `headerFingerprint` :160,
  `openAppMenu` :180, `openFrame` :216, editor import :244), listeners for A5 in
  `lib/Listener/`.
- Runner: `wasm_sdk_probe/tools/probe_m3_gate0_coep.py` (`run_editor` :326, arms
  :401/:408, `static_checks` :447, `set_files_isolation` :457, `failed_loads` :519,
  `compare` :553, `score_browser` :581, `gate` :644 — line numbers approximate after
  the last edit; grep the names).
- Three shakedown runs (not counted). The last complete one, both browsers, repeats=1:
  `findings/evidence/m3-gate-0/shakedown/2026-09-28T060421Z-apache-fpm.json`
  (1 MB — read fields with python, do not print it whole). It was taken **before** the
  last two instrument fixes (`idCount` instead of raw ids; C5 borrowing A0/A0b noise).

Shakedown 3 in one table (not evidence for the gate; evidence that the instrument runs):

| | Chrome 151 | Firefox 156 |
| --- | --- | --- |
| C1 (A0 not isolated, A1 isolated, canary loads under A0, blocked under A1) | holds | holds |
| E1 static engine scripts | fails at boot (`sdk-worker.js` blocked, `coep-frame-resource-needs-coep-header`) | fails at boot |
| E1h / E3 | 1/1 / 1/1 | 1/1 / 1/1 |
| E0 negative control | fails at boot | fails at boot |
| C3 new Nextcloud load failures in A1 / fingerprint | none / equal on judged fields | none / equal |
| A4 iframe in a non-isolated page / A4d DIP | not isolated / **isolated** | not isolated / not isolated |
| A5 Files isolated by the app's listener | isolated, no new failures | isolated, no new failures |
| A2 credentialless | isolated, canary loads | isolated, canary loads |
| W-static / W-htaccess / W-php in isolated pages | blocked / ok / ok | blocked / ok / ok |
| C7: `.js` `.wasm` / `.json` `.odt` `.data` `.metadata` static | 200 / **404** | same (server-side) |

## The rulings I need

**Q1 — is the protocol fit to decide gate 0?** If a counted run (3 repeats) returns
`PASS`, is "the shipped editor runs cross-origin-isolated inside a clean Nextcloud 34
in shape X" warranted? Attack each predicate in `score_browser` / `gate`: construct a
concrete situation where the claim is false and the check is still green. For a block
where you find nothing, say "no defect found" — do not pad.

**Q2 — the judgement calls I made. Each is a claim for you to check, with my
inclination; overturn any of them.**

- **F1 environment.** The owner pointed me at their DDEV scaffold, so I used it:
  apache-fpm, PHP 8.4, MariaDB, HTTPS through the DDEV router with mkcert, core
  replaced by the official 34.0.2 tarball (a git clone lacks the ~20 apps the tarball
  ships, which inject into every header and into Files), `debug` forced off,
  `firstrunwizard` disabled. I claim this is representative enough for gate 0. The
  alternative is the official `nextcloud:34-apache` image (already pulled).
- **F2 re-wrapped page.** E arms do not serve `e2-editor.html` byte-identical: the
  controller extracts its `<style>` and `<body>`, drops its one module `<script>`, and
  `probe.js` (which carries Nextcloud's CSP nonce) `import()`s `e2-editor-app.js`
  after `load`. The product JS/wasm bytes are the shipped ones (hashed in the report).
  I claim this tests the shipped editor, not a proxy. Is there a way it passes where
  the real page would not, or fails where the real page would work?
- **F3 what PASS licenses.** E1 (engine scripts straight from Apache, no COEP on
  them) fails in both browsers for a browser-rule reason: a dedicated worker's script
  response must itself carry COEP. E1h passes with the scripts served by PHP.
  My inclination: E1h passing licenses "dedicated route inside Nextcloud's own
  chrome is feasible", with **how** the engine files get their headers (PHP, an
  app-shipped `.htaccess` = Apache only, or blob workers = product change) left as a
  named M3 engineering item, not a gate condition. The alternative is to demand a
  server-agnostic static path before PASS.
- **F4 C3's noise rule.** Fields that differ between A0 and A0b are reported, not
  judged. Could this rule hide a real breakage?
- **F5 nginx.** Named limit today: Apache only. DDEV can switch to `nginx-fpm`, but
  its nginx config is DDEV's generic one, not Nextcloud's documented nginx config.
  My inclination: not required for the verdict, because every header the passing
  shapes rely on is set in PHP; nginx changes only W-htaccess (dead by construction)
  and C7. Measure it or leave it as a limit?
- **F6 C7's scope.** The `.json`/`.odt`/`.data`/`.metadata` 404 is a Nextcloud
  `.htaccess` whitelist (pretty URLs on), not COEP. It bites v14's split packages.
  My inclination: observation inside gate 0, consequence written into roadmap §5.3,
  not a gate condition.
- **F7 repetition.** A arms once per browser (header policy is deterministic), E arms
  3 per browser with a fresh browser each, E0 once. Enough?

## Constraints

Read-only: do not edit any file, do not start the counted run, do not start browsers.
You may run python to read the shakedown JSON, `grep`, `git log`, and read-only
`ddev occ` / `curl` against `https://litecoreprobe.ddev.site:8443` (CA:
`~/.local/share/mkcert/rootCA.pem`).

## Answer format

```
RULING: one line per question (Q1, F1..F7): uphold / overturn / amend, and to what
WHY (for the owner, 台灣正體中文白話): ≤ 15 lines
FACT CHECK: each F-claim — confirmed / wrong (with file:line or the command you ran)
CONDITIONS: numbered, each checkable, that must hold before or after the counted run
```
