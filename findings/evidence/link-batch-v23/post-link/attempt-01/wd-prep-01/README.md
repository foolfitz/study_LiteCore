# W-D preparation stopped by the pre-run CPU guard

The first requested case, `d1`, exited 1 before starting a browser. The runner recorded zero pages and refused the run because the foreign CPU monitor measured a process above its 50% limit. The measured process and complete pre-run snapshot are preserved in `d1/report.json`; the exact argv and raw stdout/stderr are in `index.json` and `d1/runner.*.txt`.

No W-D page received a product verdict, no retry was attempted, and no later case was run. The local runner mirror symlink farm is retained for inspection and excluded from Git by `.gitignore`.
