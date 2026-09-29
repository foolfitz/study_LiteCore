# Handoff, 2026-09-30 — `ZSTD DELIVERED` on host 0.2.5, all six M3 verdicts re-counted

Entry points: this file, `findings/evidence/m3-zstd/RESULT.md` (verdict, bindings, the table of
all six counted runs), `specs/SPEC-M3-zstd.md` (criteria, predictions, §7 revision rows),
`findings/evidence/m3-zstd/review-2026-09-30-opus.md` (the review and what it found),
`findings/evidence/m3-zstd/README.md` (step 0, shakedowns, Z4).

Picks up from `handoff/HANDOFF-2026-09-29h-page-honest-counted.md`. Its "What is next": H+J still
wait for the owner; A needs the owner's outward action; this session did **G**.

## What happened this session (`study_LiteCore`, `main`, not pushed)

| Commit | What |
|---|---|
| `e2de7632` | Spec written before any code; step 0 offline sizes. Closure 63,858,483 gzip → 48,527,295 zstd (−24%). **New fact: the a11y candidate `e2-editor-v14` wasm is 47,987,197 bytes of gzip — over the packager's `MAX_GZ_BYTES` (45,000,000), so the gzip-only packager refuses that core.** As zstd it is 36,078,637. |
| `e25751b4`, `80fcf3e3` | Packager writes `.zst` (level 19, 8 MiB window, frame header parsed and checked); host 0.2.5 = `litecore` `7420418` (zstd first, gzip fallback, identity decoded from gzip; each coding its own ETag; `SERVE_POLICY` lists the codings so the address moved); scorer Z0–Z2 + a `firefox-nozstd` arm. Shakedown 1 all green, 147 red cases. |
| `2265debd` | Opus review (1 BLOCKING, 2 HEAVY, 11 LIGHT) dispositioned. **BLOCKING, confirmed by reading source: `build_m3_release.py` and install-elsewhere's `archive_records` packed `.gz` only — a 0.2.5 release would have 404'd every engine request once installed.** Now `package_m3_engine.CODINGS` / `engine_members()` derive members from the manifest; Z4-1 checks the builder's members. HEAVY: Z1-1 compares every header (CSP included) between zstd and gzip; reports carry `criteria` so old reports keep their own verdicts (0.2.4's `151106` still re-scores `ASSETS DELIVERED`). Shakedown 2 green, 156 red cases. |
| `0972b6b2` | Bindings for 0.2.5 written before any counted run; Z4-2: the builder's 0.2.5 archive is 111,711,969 bytes, 52 members, byte-identical twice. |
| `3c75b00c` | **Counted: `ZSTD DELIVERED`** (chrome, firefox, firefox-nozstd 3/3 each; first open 48.56 MB vs 63.9 MB) and **Z3**: `PAGE HONEST`, `LOCKS LAND`, `VERSIONS CORRECT`, `HOST_ENTRY LANDS`, `SAME-SECOND SAVES KEPT` on 0.2.5. Each report re-scored, red-cased, `static` read by the main session. |

All four predictions written before the runs held (P1: every request type in both browsers got
zstd — Chrome's CDP record shows all 13 page modules as zstd; P2: the Firefox pref fallback got
gzip; P3: build id unchanged, address moved; P4: 48.5 MB).

## State

- `study_LiteCore`: `main`, clean after this handoff's commit, not pushed.
- `~/Projects/Nextcloud_Apps/litecore`: `7420418` (0.2.5), clean, not pushed; dev instance upgraded
  (`ddev occ upgrade`). `engine/` (gitignored) = buildId `7f4f4e2204b4a9ec`, schema
  `litecore-engine/2`, `.gz` and `.zst` per file.
- Address is now `7f4f4e2204b4a9ec-90d7bc2c`.
- `wasm_sdk_probe/build/release/litecore-0.2.5.tar.gz` (not in git), record
  `findings/evidence/m3-zstd/release-0.2.5.json`. **`findings/evidence/m3-install/release.json` is
  still 0.2.1's** — litecoreprobe's binding reads it; do not overwrite it before the reinstall.
- `litecoreprobe`: unchanged (0.2.1).

## What is next

1. **H+J — owner picks the time.** J should now install the **0.2.5** archive (the one above, not
   0.2.4). At J: copy `release-0.2.5.json` into `release.json` as part of the reinstall, and redo
   install-elsewhere I3-1 / I3-8 — its archive check now derives members through
   `engine_members()` and its assets runs will score Z clauses.
2. **A** distribution channel (owner's outward action). The archive is now 106.5 MiB (was about
   60.5); still over the App Store source default of 30 MiB either way.
3. **F** finding 105's Firefox-only minimal repro (upstream submissions stay on hold; condition 9
   moved its premise to the pre-fix host shape).
4. Registered, not scheduled:
   - **At the a11y cutover, K0-5 (gzip ≤ 45 MB) must be re-judged**: the v14-shaped wasm's gzip
     is 48.0 MB. Browsers now get zstd (36.1 MB); gzip only goes to clients that don't take
     zstd. Decide there, with the reason written (spec §5); it was not pre-relaxed here.
   - Chrome's gzip path is not exercised by any browser run (needs CDP
     `Network.setAcceptedEncodings` on worker targets; review item 11).
   - K2-2 is still anchored to `gzBytes` (can only false-red if a file's zstd exceeds its gzip by
     ~570 B; review item 12).
   - brotli not done (would be one more row in `CODINGS` and `SERVE_POLICY`).
   - Carried over: held Enter on the save button (106); finding 108's natural rate; `e2-editor.html`
     outside the hash net (094); the shared `ChromeSession` keeps `websockets` defaults.

## Things this round taught

- **A green shakedown only covers what the records record.** Shakedown 1 was all green and would
  have counted; the review found the two holes nobody recorded — the release archive (the thing
  that ships) and the CSP on the representation browsers actually get. The review's value was
  looking at what the report did not contain.
- **A packaging rule written for one engine silently blocks the next one.** `MAX_GZ_BYTES` was
  right for v8 and refuses the a11y core; nobody had measured the candidate against it. When
  touching a rule, measure the next candidate against it too.
- **A scorer that gains clauses rewrites every past verdict unless the report says which criteria
  it was run under.** The `criteria` field keeps old reports scoring as they did, without gating on
  something the product controls (the manifest schema would have let a schema-1 manifest switch
  off the clause meant to catch it).
- **Writing predictions before the counted run made the result checkable line by line** (P1–P4),
  and the fallback arm doubled as the pref's positive control: had the pref done nothing, the rows
  would have been zstd-sized and red.

## Standing rules to carry

- Never run two M3 runners (or an M3 probe) at once — each clears the whole `oc_files_lock` table.
- Counted runners refuse an uncommitted host tree; a host JS change needs an `info.xml` version bump
  and `ddev occ upgrade` (a PHP-only change got one too this time, for the release number).
- After changing `dist/`, re-run `package_m3_engine.py` (about 50 s now: zstd level 19).
- `build_m3_release.py` rewrites `release.json` unless given `--record <elsewhere>`.
- `findings/evidence/**` and `handoff/**` are English; `specs/`, `research/`, `devlog/`, and
  findings' prose are zh-TW. Specs and gate documents are append-only.
- Don't start or restart other ddev projects during a counted run or an install window.
