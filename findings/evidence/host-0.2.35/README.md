# Host 0.2.35 — finding 165 repaint correction, installed and running as found

**Installed uncounted candidate**: host **858a07cfd83e8d082e22926db6b93ea886125a8c**, package **b007f950b2e18cd2**. No relink/core build. The package changes only `spreadsheet-shell/calc-editor-session.js`; **44/45** previous records are identical, including frozen Writer v22, readonly viewer v3 and cell editor v1. Host source only bumps the version label. Full K stays deferred/batched; nominal shipped host 0.2.26.

## Acceptance

Before/after visual evidence is in [finding 165](../165-calc-format-blank/README.md). The unmodified source reproduces one stale tile then a fully blank sheet, while the model changes successfully. The fix invalidates the tile scheduler before synchronously notifying the view of the new format revision.

- Mirror: Chrome N=3 + Firefox N=3, **90/90**, **36 post-format views / 936 tiles** compared byte-for-byte against direct engine rendering; content/formats, actual ODS downloads and reopen pass.
- Actual Nextcloud Files: `format-host-01/report.json`, **24/24**. Both browsers open owned ODS, exercise B/I/U via inline text selection and selected cell, compare **12 views / 336 DOM tiles** with engine rendering, save manually, GET and inspect server ODS XML, and release their own locks normally. No unrelated Writer/H7/corpus/count runs were repeated.
- Calc autosave observation: both browsers make a committed edit, then remain idle for **35,021 real ms**. Before/after host save lists remain empty; dirty stays true. The subsequent manual save succeeds (`trigger: manual`) and server XML contains the edit. This observation is bounded to that time; the source audit separately establishes that Calc has no autosave scheduler. No autosave was added in this correction. Writer's host autosave timing remains 30 s idle / 5 min cap with 3 s quiet interval; no inference from unsaved-state guarding.
- Session unit **13/13**. The first post-fix unit attempt failed only on teardown, because its new observer read an already released scheduler; it is preserved and the observer now checks ready states. The real pre-fix revision mismatch is preserved. See the finding README for exact logs.

Read existing artifacts, without a service or browser:

```bash
python3 findings/evidence/host-0.2.35/read-result.py
```

`read-result.txt` reports the above counts; it checks the server ODS XML, raw idle/save evidence, nonempty visual populations, actual project snapshots and preserved lock file-id lists. `read-result-red.txt` rejects both an empty host check population and an explicitly false host check in memory. Original evidence is not mutated.

## Packaging, installation and cleanup

An isolated host worktree was packaged with explicit `--app`; both immutable engine archive and SHA256 list were prepared before installation. Offline K0/Z0/H5-1 has zero problems and **22/22** red cases. The wrapper binds only its local candidate buildId; full K pins/BINDING/chain remain untouched. Guarded install and an engine-only functional rollback were committed before live mutation. The latter retains host label 0.2.35 and restores the archived 0.2.34 package; it was not needed/executed.

`install.txt`: preflight-only passes; installation 12:17:59–12:18:08 Asia/Taipei, fast-forward, exact package copy, occ upgrade to 0.2.35, maintenance disabled, all three unauthenticated routes 401. Existing host controllers and JavaScript are unchanged. Package archive: `build/archive/host-0.2.35-engine-b007f950b2e18cd2`, 91 package files plus attribution.

The user had already started litecore for manual testing. **litecore remains running**, matching the initial snapshot; fgp-nc/nc-bridge remain paused, all other projects stopped. No start/stop was performed. The existing lock for fileId **24674** is present both before and after; it was not unlocked, cleared or overwritten. Every test file was in a new owned folder, removed afterward. Temporary share/user/folder absence was independently checked; no global lock table write or root command occurred. Browsers and private profiles are closed/removed. The clean isolated source/package was compared to the archive, then the worktree removed; branch and archives remain.

Actual identity, lock lists and resource absence are in `post-test-identity.json`; full project state equality is in `cleanup.json`. Existing owner documents and earlier accepted manual observations are preserved. Reopening the spreadsheet loads this corrected package. Section 34.4 **+0/+0**, cumulative **47/27**: product fix/new regression, no old judge repair. Collabora's direct-input/partial-rich-text behavior is source research only; this version retains whole-cell B/I/U and manual saving.
