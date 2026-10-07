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

## Run 3 (2026-10-07 18:02-18:07 +08:00): the reworked runner, tool-generated list

`shakedown-chrome-3.json`, kept documents in `shakedown-chrome-3.docs/` (the owner's document's saves are in
`wasm_sdk_probe/build/merge-wasm-private/shakedown-chrome-3.docs/`, not in the repository). Runner at `8ef4c5f8`
(report `runner` `c2c94578075ed50b`), after spec section 22 and the review's fixes; page `b003534c...` (the two repaint fixes,
`c50c7789`); `caseList: tool` (spec 22.1: 37 cases from `merge-native/r0c/eshape.json`) plus `--frame-cell` (F01, F02).
Chrome, one round. Not counted.

| group | cases | result |
|---|---|---|
| M2-1, boundaries + indent | 20 | 20 pass, every clause: `verified-key-undo`, native undo comment, `restorePresses` 0, generation unchanged, paragraph text after the key and after the typed `Z` = native, no toast |
| barrier | G01 | pass (`verified-selection-delete`) |
| M2-3 | C15 C16 C17 C29 C30 | 5 pass: stage and `keyPosted` as R0c decided; generation +1; the toast window closed on the reopen's own last sentence; exactly the two reopen sentences; text = original + marker, marker once; checkpoint revision = the revision before the key. C15/C16 (`keyPosted:true`): no 「沒有被改動」 |
| frame cell (spec 22.2) | F01 F02 | refused `anchor-mismatch`, `keyPosted:false`; marker (now typed at the other frame case's caret) survived the reopen |
| M2-1, the owner's document | 11 | **all `placement-mismatch`**: see below |

No 「重繪失敗」 toast in any case (run 2 had one ENGINE_DISPOSED toast; the fix is `c50c7789`). The bytes clause
(`afterKeyBytes`) was still NE when this run started; computed offline afterwards with the spec 24 reduction from the kept
documents: 19 of 21 merge/barrier documents are byte-equal to Writer's own key arm after the reduction. The two that are not are
Y01 and Y02, where the page typed `x` before the key: natively the `x` carries an rsid span, on WASM the paragraph gets an
automatic style with `style:writing-mode="lr-tb"`. Spec 12 already says comparisons with typed text use paragraph text (equal for
both); the runner now leaves `afterKeyBytes` NE for `typed-merge`.

**The owner's document cannot be placed by native coordinates.** The engine's caret after the click and End/Home never equals
the native one, because the two layouts differ: line heights natively / on WASM, in twips: 521/414 (E02), 521/276 (E05), 348/276
(E01, E12, P27, E13, E15, P62, P63), 348/230 (E10); T01's native caret is at y 275530 while the whole document is 257114 tall on
WASM. The synthetic fixtures place exactly (Latin text, same fonts on both sides). This is an instrument limit, not a merge result:
no key was pressed in these 11 cases. It is also the first measurement of the handoff's open item ("Taiwanese document font names
already get a Latin line height on v8"): on this document WASM lines are about 0.79 of the native height. Cause not diagnosed.

M2-0 (spec 24): all four inputs differ from native by bytes and are equal by paragraph text; the diff and the reduction are in the spec.
