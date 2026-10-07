# Paragraph merge, native round R0c-frame — the E shape inside a text frame (written 2026-10-07, before it ran)

Why: spec §18.1 N1 — inside a Writer text frame (fly frame), Writer can queue TEXT_SELECTION as a normal callback ahead of the flush-time START/END that the E shape's fence reads, so WASM is expected to refuse there (`anchor-mismatch`). That is a WASM flush-order question the native probe cannot see (it records the last START/END, not their order). This round gives what WASM is compared against: Writer's own key inside a frame, and whether the E shape's premises (Escape, K2, text equality, fence) hold there natively.

Input: `wasm_sdk_probe/test-docs/merge/text-frame.fodt` → `test-docs/merge/odt/text-frame.odt` (native 26.8 `soffice --headless --convert-to odt`, throwaway profile, once; the frame survives the conversion: `draw:frame` `Frame1`, anchored to a paragraph). Cases `test-docs/merge/text-frame.cases.tsv`: **F01** Delete at the end of "F01 frame first"; **F02** Backspace at the start of "F01 frame second".

Run (from `wasm_sdk_probe/`, only when no browser run is going; the probe's readbacks rely on fixed waits):
`MERGE_ESHAPE=1 MERGE_FOLLOW_TEXT=Z tools/run_merge_native.sh ../findings/evidence/merge-native/r0c-frame 3 test-docs/merge/odt/text-frame.odt test-docs/merge/text-frame.cases.tsv 1`, then `tools/check_merge_eshape.py ../findings/evidence/merge-native/r0c-frame/round-*` (it will STOP on "vacuous" — only two cases, no nothing-selected or refusal class; read the per-case decisions and KILL lines).

Predictions: placement check finds both anchors inside the frame; both cases `merge` in all three rounds; 0 KILL (Escape empties the selection without moving the point, K2 selects K1's text, its point side passes the fence, the E-shape document equals the key arm); the key arm merges the two frame paragraphs (`Delete paragraph`).

What would change the decision: a KILL natively means the E shape is wrong inside frames regardless of N1 — refuse frames explicitly in the engine before WASM. As predicted: the WASM shakedown's frame case is compared with these key-arm documents; if WASM refuses (`anchor-mismatch`), N1 is confirmed as a named limit; if it merges and matches, N1 did not bite on this shape.
