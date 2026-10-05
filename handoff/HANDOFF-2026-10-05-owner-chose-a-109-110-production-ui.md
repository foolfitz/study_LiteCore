# Handoff, 2026-10-05 — owner tested the product by hand; chose A (stop 109's data loss, fix 110, hide the harness controls)

Entry points: this file; `findings/109-a-delete-at-a-paragraph-boundary-kills-the-session-and-the-edits-are-gone.md`, `findings/110-the-host-page-repaints-nextclouds-header-and-has-no-close-button.md` and their `findings/evidence/109/`, `evidence/110/` READMEs; the owner's screenshot `findings/evidence/109/owner-screenshot-2026-10-05.png`.

Picks up from `handoff/HANDOFF-2026-10-03-installs-elsewhere-on-0.2.5.md` (J done, `INSTALLS ELSEWHERE` on 0.2.5). Nothing in the gate documents changed since; `main` at `c6db9a01` plus this file, not pushed.

## What the owner reported (2026-10-05, dev instance, host 0.2.5)

1. Pressing 「前刪」 errors. → **finding 109**, worse than reported: a delete at a paragraph boundary — toolbar 「⌦ 前刪」 or the **Delete key** at a paragraph's end, the **Backspace key** at its start — puts the session in `restart-required` with no checkpoint; save is then refused (`EDITOR_NOT_READY`) while every button still looks enabled; 「重新開啟」 reloads the last saved bytes. Unsaved edits are lost. Reproduced 4/4 in Chrome 151 (`evidence/109/`, probe `evidence/109/probe.py`); Firefox not measured. The engine refuses **before mutating** and says so (`no mutation was dispatched; start a fresh Worker`) — the barrier's selection of the paragraph separator is left in place, which is the blue highlight in the owner's screenshot.
2. Nextcloud's header looks covered; no close 「X」 like richdocuments. → **finding 110**: the host prints the product page's `<style>` into Nextcloud's page; its `body { background: var(--bg); display: flex; height: 100vh }` replaces the themed background (Files page `body`: `rgb(0,103,158)` + theming image; editor page: `rgb(244,246,248)`, no image), so the header's white icons sit on light grey. It also restyles every `button`/`select`/`input[type=text]`, Nextcloud's own included. The host has no close control.
3. 「前刪、後刪、分段、換行 should not appear in production software.」 Agreed, and the inventory is longer (below).
4. Shift+Enter: tested by the owner, it inserts a line break; the line before it then looks "distributed". **Not our defect**: the document's body paragraphs are justified and its `settings.xml` has `DoNotJustifyLinesWithManualBreak` = `false` (saved by LibreOffice 7.3.2.2), so a line ending in a manual break is stretched — desktop LibreOffice renders it the same way. Told the owner; no action unless they decide otherwise.

**Owner chose A (2026-10-05):** do 109's stop-the-loss, 110, and hiding the harness controls together, so the M3 re-count is paid once. Not chosen now: B (only the data-loss fix), C (real paragraph merging — engine work and a relink; a later round).

## The plan (not started; nothing implemented)

Write each item's acceptance criteria into a spec **before** implementing (CLAUDE.md "驗收判準的形式"), with its "if never done" default. Keep the verification proportionate (owner, 2026-10-03: don't chase verbatim text; the six-runner re-count is the existing protocol, not something to grow).

### A1 — 109: a boundary refusal must not lose content (JavaScript only, no relink)

Facts to start from (read, not yet measured unless said):
- Engine: `wasm_sdk_probe/src/probe_engine.cpp` — the selection barrier's `EDITOR_BOUNDARY_UNSUPPORTED` (~:3396, `finishSelectionBarrierError(…, selected.type != LOK_SELTYPE_NONE)` — the third argument appears to say a selection is left behind); a pre-dispatch semantic refusal (~:3813, `deleteHasSafeSemanticPrecondition` :1929) used when `semanticReadback` is on.
- Shell: `editor-shell-v2/paragraph-editor-session.js` `recoveryFor` maps **every** `EDITOR_BOUNDARY_UNSUPPORTED` to `"restart"` (comment cites E1-B §5); `editor-shell/editor-session.js` ~:319 blocks the queue as `restart-required`. **`editor-shell/editor-session.js` is hash-registered by E1-C and cannot be edited** (see the comments in `narrow-editor-v2-session.js` around finding 046's residual: overrides go in `NarrowEditorV2Session`).
- `narrow-editor-v2-session.js` already takes a checkpoint before boundary-capable **moves** (`BOUNDARY_CAPABLE_MOVES`, `_checkpointBeforeBoundaryMove`), not before deletes.

Measure first, then choose (write the choice and why into the spec):
- (a) In the refused state, can the worker still serialise the document (the content is unchanged)? If yes: save the current bytes as a checkpoint, then restart from it — zero loss.
- (b) Otherwise: when the document is dirty, take a checkpoint before `delete-backward`/`delete-forward` (the existing mechanism's shape; cost = one save per delete while dirty — measure it on a realistic document like the owner's 563 KB one).
- Also: in `restart-required`, buttons must not look pressable.
- The regression net must gain the user's path: real keys (Delete at paragraph end, Backspace at start) after a mouse-placed caret, with typed-but-unsaved content, asserting the content survives. That arm is the one that would have caught 109.

### A2 — 110: the host page (host repo `~/Projects/Nextcloud_Apps/litecore`, next version 0.2.6)

- Scope the product page's style to the editor's container (`templates/editor.php`, `lib/Controller/EditorController.php` `editor()` re-wraps the page's `<style>`/`<body>`): `body` rules onto the container, element selectors prefixed. Measure afterwards: the editor page's `body` background equals the Files page's; Nextcloud's buttons unstyled by us.
- A title bar like richdocuments': file name + close button back to Files; leaving keeps the page-honesty rules (unsaved → asked; the host decides `watchUnsaved`, SPEC-M3-page-honesty §7).
- Host JS change → `info.xml` version bump + `ddev occ upgrade` (standing rule).

### A3 — production UI in Nextcloud (prefer the host, avoid changing the page's bytes)

The page `wasm_sdk_probe/web/e2-editor.html` is pinned by sha in the M3 runners and the gates; changing it moves the page identity. Hiding in the host's own CSS keeps the page's bytes. **Check first** that every runner drives these controls programmatically (`PRESS` = `button.click()` works on hidden elements) and not by coordinates; list any that do.

Hide in the Nextcloud context (inventory from the owner's screenshot):
- the yellow developer explanation block; the subtitle 「產品 v2 契約，十五個動作」;
- the fixture `<select>` (the empty box at the toolbar's left) and 「📂 開啟檔案」;
- ◀ ▶, 「⌫ 刪除」, 「⌦ 前刪」, 「↵ 分段」, 「↳ 換行」 (keyboard covers them: Backspace/Delete, Enter, Shift+Enter — the owner confirmed Shift+Enter);
- 「要插入的文字」 + 「插入」;
- the status bar's internals (修訂, 佇列, 世代, 檢查點, 上次操作 latency) — keep something human (saved / unsaved);
- raw engine error codes in toasts (e.g. `EDITOR_BOUNDARY_UNSUPPORTED：…`) — map to plain Chinese or hide (this one touches the page; decide whether it waits for a page change).

Keep: 復原/重做, B I U S, 清除格式, 標題/內文, 項目符號/編號/移除清單, 儲存.

### Then

- Firefox for 109 (before and after the fix).
- The six M3 runners re-counted on the new host (as in the 0.2.4 and 0.2.5 rounds; see `evidence/m3-page-honesty/RESULT.md` and `evidence/m3-zstd/` for the list and commands). install-elsewhere on 0.2.6 only if the owner asks.
- A short note to the owner listing what changed on screen.

## State

- Dev instance `litecore` running (host 0.2.5); `litecoreprobe` paused. The owner's `PMPC指南.odt` is in the dev instance's admin files; the four `repro-109-*` copies were deleted.
- Product page served shows artifact `4a2710bba1ef07d9` in its banner.

## Standing rules to carry

- Never run two M3 runners (or an M3 probe) at once — each clears the whole `oc_files_lock` table. The owner may have the editor open; a runner clearing locks affects their session — tell them before a counted run.
- Counted runners refuse an uncommitted host tree; a host JS change needs an `info.xml` version bump and `ddev occ upgrade`.
- `findings/evidence/**` and `handoff/**` English; `specs/`, `research/`, `devlog/` and findings' prose zh-TW; specs and gate documents append-only.
- A verdict's re-check is pinned to the commit that recorded it.
- Byte-for-byte equality is for machine data, not prose (owner, 2026-10-03).
- The owner is the one observer who does not share our instruments (lesson again today: 109 sat behind a "designed" refusal nobody measured from the user's side).
