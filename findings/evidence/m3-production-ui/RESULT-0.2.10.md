# M3 production UI and R‴ on host 0.2.10 (findings 122, 121, 120) — result (2026-10-10)

Spec: `specs/SPEC-M3-production-ui.md` §15 (fixes and criteria §15.1–15.2, A+B §15.6, the restated commit cell §15.8, the reader's review §15.9, the freeze §15.10, bindings §15.11), under fable's four rulings on finding 122 (`findings/evidence/typing-latency/ruling/fable-ruling.md`; the owner asked for them). The 0.2.9 result is `RESULT-0.2.9.md`; this file is the one for the release that carries findings 122's, 121's and 120's fixes.

## What was released

| What | Value |
|---|---|
| Shell generation | **v59** `ad65480a…` (`d30a1b4c`), equal to v58 but for `web/e2-editor-app.js` |
| Page / session | `18c8afbe…` / `62a2a20e…` (session unchanged since v58; dist = web = served) |
| Host | `litecore` **0.2.10**, `d87960d`, clean tree; engine package buildId `bebc7e83f573d1a8` (read from the counted reports' `static.buildId`); every packaged file but the page as 0.2.9 (v19, wasm `1aafd4f9…`); 0.2.9's engine archived in `wasm_sdk_probe/build/archive/host-0.2.9-engine-7bf6dbd6142388f1/` |
| Runners | six M3 runners re-pinned, pin lines only (12 lines, `98e997e3`); host entry has no pins; `check_m3_production_ui.py` `5bce52d0…`; `run_e2_c_product_path.py` `a6e31896…` (the `ignore-a-document-that-grew` mutation re-anchored by fable's fourth ruling, `cfd72f08`) |

## Before the count (candidate `dist/`, unit and browser)

| Criterion | Result |
|---|---|
| 122-U | B1–B8 and B8-control pass (bands of floor(32767/32) = 1023 rows); red cases each red once (`../typing-latency/unit-red-cases.txt`); unit suite 183/183 |
| 121-U / 120-U | pass, red cases red (earlier commits `05f46923`, `3632dabe`) |
| 122-B | six `v59-candidate2-*.json` on page `18c8afbe…`, probe `dbad93c0…`; read by `../typing-latency/judge.py` (reviewed once by opus and codex, §15.9; 0 fixes from review) as **PASS in both browsers** (`../typing-latency/judge-output.txt`). The commit cell is fable's restatement (§15.8): every key < 2 × gap and median < gap at gap 80. Firefox on screen 49.2 / 51.1 ms median at gap 80 / 200 (v58: 187.3 at gap 200), Chrome 36.7 / 46.0 (v58: 611.0 at gap 80, 145.7 at gap 200) |
| 121-B / 120-B | re-run on `18c8afbe…` after A+B (`5293628a`): 121 four of four (both keys, both browsers), 120 both browsers |

## The count (`runs-0.2.10/`, `chain-2026-10-10.sh`, 2026-10-09 18:24 – 23:20 UTC)

Six shakedowns clean first (page honesty `clean`, locks/versions/assets/same-second exit 0, host entry `LANDS`), then:

| Report | Result |
|---|---|
| production UI, `counted-KR-x3.json` | **Kdel, Kbs, Rbs, Rdel 3/3 each in both browsers (24/24)** |
| production UI, `counted-ctl-S-P.json` | Bctl, S, P 1/1 each, both browsers (6/6) |
| production UI, `counted-B3x-x2.json` | B3x 2/2 each browser (4/4) |
| production UI, pooled mutations | **40/40** (`runs-0.2.10/red-cases-on-counted-pooled.txt`) |
| page honesty `m3-page-honesty/runs/2026-10-09T195126+0000.json` | **PAGE HONEST**, every cell 3/3 per browser; red cases 154 |
| locks `m3-locks/runs/2026-10-09T205142+0000.json` | **LOCKS LAND** (first run); red cases 99 |
| versions `m3-versions/runs/2026-10-09T213815+0000.json` | **VERSIONS CORRECT** 3/3, 3/3; red cases 68 |
| assets `m3-assets/runs/2026-10-09T214211+0000.json` | **ASSETS DELIVERED** chrome/firefox/firefox-nozstd 3/3; red cases 156 |
| host entry `m3-host-entry/runs/2026-10-09T214621Z.json` | **HOST_ENTRY LANDS**; red cases 23 (the baseline green) |
| same second `m3-same-second/runs/2026-10-09T215134+0000.json` | **SAME-SECOND SAVES KEPT** 3/3 × 4; red cases 70 |

Red-case outputs: `runs-0.2.10/red-cases-six.txt` (every runner's `--red-cases` exit 0; the script is `red-cases-2026-10-10.sh`). The red counts equal 0.2.9's. The three production-UI reports' `static` blocks are identical, `counted: true`, runner `5bce52d0…`, host 0.2.10 `d87960d`, buildId `bebc7e83f573d1a8`. Timings of the production-UI arms are in the reports and are not summarised here.

## Product-path net (M2-5 on the new page; `../release-0.2.10/product-path/`)

The re-anchored `ignore-a-document-that-grew` mutation was run once first (Chrome, `mutation-ignore-a-document-that-grew-chrome.json`): `the-canvas-follows-a-document-that-grew` FAIL, as required. Then twelve reports, v8 (the new page repointed, `d446cbfd…`) and v19 (dist as served, `18c8afbe…`) interleaved, 3 rounds × Chrome/Firefox (2026-10-09 22:02–23:20 UTC). Reader `judge.py` (0.2.9's with the two page constants re-bound; made red offline once before its verdict was read: a flipped v19 cell → P3 MISS, a wrong v19 entrypoint → P2 MISS, `judge-red-offline.txt`). `judge-output.txt`:

**`SUMMARY  P1: HIT  P2: HIT  P3: HIT (red cells 0)  P4: descriptive (differing cells 1)`** — 84 cells judged, 0 red under §23 + row 1′ (window at read time: Chrome 0 of 21 v8 records NE, Firefox 2 of 21). The one differing cell is Firefox `clear-format-removes-every-inline-format` (v8 3 NE, v19 1 PASS + 2 NE), an NE-only cell as P4 allowed. The Firefox reports exit 1 for the known red `an-inline-format-reaches-a-selection` (both arms, as in 0.2.9 and X5).

Descriptive, the shell-regression question (`old-vs-new-v19.txt`): v19 on the old page (0.2.9, shell v58) against v19 on the new page — 0 cells where the old passed every round and the new did not; one cell differs, Firefox `clear-format-removes-every-inline-format`, old 3 NE, new 1 PASS + 2 NE.

## Verdict

**R‴ holds on host 0.2.10.** Every criterion of §15.2 as amended by §15.6 and §15.8 is met: 122-U, 121-U, 120-U, 122-B (both browsers, by the reviewed reader), 121-B and 120-B on the final bytes, and R‴ — the production-UI arms, the six M3 runners and their red cases, the product-path net (after the re-anchored mutation bit), static exit 0. Findings 122, 121 and 120 can be marked fixed. 122's open items stay registered: C (forward the invalidated rectangle; relink queue), R1 (A′, admissibility measured first) and R2 (the whole-canvas re-blit on every state update), §15.8.

## Static

`make test-e2-c-static` exit 0 after the freeze, the re-anchor and the re-pin (node 183 + 5, python 108).
