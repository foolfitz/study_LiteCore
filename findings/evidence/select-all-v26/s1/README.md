# S1 -- Ctrl/Cmd+A on the user's path (SPEC-M3-select-all-v26 5.4 + append 1)

Tool `wasm_sdk_probe/tools/check_v26_select_all.py` (products `tools/v80_f_products.py`; document reading and harness
reads imported from `findings/evidence/select-all-v25/measure_select_all.py`, unedited). Page bytes `3b6c023e…`
(generation-80 candidate incl. finding 175), 2026-10-30 ~02:10-02:50 +0800, Chrome + Firefox.

- `run-01/report.json`: **`S1_HOLDS`**, 95/95 planned runs, five identities ok (after, before, unoffered, fake,
  v25-worker); every after run passes every clause, every counterexample is red for the right reason.
- `self-test.json`: **`ALL_RED`**, 47 clause ids each mutated once (the clause table is the population), plus
  identity-failed and run-missing.
- Readings worth knowing: copy toasts 「已複製 175 / 74 / 123 字」 equal to the clipboard's code points (C.count);
  the two frame documents answer 「複製：CLIPBOARD_EMPTY_SELECTION：…」 (L-complex-copy: honest, still the old raw
  style -- not in this spec's scope); Enter over the whole range is refused `EDITOR_FORMAT_GESTURE_UNSUPPORTED` with
  the raw toast and the document unchanged (L-enter-over-range); the three-page document's selection ends on page 3
  (y 45690), 5,935 characters copied; `unobserved` selected the whole document in both browsers (the "click first"
  refusal path is covered by U2 only).
- Not a gate run: the 11-run shakedown `s1-shake-01` (scratchpad); its copy run is finding 175's evidence
  (`findings/evidence/175/shake-run4-copy.json`).
