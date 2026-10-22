# ods-viewer-v2, the 160-fix link, after the link (2026-10-22)

The owner ran `bash handoff/ods-viewer-v2/link-gate0.sh` again (exit 0; `link-ods-viewer-v2-gate0.log`). Last line: `probe.wasm gzip: 47971896 bytes (cap 52428800: within)`.

Runbook G2, every reading holds (`frozen-set-after.txt`, `post-link-checks.txt`):

- Frozen set (1,543 files): only `dist/profiles/ods-viewer-v2/probe.js` and `probe.wasm` changed; no file new, none gone. The manifest (`fa54c32c`), the worker (`9c85043a`) and the base pack are byte-identical to e96e01ec's.
- Manifest: v1's + `part-info`, no `form-controls`, bits 30771. Base data and metadata identical to v1's.
- wasm: the engine's `not dispatched` line is in it (1; e96e01ec 0); v2 markers present, `verified-caret-readback` 0, `ScDocShell` 18, `OFormsCollection` 0; differs from e96e01ec and v1; stack literal PASS; E1-C intact.

Identity: **probe.wasm `aa576ce7…`**, probe.js `820bdbc8…`, worker `9c85043a…`, manifest `fa54c32c…`. Archived at `wasm_sdk_probe/build/archive/ods-viewer-v2-aa576ce7-worker-9c85043a/`.
