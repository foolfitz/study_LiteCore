# V23 pre-link mechanical verification

The four requested mechanical commands completed with exit code 0. The two Python test files reported 6 and 10 passing tests. The JavaScript syntax check produced no output. The diagnostic build precondition checker reported `preconditions hold`.

The frozen-before snapshot recorded 2,315 files. Every recorded path under `wasm_sdk_probe/` matched its recorded byte size and SHA-256. Inventory comparison across `dist/profiles/` and `build/archive/` found 2,315 expected and 2,315 actual files, with zero missing or extra files.

The explicit source input list verified 48 of 48 files with zero mismatches. The explicit core input list verified 189 of 189 files with zero mismatches. The source commit identifiers in those records are metadata; verification compared each listed file's current bytes and SHA-256 against the recorded values.

See `commands.json` for argv, exit codes, and complete command output. See `hash-and-inventory.json` for per-file mismatches and the inventory comparison. These checks do not establish browser behavior. No build was run and no input files were modified.
