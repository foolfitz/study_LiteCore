# Bounded runner setup regression

The focused test invokes `run_v23_diagnostic.main()` for both the normal `all` arm and the W-D arm. It stubs only candidate identity, local mirror creation, instrument file lists, and the browser-lock boundary. The boundary raises before pre-run checks, services, or browser startup, so the test exercises actual report setup without creating any browser observations.

Before the fix, both cases failed with `UnboundLocalError` at the module-level `instrument_files()` use. The later W-D `from v23_wd_cases import instrument_files` made that name local throughout `main`. The fix aliases that import to `wd_instrument_files`, preserving the normal instrumentation binding.

After the fix, `python3 -I wasm_sdk_probe/tests/test_run_v23_diagnostic_runner_setup.py` passed both cases. The raw pre-fix failure and post-fix test output are preserved in `red-before-fix.txt` and `green-after-fix.txt`.
