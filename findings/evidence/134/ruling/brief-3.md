# Brief 3 — finding 136 and L-134-restore-flash: fix now (one page change), or register and wait (owner-delegated)

The owner is away and said 「我授權fable帶我裁決」 for this absence, and later 「今天不受token軟上限的限制」. Return format as before: `RULING` / `WHY (台灣正體中文白話, ≤12 lines)` / `FACT CHECK` / `CONDITIONS`, written to `findings/evidence/134/ruling/ruling-3.md`. No product bytes, no `dist/`, no browsers, no commits.

## Facts (measured unless marked)

1. **Finding 136** (`findings/136-…md`, `findings/evidence/134/table/README.md` run-2, run-3). Fixture `wasm_sdk_probe/dist/e1-fixtures/table-boundary.odt`. Caret at the end of cell A1, `kj` typed, one Delete. The Delete is refused with `anchor-mismatch` and the page reopens. Then `zqx` is typed and the file saved.
   - Both browsers: `kj` lands in A1 (paragraph 1) and `zqx` in **B1** (paragraph 2). D reported success, so no toast mentioned it.
   - Paragraph end just before the table (refusal shape: key posted, not verified): `kjzqx` contiguous in paragraph 0, i.e. D was exact.
   - B holds at both table shapes: a held Delete is refused once, and the document is unchanged.
   - Cause, by code: `wasm_sdk_probe/src/probe_engine.cpp:3600-3612`. `startMergeKeyUndo` fails the fence and ends with `anchor-mismatch` while K1's one-unit selection (A1 end into B1) is still active, so the last editor state the engine pushed has its caret in B1. D reads exactly that (ruling-1 condition 2: "the engine's last pushed state"). **Read, not measured inside the engine.**
2. **L-134-restore-flash**: the view sits at the document start for 0.71–0.78 s after a reopen at the end, then returns (`acceptance-0.2.16/`, `restore-window/`). Text typed in that window lands at the restored caret, 6/6 rounds (`restore-window/README.md`). So it is visual only.
3. **Collabora prior art** (`findings/evidence/134/collabora-prior-art.md`, cool-26-04 @ `c64a7343a5c6`). A Writer reconnect does four things:
   - saves the scroll offset before teardown (`Socket.ts:571-576`);
   - ignores core's first-paragraph caret while reconnecting (`WriterTileLayer.js:128-137`);
   - clicks the saved caret centre once the layout is back, then restores the offset (`:227-238`);
   - lets the caret update from that click re-affirm the offset instead of following the caret (`CanvasTileLayer.js:3089-3101`).

   Our D is that third step; we lack the other three.
4. **C2 A/B** (ruling-2): result appended below when it lands. If the page is implicated there, any further page change must account for it.
5. Pending owner hand test: 0.2.16. No count is running; the count stays batched with the next engine change (§9.21).

## Options

- **A — one page change now, both items** (new shell generation v66, host 0.2.17, uncounted candidate):
  - **136:** D uses the caret the engine reported when no delete of this page was out (`deletesInFlight === 0`) — the last *settled* caret — not the last pushed state. Mid-barrier states are exactly what finding 131 already showed to be unreliable: a barrier's one-character selection is pushed as editor state.
  - **Flash:** while the page's own reopen is in progress (from the refusal until D's click has returned or failed), `followCaret()` does not follow. The view stays where it was. If D succeeds, the restored caret is in view and nothing scrolls. If D fails, follow as today, which is honest because the caret is at the start.
  - Acceptance: a unit test red-first for each item, then three browser runs:
    - the table probe's cell arm with the control (`kjzqx` contiguous in A1, both browsers);
    - the acceptance judge over the four arms (unchanged);
    - `scrollTop` never 0 on the end arms (reported, or judged? — your call).
  - Then condition 4's chain again (~1.5 h, sonnet) and v66 / host 0.2.17. The owner's hand test moves to 0.2.17.
- **B — register only.** 136 stays open, the flash stays a named limit, 0.2.16 stays the candidate, and the owner decides.
- **C — 136 only now** (it misplaces text; the flash does not). Same pipeline as A, with less in it.
- **D — engine-side for 136** (Escape before `anchor-mismatch`): goes to the link batch. Says nothing about the flash.

**My lean: A**, one page change for both. They live in the same function (`reopenAfterBoundaryRefusal`) and its caller, so one condition-4 chain covers both. 136 misplaces typed text. The flash has a direct prior art. And the owner said today is not budget-limited. Cost: the owner's pending hand test target moves from 0.2.16 to 0.2.17.

## Claims to attack

- **G1.** "The last settled caret" is well defined: the editor state written while `deletesInFlight === 0`. A held Backspace at the start deletes `kjkjk` first, and its last settled caret is the start after those deletes, which is correct. Could a settled state ever be stale in a way the pushed one is not? For example, a caret move by click or arrow while a delete is out.
- **G2.** Not following the caret during the reopen cannot strand the view. If `restart()` throws, or the session stops, following resumes.
- **G3.** A does not touch H1–H3 or B. 132-B and 131-B in the chain are the witnesses.
- **G4.** Should D at `anchor-mismatch` also say something in the toast (e.g. 「游標已放回原位」)? Today D is silent on success.

## Questions

1. A, B, C or D (or other)?
2. If A or C: the acceptance criteria and the red cases, and whether `scrollTop` is judged.
3. Does the C2 A/B result (appended) change anything?

## Appended: the C2 A/B result (`findings/evidence/134/c2-cell-repeat/ab/README.md`, commit `ff13f918`)

**VOID** by ruling-2's rule: the 0.2.16 arm had 0/10 spikes, against 3/10 in the earlier repeat. The 0.2.15 arm had 1/10, with the same signature (key 10 147.9 ms, stall gap 196.6 ms). Rates so far: 0.2.16 4/21, 0.2.15 1/11.

Finding 135 is registered. §15 and the G4 note say the cell is not safely under its gate. No `dist/` swap was made.

Any page change in A or C would mean measuring this cell again on the new page. That raises the question of how to judge a cell whose rate moves between sessions — the same question the owner already has for the next count (ruling-2 condition 7).
