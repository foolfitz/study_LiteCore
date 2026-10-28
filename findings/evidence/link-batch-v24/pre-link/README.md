# v24 pre-link evidence (2026-10-28)

Spec: `specs/SPEC-M3-link-batch-v24.md` (pinned `ceaa2770`; corrections in its section 14). Rulings: `findings/evidence/link-batch-v23/feature-protocol/s5-type-route-ruling/RULING.md` and `RULING-2-abi.md` (with its follow-up). No compile, link, browser, native run, DDEV or upstream action happened here. `uptime` load stayed below 0.6 with no `make` running.

## What was implemented in the tree

- Engine (`wasm_sdk_probe/src/`): `oxsdk_document_insert_typed_text` → `probe::insertTypedText` → `CommandType::InsertTypedText` → `handleInsertTypedText`, all under `#ifdef OXSDK_E2_V24_TYPED_INSERT`; `editor_api.h` keeps editor ABI 6 and refuses the define without the ABI6 feature. 137 inserted lines, 0 deleted (`git diff --stat`).
- Worker: `wasm_sdk_probe/sdk/v24-feature-worker.js`, the archived v23 worker plus six labelled hunks (`wasm_sdk_probe/tests/v24-worker-delta.json`).
- SDK: `wasm_sdk_probe/sdk/document-sdk.js` exports `INSERT_ROUTE_BY_SOURCE` and `TYPED_INSERT_DECLARATION`; `insertText` adds `route` only on a manifest declaring `typedInsert`.
- Identity tooling: `tools/check_v24_feature_contract.py`, `tools/build_e2_v24_feature_profile.py` (new files importing the v23 ones unchanged), the Makefile v24 block and `test-v24-feature-static`, the `link-batch-v24` data entry in `tools/what_the_link_ships.py`, the owner helper `tools/link_v24_feature_owner.sh` (syntax-checked with `bash -n` only).
- The page (`web/e2-editor-app.js`) is NOT changed yet: it pins v23, and the typedInsert requirement would refuse v23 (spec section 14).

## Criteria and their records

| Criterion | Record | Result |
| --- | --- | --- |
| T3 + U1 | `static-tests.txt` (`node --test tests/v24-typed-insert-sdk.test.mjs`) | 4/4 pass |
| T3 red (iv) | `t3-red/fake.*`: a scratch copy of `input/` with an added `source: "fake"` (`fake.diff`) | exit 1, names `'fake'` |
| T3 non-vacuity | `t3-red/empty.*`: an empty directory | exit 1, `read 0 adapter file(s)` |
| W1 | `static-tests.txt` (`tests/test_v24_feature_worker_delta.py`) | pass |
| W1 red | `w1-red/extra-route.*`: one route added to `INSERT_ROUTES` outside the list | exit 1 |
| W2, (d′), (viii), init presence | `static-tests.txt` (`node tests/v24_feature_worker_test.cjs`), with six causal controls (each guard removed must fail the exercise) | pass, 6/6 controls red |
| E1 | `static-tests.txt` (`tests/test_v24_typed_insert_engine.py`) | 4/4 pass |
| E1 red | `e1-red/a.*`: a line outside the v24 regions changed in `handleInsertText` (`a.diff`); `e1-red/b.*`: the NUL/LF/CR refusal moved after the dispatch (`b.diff`) | both exit 1, each naming its test |
| Identity reds in advance | `static-tests.txt` (`tests/test_v24_feature_profile.py`): `abiVersion: 7`, leaf absent or wrong, a gesture, `pasteMarkdown` dropped, profile name, a top-level leaf; the builder refuses to declare the typed route for the archived v23 binary (`missing=['_oxsdk_document_insert_typed_text']`) | pass |
| S3-v24 | `s3/make-n-B-v24.txt`, `s3/make-n-B-v23.txt`, `s3/word-diff.txt` | differences are exactly the five classes of the spec (below) |
| S3 log reader | `s3/dry-run.log` (`make -n ALLOW_FROZEN_RELINK=1 …e2-editor-v24…`) read by `check_v24_feature_contract.py --build-log` | `v24 preconditions hold` |
| V0′ | `v0/` | see below |
| Frozen set | `frozen-set-before.sha256`: every regular file under `wasm_sdk_probe/dist/profiles/` and `wasm_sdk_probe/build/archive/` (2,348 files, no symlinks) | recorded |

### S3-v24 method

Both dry runs use `make -n -B`: v23's build and profile directories exist, so without `-B` the v24 run alone prints the two `mkdir -p` lines. With `-B` both print them (two each). `editor-v24` is renamed to `editor-v23` in the v24 output before the word diff. The twelve differing lines fall into the spec's closed list: (1) `-DOXSDK_E2_V24_TYPED_INSERT` on each of the four compile lines; (2) the export recipe (copy of the v23 archive plus one `echo`); (3) the worker source and its base-worker preflight (path and sha256 of the archived v23 worker, in the preflight and in the manifest recipe); (4) the builder and contract-checker file names; (5) the guard's description text.

### V0′ (the spec's V0 as corrected in section 14)

- `v0/completion-read.*`: on the live tree `counted-r1-s5-01/read-completion.py` exits 1 with `final shell source/dist differs: sdk/document-sdk.js`. v23's `config()`/`identity()` (`wasm_sdk_probe/tools/v23_feature_selection_cases.py:484-500`) requires every generation-76 shell file in the live tree to equal its bound bytes, so any staged shell change makes this red by construction.
- `v0/completion-read-sdk-restored.*`: with only `sdk/document-sdk.js` restored to its generation-76 bytes (`9dcb8312…`, from `ceaa2770`), the same reader exits 0: `COMPLETE_R1_PASS` 144/144 and `STOPPED_S5_INCOMPLETE` 401 PASS + 1 FAIL, as recorded for v23. The v24 SDK was copied back afterwards and its sha256 (`afdff2d4…`) checked. So nothing else v23 binds was changed.
- `v0/native-run-03-reread.json`: `read_v23_native_s5_type.py` over native run-03 exits 0 and its output is identical to the committed `s5-native/reader-03.json`.
- `v0/e1-c.*`: `check_e1_c_bundle_intact.py` exits 0, `intact: true`.

## em++ checks (owner-authorized 2026-10-28, `em-checks/`)

The owner authorized these, and made it standing, after the rest of this directory was committed (`9b224a60`). Runner: `em-checks/run_em_checks.py`; every command's argv, exit code, duration and streams are in `em-checks/commands.json` and the per-step files. Each step first ran `uptime` and `pgrep -a make` (no make running; load below 0.6) and pinned itself to one core with `taskset -c 0`. Nothing emitted an object.

- **Syntax-only**: the four v24 compile lines of `s3/dry-run.log` with `-c` and `-o OBJ` removed and `-fsyntax-only` added: `sdk_api`, `probe_engine`, `unoembind_stub`, `editor_api` all exit 0. Positive control (`em-checks/syntax-control.json`): a scratch copy of `probe_engine.cpp` with an undeclared call inserted inside `handleInsertTypedText` fails with the v24 define (`use of undeclared identifier`) and passes without it, so the check does compile the v24 region.
- **M1-1** (`check_merge_key_undo_scope.py`, argv taken from `make -n test-e2-c-static`): with the carrier list as it was, exit 1 naming exactly `E2_V24` `sdk_api.o`, `probe_engine.o`, `editor_api.o` and no other rule (`m1-1-red-without-v24-carrier.*`); after adding `--carrier E2_V24=probe_engine,sdk_api,editor_api` to `test-e2-c-static`, exit 0 with 37 rules / 143 objects, and E2_V24's three guard variants (without `OXSDK_MAINLOOP_ENGINE`, `OXSDK_E2_V21_LINK_BATCH`, `OXSDK_FINDING_016_SELECTION_BARRIER`) each refused (`m1-1-green-with-v24-carrier.*`).
- **what_the_link_ships** `--since dcffd17d` (the tree v23 was linked from; `wasm_sdk_probe/src` has no difference between `dcffd17d` and `ceaa2770`) `--variant link-batch-v24 --shipped-profile dist/profiles/e2-editor-v23`: `ok: true`, `configurationDrift: []`, changed `sdk_api` (the new export) and `probe_engine` (the command kind, submit function, handler and dispatch case), identical `unoembind_stub` and `editor_api` (`ships.*`). Its `worker` field compares the tree's shared `sdk/sdk-worker.js` (the Calc worker) with v23's isolated worker and is not about v24, whose worker W1 binds.

## Not done here

- J-red (the v24 S5 judge's red cases) and every post-link criterion: no v24 judge or artifact exists yet.

## A test that was green for the wrong reason

The first E1 red cases exited 0. The script that added the `V24_E1_SRC` override to the test had failed its own assertion (the new line itself contained the pattern it checked), so the file was never written and the test kept reading the real `src/`. Found because both red cases stayed green; after the override was applied both turned red. No result had been recorded from the broken version.
