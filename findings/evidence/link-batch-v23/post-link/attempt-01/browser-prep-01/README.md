# V23 diagnostic preparation smoke, round 1

One preparation-only smoke was run in Chrome and Firefox with the explicit WASM pin and `test-docs/e1/plain-grapheme.odt`. The runner exited 0. Each individual page was evaluated with `judge_v23_diagnostic.judge`: Chrome PASS and Firefox PASS; both pages were complete, had no fatal payload, and all five smoke steps passed. This is N=1 per browser for the smoke arm only. The 24-cell aggregate population was not run or claimed.

The original invocation from repository root exited 2 before launching a browser because the fixture path is relative to the SDK directory. The valid run was performed from `wasm_sdk_probe/`; both invocations are recorded in `postpack-validation.json`.

The complete browser report is `report.json`. Archive checksums and byte-for-byte checks against the profile/linked exports all passed; details are in the sibling `postpack-validation.json`.
