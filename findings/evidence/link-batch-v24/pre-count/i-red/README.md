# Red case (i): a scratch SDK that sends typed text down the old export

Spec `specs/SPEC-M3-link-batch-v24.md` §6.3 (i) (ruling 1 (i)); default if not done or not red: T2 may not judge v24. Written before the run.

`document-sdk.scratch.js` is `wasm_sdk_probe/sdk/document-sdk.js` with one line changed (`document-sdk.scratch.diff`): `INSERT_ROUTE_BY_SOURCE` maps `beforeinput` to `"paste"`, so a typed character on the v24 profile carries `route: "paste"` and the worker calls the old export (`oxsdk_document_insert_text`, LOK paste). T3 cannot see this (the key set is unchanged); only T2 can.

Run: `tools/run_v24_feature_selection.py --population s5-type --case-id 'shift-Right@caret-mid/type' --sdk-override <this file> --keep-going`, both browsers. The cell is the plain-text type control of v23's prep-07, where paste and the keyboard give the same saved text, so T1 is expected to PASS and T2 is the only thing that can turn it red. The runner marks the report `scratch`, serves the override in place of the SDK (the plan names its hash), and records rather than enforces the inline readiness check (the readiness `Z` is mis-routed too).

Expected: each cell `FAIL` with a `T2:` reason naming `request route 'paste'` and `reply method 'paste'` for both the readiness `Z` and the typed `x`; the same page with T2 set aside (`withoutT2` in the inspection) is not a T1 failure.

## Run 01 (2026-10-28 ~11:27 +0800) — results

`run-01/` (raw cells stored as `.json.gz`, index `../i-red-run-01-storage-index.json`), runner exit 1 (both cells nonpassing, as intended; `--keep-going`).

- **Chrome and Firefox: `FAIL`**, reason `T2: insertText #0 (generation 1, text 'Z'): request route 'paste'; … reply method 'paste'; … reply completion None; insertText #1 (generation 2, text 'x'): request route 'paste'; … reply method 'paste'; … reply completion None`. The scratch SDK's hash is in the plan (`scratch.sha256` `1dcd85f3…`) and the served-source binding.
- **Correction to the expectation above:** the reader with T2 set aside (`withoutT2`) did not reach T1; it stopped at the readiness check (`readiness wire mutation differs`, NE), because the readiness `Z` carries `route: "paste"` as well. So T1 was computed directly instead (`run-01.t1-direct.txt`, v23's own `native_reference` and `s5_compare` on the `s5cand` final save vs native run-03): **True in both browsers**. The saved text is the keyboard's; only the route is wrong, and only T2 sees it.

(i) holds: T2 is red on a typed character sent down the old export.
