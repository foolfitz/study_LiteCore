# Handoff: hosts 0.2.60 and 0.2.61 released; the Calc zoom anchors on the active cell

Checkpoint **2026-11-08 ~12:25**. Supersedes `HANDOFF-2026-11-07-calc-v8-copy-html-zoom.md`. One handoff for this session.

## Where things stand

1. **0.2.60 released and hand-tested.** The owner named the slot on 2026-11-07 at 23:24.
   - `ods-editor-v8` was frozen into dist (`release-0.2.60/calc-v8-freeze/`, `FROZEN_EQUAL`), and the page moved to it. Seven
     mirror tools learned v8's URL.
   - The Calc release regression held on dist v8. Gate 36/36, `DELTA_HOLDS`, `PACKAGE_HOLDS`, installed at 23:51, Files 52/52.
   - The new host arms `calc_host_arm.py --arms zoom copy-html` are `H_CALC_HOLDS`. The `copy-html` arm runs P-H4 after the
     browsers close, with `--native-harness`.
   - The capture was `holds: false`, red only on lock rows. files_lock deleted one expired row when the run's own browsers
     previewed `手測-0.2.59/1-calc.ods` (`host-0.2.60/README.md`, access log saved).
   - Hand test (`host-0.2.60/handtest-2026-11-07/`): no item failed, so the desktop-Calc paste is fixed. One UX request: zoom
     about the view's centre shows empty cells when the data fills only the top rows.
2. **The zoom anchor (SPEC-P-calc-zoom append 5, the owner's choice C).**
   - The anchor is the active cell's top-left while it is in view, else the view's top-left. Collabora falls back to the
     selection's centre and then to the view's centre instead, and the code comment says so in English, as the owner asked.
   - It is a page-only change (`zoomAnchor()`/`zoomTo()` in `web/ods-editor-app.js`). P-Z5 was rewritten and P-Z10 added, and
     both were committed before any run of the new page.
   - `calc-zoom-anchor/p-anchor-01` is `P_HOLDS` 51/51 in both browsers. The red case `centre-anchor` is red at P-Z5;
     `fallback-centre` is red only at P-Z10.
3. **0.2.61 released** on the owner's word (A), with the same engine. One served file changed (`ods-editor-app.js`). The
   regression held (`release-0.2.61/`). Gate 30/30, installed at 12:14, Files 52/52, capture holds, and `--arms zoom` is
   `H_CALC_HOLDS`. **The hand test is pending**: `HANDTEST-2026-11-08-host-0.2.61.md`, 5 items, with fixtures in
   `手測-0.2.61/`.

## Next session

1. Record the owner's 0.2.61 hand test in `findings/evidence/host-0.2.61/handtest-2026-11-08/`, the way
   `host-0.2.60/handtest-2026-11-07/` was recorded.
2. At the next engine link, fix `L-calc-zoom-engine-reuse`: reset `gTileTwips` when a document opens.
3. Still open from the owner's earlier list:
   - Ctrl+click multi-selection;
   - renaming sheets;
   - dragging column widths and row heights;
   - freezing panes.

## Cautions

- **Native-run evidence stages `/profile/` paths.** `copy-html` runs (mirror and host arm) write
  `*-P-H4/session-paste/profile/`, and both releases had them staged. Remove each with `git rm -r --cached <dir>`, then recount
  as a separate step before committing.
- **`Instance(HOST)` needs `host-stack/bin` first on PATH.** Without it, `ddev describe` is the real ddev, and a WebDAV MKCOL went
  to the old router (404, nothing written). The fixture PUT now asserts `inst.base`.
- **Release regression names** are suffixed per release (`-0260`, `-0261`), because mirror folders are `build/calc-*/<name>`.
- **A prediction of mine was wrong**: that the host CSP would turn P-H3 red. It passed in both browsers. Whether the CSP blocks
  the same script without automation is not established.
- Unchanged:
  - submissions are on hold;
  - `build/archive` is read-only;
  - never check out a candidate in the host repo's working copy;
  - P cannot see a real Ctrl+C's user activation, nor a paste into desktop Calc.

## Section 34.4

Checks changed because of review: 0.
