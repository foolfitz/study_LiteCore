# TASK 2026-10-13i — W9 draft: the read-only ODS viewer route, in source only

ODS plan `handoff/PLAN-2026-09-03-ods-reading.md`: §0 (route B, a separate read-only viewer, chosen by the owner
2026-09-03), §3 (gate G1–G10; G9 is the viewer page's own path), §6 W9. The owner (2026-10-13, choice C) wants
the ODS preparation that touches no product bytes and needs no link. This is a DRAFT: it is not staged to
`dist/`, not bound by any gate, and it will be revised once W7 (engine/worker: `documentType`, `set_part`,
`part_name`, `{odt, ods}` allowlist) exists.

## Hard constraints

- **No file under the five bundle-scoped directories**: `editor-shell-v2/`, `editor-shell/`, `input/`, `sdk/`,
  `reader-shell/` (`e2/editor-shell-v2-bundle-v66.json`, `scope`). Import `reader-shell/tile-scheduler.js` and
  `sdk/document-sdk.js` **unmodified**. The product page's import graph must not reach any new file.
- Nothing written under `dist/`, no profile touched, no Makefile change, **do not run `make`** (finding 041:
  static targets can build). Do not modify `web/e2-editor*`, `web/ods-decisive-probe*`, or any existing tool.
- New files only: `viewer-shell/` (session/adapter), `web/ods-viewer.html`, `web/ods-viewer-app.js`, a node
  test under `wasm_sdk_probe/tests/`, a smoke runner under `wasm_sdk_probe/tools/`, evidence under
  `findings/evidence/m4-ods/W9-viewer-draft/`.

## Shape (aim at G9, without pretending W7 exists)

- `viewer-shell/ods-viewer-session.js`: opens bytes through `createDocumentEngine` + `engine.open`, owns a
  `TileScheduler` whose document context carries `part`, and exposes `{state, documentType, parts, partNames,
  currentPart, canSwitchParts}` plus `showPart(k)`. Read-only: no editor session, no key input to the engine,
  no save.
- **An adapter is the only place that knows W7 is missing**, and says so in its state:
  - `documentType`: the handle's if present, else `"unknown (pre-W7)"`. When it is known and is not
    `"spreadsheet"`, the session refuses with a typed error (G2's injection 2 will need that).
  - `partNames`: from the engine if present, else `工作表 1…N` with `namesFromEngine: false`.
  - `showPart(k)`: if the handle has no part switch, `k > 0` is refused with a typed error and the tab is
    rendered disabled with the reason; never fake a switch by repainting part 0.
  - **The name spoof** (finding 013: `oxsdk_document_open` refuses names not ending `.odt`): done in the
    adapter only, recorded in the session state as `nameSpoofed: true`, shown on the page as a diagnostic
    banner. W7 removes it.
- `web/ods-viewer.html` + `ods-viewer-app.js`: a file input, a tab strip (one element per part; text = part
  name), a scrolling viewport painted from the scheduler, a status line (state, parts, current part, spoof
  banner). Profile chosen by `?profile=` (default `e2-editor-v14`, a writer+calc profile). zh-TW UI strings.
- Whether the engine's current part is k must be READ BACK, not inferred (G9). Pre-W7 there is no read-back;
  the state says `currentPartReadBack: null` rather than echoing k.

## Verification

1. **Node unit test** (fake engine + fake handle, both a pre-W7 handle and one WITH `documentType`,
   `partNames`, `setPart`, `currentPart`): tabs = parts; `showPart(k)` reconfigures the scheduler with part k
   and reads back; pre-W7 `showPart(1)` is refused and nothing repaints; a known `"text"` document is refused;
   the spoof flag is set only when the adapter spoofed. Exhibit red first (AGENTS.md §6): break each of these
   in the session once, show the test goes red, revert; record which assertion caught it.
2. **Browser smoke**, ONE short run, a new `tools/run_ods_viewer_draft_smoke.py` modelled on
   `tools/probe_ods_on_profile.py` (scratch mirror of `dist/` with overrides; nothing under `dist/` written).
   Through the page's own file input (CDP `DOM.setFileInputFiles`), open
   `test-docs/ods/ladder/three-sheets-distinct.ods` on `e2-editor-v14`, and in the same run
   `test-docs/ods/ladder/empty-one-sheet.ods`. Report: `opened`, `parts` (expect 3 and 1), tab count and texts,
   which tabs are enabled, `nameSpoofed: true`, `evidenceClass: "diagnostic"`, and whether the first tile of
   the three-sheet file is byte-equal to the empty sheet's first tile painted in the same run (expect not
   equal; record, it is not a gate). Before running: `pgrep -af chrome` must show no other Chrome and the 1-min
   load must be < 1.0 — another agent is running a timing-sensitive browser measurement; wait for it. Check
   the KDE wallet first (`busctl --user get-property org.freedesktop.secrets
   /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked` → `b false`, else
   stop).
3. **Bundle unchanged**: find the tool that computes the shell bundle digest (it was used 2026-09-03 against
   `e2/editor-shell-v2-bundle-v43.json` with `problems: []`), run it in its read-only verify mode against v66,
   and record that the digest and `included` list are unchanged. If you cannot find a read-only mode, do not
   run anything that writes; say so.

## Deliverable

`findings/evidence/m4-ods/W9-viewer-draft/README.md` (English) starting `## SUMMARY` (≤ 30 lines): files
added, what is adapter-only (the pre-W7 list), unit test N/N and the red cases, the smoke report's fields,
the bundle check, and a short "what W7 must provide for this draft to meet G9" list. Commit only your new
paths (`git add … && git commit -m "…" -- <paths>`; retry if `.git/index.lock` exists). English commit message
ending with `Co-Authored-By: Claude Sonnet <noreply@anthropic.com>`; no `Claude-Session:` line.
