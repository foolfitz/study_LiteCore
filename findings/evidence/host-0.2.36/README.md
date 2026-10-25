# Host 0.2.36 — installed Calc grid input and rectangular selection

**Installed uncounted candidate:** host `702bad6d72be5a70d9e3aaca3290b99f0d9fc1d5`, package **2b17a0e790b24eb3**. Frozen Calc `ods-editor-v1/d5a081f8`, Writer `e2-editor-v22/f7a40bcc` and readonly viewer `ods-viewer-v3/ebb7e0cb` retain their exact bytes. No relink or core compilation. Only `ods-editor.html`, `ods-editor-app.js` and `spreadsheet-shell/calc-editor-session.js` changed: **42/45 full previous records identical**.

Source acceptance is [378/378 over six browser rounds](../calc-input-range/README.md), plus focused refusal tests 8/8 per browser and units 22/22. Astra's finite-scope closure and Claude review dispositions are recorded there. Multi-cell formatting is deliberately refused; input/F2 edits the active cell after collapsing the rectangle. Saving remains manual.

## Actual Files acceptance

`input-range-host-01/report.json`: **28/28**, two setup checks and 13 per browser. Chrome and Firefox enter through actual Files URLs containing this package identity, exercise F2, replacement input, Shift and mouse selection, B/I/U refusal, active-cell collapse, manual save, server ODS XML and normal own-lock release. Two actual post-input views / **56 DOM tiles** match direct engine render. Neighbor text is preserved. No old Writer/readonly/count acceptance is inferred or rerun for reassurance.

```bash
python3 findings/evidence/host-0.2.36/read-result.py
```

The offline reader derives required checks from the executable host runner and its inherited setup, rejects empty/missing/false results and a missing browser, and checks served identity, snapshots, independent XML, manual outcome, project states, owner-document hash and lock lists.

## Installation and environment

The candidate was prepared in an isolated worktree and archived before installation; offline K0/Z0/H5-1 has zero problems and **22/22 red cases**. Guarded install and functional rollback were committed before live changes. Installation at 16:55:55–16:56:09 Asia/Taipei fast-forwarded the host, copied the exact archive, upgraded installed version to 0.2.36, left maintenance disabled and returned 401 for all three unauthenticated routes. The install guard requires the six-round acceptance reader. Rollback was prepared but not used; it restores the 0.2.35 engine while retaining the 0.2.36 host label.

`post-test-identity.json`, `cleanup.json` and before/after snapshots establish: litecore remains **running as found**, fgp-nc/nc-bridge paused and all other projects stopped; existing **24674** lock remains untouched. Owner file **24920** remains 31,008 bytes / sha256 `a84629657cf01ea0adeb26991c6f62932e2df601637ecaee0b1fa6721afa6adb`. Temporary folder/user/share were removed; no global lock table write or root command occurred. The isolated worktree was verified clean against the installed archive, then removed; branch and immutable archive remain.

Full K, global count pins, merge BINDING and chain remain deferred/batched. Nominal shipped host stays **0.2.26**. Section 34.4 **+0/+0**, cumulative **47/27**. No new human acceptance gate is required for this finite batch.
