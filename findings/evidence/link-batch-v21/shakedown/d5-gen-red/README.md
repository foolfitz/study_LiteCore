# D5-gen: red first (ARMS-item1.md D5, ruling D-11 B)

`wasm_sdk_probe/editor-shell-v2/tests/page-document-keys-generated.test.mjs` generates D5's binding axis from the page's own `DOCUMENT_KEY_ACTIONS` × {Ctrl, Cmd} × {absent (the real v20 manifest), withheld, declared}, plus Shift/Alt/IME never taken.

- `scratch-page.diff` is the mutation: a fictional third key (`PageUp`) appended to `DOCUMENT_KEY_ACTIONS`, and `documentKeyAction` taking it whatever the profile offers. The scratch page lives only in the session scratchpad; the tree's page is unchanged.
- `transcript.txt`: on the tree's page the generated test is green (17/17). On the scratch page it is red (4 failures: Ctrl/Cmd+PageUp taken while the action is absent or withheld), and the hand-listed `page-document-keys.test.mjs` stays green (18/18) on the same scratch page, because its rows do not include the new key [observed]. This is the difference between the hand enumeration and the 「工具封閉」 form the criterion names.
