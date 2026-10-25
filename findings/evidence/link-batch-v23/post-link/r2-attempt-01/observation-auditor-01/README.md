# R2 observation auditor implementation evidence

This read-only auditor checks observation records and does not issue a cohort verdict. It validates the explicit R2 artifact identity, successful open replies, same-generation and same-handle accessibility witnesses during each open lifetime, proof-event attribution, and SHA-bound S-init cell inputs. The open lifetime begins at the open request timestamp because an editor-state event can precede the successful open response.

The focused causal-red suite ran with `python3 -I wasm_sdk_probe/tests/test_audit_v23_observations.py`: 15 tests passed. The suite covers missing, cross-generation, wrong-handle, and wrong-status witnesses (including a valid witness followed by a wrong same-handle status); failed opens; artifact hash drift; ordinary and attributed proof controls; unsupported schema; empty input; and S-init SHA and incomplete-cell handling.

The complete sample audit used `040-counted-01/frame/report.json` and `s-init-prep-03/report.json`, pinned to WASM SHA-256 `683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078`. It returned PASS for 11 R2 pages, 12 successful opens, and 47 state witnesses, with 6 V22 S-init baseline cells skipped and no problems. Full per-instance output is in `complete-samples.json`.

The incomplete control audited `s-init-prep-02/report.json`. It returned FAIL because the indexed R2 `chrome-r1-input-teh` cell has no page record (`r2-cell-page-missing`). This preparation record is incomplete and is not consumed evidence. Full output is in `incomplete-control.json`.

The V22-only fixture in the unit suite confirms that V22 cells are skipped only in an S-init index; an input set with no R2 pages still fails the zero-R2-pages check. These sample outputs validate accounting behavior only and do not establish cohort completion or browser behavior beyond the recorded pages.
