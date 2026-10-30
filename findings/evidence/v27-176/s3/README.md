# S3: finding 046's cell on the user's path, generation 80 vs the generation-81 candidate (2026-10-30)

Spec `specs/SPEC-M3-v27-finding-176.md` 7.3 S3. Tool `wasm_sdk_probe/tools/check_v81_blank_line_bullet.py` and products `tools/v81_f_products.py` (commit `11a8f56cc`, before run-01). Local mirror, no DDEV.

**The procedure.** Every input is real (Chrome CDP `Input.*`, Firefox WebDriver actions):
1. Open `../fixture-two-plain/build-01/two-plain.odt` (`56bc01b0...`) through the page's file input.
2. Click past the end of the first line at (0.80, 0.0894) of `#paper`, PL-1's measured point.
3. Press Enter.
4. Click the toolbar bullet.
5. Type the marker `mks3q`.
6. Save with the product's own save, and read the saved ODT.
7. Press Ctrl+Z twice, save again, and read that.

**Products** (identity file by file, both `ok`):
- before = generation 80: the page from git `7745a26e9` (`3b6c023e`), profile v26 = the v26 archive.
- after = `dist/` as served: the generation-81 candidate (page `b63d8ee5`, profile v27 = the v27 archive).
- Every other generation-80 module is served with 80's sha256.

## run-01 (both browsers, N=3): **S3_HOLDS** (`run-01/report.json`, exit 0)

| | Chrome | Firefox |
| --- | --- | --- |
| after: every clause | 3/3 PASS | 3/3 PASS |
| before: red for 176 | 3/3 | 3/3 |

**after.** Each run:
- pill `ready`; `#toast` empty; no `[review]` console line since the press;
- strip `• 項目符號 N ms` (47-50 ms in Chrome, 28-35 ms in Firefox);
- the bullet's reply: `ok`, `completion: "verified-format-readback"`, `formatBarrier.route: "collapsed"`, `readbackBlockCount: 2`. This is spec 4.1 item 3, "visibly judged from a two-paragraph readback", end to end;
- the first save: `Plain first` / the marker in a bullet list (`list-level-style-bullet`) / `E1-EMPTY-AFTER`, both neighbours plain paragraphs outside any list;
- both Ctrl+Z replies `ok`;
- the second save: `Plain first` / an empty paragraph in no list / `E1-EMPTY-AFTER`.

`formatBarrier.undo` is recorded, not judged: `{read: true, changed: true, actionsBefore: 1, actionsAfter: 2}` in all six runs.

**before.** Each run:
- the reply is 046's shape (`ok: false`, `failureShape: multi-block-readback`, two blocks);
- the toast says 「…不只一個段落…」 and the strip `• 項目符號 失敗`;
- the saved marker is in the bullet list anyway (the list was applied, only not verified).

`self-test-01.json`: **ALL_RED, 19/19.** It applies:
- each of the 12 after clauses' mutations to an after run;
- each of the 4 before clauses' mutations to a before run;
- one run missing, one identity failed, one run fatal.

## Mutations (spec 7.3, fable ruling 3 Q6.5, review item 4): each **S3_MUTATION_CAUGHT**, both browsers, N=1

| Mutation | Product | Runs | Clauses red (both browsers) |
| --- | --- | --- | --- |
| `press-list-none` | after, pressing 移除清單 | 2/2 FAIL | `A.saved-marker-in-bullet-list`, `A.strip` |
| `hide-review-toast` | the before page, review toast hidden | 2/2 FAIL | `A.reply-ok`, `A.completion`, `A.no-review-line`, `A.strip` |
| `cosmetic-review` | the before page, no toast, no `[review]` line, strip `N ms` | 2/2 FAIL | **only** `A.reply-ok`, `A.completion` |

`cosmetic-review` is what review item 4 predicted. On the page and in the saved ODT it is indistinguishable from v27: the strip says `• 項目符號 89 ms`, the toast is empty, and the marker is in a list. Only the worker reply row is red. Ruling 3 Q6.5's "because the ODT is read" would not have caught it.

## Named

- The S3 shakedown (Chrome only, 1 run each, scratch) gave the same shape and its self-test 19/19 red. It is not evidence.
- `press-list-none` on v27 verifies: the empty line is already in no list, and `.uno:RemoveBullets` is a setter (finding 030). It is red here only because the save has no list and the strip names 移除清單, which is what the mutation is for.
