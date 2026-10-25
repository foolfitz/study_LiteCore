# Link attempt 01 mechanical audit

The full first link log is preserved as `link-v23-diagnostic-01.log`. Its final command reports that the expected SDK worker checksum `0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350` did not match `sdk/sdk-worker.js`, and make exited with an error. The current SDK worker SHA-256 is `0bed22bdb979138f1f0c23bd41bc05896e14f69e29fba10d4e42ccbcda5e1de9`.

The diagnostic build directory contains `probe.js`, `probe.wasm`, `exports.txt`, and four object files; their sizes, SHA-256 values, and modification times are in `audit.json`. No diagnostic candidate files were found under `dist/`, and the diagnostic profile directory, worker, and manifest are absent.

Both the profile/archive frozen inventory and its file hashes remain exact: 2,315 baseline files, 2,315 actual files, zero missing, zero extra, and zero mismatches. The v22 profile and archive worker both hash to `0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350`.

The existing build checker was run in its separate `--build-log` and `--wasm` modes; both returned `preconditions hold`. Its CLI rejects using those mutually exclusive arguments together; the rejected attempt and both supported invocations are preserved in `commands.json`. This report records the mechanically observed outputs for the owner and adjudicator.
