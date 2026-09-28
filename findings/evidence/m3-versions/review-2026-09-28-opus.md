# Adversarial review — M3 versions step (spec, probe V1–V7, finding 103, R1 runner/shakedown)

Reviewer: opus, read-only. Written 2026-09-28 against `dd4ea71f` (runner sha256 `67138d39…` = the one in the
shakedown report). Nothing else in the tree was edited; nothing committed. The probe (`probe_m3_versions.py`)
was **not** run: none of my hypotheses could be tested by `--only V2`/`--only V7` as coded (see D-1), so the
two allowed runs were left unused. Every claim below is tagged **[source]** (read from NC 34.0.2 tarball under
`~/Projects/Nextcloud_Apps/litecore/nextcloud`), **[report]** (read from a JSON report, field named), or
**[scorer]** (executed `score_run` on mutated copies of the shakedown in the scratchpad).

## SUMMARY

1. [BLOCKING before counted run] Rows 1, 7, 8 ("lock / refused save / leaving make no version") are satisfied by construction for the realistic failure shape. files_versions names a version `.v<mtime>`; an operation that stores a version without moving the mtime produces no new row, it just makes the "current" row (revision == mtime) serve bytes — and R1 never GETs the current row. This step's own V5 produced exactly that artifact (refused rollback left `.v<current>`; current row went 404→200). Decide before counting: GET the current row at L1 and L2 (safe; probe V1 got 404 there) and require 404, and reword rows 7/8 to what is actually observed ("no new row, mtime unchanged"), citing V1/V3 for the rest.
2. [SHOULD FIX] Restore after two writes in one second discards the second write entirely — not in the file, not in history. `Storage::rollback` stores the pre-restore content only `if (!file_exists(.v<current mtime>))` (Storage.php:369-373), and V2 measured that after a same-second pair `.v<current mtime>` exists (holding the first write). Spec §2:21-23 and README V3 row (line 45) state "the pre-restore content is kept as a version" unconditionally; §5 does not name this. Reachable from the Files UI (restore an older row). [source + report precondition, consequence not measured]. It also breaks 103's "overwritten content stays in history" when a restore, not the host's next save, follows the same-second write.
3. [SHOULD FIX] V5 is a weaker control than written. It restores `history[0]`, which V4 had already restored, so V5 restores the current row onto identical bytes (F→F; ETag unchanged is also what a successful restore of the current row would give, per the spec's own §5 inference). "File unchanged" (README:49, spec §2:25-26) is therefore no evidence; only the 500 + `ManuallyLockedException` body is. Two variables differ from V3/V4 (lock type AND current vs older row). The refused rollback also left a stray `.v<current>` (row 1790605366: GET 404 before, 200 after, both runs) — unmentioned.
4. [SHOULD FIX] The If-Match claim is still unrevised in two places: finding 102's severity row (line 8: "我們的宿主不掉資料，因為寫入一律帶 If-Match") and finding 101's severity row (line 8, same claim) — and 101's lapsed lock is precisely 103's "鎖過期" window. `SPEC-M3-host-entry.md:46-47` / H3 ("衝突不覆寫") also equates "changed elsewhere" with 412.
5. [SHOULD FIX] 103 overclaims one window: "鎖被解掉" (103:73). Every successful unlock writes a fresh `uniqid()` ETag (LockService.php:219 and :303 → propagateEtag :470-476), so the host's If-Match fails regardless of timing (K6 measured 412 on that path). Only "上鎖失敗" and "鎖過期" (expiry deletes the row without propagateEtag, :337-339) open it.
6. [SHOULD FIX] Scorer gap: S3 ≠ S2/F/S1 is never checked. A lost third edit (marker insert failed, copy = S2 bytes) scores GREEN [scorer]; `held` (check_m3_versions.py:252) silently collapses duplicate keys; `record["inserted"]` is overwritten by the second insert and never scored. The "總" row says four states.
7. [SHOULD FIX] Row 6's 412 is not pinned to the restore: nothing checks the third save's If-Match == `afterSaves.etag` (the pre-restore server ETag). A stale-before-restore If-Match scores GREEN [scorer]. One equality closes the chain (host ETag = pre-restore ETag ≠ post-restore ETag → 412).
8. [SHOULD FIX] Red cases do not exercise their own rows. Neutralising each clause in turn [scorer]: no red case depends on row 3 "one current", row 4 "ETag moved", row 5 "older == [S1,S2]" (the step's central claim — its case mutates L3 only and is caught by row 7's L4==L3), row 5 "current exists", row 6 "server == F", row 7 "L4 == L3" (caught by row 8), or the total row. "1 open: lock taken after the read" mutates the ETag, not the order. The static case is red on the shakedown for unrelated reasons (unmutated strict score already has 3 problems). Count is 45 mutation cases + static, not 46 + 1 (README:107, dd4ea71f message).
9. [SHOULD FIX] Retention is described, but the protection is misattributed and the durability is overstated. The "total" row (S1 and S2 in history) holds only until the first expire run ≥10 s after S2. `auto` keeps one version per 2 s in the first 10 s, one per 10 s up to 60 s, one per minute up to an hour (Storage.php:63-76, 762-812). S1 is 4–5 s before S2, so it gets thinned (on a cron-mode server, within ≤5 min). What actually keeps a counted batch safe is not "read within seconds" (spec:72-73). It is the job queue: one job per ajax page load (CronService.php:266-276), and a single deduped Expire job per user+filename that is re-queued at the tail on every write (JobList.php:46-78). Risk inside a batch is low [source]; say so, and say what "correct" means in time.
10. [SHOULD FIX] Counts: "8/8" for the one-byte-longer control (README:53, 103:42) is 11/11 over the three runs (4 + 4 + 3 same-second; plus one cross-second control, 143221Z #10, → 412). 23/23, 13/13, 6/6, 1/1 and the per-run 9/3, 8/4, 6/6 are correct [report].
11. [SHOULD FIX] "The current row's GET is 404" is written as a rule (spec:19, README:29-32) but the author's own data contradict it. After a same-second pair, the current row serves the first write's bytes (V2, 4/4). After V5 it serves F. Right after a restore it crashes the server. The runner's skip-the-current-row design rests on this rule (see item 1).
12. [NOTE] The X-OC-Mtime inference (README:90-91, 103:60-61) has the wrong mechanism by source. `finalizeUpload` scans with the real write time first (File.php:351), then `touch` rescans (View.php:1256-1257) with storage_mtime changed. The ETag is then recomputed by `calculateEtag`, and it can equal an old ETag only if mtime, inode and size all match an older md5-derived ETag. So the size condition is back, and the Scanner is not the mechanism.
13. [NOTE] 103's "沒辦法關掉" (103:77, spec §5) is an unproven negative. By source, a host PUT carrying `X-OC-Mtime` = a past second would make the cached storage_mtime differ from any later writer's second. Not recommended (mtime lies, `.v` name collisions), but "cannot be closed" is stronger than the reading supports.
14. [NOTE] Possible underclaim in 103 for upstream: an ETag that doesn't move is also the sync client's change-detection signal, so a second same-second write may never be downloaded (silent divergence), not only overwritten via If-Match. Unmeasured.
15. [NOTE] Smaller items: the TypeError log line (README:47) is not archived in evidence. Strict scoring does not assert hostRepo == 49cc4ab, which spec §3 names. The lock-spec anchor "宿主最後一次存檔" should be "the write whose ETag the host holds" (a pre-LOCK same-second write keeps the LOCK's uniqid). The probe docstring and V7 comment still say "same-size" and md5 (probe:24-25, 325-328). "Files 版本分頁送的就是這個請求" is read from source (confirmed below), not observed.

## Details

### 1. Rows 1/7/8 are blind, by construction, to a version written at the current mtime

- Version identity is the mtime in seconds. `LegacyVersionsBackend::createVersion` copies the file to
  `files_versions/<path>.v<getMtime()>` (LegacyVersionsBackend.php:153-166). The DAV listing has one row per
  timestamp. An operation that stores a version *without moving the mtime* therefore adds no row. It only turns
  the row whose revision == mtime (R1's "current") from GET-404 into GET-200. [source]
- `listing()` never GETs that row (check_m3_versions.py:106-110). L1 (`[True]`), L4 == L3 and L5 == L4 compare
  only `(revision, current, sha256-of-non-current)`, so such a version is invisible to rows 1, 7 and 8. The
  red cases for these rows insert a *new* non-current row (revision 1 or 9). That is a shape the real failure
  would not have.
- This is not hypothetical in this step. V5's refused rollback ran its "first create a new version" step
  (Storage.php:369-373) before the lock refused the move. It left `.v<current mtime>` behind:
  `versions-2026-09-28T142314Z.json` log "V5 before (version bytes) GET …/1565/1790605366 → 404", then
  "V5 after restore (version bytes) GET …/1790605366 → 200". The same happens in `143009Z` (row 1790605757).
- The probe *did* GET the current row in V1 (after LOCK and after UNLOCK: `GET 404`) and in V3 (after the
  refused host save: `GET 404`), so the facts are established at the HTTP layer. R1 only re-measures the
  weaker "no new row" through the page.
- Why it must be settled before counting: rows 1/7/8 are part of what `VERSIONS CORRECT` certifies. Fixing
  them afterwards is moving a criterion. Cheap options: (A) GET the current row at L1 and L2 and require 404
  (both positions are safe per V1). (B) Reword rows 7/8 to "no new row; mtime unchanged" and name the
  post-restore blind spot. GETting the current row at L4/L5 is risky, because the first GET after a restore
  is what crashed in V3/V4.
- User-visible harm of the missed shape is small: the stray version equals the current bytes. The issue is
  that the criterion claims more than it can see.

### 2. Restore after a same-second pair loses the second write (source + measured precondition)

- `Storage::rollback` (apps/files_versions/lib/Storage.php:368-373):
  `$version = 'files_versions'.$filename.'.v'.filemtime(...); if (!file_exists($version)) { copy(...) }`.
  The pre-restore content is stored **only if** no `.v<current mtime>` exists. Then `copyFileContents`
  *moves* the chosen `.v<revision>` over the file (:413-460 → `moveFromStorage`), and `touch($file,$revision)`
  (:393).
- The precondition is measured. After two writes in one second, `.v<current mtime>` exists and holds the first
  write: V2 `versions` lists the row at the current mtime with the first save's sha
  (`142314Z` V2-host: row 1790605340 = `c43b8961…` while current mtime = 1790605340; same in both runs, both ways).
- Consequence (source, not measured): restoring any older row at that moment skips storing the second write
  and then overwrites the file with the restored bytes. The second write is in neither the file nor the
  history. The Files UI offers Restore on every non-current row (`VersionEntry.vue` `v-if="!isCurrent &&
  hasUpdatePermissions"`, shipped source map), so this is user-reachable.
- For our host: if the lost write was the host's own and the page is still open, the next save gets 412
  (the restore moved the mtime to an older second) and the page's content lands in the conflict copy. So the
  loss is recovered while the page is open. A collaborator's write, or a closed page, is not recovered.
- This also qualifies 103. Take host X at t, then B's Y at t (`.v<t>` = X), then someone restores before the
  host's next save. Y is gone, so "被蓋掉的內容仍在版本歷史裡" does not hold for that interleaving.
- Suggested: qualify spec §2:21-23 and README:45 ("kept as a version *unless a version file for the current
  mtime already exists*"), and add it to §5. Consider a probe arm (V8: same-second pair, then restore the oldest
  row, then look for the second write's sha anywhere). It is upstream (files_versions), with the same root as
  103: version identity = mtime seconds.

### 3. V5 control

- `probe_m3_versions.py:295-296`: `oldest = history[0]["revision"]` read *after* V4 restored that very revision
  (:280, :285). V5 `restoredRevision` 1790605366 equals the V5 `before` mtime (14:22:46 GMT = 1790605366) in
  `142314Z`, and 1790605757 equals 14:29:17 in `143009Z` [report]. So V5 restores the current row.
- "File unchanged" (`currentSha256Before` = `currentSha256AfterRestore` = F) is what a *successful* restore of
  the current row would also give. The unchanged ETag (`6aba7844229f6` before and after) is also what a
  successful one gives: the spec's own §5 inference, confirmed by source in "sound" below. So only the status
  (500) and the body (`OCP\Lock\ManuallyLockedException`) carry the conclusion. They do carry it, and the
  refusal site (`LockWrapper` :174, via the lock taken in `copyFileContents`) is independent of which row is
  restored. So the conclusion "the restore path refuses under a user lock" survives. The wording and the
  "two variables differ" point do not.
- Side effect to record: the refused rollback leaves `.v<current mtime>`, because the exception skips
  `elseif ($versionCreated) deleteVersion` (Storage.php:392-399).

### 4. Unrevised If-Match claims

- `findings/102-…md:8` severity: "我們的宿主不掉資料，因為寫入一律帶 `If-Match`". 81eb8f38 revised only the
  impact bullet (:58). The bullet's closing "兩條路都不會覆寫對方的位元組" now reads as scoped by the new
  qualifier. Acceptable, but add a date-stamped note in the timeline.
- `findings/101-…md:8` severity: "資料不會掉，因為我們的寫入一律帶 If-Match". 101 is a lock that lapses silently.
  Expiry deletes the lock row without a new ETag (LockService.php:337-339; Cron/Unlock), which is exactly the
  "鎖過期" window of 103:73.
- `specs/SPEC-M3-host-entry.md:46-47` ("412（別處改過或移走）時不覆寫") and H3 (:75) assume "changed elsewhere ⇒
  412". H3 itself was safe by timing: the runner's rewrite came seconds after its own upload. The spec text
  should point to 103.
- The lock spec's revision-log statement "K12 的前提不受影響：那是 files_lock 另外寫的新 ETag，不靠 mtime" is
  **correct**: `unlockFile` calls `propagateEtag` before `unlock()`/`canUnlock` (LockService.php:286-305).

### 5. 103's "鎖被解掉" window

- Every successful unlock goes through `LockService::unlock` → `propagateEtag` (:219), or `unlockFile` →
  `propagateEtag` (:303) first. `propagateEtag` writes `'etag' => uniqid()` into the cache (:470-476). After
  that, a same-second write can only reuse the *uniqid*, not the host's ETag. The host's If-Match fails
  regardless of timing. K6 (owner OCS-unlocks, then writes) measured 412/412 on this path. Remove "鎖被解掉"
  from 103:73 (and from spec §5 if copied), keeping "上鎖失敗" and "鎖過期".

### 6. S3 is never checked to be a fourth state

- Mutation: `saves[2].sha256 = S2` and `copiesAfter[0].sha256 = S2` → `score_run` returns `[]` [scorer].
- `held = {F:…, S1:…, S2:…, S3:…}` (check_m3_versions.py:252) collapses a duplicate key, so the S2 retrieval
  check is replaced by the S3 one without notice.
- `insert_marker` writes `record["inserted"]` (check_m3_locks.py:333-338). The second call overwrites the first,
  and neither is scored. Suggest `len({F, S1, S2, S3}) == 4`, plus scoring both insert results under distinct keys.

### 7. 412 attribution

- Mutation: set the third save's recorded and wire `ifMatch` to a value ≠ `afterSaves.etag` → `[]` [scorer].
  Nothing ties the host's If-Match to the pre-restore server ETag. In the shakedown it holds (Chrome save 2
  `etag` `"d6461e30…"` = `afterSaves.etag`), and by source nothing else in R1 moves the ETag: lock refresh
  takes the "extending existing lock" branch without `propagateEtag` (LockService.php:170-177). Add
  `saves[2].attempts[0].ifMatch == afterSaves.etag` so that rows 4 + 6 prove "the restore, and only the
  restore, caused the 412".

### 8. Red-case census (each clause neutralised, all 45 cases re-scored)

| clause neutralised | red cases that turn GREEN |
|---|---|
| row 1 L1 == [current] | "1 L1 …" ×2 |
| row 3 older == [F,S1] | "3 L2 lost …" ×2 |
| row 3 exactly one current | **none** ("3 L2 no current entry" also rewrites F/S1 sha to "y") |
| row 3 authors | "3 L2 version by someone else" ×2 |
| row 4 ETag moved | **none** (no case) |
| row 5 older == [S1,S2] | **none** (the case mutates L3 only; row 7's L4==L3 catches it) |
| row 5 a current exists | **none** |
| row 6 server == F | **none** (total catches "overwrote the restore") |
| row 6 lock kept | "6 the lock was lost" ×2 |
| row 7 L4 == L3 | **none** (row 8's L5==L4 catches "refused save made a version") |
| row 7 copy listing | "7 the copy has a history" ×2 |
| row 8 released | "8 not released" ×2 |
| row 8 L5 == L4 | "8 leaving made a version" ×2 |
| total | **none** (fully implied by rows 5–8 + `one_copy`) |

- The scorer itself is sound. I mutated each of the "none" clauses in isolation, and each turns red (e.g.
  dropping only the current entry from L2 → red on `len(currents)`; `afterRestore.etag = afterSaves.etag` →
  red). What is missing is the demonstration the spec asks for ("先讓評分紅一次"). Fix: make the mutations
  consistent across the listings a real failure would touch (drop S2 from L3, L4 and L5 together; add the row
  to L4 and L5 together), and add clause-isolated cases for row 4's ETag, "one current" and the LOCK-before-GET
  order.
- Static case: `score(unmutated shakedown, strict=True)["problems"]` is already
  `['make test-e2-c-static exit None', 'chrome:versions 1/1 of 3', 'firefox:versions 1/1 of 3']`. The case is
  red without its mutation. It becomes meaningful only on a counted report. Compare against the unmutated
  baseline's problem set instead.
- Count: `RED_CASES` has 23 entries, one Chrome-only → 45 mutation×browser cases, + static = 46 lines.
  README:107 and the dd4ea71f message say 46 + 1.

### 9. Retention

- `auto` (unset `versions_retention_obligation`) → `shouldAutoExpire()` is true (Expiration.php:54-57), and
  `getAutoExpireList` applies the interval table (Storage.php:63-76, 762-812) with no quota needed
  (`getExpireList` :722-754). Labels exempt a version (:941-943); R1 sets none.
- R1 history after the restore = `.v` files S1 and S2, 4–5 s apart (shakedown: 402/407 Chrome, 437/441
  Firefox). Walking the algorithm: S2 is always kept. S1 is deleted whenever the expire job runs at
  T ≥ S2 + 10 s (interval 2, step 10). Earlier, F (10–15 s before S1) is deleted once T ≥ S1 + 60 s. So
  "S1 in the versions" lasts until the next expire run: on a system-cron server, ≤5 min.
- Scheduling [source]: `scheduleExpire` → `CronBus::queueCommand` → `JobList::add(CommandJob, serialize(Expire(uid,
  filename)))`. `add` dedupes on class + argument hash and, when the job exists, **resets `last_checked` to now**
  (JobList.php:46-78). `getNext` orders by `last_checked ASC` (:178-180). Web cron runs **one** job per request
  (CronService.php:266-276), triggered by `core-ajax-cron` on every rendered page
  (BeforeTemplateRenderedListener.php:59-61). With a fixed file name, the one Expire job is pushed to the tail
  by every R1 write. Only ~4 page loads separate consecutive pushes, far fewer than the number of jobs in the
  table, so a counted batch is very unlikely to be hit.
- Asks: correct spec:72-73 ("每一份清單都在寫入後幾秒內讀" is not the protection; the queue position is).
  Make §5 concrete: saves seconds apart are thinned to about one per 10 s / per minute / per hour at the
  next expire run. State in the verdict that "S1 and S2 retrievable" is at write time. Optionally record the
  Expire CommandJob row (`last_checked`) per run, so that a missing row can be attributed without argument.

### 10–11. Counts and the "current row is 404" rule

- One-byte-longer control, same-second [report, `trials[n].oursStat`/`theirStat` mtime field]: `142621Z` n=8–11 (4),
  `143009Z` n=8–11 (4), `143221Z` n=8, 9, 11 (3) → **11/11** conditional 204. `143221Z` n=10 is cross-second →
  412. The "8/8" matches only the first two runs, while the table header says three runs.
- "GET of the current row is 404": contradicted by V2 (`versions` right after the pair: row at the current mtime
  → 200 with the first save's bytes, 4/4), by V5 (→ 200 after the refused rollback), and by V3/V4 right
  after a restore (no response). It holds only when no `.v<current mtime>` exists.

### 12–15. Notes

- X-OC-Mtime: File.php:338 `finalizeUpload` → :351 `getUpdater()->update()` (scan with the real mtime), then
  :356-363 `touch($path, $mtime)` → View.php:1256-1257 `writeUpdate` → a second scan with a *different*
  storage_mtime → `$data['etag'] = calculateEtag()` (Local.php:220, 538-558). The Scanner reuse branch is not
  taken in either scan when the upload lands in a new second. So the inference as written ("by the Scanner reading
  it would also keep the ETag") is wrong. Delete it, or restate it as an md5 collision needing equal mtime, inode
  and size.
- "關不掉": the Scanner compares `storage_mtime` (Scanner.php:174). A host PUT with `X-OC-Mtime` = a past
  second leaves the cache at that second, so any later real write differs. That is a possible closure with bad
  side effects (displayed mtime; `.v<t>` name collisions feed item 2). "Cannot" should become "we don't".
- Only `apps/files_sharing/lib/External/Storage.php` implements `IReliableEtagStorage` in the shipped code
  (grep). Object-store primary storage has its own write path/scanner. Unchecked, and "other backends not
  checked" is honest.
- The TypeError text lives only in `nextcloud.log`, per README:47. The repo's own rule is that an error message
  should carry its payload, so archive the log line next to the reports.
- `score()` strict checks `hostDirty`/`hostFiles` presence (check_m3_versions.py:266-267) but not `hostRepo` or
  the three hashes, while spec §3 names `49cc4ab`. This is inherited from the locks runner, and the report records it.
- The lock-spec anchor: after open, the host holds the LOCK's `uniqid` ETag, and the storage_mtime is the pre-LOCK
  write. A bypass write in *that* second keeps the uniqid, and the host's first save overwrites it. It is an edge
  (the file must have been written within the second before the LOCK), but "宿主最後一次存檔" is not the
  general anchor.

## Checked and found sound

- **Finding 103's discriminator.** Across 36 V7 trials, `sameEtag` and the conditional status separate
  perfectly on `stat` mtime equality: 23 same → all identical ETags and 204; 13 cross → all changed and 412.
  `stat` mtime is the Scanner's actual input. The 204 on `If-Match` is authoritative, because Sabre compares
  against the cache ETag, and both the PUT response ETag (File.php:343 after `refreshInfo` :383) and PROPFIND
  read the cache, so which ETag was compared is no confound. PHP stat cache is not a confound either:
  Local.php:162/:282 call `clearstatcache`, and each request is its own process. The 0.3 s sleep only
  separates trials. The survivor is the late body in all 23; `theirsInHistory` is 6/6; one-more-save is 1/1.
- **Trace DAV PUT → reuse.** `File::put` → `finalizeUpload` (File.php:338) → `Updater::update` (:351 →
  Updater.php:76) → `Scanner::scan(SHALLOW, -1)` → `REUSE_ETAG|REUSE_SIZE` (Scanner.php:297-298) →
  `scanFile` reuse (:168-183). The Propagator touches parents only (Propagator.php:156-165). An existing-file
  PUT writes in place, with no part file (File.php:139-141 + Common.php:133-138), which is consistent with the
  measured constant inode.
- **LOCK/UNLOCK and V3–V5 source readings.** LOCK and UNLOCK move the ETag via `uniqid` without touching
  mtime (LockService.php:183-189, 219, 470-476); lock refresh does not move it (:170-177). `LockWrapper::isFileLocked`
  ignores `TYPE_TOKEN` (LockWrapper.php:117-134). The files_lock DAV backend maps only `files/` URIs
  (FileService.php:113-116), so the versions endpoint escapes token enforcement. `handleAppLocks` retries only
  for `text`/`richdocuments` (VersionManager.php:201-209). Rollback moves the `.v` file (Storage.php:413-460).
- **The Files UI.** The restore request is `MOVE /versions/<uid>/versions/<fileId>/<rev>` → `/versions/<uid>/restore/target`
  (`versions.ts` `restoreVersion`, shipped source map). The UI's "current" is `version.mtime === currentVersionMtime`,
  so R1's current-row definition is the UI's, not an invention, and Restore is hidden for it. The spec's §5 inference
  (restoring the current-mtime row keeps the ETag) is supported by source: the skip at :369-373, the move, then
  `touch(revision)` with storage_mtime unchanged → REUSE_ETAG. It is not reachable from the UI.
- **Facts table V1–V6.** Both full runs agree cell for cell: statuses, body sha256s, listing shapes, authors
  `admin`, V3/V4 201 with the token unchanged and mtime back to the restored revision, V3 host save 412 with no
  new row, V6 copy listing current-only and the original unchanged. The versions (files_versions 1.27.0,
  files_lock 34.0.1, NC 34.0.2) match `appinfo`.
- **Runner and scorer.** The early `return bad` is always non-empty. Every `listing()` failure path (non-207,
  missing fileid → `/versions/None`, unparsable revision → fatal) scores red. L4/L5 equality is anchored to an
  exact L3 check; the copy listing must be exactly `[current]`; a fatal run is red. The shakedown `runnerSha256`
  equals the committed runner. `--score` gives clean 1/1, 1/1; `--red-cases` gives all 45 + static red.
- **R1 timing.** A restore landing in the same second as save 2 is harmless: `.v<t>` does not exist yet, so
  S2 is stored. No other step pair in R1 can share a second.
- **Revised sentences.** The lock-spec revision-log claim about K12 is correct. The spec §5 and 103 treatment of
  restore changing the ETag ("measured in V3, V4, R1; exception inferred") is accurate.

---

## Disposition (author, 2026-09-28, before any counted run)

Each item was checked against the source or the reports it cites before acting on it.

| # | disposition |
| --- | --- |
| 1 | **Adopted.** Verified in `142314Z` / `143009Z`: after the refused V5 restore the current row's `GET` went 404 → 200 in both runs. Rows 1 and 3 now `GET` the current row (L0–L2, before any restore) and require 404; rows 7 and 8 now require "no new row and the mtime unchanged" (a `GET` there would hit the post-restore TypeError). |
| 2 | **Adopted and measured.** New probe section V8: same-second pair then restore — the second write is in neither the file nor the history, 5/5 over two runs (`151353Z`, `151613Z`); cross-second 5/5 kept. Also found: before the restore, the current row serves the first write's bytes under the second write's `Content-Length`. Finding 104. Spec §2 and §5, README V3 made conditional. |
| 3 | **Adopted.** Verified: V5 restored `history[0]`, the row V4 had already restored. V5 now restores an older row with different bytes; two runs, 500 and the file still holds the current bytes. The stray `.v<mtime>` file is recorded. |
| 4 | **Adopted.** Revised in place with a dated note: finding 101 and 102 severity rows, `SPEC-M3-host-entry.md` §3 (a paragraph after the host's approach, plus a revision row). |
| 5 | **Adopted.** Verified `LockService.php:219` (`propagateEtag` after the delete). "鎖被解掉" removed from 103's window; spec §5 says so. |
| 6 | **Adopted.** Row 2 requires F, S1, S2, S3 distinct; both marker inserts are recorded separately (`inserted1`, `inserted2`) and scored; the total row is a list, not a dict. |
| 7 | **Adopted.** Row 6 requires the third save's `If-Match` to equal the ETag after the second save. |
| 8 | **Adopted.** Red cases rewritten so each clause has a case only it catches (e.g. the extra-row case mutates L3, L4 and L5 together so rows 7/8 stay green); an order case (`lock.at` after `fetched.at`) beside the ETag case; the static case now counts only a page problem the mutation adds. The total row's S1/S2 half is implied by rows 5, 7 and 8 and has no case of its own (said in the runner). Its F half now reads the original after leaving (`serverAtEnd`), independent of row 6. |
| 9 | **Adopted.** Verified `JobList::add` (existing job: `last_checked` reset, pushed to the back). Spec §4 paragraph rewritten; "S1 and S2 retrievable" stated as a write-time property. |
| 10 | **Adopted.** 11/11 (4 + 4 + 3), plus one cross-second control at 412; README and 103 corrected. |
| 11 | **Adopted.** README "How to read a version listing" now lists the measured exceptions. |
| 12 | **Adopted as a withdrawal.** The X-OC-Mtime inference is struck through in 103 and the README; neither reading (mine or the review's) is verified. |
| 13 | **Adopted.** "關不掉" → "能不能關掉沒有研究" in 103 and spec §5. |
| 14 | **Adopted as a note** in 103, marked unmeasured. |
| 15 | **Adopted:** TypeError lines archived (`nextcloud-log-typeerror-excerpt.jsonl`); strict scoring asserts the host commit `49cc4ab`; the lock spec's anchor now names "the write whose ETag the host holds"; the probe's docstring/V7 comment fixed; "the request Files sends" marked as read from the source map. |
