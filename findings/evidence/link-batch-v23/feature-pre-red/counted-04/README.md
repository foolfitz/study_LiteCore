# Historical v19 pre-red counted attempt 04

This fresh unfiltered run followed the passing wrap-line `preparation-04`. The exact command and streams are recorded beside the runner report. The runner exited 1 at Firefox `shift-Left@cell-end` during readiness validation; the saved raw cell contains the complete traceback, and its cleanup record is `{}`. This is a fatal instrumentation/readiness record, not a product verdict. No later cells ran, no retry was performed, and the aggregate judge was not run.

The first 16 cells (all Chrome cases) reported `EXPECTED_RED` with stale field `caret`. Firefox `shift-Left@caret-mid` also reported `EXPECTED_RED`; the next Firefox cell has the fatal described above. All 18 raw page records and the runner report are retained unchanged.

`integrity-summary.json` checks all page hashes against the runner report, all 15 served-source mirror hashes, the 17 runner/tooling source inputs, and ten pinned v19 profile artifacts. It does not adjudicate this incomplete population.
