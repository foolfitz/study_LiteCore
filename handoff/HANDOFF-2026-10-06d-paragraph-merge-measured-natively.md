# Handoff, 2026-10-06d — paragraph merge (finding 109's option C) measured on native LibreOffice; no engine byte changed, no spec written yet

Entry points: this file; `findings/evidence/merge-native/README.md` (the per-boundary table) and `PREDICTION.md` (written first); `wasm_sdk_probe/src/probe_engine.cpp` (the barrier, line numbers below); finding 109 (option C); `wasm_sdk_probe/tools/check_relink_queue.py` with `wasm_sdk_probe/e2/relink-queue-v3.json`.

Picks up from `handoff/HANDOFF-2026-10-06c-109-110-fixed-after-one-locks-repeat.md`. No upstream remote configured; nothing pushed.

## What happened this session

The owner (2026-10-06, after 109/110 were marked fixed) asked that a delete at a paragraph boundary MERGE the paragraphs instead of being refused. Scope **A**: change only the shipped v8 engine line, not the a11y candidate v14. Agreed plan: (1) measure natively first, no relink — **done**; (2) a spec with criteria before any code (zh-TW, `specs/`, append-only) — not started; (3) change the engine's selection barrier, the shell and page handle a completed merge without a reopen; (4) relink a new profile from the v8 line, archive the current profile first, the relink command goes to the owner; (5) a new engine package is new bindings, so the six M3 runners and the production-UI runner re-count.

| Commit | What |
|---|---|
| `da0d59eb` | Fixture `wasm_sdk_probe/test-docs/merge/boundaries.fodt` (29 cases), probe `tools/merge_native_boundaries.cpp`, runner `tools/run_merge_native.sh`, and `PREDICTION.md` — all before any run. |
| `410ad4c8` | Native results: counted round `round-20261006T065130Z` (3 rounds × 29 cases × 2 arms), reader `tools/analyze_merge_native.py`, README, and the two faulty rounds kept with their explanations. |
| the commit adding this file | This handoff. No product, spec, host or runner file changed. |

## What the engine does today (read from source, HEAD)

- `startSelectionBarrierDelete` (`probe_engine.cpp:3523`) selects one unit with Shift+Left/Right via postKeyEvent; the actions are wired at `:4818–4842` under `OXSDK_FINDING_016_SELECTION_BARRIER`.
- `verifyAndDispatchSelectionBarrierDelete` (`:3372`) needs `selectionRectangles.size() == 1` (`geometrySafe`, `:3379`) and text with no separator: `selectionBarrierContainsBoundary` (`:3246`) rejects `\r \n \t` U+2028 U+2029 U+FFFC. Otherwise `EDITOR_BOUNDARY_UNSUPPORTED`, with "start a fresh Worker" appended when something was selected.
- `rejectSelectionBarrierAtDeadline` (`:3411`) refuses when nothing got selected (document start/end) with the same code. Completion proof (`maybeFinishSelectionBarrier`, `:3268`) = `.uno:Delete`/`.uno:SwBackspace` UNO_COMMAND_RESULT success + collapsed selection, reported as `completion: "verified-selection-delete"`.
- The a11y/non-barrier path refuses through `deleteHasSafeSemanticPrecondition` (`:1929`, used at `:3811`).
- JS side: `web/e2-editor-app.js:1164` sends the code to `reopenAfterBoundaryRefusal` (`:1022`, 109's fix: checkpoint and reopen). It keys on the code only, so a delete at the document's very start/end also reopens today.

## What the native measurement says (all numbers from the README / `summary.json`)

- Instrument checks all pass: positive control (Writer's own Delete at C01 changes the document); placement self-check on every arm; same unit signature and verdict in all three rounds; 81/81 dispatched deletes reported `success: true` and left a collapsed selection.
- Unit text exactly `[10]` (one U+000A, type 1 = text): plain, numbered-heading|body, empty, anchored-frame, page-break, section, line-break boundaries. Deleting that selection equals the user's own key every time, and one Undo restores the original (81/81). `summary.json` tallies **16** such cases (C01, C02, C04–C07, C19–C28); the commit message of `410ad4c8` says "14 種交界" — the tally wins.
- Rectangle count for the unit selection is 1–4 across cases with the same `[10]` (stable within a case), so "exactly one rectangle" cannot be part of a merge rule.
- **Tables must stay refused.** The unit is the whole table's text, and deleting it deletes the table (C15, C16) or empties both cells (C17, whole row's text); the key does nothing. Recognisable before dispatch: the text is never `[10]`.
- **Label-decorated units** carry the label in the readback (`[10, 32×4, 8226, 32]`). Delete at an item's end (C08, C10, C12) and Backspace at the start of the body paragraph below an item (C13) equal the key; Backspace at a bullet/number item's start (C09, C11, C14) or a numbered heading's start (C03) **differs** (Writer removes the label or makes a list header; the select arm merges). A second step; refuse for now (so 4 same cases are refused too — a conservative loss, not a hazard).
- Document start/end (C29, C30): nothing selected, nothing dispatched, the key changes nothing.
- `.uno:Undo` reports `success: false` every time although it restores — never use its result as evidence.
- Not measured: the WASM engine's own readback (same core, different build), the a11y core's precheck, nested lists, tracked changes, fields, footnotes, RTL, any document but the fixture.
- Owner's `PMPC指南.odt` (copy at `wasm_sdk_probe/build/scratch-m3-production-ui/PMPC指南.odt`; **read from the ODT XML, not run in LibreOffice**): all ten outline levels have an empty `style:num-format`, no heading sits inside a list, so 「一、序言」 is typed text — the unlabelled-heading kind, which **no fixture case covers** (C04/C05 are outline-numbered). 23 headings, 11 lists, 0 tables.

## State

Product unchanged from 06c: 109 and 110 fixed on host 0.2.7 `0488586`, page `e97d6e03…`, shell v55, engine buildId `fabdb50ecd038802`. Finding 111 (keys overtaking text queued in the input adapter; measure first) and 112 (Files page stall, cause unknown, repeat budget spent) still open. Nothing is running; this session started no browser, runner or ddev work.

## What is next

1. **Order is the owner's.** 06c named 111's measurement next; the merge was requested after it. Neither is started beyond the native round below. Ask, do not assume.
2. **Close the fixture gap before the spec's numbers are pinned:** a small native round (predictions first) adding an unlabelled heading|body in both directions and a list boundary shaped like the PMPC document's. Same probe, per-round fixture copy.
3. **Write the spec** (zh-TW, suggested `specs/SPEC-M3-paragraph-merge.md`, criteria before any code, each with its "if never done" default). Starting direction, not decided: accept a unit whose code points are exactly `[10]` with type TEXT; drop the one-rectangle requirement for that case; keep the existing completion proof; report a distinct completion (e.g. `verified-selection-merge`); keep tables and label-decorated units refused; consider making document start/end a no-op rather than a refusal. Open questions the spec must answer: does the WASM engine read `[10]` the same way (a small check after relink, or a diagnostic profile); does the a11y core's `deleteHasSafeSemanticPrecondition` matter for scope A (expected no — say so); how shell and page treat a merge (block/structure projection refresh, undo); what the PMPC document does.
4. **Engine change** in the selection barrier only (v8 line). Make the rule's red cases before trusting a green: a `[10]` unit that is not type TEXT, a table unit, a label-decorated unit must each still be refused.
5. **Relink, owner-run.** Archive `dist/profiles/<profile>` to `build/archive/<name>/` before anything (the `probe_engine` make swaps `probe.wasm`'s hash); give the owner the command. Before that, run `check_relink_queue.py` and show the owner which open items can ride the same relink (run in this session on 2026-10-06: 64 items, 48 declared present, 16 still open, 0 drifted, nothing blocking; count again at the time).
6. **Shell/page** handle a completed merge without `reopenAfterBoundaryRefusal`; keep that path for the refusals that remain (tables, labels). A shell change is a new generation.
7. **Re-count** the six M3 runners and the production-UI runner on the new engine package (new bindings); runner pins are in 06c's rules.

## Things this round taught

- **A placement self-check caught the first round measuring the wrong boundary** (`.uno:GoToEndOfPara` straight after a hit that already ended the paragraph moves on to the next one; C01 measured P2's boundary). Without the check that round would have been counted.
- **A stale `.~lock` file (left by killing the faulty run) made every native load read-only**: every save equalled the original, so every arm read "same". A reader without a positive control would have reported 29/29 "same". The runner now loads a per-round copy and the reader fails unless the control changed the document (it fails on that round, as it should).
- **Predictions committed first showed exactly where intuition was wrong**: the readback carries list/number/heading labels (predicted plain `[10]`), and tables are selected whole (predicted "unknown, maybe `[10]`"). Both decide the design.
- **Recompute a tally before repeating it**: the commit message said 14, the summary says 16.
- The owner's document is evidence about the owner's case; a static read of it (no outline numbering) already changes which fixture case matters, and says what was not run.

## Standing rules to carry

- Never two M3 runners (or an M3 probe) at once; each clears the whole `oc_files_lock` table.
- Counted runners refuse a dirty host tree; a host JS change means an `info.xml` bump + `ddev occ upgrade`.
- After changing `dist/`, re-run `package_m3_engine.py`; the buildId is content-addressed.
- A runner changed after its pin is a new pin (append to the spec), or its reports do not count; the locks runner's pin is now `1d3099a2…` (§12.1). `check_m3_same_second.py` and `probe_m3_save_throw.py` import `open_from_files` from it.
- `findings/evidence/**` and `handoff/**` English; specs, findings' prose zh-TW; specs append-only.
- Native probes load a per-round copy of the fixture, never the fixture itself.
- Never `pkill -f` with a pattern that also matches your own shell command line (it killed the shell in this session).
