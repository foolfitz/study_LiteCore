# Does the Calc page have undo?

The owner asked on 2026-11-03. **No, it has no document undo.** Only the browser's own text undo inside the formula bar, before the entry is committed.

Probe `check_calc_undo.py`, mirror of the live Calc page with the frozen `ods-editor-v3` engine (the engine of host 0.2.52), real keys and pointer, the saved ODS read back. `run-calc-undo-03/`, Chrome and Firefox identical.

| Arm | Result |
|---|---|
| U1, a control named undo or redo | None |
| U2, commit `UNDOME` in D9, then Ctrl+Z | The page saw the key, sent nothing to the Worker; the saved file still holds `UNDOME` |
| U3, Ctrl+B on A1 (the file reads `bold`, so keys reach the page), then Ctrl+Z | The page saw the key, sent nothing; the file still reads `bold` |
| U4, `abc` in the formula bar, not committed, then Ctrl+Z | The field empties: the browser's text undo, which knows nothing of the document |
| U5, an `undo` request posted straight at the Worker | `UNSUPPORTED_OPERATION`: `undo is unavailable in profile ods-editor-v3` |

Why, read from the source: the Calc engine's `oxsdk_capabilities` has no `OXSDK_CAPABILITY_UNDO` (`wasm_sdk_probe/src/sdk_api.cpp:60-80`; Writer's has it), the Worker refuses `undo` without that capability, and the page binds no Ctrl+Z (`web/ods-editor-app.js:578`, only S, B, I, U). Core itself undoes a Calc write in one step natively (`demo-batch-3/native-calc-style/run-01`, spec `SPEC-P-demo-batch-3.md:105`).

So adding it is a link, not a page change: the capability bit in the Calc build, a new profile (manifest and worker carry the capability), then the page's button and Ctrl+Z.

`run-calc-undo-01` and `-02` are the probe's own failures, kept. 01 called a reader that lives in another module. 02's letters never reached a cell, the grid had no focus, so U2 read A1 and U4 an empty editor; its U5 request lacked `protocolVersion`. Both read "nothing happened" for the wrong reason, which is why 03 checks that the value landed before pressing Ctrl+Z.
