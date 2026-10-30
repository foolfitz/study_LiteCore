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

## Addendum (~19:00 +0800): the owner chose A; the four other actions measured; fable ruling 4 requested

- **The owner's answer.** 「A. 做多段文件最後一行（推薦）」 (~18:05): v28, a `.uno:CharLeftSel` fallback plus a last-block field. The blank document keeps the toast. The design goes to fable first; the four other actions are measured before a spec.
- **Amendment 2** (`cce4a7e76` registered, `e798427f8` judged).
  - Number, none, heading and body under CL + LAST. **V4 = `LAST-UNSAFE`** as registered (`cl-nbody-sham-heading-last` 5/5).
  - The cause, measured: 176's heading markup in a document without `office:styles` loads as a **pseudo-heading** (automatic style, parent Standard, direct outline level). The HTML export writes it as `<p>`, while the ground truth calls it `text:h`.
  - Number and none meet the per-action rule as recorded data.
  - Correction 1: the UNSAFE clause was inverted for N cells. It was fixed before any of those records was read.
- **Amendment 3** (`e798427f8` registered, `53c957838` judged).
  - Real Heading 1 fixtures. The precondition holds: the untouched heading reads `<h1>`.
  - **V5: heading and body IN-SCOPE.**
  - On the v27 route: body on a real empty Heading 1 is verified and its sham refused. This closes ruling 3 Q6.3 b1's pseudo-heading premise.
  - A pseudo-heading with text reads as body whatever the dispatch did: **L-pseudo-heading-reads-as-body**, which predates v28.
- **Found for the design** (in the fable brief): any failure shape not in `EMPTY_SELECTION_SHAPES` / `multi-block-readback` keeps the **rollback** disposition (`editor-shell-v2/paragraph-editor-client.js` ~295-345). So a fallback refusing as `unknown-structural-tag` (a table before the last line) would make today's 083 toast a rollback. This is finding 173's shape. The v28 spec must keep every fallback outcome at least as gentle as the 083 path.
- **Fable ruling 4 is running** (read-only, questions Q1-Q8: fallback command, last-block rule, failure shapes and dispositions, scope, pseudo-heading, the blank document, what the spec pins, batching). Save it as `findings/evidence/176/RULING-fable-2026-10-30-d.md`, relay it in plain words, then write the v28 spec.

Section 34.4 this round, updated: fixed-by-execution **3** (the q52 self-test scope index; the headings reader's mid-document target; correction 1 of amendment 2, found while writing the reader). Fixed-by-review **0**. Fable rulings **1 requested**.

## Addendum 2 (~19:15 +0800): ruling 4 received; owner decisions; amendment 4 done -- next is the v28 spec

- **Fable ruling 4** is saved as `findings/evidence/176/RULING-fable-2026-10-30-d.md` (`b71170036`), with the main session's verification appended: 22 cells = 18 counted + 4 smoke, all exactly 2 blocks; restores 205/205.
  - **Fallback:** `.uno:CharLeftSel` only, collapsed route only, after a NONE SelectText read, before the Q restore.
  - **Judgement:** a new last-block predicate (`lastListTag`/`lastBlockTag`) plus `blockCount == 2`.
  - **Failure shapes:**

    | outcome | shape | disposition |
    |---|---|---|
    | fallback reads NONE | `select-text-returned-none` | unchanged (the blank document byte for byte) |
    | fallback refused | new `fallback-readback-refused` | review, via the client, plus its own new page sentence |
    | judged, not satisfied | `postcondition-not-met` | as today |
    | restore failure | `selection-not-restored` | rollback |

  - **Batch:** v28 ships alone (gen 82, host 0.2.44). Section 4 of the ruling is the spec's checklist.
- **Owner decisions (~19:10, A/B):**
  - **「A. 照引擎原本規則」**: a restore failure after the fallback is rollback (ruling 4 Q3.3's default; alternative B declined).
  - **「A. 新寫一句」**: the `fallback-readback-refused` toast gets its own new sentence (ruling 4 Q3.2's default).
- **Amendment 4** (`dd8a74fcd` registered, `2939814ae` judged):
  - **V6**: number and none IN-SCOPE, re-run after registration.
  - **V7-HOLDS**: CL reads 577 bytes on 300 lines (constant cost now measured); two empty paragraphs at the end are verified with the previous one untouched; the sham is safe.
  - **Final scope**: all five actions on the multi-paragraph last line.
- **Next:**
  1. Write `specs/SPEC-M3-v28-last-line-fallback.md` (zh-TW), modelled on the v27 spec and ruling 4 section 4. Include the census (section 10 of ruling 4 section 4), the source pins (CL's handler chain in the link tree; `init.cxx:6023`), the closed hunk list, E1/E4 red cases, PL-1-v28, the gen 82 shell items, S4-a..d, and host 0.2.44.
  2. Adversarial review (opus).
  3. Pin.
  4. The appends owed: finding 176; v27 spec Q6.3 b1 premise (ruling 4 Q5.2); 046 if touched.
  5. Shell red then green, engine E1 red then green, the pre-link gates, PL-1-v28.
  6. Hand the link to the owner.
- **Accumulated uncounted engine changes since 0.2.26: v22-v27, + v28 when linked.** K and the count chain stay batched.
