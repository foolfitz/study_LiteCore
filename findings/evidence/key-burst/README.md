# Key bursts on the Writer page (SPEC-P-key-burst, finding 130's limit)

Tool: `wasm_sdk_probe/tools/check_key_burst.py` (sha256 in each `report.json` under `tool`). Mirror of `dist/` with the
page sources (`web/e2-editor.html`, `web/e2-editor-app.js`, unchanged since generation 90) and the v2 session under
test; real keys (CDP in Chrome, WebDriver actions in Firefox); a fresh `test-docs/t1-plain-zh.odt` per cell; click,
Ctrl+Home, input, quiet, toolbar save, the saved Blob read. Dev profile run: no freeze, no host.

| Run | Session | Verdict | Red |
|---|---|---|---|
| `kb-01/` | working tree (merge + seal) | `KB_HOLDS`, 10/10 per browser | none |
| `red-baseline/` | `dist/` (generation 90, `d6ee514e...`) | `RED_AS_NAMED` (K1) | K1 both bursts, their K4 notice, K6 |
| `red-no-seal/` | working tree without the seal in `_enqueue` | `RED_AS_NAMED` (K3) | K3 only: `abcde` instead of `abdxe` |
| `red-no-merge/` | working tree, merge condition always false | `RED_AS_NAMED` (K1) | as the baseline |

What the cells read (both browsers the same unless noted):

- Baseline: 14 and 40 back-to-back keys keep the first 8; the page shows "有字沒有輸入：打得比引擎處理得快" (the notice
  0.2.57 fixed). 60 keys at 30 ms: all 60 arrive (the engine keeps up at the key-repeat rate here).
- Live: 14 keys in 2 `insertText` requests, 40 keys in 2 (Chrome) or 3 (Firefox); nothing lost, no notice.
- K3 live: `abc`, Backspace, `de`, ArrowLeft, `x` gives `abdxe` in 4 inserts; without the seal the delete and the
  move run after the merged text (`abcde`).
- K6: one Ctrl+Z after `ab cd ef gh` removes `gh` both when typed at 150 ms per key (11 inserts, the reference) and
  as a burst merged into 2 inserts: Writer's undo grouping is the same for one `.uno:InsertText` of the string.

Unit tests: `wasm_sdk_probe/editor-shell-v2/tests/key-burst.test.mjs` (11). All node tests in the tree: 1025/1025.
E1-C bundle: `intact: true` (the adapter file is not changed; the merge wraps the session's adapter instance).
