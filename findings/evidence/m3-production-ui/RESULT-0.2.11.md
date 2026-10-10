# M3 production UI and R⁗ on host 0.2.11 (release P and finding 123) — result (2026-10-10)

Spec: `specs/SPEC-M3-production-ui.md` §16 (fixes and criteria §16.1–16.2, red cases §16.3 with the correction §16.7 and the re-specified window §16.8, the reader's review §16.9, the candidate page and the freeze §16.10, bindings §16.11), under fable's fifth ruling (`findings/evidence/typing-latency/ruling/fable-ruling.md`, "Fifth ruling" and its addendum; the owner asked for it). The 0.2.10 result is `RESULT-0.2.10.md`; this file is the one for the release that carries release P (`paint()` restores only what the overlay touched) and finding 123's fix.

## What was released

| What | Value |
|---|---|
| Shell generation | **v60** `784a1d93…` (`727b8fa4`), equal to v59 but for `web/e2-editor-app.js` |
| Page / session | `36c2b18b…` / `62a2a20e…` (session unchanged since v58; dist = web = served) |
| Host | `litecore` **0.2.11**, `6b53c2e`, clean tree (`hostDirty: []`); engine package buildId `b99f4b138839ff04` (read from the counted reports' `static.buildId`); every packaged file but the page as 0.2.10 (v19); 0.2.10's engine archived in `wasm_sdk_probe/build/archive/host-0.2.10-engine-bebc7e83f573d1a8/` |
| Runners | six M3 runners re-pinned, pin lines only (12 lines, `231536d5`); host entry has no pins; `check_m3_production_ui.py` `d799fa9d…`; `run_e2_c_product_path.py` `a6e31896…` (unchanged since 0.2.10) |

## Before the count (candidate `dist/`, unit and browser)

| Criterion | Result |
|---|---|
| 123-U / P-U | unit suite 189/189; red cases R-123, R-P1, R-P2, R-P4 each red once, only on their own test (`../typing-latency/p-release/unit-red-cases.txt`); the extra "no clip" mutation stays green and is recorded as an equivalent mutation |
| P1 | `../typing-latency/judge_p.py` (`1461fc03…`, reviewed once by opus and codex, §16.9; 0 fixes from review) → **PASS in both browsers**: 640 / 736 bytes re-blitted per key (Chrome / Firefox), about 0.001 % of the canvas; the shipped page re-blits 600 % (`../typing-latency/p-release/judge-candidate.txt`) |
| 123-B | both canvases **1490 × 36,847** (the §16.9 N2 reading: the canvas §16.8 named, so the red case kept its power); no `TILE_NOT_PAINTED` toast; the last band (y 35,805, **1,042 rows**) blitted after the last key; `allCurrent` 700.9 / 1,047.3 ms |
| P2 | `../typing-latency/judge_p2.py` (`1faea9d9…`, `judge.py` with the page constant and default names changed; red cases run first, `judge-p2-red-cases.txt`) → **PASS in both browsers**: gap-80 commit median 26.1 / 36.2 ms (shipped page 45.2 / 65.3), on screen 25.3 / 29.7 |
| P3 (recorded) | Firefox ratio 1.5 wide commit median 60.9 (passes §15.8 (a)(b)); ratio 2 wide 84.5 (fails (b) only — the P page's named limit, §16.10); Chrome 34.9–43.9 in all three configurations |
| 121-B / 120-B | re-run on `36c2b18b…`: identical to v59's reports but for latency strings |
| Moved mutation anchors | `caret` turned its check FAIL. `caret-ignores-x` gave `the-caret-lands-where-the-click-was` NOT_ESTABLISHED plus its also-red FAIL — **identical on the shipped v59 page** (control run, dist swapped and restored), so the NE belongs to the oracle since 2026-08-21, not to P; registered, not fixed (`../release-0.2.11/product-path/PREDICTION.md`) |

## The count (`runs-0.2.11/`, `chain-2026-10-10b.sh`, 2026-10-10 01:57 – 06:47 UTC)

Six shakedowns clean first (page honesty `clean`, locks/versions/assets/same-second exit 0, host entry `LANDS`; `wasm_sdk_probe/build/m3-count-2026-10-10b/chain.txt`), then:

| Report | Result |
|---|---|
| production UI, `counted-KR-x3.json` | **Kdel, Kbs, Rbs, Rdel 3/3 each in both browsers (24/24)** |
| production UI, `counted-ctl-S-P.json` | Bctl, S, P 1/1 each, both browsers (6/6) |
| production UI, `counted-B3x-x2.json` | B3x 2/2 each browser (4/4) |
| production UI, pooled mutations | **40/40** (`runs-0.2.11/red-cases-on-counted-pooled.txt`) |
| page honesty `m3-page-honesty/runs/2026-10-10T031815+0000.json` | **PAGE HONEST**, every cell 3/3 per browser; red cases 154 |
| locks `m3-locks/runs/2026-10-10T041853+0000.json` | **LOCKS LAND** (first run); red cases 99 |
| versions `m3-versions/runs/2026-10-10T050528+0000.json` | **VERSIONS CORRECT** 3/3, 3/3; red cases 68 |
| assets `m3-assets/runs/2026-10-10T050926+0000.json` | **ASSETS DELIVERED** chrome/firefox/firefox-nozstd 3/3; red cases 156 |
| host entry `m3-host-entry/runs/2026-10-10T051336Z.json` | **HOST_ENTRY LANDS**; red cases 23 (the baseline green) |
| same second `m3-same-second/runs/2026-10-10T051850+0000.json` | **SAME-SECOND SAVES KEPT** 3/3 × 4; red cases 70 |

Red-case outputs: `runs-0.2.11/red-cases-six.txt` (every runner's `--red-cases` exit 0; the script is `red-cases-2026-10-10b.sh`; the counts above were re-read from each runner's own `--red-cases` output). The red counts equal 0.2.10's. The three production-UI reports' `static` blocks are identical, `counted: true`, runner `d799fa9d…`, host 0.2.11 `6b53c2e`, buildId `b99f4b138839ff04`, served page `36c2b18b…`. Timings of the production-UI arms are in the reports and are not summarised here.

## Product-path net (M2-5 on the new page; `../release-0.2.11/product-path/`)

The two mutations whose anchors release P moved were run once first (above). Then twelve reports, v8 (the new page repointed, `bd29ecca…`) and v19 (dist as served, `36c2b18b…`) interleaved, 3 rounds × Chrome/Firefox (2026-10-10 05:30–06:47 UTC). Reader `judge.py` (0.2.10's with the two page constants re-bound; made red offline once before its verdict was read: a flipped v19 cell → P3 MISS, a wrong v19 entrypoint → P2 MISS, `judge-red-offline.txt`). `judge-output.txt`:

**`SUMMARY  P1: HIT  P2: HIT  P3: HIT (red cells 0)  P4: descriptive (differing cells 0)`** — 84 cells judged, 0 red under §23 + row 1′ (window at read time, before these reports were committed: Chrome 0 of 24 v8 records NE, Firefox 2 of 24, as PREDICTION.md said). The two arms agree on every cell. The Firefox reports exit 1 for the known red `an-inline-format-reaches-a-selection` (3 of 3 rounds in both arms, as in 0.2.10).

Descriptive, the shell-regression question (`old-vs-new-v19.txt`): v19 on the old page (0.2.10, shell v59) against v19 on the new page — 0 cells where the old passed every round and the new did not; one cell differs, Firefox `clear-format-removes-every-inline-format`, old 1 PASS + 2 NE, new 3 NE (an NE-only cell; it moved the other way between 0.2.9 and 0.2.10).

## Verdict

**R⁗ holds on host 0.2.11.** Every criterion of §16.2 as amended by §16.7–16.10 is met: 123-U and P-U with their red cases, P1 and 123-B (both browsers, by the reviewed reader), P2, P3 recorded, P4 (the product-path net, after the moved mutations were run), 121-B and 120-B on the final bytes, and R⁗ — the production-UI arms, the six M3 runners and their red cases, static exit 0. Finding 123 can be marked fixed. The P page's named limits stay (§16.10's rewrite of §16.6): Firefox at ratio 2 wide fails §15.8 (b) (84.5 ms, one measurement); 062's 65,535-row canvas ceiling; holding a delete key down never measured. All three go to C′.

§34.4 for this stretch: check fixes triggered by runs **1** (`judge_p.py`'s per-browser 123-B window, §16.8); triggered by reviews **0**. The count chain itself triggered none.

## Static

`make test-e2-c-static` exit 0 after the count (node 189 + 5, python 108; `../release-0.2.11/test-e2-c-static-after-count.txt`), as after the freeze and the re-pin.

## Owner hand test (2026-10-10, appended)

Asked to try, in Chrome and Firefox on the host, typing (and at 150 % / 200 % if a machine had it), watching for the toast 「重繪失敗」. Before the test the served page was checked: `engine/files/e2-editor-app.js.gz` and `.zst` in the host app both decompress to `36c2b18b…`, the app's `info.xml` says 0.2.11. The owner's reply, verbatim: "已手動測試，目前看起來正常". Two further observations from the same test, registered as new findings (not regressions of this release; neither code path changed in P): (1) in a long document, moving the caret down with the Down arrow does not scroll the view to follow it; (2) every arrow-key caret move flashes the state pill 「處理中」 although the content does not change.
