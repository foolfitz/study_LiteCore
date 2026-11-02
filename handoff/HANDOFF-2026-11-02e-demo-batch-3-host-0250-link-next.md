# Handoff: demo batch 3, host 0.2.50 installed, the owner's link is next

Checkpoint **2026-11-02, after the 0.2.50 install**. Supersedes `HANDOFF-2026-11-02d-host-0249-hand-test-next.md` for what is next. K's numbers in `HANDOFF-2026-11-02b-k-0245-holds.md` stand.

## State

- **Nominal shipped: 0.2.45** (K holds). It carries finding 179. **Installed on the own stack: 0.2.50**, uncounted: host `350cc4c`, engine `7e3edb640c50d628`, Writer on `e2-editor-v30`, shell generation 85.
- The owner's report on 0.2.49 had four points; `specs/SPEC-P-demo-batch-3.md` pins them, `findings/evidence/demo-batch-3/README.md` is the table of results.
- **Nothing of ours is running. Nothing is pushed.** The owner pushes (`git push -u github main` from this repo; the GitHub repo is public).

| Point | State |
|---|---|
| 1. Shift+Up/Down/Home/End refused | Fixed, 0.2.50 (finding 179). `featureExtendPermitted` named `e2-editor-v28`; v29 kept that worker |
| 2. Does Calc autosave? | Answered and measured on 0.2.50: 30.5 s after a committed cell |
| 3. Calc text colour, cell fill | Written, native 30/30, waits for the link |
| 4. Alignment, both apps | Written, native proof, waits for the link |

## The tree is ahead of dist/ on purpose

`web/e2-editor-app.js`, `web/e2-editor.html`, `editor-shell-v2/*`, `web/ods-editor*`, `spreadsheet-shell/*` hold the batch 3 work. **`dist/` is still generation 85.** Do not run `make e2-c-assets` or `make ods-editor-assets` until the link is in: the page on `dist/` is what 0.2.50 was packaged from.

Consequences, all expected until generation 86 is frozen:

- `build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v85.json` is red, and `make check` style targets that run it. Two new sources (`sdk/ods-editor-v3-worker.js`, `sdk/v31-alignment-worker.js`) are in its scope and the shell changed.
- `tools/check_writer_zoom.py` and `check_writer_shift_lines.py` override the page from `web/` and take the shell from `dist/`, so they fail at import (`EDITOR_ALIGN_ACTIONS`) until the assets are copied. That is a tool limit, not a product red.

## Next

1. **The owner's link.** One line, from `wasm_sdk_probe/`: `bash tools/link_demo_batch_3_owner.sh`. It links `e2-editor-v31` and `ods-editor-v3`, no core build; v29's took about 3 minutes, expect two of those. It refuses if a previous attempt exists. It prints the hashes.
2. **After the link** (agent):
   - Archive v31 as `build/archive/e2-editor-v31-<wasm8>-worker-<worker8>`, with `SHA256SUMS` and `ATTRIBUTION.md`. Add `--carrier` is already in the Makefile.
   - `make e2-c-assets`, then **P1**: `python3 -I tools/check_writer_align.py --profile e2-editor-v31 --out ...`.
   - **P2**: `cd tools; python3 check_calc_style.py --engine ../build/ods/editor-v3/profile --out ...`. Then `python3 tools/build_calc_style_profile.py --loader build/ods/editor-v3/probe.js --wasm build/ods/editor-v3/probe.wasm --worker sdk/ods-editor-v3-worker.js --exports build/ods/editor-v3/exports.txt --output dist/profiles/ods-editor-v3`, and repoint `ENGINE_OPTIONS.workerUrl` in `web/ods-editor-app.js`.
   - Neither checker has ever run against an engine. Their first red is the instrument's until shown otherwise.
   - `build_cutover_page.py --profile e2-editor-v31`, freeze generation 86 with exclusions for both new workers (template `findings/evidence/demo-batch-3/freeze-85/freeze.py`), repoint the bundle line in the Makefile.
   - Derive v86 tools and V0' (`demo-batch-3/derive/`), then the chain (`demo-batch-3/chain.sh`). **Add no file under `sdk/` or `editor-shell-v2/` while it runs**: that is what turned `v0/` red.
   - Host 0.2.51 from `host-0.2.50/derive_host_0250.py`. P3: Files, `host_batch`, `host_layout`, T6 extended to the new controls and the palette (`host_calc_theme.py` reads only what is shown, so open the popover).
3. **The owner's hand test** on 0.2.50, and whether it becomes the daily candidate.
4. **Finding 180**, the owner's call. The shipped list and heading buttons move the caret: `qBRAVO` where `BRqAVO` is right. The fix is known (spec section 6's read), needs a link and F3, F4 again.
5. The ordered-commands product arms; Microsoft formats and Calc zoom only when asked.

## Named limits and decisions

- ABI stays 6 for the alignments. Every `abiVersion === 6` gate in the shell would otherwise switch off, finding 179 with a number in place of a name.
- `L-align-blank-document`: a document of one empty paragraph has nothing to select; the answer rests on the UNO result and a readable undo stack. N2's blank arms saved the alignment.
- The Calc page has no undo button or key, so P2 has no undo cell. Native proves one write is one undo step.
- Writer keeps the selection after an alignment, unlike the other paragraph actions, which collapse it.
- A press of the alignment a Calc cell already has gives it back to `standard`, as Collabora.

## Cautions

- A worker's behaviour can depend on `manifest.profile`. `tools/check_extend_gate_instances.py` is the census; `--expect-red e2-editor-v29` is frozen history.
- Tests that pin text in `ordered_format.inc` count occurrences: `selected.type == LOK_SELTYPE_TEXT` must stay single, hence the reversed comparison in the alignment read.
- `pre-link/preprocess_same.py` compares against `46cf3eaf2`: rerun it after any engine edit. It caught a text change in `calc_cell_bridge.cpp` that behaved the same.
- Use absolute paths; a shell `cd` carries between calls.

## Section 34.4

Work since 02d (batch 3).

- **Fixed-by-execution: 3.** `v0/` red (my files appeared during the run; the tool was right). `host_shift.py` twice: a witness only pointer paths write, then a click on the page-number strip that made the empty "no refusal" greens.
- **Fixed-by-review: 3.** All Codex's, one read. The coordinate restore (N2: 16 of 33 wrong) was a design defect I had written into the spec; a link would have shipped it.
- **Fable rulings: 0.** Nothing needed one.
- Wrong statements, corrected: 1. Finding 179's draft said 0.2.40; `release.json` says 0.2.45.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs and findings in zh-TW. Linking and compiling `make` stay the owner's. Commit messages: `Co-Authored-By` yes, `Claude-Session` never.
