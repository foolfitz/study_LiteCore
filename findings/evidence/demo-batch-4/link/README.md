# The v32 link

Run by the owner, 2026-11-03 05:51 to 05:52 (+0800), `bash tools/link_demo_batch_4_owner.sh` at `b97661c9c`, exit reported by the output the owner pasted: `v32 preconditions hold` twice, then the four sha256 lines.

`link-v32-paragraph-01.log` is the `tee` of that run. The contract checks were rerun by the agent on the same files and hold. The four hashes were recomputed from `dist/profiles/e2-editor-v32/` and equal the pasted ones:

- `probe.js` a261f4c1fc72a251ca2c611e39232de87e6a6cb40eed53e729ea503bc3604c36
- `probe.wasm` 54e500931de0ee28fe5e6c9916adfef48ec7f81ae71cd432ddb1c6bc02db46fa
- `sdk-worker.js` c394302c589baff3b40ff67a7579e07cf53fc7447dd3f04b26ff9c827280ff36
- `sdk-manifest.json` 7616e19207e53fd773ec9debd6f75fd3fa10f889746855d6934fd7e9ccd916cd

Archive: `build/archive/e2-editor-v32-54e50093-worker-c394302c`.
