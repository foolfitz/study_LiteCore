# M3 locks and permissions — evidence

Step 0 of the locks-and-permissions step (owner's choice **A** of
`handoff/HANDOFF-2026-09-28f-host-entry-landed-shell-v53.md`): what the `litecore`
ddev instance (Nextcloud 34.0.2 tarball, `files_lock` 34.0.1 **shipped and enabled by
default**, `lock_timeout` unset = app default `-1`) actually answers. HTTP only, no
browser, no product bytes involved.

Probe: `wasm_sdk_probe/tools/probe_m3_lock_semantics.py`. Each report keeps every request's
raw status, the ETag/Lock-Token/Content-Type headers and a body excerpt (`log`), plus the
derived `facts`. A second user `lcprobe` is created for the run and deleted after it,
along with every file and share the probe made.

| report | what |
| --- | --- |
| `superseded/semantics-2026-09-28T100954Z.json` | **Probe bug, do not read facts from it.** The PROPFIND ETag was taken XML-escaped (`&quot;…&quot;`) and sent as `If-Match`, so every conditional PUT in it is a 412 about the probe, not about Nextcloud. Kept because its two 500s are real (see finding 100). |
| `semantics-2026-09-28T101145Z.json` | L1 (both ways of taking a user lock), L3, L4, P1, P2 |
| `semantics-2026-09-28T101329Z.json` | same, plus L5; L1–P2 statuses identical to `101145Z` cell for cell |
| `semantics-2026-09-28T101717Z.json` | L6 only (`--only L6`; a fourth full run hit Nextcloud's share-creation limit, HTTP 429, 20 per 10 min) |
| `semantics-2026-09-28T130648Z.json` | L7 and L8 (`--only L7 L8`), added after the review: L7 = a share recipient's refused OCS unlock of our token lock, and a PUT by that recipient carrying the holder's token; L8 = finding 101's minimal repro with the host's fix beside it as the control |
| `semantics-2026-09-28T130750Z.json` | L7 again, with the recipient's PUT sending bytes distinct from the fixture, a GET readback by the holder, and the recipient's own PROPFIND `lockdiscovery`; every L7 status identical to `130648Z` |

## Facts (L1–P2: two runs agree; L5, L6: one run)

| # | observation | status / value |
| --- | --- | --- |
| L1 | user lock (OCS `PUT /ocs/v2.php/apps/files_lock/lock/{id}` or DAV `LOCK` + `X-User-Lock: 1`) | 200 |
| L1 | **taking the lock changes the file's own ETag** | yes (both ways) |
| L1 | the holder's PUT with the post-lock ETag | 204 |
| L1 | another user's PUT | 423 |
| L1 | another user's lock attempt: OCS / DAV `X-User-Lock` | **500** / 423 |
| L1 | holder locks again (extension) — ETag changes? | 200, **no** |
| L1 | unlock — ETag changes? | 200, **yes** |
| L1 | `nc:lock-timeout` of a user lock | `-60` → never expires (`FileLock::getETA` returns infinite for timeout ≤ 0) |
| L3 | token lock (RFC 4918 `LOCK`, `Timeout: Second-8`) | 200, `Lock-Token` present, ETag changes |
| L3 | the holder's PUT without `If: (<token>)` / with it | **423** / 204 |
| L3 | refresh (`LOCK` with `If`, no body) | 200 |
| L3 | another user's PUT | 423 |
| L3 | PUT without token 12 s after the last refresh (8 s timeout) | 204 — the lock expired |
| L3 | `UNLOCK` with `Lock-Token`, then PUT without token | 204, 204 |
| L5 | a token lock as another user sees it | `nc:lock` 1, owner `admin`, owner-type `2`, timeout `300` |
| L5 | the same user's second `LOCK` (a second window) / `X-User-Lock` | 423 / 423 |
| L5 | another user's token `LOCK` / OCS unlock (not file owner) | 423 / 423 |
| L5 | **the file owner's OCS unlock of a token lock, without the token** | 200, then PUT without token 204 |
| L5 | the holder's refresh with the token that was removed | **400** (not 412) |
| L6 | token refresh / expiry — does the ETag move? | 200, **no** / **no** |
| L6 | PUT with the right `If-Match` and an **expired** token / a **removed** token | **412** / **412**, nothing written |
| L6 | then the same PUT with `If-Match` only | 204 |
| L6 | the file owner's unlock of a token lock — ETag moves? | yes |
| L4 | someone else holds a user lock: our OCS lock / DAV `X-User-Lock` / token `LOCK` / PUT | **500** / 423 / 423 / 423 |
| L4 | the file owner removes someone else's user lock (OCS DELETE) | 200 |
| P1 | read-only share of a file (`oc:permissions` `SGDN`, no `W`): recipient's PUT | 403 |
| P1 | recipient's new file next to it (their own root) | 201 |
| P1 | read-only share of a folder: PUT of the file inside / a new file inside | 403 / **403** |
| P2 | PUT over quota | 507 |

## What this settles and what it does not

- The lock has to be taken **before** the GET that records the version, or the host's
  first save is refused as a conflict with its own lock. A refresh of the same lock does
  not move the ETag; an unlock does.
- A conflict copy **next to the file** is not a universal way out: in a read-only shared
  folder it is 403, and over quota it would be 507.
- The OCS lock endpoint cannot tell "someone else holds it" from a server error (finding
  100); DAV `LOCK` can.
- **Not measured here:** what the Files UI shows for a type-2 lock and whether its
  "unlock" is offered for it; how Nextcloud Text or Office behave on a file that holds our
  lock; `keepalive` UNLOCK on page close in either browser; timer throttling of a
  heartbeat in a background tab; session expiry (401) through the browser's cookie
  session; nginx.

## L7 and L8 (added 2026-09-28, after the review)

- **L7, K12's premise, now measured (2/2):** the recipient's OCS unlock is refused (423),
  the ETag moves anyway, `nc:lock` stays `1`, and the holder's PUT with its live token
  and the pre-refusal `If-Match` gets 412. Until this run it rested on reading
  `LockService::unlockFile` only (`propagateEtag` before the permission check).
- **L7, a lock bypass (2/2, finding 102):** the recipient's token-less PUT is refused
  (423), but the same PUT carrying the **holder's** token is 204, and in `130750Z` the
  holder's GET reads back the recipient's bytes. The token is not hard to get: it is in
  the refused unlock's 423 body, and in the recipient's own PROPFIND `lockdiscovery` (207).
  RFC 4918 §6.5 treats tokens as public; §6.4 requires the server to check that the
  principal submitting one is the lock's creator. This server does not.
- **L8, finding 101 minimal (1/1):** A locked with `Second-20`, refreshed at 10.3 s with
  `Second-20`, took a token-less PUT at 22.32 s with 204 and `nc:lock` was empty. B, the
  host's fix (refresh at 10.59 s with `Second-30`), refused the same PUT at 23.2 s with
  423, lock still held — the control that A's 204 means the lock was gone, not that the
  PUT was never going to be refused.

## Shakedown against host `49cc4ab` (2026-09-28)

- `shakedown/2026-09-28T121837+0000.json` — all twelve arms, both browsers, one repeat.
  21 of 22 cells clean. **Chrome K7 is red, and the host never ran:** at 12:53:47Z the
  run's reset upload got 404, the login page got 404, the server read got 404, and the
  404 body is `404 page not found` (text/plain) — the shared ddev-router's answer when no
  route matches. The owner's other ddev project's containers (`ddev-fgp-nc-web`, `-db`)
  were **created** at 12:53:42.5Z, five seconds earlier; a project start rewrites the
  router's routes. Attributed by timing and by the response's signature, not by a
  reproduced mechanism. By the end of the same run a PROPFIND answered 207.
- `shakedown/2026-09-28T130528+0000.json` — Chrome K7 alone (`--arms expired --browsers
  chrome`), run because the first one never reached the host: clean.
- Red cases (`--red-cases`): against `121837`, 83 `red`, 0 `GREEN`, 0 `MISSING`, and the
  four Chrome K7 cases `SKIP` (their base run is the dead one); against `130528`, those
  four are `red` and the static check is `red`. Together every mutation × browser pair
  turns red once.

## Counted run: rules fixed before it started

Written before `runs/` has any report, because of the Chrome K7 cell above:

1. A counted run is judged as a whole. A red run in it is not replaced, and no report is
   edited or merged.
2. If a red run's own record shows the instance was not reachable at setup — the reset
   upload **and** the login page both got the router's `404 page not found` — the whole
   counted run is repeated, and the red report stays in `runs/` with a line here saying
   why it does not count. Any other red is read as a finding first.
3. A repeat is a new full counted run, not the missing arms.
4. No other ddev project is started or restarted while a counted run is going.


## Counted run (2026-09-28)

`runs/2026-09-28T131020+0000.json`: **`LOCKS LAND`**, 52/52 runs, no red, so none of the
rules above was invoked. Red cases against it: 87 `red`, nothing else. Read `RESULT.md`.

## Interrupted shakedown on host 0.2.6 (2026-10-05, SPEC-M3-production-ui)

`shakedown/2026-10-05T173027+0000.json` — part of a background chain that ran the six M3 runners
one at a time on host 0.2.6 `fa08307` with page `d41ae604…` (before the B1 fix). The machine shut
down at 01:43 local (17:43 UTC) during `heartbeat` in Firefox, so the report has no `score` and no
`completedAt`. The five arms it finished pass with the runner's own `score_arm`: `hold` and
`closetab` in both browsers, `heartbeat` in Chrome. Kept as the record of what ran; superseded by
the runs on host 0.2.7 and page `e97d6e03…` (SPEC-M3-production-ui §11), which are the ones that count.
