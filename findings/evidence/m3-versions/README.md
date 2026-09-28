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
| `versions-2026-09-28T151353Z.json` | V4, V5 (corrected, see below) and V8 (added after the review) |
| `versions-2026-09-28T151613Z.json` | V4, V5, V8 again; every V4/V5 status identical to `151353Z`, V8 as described below |
| `nextcloud-log-typeerror-excerpt.jsonl` | the server's own record of four of the version `GET`s that got no response (time, URL, exception, first trace frames), cut from `nextcloud.log` |
| `review-2026-09-28-opus.md` | the adversarial review of this step (before any counted run), with the author's disposition appended |

In `142314Z` and `143009Z`, V5 restored the row V4 had already restored, i.e. the current
bytes onto themselves (review item 3): there, "file unchanged" is no evidence of a refusal and
only the 500 and its body are. From `151353Z` on, V5 restores an older row whose bytes differ
from the current ones.

Two earlier invocations wrote no report: the probe died on a dropped connection (the
server-side crash under V3 below) before it reached the report. Each left one V3 file
behind with a live token lock; both were deleted after the lock timed out.

## How to read a version listing

`PROPFIND Depth: 1` on `/remote.php/dav/versions/<user>/versions/<fileid>` lists one entry
per version row in the database, **including one for the current content**: its
revision equals the file's mtime (epoch seconds). Every other entry is an earlier state.
A `GET` of the current row is 404 when there is no `.v<mtime>` file, which is the normal
case (V1, and every listing before a restore in R1). It is **not** a rule. Measured exceptions:

- after two writes in the same second, a `.v<mtime>` file exists and holds the **first**
  write's bytes, while the row's metadata is the second write's: the `GET` is 200 with the
  first write's bytes, and when the sizes differ, with a `Content-Length` that does not match
  them (`IncompleteRead`, V8);
- after a **refused** restore (V5), the rollback's first step has already copied the current
  content to `.v<mtime>`, so the row starts answering 200 (404 → 200 in all four V5 runs);
- right after a restore, the `GET` of the restored row gets no response (a server-side
  `TypeError`, V3, V4, V8).

## Facts (V1–V6: two runs agree, V5 as corrected in two more; V7: three runs; V8: two runs)

| # | observation | value |
| --- | --- | --- |
| V1 | history after upload, then two saves 2.5 s apart — host-like (token lock, conditional PUTs) | `[fixture, save 1]` + current = save 2 |
| V1 | the same, plain client (no lock, unconditional PUTs) | `[fixture, save 1]` + current = save 2 — **same shape** |
| V1 | `LOCK` / `UNLOCK`: ETag moves? mtime moves? version added? | yes / **no** / **no** |
| V1 | `nc:version-author` of every version, both ways | `admin` |
| V2 | two saves inside one second, both ways | the first of the two is in no version once a third save lands; right after the pair, the entry whose revision equals the current mtime serves the **first** save's bytes |
| V2 | the two same-second PUTs' ETags | **identical** (different bodies) |
| V3 | the holder's own restore (`MOVE` to `restore/target`, no token — what Files' Versions tab sends) while our token lock is held | **201**: the file now holds the restored bytes, the token lock is still there with the same token, the ETag moved, the mtime went back to the restored revision |
| V3 | the pre-restore content | kept as a version (the rollback stores it first) — **only when no `.v<current mtime>` exists**, see V8 |
| V3 | the host's next save (pre-restore `If-Match`, token) | **412**, nothing written, no version added |
| V3 | `GET` of the restored revision's entry right after the restore | **no response**: the server throws `TypeError: fwrite(): Argument #2 ($data) must be of type string, false given` (`nextcloud.log`); later the same `GET` is a plain 404 |
| V4 | a share recipient's (write permission) restore while our token lock is held | **201**, same as V3 |
| V5 | control: the recipient holds a **user** lock; the owner's restore of an older row with different bytes (`151353Z`, `151613Z`) | **500** `OCP\Lock\ManuallyLockedException`, file still holds the current bytes (a successful restore would have changed them) — the restore path does refuse under a lock, just not under a token lock |
| V5 | side effect of the refused restore | a `.v<current mtime>` file is left behind: the current row's `GET` goes 404 → 200 (4/4 runs) |
| V6 | a conflict copy (`PUT If-None-Match: *`) | 201; its listing has the current entry only; the original's history unchanged |
| V7 | someone else's write in the **same second** as ours, then our PUT with our (now stale) `If-Match` | ETag unchanged, **204: their write is overwritten** — 23/23 same-second trials over three runs |
| V7 | the same across a second boundary | ETag moved, **412** — 13/13 |
| V7 | their write one byte longer than ours (meant as a control for "same size") | no difference: 11/11 same-second (4 + 4 + 3) still share the ETag and are overwritten; the twelfth crossed a second boundary and got 412 |
| V7 | server-side `stat` of the file across every write | same inode throughout; only mtime (seconds) and size change |
| V7 | the overwritten body afterwards (`143221Z`) | in the version list 6/6; still there after one more save a second later (1/1) — but see V8: a restore instead of a save loses it |
| V8 | two writes A, B in the same second, then a restore of the oldest version | **B is in neither the file nor the history** — 5/5 over two runs; before the restore the current row serves A's bytes with B's `Content-Length` |
| V8 | the same with A and B in different seconds (1.5 s apart, 4; one 0-gap trial that crossed a boundary, 1) | A and B both kept as versions — 5/5 |

## Reading of V7 (source, then measured)

`Local::calculateEtag` hashes mtime, inode, device and size, which suggested "same second
**and** same size". The one-byte-longer arm refuted the size half. The ETag the cache keeps
comes from `lib/private/Files/Cache/Scanner.php:174-183`: when the file's `storage_mtime`
(seconds) has not changed, the scanner reuses the cached ETag (`REUSE_ETAG`) whatever the
size. So any write that lands in the same wall-clock second as the previous one leaves
the ETag as it was, and `If-Match` cannot tell the two apart. Finding 103.

## Reading of V8 (source)

Finding 104. `Storage::rollback` (`apps/files_versions/lib/Storage.php:369-373`) copies the
current content to `.v<current mtime>` **only if that file does not exist**. After a
same-second pair it does exist — `store()` wrote the first write's bytes there when the
second write came in, and `post_write_hook` then only updated the existing row's metadata
because the mtime had not moved (`Listener/FileEventsListener.php:326-347`). So the rollback
keeps nothing of the second write and moves the old version file into place.

## Reading of V3–V5 (source)

- `files_lock` `LockWrapper::isFileLocked` (`apps/files_lock/lib/Storage/LockWrapper.php`)
  reports a file as locked for `TYPE_USER` locks held by someone else and `TYPE_APP` locks
  outside their scope. A `TYPE_TOKEN` lock (the host's) is never "locked" at the storage
  layer; it is enforced only by Sabre's lock plugin on DAV `files/` paths, and the
  versions endpoint is not one. The rollback writes through the storage layer.
- `files_versions` `VersionManager::handleAppLocks` retries a refused rollback inside the
  lock's scope only for `text` and `richdocuments` app locks ("they can handle changes of
  open files"); a user lock is re-thrown, which the versions DAV endpoint answers as 500.
- The Files Versions tab offers "Restore" when the node has update permission, and sends
  exactly the `MOVE` the probe sends (`VersionEntry.vue`, `versions.ts`, both read from the
  shipped source map, not observed in a browser), and a token-locked file still shows
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
- A writer that sets the mtime (`X-OC-Mtime`, which sync clients send). The first version
  of this README inferred it would keep the ETag through the Scanner reuse; the review read
  the upload path (`finalizeUpload` scans with the real write time, then `touch` rescans)
  as recomputing the ETag with `Local::calculateEtag`, which would need the same size and
  inode too. Neither reading is verified here.
- nginx, encryption, and other storage backends: the Scanner skips the ETag reuse for storages
  that implement `IReliableEtagStorage`; which backends do was not checked.

## Arm R1 through the real page (`check_m3_versions.py`)

Spec: `specs/SPEC-M3-versions.md` §4, written and committed (`81eb8f38`) before the runner
existed. The runner borrows every page-driving helper from `check_m3_locks.py` and does not
edit it (that file's hash is bound to the LOCKS LAND counted run).

- `shakedown/2026-09-28T143951+0000.json` — one run per browser, both clean. In both:
  the listing after open holds the current entry only; after two saves it is `[F, S1]` +
  current; the restore (Files' request, no token) is 201 with the token unchanged; after
  it the listing is `[S1, S2]` + current (= F); the third save is one attempt, 412 with the
  token, and lands in a conflict copy equal to S3 whose own listing is the current entry
  only; the original still holds F; leaving releases the lock in 0.3 s (Chrome) / 0.4 s
  (Firefox) and the listing does not change. `--red-cases` against it: all 46 mutation ×
  browser cases and the static case red.
- `shakedown/2026-09-28T151943+0000.json` — after the review, with the revised runner (the
  current row fetched at L0–L2, both inserts recorded, the original read again after
  leaving): one run per browser, both clean; the current row's `GET` is 404 at L0, L1 and
  L2 in both. `--red-cases` against it: 67 mutation × browser cases and the static case, all
  red. A per-case census (each mutated run scored on its own) shows every case caught by its
  own row; the cases that trip more than one line do so where rows overlap by design (Chrome's
  wire check repeats the host record; "no copy" also empties the total row's S3 half, which
  row 6 implies). One case was fixed after the census: the third save's `If-Match` is now
  scored and mutated on the attempt level, the one the wire check compares.
