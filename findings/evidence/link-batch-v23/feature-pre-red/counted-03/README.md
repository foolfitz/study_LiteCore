# Historical v19 pre-red counted attempt 03

This fresh unfiltered run followed the passing `preparation-03` and a passing unchanged pre-run guard check. The exact command, exit status, stdout, and stderr are recorded beside the report. The runner exited 1 at the first non-`EXPECTED_RED` case.

Eight Chrome cells were captured. The first seven cases (`caret-mid`, `cell-end`, `cjk-mid`, `doc-end`, `empty-para`, `heading-mid`, and `list-mid`) each reported `EXPECTED_RED` with stale field `caret`. The eighth, `shift-Left@wrap-line-end`, reported `NOT_ESTABLISHED` with reason `wrapped prefix is not fixture text`. The run stopped immediately; no Firefox cells ran, and the aggregate judge was not run. Raw page records are retained unchanged.

`integrity-summary.json` checks captured page hashes, served-source mirror hashes, the 17 runner/tooling source inputs, and ten v19 profile artifact hashes. It does not adjudicate the stopped case.
