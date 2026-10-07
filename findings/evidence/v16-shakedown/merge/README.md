# v16 merge (option B) on WASM: the uncounted shakedown

Runner: `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py` (written 2026-10-07; **not counted, instrumented** -- a classic script
in the served HTML wraps `Worker` and writes what the document worker answered into a DOM node; the design has had no
adversarial review yet). Chrome only, `--candidate-profile e2-editor-v16`, one round, the cases
C01 C02 I02 C11 Y01 C29 C30 C17 C15 F01, after M2-0 on both fixtures. Expectations come from R0c's decisions
(`merge-native/r0c/eshape.json`, `r0c-frame/`); references are the native key arms `r1-<case>-key.odt` and `-key-follow.odt`.

| report | page served | what it shows |
|---|---|---|
| `shakedown-chrome-1.json` | **dist/e2-editor-app.js** repointed (the v8-era page) | the wrong page: B's refusal wording and the 84-retry BUSY budget are not in it; every refusal toast says the old 「文件沒有被改動」, including C15 with `keyPosted:true`; two 「重繪失敗：BUSY」 toasts on C15. C11 not run (placement: Home at a bulleted paragraph's start went in front of the label, x 1778 against the native 2138) |
| `shakedown-chrome-2.json` | **web/e2-editor-app.js** repointed (the cutover tool's source, page sha256 `3cf01330...`) | below |

Run 2, per case (generation = the page's `#s-generation` before and after the key):

| case | expected (R0c) | outcome | generation | key→reply | document after the key / after a typed `Z` |
|---|---|---|---|---|---|
| C01 C02 I02 C11 | merge | `verified-key-undo`, `Delete paragraph`, restorePresses 0 | 1→1 | 122–144 ms | paragraph text = native key arm / = native key-follow |
| Y01 (`x` then Delete at once) | typed-merge | `verified-key-undo` (actionsBefore 1) | 1→1 | 752 ms (engine `keyToUndoMs` 629) | text = native |
| C29 C30 | nothing-selected | refused `nothing-selected`, keyPosted false | 1→2 | 255 ms | reopened = original + marker; toast 「這一下沒有取得可刪除的內容。文件沒有被改動…」 |
| C17 | refused-k1-anchor | refused `anchor-mismatch`, keyPosted false | 1→2 | 42 ms | reopened = original + marker; 「這裡目前還不能這樣刪除。文件沒有被改動…」 |
| C15 | key-noop | refused `key-deadline`, **keyPosted true** | 1→2 | 2095 ms | reopened = original + marker; toast 「這一下刪除送出了，但沒能確認它做了什麼，正在重新載入…」 (no 「沒有被改動」); the second toast was not seen |
| F01 (text frame) | merge natively | refused **`anchor-mismatch`** (both runs) | 1→2 | 38 ms | spec 18.1 N1 holds on WASM; an extra toast 「重繪失敗：ENGINE_DISPOSED：engine is disposed」 during the reopen (also on C17 in run 1) |

Not satisfied or not measured:
- **M2-0: `content.xml` bytes differ from native on both fixtures** (paragraph text equal). Every merge compares equal by text and
  unequal by bytes, so no byte criterion can be judged until a reduction is derived from that diff and appended to the spec.
- Runner limit: the refusal arms type the marker at C01's native caret, which is a boundaries.odt position; on text-frame.odt
  (F01) it lands elsewhere, so F01's reopen check is not meaningful (`markerSurvived` false in run 1).
- The extra ENGINE_DISPOSED toast is intermittent (1 of 5 refusals per run so far); spec M2-3 says "no toast other than the
  expected one", so it would fail a counted run. Not diagnosed.
- Firefox, rounds > 1, M2-1's tool-closed case list, the M2-1 red case on v8, M2-1b (N ≥ 20), M2-4 (105 merges): not run.
- The product-path runner's `--candidate-profile` also repoints **dist's** page, so its "candidate" reports (v15 and v16 today)
  measured the v8-era page with the new engine, not the page `build_cutover_page.py` would ship, while saying the cutover
  "produces these exact bytes". `build_cutover_page.py` reads `web/` and would refuse on the sha mismatch, so this is not silent
  at the cutover, but it means no product-path run has measured B's page yet.
