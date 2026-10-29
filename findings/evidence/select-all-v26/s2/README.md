# S2 -- finding 174 on the owner's path (SPEC-M3-select-all-v26 5.5)

Tool `wasm_sdk_probe/tools/check_v80_blank_bullet.py` (imports `check_v79_blank_bullet.py` unedited; products
`tools/v80_f_products.py`). 2026-10-30, Chrome + Firefox, arms noclick/click, N=3, both products.

- `run-01/report.json`: **`S2_HOLDS`**. after (generation-80 candidate) 12/12 PASS: 173's shape reached, `ready`, no
  notice, 083's sentence, the queue open, the marker in a list in the saved ODT, and the toast **not** `bad`, no
  `MUTATION_OUTCOME_UNKNOWN`, no `selection read`. before (generation 79) 12/12 red for 174: the same four B1
  clauses hold and the toast is `bad` with the code.
- `self-test.json`: `ALL_RED`, 10 mutations (toast bad / style unread / code shown / English shown / notice / marker
  out of list / before not bad / before without code / a run missing / identity failed).
- Shakedown `s2-shake-01` (1 run per product, Chrome) ran in the session scratchpad and is not kept.
