# M1-1 witness: the unchanged tool on the tree with the v20 block applied (ruling 6 condition 50.2)

The §34.4 witness for M1-1. The tool is `tools/check_merge_key_undo_scope.py` exactly as committed (unchanged since v19). It was run once at `head.txt` (`d7d62039`, the commit that applied the v20 Makefile block) with `--base 5d77dc84` and its default carriers (E2_V15, E2_V19). No `make` was run; the tool preprocesses `src/` from `git archive BASE` and from the working tree.

- `exit.txt`: `exit 1`. `stdout.txt`: 26 rules, 104 objects, 5 different. `m1-1-base-5d77dc84.json`: the full report. `stderr.txt`: empty. `time.txt`: 8.4 s wall.
- Differing objects:
  - `E2_V15 …/probe_engine.o` and `E2_V19 …/probe_engine.o` (the two existing carriers, as at v19);
  - `E2_V20 build/e2/editor-v20/sdk_api.o`, `…/probe_engine.o` **and `…/editor_api.o`**.
- `unbuildable: FINDING_012_DIAGNOSTIC …/probe_engine.o` is pre-existing; v19's runs show the same (`findings/evidence/v19/pre-link/gates-after-v56.txt:11`).

**Why it is red.** The tool's rule is "only a carrier's `probe_engine.o` may differ, and every other object of a carrier must be equal". E2_V20 is not among the default carriers, and its `sdk_api.o` and `editor_api.o` differ legitimately. A correct v20 cannot pass that rule. This is the honest run that the repair (condition 50.3) answers to.

**Not predicted by ruling 6: `editor_api.o` differs.** Ruling 6 expects `probe_engine` and `sdk_api` only (conditions 50.4, 51). The difference is declarations only. `editor_api-define-diff.txt` preprocesses `src/editor_api.cpp` with the v20 rule's own command (`make -n -B EXTRA_DEFINES= build/e2/editor-v20/editor_api.o`, `-c` → `-E -P`), once with `-DOXSDK_E2_V20_LINK_BATCH` and once without. Two hunks differ:
- the C export's declaration `oxsdk_document_page_rectangles(...)`, from `src/sdk_api.h:102`;
- `SubmitStatus pageRectangles(...)`, from `src/probe_engine.hpp:47–52`.

Neither hunk contains a definition. `editor_api.cpp` includes both headers, so it sees two prototypes it never calls.
