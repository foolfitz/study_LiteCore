# M3 production UI on host 0.2.12 (C′ with findings 124 and 125) — result (2026-10-12)

Spec: `specs/SPEC-M3-production-ui.md` §17 (design §17.2, the harness port §17.3 as corrected in §17.11, criteria §17.4 as corrected in §17.9–17.10, order §17.7, results before the count §17.12–17.18, C5 (ii) §17.20 and its ruling §17.21, bindings §17.22, the stop and the launcher fix §17.23). The 0.2.11 result is `RESULT-0.2.11.md`; this file is the one for the release that carries C′ (a window-sized canvas, native scrolling, out-of-window bands expired by revision) and the fixes for findings 124 and 125 (and, through C′, 126).

## What was released

| What | Value |
|---|---|
| Shell generation | **v61** `f48df85b…`, equal to v60 but for `web/e2-editor-app.js` |
| Page / session | `8909564e…` / `62a2a20e…` (session unchanged since v58; dist = web = served) |
| Host | `litecore` **0.2.12**, `b245ae7`, clean tree (`hostDirty: []`); engine package buildId `45cdcedfc0fe7e61` (read from the counted reports' `static.buildId`); its 22 files differ from 0.2.11's only in the page (v19); 0.2.11's engine archived in `wasm_sdk_probe/build/archive/host-0.2.11-engine-b99f4b138839ff04/` |
| Runners | six M3 runners re-pinned, pin lines only (§17.22); host entry has no pins; `check_m3_production_ui.py` `c9d51781…`; `run_e2_c_product_path.py` `bd6fc0ca…` (the C5 (ii) runner, unchanged) |
| Shared launcher | `run_browser_probe.py` **`2f14d9dd…`** (was `663b2ffa…`): `ChromeSession` waits 5 s after CDP is ready, before any navigation (§17.23, finding 112). No pin names it |

## Before the count (C′ page `8909564e…`)

| Criterion | Result (spec section, evidence) |
|---|---|
| C6 | red case reproduced on the P page (finding 126); on the C′ page **8/8 DRAWN** — 40 pages at ratio 2 wide and 50 at ratio 1.5 wide draw top and bottom; the canvas is a 4,092–4,380-row window (§17.16, `../c-prime/final-page/`) |
| C1 | unit `C1-U` passes with its red cases (`../c-prime/page/unit-red-cases.txt`); run-time reading C1′ holds in 8/8 rounds, `#paper` = document height (§17.18, recorded) |
| C2 | **PASS both browsers** at ratio 2 wide (`judge_c2.py`): gap-80 commit median Chrome 17.6 / Firefox 21.4 ms (P page 43.9 / 84.5); ratio 1 P2 cells PASS (§17.17, `../c-prime/c2/`) |
| C3 / C4 | 6/6 PASS on the real page; the two red pages red in both browsers (§17.16) |
| C5 (i) | the ported net on the P page: **0 differences** against 0.2.11's counted reports, after fable's ruling B (§17.12) |
| C5 (ii) | see the §17.21 line below |
| 124-U / 125-U | page unit suite passes on `8909564e…` (124-U1–U5, 125-U1–U6 in `../release-0.2.12/test-e2-c-static-after-count.txt`); every red case red on its own tests (`../c-prime/page/unit-red-cases.txt`, committed with the page in `0ad30e73`) |
| 124-B / 125-B | **PASS both browsers**: 40 ArrowDown presses, the caret never leaves the desk; 「處理中」 never shown while `#state-pill` was `busy` ≥ 40 times (§17.16) |
| Witness | 0 red on the C′-only page and on the final page (§17.13, §17.15); the `Rdel` witness on the host build red in both browsers as predicted — the page-smoke port has its §34.4 witness (§17.22) |

**The §17.21 line**: C5 (ii): 44/47 by the committed rule, not held (§17.20); C5 (ii)′ 46/46 live mutations red + 1 dead registered (§17.21); runner `bd6fc0ca…` unchanged; ledger then 6/5; Chrome only.

Registrations carried from §17.21, each with its if-never-done default:

1. **`inline-format-rollback` is a dead mutation; its check guards behaviour that nothing exercises** (CLAUDE.md §3). If never done: the mutation stays listed as dead, and a PASS of `a-failed-format-does-not-block-the-session` is **not evidence**.
2. **`rollback`**: declaration unchanged; red = the declared check NE **and** `recoveryPairing.held == true` **and** `recovery-returns-what-the-product-promised` FAIL **and** `sessionDied.latency == 「回到檢查點 失敗」`; its runner `ok` is structurally false. If never done: judged by that reading.
3. **`geometry-declared-but-not-delivered`** counts on v12, not v14 (`requiresFlag` names no profile). If never done: run it on v12 as §17.21 says.

Drafter ledger (§17.21, CLAUDE.md §11 form; not moved into CLAUDE.md — the owner decides): the C5 (ii) flag was wrong (v14 made the geometry mutation a no-op); the `rollback` precedent of 10-09 was not carried into the prediction; the dead mutation went unnoticed since 08-19; three of my claims to fable had to be narrowed; one of fable's line citations was wrong (:9775 → :9792), caught at the cross-check.

## The first chain stopped; the launcher fix (§17.23)

The first count chain (`runs-0.2.12/chain-2026-10-11.sh`, 2026-10-11 10:41 UTC) stopped at the locks shakedown: `chrome:readonly` (K9′) found an empty Files list, 43 `net::ERR_CERT_VERIFIER_CHANGED`; no counted run started (`runs-0.2.12/stop-1/`). Two diagnoses (`../112/cert-verifier/`, `../112/cert-verifier/second-round/`) found two certificate-verifier resets in a fresh headless Chrome's first 2.5 s (max 2.421 s over 64 launches), each sweeping the origin's HTTP/2 session; delaying the first request to 5 s missed every one. The owner chose the 5-s warm-up in the shared launcher and a re-run of the whole chain. §34.4 witness: `../m3-locks/shakedown/2026-10-11T110140+0000.json`.

## The count (`runs-0.2.12/`, `chain-2026-10-11b.sh`, 2026-10-11 14:39 – 19:41 UTC, tree `7fb0ed08`)

Six shakedowns clean first (page honesty `clean`, locks/versions/assets/same-second exit 0 with `clean` verdicts, host entry `LANDS`; `chain-2026-10-11b.out`), then:

| Report | Result |
|---|---|
| production UI, `counted-KR-x3.json` | **Kdel, Kbs, Rbs, Rdel 3/3 each in both browsers (24/24)** |
| production UI, `counted-ctl-S-P.json` | Bctl, S, P 1/1 each, both browsers (6/6) |
| production UI, `counted-B3x-x2.json` | B3x 2/2 each browser (4/4) |
| production UI, pooled mutations | **40/40** (`runs-0.2.12/red-cases-on-counted-pooled.txt`) |
| page honesty `m3-page-honesty/runs/2026-10-11T160416+0000.json` | **PAGE HONEST**, every cell 3/3 per browser; red cases 154 |
| locks `m3-locks/runs/2026-10-11T170844+0000.json` | **LOCKS LAND**, `problems=[]`; `chrome:readonly` 3/3; red cases 99 |
| versions `m3-versions/runs/2026-10-11T175737+0000.json` | **VERSIONS CORRECT** 3/3, 3/3; red cases 68 |
| assets `m3-assets/runs/2026-10-11T180154+0000.json` | **ASSETS DELIVERED** chrome/firefox/firefox-nozstd 3/3; red cases 156 |
| host entry `m3-host-entry/runs/2026-10-11T180622Z.json` | **HOST_ENTRY LANDS**; red cases 23 (plus the baseline green) |
| same second `m3-same-second/runs/2026-10-11T181217+0000.json` | **SAME-SECOND SAVES KEPT** 3/3 × 4; red cases 70 |

Red-case outputs: `runs-0.2.12/red-cases-six.txt` (script `red-cases-2026-10-11b.sh`; every runner's `--red-cases` exit 0; the counts above were re-read from each runner's full `--red-cases` output, which the script tails). The red counts equal 0.2.11's. The three production-UI reports' `static` blocks are identical, `counted: true`, runner `c9d51781…`, host 0.2.12 `b245ae7`, buildId `45cdcedfc0fe7e61`, served page `8909564e…`, shell bundle v61 `f48df85b…` with `problems: []`.

### §17.23's predictions for the re-run

| | Prediction | Result |
|---|---|---|
| Q1 | locks shakedown's 12 Chrome arms all pass (K9′ included); the chain passes all six shakedowns | **Held.** All 22 arms passed; Chrome Files rows present 0.00–0.06 s after the page load returned; the capture (`filesRowDiagnostic`) never fired. The counted locks run then passed every Chrome cell (`chrome:readonly` 3/3) |
| Q2 | no report this chain wrote contains `ERR_CERT_VERIFIER_CHANGED` | **Held.** `grep -l` over the 56 files the chain wrote: 0. Positive control: the same grep counts 86 in stop-1's locks report. Limit as stated: only locks, host entry, same second and versions record CDP load failures |
| Q3 | duration grows by about 5 s × Chrome launches (an estimate, not a criterion) | 5 h 01 m 35 s against 0.2.11's 4 h 49 m 37 s: **+11 m 58 s**. Launches were not counted, so this is not converted into a per-launch figure |

One clean chain is not a rate: the old rate was low (1 of 12 Chrome arms in stop-1; finding 112's census, 1 of 1,244 Files opens before it). What this chain shows is that the change did not break any runner, and that the reset did not recur in any of its Chrome launches.

## Product-path net (`../release-0.2.12/product-path/`)

Twelve reports, v8 (the page repointed, `0660beaf…`) and v19 (dist as served, `8909564e…`) interleaved, 3 rounds × Chrome/Firefox (18:23–19:41 UTC). Reader `judge.py` (0.2.11's with the two page constants re-bound); made red offline once before its verdict was read (a flipped v19 cell → P3 MISS; a wrong v19 entrypoint → P2 MISS; `judge-red-offline.txt`). **Watch item first (§17.15)**: Chrome `clear-format-removes-every-inline-format` PASS in all 6 Chrome runs (both arms), so the verdict was read; §17.15's single Chrome NE stays registered as a single occurrence.

`judge-output.txt`: **`SUMMARY  P1: HIT  P2: HIT  P3: HIT (red cells 0)  P4: descriptive (differing cells 1)`** — 84 cells, 0 red under §23 + row 1′ (window at read time: Chrome 0 of 30 v8 records NE, Firefox 2 of 30, as PREDICTION.md said). The one differing cell is Firefox `clear-format-removes-every-inline-format`, v8 2 PASS + 1 NE, v19 3 NE — 0.2.11's kind (NE-only), as P4 predicted. The Firefox reports exit 1 for the known red `an-inline-format-reaches-a-selection` (3 of 3 rounds in both arms). **The v8 arm ran on the C′ page for the first time** and agrees with v19 on 83 of 84 cells.

Descriptive, the page-regression question (`old-vs-new-v19.txt`): v19 on the old page (0.2.11, `36c2b18b…`, shell v60) against v19 on the new page — **0 cells differ** in either browser (42 + 42).

## Verdict

**The count holds on host 0.2.12.** §17.4's criteria as amended (§17.9–17.10, §17.21 for C5 (ii)) are met before the count, and the count itself — the production-UI arms, the six M3 runners and their red cases, the product-path net, static exit 0 — is clean. By their own criteria:

- **Finding 124 can be marked fixed** (124-U with its red cases; 124-B in both browsers).
- **Finding 125 can be marked fixed** (125-U with its red cases; 125-B in both browsers). Recorded, not a criterion: the browser positive control for a 700-ms save fired once in Chrome (723.5 ms) and never in Firefox (§17.18).
- **Finding 126 can be marked fixed** for the case it was registered on (C6's C′ half, 8/8 DRAWN at 40 and 50 pages).
- **Finding 112**: the fix held through this chain; one chain, not a rate (above).

Named limits carried (§17.8, §17.23): fast scrollbar flicks show old pixels or blank until bands arrive; R_b's time depends on the network; the ~62 s component-install reset is outside the warm-up; locks' `loadingFailed` has no timestamps.

§34.4 at this result: **因執行而修 7, 因審核而修 5.** This stretch added one run-triggered fix (the launcher warm-up; witness above) and no review-triggered one. §17.21's registered future runner opening is now the 8th.

## Static

`make test-e2-c-static` exit 0 after the count (node 213 + 5, python 108; `../release-0.2.12/test-e2-c-static-after-count.txt`), as after the warm-up (`test-e2-c-static-after-warmup.txt`).

## Owner hand test (2026-10-12, appended)

Asked to try, in Chrome and Firefox on the host: typing; on a long document, arrow keys move the view with the caret (124) and the pill does not flash 「處理中」 (125); a document long enough to have gone blank before C′ opens and draws (126). Before the test the litecore ddev project was started (it had been stopped), and the served page was read over HTTP from the editor's own address (`/apps/litecore/r/45cdcedfc0fe7e61-90d7bc2c/e2-editor-app.js`, gzip): `8909564e…`; `occ app:list` says litecore 0.2.12. For 126 a 60-page A4 document from `wasm_sdk_probe/tools/create_long_document.py` was put in admin's Files as `手測-126-60頁.odt` (the longest document there was the owner's 22 pages; on a 1× screen the P page went blank from about 53 pages).

The owner's reply, verbatim: "都通過，幾個小問題：1. delete / backspace 刪去文字的時候會有殘影 2. 將文字反白選取的時候，使用方向鍵會報錯 3. 我需要「shift + 方向鍵 = 選取文字」的功能 D: 長文件 works，不過拖曳捲軸進行捲動的時候，不知道自己捲到第幾頁，我記得collabora好像是，捲軸上會顯示頁碼". A follow-up, verbatim: "捲軸那項我沒寫清楚，但在UX上也很重要".

So the release's own items held in the owner's hands (124, 125, 126 by D). The four further items are not regressions of this release — neither the delete path's BUSY back-off nor the gestures the move actions accept changed in C′ — and are registered separately: (1) → finding 128, (2) → finding 129, (3) and the scrollbar page number → requests in `specs/SPEC-M3-production-ui.md` §17.25. The reproductions are `../128/` and `../129/`.
