# Handoff: Calc copy (engine side done, link with the owner) and Calc sheets (done on dev)

Checkpoint **2026-11-06**, last updated **2026-11-07** after the 0.2.59 hand test. Supersedes `HANDOFF-2026-11-05b-host-0258-installed.md`. One handoff for this session.

## The owner's decisions this session

- From the 0.2.58 hand-test candidates: **A, "Ctrl+C + cross-sheet UI"**.
- "Seeing a sheet's identity": **"請去查 Collabora 怎麼做"**. The finding is in `SPEC-P-calc-sheets.md` section 1, and the agent implemented Collabora's three.
- Ctrl+C turned out to need a link (my first "maybe page-only" was wrong: `transobj.cxx` `lcl_reduceBlock` cuts whole-range copies to the used area with a moving start, so `partText` cannot be sliced). Asked how to schedule it, the owner chose **A, "both in parallel"**: the agent does the page work, and the owner runs the link.

## Done, all committed

- `337a00f45`: **Calc copy, engine side.** Bridge op 15 (`OXSDK_ODS_COPY`) selects the range in the core, takes LOK `getTextSelection("text/plain;charset=utf-8")`, then restores the selection. Capability bit 26 `cell-copy`. Worker delta `tests/ods-v7-worker-delta.json`. Makefile `ods-editor-v7-dev` (a new dev profile, because v6 is frozen). Native `findings/evidence/calc-copy/n-01` is **N_HOLDS**: the red case is red, and the control refuses op 15. The em++ `-fsyntax-only` checks pass with positive controls (`pre-link-syntax-02`; the first run was a parser bug in my tool, recorded in that README).
- `983ad536a`: **Calc sheets, page only** (frozen v6 engine, no link): a lock on a protected sheet's tab (from `partInfo`'s `protected`), `#sheet-position` "工作表 N／M", a name box that takes `Sheet.A1`, `'Sheet name'.A1` and `Sheet!A1`, and pointed references. With the caret in a slot, a click inserts `B1` or `$Sheet.B1`, a drag inserts a range, and a tab only shows its sheet without committing. Enter or Esc goes home first. `findings/evidence/calc-sheets/p-02` is **P_HOLDS** 9/9 in Chrome and Firefox, and both red cases are red where the spec says. E1 (native) records the core's quoting rule.
- `aa169eca1`: `tools/check_calc_copy.py` (P-C1..P-C5 plus the `anchor-only` red case), ready, and `tests/calc-copy.test.mjs` 7/7.
- The node suite (every `*.test.mjs` outside build/ and dist/) passes 1045/1045 after `983ad536a`, and 1052 with `calc-copy.test.mjs`. The three Calc mutation tools pass; `!state.away` is now one of the 12 format predicates.

## The link and the page runs (2026-11-06, after the link)

- The owner ran `link.sh`: exit 0, 2 m 52 s. `build/ods/editor-v7/profile`, wasm `36d0e1b8`, worker `8b49b46e`, archived read-only as
  `build/archive/ods-editor-v7-dev-36d0e1b8`.
- `findings/evidence/calc-copy/p-01` was red in P-C3 only, because of the spec: "the undo button stays disabled" assumed something the page
  never does. Spec append 1 withdrew it and measures one undo finding nothing. `p-02` is **P_HOLDS** 6/6 in each browser.
  `p-red-anchor-only` is red in P-C1.
- `v7-regression/`: sheets 9/9, headers 145/121, structure 18/18, all **P_HOLDS** on v7 (`60e8786da`).

## Release 0.2.59 (the owner chose A, "現在發布給你手測")

- `8f064145e`: `ods-editor-v7` frozen into dist (`FROZEN_EQUAL`), the page points at v7, and six mirror tools learned v7's URL.
- `findings/evidence/release-0.2.59/`: node 1052/1052, the Calc mutation tools pass, and the Calc release regression (10 nets, 15 min)
  holds on dist v7. Writer was not re-run: its bytes are 0.2.58's (generation 91), so the gate reads 0.2.58's records (cadence item 5).
- `findings/evidence/host-0.2.59/` (`71b69d389`): host `480ba6b`, engine `a2e67f21`. Gate 32/32, `DELTA_HOLDS`, `PACKAGE_HOLDS`,
  `CANDIDATE_INSTALLED` (12:44), Files 52/52, capture holds. New arm `tools/calc_host_arm.py --arms sheets copy`: `H_CALC_HOLDS`.
- The hand-test script is `HANDTEST-2026-11-06-host-0.2.59.md` (10 items). The fixtures are in admin's `手測-0.2.59/`.

## Hand test of 0.2.59 (2026-11-06/07)

Record: `findings/evidence/host-0.2.59/handtest-2026-11-06/README.md` (`25f1035f8`, `52e333467`).

- Owner: "測完了，writer 沒問題". Asked about the other Calc items, the owner said all are normal ("都正常").
- One finding: copying a column (a multi-row range) and pasting it into desktop LibreOffice Calc splits cells at spaces (A1 `原始中文 Alpha` -> `原始中文` | `Alpha`). One cell or one row does not split.
- Cause, measured: the clipboard text is correct TSV. Desktop Calc sends multi-line `STRING` through the Text Import dialog with the user's last-used separators (`libreoffice-26-8/sc/source/ui/view/viewfun5.cxx` around line 760, `SC_PASTETEXT`, `SaveParameters`), but pastes HTML before `STRING` when both are offered (`sc/source/ui/view/viewfun3.cxx`, `PasteFromSystem`). Collabora puts `text/html` and `text/plain` (`cool-26-04/browser/src/map/Clipboard.js`).
- Owner's decision: **A, "照 Collabora，連結一次"**. The engine's copy op also returns the core's own `text/html`, and the page writes both formats.
- Owner's added request, verbatim: "如果要連結的話，幫我加一個功能，Calc沒有頁面放大縮小". That is Calc page zoom, in the same link.
- Still open from the owner's earlier list: Ctrl+click multi-selection, renaming sheets, dragging column widths and row heights, freezing panes.

## Next session: the ods-editor-v8 link batch (copy text/html + Calc zoom)

Work order, in this order. Both items go into one link that the owner runs.

**1. Copy `text/html`.** Write SPEC-P-calc-copy append 2 first. The spec is append-only, and its criteria are pinned before any measurement that counts.

- Engine: op 15 is `accessCopy` in `wasm_sdk_probe/src/calc_cell_bridge.cpp`. It selects the range, calls `doc->pClass->getTextSelection(doc, "text/plain;charset=utf-8", nullptr)`, then restores the selection. Add a `text/html` read while the range is still selected (before `restore()`), under a new define (suggested `OXSDK_ODS_COPY_HTML`), with capability bit 27. Bits 0-26 are taken in `src/sdk_api.h` (checked: 26 is `OXSDK_CAPABILITY_CELL_COPY`, nothing at 27-31).
- Profile: a new dev profile `ods-editor-v8`. v7 is frozen in `dist/profiles/ods-editor-v7` and released in host 0.2.59.
- Worker: derive the delta from the frozen v7 worker (`dist/profiles/ods-editor-v7/sdk-worker.js`) with a new entry in `tools/derive_ms_formats_worker.py`, plus a new entry in `tools/build_ms_formats_profile.py`. In both, v7's entry is `calc-copy` (base v6).
- Makefile: a v8 block modelled on the v7 block (`ods-editor-v7-dev`, around line 6124). The bridge object's rule there lists its defines by hand, not through `ODS_EDITOR_V7_DEFINES`, so add the new define in both places.
- Pre-link syntax check: make the define and the marked blocks parameters of `tools/check_v7_syntax.py` (its `MARK` is hardcoded to `OXSDK_ODS_COPY`). Parametrise it, do not copy it (cadence item 2).
- Page: `web/ods-editor-app.js` currently calls `navigator.clipboard.writeText(result.plainText)` (around line 1195). Change it to `navigator.clipboard.write([new ClipboardItem({...text/plain, text/html...})])`, with `writeText` as the fallback. Measure on both browsers whether `ClipboardItem` with `text/html` works (record the Firefox version) and what Chrome's HTML sanitising leaves. In P, read back with `navigator.clipboard.read()`.
- Native first measurement: the pattern is `tools/build_calc_undo_native.py` + `tools/check_calc_copy_native.py` (`findings/evidence/calc-copy/n-01`). It should show that the core's HTML parses into one `<td>` per cell with the cells' texts, which is the property that matters. If feasible, also try a native LOK paste of that HTML into a sheet.

**2. Calc zoom.** Nothing is measured yet.

- Known: the bridge forces `doc->pClass->setClientZoom(doc, 256, 256, 3840, 3840)` ("1 CSS px = 15 twips") in `access()` of `calc_cell_bridge.cpp`, and again in `accessHeaders` (op 13), which depends on that mapping. `SPEC-P-demo-batch-1.md` line 12 cites it as `calc_cell_bridge.cpp:245`; that line number is stale.
- Known: `web/ods-editor-app.js` converts with a fixed 15 throughout: `place()` and `revealCell()` divide twips by 15, so do the cell editor placement and the surface size; `point()` multiplies pixels by 15. The header gutter is in fixed CSS px (`HEADER_LEFT=48`, `HEADER_TOP=20`).
- Writer has a zoom: `specs/SPEC-P-demo-batch-1.md` section 3 (its named limit `L-calc-zoom-not-done` is this item), and `wasm_sdk_probe/tools/check_writer_zoom.py` (Z0-Z8).
- Before specifying, measure what the engine and the page do, and read how Collabora zooms Calc (`cool-26-04/browser/src`). It probably needs the engine, hence the same link, but establish that first.

**3. Link and release.** The owner runs the link (`findings/evidence/calc-copy/link/link.sh` is the v7 pattern). Then P on v8 with its red cases, and the Calc regression on v8 (`findings/evidence/calc-copy/v7-regression/` is the pattern). Then offer the owner a hand-test slot. Release 0.2.60 only on a named slot (CLAUDE.md, cadence).

## Cautions

- **Measurement limit of P-C (named in the tool):** Chrome is granted clipboard permission and Firefox runs with `dom.events.testing.asyncClipboard`. Both relax the user-activation rule, so P cannot show that a Ctrl+C's activation survives the engine round trip. Only the owner's hand test can.
- While another sheet is shown for a formula, do not read cells through `readCell` in tools: it asks the engine for the cell on the sheet then shown. Judge "nothing committed" by the revision instead (spec append 1).
- `check_calc_format_entry_mutations.py` parses `formatAvailable` and accepts only `state.*`, `!pendingEntry` and `!dragWork` terms. Write any new eligibility term as a state field, the way `state.away` is. `check_calc_range_mutations.py` needs `cell.column!==column` to occur once in `calc-document-sdk.js`.
- The P tools' mirrors live under `build/calc-sheets/` and `build/calc-copy/`. Snap Firefox cannot read fixtures under `/tmp`, so give `--out` paths outside it.
- `git add` of a native-run evidence folder stages the harness's `session-*/profile/` directories. Unstage them: earlier commits keep only fixtures, reports and observations.
- Unchanged: submissions are on hold; `build/archive` is hardlinked or read-only; never check out a candidate in the host repo's working copy.

## Section 34.4

Checks changed because of review: 0.
