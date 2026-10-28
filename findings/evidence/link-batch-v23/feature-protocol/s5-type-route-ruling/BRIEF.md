# Brief sent to fable for the typing-route ruling (2026-10-28, verbatim)

You are asked for a binding design ruling in the study_LiteCore repository (/home/jiajun/LibreOffice/study_LiteCore). The owner chose "ask fable to rule" for this decision. Read-only: do NOT edit any file, do NOT run builds, browsers, native harnesses or long commands, do NOT run repository-wide searches (a native measurement is running; grep only inside the specific files/dirs named below). Short `sed -n`/`grep -n` on named files is fine.

## Decision to make

Which route should the SUCCESSOR editor identity (after frozen e2-editor-v23, ABI6) use to apply TYPED text, so that S5 type cells match the bound native keyboard oracle — and what is the scope/acceptance for that change? Options I see (you may reject all or add one):

- A. Typed text (adapter commits from `beforeinput` insertText/insertReplacementText and IME composition end) goes through `.uno:InsertText` (FN_INSERT_STRING → SwWrtShell::InsertByWord → SwWrtShell::Insert); real paste (`paste` event / clipboard API) keeps LOK `paste(text/plain;charset=utf-8)`. Needs the page/SDK to carry typing-vs-paste origin to the engine → protocol/ABI change in engine + worker + page.
- B. Engine-only, no ABI change: every single-line `insertText` goes through `.uno:InsertText`; text containing a line break keeps LOK paste. Cost: real single-line Ctrl+V changes from Writer paste semantics to replace-selection semantics; existing paste checks must be re-read.
- C. Typed text goes through postKeyEvent per character (the engine's existing fallback path). Closest to the keyboard (incl. autocorrect) but non-BMP characters, long IME commits and async queueing are risks.

## Established facts (verify the ones your ruling depends on)

1. Counted S5-02 stopped at Chrome `shift-Right@cell-end/type` after 401 PASS: product saves A1 `A1 cell textx` / B1 `B1 cell textx#`; bound native run-03 keyboard oracle saves A1 `` / B1 `x`. The engine's `handleInsertText` (wasm_sdk_probe/src/probe_engine.cpp ~line 3788) uses LOK paste first, postKeyEvent only if paste returns false; actual response said `method: paste`.
2. Today's native route comparison (native LOK 26.8, same fixture/selection, 15 arms × 3 rounds, every arm stable; `table2/key-x` reproduces run-03's bound save): native paste gives exactly the product's result; `.uno:InsertText` and ext-text-input (postWindowExtTextInputEvent TEXTINPUT+END) both give A1 `` / B1 `x` = keyboard. Over a plain-text selection and at a caret, paste equals keyboard (why the other 401 cells passed). A second defect: later cells of a multi-cell paste get the UTF-16LE bytes decoded one byte per char (`xy`→`x#y#`, `中`→`-N`, `é` dropped, 4-cell selection → all 3 later cells `x#`); registered as finding 169. An LC_ALL=C rerun gave identical outcomes for all 15 arms (a clean confirmation run is in progress; the first LC_ALL=C run is marked "protected inputs changed" only because I edited the reader during it).
3. Source (core libreoffice-26-8 @671c848b): keyboard `SwEditWin::FlushInBuffer` ends in `rSh.Insert(m_aInBuffer)` (sw/source/uibase/docvw/edtwin.cxx ~927–1075); FN_INSERT_STRING handler sw/source/uibase/shells/textsh.cxx:153; `SwWrtShell::InsertByWord`/`Insert` sw/source/uibase/wrtsh/wrtsh1.cxx:221–300 (selection → DelRight → Insert); paste skips selection deletion in table mode sw/source/uibase/dochdl/swdtflvr.cxx:~1775; StartExtTextInput DelRight edtwin.cxx:5931. In native, postUnoCommand(.uno:InsertText) returned in 0.12 ms (queued), completed within the following settle.

## Read

- handoff/HANDOFF-2026-10-28-v23-r1-counted-pass-s5-table-type-failure-claude-next.md (state, constraints, "Claude's next bounded work")
- findings/168-sdk-type-over-a-cross-cell-selection-pastes-into-both-cells-and-adds-a-hash.md (zh-TW; incl. 2026-10-28 addendum) and findings/169-writer-plain-text-paste-into-a-multi-cell-selection-decodes-later-cells-byte-by-byte.md
- findings/evidence/link-batch-v23/feature-protocol/f168-native-routes/README.md and reader-run-01.json
- findings/evidence/link-batch-v23/feature-protocol/s5-table-type-diagnostic-01/README.md
- findings/evidence/link-batch-v23/feature-protocol/s5-type-oracle-ruling/RULING.md (fable ruling 3: the native-type requirement) and s5-order-oracle-review/RULING.md (Astra A: only a deletion-partition amendment; must not be broadened)
- wasm_sdk_probe/input/input-adapter.js (commit metadata `source`), wasm_sdk_probe/editor-shell/editor-session.js:92–93 and ~511 (commit → document.insertText; NOTE this file is hash-registered for the E1-C judgement, see wasm_sdk_probe/tools/check_e1_c_bundle_intact.py header — a page-side subclass override was the earlier precedent, finding 068), wasm_sdk_probe/sdk/document-sdk.js:533, wasm_sdk_probe/sdk/sdk-worker.js:1477, wasm_sdk_probe/src/ordered_engine_reply.inc (composeOrderedUno: the existing ordered UNO-with-result proof pattern)
- AGENTS.md sections "驗收判準的形式" §1, §2, §4, §9 (criteria must be per-instance or tool-closed enumerations; each criterion needs a default verdict if never done)

## Constraints

Frozen v23 is never overwritten; a repair is a successor identity with fresh bindings; the completed R1 144/144 and four-arm results belong to v23 and do not transfer automatically. Core/engine builds and relinks are run by the owner. Upstream submission is on hold. Not measured yet: candidate routes on WASM, autocorrect-triggering input, IME/non-BMP, other S5 shapes through the candidate routes, desktop Writer.

## Output (≤ 90 lines, English)

Start with `## SUMMARY` (≤ 25 lines): the chosen route and why, in plain words the owner can follow. Then: (1) the ruling, with which facts above you verified by reading source/evidence yourself; (2) whether finding 169 is in or out of the successor's scope and why; (3) prospective acceptance criteria for the successor's typing route (form per AGENTS.md §1, each with a default verdict), including the red controls required before any counted S5 run; (4) what must be revalidated on the successor versus what can stay v23-scoped; (5) any measurement that must happen before implementation (e.g. on WASM) and its pass condition. Do not soften; if a fact above is wrong, say so.
