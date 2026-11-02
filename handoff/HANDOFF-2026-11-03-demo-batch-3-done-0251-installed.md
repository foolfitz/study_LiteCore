# Handoff: demo batch 3 done, host 0.2.51 installed, batch 4 is recorded

Checkpoint **2026-11-03, after the 0.2.51 install**. Supersedes `HANDOFF-2026-11-02e-demo-batch-3-host-0250-link-next.md` for what is next. K's numbers in `HANDOFF-2026-11-02b-k-0245-holds.md` stand.

## State

- **Nominal shipped: 0.2.45** (K holds). It carries finding 179. **Installed on the own stack: 0.2.51**, uncounted: host `1b8c667`, engine `60fd728f61134b05`, Writer on `e2-editor-v31`, Calc on `ods-editor-v3`, shell generation 86 (`535c474c`).
- All four points of the owner's report on 0.2.49 are on the host. `findings/evidence/demo-batch-3/README.md`, `findings/evidence/host-0.2.51/README.md`.
- **Nothing of ours is running. Nothing is pushed.** The owner pushes (`git push -u github main` from this repo; the host repo likewise, branch `host-0.2.51`).

## Next

1. **The owner's hand test on 0.2.51**, and whether it becomes the daily candidate. Reload open tabs. 0.2.50's hand test was never reported; 0.2.51 contains it.
2. **Demo batch 4**, `specs/SPEC-P-demo-batch-4.md`. Three things, one link, one regression:
   - H1 to H4 in a menu from the heading button. New actions: `heading-level-1-only` is a manifest limit, not a page limit.
   - Heading and list apply and take off on the same button (owner, 2026-11-02: separate buttons go against ordinary use). Today a second press does nothing; `cancel-today/` measured it.
   - Finding 180, the caret after these buttons, by the read in demo batch 3 spec section 6.
   The spec's section 4 holds the design direction and Collabora's way, with paths. Pin the criteria before implementing. **The link needs the owner's word again**: "連結你幫我跑" covered the batch 3 link.
3. Ordered-commands product arms; Microsoft formats and Calc zoom only when asked. `demo-to-colleagues-goal` memory: zoom, Calc tab scrollbars, Microsoft files are the owner's stated order.

## Before batch 4 is designed

Three facts decide its shape, all read this session:

- The toggle cannot be page-only. The worker's `format` projects B, I, U, strike only (`sdk/v31-alignment-worker.js:525`); `listBullet`, `listNumber`, `paragraphStyle` stop there. Finding 021 measured those caches not following the caret, on an older engine; re-measure before trusting them.
- Collabora's toggle lives in core: a bare `.uno:DefaultBullet`, and `sw/source/uibase/shells/txtnum.cxx` reads `SelectionHasBullet()`, the document and no cache. Finding 030 is why ours carries `On`. Bare dispatch needs a postcondition that accepts both directions.
- `tools/run_e2_c_product_path.py` presses `set-list-none` and `set-paragraph-body`. Removing the buttons breaks the runner, so it changes with them.

`tools/check_writer_align.py`'s `P1c/control/list-button-still-moves-the-caret` pins finding 180 as a control. It turns red when 180 is fixed; it goes with the fix.

## Named limits and decisions

- ABI stays 6.
- `L-align-blank-document`: as in 02e.
- The Calc page has no row or column headers, so no whole column on the product path; the limit is native (N1). No undo on the Calc page.
- A refused Calc range disables the buttons and says why in `title`, as B, I, U do. No toast.
- F3's clear wait: the next generation's F3 runner takes the toast wait as a replacement, or the cell reds every few runs (finding 178's append).

## Cautions

- **The regression chain does not run the unit suites or the mutation tools.** `node --test editor-shell-v2/tests/*.test.mjs`, `node --test tests/calc-*.test.mjs tests/ods-*.test.mjs`, `tools/check_calc_{format_entry,range,autosave}_mutations.py`. Two of the tools had refused to run since batch 3, on anchors that batch duplicated. Run them after any page change.
- A judge that reads four arms hides the rest: `f4-86/firefox` held the same NOT_ESTABLISHED cell and F4 read 24/24. A census over `report.json` files found it.
- A rate decides what a passing rerun is worth. At a natural 1/4, three greens are 42% luck. Read the requests.
- `check_calc_style.py`'s `mirror` and `run_calc_editor_browser.py` map both `ods-editor-v2` and `-v3`; the next Calc profile needs a line in the second.
- Use absolute paths; a shell `cd` carries between calls.

## Section 34.4

Work since 02e.

- **Fixed-by-execution: 8.** P2's sample on a glyph. P2's merge range, twice (focus pulled to column A by the merge, then a skipped hidden row). P2 reading the toast where the page uses `title`. P1's swap mutation that did nothing. `host_batch3.py` calling a helper from the wrong module. T6 comparing an unpainted `color`, and naming controls that have ids. `derive_host_0251.py`, an apostrophe.
- **Fixed-by-review: 0.** No review this session; Codex's MCP failed to connect and nothing needed it.
- **Fable rulings: 0.**
- Product gaps found: 1, the refused colour and alignment buttons saying nothing. Test gaps: 2 idle mutation tools, one untested `setStyle` path.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs and findings in zh-TW. Compiling `make` stays the owner's unless they say otherwise for that build. Commit messages: `Co-Authored-By` yes, `Claude-Session` never.
