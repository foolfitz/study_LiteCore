# Owner build: Calc range-format successor

Status: source and executable probe preparation only. No native compile, WebAssembly link, native range test or v2 browser acceptance has been performed by the agent. The installed host remains 0.2.36 with frozen ods-editor-v1. Autosave's v1 development/acceptance results do not establish native range behavior.

The current instructions reserve compiling commands for the owner. This is a small native bridge/driver build and a successor SDK compile/link against existing core libraries; it is **not a LibreOffice core rebuild**. Expected duration is roughly 3–10 minutes on this workstation, an estimate rather than a measured v2 duration. Output stays under `wasm_sdk_probe/build/`; no root access is needed, and no installed profile is overwritten.

## Owner commands

Run in Bash:

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
uptime
pgrep -a make
```

If another build or long measurement is active, defer this build. `pgrep` returning exit 1 with no output means no matching make process was found. When the machine is available:

```bash
make -j1 build/calc-range-native/calc-cell-native build/ods/editor-v2/profile/sdk-manifest.json
```

Report completion and the printed profile/hash JSON, or the first compiler/link error and its surrounding lines. Expected profile: `ods-editor-v2`; capability bits: **522291**; added capability: `cell-range-formatting`; range limit: **65536**. The old v1 manifest and wasm must remain untouched. Do not pass a frozen-relink override. The Makefile's native target uses `build-native-26-8`; the wasm target uses the already-built `wasm-lite/build-ods-viewer-v2` core, exactly as the existing cell profile did.

The agent has run only `make -n` to inspect this dependency graph. That dry run requested the small bridge/driver and four SDK objects plus linking, with no core build target.

## Agent continuation after the owner reports a successful build

Run from the study repository root. These commands execute tests only and do not compile:

```bash
python3 wasm_sdk_probe/tools/probe_calc_range_native.py --out findings/evidence/calc-range-autosave/native-01
```

The native probe opens fresh owned fixtures and calls the native bridge directly, bypassing JavaScript's cap validation. Its 22 finite cases cover each format across ordinary/contained-merge/hidden/protected/boundary-refused ranges, mixed→on→off/idempotence, and the exact 65536/65537 boundary. Inspect actual failures before changing either implementation or checks. This probe does not measure protocol revision or UI behavior; those belong to the browser layer.

```bash
python3 wasm_sdk_probe/tools/probe_calc_range_format.py --profile wasm_sdk_probe/build/ods/editor-v2/profile --out findings/evidence/calc-range-autosave/range-browser-01 --browsers chrome,firefox --repeats 3
python3 wasm_sdk_probe/tools/read_calc_range_format.py findings/evidence/calc-range-autosave/range-browser-01 --red-cases
```

The browser probe creates an isolated mirror and changes **only that mirror's** engine URL to `profiles/ods-editor-v2/sdk-worker.js`; the manifest and all engine file hashes are recorded. It does not change the product's current v1 default or overwrite dist. Its executable check population is derived by the reader (currently 40 per run). It includes real toolbar mixed/on/off transitions, explicit targeting despite unrelated cursor reads, all fixture-defined native refusals, stale revision, SDK cap, hidden inclusion, neighbors/other sheet, actual tile comparison, exported script-family styles and reopen into a new session. Direct SDK diagnostic setup writes invalidate the mirror scheduler before any subsequent UI event; they are not represented as product toolbar evidence.

Neither probe has yet run against v2. Test-harness errors must be recorded separately from product failures. Use a new `*-02` directory for a repeated attempt rather than overwriting observations. Run the existing focused input/selection regression with appropriate v2 expectations; the old v1 range-format-refusal assertions cannot be relabeled as v2 acceptance.

After range acceptance, run the combined candidate's actual Files autosave/range routes with fresh owned fixtures and its own lock tokens. Re-read actual service state, preserve owner document 24920 and unrelated lock 24674, and perform no global lock cleanup. Then archive exact accepted bytes, freeze the new v2 identity, prepare a package and guarded install/rollback, and switch the product's engine URL only in that reviewed candidate. Full K, global counts/pins and BINDING remain deferred.

## Available checks before native build

```bash
node --test wasm_sdk_probe/tests/calc-document-sdk.test.mjs wasm_sdk_probe/tests/calc-editor-session.test.mjs wasm_sdk_probe/tests/calc-host-contract.test.mjs
python3 wasm_sdk_probe/tools/check_calc_range_mutations.py
```

These passed 27 unit cases and six executable mutation controls in this preparation round. They establish SDK/session refusal, explicit-target and committed-only-save behavior against test doubles; they do not prove that native UNO compilation or range writes succeed. See the separate autosave artifact reader for that layer's counted run and source identities.
