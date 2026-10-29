# P1 -- profile e2-editor-v26 is the v25 archive plus a closed list (SPEC-M3-select-all-v26 5.1)

2026-10-30. Tool `wasm_sdk_probe/tools/check_v26_profile.py`; profile assembled by
`wasm_sdk_probe/tools/build_e2_v26_select_all_profile.py` through the Makefile rule
`dist/profiles/e2-editor-v26/sdk-manifest.json` (`make -n` printed only the two python lines: no object, no link).

| file | what | verdict |
|---|---|---|
| `v25-control.json` | P1 run on `dist/profiles/e2-editor-v25` (must fail: nothing changed is not the closed list) | `P1_FAILS`, exit 1 |
| `dist-profile.json` | P1 on `dist/profiles/e2-editor-v26` | `P1_HOLDS`, population 23, ids 1..23 contiguous |
| `archive-profile.json` | P1 on `build/archive/e2-editor-v26-44cb15ea-worker-95d6e7ae` (adds `exportsEqual`) | `P1_HOLDS` |
| `red/red-cases.json` | 9 mutations of a copy of the dist profile | `RED_CASES_HOLD`: each `P1_FAILS` on its expected clause |

Identity: wasm `44cb15ea8d36f0e0…` and loader `ed1d9a55…` = v25 archive; worker `95d6e7ae375e60ef…` (the v25 worker
plus one comment line and `featureExtendPermitted` naming `e2-editor-v26`); manifest `835752a3cfa1dbe2…` (four values
changed: `profile`, `sdkVersion`, `editorContract.workerSha256`, `editorContract.actions["select-all"]`).

**Fixed by execution, before use (1):** P1's first run read the population from the literal pairs of the worker's
V2/V3/V4 action tables only and missed V1's ten names, which V2 spreads in (13 of 23). It was green anyway, so the
"every action present" clause was partly vacuous. The parser now follows `...TABLE` spreads, a contiguity clause
(ids exactly 1..N) was added, every mutation must fail its named clause (not merely fail), and the `v1-action-omitted`
mutation was added -- the old parser could not have caught it on that clause. The first red-case output was deleted
and regenerated (it was never committed).
