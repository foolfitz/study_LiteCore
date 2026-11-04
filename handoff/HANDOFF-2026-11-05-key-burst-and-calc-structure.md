# Handoff: Writer key bursts fixed (dev) and Calc insert/delete rows and columns (dev); nothing released

Checkpoint **2026-11-05 02:40**. Supersedes `HANDOFF-2026-11-04c-host-0257-zoom-fix-released.md`. One handoff for this session.

## The owner's decisions this session

- Calc headers (dev profile `ods-editor-v6`): **B, not released yet** -- no hand-test slot; do the next features first.
- Next features: **B (Calc insert/delete rows and columns) and D (Firefox loses keys in a burst, finding 130)**.
- Before going to sleep: "需要連結還是編譯的話都請你幫我跑；若有難以決策的地方，發給fable，我授權他代我裁決". The agent ran
  the link (after `uptime` / `pgrep -a make`). No decision was judged hard enough for fable; every choice is written in the
  specs with its reason (desktop Calc / Collabora conventions).

## Done, all committed

### D: key bursts (`specs/SPEC-P-key-burst.md`, `findings/evidence/key-burst/`, commit `2b806e92e`)

- Cause: the input adapter commits one character at a time and refuses the 9th waiting one; both browsers (not only Firefox).
- The adapter (`input/input-adapter.js`) is bound byte for byte by E1-C's shell bundle, so it is unchanged. The fix is in
  `editor-shell-v2/narrow-editor-v2-session.js`: `coalesceTypedText(adapter)` wraps the session's adapter instance -- typed text
  (beforeinput + insertText, no line break) joins the waiting entry; `_enqueue` seals every waiting entry for any operation that
  is not `commit-text` (finding 111's order). Line breaks, IME and paste are not merged (limit 8 still applies to them).
- `tools/check_key_burst.py` (mirror, real keys): `kb-01` **`KB_HOLDS`** Chrome 10/10, Firefox 10/10 (40 back-to-back keys in 2-3
  inserts; undo grouping equals 150 ms typing). Reds: baseline (generation 90's session) keeps 8 keys + notice; `no-seal` reds K3
  only (`abcde`); `no-merge` as the baseline. Unit tests `editor-shell-v2/tests/key-burst.test.mjs` (11). E1-C `intact: true`.
- Codex adversarial review: no new loss or reorder; confirms the pre-existing held-second-Backspace edge (spec 4, named limit).
- Finding 130 status updated ("上限已在 dev 修好、未發布").

### B: Calc insert/delete rows and columns (`specs/SPEC-P-calc-structure.md`, `findings/evidence/calc-structure/`)

- Engine (`64a708ed1`): cell op 14 under `OXSDK_ODS_STRUCTURE` (UNO `insertByIndex` / `removeByIndex`), capability bit 25
  `cell-structure`; `probe_engine` counts op 14 as a mutation. N on the native core (`n-01`): **`N_HOLDS`** -- references adjust,
  a merge crossed by an inserted column grows (A3:B3 -> A3:C3), one undo action each, refusals (`READ_ONLY`, `STRUCTURE_REFUSED`
  for data in the last row/column and a split array formula) leave the undo count and reads unchanged; both reds red.
- Worker: hunks 8-13 in `tests/ods-v6-worker-delta.json`; profile entry `calc-headers` in `tools/build_ms_formats_profile.py`
  now also claims `cell-structure` + a `structureContract`; Makefile v6 rules add the define.
- **Linked** (agent-run on the owner's word): `build/ods/editor-v6/profile`, wasm `47e3792c`, worker `cbf3c1ef`, 2 min 31 s;
  archived read-only `build/archive/ods-editor-v6-dev-47e3792c` (the headers-only link stays as `-bd85b751`).
- SDK `changeStructure` / `normalizeStructure`; session `structurePlan` / `changeStructure` (same indices stay selected); page
  right-click menu on row/column headers and cells (`#structure-menu`), Shift+F10 / menu key, Ctrl+plus / Ctrl+minus on whole
  rows or columns, disabled items with reasons, refusal sentences (`f4cbcf77f`).
- P (`tools/check_calc_structure.py`): `p-02` **`P_HOLDS`** Chrome 18/18, Firefox 18/18; reds `above-index-plus-1`, `count-one`,
  `no-reason-title` each red in their criterion; **P-S8** `check_calc_headers.py` on the relinked profile `P_HOLDS` 145/145,
  121/121. Node suite 1038/1038; the three Calc mutation tools pass.
- Spec appends: 1 corrects P-S2's selection (column C stays, as rule 2.5 says) before any P run; 2 added a hidden-endpoint
  fallback on a premise I had not measured; **3 withdraws it** (op 0 reads hidden cells fine: 14 twips), then `p-02` was rerun.

## Next, in order

1. **Ask the owner for a hand-test slot.** The next release now carries three features: Calc headers + Calc structure (profile v6)
   and Writer key bursts (shell). At the slot:
   - Writer: generation 91 = 90 + `narrow-editor-v2-session.js` (write `e2/generations/generation-91.json` from 90's, freeze with
     `findings/evidence/zoom-comment-loop/gen-90/freeze/argv.json`'s argv, rebind the Makefile line, `v0_prime.py --generation 91`
     with `gen-90/v0/v0-prime.json`'s K arguments); Writer release regression (P5, P4, S1, P1, Z, F3, F4) plus `check_key_burst.py`
     on dist. Spec key-burst 4: a judge that counts `insertText` requests per typed key may need its reading fixed (cadence rule 4),
     not the product.
   - Calc: freeze `ods-editor-v6` into `dist/profiles/` from `build/archive/ods-editor-v6-dev-47e3792c` (check the sums), repoint
     `web/ods-editor-app.js` `ENGINE_OPTIONS.workerUrl` v5 -> v6, Calc release regression (C, CU, cell, range, autosave, P2 -- the
     tools and v5 evidence are in `host-0.2.56/release-inputs.json`) plus `check_calc_headers.py` and `check_calc_structure.py` on dist.
   - Host 0.2.58 with `host_release.py` (served delta: Calc page files, `profiles/ods-editor-v5 -> v6`, the Writer shell file).
2. Owner hand test (zh-TW when handing over): Calc -- headers (open an .ods; A.. and 1..; hidden column/row skipped; click C,
   shift-click E, drag; corner; bold a whole column and undo; Ctrl+Space / Shift+Space; scroll far and headers follow); right click
   a row header -> 上方插入列 / 刪除列, a column header -> 右方插入欄, a cell -> six items; Ctrl+minus on a whole column; undo each;
   a protected sheet shows disabled items with a reason. Writer -- type a fast burst (or paste-speed typing) in Firefox and Chrome:
   nothing lost; Backspace / arrows in the middle of fast typing keep their place.
3. Named limits (specs): structure -- sheet-protection "allow insert" options, the partial-selection Ctrl+plus/minus dialog,
   insert cells (not whole lines), multi-range selections; key bursts -- line breaks / IME / paste still one entry each.

## Cautions

- `build/archive` files are hardlinked or read-only: never write an archive file in place.
- `tools/check_calc_structure.py` and `check_key_burst.py` mirror under `build/calc-structure/<out>` and `build/key-burst-*`;
  `--out` must not exist. Do not edit `web/`, `spreadsheet-shell/`, `sdk/` while a P chain runs (each run copies them at its start).
- The native harness prints `getCommandValues(".uno:Undo")` as several lines plus an empty line: read until the JSON parses and
  consume the empty line (`check_calc_structure_native.py` `undo_count`).
- A hidden row or column is readable through op 0 (14 twips); do not build around "hidden cells have no geometry".
- Unchanged from the last handoff: four Writer mutations in `run_e2_c_product_path.py` have no anchor on the page;
  `test_v21_shakedown_common.py::test_the_real_mirror_reproduces_the_round_identity` red from before; submissions on hold; never
  check out a candidate in the host repo's working copy (it is the live app).

## Section 34.4

Checks changed because of review: 0.
