# M1-1 extended: per-carrier object sets (ruling 6 condition 50 as amended). Green run 2 is RED; stopped.

Tool: `wasm_sdk_probe/tools/check_merge_key_undo_scope.py`, extended so that `--carrier RULE[=obj,...]` declares which objects of RULE must differ from BASE (default `probe_engine`, as before). Every declared object must differ; every undeclared object of that carrier and of every other rule must be equal; the compile guards run on every carrier's `probe_engine`. `head.txt` has the tool's sha256 and the tree it ran on. `run.sh` produced everything in this directory (run from `wasm_sdk_probe/`); each run has `NAME.{cmd,stdout,stderr,exit}.txt` and `NAME.json`. All stderr files are empty. No `make` target that builds was run: the tool reads compile commands from `make -n -B` and preprocesses `src/` from `git archive BASE` and the working tree.

## The default invocation is unchanged

`default-after-change.*` is `--base 5d77dc84` with no `=objs`, after the change. Its stdout and its JSON are byte-identical to the witness's (`../m1-1-witness/stdout.txt`, `m1-1-base-5d77dc84.json`): exit 1, 26 rules, 104 objects, 5 different, the same three `E2_V20` FAIL lines (`default-vs-witness-stdout.diff` and `default-vs-witness-json.diff`, both `diff exit 0`). A summary line gains a `declared` key only when some carrier declares more than `probe_engine`, so the default line is not touched.

## Results

| run | arguments (besides `--json`) | exit | what the output says |
|---|---|---|---|
| green-1 | `--base 5d77dc84 --carrier E2_V15 --carrier E2_V19 --carrier E2_V20=probe_engine,sdk_api,editor_api` | **0** | 5 different: v15 and v19 `probe_engine`, v20 `probe_engine`, `sdk_api`, `editor_api`; no FAIL line; the six guard runs all exit 1 |
| green-2 | `--base '82af92ca^' --carrier E2_V20=probe_engine,sdk_api,editor_api` | **1 (RED)** | `FAIL E2_V15 …/probe_engine.o: preprocessed output differs from 82af92ca^` and `FAIL E2_V19 …/probe_engine.o: …` |
| red-1 | green-1 with `E2_V20=probe_engine` | 1 | `FAIL E2_V20 …/sdk_api.o`, `FAIL E2_V20 …/editor_api.o` (differ from 5d77dc84) |
| red-2 | green-1 with `E2_V20=probe_engine,sdk_api` | 1 | `FAIL E2_V20 …/editor_api.o` |
| red-3 | green-1 with `E2_V20=probe_engine,sdk_api,editor_api,unoembind_stub` | 1 | `FAIL E2_V20: its unoembind_stub object does not differ from 5d77dc84 (declared to differ, did not move)` |
| red-4 | green-1 plus `--inject E2_V19=-DOXSDK_E2_V20_LINK_BATCH` | 1 | `FAIL E2_V19 …/sdk_api.o`, `FAIL E2_V19 …/editor_api.o` |
| red-5 | green-2 plus `--carrier E2_V19` | 1 | `FAIL E2_V15 …/probe_engine.o: preprocessed output differs from 82af92ca^` only (see below: not the failure the case was written for) |

Red cases 1 to 4 were run on green-1's carrier list (v15 and v19 stay declared) with only the `E2_V20` part changed, so the one thing wrong in each is the thing the case names. The ruling does not say which base red cases 1 to 4 use; this is a choice.

## Why green-2 is red (a measured fact, and a reading)

At base `82af92ca^` the preprocessed `probe_engine` of E2_V15 and of E2_V19 is not equal to the working tree's. `diag-E2_V15-probe_engine-pp-diff.txt` and `diag-E2_V19-probe_engine-pp-diff.txt` (made by `diag_pp_diff.py`, which uses the tool's own `compile_command` and `preprocess_args`) show the same single hunk in each, one line changed and one line added out of 87,200:

```
-       << ",\"stage\":\"" << jsonEscape(stage) << "\",\"restorePresses\":0}}";
+       << ",\"stage\":\"" << jsonEscape(stage) << "\",\"restorePresses\":0}";
+  json << "}";
```

The source hunk is in `part1-probe_engine-source-diff.txt` (`git diff 82af92ca^ 82af92ca -- src/probe_engine.cpp`, the `finishMergeKeyError` function): part 1 split the closing `}}` into `}`, then `#ifdef OXSDK_E2_V20_LINK_BATCH appendCaretBefore(json, transaction); #endif`, then an **unconditional** `json << "}";`. The first statement now ends before the guard, so the text exists in every rule that compiles `probe_engine.cpp`. `part1-src-log.txt`: `82af92ca` is the only commit touching `wasm_sdk_probe/src` between `82af92ca^` and HEAD, so nothing else can be the cause.

Reading, not measured: without the define, the two statements append the same characters (`}` then `}`) that the one literal appended, so a v15 or v19 build would emit the same bytes at run time. What M1-1 measures is the preprocessed text, and that text differs. The claim "v15's and v19's objects preprocess as before part 1" (part 1 README, the first Makefile comment, ruling 6 F8) is therefore **false as measured**, in one place, by a runtime-neutral refactor outside the define. The deployed v15 and v19 binaries are not affected (they are frozen artifacts); the claim about the source is.

## Red-5 went red, but not for its reason

Red-5 was written to show that `--carrier E2_V19` is red at `82af92ca^` because E2_V19's `probe_engine` is equal there ("declared to differ, did not move"). It is not equal there (above), so E2_V19's declaration is satisfied and the exit 1 comes from E2_V15's undeclared `probe_engine` difference. The case's intended path (a declared `probe_engine` that did not move) is shown on a different base by red-3 (`unoembind_stub`) and by `tests/test_merge_key_undo_scope.py::test_mutations_of_the_green_rows`. I did not add a replacement case.

## What was NOT done, and why

- The Makefile comment (Amendment 1, condition 53′) is **not committed**. It would put into the Makefile "with `--base 82af92ca^` only this rule's `probe_engine.o`, `sdk_api.o` and `editor_api.o` may differ", which green-2 shows to be false. I applied it, ran everything, saw green-2, and restored the Makefile (`head.txt`'s Makefile sha256 is the committed one; the comment is a comment, so the runs do not depend on it).
- `tests/test_merge_key_undo_scope.py` carries green-1 and red-1 to red-4 (rows loaded from the committed JSON), the witness reproduced offline, and mutations. It does **not** assert green-2 or red-5, so nothing in the tests encodes the red as expected.
- X1 (condition 49) and `what_the_link_ships` (condition 51) were not started: the task's rule is to stop on a green run that is not green, and condition 54 orders them after M1-1.

## For whoever decides (not decided here)

The tool did its job: it found that part 1 reached v15 and v19 outside the define. What to do with the hunk, and what the Makefile comment may then say, is a ruling, not a tool change: for instance guarding the `json << "}"` (an engine edit after `82af92ca` was called final), or declaring that hunk as a recorded runtime-neutral difference (which the tool has no way to express and which would be new mechanism). The M1-1 extension itself needs no change for either path except that green-2's carrier list may need to change.

## Appended after commit 543a5566 (ruling 6 amendment 2, conditions 56, 57)

Nothing above is edited. It stays as the record of the stop.

- **Green-2's red is resolved by `543a5566`.** That commit restored the exact pre-part-1 text of `finishMergeKeyError`'s tail on the non-define path (`#ifdef OXSDK_E2_V20_LINK_BATCH … #else … #endif`). The evidence is in `after-56/` (its own `README.md`): green-2 exit 0, green-1 exit 0, red cases 1 to 4 with the same verdicts, red-5 red on exactly one line, and the v20 `probe_engine` preprocessed hash unchanged (`after-56/56a-v20-probe-engine-preprocessed-sha256.txt`). The sentence "green-2 is RED" in this file's title and in "Why green-2 is red" describes the pre-56 runs in this directory only; those outputs are kept unchanged as the record.
- **Red-5 in its corrected form (condition 57).** `after-56/red-5-base-82af92ca-up-with-v19.stdout.txt` has exactly one `FAIL` line, `FAIL E2_V19: its probe_engine object does not differ from 82af92ca^ (B is not in it)`. The red-5 recorded in this directory (pre-56) was red on `E2_V15 …/probe_engine.o: preprocessed output differs` instead and, by condition 57's default, was not a red case.
- **`run.sh` changed** (the only edit to the committed script): `OUT=DIR` writes elsewhere (default unchanged, so the pre-56 outputs here were not overwritten), `red5_clean` judges whether red-5's stdout is exactly that one line, `bash run.sh --check-red5 FILE` runs that judgement alone, and the normal run ends with `red-5: clean red case` or `red-5: NOT A RED CASE`. The outputs in this directory were produced by the earlier version of the script (commit `7719ae25`); its run commands are unchanged. `red5-clean-check.txt` runs `--check-red5` on both red-5 files: the pre-56 one prints `NOT A RED CASE` (exit 1), the after-56 one prints `CLEAN` (exit 0).
- **`rerun-after-56/`** is the updated `run.sh` run once into a fresh directory at the HEAD recorded in its `head.txt` (which contains `543a5566`): `run.sh.output.txt` shows green-1 exit 0, green-2 exit 0, red cases 1 to 5 exit 1 and `red-5: clean red case`; its red-5 stdout is the one line above. The default invocation is still exit 1 with the witness's three `E2_V20` lines, as it must be.
- **Tests.** `tests/test_merge_key_undo_scope.py` now carries the after-56 green-2 and green-1 rows, red-5 asserted to be exactly the one failing line (stdout and exit file included), a mutation of the green-2 rows (a frozen carrier's `probe_engine` moving turns it red), and two negative controls on the pre-56 files (the pre-56 green-2 is still judged red on E2_V15 and E2_V19, the pre-56 red-5 is still judged not a red case). With `tests.test_profile_identity`: 52 tests, OK.
- **Still not done here:** the Makefile comment (53′) was committed with the engine edit in `543a5566` (condition 59), not by this directory's commits.
