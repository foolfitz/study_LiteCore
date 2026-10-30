# S4: finding 083's path on a multi-paragraph last line, the user's path, generation 81 vs the generation-82 candidate (2026-10-30)

Spec `specs/SPEC-M3-v28-last-line-fallback.md` 7.3 S4. Procedure pinned by append 1 (14), committed with the tool before any run. Tool `wasm_sdk_probe/tools/check_v82_last_line_bullet.py`, products `tools/v82_f_products.py` (`61633e7df`). Local mirror, no DDEV. Run by `run.sh` (21:26-22:19 +0800).

**Products** (identity file by file, both `ok`):
- before = generation 81: page `b63d8ee5` and client `7d1c1eb2` from git `a9a04dc64`, profile v27 = the v27 archive.
- after = `dist/` as served: page `3b0a2ebb`, client `d07a58e0` (both equal to the tree and different from 81's), profile v28 = the v28 archive (`13f674e4`).
- Every other generation-81 module is served with 81's sha256.

## run-01 (both browsers, N=3): **S4_HOLDS** (`run-01/report.json`, exit 0)

| cell | fixture, procedure | after (every clause) | before |
|---|---|---|---|
| a | two-plain, click below, Enter, bullet, type, save; Ctrl+Z x2, save | 6/6 PASS | 6/6 red for 083 |
| e | two-plain, Enter x2, bullet, type, save | 6/6 PASS | recorded (083) |
| b-number | two-plain, Enter, 1. 編號, save; Ctrl+Z, save | 6/6 PASS | 6/6 red for 083 |
| b-heading | two-plain, Enter, 標題, save; Ctrl+Z, save | 6/6 PASS | 6/6 red for 083 |
| b-none | bulleted-last, 移除清單, save; Ctrl+Z, save | 6/6 PASS | 6/6 red for 083 |
| b-body | realheading-last, 內文, save; Ctrl+Z, save | 6/6 PASS | 6/6 red for 083 |
| d | table-then-empty-last, bullet, type, save; 「↶ 復原」 x2, save | 6/6 PASS | recorded (083) |
| c | the blank document, B1's procedure, arms noclick and click | 12/12 PASS | 12/12 PASS |

**after, the verified cells (a, e, b-\*).** Every run:
- pill `ready`, `#toast` empty, no `[review]` line, strip `<label> N ms` (25-52 ms);
- the reply: `ok`, `completion: "verified-format-readback"`, route `collapsed`, and the fallback ran: `blockCount 2`, `restoreConfirmed true`;
- the fallback's last block: a/e `ul`/`p`, number `ol`/`p`, none `""`/`p`, heading `""`/`h1`, body `""`/`p` (the real Heading 1 became `p`);
- the save: the target state on the last paragraph (a/e the marker in a bullet list, number in a number list, none out of any list, heading `text:h` `Heading_20_1`, body `text:p` `Text_20_body`), every paragraph before it unchanged; in e the empty paragraph before the marker is NOT in the list;
- a: after two Ctrl+Z, three paragraphs, the last empty and in no list (S3's strength); b-\*: after one Ctrl+Z the last paragraph is back in the fixture's state.

Typing after the press landed in the dispatch paragraph (a, e, d): the selection mode was cleared on the user's path (spec 4.1 item 6).

**after, d (a table before the last line).** Every run:
- `failureShape: "fallback-readback-refused"`, `fallback.refusal: "unknown-structural-tag"`, `restoreConfirmed: true`, dispatched, collapsed;
- the toast is the new sentence: 「• 項目符號：動作已送出，但這一段後面沒有可以一起選的段落，檢查改成往前多選一格，碰到了表格或其他讀不了的內容，所以無法核對。請看一下結果，不是你要的就按「復原」。這是檢查的極限，不是文件壞了」; no 「回到檢查點」, no checkpoint notice; strip `• 項目符號：待確認`; `[review] • 項目符號: MUTATION_OUTCOME_UNKNOWN: the fallback selection's readback …` on the console;
- the typed marker is in the last paragraph, `Cell text` unchanged in its table cell (no selection the user did not make was left behind); after two 「↶ 復原」 the last paragraph is empty and in no list.

**before (generation 81, v27).** Every a/b-\* run is 083's: `select-text-returned-none`, 083's sentence, no `fallback` in the reply. d and e are the same (recorded, not judged).

**c (the blank document).** Both products: S2′'s judge PASS (083's path, 083's sentence, strip 「：待確認」 at the press and after typing, the marker in a list). after: `fallback {ran: true, selectionType: 0, blockCount 0, restoreConfirmed true}`; before: no `fallback`. The user-visible tuple (pill, toast, both strips, notice) is one value across all 24 runs.

`self-test-01.json`: **ALL_RED**, 130 mutations (every clause of every cell, the blank cell's five, a missing run, an identity failure, a fatal run).

## Mutations (each must make every run FAIL, red on its own clause)

| mutation | report | result |
|---|---|---|
| press-list-none | `mutation-press-list-none/` | **S4_MUTATION_MISSED**: 5/6 FAIL, Chrome 3 NE (`page not ready`: the page did not reach `ready` within 240 s, before any input) |
| press-list-none, re-run | `mutation-press-list-none-run-02/` | **S4_MUTATION_CAUGHT** 6/6, red on `saved-target-state` (and strip, fallback-last-ul) |
| cosmetic-review | `mutation-cosmetic-review/` | **CAUGHT** 6/6: the page clauses hold (no toast, no `[review]`, `N ms`), red only on the worker reply row (reply-ok, completion, fallback-\*) |
| wrong-button-b-number / b-none / b-heading / b-body | `mutation-wrong-button-*/` | **CAUGHT** 6/6 each, red on `saved-target-state` (and strip) |

The first press-list-none report is kept as it is. Its NE is not a held mutation (no run PASSed), but the rule is "every run FAIL", so it does not count; the re-run is the count. One `page not ready` in 150 page loads today (144 in `run.sh`, 6 in run-02).
