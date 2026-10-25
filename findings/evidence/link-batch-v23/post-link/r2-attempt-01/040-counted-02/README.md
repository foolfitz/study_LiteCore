# Counted 040 observations, fixed UA graph

This is a fresh counted population in phase `040-counted-02`, separated from phase 01 after the UA graph reset `fca24be7`. It contains three arms (`frame`, `html-positive`, `html-negative`), each run in Chrome and Firefox for three rounds, for 18 completed pages. All pages report `complete: true` and no fatal payload; the three `preRun.refuse` arrays are empty.

All pages bind profile `e2-editor-v23-diag-r2` and WASM SHA-256 `683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078`. The observed user-agent strings were stable within each browser: HeadlessChrome 151.0.0.0 and Firefox 157.0. Runner argv and observed progress output are recorded in `runner-commands.json` and `runner-output-observed.txt`. The reports are the source records; the progress transcript does not assert a runner exit code.

Actual aggregate reader and observation auditor invocations were run after all three reports completed. Their argv, exit codes, stdout, and stderr are preserved under `reader-captures/`. The aggregate reader returned PASS (exit 0). The auditor returned PASS (exit 0): 18 R2 pages, 24 successful opens, 180 same-generation/same-handle state witnesses, and zero problems. This records observation accounting for this population and does not claim broader cohort completion.

Generated mirror trees remain available locally for the reports; each arm's `.gitignore` excludes `/mirror/` from Git evidence commits.
