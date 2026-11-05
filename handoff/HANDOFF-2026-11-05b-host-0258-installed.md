# Handoff: host 0.2.58 installed and hand-tested (Calc headers, Calc structure, Writer key bursts); paused

Checkpoint **2026-11-05 12:55**. Supersedes `HANDOFF-2026-11-05-key-burst-and-calc-structure.md`. One handoff for this session.

## The owner's decision this session

- Hand-test slot: **A, "現在就發布 0.2.58"**. The agent did the whole release, as the option said.

## Done, all committed

- Writer **shell generation 91** = 90 + `narrow-editor-v2-session.js` (`56d6bfed2`). It has its own `e2/generations/generation-91.json`
  and manifest `e2/editor-shell-v2-bundle-v91.json`, and the Makefile's static check names v91. E1-C was intact before and after.
  V0' 91 holds.
- Calc **`ods-editor-v6` frozen** into `dist/profiles/` (three copies equal to the link's receipt). The page points at v6, and the
  four Calc mirror tools learned v6's URL (`3d1ffa921`). The node suite passes 1037/1037 (1038 counted a test that spec append 3
  withdrew), and the three Calc mutation tools pass.
- **Release regression** (`findings/evidence/release-0.2.58/`, 2 h serial, both browsers) is all green: P5 P4 S1 Z(t3, l1) P1, KB on
  dist, F4 24/24, F3 equal; Calc C CU cell range autosave P2, headers P and structure P on dist.
- **Host 0.2.58** (`findings/evidence/host-0.2.58/`, `c400b232f`): host `0bf488a`, engine `9e9310e3`. Gate 39/39, `DELTA_HOLDS`,
  `PACKAGE_HOLDS`, `CANDIDATE_INSTALLED`, Files 52/52, capture holds.
- **New host arm** `calc-host-arm/`: the two Calc page criteria run unchanged on the host route. Header geometry holds there too, so
  Nextcloud's button CSS does not distort the DOM headers. P-H5's `pending` clause cannot be observed on the host, which has no
  `?diagnostics=1`; `read_run.py` registers that, with reds.
- Finding 130's status: released with 0.2.58.
- The hand-test fixtures are in admin's Files under `手測-0.2.58/` (`1-calc.ods` = `create_calc_structure_fixture.py`'s output,
  `2-writer.odt` = `test-docs/t1-plain-zh.odt`). The script is `HANDTEST-2026-11-05-host-0.2.58.md` (repo root, zh-TW, 10 items).

## Hand test (2026-11-05, after the install)

The owner: "手測全部通過" -- all 10 items pass. Record: `findings/evidence/host-0.2.58/handtest-2026-11-05/README.md`. Then:
"我們暫時告一段落吧" -- the work pauses here. `手測-0.2.58/` is still on admin (deleting it is the owner's call).

## Next, when the owner resumes (the owner picks)

Calc candidates the owner added with the result (not started, not specified further):
1. Ctrl+C copies cells, whole columns and whole rows.
2. Ctrl+click adds cells to the selection (multi-range; a named limit of SPEC-P-calc-structure).
3. Naming (renaming) sheets.
4. Seeing a sheet's identity, and referencing data from another sheet.

Earlier candidates still open: drag to resize column width and row height; freeze panes. Before specifying any of them, measure
what the engine and the page already do. For example, a formula like `=$另一張表.A1` typed in the formula bar may already work;
only the UI to see or pick it may be missing. Each one is a fresh spec with its first measurement and one red case.

## Cautions

- `check_key_burst.py --subject baseline` reads dist. Since this freeze, dist is generation 91, so the docstring's "(generation 90)"
  no longer holds. The baseline red is `findings/evidence/key-burst/red-baseline/`.
- Host-route readers: anything that reads `window.__calcEditor.inputState`, `.autosave` or `.lastExport` is diagnostics-only, and
  the host never passes `?diagnostics=1`. Wait with `window.__calcEditor?.state?.…`, because the module runs after the shell is
  drawn.
- Unchanged: `build/archive` is hardlinked or read-only; never check out a candidate in the host repo's working copy; submissions
  are on hold; the four Writer mutations in `run_e2_c_product_path.py` still have no anchor.

## Section 34.4

Checks changed because of review: 0.
