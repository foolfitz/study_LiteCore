# Review brief 1 — the 132 page change (H1–H3), adversarial

You are an adversarial reviewer. Read-only: do not edit any file except your output, do not run browsers, do not run `make`, do not touch `~/Projects/Nextcloud_Apps/`. Output: `findings/evidence/132/review/review-1.md` (English), starting with `## SUMMARY` (≤ 30 lines), then findings, each tagged **BLOCKING** / **SHOULD** / **NOTE**.

## What to review

- Spec: `specs/SPEC-M3-held-key.md` (commit `dbe74a68`): §2 mechanism and baseline, §3 design H1–H3, §4 the owner's decision, §5 criteria.
- The product change: `git show 69c05657 -- wasm_sdk_probe/web/e2-editor-app.js` (page `abc3d97b…`). Three changes:
  - **H1** `bandOrder(bands, visible, caretRows)` + `caretDocRows()`; `renderDocument` passes it.
  - **H2** `HELD_DELETE_DEPTH = 2`, `dropsHeldRepeat`, `skipHeldRepeat` registered on the sink's `keydown`: a Backspace/Delete keydown with `repeat === true`, not composing, while the page's own `deletesInFlight >= 2`, is `preventDefault`ed (so no `beforeinput`, nothing sent). Presses are never dropped. The owner chose this behaviour knowingly (§4): a 2 s hold deletes ~25 characters, not 52.
  - **H3** `overlayEditorState()` + `overlayState`: while `deletesInFlight > 0`, an engine state whose selection is a range is not adopted; the overlay keeps the state it drew before. The delete listener calls `paint()` once when `deletesInFlight` returns to 0.
- Unit tests: `git show 365515a4` (written first, red on the old page) and `findings/evidence/132/unit/` (green, mutants).

## Questions — answer each with file:line and a concrete failure scenario, or say plainly that you found none

1. **H3 hides something real.** Find a sequence in which a range that IS the user's (drag selection, Ctrl+A if offered, a selection the engine reports after an undo/redo, a range left by a refused delete-selection, a restart/reopen after a boundary refusal — finding 109's `reopenAfterBoundaryRefusal`, `restart()`) is never drawn, or a caret is drawn somewhere the document no longer has it, for longer than until the next state write after `deletesInFlight` returns to 0. Consider `overlayState` surviving a session replacement (restart, reopen) — `session` is replaced but `overlayState` is module-level.
2. **H3 and the paint paths.** `paint()`, `paintBand()`, `moveWindow()`, `layoutCanvas()` all draw from `overlayShapes()`. Is there a path where the overlay drawn from the kept state disagrees with what is on the canvas (a wash drawn twice — it is a multiply — or a caret left behind), e.g. a window move (`onDeskScroll` → `moveWindow`) or a resize during a delete?
3. **H2 starves or loses.** Can `deletesInFlight` stay ≥ 2 with nothing actually in the engine (a leak: an `editorAction` that never settles, `run()` awaiting a repaint pass that never ends, a BUSY retry loop of up to 84 × 120 ms), so that a held key does nothing for seconds? Is a key the user pressed (not a repeat) ever dropped? What happens with Delete held at a paragraph end (boundary merge, SPEC-M3-paragraph-merge; finding 109's refusal → reopen) or Backspace held into a table / a refusal: does the queue or the reopen interact badly with H2?
4. **H2 and the platform.** `event.repeat` on a held key: true in Chrome and Firefox on Linux (measured: 51/52 flagged). Any platform/IME/virtual-keyboard case where every keydown is `repeat: true`, or Backspace arrives as `key: "Process"`/`Unidentified`, so that H2 drops or keeps the wrong ones? `isComposing` handling vs the existing composition code.
5. **H1.** Is `caretDocRows()` ever wrong enough to matter (stale caret from a previous state, caret during a range, `docRows` vs `heightTwips` mismatch after a document size change — finding 118's `documentSizeChanged` path)? Does putting the caret's band first change anything the 122/123/C′ criteria rely on (the pass ending after the band in flight, `renderAgain`, the window cache)?
6. **The criteria (§5).** Is there a page that would pass 132-B's (a)–(e) and the unit tests while the owner would still see 「累積延遲、再一口氣出現」 or a blue flash? Do not propose new machinery; say whether a criterion is aimed at the wrong quantity, with the scenario.

Ground rules (CLAUDE.md §34 of SPEC-M3-paragraph-merge, the "checks stop rule"): review the product change and the spec; do not redesign the test machinery. A finding about a check is only BLOCKING if it names a concrete product failure the check would pass. Mark anything you could not verify from the source as unverified.
