# C2 on the final C′ page (2026-10-11 03:40–03:44Z)

Page `dist/e2-editor-app.js` = `8909564eb2316afa…`, tree `67b20201` (the commit that set both judges' page pins,
pin lines only). Chain `chain-c2.sh`, log `chain.txt`: desktop clean at start (no Chrome process, load 0.11);
nothing else ran beside it. Tools: `probe_typing_latency_view.py` `1412e4c863de6fcb` over the counted probe
`probe_typing_latency.py` `dbad93c0dcf27fbf`. Judges' output: `judge-output.txt`.

**C2 PASS** (`judge_c2.py`, ratio 2 wide = `--dpr 2 --window 1400x1000`, owner document): both browsers, every
cell, exit 0. **P2's cells at ratio 1 PASS** (`../../typing-latency/judge_p2.py --dir ratio-1`, its page pin moved
to this page): both browsers, every cell, exit 0. The P-page verdicts that `judge_p2.py` produced before remain
reproducible with the reader as it was: `git show 67b20201^:findings/evidence/typing-latency/judge_p2.py`.

Against spec §17.10's predictions (written before any run; median = the probe's upper median):

| Cell | Predicted Chrome / Firefox | Measured Chrome / Firefox | P page (§16) |
|---|---|---|---|
| ratio 2 wide, gap 80, commit median / max | 30–42 / < 70 ; 40–65 / < 110 | **17.6 / 35.9 ; 21.4 / 37.2** | 43.9 / — ; 84.5 / — |
| ratio 2 wide, on screen median (gap 80, 200) / max | 30–42 / < 80 ; 35–55 / < 90 | 24.7, 33.5 / 43.3 ; 29.1, 34.1 / 44.5 | 43.2 ; 53.4 |
| ratio 1.5 wide, gap 80, commit median (recorded) | 30–45 ; 40–65 | 17.9 ; 21.6 | 35.2 ; 60.9 |
| ratio 1 (P2), owner gap 80, commit median | 22–30 ; 30–40 | 18.7 ; 20.8 | 26.1 ; 36.2 |
| ratio 1 (P2), boundaries gap 200, commit median (≤ 10) | — | 4.5 ; 3.9 | — |

Every miss is on the fast side, as in the P release. The row the prediction singled out — Firefox's (b) at
ratio 2 wide, 84.5 ms on the P page and failing there — is **21.4 ms**. Canvas rows recorded by the probe:
4,380 (Chrome) and 4,092 (Firefox) at ratio 2 wide, 4,092 at ratio 1 for the owner document — the window, not
the document. Per-key backlog is 0 for every key in both browsers. The (ii) times (whole canvas current after
the last key, recorded) are 51.4–68.4 ms.

Recorded only, ratio 1.5 wide: `ratio-1.5/` (no judge; numbers in `chain.txt` and the reports' `summary`).
