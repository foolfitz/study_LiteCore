# Plan, 2026-10-20: the ordered-commands batch (engine v23) — scope and first steps

Status: **draft for the owner's scope choice** (§4). Nothing here is a criterion. The spec (`specs/SPEC-M3-ordered-commands.md`, zh-TW) is written after the scope and the candidate are chosen, and its criteria are pinned before any implementation.

The owner chose "A+B" on 2026-10-20. A is "start the ordered-commands batch's preliminary work: native measurements, then the spec with its criteria pinned first, then review; no link, no ddev". B (host 0.2.28) is prepared separately (`b6a8379f`, v22 spec §14).

## 1. The one property

From ruling 4 (`findings/evidence/link-batch/review/ruling-4.md`) and ruling 5 (`ruling-5.md`): **every document command the page asks for is applied in the order Writer would apply it.**

Today it is not. A synchronous LOK command can run before a posted key that core has not run yet (finding 137). The synchronous commands are `.uno:Delete`, typing through `paste`, `.uno:Bold`, and `setTextSelection`; the posted key is an arrow. The result can be:
- a wrong delete;
- a typed character landing one unit early;
- a format applied to just-deselected text.

Every divergence the model found had a key still queued. There is no interim patch, because any wait rule is a timing bet (finding 137; ruling 4).

## 2. What is deferred to this batch (census, 2026-10-20)

An Explore census of handoff/, specs/ and findings/ found 18 items. Its sources are listed in §6. They group into four tiers:

**Tier 1: the ordering fix itself**
1. Finding 137's root fix, for all three effects. Candidates A, A′, B and C are in `SPEC-M3-link-batch.md` §13.4 and §14.
2. L-142-readback-overtaken. A move is answered by the 250 ms readback with a stale caret, and the next synchronous command overtakes it. After any save it is 6/6 (`SPEC-M3-link-batch-v21.md`:462-466).
3. Finding 151's arrow half: the first arrow after an edit. The counted check `a-boundary-arrow-press-does-not-cost-the-work` (096) pins today's behaviour, so changing it needs a §34 ruling (`findings/151-…md`:33-54).
4. L-md-137: Markdown paste is in 137's class (`SPEC-M3-link-batch-v21.md`:111).

**Tier 2: what the ordering makes safe**
5. Shift+Arrow (link-batch item 1). The owner asked for it by name. Default: it ships on no profile until this spec exists (`SPEC-M3-link-batch.md` §13.5).
6. Arrows on a range (item 2; finding 129's prescription), with R1 (129's 42 cells plus the L-129 wrap cell).
7. The rest of the extend package:
   - the §10.4/§12.4 delete-form resolver;
   - S1–S5 and S-12 (held Shift);
   - the §12.5 pin widening;
   - S2's 16-cell v19 pre-red.
8. Three counted product-path arms withdrawn in v20, which "return with Shift+Arrow": Shift after an insert, Shift after a merging Backspace, and Shift+Right held for 1 s (`v20-shakedown/ARMS.md`:23).
9. The forged-completion residual and L-extend-prior-flush (`HANDOFF-2026-10-13f`:103-104).

**Tier 3: answers that depend on the chosen candidate**
10. An immediate document-boundary answer, replacing today's 2.25 s window. Options (a)–(e) are in `handoff/link-batch-v21/facts-caret-boundary.md` §(c).
11. `handleEditorPlaceCaret` completing on `TEXT_SELECTION` (finding 140's second pass).
12. The C manifest declaration, which ships with its first reader (it was withdrawn from v21).
13. The L-C-number-or-indent closure. Only candidate A closes it; under B or C it is re-registered (`SPEC-M3-link-batch.md` §15.1).

**Required content of the spec, whatever the scope**
14. The three fixed first-round review questions. Question 2 must name positions (i)–(iii) with their native `.uno:Undo` tops; without them the spec "不算定稿" (§13.4, §15.1).
15. The model's known limit: bold does not change rectangle widths in the model (§14).
16. ABI 6 or later, if extend is touched (v21 used ABI 5).
17. A §34 ruling for the counted 096 check, if item 3 is in.

**Adjacent, not this spec**
18. Typing during the no-op 2.25 s window (task 10-14m).
- Level-2 `STACK_OVERFLOW_CHECK` on the owner's next diagnostic link (v22 spec §3.3).
- D6 (paste, then Ctrl+End, then type) implemented before the next item-1 run.

## 3. The order of work

As ruling 4 and ruling 5 fix it: **measure natively, then the model, then wiring.** In detail:

1. **Facts from source** (done 2026-10-20; an opus subagent, its load-bearing citations re-read by the main session): `handoff/link-batch-v23/facts-lok-command-ordering.md`. It covers, for each wire action, which LOK entry the engine uses and whether that entry is synchronous or posted. It also covers the VCL user-event queue, re-entrancy, and what a FIFO marker would need, with or without the internal API. This is what decides which candidates are buildable at all.
2. **Choose the candidate.** This is a hard decision: the consequences are an engine design and an ABI change, so per memory `offer-fable-for-judgement-calls` the owner is asked whether fable rules on it. The inputs are the facts sheet, and what each candidate covers and closes:

   | | deletes | typing | formats | closes L-C-number-or-indent | needs |
   |---|---|---|---|---|---|
   | A | yes | no | no | yes | the merge path's undo proof per delete |
   | A′ | (with A) | yes | yes | (with A) | measurements for IME, finding 122's latency and accelerators |
   | B | yes | yes | yes | no | a marker; §16.1's forgery analysis |
   | C | yes | yes | yes | no | unipoll; blocked by finding 040 |

3. **Native arms for the chosen candidate.** Native runs only, no link (the precedent is v21's 1a/1b/1c). Candidate A's to-measure list is in ruling 4: Delete/Backspace on ranges against `.uno:Delete`'s result, the boundary case, and `selectedText`.
4. **The model**, re-run with the candidate. It must pass condition 33's two shapes (typing and formats behind a queued key) and the generator's existing shapes.
5. **The spec**, with criteria pinned first, then **two-seat review** (opus plus `codex exec -s read-only`; the codex MCP failed to connect this session) with the three fixed questions.
6. **Implementation**: red cases first, then the witness on the no-host page, a shell freeze, and v22 archived.
7. **The owner links v23.**
8. Shakedown, host 0.2.29, and **K**. K is the count for v22's accumulated changes too, in a window the owner names; ask before it runs (memory `release-count-batched`).

## 4. Scope choice for the owner (A/B/C)

- **A (recommended): tiers 1 and 2.** This is the ordering fix plus Shift+Arrow and arrows on a range. The ordering fix exists to make Shift+Arrow safe (ruling 4), and the owner asked for Shift+Arrow. Tier 3 items come in only where the chosen candidate makes them free; for example, under A the L-C-number-or-indent residual closes by construction.
- **B: tier 1 only.** This is the ordering fix without new keys. It is smaller and quicker to count. Shift+Arrow then waits one more batch.
- **C: tiers 1–3.** This is everything, including the immediate boundary answer and the C declaration. It is the largest, and tier 3's designs depend on the candidate, so they would be specified after it is chosen.

The default if nothing is chosen: the facts sheet and the candidate analysis proceed (they are needed under every option), and no spec is written.

## 5. What needs the owner

- The scope (§4).
- Whether fable rules on the candidate (§3 step 2).
- The link (`make`).
- The ddev window for host 0.2.29 and for K.
- Unchanged from the v22 handoff: the hand tests on 0.2.27 (F3-hand, Ctrl/Cmd+Home/End, the dialog), and the window for 0.2.28.

## 6. Census sources (newest first; from the Explore census, 2026-10-20)

- `specs/SPEC-M3-link-batch.md`:
  - §13.3–§13.5: the deferral, condition 34, and the three fixed questions;
  - §14: the rename, A′, and the model limit;
  - §15.1: L-C-number-or-indent;
  - §17.4: Rbs/Rdel's ≥ 2,000 ms positive control.
- `findings/evidence/link-batch/review/ruling-4.md` (`5a8d69f1`): the six holes and candidate A's to-measure list.
- `findings/evidence/link-batch/review/ruling-5.md` (`b0ca2790`): conditions 37–41.
- `findings/137-…md`: the model's counts (coverage, not frequency).
- `findings/151-…md`, `findings/096-…md`:421-423, and `findings/evidence/link-batch-v21/shakedown/review/ruling-fable-1.md`.
- `specs/SPEC-M3-link-batch-v21.md`:
  - §2 and §4.3: the C declaration withdrawn, L-md-137;
  - §9.1, §9.11, §9.13;
  - §12.3: L-142-readback-overtaken.
- `handoff/PLAN-2026-10-16-link-batch-v21.md`:94-113 and 132: the boundary answer and placeCaret.
- `handoff/link-batch-v21/facts-caret-boundary.md`: the boundary facts and options (a)–(e), and placeCaret on `TEXT_SELECTION`.
- `handoff/link-batch-v21/facts-markdown-cfield.md`:212-218: the C field's open questions.
- `handoff/HANDOFF-2026-10-13f-shift-arrow-deferred-137-registered-v20-part1.md`:33-40, 51 and 103-107.
- `findings/evidence/link-batch/extend-signatures/run-20261013T095104Z/`: native extend signatures (111 cells).
- `findings/evidence/link-batch/extend-model/README.md`, `wasm_sdk_probe/tests/extend_completion_model_test.cpp` and `wasm_sdk_probe/src/extend_completion.hpp`: the model.
