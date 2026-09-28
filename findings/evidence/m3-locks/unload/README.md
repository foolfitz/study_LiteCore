# Releasing the lock when the page goes away — what reached the server

2026-09-28. Found by the first K1 shakedown (`../shakedown/2026-09-28T103223+0000.json`):
everything in the arm passed except the release. After navigating from the editor to
Files, the lock was still there 15 s later. The Apache access log shows **no UNLOCK
from the browser at all**, and CDP recorded two `net::ERR_ABORTED` fetches on the DAV URL.

The host sent one `fetch(…, { method: 'UNLOCK', keepalive: true })` from `pagehide`.

Every arm below runs against the `litecore` ddev instance, with a fresh browser per
repetition. "Released" means that a server-side PROPFIND 4–7 s after the navigation shows
`nc:lock` empty, and that the same PROPFIND before the navigation showed `1`. That
before-check is the positive control; `unlock_exp.py`'s first version lacked it, and its
LOCK was actually a 500 caused by the script itself. "Arrived" means the request's nonce
is in `/var/log/apache2/access.log`.

**Raw output.** Only `unlock_exp10.out` was kept. The other rows are transcribed from the
session's console output, and the scripts are here to be rerun. They import helpers from
`check_m3_locks.py`, the version before the host sent UNLOCK twice.

| script | page | browser | what `pagehide` (or the named event) sends | result |
| --- | --- | --- | --- | --- |
| exp3 | Files | Chrome 151 headless, CDP `Page.navigate` | one keepalive UNLOCK | released **0/4** |
| exp3 | Files | same | keepalive GET, then keepalive UNLOCK | released 3/4 |
| exp4 | Files | same | one `sendBeacon` POST | arrived **0/4** |
| exp4 | Files | Firefox 156, WebDriver | one `sendBeacon` POST | arrived 4/4 |
| exp4 | Files | Firefox 156 | one keepalive UNLOCK | released **4/4** |
| exp5 | Files | Chrome, `Network.disable` before navigating | one beacon / one UNLOCK | 0/4 / 0/4 |
| exp6 | Files | Chrome, the page navigates itself 1.5 s after the DevTools socket was closed | one beacon / one UNLOCK | 0/4 / 0/4 (the navigation itself is in the access log every time) |
| exp7 | Files | Chrome **headful** on Xvfb, detached as in exp6 | one beacon / one UNLOCK | 0/4 / 0/4 |
| exp8 | Files | Chrome headless, `Page.navigate` ×3 and `location.href` ×3 | beacons from `beforeunload`, `visibilitychange`, and `pagehide`, plus a keepalive POST from `pagehide` | the `pagehide` beacon and POST arrived 6/6; the `beforeunload` beacon 6/6; `visibilitychange` 1/6 |
| exp9 | editor | Chrome headless | the host's UNLOCK, plus the three exp8 probes | released 3/3, probes 3/3 |
| **exp10** | **editor** | **Chrome headless** | V0: the host's UNLOCK only | **0/4** |
| exp10 | editor | same | V1: V0 plus a `beforeunload` beacon | 0/4 |
| exp10 | editor | same | V2: V0 plus a `pagehide` beacon | 1/4 |
| exp10 | editor | same | V3: V0 plus a second identical `pagehide` UNLOCK | **4/4** |
| exp10 | editor | same | V4: V0 plus an UNLOCK from `beforeunload` | **4/4** |

## Reading

- The CDP Network domain, an attached DevTools session and headless mode are all
  excluded as the cause (exp5, exp6, exp7).
- Firefox delivers the single request.
- No hypothesis tried fits every row. "A lone unload request is dropped" fits exp3,
  exp4 and exp10 V0/V2/V3, but not V1: a `beforeunload` beacon plus the `pagehide`
  UNLOCK still gives 0/4. "The first request is dropped" is contradicted by exp8 and
  exp9, where the first one arrives. **The mechanism is not known.** Public descriptions
  say Chromium delivers `pagehide` beacons on navigation. So this may be specific to
  something in this setup that was not isolated: the instance, the profile flags, or
  something else.
- The host now sends the UNLOCK **twice from `pagehide`** (V3). That is chosen from
  measurement, not from an explanation. V4 was equally good, but it releases the lock in
  `beforeunload`, which can be followed by the user choosing to stay.
- K1 and K2 of the spec measure the outcome through the whole route, in both browsers.
  **Neither says anything about real users' Chrome beyond what these rows say.**
