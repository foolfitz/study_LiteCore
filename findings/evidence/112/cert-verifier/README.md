# Does headless Chrome reset its certificate verifier on its own after launch? — result (2026-10-11)

Prediction and reading rule: `PREDICTION.md` (committed before the counted launches, `567d15b4`, with its correction
after two smoke runs). Instrument `probe_cert_verifier.py`, arms `run-arms.sh`, log `runs.log`, reports
`e1-{1,2,3}.json` (runner flags), `e2-{1,2}.json` (+ `--disable-component-update`). Chrome 151.0.7922.169, 360 s per
launch, 2026-10-11T12:06:59Z → 12:37:07Z, nothing else running.

| Launch | fetches (ok / failed) | `ERR_CERT_VERIFIER_CHANGED` | certificate components installed (s after launch) |
|---|---|---|---|
| e1-1 | 47,254 / 0 | 0 | SSLErrorAssistant/7 63.9; CertificateRevocation/10831 64.9; PKIMetadata/1798 64.9 |
| e1-2 | 47,129 / 1 | **1, at t = 2.316 s** (12:13:03.720Z), a `Fetch`, 0.54 s after the loop started | SSLErrorAssistant/7 61.9; PKIMetadata/1798 62.9; CertificateRevocation/10831 64.9 |
| e1-3 | 47,518 / 0 | 0 | SSLErrorAssistant/7 61.8; CertificateRevocation/10831 62.8; PKIMetadata/1798 63.8 |
| e2-1 | 48,192 / 0 | 0 | none |
| e2-2 | 47,887 / 0 | 0 | none |

`chrome://components` at the end of each E1 launch: PKI Metadata 1798, CRLSet 10831, Certificate Error Assistant 7.

## Reading by PREDICTION.md

- **P0 holds**: ~47,000 fetches per launch (floor 1,000); no failure kind other than the one below.
- **P1 holds**: in every E1 launch the PKI metadata (Chrome Root Store) and CRLSet components install, at 62–65 s.
- **P3 holds**: E2 installs nothing and has 0 failures.
- **P2 does not hold**: the installs at 62–65 s hit **no** request in any of three launches, although a ~0.85 MB stream
  was in flight most of the time (~130 requests/s). The one `ERR_CERT_VERIFIER_CHANGED` seen came at **2.3 s after
  launch**, nowhere near an install.

So H1 as stated — "the component install ~1 minute after launch is what resets the verifier" — is **not supported**.
What the run does show is a verifier reset **in the first seconds after launch**, in 1 of 3 E1 launches and 0 of 2 E2
launches (too few to say whether the flag matters for it).

## Why that matches the locks shakedown

`check_m3_locks.py` starts a **fresh** `LockChrome` per arm (`run_arm`, ~:491), logs in (~:511) and opens the Files
page (~:513) right away, so the Files page's ~190-request burst falls in the first seconds after launch — the window
where e1-2's reset came — not at ~60 s. The shakedown's red arm (K9′ Chrome, started 11:33:04Z) fits the early window.
This is a match in time, not a demonstration of the same cause.

## Not established

- What the early reset is (candidates, none measured: the network service applying its initial certificate
  configuration — e.g. the user NSS store holding ddev's mkcert root, or the compiled-in root store — after the first
  connections were already made).
- Whether `--disable-component-update` prevents it (0 / 2 is no evidence either way).
- Its rate per launch (1 / 3 here; 2 known hits in the M3 record, ~1,500 Chrome opens from the Files page).

Per the reading rule ("P1 + P3 without P2 … the decision goes back to the owner"), nothing is changed.
