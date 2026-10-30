# v27 pre-link evidence (SPEC-M3-v27-finding-176 7.2), engine step

Engine edits, all under `OXSDK_E2_V27_FIRST_BLOCK` (spec 4.1 item 6's closed list):
- `src/editor_api.h`: the `#error` guard (v27 requires v25; the TU carrying it is `editor_api.cpp`);
- `src/probe_engine.cpp`: `FormatStateBarrier` undo fields; `appendFormatBarrierDetails` writes `undo` inside `formatBarrier`;
- `src/ordered_format.inc`:
  - the undo read before the post;
  - no restore before the select on the collapsed route;
  - the `multiBlock` refusal only off the collapsed route;
  - the undo read after the final restore.
- Every v27 block keeps v25's text verbatim under `#else`: `strip_v27(edited inc) == HEAD's inc`, byte for byte (checked when the tests ran).

## E1 / E2

- `e1-red-before-inc-edit.txt`: `tests/test_ordered_format_v27.py --witness`, run after the struct/serializer/guard edit and before the inc edit. Exit 1. (a), (b), (d) and every (f) clause FAIL; the guards that pass today, (c), pre-dispatch refusal and single-block, pass.
- `e1-e3-native-tests.txt`, after the inc edit:
  - `tests/test_ordered_format_v27.py` OK: the original is green; v25-behaviour (v27 blocks stripped, compiled WITH the v27 define) and three mutations (`collapsed-check-all-routes`, `g-on-range-single`, `undo-record-skipped`) are each red with FAIL lines.

## E3

The three inc-text tests that are in no Makefile target, run one by one (`PYTHONPATH=tests`): `test_ordered_format.py`, `test_ordered_format_scope.py` and `test_ordered_format_v25.py`, all OK.

The scope checker counts braces textually. A first form of the `multiBlock` edit split one `if (...) {` across `#ifdef`/`#else` and made it "unbalanced". It was rewritten so that each branch is a whole `if` block. That is fixed-by-execution 1.

Positive control for the scope rule, run when the tests ran: an undo read inserted into the reply is flagged.

## E4 (fable ruling 3 Q6.2)

`tests/test_format_readback_v27.py` (`e4-unittest.txt`: OK).

**How it runs.**
- It cuts the production `parseFormatReadback`, its three helpers and `formatBarrierReadbackSatisfied` out of `src/probe_engine.cpp`, and compiles them natively.
- It feeds them 18 rows' recorded `format.html`:
  - the F rows a1, a2, n2, n3 and r1-r6 (r2 has no readback);
  - their G twins, g-a1..g-n3 and g-r3..g-r5;
  - a6g and b1g.

**Ground truth.**
- Each row's predicate is judged against the saved document's dispatch paragraph (`read_cells.saved_target`).
- `e4-parser-on-recorded-markup.json` lists every row. All 18 agree, including the two shams that must be "not satisfied" (n2 and g-n2: the first tag is `p`, so `listTag` is "").
- Hand pins: n2, r6 (two items in one list), r5 (`h1`), and a1 (one block).

**Red cases.** One flipped expectation and one wrong pin are each reported.

## V0-v27

`v0_preprocess.py 9fbbb9b93`, derived from v25's tool: only VARIANTS gains `editor-v25`; the names change.

- Result: **V0_V27_HOLDS** (`v0-v27.json`). Every unit of `E2_C_SOURCES` (sdk_api, probe_engine, unoembind_stub, editor_api) under the v23, v24 and v25 compile lines preprocesses identically (`-E -P`, nonblank lines) to the parent of the engine commit. That parent's `wasm_sdk_probe/src` is identical to `9d7fb9e7c`, v25's link source.
- Positive control `--mutate` (`v0-v27-positive-control.json`): exactly the three `probe_engine` rows differ.
- 3.8 s, one core, load 0.05.

## S

`s_syntax.py`, derived from v25's tool.

- Result: **S_V27_HOLDS** (`s-v27.json`). Every unit is clean with `-DOXSDK_E2_V27_FIRST_BLOCK` on the v25 compile line.
- Control 1: a deliberate error inside a v27-only block of `ordered_format.inc` fails with the define and passes without it.
- Control 2: the v27 define without the v25 define, aimed at the TU that carries the guard (`editor_api.cpp`), hits `#error "the v27 first-block read requires the v25 format-proof engine"`.
- `taskset -c 0`, about 5 s in all.

## Worker step

`sdk/v27-first-block-worker.js` is the archived v26 worker (`95d6e7ae...`) plus `tests/v27-worker-delta.json`, four hunks:
- item 1: the profile term in `featureExtendPermitted`, two hunks (its comment and the comparison);
- item 2: the `undo` projection in `productFormatBarrier`, plus `productFormatUndo`;
- item 3: the header.

**W1** (`w1-delta.txt`): the list applied to the archived worker gives the candidate byte for byte. A copy with one extra line fails.

**W2** (`w2-worker.txt`): the real source in a vm sandbox.
- The projection inside `formatBarrier` is `{read, changed, actionsBefore, actionsAfter}`: no `top`; a field of the wrong type is null; an absent record and an array are null; a top-level `undo` is not read.
- Line extension stays permitted under `e2-editor-v27`.
- Four causal controls, each red: the old profile term, the projection removed, `top` projected, an untyped `read`.

My first W2 called `featureExtendPermitted()` without its action argument. The test was wrong, not the worker; fixed before the run recorded here.

## PL-1 (the relink gate)

Done before the mechanics, in its own directory: `../pl1/README.md`. **PL1_WOULD_VERIFY 12/12** (Chrome and Firefox x F3's list-contexts cell and S3's recipe x 3; every v26 record is 046's cell and passes v27's collapsed rule); self-test 68/68 red. S3's document: `../fixture-two-plain/`.

## Build mechanics step (spec 5)

New, v25's/v26's tools not edited:
- **Makefile v27 block.** v25's rules verbatim plus `-DOXSDK_E2_V27_FIRST_BLOCK`.
  - The v26 archive (`e2-editor-v26-44cb15ea-worker-95d6e7ae`) is the base: its `exports.txt` (= v25's), its worker pin `95d6e7ae...` in the preflight, and its manifest as a dependency.
  - Worker `cp sdk/v27-first-block-worker.js`; the link guarded (`refuse_unasked_relink`) with `link_product_stack_1m`.
  - `test-v27-first-block-static`: E1/E2, E4, W1, the new profile test, W2.
- **`tools/check_v27_first_block_contract.py`.** `check_v25_feature_contract.py` with the names changed: v26 archive and worker pin, `sdk/v27-first-block-worker.js`, `build/e2/editor-v27`, plus the v27 define in `DEFINES`.
- **`tools/build_e2_v27_first_block_profile.py`.** The v25 construction, then the archived v26 manifest's `select-all` leaf. Its summary's `withheld` is recomputed after that leaf is replaced: the v5 builder prints it before. Without the recomputation, the build log would say `withheld: ["select-all"]` for a manifest that grants it. Caught on the first dry run.
- **`tools/link_v27_first_block_owner.sh`.** v25's with the names changed, plus `selectAll` in the final JSON. Agent ran `bash -n` only (exit 0).
- **`tests/test_v27_first_block_profile.py`** (7 tests), the shape of v25's, plus one addition:
  - the builder run end to end on the v26 archive's own wasm and loader with the v27 worker gives v26's manifest with exactly `/editorContract/workerSha256`, `/profile` and `/sdkVersion` changed, and `withheld: []`;
  - reds in advance: ABI 7, typedInsert absent, a new leaf, the `formatBarrier` leaf bumped, select-all withheld again, a gesture, the profile name, a top-level leaf, the v26 worker refused, a wrong identity, a build log without the v27 define or with three units.
- `static-tests.txt`: `make test-v27-first-block-static` exit 0.

### M1-1

- `m1-1-red-without-v27-carrier.*`: exit 1, naming exactly E2_V27's `sdk_api.o`, `probe_engine.o`, `editor_api.o`.
- `m1-1-green-with-v27-carrier.*`: with `--carrier E2_V27=probe_engine,sdk_api,editor_api` added to `test-e2-c-static`, exit 0, 39 rules / 151 objects; E2_V27's three guard variants refused.
- The argv equals the Makefile's line (`shlex`-compared after the edit). `taskset -c 0`, 57-58 s each.

### L

- `ships.*`: `what_the_link_ships.py --since 9d7fb9e7c --variant link-batch-v27 --shipped-profile dist/profiles/e2-editor-v26` (variant added, data only). `ok`, no drift. Only `probe_engine` changes, two hunks, both in the .cpp: the struct fields and the serializer. The other three units are identical. The worker row compares the tree's generic `sdk/sdk-worker.js` with v26's, as in v25 (recorded, not judged).
- `l-confined.json`: `tools/check_v27_ships_confined.py` (derived from v25's, not edited) -> **CONFINED_V27_HOLDS**, exit 0, 3 s.
  - A: 40 differing preprocessed lines (22 in `ordered_format.inc`, 18 in `probe_engine.cpp`), all inside v27 branches.
  - B: v25's line on the live tree equals v25's line on `9d7fb9e7c`, all four units.
  - C: v25's line is v27's without the define, all four units.
  - **D (new)**: with every `OXSDK_E2_V27_FIRST_BLOCK` group stripped, all 33 source files equal `9d7fb9e7c` byte for byte. The groups are exactly the seven declared hunks of spec 4.1 item 6: the guard, the undo fields, the undo serialisation, the undo read before the post, no restore before the select on the collapsed route, the `multiBlock` refusal off the collapsed route, and the undo read after the restore. None is nested in a v25 branch. The four untracked `src/*.o` files are listed as ignored (not source).
- `l-confined-red-cases.txt`: three scratch copies of `src/`, each `CONFINED_V27_RED` for its own reason.
  - One code line added outside any group: red on B and D.
  - The undo-read-after-restore group removed: red on D only ("declared hunk ... found in 0 groups").
  - An undeclared v27 group added: red on D only.
  - The last two are invisible to A/B/C, which is why D exists.

### PIN

- `source-pin.json` (`source_pin.py --write`). Section 10's six core files are hashed in the link tree, the Makefile's `LOSRC` = `../libreoffice-26-8` read from `make -pn`, and in `native-lok-26-8/src`. Both trees are at git `671c848b`, and **all six agree**.
  - `--check` holds.
  - `source-pin-red-case.txt`: a copy with one byte of `pam.cxx` flipped is `PIN_RED` naming that file; restored, it holds.
- `frozen-set-before.sha256`: every regular file under `dist/profiles/` and `build/archive/`, 2,757 files.
  - All 2,453 of v25's pre-link set are present with the same hashes.
  - No `e2-editor-v27` file exists.
- `v26-archive-sha256sums.txt`: the v26 archive verifies 5/5.
- **Absent before the link:** `build/e2/editor-v27`, `dist/profiles/e2-editor-v27`, `build/link-v27-first-block-01.log`.
- `make-n-owner-command.txt`: `make -n` of the owner's one command, with the script's environment unsets.
  - It prints exactly the four `build/e2/editor-v27` compiles, the exports `cp`, one guarded link, the worker `cp` and the manifest build.
  - No v23D/v23D_R2/v23/v24/v25 object.
  - The link line equals v25's link line with the build directory renamed (35 tokens; `make -n -B` of v25's `probe.js`).

### `make -k test-e2-c-static` (`test-e2-c-static.txt`, exit 2)

M1-1 inside it is green. Three Python unit tests are red. Each predates this session and touches nothing this step changed:
- `test_e2_c_shell_bundle ... real_manifest_matches_the_real_tree`.
  - The v24/v25/v26 workers already sat in `sdk/` unclassified; v27's is the fourth.
  - The live page differs from `dist/` since the shell item (`9fbbb9b93`).
  - Both close at generation 81's freeze, whose exclusion list is v80's plus `sdk/v27-first-block-worker.js` (spec 7.3).
- `test_product_path_mutations ... (mutation='copy-lies')`: the named debt **L-copy-lies-pattern-stale** (finding 175's ruling, item 6). `run_e2_c_product_path.py` is bound.
- `test_session_liveness ... inducing_arms_hold_the_guard_off`: 4 != 3. The bound runner has had four `with liveness.expecting(` since `c6213c854` (2026-10-27; its parent has 3).
