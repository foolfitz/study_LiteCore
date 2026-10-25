# Formal R2 W-D 120-cell cohort

The case list was derived from `v23_wd_cases.PLANS` and `FIXTURES`. For each of the 12 cases, a fresh output directory recorded five rounds in Chrome and Firefox. Each run used the exact original native `.fodt` fixture bytes, the corresponding `wd-CASE.odt` loader alias, profile `e2-editor-v23-diag-r2`, and explicit WASM SHA-256 `683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078`. Preparation outputs were not reused.

All 120 pages completed with runner exit code 0. The per-case audit checked artifact identity, SDK and W-D source graphs, served mirror bindings, copied W-D worker bytes, native fixture SHA-256, actual browser user-agent, unique page hash, and each page against `judge_v23_wd.judge` plus the corresponding `reference(case)`. All 120 cell verdicts were PASS; there were no duplicate page hashes, CPU refusals, or fatal payloads.

The explicit R2 W-D reader returned PASS for all 120 cells. The independent observation auditor returned PASS for 120 R2 pages, 120 successful opens, 2160 same-generation/same-handle accessibility witnesses, zero proof events, and zero problems. Actual reader argv, exit codes, stdout, and stderr are preserved under `reader-captures/`; each case directory contains its full report, actual runner stdout/stderr, and mechanical audit record.

This is the declared W-D observation population only. Generated `mirror/` trees remain local and are excluded from Git by this directory's `.gitignore`.
