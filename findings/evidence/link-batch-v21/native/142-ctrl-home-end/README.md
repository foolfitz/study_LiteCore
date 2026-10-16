# Finding 142, native arms: Ctrl+Home / Ctrl+End on the key path (link batch v21, plan step 1a)

Plan: `handoff/PLAN-2026-10-16-link-batch-v21.md` §2.1 and §4 step 1a. Fact sheet: `handoff/link-batch-v21/facts-caret-boundary.md` ITEM 3. Finding: `findings/142-ctrl-home-does-not-move-the-caret.md`.

Question: before the engine gets `move-document-start` / `move-document-end`, what does native Writer do when the engine posts Ctrl+Home / Ctrl+End on the **key path**, from various starting shapes?

Labels used below: **[observed]** = read off the raw files in `out/` (recomputable with `tool/read_results.py`); **[source]** = read in the native source tree at the cited line; **[inferred]** = my reasoning from the two. Nothing here is observed on WASM.

## Summary

All 81 arms ran 3 times, each round a separate process. **Every arm agreed 3/3.** No measured window hit its cap, and every press came after at least 1.5 s of quiet. The positive controls all passed. The reader exits 0: `out/reader-output.txt`.

1. **Ctrl+Home / Ctrl+End from mid-text** moves the caret to the document start or end and emits exactly **one** callback, `INVALIDATE_VISIBLE_CURSOR`. It arrives 0.3–0.9 ms after the post, and nothing follows for at least 2 s. There is no `TEXT_SELECTION` and no `STATE_CHANGED`, and `.uno:Undo` is unchanged. [observed] Across all 252 Ctrl+Home/End presses in every arm, Undo never changed. [observed]
2. **At the boundary already** there is **no callback of any kind** for at least 2 s, which is finding 096's shape. That holds after Down+Up placement, right after load, at the end, and for a second press. [observed]
3. **Tables step, as Writer's source says** (`sw/source/uibase/wrtsh/move.cxx:213-238` for `GoStart`, `:319-323` for `GoEnd`) [source]. [observed]
   - From mid-cell B2, Ctrl+Home goes to the **cell start**, then the **table start** (A1), then the **document start**. A fourth press was not measured.
   - From mid-cell A1, the cell start and the table start coincide, so it is the cell start, then the document start, then silence on the third press.
   - Ctrl+End, from mid-cell A1 and from mid-cell B2 alike, goes to the cell end, then the table end (end of C3), then the document end (end of "After the table").
   - Steps inside the table emit `INVALIDATE_VISIBLE_CURSOR`, plus `RULER_UPDATE`/`STATE_CHANGED` when the cell changes.
   - Leaving the table adds `TABLE_SELECTED` (an empty `{ }`), `CONTEXT_CHANGED`, rulers and about 18 `STATE_CHANGED`. Those arrive up to about 765 ms after the post.
4. **A document that starts with a table.** From body text after the table, Ctrl+Home lands in **A1 at offset 0**, the first position of the document. A second and third press are silent. [observed] So the "document start" here is the first cell, and nothing marks it as different. [inferred]
5. **A document that ends with a table.** Ctrl+End lands in an **empty paragraph after the table**, with one cursor callback; further presses are silent. [observed] That paragraph is in the saved document (`tl-end-*`: 6 → 7 paragraphs, the new empty one after `'B2 last'`) although Undo is empty. The caret landed in it before any save, so it was already in the model after load: Writer added it on import, not on the key. [observed + inferred]
6. **Header / footer** (`.uno:JumpToHeader` / `JumpToFooter`, and an engine click into the header) [observed]:
   - press 1 goes to the header start or footer end;
   - press 2 goes to the **body** document start or end, adding `TAB_STOP_LIST` and rulers;
   - press 3 is silent.

   `move.cxx:277-283` (GoStart), `:335-341` (GoEnd) [source].
7. **Sections** (an extra arm; `GoStart`/`GoEnd` try the current section first, `move.cxx:285-290`, `:344`) [source]: press 1 goes to the **section start/end**, press 2 to the document start/end, press 3 is silent. [observed] Together with items 3 and 6: **one press reaches the document boundary only when the caret is in plain body text outside tables and sections.** Otherwise it takes 2 or 3 presses, and every intermediate press looks like an ordinary move (a cursor callback). [observed]
8. **Ranges collapse.** This holds for a one-paragraph range, a cross-paragraph range, and a backward cross-paragraph range, all made through the engine's text-handles path. [observed]
   - Ctrl+Home emits `TEXT_SELECTION` with an **empty** payload, **then** `INVALIDATE_VISIBLE_CURSOR`, both about 0.5 ms after the post, then `STATE_CHANGED` up to about 300 ms.
   - Afterwards the selection is empty and the caret is at the document start or end, whatever the range's direction.
9. **Finding 142's red sequence natively.** [observed]
   - Mid-text, Ctrl+Home, then Backspace: the Backspace emits **nothing**, Undo is unchanged, and the saved text and paragraph shape equal the fixture.
   - Ctrl+End then Delete: the same.
   - Ctrl+Home then K1 (Shift+Left): **no selection** at +250 ms or at +2250 ms, and no callback for about 4.3 s. Ctrl+End then forward K1 (Shift+Right): the same.
10. **But only when the first paragraph is plain.** With a bulleted or numbered first paragraph, Ctrl+Home lands at the text start after the label. Writer's own Backspace there is `Number On/Off`: the item becomes a `list-header`, and no cursor callback comes. With a first-line indent, Ctrl+Home lands at x = 1985, the indented start; Backspace is `Apply attributes`, the indent goes from 1 cm to 0, and the caret moves to x = 1418. [observed] These are positions 2 and 3 of `specs/SPEC-M3-link-batch.md` §15.1, L-C-number-or-indent. So the red test's "Backspace after Ctrl+Home is a boundary no-op" holds only when the first paragraph has no numbering and no first-line indent. Once `move-document-start` exists, these positions are one key away from anywhere. [inferred]
11. **Surprise: Writer's key handler has no Ctrl+Home case.** [source] The key falls through `SwEditWin::KeyInput` (`edtwin.cxx:2420-2444`) to `SfxViewShell::ExecKey_Impl` (`sfx2/source/view/viewsh.cxx:3203-3251`). There the module accelerator table maps `HOME_MOD1` to **`.uno:GoToStartOfDoc`** and `END_MOD1` to `.uno:GoToEndOfDoc` (`officecfg/.../Accelerators.xcu:6683-6688`, `:6419-6424`, TextDocument module). So the "key path" ends in the same Writer command as the rejected `.uno:` route. [source] The two differ in the engine's bookkeeping (`mutation=false` against the uno-mutation route) and in dispatch timing, not in what Writer does. [inferred]
12. **Surprise: in this threaded native LOK, Ctrl+Home's move is not FIFO with a key that Writer handles itself.** [observed] Put the caret at the start of a numbered *second* paragraph. Then Ctrl+Home followed by Backspace turned P2's numbering off (`Number On/Off`, P2 becomes a list-header), and only then did the caret reach the document start. This happened 3/3 with the keys posted back-to-back and 3/3 with both keys queued from inside a callback. [observed]

    Writer's own Backspace there is `Number On/Off` (control `ctl-bksp-at-num`). A Backspace that ran *after* the move would have hit the plain first paragraph. [observed]

    By source:
    - without unipoll, `AcceleratorExecute::execute` dispatches through `AsyncAccelExec`, a separately posted user event (`svtools/source/misc/acceleratorexecute.cxx:213-226`, `vcl/source/helper/evntpost.cxx:42-46`);
    - Backspace at a numbered paragraph's start is done inside `SwEditWin::KeyInput` itself (`edtwin.cxx:2048-2110`).

    The mid-text Backspace and Delete arms come out ordered: the document is unchanged, both back-to-back and queued. The likely reason is that those keys also go through the accelerator table (`.uno:SwBackspace`), so their dispatches queue in key order. [source + inferred]

    **The WASM engine runs LOK in unipoll mode** (`probe_engine.cpp:6667-6680`, `runLoop` at `:6705`). There, `postEventAsync` runs the key synchronously (`sfx2/source/view/lokhelper.cxx:1283-1287`) and the accelerator dispatches synchronously (`acceleratorexecute.cxx:213-216`). By source, then, this reordering cannot happen on WASM. [source + inferred; not observed]


## How to read the table

- One row per measured press, from round 1. The "runs agree" column is the reader's comparison of all three rounds. It covers:
  - the callback types in order, without `STATE_CHANGED`;
  - whether any `STATE_CHANGED` came;
  - the caret rectangle and the selection after the press;
  - Undo changed and the Undo top;
  - the K1 reads;
  - the locator;
  - the saved text and paragraph shape.

  Timing is not compared; the timing columns are min–max (first callback) and max (last callback) over the three rounds.
- "placed at" and "lands at" name the caret position as `before|after` on its line. The reader learns each position from a locator read at the same rectangle in the same fixture, in this arm, a sibling `-nK` arm or a `place-*` arm. Rectangles are in twips, on this host's fonts.
- `ch` = Ctrl+Home (9220), `ce` = Ctrl+End (9221), `bksp` = 1283, `del` = 1286, `k1` = Shift+Left (5122), `k1r` = Shift+Right (5123).
- In the `q-*` arms "placed at" is the caret **before the trigger key**. The pair is posted after the trigger has moved the caret one step (Right: `Brav|o` → `Bravo|`; Down: P1 start → P2 start).

## Results table (verbatim from `out/reader-output.txt`)

| arm | runs agree | placed at | press | callbacks after the post (STATE_CHANGED omitted; +S = some came) | first cb ms (min-max) | last cb ms (max) | caret moved | caret after | lands at | selection after | Undo changed / top | saved text |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a1-home-mid | 3/3 | «Bravo\| second paragraph» | ch (9220) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.9 | 1 | yes | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no |  |
| a2-end-mid | 3/3 | «Bravo\| second paragraph» | ce (9221) | INVALIDATE_VISIBLE_CURSOR | 0.3-0.4 | 0 | yes | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no |  |
| a3-home-at-start | 3/3 | «\|Alpha first paragraph» | ch (9220) | **none** (silent >= 2008 ms) | none | none | no | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no |  |
| a3-home-after-load | 3/3 | «\|Alpha first paragraph» | ch (9220) | **none** (silent >= 2009 ms) | none | none | no | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no |  |
| a3-end-at-end | 3/3 | «Charlie third paragraph\|» | ce (9221) | **none** (silent >= 2009 ms) | none | none | no | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no |  |
| a3-home-twice | 3/3 | «Bravo\| second paragraph» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.6 | 1 | yes | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no |  |
|  |  |  | ch2 (9220) | **none** (silent >= 2008 ms) | none | none | no | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no |  |
| a3-end-twice | 3/3 | «Bravo\| second paragraph» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.5 | 0 | yes | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no |  |
|  |  |  | ce2 (9221) | **none** (silent >= 2006 ms) | none | none | no | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no |  |
| t-home-A1-n1 | 3/3 | «A1\| text» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.7 | 1 | yes | 1418, 1694, 0, 276 | «\|A1 text» | - | no |  |
| t-home-B2-n1 | 3/3 | «B2\| text» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.6 | 1 | yes | 4630, 1970, 0, 276 | «\|B2 text» | - | no |  |
| t-end-A1-n1 | 3/3 | «A1\| text» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.4 | 0 | yes | 2131, 1694, 0, 276 | «A1 text\|» | - | no |  |
| t-end-B2-n1 | 3/3 | «B2\| text» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.3-0.6 | 1 | yes | 5329, 1970, 0, 276 | «B2 text\|» | - | no |  |
| t-home-A1-n2 | 3/3 | «A1\| text» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.4 | 0 | yes | 1418, 1694, 0, 276 | «\|A1 text» | - | no |  |
|  |  |  | ch2 (9220) | TABLE_SELECTED, CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.6-0.7 | 764 | yes | 1418, 1418, 0, 276 | «\|Before the table» | - | no |  |
| t-home-B2-n2 | 3/3 | «B2\| text» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.4 | 0 | yes | 4630, 1970, 0, 276 | «\|B2 text» | - | no |  |
|  |  |  | ch2 (9220) | INVALIDATE_VISIBLE_CURSOR, RULER_UPDATE +S | 0.5-0.7 | 423 | yes | 1418, 1694, 0, 276 | «\|A1 text» | - | no |  |
| t-end-A1-n2 | 3/3 | «A1\| text» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.6 | 1 | yes | 2131, 1694, 0, 276 | «A1 text\|» | - | no |  |
|  |  |  | ce2 (9221) | INVALIDATE_VISIBLE_CURSOR, RULER_UPDATE +S | 0.4-0.4 | 422 | yes | 8542, 2246, 0, 276 | «C3 text\|» | - | no |  |
| t-end-B2-n2 | 3/3 | «B2\| text» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.7 | 1 | yes | 5329, 1970, 0, 276 | «B2 text\|» | - | no |  |
|  |  |  | ce2 (9221) | INVALIDATE_VISIBLE_CURSOR, RULER_UPDATE +S | 0.4-0.4 | 423 | yes | 8542, 2246, 0, 276 | «C3 text\|» | - | no |  |
| t-home-A1-n3 | 3/3 | «A1\| text» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.7 | 1 | yes | 1418, 1694, 0, 276 | «\|A1 text» | - | no |  |
|  |  |  | ch2 (9220) | TABLE_SELECTED, CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.6-0.9 | 763 | yes | 1418, 1418, 0, 276 | «\|Before the table» | - | no |  |
|  |  |  | ch3 (9220) | **none** (silent >= 2009 ms) | none | none | no | 1418, 1418, 0, 276 | «\|Before the table» | - | no |  |
| t-home-B2-n3 | 3/3 | «B2\| text» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.8 | 1 | yes | 4630, 1970, 0, 276 | «\|B2 text» | - | no |  |
|  |  |  | ch2 (9220) | INVALIDATE_VISIBLE_CURSOR, RULER_UPDATE +S | 0.5-0.8 | 422 | yes | 1418, 1694, 0, 276 | «\|A1 text» | - | no |  |
|  |  |  | ch3 (9220) | TABLE_SELECTED, CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.6-1.0 | 764 | yes | 1418, 1418, 0, 276 | «\|Before the table» | - | no |  |
| t-end-A1-n3 | 3/3 | «A1\| text» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.4 | 0 | yes | 2131, 1694, 0, 276 | «A1 text\|» | - | no |  |
|  |  |  | ce2 (9221) | INVALIDATE_VISIBLE_CURSOR, RULER_UPDATE +S | 0.4-0.7 | 423 | yes | 8542, 2246, 0, 276 | «C3 text\|» | - | no |  |
|  |  |  | ce3 (9221) | TABLE_SELECTED, CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.5-0.5 | 764 | yes | 2803, 2522, 0, 276 | «After the table\|» | - | no |  |
| t-end-B2-n3 | 3/3 | «B2\| text» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.3-0.5 | 0 | yes | 5329, 1970, 0, 276 | «B2 text\|» | - | no |  |
|  |  |  | ce2 (9221) | INVALIDATE_VISIBLE_CURSOR, RULER_UPDATE +S | 0.3-0.7 | 423 | yes | 8542, 2246, 0, 276 | «C3 text\|» | - | no |  |
|  |  |  | ce3 (9221) | TABLE_SELECTED, CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.4-0.8 | 763 | yes | 2803, 2522, 0, 276 | «After the table\|» | - | no |  |
| tf-home-n1 | 3/3 | «Body\| after table» | ch1 (9220) | TABLE_SELECTED, CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.6-0.8 | 724 | yes | 1418, 1418, 0, 276 | «\|A1 first» | - | no |  |
| tl-end-n1 | 3/3 | «Body\| before table» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.3-0.6 | 1 | yes | 1418, 2522, 0, 277 | «(empty paragraph)» | - | no | DIFFERS: paragraph '' inserted after 'B2 last'; shape: 6 -> 7 paragraphs |
| tf-home-n2 | 3/3 | «Body\| after table» | ch1 (9220) | TABLE_SELECTED, CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.6-0.8 | 723 | yes | 1418, 1418, 0, 276 | «\|A1 first» | - | no |  |
|  |  |  | ch2 (9220) | **none** (silent >= 2008 ms) | none | none | no | 1418, 1418, 0, 276 | «\|A1 first» | - | no |  |
| tl-end-n2 | 3/3 | «Body\| before table» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.6 | 1 | yes | 1418, 2522, 0, 277 | «(empty paragraph)» | - | no |  |
|  |  |  | ce2 (9221) | **none** (silent >= 2007 ms) | none | none | no | 1418, 2522, 0, 277 | «(empty paragraph)» | - | no | DIFFERS: paragraph '' inserted after 'B2 last'; shape: 6 -> 7 paragraphs |
| tf-home-n3 | 3/3 | «Body\| after table» | ch1 (9220) | TABLE_SELECTED, CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.6-0.9 | 724 | yes | 1418, 1418, 0, 276 | «\|A1 first» | - | no |  |
|  |  |  | ch2 (9220) | **none** (silent >= 2007 ms) | none | none | no | 1418, 1418, 0, 276 | «\|A1 first» | - | no |  |
|  |  |  | ch3 (9220) | **none** (silent >= 2006 ms) | none | none | no | 1418, 1418, 0, 276 | «\|A1 first» | - | no |  |
| tl-end-n3 | 3/3 | «Body\| before table» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.7 | 1 | yes | 1418, 2522, 0, 277 | «(empty paragraph)» | - | no |  |
|  |  |  | ce2 (9221) | **none** (silent >= 2007 ms) | none | none | no | 1418, 2522, 0, 277 | «(empty paragraph)» | - | no |  |
|  |  |  | ce3 (9221) | **none** (silent >= 2007 ms) | none | none | no | 1418, 2522, 0, 277 | «(empty paragraph)» | - | no | DIFFERS: paragraph '' inserted after 'B2 last'; shape: 6 -> 7 paragraphs |
| r-one-home | 3/3 | range 'second' | ch (9220) | TEXT_SELECTION, INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.7 | 301 | yes | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no |  |
| r-one-end | 3/3 | range 'second' | ce (9221) | TEXT_SELECTION, INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.6 | 301 | yes | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no |  |
| r-cross-home | 3/3 | range 'second paragraph\nCharlie' | ch (9220) | TEXT_SELECTION, INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.6 | 301 | yes | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no |  |
| r-cross-end | 3/3 | range 'second paragraph\nCharlie' | ce (9221) | TEXT_SELECTION, INVALIDATE_VISIBLE_CURSOR +S | 0.4-0.5 | 301 | yes | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no |  |
| r-bwd-home | 3/3 | range 'second paragraph\nCharlie' | ch (9220) | TEXT_SELECTION, INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.6 | 301 | yes | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no |  |
| r-bwd-end | 3/3 | range 'second paragraph\nCharlie' | ce (9221) | TEXT_SELECTION, INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.6 | 301 | yes | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no |  |
| hf-home-hdr-n1 | 3/3 | «Header\| line text» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.5 | 0 | yes | 1418, 1418, 0, 276 | «\|Header line text» | - | no |  |
| hf-end-ftr-n1 | 3/3 | «Footer\| line text» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.5 | 0 | yes | 2884, 15712, 0, 276 | «Footer line text\|» | - | no |  |
| hf-home-hdr-n2 | 3/3 | «Header\| line text» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.5 | 1 | yes | 1418, 1418, 0, 276 | «\|Header line text» | - | no |  |
|  |  |  | ch2 (9220) | INVALIDATE_VISIBLE_CURSOR, TAB_STOP_LIST, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.5-0.5 | 463 | yes | 1418, 1921, 0, 276 | «\|Alpha first paragraph» | - | no |  |
| hf-end-ftr-n2 | 3/3 | «Footer\| line text» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.5 | 0 | yes | 2884, 15712, 0, 276 | «Footer line text\|» | - | no |  |
|  |  |  | ce2 (9221) | INVALIDATE_VISIBLE_CURSOR, TAB_STOP_LIST, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.3-0.4 | 463 | yes | 3657, 2473, 0, 276 | «Charlie third paragraph\|» | - | no |  |
| hf-home-hdr-n3 | 3/3 | «Header\| line text» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.5 | 0 | yes | 1418, 1418, 0, 276 | «\|Header line text» | - | no |  |
|  |  |  | ch2 (9220) | INVALIDATE_VISIBLE_CURSOR, TAB_STOP_LIST, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.5-0.5 | 463 | yes | 1418, 1921, 0, 276 | «\|Alpha first paragraph» | - | no |  |
|  |  |  | ch3 (9220) | **none** (silent >= 2006 ms) | none | none | no | 1418, 1921, 0, 276 | «\|Alpha first paragraph» | - | no |  |
| hf-end-ftr-n3 | 3/3 | «Footer\| line text» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.5 | 0 | yes | 2884, 15712, 0, 276 | «Footer line text\|» | - | no |  |
|  |  |  | ce2 (9221) | INVALIDATE_VISIBLE_CURSOR, TAB_STOP_LIST, VERTICAL_RULER_UPDATE, RULER_UPDATE +S | 0.3-0.6 | 463 | yes | 3657, 2473, 0, 276 | «Charlie third paragraph\|» | - | no |  |
|  |  |  | ce3 (9221) | **none** (silent >= 2007 ms) | none | none | no | 3657, 2473, 0, 276 | «Charlie third paragraph\|» | - | no |  |
| hf-home-hdr-click | 3/3 | «Header\| line text» | ch (9220) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.9 | 1 | yes | 1418, 1418, 0, 276 | «\|Header line text» | - | no |  |
| sec-home-n1 | 3/3 | «Inside\| section two» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.7 | 1 | yes | 1418, 1694, 0, 276 | «\|Inside section one» | - | no |  |
| sec-end-n1 | 3/3 | «Inside\| section one» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.7 | 1 | yes | 3164, 1970, 0, 276 | «Inside section two\|» | - | no |  |
| sec-home-n2 | 3/3 | «Inside\| section two» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.8 | 1 | yes | 1418, 1694, 0, 276 | «\|Inside section one» | - | no |  |
|  |  |  | ch2 (9220) | INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.6 | 322 | yes | 1418, 1418, 0, 276 | «\|Before the section» | - | no |  |
| sec-end-n2 | 3/3 | «Inside\| section one» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.7 | 1 | yes | 3164, 1970, 0, 276 | «Inside section two\|» | - | no |  |
|  |  |  | ce2 (9221) | INVALIDATE_VISIBLE_CURSOR +S | 0.4-0.4 | 322 | yes | 3017, 2246, 0, 276 | «After the section\|» | - | no |  |
| sec-home-n3 | 3/3 | «Inside\| section two» | ch1 (9220) | INVALIDATE_VISIBLE_CURSOR | 0.5-1.1 | 1 | yes | 1418, 1694, 0, 276 | «\|Inside section one» | - | no |  |
|  |  |  | ch2 (9220) | INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.8 | 322 | yes | 1418, 1418, 0, 276 | «\|Before the section» | - | no |  |
|  |  |  | ch3 (9220) | **none** (silent >= 2009 ms) | none | none | no | 1418, 1418, 0, 276 | «\|Before the section» | - | no |  |
| sec-end-n3 | 3/3 | «Inside\| section one» | ce1 (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.6 | 1 | yes | 3164, 1970, 0, 276 | «Inside section two\|» | - | no |  |
|  |  |  | ce2 (9221) | INVALIDATE_VISIBLE_CURSOR +S | 0.3-0.4 | 322 | yes | 3017, 2246, 0, 276 | «After the section\|» | - | no |  |
|  |  |  | ce3 (9221) | **none** (silent >= 2010 ms) | none | none | no | 3017, 2246, 0, 276 | «After the section\|» | - | no |  |
| red-home-bksp | 3/3 | «Bravo\| second paragraph» | ch (9220) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.5 | 1 | yes | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no |  |
|  |  |  | bksp (1283) | **none** (silent >= 2009 ms) | none | none | no | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no | same; shape: as fixture |
| red-end-del | 3/3 | «Bravo\| second paragraph» | ce (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.4 | 0 | yes | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no |  |
|  |  |  | del (1286) | **none** (silent >= 2007 ms) | none | none | no | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no | same; shape: as fixture |
| red-home-k1 | 3/3 | «Bravo\| second paragraph» | ch (9220) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.6 | 1 | yes | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no |  |
|  |  |  | k1 (5122) | **none** (silent >= 4261 ms) | none | none | no | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | +250: ''; +2250: '' | no |  |
| red-end-k1r | 3/3 | «Bravo\| second paragraph» | ce (9221) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.7 | 1 | yes | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no |  |
|  |  |  | k1r (5123) | **none** (silent >= 4259 ms) | none | none | no | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | +250: ''; +2250: '' | no |  |
| b2b-home-bksp | 3/3 | «Bravo\| second paragraph» | ch+bksp (9220+1283) | INVALIDATE_VISIBLE_CURSOR | 0.6-0.8 | 1 | yes | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no | same; shape: as fixture |
| b2b-end-del | 3/3 | «Bravo\| second paragraph» | ce+del (9221+1286) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.5 | 1 | yes | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no | same; shape: as fixture |
| ctl-home | 3/3 | «Bravo\| second paragraph» | home (1028) | INVALIDATE_VISIBLE_CURSOR | 0.4-0.7 | 1 | yes | 1418, 1694, 0, 276 | «\|Bravo second paragraph» | - | no |  |
| ctl-down | 3/3 | «Bravo\| second paragraph» | down (1024) | INVALIDATE_VISIBLE_CURSOR | 0.5-0.5 | 0 | yes | 2017, 1970, 0, 276 | «Charli\|e third paragraph» | - | no |  |
| ctl-bksp | 3/3 | «Bravo\| second paragraph» | bksp (1283) | INVALIDATE_VISIBLE_CURSOR +S | 0.8-0.8 | 623 | yes | 1884, 1694, 0, 276 | «Brav\| second paragraph» | - | yes / Delete “o” | DIFFERS: 'Bravo second paragraph' -> 'Brav second paragraph'; shape: as fixture |
| ctl-k1 | 3/3 | «Bravo\| second paragraph» | k1 (5122) | TEXT_SELECTION_START, TEXT_SELECTION_END, TEXT_SELECTION, INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.7 | 322 | yes | 1884, 1694, 0, 276 | (range) | +250: 'o'; +2250: 'o' | no |  |
| ctl-k1r | 3/3 | «Bravo\| second paragraph» | k1r (5123) | TEXT_SELECTION_START, TEXT_SELECTION_END, TEXT_SELECTION, INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.8 | 322 | yes | 2064, 1694, 0, 276 | (range) | +250: ' '; +2250: ' ' | no |  |
| x-bullet-home-bksp | 3/3 | «Be\|ta two» | ch (9220) | CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, RULER_UPDATE +S | 0.6-0.6 | 765 | yes | 2138, 1418, 0, 276 | «\|Alpha one» | - | no |  |
|  |  |  | bksp (1283) | (none) +S | 0.7-1.0 | 302 | no | 2138, 1418, 0, 276 | «\|Alpha one» | - | yes / Number On/Off | same; shape: P1 list-item, text-indent none -> list-header, text-indent none |
| x-numbered-home-bksp | 3/3 | «Pla\|in second» | ch (9220) | CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, RULER_UPDATE +S | 0.5-1.1 | 764 | yes | 2138, 1418, 0, 276 | «\|Numbered first» | - | no |  |
|  |  |  | bksp (1283) | (none) +S | 0.6-0.6 | 322 | no | 2138, 1418, 0, 276 | «\|Numbered first» | - | yes / Number On/Off | same; shape: P1 list-item, text-indent none -> list-header, text-indent none |
| x-indent-home-bksp | 3/3 | «Sec\|ond» | ch (9220) | INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.8 | 322 | yes | 1985, 1418, 0, 276 | «\|Indented first» | - | no |  |
|  |  |  | bksp (1283) | INVALIDATE_VISIBLE_CURSOR +S | 0.6-0.7 | 322 | yes | 1418, 1418, 0, 276 | «\|Indented first» | - | yes / Apply attributes | same; shape: P1 none, text-indent 1cm -> none, text-indent 0in |
| x-indent-home | 3/3 | «Sec\|ond» | ch (9220) | INVALIDATE_VISIBLE_CURSOR +S | 0.5-0.8 | 322 | yes | 1985, 1418, 0, 276 | «\|Indented first» | - | no |  |
| q-home-bksp | 3/3 | «Brav\| second paragraph» | ch+bksp (9220+1283) | INVALIDATE_VISIBLE_CURSOR | 0.3-0.4 | 0 | yes | 1418, 1418, 0, 276 | «\|Alpha first paragraph» | - | no | same; shape: as fixture |
| q-end-del | 3/3 | «Brav\| second paragraph» | ce+del (9221+1286) | INVALIDATE_VISIBLE_CURSOR | 0.2-0.3 | 0 | yes | 3657, 1970, 0, 276 | «Charlie third paragraph\|» | - | no | same; shape: as fixture |
| q-ctl-home-bksp | 3/3 | «Brav\| second paragraph» | home+bksp (1028+1283) | INVALIDATE_VISIBLE_CURSOR +S | 0.6-0.8 | 623 | yes | 3470, 1418, 0, 276 | «Alpha first paragraph\|Bravo second paragraph» | - | yes / Delete paragraph | DIFFERS: 'Alpha first paragraph' / 'Bravo second paragraph' -> 'Alpha first paragraphBravo second paragraph'; shape: 3 -> 2 paragraphs |
| ctl-bksp-at-num | 3/3 | «\|Numbered second» | bksp (1283) | (none) +S | 0.6-0.7 | 322 | no | 2138, 1694, 0, 276 | «\|Numbered second» | - | yes / Number On/Off | same; shape: P2 list-item, text-indent none -> list-header, text-indent none |
| b2b-home-bksp-at-num | 3/3 | «\|Numbered second» | ch+bksp (9220+1283) | CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR, RULER_UPDATE +S | 1.1-1.2 | 764 | yes | 1418, 1418, 0, 276 | «\|Plain first» | - | yes / Number On/Off | same; shape: P2 list-item, text-indent none -> list-header, text-indent none |
| q-home-bksp-at-num | 3/3 | «\|Plain first» | ch+bksp (9220+1283) | CONTEXT_CHANGED, INVALIDATE_VISIBLE_CURSOR +S | 1.2-1.6 | 603 | no | 1418, 1418, 0, 276 | «\|Plain first» | - | yes / Number On/Off | same; shape: P2 list-item, text-indent none -> list-header, text-indent none |

Placement checks (group P): caret after placement, and the locator there

- `place-plain3-mid` (3/3): caret ['2004, 1694, 0, 276'], locator ['Bravo| second paragraph']
- `place-plain3-start` (3/3): caret ['1418, 1418, 0, 276'], locator ['|Alpha first paragraph']
- `place-plain3-end` (3/3): caret ['3657, 1970, 0, 276'], locator ['Charlie third paragraph|']
- `place-table-A1` (3/3): caret ['1711, 1694, 0, 276'], locator ['A1| text']
- `place-table-B2` (3/3): caret ['4910, 1970, 0, 276'], locator ['B2| text']
- `place-tf-body` (3/3): caret ['1938, 1970, 0, 276'], locator ['Body| after table']
- `place-tl-body` (3/3): caret ['1938, 1694, 0, 276'], locator ['Body| before table']
- `place-hdr` (3/3): caret ['2110, 1418, 0, 276'], locator ['Header| line text']
- `place-ftr` (3/3): caret ['2044, 15712, 0, 276'], locator ['Footer| line text']
- `place-hdr-click` (3/3): caret ['2110, 1418, 0, 276'], locator ['Header| line text']
- `place-sec-two` (3/3): caret ['2004, 1970, 0, 276'], locator ['Inside| section two']
- `place-sec-one` (3/3): caret ['2004, 1694, 0, 276'], locator ['Inside| section one']
- `place-bullet` (3/3): caret ['1684, 1694, 0, 276'], locator ['Be|ta two']
- `place-numbered` (3/3): caret ['1724, 1694, 0, 276'], locator ['Pla|in second']
- `place-indent` (3/3): caret ['1764, 1694, 0, 276'], locator ['Sec|ond']
- `place-numsecond` (3/3): caret ['2138, 1694, 0, 276'], locator ['|Numbered second']

## Positive controls (arm 9 and the discriminator)

Each must hold in all three rounds, or the reader exits red. All hold. [observed]

- `ctl-home` (plain Home from mid-text) and `ctl-down` (plain Down): one `INVALIDATE_VISIBLE_CURSOR`, about 0.5 ms after the post, and the caret moved. So a moving key does produce a visible callback in this probe, and the silent rows above are not a dead probe.
- `ctl-bksp` (plain Backspace from mid-text): Undo `Delete “o”`, and the saved text is `'Bravo second paragraph' -> 'Brav second paragraph'`. So the saved-text comparison does go red when a key deletes. Arm 8's "same" is a reading, not a comparison that cannot fail.
- `ctl-k1`, `ctl-k1r` (K1 from mid-text): `'o'` and `' '` are selected at +250 ms and +2250 ms. So the "no selection" readings in `red-home-k1` / `red-end-k1r` are not a K1 that never runs.
- `ctl-bksp-at-num` (Backspace at the start of the numbered P2): `Number On/Off`, with P2 going from `list-item` to `list-header`. This is what lets `b2b-home-bksp-at-num` / `q-home-bksp-at-num` tell "Backspace before the move" from "Backspace after the move".
- `q-ctl-home-bksp` (plain Home and Backspace, queued the same way as the Q arms): the paragraphs merge (`Delete paragraph`, 3 → 2 paragraphs). So both queued keys do run, in order, and the Q mechanism is not a no-op.

## The back-to-back and queued-pair arms

`B` posts the two keys a few microseconds apart. In threaded LOK the main thread may process the first key in between, so a FIFO-looking result from `B` alone proves nothing.

`Q` (`tool/f142_native_queued_pair.cpp`) arms a trigger and posts the pair from inside the trigger's `INVALIDATE_VISIBLE_CURSOR` callback. The callback runs on the LOK main thread during the callback flush, so both keys are queued before core handles either. `fired: true` in 3/3 for every `Q` arm. [observed] The claim that both are queued is [inferred]; `q-ctl-home-bksp` shows both keys ran.

`Q` is the main probe plus one step and its callback hook (diff the two sources). It has its own binary, sha256 `50182bda…9e2a`.

| arm | where the caret is when the pair is handled | result (3/3) |
|---|---|---|
| `b2b-home-bksp`, `q-home-bksp` | mid-text `Bravo\|` | document unchanged, caret at the document start: the Backspace ran after the move |
| `b2b-end-del`, `q-end-del` | mid-text `Bravo\|` | document unchanged, caret at the document end |
| `b2b-home-bksp-at-num`, `q-home-bksp-at-num` | start of the numbered P2 | **P2 `Number On/Off`**, then the caret at the document start: **the Backspace ran before the move** |

The mid-text rows alone would have suggested "ordered". The at-num rows show the order depends on which keys Writer dispatches through the accelerator table. See summary item 12 for the source reading and for why this does not carry over to a unipoll host.

## The reader, and its red case

`tool/read_results.py out fixtures` recomputes everything above from the raw files. It goes red (exit 1) when:

- a run is missing or incomplete;
- an arm's rounds disagree;
- a window was capped, or a press had less than 1.5 s of quiet before it;
- an `-nN` family is inconsistent;
- a positive control fails;
- two arms' locators disagree about the same rectangle.

It was made to go red once. `tool/break_one_for_red_demo.py` changed `a1-home-mid/r2.jsonl` in a scratch copy of `out/` so the Ctrl+Home lands at `1418, 1694` instead of `1418, 1418`. The reader exited 1 with two independent reasons: the runs disagree (2/3), and a locator disagrees about `1418, 1694`. On the unbroken `out/` it exits 0. Transcript: `out/reader-red-demo.txt`.

## What this does NOT show

- **Nothing about WASM.** This is native LOK 26.8 running **threaded** (no `runLoop`, so `vcl::lok::isUnipoll()` is false). The WASM engine runs **unipoll** by source (`probe_engine.cpp:6667-6680`, `:6705`).
  - Under unipoll, by source, a posted key runs synchronously inside `postKeyEvent`, and so does its accelerator dispatch (summary item 12).
  - So the timings here (first callback 0.2–1.6 ms; rulers and `STATE_CHANGED` up to about 765 ms) and the ordering results of the `B`/`Q` arms do not transfer.
  - The set and order of callback types *may* transfer, since the same Writer code runs. That is [inferred] and unmeasured.
- **The engine is not exercised:** no first-callback completion rule, no 250 ms readback, no revision guard. This records what core emits. On a range, `TEXT_SELECTION` (empty) arrives before the cursor callback, at most 0.005 ms apart. Whether a completion on the first of them reads back the new caret is not measured here.
- **Geometry is this host's.** Rectangles use the host's fonts, and the WASM image's fonts differ (finding 113).
- **Shapes not tried:**
  - footnotes, endnotes, frames, text boxes and shapes (the FLY branches of `GoStart`/`GoEnd`);
  - nested tables, a table inside a section, a document that starts with a section;
  - an empty document, or one that is only a table;
  - empty cells (`GoStart`'s cell step fails on an empty cell, by source);
  - a multi-page document, where Ctrl+End across pages may add page or scroll callbacks;
  - first-page or left/right headers, and a footer reached by a click;
  - hidden text at the start (review 6's `hidden-start`), tracked changes, RTL or CJK text, read-only sections, comments, fields;
  - an IME composition in progress, and more than one view.
- **Range shapes:** only ranges made by the text-handles path, which is what `select_range` uses. Mouse-drag and keyboard-made ranges were not tried.
- **Ordering beyond keys:** whether a synchronous LOK call (`paste`, `setTextSelection`, `postUnoCommand`) made while Ctrl+Home's dispatch is still pending is reordered. Only key-after-key was tried.
- **Mutations without Undo:** Undo is read through `getCommandValues(".uno:Undo")`, so a change that leaves no Undo action would be invisible to it. Only the arms that save (`red-*`, `b2b-*`, `q-*`, `ctl-bksp*`, `x-*-bksp`, `tl-end-*`) also compare the saved text and paragraph shape.
- **"Silent" is bounded:** it means no callback within a 2,000 ms quiet window (about 4.3 s for K1 arms). A callback later than that would be missed. None arrived later than about 765 ms in any arm that had callbacks.

## Files

- `tool/f142_native_ctrl_home_end.cpp`: the probe. Sha256 `6804626f…1fc53`, the source of binary `5219e704…4736`. All arms except `q-*` used it.
- `tool/f142_native_queued_pair.cpp`: the `Q` variant, binary `50182bda…9e2a`.
- `tool/make_fixtures.py`: the fixtures, except `bullet` and `indent` (see above).
- `tool/run_arms.py`: the runner and the arm table.
  - The main run (73 arms x 3, 02:25–03:27 UTC) used it before four arms were appended (`x-indent-home`, `q-home-bksp`, `q-end-del`, `q-ctl-home-bksp`).
  - Another four were appended after those read FIFO (`place-numsecond`, `ctl-bksp-at-num`, `b2b-home-bksp-at-num`, `q-home-bksp-at-num`), together with the `numbered-second` fixture.
  - No definition of an earlier arm changed. Checked against a copy of the main run's `arms.json`: zero changed definitions, apart from the added `tool` field.
- `tool/read_results.py`: the reader. `tool/break_one_for_red_demo.py`: the red case.
- `fixtures/*.fodt`: the inputs.
- `out/<arm>/r<N>.jsonl`: raw output, one JSON line per record (`env`, `load`, `setup`, `point`, `press`, `locate`, `saved`, `done`).
- `out/<arm>/r<N>.stderr`: SAL warnings, all routine. The counts are below.
- `out/<arm>/r<N>.fodt.gz`: the saved document, for arms that save.
- `out/arms.json`, `out/run-log.jsonl` (one line per process: start, seconds, exit, load average, command), `out/environment.txt`.
- `out/reader-output.txt`, `out/reader-red-demo.txt`.
- `SHA256SUMS`: every file here except itself.

stderr, all 243 processes: no crash and no error line [observed]. The warnings are:

- `no explicit viewshell set` x972;
- `Flavor text/plain;charset=utf-16 is not supported` x825, apparently the selection read with nothing selected [inferred];
- one each per process: `SvxTabStopItem expected`, `OpenCL driver check failed`, two `MsLangId … not configured yet`, and `error removing directory …/extensions` in the fresh profile;
- `Found unknown auto SwNumRule during reset!` x48, in the list fixtures.

## What was run

### Engine

- Install: `native-lok-26-8/build/instdir/program`, the one the repo's earlier native harnesses use (`wasm_sdk_probe/tools/run_f096_native_dedup.sh:9`, `run_link_native_extend_signatures.sh:15`, `run_merge_native.sh:17`).
- Its source tree is `native-lok-26-8/src` (`SRC_ROOT` in `native-lok-26-8/build/config_host.mk`), git HEAD `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`. That equals the install's own `buildid` in `program/versionrc`. The headers used to compile are `libreoffice-26-8/include`, same HEAD.
- **This is a merged-library build.** `program/libsofficeapp.so` is a 21-byte stub whose content is `invalid - merged lib`; its sha256 is `9ad35464…1947c`. The code is in `program/libmergedlo.so`, 159,097,704 bytes, sha256 `2d49c9ff845d3e2cd3fb5d109ea95e9ce01bf45f2925e9a1ed2176eaedd3f924`. [observed] The sha256 that `findings/evidence/new-document/probe-1-native-defaults/README.md` gives for `libsofficeapp.so` (`9ad35464…`) is the stub's, and the git HEAD it gives (`96dd0fce…`) is not an object in `native-lok-26-8/src`. Neither changes that README's results; noted so nobody takes `9ad35464…` as the engine's identity.
- Configure flags: `out/environment.txt` (`--disable-debug --enable-sal-log --with-lang=en-US --without-fonts …`).

### Environment (each process)

- `SAL_USE_VCLPLUGIN=svp` (set by the runner). `SAL_LOK_OPTIONS` removed, so LOK runs **threaded, not unipoll** (see "What this does NOT show"). `LANG=zh_TW.UTF-8`, `LANGUAGE` empty, `LC_ALL` and `SAL_LOG` unset, all inherited. Every JSONL's first line records these again.
- `nice -n 10`, one process at a time, a fresh empty user profile per process, and the process's own copy of the fixture. Rounds are run-major: round 1 of every arm, then round 2, then round 3.
- Every fixture sets its own page layout (A4, 2 cm margins), so the host locale does not change the geometry.
- Full record: `out/environment.txt`. Per-process start time, duration, exit code and load average: `out/run-log.jsonl`.

### The probe

`tool/f142_native_ctrl_home_end.cpp` is one file. It started from `findings/evidence/link-batch/review/review-6-artifacts/native/k1probe.cpp` (placement steps, Undo read, fodt save) and `wasm_sdk_probe/tools/link_native_extend_signatures.cpp` (callback recording, the engine's click and text-handles calls). It was compiled with the repo's native recipe (`wasm_sdk_probe/Makefile:2710`):

```
g++ -std=c++17 -O2 -Wall -I libreoffice-26-8/include tool/f142_native_ctrl_home_end.cpp -ldl -lpthread -o f142-native
```

The binary (sha256 `5219e704…4736`) lives only in the session scratchpad.

**Key shape.** Keys are posted exactly as `wasm_sdk_probe/src/probe_engine.cpp` posts a key-path action: `postKeyEvent(KEYINPUT, 0, code)` then `postKeyEvent(KEYUP, 0, code)` (`:5740-5743`). Here `code` is the `css::awt::Key` value OR'd with the modifier bits: Mod1 = `0x2000` (`:1094`), Shift = `0x1000` (`:1091`). Select-all is `Key::A | EditorMod1Modifier` (`:5691`), so:

- Ctrl+Home = `1028 | 0x2000` = **9220**;
- Ctrl+End = `1029 | 0x2000` = **9221**;
- the user's Backspace and Delete are 1283 and 1286, posted the same way as `postMergeKeyEvents` (`:3757-3762`);
- K1 is Shift+Left (5122) or Shift+Right (5123), as the barrier posts it (`:4236-4246`).

**Placement.** Carets are placed with plain keys: Down, Right, Home, End (plain Up only in `a3-home-at-start`). Ranges are made through the engine's **text-handles** path: `setTextSelection` RESET and START at point A, then END at point B. That is the path `oxsdk_editor_select_range` uses (`editor_api.cpp:219-222` → `probe_engine.cpp:5810-5853`). Points A and B are caret rectangles recorded on the way, as `link_native_extend_signatures.cpp` does. The header arm `hf-home-hdr-click` reaches the header with the engine's click (`postMouseEvent` DOWN+UP, count 1, button 1). Its target point is the header caret found by `.uno:JumpToHeader`. The click on the body comes first, so the arm proves that the click moves the caret into the header. The other header and footer arms use `.uno:JumpToHeader` / `.uno:JumpToFooter`.

**What a measured press records.** The probe first waits for 1.5 s with no callbacks. It then reads:

- the selection, with `getSelectionTypeAndText`;
- the last `INVALIDATE_VISIBLE_CURSOR` and `TEXT_SELECTION` payloads;
- `getCommandValues(".uno:Undo")`.

Then it posts the key or keys. It records **every** callback that follows: type, payload up to 600 bytes, and ms since the first post. It stops after 2,000 ms with no callback (cap 15 s), reads the same four things again, and prints one JSON line.

`quietAfterLastMs` is the window's length after the last callback. For a press with no callbacks it is the whole window.

After all measured presses comes the **locator**: Shift+End and read the selection, then Shift+Home and read it again. That gives the text after and before the caret on its line. The paragraph texts are short and unique, so this names the paragraph and the offset. Because the locator changes the selection, it always comes last. The landing point after an earlier press is therefore read from a sibling arm with fewer presses (`-n1`, `-n2`). The reader checks that the rectangles agree.

**Back-to-back (`B`).** The two keys are posted with no wait between them, each as KEYINPUT+KEYUP.

**Queued pair (`Q`, separate source).** The pair is posted from inside a callback; see "The queued-pair arms" below.

### Fixtures

`tool/make_fixtures.py` writes the flat-ODT fixtures in `fixtures/`:

- `plain3`: three paragraphs;
- `table-mid`: text, a 3x3 table, text;
- `table-first` and `table-last`: a document that starts or ends with a 2x2 table;
- `header-footer`;
- `section-mid`;
- `numbered-first`;
- `numbered-second`, added for the discriminator arms.

`bullet.fodt` and `indent.fodt` are byte-for-byte the output of review 6's generator, `findings/evidence/link-batch/review/review-6-artifacts/native/make_fixtures.py`. Its sha256 `a60b5818…` matches review 6's appendix B. Hashes are in `SHA256SUMS`.

### Commands

```
python3 -I tool/make_fixtures.py fixtures
python3 -I findings/evidence/link-batch/review/review-6-artifacts/native/make_fixtures.py <tmp>   # then copy bullet.fodt, indent.fodt
python3 -I tool/run_arms.py --binary <scratch>/f142-native --install native-lok-26-8/build/instdir/program \
    --fixtures fixtures --out out --work <scratch>/work --runs 3
# second invocation (appended arms; the queued-pair binary is built from tool/f142_native_queued_pair.cpp the same way)
python3 -I tool/run_arms.py --binary <scratch>/f142-native --binary-queued <scratch>/f142-native-queued \
    --install native-lok-26-8/build/instdir/program --fixtures fixtures --out out --work <scratch>/work --runs 3 \
    --only q-home-bksp,q-end-del,q-ctl-home-bksp,x-indent-home
# third invocation (the discriminator, after the second read FIFO; fixture numbered-second added to make_fixtures.py)
python3 -I tool/run_arms.py ... --only place-numsecond,ctl-bksp-at-num,b2b-home-bksp-at-num,q-home-bksp-at-num
python3 -I tool/read_results.py out fixtures > out/reader-output.txt
```

The arm table, each arm's script and a one-line note are in `tool/run_arms.py`, and in `out/arms.json` as the reader reads it.

## Note added by the main session (2026-10-16, after the run)

The Markdown native arms ran on the same machine during this run. Their runner waited for idle, but this runner did not wait, so 24 of the Markdown processes overlapped processes of this run. The list is in `../markdown-paste/out/overlap-with-142.txt`. The language arms (10:15–10:23) overlapped too.

- **Not affected:** what this README states about **which** callbacks arrive and in **what order**, where the caret lands, and whether Undo or the saved text changed. These are behaviour, and every arm agreed 3/3.
- **To be read with this caveat:** the millisecond columns (first and last callback, quiet time). No criterion in `specs/SPEC-M3-link-batch-v21.md` uses them.
