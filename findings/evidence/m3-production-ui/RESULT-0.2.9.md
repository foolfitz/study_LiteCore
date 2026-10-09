# M3 production UI and R′ on host 0.2.9 (findings 119 and 111) — result (2026-10-09)

Spec: `specs/SPEC-M3-production-ui.md` §14 (criteria and predictions `65b4dcc6`, reading §14.5, bindings §14.6), under fable's two rulings on the owner's authority (`findings/evidence/fast-delete-recovery/ruling/fable-ruling.md`). The 0.2.8 result is `RESULT-0.2.8.md`; this file is the one for the release that carries findings 119's and 111's fixes.

## What was released

| What | Value |
|---|---|
| Shell generation | **v58** `a6f9331a…` (`37fcb71e`), equal to v57 but for `editor-shell-v2/narrow-editor-v2-session.js` (119: `73da170e`; 111: `f26b80a6`) and `web/e2-editor-app.js` (119) |
| Page / session | `537d62d7…` / `62a2a20e…` (dist = web = served) |
| Host | `litecore` **0.2.9**, `069de55`, clean tree; engine package buildId `7bf6dbd6142388f1` (read from each report's `static.buildId`); wasm and packs unchanged from 0.2.8 (v19) |
| Runners | the seven M3 runners re-pinned, pin lines only (`db081684`); `check_m3_production_ui.py` `fc4b2298…`; `run_e2_c_product_path.py` `7468abcd…` (the `rollback` mutation re-anchored by the second ruling, `521ed923`) |

## Before the count (candidate `dist/`, unit and browser; §14.2)

| Criterion | Result |
|---|---|
| F119-U | U1–U6 pass; four red cases each red once (`../fast-delete-recovery/unit-red-cases.txt`) |
| F111-U | five prototype tests + U7 (generation guard) + U8 (save order) pass; two red cases (`../111/unit-red-cases.txt`) |
| F111-B | 160/160 correct, 0 overtaken, both documents, both browsers, gaps 0 and 10 ms (`../111/PREDICTION.md`) |
| F119-B | injection arm 3/3 + 3/3 PASS; natural arm 0 failures in 400 on one page → the natural path is registered 「沒有實例可量」 and the injection arm carries the browser half, by the rule written before the run (`../fast-delete-recovery/PREDICTION.md`) |

## The count (`runs-0.2.9/`, `chain-2026-10-09b.sh`, 2026-10-08 23:20 – 2026-10-09 UTC)

Six shakedowns clean first (page honesty `clean`, locks/versions/assets/same-second exit 0, host entry `LANDS`), then:

| Report | Result |
|---|---|
| production UI, `counted-KR-x3.json` | **Kdel, Kbs, Rbs, Rdel 3/3 each in both browsers (24/24)** |
| production UI, `counted-ctl-S-P.json` | Bctl, S, P 1/1 each, both browsers (6/6) |
| production UI, `counted-B3x-x2.json` | B3x 2/2 each browser (4/4) |
| production UI, pooled mutations | **40/40** (`runs-0.2.9/red-cases-on-counted-pooled.txt`) |
| page honesty `m3-page-honesty/runs/2026-10-09T004203+0000.json` | **PAGE HONEST**, every cell 3/3 per browser; red cases 154/154 |
| locks `m3-locks/runs/2026-10-09T014229+0000.json` | **LOCKS LAND** (first run); red cases 99 |
| versions `m3-versions/runs/2026-10-09T022856+0000.json` | **VERSIONS CORRECT** 3/3, 3/3; red cases 68 |
| assets `m3-assets/runs/2026-10-09T023254+0000.json` | **ASSETS DELIVERED** chrome/firefox/firefox-nozstd 3/3; red cases 156 |
| host entry `m3-host-entry/runs/2026-10-09T023708Z.json` | **HOST_ENTRY LANDS**; red cases 23 (the baseline green) |
| same second `m3-same-second/runs/2026-10-09T024226+0000.json` | **SAME-SECOND SAVES KEPT** 3/3 × 4; red cases 70 |

Red-case outputs: `runs-0.2.9/red-cases-six.txt` (every runner's `--red-cases` exit 0). The three production-UI reports' `static` blocks are identical, `counted: true`, runner `fc4b2298…`.

Numbers from the production-UI arms (as on 0.2.8, so 111's hold changed none of these paths' timing measurably): Kdel 163–174 ms per Delete; Kbs 139–157 + 169–171 ms; Rbs Home 864–885 ms (096's C-half checkpoint + the move), reopen 1038–1064 ms (Chrome) / 1911–1992 ms (Firefox); Rdel End 276–278 ms, reopen 1042–1074 / 1929–2015 ms; B3x `data-limit` `saved` 0.48 s after the third key in all four runs; Bctl 104 / 137 ms; S 0 elements outside the container change over 1065 / 974 properties, 87 inside.

## Product-path net (M2-5 on the new page; `../release-0.2.9/product-path/`)

Twelve reports, v8 (the new page repointed, `4d3f3bd6…`) and v19 (dist as served, `537d62d7…`) interleaved, 3 rounds × Chrome/Firefox (2026-10-09 02:53–04:11 UTC; the chain log, `runs-0.2.9/chain-2026-10-09b.txt`). Reader `judge.py` (a copy of X5's with the roles swapped and §36.2's row 1′ for the recovery cell; made red offline once before its verdict was read: a flipped v19 cell → P3 MISS, a wrong entrypoint → P2 MISS). `judge-output.txt`:

**`SUMMARY  P1: HIT  P2: HIT  P3: HIT (red cells 0)  P4: descriptive (differing cells 0)`** — 84 cells judged, 0 red under §23 + row 1′ (window at read time: Chrome 0 of 18 v8 records NE, Firefox 2 of 18); the two arms' counts are equal in all 84 cells. The Firefox reports exit 1 for the known red `an-inline-format-reaches-a-selection` (both arms, as in X5). Predictions: P1–P3 hit; P4 predicted a few differing cells, there were none.

Descriptive, the shell-regression question (`old-vs-new-v19.txt`): v19 on the old page (X5, shell v57) against v19 on the new page — 0 cells where the old passed every round and the new did not; one cell differs, Firefox `recovery-returns-what-the-product-promised`, old 1 NE + 2 PASS, new 3 PASS.

## Verdict

**R′ holds on host 0.2.9.** Every criterion of §14.2 is met: F119-U, F111-U, F111-B, F119-B (by the injection arm, the natural path registered 「沒有實例可量」, 0 in 400), and R′ — the production-UI arms, the six M3 runners and their red cases, the product-path net, static exit 0. Findings 119 and 111 can be marked fixed; 119's natural path stays named as not measured, and its engine cause C stays open in the relink queue.

## Static

`make test-e2-c-static` exit 0 after the freeze and the re-anchor (`521ed923`; node 169 + 5, python 108).
