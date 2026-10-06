# Product-path net on shell generation v55 (M3 production UI)

`wasm_sdk_probe/tools/run_e2_c_product_path.py`, Chrome, 2026-10-06, the no-host page from `dist/`:
`--out v55-shipping-e2-editor-v8.json` (the shipped profile) and
`--profile e2-editor-v14 --out v55-profile-e2-editor-v14.json`.

| Report | Served shell | Entry page | Result | Against v54's (`m3-page-honesty/product-path/v54-*.json`) |
|---|---|---|---|---|
| `v55-shipping-e2-editor-v8.json` | `2470765a…` = declared (v55) | `e97d6e03…` | 40 PASS / 2 NOT_ESTABLISHED, `ok` true, no page errors | cell for cell the same |
| `v55-profile-e2-editor-v14.json` | `ccf52114…` (the v14 repoint) | `47fea25c…` | 40 PASS / 2 NOT_ESTABLISHED, `ok` true, no page errors | cell for cell the same |

The two NOT_ESTABLISHED are the standing ones on both profiles
(`notice-action-recovers-the-session`, `a-refused-action-is-reported-and-changes-nothing`).
SPEC-M3-production-ui §10 (review item 20) predicted no cell would change: the net never reaches a
paragraph-boundary refusal, let alone a third one, and its saves in a stopped session already
returned an empty capture before the toolbar was disabled there. Measured: none changed.

The first v14 run was cut off at 09:06 local when the Claude Code session ended (the process was
stopped with it); this one is the rerun, complete.

`make test-e2-c-static` exit 0 on the tree that froze v55 (`72549b38`; node 135 + 5, python 108),
after re-anchoring two checks that read the line `saveOnce()` now takes its bytes on
(the net's `save` mutation, and relink-queue item `queue-product-save-button-writes-object-object`).
