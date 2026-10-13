# Review 1 — ruling-3 condition 9: the two probes' new arms/readers and the judge

One adversarial pass, as `brief-1.md` asks (§34: each reading tool reviewed once). Reviewer: opus, 2026-10-13. Nothing edited but this file, nothing committed. No browser, probe or ddev call.

**Read in full:** `134/ruling/ruling-3.md` (with addenda 1–3), `handoff/tasks/TASK-2026-10-13c-136-probes-and-judge.md`, the three tools at HEAD, and their change `53f7aff5^..53f7aff5`. The brief's `5901681c^` is `53f7aff5` itself, so a diff from there shows only the baseline commits. Also read: `136/judge/README.md` with reds (a)–(c), `136/baseline-0.2.16/` (README, both reports, both judge outputs), and the page fix `53db5422..b2b488c0`. The page's working copy is `aebef525…` in both `web/` and `dist/`. Also read: `editor-shell/editor-session.js` :255-335 and `check_m3_production_ui.py` :210-300.

**Run (judge only, on existing reports, `--page 6470dec0…`):**
- Both baseline reports reproduce their committed `judge-output.txt` line for line.
- Reds (a) and (b) reproduce their files line for line.
- Two synthetic reports, derived from the baseline in the session scratchpad and described under S1 and N1, each exit 0.

**Verdict:**
- The judge does what it says. Tool closure holds, and every claim in `136/judge/README.md` checks out against the code.
- I found **no correct page that this judge would FAIL for a reason unrelated to the fix** (N7).
- One gap lets a page with 136 still in it pass (S1). It is cheap to close.
- Separately, the baseline's own timing predicts that **0.2.17 will put the caret one glyph into paragraph 0 on `start-hold`**. If so, the judge will FAIL that arm, and correctly so (B1). This is a defect in the fix, not in the instrument. It goes first because it decides how a red `start-hold` on the run now in progress must be read.

## BLOCKING

### B1 (the page, not the judge; predicted from measured timing). On `start-hold`, the FIFO head is one delete stale, so D puts the caret after the first glyph of paragraph 0

**Where.**
- `wasm_sdk_probe/web/e2-editor-app.js:1961`: the push takes `session.state.snapshot.editorState?.caret` at send time.
- `e2-editor-app.js:1696-1697`: the reopen reads the head.
- `e2-editor-app.js:1720`: D clicks at that caret.
- `ruling-3.md` FACT CHECK, G1 (iv), supplies the premise: "`start-hold` — the refused sixth delete is sent while the fifth is out or done; the fifth's K1 point (Shift+Left from 1) is position 0".

**Why the premise does not hold at the timing H2 produces.**
- H2 frees a slot when the previous delete's handler `.finally` runs (`:2403-2418`, `:2625-2631`). Each delete is sent the moment a repeat finds `deletesInFlight < 2`.
- The drain writes delete N's result state, resolves it, and **in the same microtask** posts delete N+1 to the Worker (`editor-session.js:290-314`: `state.update` :307, `item.resolve` :314, then the loop's next `shift()` :290 and `item.operation` :299). Delete N+1's K1 selection can only reach the page after a Worker round trip.
- When a repaint is already in flight, `renderDocument()` returns at once (`:1194`). The slot therefore frees in the same turn as N's result.
- So the refused delete's send-time caret is delete N's **result**: in `start-hold`, the fourth delete's, i.e. position 1 of `k` + paragraph 0. It is position 0 only if the fifth's K1 push won a race against the next repeat.

**Measured on the pre-fix page.** Of 8 `start-hold` rounds, 4 are this baseline and 4 are `134/acceptance-0.2.16`. In all 8, 5 deletes succeed, the 6th `beforeinput` is the refused one, and the 7th is rejected with it. The refused delete was sent this long after the **fourth** delete's completion sample, and about 50 ms before the fifth's:

| run | Chrome r0 | Chrome r1 | Firefox r0 | Firefox r1 |
|---|---|---|---|---|
| baseline-0.2.16 | **0.1 ms** | 15.6 ms | 9.9 ms | 8.9 ms |
| acceptance-0.2.16 | 3.0 ms | 1.4 ms | 6.7 ms | 8.0 ms |

At 0.1 ms no Worker message can have arrived in between, so in that round the head is certainly position 1. In the others it depends on how fast K1 is pushed, which the instrument does not record: the samples carry no caret. On `6470dec0` none of this showed, because D read the snapshot at reopen time. That snapshot is the refused delete's own K1 at position 0, and 8/8 passed.

**What D does with it on `aebef525`.**
- Paragraph 0 of the owner's document is `Heading 1`: bold, 18 pt western and Asian, western font Liberation Sans (inherited from `Standard (user)`). Its first character is a full-width CJK glyph.
- Liberation Sans Bold `k` advances 1139/2048 em, which is **200 twips** at 18 pt (read from the font's `hmtx`). The first glyph is 360 twips wide, so its midpoint is at **180 twips**.
- D therefore clicks about 20 twips past the midpoint, more if Writer's Asian/non-Asian autospace applies. The caret lands **after** the first glyph, `wvy` is typed there, and the reader gives `afterParagraphs [0]` with `afterAtStart false`.
- The judge prints `AFTER not at the start of its paragraph (afterAtStart False)` and exits 1.

**Consequences.**
- (i) A `start-hold` red on 0.2.17 is the fix regressing a shape 0.2.16 got right. Do not adjust the judge or the arm to fit; ruling-3's own rule applies.
- (ii) A `start-hold` green on 0.2.17 does not show that the head was position 0. With two rounds per browser, the K1 push may simply have won every race.
- (iii) Same mechanism, not probed: any held **Backspace** that is refused after deleting, e.g. into a table cell's start. Forward Delete does not move the caret, so a stale head costs nothing there. This is why the table arms cannot see it.
- (iv) The unit tests U-136a–c do not model H2's timing. They pin "send-time", and send-time is exactly what is wrong here.

**For the ruling author, not prescribed here.** The caret the user had when the refused delete was taken is the state written when the **previous** delete resolved (`editor-session.js:307`, before `:314`), or the send-time caret when nothing was out. It is not the send-time caret, and not anything read after the previous delete's repaint: by then a cell-end K1 may already be in the snapshot, which is 136's race.

## SHOULD

### S1. Press-type contiguity is not pinned to a paragraph, so `cell-press-type` can go vacuous and pass with 136 unfixed

**Where.**
- `judge_held_into_refusal.py:163-168` (`contiguous`), with RULES at `:228`, `:230` and `:232`.
- The reader's `controlThenMark` is `any(CONTROL + MARK in t for t in texts)` (`probe_held_into_refusal.py:142`).
- `probe_table_refusal.py:46-60` (`nav`) records `revBefore`/`revAfter` for the ArrowDown, but nothing reads them. The table probe's own history has run-1 sending every key to `<body>` (comment at `:76-77`).

**Case.** If the ArrowDown does not move the caret, `cell-press-type` types `kj` at the end of paragraph 0. That is the `before-table` shape, where D is exact on every page, and every rule still holds. Synthetic M1 shows it:
- Built from `baseline-0.2.16/table/report.json`, with `cell-press-type`'s reader fields set to `controlParagraphs [0]`, `markParagraphs [0]`, `controlThenMark true`, and `cell-hold` set to its fixed-page outcome.
- The judge exits **0, verdict PASS**, although the page under that report is `6470dec0` with 136 in it.

`cell-hold` is not exposed, because `after_at("end", 1)` pins paragraph 1.

**Fix (rule only; the field is already recorded).** Require `controlParagraphs == [want]` on the press-type arms: `[1]` for `cell-press-type`, `[0]` for `before-table-press-type`, and `[last]` for `end-press-type`, which `mark_at_end` already half-covers. With counts `controls 1`/`marks 1` and contiguity, that pins `kjzqx` to the paragraph the arm is about.

## NOTE

### N1. The `scrollTop` window cannot close before the jump on this page, but nothing after its close is judged

**Where.** `judge_held_into_refusal.py:180-191` and `:194-207`.

**Checked against `aebef525`.**
- The window opens at the first `restart-required`. `reopening` is raised only after that state (`e2-editor-app.js:1672`), and the fresh engine's start caret can only arrive after `session.restart()`, which comes later. The opening is therefore early enough.
- It closes at the first sample whose toast contains 「已重新載入」. That toast (`:1732`) is set in the same microtask as `reopening = false; followCaret();` (`:1740-1741`), and the MutationObserver records the sample only after that microtask. **The closing sample already carries the explicit follow's `scrollTop`.**
- `placeCaret` resolves only after its `editorState` has been written (`editor-session.js:307` then `:314`). So the explicit follow sees D's caret, not the fresh engine's.
- No other toast in the reopen path contains 「已重新載入」. 「正在重新載入」, the ceiling sentence, and `run()`'s 「重新載入：…」 on failure do not, so a failed reopen leaves the window open, which is a FAIL.

**Not covered.** An excursion after the toast is not judged. Synthetic M2 shows it: the end rounds of `baseline-0.2.16/held/report.json` with the window held at `pre`, plus one sample at 0 right after the closing sample and one back at `pre` 700 ms later. That report exits 0. I found no page path that produces it.

**Cheap to close.** Judge every sample from the refusal to the end of the log. On the baseline the post-window values are 21477/21596 (Chrome) and 21463/21582 (Firefox), all ≥ `pre`, so no correct end round would turn red.

The 0.5× threshold and the `pre > 0` precondition are sound: the fresh engine's caret is the document start, so the jump goes to 0, and `pre` 0 would make the rule hold for any page. The added `#desk` `scroll` listener only reads, and it catches any excursion that lasts into a frame.

### N2. `pre` is the last sample before `restart-required`, not `stateBeforeKey`

**Where.** `judge_held_into_refusal.py:188`.

A view moved between the key and `restart-required` would become the reference. That interval is where K1's state is written and followed, with `reopening` still false. At the document end K1 selects nothing, so both end arms are unaffected today. Also requiring `window ≥ 0.5 × stateBeforeKey.scroll` would close it at no cost (baseline: the same values).

### N3. Coverage the arms do not have; both are covered only by unit tests

- **FIFO head against "last delete sent"** (G1 (v)) is not exercised by any arm:
  - `cell-hold`'s only delete is refused at 46 ms (Chrome), before the first repeat at 500 ms.
  - `before-table-hold` does send a second delete while the first is out, but both send-time carets are the end of paragraph 0.
  - The race rests on U-136b alone.
- **A held Backspace into a cell start** (see B1 (iii)) has no arm.

### N4. The run-3 fallback is sound and unreachable for new reports

**Where.** `judge_held_into_refusal.py:77-83`.

- `server_read` always sets `controlThenMark` (`probe_held_into_refusal.py:142`). No current probe writes `run["control"]`, and a run without `server` is `fatal`.
- Even where the fallback is taken, it cannot make an arm pass. Every rule includes `counts(...)`, which needs `controls`/`afters`, and run-3 has neither (red (a): `controls not recorded` on all four press rounds).

### N5. The zero-count rule for untyped marks is sound and necessary

**Where.** `judge_held_into_refusal.py:115-123`, RULES `:224-233`.

- **Necessary.** `strip_marks` removes `zqx`, then `kj`, then `wvy` (`probe_held_into_refusal.py:121-124`). A `kjkj`/`kj` residue of `start-hold`'s `kjkjk` would vanish from `sameAsOriginal` and is caught only by `controls ≠ 0`. A single `k` residue is caught by the difference.
- **No false FAIL found on a correct page.** `keyed()` waits for a quiet session before and after every character (`check_m3_production_ui.py:277-286`). So the finding-111 loss, where `kj` is still queued behind the key, cannot happen in these probes. The owner's document and the fixture hold no `kj`, `zqx` or `wvy`: checked here, and enforced per run by `marksInOriginal`.

### N6. Tool closure and non-vacuity: verified

**Where.** `judge_held_into_refusal.py:69-74` and `:281-321`.

What holds:
- The probe is chosen by `report["probe"]`; an unknown probe is a FAIL.
- `ARMS` is read by `ast` from that probe: a tuple in the held probe, the dict keys in the table probe.
- A declared arm without both a rule and a minimum is a FAIL, and so is a run of an undeclared arm. Red (c) confirms this for both probes.
- Every browser in `--browsers` needs at least the minimum number of rounds per arm, and a `fatal` round counts as a FAIL.
- A partial report fails on `staticAfter`, because the probes rewrite `report.json` after every round.

Two operator-side caveats:
- `--browsers chrome` drops Firefox from the requirement (`:276`), and the verdict line does not say which browsers were required. Printing them would make it visible.
- Each report is judged separately, so condition 3 needs **both** invocations. Nothing joins the two verdicts.

### N7. A correct page failed for a reason unrelated to the fix: none found

Checked:
- The start arms' "every sample 0" against `IN_TEXT`, which is within the first screen (baseline series `[0]`).
- The closing toast text in `aebef525`, both sentences, with and without `restored`.
- The explicit follow on the end arms, where the restored caret is the pre-refusal key or in view, so there is no scroll.
- `one_reopen` against B, where `deleteRefusedThisHold` drops the post-reopen repeats.
- The table arms' paragraph indexes (`kj` in [1] on `cell-press-type`, both browsers, both runs).
- The before-table "uncertain" path, where the document is kept.

The only red I expect on 0.2.17 is B1, and that one comes from the fix.

## Answers to the brief

1. **Green while broken.**
   - **136 unfixed:** caught by `cell-press-type` and `cell-hold` (4/4 + 2/2 on `6470dec0`), except when the ArrowDown fails (S1, reachable, exit 0).
   - **Flash:** caught inside the window. Only an after-toast excursion escapes (N1), and I found no path for it.
   - **Wrong offset in the right paragraph:** caught on every arm, including `start-hold` for a single glyph on this document (B1). B1 itself is such an offset, coming from the fix.
   - **B broken:** caught, because the post-reopen repeats would be refused a second time and the judge requires exactly one refusal.
   - **D broken:** caught on every non-start arm. On the start arms it is invisible by design.
2. **`scrollTop`:** the window is sound for this page (N1). The 0.5× threshold and `pre > 0` are sound. The added scroll sampling is adequate. The window does not judge after its close (N1), and `pre` is not tied to `stateBeforeKey` (N2).
3. **Rules beyond the ruling's text:** both are sound. The fallback is unreachable for new reports (N4, N5).
4. **Closure and non-vacuity per browser:** they hold (N6). Fix S1 so that each press-type arm is pinned to the paragraph it names.
