# Tree fixes per fable ruling 1 (v21): fix 2, fix 1, item 2's entry off — red first

- **Ruling:** `../shakedown/review/ruling-fable-1.md` (Q1 conditions 1 and 2's test part; Q2 conditions 1–3; Q4 condition 1).
- **Spec:** `specs/SPEC-M3-link-batch-v21.md` §12.3, committed at `e25ccc15` before any of this.
- **Measurements behind the fixes:** `../shakedown/diag-dirty-move/README.md`: V6e, V9 (fix1), V10 (fix2).
- **Scope:** node tests and source only. No browser, no build, no `make`, no `--write`, no ddev.

Labels: **[observed]** = read from an output in this folder; **[source]** = read from the code; **[inferred]** = reasoning.

## Files

| file | what |
|---|---|
| `fix2-red-before.txt` | the new `page-move-during-delete.test.mjs` on the page before fix 2: 5 red, 5 green |
| `fix2-green-after.txt` | the same file plus the six page tests around it, after fix 2: 80/80 |
| `fix1-red-before.txt` | the rewritten and the new session test on the session before fix 1: 2 red of 81 |
| `fix1-old-test-red-on-fix.txt` | the session test as at HEAD, run on the session with fix 1: "all eight bank it" red |
| `fix1-green-after.txt` | session test and `closed-lists` (D13) after fix 1: 93/93 |
| `mutation-witness-exit.txt` | `apply_mutation` for `boundary-move-takes-no-checkpoint` on the fixed tree, before the update: the runner's own exit |
| `mutation-applies-after.txt` | the same call after the `find` update: one hit, and the diff of the mirrored file |
| `mutation_witness.py` | the script for those two (it calls the runner's `apply_mutation` into a scratch directory) |
| `mutation-census.txt`, `mutation_census.py` | the hit count of all 44 page, markup and v2-session mutations, before and after |
| `fix3-red-before.txt` | the new and rewritten Markdown-entry tests on the page before the switch: 3 red of 23 |
| `fix3-green-after.txt` | the same after: 23/23 |
| `node-suite-final.txt` | `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs`: 596/596 |
| `e1c-intact.txt` | `check_e1_c_bundle_intact.py`: `intact: true` |
| `unittest-v21.txt` | `unittest discover -p 'test_v21_*.py'`: 88 run, 1 failure (below) |
| `cutover-page-print.txt` | `build_cutover_page.py --profile e2-editor-v21`, no `--write` |

## Identities

| file | before (HEAD `193143b8`, unchanged since `e25ccc15`) | after |
|---|---|---|
| `web/e2-editor-app.js` | `bd15e7efbc66d4cc…` | `59553850b3383e4fe6e48bbb8eaf82c5aeebe380bde4e8d9e9e35430b3176a1c` |
| `web/e2-editor.html` | `1d15814949c633ce…` | unchanged |
| `editor-shell-v2/narrow-editor-v2-session.js` | `443e0f1e7c85f359…` | `f1509ff22e6e2d8d945cfd803d293fd4cf102cece27618f54825571a2e1ef3a8` |
| served page, `build_cutover_page.py --profile e2-editor-v21` | `3d5112161b23b060…` | `605cf24b3dff5a2de1d219ee59e79adc92048e46436d098b7c7a3d837761fa0f` |
| shell digest of a shakedown mirror (`v21_shakedown_common.build_mirror`) | `e0252c0b22d37a20…` | `e35923a08107662d600d874f6986ef31aa8e8583955386929c26ebec62d82b06` |

- [observed] HEAD's page, repointed with the shakedown's own function, gives the pinned `3d5112161b23b060…`. The fixed tree gives `605cf24b…`. That matches `cutover-page-print.txt`.

## Fix 2 (finding 150): one predicate, rule A

- **Change** [source]: `clicksBeforeMove(shape, gestures, pointMovesInFlight, deletesInFlight)` in `web/e2-editor-app.js`.
  - It returns false while `deletesInFlight > 0` (finding 131's rule A). Otherwise it makes the old decision.
  - The arrows' keydown path and `sendDocumentMove` both call it. Neither keeps its own copy of the decision.
- **Test** [source]: `editor-shell-v2/tests/page-move-during-delete.test.mjs`.
  - It slices the page's keydown listener, `takeDocumentKey`, `sendDocumentMove`, `moveFromPoint` and the delete path.
  - It runs them on the real `NarrowEditorV2Session` over a fake engine. While a delete is out, that engine announces the barrier's one-character selection as `editor-state`.
- **Red, before** [observed]: 5 red, 5 green.
  - Red: the predicate test (it is absent), the barrier case for the arrow and for Ctrl+End, D8 (e) and V6e.
  - D8 (e) on the old page sent `delete-backward, delete-backward, place-caret, delete-forward, move-document-end`. The text became `ABCFGIJ` where key order gives `ABCFGHIJ`. That is the measured shape: the click goes before the Delete, and the Delete runs at the click.
  - Green, as controls: a real range still clicks first, for the arrow and for Ctrl+End; a caret goes straight out; and the range control (drag, ArrowRight, Delete).
- **Green, after** [observed]: 10/10.
  - The six page tests around it pass too, 80/80 together: `page-document-keys`, `-generated`, `page-held-after-move`, `page-held-deletes`, `page-held-depth`, `page-delete-and-sink`.
  - `page-document-keys(-generated)` now also slice the predicate, and declare `deletesInFlight = 0`. Without that, their copy of `sendDocumentMove` cannot compile.

## Fix 1 (finding 151): the six arrows keep the checkpoint, 22/23 do not

- **Change** [source]:
  - `BOUNDARY_CAPABLE_MOVES` stays eight, and D13's `closed-lists` is green.
  - A second set, `CHECKPOINTED_MOVES`, holds the six arrow, Home and End moves. In `action()`, only that set calls `_checkpointBeforeBoundaryMove`.
  - The comment gives three reasons: D7's ≤251 ms readbacks; V1/V2/V4 18/18 at the old caret, and 18/18 correct with the fix; the arrows stay only because `a-boundary-arrow-press-does-not-cost-the-work` pins them.
- **Tests** [source]:
  - "finding 096: all eight key-path moves bank it" is rewritten as "finding 096 / 151: the six arrow moves bank it, the two document moves and everything else do not".
  - Before, it checked 4 hand-picked others. It now checks all 14 non-move actions, generated from `EDITOR_V4_ACTIONS`.
  - New: "finding 151: a DIRTY document's Ctrl+Home/End sends no save, stays dirty, and banks no checkpoint". It covers both document moves.
- **Red, before** [observed]: 2 of 81 red on the old session (`move-document-start banked a checkpoint`, `… sent a save`).
- **The old test on the new session** [observed]: "all eight … bank it" is red: `move-document-start banked nothing`.
- **Green, after** [observed]: 93/93 (session test + `closed-lists`).

## The counted mutation (ruling Q2 condition 3, §34.4)

- **Witness** [observed, `mutation-witness-exit.txt`]: on the fixed tree, with the entry as it was, the runner's `apply_mutation` found 0 hits. It exited with its own message: "The tree moved under the mutation; fix the pattern rather than the count." No browser and no runner run were used.
- **Update** [source]: only the `find` changed, from `if (BOUNDARY_CAPABLE_MOVES.has(action))` to `if (CHECKPOINTED_MOVES.has(action))`.
  - The `replace` (empty), `check`, `reintroduces` and `alsoRed` are unchanged. Nothing else in `tools/run_e2_c_product_path.py` changed.
- **Applies** [observed, `mutation-applies-after.txt`]: one hit.
  - The mirrored session file is real, not a symlink.
  - It differs from the tree by exactly the two checkpoint lines in `action()`, so the mutation still removes the arrows' checkpoint.
  - [source] The check drives ArrowUp, which is still in `CHECKPOINTED_MOVES`. Whether it goes red is for the next counted run; this round did not run it.
- **Census** [observed, `mutation-census.txt`]: all 44 mutations on the page, the markup and the v2 session hit exactly once, before and after.
- **Tally for the handoff:** modified because of execution 1, because of review 0.

## Item 2's entry off (finding 153)

- **Change** [source]: `const PASTE_MARKDOWN_ENTRY_SHIPS = false;` near the top of the page, with a comment naming finding 153 and §12.3 (e).
  - It gates `updatePasteMarkdownAffordance`. The button stays hidden, but the session is still asked every time: `tools/v21_page_hook.py` captures the page's session through that call.
  - It also gates `openMarkdownDialog` and `insertMarkdownFromDialog`.
  - The dialog code and the markup are kept, and the toolbar's route to `openMarkdownDialog` is unchanged. While the switch is off, that function returns before `showModal`.
  - No SDK change. The HTML is unchanged: its comment 「只有 profile 宣告了 pasteMarkdown 才顯示」 still holds as an "only if".
- **Tests** [source], in `page-markdown-dialog.test.mjs`:
  - New: "§12.3 (e): the v21 profile offers the paste, and the shell shows no entry and no route to the dialog".
    - It uses the real v21 manifest, and the client still offers the paste (`offersPasteMarkdown() === true`).
    - The button is hidden, and the session was still asked.
    - Neither `openMarkdownDialog()` nor the page's own toolbar click handler on `paste-markdown` opens the dialog. Nothing is pasted or enqueued.
  - The M8 matrix that asserted "declared → shown" now reads hidden for every profile, the real v21 manifest included. The same matrix with the switch on keeps the old reading (shown exactly when declared): that is the kept code, as the next batch will turn it on.
  - The tests that drive the dialog itself turn the switch on, and the file says so: M11 ×2, 9.14, 插入, the refusal sentences, and post-dispatch.
  - "No session is no entry" checks both switch values.
- **Red, before** [observed]: 3 of 23 red: the new test, "M8 declared" and "M8 real v21". On the old page the entry is shown.
- **Green, after** [observed]: 23/23.

## Final checks

- [observed] Node: **596/596** pass, 0 fail, on the first run. The `place-caret-second-pass` flake did not occur.
- [observed] E1-C: `intact: true`.
- [observed] `test_v21_*.py`: 88 run, **1 failure**, `test_v21_shakedown_common.MirrorTest.test_the_real_mirror_reproduces_the_round_identity`.
  - `pageServed` and `shellDigest` are false; the four profile files are true.
  - [inferred] That test pins the shakedown round's identity, which is the pre-fix page `3d5112…` and shell `e0252c0b…`. The fixed tree changes both by design. The new values are in the identities table.
  - The pin lives in `tools/v21_shakedown_common.py`, which this change may not touch. Re-pinning belongs to the step that builds and records the candidate page (ruling, overall step 5).

## Not done, and what this moves for other tools

- **Not run here:** the ruling's evidence runs. These are Q1 conditions 2 and 3 (D8 (a)–(e), and V6e as a record arm, N=3 in both browsers), Q2's D14 and D11, and Q4 conditions 2 and 4 (M7, the `open` cell).
- [source] **The diag tool's candidate patches no longer apply.** `tools/diag_v21_dirty_move.py` patches fix1, fix2 and fix3 by exact text, and that text is gone from the tree. Its V5/V11 arms cannot open the dialog on this page, because the entry is off.
- [source] **The shakedown identity pin** described above.
