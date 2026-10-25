# Bounded diagnostic browser protocol (before first actual execution)

This implements existing SPEC-M3-ordered-commands sections 9.2, 15.4 and 16.5 only. It adds no product actions or acceptance population. Chrome and Firefox, three fresh processes per arm per browser. Arms are the executable `ARMS` in `tools/judge_v23_diagnostic.py`: smoke, proof, hang, js-thread. An absent arm, missing observation or missing positive control is NOT_ESTABLISHED. One-round preparation is never a completed cohort. No execution has occurred when this protocol is introduced.

The explicit candidate SHA256 must be copied from the actual owner-linked `e2-editor-v23-diag` WASM. Before starting and before every process the runner reads the profile, WASM, loader, worker and manifest. The page independently fetches and hashes the same artifacts. The reader reads actual files again and requires exact identity. ABI5 alone does not identify v23; v22 is a mandatory synthetic red case. A changed candidate requires a new output directory. Build-log preconditions remain the separate build reader's responsibility.

Every arm opens the same supplied ODT in the existing NarrowEditorV2Session and records actual worker requests/responses, debug events, worker creation/termination and performance timestamps. Every actual open, including recovery opens, requires its successful response and following actual editor-state a11y read (`core-built-without-accessibility`). The harness never substitutes manifest/source configuration for this read. The SDK uses its existing default timeout; no timer or LOK behavior is patched.

* Smoke: open; commit the ASCII marker `V23_DIAGNOSTIC_TOKEN`; move one character left; save actual ODT; verify marker in saved content.xml; send two concurrent editorGetStateV2 requests directly through Engine._request, bypassing the session serial queue. Every recorded poll drains at most one command, never drains with a reply pending, and never sends a reply and drains together. At least one recorded entry depth must be >=2, otherwise NE. Ordinary missing-proof events must be zero.
* Proof control: enqueue the private kind2 through the actual session queue. Require a matching private-entry event and exactly one matching cumulative-count1 UNO_COMMAND_RESULT missing-proof event, plus the SDK's MUTATION_OUTCOME_UNKNOWN rejection with its exact failureShape. No fabricated result or fake WASM can count.
* Never-return control: enqueue private kind1 through the actual session queue; require matching entry, existing SDK TIMEOUT with timeoutMs30000, actual recoverable-error session state, session.restart replacing the terminated worker, a successful recovery open and save. Timestamps record the observed timeout and recovery latency without inventing a new allowance. If existing SDK late-deadline grace occurs, retain full error details and do not reinterpret it as an exact 30-second observation.
* JS-thread negative control: the same procedure with private kind3's direct LOK selection entrance on an open document. An observed return is a failure of the required positive hang control; absent entry is NE. This control does not establish the separate frame/destroy positive arms.

The 300-second runner bound is only an observation limit and owned-process cleanup boundary; it cannot establish SDK recovery. Fresh output paths prevent overwriting earlier failures. The existing shared browser lock serializes all runs; browser and HTTP server cleanup target only owned processes. No host, service configuration, live file, frozen profile, build or release counter is touched.

## Explicitly unclosed

W-D and its native-seq comparison, S-init, 040-W frame and destroy, largest fixture/64KiB Markdown/long60, S-move-dirty, idle-layout/tile latency, functional ABI6, host/product-path gates and K remain separate work. A bounded PASS is never all of section9.2.

## Commands after owner link

From `wasm_sdk_probe`, with the actual candidate hash and a small existing ODT fixture:

```sh
python3 -I tools/run_v23_diagnostic.py --wasm-sha256 SHA256 --fixture PATH.odt --output ../findings/evidence/link-batch-v23/browser-diagnostic/run-01
python3 -I tools/judge_v23_diagnostic.py ../findings/evidence/link-batch-v23/browser-diagnostic/run-01/report.json --profile-dir dist/profiles/e2-editor-v23-diag --wasm-sha256 SHA256
```

The runner defaults to the full24-process bounded population. Source/VM/reader tests are preparation only and must be reported separately from these actual browser runs.
