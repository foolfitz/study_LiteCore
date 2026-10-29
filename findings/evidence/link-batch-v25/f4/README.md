# F4: the four product arms on v25 / frozen generation 78, both browsers: 24/24 PASS (2026-10-29)

Spec `specs/SPEC-M3-link-batch-v25.md` 6.3 F4. Local mirror, no DDEV. Wrapper `wasm_sdk_probe/tools/run_v25_four_arms.py`, reader `tools/judge_v25_product_four_arms.py`, identity `tools/v25_four_arms_identity.py` (committed `55b3acc59` before this run). They are v24's A4 tools with v25's names; the closed list of differences is in each docstring. No V0″ preflight: v24's wrapper ran V0″ because A4-v24 was a count; F4 is a section 6.3 check, and the carried-over v24 counts are re-read by V0′ (`../cutover/`, `../freeze-78/v0/`).

Pre-run red cases (no browser, recorded in spec 15/16 and the handoff): `--preflight-only --without-override` (v76) -> NOT_ESTABLISHED, `served sdk/document-sdk.js is not the reported shell generation`; `--shell-manifest …v77.json` -> NOT_ESTABLISHED, `served web/e2-editor-app.js is not the reported shell generation`; the v25 reader on v24's counted records (`../../link-batch-v24/four-arms-counted-01/`) -> all 24 rows NOT_ESTABLISHED, `shell generation is not frozen 78`.

## Run (chrome 15:37:40-15:47:23, firefox -15:57:26 +0800)

`chrome/`, `firefox/`: each the wrapper's `wrapper.json` (override v76 -> v78 applied, file `91bc4f68…`; identity profile `e2-editor-v25`, shell `…v78.json`; pre-run refusals none; foreign CPU ok), the runner's `report.json` and `report.v23-four-arms/`, `four-arms-reader.json`. Wrapper exit 0 in both; the runner's own exit is 1 in both, because the full product-path suite has non-PASS checks (below), as on v24.

`aggregate-judge.json` (`judge_v25_product_four_arms.py`, both run dirs): **all four arms PASS, 24 rows (4 arms x 3 cells x 2 browsers), no problems.**

## The other checks of these two runs (recorded, not F4's criterion; F3 judges them on its own runs)

- Chrome: 42 PASS / 2 NE / 2 FAIL. FAIL: `the-enter-key-reaches-the-document` (I-enter-raw-substring), `a-boundary-arrow-press-does-not-cost-the-work` (I-worker-inducer-single-shot). NE: `notice-action-recovers-the-session`, `a-refused-action-is-reported-and-changes-nothing` (both long-standing; CLAUDE.md "有行為而沒有東西守著" section). All four Chrome DISPOSITIONS product cells PASS.
- Firefox: 35 PASS / 10 NE / 1 FAIL. FAIL: `an-inline-format-reaches-a-selection` (also FAIL on v24's T4; not one of the nine cells). Both Firefox product cells PASS.
