# Paragraph merge, native, fifth round — predictions (written 2026-10-06, before the round ran)

Round four showed option B's sequence gives Writer's own document at every paragraph boundary measured, and that the undo stack changed exactly when the document did (324 boundary-batch presses, 0 disagreements). It left one question the engine's design depends on: **what B's proof reads once the undo stack is full.** `.uno:UndoCount` cannot move past the limit, so B compares the whole `.uno:Undo` payload; this round measures whether that payload still changes on every press that changes the document, and stays put on every press that does not, with the stack full.

## What the payload is (read from source, `svl/source/undo/undo.cxx:1310–1335`)

`SfxUndoManager::GetUndoActionsInfo()` lists every undo action, newest first, as `{index, comment, viewId, dateTime}`. `dateTime` is the action's creation time (`SfxUndoAction` constructor, `DateTime::SYSTEM`), written by `utl::toISO8601`; natively `GetSystemDateTime` (`tools/source/datetime/systemdatetime.cxx:41`) takes `std::chrono::system_clock` to the nanosecond, and round four's payloads carry it (`"2026-10-06T08:12:22,427464402"`). At the limit the oldest action is dropped and the list shifts by one, so the payload is unchanged after a new action only if every listed action has the same comment, view and timestamp as its neighbour.

The default limit is **100** (`officecfg/registry/schema/org/openoffice/Office/Common.xcs`, `Undo/Steps`, `<value>100</value>`, range 1–1000) — read, so the handoff's "not read" is closed. This round sets it to 3 so ten presses pass it (`MERGE_UNDO_STEPS=3`, the runner writes it into the profile and leaves `undo-steps.txt`).

## Instruments (this commit)

- `test-docs/merge/undo-limit.fodt` + `round-h-limit.cases.tsv` (`2e952d79`): **H01**, Delete at the end of "L01" ten times — join, delete the joined letter, join, … — every press a new action, the comments alternating.
- `test-docs/merge/undo-limit-same.fodt` + `round-h-limit-same.cases.tsv` (new): **H02**, Delete at the end of "S01" before eight empty paragraphs — eight joins with **the same comment**, then two presses at the document's end. Once the stack is full only the timestamps can tell one join from the next; presses 9–10 are no-ops with the stack full.
- `tools/analyze_merge_undo.py`: with `undo-steps.txt` present it also reports, per press, whether `.uno:UndoCount` alone would have agreed with `content.xml`, and whether the stack changed only in its timestamps; it **exits non-zero unless the count reached the limit** (red case run on a copy of `undo/round-20261006T081216Z` with a fake limit of 50: "NOT REACHED", exit 1). Re-read on round four's `undo/round-20261006T081216Z`: unchanged, 174 presses, 0 disagreements. (That re-read also shows where the count alone fails below any limit: 15 presses, every one an in-paragraph character delete folded into the previous one — `Delete “M0”`, `Delete “ha”`, `Delete “M2”` — never a boundary.)

Run: `MERGE_UNDO_STEPS=3 tools/run_merge_native.sh ../findings/evidence/merge-native/limit 3 test-docs/merge/<fixture> test-docs/merge/<cases> 10`, once per fixture.

## Predictions

| What | Prediction |
|---|---|
| Count, key arm, H01 and H02 | 1, 2, 3, then 3 for every later press (the limit took effect) |
| H01, presses 1–10 | every press changes `content.xml`; the payload changes on every press; **0 payload disagreements**; count-only disagreements on presses 4–10 (7 per round, 21) |
| H01 comments | alternate between the join (`Delete paragraph`) and the letter (`Delete “b”`, `“c”`, …); a letter's delete does not fold into the join before it |
| H02, presses 1–8 | every press changes `content.xml` and the payload; all eight with the same comment; presses 4–8 change the payload **only in its timestamps** (5 per round, 15); count-only disagreements on the same 15 |
| H02, presses 9–10 | `content.xml` unchanged, payload unchanged (no-op at the document's end with the stack full) |
| Select and b arms | one press each, below the limit; as in round four (b equals the key arm's first press) |

What would change the decision:

- A press at the limit that changes `content.xml` while the payload stays the same: comparing the payload is not B's proof once the stack is full, and B needs another one (or must refuse when the count is at the limit).
- A no-op press (H02 9–10) whose payload changes: B would report a change that did not happen.
- The count not reaching 3: the setting did not take effect and the round says nothing (the reader fails it).

What this round cannot say: natively two presses are always apart by the probe's fixed waits and timestamps run to the nanosecond, so H02 cannot produce two joins in one clock tick. On WASM `std::chrono::system_clock` goes through Emscripten's `clock_gettime(CLOCK_REALTIME)` → WASI `clock_time_get` → `Date.now()` (`wasm-lite/tools/emsdk/upstream/emscripten/src/lib/libwasi.js:162–170`, `src/lib/libcore.js:1318`): whole milliseconds (read, not measured). Whether two same-comment actions can share a timestamp there is for the WASM measurement at the limit, not this round.
