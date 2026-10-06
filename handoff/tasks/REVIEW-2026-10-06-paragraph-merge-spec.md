# Adversarial review: SPEC-M3-paragraph-merge (option B), before any code

Repository: /home/jiajun/LibreOffice/study_LiteCore (read-only for you; do NOT edit, commit or build anything; do not run `make`).

Read, in this order:
1. `specs/SPEC-M3-paragraph-merge.md` (zh-TW; the object under review, commit 30d12a45).
2. `handoff/HANDOFF-2026-10-06f-b-restores-in-two-presses-spec-not-written.md` and `handoff/HANDOFF-2026-10-06e-option-b-is-feasible-natively.md` (the drafts it came from).
3. `findings/evidence/merge-native/README.md` (the native evidence: rounds four to six), and as needed `findings/evidence/merge-native/restore/*/arms.jsonl`.
4. Source the spec cites: `wasm_sdk_probe/src/probe_engine.cpp` (barrier ~3241–3560, callback handler ~2480–2600, engine loops ~5506–5600 and ~5715–5845), `wasm_sdk_probe/sdk/sdk-worker.js` (~843–870, ~1060–1075), `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js` (~255–290), `wasm_sdk_probe/editor-shell-v2/paragraph-editor-session.js` (`recoveryFor`), `wasm_sdk_probe/web/e2-editor-app.js` (~49, ~1019–1070, ~1915). LibreOffice core source is at `libreoffice-26-8/` (e.g. `desktop/source/lib/init.cxx`, `sfx2/source/view/lokhelper.cxx`, `sw/source/core/crsr/crsrsh.cxx`, `svl/source/undo/undo.cxx`).
5. `CLAUDE.md` sections 1–9 (the project's rules for what a criterion may look like: per-instance property / tool-closed enumeration / hand enumeration that may only be a registered one-off measurement; every criterion needs an "if never done" default).

The design: at a paragraph boundary, the engine keeps today's Shift+arrow unit selection, then presses the opposite arrow without Shift (at most twice, the second only when the first did not bring the caret back), reads the `.uno:Undo` payload P0, waits for the wall-clock millisecond to pass, posts the user's own key, and proves the key did something by the whole payload changing (`verified-key-undo`); otherwise it refuses with `EDITOR_BOUNDARY_UNSUPPORTED` + `mergeKey{keyPosted, stage}`.

## What to attack

Attack the CRITERIA and the ARGUMENTS, not the decision to do B (the owner chose B; do not relitigate that).

A. For each criterion in section 4 (M1-1..M1-5, R0, M2-0..M2-5, R): construct a concrete scenario in which the thing it guards is broken but the criterion stays green (or vacuous). Say which form it really is (per CLAUDE.md section 1) if the spec mislabels it. Say whether its "if never done" default is a real default.
B. Section 3.2 (restore evidence attribution): the spec claims the handoff's "safe direction" risk is actually unsafe, and proposes the rule "evidence for press N = the first callback after press N was posted whose caret rectangle differs from the caret known when press N was posted; press 1 additionally needs the selection collapse; the unit's own caret must have been seen before press 1". Try to break the rule: find an interleaving of LOK callbacks (re-sent carets, coalesced callbacks, an intermediate caret within one key press, selection and caret callbacks in either order, the engine thread running between two callbacks of one flush, `readSelection()` delivering callbacks re-entrantly as the code comments at ~3430 warn) in which the rule posts the user's key while the caret is not at the placed position. If the rule survives, say so and say what premise it rests on. If you can, read `CallbackFlushHandler` in `libreoffice-26-8/desktop/source/lib/init.cxx` (queue / dedup of LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR and LOK_CALLBACK_TEXT_SELECTION) and say whether the premise holds, citing lines.
C. The clock guard (3.1 item 7): is "new top dateTime strictly greater than the old top dateTime" actually guaranteed? Consider which thread creates the undo action, which clock, the ISO8601 serialization precision on WASM, and whether an action can be MODIFIED in place (e.g. Writer merging a typing action into the previous one) so the payload changes without a new action, or a new action replaces the top with an identical serialization.
D. The key-deadline path (3.1 item 9): is mapping "key posted, payload unchanged at 2000 ms" to `EDITOR_BOUNDARY_UNSUPPORTED` honest end to end through `narrow-editor-v2-session.js` (`_checkpointBeforeBoundaryRestart`, `restartKeepsContent`) and the page? Find a path where the user loses unsaved content or is told something false.
E. Anything the spec claims as fact (section 2) that the cited source or evidence does not support. Quote the line.
F. Gaps: a failure mode of B that no criterion would catch.

## Output

Write your full report to `/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/33c32a87-e057-4459-8cde-fb91de82f9ab/scratchpad/REVIEW-<your-seat>.md` where <your-seat> is given below, and also return it as your final message. Start with `## SUMMARY` (at most 30 lines): numbered findings, each tagged BLOCKING (must change before code), SHOULD, or NOTE, each one sentence. Then one section per letter A–F with the details. For any section where you find nothing, write "no defect found" — do not pad. Every claim about source must cite file:line. Do not propose rewriting the spec wholesale; propose the smallest change that closes each defect.
