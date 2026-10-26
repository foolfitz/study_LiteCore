# Native S5 harness build 01

Built 2026-10-27 01:29 (+0800) at the owner's explicit request in the session ("幫我編譯"), after checking `uptime` (load 0.63) and `pgrep -a make` (none), and after the session's own browser preparation had finished. The command is the runbook's (`handoff/RUNBOOK-2026-10-26-v23-native-s5.md`):

```bash
python3 -I wasm_sdk_probe/tools/build_v23_native_s5_owner.py --build --out wasm_sdk_probe/build/native/v23-s5-owner-01
```

Exit 0 in 1.7 s; `build.stdout` and `build.stderr` are empty. `build-receipt.json` records `protectedInputsUnchanged: true`, `snapshotsMatch: true`, the three compiled sources (the included archived signature source still `1e29f73b…ef17`), six LibreOfficeKit header hashes, g++ 15.2.0 and the binary `4a6d9c48d18dfa4e6a41e3f859b44c8bdf4d46b060758a4cfb220339c9e43cfa` (`binary.sha256`). The build directory itself is untracked (`/wasm_sdk_probe/*` is ignored); these copies preserve its receipt. No native measurement has run.
