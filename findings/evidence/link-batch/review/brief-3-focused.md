# Review brief 3 — focused, bounded: SPEC-M3-link-batch §10 only

**Subject:** `specs/SPEC-M3-link-batch.md` §10 only (commit `66e39525`, zh-TW). It writes fable ruling 2
(`findings/evidence/link-batch/review/ruling-2.md`, `918c2497`) into the spec. This is the single focused round
that ruling 2, condition 14, requires. **There is no third round.** Do not review other sections, and do not
reopen the rulings.

**Answer exactly these five questions** (fixed in §10.11). Each answer either names a concrete counterexample
with file:line evidence and a step-by-step scenario, or says "none found" and lists what you checked.

1. A path that completes before its own flush, whose late flush carries a `TEXT_SELECTION` that differs from
   the next extend's dispatch cache, and that is NOT in L-extend-prior-flush's population (§10.1). Check every
   completion site in `wasm_sdk_probe/src/probe_engine.cpp` that does not wait for its own callback.
2. A path where K1's late `TEXT_SELECTION`, arriving inside §10.5's window, reaches the ordinary unit path with
   a P that the anchor fence does not catch (`merge_key_undo.hpp`, `startSelectionBarrierDelete`,
   `handleSelectionBarrierStateCallback`, `rejectSelectionBarrierAtDeadline`).
3. A page-count change that emits neither `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED` nor a paint reply with
   `documentSizeChanged` (`libreoffice-26-8/sw/`, `desktop/source/lib/init.cxx`; `probe_engine.cpp:3120–3150`).
4. Whether S5's population or oracle (§10.4) can be passed by a broken product in an honest run.
5. Whether S-1's pin list (§10.9) is complete. Grep for every file that pins the editor ABI version, the
   manifest's move gestures and limits, or `MOVE_ACTIONS`.

**Limits:** SPEC-M3-paragraph-merge §34. Checks guard honest accidents only. Propose no new machinery unless
a criterion would pass a broken product in an honest run.

**Output:** write `findings/evidence/link-batch/review/review-3-focused.md` (English).
- Begin with `## SUMMARY` (≤ 20 lines).
- Then one section per question, each with a verdict of COUNTEREXAMPLE, SHOULD or NONE.
- Edit nothing else.

**Commit:** only your file, with an English message ending
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and no `Claude-Session:` line. If `.git/index.lock`
exists, retry.
