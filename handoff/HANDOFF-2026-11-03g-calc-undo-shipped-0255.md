# Handoff: Calc document undo linked, frozen and installed as host 0.2.55

Checkpoint **2026-11-03 18:40**. Supersedes `HANDOFF-2026-11-03f-calc-undo-ready-to-link.md`; its cautions still stand.

## State

- **Installed on the own stack: 0.2.55** (host `5db53ac`, engine `1d2608fc`). Writer `e2-editor-v32`, generation 88 (unchanged). **Calc `ods-editor-v4`** (wasm `9f37ed5a`, frozen in `dist/profiles/ods-editor-v4`, archive `build/archive/ods-editor-v4-9f37ed5a-worker-4a06fbe4`). Nominal shipped 0.2.45.
- The Calc page (`web/` = `dist/`) loads v4 and shows 復原 / 重做; Ctrl+Z, Ctrl+Y, Ctrl+Shift+Z from the grid.
- Host repo `main` = `5db53ac` locally (fast-forwarded through 0.2.53, 0.2.54, 0.2.55). **Nothing pushed.** The owner has hand-tested none of 0.2.52 to 0.2.55.

## Done since 03f

- **Link** (the owner asked the agent to run it): 2 min 35 s, exit 0, capability bits 1046835 (`findings/evidence/calc-undo/link/`). Smoke on the development profile (`post-link-dev/`).
- **CU tool** `wasm_sdk_probe/tools/check_calc_undo_cu.py` (spec 4.5 and 6, CU-1 to CU-7, CU-9): `CU_HOLDS` on both browsers on the development and the frozen v4; red on v3 on every arm but CU-3, whose red comes from a page mutation (`--mutate field-guard`). Calc arms on v4: cell 31/31, range 40/40, autosave 18/18, P2 33/33, C 14/14 and 11/11.
- **Freeze and switch** (`after-freeze/`): v4 copied to dist and the archive, the page pointer moved, `make ods-editor-assets`; the mirror tools that alias the page's engine URL learned v4 (`run_calc_editor_browser.py`, `check_calc_style.py`, `check_calc_sheet_view.py`).
- **Host 0.2.55** (`findings/evidence/host-0.2.55/README.md`): `host_batch7.py` red on 0.2.54 first, then `H7_HOLDS` 12/12 on both browsers on the owner's path (Files, WebDAV read-back); batch 6, T6 (96 controls), Files 52/52, host batch, layout, capture-after.

## Next

1. **The owner's hand test** on 0.2.55, whenever possible: the 0.2.54 list (`HANDOFF-2026-11-03e-...md`) plus Calc: type in a cell and Enter, then 復原 (or Ctrl+Z) and 重做 (Ctrl+Y); bold a cell, 復原 once (one press is enough now); type without Enter and press 復原 (the entry goes, the document does not change); write on the second sheet, go back to the first, 復原 (it shows the second sheet and the cell).
2. Not started: C (ordered commands); the owner's demo list (zoom, Calc sheet-tab scrolling, opening Microsoft documents).

## Cautions

- A new Calc profile means updating every mirror tool that aliases the page's engine URL by name; a list that lacks the new name loads nothing. The three are named above; `check_calc_undo_cu.py` already knows v4.
- `run_calc_editor_browser.py` and `check_calc_sheet_view.py` key their mirror directory by the output folder's name and keep it: reuse a name and they die at once on `FileExistsError`.
- Running a tool from `wasm_sdk_probe/tools` with `--out ../findings/...` writes under `wasm_sdk_probe/findings/` (ignored by git). Use absolute paths for evidence.
- Named limit `L-undo-no-deadline` (spec section 6) stands.

## Section 34.4

Since `HANDOFF-2026-11-03f`.

- **Fixed-by-execution: 8.** CU tool: save before navigating, the failure screenshot, the CU-2 redo cells and the CU-9 view cell made conditional (both vacuous on v3), CU-9's file check given a positive control; the mirror tools' v4 name; 0.2.55's gate reading the static criteria and the arm reports; the export-check output's location.
- **Fixed-by-review: 0.**
- **Fable rulings: 0.** Codex: none since 03f.
- Wrong statements, corrected: 0.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs and findings in zh-TW. Compiling `make` and the link stay the owner's unless the owner asks (the owner asked for this link). Commit messages: `Co-Authored-By` yes, `Claude-Session` never. Codex through `codex exec` only.

## The owner's choice for the next session (2026-11-03 18:45)

**Open Microsoft documents** (the owner's demo list, 11-02: "開微軟文件（可參考 Collabora）"). Not started; this session stopped here only because its context passed the soft limit. Start from spec, criteria before code, as every batch here: what Collabora does for .docx/.xlsx (the `cool-26-04` reference checkout, memory `cool-26-04-reference-checkout`), what the host's file action and routes accept today (`src/files.js` maps only ODT and ODS), what the engine profiles can load (the Writer and Calc builds were linked for ODF; check which import filters the cores carry before promising a format), and whether saving goes back as the Microsoft format or as ODF. Measure the import natively before any link.
