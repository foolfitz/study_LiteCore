# Handoff: ods-editor-v8 (Calc copy with text/html, Calc zoom) -- engine and page done, waiting for the owner's link

Checkpoint **2026-11-07**. Supersedes `HANDOFF-2026-11-06-calc-copy-and-sheets.md`. One handoff for this session.

## Where things stand

Both items the owner asked for after the 0.2.59 hand test go into **one link, `ods-editor-v8`**:

1. **Copy also writes `text/html`** (owner's A, "照 Collabora，連結一次"). This fixes the column paste that split at spaces in desktop Calc. Spec: `specs/SPEC-P-calc-copy.md` sections 9 and 10 (appends 2 and 3).
2. **Calc zoom** (owner: "Calc沒有頁面放大縮小"). Spec: `specs/SPEC-P-calc-zoom.md` (initial version plus appends 1 and 2).

Everything before the link is done and committed. **The link has not been run yet.** It is the owner's:

```
bash ~/LibreOffice/study_LiteCore/findings/evidence/calc-v8/link/link.sh
```

It takes about 3 minutes (v7 took 2 m 52 s) and writes `findings/evidence/calc-v8/link/link-01.*` and `profile-SHA256SUMS`.

## Commits this session

- `e03122f98`: both specs, criteria pinned before any counted run.
- `04390df77`: criteria corrected after **uncounted** tool shakedowns, before the counted runs:
  - copy append 3: the core's HTML export skips hidden rows and columns (`htmlexp.cxx`), so column A's HTML has 999 rows;
  - zoom append 1: a red fill covers the grid line (top/left −1 px), 200% rounds half a twip, and the document size grows with where the cursor has been, not with the zoom.
- `baa1176ed`: **the engine side.**
  - Bridge `OXSDK_ODS_COPY_HTML` (bit 27): op 15 also returns `htmlText`.
  - Bridge `OXSDK_ODS_ZOOM` (bit 28): op 16 `{tileTwips}` with closed list `kTileTwips` {7680, 5120, 3840, 3072, 2560, 1920} = 50..200%. It is stored in `gTileTwips`. Every operation calls `applyClientZoom`, and op 5's hit test divides by 256/T.
  - Makefile `ods-editor-v8-dev`.
  - Worker delta `tests/ods-v8-worker-delta.json` (`cellZoom`), with tests 6/6.
  - Entries `calc-html-zoom` in `derive_ms_formats_worker.py` and `build_ms_formats_profile.py`.
  - Native evidence in `findings/evidence/calc-v8/`: **n-copy-01 N_HOLDS** and **n-zoom-01 N_HOLDS**, each with its red cases and the v7 control.
  - em++ `-fsyntax-only` is green, with 4 positive controls red. `check_v7_syntax.py` is now parametrised (`--target`, `--define`), and its default run reproduces v7's verdict.
- `c5a1943ee`: zoom append 2, written before any P run. P-Z5 is judged by the centre cell, because twips are not comparable across zoom levels. P-Z7's zoom-only segment runs before F100 is painted.
- `381869ee8`: **the page side.**
  - SDK: `htmlText`, `setZoom`, `normalizeZoom`, `ZOOM_PERCENTS`.
  - Viewer session: `setScale`.
  - Calc session: `setZoom(percent, {centre})`. It re-reads the selection's ends at the new zoom and returns the centre cell's rectangle before and after.
  - Page:
    - Every `/15` and `*15` is now `tw()` = 15/s.
    - Zoom group at the toolbar's end (`#zoom-out`, `#zoom-level`, `#zoom-in`, all `data-zoom-group`). It is hidden without `cell-zoom` and disabled while editing.
    - The entry's font scales through `--calc-zoom`.
    - Copy writes a `ClipboardItem` with `text/plain` and `text/html`, and falls back to `writeText`. `__calcEditor.lastCopy` and `__calcEditor.zoom` are there for P.
  - The node suite is 1068/1068 and the three Calc mutation tools pass. `check_calc_copy.py` on **frozen v7** with this page is P_HOLDS 6/6 in each browser (`build/calc-copy-shake/v7-page-01`, not committed).

## Next session, in this order

1. **After the owner's link**, check the receipt: exit 0, `profile-SHA256SUMS`, and capability bits = v7's | (1<<27) | (1<<28). Then archive the profile read-only as `build/archive/ods-editor-v8-dev-<wasm8>`, as v7's was.
2. **P copy on v8**:
   `cd wasm_sdk_probe/tools && python3 check_calc_copy.py --html --out ../../findings/evidence/calc-v8/p-copy-01 --engine ../build/ods/editor-v8/profile --native-harness ../../findings/evidence/calc-v8/native-build-01/v8/calc-undo-native`
   Then `--mutate plain-only` must be MUTATION_RED in P-H1. Record both browser versions and what each browser's read-back HTML kept (`P-H1-registration`).
   - If P-H1 shows LOK's `<pre>` fallback instead of a table, the wasm core did not ship the HTML export. That would be a finding; `libscfiltlo` does list `htmlexp.o`, though.
3. **P zoom on v8**:
   `python3 check_calc_zoom.py --out ../../findings/evidence/calc-v8/p-zoom-01 --engine ../build/ods/editor-v8/profile`
   Then each of `--mutate point-15`, `no-op16` and `no-centre` must be MUTATION_RED.
   - The P zoom tool has **never run** (it needs v8). Expect tool bugs on the first run: fix them by execution and record them. Watch especially whether the name box's Enter leaves focus on the grid for the `ArrowDown`, and how the header strips' client rectangles line up with `#active-cell` (P-Z4's 1 px).
4. **Calc regression on v8**: follow `findings/evidence/calc-copy/v7-regression/` (sheets 9/9, headers, structure) with v8's profile.
5. Offer the owner a hand-test slot. Release 0.2.60 only on a named slot (CLAUDE.md, cadence). The freeze and the host package follow `release-0.2.59/` and `host-0.2.59/`. The page's `ENGINE_OPTIONS` still names `ods-editor-v7`; switch it to v8 at the freeze, and the mirror tools already accept both names.

## Cautions

- `calc-v8/native-build-01/v8/calc-undo-native` is the native harness for P-H4, so keep that path.
- The driver `tools/calc_undo_native.cpp` gained `paste` and `paint` actions. Older builds keep their own source snapshots.
- Zoom levels are the bridge's `kTileTwips`. The worker delta, `ZOOM_TILE_TWIPS` in the SDK, both native and P tools, and the unit tests read the list from there or check against it. To add a level, change `kTileTwips` and `ZOOM_TILE_TWIPS` together, because the worker test asserts the literal.
- Named limits (in the specs):
  - HTML has no hidden rows or columns, but the plain text keeps them.
  - Header labels do not scale.
  - No zoom while editing.
  - The zoom is not persisted.
  - Ctrl+wheel and Ctrl+± are still the browser's.
- Unchanged: submissions are on hold; `build/archive` is hardlinked or read-only; never check out a candidate in the host repo's working copy; unstage `session-*/profile/` when adding native evidence.
- The P-C measurement limit still applies. P can't show that a Ctrl+C's user activation survives the engine round trip, so only the owner's hand test can, and P can't see a paste into desktop Calc either.

## Section 34.4

Checks changed because of review: 0.
