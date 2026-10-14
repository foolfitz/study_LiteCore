# v20 post-link checks (RUNBOOK-relink-v20 §3), 2026-10-14

The owner linked v20 at about 10:35–10:38 +0800. The main session then ran the checks below; `head.txt` records the commit they ran at.

| check | result | file |
|---|---|---|
| v8, v15, v18, v19 unchanged (16 hashes against runbook §1) | **equal**, all 16 | `sha256-profiles.txt` |
| v20 produced | wasm `313b08d5…`, loader `e6b8c74a…`, worker `478d0da1…` (the pinned tree worker), manifest `50aade86…` | `sha256-profiles.txt` |
| the new export reaches the glue | `1` mapping line `_oxsdk_document_page_rectangles"]=…=wasmExports[…]` | `export-and-calc.txt` |
| Writer only | `ScDocShell` 0 occurrences | `export-and-calc.txt` |
| X1, v20 mode (condition 49) | `VERDICT PASS`, exit 0; the moved leaves are the link outputs, the name, `sdkVersion` and the one declared leaf `.editorContract.pageRectangles` | `x1.txt` |
| M1-1, base `5d77dc84` (v15, v19, `E2_V20=probe_engine,sdk_api,editor_api`) | exit 0 | `m1-1-base-5d77dc84.txt` |
| M1-1, base `82af92ca^` (`E2_V20=probe_engine,sdk_api,editor_api`) | exit 0 | `m1-1-base-82af92ca-up.txt` |
| archive | `build/archive/e2-editor-v20-313b08d5-worker-478d0da1/` (copies of its `SHA256SUMS` and `ATTRIBUTION.md` here) | `archive-*` |

- `loader … differs (recorded, 32.1)`: v20's glue differs from v19's. This is expected, because the glue gains the new export's mapping. It is a one-time record, not a criterion.
- Not yet done: shell generation v67 is not frozen; task 10-14c (129-B on the v67 bytes, on v19) was running while the link ran, so its CPU load overlapped the link for about 3 minutes.
- Nothing binds to v20 yet. `BINDING` comes in its own commit, after the first v20 shakedown on WASM (runbook §4).
