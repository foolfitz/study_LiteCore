# O4: the first link of `ods-viewer-v1`, and the checks right after it

The owner ran `make ALLOW_FROZEN_RELINK=1 dist/profiles/ods-viewer-v1/sdk-manifest.json` on 2026-10-20,
21:16–21:18 (`link-ods-viewer-v1.log`). Runbook: `handoff/RUNBOOK-link-ods-viewer-v1.md` §3. The main
session did every check below the same evening, before anything ran on the new profile.

| check | result | file |
| --- | --- | --- |
| the frozen set (1,430 files under `dist/profiles/`, `build/archive/`) | `sha256sum -c` exit 0; 6 new files, all in `dist/profiles/ods-viewer-v1/`; none removed | `frozen-set-check.txt`, `new-files.txt` |
| the 1 MiB stack in the loader | `VERDICT PASS` on `dist/` and `build/` `probe.js` | `stack-literal.txt` |
| Calc is in the bytes | `ScDocShell` 18 times (e2-editor-v22: 0) | `bytes.txt` |
| the viewer's code is in, the editor's is not | `partBefore` present; `verified-caret-readback` absent (also checked by the recipe) | `bytes.txt` |
| E1-C | `"intact": true` | — |
| dist equals build | `cmp` equal for `probe.wasm` | — |
| the builder's E8 check, inside the recipe | ok, base pack `6f7424a1…`, same sha from the original image | `link-ods-viewer-v1.log` |

Identities: `probe.wasm` 135,185,771 bytes, sha256 `f6ab3cdb9fa50692…`; `probe.js` `c6f2ce41…`; worker
`cc2d6514…` (the pin); manifest `8f37d00a…` (`sdk-manifest.json`, copied here).

**Archived** at `wasm_sdk_probe/build/archive/ods-viewer-v1-f6ab3cdb-worker-cc2d6514/` (untracked; the
SHA256SUMS and ATTRIBUTION.md are copied here as `archive-*`), `sha256sum -c` OK.

Nothing has run on this profile yet. Its first run is Phase E's (`tools/run_ods_viewer_phase_e.py`).
