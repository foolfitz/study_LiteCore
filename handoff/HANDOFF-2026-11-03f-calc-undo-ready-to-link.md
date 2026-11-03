# Handoff: Calc undo is ready to link (ods-editor-v4); hosts 0.2.53 and 0.2.54 installed

Checkpoint **2026-11-03 ~16:00**. Supersedes `HANDOFF-2026-11-03e-hosts-0253-0254-installed-calc-undo-measured.md` for what is next; its state and cautions still stand.

## State

- **Installed on the own stack: 0.2.54** (host `8c95b50`, engine `89860962`, Writer `e2-editor-v32`, generation 88; Calc `ods-editor-v3`). Nominal shipped 0.2.45. The owner has hand-tested none of 0.2.52 to 0.2.54 (could not today). Nothing pushed.
- **Calc undo payload committed, not linked** (`9e8b15e15`). The Calc page in `web/` carries the undo buttons and keys, hidden on v3; it still loads `ods-editor-v3`. `dist/` is unchanged (the page goes there at the switch).
- Writer generation 88's bundle check: `problems: []` (the v4 worker is derived at build time, not kept in `sdk/`).

## Done this part (spec `specs/SPEC-P-calc-undo.md` sections 2 to 6, evidence `findings/evidence/calc-undo/`)

- **NU** (`native-01.md`): every Calc page write is one engine undo except single-cell bold and italic, three each; Ctrl+B over a draft four. Predictions committed before the run.
- **NU-2, NU-3** (`nu2-nu3.md`): the stack's seven preconditions hold; `.uno:Undo` answers `success:false` whether or not it did anything; an input undo moves the cell cursor to the restored cell, an attribute undo does not. The bridge fix (one `setPropertyValues`, under `OXSDK_ODS_UNDO`) makes bold and italic one undo; the control build without the define stays three.
- **Payload**: E1 capability bit, E2 the two exports (now actually compiled for Calc), E3 the bridge, E4 the engine's undo walk (`startOdsUndoWalk`, `handleOdsUndoVerify`, a `dispatch()` gate, a dispatch-failure check), the `ods-editor-v4` Makefile rules, `tools/build_calc_undo_profile.py`, `tools/derive_ods_v4_worker.py` + `tests/ods-v4-worker-delta.json`, the session (`undo`, `redo`, `_walk`) and the page (buttons, Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z, sentences).
- **Pre-link checks, all green**: `pre-link-syntax-03` (em++ `-fsyntax-only`, v4 and v3, positive controls), `pre-link-ships` (every v4 export has a body; red on the pre-fix source), lock scopes, Calc unit tests 67/67, `tests/ods_v4_worker_test.cjs` (with a causal control on the v3 worker), the three Calc mutation tools, the new page on v3 regresses nothing (`pre-link-page-on-v3`: C 14/14 and 11/11, cell 31/31, both browsers).
- **Codex review** (`review/README.md`): six findings, five fixed, one by design. The first would have failed the link.

## Next, in order

1. **The owner links**: `handoff/RUNBOOK-relink-calc-v4.md` (one line, about 3 minutes; report the exit and the last JSON block, `capabilityBits` 1046835).
2. After the link, the runbook's "After": freeze, switch the page pointer, write and run the CU tool (red on v3 first), the Calc regressions on v4, host 0.2.55.
3. The owner's hand test, whenever possible: on 0.2.54 the list in `HANDOFF-2026-11-03e-...md`; after 0.2.55, Calc undo too.
4. Not started: C (ordered commands); the owner's demo list (zoom, Calc sheet-tab scrolling, opening Microsoft documents).

## Cautions

- `probe_calc_undo_native.py` and `probe_calc_undo_stack_native.py` run without `-I`. The native driver build is `tools/build_calc_undo_native.py` (single-file g++, agent-run, receipt).
- A new file in `sdk/` turns generation 88's shell bundle check red (`build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v88.json` prints it). Keep Calc-only files out of `sdk/`.
- `commandResultMatches` and other helpers inside `#ifdef OXSDK_EDITOR_DISCOVERY` do not exist in Calc builds; `-fsyntax-only` with v4's defines finds that, `check_calc_undo_ships.py` finds missing export bodies.
- Named limit `L-undo-no-deadline`: a dispatch that neither fails nor answers leaves the walk active; the SDK timeout makes the page uncertain.

## Section 34.4

Since `HANDOFF-2026-11-03e`.

- **Fixed-by-execution: 6.** The NU-2 reader (pretty-printed JSON), the native build's snapshot layout, the worker test's cross-realm comparison and its causal-control pattern, `commandResultMatches` (caught by the syntax check), the v4 worker's location (caught by the bundle check).
- **Fixed-by-review: 5.** Codex's findings 1, 2, 3, 5, 6.
- **Fable rulings: 0.** Codex: one read-only review.
- Wrong statements, corrected: 1. The 4.2 design said the v4 worker would equal v3's byte for byte; it needs two hunks (the reply drops the counts and the cursor). Corrected in spec section 6.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs and findings in zh-TW. Compiling `make` and the link stay the owner's. Commit messages: `Co-Authored-By` yes, `Claude-Session` never. Codex through `codex exec` only.
