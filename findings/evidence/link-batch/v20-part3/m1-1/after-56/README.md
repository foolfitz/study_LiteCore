# M1-1 after the engine edit of ruling 6 amendment 2 (conditions 56, 57, 59)

**The edit.** It is in `src/probe_engine.cpp`, `finishMergeKeyError`; the diff is in `engine-edit.diff`. Part 1 (`82af92ca`) had changed the unconditional literal `…"restorePresses\":0}}"` to `…0}"`, followed by a guarded `appendCaretBefore` and an unguarded `json << "}";`. The edit puts all three lines under `#ifdef OXSDK_E2_V20_LINK_BATCH` and restores the exact pre-part-1 line under `#else`. Nothing else in `src/` changed (`working-tree-src.txt`, taken before the commit).

- **56(a), the v20 object is unchanged.** `56a-v20-probe-engine-preprocessed-sha256.txt` preprocesses `src/probe_engine.cpp` with the v20 rule's own command (`pp.sh`: `make -n -B EXTRA_DEFINES= build/e2/editor-v20/probe_engine.o`, `-c` → `-E -P`). The sha256 is the same before the edit (HEAD `c997c271`) and after it: `8926e4cb…`. So the object review 6 read is still the v20 object, and the edit needs no new §6 review.
- **56(b), green-2 is now green.** `green-2-base-82af92ca-up`: exit 0. Before the edit it was exit 1, with E2_V15 and E2_V19 `probe_engine.o` differing (`../green-2-base-82af92ca-up.*`). With base `82af92ca^`, only E2_V20's three declared objects differ. This is what establishes "part 1's define reaches only v20's objects".
- **56(c), the other runs give the same verdicts as before the edit** (`../`):
  - `green-1-base-5d77dc84`: exit 0.
  - `red-1-v20-engine-only`: exit 1. `sdk_api.o` and `editor_api.o` are undeclared.
  - `red-2-v20-engine-sdk-api`: exit 1. `editor_api.o` is undeclared.
  - `red-3-v20-declared-unmoved`: exit 1. `unoembind_stub` was declared to differ and did not move.
  - `red-4-inject-v19-define`: exit 1. E2_V19's `sdk_api.o` and `editor_api.o` differ.
- **56(d) / 57, red-5 in its corrected form.** `red-5-base-82af92ca-up-with-v19`: exit 1, and it is red only on `FAIL E2_V19: its probe_engine object does not differ from 82af92ca^ (B is not in it)`, with no other FAIL line. Before the edit it was red for the wrong reason (E2_V15's undeclared difference).
- **56(e), lock scopes.** `lock-scopes.*`: exit 0, `gState.mutex 12, gMergeMutex 13`, unchanged.
- **59, the Makefile comment.** The comment now names the three objects, with `editor_api.o` as declarations only. It is committed in the same commit as the edit, after 56(b) was green.

All runs above were made on the working tree before the commit, with HEAD at `head.txt`. M1-1 preprocesses the working tree's `src/`, so they measure the edit as committed.
