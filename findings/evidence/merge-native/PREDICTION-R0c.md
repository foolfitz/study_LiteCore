# Paragraph merge, native round R0c — the E shape (written 2026-10-06, before R0c ran)

R0c measures the premises of the restore that replaced the unshifted one (`specs/SPEC-M3-paragraph-merge.md` §16, the ruling on §15.2): K1 Shift+arrow (as today), `.uno:Escape`, K2 Shift+arrow back, `.uno:Escape`, the key — no unshifted arrow anywhere, each step sent after the previous one's proof. §16.3 lists the kill conditions; this file fixes what is expected before the run. Default if R0c is never run (16.3): no second press, v15 not linked.

## Instruments (this commit)

- Probe `tools/merge_native_boundaries.cpp`: `MERGE_ESHAPE=1` makes the b arm run the E shape (`runEShape`): the `.uno:Undo` payload before K1 (`undoStart`), K1's readback (`unit`, as before), then `.uno:Escape` via `postUnoCommand` with a completion listener (forced synchronous, `unoctitm.cxx:654–657`) and its readback `esc1` (START/END cleared right before) and payload `esc1Undo`, K2 and its readback `k2`, the second Escape (`esc2`, `esc2Undo`), the key, save, follow text. Nothing selected at K1: no Escape, no K2, no key (`eshapeStop`). Without the variable every arm is byte-for-byte what R0 and R0b ran.
- Reader `tools/check_merge_eshape.py`: applies 16.2's stopping rules per case and round (nothing-selected; barrier; K1 anchor absent or fence failing; K2 text differing from K1's, K2 point side absent; then the key), checks the Escape premises only where v15 would send that Escape, compares the b arm's document with the key arm's where v15 would press the key (bytes; paragraph text for typed cases; follow text by paragraph text), and STOPs on a decision that differs between rounds, a missing arm, or a class that never occurs. KILL lines are 16.3's kill conditions.

The reader's red cases run on a shakedown round (below), before the counted runs, and are recorded in the results section.

## Runs

From `wasm_sdk_probe/`, one at a time, `MERGE_ESHAPE=1 MERGE_FOLLOW_TEXT=Z`, 3 rounds each:

0. Shakedown, **not counted**, only for the reader's red cases: `test-docs/merge/odt/boundaries.odt` with a two-row case file (C01 forward, C02 backward), 1 round, output under `build/merge-native-r0c-shakedown/`.
1. `tools/run_merge_native.sh ../findings/evidence/merge-native/r0c 3 test-docs/merge/odt/boundaries.odt test-docs/merge/r0-boundaries.cases.tsv 1`
2. the same with `boundaries-indent.odt` and `r0-indent.cases.tsv`
3. the same with the owner's document and `r0-pmpc.cases.tsv`, output under `build/merge-native-pmpc/r0c` (arms only into `r0c/`)

Then `tools/check_merge_eshape.py --json ../findings/evidence/merge-native/r0c/eshape.json <the three round dirs>`.

## Predictions

| What | Prediction (per round; the same in all three) |
|---|---|
| nothing-selected | C29, C30 |
| barrier (no separator; not the E shape) | G01 |
| refused at K1, no anchor (table-cell selection, 14.1) | C17 |
| refused at K2, text differs from K1's | C15, C16 — K1 swallowed a whole table row; after Escape #1 the point is past the row, and K2 selects one unit back, not the row |
| typed-merge | Y01, Y02 |
| merge | boundaries C01 C02 C03 C08 C09 C10 C11 C12 C13 C14 C27 I01 I02 I03; indent D01 D04 D08 D12; owner's E01 E02 E05 E10 E12 T01 P27 E13 E15 P62 P63 |
| Escape #1 (where sent) | `TEXT_SELECTION` empty, no START/END, payload equal to `undoStart`, caret at K1's point (same x, inside its line); the result says success |
| K2 (where sent) | selected text byte-equal to K1's for every merge and typed-merge case — **including the nine labelled ones** (I02 C08 C10 I03 I01 P27 E13 P62 P63), because K2 has a mark and so does not stop in front of the label (`crsrsh.cxx:351–360`); point side (START forward, END backward) satisfies 14.2 against the origin caret on every such row |
| Escape #2 | empty, payload unchanged; on ordinary lines no caret delivered (K2's caret with a mark already equals the origin's), on the taller lines of P27, P62, P63 the delivered caret equals the origin caret |
| The key | b arm `content.xml` byte-equal to the key arm in every merge case; paragraph text equal in Y01, Y02; follow text `Z` lands as after the key arm everywhere |
| KILL, STOP | none |

Uncertain, said in advance: (i) C15/C16 could instead be refused at K2's fence or anchor, or K2 could select something that happens to equal K1's text — the last would be a KILL only if its point side then fails the fence; (ii) Escape #1 on C15/C16 leaves the point inside or after a table, a place no earlier round put a collapsed caret; (iii) `.uno:Escape` could leave Writer in a state where the key behaves differently from a fresh caret (`m_bInSelect` and the cursor function pointers are reset by `EnterStdMode`, the same state today's `.uno:Delete` barrier leaves — read, not measured).

## What would change the decision

- Any KILL on a merge or typed-merge row: the E shape is not Writer's key there; §16 goes back to the owner's options with that row (fable's fallback order: G, then B; never C).
- A labelled case refused at K2 by its text: Shift+arrow back does not select the same unit, the label-skipping argument is wrong for that shape.
- Escape changing the undo payload anywhere: the proof that the key changed the payload (3.1 item 8) would need the Escape's action excluded; not designed.
- As predicted: header and model move to the E shape (16.4); then engine glue.
