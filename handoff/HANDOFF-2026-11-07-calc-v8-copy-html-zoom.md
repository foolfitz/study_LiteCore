# Handoff: ods-editor-v8 (Calc copy with text/html, Calc zoom) -- linked, P holds, regression holds; waits for a hand-test slot

Checkpoint **2026-11-07 ~04:50**. Supersedes `HANDOFF-2026-11-06-calc-copy-and-sheets.md`. One handoff for this session.

The owner went to sleep mid-session and authorised this round to proceed autonomously. Fable may decide in the owner's place, and Codex may be used (`codex exec`). No decision needed fable: the one fork that came up, whether to release, is settled by CLAUDE.md's cadence rule.

## Where things stand

Both items the owner asked for after the 0.2.59 hand test are done on the **dev profile `ods-editor-v8`** and verified. **Nothing is released.** Release needs a hand-test slot that the owner names (CLAUDE.md, cadence 1). The draft hand-test script is `HANDTEST-2026-11-07-host-0.2.60.md`, 10 items.

1. **Copy writes `text/plain` and `text/html`.** This fixes the 0.2.59 finding that a column pasted into desktop Calc split at spaces. Spec: `specs/SPEC-P-calc-copy.md` sections 9-12 (appends 2-5).
2. **Calc zoom**, 50/75/100/125/150/200, from the toolbar's last group. Spec: `specs/SPEC-P-calc-zoom.md` (initial version plus appends 1-4). The engine is needed: the core floors rows to whole pixels at the zoom it paints at, so 100% coordinates cannot be scaled (75% is off by 70 px at row 100, measured). Op 16 stores the tile twips, and every op uses them.

All evidence is in `findings/evidence/calc-v8/README.md`, which carries the full table.

- **Link** (agent-run on the owner's explicit request): 2 m 40 s, wasm `61e2a069`, worker `91d514f1`. Archived as `build/archive/ods-editor-v8-dev-61e2a069`.
- **Native:** n-copy-01 and n-zoom-01 N_HOLDS.
- **P copy:** p-copy-04 P_HOLDS 10/10 in Chrome 156 and Firefox 157. P-H4 takes each browser's read-back HTML, pastes it through the native core's `.uno:Paste`, and keeps A1 = `原始中文 Alpha` in one cell. The red case plain-only is red.
- **P zoom:** p-zoom-02 P_HOLDS 41/41 in each browser. The four red cases are red where the spec says.
- **Codex review** (`review-codex-01/`): 7 findings, 6 adopted (behaviour changes), 1 named limit (`L-calc-zoom-engine-reuse`). P-Z9 was added because of review finding 3. p-zoom-01 had independently hung on exactly that bug.
- **Regression:** the Calc nets of the 0.2.59 release regression all hold on v8 (`regression/`).
- **Units:** node 1070/1070 and the Calc mutation tools pass (`units/`).

## Corrections made this session (all appended to the specs, originals kept)

- Copy append 3: the core's HTML export skips hidden rows and columns, so column A's HTML has 999 rows. This is a named limit: HTML and plain text differ on hidden rows.
- Copy append 4: P-H4 compared B1:C2 with A1:C2; it now pastes A1:C2's browser HTML.
- Copy append 5: Firefox's WebDriver scripts run in a sandbox. To change the page's global, insert a `<script>`.
- Zoom append 1:
  - the red fill covers the grid line (−1 px on top/left), and 200% rounds half a twip;
  - the document size follows where the cursor has been, not the zoom.
- Zoom append 2: P-Z5 is judged by the centre cell, because twips are not comparable across zooms. The P-Z7 segment runs before painting.
- Zoom append 3: Codex.
- Zoom append 4: the P-Z5 column is not judged at the scroll range's ends. The fixture is narrower than the viewport at 50%.

## Next session

1. When the owner names a hand-test slot, release **0.2.60**, following `release-0.2.59/` and `host-0.2.59/`:
   - Freeze `ods-editor-v8` into dist (`FROZEN_EQUAL`).
   - Switch the page's `ENGINE_OPTIONS` from `ods-editor-v7` to `ods-editor-v8`.
   - Add `ods-editor-v8` to the mirror tools' name lists. `check_calc_copy.py` and `check_calc_zoom.py` already have it. Missing: `check_calc_sheet_view.py`, `check_calc_undo_cu.py`, `run_calc_editor_browser.py`, `check_calc_style.py`, `check_calc_headers.py`, `check_calc_structure.py`, `check_calc_sheets.py`, and `calc_host_arm.py` if it lists names.
   - Run the release regression on dist, with `check_calc_zoom.py` and `check_calc_copy.py --html` added.
   - Build the host package, install, Files 52/52.
   - Add a host arm for zoom and copy-html. `tools/calc_host_arm.py --arms` is parametrised, so add arms, not a new tool.
   - Put the fixtures in `手測-0.2.60/`, and drop the "draft" header from the hand-test script.
   - Writer is unchanged (cadence 5).
2. At the next engine link, fix `L-calc-zoom-engine-reuse`: reset `gTileTwips` when a document opens.
3. Still open from the owner's earlier list: Ctrl+click multi-selection, renaming sheets, dragging column widths and row heights, freezing panes.

## Cautions

- **Before committing native-run evidence, check that 0 `/profile/` paths are staged, as a separate step.** `git reset -q $(… grep /profile/)` once silently left 117 staged. They were caught after the commit and removed with `git rm -r --cached` plus an amend, before any push. `git rm -r --cached <dir>` is the reliable form.
- Mirror folders are named after `--out` (`build/calc-*/<name>`), so reusing a name fails at once with `FileExistsError`. Give every run a fresh name.
- `calc-v8/native-build-01/v8/calc-undo-native` is the native harness for P-H4 (`--native-harness`).
- Zoom levels are the bridge's `kTileTwips`. `ZOOM_TILE_TWIPS` in the SDK and the worker delta's literal must change with it; the unit tests assert both.
- `renderZoom` runs inside `renderFormatControls`, like the style controls: a drag's end calls that alone. `calc-format-entry.test.mjs` stubs `renderZoom` and counts it.
- Unchanged:
  - submissions are on hold;
  - `build/archive` is read-only;
  - never check out a candidate in the host repo's working copy;
  - P cannot see a real Ctrl+C's user activation, nor a paste into desktop Calc, so both are hand-test items.

## Section 34.4

Checks changed because of review: 1 (P-Z9).
