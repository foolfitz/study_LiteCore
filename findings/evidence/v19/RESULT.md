# v19: the round's result (X1-X7, spec §31.4)

The criteria are spec SPEC-M3-paragraph-merge §31.4 as corrected by §32-§36. The predictions were committed before the round (`PREDICTION.md`, `4a335888`). The chain ran 2026-10-08 19:52-22:52 +0800 (`chain.sh`, `chain.log`), one tool at a time. **Every item has a verdict: X1-X5 and X7 pass, X6 (diagnostic) as predicted. Two of them pass only after a ruling by fable that the owner asked for (§35, §36), and both rulings are committed verbatim.**

## Identity

- The owner linked v19 at 19:42 (`post-link/README.md`): wasm `1aafd4f9…`, loader `46b2f40a…` (= v15/v18), worker `00882139…`, manifest `902111fa…`, `withheld: ["select-all"]`. v8's, v15's and v18's twelve hashes unchanged. Archive `build/archive/e2-editor-v19-1aafd4f9-worker-00882139/`.
- Binding `8da777d7` (nine `BOUND_KEYS`, each checked against a second source); runner `73b2e9ff4b1e6fbe`, untouched since.
- `identity-at-start.txt` / `identity-at-end.txt`: equal except `tools/judge_counted_m2.py`, changed mid-chain under §34.1 (b) (§35). No chain step runs that reader.

## Verdicts

| Item | Verdict | Read from |
|---|---|---|
| X1 identity | PASS | `post-link/x1-check-profile-identity.txt` (`VERDICT PASS`; manifests differ in `.profile`, `.sdkVersion`, `.editorContract.wasmSha256` only) |
| X2 scope (M1-1) | PASS | `x2-m1-1/run.log`: green rc 0 (its line = `post-link/m1-1-after-link.txt`); `red-only-v15`, `red-inject-v8`, `red-v8-as-carrier` rc 1, each on the expected object |
| X3 W3/W5 probes | PASS | `x3-w3-w5/judge-output.txt`: W3 PASS, W5 PASS; v19's readings equal v18's committed ones (27 and 8 bands, every top equal, the same asked/answered families) |
| X4 corpus v19 vs v18 | PASS | `x4-layout-corpus/judge-output.txt`: exit 0, `VERDICT: PASS`; not comparable 5/5; not measured 23, the same set as v18's counted run; measured 48, max difference 0 px |
| X5 product path v8 vs v19 | PASS after §36 | `x5-product-path/judge-output-rejudged.txt`: `P1: HIT  P2: HIT  P3: MISS (red cells 1)`; the one cell is unclaimed under §23 row 1′ (§36.2, `census-firefox.txt`) |
| X6 owner document (diagnostic) | as predicted | `x6-v5/judge-output.txt`: `pre: HIT  O1: HIT  O2: HIT  O3: descriptive` (E02 4 of 15 soft page breaks, finding 115, as v18) |
| X7 counted M2 | PASS after §35 | `x7-counted-m2/judge-output-rejudged.txt`: exit 0, `VERDICT PASS (chrome, firefox; runner 73b2e9ff4b1e6fbe; page e00ab76a550dc12f; wasm 1aafd4f9da42fd83)` |

## X7 in numbers (both browsers)

- M2-1 60/60 `verified-key-undo`; M2-3 15; barrier 3; M2-1b 20; M2-0 every fixture; the v8 red case C01-C03 refused and reopened; identity on every report.
- M2-2: counted runner latency 103.5-158.3 ms (Chrome) / 110.5-149.7 ms (Firefox); engine `keyToUndoMs` 15-45 / 15-46 ms. M2-1b engine 30-42 / 30-30 ms.
- **M2-4 (finding 117's fix): 105/105, 0 slow presses, engine `keyToUndoMs` [min, median, max] = [30, 32, 36] ms (Chrome) and [30, 32, 33] ms (Firefox).** v18: 102 presses at 2001-2002 ms. No toast through the save (finding 118's watch).
- First reading: exit 1, `VERDICT FAIL: ['chrome control', 'firefox control']` (`judge-output.txt`). The only false field was `toastsAtEnd`, `已存出 14.2 KB` against `已存出 14.3 KB`. The cause is in the saved files: `dc:date` and `Rsid` change by a byte or two on every save, and C03's file sits on the 14.25 KB rounding edge. fable's ruling (`x7-counted-m2/fable-ruling-control.md`) is §34.1 (b), reader only; four red cases; re-judged without a re-run (§35).

## Predictions

| Prediction | Outcome |
|---|---|
| M2-4 every press engine < 300 ms | HIT (max 36 ms) |
| Y01/Y02 engine latency in the 28-49 ms band | HIT (M2-1b 30-42 ms) |
| Minimum engine `keyToUndoMs` ≥ 2 ms (§33.4, the clock-guard argument) | HIT: 15 ms (counted M2-1); M2-4's minimum 30 ms |
| X7 control: pair 0 differ | MISS on the raw pair (2 and 3 rows, KB figure only); met after §35 |
| X5.P2 precondition | HIT on the fields PREDICTION names; the copied reader's extra clause missed (§36.4) |
| X5.P3: 0 red cells | MISS by the reader (1); 0 claimed red cells under §36 |
| X5.P4: counts equal v18's run except the cells that varied | 83/84 equal; the differing cell is Firefox recovery. PREDICTION wrongly said that cell had varied in v18's run (it varied in v17's v8 arm; §36.5) |
| X4: every measured document 0 px | HIT |
| X3: v19 = v18 readings | HIT |
| X6 O1-O3 | HIT |

## Check fixes in this round (§34.4)

- **Triggered by runs: 2.** (1) the counted-M2 reader's paired control, where the KB figure is now a variable (§35, witness: the X7 reports); (2) the X5 reader copy's stale `distPageWasTheSame is False` (§36.4, witness: the six v19 X5 reports).
- **Triggered by reviews: 0.**
- Not counted, recorded: the census tool's first window (`observed.fallbackInducer`) admitted only NE records. Its own red case (2) stayed green and caught it before its first use (§36.2, `*-first-version.txt`).

## Not established

- Holding Delete down (M2-4 rests at least 0.5 s between presses), and M2-4/M2-1b on an uninstrumented page (§33.4).
- Why 038 sometimes does not wedge; the §23 blind spot (a regression that shows up as "precondition fails more often"). This round's rates show nothing: 2/23 for the candidates, 2/18 for v8.
- Anything about the host: 0.2.8 and R come after the cutover.
