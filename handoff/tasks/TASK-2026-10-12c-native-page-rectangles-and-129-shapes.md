# Task 2026-10-12c — native: page rectangles (link batch) and finding 129's selection shapes

Written by the main session before any run. The predictions below were written before the tools existed; copy them verbatim into each README's "Prediction" section BEFORE the first run, and do not edit them afterwards (a miss is recorded as a miss).

## Ground rules

- **Native only.** No browser runs, no ddev, no WASM. The main session runs browser timing measurements on this machine after you finish; say clearly in your report when your last native run ended.
- **No product bytes.** Do not modify anything under `wasm_sdk_probe/web/`, `wasm_sdk_probe/dist/`, `wasm_sdk_probe/editor-shell*/`, `wasm_sdk_probe/sdk/`, `wasm_sdk_probe/src/`, `wasm_sdk_probe/input/`, or the host repo `~/Projects/Nextcloud_Apps/`. Do not run `make` in `wasm_sdk_probe/` (engine and profile builds are not yours). The native install `native-lok-26-8/build/instdir` is read-only; `SAL_USE_VCLPLUGIN=svp`.
- **Do not commit.** Leave your new files in the tree (they are tracked paths: `wasm_sdk_probe/tools/`, `wasm_sdk_probe/test-docs/`, `findings/evidence/`). The main session reads and commits them.
- **English** for everything you write (tools, READMEs).
- Pattern to follow: `wasm_sdk_probe/tools/f129_native_arrow_on_selection.cpp` (how it initialises LOK, loads a fixture, waits for callbacks, makes a selection with Shift+Right, types `#`, reads the text with SelectAll + getTextSelection) and its evidence `findings/evidence/129/README.md`, `findings/evidence/129/native/round-20261012T020528Z/`. Find how it was compiled (sibling native tools in `wasm_sdk_probe/tools/*.cpp` carry build lines in their headers or READMEs under `findings/evidence/`); record the exact build command in each README.
- **Report only what raw output shows.** Every number in a README must be traceable to a raw file committed next to it (jsonl / txt). If something is inferred, label it "inferred". If an instrument fault is found, keep the faulty round in a folder suffixed `-instrument-fault` and say what was wrong (the 129 P1 round is the precedent).
- Hash the inputs (`sha256sum` of fixtures, documents, tool sources) into an `inputs.sha256` per round.

## Part N1 — `getPartPageRectangles` (link batch item 2, `handoff/PLAN-2026-10-12-link-batch-shift-selection-and-page-number.md`)

Tool: `wasm_sdk_probe/tools/native_page_rectangles.cpp`. Evidence: `findings/evidence/link-batch/page-rectangles/round-<UTC stamp>/` + `findings/evidence/link-batch/page-rectangles/README.md`.

Documents:
1. The owner's document `wasm_sdk_probe/build/scratch-m3-production-ui/PMPC指南.odt` (gitignored: never copy it into the tree; record its sha256 only; record no text from it).
2. A 60-page document from `wasm_sdk_probe/tools/create_long_document.py --pages 60 --out <scratch path>` (record the command and the output's sha256; do not commit the output).

For each document, after load and after layout settles (wait for callbacks to go quiet):
- Call `getPartPageRectangles()` and store the raw returned string verbatim (in the raw file; for the owner's document the rectangles are geometry, not text, so they may be stored).
- Parse it: number of rectangles, each rectangle's x, y, w, h; note the units (twips is expected — say what makes you conclude it) and whether rectangles are contiguous/gapped vertically.
- Compare the count with `getDocumentSize()` and with any other page-count source you can read natively without inventing one (e.g. `.uno:...` status, the document statistics); if none, say none.
- Cost: time 10 consecutive calls (`std::chrono::steady_clock`), report first and the other nine separately.
- Edit A (adds a page): move to the end of the document (`.uno:GoToEndOfDoc`) and dispatch `.uno:InsertPagebreak`; wait quiet; call again: count before/after; record every callback type that arrived between the edit and quiet (especially `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED`).
- Edit B (does not add a page): type one character in the first paragraph; same readings.
- Repeat the whole sequence 3 times per document (fresh load each time).

Prediction (main session, before any run):
- P-N1a: the string is `x, y, w, h; x, y, w, h; ...` in twips (from `SwWrtShell::getPageRectangles`).
- P-N1b: the 60-page document gives 60 rectangles natively (it may differ on WASM because of fonts; not asserted here).
- P-N1c: first call < 50 ms, later calls < 5 ms on 60 pages.
- P-N1d: Edit A adds exactly one rectangle and is followed by `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED`; Edit B leaves the rectangles unchanged.

## Part N2 — finding 129: does "click at the point, then the key" reproduce Writer, including the hard shapes?

The page fix planned for release 0.2.13 (`specs/SPEC-M3-autosave.md` §3.7, §8.1 Q5): when text is selected and an unshifted Left/Right/Up/Down/Home/End is pressed, the page (which cannot send a move on a range) first CLICKS at the point's cursor rectangle — x = the cursor rectangle's x, y = its y + height / 2 — which collapses the selection there, and then sends the ordinary collapsed move. The engine's click is `postMouseEvent(LOK_MOUSEEVENT_MOUSEBUTTONDOWN, x, y, 1, 1, 0)` followed by the same with `MOUSEBUTTONUP` (`wasm_sdk_probe/src/probe_engine.cpp` `handleClick`, about line 3163). The question is whether that emulation lands where Writer itself lands.

Tool: either extend `f129_native_arrow_on_selection.cpp` behind a new mode or write `wasm_sdk_probe/tools/f129_native_point_click.cpp`; do NOT change the behaviour of the existing arms (if you extend, rerun the old arms once and show they give the same text as `round-20261012T020528Z`). Evidence: `findings/evidence/129/native/point-click-round-<UTC stamp>/` and a new section appended to `findings/evidence/129/README.md` (append only; do not edit existing text).

Fixture: the existing `wasm_sdk_probe/test-docs/f129/arrow-selection.fodt` for the old 12 arms, plus a new `wasm_sdk_probe/test-docs/f129/arrow-selection-shapes.fodt` holding these shapes (plain default styles; ASCII text so nothing depends on CJK fonts):
- S1 soft wrap: a paragraph long enough to wrap to at least 3 lines at the default page width. Selection FORWARD from inside line 1 to exactly the first wrap position (the point at the offset where line 2 starts). Find the wrap offset from the cursor rectangle (the y changes when Right crosses it) and record it.
- S2 hard break: a paragraph with a `<text:line-break/>` in it. Selection FORWARD ending right before the line-break (the point at the end of the first visual line).
- S3 empty paragraph: a text paragraph followed by an empty paragraph. Selection FORWARD from inside the text paragraph into the empty paragraph (the point in the empty paragraph).
- S4 inside a table cell: a 2x2 table with text in each cell. Selection FORWARD inside cell A1's text.
- S5 across cells: selection FORWARD from inside A1's text into B1 (Shift+Right across the cell boundary; Writer may turn this into a cell selection — record what `getTextSelection` and the selection callbacks say).

For every selection (the old FORWARD and BACKWARD selections on P2, and S1–S5) and every key of Left, Right, Up, Down, Home, End, run three arms on a FRESH load each:
- `ref-<shape>-<key>`: Writer's own behaviour — press the key with the selection in place, type `#`, read the text (the existing method).
- `emu-<shape>-<key>`: the planned fix — read the latest `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` rectangle while the selection exists (record it), post the click at (x, y + h/2), wait for quiet, press the key (unshifted), type `#`, read the text.
- once per shape (not per key) `click-only-<shape>`: the click alone, then `#` — where the collapse itself lands.

Record for every `emu-*` and `click-only-*` arm: the callbacks (type and payload) that arrive after the click and before quiet, with their times relative to the click; whether ANY callback arrived within 400 ms (on WASM, a click that the engine answers with nothing costs a 400 ms wait in the page — `editor-shell/editor-session.js` `placeCaret`, `caretAckGraceMs`).

Summary table in the README: per shape × key, `ref` text vs `emu` text (where `#` landed, as an offset and a short excerpt of our fixture text), and `same` / `differs`.

Prediction (main session, before any run):
- P-N2a: `emu` = `ref` in all 12 old arms.
- P-N2b: in S2, S3 and S4, `emu` = `ref` for all six keys.
- P-N2c: S1 (soft wrap) is where they may differ — the point at the wrap offset has two visual positions (end of line 1, start of line 2); predicted: Left and Right same, at least one of Home / End / Up / Down differs.
- P-N2d: S5 is a cell selection; no prediction of `ref` beyond "it is not an error"; `emu` lands inside B1.
- P-N2e: every click on a selection is answered by at least one callback within 400 ms (the selection disappearing is news).

## Report (to the main session)

Start with `## SUMMARY` (≤ 30 lines): which predictions held / missed, the summary tables' bottom lines, the paths of everything you wrote, the time your last native run ended, and any instrument fault. Then details if needed.
