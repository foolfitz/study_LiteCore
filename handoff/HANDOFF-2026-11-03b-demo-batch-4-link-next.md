# Handoff: demo batch 4 ready, the owner's link is next

Checkpoint **2026-11-03 02:15**. Supersedes `HANDOFF-2026-11-03-demo-batch-3-done-0251-installed.md` for what is next. K's numbers in `HANDOFF-2026-11-02b-k-0245-holds.md` stand.

## State

- **Nominal shipped: 0.2.45** (K holds). **Installed on the own stack: 0.2.51**, the owner's hand test passed on 2026-11-03. Whether it becomes the daily candidate is still the owner's.
- **Demo batch 4 is done up to the link.** `specs/SPEC-P-demo-batch-4.md` sections 5 to 7, `findings/evidence/demo-batch-4/README.md`.
- **Nothing of ours is running. Nothing is pushed.** The owner went to sleep without saying "幫我建置", so the link was not run.

## Next

1. **The owner's link**: `handoff/RUNBOOK-relink-v32.md`. One line from `wasm_sdk_probe/`: `bash tools/link_demo_batch_4_owner.sh`, about 3 minutes. An agent runs it only on the owner's word in that session.
2. Everything after the link is in the runbook: archive, assets, P4, P4's red cases, P1', cutover, generation 87, the chain, host 0.2.52, the hand-test list.
3. Ordered-commands product arms; Microsoft formats and Calc zoom only when asked.

## What changed from the plan in spec section 4

The plan was a one-character read and a bare dispatch. Neither survived measurement. All paragraph actions on v32 use one read, `probe::writerSelectionParagraphs` in the new unit `src/writer_caret_bridge.cpp`, which walks `XModel::getCurrentSelection()`'s paragraphs and selects nothing. So there is no restore and finding 180 goes away by construction. Toggles choose between the existing setters from that read. Details and reasons in spec section 5.

The new unit is the one real unknown: **the bridge has only ever run natively.** `-fsyntax-only` passes on the Wasm core's headers and `pre-link/symbols.json` finds its two sfx2 symbols in the archives, but its cost on Wasm is unmeasured. Read the first press's latency in P4 before anything else.

## Two shipped defects found on the way

Both on the page as installed, both browsers, `before-v31/run-01`.

- **Finding 182, high.** A range from inside a paragraph into the next, press 標題: the style lands, the page reports `EDITOR_FORMAT_POSTCONDITION_FAILED`, the session goes `recoverable-error` and save is gone. Unsaved work is lost. In the line since E2-B, so 0.2.45 carries it. Fixed in v32.
- **Finding 181.** A selection at a paragraph's start, press 標題: core builds an inline heading frame (`SwDocShell::MakeInlineHeading`). Fixed in v32 by widening to the paragraph.

Until the link, tell anyone demoing: start a range at the paragraph's start, or save first.

## Limits

`L-number-on-heading`, `L-table-in-selection`, `L-list-style-levels`, `L-none-list-level`, `L-numbered-heading-state`, and the read's limit of 500 paragraphs. Spec sections 5 and 7. `L-align-blank-document` and the blank-document prompt are retired: the read works there. Ruling 3's premise was that nothing could be read, so this removes the premise, it does not reverse the ruling.

ABI stays 6. `set-paragraph-heading` keeps its `heading-level-1-only` limit; the toggles do not carry it.

## Cautions

- **The tree is ahead of `dist/` on purpose**, as before batch 3's link: `web/e2-editor-*`, `editor-shell-v2/*`, `sdk/v32-paragraph-read-worker.js`. Do not run `make e2-c-assets` before the link. `check_writer_zoom`, `check_writer_shift_lines` and `check_writer_align` read the page from `web/` and the shell from `dist/`, so they fail at import until then.
- `tools/check_writer_toggle.py` has run only T9 and T10, on the preview. Its first red on an engine is the tool's until shown otherwise.
- A stopped LOK harness leaves `.~lock.<name>#` beside the document. The next run opens read-only and every command silently does nothing while every read agrees with the file. `native-caret-read/run.sh` copies the fixtures per run; do the same.
- `pkill -f` or `pgrep -f` with a pattern that is also in your own shell's command line hits your own shell. Use PIDs, and `tail --pid` to wait.
- N2's `para-start` and `list-start` places are not at a paragraph's start (`.uno:GoLeft` moves from the point). Do not cite them for that.
- `cancel-today/` and `before-v31/` are the shipped page. `preview/` is the v31 engine with a forced `offers` test: nothing there is evidence about an action.
- Use absolute paths; a shell `cd` carries between calls.

## Section 34.4

Work since 11-03.

- **Fixed-by-execution: 8.** A stale lock made a whole N4 part read-only. N2's places. A doctored manifest the binary refuses, replaced by forcing `offers`. N4's reader twice (FOXTROT's own X, nested lists). The bridge line in the contract's define check. The bridge object in the rule M1-1 walks. Chrome's CDP key firing no default click. A limit I wrote from misreading `preview/run-01`, retracted in spec section 7.
- **Fixed-by-review: 8.** All Codex's, one round: the read's limit, review for the three shapes, focus after a keyboard press, the menu on an unavailable session, and four groups of acceptance cells (bullet against number, whole-document compare, the notice read before the save, the exact wrapped position).
- **Fable rulings: 0.** Nothing needed one.
- Wrong statements, corrected: 2. The first-broadcast limit above. Finding 180's stated fix.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs and findings in zh-TW. Compiling `make` and the link stay the owner's unless they say otherwise for that build. Commit messages: `Co-Authored-By` yes, `Claude-Session` never.
