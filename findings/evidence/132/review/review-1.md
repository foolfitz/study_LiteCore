## SUMMARY

Reviewed `69c05657` (page `abc3d97b…`, `web/e2-editor-app.js`) against `specs/SPEC-M3-held-key.md` §2–§5 (`dbe74a68`), the 132-U tests (`365515a4`) and `findings/evidence/132/unit/`. Re-ran `node --test page-*.test.mjs` in `editor-shell-v2/tests`: 74/74 pass, the seven 132-U tests included. Paths below are relative to `wasm_sdk_probe/web/e2-editor-app.js` unless named.

**No BLOCKING.** H1–H3 do what §3 says, and I found no sequence in which they lose an edit, drop a press, or leave a wrong overlay on the canvas.

- **Q1 (H3 hides something real):** none found. A range that arrives while a delete is out gets drawn by the settle `paint()` (:2368-2369), or by the next `paintBand` when `lastTiles` is empty (:1391). The hiding lasts only while `deletesInFlight > 0`, so at most as long as the hold. Module-level `overlayState` (:203) survives `restart()` and `openDocument()`, but every path that replaces the engine drains `deletesInFlight` to 0 before the new engine pushes a state, and that state is collapsed (N1, N2).
- **Q2 (paint paths):** none found. H3 does not create a new way for `paintBand` to adopt a state `paint()` never drew. The 1→0 transition and the settle paint run in one microtask checkpoint, and a band only lands from a separate Worker-message task (N3).
- **Q3 (H2 starves/loses):** no leak. `run()`'s repaint is inside the count, but from a delete's `run()` it cannot enter the 84 × 120 ms BUSY loop, because `engineActionsOut ≥ 1` there (:1290-1299). A press is never dropped. **S1:** a held Backspace at the document start (or Delete at the end, or into a table) hits the refusal again after every reopen. That is three refusals in about 3–5 s, after which the page hits the Worker-generation ceiling. This was already the behaviour on `d761f1ce` and H2 did not introduce it, but it is unregistered.
- **Q4 (platform):** every misread found is fail-open (`Process`, `Unidentified`, autorepeat sent as press/release pairs): the old tail comes back and no data is at risk (N5). **S3:** 132-B's `repeat` flags are set by the drivers (CDP `autoRepeat`, WebDriver), not by the operating system's autorepeat. A desk whose real path does not set `repeat` would still pass 132-B while the owner sees the 1.8 s tail.
- **Q5 (H1):** `caretDocRows()` uses the same scale as the overlay and the pass, so it is wrong exactly when they are (N6). Nothing in 122-B, 122-U or C′ depends on "top of the view first".
- **Q6 (criteria):** **S2:** under a held key a pass paints only its first band. Anything that changes outside the caret's band stays frozen until release, then appears all at once. That covers the lower part of a caret line that straddles a band edge, and lines below the caret that reflow across an edge. (b) cannot see this: it reads only the band holding the caret's top row (`probe_hand_test_0212.py:81-84`). This is the owner's 「再一口氣出現」 in a smaller form. It is not a regression.
- **NOTEs:** N1–N11, including the release→fresh time being recorded but not gated (N7), devicePixelRatio 1 only (N8), a possible blue wash during a refusal's reopen (N9), and a misplaced doc comment (N10).

---

## SHOULD

### S1 — A held key at a refusing boundary refuses again after every reopen, and three refusals reach the Worker-generation ceiling (Q3; already true on `d761f1ce`; read from the source, not measured in a browser)

The chain:

1. **The refusal.** The engine refuses Backspace at the document start, or Delete at its end, with `nothing-selected` after the 250 ms deadline (`src/probe_engine.cpp:3859-3863`). `finishMergeKeyError` sends that as `EDITOR_BOUNDARY_UNSUPPORTED` (`:3378-3401`). Into a table, the stage is `anchor-mismatch` instead (`specs/SPEC-M3-paragraph-merge.md:547`).
2. **The session blocks.** The session's `_drain` calls `_blockQueue(…, "restart-required")` (`editor-shell/editor-session.js:319-320`). That rejects every queued item and disables the sink (`:342-352`). All of the page's deletes settle, so `deletesInFlight` is back to 0 (:2368).
3. **The page reopens.** `run()` calls `reopenAfterBoundaryRefusal` (:1797-1799). It restarts the session and calls `el.sink.focus()` the moment the restart returns (:1684-1687), while the key may still be down.
4. **H2 does not stop the next refusal.** The next autorepeat reaches the re-focused sink with `repeat: true`. At count 0, `dropsHeldRepeat` returns false (:2579-2582), so the delete is sent and refused again 250 ms later.
5. **The ceiling.** Reopens took 1.0–2.1 s in the counted 0.2.10 runs (`findings/evidence/m3-production-ui/runs-0.2.10/counted-B3x-x2.json`, `counted-KR-x3.json`, latency lines 「重新載入 1011–2051 ms」). So the second refusal comes about 1.5–2.6 s after the caret reaches the start, and the third about 3–5 s after.
   - `maxWorkerGenerations` defaults to 3 (`editor-session.js:81`), and every open adds one (`:161`).
   - At the third refusal `restartAvailable()` is false (`editor-shell-v2/narrow-editor-v2-session.js:460-462`), so the page goes to `rescueAtGenerationLimit` (:1659-1662) and tells the user to reload.

**Scenario.** The user holds Backspace to clear the first line of the document and keeps holding about 2 s past its start; the baseline's own hold is 2 s. The result is two reopens, each with 109's 「緊接在這一鍵前後打的字可能沒有打進去」 caveat (:1694-1696). A hold of about 4 s ends the page's editing.

**Why it is not BLOCKING.** `d761f1ce` does the same: its whole queue is rejected at the first refusal, and repeats resume after the reopen. H2 neither adds this nor removes it.

**Why it belongs here.** §3.2 is now the one place that decides what a held repeat means, and §8 has no entry for this. The merge spec itself records that held keys at a boundary were never measured (`specs/SPEC-M3-paragraph-merge.md:1158`).

**Disposition.** Register a named limit (e.g. L-132-held-into-refusal) and put the choice to the owner:
- **A.** Register only.
- **B.** Also drop Backspace/Delete repeats from a boundary refusal until that key's keyup. That is a page-only rule of H2's own shape; it is not a check.

### S2 — Under a hold only the caret's band is repainted, so changes in other bands freeze until release; criterion (b) cannot see it (Q5, Q6)

**The mechanism.**
- Under a held key, each pass gets through its first band only.
- **Why the pass stops.** The next delete's barrier makes the second band's request BUSY, and the pass gives up (:1290-1293). Or the next delete's `run()` sets `renderAgain`, because it calls `renderDocument` while a pass is running (:1177).
- **The evidence.** In the baseline's low arm, the second band was repainted once in 52 deletes (`baseline/README.md` table).
- **What H2 changes.** Repeats that H2 drops no longer end a pass through `endRenderPassOnInput` (:2398-2403), but passes still end at the next delete as above.
- **What H1 changes.** H1 makes that one band the caret's (:1138-1144).

**Failure scenarios (inference).** Each passes 132-B and the unit tests.

1. **A straddling caret line.** The caret line straddles a band edge. `holdsCaret` is true for both bands, and the tie goes to the lower index (:1144). The upper part of the line follows the hold. The lower part (the glyphs' bottoms) keeps showing the deleted characters until release plus one pass. The probability is about line height ÷ 1,023 rows (2–5 % of lines at ratio 1, more at 1.5).
2. **Reflow across a band edge.** The caret is mid-paragraph and the paragraph continues past a band edge below it. Each delete eventually pulls words up from the next lines. The lines below the edge show the pre-hold layout during the hold, with words duplicated or missing across the edge, and jump at release.
   - This is common: there are about three band edges per A4 page at ratio 1.
   - It is the owner's 「再一口氣出現」, smaller.

**Why (b) is blind to it.** `deletesShownAtRelease` comes from the label of the band holding the caret's top row only (`tools/probe_hand_test_0212.py:81-84`, `caretRow` from `#sink`'s top; `hold_summary` :494-506). Under H1's tie-break that is exactly the band that does get painted. The hold arms put the caret at rows 229 and 1338, mid-band. Whether their paragraphs reflow across an edge is unverified.

**Not a regression.** `d761f1ce` behaves the same when the caret is in the top band, and worse otherwise.

**Disposition.** Under the stop rule, no new criterion. Before the 132-B run, name it in §8 (e.g. L-132-other-bands) and in §7, so a green (b) is not read as "the screen follows the engine" in general and the owner's hand test is not the first to find it.

### S3 — 132-B's `repeat` flag is synthesized by the drivers, not produced by the platform (Q4, Q6)

**What the baseline actually established.** The baseline's "the repeat flag is real: 51 of 52" (`baseline/README.md`, Positive controls) comes from repeats that the drivers labelled:
- Chrome: CDP `Input.dispatchKeyEvent` with `autoRepeat: true`.
- Firefox: WebDriver, where "a keyDown of a key already down is a repeat by the spec".

So (a) shows that H2 works when `repeat` arrives set. It does not show that the owner's real keyboard path sets it. Among the unknowns: X11 or Wayland, and whether IBus/fcitx sit in the path.

**If the real path does not set `repeat`.** H2 never engages and fails open: the 1.8 s tail returns, H1 and H3 still work, and no data is at risk. 132-B would be green while the owner still sees 累積延遲. This is the "verify the proxy, not the claim" shape (CLAUDE.md §7). It is unverified either way.

**Disposition.** No new machinery. Put one line on the owner's hand test: hold Backspace for about 2 s mid-text; deletion should stop within about 0.15 s of release. The owner's hand test is the only witness for the platform half.

---

## NOTE

**N1 (Q1) — `overlayState` across a session replacement.** It is module-level (:203) and reset neither in `layoutCanvas` nor in `openDocument`. No failure found:
- **`restart()` keeps the `session` object.** `_blockQueue` has already rejected every queued delete and disabled the sink (`editor-session.js:342-352`). So `deletesInFlight` is 0 before the new engine pushes anything, and the first `overlayShapes()` call adopts its state.
- **`openDocument()` replaces `session`.** It awaits `close()` first, which rejects pending operations (`editor-session.js:625-636`). The new document's first state is collapsed.
- **What a stale kept state would need.** `deletesInFlight > 0` and a range as the new session's state, at once. I found no path that produces both.

**N2 (Q1) — the hidden window is bounded by the count, not by the next state write.**
- **A drag during a held key.** The range is drawn at release. That is by design: §3.3 says a range that arrives while a delete is in flight is drawn once the count returns to 0.
- **Undo or redo pressed during a delete.** If the range it reports arrives while the delete's `run()` is still repainting, it is drawn at the settle paint.
- **A refused delete-selection.** The kept state is the user's range, which was adopted at count 0 when the drag ended, so it stays drawn.
- **Ctrl+A.** Unbound (:2483-2491).

**N3 (Q2) — paint paths.**
- **`paint()`** restores band pixels under the old and new areas before drawing (:1400-1421), so a kept state either has the painted key (no-op) or is drawn once.
- **`moveWindow`** redraws the kept overlay whole over fresh pixels (:1051-1062).
- **`layoutCanvas`** clears both the canvas and `paintedOverlay` (:1008-1009).
- **The one H3-specific risk** would be `paintBand` adopting a state `paint()` never drew: the count goes 1→0 with a range in the engine, and a band lands before the settle paint. That cannot interleave:
  - The decrement and the settle `paint()` run in the microtask checkpoint of the action's own settlement.
  - A band lands from a separate Worker-message task.
  - A pass started in `renderDocument`'s `finally` (:1314) awaits before any `paintBand`.
- **Already true before H3.** A state write whose `paint()` returned on empty `lastTiles` (:1391) is first drawn by `paintBand`, inside that band only. The canvas was just cleared there, so nothing is left behind.

**N4 (Q3) — what "two out" means.**
- **The count includes the repaint.** `deletesInFlight` covers `run()`'s repaint (:1787 inside :1918). So "2 out" can mean one repainting and one in the engine, with nothing queued.
- **Why the engine still does not idle (inference).** It would idle only if that repaint outlasts the delete in the engine. Inside a delete's `run()` the repaint ends at the first BUSY (:1290-1293), and the BUSY loop (:1294-1299) is unreachable with `engineActionsOut ≥ 1`. So the count drops about one band after the previous delete completes, and the next repeat is queued before the engine finishes.
- **Upper bounds.** The count can otherwise be held only by SDK timeouts: 30 s per action, 60 s per band (:1235).
- **Witnesses.** (c) ≥ 20 is the right witness. Presses are never dropped by construction, with U3/U4 and 131-B as witnesses.
- **Held Delete across paragraph merges.** Each merge is one delete (30–36 ms each after 117), so depth 2 is unaffected. It only matters when the merge reaches a refusal (S1).

**N5 (Q4) — platform and IME cases.** All the misreads found are fail-open (the tail comes back, nothing lost):
- **Fail-open.** Backspace arriving as `Process`, `Unidentified` or keyCode 229 (an IME consuming it, Android virtual keyboards). Autorepeat sent as press/release pairs (remote desktop, X11 without detectable autorepeat).
- **The only drop-the-wrong-key direction.** Chromium flags a press as a repeat when it is the same key and modifiers within 2 s and the release was never seen. That is from memory of `ui/events` `KeyEvent::IsRepeated` and unverified here. It matters only at depth ≥ 2, mid-pipeline.
- **131-B does not exercise it.** 131-B's presses are driver-labelled `repeat: false`, so it cannot witness this case either way.
- **`isComposing`** matches the Enter guard (:2525). A composing Backspace arrives as `Process` anyway.

**N6 (Q5) — `caretDocRows()` consistency.**
- **Same scale everywhere.** `caretDocRows()` (:1149-1155) uses the same `docRows / heightTwips` as `overlayShapes` (:1493) and the pass's band twips (:1217-1228).
- **The 118 path.** It re-lays out in the same continuation that saw `documentSizeChanged` (:1250, :1272-1280), so no pass starts with `docRows` and `heightTwips` disagreeing.
- **A stale caret, or a barrier's cursor during a range,** costs at most one pass with a neighbouring band first.
- **Nothing depends on the old order.** I found nothing in 122-B (`typing-latency/judge.py`: on-screen median and max, "(ii) every band current"), 122-U or C′ that relies on "top of the view first". The 122 B′ design itself said 「先畫游標所在／視窗內的條」 (`SPEC-M3-production-ui.md:567`).

**N7 (Q6) — (a) and (b) are counts at the release instant.** The quantity the owner names (「要等一下子才會不見」) is the time from release to final screen. It is recorded (`caretBandFreshAfterReleaseMs`) but not gated. §7 predicts ≤ 160 ms; whoever reads the report should compare against that. No change proposed.

**N8 — 132-B runs at devicePixelRatio 1.** The baseline used a 1850 × 980 desk at ratio 1. The owner's laptop is 1.5: bands are shorter in CSS pixels, which makes S2 more frequent, and cost more per band. It is worth saying in the report.

**N9 — possible blue wash during a refusal's reopen.**
- **When it happens.** A refused merge-key may leave the engine with K1's selection (unverified). If it does, the settle paint at count 0 draws it, and it stays until the new engine's first state, about 1–2 s.
- **Not new.** `d761f1ce` draws it too, at once.
- **Not covered by (d)**, because the hold arms contain no refusal.

**N10 — misplaced doc comment.** `overlayShapes`' doc comment ("The caret and the selection as the canvas draws them…", :1462-1467) now sits above `overlayEditorState`'s (:1468-1478), and `overlayShapes` (:1485) has none. Cosmetic.

**N11 — H3's scope.**
- **Covered:** only the delete listener's deletes.
- **Toolbar ⌫/⌦:** still flash the barrier's range, but production hides them (`SPEC-M3-production-ui.md:74-77`).
- **Cut:** its range is the user's anyway.

No action.
