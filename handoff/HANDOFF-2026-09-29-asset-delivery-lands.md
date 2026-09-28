# Handoff, 2026-09-29 — Asset delivery lands; finding 105 fixed; K3 rerun

Entry points: this file, `specs/SPEC-M3-asset-delivery.md`, `findings/evidence/m3-assets/RESULT.md`,
`findings/evidence/m3-assets/README.md`, `findings/evidence/m3-assets/review-2026-09-29-opus.md`,
`findings/105-host-leaving-the-editor-in-firefox-with-the-cache-on-often-keeps-the-lock.md`,
`research/ROADMAP-2026-08-20-milestones.md` §5.3.

Picks up from `HANDOFF-2026-09-28i-versions-correct.md`. The owner picked this task in their own
words — "A. 資產派送（§5.3）" — which was option **C** in that handoff.

## Result

Counted run `findings/evidence/m3-assets/runs/2026-09-28T172628+0000.json`:
**`ASSETS DELIVERED`**, Chrome 151 3/3 and Firefox 156 3/3, host `litecore` `5e53362` (app
version 0.2.1, clean), engine buildId `9076b0b425222c0e`, address
`9076b0b425222c0e-566647db`, 22 files, 169,617,155 → 63,855,360 bytes; page
`e2-editor-app.js` `fbfb59a4…` and profile `e2-editor-v8` unchanged; runner
`check_m3_assets.py` `9e97044094f7…`. Re-scored from the stored report: same. `--red-cases`:
84 red, nothing else. `make test-e2-c-static` exit 0; `docker ps` identical before/after.

K3 (the three earlier M3 flows, repeated on `5e53362`): versions `VERSIONS CORRECT`
(`../m3-versions/runs/2026-09-28T173014+0000.json`, 68 red all red), locks `LOCKS LAND`
(`../m3-locks/runs/2026-09-28T174346+0000.json`, 87 red all red) — both hold, re-scored by
the main session. **Host entry could not run on this host or any locking host** — not a
regression (below).

## What happened this session, in order

1. **Step 0 measurement** (`dc8df23a`): the real bottleneck was not the Apache extension
   allow-list (roadmap §5.3's earlier premise) but that **cache on, every open re-fetches
   the full 169.6 MB closure** — PHP serves everything but the wasm with `no-cache` and no
   validator, and the raw 115 MB wasm exceeds Firefox's per-entry cache cap (kept ≤45 MB
   encoded, not kept at 60 MB) and Chrome's cap, which follows the profile disk's free space
   (confound: Chrome's step-0 profile was on tmpfs).
2. **Spec** (`dc8df23a`, with step 0), **host** (`7a11a4b`), **runner + packager** (`d60f9c50`): the app now packs
   its own gzip'd engine (`wasm_sdk_probe/tools/package_m3_engine.py` → `engine/`) and serves
   it through one PHP route, immutable + ETag. First shakedown hit **finding 105**: Firefox
   with the cache on often sent no UNLOCK on leaving, so the next open got `LOCK` 423.
   Host `c296d2a` moved the unlock to `beforeunload` (app version bumped to 0.2.0) and
   `8075b48` added an ETag per packaged file (closing a Chrome K2-3 red: the worker's
   `cache: "no-cache"` re-fetch of `sdk-manifest.json` now 304s).
3. **Adversarial review** (opus, read-only, 17 items, `findings/evidence/m3-assets/review-2026-09-29-opus.md`):
   13 adopted, 3 adopted in part (8, 12, 14), 1 named but not fixed (7: the guarded leave);
   disposition table at the end of the review file. Heaviest: the buildId covered decoded bodies only, not the
   served headers (CSP/COEP/Content-Type), so a header-only host change would never reach
   warm browsers — fixed by folding a serving-policy hash into the address (`5e53362`, app
   version 0.2.1). Also corrected: finding 105's mechanism (failures write the engine *into*
   a cold cache, they don't read it from a warm one) and its statistics (old host evidenced
   8/9, not 9/10; "more frequent on the new host" is only a suggestion — p≈0.11 within one
   probe, ≈0.04 only when three instruments are pooled); Firefox's cache is wiped on every logout (`Clear-Site-Data`, not previously
   in spec §5); K2-3 was rewritten so only the product's own `cache: "no-cache"` paths may
   304 on the second open (it had drifted to accepting any 304, so `immutable` wasn't being
   tested); K2-5 now reads the server's `nc:lock` itself instead of trusting the host's
   self-report.
4. **Counted run** `ASSETS DELIVERED` landed (`7e909bb4`).
5. **K3**: versions and locks re-run on `5e53362` by a sonnet executor, re-scored by the main
   session — both hold. Host entry's runner could not complete: it closes the browser without
   leaving the page, so the token lock it took stays until it lapses (~306 s) and its own next
   reset upload gets 423. The executor's read ("something actively re-locking; an orphaned
   geckodriver") was checked against the access log and is wrong — the lock is the runner's
   own HeadlessChrome. This is pre-existing (host entry's last real counted run predates the
   lock feature) and not a regression; everything it checked is now covered by versions/locks
   except H5 (page rejects a broken host), which is page behaviour and the page is unchanged
   (`5f55ee90`).
6. **Roadmap §5.3 corrected** with the 2026-09-29 result paragraph (`7e909bb4`): the premises
   "served directly by the web server" and "not through PHP" withdrawn.

## State

- `study_LiteCore`: `main`, commits `dc8df23a` through `5f55ee90` (asset delivery: 5 commits;
  versions before them: `dd4ea71f`, `820557a7`, `66656c7e`), not pushed.
- `~/Projects/Nextcloud_Apps/litecore`: `5e53362` (app version 0.2.1), clean, not pushed.
- **`engine/` is not tracked in the host's git.** After any clone or any change to
  study_LiteCore's `dist/`, run `python3 wasm_sdk_probe/tools/package_m3_engine.py` (it
  refuses to write any `.gz` over 45,000,000 bytes — Firefox's measured cache-cap
  boundary). If a new top-level entry is added to the host repo, the container needs
  `ddev nc-link` to see it.
- The ddev web container still has the **old read-only bind mount `/mnt/litecore-dist`**
  present until the owner's next `ddev restart` — the compose reference was removed, nothing
  reads the mount, but it has not been unmounted yet.
- Host JS changes require bumping `appinfo/info.xml` `<version>`, then `ddev occ upgrade`
  (K0-6 checks that the version-bump commit is not older than the last `js/` commit).
- A stray `geckodriver --port 58719` (PID 2827195, started 2026-09-28 14:03 +0800, no
  browser under it) was found and left alone — it holds no lock.
- Finding 105 is fixed on our own host (not an upstream submission item); its residual
  **guarded-leave path** (host asks "leave anyway?" — content stranded or a save in flight)
  still unlocks only at `pagehide`, unmeasured, and the Firefox-side mechanism itself has
  no minimal repro yet (see option F).

## What is next — owner's choice

- **A. Distribution channel.** App Store (K4's archive is 60.5 MiB against the store's
  30 MiB source default, but the live store has published `richdocumentscode` at 269 MB —
  ask or try) or an install-time engine download (a different, unwritten mechanism).
- **B. Install the release archive into another clean Nextcloud.** Needs either
  `litecoreprobe` or a new ddev project; a new project rebuilds the shared router, which
  404s the owner's other ddev projects briefly.
- **C. Page read-only mode and the "clean" semantic** (carried over from 09-28i's option B).
  Both are page/shell identity changes; host-entry, locks, versions and assets counted runs
  would all be re-run against the new page afterward.
- **D. Host-only hardening for findings 103/104** (carried over from 09-28i's option D):
  never let two of the host's own saves land in the same wall-clock second; compare server
  bytes to the last saved bytes before each save.
- **E. Retire or adapt the host-entry runner.** Its only check not covered elsewhere is H5
  (the page refusing a broken host); everything else is now exercised by the versions and
  locks runs.
- **F. Finding 105's unfixed guarded-leave path, plus a Firefox-only minimal repro**
  (a page with no product code, `pagehide` sending a keepalive fetch, cache on/off) — must
  include a large cacheable download just before leaving, or it likely won't reproduce.
- **G. zstd/brotli for the engine** — about 15 MB less on first open; cost is a fallback for
  clients that don't accept it (PHP has no built-in zstd/brotli decoder, unlike gzip/zlib).

Main session's lean: **B** first — it is the direct proof of the step's goal ("installable
anywhere but this ddev"), needs only the owner's OK to touch `litecoreprobe` (no new ddev
project, so no router rebuild), and would also end the old bind mount's ambiguity. **E** is a
small cleanup worth doing alongside: a counted runner that cannot run is a hole in the
regression net. A needs an outward action by the owner (asking the store).

Standing rules: don't start or restart other ddev projects during a counted run; counted
runners assume a clean host tree (they refuse to run against an uncommitted host).
