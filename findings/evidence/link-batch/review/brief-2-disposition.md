# Ruling brief 2 — dispositions for review 1 of SPEC-M3-link-batch, and the owner's open questions

**Authority:** the owner, 2026-10-13: 「有疑義的發給fable，我授權它代我下決定」. You rule on the owner's behalf.
Link steps, pushes and deletions are excluded.

**Reply with these parts:**
- `RULING`: one entry per item below.
- `WHY (for the owner)`: Traditional Chinese (Taiwan), plain language, at most 10 sentences in total.
- `FACT CHECK`: for each fact or claim you relied on, confirmed / refuted / not checked, with file:line.
- `CONDITIONS`: numbered and checkable.

Write it to `findings/evidence/link-batch/review/ruling-2.md`. Commit only that file, with an English message
ending `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and no `Claude-Session:` line.

**Inputs:**
- `specs/SPEC-M3-link-batch.md` at `b5f2e812` (zh-TW). §9 is the completion rule.
- Review 1: `findings/evidence/link-batch/review/review-1-spec.md` (`cf0e15d2`): 3 BLOCKING, 12 SHOULD, 11 NOTE.
- Native data: `findings/evidence/link-batch/extend-signatures/` (`81eaf66d`).
- Prior rulings this must stay consistent with:
  - `specs/SPEC-M3-paragraph-merge.md` §3.2, the transition rule. A key's evidence is only a callback that
    differs from what was known at dispatch.
  - The same spec's §15.1 and §16.1, where "every step leaves a trace" was ruled, and "any rectangle change can
    forge a cursor".
- §34 of the same spec (the owner's rule on checking machinery) applies. Checks guard honest accidents only;
  no new machinery unless a criterion would pass a broken product in an honest run.

**The main session's verification of the review** (main session, 2026-10-13):
- Confirmed:
  - merge spec §3.2 (lines 80–90) and §16.1 (lines 526–533) say what the review quotes;
  - `handleInsertText` answers `inserted` synchronously after `paste()` and waits for no callback
    (`probe_engine.cpp:3186–3221`);
  - completion runs per callback, right after the cache update (`probe_engine.cpp:2655`).
- Not checked by the main session:
  - S-5's 16-versus-18 count;
  - the worker's line-move refusal (S-1);
  - the page branch claims (S-2);
  - every page-number item.

## Items to rule on

### B1 — what an extend, and a move that starts on a range, may complete on

The main session's §9 rule (complete on `INVALIDATE_VISIBLE_CURSOR`) is withdrawn: it is the rule §3.2 already
rejected. The candidates the main session sees, all to be attacked:

- **(a) Transition rule only.** Accept a cursor callback only after a `TEXT_SELECTION` whose payload differs from
  the selection cached at dispatch (the review's remedy i).
  - Native: every changing cell has exactly one such `TEXT_SELECTION`.
  - Hole the main session sees: a preceding operation that completed before its own flush AND changed the
    selection. Typing over a range, and the merge key that completes by polling, both qualify. Their late
    flush carries a differing `TEXT_SELECTION` followed by a cursor, which (a) would accept for the extend
    before the extend's key runs.
- **(b) (a) plus "no move or extend is posted while an earlier synchronous completion's flush is outstanding".**
  The engine already knows which completions were synchronous. This needs a defined "flush seen" signal. Is
  there one that cannot be forged? For example, the cursor callback following the insert's own text change, or
  `documentChangeSequence` advancing.
- **(c) Make the engine's answer independent of callbacks for extends:** after the key, complete by polling a
  synchronous read (`getTextSelection` text/type) until it differs from dispatch, like the merge key's
  `.uno:Undo` poll.
  - Cost: `getTextSelection` takes the SolarMutex.
  - Gain: it reflects core state, not flush timing.
  - Hole: a poll result can still be the previous operation's effect if that operation was not yet applied
    in core.
- **(d) Narrow this link's scope:** ship page number, C, the 136 items and the count now; keep Shift+Arrow and
  range moves for a second link with their own design. The owner asked for Shift+Arrow explicitly.

Also rule on S2's added population, the review's remedy ii:
- insert then Shift+key with no wait;
- merging Backspace then Shift+key;
- Shift+Right held for 1 s.

Should these be product-page runner arms, or model-test sequences in `tests/merge_key_undo_model_test.cpp`?

### B2 — the delete routed from a mid-flight snapshot

The main session's lean is to accept both parts:
- The page chooses the delete form (`delete-backward` or `delete-selection`) when the queued item runs, not at
  `beforeinput`. Alternatively it counts moves and extends in flight.
- New criterion S5: Shift+key immediately followed by Backspace, Delete, or a typed character. The saved
  document must equal Writer's for the same sequence.

Rule on which page mechanism (late binding versus an in-flight count), and whether S5 is a tool-closed
enumeration over S1's cells or a fixed short list.

### B3 — C's late Shift

The main session's lean is to accept the review's remedy:
- After the first NONE, keep the transaction open for `MergeStepDeadlineMs`. If a non-empty `TEXT_SELECTION`
  arrives, refuse as today (`unit-late`, reopen). Otherwise complete as a no-op.
- Drop the 「收回成 barrier 之前的游標」 clause.
- C1's busy arm becomes a per-completion criterion: at least 500 ms after every no-op completion, the engine's
  `editor-get-state` reads selection NONE.
- The residual (K1 slower than the window) becomes a named limit.

Is that window long enough, given finding 135's roughly 200 ms worker stalls?

### SHOULD S-1 to S-12, and the NOTEs

The main session's lean is to accept them all as written, except as follows. Overrule any of them.

- **S-4:** S2's reference becomes "the engine's editor-state cache at least 500 ms after completion, read with
  `editor-get-state`". That is the engine side, not the page snapshot. §9's "still right, only slow" sentence is
  struck.
- **S-5:** the v19 red prediction is re-derived from the source before use; the count is whatever the
  derivation gives.
- **S-9:** existing 134/136 guard arms that C turns red by design are listed in §7 before the count, with their
  new expected values. They are not discovered red during the count.
- **S-10:** M is asserted as 60 by construction on the 60-page fixture. The page-centre oracle is computed
  from the rectangles and the viewport actually used. The page re-reads rectangles when the engine's
  `documentChangeSequence` advances, not only on `documentSizeChanged` from a paint. Also correct the
  Collabora read-only claim: `Parts.js` only serves prev/next.
- **S-12:** held Shift+arrow gets the same pacing as finding 132's held delete. Repeats that run ahead of the
  engine are not sent.

### The owner's open questions (spec §8)

- **Q-A:** where the page number goes. The main session leans towards a bottom status line, Collabora's place,
  shown in the host too.
- **Q-C:** whether item 2 (moves on a range go to Writer) ships in this link. The main session leans yes. Per
  S-2, the manifest change flips the page's 129 branch anyway, so "keep 0.2.13's prescription" would itself
  need new page code.
- **Q-D:** whether the page number should be core-computed (forward `.uno:StatePageNumber` after telling core
  the visible area). The main session leans no: it costs an engine call per scroll, and the strings follow the
  build's locale.

### Order

After the ruling, the main session will:
1. write the dispositions into the spec as an appended section;
2. send the revised spec to a second review only if your ruling says so;
3. then implement.

Say whether a second review is required before code.
