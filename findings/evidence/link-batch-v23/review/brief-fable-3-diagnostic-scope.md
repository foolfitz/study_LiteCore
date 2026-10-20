# Brief for fable, ruling 3 (v23): what the diagnostic profile's engine code contains, before any of it is written

**Authority.** The owner, in the conversation on 2026-10-20 (~17:42). The main session asked whether the diagnostic profile's caret delete should be the new path or v22's, with a recommendation. The owner answered **"送 fable 裁決"**. The owner is present and will read §1.

**Language.** §1 is plain-language zh-TW for the owner. The rest is English.

**Constraints:**
- Read-only. No ddev, no browser, no make, no native LibreOffice run.
- Targeted reads only. **No search of the whole repository**: a native run (object-click, then N1's second run, whose N1c cell compares poll delays) is running on this machine while you work. Never `cd` into `libreoffice-26-8/`.
- Use absolute paths. `R` = `/home/jiajun/LibreOffice/study_LiteCore`, `lo/` = `R/libreoffice-26-8/`, `ev/` = `R/findings/evidence/link-batch-v23/`, `pe` = `R/wasm_sdk_probe/src/probe_engine.cpp`, `spec` = `R/specs/SPEC-M3-ordered-commands.md`.

## Since ruling 2

- **Spec §15** appended ruling 2 (`516390c7`). The two native readers had their one review (`465c55c1`).
- **G-HOLDS** (`4e0207ab`, `ev/native/caret-delete-witness/README.md`, spec §15.7). Under `uni1` the paired decider counts exactly the characters the saved document lost, in every cell; undo-only gives 19 on the two underscore arms; the a11y read at return already carries the key's effect. The hole is runs of identical characters, not CJK sentences.
- **The object-click arm** is pinned (`1085726b`, `ev/native/object-click/ARMS.md`). Its first counted run was cut at 72/80 by a session restart and is kept as `out-interrupted-1726/`; the re-run is in progress. **The N1 second run** is pinned (`ed7666e4`, `ev/native/ordered-commands/ARMS-n1b.md`) and runs after it. Neither result is in yet; do not rely on either.
- The handoff that orders the next step is `R/handoff/HANDOFF-2026-10-20d-review-1-ruling-2-native-arms.md` ("Next 3").

## What the main session found while reading the engine before writing it

The engine today has three asynchronous completion styles, all emitted from inside `onLokCallback`:
- **first matching callback**: `completePendingEditorOperation` (`pe:2215-2281`), called from the callback at `pe:2727`; the 250 ms readbacks only on the blocking `engineLoop` (`pe:6455-6474`), deliberately not on the mainloop profile (`pe:2349-2363`);
- **UNO result**: the `UNO_COMMAND_RESULT` branch emits `uno-command-result` and runs 059's check against the `STATE_CHANGED` cache **at the moment the result arrives** (`pe:2802-2873`, `:2827-2835`);
- **staged barriers**: the selection barrier with merge option B (`pe:3442-4271`) and the format barrier (`pe:4646-5470`). Each stage waits for a callback, queues a step as a synthetic command, and has a deadline (250 ms, 2000 ms, 15 ms poll, 5000 ms) served by the blocking loop or by `mainLoopDrainCommands` (`pe:6688-6752`).

The only existing C-shaped loop is the `OXSDK_MAINLOOP_ENGINE` profile (`pe:6609-6931`). It cannot carry v22's defines: `#error "OXSDK_MERGE_KEY_UNDO is not wired into OXSDK_MAINLOOP_ENGINE"` (`pe:15-17`), and V21 requires MERGE (`pe:30-32`). Spec §5.1 says that `#error` is "replaced by the new wiring, not deleted".

## Questions (each answered with its form, per CLAUDE.md §1, and its default if never done, per §2)

- **Q1 (the owner's question). Which caret delete does the diagnostic profile carry?**
  - The texts disagree:
    - spec §9.2 (`spec:184-186`, the sentence at `:186`): the diagnostic wires "§5.1–§5.3 and §5.7, no feature". §5.3 includes **A3** (the selection-barrier delete: "withdrawn, the user's own key instead (§5.4)", `spec:108`) and **A5** (merge option B: "time and fences withdrawn; `judgeAfterKey` stays as the at-return proof", `spec:110`);
    - spec §9.3 (`spec:200-202`, the sentence at `:202`) lists "**§5.4's deletes**" under the second (feature) link;
    - ruling 2 §4 (`ev/review/ruling-fable-2.md:143`) lists "the decider's fixture test (the undo-only variant mislabels 6)" with the **diagnostic** profile's engine code; spec §15.7 says "§15.1's engine code may be written, with the a11y-available guard";
    - spec §9.2's W-D (`spec:190`) runs D1–D6 through the engine's wire actions on the diagnostic; D2, D2′ and D5 are deletes (`ev/native/ordered-commands/README.md`, the table).
  - The two readings the main session sees:
    - **(A)** the diagnostic's caret Backspace/Delete is the user's own key with the paired decider and the a11y-available guard (§15.1); the selection barrier and option B are not used on v23; §9.3's "§5.4's deletes" is read as the shell and product-path half. The main session recommended this to the owner: W-D's delete arms then measure the path that ships, and no option-B wiring is written for the poll loop only to be removed.
    - **(B)** the diagnostic keeps v22's delete (barrier K1 + `.uno:Delete`, merge option B) and wires its deadlines and the 15 ms key poll into the poll loop; the new delete comes with the feature profile. Attribution on the diagnostic stays topology-only, at the cost of throwaway wiring and of §5.3 A3/A5 not being applied there.
  - Whichever you choose, say what replaces the `#error` at `pe:15-17`.
- **Q2. What "staging withdrawn" (§5.3 A7, `spec:112`) means for the format barrier, and for any other callback-waiting stage.**
  - The facts sheet notes that the barrier's containment check and its restore confirmation read the **callback-fed** rectangle cache (`pe:4731-4763`, `:4998`), which is current only after the step's flush; "a single-command barrier would need direct LOK reads instead of the cache" (`R/handoff/link-batch-v23/facts-async-key-machinery.md:86`).
  - Two readings:
    - **(a) one command**: dispatch, select, read, restore, all inside one command, at return. The restore can be confirmed by `getSelectionType` NONE. Containment has no synchronous source, so it would be dropped (046's fingerprint check, `pe:5164-5187`, is a synchronous read and stays) or replaced by a read you name.
    - **(b) poll-stepped, nothing waits**: each step runs at the first poll after the previous step's flush, reading the refreshed cache. A proof absent at that poll is the answer (for example 034's silent empty last paragraph: no selection after `.uno:SelectText` at the next poll is a refusal then, not a wait). No deadline, no 5000 ms. The barrier keeps its BUSY gates across its polls.
  - Which, and does the same reading govern every other stage machine that survives on v23?
- **Q3. Where a reply is composed, and what a missing proof at the first poll means.**
  - The main session reads §5.2 ("the reply is sent at that poll", `spec:97`), ruling 2 §2.1 item 4 ("the reply's `state` is the post-flush cache", `ruling-fable-2.md:47`) and §2.2 ("the cache holds [the Bold item] at the reply poll", `:61`) as: **under v23, callbacks in the flush only update the cache and record evidence; every reply is composed and sent at the first poll after the command's LOK calls returned**. Two consequences follow, and the second is a decision:
    - (i) `completePendingEditorOperation` and the `UNO_COMMAND_RESULT` branch stop emitting under v23. A move, place-caret or select with no matching callback by that poll answers with its readback name (`verified-move-readback`, `verified-caret-readback`, `verified-selection-readback`; A1, A8). 059's check runs at the poll, after the whole flush.
    - (ii) **A proof that is a callback and is absent at that poll**, for commands that are not moves: the `UNO_COMMAND_RESULT` of a listener-posted command (N1a says it cannot be absent, and N1-HOLDS measured that natively); `.uno:ExecuteSearch`, which the engine posts **without** a listener (`pe:3325-3326`), so its result may be queued past the poll (§15.2's correction of §1); the comment's `LOK_CALLBACK_COMMENT` "Add", which today follows a `.uno:Escape` posted **from inside the callback** (`pe:2875-2880`; §5.7 rule 2 moves that to the next poll). Options the main session sees, none recommended: answer at that poll with a typed error (a visible violation; no new timer); or keep the request open until the proof arrives, as today, with the SDK's 30 s as the only bound (§5.6); or split by command class.
  - Is the reading in the first bullet right, and what is (ii)'s rule?

## The main session's own decisions (for objection; each is cheap to reverse now)

- **The diagnostic keeps editor ABI 5.** Its action set is v22's. ABI 6 in spec §5.8 is the feature profile's, with the new actions after `kMaxInternalEditorAction`. Two binaries both called 6 with different action sets would be the identity confusion CLAUDE.md warns about.
- **"A reply is pending" for `anyInput` (§5.2's hard rule)** means a command that has returned and whose reply will be composed at the next poll. It is true from the command's return until that poll. At a poll the order is: a pending reply first, else one queued command, else nothing; the poll never waits (§5.2, §15.2).
- **The pure parts go into headers with host unit tests, red cases first** (the `merge_key_undo.hpp` pattern): the poll step choice and `anyInput`; the paired decider with its a11y guard (fixture generated from the committed G run, labels from the saved text); the table of `STATE_CHANGED` keys a reply may read, compared with `read_n1.py --on-time-list` once N1's second run exists; the static completion table of §5.8. The build-record preconditions (`STACK_OVERFLOW_CHECK=2` on the diagnostic link only; `OXSDK_FINDING_016_SCHEDULER_PROBE` not defined) are a script over the Makefile and the owner's build log, with red cases.
- **The diagnostic-only instruments §9.2 needs are in the diagnostic profile only**: the per-poll queue depth and drain count; a test command that never returns (the hang path's red case, addendum §2.3); a LOK call from the JS-side thread for 040-W's positive control.

## What to return

- Write nothing under the repository. Return the ruling's full text in your final message; the main session saves it verbatim as `ev/review/ruling-fable-3.md` and appends its own source check after it, as with ruling 2.
- The shape: §1 in zh-TW, plain language, for the owner; §2 the answers in English, each with its form and its default if never done.
- If an answer changes a criterion, say whether it meets CLAUDE.md §9's four conditions, or is a correction to append.
