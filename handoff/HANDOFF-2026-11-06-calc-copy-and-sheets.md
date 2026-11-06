# Handoff: Calc copy (engine side done, link with the owner) and Calc sheets (done on dev)

Checkpoint **2026-11-06**. Supersedes `HANDOFF-2026-11-05b-host-0258-installed.md`. One handoff for this session.

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

## Next

Waiting for the owner's hand test of 0.2.59. Record the result as `findings/evidence/host-0.2.59/handtest-2026-11-06/README.md`, the
way 0.2.58's was. Items 1 and 2 matter most: only a real browser shows whether a real Ctrl+C may write the clipboard after the engine
round trip. Still open from the owner's list: Ctrl+click multi-selection, renaming sheets, dragging column widths and row heights,
and freezing panes. Renaming and widths need a link; batch them.

## Cautions

- **Measurement limit of P-C (named in the tool):** Chrome is granted clipboard permission and Firefox runs with `dom.events.testing.asyncClipboard`. Both relax the user-activation rule, so P cannot show that a Ctrl+C's activation survives the engine round trip. Only the owner's hand test can.
- While another sheet is shown for a formula, do not read cells through `readCell` in tools: it asks the engine for the cell on the sheet then shown. Judge "nothing committed" by the revision instead (spec append 1).
- `check_calc_format_entry_mutations.py` parses `formatAvailable` and accepts only `state.*`, `!pendingEntry` and `!dragWork` terms. Write any new eligibility term as a state field, the way `state.away` is. `check_calc_range_mutations.py` needs `cell.column!==column` to occur once in `calc-document-sdk.js`.
- The P tools' mirrors live under `build/calc-sheets/` and `build/calc-copy/`. Snap Firefox cannot read fixtures under `/tmp`, so give `--out` paths outside it.
- Unchanged: submissions are on hold; `build/archive` is hardlinked or read-only; never check out a candidate in the host repo's working copy.

## Section 34.4

Checks changed because of review: 0.
