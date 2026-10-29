# Finding 173 page fix: evidence for shell generation 79 (SPEC-M3-shell-v79-finding-173)

Spec `specs/SPEC-M3-shell-v79-finding-173.md` (pinned `a43a69bc6`, before any implementation or browser run).

## The change

- `editor-shell-v2/paragraph-editor-client.js` exports `EMPTY_SELECTION_SHAPES` = `["stage-deadline:awaiting-selection", "select-text-returned-none"]`; finding 083's disposition rule tests membership instead of equality with the first name. The rule's other three conditions (`dispatched === true`, `route === "collapsed"`, `selectionResultSeen === true`) and every other rule are unchanged.
- `web/e2-editor-app.js` imports that list and picks finding 083's review sentence from it (one list, so the sentence cannot drift from the disposition). The sentence itself is unchanged.
- Hashes (`assets-hashes.txt`): page `6e66c930…` -> **`9cb6ea1f…`**; client `4616ae17…` -> **`7d1c1eb2…`**. `make -n e2-c-assets` printed exactly the two expected `cp` lines (`make-n-e2-c-assets.txt`); after `make e2-c-assets` both `cmp` equal to the source.

## U1, U2 (`u1/`, `u2/`)

Both red first, on the unchanged code (`red-before.txt`, headers carry the hashes): U1's new test fails at its first assertion (`select-text-returned-none` -> `dispatched-rollback`); U2's first test fails with the "covered more than one paragraph" sentence. After the change: U1 15/15, U2 6/6, all `editor-shell-v2/tests/*.test.mjs` **524/524** (`u1/all-shell-tests-after.txt`). U2 carries its own mutation (only 083's name in the list -> the wrong sentence), so its first test is not vacuously green.

## B1 (`b1/`), tool `wasm_sdk_probe/tools/check_v79_blank_bullet.py`, products `tools/v79_f_products.py`

The owner's path: the host's own blank template (`en-US_zh-TW_A4.odt`, sha256 `7e6221b6…`) through the page's file input; a real mouse click on the toolbar bullet (CDP / WebDriver), then the marker typed with real keys without restoring focus, then the product's save; the saved ODT read from the Blob the page hands over.

- **`b1/pre-fix/`** (before the change, 1 repetition): `before` red for 173 in Chrome and Firefox, both arms (`select-text-returned-none`, dispatched, collapsed, `selectionResultSeen: true`; pill `recoverable-error`, notice shown). `after` refused by its identity on exactly `declaredDifferFromGeneration78: false`. Verdict `B1_RED` as designed. First measurement of 173 in Firefox: the same shape.
- **`b1/run-01/`** (after the change, 2026-10-29 ~22:56-23:20 +0800): **`B1_HOLDS`**. `before` 12/12 red for 173; `after` 12/12 PASS: the bullet reply is 173's shape, pill `ready`, notice hidden, the toast is finding 083's sentence; focus back on the sink; 9 real keys -> 9 `insertText` (`uno-insert-text`), all ok, revision 0 -> 9; the saved paragraph `mkbulletq` sits in `list-item` / `list`. Identities: `before` = generation 78 file by file; `after` = 78 except exactly the two declared files, which equal the tree (`9cb6ea1f…`, `7d1c1eb2…`).
- **`b1/run-01/self-test.json`**: `ALL_RED`, 8 mutations of the real report (toast sentence, notice shown, marker out of the list, a refused insert, another failure shape -> that run NE, a before run `ready`, a missing run, a failed identity).

Not a timing measurement (no desk gate). The engine's own record is not read here (spec section 6, L-no-engine-record-in-b1).
