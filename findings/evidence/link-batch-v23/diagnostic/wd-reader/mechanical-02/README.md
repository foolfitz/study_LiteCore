# W-D reader mechanical controls, second run

The updated W-D reader test passed all 7 test groups, JavaScript syntax check passed with no output, and `run_v23_diagnostic.py --help` exited 0.

Three of the four direct synthetic mutations were rejected: `bold-disabled`, `false-wire-bold`, and `extra-click` returned `FAIL`. The requested `wrong-click` mutation set payload fields `x` and `y` to 999999 and returned `PASS`. Repeating the control using the actual protocol fields `xTwips` and `yTwips` returned `FAIL`, matching the existing unit test. This identifies a mismatch between the requested mutation field names and the synthetic protocol payload; the requested four-control condition is therefore not satisfied.

No source, criteria, candidate, or frozen inventory files were changed. No build or browser run was performed. Complete outputs and exit codes are in `commands.json`.
