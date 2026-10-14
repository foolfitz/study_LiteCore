# what_the_link_ships for v20 (ruling 6 condition 51, as amended by Amendment 1 (2))

Tool change: one data entry, `link-batch-v20` in `VARIANTS` of `wasm_sdk_probe/tools/what_the_link_ships.py` (`E2_V20_OBJECTS`, `E1_CPPFLAGS`, `MERGE_V15_DEFINES + -DOXSDK_E2_V20_LINK_BATCH`, `PRODUCT_UNITS`). Nothing else in the tool changed. The tool has no test file and I did not make the new entry go red; the only guard the entry has is the tool's own `configurationDrift` check (the Makefile's object list and every define must still appear in `make -pn`), which is empty here.

## The run

`plain.cmd.txt` is `python3 tools/what_the_link_ships.py --since c0337ae3 --variant link-batch-v20 --shipped-profile dist/profiles/e2-editor-v19`. Exit 0 (`plain.exit.txt`), stderr empty. `json.*` is the same command with `--json`: exit 0, `configurationDrift: []`, `errors: {}`, `ok: true`. `head.txt` has the tool's sha256, `c0337ae3`'s full hash, and the sha256 of the tree's worker (`478d0da1…`, the Makefile's pin) and v19's packed worker (`00882139…`).

## Does it match condition 51's expectation? Yes, line by line

| condition 51 expects | the output (`plain.stdout.txt`) |
|---|---|
| `probe_engine` and `sdk_api` changed, by `82af92ca`'s hunks only | `CHANGED sdk_api`, `CHANGED probe_engine`. `cross-checks.txt`: of the commits touching `wasm_sdk_probe/src` since `c0337ae3`, only `82af92ca` touches a `.cpp` or any header a unit includes; `fce084d6` and `19cec698` touch only `extend_completion.hpp`, which no unit includes (the grep in `cross-checks.txt` finds only the header's own comment). This is an argument from which commits touched what, not a hunk-by-hunk match of the tool's output to `82af92ca`'s diff. |
| `unoembind_stub`, `editor_api` identical | `same unoembind_stub`, `same editor_api`. **Read the limit below.** |
| worker not identical to v19's; added code lines are part 1's nine hunks | `CHANGED sdk-worker.js 00882139cd0b2e58 -> 478d0da1dbfcf936 (+94/-0 lines, 61 of them code)`. `cross-checks.txt`: `diff -U0` of v19's packed worker against the tree's has 9 hunks, 0 removed lines, 94 added lines (90 non-blank, the "90 changed lines in 9 hunks" of `v20-part1/README.md` §3); the last commit touching `sdk/sdk-worker.js` is `150c1770`, part 1's worker commit. The nine hunks are counted, not matched one by one. |
| `configurationDrift` empty | `[]` in `json.stdout.json`; nothing on stderr. |
| any other changed unit stops the link | none: all four units are accounted for (two same, two changed), no error. |

So this tool does not stop the link.

## The limit (Amendment 1 (2)): why `editor_api` reads identical

The tool fetches only each unit's `.cpp` at `--since` (`source_at`) and preprocesses both the old and the new `.cpp` with `-Isrc`, so **both sides read the tree's headers**. A change that reaches an unchanged `.cpp` only through a header is invisible to it by construction. `editor_api.cpp` has not changed since `c0337ae3`, so it reads identical; as the v20 rule compiles it, `editor_api.o` does differ from before part 1, by two declarations that come in through `probe_engine.hpp` and `sdk_api.h` (`../m1-1-witness/editor_api-define-diff.txt`; M1-1 counts it as differing in `../m1-1/green-1-base-5d77dc84.json`). The division of labour is therefore: this tool answers "which `.cpp` changed since the shipped link, under the tree's headers"; the define's reach through headers is M1-1's question (it archives the whole `src/`, headers included, at its `--base`). Without this paragraph the `same editor_api` line would be misleading evidence.

## Do not read "identical" as the whole story: M1-1's green-2 is currently red

This tool compiles the v20 configuration only (the define is on). It says nothing about whether part 1 reached the v15 and v19 rules. M1-1 asks that, and its second green run (`--base 82af92ca^`) is **red as of its commit**: E2_V15's and E2_V19's `probe_engine` preprocess differently from the tree before part 1, because of one unguarded hunk in `finishMergeKeyError` (`}}` split into `}` plus an unconditional `json << "}"`). See `../m1-1/README.md`. Ruling 6 Amendment 2 (`c997c271`, subject line) rules a restore of the pre-part-1 text on the non-define path (conditions 56 to 61) and says the link waits on 56; I have not read the amendment's text beyond that subject line and have not touched the engine.

## State of the tree during the runs

Both runs finished at 10:12:37 (+0800, file mtimes in `engine-edit-state.txt`) on `c997c271` plus this tool edit. At 10:12:54 another executor's uncommitted edit to `src/probe_engine.cpp` (the `finishMergeKeyError` restore) appeared. I re-ran the plain command with that edit present: `plain-with-uncommitted-engine-edit.stdout.txt` is byte-identical to `plain.stdout.txt` (exit 0, stderr empty; the edit and its sha256 are in `engine-edit-state.txt`). That is expected to hold, since the edit differs only on the path without the define, which this variant never compiles, but the evidence is the identical re-run, not the reasoning. Whoever rules on condition 56's closure should re-run this tool on the final tree; one command, in `plain.cmd.txt`.

## Appended: re-run at HEAD ≥ `543a5566` (condition 56 landed)

Nothing above is edited. The sentence "M1-1's green-2 is currently red" in the section "Do not read 'identical' as the whole story" was true when written and is **corrected here: it is no longer true.** Ruling 6 amendment 2's condition 56 landed in `543a5566`, and M1-1's green-2 (`--base 82af92ca^`) is exit 0 (`../m1-1/after-56/README.md`, `../m1-1/rerun-after-56/`). The reasoning in that section, that this tool answers only for the v20 configuration and M1-1 answers for the other rules, still stands.

The same command was run again (`plain.cmd.txt`) on HEAD `b110834f` (`head-after-56.txt`: contains `543a5566`, `src/` and `sdk/` clean, `src/probe_engine.cpp` sha256 `ab2c17a7…`, the same file the earlier "uncommitted engine edit" re-run saw). Result: exit 0, stderr empty, in plain (`plain-after-56.*`) and `--json` (`json-after-56.*`). **Nothing changed:** `plain-vs-after-56.diff` and `json-vs-after-56.diff` are both `diff exit 0`, with the same two changed units (`sdk_api`, `probe_engine`), the same two identical units (`unoembind_stub`, `editor_api`), the same worker difference (`00882139…` → `478d0da1…`, +94/-0) and an empty `configurationDrift`. This is the expected outcome, and it is now measured on the committed tree, not on an uncommitted edit. The `editor_api` limit above is unchanged.
