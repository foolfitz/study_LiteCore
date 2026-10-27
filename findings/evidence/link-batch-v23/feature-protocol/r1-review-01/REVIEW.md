## SUMMARY

- Scope: commit `2b561678` (R1 plan, page, runner and reader) checked against `handoff/PROTOCOL-2026-10-26-v23-r1-inputs.md`, plus the 24 real pages of `r1-prep-01`. Read-only. The code was read from `git show 2b561678:`, and the commit's reader was run from a scratch copy, not from the moving working tree. Nothing was edited except this file. No browser, native run, build, `run_*` or `diag_*` tool was used.
- **False PASS.** I found no path to an R1 PASS that the protocol's explicit NE/FAIL list forbids, with one interpretive exception. The R1 reader handles "late" only as timing: the readback must come at least 500 ms after the terminal, and the marker must come after the delayed reads. It never compares the move reply's reported `state` with the delayed readback, which is the check S2 calls `stale` and FAILs. Under that reading of "late", a stale reply whose cursor settles correctly would PASS R1 (issue 1). On prep-01, 0 of 36 arms are stale, so no recorded verdict changes. Before counting, the root needs a ruling on what "late" means for R1.
- **Other findings.** None can give a false PASS on observed data.
  - (2) The emuend control rectangle is `selection.end`. It is pinned only as "one of the two setup endpoints", not explicitly as the line-2 start. All three emuend shapes are forward selections, so END is the line-2 start under either LOK ordering. prep-01 confirms this in all 4 emuend arms.
  - (3) Pinning to the native made text gives three different outcomes for one cause (a browser wrap different from native): s1-family cells become NE, m1-family cells FAIL with a note when a token repeats, and NE otherwise. This is the Q1 asymmetry. It can only give false FAIL/NE.
  - (4) The literal premise rule `len(boxes)==1` relies on how LOK represents rectangles. Search rectangles are not one per line: the middle lines merge into one block. Still, 1 rectangle implied 1 line in every observation, and this is the same rule the S1 `single_line()` already uses.
  - (5) A counted run stops at the first nonpassing cell (`--keep-going` is allowed only in preparation). With "once per browser", that loses per-cell records. It cannot produce a PASS.
  - (6) The candidate FAIL checks run before closure and generation checks, so an observation that is also invalid for instrument reasons is recorded FAIL, not NE. This affects only the record.
- **Marker mapping is sound.** I re-mapped all 216 native `ref` observations from their raw path and line: all are unique, round-trip, and match the plan. Index and position are a bijection over every index of all three fixtures. The browser save must equal the fixture plus exactly one `#`, so a position is unique. Literal cells compare logical position only, so two affinities at the same offset map to one position. That is the protocol's own choice: native marked text carries no affinity either. Layout-relative cells also compare the caret, which is Q5.
- **Open questions Q1–Q7.** All seven are safe: none can make a false PASS. They differ on whether a ruling is needed before counting.
  - **Q2: decision required.** The runner (`run_v23_feature_selection.py:192`) and the reader's `main` (`judge_v23_feature_selection.py:921`) refuse a counted R1 report that has no pre-red report. `feature-pre-red/counted-05/report.json`, the one selection-counted-01 used, is on disk with its raw cells. Passing it cannot create a PASS.
  - **Q1: confirm the default before the count.** The current default, a FAIL with a note, is pinned by a test. If the root wants NE instead, decide it before the count, not after a FAIL. The exposure is moot on this profile: browser twips equal native twips, W=101 and B=89, in both browsers.
  - **Q3–Q6: no ruling needed.** For Q6, I confirmed natively that emuend agrees with ref in 18 (shape, key) pairs × 3 rounds.
  - **Q7: partly open.** prep-01 exercised all five paths. Still unexercised: the emu-control `click` at a line-1-end cursor from an open range (9 cells: m1e/m1d/s1d × Up/Home/End), and the `single-visual-line` / `table-cell-line` premises. The risk is NE only.
- **prep-01.** I re-inspected 24 of 24 pages with the commit's reader and each page's stored config: all PASS, and identical apart from tuple-versus-list form. I also cross-checked against native data, outside the reader: in all 24 cells, the setup caret, TEXT_SELECTION_START and END, the candidate readback caret and the marker equal native `selectionState`, `cursorAfter` (in twips) and the native logical landing. So each PASS holds for the reasons the README gives.
- **S1–S5 unchanged.** The diff only adds code. Re-reading with the commit's reader and each stored config gives identical results: selection-counted-01 234/234, s5-counted-01 106/106 (including its 1 FAIL), s5-prep-04 12/12, and the commit's own selection-prep-07 + s5-prep-03 test (35 pages) passes. The mutation sweep's bound hashes (`33a196ea…` reader, `8aeb2e40…` tests) match the commit. A condition-disabling census cannot detect absent checks such as issues 1 and 2.

## 1. Issues (file:line at `2b561678`)

### 1. "late" is read as timing only; the reply/readback agreement is never checked (possible false PASS, interpretive)

- `wasm_sdk_probe/tools/judge_v23_feature_selection.py:672-685` (`r1_arm`):
  - binds the reply (`v['reply']==c['result']==terminal`) and its accounting;
  - requires the readback to be at least 500 ms after the terminal (676);
  - requires the marker to come after the delayed reads (`r1_marker_witness`).
- It never runs the existing S2 comparison of the same reader (`arm()` at 273, `s2_compare`). That comparison checks the terminal's `state.caret`/`state.selection` against the delayed readback, and the reply's collapsed flag against the active selection type.
- Scenario: the candidate's Down reply reports `state.caret` at its pre-move position, and the engine moves the cursor only later. The 500 ms readback and the `#` then show the native or control landing, so R1 PASSes. S2 would record `staleFields:['caret']` and FAIL the same observation.
- The protocol (§ Execution) says "a late/error/recovery result cannot count as R1 PASS".
- Measured on prep-01: `s2_compare` over all 36 arms (control and candidate) returns `[]`, so no prep-01 verdict depends on this.
- R1 also does not record the S2-style `lateCursorObservations`. That is a record gap only.
- If the ruling is that "late" includes the S2 stale comparison, the fix reuses `s2_compare` and needs no new mechanism. Choosing the reading is a criterion decision, so I stop here.
- Tying a literal cell's readback caret to its marker would need a caret→logical mapping. That is a new mechanism and is out of scope.

### 2. The emuend rectangle is not pinned to the line-2 start (no reachable false PASS)

- `judge_v23_feature_selection.py:665` takes `selection.get('end')`. Line 658 only proves `{start,end} == {anchor, selectionEnd}` as a set.
- The protocol says "the actual browser `TEXT_SELECTION_END` rectangle at line2 start".
- Scenario: if END were reported at the anchor (W−10, line 1), the control would click on line 1. That gives a false FAIL, or a false PASS only if the candidate's Down also moved from the anchor.
- This is not reachable. m1e, s1d and m1d are all forward selections, so END is the line-2 start under document order and under anchor/cursor order alike. p2-backward shows LOK uses document order.
- On prep-01, `controlRect` = (1418,1694) = the located `selectionEnd` in all 4 emuend arms.
- Asserting `xy(rect)==xy(carets['selectionEnd'])` would restate the protocol's words, not add a criterion.

### 3. The made-text pin makes outcomes depend on where the browser wraps (false FAIL/NE only; Q1)

- The plan cross-check is `v23_feature_selection_cases.py:373-374`; the reader check is `judge…py:651`. Every shape must reproduce the native selected text.
- Consequences for a browser wrap that differs from native:
  - s1 family (s1, s1e, s1d: `scar papa` is unique): every cell is NE, the layout-relative ones included.
  - m1 family (m1r, m1e, m1d): when B−10 (or B−9) hits a token repeat, the literal Left/Right cells read FAIL with the note "(setup not at the native logical position)" (`judge…py:727-728`); otherwise they are NE.
- No false PASS: matching native's absolute landing after a shifted setup would need a jump of about 31 characters.
- Moot on this profile. In both browsers, every caret and selection rectangle of all 12 shapes equals the native twips: W=101 and B=89, as computed by the same engine layout.

### 4. The literal premise witness relies on LOK's rectangle representation (note)

- `judge…py:698` uses `len(boxes)==1` with the caret on the rectangle's y.
- prep-01 shows search rectangles are not one per line:
  - S1 paragraph: `[1418,1418,9972,275]`, `[1418,1694,9972,827]` (three lines merged), `[1418,2522,7031,275]`;
  - token paragraph: the middle block has height 551.
- In every multi-line observation the first line stayed a separate rectangle, so 1 rectangle implied 1 line. This is the same rule as S1 `single_line()` (`:781`).
- A false PASS would need three things at once: LOK merging a two-line match into one rectangle, the browser wrapping P2, A1, B1 or the hard-break line, and the landing still equalling native. That is not reachable on the observed layout.
- prep-01 exercised only the `hard-break-line` (s2/Home) and `empty-paragraph` (s3/End) premises.

### 5. A counted run stops at the first nonpassing cell (false NE / lost records only)

- `run_v23_feature_selection.py:189` and `:232`: `--keep-going` is accepted only with `--preparation-only`, so a counted R1 run stops at the first nonpassing cell.
- The R1 verdict is unaffected: any NE or FAIL already decides it.
- The later cells go unrecorded, though, and a rerun would repeat cells despite "once per browser". This needs a procedural decision, not a reader change.

### 6. FAIL can pre-empt instrument-validity checks (wrong record only)

- The candidate's FAIL checks (`judge…py:683-685`) are raised inside `r1_arm`, before `inspect_r1`'s generation, open-count and `e.closure()` checks (`:708-714`).
- An observation that both changed the revision and carries an unplanned call or worker is recorded FAIL instead of NE. The S arms behave the same way.
- Related: `r1_saved_marker` (`v23_feature_selection_cases.py:261`) compares paragraph texts, not containers. A save that changed the table structure but kept the paragraph order would still map. The landing stays correct; only the record is affected.

## 2. Open questions Q1–Q7

| Q | False PASS possible? | Ruling before counting? |
| --- | --- | --- |
| Q1 token wrap | No; see issue 3. The exposure is moot on the pinned layout (B=89 in both browsers). | Not needed for safety. The current default (annotated FAIL, test-pinned) should be confirmed before the count so a FAIL is not adjudicated afterwards. |
| Q2 pre-red | No: it is an extra prerequisite. | **Yes, procedurally.** Without `--pre-red-report` the runner refuses to start, and judge `main` re-verifies it (`:921`). counted-05 is available. |
| Q3 s5 type | No. prep-01 observed `text` for s5 (and for every shape) in both browsers. Requiring `complex` would make s5 NE on the real product. The witness is the made text of both whole cells (unreachable from A1:11 by a plain text range), caret B1:0 and start/end A1:11/A1:15, all equal to native twips. | No. |
| Q4 drag release | No. x=12099 lies between the line edge 11390 and the width. The s1d/m1d setups equal native caret, start and end exactly. | No. |
| Q5 caret AND marker | No: it is stricter, so it can only add FAILs. | No. Only if the root reads "caret/logical marker" as logical-only. |
| Q6 causal arm | No. The protocol does not ask for a browser old-click arm. Natively, emuend equals ref for all 18 (shape, key) pairs × 3 rounds (checked from the dragend round's raw rows; `collect()` does not bind that folder). | No. |
| Q7 unexecuted paths | No: refusal gives NE. prep-01 exercised all five listed paths in both browsers. Still unexercised: the range-route `click` at a line-1-end visible cursor (emu control for m1e/m1d/s1d × Up/Home/End), and the `single-visual-line` / `table-cell-line` premises. | No. |

## 3. prep-01 spot checks (both browsers identical)

- **Literal: p2-forward/Left.**
  - Setup: 'BETA GAMMA', caret (4152,1694) = located P2:19, endpoints {P2:9, P2:19}.
  - Result: readback (3992,1694) collapsed; save marker P2:18 = native [1,18]; twips equal native `cursorAfter`.
- **Layout-relative: s1/Up.**
  - Both arms: walk W=101; 'scar papa ' selected; caret at the line-2 start (1418,1694).
  - Control: click at (1418,1694+138), witnessed collapsed at (1418,1694).
  - Both arms land at (1418,1418), [0,0] = native.
- **emuend: m1e/Down and s1d/Down.**
  - `controlRect` = `selection.end` = (1418,1694,h275), the line-2 start, while the visible caret is at the line-1 end: (11322,1418) for m1e and (11021,1418) for s1d.
  - Both arms land at (1418,1970): [0,180] and [0,201], matching native. The old emu landings ([0,270] and [0,199]) are recorded on the row.
- **s5 table cell: s5/Left.**
  - Made 'S4 cell A1 text\tS4 cell B1 text\n', type `text`, caret (6403,4178) = B1:0, start/end (2477)/(2837) = A1:11/A1:15. This is identical to native `TEXT_SELECTION_START/END` and `INVALIDATE_VISIBLE_CURSOR`.
  - Lands at (2837,4178), marker [5,15] = native.
