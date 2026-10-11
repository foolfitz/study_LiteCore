# Second round — when does headless Chrome reset its certificate verifier after launch, and what makes the reset go away? Prediction (2026-10-11, before any counted launch)

Owner's choice after the first round (`../README.md`): 「A 第二輪短趟診斷」 — short launches, the first ~15 s only,
measure the early reset's rate and which change makes it disappear. Delegated to fable.

## What was read before designing the arms (Chromium source at tag `151.0.7922.169`, the Chrome on this machine)

The first round left the early reset's cause open. Reading the source gives one mechanism that produces exactly the
symptom, and it predicts a cheap discriminator:

- `ERR_CERT_VERIFIER_CHANGED` (−455) is raised when the verifier **notifies a change**: `SSLClientContext::
  OnCertVerifierChanged` → `NotifySSLConfigChanged(kCertVerifierChanged)` (`net/socket/ssl_client_socket.cc:308`);
  `SpdySessionPool::OnSSLConfigChanged` → `MakeCurrentSessionsGoingAway(ERR_CERT_VERIFIER_CHANGED)`
  (`net/spdy/spdy_session_pool.cc:470-483`); `SpdySession::StartGoingAway(kLastStreamId, status)` fails every
  **pending** stream request and every **created-but-not-yet-active** stream with that status, while active streams
  finish (`net/spdy/spdy_session.cc:1367-1416`). The socket pool refreshes each group and closes idle sockets with the
  net-log reason `"Cert verifier changed"` (`net/socket/transport_client_socket_pool.cc:53,866-889,974-1014`).
  `HttpNetworkTransaction` does not retry −455 (no case in `http_network_transaction.cc`). So a page that has a burst
  of requests queued on its HTTP/2 session at the instant of a change loses exactly the queued ones — the locks arm's
  43 of ~190 is that shape; the instance speaks HTTP/2 (curl: `2`).
- A change is notified whenever the verifier's data is replaced: `MultiThreadedCertVerifier::UpdateVerifyProcData`
  → `NotifyCertVerifierChanged` (`net/cert/multi_threaded_cert_verifier.cc:292-300`), called from
  `CertVerifierServiceFactoryImpl::UpdateVerifierServices` (`services/cert_verifier/cert_verifier_service_factory.cc:
  554`) for **every** context, after `UpdateCRLSet`, `UpdateCtLogList`, `DisableCtEnforcement`,
  `UpdateChromeRootStore`, `UpdateMtcMetadata`, **`UpdateNetworkTime`** (`:510-519`); and per context from
  `CertVerifierServiceImpl::UpdateAdditionalCertificates` and `SetCTPolicy` (`cert_verifier_service.cc:143-193`).
- **Network time reaches the verifier**: `CertVerifierServiceTimeUpdater` (created in `SystemNetworkContextManager::
  OnNetworkServiceCreated`, `chrome/browser/net/system_network_context_manager.cc:912-918`, feature
  `kCertVerificationNetworkTime` **enabled by default** on Linux, `chrome/browser/browser_features.cc:56`) forwards
  every `NetworkTimeTracker` update to `UpdateNetworkTime` (`chrome/browser/net/cert_verifier_service_time_updater.cc`).
  The tracker queries `http://clients2.google.com/time/1/current` at construction on a profile with no saved mapping
  (`QueueCheckTime(base::Seconds(0))`, `components/network_time/network_time_tracker.cc:270`; feature
  `kNetworkTimeServiceQuerying` enabled by default on Linux, `:65`, default fetch behaviour background-and-on-demand,
  `:104-107`), and the variations seed fetch also feeds it from its response `Date`
  (`components/variations/service/variations_service.cc:883`). This path is **not** gated by `--disable-component-update`.
- The NSS→profile certificate migration (`kEnableNSSCertMigration`, `components/server_certificate_database/
  server_certificate_database_service.cc:38`) is **disabled by default**; the owner's "NSS user DB load" candidate
  does not come through that path in 151.

So the hypothesis for this round is **H2: the early resets are network-time pushes** (the time query's, the seed's)
and perhaps something else not identified by reading; the instrument is built to see each reset directly, whatever
its cause, and to say what the browser had just done.

## Instrument (`probe_early_reset.py`; smoke-tested, see below)

One launch per invocation. Chrome 151 with exactly the runners' flags (`wasm_sdk_probe/tools/run_browser_probe.py:
213-223`) **plus `--log-net-log=<file>`** (every arm) and the arm's flags. The page navigates to `/status.php` on the
ddev instance as soon as CDP answers (~0.18 s after launch) and keeps 2 fetches of a 0.85 MB same-origin asset in
flight (the first round's shape) until the window ends; every `Network.loadingFailed` is recorded with its time since
launch. Then a fetch to a closed local port must fail (`net::ERR_CONNECTION_REFUSED`; positive control that failure
capture is alive in that launch). Chrome is closed via `Browser.close`; the net log is parsed into the report
(`netlog.*`): **a reset = a cluster of `SOCKET_POOL_CLOSING_SOCKET` events with reason `"Cert verifier changed"`
closer than 50 ms**, with the HTTP/2 sessions that went away within 1 s after it (by host, so "the origin's session
went away" is read, not inferred), any −455 events, the browser's own requests that completed or started within 1 s
before it (URLs recorded **without query strings**), the network-time query, `CERT_VERIFY_PROC` jobs, every host
contacted. The raw net logs (60–95 MB each, gzipped after parsing) stay in the session scratch directory, not in
evidence; the per-launch JSON carries everything the rule reads.

**Deviation from the runners' flags, and why it is acceptable.** `--log-net-log` attaches a file observer to the
network service's event log; it does not touch certificate verification, the time tracker, component updates or
request scheduling. Without it a reset is visible only when a stream happens to be in the vulnerable state (the first
round's detector; 1 hit in 3 launches), which measures the detector, not the reset. With it every reset is visible,
and the two detectors cross-check each other in the launches where a request does fail.

**Smoke runs (not counted; reports in the scratch directory except the control below):**

- `smoke-a` (16 s), `smoke-a2` (16 s): CDP ready at 0.18 s, loop at 0.3 s; ~1,900–2,100 fetches ok; net log complete
  (534k–562k events). Resets at **0.174 / 0.177 s** (17 ms after the time query completed at 0.157 / 0.171 s; one
  Google session went away) and at **2.304 / 2.337 s** (3 sockets closed, **7 HTTP/2 sessions including the
  origin's** went away; nothing of the browser's had completed in the second before it; the GCM check-in to
  `android.clients.google.com/checkin` had started ~70 ms earlier and was still in flight). `smoke-a` also had one at
  0.333 s, right after the variations seed fetch completed (0.332 s). No request-level hit in either (2 streams, no
  queue). The first smoke's control fetch used port 1 and got `ERR_UNSAFE_PORT`: fixed to a free high port.
- `smoke-b` = **`control-70s.json`** (kept, 70 s, runner flags): the same two early resets (0.175, 2.297 s) and one at
  **61.87 s** while the first round's certificate components were being installed (CRLSet 10831 and the SSL error
  assistant fetched at 61.6–61.8 s, PKI metadata after) — the net-log detector sees the reset the first round could
  only infer. **That is the positive control for the net-log detector.** The CDP detector's positive control is the
  first round's `e1-2` plus the deliberate control fetch in every launch.

So the "early reset" is at least two events: **R_a** at ~0.17 s (and the seed's at ~0.33 s), and **R_b** at ~2.3 s.
The runners' Files burst lands at ~2–3.5 s after launch; R_b is the one that matches the locks arm in time.

## Arms (`run_round.py`; interleaved e1, e2, e3, e5, e6, e1, … so a drift over the ~22 minutes spreads over every arm)

| Arm | n | Launch | Window |
|---|---|---|---|
| E1 | 20 | runners' flags | loop from ~0.3 s to 16 s |
| E2 | 8 | + `--disable-component-update` (the first round's flag) | same |
| E3 | 12 | runners' flags, **no request at all until 5 s after launch** (page stays `about:blank`), then the loop | 5 s → 21 s |
| E5 | 12 | + `--disable-features=CertVerificationNetworkTime` (no network-time push; the time query still runs) | 16 s |
| E6 | 12 | + `--disable-background-networking` (the usual automation flag: no seed, no update check, …) | 16 s |

Counts: E2 is smaller than the owner's 20 because the first round already showed the flag's component installs are
not the trigger and the source shows the time path is not gated by it; E5/E6 are the discriminators this round adds.
64 launches, one at a time, nothing else running (checked: no Chrome, the owner's Firefox idle, load 0.1).

## Predictions

| | Prediction |
|---|---|
| P0 (per launch) | ≥ 500 fetches ok; the control failure recorded; net log parsed, complete, reaching the window's end; ≥ 1 HTTP/2 session to the origin. A launch failing P0 is void; an arm with > 25 % void is void. |
| P1 (E1) | **R_b** (a reset at 1.0–6.0 s) in ≥ 90 % of launches, and in ≥ 90 % it takes the origin's HTTP/2 session away; R_a (< 1.0 s) in ≥ 90 %; **no** reset at 6–16 s. Request-level hits: some, number unknown (the loop's vulnerable state is brief); reported, not a criterion. |
| P2 (E2) | R_b in ≥ 75 % — `--disable-component-update` does not remove it. |
| P3 (E3) | R_b still present (≥ 75 %) although no request has been made — **time-triggered, not request-triggered**; **0 resets at or after the first request** (5 s) and 0 hits. |
| P4 (E5) | **No reset before 1.0 s** (R_a is the time query's push; the seed's too). **R_b persists** (≥ 75 %) — written as the prediction because R_b in the smoke runs followed no completed request and hit the page's context specifically; if R_b vanishes in E5 (0 of ≥ 12 while E1 ≥ 90 %), R_b *is* a network-time push and P4 is wrong on that half. |
| P5 (E6) | The net log shows no time query, no seed, no update check. R_a absent. R_b: no prediction — if absent, it rides on a background request (e.g. the GCM check-in); if present, it does not. |

## Reading (machine-applied by `summarize.py`; its `SUMMARY` lines are the reading; exit code is not)

- **V1** E1 R_b ≥ 90 % → the phenomenon is established under the runners' flags; otherwise the round says nothing
  about a fix and everything below is reported as observation only.
- **V2** E2 R_b ≥ 75 % → the first round's flag is not a fix.
- **V3a** E3 R_b ≥ 75 % → time-triggered. **V3b** E3 has 0 resets at/after its first request → a 5 s idle wait avoids
  every reset this instrument can see.
- **V4a** E5 has 0 early resets → R_a is the network-time push. **V4b** E5 R_b ≥ 75 % → R_b is not.
- **V5** as P5, reported.
- **Decision** (fixed now): **D1** if a flag arm (E5 or E6, ≥ 12 valid) has **0 resets** in its whole window while V1
  holds → recommend that flag in `ChromeSession.__init__`; chain prediction: 0 `ERR_CERT_VERIFIER_CHANGED` across the
  locks shakedown's 12 Chrome arms. **D2** else, if V1 holds, no late reset in any 16-s window, every R_b ≤ 4.0 s and
  V3b holds → recommend a **5 s wait after launch** in `ChromeSession.__init__` (before the first navigation), with
  its residual risk stated (time-based: a slower machine or network moves R_b later; the wait does not see it).
  **D3** otherwise → no recommendation; the red stays unexplained.
- Either D1 or D2 is a `specs/SPEC-M3-paragraph-merge.md` §34 check-machinery change: witnesses = the locks shakedown
  report (`../../../m3-locks/shakedown/2026-10-11T110140+0000.json`, the honest run that was misjudged as a product
  red) and this round's reports; ledger 因執行而修 6 → 7 (or 8 if §17.21's reserved runner opening lands first —
  `handoff/HANDOFF-2026-10-11e…md` Open 1), 因審核而修 stays 5. The decision itself is the owner's.

**If this is never done**: the first round's "not established" stands, the shakedown red stays unexplained, the
chain does not start.

**Not expected to be established here, whatever the result**: the identity of R_b's caller if neither E5 nor E6
removes it (the net log shows a change, not who asked for it); the locks arm's own time-since-launch of its failures
(its report has no timestamps on them).
