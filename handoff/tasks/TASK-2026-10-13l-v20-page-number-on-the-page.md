# TASK 2026-10-13l — v20, part 2: the page number on the page, and the page's side of C

**Spec:** `specs/SPEC-M3-link-batch.md`, scope **§13.3**. For the page number: §4.3 (as corrected by §10.8),
§10.8, §10.10 Q-A, §12.3. For C: §10.5 ("the page shows no toast and does not reopen"). Part 1 is done
(`82af92ca..51ad4261`; account `findings/evidence/link-batch/v20-part1/README.md`, read its SUMMARY and §4, §5,
§9). Nothing has been linked: no engine that answers `page-rectangles` exists yet, so this part is verified by
node unit tests and by reading, and its first browser execution is the v20 shakedown (later task).

**This task changes source only.** Files you may change: `wasm_sdk_probe/web/e2-editor-app.js`,
`wasm_sdk_probe/web/e2-editor.html`, `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js`, and tests
under `wasm_sdk_probe/editor-shell-v2/tests/`. Do **not** touch: `dist/`, any profile, `Makefile`, `tools/`,
`e2/*.json`, any pin or binding, the page's pinned profile/wasm lines, `src/`, `sdk/`, the client, the host
repository. **Do not add a new `.js` file**: the shell bundle is the import graph from `web/e2-editor-app.js`
and every bundled file needs its own Makefile copy rule (`Makefile:2904–2925`), which is part 3's. Put
node-testable code in `editor-shell-v2/narrow-editor-v2-session.js`, which the page already imports and which
already exports page-facing pure functions (`selectionShapeOf`).

## 1. What the user sees

- A line at the **bottom, left**, drawn by the page: 「第 N 頁，共 M 頁」, or 「第 N–L 頁，共 M 頁」 when the
  visible region spans more than one page (N≠L; the dash is U+2013 as written here).
- **It must be visible inside the host.** The host hides the page's whole dev `.statusbar` with
  `#litecore-editor-root .statusbar { display: none; }` (`~/Projects/Nextcloud_Apps/litecore/templates/
  editor.php:51`, read only). So the line is **its own element outside `.statusbar`** (for example
  `<div id="page-status">` placed after `#desk`, before `.statusbar`), not a span inside it. No host change.
  Whether it looks right under the host's styles is the owner's hand test (§10.10), not yours; do not try to
  load the host.
- **Not a live region** (no `aria-live`, no `role="status"`): scrolling must not speak (findings 087/088 are
  about a page that spoke too much). Plain text a screen reader can reach by browsing.
- **Absent unless offered.** When `session.offersPageRectangles()` is false (every existing profile: v8, v19),
  the element stays `hidden` and the page never calls `pageRectangles()`. The page on v19 must behave exactly
  as today. Add the session passthrough `offersPageRectangles()` beside `offersRedo()`
  (`narrow-editor-v2-session.js:726`).

## 2. How N, L and M are computed (pure functions, exported from the session module)

- Input: the parsed rectangles (`handle.pageRectangles()` → `{rectangles:[{x,y,width,height}], parts, …}`,
  twips) and the visible region in twips. M = `rectangles.length`.
- N = 1-based index of the **first** rectangle that intersects the visible region; L = the **last**. Use the
  whole rectangle (Writer subtracts the page margins; we cannot, named limit **L-page-margin**). Intersect in
  both axes, strict (`<`), so a region that only touches an edge does not count.
- Never infer anything from equal page heights, never assume rectangles are sorted: order by the string's
  order (core emits them in page order; `sw/source/core/crsr/crsrsh.cxx:1655`), and if a later rectangle's
  `y` is smaller than an earlier one's, still use string order — do not sort.
- If no rectangle intersects (cannot happen with a viewport taller than the inter-page gap, but the function
  must be total): return null and the line shows nothing (`hidden`), not a guess.
- The visible region comes from what the page already measures: `visibleDocRows()` (`e2-editor-app.js:1188`,
  device rows of `#paper` inside `#desk`) scaled by `session.document.heightTwips / docRows`, and the full
  document width. Write the conversion as a pure function too, so a test can pin it.
- Text: one pure function from `{first, last, count}` to the string above.

## 3. When the page reads, and when it only recomputes

- **Read `pageRectangles()` (one engine call):**
  - once after every open of a document, including the reopen after a refusal and a worker restart (a new
    engine starts its counter at 0; key the "last read" on the session's document/handle, not on the counter
    alone);
  - when the page's `editorState.documentSizeChangedCount` differs from the value at the last completed read;
  - when a paint reply carries `documentSizeChanged: true` (the page already sees it, `e2-editor-app.js:1276`).
- **Never** read on `documentChangeSequence` (typing sends no `INVALIDATE_TILES` — spec §10.8, F2), on
  scroll, resize, zoom or caret movement. Those only **recompute** N and L from the last rectangles.
- **Coalesce:** at most one read in flight; if a trigger arrives while one is in flight, exactly one more read
  follows it. A read that fails (typed `PageRectanglesError`, `UNSUPPORTED_OPERATION`, a disposed engine)
  hides the line and toasts nothing (a page number is not worth a toast); the next trigger tries again. A read
  that resolves for a session that is no longer current is dropped.
- Put this scheduler in the session module as a small class or function with an injected `read()` and
  clock-free logic, so node can test it without a DOM.
- **The allowlist.** `NarrowEditorV2Session._handleEngineEvent` (`narrow-editor-v2-session.js:285–311`)
  copies named fields into `editorState`; `documentSizeChangedCount` must be named there, or the page never
  sees it. Find **every** writer of the page's `editorState` (finding 084: there were two, the push and the
  drain's `getState()`, `editor-shell/editor-session.js` ~301–311) and make sure the counter survives each;
  say in the README which writers exist and what each now carries.

## 4. C on the page (§10.5)

The engine now answers a Backspace/Delete at a document end with `editor-action-completed`,
`completion: "verified-boundary-noop"`, `changed: false`, revision unchanged, after about 2.25 s. The client
already accepts it (part 1). The page must **not toast and not reopen** on it. Read the path from the page's
delete through the session's `action()` and drain to the page, and show by a node test that this completion
produces no toast/reopen call. Also report, **without changing it**, what the session does with a delete
whose completion says `changed: false`: does it count as a mutation (`_contentSequence`, dirty/unsaved mark,
autosave or checkpoint trigger)? If it does, write that down with file:line and the smallest change that would
honour `changed: false`, and stop there; whether to change it is a ruling, not yours (findings 098/099 are
about exactly this kind of mark).

## 5. Tests and checks (run them; record the outputs)

- New node tests under `editor-shell-v2/tests/` for: the span function (one page; two pages; the boundary
  touching but not crossing; mixed portrait/landscape widths with different `x`; no intersection → null;
  60 pages of the native shape in `findings/evidence/link-batch/page-rectangles/`); the text function; the
  region conversion; the scheduler (open → 1 read; counter change → 1; `documentChangeSequence` change only →
  0; 50 recomputes → 0; three triggers during one in-flight read → exactly 1 more; new document with counter
  back at 0 → 1; not offered → 0 ever; failure → line hidden, next trigger reads); the allowlist (an
  `editor-state` event carrying `documentSizeChangedCount` reaches `snapshot.editorState`); the no-toast /
  no-reopen path for `verified-boundary-noop`. Show every new test red once against the unmodified sources
  (or say why a test cannot be red first).
- `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs`: all pass (344 before this part).
- `node --check web/e2-editor-app.js`.
- Python tests that read the page or the session source without building: run
  `python3 -m unittest tests.test_product_path_mutations tests.test_e2_profile` and grep `tests/` and `tools/`
  for other readers of the two files (`audit_product_path_coverage.py`, `build_cutover_page.py`'s anchors,
  any anchor string the product-path runner patches). List anything that goes red and why. **Do not edit
  pins, anchors or checks**; `tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree`
  is already red by design (part 1) and stays red until part 3's freeze.
- Do not run `make` (finding 041: the asset targets build), any browser, or any `tools/run_*.py`.

## 6. Deliverables

- Commits touching only the files listed at the top. English commit messages ending with
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and no `Claude-Session:` line. Retry if
  `.git/index.lock` exists.
- `findings/evidence/link-batch/v20-part2/README.md` (English), beginning with `## SUMMARY` (≤ 30 lines):
  the element and where it sits; the pure functions and their contracts; the scheduler's rules; every writer
  of `editorState` and what it carries; the §4 reading (with file:line) and, if a `changed: false` delete
  counts as a mutation, the proposed change; test outputs (red first, then green); anchors or pins that a
  later freeze must move; anything in the spec you found contradictory or unimplementable. If you find such a
  thing, **stop and report it; do not improvise.**
