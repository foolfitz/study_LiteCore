# Handoff, 2026-09-29c — `INSTALLS ELSEWHERE`

Entry points: this file, `findings/evidence/m3-install/RESULT.md`,
`specs/SPEC-M3-install-elsewhere.md`, `research/ROADMAP-2026-08-20-milestones.md` §5.5.

Picks up from `handoff/HANDOFF-2026-09-29b-install-elsewhere-reviewed-not-counted.md`. The owner
said they were away, asked for the follow-up tasks to be run autonomously, and authorized fable
to decide anything needing a call ("我不在座位，請自主執行後續任務 / 如果有需要決策的地方，請發包給
fable，我授權它代替我裁決").

## Status

**`INSTALLS ELSEWHERE`** — counted window `findings/evidence/m3-install/runs/2026-09-29T012339+0000.json`,
no problem, 6,806 samples over 3470 s; re-scored from the stored report with the same result;
red cases 111 of 111 red. On litecoreprobe, with `litecore` installed from the release archive:
`ASSETS DELIVERED` (Chrome 3/3, Firefox 3/3), `VERSIONS CORRECT` (3/3, 3/3), host entry `LANDS`,
`LOCKS LAND` (22 cells, 52/52). Host entry also counted `LANDS` on the dev instance before the
window (`findings/evidence/m3-host-entry/runs/2026-09-29T010833Z.json`) — the first counted
host-entry run on a locking host. Both qualifiers travel with the verdict: the instance is not
fresh; "no server-side document process" excludes network services running before the window
and `docker exec`-rooted process trees.

## What happened this session, in order

1. Review 2's 15 open items implemented. Three it had left to "next session decides" (4, 12, 14)
   were **measured first**: a 25-line FastCGI client run by the container's PHP CLI makes a real
   `php-fpm: pool www` worker run a script (no HTTP, no docroot file); its `exec('… &')` child is
   adopted by PID 1 at once and inherits the worker's open file
   (`findings/evidence/m3-install/fpm-path-measurement-2026-09-29.md`). Then **fable ruled**
   (owner-authorized, read-only): Q1 C — an in-window **control 4** in a real worker; Q2 C — "no
   subreaper" becomes a per-window measured sentence on two paths, not a universal one; Q3 C
   amended — bind `wasm_sdk_probe/`'s git tree, last commit, `--untracked-files=all` porcelain
   and interpreter versions at the equivalence check, window start and end. Thirteen conditions,
   all landed (`ruling-2026-09-29-fable-controls.md`, its table says where). Commit `5a4bc239`.
2. Reinstall 2 (from nothing: app config deleted), equivalence, shakedown `003935` — everything
   new worked; two I3-7 red cases GREEN only because their messages were constant strings.
3. **Review 3** (opus, read-only, 15 items, `review-2026-09-29-opus-3.md`). Verified before
   acting. The one that mattered: I4-1b keyed processes on `lstart`, which is btime + ticks/HZ;
   btime moves with clock steps (fraction 0.80, NTP on, 3 suspends this boot), so a 0.2 s NTP
   step would have turned every sample of the hour-long window red. Now keyed on
   `/proc/<pid>/stat` field 22. Also: the baseline could whitelist an earlier orphan (now every
   baseline PID-1 descendant must start within 10 s of PID 1); control 4's excuse ran ~11 s, not
   ~5 (now ends when its request returns); the spec's reason for deleting the app config was
   false (NC 34's `app:enable` always installs; the leftover `installed_version` only picks the
   upgrade-flavoured branch — kept, reason corrected). Red cases 90 → 111. Commit `b30b58b7`.
4. Reinstall 3 (the baseline the verdict binds to), equivalence, dev host-entry counted run
   (`LANDS`, red all red), last shakedown `011402` (`--strict --red-cases` 111/111), then the
   counted window. Result commit `71e0ac8e`.

## State

- `study_LiteCore`: `main`, clean after this handoff's commit, not pushed (no `origin`; the
  `github` remote is far behind — pre-existing).
- `~/Projects/Nextcloud_Apps/litecore`: `5e53362` (0.2.1), clean, not pushed. Untouched this
  session.
- `litecoreprobe` has `litecore` 0.2.1 from the release archive (reinstall 3). Its web container
  has run since 2026-09-28T05:50:31Z; **a container restart invalidates `install.json`'s
  baseline** (I4-1b goes red on any later window until `install --reinstall`).
- Release archive `wasm_sdk_probe/build/release/litecore-0.2.1.tar.gz` (sha256 `849f29f7…`),
  gitignored; `build_m3_release.py` rebuilds it byte-identically.

## What is next — owner's choice (carried over; B and E are done)

- **A. Distribution channel.** App Store (the archive is 60.5 MiB; the store's default is 30 MiB
  but it has published `richdocumentscode` at 269 MB — ask or try) or an install-time engine
  download (unwritten mechanism). Needs an outward action by the owner.
- **C. Page read-only mode and the "clean" semantic.** Page/shell identity changes; every counted
  M3 run would be re-run against the new page.
- **D. Host-only hardening for findings 103/104**: never let two of the host's own saves land in
  the same wall-clock second; compare server bytes to the last saved bytes before each save.
  (104 is a data loss: two writes in one second, then any restore, loses the second.)
- **F. Finding 105's unfixed guarded-leave path, plus a Firefox-only minimal repro** (no product
  code, `pagehide` keepalive fetch, cache on/off, a large cacheable download just before leaving).
- **G. zstd/brotli for the engine** — ~15 MB less on first open; needs a fallback (PHP has no
  built-in zstd/brotli decoder).
- **H (new). A truly fresh instance** — the verdict's first qualifier. Needs a new ddev project,
  which rebuilds the shared router (the owner's other projects 404 briefly).

## Standing rules

- Don't start or restart other ddev projects during a counted run; any container lifecycle
  activity on the host during an install-elsewhere window turns I4-3 red.
- Counted runners refuse an uncommitted host tree; the install-elsewhere window refuses an
  uncommitted `wasm_sdk_probe/`.
- `findings/evidence/**` and `handoff/**` are English.
- Write `--strict --red-cases FILE` (argparse needs the file right after `--red-cases`).
