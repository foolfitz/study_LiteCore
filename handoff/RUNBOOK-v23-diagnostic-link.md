# Owner link: v23 diagnostic candidate C, editor ABI 5

This is the diagnostic build boundary, not the historical feature-v23 link. The coordinating agent must confirm the engine source and required integration red cases are complete, the chosen restoration path has satisfied its native prerequisite under the current appended specification, and the final dry-run is clean before presenting the owner command. This document alone does not assert those engine gates passed. The original 45-process RESET cohort formally failed (evidence preserved); the restore-v2 harness has now been owner-built. Its DELETE Q cohort passed 45/45 across five rounds; FORMAT retains a separate native prerequisite. The engine integration is source-complete for review, but this WASM link remains blocked until the FORMAT ruling/body and final integration review are complete. If the owner never links, all WASM claims remain unestablished and the current Writer product remains unchanged.

## Artifact and source contract

- Build: `wasm_sdk_probe/build/e2/editor-v23-diag`.
- Profile: `e2-editor-v23-diag`, editor ABI 5, the complete v22 semantic editor contract and public capabilities unchanged; loader/WASM/worker hash bindings identify and verify the new candidate bytes. Feature action additions and ABI 6 come only after diagnostic gates.
- Core: `wasm-lite/build-headless-probe`, as v22, accessibility stripped. No Calc core substitution.
- Compile: v22's selection/format barriers and v20/v21 defines, plus `OXSDK_MAINLOOP_ENGINE`, `OXSDK_E2_V23_LINK_BATCH`, `OXSDK_E2_V23_DIAGNOSTIC`. No `OXSDK_FINDING_016_SCHEDULER_PROBE`.
- Link: `link_product_stack_1m` flags plus `-sSTACK_OVERFLOW_CHECK=2` in the separate `link_v23_diagnostic` macro. Its default `CHECK_NULL_WRITES` is on; record the installed Emscripten settings and resulting loader when linking.
- Worker: frozen base `sdk/sdk-worker.js`, sha256 `0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350`, concatenated with `sdk/v23-diagnostic-worker-tail.js` into this build directory only. Existing frozen worker/profile bytes are not rewritten.
- Private entrance: `_oxsdk_v23_diagnostic(kind, requestId)`; 1 queues a never-return command, 2 queues intentional missing proof, 3 calls selection LOK on the JS-side thread with an open document. Kinds 4–8 are the closed W-D inputs (range Left requiring TEXT, ShiftLeft, ShiftRight, ShiftEnd, ShiftHome), using normal ordered key dispatch and composition. See `findings/evidence/link-batch-v23/pre-link/diagnostic-packaging/private-wd-routing.md` for the owner-proxy route ruling. It is compiled only with the single diagnostic define; no public SDK method, editor action or capability is added.

The harness calls the existing engine object's `_request("v23Diagnostic", {kind: 1})` with default options. That uses the SDK's existing page-side 30-second request timeout and best-effort cancel message (including its existing late-deadline extension behavior). A cancel message does not stop a synchronous LOK hang: kind 3 blocks the worker event loop and cannot process that message; kind 1 may retain worker-side pending state. After a hang, use the existing session recovery/disposal path to terminate the worker before reuse. Kind 2's engine error follows the base worker's `fail()` path, which clears its pending entry. The diagnostic tail adds only the top-level `failureShape` to that existing error projection; it does not relabel it as a format/merge failure. To test session recovery, invoke it through the existing session action/recovery path and record the result; a harness-owned timer alone is not recovery evidence. The private tail checks exact diagnostic profile plus ABI 5 before dispatch. SDK request ids are uint32, 1 through 0xffffffff; this private C `int` entrance accepts only 1 through 0x7fffffff. Diagnostic trials use fresh engines. This bound is not a claim about the full SDK id range. Enable existing SDK debug diagnostics to receive `v23-poll` (queued, drained, replyPending) and `v23-proof-absent` events through the unchanged worker event bridge.

## Agent preparation, no compilation

From `wasm_sdk_probe`, run and retain output at fresh evidence paths:

```bash
python3 -I tools/check_v23_diagnostic_build.py --makefile Makefile
python3 -I tools/check_v23_diagnostic_build.py --self-test
python3 -I tests/v23_diagnostic_packaging_test.py
node tests/v23_diagnostic_worker_test.cjs
node tests/v23_diagnostic_error_test.cjs
python3 tests/test_ordered_engine_scope.py
python3 tests/test_ordered_format_scope.py
python3 tests/test_ordered_command_contract.py
python3 tests/test_ordered_format.py
python3 tests/test_reply_state_reads.py
make -n -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v23-diag/sdk-manifest.json > build/v23-diagnostic-dry-run.txt
python3 -I tools/check_v23_diagnostic_build.py --build-log build/v23-diagnostic-dry-run.txt
```

The last check reads planned commands, not actual build evidence. Confirm its compile/link destinations are this diagnostic directory only. Before handing over, record the final source commit and hashes, compiler/core link inputs, engine gate results, and hashes of every existing file in `dist/profiles/` and `build/archive/`. Record the baseline inventory too, so unexpected new files outside this candidate are visible. Preserve all previous attempts. Check `uptime` and `pgrep -a make`; if another build or long measurement remains active, tell the owner before requesting this link. Do not run a compiling make as an agent.

## Exact owner command

Run in Bash. Allow roughly 3–10 minutes for four small object compilations plus the full WASM link and packing; one job, no core build. The log must be new: if the command says the log already exists, stop and let the agent preserve/read that attempt rather than overwrite it.

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
(
  set -o pipefail
  unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX MAKEFLAGS MFLAGS GNUMAKEFLAGS
  if test -e build/link-v23-diagnostic-01.log; then
    echo 'Existing diagnostic log: stop and report this attempt.'
    exit 1
  fi
  make -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v23-diag/sdk-manifest.json 2>&1 | tee build/link-v23-diagnostic-01.log
)
```

Report success/failure and the final error if any. `ALLOW_FROZEN_RELINK=1` applies only to this exact target. Do not substitute any old v23, v22, Calc or feature target. Do not run a clean or core rebuild. On failure, keep the log and partial outputs and stop; a retry needs its own preserved log and a reader decision about any reused objects. The build-log checker requires actual diagnostic compile lines and exactly one link line, so an incremental-only retry log cannot establish the full build preconditions by itself.

## Agent after owner completion

1. Verify the frozen file hashes and inventory first. Any unexpected change stops this sequence.
2. Read the actual log and bytes:

   ```bash
   python3 -I tools/check_v23_diagnostic_build.py --build-log build/link-v23-diagnostic-01.log
   python3 -I tools/check_v23_diagnostic_build.py --wasm dist/profiles/e2-editor-v23-diag/probe.wasm
   python3 -I tools/check_e1_c_bundle_intact.py
   ```

3. Record actual loader/WASM/worker/manifest/export hashes. Confirm ABI 5, exact profile, full semantic editor contract and public capabilities equal v22, with all three artifact hash fields separately verified against the actual candidate files; worker is exact base plus private tail; export inventory is v22's plus the single private export. Confirm actual core link inputs still match the recorded headless core.
4. Archive those five bound files, checksum inventory and attribution under a new directory named by both WASM and worker hashes. Freeze only now, after all source edits and actual-byte checks. Never replace an existing archive generation.
5. Run specification 9.2 as amended by the latest appended rulings (currently through 18, with the private W-D route append pending the native cohort close) on this exact identity. Readers must bind profile plus WASM hash, reject v22 identity, and retain the depth-at-least-two witness and missing-proof positive control. No feature implementation follows until all diagnostic gates pass. Browser reports and source/dry-run tests are distinct evidence.

No host deployment, ddev state change, K/counting edit or Calc reopening is part of this boundary.
