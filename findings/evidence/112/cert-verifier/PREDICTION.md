# Does headless Chrome reset its certificate verifier on its own, a while after launch? — prediction (2026-10-11, before any run)

Trigger: the 0.2.12 count chain's locks shakedown, K9′ Chrome — the Files page's 43 requests all failed with
`net::ERR_CERT_VERIFIER_CHANGED` (`../../m3-production-ui/runs-0.2.12/stop-1/README.md`). Owner chose
「A 先診斷再重跑」.

**Hypothesis H1.** Chrome's component updater installs a certificate-related component (PKI metadata / Chrome Root
Store, or the CRLSet) into a fresh profile some time after launch; installing it resets the certificate verifier, and
every request in flight at that instant fails with `ERR_CERT_VERIFIER_CHANGED`. The runners launch Chrome with a fresh
`--user-data-dir` and no `--disable-component-update` (`wasm_sdk_probe/tools/run_browser_probe.py:213-223`), so every
browser a runner starts is exposed.

**Instrument.** `probe_cert_verifier.py` (this directory; standalone, imports nothing from `tools/`). It launches
Chrome 151 with exactly the runner's flags (`--headless=new --remote-debugging-port --remote-allow-origins=*
--user-data-dir=<fresh> --no-first-run --no-default-browser-check`), optionally plus `--disable-component-update`;
navigates to `https://litecore.ddev.site:8443/status.php`; keeps 4 `fetch(…, {cache: "no-store"})` of a small static
file of the same origin in flight continuously; records every `Network.loadingFailed` (wall clock, error text); and
lists the profile directory once a second, recording when each top-level entry first appears. 360 s per launch.
Positive control for the reader: the request count must be in the thousands per launch (a loop that never ran would
also show zero failures).

**Arms.** E1: runner flags, 3 launches. E2: runner flags + `--disable-component-update`, 2 launches. One at a time,
nothing else running (the chain is stopped).

| | Prediction |
|---|---|
| P1 | In every E1 launch a certificate-related component directory appears in the profile within 360 s (`PKIMetadata` and/or `CertificateRevocation`; the exact names are read from the run, not assumed) |
| P2 | In at least one E1 launch, `ERR_CERT_VERIFIER_CHANGED` failures occur, all within about 2 s of such a directory appearing |
| P3 | E2: none of those directories appears, and 0 `ERR_CERT_VERIFIER_CHANGED` |
| P0 | every launch completes ≥ 1,000 fetches (positive control); any other failure kind is listed |

**Reading.** P0 fails → the instrument is not measuring; fix it before reading anything. P1 + P2 + P3 → H1 holds: the
fix is the launch flag in `run_browser_probe.py` (a §34 change with this report and the locks shakedown report as
witnesses; 因執行而修 6 → 7), then the chain from the top. P1 + P3 without P2 → the mechanism is present but this
instrument did not catch the reset hitting a request; reported as partial, the decision goes back to the owner. P1
fails → H1 is wrong as stated; nothing is changed and the decision goes back to the owner.

**Correction (after two 20-s smoke runs of the instrument, before any counted launch):** (1) every component directory
(`PKIMetadata`, `CertificateRevocation`, `SSLErrorAssistant`, …) is created **empty at launch** (t ≈ 1.8 s), and
`chrome://components` lists every component at `0.0.0.0` / 「全新」 at 20 s — so "a directory appears" is not an
install. P1/P2 now read the **first entry appearing inside** `PKIMetadata/` or `CertificateRevocation/` (a version
directory), and the end-of-launch `chrome://components` text records the installed versions. (2) The first loop ran
~860 requests/s; the fetched file is now `/dist/workflowengine-workflowengine.js` (847,387 bytes) in 2 loops (~130
requests/s, a stream in flight most of the time). P0's floor stays 1,000 fetches per launch. Seen in passing:
`component_crx_cache/metadata.json` appears at ~10.8 s (the updater starts). Smoke reports are not kept as evidence.
