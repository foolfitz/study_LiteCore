# Plan, 2026-10-12 — the next link: Shift+Arrow selection and the page number (and, possibly, moves on a range)

Owner's words (2026-10-12): 「新需求：沒關係你再安排開發時程」; 「頁碼：照collabora做法」. Recorded in `specs/SPEC-M3-production-ui.md` §17.25–17.26. This file is a plan, not a spec: nothing here is a criterion yet. The link is the owner's step; nothing in this plan touches product bytes until a spec is written and reviewed.

## Order against the rest

1. Release 0.2.13 (finding 127 autosave + 128 / 129 page fix / 130) is first; it needs no link (`specs/SPEC-M3-autosave.md`).
2. This plan's native measurements and spec run in parallel with 0.2.13 (no product bytes).
3. The link goes on the CURRENT core (writer-only, the v8 line; v19 carries no Calc: `ScDocShell` 0 occurrences in `dist/profiles/e2-editor-v19/probe.wasm`, 18 in v12/v14). One variable per link. Moving the product onto the writer+calc core (the a11y line, needed for ODS reading) is a separate step; the owner was offered A/B/C on 2026-10-12 and had not answered when this was written.

## Item 1 — Shift+Arrow extends the selection (request one)

- **Today**: the page sends Shift+Arrow as the plain move (`web/e2-editor-app.js:2398–2405` ignores `shiftKey`); v19's 21 actions have no extend action; the contract refuses arbitrary key codes and UNO commands.
- **Native reference, measured** (`findings/evidence/129/native/round-20261012T020528Z/`, arms `caret-shift-*`): Shift+Left/Right/Up/Down/Home/End from a caret extend from the point exactly as expected (e.g. Shift+End selects `BETA GAMMA DELTA`, Shift+Down selects to the next paragraph at the point's column).
- **Open**: (a) how the engine should dispatch them — key events with `KEY_SHIFT` (the barrier already uses Shift+Left/Right internally: `merge_native_boundaries.cpp` header, `probe_engine.cpp` startSelectionBarrierDelete) or `.uno:CharLeftSel` and friends; (b) what the barrier verifies for an extend (the selection's rectangles changed? the selected text grew by one unit?); (c) the gestures: an extend starts from `collapsed` or a range, and ends in a range — the manifest's gesture model is about the starting shape; (d) whether the page's `lastSelectionShape` and the toolbar's gesture affordance follow (they read the engine's state, so they should).
- **Next native step**: none needed for the behaviour itself; measure the barrier's candidate signatures natively before writing the engine side.

## Item 2 — the page number, Collabora's way (request two)

- **What Collabora does, read** (`cool-26-04/browser/src/control/Parts.js:312–360`; `layer/tile/WriterTileLayer.js:201`): the client holds the page rectangles (from the document status `pagerectangles`), works out the current page from them and the view, and shows `Page N of M` in the **status bar**; no scrollbar tooltip was found in `canvas/sections/ScrollSection.ts`.
- **What LOK offers, read**: `getPartPageRectangles` (`libreoffice-26-8/desktop/source/lib/init.cxx:4075`) → `SwXTextDocument::getPartPageRectangles` (`sw/source/uibase/uno/unotxdoc.cxx:3432`) → `SwWrtShell::getPageRectangles()`, twips. Not exposed by our engine or SDK today (no page geometry anywhere in `sdk/`).
- **Design sketch**: one engine operation returning the rectangles; the SDK re-reads them when the paint reply says `documentSizeChanged` (finding 062's flag already exists); the page computes N from `#desk`'s view centre against the rectangles and shows 「第 N 頁，共 M 頁」 in its status line. Never inferred from equal page heights (landscape pages and sections break that).
- **Next native step**: call `getPartPageRectangles` on the owner's document and on `tools/create_long_document.py` output (60 pages), record the format and the cost (it walks every page), and whether it changes after an edit that adds a page.

## Item 3 — possibly: moves on a range (finding 129's alternative remedy)

0.2.13 fixes 129 in the page (collapse at the point, then move). If that turns out unreliable on WASM (spec M4 / Q5), the alternative is to grant the six moves the range gestures so Writer handles the key itself; that changes the manifest (a profile identity) and needs the engine's move barrier measured from a range. Decide after 0.2.13's M4.

## Not in this link

ODS / Calc (separate step, see Order 3). Block identity (long term).
