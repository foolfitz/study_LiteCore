# Calc range formatting and committed-change autosave — complete

**Installed host 0.2.37 / package 754ae8eafd15edda.** The owner built ods-editor-v2; final native, browser, actual Files and preservation evidence is established. [Host evidence](../host-0.2.37/README.md), [owner report](../../../research/2026-10-25-calc-range-autosave.md), [ruling](../../../handoff/RULING-2026-10-25-calc-range-autosave.md). Earlier prebuild NOT_ESTABLISHED statuses remain historical in the prior handoff/specification, not the current result.

## Authoritative final cohorts

| Layer | Artifact | Result |
| --- | --- | --- |
| Owner build identity | owner-build.json | Exact supplied loader/wasm/worker/manifest hashes and bits 522291 |
| Native bridge | native-01/report.json | 22/22; direct native cap boundary, protected/merge/mixed/idempotent cases |
| Range browser | range-browser-03/report.json | Chrome/Firefox N=3; 240/240; six views / 156 real DOM tiles; ODS/script-family XML/reopen |
| Autosave v2 | auto-v2-02/report.json | Chrome/Firefox N=3; 108/108; 18 exported ODS snapshots |
| Cell compatibility | cell-v2-02/report.json | Chrome/Firefox N=1; 62/62 existing input/format/protection/download/reopen checks |
| Source guards | units-after-format-entry.txt | 59/59; 15/15 format-entry mutations rejected |
| Independent XML resolver | xml-reader-units.txt | 4/4; repeats, defaults/parents, precedence and missing/cyclic refusal |
| Actual Files | ../host-0.2.37/range-autosave-host-01/report.json | 54/54; see host reader and preservation snapshots |

```bash
python3 wasm_sdk_probe/tools/read_calc_range_format.py findings/evidence/calc-range-autosave/range-browser-03 --red-cases
python3 wasm_sdk_probe/tools/read_calc_autosave.py findings/evidence/calc-range-autosave/auto-v2-02 --red-cases
```

Range/autosave readers reject six controls each. The range reader independently parses exported styles, checks actual tile artifacts and rejects a directly corrupted ODS style as well as false/missing report populations. The autosave v2 wrapper records its actual engine binding and reuses the closed 18-case population. HOST-double evidence proves the page/engine contract; real WebDAV, server bytes, sticky host behavior and own-lock release are measured separately by the actual Files driver, not inferred from the double.

Frozen ods-editor-v2: wasm `5bc53490b95fa7a0f7f9ff2e26a6e02cd480e9867171a89d0e1ddd13f035c96f`, worker `0bed22bdb979138f1f0c23bd41bc05896e14f69e29fba10d4e42ccbcda5e1de9`. Exact six hashes are in owner-build.json and ../host-0.2.37/freeze-v2.json. No agent native compilation/relink, no frozen predecessor overwrite. E1-C remains `187706b2dcb07d2b`. Twenty-two disposable native fixture profiles were removed after the processes exited; requests, observations and ODS files remain.

## Failed, historical and superseded observations

- auto-development-01/02: allowed dirty snapshot but no timer. Actual browser DOM timer functions received the controller as their receiver. Arrow wrappers corrected it; a default-timer test and failing mutation control cover it. Development 03 passed Chrome 17/17.
- auto-final-01: began before section 17 criteria despite its name; development only, interrupted. 02 refused the still-held private browser lock during cleanup and did no measurement.
- auto-final-03: five 17-case rounds passed, last Firefox setup failed at A1/revision0/no error with zero autosave cases. Final 04 repeated a setup failure after public ready was awaited, disproving the ready-only explanation; neither report is an accepted N=3 cohort.
- address-red-01: focused B2 changed to A1 on one existing session emission. Correction 720adcc6 preserves focused text, normalizes on blur. Section18 precedes the red/fix. This proves the overwrite mechanism, not exclusive causation of every historical startup symptom.
- auto-final-05: accepted v1 mirror 108/108 and six controls, source-preparation phase only. Its current-source binding must not be relabeled as successor delivery.
- range-browser-01: all six rounds reached 38 passing checks, then the XML harness incorrectly required cell-local style names. Actual ODS correctly used column default styles. The independent XML resolver now follows ODF1.3 section 16.2 defaults/parents and compressed axes; the same 40-case population then passed in range-browser-02.
- range-browser-02 / auto-v2-01 / cell-v2-01: valid pre-shortcut-correction cohorts (240/108/62), retained with original hashes. They are not substituted for the final candidate.
- shortcut-queued-selection-source-red.json: actual page function and session with fake engine/held host showed old A1 toggle state applied after queued E5 selection. Shared toolbar/keyboard eligibility and drag-end refresh corrected it; 14 new actual-source tests and the complete 15-mutation census pass. Specification21 authorized one replay of unchanged range40/autosave18 populations for this new JS candidate.

The final range-browser-03 / auto-v2-02 / cell-v2-02 cohorts pass after that bounded correction. They are not assembled from earlier successful rounds. All failed artifacts remain intact. Ordinary readers that compare current sources reject changed current sources; use the final cohorts above for the installed candidate, not old reports with mismatching source identities.

## Reviews, scope and closure

English Claude Code requests/raw results and [dispositions](review-outcomes.md) are retained. Completed autosave review03 session `4b697d5f-b933-4ee0-834e-662ce50d0543`; completed successor review05 session `3271b97d-adf0-42d5-80df-481aa232cd86`. Review01/02 and native04 timed out without verdict; no timeout or failed bare login control was treated as approval. Astra `/root/astra_calc_scope` reused its authority for scope, complete-chain adjudication, the real shortcut correction and final artifact closure.

Autosave saves confirmed model changes and never forcibly confirms active draft/IME. Copy/stranded/export failure pauses retries; manual original success resumes. Whole-rectangle formatting is capped at65536 logical cells, includes hidden cells, refuses boundary-intersecting merges/protection before mutation, and conservatively blocks after an unknown outcome. Arbitrary parallel SDK callers, real OS IME and key reception during the pre-existing ordinary cell-commit waiting interval are not established.

All final readers, actual host/preservation and cleanup pass; no remaining human/build blocker in this batch. Full K/global counts/pins/BINDING remain deferred. The unrelated pre-existing codex-claude-code-delegation.md remains outside the batch. See the final handoff for exact retained archives and next-work limits.
