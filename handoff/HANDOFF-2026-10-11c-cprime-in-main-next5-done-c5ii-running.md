# Handoff, 2026-10-11c — the C′ page (with 124 and 125) is in main and built; the witness is 0 red on both pages; Next 5 is done (condition 3, C3/C4, C6, 124-B/125-B, C2, C1 and the recorded items); C5 (ii) is RUNNING detached; the release step (Next 7) has not started

Picks up from `HANDOFF-2026-10-11b-c5i-chain-running-c-prime-written-in-worktree.md` (its Addendum 3: C5 (i) holds).
Repository root `/home/jiajun/LibreOffice/study_LiteCore`. Spec `specs/SPEC-M3-production-ui.md` §17.13–§17.18 record
everything below in zh-TW; evidence READMEs are English.

## What happened, in order

| Commits | What |
|---|---|
| `90242ebc` | C′-only page (`57d21411`) cherry-picked; `make e2-c-assets` → `dist/` = `web/` = `f5121fd4…`. Uncounted smoke (Chrome) ok. **Static suite on the C′ tree exit 2** (rule ddd): manifest out of date (expected until v61), `gesture-abort-not-wired` anchor (known), and — not anticipated — `--caret-source-diagnostic`'s two anchors. |
| `7a4601c3` | **Witness on the C′-only page = 0 red** (pre-port runners `08d73cff` restored temporarily, v19 arm, Chrome + Firefox, vs 0.2.11 v19 r1–r3). Positive control: long-document arms read a 4,092-row window (P page: 4,992–39,839). Reader `findings/evidence/c-prime/witness/judge_witness.py` (red cases `judge-red-cases.txt`). §17.13. |
| `bbce5596`, `0ad30e73`, `3eccb235` | 124, 125, `13f91117` cherry-picked; `dist/` = `web/` = **`8909564e…` (final page)**. |
| `e1303987` | Three diagnostic anchors re-anchored (`CARET_SOURCE_ANCHOR`, `CARET_ANNOUNCE_ANCHOR`, `PAGE_STATE_ANCHOR` — the last one broken by 125's `showState(...)`). `run_e2_c_product_path.py` = **`bd6fc0caf677ee9c`**. Static suite now fails ONLY the shell manifest (v60 out of date; clears at the v61 freeze). Evidence `findings/evidence/c-prime/page/STATIC-SUITE.md`. |
| `0c9a8394` | **Owner's two choices** (AskUserQuestion): (1) measure the witness again on the final page (not register-only, not revert the ports); (2) §34.4 counts each re-anchor +1 per the `ignore-a-document-that-grew` precedent → **因執行而修 6, 因審核而修 5**. §17.14. Final-page witness prediction committed first. |
| `1f186370` | **Final-page witness**: unported and ported runners on the same page, v19 arm, both browsers. **Port-witness 0, page-effect 0** (as predicted) → the product-path and page-honesty ports are **registered as having no witness on either page**; the page-smoke port waits for production UI `Rdel` with the pre-port smoke on the first host build carrying the page (Next 7). One movement outside the prediction: Chrome ported `clear-format-removes-every-inline-format` NE (finding 077's toggle mechanism; Firefox 59/68 NE historically, Chrome first in 68) → **watch item**: if NE in ≥ 2 of the release net's 6 Chrome runs, diagnose before the count. §17.15. |
| `817c7999`, `6eb20111` | Red pages from the final page; **Next 5 non-latency chain**: condition 3 red cases red in both browsers (read from the reports — the chain's gate wrongly took a probe crash's exit 1 as "red"; the crash is `probe_c_prime_window.py:336` summary iterating `c4 = False` without `--c4`; registered, not fixed); **C3/C4 6/6 PASS** (C4 all < 400 ms; bold arm's C3 time ~1.5 s includes the bold command, not separable); **C6 8/8 DRAWN** (126's 40/50-page documents drawn top and bottom, canvas 4,092–4,380 rows); **124-B, 125-B PASS** both browsers. §17.16. |
| `67b20201`, `0fe36c43` | Judges' page pins moved to the final page (`judge_c2.py`, `judge_p2.py` pin lines only). **C2 PASS** both browsers every cell; ratio-1 P2 cells PASS. Every timing on the fast side: gap-80 commit median Chrome 17.6 / Firefox 21.4 ms (predicted 30–42 / 40–65; P page 43.9 / 84.5). §17.17. |
| `a3379456`, `56e012a6`, `da8082e8` | New probe `wasm_sdk_probe/tools/probe_c_prime_recorded.py` (recording instrument, not a check). **C1′ holds in 8 runs** (Chrome ratio 2 wide = 4,380 rows — §17.9 N4's "4,092" does not hold for Chrome, desk 730 px); `#paper` = document height; `lastTiles` ≤ 36.8 MB; fling: 17–18 of 21 frames stale at ratio 2, current 16–62 ms after the last frame (the first chain's 1.68 s was the probe's own 2-s sleep floor — fixed, rerun); **H9: no `INVALIDATE_TILES` while typing**; **125's browser positive control seen once in Chrome** (723.5 ms save, 「處理中」 at 699.9 ms), **not exercised in Firefox** (no save reached 700 ms). §17.18. |
| `a74a2494`, `01c948fc` | C5 (ii) prediction + reading rule + chain, committed before launch (47 ordinary mutations predicted red; correction 46→47 appended before the start). |

## State

| Item | State |
|---|---|
| Product bytes | `web/e2-editor-app.js` = `dist/e2-editor-app.js` = `8909564eb2316afa…` (C′ + 124 + 125). Shell still **v60** (manifest out of date — expected), host `litecore` **0.2.11** `6b53c2e`, engine v19. No v61, no host 0.2.12, no host pin touched. |
| Runners (HEAD) | `run_e2_c_page_smoke.py` `cc38ee97ca20611d`, `run_e2_c_product_path.py` `bd6fc0caf677ee9c`, `check_m3_page_honesty.py` `17a38fe756fe3e0b`. |
| **C5 (ii)** | **RUNNING** detached since 2026-10-11T03:56:00Z (11:56 CST): `findings/evidence/c-prime/c5ii/chain-c5ii.sh`, progress `findings/evidence/c-prime/c5ii/chain.txt` (one line per mutation, last line `DONE`). 51 runs × ~6.5 min ≈ 5.5 h → about **09:30Z (17:30 CST)**. Flags: three a11y mutations with `--candidate-profile e2-editor-v14`, `cut-swallows-the-refusal` with `--refusal-diagnostic` (the runner declares `requiresFlag` but does not enforce it). |
| Constraint while it runs | Do not change `web/`, `dist/`, or any file under `wasm_sdk_probe/tools/`; no browsers, nothing CPU-heavy beside it (rule vv). Committing evidence/docs elsewhere is safe. |
| §34.4 | **因執行而修 6, 因審核而修 5** (the review budget is spent; the second number must stay 5). The recorded-items probe's timer fix is an instrument fix, not a check. |
| Findings | 124, 125, 126: criteria all measured on the final page (124-U/124-B, 125-U/125-B, C6's C′ half) — **statuses are updated at the release step, not before** (previous handoff's rule). |
| Not pushed | Count with `git rev-list --count github/main..HEAD`; pushing is the owner's decision. |

## Next

1. **Read C5 (ii)** when `chain.txt` ends `DONE`, by `PREDICTION.md`'s rule (declared check FAIL = red; NOT the runner's `ok`; `caret-ignores-x` per §17.10; `checkpoint-write-fails` and `copy-lies` as declared; `a11y-projection-at-its-static-position` recorded). Runs with no report / `complete` not true are re-run once alone. Any ordinary mutation not red = C5 (ii) does not hold → stop and diagnose before the release step. Write `c5ii/README.md` (English) and §17.19 (zh-TW).
2. **The release step** (§17.7 step 5, previous handoff's Next 7): `make test-e2-c-static` (expect only the manifest failure, which the freeze clears) → E1-C intact → freeze shell **v61** (v60 untouched) → host **0.2.12** carrying the page → re-pin (pin lines only) → **before the count: production UI `Rdel` once with the pre-port `run_e2_c_page_smoke.py` (`git show 08d73cff:…`) on 0.2.12, both browsers — predicted red (`witness/PREDICTION.md`), the page-smoke port's §34.4 witness** → the count chain (shakedowns first; any non-clean = STOP; gate on report verdicts, not exit codes) and the product-path net → watch item: Chrome `clear-format-removes-every-inline-format` NE ≥ 2 of 6 → diagnose before counting → `RESULT-0.2.12.md` → findings 124 / 125 / 126 statuses each by its own criterion → tell the owner, offer a hand test (typing; arrows on a long document; a document past 33 pages at 150 %). Pushing stays the owner's.

## Open (new this stretch)

- `probe_c_prime_window.py` crashes in its summary line without `--c4` (report written first; exit code wrong). Registered.
- Firefox has no browser positive control for 125's 700 ms show (no save reached 700 ms). Registered; 125-U and Chrome's one run cover it.
- `clear-format-removes-every-inline-format` Chrome NE watch item (above).
- The bold arm's C3 time is not separable from the bold command (no timestamp of the press in the report).
- Carried, unchanged: everything in the previous handoff's Open list.

## Standing rules (new this stretch)

- **(eee) A chain's gate reads the report's verdict, never the exit code.** Evidence: `findings/evidence/c-prime/final-page/chain.txt` printed "both red cases red" on a Python traceback's exit 1.
- **(fff) Identical numbers across runs of different configurations are the instrument's floor until shown otherwise.** Evidence: fling "current after last frame" 1,680–1,691 ms in four runs = the probe's 2-s sleep minus the 0.33-s fling.
- **(ggg) A re-anchoring claim covers only the list it was checked against.** Evidence: "50 of 51 mutation anchors match" was true for `MUTATIONS` and silent about the diagnostic mirrors, three of which broke (`STATIC-SUITE.md`).
