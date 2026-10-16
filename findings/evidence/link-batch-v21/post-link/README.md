# v21 post-link checks (RUNBOOK-relink-v21 §3), main session, 2026-10-16

**The link.** It ran 22:22:06–22:25:18 +0800 and make exited 0. The main session ran it at the owner's explicit request; the owner was afraid of copy-paste errors. The two pre-checks printed `0` and nothing. The full log is `link-v21.log`.

| check | result |
|---|---|
| v21 hashes | `v21-sha256.txt`: wasm `db3408f5…`, loader `0b6cf02a…`, worker `0d55bcfa…`, manifest `72067d5a…` |
| frozen set | `frozen-set-after.sha256` is identical to `../pre-link/frozen-set-before.sha256`: 1,306 files under dist/profiles and build/archive, v21 excluded |
| export in glue | `_oxsdk_document_paste_markdown` mapping: 1 |
| Writer only | `ScDocShell` in probe.wasm: 0 |
| X1 vs v20 | `x1-v21-vs-v20.txt`: VERDICT PASS. The deltas are exactly the declared ones, and "other than the link's outputs and the name: none" |
| M1-1 | `m1-1-baseB.txt` (base 523871fa, E2_V21) and `m1-1-baseA.txt` (base 5d77dc84, E2_V15/V19/V20/V21): both exit 0 |

**Archive.** `wasm_sdk_probe/build/archive/e2-editor-v21-db3408f5-worker-0d55bcfa/` holds probe.wasm, probe.js, sdk-worker.js, sdk-manifest.json and exports.txt, with SHA256SUMS and ATTRIBUTION.md. It was made right after the link and is not in git.
