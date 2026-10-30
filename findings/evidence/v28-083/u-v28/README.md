# U-v28: the shell half of SPEC-M3-v28-last-line-fallback (sections 4.3, 7.2 U-v28)

## What changed

- **Client.** `editor-shell-v2/paragraph-editor-client.js` exports `FALLBACK_REFUSED_SHAPES = ["fallback-readback-refused"]`. A new disposition branch sends dispatched + collapsed + `selectionResultSeen` + that shape to `dispatched-unverified`. `EMPTY_SELECTION_SHAPES` is unchanged.
- **Page.** `web/e2-editor-app.js` imports the list, and `run()` gives the shape its own sentence (it contains 往前多選一格, not 最後一段). The page's `workerUrl` still points at v27; the cut-over to v28 comes after the link.
- **New tests.**
  - `editor-shell-v2/tests/v28-fallback-disposition.test.mjs`: 4 tests;
  - `editor-shell-v2/tests/v28-fallback-sentence.test.mjs`: 3 tests.
- **Declared test edits** (spec 4.3 item 3). The injected parameter lists of `page-review-sentence.test.mjs`, `page-review-presentation.test.mjs` and `page-review-latency.test.mjs` now include `FALLBACK_REFUSED_SHAPES`. Their assertions are unchanged.

## Witnesses

| file | what it shows |
|---|---|
| `red-before.txt` | the new tests on the unchanged client and page: **4 red** (the disposition, the exported list, the sentence, `run()` consulting the list); 3 green, the guards that hold before and after |
| `page-tests-red-before.txt` | the three page tests on the changed page, before their parameter lists were edited: **3 red, `ReferenceError: FALLBACK_REFUSED_SHAPES is not defined`**, as review item 2 predicted |
| `shell-tests-after.txt` | `node --test editor-shell-v2/tests/*.test.mjs`: **565/566** |
| `e1-c-before.txt`, `e1-c-after.txt` | `check_e1_c_bundle_intact.py` `intact: true` both times |

## The one red in `shell-tests-after.txt` predates this change

`page-select-all.test.mjs:152`, "U2 wiring ... on profile v26", pins `workerUrl: "./profiles/e2-editor-v26/sdk-worker.js"`.

The page has pointed at v27 since the v27 cut-over (`git show HEAD:wasm_sdk_probe/web/e2-editor-app.js`, line 3850). So this test has been red by construction since generation 81, before this change. It was not named before; it is named here as **L-select-all-u2-pins-v26-profile**.

It is not fixed in this batch (owner, 2026-10-30: do not get pulled into fixing machinery). It does not test anything v28 changes.
