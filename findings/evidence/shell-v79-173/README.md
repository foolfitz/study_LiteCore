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

## Generation 79 (`freeze-79/`)

See `freeze-79/README.md`: 79 differs from 78 in exactly the two declared files; Makefile bundle line red before / green after / red on v78 and on the tool default; E1-C intact.

## F3-79 (`f3/`), spec 5.4

`tools/run_v79_f3.py`, Chrome and Firefox, 1 run each (2026-10-29 ~23:06-23:26 +0800), runner bound to generation 79 (`run-01/*/shell-manifest-override.json`: default v76, used v79, the runner took it). The runner exits 1 as v25's did (the suite has known non-PASS cells); the verdict is the readers':

- **Reading 1** (`read-01.json`, `tools/read_v25_f3.py` unchanged, spec v25 16 / 16.1 against v24 T4 run-02): **`F3_HOLDS`**, no problems; P 4 + 2 PASS; the recovery sentinel NE with its pairing held. The `improved` list is the same moves v25 run-02 had against v24.
- **Reading 2** (`equal-01.json`, `tools/read_v79_f3_equal.py` against v25 F3 run-02): **`F3_79_EQUAL`**, 46/46 cells equal in Chrome and 46/46 in Firefox; nothing moved.

## F4-79 (`f4/`), spec 5.4

`tools/run_v79_four_arms.py`, Chrome 9.7 min and Firefox 9.9 min, preflight READY on generation 79; `aggregate-judge.json` (`tools/judge_v79_product_four_arms.py`, absolute run dirs): **all four arms PASS, 24 rows, no problems**. Preflight reds (`preflight-red-v78`, `preflight-red-no-override`): exit 1, each naming `editor-shell-v2/paragraph-editor-client.js` as not the reported generation.

## V0′ and E1-C (`v0/`), spec 5.5

`v0/run_v0_prime.py` (restores, re-reads, puts back in `finally`): **`V0_PRIME_HOLDS`** (`v0-prime.json`).

- Stage v24 (page `b15a6d8e` + client `4616ae17` = generation 77, source and dist/): `read_v24_remaining_cohort.py` exit 0, byte-identical to `link-batch-v24/remaining-counted-01/completion-read-01.json` (85 s); `judge_v24_product_four_arms.py` (the receipt's absolute argv, `-I`) exit 0, byte-identical to `link-batch-v24/four-arms-counted-01/aggregate-judge.json`.
- Stage v25 (page `6e66c930` + the same client = generation 78): `judge_v25_product_four_arms.py` exit 0, byte-identical to `link-batch-v25/f4/aggregate-judge.json`.
- Put back (`git checkout HEAD --` both files, `make e2-c-assets`): source and dist/ `9cb6ea1f…` / `7d1c1eb2…`; v79 bundle line exit 0; E1-C `intact: true`, bundle `187706b2dcb07d2b` (`e1-c-after-put-back.json`).
- Control (`live-red-*`): on the live generation-79 tree both four-arm readers are NOT_ESTABLISHED in all 24 rows, by construction -- v24's "shell digest differs: d07397e7…", v25's "digest is not generation 78: d07397e7…". The restore is what makes them readable.

## Section 34.4 (this round)

Fixed by execution **0**. Fixed by review **0**. (B1's first launch never started: its stderr was redirected into a directory that did not exist yet; a shell slip, not a tool or check change.)
