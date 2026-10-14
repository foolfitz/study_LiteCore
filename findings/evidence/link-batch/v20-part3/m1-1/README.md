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
