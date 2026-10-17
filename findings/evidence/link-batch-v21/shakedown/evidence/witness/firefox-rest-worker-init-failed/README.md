# Witness (§34.4): a Firefox session lost d5w, xlc and table to `WORKER_INIT_FAILED`

Committed **before** the re-run. This report is **not** judged as evidence. It has been moved out of `../../item1/`, because the judge takes one report per (browser, arm).

## The run

- `run_v21_shakedown_item1.py --browser firefox --arms d2p,d8,d8red,d11a,d11b,d11c,d12,d5w,xlc,table,d6 --rounds 3`, 2026-10-17 07:55–08:48, Firefox 157.0.1, one browser session for the whole invocation.
- Files: `report-firefox-…-20261017T075528.json`, `docs/firefox-20261017T075528/`, `run-firefox-rest.log`.
- `judge-preview-with-this-report.txt` is the item-1 judge over `../../item1/` with this report still in it.

## What happened

- **Loads 1–44 were fine.** These are d2p, d8, d8red, d11a (page `v21host`), d11b, d11c and d12 (page `v21hook`), and d5w round 1 (`v20`, then `v21`). Every round was done. In the preview, D2′, D8, D11a, D11b, D11c and D12 read PASS for Firefox.
- **From load 45 on, every load failed.** The first was d5w round 2 on `v20`. On each one, the engine's init failed: `#s-*` read `recoverable-error`, with the toast `WORKER_INIT_FAILED：abort@…/profiles/e2-editor-v2x/probe.js:7:20337 / instantiateArrayBuffer@…:7:21105`. The pages were `v20` (port 43317) and `v21` (port 46007). The start state then read `not-observed: no selection reported within 10.0 s` [observed: the report's `open.settled`].
- **The session never recovered.** d5w rounds 2–3 (4 loads), xlc (9) and table (3) were all lost. As a result D5-w reads NOT_ESTABLISHED, and the records R-xlc and R-table are empty.

## Why this is the harness, not the product

- **[observed]** The same page, in its own Firefox session (`../../item1/report-firefox-d1-20261017T071208.json`), loaded 120 times without one init failure.
- **[observed]** The session that failed had loaded five origins: v21, dist0224, v21host, v21hook and v20, each from its own mirror server. Pages `v21host` and `v21hook` carry the runner's instruments (the host shim and S-3's page hook).
- **[observed]** The failure is an allocation abort in `instantiateArrayBuffer`. That is the shape of finding 024: Firefox reclaims the engine workers of a page navigated away from only lazily, so memory runs out after N navigations. Finding 024 records it as fixed in Nightly 155, and this is 157.0.1.
- **[inferred]** Some navigation in this mix still leaves an engine unreclaimed, so its memory accumulates within one session. Which navigation, and whether the instruments hold the session, is **not measured**. A user does not navigate one tab across five instrumented origins.
- **[observed]** Chrome ran the same 11 arms in one session (`../../item1/report-chrome-d2p-…-20261017T062254.json`) without a failure.

## The remedy (procedural; no tool is edited)

The runner is unchanged. Its arms are re-run in **three fresh Firefox sessions**, so that no session repeats this mix:

- A: `d2p,d8,d8red,d11b` (v21, dist0224);
- B: `d11a,d11c,d12` (v21host, v21hook; 9 loads);
- C: `d5w,xlc,table,d6` (v20, v21).

The re-run reports are the ones judged. The good rounds of d2p–d12 here are re-measured, not reused: the judge reads one report per (browser, arm), and evidence files are not split.

Tally: tools modified because of execution, unchanged by this witness; runs lost to the harness and re-run, +1.
