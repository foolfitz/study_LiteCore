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
