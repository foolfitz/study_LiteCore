# Adversarial review brief — SPEC-M3-production-ui (findings 109, 110, A3), before any counted run

You are reviewing, not implementing. Do not edit any file. Do not run any M3 runner or anything that
opens the `litecore` dev instance in a browser (every M3 runner clears the whole `oc_files_lock` table,
and a run is in progress or about to be). Reading files, `git show`, `git diff`, `node --test` on unit
tests and `python3 -m py_compile` are fine.

## What to read

- `specs/SPEC-M3-production-ui.md` (zh-TW; the criteria table in §4 is the contract).
- study_LiteCore commit `27402abc`: `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js`
  (`_checkpointBeforeBoundaryRestart`, `restartKeepsContent`, the call in `action()`), its tests
  (`editor-shell-v2/tests/narrow-editor-v2-session.test.mjs`, the "finding 109" section), and
  `wasm_sdk_probe/web/e2-editor-app.js` (`reopenAfterBoundaryRefusal`, the branch in `run()`,
  `applySessionAvailability`, the guard at the top of `editorAction`).
- The base class it relies on and must not change: `wasm_sdk_probe/editor-shell/editor-session.js`
  (`_drain`, `_blockQueue`, `_checkpointBeforeSelection`, `_openFresh`, `restart`, `save`).
- The engine refusal sites: `wasm_sdk_probe/src/probe_engine.cpp` around :3256–:3445 and :3795–:3820.
- Host repo `~/Projects/Nextcloud_Apps/litecore` commit `96a13b9` (0.2.6): `lib/Controller/EditorController.php`
  (`scopedStyle`, `editor()`, `resolve()`'s new `dir`), `templates/editor.php`, `js/litecore-editor.js` (`titleBar`).
- The new runner `wasm_sdk_probe/tools/check_m3_production_ui.py` and the one-line change to
  `wasm_sdk_probe/tools/check_m3_page_honesty.py` `activate()`.
- Reports: `findings/evidence/m3-production-ui/prefix/*.json` (host 0.2.5, expected red) and, if present,
  `findings/evidence/m3-production-ui/shakedown/*.json` (host 0.2.6).

## Questions — answer each, with file:line

1. **Data safety of A1.** Is there any sequence in which a boundary refusal now loses unsaved work, or in
   which `reopenAfterBoundaryRefusal` restarts into OLDER content than the user had? Consider: edits queued
   behind the refused delete (they are rejected by `_blockQueue`), a save in flight to the host
   (`savesUnsettled`), the view-only gate, a checkpoint save that fails, a second refusal right after the
   reopen, the generation ceiling (`WORKER_GENERATION_LIMIT`), and the a11y core's semantic refusal.
2. **Is `restartKeepsContent()` the right question?** It mirrors `_openFresh`'s choice. Could the two
   disagree (e.g. `_authorityStamp`/`_checkpointStamp` semantics after a save, after a rollback)?
3. **`applySessionAvailability`.** Can it leave a button permanently disabled, or re-enable one that view-only
   or the manifest meant to keep disabled? Does it fight `showExpired` or `openFromHost`?
4. **`scopedStyle` + `@scope`.** Can the regex replace the wrong thing or miss a document-level rule the page
   has? Does anything in the page's CSS stop working inside `@scope` (custom properties, `*`, `#sink`
   positioning, `position: fixed` toast)? Is the 500 fail-closed path reachable by a legitimate page?
5. **Close button.** Is `filesUrl` right for files in subfolders, in shared folders, and with pretty URLs off?
   Can closing bypass the leave guard (page-honesty §7: the host alone decides)?
6. **The runner's predicates.** For each criterion in spec §4, can it pass while the claim is false
   (vacuity, a wrong anchor, a field that is always equal)? Name the mutation the scorer would miss.
   Is the red-first evidence (the 0.2.5 runs) red for the right reason in each arm?
7. **Anything in the spec that is a hand enumeration posing as a hard criterion** (CLAUDE.md
   「驗收判準的形式」 §1), or a criterion with no "if never done" default.

## Output

Start with `## SUMMARY` (at most 30 lines): every finding labelled **BLOCKING** (must change before a
counted run) or **NON-BLOCKING**, one line each with file:line. Then details. A finding is BLOCKING only
if you can state the concrete sequence or input that produces the wrong outcome; a suspicion goes under
NON-BLOCKING with what would confirm it.
