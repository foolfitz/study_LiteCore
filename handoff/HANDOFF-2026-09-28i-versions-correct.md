# Handoff, 2026-09-28 (i) — Versions correct; findings 103 and 104

Entry points: this file, `findings/evidence/m3-versions/RESULT.md`,
`findings/evidence/m3-versions/README.md`, `specs/SPEC-M3-versions.md`,
`findings/103-…md`, `findings/104-…md`, `findings/evidence/m3-versions/review-2026-09-28-opus.md`.

Picks up from `HANDOFF-2026-09-28h-locks-land.md`, option A (versions). The owner said
"carry on from the handoff" without picking among A/B/C; A was the only one that needs no
owner decision (no page change), so it was done. B and C are still the owner's.

## Result

Counted run `findings/evidence/m3-versions/runs/2026-09-28T152217+0000.json`:
**`VERSIONS CORRECT`**, arm R1, Chrome 151 3/3 and Firefox 156 3/3, host `litecore` `49cc4ab`
(clean), page `fbfb59a4…`, runner `ea1685d5…`. Re-scored from the stored report: same.
`--red-cases`: 68 red, nothing else. No ddev container created during the run. Page, shell
(v53), engine, profile, host: untouched.

## What happened this session, in order

1. **HTTP probe** `probe_m3_versions.py` (V1–V8; reports `versions-2026-09-28T*.json`). Our
   saves version exactly like a plain client; LOCK/UNLOCK move the ETag but add no version
   and do not move the mtime; **a restore (Files' request, no token) goes through our token
   lock**, 201, lock kept — files_lock's storage wrapper ignores `TYPE_TOKEN` locks and the
   versions endpoint is not a DAV `files/` path. Under a *user* lock the same restore is 500
   (control). The host's next save after a restore is 412 → conflict copy (K12's branch).
2. **Finding 103** (from V2, measured by V7): a write in the same wall-clock second as the
   previous one keeps the ETag (`Scanner.php:174-183` reuses it while `storage_mtime` is
   unchanged), so a PUT with the stale `If-Match` overwrites it. Same-second 23/23 overwritten,
   cross-second 13/13 412; size does not matter (11/11). The "If-Match so no data loss"
   sentence was revised in place in the lock spec, the host-entry spec, and findings 101/102.
3. **Spec** `SPEC-M3-versions.md` written and committed before the runner (`81eb8f38`).
   Host unchanged. One arm, R1.
4. **Runner** `check_m3_versions.py` (borrows the page drivers from `check_m3_locks.py`
   without editing it). First shakedown clean.
5. **Adversarial review** (opus, read-only): 15 items, all adopted after checking each
   against source or reports (disposition appended to the review file). The heavy ones: the
   "no version" rows could pass while a version file sat under the current mtime (V5 had
   left exactly that) → rows 1/3 now GET the current row and require 404; the scorer let a
   lost third edit through → four distinct states required; V5 had restored the current
   bytes onto themselves → redone. Red cases rewritten so every clause has its own case.
6. **Finding 104** (review item 2, then measured by V8): after two writes in the same second,
   any restore loses the second write for good — `Storage::rollback` saves the pre-restore
   content only if `.v<mtime>` does not exist, and after a same-second pair it does.
   Same-second 5/5 lost, cross-second 5/5 kept. Also: the current row then serves the first
   write's bytes under the second write's `Content-Length`.
7. Second shakedown clean, 68 red cases, then the counted run.
8. **Roadmap §5.3 corrected**: "169 MB cannot be an App Store tarball" is not a rule. The
   store's source default is `MAX_DOWNLOAD_SIZE = 30 MiB`, but the live store published
   `richdocumentscode` 26.4.402 (2026-09-24) whose archive is 269 MB. Whether our app gets
   the same treatment is unknown.

## State

- `study_LiteCore`: everything above committed on `main`, not pushed.
- `~/Projects/Nextcloud_Apps/litecore`: `49cc4ab`, clean, not pushed. No host change.
- Findings 103 and 104 stay on the submission freeze; both need a duplicate search, and
  103 the same security-policy check as 102 before any public issue.

## What is next — owner's choice

Roadmap §5.5 now has "versions correct" and "locks correct". What is left of M3:

- **B. Page read-only mode and the "clean" semantic** (unchanged from 09-28h). Both are
  page/shell changes → a new page identity and shell generation; the host-entry, locks and
  versions counted runs are bound to page `fbfb59a4…` and would be re-run on the new page
  (all automated, roughly an hour of runs). Worth doing both in one identity change.
- **C. Asset delivery (§5.3).** Still the bigger obstacle to installing the app anywhere
  but this ddev: v14's `.data`/`.metadata` and every `.json` are 404 through Apache's
  extension allow-list and need a PHP route or another path (the engine scripts already need
  PHP for COEP). The App Store size question is now "unknown, ask or try", not "impossible".
- **D. Small host-only hardening for 103/104** (new, optional): (1) never let two of the
  host's own saves land in the same second (wait out the second before a PUT) — removes the
  host's own contribution to 104; (2) compare the server's bytes with the last saved bytes
  before each save — narrows 103, does not close it. No page change; the lock and version
  counted runs would be re-run against the new host commit.

Standing rules: ask the owner not to start or restart other ddev projects during a counted
run (the owner started `nc-bridge` during this session, before the counted run; nothing
moved during it).
