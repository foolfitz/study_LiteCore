# Page honesty §7.14: a button hidden at census is not asked to advance (2026-10-17)

The owner chose this fix (option A, 2026-10-17) over sending it to fable. SPEC-M3-page-honesty §7.14 holds the text, written before the code.

| step | file | result |
|---|---|---|
| witness (§34.4) | `../shakedown/2026-10-17T105421+0000.json` (`1e2bb146`) | Vrw Chrome on host 0.2.26: exactly one problem, `V2 control: paste-markdown did not advance`; only that button is `hidden: true` at census |
| baseline red cases, before any edit | 0.2.24 counted report `../runs/2026-10-15T183256+0000.json` | `red cases: 154 red, 0 not red or missing` |
| two new red cases, old clause | same report | 158 red (both new cases red in both browsers) |
| the clause change | `check_m3_page_honesty.py` (`47fa9a43…` → `3eab7432…`) | `red-cases-after-fix.txt`: 158 red, 0 missing |
| the new case 1 catches the wrong exemption | the clause temporarily as `not any(hidden.values())` (any hidden button exempts every button) | 156 red, 2 GREEN: case 1 in both browsers; file restored, sha checked |
| the witness re-scored | `witness-rescored-after-fix.txt` | `VERDICT clean  Vrw/chrome:1/1` |
| live, after the fix | `../shakedown/2026-10-17T110651+0000.json` | `VERDICT clean` Vrw and Vro, Chrome and Firefox, 1 round each. paste-markdown: Vrw rev 20 → 20 (exempt), Vro rev 0 → 0, pending 0, ready (still clicked in read-only) |

§34.4: **repaired because of execution +1** (this clause; witness above). Repaired because of review: 0.
