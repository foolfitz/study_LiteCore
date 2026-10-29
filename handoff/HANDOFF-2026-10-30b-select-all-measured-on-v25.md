# Handoff: select-all measured on v25 with its gesture granted (work order v26, deliverable 1 done)

Checkpoint **2026-10-30 ~01:20 +0800**. Supersedes `HANDOFF-2026-10-30-finding-173-fixed-host-0241-installed.md`
as the entry point; that file still holds for everything it says that is not superseded here (state of host 0.2.41,
generation 79, its cautions). Study HEAD **b5d3b9834** plus the commit that adds this file. Tree clean except the
unrelated untracked `codex-claude-code-delegation.md` (preserve it). **Nothing is running.**

## State

Unchanged from 10-30: host **0.2.41** installed on the owner's DDEV (daily uncounted candidate; nominal shipped
0.2.26), `dist/` serves page `9cb6ea1f…` (generation 79, profile `e2-editor-v25`). K has not run. Nothing in
`dist/`, no profile, no generation and no host package changed this round.

## Done this round

1. **Work order v26 select-all, deliverable 1, questions 2-3 measured** (`findings/evidence/select-all-v25/`,
   README in English; research note part 2 in `research/2026-10-29-select-all-route-on-v25.md`, zh-TW).
   Harness path: select-all posted to the document worker directly on a symlink mirror of `dist/` with a scratch
   manifest (all three gestures; also collapsed-only and the shipped withheld manifest as products). Chrome.
   run-01 46 runs, run-02 8 bold runs (final ODTs kept). Findings:
   - From body text select-all selects the whole document: ends = document start/end carets, copy holds every body
     paragraph and cell in order, the page draws the wash, revision unchanged, `changed:false`. The reply is
     composed after the selection callbacks in the same poll (59/59 ok selection replies equal the later state).
   - Follow-ups over the whole range: typing replaces everything (tables, frames, notes go; the FIRST paragraph's
     style stays), real Backspace goes out as `delete-selection` and empties the document, bold reaches every body
     paragraph and cell, undo restores in 2 steps. Blank document (finding 173's): ok/collapsed, nothing breaks.
   - Limits: a range holding an as-char frame copies as `complex` with no text (copy throws, cut stops before
     deleting -- read, not run); note bodies are not in the copy but are deleted with their anchor; a grant needs
     BOTH range bits (collapsed-only refuses the second press; caret in a cell = cell -> table -> document, three
     presses); `delete-selection`'s manifest limit `not-characterised-in-tables-or-note-apparatus` is met by every
     whole-document range.
   - The 2026-08-19 geometric-range failure does NOT reproduce on v25 (it selects the whole document); constructed
     controls `degenerate` ((0,0)-(1,1): ok, collapsed) and `partial` (first line) are rejected by the summary's
     predicate. The list-contexts `partial-bold` control is confounded by its bold-by-named-style heading (B turned
     bold OFF; recorded, not re-judged); table-boundary's is clean.
   - The page's `selectionShape` belief stayed `collapsed` after all 53 harness selections -- the page path must
     update it from the reply.
2. Question 4 (page binding) is planned in the note, not implemented: `select-all` into the client's `APPENDED`
   with the existing "move" postcondition (both completions seen are the two it accepts), Ctrl+A/Cmd+A only when
   `session.offers("select-all")`, `lastSelectionShape` from the reply, honest wording for a blank document.

## Next steps

1. **Owner's hand test on 0.2.41** (still open from 10-30 step 1; asked again this session).
2. **Owner decision asked this session**: ship select-all (A) with the v26 engine batch as decided 10-29 -- but
   nothing else is queued for v26 -- or (B) as a manifest-only successor profile + new shell generation + page,
   no relink, in the next host. Either way the next deliverable is the zh-TW spec with pinned criteria and red cases
   (work order "Then" plus the additions in the note's 2026-10-30 paragraph: a collapsed-only grant must be red; a
   page whose `selectionShape` stays collapsed after select-all must be red; frame-document copy needs an honest
   failure; Firefox).
3. Still open: K; the `what_the_link_ships` census; spec v25 section 2/10 leftovers; `capture-after.py`'s named
   limit (10-30 handoff).

## Cautions

All of 10-30's, plus:
- `measure_select_all.py` writes only `--out` (must not exist) and a mirror under `wasm_sdk_probe/build/` that it
  deletes; it never writes `dist/`. Its scratch manifests keep `profile: "e2-editor-v25"` because the worker keys
  the ABI6 extend moves on that name -- a real successor profile must change that name AND the worker check
  (`featureExtendPermitted`, `sdk/v25-feature-worker.js`) or the extend moves silently stop being permitted.
- run-01's `final.unchanged` compares text only; do not cite run-01 bold rows for formatting (use run-02).

## Section 34.4 this round

Fixed-by-execution **0**, fixed-by-review **0** for existing checks (none was changed). The new research tool was
changed twice by its own runs (listed in its README: controls after shake-01, bold reading after run-01).

## Language

Replies to the owner: Taiwan Traditional Chinese (A/B/C for options). Evidence, upstream text and `handoff/**`:
English. `devlog/`, `research/`, `specs/`: zh-TW (specs append-only once pinned).
