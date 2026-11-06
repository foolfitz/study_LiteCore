# Calc sheets (SPEC-P-calc-sheets): evidence

Spec: `specs/SPEC-P-calc-sheets.md`. This covers seeing a sheet's identity (Collabora's three: a lock on a protected sheet's tab, the sheet's position in the status bar, a name box that takes a sheet) and pointing at cells, including on another sheet, to write a formula. There is no engine change: every page run uses the frozen `dist/profiles/ods-editor-v6`.

| Path | What |
|---|---|
| `e1/` | `tools/probe_calc_sheets_native.py` on the native 26.8 core (the copy harness from `../calc-copy/native-build-01`), fixture `tools/create_calc_sheets_fixture.py`. A measurement, not a verdict: how the core reads and writes a reference to another sheet. It quotes a name only when needed (`$'有 空白'.B1`, `$'2026'.B1`, `$'O''Neil'.B1`; not `$Sheet_3.B1` or `$另一張表.A1`), matches names without case, and gives `#NAME?` for Excel's `Sheet!A1` |
| `p-01/` | `tools/check_calc_sheets.py`, Chrome and Firefox: **P_HOLDS**, 9/9 each. Run on the page before one refactor (the "another sheet is shown" test moved from a page function into the session's `state.away`, so that `check_calc_format_entry_mutations.py` can read `formatAvailable`) |
| `p-02/` | The same tool on the committed page bytes: **P_HOLDS**, 9/9 in each browser |
| `p-red-never-quote/` | Red case (a): sheet names never quoted → **MUTATION_RED**, red in P-T6 only |
| `p-red-browse-commits/` | Red case (b): a tab click with the caret in a slot commits (`showPart` in place of `browsePart`) → **MUTATION_RED** in P-T5, and in P-T6 and P-T8, which also browse |

Before the formal runs there was a Chrome trial in a scratchpad, which does not count. P-T1–T6, T8 and T9 passed. P-T7 crashed because H4 is on the fixture's hidden row 4, which has no row header to click. Spec append 1 moved P-T7 to H7. A Firefox trial could not open the fixture, because snap Firefox cannot read the scratchpad under `/tmp`. The formal runs write under `findings/`.

Also run on the final code: the node suite (every `*.test.mjs` outside build/ and dist/), 1045/1045. That is 1037 + U-T1..U-T3 + 4 v7 worker tests + the format test's new `away` case, which is red against the page before this change. The three Calc mutation tools pass, and `!state.away` is one of the 12 format predicates rejected.
