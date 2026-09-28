# Handoff, 2026-09-28 (g) — Locks host patched after review; full shakedown next

Entry points: this file, `specs/SPEC-M3-locks-and-permissions.md`,
`findings/evidence/m3-locks/README.md`, `findings/evidence/m3-locks/review-2026-09-28-opus.md`,
the app repo `~/Projects/Nextcloud_Apps/litecore`.

The owner chose **A** of 09-28f (locks and permissions next). After step 0's HTTP
measurement the owner chose token lock + timeout (RFC 4918 `LOCK`, `Timeout: Second-300`,
refresh every 60 s, `UNLOCK` on `pagehide`). Later the owner chose to withdraw K2 (tab
close releases the lock) and replace it with K2′ (the lock lapses within 300 s instead):
closing a tab does not release it in either browser — Chrome sends both `UNLOCK`s but gets
401 (no usable cookie session on tab close), Firefox sends nothing at all on window close
(`SPEC-M3-locks-and-permissions.md` §5, second row from the top).

## Done

- **Step 0** (`wasm_sdk_probe/tools/probe_m3_lock_semantics.py`, HTTP only, no browser):
  `files_lock` ships enabled by default in the NC 34.0.2 tarball; taking or removing a
  lock moves the file's own ETag, a refresh does not; a PUT with a dead token gets 412
  even with the right `If-Match`; user locks never expire by default (`nc:lock-timeout`
  `-60`); a read-only share's PUT is 403, a read-only share **folder**'s PUT (even a new
  file inside it) is 403 too; over quota is 507. Finding 100: the `files_lock` OCS lock
  endpoint answers 500, not 423, when someone else already holds the lock (`FileLock`
  object passed where `import()` wants an array). Reports:
  `findings/evidence/m3-locks/semantics-2026-09-28T101145Z.json`, `…101329Z.json`,
  `…101717Z.json`; `superseded/semantics-2026-09-28T100954Z.json` is kept only for its two
  500s (finding 100), its conditional PUTs are a probe bug (XML-escaped ETag sent as
  `If-Match`).
- **Unload investigation** (`findings/evidence/m3-locks/unload/README.md`): in Chrome 151
  a single `keepalive` `UNLOCK` sent from `pagehide` reached the server 0/4, two of them
  4/4 (exp10, on the real editor page); the mechanism is not known — CDP Network domain, an
  attached DevTools session, and headless mode were all excluded as the cause (ten
  experiments, `unload/unlock_exp3.py`–`unlock_exp10.py`). Firefox delivers the single
  request reliably. The host now sends `UNLOCK` twice from `pagehide`
  (`js/litecore-editor.js` line ~204, comment cites the 0/4 vs 4/4 split). Navigating away
  (K1, not closing the tab) released the lock in both browsers in shakedown
  `2026-09-28T110206+0000.json`.
- **Adversarial review** (opus, read-only; scope: spec §3–§4, host at `litecore` `4bd24e1`,
  `check_m3_locks.py` at `a7074cc3`, the step-0 and unload evidence; no HTTP requests, no
  browser, no `ddev` run) → full disposition table in
  `findings/evidence/m3-locks/review-2026-09-28-opus.md`. Its top finding was measured,
  not just plausible: `files_lock`'s token-lock refresh does not extend the lock —
  `LockBackend::lock`'s refresh path resets `ttl` to the request's `Timeout` but never
  touches `creation`, so the lock always expires at `creation + 300` regardless of how
  many refreshes happened (finding 101). Firefox K3 in shakedown
  `2026-09-28T112341+0000.json` gave refreshes `[200, 200, 200, 200, 400]`, exactly the
  reviewer's prediction from source alone, and `nc:lock` was already empty at the 330 s
  mark. Host fix: the refresh now sends `Timeout: Second-(elapsed since lock + 300)`.
  Other adopted fixes (spec §5, first revision-log row, and the review's disposition
  column): S3 checks `lockdiscovery` before dropping a token on 412 (a refused OCS unlock
  by someone else still moves the ETag — `LockService::unlockFile` runs `propagateEtag`
  before the permission check — which made the old host drop a live token, retry into its
  own lock (423), write a copy with a wrong "locked by someone else" message and leave the
  lock orphaned; nothing was overwritten; new arm **K12** drives exactly this); S4 saves with an unknown version go to
  the copy path instead of throwing; S5 a cancelled download no longer clears the
  leave-guard (only a later successful save does); S5′ a save still in flight also blocks
  leaving; K1's refresh loses the lock only on 400/404/409/412/423 (not on 5xx/401/429,
  which may just mean the server hasn't heard back yet); K2′/K4/K8 each gained a check
  that the page actually closed/died/froze (tab or window gone, processes gone, no refresh
  during the freeze window) since before the refresh fix those three arms could not tell a
  dead page from one whose lock merely timed out; Chrome arms (K1, K6, K7, K11, K12) now
  read `If-Match`/`If` off the wire via CDP, not only from the host's own record; a counted
  run now refuses a dirty host repo and hashes the controller and template files too, not
  only the JS. Not changed: `LOCK` on a path that has vanished between the route and the
  lock creates an empty file (named limit, `review-2026-09-28-opus.md` row 15).
- Host commits (`~/Projects/Nextcloud_Apps/litecore`, own git repo): `6f8a780` (host entry,
  09-28f), `0dcb745` (never write unconditionally), `4bd24e1` (token lock before the read,
  a way out for every refused save — this is what the review's scope covers), `49cc4ab`
  (refresh that really extends, and the review's other fixes — **current HEAD, tree
  clean**).
- Runner: `wasm_sdk_probe/tools/check_m3_locks.py` (current version's sha is recorded in
  each report's `runnerSha256`). `PLAN` (line 63) has all twelve arms:
  `hold`=K1 (3× both browsers), `closetab`=K2′ (1× both), `heartbeat`=K3 (1× both),
  `crash`=K4 (1× both), `foreign-lock`=K5 (3× both), `broken-then-written`=K6 (3× both),
  `expired`=K7 (3× both), `frozen`=K8 (1×, Chrome only), `readonly`=K9 (3× both),
  `nowhere`=K10 (3× both), `offline`=K11 (3×, Chrome only), `unlock-refused`=K12 (3× both).
  `RED_CASES` (line 974) has 51 named mutations plus a static-page check, one per claim in
  the criteria table, each asserted to find its own arm's run and turn it red
  (`red_cases()`, line 1029, fails on a MISSING run as well as on a GREEN one — a red case
  that never ran proves nothing). `main()` (line 1062) refuses a `--label counted` run
  outright if the served page's sha256 (`dist/` and `web/`) is not the spec's
  `fbfb59a4…`, or if the host repo has uncommitted changes.

## Shakedown status — none of this has run against the current host or runner

All of the following are single runs (not the counted plan's repeat counts), each read as
a shakedown, not a verdict:

- `2026-09-28T103223+0000.json` — first K1 run; everything passed except release (the
  unload finding above; fixed by sending `UNLOCK` twice).
- `2026-09-28T110206+0000.json` — K1 (hold, both browsers) and the first K2 attempt that
  led to K2 being withdrawn (closing a tab does not release in either browser).
- `2026-09-28T110600+0000.json` — K7, K9, K10, K11 passed; K5 and K6 were red, but in the
  runner itself (a borrowed HTTP client truncated response bodies at 1500 characters,
  cutting off the copy-file listing) — the runner has since been fixed to read the full
  body; host behavior in that run was correct.
- `2026-09-28T112341+0000.json` — K5, K6, K8 passed. **K3 (Firefox) was red**: finding
  101, now fixed in the host. K2′/K4 lapsed at roughly the 306 s mark in this run, but
  that measurement was **not discriminating** before the refresh fix — the old token-lock
  bug meant every lock died at 300 s regardless of whether the page was still alive, so a
  "lapsed at ~306 s" result was consistent with both a correctly-dead page and a page that
  was still running but had lost its lock anyway.

**No arm has yet run against host `49cc4ab` with the current runner. K12 has never run at
all** — it was added after the review, before any counted run.

## A self-inflicted incident, recorded

An `mv dir/$EMPTY` moved `findings/evidence/m3-host-entry/shakedown/` away during this
session. It was restored byte-identical before any commit; `git status` was clean at the
time this file was written. No commit was made while it was missing.

## State

`study_LiteCore`: tree clean at `b17df601`, not pushed. `~/Projects/Nextcloud_Apps/litecore`:
tree clean at `49cc4ab`, its own repo, not pushed. Product page `web/e2-editor-app.js` is
unchanged (`fbfb59a4…`), shell generation v53, no engine change, no link — all of this
work is in the `litecore` app and the runner only.

Session ended at a context soft limit, not at a result: the host is patched and believed
correct against every review finding, but nothing has been counted or even shaken down
against it yet.

## What is next

1. **Full shakedown, all 12 arms, both browsers, against `49cc4ab`:**
   ```
   python3 wasm_sdk_probe/tools/check_m3_locks.py --label shakedown --browsers chrome,firefox --repeats 1
   ```
   Expect roughly 75–80 minutes (K3's heartbeat alone idles 330 s, K4/K8/K11 have their
   own waits); run it in background. A sonnet executor is fine for this (per the delegation
   form in memory: long runs that bank evidence go to sonnet, diagnosis and judgement
   calls stay with fable/opus). Expect every arm green; any red is a finding to read
   before touching anything else — do not re-run hoping it clears.
2. **Red cases against that shakedown report:**
   ```
   python3 wasm_sdk_probe/tools/check_m3_locks.py --red-cases findings/evidence/m3-locks/shakedown/<that file>.json
   ```
   Every one of the 51 named mutations plus the static-page check must print `red`. A
   `MISSING` (the arm never ran) or a `GREEN` (the mutation didn't turn it red) is a
   failure to fix before counting — per `red_cases()`, a red case that never ran proves
   nothing.
3. **Optional, cheap HTTP-only confirmations** while nothing else is using the ddev
   instance (no need to block step 4 on these): the minimal repro for finding 101 listed
   in its "still needed" section (`Timeout: Second-20`, refresh at 10 s, token-less
   PUT at 22 s should be 204 if the refresh really didn't extend it); a probe arm for the
   refused-unlock-moves-the-ETag claim behind K12, source-verified only so far.
4. **Counted run:**
   ```
   python3 wasm_sdk_probe/tools/check_m3_locks.py --label counted
   ```
   Refuses on its own if the host repo is dirty or the served page is not `fbfb59a4…`.
   Roughly 80 minutes; delegate to sonnet. Then: `RESULT.md` in
   `findings/evidence/m3-locks/`, an update to
   `research/ROADMAP-2026-08-20-milestones.md` §5.4, and a handoff.
5. **Remaining named limits** (spec §3 "明確不承諾", and the review's not-driven/plausible
   rows) — not blocking, but worth carrying forward: the page has no read-only mode
   (a read-only file can still be edited, save goes through the copy path); "clean" is
   still set before the host accepts the save (a shell-level semantic, a separate step);
   an edit that was never saved is not guarded on leaving, by design; background-tab timer
   throttling of the 60 s heartbeat is believed to stay inside the 300 s window but is not
   measured; bfcache is not covered (a page restored from it does not re-lock); `LOCK` on
   a path that vanished between the route and the lock creates an empty file (not changed,
   review row 15); the in-flight-save leaving guard (S5′) is implemented but not measured
   (review row 8); reopening a file within 5 minutes of closing its tab shows the
   "someone else has it open" notice and saves go through the copy path — named, not a
   bug; findings 100 and 101 (upstream `files_lock`) stay on the submission freeze in
   place since 2026-08-15 — each finding's own "還缺什麼"
   checklist (confirm unfixed on `files_lock` main, check for GitHub duplicates) is the
   re-entry condition, not part of this milestone.
