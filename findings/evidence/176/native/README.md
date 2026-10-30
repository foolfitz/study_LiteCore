# Finding 176, engine item C, native arm (fable ruling 2026-10-30 §3.3 step 1)

**Result: `WITNESS-FAILS`** -- the ruling's candidate (the caret paragraph's list state item) is never available to the reply. Judged by `tool/read_cells.py out` (`out/reader-output.json`) against `PREDICTION.md`, which was registered before the harness was compiled; amendment 1 (after the smoke, before this run) added recorded fields only.

**Recorded, not pre-registered:** two synchronous observables answered correctly in every clean round (below). They are inputs for the design decision, not a verdict.

## What was run

- **Harness** `tool/f176_native.cpp`: N1's `oc_native.cpp` (sha 6e6b22d9...) plus four marked additions.
  - Op `F` runs the ordered engine's collapsed-caret format action in one call, in `wasm_sdk_probe/src/ordered_format.inc`'s order: dispatch; RESET/START/RESET at the caret point captured before the dispatch; `.uno:SelectText`; the synchronous selection read; `text/html` if TEXT; RESET/START/RESET; the read again.
  - Op `G` is F without the restore before the select.
  - F and G also record `.uno:Undo` before their first call.
  - Every op records its callback indices, so callbacks split by index (not by clock) into during-the-call, before the first poll (on time) and late.
- **Build**: `build-02/build-receipt.json` (single-file g++, 1.5 s, binary sha a5c15343...; binaries not committed). `build-01` is the smoke's build.
- **Core**: `native-lok-26-8/build/instdir/program`, buildid 671c848b (the N1 core).
- **Mode**: `uni1ai` only (the engine's cadence). 22 cells x 5 rounds, 2026-10-30 03:30-03:48Z, one process each, run-major, `nice -n 10`, fresh profile, `SAL_USE_VCLPLUGIN=svp`, `SAL_LOK_OPTIONS=unipoll`. 110/110 exit 0; load1 <= 2.45 (not a timing measurement: on time vs late is by index).
- **Fixtures**: `tool/make_fixtures.py` (N1's `doc`/`p`/bullet style, imported), `fixtures/SHA256SUMS`. `blank-one.odt` is the host's blank template byte for byte (sha 7e6221b6..., B1's pin).
- **Ground truth**: the saved FODT of every round (`out/<cell>/rN.fodt.gz`), never the callbacks.

## Findings

**1. The state item is late, everywhere (P1 fails 25/25).**
- In every round of every A cell, the saved paragraph is a bullet, and `.uno:DefaultBullet=true` arrives **after** the first poll: 25/25, 298-601 ms after it, median 300 ms. That includes a1, the paragraph with text.
- No `.uno:DefaultBullet` item arrives before the first poll in any cell. The only on-time STATE_CHANGED keys are `.uno:ModifiedStatus` and `.uno:StateWordCount`.
- Nothing is delivered during the call (`nDuring` = 0 in all 110 rounds).
- This is N1b's timer class (SfxBindings' idle timer): the item reaches the engine after the reply has been composed.

**2. P0 holds: the native cells are the browser's cells.**
- a2 and a3 read two blocks (`<ul><li><p></p></li></ul><p>E1-EMPTY-AFTER</p>`).
- a4 and a5 select nothing (selection type NONE: 083/173's `select-text-returned-none`).
- a1 reads one block.

**3. P2 holds: the sham cells say nothing.** n1-n3 get no bullet item at all, and the saved paragraph is not in a list. That includes n2, where the overshoot reaches a bullet.

**4. Recorded: the readback's FIRST block is the dispatch paragraph.**
- The parser's first-block fields (`listTag` = the first structural tag if it is ul/ol, `blockTag` = the first block tag) are what `formatBarrierReadbackSatisfied()` already reads. In every clean round of every cell with a readback, they equal the saved state of the dispatch paragraph:
  - **Multi-block cells (16 cells x 5 rounds):** a2, a3, n1-n3, r1 (bullet on a bulleted empty line), r3 (numbering -> `ol`), r4 (none), r5 (heading -> `h1`), r6 (empty line before a list item: `items=2`), and their G twins.
  - **Single-block cells:** a1 and g-a1.
- By source, `.uno:SelectText` is `FN_SELECT_PARA` (`sw/sdi/swriter.sdi:5649`). The handler is `sw/source/uibase/shells/textsh1.cxx:1975`: `SttPara()` unless already at the start, then `EndPara(true)`.
- `GoCurrPara` (`sw/source/core/crsr/pam.cxx:1238`) moves to the NEXT content node only when the point is already at the paragraph end, which an empty paragraph always is. So the selection starts at the start of the paragraph holding the cursor, and overshoots forward by exactly one paragraph. It never goes upward.
- This bears on 046's B-case counterexample ("overflow upward onto an already-bulleted paragraph"). It answers that only if the cursor is in the dispatch paragraph when the select runs: in F that rests on the geometric restore, in G on the dispatch not moving the cursor.

**5. Recorded: the undo stack is synchronous and dispatch-scoped.**
- Every A cell: exactly one new top action `Number On/Off` at return (a3: on top of its `New Paragraph`).
- The N cells: no change.
- r3: `Number On/Off`; r4: `Delete numbering`; r5: `Apply Styles: Heading 1`.
- r1 (already a bullet): **no change**, finding 030's silent no-op, so the undo stack cannot tell "nothing to do" from "did nothing".
- On the 083 path (a4, a5) the undo stack is the only synchronous observable this run found: there is no readback to read.

**6. Recorded: G = F.** In every cell, the F and G twins have the same readback, first block, undo and saved result, 5/5 each.

## Reader and its red cases

`tool/read_cells.py --self-test out` (`out/self-test.json`, `ALL_AS_EXPECTED`, 12 cases). It builds its cases from this run's own summaries:
- **Verdict reachability.**
  - Every A cell's late items moved on time -> `WITNESS-HOLDS`.
  - Then an on-time `true` in n2 -> `FAILS`.
  - A `false` in a4 -> `HOLDS-MID-ONLY`.
  - a2 saved out of a list -> `FAILS`.
  - One unclean a2 round -> `NOT-ESTABLISHED`.
  - a3 read as one block -> `NOT-ESTABLISHED`.
  - n1 saved in a list -> `FAILS`.
- **The recorded first-block comparison can say "disagrees":** three mutations.
- **A record whose index window does not align is unclean.**

## Not measured here

- WASM. Native unipoll is the method this spec family uses for on-time lists (N1). The product's own reply is measured after a link.
- The product path (page, worker, session disposition). Carets placed by click (all carets here come from keys).
- An empty paragraph followed by another empty paragraph; paragraphs in tables, frames or notes.
- Whether the dispatch can move the cursor to another paragraph for any of the five actions. By source and by G = F here it does not; this is not a proof for every document.
