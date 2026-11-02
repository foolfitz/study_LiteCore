# Handoff: demo batch 1 done, host 0.2.47 installed, the owner's hand test is next

Checkpoint **2026-11-02 ~14:00 +0800**. Supersedes `HANDOFF-2026-11-02b-k-0245-holds.md` for what is next; K's numbers there stand.

## State

- **Nominal shipped: 0.2.45** (K holds). **Installed on the own stack: 0.2.47**, an uncounted candidate: host `d6cbbd9`, engine `268e3009dbf33a5a`, Writer `e2-editor-v29`, shell generation 84 (`3998f606`), page `c377b9f2`, HTML `6800b2d5`, Calc `ods-editor-v2`, viewer `ods-viewer-v3`.
- Nothing of ours is running. Local commits are not pushed.
- Spec: `specs/SPEC-P-demo-batch-1.md`, results in section 7. Evidence map: `findings/evidence/demo-batch-1/README.md`, `findings/evidence/host-0.2.47/README.md`.

## What the owner asked

For a demo to colleagues: zoom on the editing page, the Calc tab scroll, opening Microsoft documents. The third was answered **C: not this time**. Calc zoom was to ride that link, so it is not done either (`L-calc-zoom-not-done`).

## Done

- **Calc.** Each sheet keeps its scroll and active cell while the document is open, on the editor and the viewer. Not "always the top": a sheet seen before comes back where it was left, as in Collabora's `SheetSwitch.ts`. A sheet not seen before starts at the top with A1. `showPart` used to read A1 on every switch, so the active cell had to be kept as well or the next arrow key jumped to the top.
- **Writer.** Toolbar `-`, percent, `+`; 50 to 200; 100% is 1 CSS px = 15 twips; the default is the old fit, the percent button returns to it. Horizontal scroll and caret follow when the paper is wider than the desk. View controls are exempt from the fail-closed view-only rule (`VIEW_CONTROLS`), or a read-only document could not zoom.

## The regression, and why the mirror could not see it

`flex: none`, needed so a zoomed paper is not shrunk, exposed 15 px the flex shrink had hidden: on an empty desk the first layout runs before the vertical scrollbar exists. Chrome at 780 px got a horizontal scrollbar 0.2.45 does not have. Fixed with `scrollbar-gutter: stable`. Found by `host_batch.py` on 0.2.46, which is why 0.2.46 exists and is not a candidate. **The mirror opens a default document first, so its desk always has the scrollbar; a mutation there stays green** (`writer-zoom/z10-red-before`). Z10 is judged on the host, and its red is the real 0.2.46.

## Next

1. The owner's hand test on `https://litecore.localhost:18443`, then their word on whether 0.2.47 replaces 0.2.45 as the daily candidate.
2. Still open from 11-02b: the ordered-commands product arms, 18 cells with a right answer and 24 records (SPEC-M3-ordered-commands 21.2 and 21.3); the owner put them behind the demo.
3. Microsoft formats and Calc zoom, when asked. What was read: both wasm files carry the Word and Excel filters; `sdk_api.cpp:126` and `:189-191` refuse the names and the save formats, so it needs a link; no core tree has Impress. Before anything else, open 3 to 5 real documents with the `.odt` name workaround as a diagnostic.

## Reds that are not this batch's, left as they are

- `editor-shell-v2/tests/page-select-all.test.mjs` "U2 wiring" pins `e2-editor-v26`; the suite is 565/566.
- `tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree` reads the tool's default manifest, still v76.
- `tests/test_product_path_mutations.py` `copy-lies`: its target string is gone since finding 175's page.

Each was checked against the commit before the batch.

## Cautions

- `run_v84_*`, `judge_v84_*`, `v84_four_arms_identity.py` read `web/e2-editor.html` live. Any HTML change means F4 again, and V0' needs a new directory: `derive_v0_prime.py <dir>`.
- `check_writer_zoom.py --arms` is a diagnostic; its verdict line still says `Z_HOLDS` over the arms it ran.
- `host_batch.py` drives C on the editor page only. The viewer's C is mirror evidence.
- A shell `cd` carries between calls. A `cd` into `cool-26-04` moved the session's root there and two reads failed on relative paths. Use absolute paths.

## Section 34.4

- **Fixed-by-execution: 3.** The tile key's separator in `check_calc_sheet_view.py`; `Instance.upload` only takes files under `dist/`; the `flex: none` regression and Z10.
- **Fixed-by-review: 0. Fable rulings: 0.**
- Wrong statements, corrected: 2. "The `no-gutter` mutation goes red at Z10" (spec append 1, corrected before the fix). "Never measured" about the ordered arms, corrected to the owner in the same session: native and old-engine measurements exist.

## Addendum, same day

The owner's hand test passed: 「測試皆通過」. Next item 1 is closed. 0.2.47 stays installed as the daily uncounted candidate; nominal shipped stays 0.2.45. Nothing is waiting on the owner.

## Addendum 2, same day: batch 2, host 0.2.48 installed

The owner asked for Save and Close at the same place on Writer and Calc, as in Collabora. Spec `specs/SPEC-P-demo-batch-2.md`, results in section 6; `findings/evidence/host-0.2.48/README.md`.

- Save is the first toolbar control on both pages, a plain icon. Close is at the far right of the title row on all three pages. Host `0411329`, engine `a632c4463e700493`, HTML `80162183` and Calc `714dba8f`; generation 84 unchanged.
- The owner's screenshot also showed the dark theme washing the Writer toolbar out: contrast 1.51. Both toolbars now set their own ink. Outside the toolbar nothing changed (`L-toolbar-only-theme`): Calc's formula bar and sheet tabs stay dark, and Nextcloud fades `<em>`, so Calc's `I` reads lighter than `B` and `U`.
- `capture-after.py` is red on one clause, the lock table, because the owner's two tabs were open and refreshing their locks (`L-capture-after-live-lock-refreshed`). Those tabs still run 0.2.47's page until reloaded.
- The separator after Save is `.after-save`, deliberately not `.sep`: the host hides by `.sep:nth-of-type(n)`, which counts spans on their own.
- Waiting on the owner: the hand test.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs in zh-TW. Linking and compiling `make` stay the owner's. Commit messages: `Co-Authored-By` yes, `Claude-Session` never.
