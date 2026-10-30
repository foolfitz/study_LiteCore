# Handoff: the 083 path measured natively (ruling 3 Q5.2) -- the blank document cannot be read, a multi-paragraph last line can

Checkpoint **2026-10-30 ~18:00 +0800**. Supersedes `HANDOFF-2026-10-30i-host-0243-installed-hand-tests-done.md` (including its Addendum) for what it says next; that file still holds for the shipped state.

Study HEAD **49ecba3ff** plus this file's commit. Untracked, all to be kept:
- `codex-claude-code-delegation.md` -- not ours;
- native harness binaries: `findings/evidence/176/native/build-01/f176-native`, `build-02/f176-native`, `findings/evidence/176/native-q52/build-01/f083-native`.

**No evidence runner is running.** Shipped state unchanged: `dist/` serves generation 81 / profile `e2-editor-v27`; the live host runs **0.2.43**, the daily uncounted candidate (owner A, 17:00). The nominal shipped host stays 0.2.26.

## What was done

The owner picked 「A. 量 083 那格」 (~17:05). Everything is under `findings/evidence/176/native-q52/` (see its `README.md`):

| Step | Commit | Result |
|---|---|---|
| Criteria registered before compiling; harness, fixtures, smoke; amendment 1 (smoke, nothing changed) | `15cd044a1` | `PREDICTION.md`; `tool/f083_native.cpp` = `f176_native.cpp` + op H (G, then a fallback selection only when `.uno:SelectText` reads NONE) |
| Counted run, 27 cells x 5, all exit 0; reader + self-test 36/36; finding 176 append | `49ecba3ff` | below |

Verdicts:
- **V1 `ONE-BLOCK-DOES-NOT-VERIFY`** (fail closed). On the host's blank template `.uno:SelectAll` reads NONE, 5/5, for all five actions, the sham and the no-op. `.uno:CharLeftSel` reads NONE too. An empty one-paragraph document has no non-collapsed selection. **Ruling 3 Q5.2's premise for the owner's case does not hold**: no selection-based readback exists there.
- **V2 `LAST-HOLDS`** (SelectAll) and **V3 `LAST-HOLDS`** (CharLeftSel):
  - On multi-paragraph documents (a4, a7 = End+Enter at the last paragraph, a8, a section before it, the last paragraph inside a section), the readback's LAST block equals the saved dispatch paragraph, 5/5 each.
  - The shams are safe.
  - Tables are refused by the existing parser (body-level `<table>`), so they fail closed.
  - The existing first-block predicate is wrong here: it rejects the applied cells (except a8), and it is satisfied on the n8 sham. **A last-block field is needed.**
- **SelectAll is COMPLEX above 10,000 characters** (`desktop/source/lib/init.cxx:6023`; 5/5 on 300 lines). CharLeftSel's read is the paragraph break only (561-581 bytes). It was not run on the long document; that is predicted by construction.
- The Q restore clears both fallbacks, 135/135.

## Owner state

Pending with the owner (asked at this checkpoint, A/B/C; see the reply in the session). The main session recommends **A, with the design questions going to fable first**:
- **A.** Build the multi-paragraph last line in the next engine batch (v28): on `select-text-returned-none`, a `.uno:CharLeftSel` fallback plus a last-block field. The blank document keeps the toast.
- **B.** Look for another observable for the blank document. The only ones on record are the late `.uno:DefaultBullet` state item (~300-600 ms after the reply, `../native/`) and the undo stack (declined alone by ruling 3 Q5.1). Either is a new mechanism, which is a fable question.
- **C.** Stop at the measurement; the 083 sentence stays.

Before a v28 spec, the five paragraph actions need native cells on **multi-paragraph** documents: only the bullet was run there. That needs the existing harness, minutes, no ddev.

## Cautions

- **Cross-session.** Another session uses DDEV. Do not touch DDEV or the owner's desktop processes.
- **Bound tools** as in 10-30i (derive, never edit). The new harness is derived; `../native/tool/run_cells.py` was imported unedited.
- **Count chain.** The count chain and K stay batched; the uncounted engine changes span v22-v27. A v28 would add to them.

## Section 34.4 this round

- Fixed-by-execution: **1**. The self-test's scope cases indexed the verdict object instead of its `actions`; this was fixed before any self-test result was recorded.
- Fixed-by-review: **0**.
- Fable rulings: **0**.

## Language

- Replies to the owner: Taiwan Traditional Chinese, with A/B/C options.
- Evidence and `handoff/**`: English.
- Specs and findings: zh-TW.
