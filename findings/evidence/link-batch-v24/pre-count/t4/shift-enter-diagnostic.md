# Diagnostic: `the-enter-key-reaches-the-document` changed from PASS (v23) to FAIL (v24), Chrome

**Observed in T4** (`chrome/report.json`): the Enter arm PASS on both; the Shift+Enter arm on v24 has both markers in one paragraph and the paragraph count unchanged (`together: true`), but `lineBreaksBetween: false`. The check's oracle for that arm is the raw-XML substring `SHFTKEYA<text:line-break/>SHFTKEYB` in content.xml (`tools/run_e2_c_product_path.py:8724-8726`), and the check keeps booleans, not the XML.

**Replay** (`wasm_sdk_probe/tools/diag_v24_shift_enter.py`, new; Chrome, real CDP Shift+Enter, the page's own save button with the Blob kept): two products from mirrors of dist/ — **v23** = the generation-76 page and SDK from git (`c25b11c4…`, `9dcb8312…`) over the v23 profile; **v24** = dist as served.

- `shift-enter-diagnostic-01/` (only the Shift arm, a mid-line click, no save between the markers): literal present in all four (v23 ×2, v24 ×2). v24's typed text is wrapped in `<text:span text:style-name="T1">…</text:span>`, but both markers and the break sit in one span.
- `shift-enter-diagnostic-02/` (`--replay`: the check's own steps — reopen as `enter-key.odt`, both arms in order, the runner's own `LINE_INK` / `caret_click_fractions` / `place_caret_and_settle`, a save after the first marker as the check does): **reproduced 2/2 on v24, 0/2 on v23**:
  - v23: `<text:p …>SHFTKEYA<text:line-break/>SHFTKEYBE</text:p>`
  - v24: `<text:p …><text:span text:style-name="T1">SHFTKEYA<text:line-break/></text:span><text:span text:style-name="T2">SHFTKEYB</text:span>E</text:p>`
  - `T1`…`T4` in v24's automatic styles carry only `officeooo:rsid` (T1 `0005e7d8`, T2 `00070e01`); v23's save has no text automatic styles at all.

**Reading.** The line break is in the document, between the two markers, in the same paragraph, on v24 exactly as on v23. What changed is the XML around typed text: `.uno:InsertText` is Writer's keyboard insertion, which stamps each typed run with the session's rsid (`officeooo:rsid`, as desktop Writer does for typing), and the save between the two markers starts a new rsid, so the second marker lands in a second span. The paste route never wrote rsid spans. The check's substring oracle was written against paste-route XML and cannot see a line break across a span boundary. **This is not a product regression; it is an oracle that only holds for the old route's XML shape.** (Inference about rsid-per-save from the two values and the save's position; the XML itself is observed.)

Consequences, not acted on here: (a) the check would need an oracle that reads the paragraph's text with line breaks rather than a raw substring — but `tools/run_e2_c_product_path.py` is byte-bound by v23's `counted-r1-s5-01/cohort.json`, so it cannot be edited without turning v23's completion re-read red; (b) any other check or tool that compares typed text in raw content.xml will meet the same spans on v24. Decision pending (see the handoff).
