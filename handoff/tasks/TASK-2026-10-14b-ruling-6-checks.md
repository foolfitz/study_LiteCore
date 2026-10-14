# Task 2026-10-14b: ruling 6's three check items (conditions 50′, 49, 51), before the v20 link

**Ruling:** `findings/evidence/link-batch/review/ruling-6.md`: §Q5, conditions 49, 50, 51, 53, **and Amendment 1 at the end, which replaces 50.4 and 50.5 and corrects 51 and 53**. Read all of it first. Where this file and the ruling disagree, the ruling (as amended) wins.

The witness already exists: `findings/evidence/link-batch/v20-part3/m1-1-witness/` (`f4c1e7ac`). It holds the unchanged M1-1 tool's red run on the tree with the v20 Makefile block applied (`d7d62039`). Read its README.

All paths below are relative to `wasm_sdk_probe/`, and every command runs from there.

## Hard limits

- **No `make` that builds anything.** Only `make -n` dry runs, which the tools already do internally. No link, no `ALLOW_FROZEN_RELINK`. Do not touch `dist/`, any profile, `src/`, `sdk/` or `web/`, and do not touch `editor-shell*/`, because another executor is working there.
- The only Makefile edit allowed is the comment line in condition 53 as amended. It goes in the same commit as the M1-1 extension. Change nothing else in the Makefile.
- Another session commits in this same tree. Stage and commit **only your own paths** (`git commit -- <paths>`). Never use `git add -A` or `git add .`.
- §34 applies, and these are the only tool changes allowed:
  - M1-1: the repair the ruling describes;
  - X1: the new-use flags the ruling describes;
  - `what_the_link_ships.py`: one data entry.
- If a red case does not go red, or a green run does not go green, **stop and report** with the output. Do not adjust the tool or the case to make it pass.

## Work, in this order

1. **M1-1, `tools/check_merge_key_undo_scope.py`** (conditions 50.3, 50.4′, 50.5′, 50.6, 53′).
   - Extend `--carrier RULE[=obj,…]`. The default object set is `probe_engine`, and the default carriers stay E2_V15 and E2_V19.
   - For each carrier, every declared object must differ from BASE. Every undeclared object of that carrier, and of every other rule, must be equal. The compile guards (with `OXSDK_MAINLOOP_ENGINE` added, and without `OXSDK_FINDING_016_SELECTION_BARRIER`) run on every carrier's `probe_engine`.
   - Green runs, with outputs committed under `findings/evidence/link-batch/v20-part3/m1-1/`:
     - `--base 5d77dc84 --carrier E2_V15 --carrier E2_V19 --carrier E2_V20=probe_engine,sdk_api,editor_api`
     - `--base 82af92ca^ --carrier E2_V20=probe_engine,sdk_api,editor_api`
   - Five red cases, committed alongside, each with its exit code and the failing line:
     - `E2_V20=probe_engine`
     - `E2_V20=probe_engine,sdk_api`
     - `E2_V20=probe_engine,sdk_api,editor_api,unoembind_stub` (declared but did not move)
     - `--inject E2_V19=-DOXSDK_E2_V20_LINK_BATCH`
     - the `82af92ca^` run with `--carrier E2_V19` added
   - Before changing the tool, confirm the default invocation still prints what the witness printed, with the same exit and the same five objects. After the change, the default invocation (no `=objs`) must behave exactly as before on v19-shaped input.
   - Extend `tests/test_merge_key_undo_scope.py` with the rows from the green runs and the red cases. It must pass.
   - In the **same commit**, replace the Makefile comment sentence with Amendment 1's text, which names `probe_engine.o`, `sdk_api.o` and `editor_api.o` (declarations only, `v20-part3/m1-1-witness/editor_api-define-diff.txt`).
2. **X1, `tools/check_profile_identity.py`** (condition 49).
   - Add repeatable flags: `--declared-worker SHA`, `--declared-new-leaf PATH=VALUE` and `--declared-export SYMBOL`. They follow 49 (a)–(c) exactly. A declared delta that did not move must FAIL.
   - With no flags the behaviour must be byte-identical. Prove it: re-run the exact v19 invocation recorded in `findings/evidence/v19/post-link/` against its committed inputs (the v19 dist profile, the v18 reference, the two export lists named there), and diff the output against `findings/evidence/v19/post-link/x1-check-profile-identity.txt`. The diff must be empty. Commit the diff.
   - Extend `tests/test_profile_identity.py` with a synthetic v20 green case and the seven red cases listed in 49 (d). It must pass.
   - Write the v20 invocation, with its three deltas, into a short README under `findings/evidence/link-batch/v20-part3/x1/`. It cannot run yet, because v20 is not linked. The deltas are:
     - worker `478d0da1dbfcf93615a00025c3c2f9b72c3cfa486d04746f03dea5fcf757b099`;
     - leaf `.editorContract.pageRectangles=document-sdk-page-rectangles`; check the exact leaf path syntax the tool uses;
     - export `_oxsdk_document_page_rectangles`.
3. **`tools/what_the_link_ships.py`** (condition 51 as amended).
   - Add a `link-batch-v20` entry in `VARIANTS`, as data only.
   - Run `python3 tools/what_the_link_ships.py --since c0337ae3 --variant link-batch-v20 --shipped-profile dist/profiles/e2-editor-v19` and commit its output under `findings/evidence/link-batch/v20-part3/what-the-link-ships/`.
   - Write a README there. It must state whether the output matches 51's expectation, and it must name the limit from Amendment 1 (2): the tool reads only each `.cpp` at `--since` under the tree's headers, so `editor_api` reads identical even though M1-1 shows a declaration-only difference. If any other unit changed, stop: that stops the link.

## Done means

- Every run's stdout, stderr and exit code is committed, with a README in each evidence directory (English).
- `python3 -m unittest tests.test_merge_key_undo_scope tests.test_profile_identity` passes.
- Commits carry your model's `Co-Authored-By` trailer.
- Report a `## SUMMARY` of at most 30 lines covering:
  - the commits;
  - the green runs and their exit codes;
  - each red case's exit code;
  - X1's default-identity diff (empty or not);
  - the `what_the_link_ships` verdict;
  - anything you stopped on.
