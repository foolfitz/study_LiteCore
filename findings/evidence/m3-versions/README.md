# M3 versions — evidence

Step 0 of the versions step (option **A** of `handoff/HANDOFF-2026-09-28h-locks-land.md`):
what Nextcloud's own file versions look like around the `litecore` host's saves, on the
same ddev instance (Nextcloud 34.0.2 tarball, `files_versions` 1.27.0 and `files_lock`
34.0.1 shipped and enabled, `versions_retention_obligation` unset = `auto`,
`backgroundjobs_mode` unset = `ajax`). HTTP only, no browser, no product bytes involved.

Probe: `wasm_sdk_probe/tools/probe_m3_versions.py`. It reproduces the host's write pattern
(token `LOCK` with `Timeout: Second-300`, then `PUT` with `If-Match` and `If: (<token>)`)
next to a plain client doing the same writes with the same timing, and lists every
version with the sha256 of its bytes (`GET` of each version href). Every request's
status, ETag, and a body excerpt are in `log`. A second user `lcprobe` is created for
the run and deleted after it, with every file and share the probe made.

| report | what |
| --- | --- |
| `versions-2026-09-28T142314Z.json` | V1–V6, first full run |
| `versions-2026-09-28T142621Z.json` | V7 only (added after V2 of the first run), 12 trials |
| `versions-2026-09-28T143009Z.json` | V1–V7, second full run; V1–V6 identical to `142314Z` cell for cell (ids and times aside) |
| `versions-2026-09-28T143221Z.json` | V7 only, with `theirsInHistory` per trial and one more save after the last trial |

Two earlier invocations wrote no report: the probe died on a dropped connection (the
server-side crash under V3 below) before it reached the report. Each left one V3 file
behind with a live token lock; both were deleted after the lock timed out.

## How to read a version listing

`PROPFIND Depth: 1` on `/remote.php/dav/versions/<user>/versions/<fileid>` lists one entry
per version row in the database, **including one for the current content**: its
revision equals the file's mtime (epoch seconds), and a `GET` of it is 404 because there
is no `.v<mtime>` file for the current content. Every other entry is an earlier state.

## Facts (V1–V6: two runs agree; V7: three runs)

| # | observation | value |
| --- | --- | --- |
| V1 | history after upload, then two saves 2.5 s apart — host-like (token lock, conditional PUTs) | `[fixture, save 1]` + current = save 2 |
| V1 | the same, plain client (no lock, unconditional PUTs) | `[fixture, save 1]` + current = save 2 — **same shape** |
| V1 | `LOCK` / `UNLOCK`: ETag moves? mtime moves? version added? | yes / **no** / **no** |
| V1 | `nc:version-author` of every version, both ways | `admin` |
| V2 | two saves inside one second, both ways | the first of the two is in no version once a third save lands; right after the pair, the entry whose revision equals the current mtime serves the **first** save's bytes |
| V2 | the two same-second PUTs' ETags | **identical** (different bodies) |
| V3 | the holder's own restore (`MOVE` to `restore/target`, no token — what Files' Versions tab sends) while our token lock is held | **201**: the file now holds the restored bytes, the token lock is still there with the same token, the ETag moved, the mtime went back to the restored revision |
| V3 | the pre-restore content | kept as a version (the rollback stores it first) |
| V3 | the host's next save (pre-restore `If-Match`, token) | **412**, nothing written, no version added |
| V3 | `GET` of the restored revision's entry right after the restore | **no response**: the server throws `TypeError: fwrite(): Argument #2 ($data) must be of type string, false given` (`nextcloud.log`); later the same `GET` is a plain 404 |
| V4 | a share recipient's (write permission) restore while our token lock is held | **201**, same as V3 |
| V5 | control: the recipient holds a **user** lock; the owner's restore | **500** `OCP\Lock\ManuallyLockedException`, file unchanged — the restore path does refuse under a lock, just not under a token lock |
| V6 | a conflict copy (`PUT If-None-Match: *`) | 201; its listing has the current entry only; the original's history unchanged |
| V7 | someone else's write in the **same second** as ours, then our PUT with our (now stale) `If-Match` | ETag unchanged, **204: their write is overwritten** — 23/23 same-second trials over three runs |
| V7 | the same across a second boundary | ETag moved, **412** — 13/13 |
| V7 | their write one byte longer than ours (meant as a control for "same size") | no difference: 8/8 same-second still share the ETag and are overwritten |
| V7 | server-side `stat` of the file across every write | same inode throughout; only mtime (seconds) and size change |
| V7 | the overwritten body afterwards (`143221Z`) | in the version list 6/6; still there after one more save a second later (1/1) |

## Reading of V7 (source, then measured)

`Local::calculateEtag` hashes mtime, inode, device and size, which suggested "same second
**and** same size". The one-byte-longer arm refuted the size half. The ETag the cache keeps
comes from `lib/private/Files/Cache/Scanner.php:174-183`: when the file's `storage_mtime`
(seconds) has not changed, the scanner reuses the cached ETag (`REUSE_ETAG`) whatever the
size. So any write that lands in the same wall-clock second as the previous one leaves
the ETag as it was, and `If-Match` cannot tell the two apart. Finding 103.

## Reading of V3–V5 (source)

- `files_lock` `LockWrapper::isFileLocked` (`apps/files_lock/lib/Storage/LockWrapper.php`)
  reports a file as locked for `TYPE_USER` locks held by someone else and `TYPE_APP` locks
  outside their scope. A `TYPE_TOKEN` lock (the host's) is never "locked" at the storage
  layer; it is enforced only by Sabre's lock plugin on DAV `files/` paths, and the
  versions endpoint is not one. The rollback writes through the storage layer.
- `files_versions` `VersionManager::handleAppLocks` retries a refused rollback inside the
  lock's scope only for `text` and `richdocuments` app locks ("they can handle changes of
  open files"); a user lock is re-thrown, which the versions DAV endpoint answers as 500.
- The Files Versions tab offers "Restore" when the node has update permission
  (`VersionEntry.vue`, from the shipped source map), and a token-locked file still shows
  `oc:permissions` `RGDNVW` to its holder. Whether the button is in fact shown on a file
  our host holds was **not** looked at in a browser.
- Rollback on local storage **moves** the version file into place
  (`Storage::copyFileContents` → `moveFromStorage`), so the restored revision's `.v` file
  is gone from disk while its database row stays; that is the likely reason for the
  TypeError, not verified.

## Not measured here

- The retention policy (`auto`) thinning versions later: its expire job is queued on
  every version and, in `ajax` mode, runs on page loads. Every listing above was read
  within seconds of the writes.
- A writer that sets the mtime (`X-OC-Mtime`, which sync clients send) to the current
  one a second or more later; by the Scanner reading it would also keep the ETag.
- nginx, encryption, and other storage backends: the Scanner skips the ETag reuse for storages
  that implement `IReliableEtagStorage`; which backends do was not checked.
