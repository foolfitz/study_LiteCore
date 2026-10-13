# TASK 2026-10-13h — link batch, native step: what does core broadcast for Shift+Arrow, and for a plain arrow on a range?

Plan: `handoff/PLAN-2026-10-12-link-batch-shift-selection-and-page-number.md`, item 1 ("measure the barrier's
candidate signatures natively before writing the engine side") and item 3 (moves on a range). Native only:
no browser, no profile, no product bytes. Evidence: `findings/evidence/link-batch/extend-signatures/`
(English).

## Why (what the engine does today — read in source)

`wasm_sdk_probe/src/probe_engine.cpp` ~5420–5510: a move action posts one key (KEYINPUT + KEYUP);
`extend` adds `KEY_SHIFT` (0x1000). Completion is the FIRST matching callback
(`completePendingEditorOperation`, ~2155): a plain move completes on `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`
or `LOK_CALLBACK_TEXT_SELECTION`, whichever comes first; an extend completes on `LOK_CALLBACK_TEXT_SELECTION`
only; if nothing arrives, a readback deadline completes it as `verified-move-readback` (finding 096). The
completion serialises the engine's cached state at that moment. So the engine's answer is right only if
the callback it completes on is the LAST one that changes the state it reports. Today the ABI accepts
`extend` only for the two character moves, and the manifest grants all six moves `collapsed` only; the link
would widen both. Before writing that, we need to know, for each starting shape and key:

1. which callbacks core emits after the key, in what order, with what payloads, and how long after the post;
2. whether `TEXT_SELECTION` arrives in every cell where the selection changes — including when an extend
   SHRINKS the selection to nothing (does it arrive with an empty payload, or not at all?);
3. whether `INVALIDATE_VISIBLE_CURSOR` (the point) arrives BEFORE or AFTER the last `TEXT_SELECTION`
   (if after, an engine completing on `TEXT_SELECTION` reports a stale caret — the finding 084 shape);
4. whether any cell emits MORE than one `TEXT_SELECTION` (completing on the first would report an
   intermediate state);
5. which cells emit nothing at all (they need the readback path);
6. for a plain (unshifted) key on a range, the same four questions (item 3);
7. whether a Shift+key leaves Writer in a state that breaks the NEXT product selection (finding 039/043:
   `SwWrtShell::m_bInSelect` left set makes a later `setTextSelection` END select nothing).

## Instrument

New `wasm_sdk_probe/tools/link_native_extend_signatures.cpp` + `run_link_native_extend_signatures.sh`,
modelled on `tools/f129_native_arrow_on_selection.cpp` and `tools/run_f129_native_point_click.sh` (same
build line, same install `native-lok-26-8/build/instdir/program`, `SAL_USE_VCLPLUGIN=svp`, each round its own
process and profile, fixture copies per round, `inputs.sha256`, `tool-source-as-run.cpp`). Record in the README
the git commit of `native-lok-26-8`'s source and of `libreoffice-26-8` (the WASM core's source), and say
they differ if they do.

Callback recording: register a callback that appends `{type (numeric AND name), payload (≤ 400 chars),
tMs since the key's KEYINPUT post}` for EVERY callback type, under a mutex. After posting the key, wait
1500 ms, then snapshot the list. Record the last callback's `tMs` and whether anything arrived after 300 ms.
Also record before and after the key: `getTextSelection("text/plain;charset=utf-8")`, the last
`TEXT_SELECTION` payload, the last `INVALIDATE_VISIBLE_CURSOR` payload, the last `TEXT_SELECTION_START`/`_END`.
Every arm is a fresh document load. Make starting shapes the way the PRODUCT makes them:
- a caret: one click (`postMouseEvent` BUTTONDOWN+BUTTONUP at a point, count 1, button 1), as the
  engine's place-caret does;
- a range: a mouse drag (BUTTONDOWN at A, MOUSEMOVE to B, BUTTONUP at B), as `OXSDK_EDITOR_SELECTION_MOUSE_DRAG`
  does (probe_engine.cpp ~5566);
- additionally one keyboard-made range (Shift+Right ×3 from a caret), to compare with the drag-made one.
Take coordinates from the document's own geometry (e.g. a caret's `INVALIDATE_VISIBLE_CURSOR` rectangle
after a `.uno:GoToStartOfDoc` / character moves), not from hard-coded twips; log them.

## Fixture

New `wasm_sdk_probe/test-docs/link-batch/extend-signatures.fodt` (a generator script is fine): a plain
paragraph above; `P2 ALPHA BETA GAMMA DELTA`; a plain paragraph below; an empty paragraph; a paragraph long
enough to wrap at least twice; a CJK paragraph (e.g. `中文段落測試，這是第二句。`); a Heading 1; a bulleted
list item; a 2×2 table with text in each cell; a final plain paragraph that ends the document.

## Arms (shape × key), all in each round

Shapes: `caret-mid` (inside `BETA`); `range-fwd` (drag `BETA GAMMA` left→right, point at end);
`range-bwd` (same text right→left, point at start); `range-one` (one character, left→right);
`range-cross` (middle of P2 → middle of the paragraph below); `range-kbd` (Shift+Right ×3 from caret-mid);
`doc-start`; `doc-end`; `empty-para`; `wrap-line-end` (caret at the end of the first displayed line of the
wrapped paragraph, reached with End); `cjk-mid`; `heading-mid`; `list-mid`; `cell-end` (end of the text in
the top-left cell).

Keys: Shift+{Left, Right, Up, Down, Home, End} on every shape. Plain {Left, Right, Up, Down, Home, End} on
`range-fwd`, `range-bwd`, `range-cross`, `range-kbd` (item 3). Plus a control arm per round: `caret-mid`
with no key (the 1500 ms window must be empty, or the window is contaminated by load-time callbacks — if it
is not empty, say so and lengthen the settle before the key until it is).

Interaction arms (question 7), from `caret-mid`: Shift+Right, then (a) a product click elsewhere → the
selection is gone and the caret is at the click; (b) a product drag over `ALPHA` → the selected text is
exactly `ALPHA`; (c) `setTextSelection` RESET + START + END over `DELTA` (the engine's text-handles path,
~5577) → exactly `DELTA`. Repeat (a)–(c) after Shift+Down and after Shift+End. Record pass/fail by the
selected text, with the raw text.

Rounds: 3, separate processes. A cell whose callback TYPE SEQUENCE differs between rounds is reported as
INTERMITTENT, with all three sequences — not resolved by majority.

## Predictions (written now, so a surprise registers as one)

- P-a: every Shift+key that changes the selection emits ≥ 1 `TEXT_SELECTION`.
- P-b: Shift+Left at `doc-start`, Shift+Right at `doc-end`, Shift+Up on the first line and Shift+Down on the
  last line emit nothing (the 096 shape).
- P-c: Shift+Left on `range-one` emits `TEXT_SELECTION` with an EMPTY payload (it collapses).
- P-d: interaction arms (a)–(c) all pass.
No prediction about order (question 3) — that is the thing being measured.

## Deliverables

An analyser `wasm_sdk_probe/tools/analyze_link_native_extend.py` that reads only the round outputs and
writes the summary tables (form two: re-runnable in one line; it must refuse — exit non-zero — on zero
rounds or on a round with zero arms). `findings/evidence/link-batch/extend-signatures/README.md` starting
with `## SUMMARY` (≤ 30 lines): per prediction, held / failed with the cells; per shape × key, the callback
TYPE sequence (compact, e.g. `SEL,CUR` / `CUR,SEL,SEL` / `—`), the count of `TEXT_SELECTION`, whether the
last `INVALIDATE_VISIBLE_CURSOR` precedes the last `TEXT_SELECTION`, last-callback ms; the empty cells; the
intermittent cells; interaction arms. Tables wider than 83 columns are fine in the README (it is not a
Bugzilla comment). Commit only `wasm_sdk_probe/tools/link_native_extend_signatures.cpp`,
`run_link_native_extend_signatures.sh`, `analyze_link_native_extend.py`, the fixture (and its generator if
any) and the evidence dir (`git add … && git commit -m "…" -- <paths>`; if `.git/index.lock` exists, wait and
retry — other agents commit in parallel). English commit message ending with
`Co-Authored-By: Claude Sonnet <noreply@anthropic.com>`; no `Claude-Session:` line.

Do not touch `src/`, `sdk/`, `web/`, `dist/`, any profile, any spec or plan. Do not draw design
conclusions in the README beyond the tables; the main session designs the barrier from them.
