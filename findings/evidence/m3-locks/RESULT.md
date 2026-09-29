# M3 locks and permissions — result (2026-09-28)

```
$ python3 wasm_sdk_probe/tools/check_m3_locks.py --score findings/evidence/m3-locks/runs/2026-09-28T131020+0000.json
LOCKS LAND chrome:broken-then-written=3/3 chrome:closetab=1/1 chrome:crash=1/1 chrome:expired=3/3 chrome:foreign-lock=3/3 chrome:frozen=1/1 chrome:heartbeat=1/1 chrome:hold=3/3 chrome:nowhere=3/3 chrome:offline=3/3 chrome:readonly=3/3 chrome:unlock-refused=3/3 firefox:broken-then-written=3/3 firefox:closetab=1/1 firefox:crash=1/1 firefox:expired=3/3 firefox:foreign-lock=3/3 firefox:heartbeat=1/1 firefox:hold=3/3 firefox:nowhere=3/3 firefox:readonly=3/3 firefox:unlock-refused=3/3 problems=[]
```

**The `litecore` app now holds a WebDAV token lock while a file is open, keeps it alive,
and has a way out for every refused save**, in Chrome 151 and Firefox 156. Criteria:
`specs/SPEC-M3-locks-and-permissions.md` §4 (K1–K12), with every revision logged in §5
before the counted run started (the last criterion change is the post-review row; the
row added during the run only adds a named limit).

## What was measured, and against what

| | |
| --- | --- |
| counted report | `runs/2026-09-28T131020+0000.json`, 13:10:20Z → 14:07:09Z, 52 runs, the plan's full repeat counts |
| host | `litecore` app `49cc4ab5bad1…`, tree clean at run start (`hostDirty` empty); `js/litecore-editor.js` `a6c51d6a63bd…`, `EditorController.php` `52075fe1c496…`, `templates/editor.php` `49876f2b2eb2…` |
| page | `web/e2-editor-app.js` = `dist/` = `fbfb59a4…` (unchanged since the host entry); shell v53; engine, profile, link untouched |
| static | `make test-e2-c-static` exit 0 |
| runner | `check_m3_locks.py` `735c998a173f…`, byte-identical to the committed file at the time of scoring |
| red cases | `--red-cases` against this report: **87 `red`**, 0 `GREEN`, 0 `MISSING`, 0 `SKIP` (51 named mutations across their browsers, plus the static-page check) |
| environment | NC 34.0.2 tarball, `files_lock` 34.0.1 enabled by default, `lock_timeout` unset, Apache, ddev |

## Per arm

| arm | Chrome 151 | Firefox 156 | what the numbers say |
| --- | --- | --- | --- |
| **K1** hold | 3/3 | 3/3 | lock before the GET; other user sees the lock and gets 423; two saves 204 with the token and chained `If-Match` (Chrome also on the wire); navigating to Files released the lock at **0.3–0.4 s** in all six |
| **K2′** closetab | 1/1 | 1/1 | held at 291.0 s, gone at **306.3 s** in both; the editor tab (Chrome) / window (Firefox) is really gone |
| **K3** heartbeat | 1/1 | 1/1 | after 330 s idle: `nc:lock` still 1, **same token as at the start**, refreshes `[200, 200, 200, 200, 200]`, save 204 — the refresh fix for finding 101 works end to end |
| **K4** crash | 1/1 | 1/1 | held at 291.1–291.2 s, gone at **306.4–306.5 s**; no killed process left alive |
| **K5** foreign-lock | 3/3 | 3/3 | `LOCK` 423, no token, holder named; save 423 → conflict copy with the sent bytes; original untouched |
| **K6** broken-then-written | 3/3 | 3/3 | token PUT 412, token-less `If-Match` PUT 412; copy has the sent bytes; server keeps the intruder's bytes |
| **K7** expired | 3/3 | 3/3 | token PUT 412, token-less PUT 204; no copy |
| **K8** frozen | 1/1 | — | frozen from page time 3.5 s to 333.8 s; lock empty at 320 s; **zero refreshes** during the freeze; the save found the loss (412 with token, then 204 without) |
| **K9** readonly | 3/3 | 3/3 | no `LOCK` sent; PUT 403; copy in the recipient's own folder 201 |
| **K10** nowhere | 3/3 | 3/3 | PUT 403, copy 403; download bytes = sent bytes; (Chrome) leaving is still guarded after the download |
| **K11** offline | 3/3 | — | both writes fail on the wire; the refresh that failed offline kept the lock (`held` 3/3); after reconnect the second save 204 with the token |
| **K12** unlock-refused | 3/3 | 3/3 | other user's unlock 423; ETag moved, token unchanged; one PUT, 412, **no retry**; conflict copy; still held after |
| click → document opened | 2.19–2.54 s (28 runs) | 2.94–3.04 s (24 runs) | same as the host entry (2.51–2.54 / 3.01–3.08) |

**Why K2′ and K4 now discriminate and did not before.** In the pre-fix shakedown
(`shakedown/2026-09-28T112341+0000.json`) a lock lapsed at about 306 s whether or not the
page was alive, because the token-lock refresh never extended it (finding 101). In this
run K3 is the positive control: a live page still holds the **same** lock at 330 s. So
the 306 s lapse in K2′/K4 is the page being gone, not the lock dying anyway — and each of
those arms also checks directly that the page is gone.

## What led here (all in this directory)

- Step 0 (`semantics-*.json`, HTTP only) fixed the server facts the design stands on; the
  unload investigation (`unload/`) is why the host sends `UNLOCK` twice and why K2 was
  withdrawn for K2′.
- The adversarial review (`review-2026-09-28-opus.md`) found finding 101 from source and
  predicted K3's red refreshes exactly; the host fix and the other adopted rows are in
  `49cc4ab`.
- Full shakedown against `49cc4ab` (`shakedown/2026-09-28T121837+0000.json`) + the one
  Chrome K7 re-run (`…130528…`): see `README.md`. The one red cell there was the shared
  ddev-router answering 404 during another project's start; the host never ran in it.
- Counted-run rules were committed before the run (`README.md`, last section). None of
  them was needed: the run had no red.

## Findings from this step (upstream, all on the submission freeze since 2026-08-15)

- **100** — the `files_lock` OCS lock endpoint answers 500, not 423, when someone else
  holds the lock.
- **101** — a token-lock refresh does not extend the lock; it always expires at
  `creation + Timeout`. Minimal HTTP repro with a control: `semantics-2026-09-28T130648Z.json` (L8).
  Host works around it.
- **102** — the token lock accepts the holder's token from any user with write access: a
  share recipient's PUT with it is 204 and the file holds their bytes (2/2, L7). The host
  loses no data (every write carries `If-Match`; the live-token 412 branch is the one K12
  drives), but the lock only binds clients that play by the rules. Check the security
  policy before any public report.

## What this does not say (named limits, spec §3 "明確不承諾" and the review)

- A lock only stops cooperating clients (finding 102). The bypass write itself is in no arm.
- The page has no read-only mode: a read-only file can be edited; save goes to the copy.
- "Clean" is still set before the host accepts a save (a shell-level semantic, a separate step).
- An edit that was never saved is not guarded on leaving, by design.
- Closing a tab does not release the lock in either browser (Chrome's `UNLOCK` gets 401,
  Firefox sends nothing); the lock lapses by about 306 s. Reopening within that window
  shows "someone else has it open" and saves go to the copy path — named, not a bug.
- Not measured: background-tab timer throttling of the 60 s heartbeat; a page restored
  from bfcache (it does not re-lock); the in-flight-save leaving guard (S5′); `LOCK` on a
  path that vanished between the route and the lock (creates an empty file, review row 15);
  Firefox K8/K11 (no freeze or offline hook in the driver); whether 102 also holds for
  user locks; nginx, Safari, a machine with third-party apps; versions (Nextcloud's own
  file versions after our saves).

## Re-run on the page-honesty page and host 0.2.4 (2026-09-29)

SPEC-M3-page-honesty §7.6/§7.11: the page moved to `fc80050c…` (view-only mode, the leave
guard, held Ctrl+S) and the host to 0.2.4 (`369e6ed`, finding 108), so this runner was
re-counted. Bindings written before the run (`a2df684f`): `PAGE_SHA256` = `fc80050c…`. Engine package
`7f4f4e2204b4a9ec`, shell generation v54. No expectation amended.

- Shakedown: `shakedown/2026-09-29T112644+0000.json` — clean.
- **Counted: `runs/2026-09-29T142032+0000.json` — `LOCKS LAND`**, all 22 arms (K1–K12), 52 runs, no problems.
- Red cases on the counted report: `runs/red-cases-on-2026-09-29T142032.txt` — 99 red, 0 not.

Run one at a time after `PAGE HONEST` (`m3-page-honesty/RESULT.md`, which lists all six).
