# Select-all (action 21) on v25 with its gesture granted -- research measurement

Work order `handoff/WORKORDER-v26-select-all.md`, deliverable 1, questions 2-3. Research note (zh-TW):
`research/2026-10-29-select-all-route-on-v25.md` (part 1 = question 1 by source reading; part 2 = this
measurement). **Not a gate check, not a spec criterion**: no verdict here binds anything; the spec that grants
select-all pins its own criteria before its own runs.

## What was run

`measure_select_all.py` (this directory), `--plan full`, Chrome only, 2026-10-30 from ~00:25 +0800, output
`run-01/report.json`. Shakedowns `sa-shake-01` and `sa-shake-02` ran in the session scratchpad and are not kept;
what they changed in the tool is listed below.

- **Harness path.** The shell client refuses `select-all` before any request, so the observer injected into the
  HTML posts it to the document worker directly (request ids >= 2,000,000,000; the SDK client ignores replies to
  ids it did not issue). The engine's editor-state events still reach the page's session, so the selection wash
  the page draws and the page's later keys and buttons are the product's own. **What the page would do on Ctrl+A
  is not measured** -- that path does not exist yet.
- **Products** (symlink mirrors of `dist/` under `wasm_sdk_probe/build/`, deleted after the run; identity checked
  file by file, recorded in `report.json` `identities`):
  - `grant`: dist as served (page `9cb6ea1f`, shell generation 79, profile `e2-editor-v25`, engine files equal to
    `build/archive/e2-editor-v25-44cb15ea-worker-75557b22`) with a scratch `sdk-manifest.json` whose `select-all`
    grants `collapsed`, `range-single`, `range-cross` (sha256 `5442c253…`); every other manifest field equal.
  - `grant-collapsed`: the same with `collapsed` only.
  - `withheld`: the shipped manifest (`e7780061…`, `gestures: []`).
  The scratch manifests keep `profile: "e2-editor-v25"` because the worker keys the ABI6 extend moves on that
  name. They were never in `dist/`.
- **Fixtures**: `dist/e1-fixtures/` list-contexts, table-boundary, frame-contexts (table cell with an as-char
  frame, a footnote holding a frame), endnote-frame, frame-no-image (as-char text box); and the host's blank
  template for a zh_TW user (`blank/en-US_zh-TW_A4.odt`, finding 173's document). Opened through the page's file
  input.
- **Per run** (fresh Chrome): real click into the document; harness save (baseline); harness
  `move-document-end` / `move-document-start` (reference carets); the arm; harness save (final). After each
  selection request: the reply, a later `editorGetStateV2`, `getSelection` (the engine's copy path -- what the
  page's Ctrl+C puts on the clipboard), the wash rectangles the page drew (`fillRect` calls with the overlay's
  multiply/`#b7d3f2`, i.e. the draw calls, not pixels), the page's pill/toast/notice, and every engine JSON
  object the worker parsed (CDP worker attach, `JSON.parse` observer; tiles excluded).
- **"Whole"** (the summary's predicate, not a criterion): reply ok, reply selection not collapsed, every
  body-level text of the baseline (paragraphs, list items, table cells; notes and frames read apart) appears in
  the copy text in order, and the page drew at least one wash rectangle.

## Controls

- `withheld`: the direct post must be refused (`UNSUPPORTED_OPERATION`) and nothing selected.
- 2026-08-19's construction (`geometric`, editorSelectRangeV2 (0,0)-(width-1,height-1)) was meant as the
  positive control for "reported success, selected nothing". **shake-01 found it selects the whole document on
  v25** (same ends, same copy text as select-all), so on this engine it is a reproduction attempt, not a control.
  Two constructed controls were added for shake-02 and kept in the full plan:
  - `degenerate`: (0,0)-(1,1) -- ok, collapsed, nothing copied, no wash: the "reported success, selected
    nothing" shape, which "whole" must reject;
  - `partial`: (0,0) to the first line's middle at the right edge -- ok, a real range with a wash that is not the
    document, which "whole" must reject (the anchor clause, not the collapsed clause, does the work).

## Runs

| run | plan | runs | fatal | identities | notes |
|---|---|---:|---:|---|---|
| `run-01` | `full` | 46 | 0 | grant, grant-collapsed, withheld: all `ok` | final reading compares TEXT only |
| `run-02` | `bold` | 8 | 0 | grant `ok` | bold reading per paragraph; final ODTs kept |

Changed in the tool between runs (both are this new tool's own development, not a change to any existing check):
after shake-01 the `degenerate` / `partial` controls (above); after run-01 the bold reading, the kept ODTs, the
`partial-bold` control arm and the `bold` plan -- because run-01's `final.unchanged` compares paragraph text and
therefore could not say whether bold was applied (run-01's bold rows say only "text unchanged"). The bold reader
was made red before use: a mutant of `frame-contexts.odt` with one paragraph bold by automatic paragraph style,
one by a span and the note's paragraph bold read back as 41/41, 16/37 and (note) excluded; the plain fixture
read 0 everywhere.

## Results (run-01 unless stated)

**Select-all itself, caret in body text** (the six fixtures x six arms all start the same way, so each line below
is 6 runs out of 6):

| fixture | reply | selection (reply = later state) | copy (`getSelection`) | wash draws |
|---|---|---|---|---:|
| list-contexts | ok, `documented-callback-visible-cursor`, `changed:false`, revision 0 -> 0 | range, 4 rects, ends = doc-start / doc-end carets | text, 175 chars, 9/9 anchors in order | 8 |
| table-boundary | same | range, 4 rects | text, 74 chars, 6/6 (cells tab-separated) | 8 |
| endnote-frame | same | range, 4 rects | text, 123 chars, 3/3; the endnote body is NOT in it | 12 |
| frame-contexts | same | range, 6 rects | **`complex`, 0 chars** | 12 |
| frame-no-image | same | range, 4 rects | **`complex`, 0 chars** | 8 |
| blank | ok, `verified-move-readback` | collapsed, 0 rects | `none` | 0 |

- The reply's selection equals the later `editorGetStateV2` for every one of the 59 selection requests that
  answered ok (61 requests over run-01 and run-02; the 2 refusals carry no selection). Worker record
  (list-contexts look): editor-state events seq 13-16 (range from seq 15), then `editor-action-completed` with
  `callbackSequenceAfter` 16 about 10 ms later -- **the reply is composed after the selection callbacks, in the
  same poll**; one further editor-state (seq 17) ~300 ms later carries the same selection.
- Every page read recorded (after each request, each follow-up, each undo, the end) is `ready` with no notice; the
  page drew the wash from the engine's pushed state although
  it never saw the reply.
- `complex`: the engine reads text only for `LOK_SELTYPE_TEXT` (`probe_engine.cpp` `selectionTypeName`; LOK
  reports COMPLEX for a selection holding an as-char frame). The page's copy then throws
  `UNSUPPORTED_CLIPBOARD_TYPE` / `CLIPBOARD_EMPTY_SELECTION` (`input/clipboard-adapter.js:54-72`, read, not run
  here) and cut copies first and stops before deleting (`e2-editor-app.js` cut handler, read). Not specific to
  select-all: any range over such a frame; select-all makes it the common case.

**What follows a whole-document range** (final save after the arm):

| arm | list-contexts | table-boundary | frame-contexts | endnote-frame | frame-no-image | blank |
|---|---|---|---|---|---|---|
| type (real keys, 6 x `insertText` route `uno-insert-text`, all ok) | one heading `mkallq` | one paragraph `mkallq` (table gone) | one paragraph (table, frames, footnote gone) | one paragraph (endnote gone) | one paragraph (frame gone) | `mkallq` |
| backspace (real key; the page sent `delete-selection`) | one empty heading | one empty paragraph | same | same | same | `delete-backward`, nothing changed |
| delete-selection (harness) | ok, `uno-command-result`, `changed:true`, rev 0 -> 1; one empty heading | same; empty | same | same | same | refused `EDITOR_FORMAT_GESTURE_UNSUPPORTED` (collapsed) |
| type-undo (page's undo button) | 2 undos to the baseline text | 2 | 2 (table, frames, note back) | 2 | 2 | 1 |
| bold (real B click, run-02) | every paragraph bold (incl. heading) | every paragraph and cell | every body paragraph and cell | every body paragraph | every body paragraph | nothing to bold |

Typing over the range keeps the FIRST paragraph's paragraph style (list-contexts comes back as a heading); this
matches desktop Writer's behaviour as far as known, NOT compared against native here. Notes and frames inside the
range are removed with it by typing or deleting, and come back with the undo.

**Other contexts and the gesture grant:**

- Caret in a table cell (`table-cell`, harness `move-line-down` from the first line): press 1 selects the cell
  (`E1-CELL-A1`, 10 chars), press 2 the table (44 chars), press 3 the document (74 chars, 6/6). On
  frame-contexts the same three steps (1, 1, 6 rects), copy `complex` throughout (the frame is in that cell).
- `twice`: a second select-all from the whole range answers ok, `verified-move-readback`, same selection, no new
  wash draw (nothing to redraw). With `grant-collapsed` the second press is refused
  `EDITOR_FORMAT_GESTURE_UNSUPPORTED` and the selection stays -- research note part 1 detail 2 confirmed: a
  select-all grant needs both range bits for the second press (and for press 2/3 in a table).
- `withheld`: `UNSUPPORTED_OPERATION` ("select-all is not offered by profile e2-editor-v25"), nothing selected.

**Controls:**

- `geometric` (2026-08-19's construction) on v25: ok, `documented-callback-text-selection`, the whole document
  (list-contexts 9/9, table-boundary 6/6) -- **the 08-19 failure does not reproduce on the ordered engine**.
- `degenerate`: ok, `verified-selection-readback`, collapsed, nothing copied, no wash -> "whole" false. This is
  the "reported success, selected nothing" shape, and the summary's predicate rejects it.
- `partial`: ok, a 1-rectangle range with a wash, 13 chars -> "whole" false on the anchor clause.
- `partial-bold` (run-02): table-boundary -- only the first paragraph bold, the rest not (the bold reading tells a
  partial range from the document). list-contexts -- **confounded by the fixture**: its first paragraph is a
  heading whose named style is already bold, so the B click turned bold OFF (the save writes `P1` with
  `fo:font-weight="normal"`); the reading counts bold only and reads 0. Recorded as a confounded control, not
  re-judged.

## Limits

- Chrome only; Firefox not run. Harness-posted select-all; the page's own Ctrl+A path does not exist.
- Caret contexts measured: body text, a table cell. NOT measured: caret inside a frame, a footnote or an endnote;
  a document that begins or ends with a table; multi-page documents (all fixtures are one page, so the wash
  never had rectangles outside the canvas window).
- Desktop Writer was not run for comparison; "as Writer does" above is stated as inference.
- `page_rows` records no `enabled` field, so which way a B click went is read from the saved document.
