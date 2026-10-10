# Disposition of the dual review of the six C′ tools (2026-10-11)

Seats: `codex-review-tools.md` (codex exec -s read-only), `opus-review-tools.md` (opus subagent). Prompt:
`review-prompt-tools.md`. This is the §34.3 review of these tools: their one review; the budget is spent.
Every BLOCKING item was checked against the source by the main session before it was acted on.

| Item | Seats | Verified | Disposition |
|---|---|---|---|
| C3/C4 shim matches `render`, the SDK posts `paint` | codex 6, opus B1 | `dist/sdk/document-sdk.js:398-399` | **fixed** `f9842ce5` |
| C4 judged before the page's scroll handler moved the window; prefetch can fold | codex (latent), opus B2 | page `onDeskScroll` is a passive scroll listener | **fixed** `f9842ce5`: `windowCoversView` -- current only when the window holds the rows the desk shows; applies to the prefetch steps too |
| 125-B implements §17.2, not §17.9 (d) | codex 5, opus B3 | probe :62-82, :231-244 | **fixed** `f9842ce5`: `data-state` attribute observed, `#state-shown` inside `#state-pill`, parent not required hidden |
| 124-B/125-B accept a partial stimulus | codex 5 | probe :228 compares with `--presses` | **fixed** `f9842ce5`: verdicts only for 40 presses and 5 letters, `pass: null` otherwise |
| judge_c2 PASS under `--slots`/`--browsers` | codex 1, opus B4 | :73-83, :160 | **fixed** `f9842ce5`: every override printed; a PASS under one says it is not C2's verdict; red cases now a re-runnable script |
| compare.py takes a wrong candidate directory | codex 2, opus N2 | 0.2.10 vs 0.2.11 gives 0 | **fixed** `f9842ce5`: chain.log runners printed, `--cand-runner` REFUSES another; M3 mode prints runner/label/startedAt. **Registered**: no page or P1 check; the `--m3` list is passed by the operator (the C5 (i) reading passes all eight names of `../c5/importers-output.txt`) |
| importers.py with a wrong nonempty base | codex 3 | `--base 42e3cebd~1` printed all clear, exit 0 | **fixed** `f9842ce5`: resolved base printed; none reached = exit 3 |
| bold arm has no positive control | opus N6b | `boldApplied` recorded only | **fixed** (this commit): `boldChanges` = counter steps across the click; < 2 makes the arm NOT_JUDGED |
| batched `data-state` writes logged as the final value | opus N7 | observer pushed the current value per record | **fixed** (this commit): `attributeOldValue`, each record's new value taken from the next record |
| C6 has no verdict | opus N5 | probe reports raw counts | **criterion pinned now, no tool** (CLAUDE.md §8 kept by writing it before the run): on the C′ page a C6 cell is DRAWN when the top region's dark pixels > 10,000 AND the last page's top region's > 10,000 (P-page controls 66,204-154,776; blanks 0), no 「重繪失敗」 toast, and the report exists; anything else -- a crash, out of memory, no report -- is red |
| §17.5's C3 red case ("bands blitted only at the end of a pass") cannot turn C3 red | opus C | C3 is judged on the end state | **withdrawn** for this probe (CLAUDE.md §4): that mutation only delays, which `wholeWindowCurrentAfterLastKeyMs` records. Ruling condition 3's two red cases stand and run before any count: `../c34/make_red_pages.py` keeps off-window bands AND relabels them, so C4 can see them; label-at-reply is expected in the bold arm (and probabilistic in the typing arm) |
| C2's ratio-1 half has no reader on C′ | opus N1 | `judge_p2.py:35` pins the P page | **named step**: re-pin `judge_p2.py`'s page constant (pin line only) before reading the ratio-1 cells on the C′ page |
| C5 (ii) has no reader; caret-ignores-x rule encoded nowhere | opus N3 | -- | **registered**: C5 (ii) is read from each `--mutate` run's own report (the runner's mutation verdict), with §17.10's caret-ignores-x rule applied to that one mutation and written beside it; no new reader |
| importers.py only over the chain's runners; subprocess imports invisible | opus N4 | -- | **registered**; sufficient for C5 (i), whose runners are the chain's |
| wheel read may race smooth scrolling | opus N7 | -- | **registered** (a false FAIL, not a false PASS) |
| C3 requires no listed band outside the window; bold arm's time from the last ArrowLeft | opus N6a, N6c | -- | no change (stricter but harmless; recorded only) |

§34.4 for this stretch: **因執行而修 3** (the harness port, §17.3: `run_e2_c_page_smoke.py`, `run_e2_c_product_path.py`,
`check_m3_page_honesty.py`; their witness is still to run, see `../witness/PREDICTION.md`); **因審核而修 5**
(`probe_c_prime_window.py`, `probe_124_125_arrows.py`, `judge_c2.py`, `compare.py`, `importers.py`). The six
tools' review budget is spent: any later change to them needs a committed report whose verdict it changes.
