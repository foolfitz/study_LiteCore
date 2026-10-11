# The page-smoke port's §34.4 witness on host 0.2.12 — production UI `Rdel` with the pre-port runners

Prediction: `../PREDICTION.md`, "Not observable on the product path" (written before the witness runs, 2026-10-11):
production UI `Rdel`, both browsers, every round — **red**, because the pre-port `POINT_AT` takes `LAST_LINE`'s
y 0.990622 as a fraction of the CANVAS box, which on C′ is the window at the top of the owner document, so the click
lands about page 4, not on the last line, and the refusal the arm expects at the document's end does not come.

Run (`run-host-rdel.sh`, attempt 2, 2026-10-11T10:37:58Z → 10:40:52Z, uncounted, one round): host 0.2.12
(`b245ae7`), page `8909564e…`, `check_m3_production_ui.py` at HEAD (`c9d51781…`), `run_e2_c_page_smoke.py`
(`5f26e3bd…`) and `check_m3_page_honesty.py` (`505f4f3a…`) both at `08d73cff`; both restored afterwards to HEAD
(`cc38ee97…`, `6540756e…`, `log.txt`). Report `pre-port-rdel.json`.

**Result: red in both browsers, as predicted, by the predicted mechanism.**

| Browser | Outcome | Failures (from the report) |
|---|---|---|
| Chrome | FAIL (0/1) | `generation 1 -> 1: no refusal-and-reopen happened`; `A1-2' R: the server's text (marker removed) is not the original's: first difference at paragraph 42, 211 paragraphs`; `A1-3: no sample outside ready/busy` |
| Firefox | FAIL (0/1) | the same three |

Paragraph 42 of 211 is the mid-document landing the prediction computed (row ≈ 0.99 × 4,092 ≈ page 4 of 22): the
marker and the delete acted there, not at the end, so no boundary refusal and no reopen. The ported runners' `Rdel`
on the same host is in the count chain (`../../../m3-production-ui/runs-0.2.12/`), which is this witness's positive
control.

So the port of `run_e2_c_page_smoke.py` (§17.3, 因執行而修 1) **has its §34.4 witness**: an honest run of the
unported runner on the release page that misjudges the product (red on a page whose `Rdel` behaviour is the count's
to judge). Attempt 1 measured nothing (`attempt-1-import-error/`).
