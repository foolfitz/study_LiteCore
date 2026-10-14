# Ruling brief 7: review 6's open items, part 2's open items, §34 on part 3's checks, the stack sweep, and the v20 Makefile block

**Authority:** the owner, 2026-10-14: 「我授權fable代我做決定，Makefile 草稿也交給他」. This round the Makefile
answer is yours too. Until now every Makefile change went to the owner first (finding 042: any Makefile edit
makes every object that lists `Makefile` as a prerequisite stale). The owner has now delegated that answer.
Linking, pushing and deleting stay out of scope. The link is the owner's step.

**Inputs (read these, not my summaries):**
- `handoff/HANDOFF-2026-10-13g-v20-part2-and-review-6-landed-dispositions-pending.md` (the state)
- `findings/evidence/link-batch/review/review-6-engine-code.md` (review 6, opus, no BLOCKING) and `review-6-artifacts/`
- `findings/evidence/link-batch/v20-part2/README.md` §3 (scheduler) and §4 (C on the page)
- `findings/evidence/link-batch/v20-part3/makefile-v20.patch` (96 lines, not applied)
- `specs/SPEC-M3-link-batch.md` §12–§13 (rulings 2–4) and `specs/SPEC-M3-paragraph-merge.md` §34 (the stop rule)
- `findings/evidence/link-batch/review/ruling-5.md` (finding 137 broadened; the ordered-commands spec, candidates A/A′/B/C)

Line numbers are for HEAD `f1f75e88` unless stated otherwise. `wasm_sdk_probe/` is the root for relative paths below.

## Facts I checked this session (each one is a claim for you to attack)

- **F1.** In review 6 §1.2 (native, 3/3 each), K1 changes nothing that the barrier can see in any of these three positions, while Writer's own key changes the document:
  - (i) Delete in front of a numbering label;
  - (ii) Backspace at the document start, first paragraph bulleted;
  - (iii) the same, first paragraph with a first-line indent.

  v19 answers `nothing-selected` (reopen, toast). v20 answers `verified-boundary-noop` after about 2.25 s, silently. In (i), the caret also visibly jumps past the label.
- **F2.** K1 gives no callback in (ii), (iii) or the plain control (a document start with no numbering and no indent). K1 alone therefore cannot tell (ii) or (iii) from a true boundary (review 6 §1.2 table, rows 2–4).
- **F3.** Ruling 5's candidate A for the ordered-commands spec is "the user's own key, FIFO, proved by the `.uno:Undo` payload". Under A, Writer's own edit happens in all three positions. My claim: any residual registered here therefore has a named closure.
- **F4.** `editor-shell/editor-session.js` is E1-C-bound. I ran `python3 tools/check_e1_c_bundle_intact.py` on 2026-10-14 and it printed `intact: true`; the file names both bound files at :11–12. Finding 068's fix was a subclass override for the same reason. A Q4 fix in the base class unbinds `E1_GO_ODT_EDITOR`.
- **F5 (new; review 6 does not say this).** In v19, a lone `LOK_CALLBACK_INVALIDATE_TILES` already advances `sourceSequence`: `src/probe_engine.cpp:2593–2596`, outside the v20 define (`editorStateChanged = true` unconditionally, then `++gEditorState.sourceSequence` at :2678). The base class's own comment says so too (`editor-shell/editor-session.js:379–381`: "It also advances for callbacks that have nothing to do with the caret (a tile invalidation, say)").
  - Consequence: a tile invalidation arriving inside the click's 22–28 ms already ends a same-line `placeCaret` wait early on v19, and so on 0.2.12 and 0.2.18. That is the `onTarget && acknowledged` branch at :426.
  - Review 6 §4.3 names only the insert reply's late caret as v19's existing trigger, and its harness's v19 arm models no tile bump.
  - So review 6's first fix option ("don't count an advance whose only difference is `documentSizeChangedCount`") would leave the tile trigger in place. Its second option ("require `caretMoved` before the grace period ends") covers both triggers.
  - **Not measured:** whether a lone tile invalidation (online spelling, idle layout, anything with no caret callback beside it) occurs on WASM inside a click's window. I also have not measured the second option's cost: a same-line click whose answer leaves the caret rectangle unchanged waits `graceMs` (400 ms) instead of returning on the acknowledgement. Examples are an identical-point click, or perhaps a click that only collapses a selection at its caret end.
- **F6.** Part 2's scheduler consumes a failed read's trigger (`editor-shell-v2/narrow-editor-v2-session.js:328–337`). On failure, `_issuedAt` stays at the counter the read was issued at. Every later push with that same counter returns early at :289. So after a BUSY (a push that arrives during a merge re-reads into a BUSY, review 6 §3), the page-number line stays hidden until one of three things happens: the counter changes, the document reopens, or a paint reply carries `documentSizeChanged`. Review 6 §3 requires a re-read after BUSY. The smallest change I see is `this._issuedAt = null` in the error branch: the next push of any kind then re-reads, so retries are bounded by pushes. Pushes that arrive while a read is in flight are already covered by `_again` (:290, :308, :335).
- **F7.** `tools/check_profile_identity.py` (X1) requires three things: the worker byte-identical to the reference's (:82–83), byte-identical export lists (:85), and every manifest leaf equal except the profile names and link outputs (:13). A correct v20 against v19 is therefore red on `worker`, `exports` and `manifest` (the new `editorContract.pageRectangles` leaf).
- **F8.** Part 1's claim "v15 and v19 objects rebuilt from this source are unchanged" rests on `check_merge_key_undo_scope.py --base 5d77dc84`. That run shows only that the two existing carriers differ from a base that is older than the merge work. It does not show that part 1 left them unchanged. Showing that needs base = `82af92ca^`. **The Makefile patch's own comment repeats this unestablished claim** (patch lines 13–15: "v15's and v19's objects rebuilt from this source preprocess as before (tools/check_merge_key_undo_scope.py)").
- **F9.** §34.1's freeze window (BINDING set → v19's X7 read) has closed: v19's X7 was read on 10-08f. §34.4 still applies, so a check change needs a witness, which is an honest committed report the check misjudged.
- **F10.** Every frozen product link in `Makefile` calls `refuse_unasked_relink` (`:880`; v15 :1266, v19 :1486, and so on). After the block is applied, a bare `make` on a frozen target recompiles that target's objects, because `Makefile` is a prerequisite, and is then refused at the link. The frozen `dist/` bytes do not move. My claim, unverified: those recompiled objects are what `check_merge_key_undo_scope.py` would compare, so the M1-1 witness run has to be read with this in mind.

## Questions (rule on each; my lean and why are given, attack them)

**Q1 — review 6 Q1, C's window on (i)/(ii)/(iii).**
- A: register a named residual (for example `L-C-number-or-indent`) beside L-C-late-K1, with ordered-commands candidate A as its closure (F3), and name it in the v20 release text.
- B: for (i) only, refuse when the caret moved during the window. That is about three engine lines under the define, and it needs a red case. It does not reach (ii) or (iii) (F2).

*My lean: A.* B gives back v19's answer for (i), but v19's answer is a reopen plus a toast, which still does not do Writer's edit. B would also be an engine change landing after review 6 with no review of its own. Also rule: do (ii) and (iii) need anything beyond the residual? Under v19 and v20 alike the product does not do Writer's edit. The difference is a toast against silence, plus about 2.25 s of waiting.

**Q2 — review 6 Q4, `placeCaret`'s acknowledgement test.**
- Rule which fix, given F5: exclude size-only advances, or require caret evidence on the same line.
- Rule where it goes. F4 says it goes in a `NarrowEditorV2Session` override, but check that.
- Rule whether it lands before the shell freeze (it is page/shell, no relink).
- Rule whether the pre-existing tile-invalidation trigger on 0.2.12/0.2.18 is a new finding or belongs to an existing one (048? 137?).

*My lean:* option two (caret evidence, which covers both triggers), as a subclass override, before the freeze. Register the tile trigger as a finding with "not measured on WASM" stated. Measure the 400 ms grace cost natively or in the harness before choosing, if you think it could matter.

**Q3 — part 2 §4, a `verified-boundary-noop` delete counts as a mutation.**

The measured chain (part 2 README §4) is: dirty, then a content stamp, then a checkpoint `save()` on the next boundary move, then a host autosave of unchanged bytes. The dirty pill also reads as edited.

- (a) Apply README §4's roughly ten lines (`_enqueueOwned`, so the operation can flip its own item's `mutation`). This needs a pin test for the second private seam of the frozen base.
- (b) Register the chain and leave it.

The precedents are findings 098 and 099: a non-mutation marked as a mutation, and revision used as a stand-in for content. Both were fixed. *My lean: (a).*

**Q4 — the scheduler after BUSY (F6).**

Apply the one-line `_issuedAt = null` on failure, with one test, red first? Or another rule? *My lean: apply it.* It is a product change, not a check, so §34 does not apply to it.

**Q5 — §34 on part 3's checks (F7, F8, F9).**
- X1's optional declared deltas: `--declared-worker SHA`, `--declared-new-leaf PATH=VALUE`, `--declared-export SYMBOL`. With none given, the behaviour is unchanged.
- M1-1's per-carrier object sets, plus a run with base `82af92ca^`.
- A `what_the_link_ships.py` `link-batch-v20` variant (data only, `--since c0337ae3`).

Rule whether each of these is a new use for a new identity, or a repair that needs a witness.

*My lean:*
- X1's deltas are a new use: no committed judgement changes, and the default is identical.
- M1-1 is a repair. Its witness is the red report from the first run after the Makefile block is applied. Commit that report before changing the tool.
- `what_the_link_ships` is data.
- The Makefile comment's F8 sentence is corrected (Q7).

**Q6 — 10-13f Next 7, the Writer stack sweep (spec §12.6), pre-W8, no link.**

The lean from 10-13g:
- Make a separately named diagnostic profile directory: a copy of the shipped Writer profile, with `probe.js`'s stack literal patched the way `90fed9b7` patches it, and its manifest's `profile` and `loaderSha256` rewritten.
- Run it through the unmodified product-path runner's `--profile`.

Open: how to show the patch took effect without `probe_ods_on_profile.py`'s echo. One option is to carry the same echo anchor in the diagnostic copy, if the runner records worker console output (I have not checked). §12.6's default if this is never done: W8 carries the obligation, and this batch is unchanged.

*My lean:* the approach above, scheduled after the link, because nothing in v20 waits on it.

**Q7 — the v20 Makefile block (`makefile-v20.patch`).**
- A: apply as drafted.
- B: apply after the dispositions above are applied in the source.
- C: amend it.

Dependencies:
- A Q1 B changes `src/probe_engine.cpp` under the same define. The block is unchanged, but the source must be final before the owner links.
- The pinned worker sha256 (`478d0da1…`) moves only if a disposition touches `sdk/sdk-worker.js`. None of my leans does.
- The comment carries F8's unestablished sentence.

*My lean:* B with the comment corrected, then the M1-1 run with base `82af92ca^` straight away. That run is Q5's witness. Also check: does anything else in the 96 lines strike you as wrong? For example, the dependency list, or `--inline-range-gestures all` carried over from v19.

## Output

Write `findings/evidence/link-batch/review/ruling-6.md` in the shape of `ruling-5.md`:
- `## RULING`, one subsection per question;
- `## WHY (for the owner)`, in 台灣正體中文, plain words, one paragraph;
- `## FACT CHECK`, a table of the claims you relied on, each with status and where it is;
- `## CONDITIONS`, numbered from 42 (ruling 5 used up to 41).

Do not edit any other file, do not commit, and do not build or link anything. Scratch runs go to your scratchpad. Return a SUMMARY of at most 30 lines.
