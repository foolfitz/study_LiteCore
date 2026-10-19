# v22 shell edits (SPEC-M3-link-batch-v22 §11.1, §11.7 step 2; fable ruling 5)

The three tree edits, made after the criteria were appended (`8917626d`):

- `web/e2-editor-app.js`: `PASTE_MARKDOWN_ENTRY_SHIPS = true` (item 2's entry; the comment rewritten for v22).
- `closeMarkdownDialog`: `if (session) { el.sink.blur(); el.sink.focus({ preventScroll: true }); }` (finding 152, fix 3).
- `web/e2-editor.html`: `#markdown-dialog:not([open]) { display: none; }` in the dialog's style block (finding 154, the page's half).

**One commit, not three.** Ruling 5 §4 step 2 asks for one commit each. The three edits share one test file, `editor-shell-v2/tests/page-markdown-dialog.test.mjs`. So they are committed together, and their red cases are in one red run.

## Red first

`page-markdown-dialog-red-before-edits.txt`: the rewritten test file run against the page and HTML **before** the edits. 21 pass, **7 fail**, and they are exactly the expected seven:

- the v22 §11.2 (b) test ("the shipped shell shows the entry and routes it to the dialog");
- three "as shipped" M8 cells where the profile declares the paste (declared, real v21, real v22). The three non-declaring cells already pass, because the old switch hid the entry everywhere;
- the two finding 152 fix 3 cells (取消, 插入): the sink is only focused, not blurred first;
- the finding 154 HTML rule.

After the edits: 28/28. All node tests (`editor-shell-v2/tests/*.test.mjs`, `sdk/tests/*.test.mjs`): 601/601. E1-C `intact: true`.

## The static target

`test-e2-c-static-after-edits.txt`: `make -k test-e2-c-static` exits 2 at **one expected red**, `test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree`:
- "dist copy differs from source: web/e2-editor-app.js";
- the v74 bundle is out of date for `web/e2-editor-app.js`.

That is the v75 freeze not yet made (spec §11.7 step 7), the same red v21 had before v74. The HTML is not in the shell bundle.

`test-e2-c-static-rest.txt`: every command of the target after that line, run by the main session from `make -n` (`bash -e -x`). All 40 exit 0. That includes the M1-1 line, the relink queue and `check_gesture_offers.py`.

## The page the evidence runs measure

`page-served-v22.txt`: `tools/build_cutover_page.py --profile e2-editor-v22` (no `--write`).
- **pageServed = `3b96cb1661aba6de6add989c98c80ab393cd394307763bc6dc28c9440fba82e2`**;
- pin `db3408f55316bf67` → `f7a40bcce073d913`.

`tree-shell-sha256.txt`: the tree page and HTML after the edits.
