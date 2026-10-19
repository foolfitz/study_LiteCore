# v22 bindings for the evidence runs (SPEC-M3-link-batch-v22 §11.7 step 3; fable ruling 5 §4 step 3)

Each change moves a pin from v21 to v22, or keeps a v21 label meaning v21. None changes how a judge reads a report. §34.4: 0 / 0 (bindings and additions).

| file | change | why |
|---|---|---|
| `tools/v21_shakedown_common.py` | `DEFAULT_PROFILE` `e2-editor-v21` → `e2-editor-v22`; `EXPECTED["e2-editor-v22"]` = the archived wasm `f7a40bcc…`, loader `dc4c2c84…`, worker `0d55bcfa…`, manifest `000921c1…`, pageServed `3b96cb16…`; `build_mirror(root=…)`, optional, default `dist/` | the round's mirrors are v22's; the 0.2.24 red case needs a root other than `dist/` |
| `tools/judge_v21_shakedown_item2.py` | `WASM` → `f7a40bcc…` (the old value in the comment) | spec §12 (b): the only constant the item-2 judge reads at judging |
| `tools/diag_v21_dirty_move.py` | `V21_PAGE_PREFIX` → `3b96cb1661aba6de`; `CHROME_ONLY` loses `v11c`, `v11d` (an addition); the fix label names `common.DEFAULT_PROFILE` | F3 measures the v22 page; F3 needs V11c/V11d in Firefox |
| `tools/run_v21_shakedown_item1.py` | `dist0224` = the 0.2.24 host package from `build/archive/host-0.2.24-engine-d3cd39bbc71ec311/`, decompressed, every file checked against its `MANIFEST.json` (`host_0224_root`) | ruling 5 item 14: `dist/` is v74 now, so "dist/'s page and shell" stopped being 0.2.24's |
| `…/diag-long-paragraph/tool/diag_long_paragraph.py` | the `v21` and `v21stack<N>` pages pass `page_profile="e2-editor-v21"` | they took the default, which is now v22; without this, `v21` would silently be v22 |
| `tests/test_v21_shakedown_common.py` | the real-mirror test compares with `EXPECTED[DEFAULT_PROFILE]` and asserts the profile | it named v21's key; red after the move (the only red), green after |

## Witnesses (`mirror-identity-witness.txt`, no browser: mirrors built and hashed)

- **The default mirror** (variant label `v21`, profile `e2-editor-v22`):
  - pageServed `3b96cb16…`, shell digest `e35923a0…`;
  - all six identity checks true, `identityOk: true`, wasm `f7a40bcc…`.
- **`dist0224` from the archive** (22 files decompressed, all equal to `MANIFEST.json`):
  - pageServed **`901dd6a6…`** and shell digest **`e7c4eefe…`**: exactly `run_v21_d2.HOST_EXPECT["0224"]`'s;
  - wasm `313b08d5…` (v20).
- **Control, the old source** (`dist/` as it is today):
  - pageServed `59553850…` and shell digest `e35923a0…`;
  - neither is 0.2.24's, so the binding had to move.

## Checks

- `population-check.txt`: `v21_item2_population.py --check` against the committed `population.json`: **SAME**.
- `judge-item2-self-test.txt`: 69 red cases, 8 refusals, 1 short report, 0 problems, exit 0.
- `judge-item1-self-test.txt`: 85/85, exit 0.
- `unit-tests.txt`: the v21 tools' unit tests (item-1 judge, item-2 judge, population, common, workers, network, page hook, compare, fixtures): 83 OK.
- E1-C `intact: true`.
