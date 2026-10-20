# Brief for fable, ruling 1 addendum 1 (v23): four questions the spec draft cannot settle by itself

**Authority:** the same as ruling 1. The owner, 2026-10-20 ~06:40: 「我不在座位，請自主執行任務，另外我授權給fable 代我做決策」. §1 is plain-language zh-TW for the owner; the rest is English. Constraints are as ruling 1's brief: read-only, no ddev, no browser, no make, targeted reads.

**Since ruling 1:**
- The native arms read **VERDICT C-HOLDS** (`24c5b635`; `findings/evidence/link-batch-v23/native/ordered-commands/README.md`). Seven decision arms are Writer-order 5/5 under unipoll, the q controls reorder 5/5, and D8 holds.
- D7's undo tops at return: (i) `Number On/Off`, (ii) `Number On/Off`, (iii) `Apply attributes`, plain P1: none.
- **Finding 156**: since upstream `caa4036188ed`, `lo_runLoop` never runs `Desktop::Main` (`ImplSVMain`'s early return). Natively the stack Desktop is then destroyed, so the native harness had to skip `runLoop` and call `SfxApplication::GetOrCreate()` (`smoke/NOTES.md`). WASM leaks the Desktop.
- An opus inventory of the engine's asynchronous-key machinery, every claim cited: `handoff/link-batch-v23/facts-async-key-machinery.md` (`ee0f167e`). The main session re-read:
  - the drain runs until the queue is empty (`probe_engine.cpp:6688-6750`), against your §2.5;
  - ABI 5 (`editor_api.h:48-52`);
  - `kMaxInternalEditorAction` 25 (`:7281`);
  - the deadline constants (`:470,479,506,603,605,607,1047`, longest 5000 ms);
  - the flush is a posted user event (`init.cxx:2577-2580`).

**The draft spec:** `specs/SPEC-M3-ordered-commands.md` (zh-TW). It is committed with this brief, and its header says it is NOT pinned. It is pinned at the first commit after your answers are written into it.

## Questions

- **Q1 (§34, the counted 096 check).** `a-boundary-arrow-press-does-not-cost-the-work` (`wasm_sdk_probe/tools/run_e2_c_product_path.py:2205-2262`, `:9550-9575`; `findings/096-…md:421-423`) pins today's behaviour: a boundary arrow takes no checkpoint, under the 2.25 s window. Finding 151's arrow half, and C's at-return no-op, change what it pins. Write the §34 ruling, with CLAUDE.md §9's four conditions, before any run that would satisfy it. Draft §4 row 3 and §13 Q1.
- **Q2 (the barrier and the vocabulary).** Draft §5.4 withdraws the selection barrier (K1): the main session cannot name anything it still guards under C, and your §2.8(b) default is the user's own key. Draft §5.8 keeps the completion strings' names (`verified-key-undo`, `verified-boundary-noop`) with ABI-6 semantics, because the consumers span the client, session, page, worker and tools, and `editor-shell/editor-client.js:70-86` / `editor-session.js` are bound by **E1-C's judgement**. It also asks what happens to the wasm-byte detector `run_merge_wasm_shakedown.py:208` (imported by `check_m3_production_ui.py:653`). Is that right, and what is the default?
- **Q3 (completion and the watchdog).** Draft §5.2: one command per poll; a command completes when its call has returned and the next poll has come (the core is idle, so its flush has run); the reply goes out then. N1 (§9.1) measures that inference natively before any engine code. Draft §5.6: a worker-side watchdog at 5 s (today's longest engine deadline) replaces every wait-for-callback deadline. Are the forms and defaults right? Is N1 the right arm, and is its red case enough?
- **Q4.** Should level-2 `STACK_OVERFLOW_CHECK` (v22 spec §3.3, registered for "the owner's next diagnostic link") ride the v23 diagnostic profile (§9.2)?

Also say what the draft gets wrong or leaves out: anything in §4's 18 dispositions, §5.3's A1–A13 table, §7, §8, §9 or §11.

**Shape:** as ruling 1: `## 1. 裁決（白話，給擁有者）`, `## 2. Answers (English)` (numbered, each with its form and default), `## 3. Facts checked`, `## 4. What the main session does next`.
