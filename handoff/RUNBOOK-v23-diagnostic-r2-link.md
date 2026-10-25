# Owner link: the minimal r2 literal-040 diagnostic successor

This command builds only `e2-editor-v23-diag-r2` into new `build/e2/editor-v23-diag-r2` and `dist/profiles/e2-editor-v23-diag-r2` directories. The original `52cf9d23` WASM / `889edcde` worker profile and archive remain frozen. Never substitute the original diagnostic target or reuse its objects. No Calc/core/host changes belong to this work.

Authority: committed English ruling `handoff/RULING-2026-10-26-v23-s-init-and-040.md` and appended specification section 20. Source commits `8816cc9d` and `4f119450` add only the queued kind9 HTML entrance and its diagnostic identity/worker/tooling. ABI remains 5, the complete v22 public semantic editor contract stays unchanged, and the core is still `wasm-lite/build-headless-probe`. No public 037 guard is relaxed. Kinds1–8 remain; kind10 is refused. The single `OXSDK_E2_V23_DIAGNOSTIC` define still contains all instrumentation.

Pre-link evidence: `findings/evidence/link-batch-v23/pre-link/diagnostic-r2-01/`. The coordinating agent reviews this exact source/check boundary before presenting the command. Syntax-only, fake-LOK causal controls, actual archived-base worker tests, packing fault controls, exact target dry-run and legacy preprocessing have passed. Those are not WASM/browser results. The original bounded cohort's failed observations remain attributed to the original identity.

## Exact owner command

Run from Bash, about 3–10 minutes for four small objects plus one full WASM link and packing, one job, no core rebuild. A fresh log is mandatory.

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
(
  set -o pipefail
  unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX MAKEFLAGS MFLAGS GNUMAKEFLAGS
  if test -e build/link-v23-diagnostic-r2-01.log; then
    echo 'Existing r2 log: stop and report this preserved attempt.'
    exit 1
  fi
  make -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v23-diag-r2/sdk-manifest.json 2>&1 | tee build/link-v23-diagnostic-r2-01.log
)
```

The worker base preflight must run before object compilation: it checks the actual archived v22 bytes, not the current Calc source worker. The derived worker is that archive plus `sdk/v23-diagnostic-r2-worker-tail.js`. The new wrapper accepts exactly the r2 identity; the original wrapper still accepts exactly the original identity by default. Both verify the complete v22 semantic contract and actual artifact hash bindings.

Do not clean, retry, repack, or rerun a link automatically after a failure. Preserve partial outputs and the log; read the exact failure first. The old packaging-resume tool is bound to attempt01's old audited source and is not a retry path for this successor.

## After owner completion

1. Compare all preexisting files against `diagnostic-r2-01/frozen-before.json` (2,326 files). No prior profile/archive file may change; only the newly created r2 profile is outside that inventory.
2. Read actual evidence, with the explicit successor identity:

   ```bash
   python3 -I tools/check_v23_diagnostic_build.py --build-log build/link-v23-diagnostic-r2-01.log --profile e2-editor-v23-diag-r2
   python3 -I tools/check_v23_diagnostic_build.py --wasm dist/profiles/e2-editor-v23-diag-r2/probe.wasm --profile e2-editor-v23-diag-r2
   python3 -I tools/check_e1_c_bundle_intact.py
   ```

3. Check actual compiled source/core inputs against the boundary, actual manifest ABI5/profile, complete public contract equality to v22, export inventory, and exact archived-base-plus-r2-tail worker bytes. Record hashes of loader, WASM, worker, manifest and exports. The link log must show four fresh object compilations and one diagnostic link with `STACK_OVERFLOW_CHECK=2`, the same core, and no scheduler-probe define.
4. Archive those five actual files under a new name containing the new WASM and worker hash prefixes, with checksums and attribution. Never replace the old diagnostic archive or predeclare the new actual hashes.
5. Run only the predeclared successor diagnostic/corrected040/S-init populations against this identity; the scope ruling and artifact readers decide their outcomes. Missing/failed runtime proof remains unestablished/failed. No ABI6 feature implementation follows until the diagnostic decision is established.

## Private kind9 wire contract

The harness calls existing `Engine._request('v23Diagnostic', {kind:9})`, with its default timeout and normal pending lifecycle. It must establish and record the ruling's actual COMPLEX image-bearing selection before counting.

The engine queue dispatch emits `{type:'v23-control',kind:9,requestId}`, then calls literally `getTextSelection(document,"text/html",nullptr)` on the engine thread. On return it emits `{type:'v23-html-return',requestId,html,bytes}`. `bytes` is the actual UTF-8 byte count. At the first post-command poll, the cached owned string produces private `v23-html-result`; the r2 tail calls the unchanged base completion helper, returning SDK `{html,bytes}` and clearing pending/open state. Entry/return events alone cannot complete the request. Empty/native-null HTML becomes empty string/zero bytes; the literal040 reader must reject an absent image witness. No arbitrary MIME, UNO or key parameter is exposed. Kind3's existing wrong-thread negative entrance is unchanged.
