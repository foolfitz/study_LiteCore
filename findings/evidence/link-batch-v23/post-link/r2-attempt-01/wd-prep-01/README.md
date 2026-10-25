# W-D N1 preparation, partial population

The 12 W-D cases were derived from `v23_wd_cases.PLANS` and its `FIXTURES` mapping. Each started runner used the exact native `.fodt` fixture bytes and the loader alias `wd-CASE.odt`, profile `e2-editor-v23-diag-r2`, explicit WASM SHA-256 `683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078`, both browsers, and one round.

Cases `d1`, `d2`, `d2p`, `d3`, and `d4` completed cleanly: 10 pages total, all PASS against `judge_v23_wd.judge` and each case's native `reference(case)`. For each report, the mechanical audit checked candidate identity, SDK/source graph and served mirror binding, W-D instrumentation hashes and copied worker bytes, exact native fixture hash, actual browser user-agent, and cross-page uniqueness.

Case `d5` was attempted next but stopped at the runner's foreign CPU guard before browser startup. Its runner exited 1 with stderr `foreign CPU load: no browser started; use a fresh output for a later trial`; the report contains zero runs. No retry was performed and later cases were not started. The attempt is preserved as an environment refusal, not a product verdict.

`population.json`, each case's `mechanical-audit.json`, runner stdout/stderr, and full report preserve the derived population and all completed/refused records. This is uncounted N1 preparation, not the final 120-cell W-D cohort; the final reader remains NOT_ESTABLISHED. Generated mirror trees are retained locally and ignored by this directory's `.gitignore`.
