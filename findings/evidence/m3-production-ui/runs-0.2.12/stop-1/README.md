# 0.2.12 count chain, stop 1 (2026-10-11T11:37:07Z) — locks shakedown not clean, no counted run started

Chain `../chain-2026-10-11.sh` from tree `fa8b0ddb`, host 0.2.12 `b245ae7`, page `8909564e…`. Shakedown
`page_honesty` clean (`../../../m3-page-honesty/shakedown/2026-10-11T104128+0000.json`). Shakedown `locks`
(`../../../m3-locks/shakedown/2026-10-11T110140+0000.json`) **21 of 22 arms passed; `readonly` (K9′) on Chrome 0/1**
→ `STOP`, as the chain is written to. Nothing counted ran; no product or runner byte changed.

The one red arm, read from the report (`runs[]`, arm `readonly`, browser `chrome`, started 11:33:04Z): reset upload
204, grant 200, login 200 (dashboard); the Files page `/apps/files/files?dir=/` loaded (`readyState: complete`) but
listed nothing (`rows: 0`, body text 24 characters) for 60.29 s, then the click on the missing row threw (`fatal`).
The runner's `filesRowDiagnostic` (added after finding 112) recorded the browser side: **43 `Network.loadingFailed`,
every one `net::ERR_CERT_VERIFIER_CHANGED`** (Files' and core's scripts and l10n bundles), and the consequences as
page exceptions (`ReferenceError: OC is not defined`, …). Firefox's same arm passed; every other arm passed in both
browsers.

Observed: the user's NSS database (`~/.pki/nssdb`) was last modified 2026-07-26. The runner launches Chrome with a
fresh `--user-data-dir` and no `--disable-component-update` (`tools/run_browser_probe.py:213-223`).

Hypothesis (not measured): Chrome's component updater installs a certificate component (root store / PKI metadata /
CRLSet) into the fresh profile some time after launch; installing it resets the certificate verifier and every request
in flight fails with `ERR_CERT_VERIFIER_CHANGED`. Finding 112 (2026-10-06, the same Files-page shape, no browser-side
evidence then) is probably the same event. Diagnosis: `../../../112/cert-verifier/` (owner chose 「A 先診斷再重跑」).
