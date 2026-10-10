# opus adversarial review of SPEC-M3-production-ui §17 (2026-10-11; read-only; prompt: F1–F8 in the main session's brief). Verbatim.

## Ranked findings

**B1 BLOCKING (F3/F4): the revision label can lag the edit, so the visible window can stay stale.**
- Claim attacked: §17.2 says the page's "latest" revision is the one carried by `document-invalidated`, and a pass asks only for bands that are absent or older than latest. That rule applies inside the window too.
- Evidence, from engine source:
  - `onLokCallback` reads `gCallbackRevision` and emits the lok event first (`src/probe_engine.cpp:2542–2548`).
  - Editor UNO actions advance the revision later, in the `LOK_CALLBACK_UNO_COMMAND_RESULT` handler (:2730–2774). The format barrier does the same (:1603).
  - So the cursor invalidation that announces a Backspace, Delete, format or undo is likely to carry the pre-edit revision. Nothing has measured this ordering.
  - Typing goes through `handleInsertText` (:3186–3211), which increments right after the paste, so typing is probably fine.
  - Today `run()` repaints every band after each operation (`web/e2-editor-app.js:1431`). Under C′ that call would find nothing "stale".
- Consequence: after a non-typing edit, the deleted or bolded text can stay on screen while the page is quiet. An invalidation with no revision bump is dropped the same way.
  - The product-path format and delete checks read the saved ODT, not pixels (058's lesson).
  - C3 and C4 only type.
  - So every criterion would be green.
- Fix:
  - latest = max(`snapshot.revision`, the tile reply's `revision` (:3153–3157, stored at `document-sdk.js:409`), the invalidation's revision);
  - always re-request the window's bands on any invalidation or `run()`;
  - define "last" in C3/C4 as `#s-revision`;
  - add Backspace and set-bold to C4.

**B2 BLOCKING (F6): 125 breaks runners that the spec says will not change.**
- `check_m3_page_honesty.py:287–291` clicks `#state-pill` for user activation. Its own comment says a hidden element's box is 0×0 and the click lands at (0,0) on Nextcloud's header. `check_m3_production_ui.py:514` and `:567` make the same click.
- INVENTORY (:155–173) flags visible text outside `TEXT_PLACES` (:112). That list has `#state-pill` but not `#state-shown`, so 「就緒」 becomes `badText` and A3-1 FAILs (:681–682).
- Consequence: these runner edits need §34.4 witnesses. They raise 因執行而修 above the declared 3.

**B3 BLOCKING (F1): the window is smaller than one page in every default runner window.**
- Chrome's default standalone desk is 139 px (`findings/evidence/124/README.md`), so W ≈ 417 rows. The 0.2.11 reports show one page at 725×1012 (Chrome) and 900×1256 (Firefox).
- Firefox headless at 1366×768 gives a desk of about 300 px, so W ≈ 900 < 1256.
- Consequence:
  - Every address taken as a fraction of the canvas and every whole-canvas scan changes: INK_ROWS (:832), `stable_bands` (:3407), page honesty's TEXT_LINES (:196).
  - The `len(bands)==len(lines)` arms (:6186, :6278, :6367, :9408) see only the window. They return NE, which §23 row 1 counts as red, unless the port stitches per-row reads from several window positions.
  - The §17.3 inference and the C5 witness prediction (§17.6) are wrong, and the port is bigger than the census says.
- No consistent escape is written down:
  - a floor on W contradicts binding C1 (`≤ 3×desk.clientHeight×dpr`);
  - larger runner windows break the 0.2.11 reference (060 showed verdicts depend on the window).
- Decide before porting. I recommend assembling the scans from window reads with no change to judging logic, and amending §17.3/§17.6.

**S1 SHOULD-FIX (F3): no "re-place only if `winTop` changes".**
- At a clamped edge, or when W = docRows (short documents), the visible range is always within a quarter window of an edge.
- So every scroll event re-blits the whole window (one A4 page at ratio 2 wide ≈ 17.8 MB) and calls `renderDocument`, setting `renderAgain` and cutting off the pass in flight.
- With W smaller than one 1023-row band, re-placement happens about every 35 px of scrolling.

**S2 SHOULD-FIX (F3): the design list leaves out code that must change.**
- `visibleCanvasRows` (:870–879, which the ruling names)
- `overlayShapes` scaleY (:1145)
- `paint`'s `renderBands(el.canvas.height)` (:1080)
- `renderDocument`'s `total` (:915)
- `setPointerCapture` (:1823)
- a `winTop` clamp after a 118 shrink
- "subtract `winTop` when painting, not when requesting" for the band in flight

**S3 SHOULD-FIX (F5): scrolling during a selection is not what Collabora does.** "反白中…照捲" contradicts "照 Collabora": Collabora does not jump the view during a complex selection (`_allowViewJump`, cited in the 124 README). During a real drag, replies that arrive mid-drag would scroll content under a pointer that has not moved.

**S4 SHOULD-FIX (F6): 125's "什麼都不顯示" is ambiguous.**
- It can mean blank or keep the last label. 125-B counts only 「處理中」, so a blank↔就緒 flicker passes it.
- The direct writes at :2262 (已過期) and :2423 (錯誤) bypass `updateState`. A pending 700 ms timer would overwrite them with 處理中 unless they cancel it.

**S5 SHOULD-FIX (F7/F8): retiring the mutation is argued, not run.**
- The retirement rests on derivation and is excluded from C5(ii) in advance. The ruling's C5 says "every mutation red", and §34.4 and CLAUDE.md §7 want a run: apply the mutation on C′ and record that it survives.
- Afterwards the C2 clause of `the-projection-is-placed-where-the-document-is` has no red case. Register that under §3.
- The importer list in C5 is written by hand (§1); derive it from the imports.
- 1′'s window is defined only for v8 reports and one cell's field. Say how it applies to the v19 arm and to the reverse direction.

**S6 SHOULD-FIX (F8): 124 and 125 in the same candidate spoil the §34.4 witness.** The ruling's witness is "red only on geometry-addressed checks". With a 139-px desk, 124 scrolls in nearly every cell, and 125 turns A3-1 red. Run the witness on the C′ commit before 124 and 125 land.

**N1 NOTE: C1 can fail on rounding alone.** `round(cssWidth×dpr)/cssWidth` can exceed dpr (725×1.5 → 1088), and `clientHeight` is rounded, so a correct page can miss the bound by 1–3 rows. Specify floor().

**N2 NOTE: C6's text and its instrument disagree.** The criterion says the LD-BOTTOM line. `probe_c6_long_document.py:117–124` counts dark pixels at the top of the last page. The ruling's "last strip" would call a drawn page blank: at 40 pages ratio 2 wide the last 712-row band is entirely below LD-BOTTOM, which sits about 68% down the page. A crash or OOM outcome is not classified.

**N3 NOTE: C6's default is stricter than the ruling's.** §17.4 says "C′ 上不過→不收"; the ruling's default keeps a named limit. Say so explicitly.

**N4 NOTE: the C1 and memory predictions use the wrong desk height.** They assume a 960-px desk. On the standalone page at 1400×1000 the desk is about 540 px, so W ≈ 3,234 rows.

**N5 NOTE: a deferred disposition (CLAUDE.md §2).** §17.8's "處置另寫" leaves the V4 outcome to a later decision.

## F1–F8

- **F1 WRONG.** See B3.
- **F2 HOLDS, with caveats.** The arithmetic is right (98,869 / 92,682 measured against 98,920 / 92,750 computed). The red case reproduced (`034c5b3f`), and worse than predicted: the whole canvas is blank, top included, in both browsers (finding 126). The screenshot reading separates blank from drawn (0 against tens of thousands of dark pixels). Caveats are in N2. The canvases between about 66,000 and 98,000 rows were never measured.
- **F3 WRONG.** See B1, S1 and S2. I found no infinite loop.
- **F4 WRONG.** It is the same underlying counter, sampled at different moments, and the label is safe only if "latest" never lags.
- **F5 mostly HOLDS.** The V4 prediction is sound on the host page: Chrome 800×600 minus the 50-px header, with the status bar and provenance hidden (`templates/editor.php:34–50`), leaves a desk of roughly 470 px. IME composition does not move the engine caret, so 124 does not scroll during it. I found no a11y conflict. Exceptions: S3 and S6.
- **F6 WRONG.** See B2 and S4.
- **F7 computable.** Between 0.2.10 and 0.2.11 only Firefox v19 `clear-format…` differs (PNN against NNN). Zero differences is achievable, but 12 Firefox cells (NNN, FFF) are blind. The equivalent-mutation argument is right: `.paper` has no padding and `#a11y-doc` keeps `margin:0`, so `offsetTop==0`. The procedure is not (S5).
- **F8: contradictions with the ruling.** S5 (C5 "every mutation red"), N3 (C6 default) and S6 (the witness premise). Hand enumeration (§1): S5's importer list.

## MOST IMPORTANT THREE

1. "Latest revision" from `document-invalidated` can trail UNO-path edits (B1), so a Backspace or bold can stay stale on screen with every criterion green.
2. Hiding `#state-pill` breaks the activation clicks and A3-1 in production UI and page honesty (B2), contrary to "runners unchanged".
3. In default runner windows the 3× window is smaller than one page (B3), so the §17.3 scope inference and the witness prediction are wrong, and the C1-bound window conflicts with the counted reference.

## Main session's check (2026-10-11, before acting)

- **B1 holds as a risk**: `advanceRevision()` (`src/probe_engine.cpp:2478–2481`) stores the callback revision only when called; `onLokCallback` (:2540–2548) stamps whatever `gCallbackRevision` holds when the callback fires; `run()` awaits `renderDocument()` after every operation (`web/e2-editor-app.js:1425–1431`). The ordering for UNO-path edits is unmeasured (R1 measured only typing).
- **B2 holds**: `check_m3_page_honesty.py:287–291` and `check_m3_production_ui.py:514`, `:567` real-click `#state-pill`; `TEXT_PLACES` (:112) names `#state-pill` and INVENTORY admits visible text by `p.closest(PLACES)` (:167). No runner uses the pill's TEXT for logic (grep of `get("label")` in the runners: none from `READ_STATE`).
- **B3 holds**: `run_browser_probe.ChromeSession` passes no window size (`--headless=new` only, :216), so Chrome is 800 × 600 and the standalone desk 139 px (measured).
