# Next 5 on the final C′ page, the non-latency part (2026-10-11 03:26–03:37Z)

Page `dist/e2-editor-app.js` = `8909564eb2316afa…` (C′ + 124 + 125), tree `817c7999`. Chain `chain-next5.sh`, log
`chain.txt`. Tools as reviewed: `probe_c_prime_window.py` `1cb2ac337e03`, `probe_c6_long_document.py`
`7a31fba60893`, `probe_124_125_arrows.py` `ad4e4705a6dd`; `run_e2_c_product_path.py` `bd6fc0caf677ee9c`.
Everything below is read from the JSON reports, not from exit codes (see "The chain's gate" below).

## A. Ruling-1 condition 3: the two red pages (`c34-red/`)

Red pages made from this page by `../c34/make_red_pages.py` (`../c34/red-pages-made.txt`):
`never-stale-outside` `6fa1459830398934`, `label-at-reply` `5b1aa8d34a2dbe28`.

| Red page | Arm | Chrome | Firefox | Signature |
|---|---|---|---|---|
| never-stale-outside | typing, `--c4` | **FAIL** (C4 at 0.5 and 1.0 not current) | **FAIL** (same) | at both scrolls `pageSaysCurrent: true`, `probeSeesCurrent: false`: relabelled old pixels |
| label-at-reply | bold | **FAIL** (C3 not current) | **FAIL** | `pageSaysCurrent: true`, `probeSeesCurrent: false` |
| label-at-reply | typing | PASS | PASS | expected probabilistic (ruling 1, condition 3) |

**Condition 3 holds**: both red cases are red in both browsers, each through the probe's own observer.

### The chain's gate passed for the wrong reason

`chain-next5.sh` took exit 1 as "red". The four `label-at-reply` runs exit 1 because the probe crashes AFTER
writing its report: the stdout summary iterates `report.get("c4", [])`, and without `--c4` that key holds
`False` (`TypeError: 'bool' object is not iterable`, `probe_c_prime_window.py:336`). So the chain's line
"condition 3: both red cases red in both browsers" was printed on a crash, not on a verdict; the table above
is from the reports, which were complete (`verdict` FAIL in both bold runs). **Registered, not fixed**
(§34.4): the crash only affects the summary line and the exit code of runs without `--c4`; every real-page run
used `--c4`, and no run without it is planned. A later chain must gate on the report's `verdict`, not on the
exit code.

## B. C3 / C4 on the real page (`c34/`): **6 of 6 PASS**

| Browser (window rows) | Arm | C3 current | `wholeWindowCurrentAfterLastKeyMs` | C4 0.5 / 1.0 (ms) |
|---|---|---|---|---|
| Chrome (4,380) | typing | yes | 63.6 | 86.5 / 96.4 |
| Chrome | backspace | yes | 222.1 | 62.3 / 109.9 |
| Chrome | bold | yes | 1,473.5 | 68.5 / 107.2 |
| Firefox (4,092) | typing | yes | 61.2 | 151.0 / 105.4 |
| Firefox | backspace | yes | 208.6 | 62.1 / 123.1 |
| Firefox | bold | yes | 1,510.8 | 128.9 / 123.6 |

Against the predictions of spec §17.10 (recorded items, not criteria): C4 < 400 ms — **holds** in all twelve.
C3 60–200 ms (Chrome) / 120–300 ms (Firefox): typing and backspace near it (Chrome backspace 222.1 is 22 ms
over; Firefox typing 61.2 is under); **bold misses by about 1.3 s in both browsers**. The bold arm's time runs
from its last key, the third ArrowLeft, which comes before the toolbar's bold press (registered by the tools'
review as "stricter, harmless"), so the 1.5 s contains the bold command and its format barrier, not only the
window's refresh. The report has no timestamp for the bold press, so the two parts cannot be separated from
it; this is not read as slow repainting.

## C. C6 on the C′ page (`c6/`): **8 of 8 DRAWN**

Criterion pinned before any C′ run (`../review/DISPOSITION-tools.md`): DRAWN when top dark > 10,000 AND last
page dark > 10,000, no 「重繪失敗」 toast, report exists.

| Browser | Document | `docRows` | canvas rows | top dark | last page dark | 重繪失敗 | P page (same document) |
|---|---|---|---|---|---|---|---|
| Chrome | 40 p, ratio 2 wide | 98,869 | 4,380 | 147,215 | 155,206 | no | 0 / 0 |
| Chrome | 24 p, ratio 2 (control) | 59,338 | 4,380 | 147,215 | 154,850 | no | 147,194 / 154,776 |
| Chrome | 50 p, ratio 1.5 wide | 92,682 | 4,092 | 74,771 | 78,402 | no | 0 / 0 |
| Chrome | 33 p, ratio 1.5 (control) | 61,181 | 4,092 | 74,771 | 72,924 | no | 74,573 / 72,030 |
| Firefox | 40 p, ratio 2 wide | 98,869 | 4,092 | 128,041 | 135,835 | no | 0 / 0, 重繪失敗 |
| Firefox | 24 p, ratio 2 (control) | 59,338 | 4,092 | 128,041 | 135,538 | no | 127,420 / 132,867 |
| Firefox | 50 p, ratio 1.5 wide | 92,682 | 4,092 | 66,292 | 70,135 | no | 0 / 0, 重繪失敗 |
| Firefox | 33 p, ratio 1.5 (control) | 61,181 | 4,092 | 66,292 | 69,840 | no | 66,204 / 69,735 |

(`geometry.height` is the ported `GEOMETRY`'s document rows; `geometry.canvasHeight` is the canvas, the window.
P-page column from `../c6/README.md`.) The two documents finding 126 blanks whole on the P page are drawn top
and bottom on this page, by a canvas of 4,092–4,380 rows. 126's status is updated at the release step (handoff
Next 5 / 7), not here.

## D. 124-B / 125-B (`arrows/`): **PASS / PASS in both browsers**

40 ArrowDown presses then 5 letters, 1400 × 1000, owner document (the tool's verdicts exist only for exactly
40 and 5).

| | Chrome | Firefox |
|---|---|---|
| `verdict124B` | **pass** | **pass** |
| `scrollTopValuesDuringArrows` | 0, 353, 1005, 1373 | 0, 333, 674, 1049, 1359 |
| presses with the caret outside the desk | 0 | 0 |
| `verdict125B` | **pass** | **pass** |
| busy flashes during arrows (machine pill), length | 40, median 34.9 ms | 40, median 37.0 ms |
| shown pill `busy` (「處理中」 shown) | 0 | 0 |
| sink focused throughout; revision after 5 letters | yes; 5 | yes; 5 |

## What this does not cover

C2 (typing latency, a separate session on a clean desktop, after the judges' page pins are set); the C1
runtime read and the recorded items of §17.4; C5 (ii).
