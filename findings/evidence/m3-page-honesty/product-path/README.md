# Product-path net on shell generation v54 (M3 page honesty)

`wasm_sdk_probe/tools/run_e2_c_product_path.py`, Chrome, 2026-09-29, the no-host
page from `dist/`: `--out v54-shipping-e2-editor-v8.json` (the shipped profile)
and `--profile e2-editor-v14 --out v54-profile-e2-editor-v14.json`.

| Report | Served shell | Entry page | Result | Against v53's (`m3-host-entry/product-path/host-entry-*.json`) |
|---|---|---|---|---|
| `v54-shipping-e2-editor-v8.json` | `4a92f90f…` = declared (v54) | `fc80050c…` | 40 PASS / 2 NOT_ESTABLISHED, `ok` true, 0 page errors | cell for cell the same |
| `v54-profile-e2-editor-v14.json` | `b8122702…` (the v14 repoint) | `fb00ed4d…` | 40 PASS / 2 NOT_ESTABLISHED, `ok` true, 0 page errors | cell for cell the same |

The two NOT_ESTABLISHED are the standing ones on both profiles
(`notice-action-recovers-the-session`, `a-refused-action-is-reported-and-changes-nothing`).
So the page-honesty changes (view-only mode, the leave guard, held Ctrl+S) change
nothing on the no-host product path.

`make test-e2-c-static` exit 0 on the same tree (node 116 + 5, python 108) after
one fix: the `--barrier-details-diagnostic` anchor in `run_e2_c_product_path.py`
no longer matched the page (its `run()` catch now opens with the view-only
branch); the static test that guards that anchor caught it.
