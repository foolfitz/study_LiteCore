# F3-83 (2026-11-01)

Spec `specs/SPEC-M3-v29-tick-pacing.md` section 6 T3, appends 2 and 4. Finding 178.

| runner | Firefox | Chrome | page |
|---|---|---|---|
| `run_v83_f3_clipboard.py` as pinned | NE x4 (`run-01` to `run-04`) | PASS x2 | run-01 old, the rest final |
| `diag_clear_wait.py`, wait for the toast | PASS, NE, NE | NE | final |
| `diag_format_log.py`, the same plus a log | NE, NE | PASS, PASS | final |
| **`diag_single_press.py`, the first press removed** | **PASS x3** | **PASS** | final |

Cell: `clear-format-removes-every-inline-format`. Nothing else moved in any run.

**Reading** (`diag-single-press/equal.json`, on `firefox-1` and `chrome-1`): `F3_83_EQUAL`, 46/46 per browser, reading 1 exactly F3-82's four problems. `equal-self-test.json`: ALL_RED. `firefox-2`, `firefox-3`: compared cell by cell in the same way, no move.

The prediction was committed before the run (`7aca664aa`). `diag-format-log/firefox-1.format-log.json` holds the sequence that showed it: one press, two requests.
