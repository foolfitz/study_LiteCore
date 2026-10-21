# The Phase E harness and the v2 shell, exercised on ods-viewer-v1 (2026-10-21)

Not a gate run. `run_ods_viewer_phase_e.py --profile ods-viewer-v1 --only ladder/ --only upstream/fdo67682-2.ods --only upstream/tdf154005.ods`, on the mirror (no ddev), with the shell and harness page of commit 99d06192 plus the SDK's part-text pass-through and the harness/runner changes of the commit that adds this file. The engine is v1's (`dist/profiles/ods-viewer-v1`, unchanged).

Result: E1–E6 PASS (12 records). What it shows about the new code, read from `report-2026-10-21T023626Z.json`:

- The v2 shell on a v1 engine says what it had to assume: every opened file carries `adapterFallbacks: ["part-visibility-unknown"]` and `partVisible: null` (v1's manifest has no `part-info`).
- The new harness fields are recorded: `fdo67682-2.ods` parts 12–23 (hidden) are refused `PART_READBACK_MISMATCH` the v1 way, each with `setPartCalls: 1` (the engine was asked) and `readBackAfterError: 11` (it stayed on the last visible sheet). On v2 the same sheets must be `PART_HIDDEN` with `setPartCalls: 0` (V2-157 / E5).
- The form-control path: `tdf154005.ods` is refused `FORM_CONTROLS_UNSUPPORTED` before any engine with `formControlsDrawable: false` -- the harness's `formControlsSupported()` fetched v1's manifest beside the worker and found no `form-controls`.
- `selectAllWaitMs` is null throughout (v1's engine does not send it); V2-160 does not run for a profile without `part-info`.
