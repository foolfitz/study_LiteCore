# E1 witness: the Enter check's Shift-arm oracle, and the raw-content census (ruling 1 §2.2–§2.4)

**E1** (declared in `../../bound-tool-edits.json` before it landed): `wasm_sdk_probe/tools/run_e2_c_product_path.py` gains the module-level `paragraph_texts_with_breaks(content)` (every `text:p`/`text:h` read through inline elements, `"\n"` for each `text:line-break`, nothing else transformed), and the Shift arm's `lineBreaksBetween` becomes "some paragraph contains `first\nsecond`", with the read paragraph recorded as `paragraphText`. 35 lines added, 3 removed; frozen `7ba30235…` → live `59804737…`. `together`, the Enter arm, `press_key`, the prose and Firefox's NE path are untouched.

**Witness** (§34): run 01's Chrome report (`../chrome/report.json`, the honest run the old oracle misjudged) and `../shift-enter-diagnostic-02/` (the break present).

**Controls** (`controls.py` → `results.json`, 2026-10-28, `CONTROLS_HOLD`, 6/6): the old oracle (the replaced expression with its nested `paragraphs_of`, copied into `controls.py`) on the four `*-SHFTKEYA.odt` saves gives True, True, False, False — the red before E1; the new oracle gives True ×4. On scratch copies of v24-1's content.xml the new oracle is False for (n1) the break removed (paragraph `SHFTKEYASHFTKEYBE`), (n2) a paragraph split (`SHFTKEYA` / `SHFTKEYBE`), (n3) a tab instead (`SHFTKEYASHFTKEYBE`), (n4) text after the break (`SHFTKEYA\nQQSHFTKEYBE`); each mutation still parses with both markers present.

**Census** (§2.2 item 4; one-time, registered, not a gate). Every use of a save's raw `content` in the runner after E1 (`grep -n 'get("content")'` and the `in content` forms), by what its needle is:

- markup in the needle, two typed runs: only the old Shift-arm literal (replaced by E1).
- markup, presence anywhere: `the-edit-buttons-do-what-they-say`, `"<text:line-break/>" in content` (`:7299`, was `:7269` before E1) — a break anywhere; span-safe.
- one typed or inserted run as the needle (one `insertText`, so contiguous text even inside a span): `firstLanded`/`secondLanded` (`:8739`, `:8751`), `KEYBOARD_MARK` (`:5981`, `:5992`), `INSERT_MARK` and the undo/redo witnesses derived from the save's own text (`:5530`–`:5627`), `PASTE_MARK` count (`:6043`), `MKFOCUS` (`:7198`), `MD-CONTROL` (`:8636`), `LONG_INSERT[:32]` (`:8928`), `RESCUE_*` (`:9298`), `BOUNDARY_MARK` (`:4189`), `IME_TEXTS` (`:5431`).
- parsed, not substring: `formatted_runs` / `formatted_paragraphs` (`:3294`, `:3319`, used at `:8450`), the list-level regex over styles (`:3545`).
- recorded, not judged: `spansAfterBreak` (`:7127`, a count of `<text:span`, read by no verdict).

Result as the ruling expected: the Enter Shift arm was the only oracle a typed route's rsid spans could break. Every run-01 check outside the Enter check kept its v23 outcome (`../README.md`), consistent with this.
