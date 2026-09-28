# Adversarial review (opus, read-only), 2026-09-28 — and what was done with it

Scope: spec §3–§4, the host (`litecore` `4bd24e1`), `check_m3_locks.py` as of `a7074cc3`,
and the step-0 and unload evidence. The reviewer made no HTTP requests, ran no browser and
ran no `ddev`: a shakedown was using the instance at the time. Before adopting any
finding, the main session re-read the source it cites. Findings marked "verified" below
were re-checked that way. "Measured" means the shakedown data confirms it.

| # | finding (reviewer's severity) | status here | disposition |
| --- | --- | --- | --- |
| 1 | HIGH: a token-lock refresh does not extend the lock. `LockBackend::lock` resets ttl to the request's Timeout and `creation` is never updated, so the lock expires at creation + 300. | **verified and measured**: Firefox K3 in `shakedown/2026-09-28T112341+0000.json` gave `refreshes [200,200,200,200,400]`, exactly as predicted | Host sends `Timeout: Second-(elapsed + 300)`. Finding 101. |
| 2 | MED: K2′, K4 and K8 cannot tell whether the page died or froze (the lock expired at 300 s either way) | follows from 1 | With 1 fixed, those arms discriminate again. Added: K2′ checks the tab or window is gone; K4 checks the processes are gone; K8 checks no refresh happened inside the freeze window. |
| 3 | MED: a refused OCS unlock still moves the ETag (`LockService::unlockFile` runs `propagateEtag` before the permission check), and then the host drops a live token | **verified** (source) | Host: on a 412 while carrying the token, check `lockdiscovery` first, and drop the token only if it is gone. New arm K12 drives exactly this. |
| 4 | MED: a counted verdict is not bound to the host code | verified | Counted run refuses a dirty host repo; strict scoring requires `hostDirty` empty; controller and template are now hashed too. |
| 5 | MED-LOW: If-Match and If are judged only from the host's own record | verified | Chrome: request headers taken from CDP (`wire()`). K1, K6, K7, K11 and K12 check If-Match equals the recorded value and If equals the server's token exactly when expected; also that LOCK precedes GET on the wire. |
| 6 | MED-LOW: `saveOnce` throws on an unknown ETag before reaching the copy/strand path | verified (code) | Host: an unknown version goes to the copy path instead. |
| 7 | MED-LOW: clicking download clears the leave guard, but a cancelled "Save as" loses the bytes | verified (code) | Host: the download no longer clears the guard; only a later successful save does. The K10 row is revised to match. |
| 8 | LOW-MED: a save still in flight is not guarded on leaving | plausible | Host: the guard also covers saves in flight. Not measured (named). |
| 9 | LOW: K11 never has a refresh during the outage | verified (data: `refreshes: []`) | K11 now stays offline until a refresh has failed on the network, and requires the lock to be still held. |
| 10 | LOW: a refresh answered 5xx, 401 or 429 drops a live token | verified (code) | Host: the lock counts as lost only on 400, 404, 409, 412 or 423. |
| 11 | LOW: another LiteCore user's token lock shows as "LiteCore" | verified (source: `LockService` display name = `<d:owner>`) | Host: `<d:owner>` carries the user's display name. Not driven by an arm (K5 uses a user lock). |
| 12 | LOW: LOCK answers 200 with a token that does not exist when the user already holds their own user lock | source-plausible | Host: after a 200, check the token is in `lockdiscovery`; if not, it is not held. Not driven. |
| 13 | LOW: the second UNLOCK is answered 500 (or 204 on a race), not 412 as the comment says | source-plausible; Firefox access log shows 204 + 204 | Comment and spec reworded; nothing relies on the status. |
| 14 | LOW: red cases can pass vacuously, and several claims have no mutation | verified | `--red-cases` now fails on a missing run; mutations are added for the named claims and run on both browsers where applicable. |
| 15 | LOW: LOCK on a path that has disappeared creates an empty file | source-plausible | **Not changed.** Named limit (a file deleted between the route and the LOCK). |
| 16 | INFO: root cause of finding 100 | already in finding 100 | — |

The reviewer reported "no defect found" for these:
- the S3 retry overwriting someone else's change;
- a refresh or UNLOCK race bringing a lock back;
- a second UNLOCK releasing someone else's lock;
- XSS;
- the LOCK-before-GET check;
- K7's timing;
- the L1, L3, L5 and L6 claims.
