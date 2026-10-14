# v20, part 2 — the page number on the page, and the page's side of C

## SUMMARY

- Task: `handoff/tasks/TASK-2026-10-13l-v20-page-number-on-the-page.md`. Scope: spec §13.3 — the page number (§4.3 as corrected by §10.8, §10.10 Q-A, §12.3) and C on the page (§10.5). Source only: `web/e2-editor-app.js`, `web/e2-editor.html`, `editor-shell-v2/narrow-editor-v2-session.js`, tests under `editor-shell-v2/tests/`. No make, no browser, no `tools/run_*.py`, no `dist/`, profile, pin, binding or new `.js` file. Nothing has been linked; the first browser execution is the v20 shakedown.
- The element: `<div id="page-status" hidden>` (`web/e2-editor.html:332`), its own element after `#desk` and before `.statusbar` so the host's `#litecore-editor-root .statusbar { display: none }` (`editor.php:51`) does not hide it; no `aria-live`, no `role`; its rule (`:205`) sets no `display`, so `hidden` keeps working. Text 「第 N 頁，共 M 頁」 / 「第 N–L 頁，共 M 頁」 (U+2013).
- Pure functions, exported from the session module: `pageSpanOf(rectangles, region)` → `{first, last, count}` or null (Writer's rule on whole rectangles = named limit **L-page-margin**; strict `<` on both axes; string order, never sorted, nothing inferred from heights; total); `visibleRegionTwips(top, bottom, docRows, widthTwips, heightTwips)` → `{x:0, y, width, height}` or null; `pageStatusText(span)` → the string or null.
- The scheduler, `PageRectanglesScheduler` (`narrow-editor-v2-session.js:253`), injected `read(key)`, clock-free: reads once per `documentOpened` (keyed on the document object — first open, reopen after a refusal, restart), on a `documentSizeChangedCount` change, on `sizeChangeReported` (a paint reply's `documentSizeChanged`); never on `documentChangeSequence`, scroll, resize, zoom or caret (those only recompute). One read in flight; triggers meanwhile collapse into exactly one follow-up at the latest counter; a failure reports null (line hidden, no toast) and consumes its trigger; an answer for a non-current document is dropped; a `read` that throws synchronously is a failure.
- The page asks the engine from one place (`e2-editor-app.js:267`, the scheduler's `read`), gated on `session.offersPageRectangles()` (new passthrough beside `offersRedo()`, `:933`): on v8/v19 the element stays hidden and `pageRectangles()` is never called. Hooks: `notePageRectangles(snapshot)` in `updateState` (`:811`), `updatePageStatus()` first in `onDeskScroll` (`:1147`) and last in `layoutCanvas` (`:1131`), the `documentResized` block of `renderDocument` reports the paint trigger (`:1396`), `openDocument`'s close drops answers in flight (`:3058`). No new listener, no new file.
- `editorState` has three writers; all three now carry `documentSizeChangedCount`: (1) `_openFresh`'s `getState()` → `transition("ready")` (`editor-shell/editor-session.js:189-197`; the worker's `editorGetStateV2` reply names it, `sdk-worker.js:1010`); (2) the drain's `result.state || getState()` (`:301-311`; action replies go through the worker's `productEditorState`, `:374`); (3) the subclass's `_handleEngineEvent` allowlist (`narrow-editor-v2-session.js:498`, **added here**; integer or null).
- C on the page (§4): `verified-boundary-noop` resolves through `run()` (`:1923`) — no toast, no reopen (both live in its `catch`; `reopensAfterRefusal`, `:1746`, asks errors only). No page change was needed. **Reported, not changed:** the session counts that delete as a mutation — `action()` enqueues every non-move with `mutation: true` (`narrow-editor-v2-session.js:770`), the frozen drain bumps the content stamp and sets `dirty` (`editor-session.js:304, 309`). Measured on the v2 fixture: `dirty false→true`, `_contentSequence 0→1`, `hasUnsavedEdits() true`; the next boundary move then banks a checkpoint (one ODT save per noop+move), and with a host `noteAutosaveState` arms an autosave of unchanged bytes (`e2-editor-app.js:2847-2855`). The smallest change that honours `changed: false` is in §4 below; whether to make it is a ruling.
- Tests: `page-number.test.mjs` (36) and `page-boundary-noop.test.mjs` (6). Red first: page-number fails at import on the unmodified module; with the module and without the page its six page/HTML cases fail by name (27/36); boundary-noop is green on the unmodified page by construction and carries a mutation control that makes the assertion fail. Then `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs`: **386 pass, 0 fail** (344 before). `node --check web/e2-editor-app.js`: OK.
- Checks modified because of execution (§34): 2 — `page-paint-overlay.test.mjs` and `page-render-bands.test.mjs` gained stub names (`updatePageStatus`, `pageRectangles`) in their `new Function` sandboxes, the `positionProjection` precedent; assertions untouched; witness = the first full run (9 failures, 5 × `ReferenceError: updatePageStatus is not defined`). Modified because of review: 0.
- Python readers: `test_product_path_mutations` + `test_e2_profile` 66 OK (1 skipped), `test_ink_rows_caret` + `test_merge_wasm_clauses` 61 OK (14 skipped), unchanged from before; `test_e2_c_shell_bundle::test_the_real_manifest_matches_the_real_tree` red by design, now naming four dist copies (client, session, document-sdk, page). Anchor census: all 103 literals the runner, cutover builder, mutation test and audit aim at the two files occur exactly as often as before. `audit_product_path_coverage.py` red before and after for its pre-existing reasons, output byte-identical.
- Pins a later freeze must move: none new; part 3's freeze covers the four dist copies above, and `offersPageRectangles` is on the session only (no `.d.ts` pin for the session). Spec: nothing contradictory or unimplementable; six judgement calls in §7.
- Environment note: this worktree has no `dist/` (gitignored); a read-only symlink to the main tree's `dist` was placed in the worktree so the manifest-reading tests could run; no byte under `dist` was written.
- Commits: `69ac9381` (session module), `abb442c5` (page, HTML, tests), this README.

## 1. What the user sees, and where it sits

`web/e2-editor.html:332`:

```html
  <div id="page-status" hidden></div>
```

placed after the closing `</div>` of `#desk` and before `<div class="statusbar">`. The rule (`:205`) sets padding, 12px, muted colour, the bar background and a top border, left-aligned, and deliberately no `display` — an author `display` would override the UA's `[hidden] { display: none }` and the element would hold a blank line whenever there is nothing to say. No `aria-live`, no `role`: a page that spoke on scroll is findings 087/088. The host's styling of it is the owner's hand test (§10.10); the host was not loaded.

On every existing profile `session.offersPageRectangles()` is false, the scheduler's `offered()` returns false, no read is ever issued, `onResult` is never called, and the element never leaves `hidden`. The page's other behaviour on v19 is unchanged: the only new work per state write is `notePageRectangles()`, which compares two object references and returns.

## 2. The pure functions and their contracts (`editor-shell-v2/narrow-editor-v2-session.js`)

| function | line | contract |
|---|---|---|
| `pageSpanOf(rectangles, region)` | 191 | `rectangles` from `handle.pageRectangles()` (`[{x,y,width,height}]`, twips), `region` a rectangle in twips. Returns `{first, last, count}` with `first` = 1-based index of the first rectangle that intersects, `last` = the last, `count = rectangles.length`; or **null** when nothing intersects, the list is empty or not an array, or the region is not a rectangle. Intersection is strict (`<`) on both axes, so touching an edge does not count. Whole rectangles (L-page-margin). String order is page order: never sorted, so a later rectangle with a smaller `y` still answers by position; nothing is inferred from equal heights. A malformed entry is skipped for N and L and still counted in M, so M stays what the engine said. |
| `visibleRegionTwips(top, bottom, docRows, widthTwips, heightTwips)` | 211 | Device rows `[top, bottom)` of `#paper` (what `visibleDocRows()` measures) scaled by `heightTwips / docRows`; `x: 0`, `width: widthTwips` (the full document width — the page never scrolls sideways and Writer's rule is about vertical overlap). Null when any input is not finite, `docRows`, `widthTwips` or `heightTwips` is ≤ 0, or `bottom <= top`. |
| `pageStatusText(span)` | 219 | `第 ${first} 頁，共 ${count} 頁` when `first === last`, else `第 ${first}–${last} 頁，共 ${count} 頁`. Null for anything that is not a span of three integers. |

Named limits registered here: **L-page-margin** (above) and, carried over from §4.3, **L-page-virtual** (physical page numbers only; a custom start number or roman numbering is not known to this line).

## 3. The scheduler (`PageRectanglesScheduler`, lines 253–341)

Constructor `{ read, offered = () => true, onResult = () => {} }`. State: `_key` (the document the line describes), `_observed` (the latest `documentSizeChangedCount` seen for it), `_issuedAt` (the counter the last read was issued at), `_inFlight`, `_again`; counters `reads`, `failures`, `dropped`.

| call | effect |
|---|---|
| `documentOpened(key, editorState)` | sets `_key`, `_observed` from the state's counter (integer or null), clears `_issuedAt`, schedules a read. |
| `stateObserved(key, editorState)` | ignored unless `key === _key` and the state carries an integer counter; records it; schedules a read only when it differs from `_issuedAt` (or no read has been issued for this document yet). `documentChangeSequence` and every other field are never looked at. |
| `sizeChangeReported(key)` | schedules a read when `key === _key`. |
| `closed()` | clears `_key` (an answer in flight is dropped) and the follow-up flag. |

`_schedule()`: nothing unless `offered()` is `true`; if a read is in flight, mark `_again`; else `_issue()`. `_issue()`: `_issuedAt = _observed`, `reads += 1`, call `read(key)` (a synchronous throw becomes a rejected promise). `_settle()`: if the key is no longer current, `dropped += 1` and nothing is delivered; on error `failures += 1` and `onResult(key, null, error)`; else `onResult(key, result, null)`; then, if `_again` and a document is current, exactly one follow-up read. A failed read therefore consumes its trigger (the counter it was issued at is recorded), so a profile whose read always fails costs one call per trigger, not one per state write; the next open, counter change or size report tries again.

The page's wiring (`web/e2-editor-app.js`): `const pageRectangles = new PageRectanglesScheduler({ offered: () => session?.offersPageRectangles?.() === true, read: (document) => document.pageRectangles({ timeoutMs: 30000 }), onResult(...) })` (`:267`). `notePageRectangles(snapshot)` (`:278`) runs from `updateState` on every state write: when the snapshot is `ready`/`busy` and `session.document` is a different object from the one the line describes, it hides the line and calls `documentOpened(document, snapshot.editorState)`; otherwise `stateObserved`. This covers the first open, the reopen after a refusal (`session.restart()` from `reopenAfterBoundaryRefusal`) and the notice's rollback uniformly, because each produces a `ready` transition with a new document object. `updatePageStatus()` (`:299`) recomputes from the last rectangles and `visibleDocRows()`; it runs from `onDeskScroll` (first statement, before the early returns; `followCaret` scrolls the desk, which fires `scroll`), from the end of `layoutCanvas` (resize, and the relayout after a size change), and after every delivered read. The `documentResized` block in `renderDocument` calls `sizeChangeReported(session.document)` before `layoutCanvas()` (`:1396`). `openDocument` calls `closed()` and hides the line before `session.close()` (`:3058`).

A transient to know about: between a paint reply that reports a size change and the `layoutCanvas()` that follows in the same pass, `docRows` describes the old layout while `session.document.heightTwips` is already the new height, so one recompute may map rows with the new scale over the old rows; the relayout and the read that follow correct it within the pass.

## 4. C on the page, and what the session does with `changed: false`

Path read: `beforeinput` (`deleteContentBackward`/`deleteContentForward`, `:2501`) → `editorAction(sent)` → `run(label, () => session.action(action, options))` (`:2063`) → `NarrowEditorV2Session.action()` (`narrow-editor-v2-session.js:708`) → `_enqueue(..., { mutation: !BOUNDARY_CAPABLE_MOVES.has(action) })` (`:770`) → `EditorSession._drain()` (`editor-session.js:279`) → `editor.action()` (the v2 client, which since part 1 accepts `verified-boundary-noop` with `changed === false` and the revision unchanged) → the drain resolves the item → `run()`'s success path (`changes += 1`, latency text, `renderDocument()`) → `editorAction` returns. Toast and reopen exist only in `run()`'s `catch` (`:1934-1945`): `reopensAfterRefusal(error)` is true for `EDITOR_BOUNDARY_UNSUPPORTED` or `EDITOR_STATE_UNAVAILABLE` with `recovery: "restart"`; everything else toasts. A resolution reaches neither. `beforeinput`'s `.catch(() => { deleteRefusedThisHold = true; })` (134 B) is not reached either. **No page change was needed**; `page-boundary-noop.test.mjs` pins it with the page's own `run()`.

What the session does with the completion, **unchanged** (reported as asked):

- `action()` decides the mutation flag at enqueue time from the action name alone: `{ mutation: !BOUNDARY_CAPABLE_MOVES.has(action) }` (`narrow-editor-v2-session.js:770`) — `delete-backward`/`delete-forward` are not moves, so `mutation: true`.
- The frozen drain then, after the operation returns: `if (item.mutation) this._currentContentStamp = ++this._contentSequence;` (`editor-shell/editor-session.js:304-305`) and `dirty: this.state.snapshot.dirty || item.mutation` (`:309`). The revision does not move (the engine did not advance it).
- Measured on the v2 fixture (`scratchpad/measure-noop-mutation.mjs`, output kept in this session's scratchpad), clean document → one `verified-boundary-noop` delete: `dirty false→true`, `_contentSequence 0→1`, `_currentContentStamp 0→1`, `hasUnsavedEdits() false→true`; a following `move-character-left` then banks a checkpoint (`boundaryCheckpointsTaken 1`, one ODT `save()`), because `_checkpointBeforeBoundaryMove` compares the stamp (`:574-587`); a second noop and move cost a second save.
- Consequences on the page: with a host, `noteAutosaveState` arms an autosave once the session is `ready` with `hasUnsavedEdits()` true (`e2-editor-app.js:2847-2855`) — a host write of unchanged bytes; `hasUnsavedWork` keeps the leave guard on; the `dirty` pill reads as edited.

Smallest change that would honour `changed: false` (NOT applied; a ruling): the drain reads `item.mutation` only after the operation returns (`:304`), and the item is pushed onto `this._queue` synchronously inside `super._enqueue` (`:263`). So the subclass can let the operation flip the flag on the item it runs as:

```js
// in NarrowEditorV2Session: the one place super._enqueue is reached (its own
// _enqueue and _releaseHeld), wrapped so the operation can reach its item.
_enqueueOwned(label, operation, options) {
  let item = null;
  const before = this._queue.length;
  const owned = (runtime) => operation(runtime, { completedUnchanged: () => { if (item) item.mutation = false; } });
  const promise = super._enqueue(label, owned, options);
  if (this._queue.length === before + 1) item = this._queue[before];   // EDITOR_NOT_READY pushes nothing
  return promise;
}
// in action()'s operation, after `const result = await editor.action(action, options)`:
if (result?.completion === "verified-boundary-noop" && result?.changed === false) tools.completedUnchanged();
```

About ten lines; it depends on a second private seam of the frozen base (`_queue` is pushed synchronously and `item.mutation` is read after the operation), which would need its own pin test as the `editor` seam has. The alternative of compensating in `action()`'s `.then` (restoring the stamp and `dirty`) is wrong: the drain starts the next queued operation synchronously after resolving, and `_checkpointBeforeBoundaryMove` reads `dirty` at its top before the `.then` runs.

## 5. Tests

New: `editor-shell-v2/tests/page-number.test.mjs` (36 cases: 9 span incl. the 60-page native string from `findings/evidence/link-batch/page-rectangles/round-20261012T030439Z/long60-r1.jsonl` through `parsePageRectangles`; 2 text; 2 region; 12 scheduler; 4 writers; 1 passthrough; 6 page/HTML incl. `updatePageStatus()` taken from the page source and run 50 times against a model element with the document's `pageRectangles` counted) and `editor-shell-v2/tests/page-boundary-noop.test.mjs` (6: `run()` from the page source on the noop → no toast, no reopen, one repaint; `reopensAfterRefusal` on results and errors; the catch path's controls; the mutation control; the session's `action()` on both deletes).

Red first, unmodified sources (`node --test` of the two files):

```
✖ editor-shell-v2/tests/page-number.test.mjs
SyntaxError: The requested module '../narrow-editor-v2-session.js' does not provide an export named 'PageRectanglesScheduler'
✔ 6 of page-boundary-noop.test.mjs (incl. "the assertion has teeth: a run() that toasts on changed === false fails it")
ℹ tests 7  ℹ pass 6  ℹ fail 1
```

The boundary-noop cases cannot be red first: the unmodified page already neither toasts nor reopens on a resolution. The mutation control (a copy of `run()` that toasts on `changed === false`) is shown to fail the same assertion.

Red by name, session module done and page untouched (`page-number.test.mjs` alone): `ℹ tests 36 ℹ pass 27 ℹ fail 9` — the six page/HTML cases (`html: #page-status …`, `page: pageRectangles() is called in exactly one place …`, `page: open and state writes go through notePageRectangles …`, `page: fifty recomputes …`, `page: no rectangles yet …`, `page: the line follows the view …`) plus three test-side errors fixed before the page was written (a wrong expectation for a malformed entry — the real page at index 1 does intersect, so `{2,2,2}` is the contract; an exact float comparison; a fixture option the client does not forward).

First full run after the page: `ℹ tests 386 ℹ pass 377 ℹ fail 9` — the two wiring cases (my own patterns: the comment block also says `.pageRectangles(`; the `role` guard was broader than the element) and seven pre-existing page tests (`P-U4` ×2, `122 B5`, `W-U3`–`W-U6`), `5 × ReferenceError: updatePageStatus is not defined` and B5 by assertion (the `pageRectangles` ReferenceError lands in `renderDocument`'s catch). Disposition: the two sandboxes gained stubs on the `positionProjection` precedent (§34: modified because of execution, witnessed by this run).

Green:

```
node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs
ℹ tests 386  ℹ pass 386  ℹ fail 0
node --check web/e2-editor-app.js   -> OK
```

## 6. Checks that read the two files without building

| check | before | after |
|---|---|---|
| `python3 -m unittest tests.test_product_path_mutations tests.test_e2_profile` | 66 OK, 1 skipped | same |
| `tests.test_ink_rows_caret tests.test_merge_wasm_clauses` | 61 OK, 14 skipped | same |
| `tests.test_e2_c_shell_bundle::test_the_real_manifest_matches_the_real_tree` | red by design (client, document-sdk) | red by design, four files: `narrow-editor-v2-client.js`, `narrow-editor-v2-session.js`, `sdk/document-sdk.js`, `web/e2-editor-app.js` |
| anchor census (every string literal ≥ 12 chars in `run_e2_c_product_path.py`, `build_cutover_page.py`, `test_product_path_mutations.py`, `audit_product_path_coverage.py` that occurs in either file; 103 literals) | counts | identical, `diff` empty — `PAGE_STATE_ANCHOR` (`function updateState(snapshot) {`), `BARRIER_DETAILS_ANCHOR` (`run()`'s catch), `CARET_SOURCE_ANCHOR` (`moveSinkToCaret`), `CARET_ANNOUNCE_ANCHOR` (`openDocument`'s `onEvent`) and the two session mutations (`review-disposition`, `boundary-move-takes-no-checkpoint`) all still occur exactly once |
| `tools/audit_product_path_coverage.py` | exit 1, `ok: false` (pre-existing: the `#paper` pointer listeners and `scroll#desk` unaccounted, four `#canvas` registry entries the page no longer has) | byte-identical output — no new listener was added |
| `product-page-calls.test.mjs`, `declaration-drift.test.mjs` | 16 pass | 16 pass (`session.offersPageRectangles` exists on the class) |

Nothing to move for the freeze beyond what part 3 already owns (the dist copies above and the bundle manifest). The page's pinned profile/wasm lines were not touched (the cutover builder's `repointed_page` still finds them; `test_e2_profile` green).

## 7. Spec reading: nothing contradictory or unimplementable; six judgement calls

1. **The read's key is the document object** (`session.document`), compared by identity. The task says "the session's document/handle, not the counter alone"; handle numbers restart with every Worker and generations restart with every session, so neither number is unique across a page's life while the object is.
2. **A failed read consumes its trigger** (the counter it was issued at is recorded whether it succeeds or fails). The task's "differs from the value at the last completed read" would, read as success-only, re-issue a failing read on every state write; "the next trigger tries again" is implemented as the next open, counter change or size report.
3. **A state whose counter is missing or null is not a trigger.** Profiles without the counter do not offer the read either; on a profile that does, a writer that dropped the field must not look like a change.
4. **`notePageRectangles` only acts on `ready`/`busy` snapshots**, so a half-open document (an open that fails after the handle is assigned) and the `loading` snapshot of a restart (which still holds the old document object) issue nothing.
5. **The region uses `session.document.heightTwips` at recompute time**, as the task wrote the conversion, rather than the height `docRows` was laid out from; the one-pass transient is described in §3.
6. **Two existing test sandboxes were given stub names** rather than moving the hooks off `onDeskScroll`/`layoutCanvas`/`renderDocument` to new listeners, because the task places the paint trigger at `e2-editor-app.js:1276` and new listeners would widen the coverage audit's unaccounted set.

Not executed anywhere: the page's wiring has run in node sandboxes only (`updatePageStatus`, `run`), never in a browser; the scheduler has never been driven by a real `pageRectangles()`.

## 8. Commits

| commit | contents |
|---|---|
| `69ac9381` | `editor-shell-v2/narrow-editor-v2-session.js`: `pageSpanOf`, `visibleRegionTwips`, `pageStatusText`, `PageRectanglesScheduler`, `documentSizeChangedCount` in the allowlist, `offersPageRectangles()` |
| `abb442c5` | `web/e2-editor-app.js`, `web/e2-editor.html`, `tests/page-number.test.mjs`, `tests/page-boundary-noop.test.mjs`, sandbox stubs in `tests/page-paint-overlay.test.mjs` and `tests/page-render-bands.test.mjs` |
| (this commit) | this README |

## 9. Ruling 6 fixes (2026-10-14, task `TASK-2026-10-14a`, conditions 45, 47, 48)

Append-only. Ruling: `findings/evidence/link-batch/review/ruling-6.md` §Q2, §Q3, §Q4. All three fixes are in `editor-shell-v2/narrow-editor-v2-session.js`; `editor-shell/` untouched (`check_e1_c_bundle_intact.py` → `intact: true`, bundle `187706b2…`, before the first change and after the last commit). No build, no link, no freeze; `web/`, `sdk/`, `src/`, `dist/`, tools, profiles, pins untouched. Line numbers are of the tree at the last commit below. Full suite `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs`: 386 → 389 (48) → 395 (47) → **412 pass, 0 fail** (45); `node --check` OK after each.

### 9.1 Condition 48 — the scheduler after a failed read (`aeaf92c0`)

- `narrow-editor-v2-session.js:375`: `this._issuedAt = null` in `PageRectanglesScheduler._settle`'s error branch, before `_onResult` (so a synchronous re-entry from `onResult` already sees the reset). The `dropped` branch is untouched: `documentOpened` clears `_issuedAt` for the new document anyway. Class comment corrected in place (`:243-252`).
- **§3's cost sentence is corrected here, superseding its last sentence and §7 call 2:** a read that always fails costs **one read per state write while it fails**, not one per trigger. A failure puts the scheduler back in its "no read issued for this document" state; retries are bounded by state writes, and the action that caused the BUSY always ends with one (the drain writes `editorState` after every item). A second write with the same counter while the retry is in flight still adds nothing (`stateObserved`'s early return on `_issuedAt`).
- Tests, `page-number.test.mjs:376` (a), `:393` (b, control), `:404` (c). Red first on the unmodified module:

  ```
  ✖ scheduler (48a): a failed read, then a state write with the same counter -> re-reads
    AssertionError: a state write after a failed read must re-read   actual: 0, expected: 1
  ℹ tests 39  ℹ pass 37  ℹ fail 2
  ```

  The second red is the existing test at `:335`, which pinned the behaviour the ruling reverses ("Same counter again: the failure consumed its trigger, no storm", `pending.length === 0`) and is rewritten to the ruled contract (one re-read on the first same-counter write, none on the second while that retry is in flight). (b) and (c) pass before and after, as controls should. After: 39/39.

### 9.2 Condition 47 — a `verified-boundary-noop` delete is not a mutation (`a6ecb7fd`)

- `narrow-editor-v2-session.js:1036` `_enqueueOwned(label, operation, options)`: wraps the operation as `operation(runtime, tools)` with `tools.completedUnchanged()` clearing the item's `mutation`; `:995` the subclass's `_enqueue` and `:1089` `_releaseHeld` go through it (the only two places `super._enqueue` was reached). `:858` in `action()`: the call happens only when `result?.completion === "verified-boundary-noop" && result?.changed === false`. The view-only gate reads `options.mutation` before the operation and is unchanged.
- **Not README §4's sketch verbatim (judgement call).** The sketch takes the item as `this._queue[before]` after `super._enqueue` returns. `EditorSession._drain()` is `async` and runs synchronously up to its first `await`: when no drain is active it `shift()`s the new item and starts the operation *inside* `super._enqueue`, so the queue is empty again when that returns. Measured on the fixture with the sketch applied literally (scratch script, not committed):

  ```
  {"queue":"idle at enqueue","sketchFoundItem":false,"queueLengthAfterSuperEnqueue":0,"dirtyAfter":true}
  {"queue":"busy at enqueue (second item)","sketchFoundItem":true,"queueLengthAfterSuperEnqueue":1}
  ```

  The user's lone Backspace is the idle case, and the README measurement test stayed red under the sketch (same assertion as below). The item is therefore taken at the push, the only moment it is reachable: `_watchQueue()` (`:1054`, installed in the constructor at `:422`, the shape of 084's `state.update` wrapper) observes `this._queue.push`, counts pushes (`queuePushesSeen`) and remembers the newest item; `_enqueueOwned` claims it by the identity of the wrapped operation. `EDITOR_NOT_READY` pushes nothing and claims nothing. This adds one dependency beyond the ruling's two: the base keeps one array for the session's life (`_queue` is assigned in its constructor only, `_blockQueue` splices in place) — pinned below.
- Seam pins, `narrow-editor-v2-session.test.mjs:229` (the shape of `:211`): through the **base's** `_enqueue` directly, exactly one item is pushed synchronously carrying `mutation: true`; an operation that sets `item.mutation = false` after an `await` leaves `dirty` false and the stamp unchanged, the same item left alone marks dirty (control). `:265`: the observer survives a rollback (same array, one enqueue → one push seen afterwards). A first draft asserted "open() pushes" — it does not (test-side error, fixed before commit).
- README §4's measurement as the red-first test, `page-boundary-noop.test.mjs:208`:

  ```
  ✖ 47: a clean document and one verified-boundary-noop delete: not dirty, stamp unchanged, ...
    AssertionError: changed: false is not a mutation   actual: true, expected: false
  ```

  After: `dirty` false, `_contentSequence` and `_currentContentStamp` unchanged, `hasUnsavedEdits()` false, the following `move-character-left` banks no checkpoint (`boundaryCheckpointsTaken` 0, zero `save()` calls). Control `:229`: a verified delete sets `dirty`, bumps the stamp, and the following move banks one checkpoint (one save). Scope `:246`: a paragraph action's `verified-format-readback` with `changed: null` stays a mutation. View-only `:268`: both deletes refused with `EDITOR_VIEW_ONLY`, nothing reaches the engine, moves still allowed.
- **Judgement call on the scope test.** My first two scope cases (`verified-selection-delete` with `changed: false`; `verified-boundary-noop` with `changed: null`) came out `dirty: false` — not the flip firing but the client refusing the reply (`narrow-editor-v2-client.js:311-322` admits exactly the noop pair or a verified change; a rejected action is never a mutation). The accepted completion nearest the noop is a paragraph action's `changed: null`, so that is the committed case.
- The fixture gained `{ noop }` and answers moves like moves (`changed: false`, revision unchanged, `documented-callback-visible-cursor`), because the client's inherited postcondition refuses a move reply that advances the revision — the previous fixture never drove a move.

### 9.3 Condition 45 — the `placeCaret` acknowledgement, finding 138 (`bcf3f747`)

- Selection shape read from source before writing the predicate: `NarrowEditorV2Client.getState()` → `ParagraphEditorClient.getState()` → `editorGetStateV2` → `sdk-worker.js` `editor-state-result` branch forwards `selection: event.selection` raw → `probe_engine.cpp` `appendEditorState` emits `{observed, collapsed, start, end, rectangles:[{x,y,width,height}|null]}`. `collapsed` and `rectangles` are in the reply; nothing was invented.
- `narrow-editor-v2-session.js:608` `placeCaret(xTwips, yTwips, options)`, an own override with the base's contract: same options (`caretTimeoutMs`, `caretAckGraceMs`), result shape, the three `caretConfirmedBy` strings, `EDITOR_CARET_NOT_PLACED` with identical `details`. `:626`: `acknowledged = sequenceAdvanced && (caretMoved || selectionChanged)`; return on `(onTarget && (acknowledged || elapsed >= graceMs)) || (acknowledged && caretMoved)` — the 052 path is literally the base's (`caretMoved` implies the evidence). `:165` `selectionDiffers(selection, previous)`: `collapsed`, the rectangle count, and each rectangle's position via `caretDiffers`.
- **Judgement call: rectangles compared by position only** (x, y; not width/height), for 052's reason — a relayout inside the click's window can change a rectangle's height, and a relayout must not stand in for a click (that is the 138 class). A plain click on a live selection flips `collapsed` and empties `rectangles`, so nothing a plain click does is missed. `observed`, `start`, `end` are not compared (`observed` is about the readback; the end points follow the rectangles).
- Test, `place-caret-acknowledgement.test.mjs`: review 6's harness with ruling 6's four added arms; `Object.create(Class.prototype)` with `_enqueue` stubbed, the product's `placeCaret` against a scripted engine in which only the timing of state changes is scripted (lone push at 3 ms, click processed at 25 ms, the measured 22–28 ms). Seven arms on the subclass (`:174`), the same seven on the frozen base as controls (`:184`: its three false acknowledgements are pinned, which is what shows the lone bump lands inside the window and a sequence-only predicate would be caught), the own-override structural check (`:190`), the error-shape contract (`:196`, both classes time out on a never-processed click with the caret on another line; `details` deep-equal) and the `caretConfirmedBy` contract (`:212`). Red first on the un-overridden subclass — exactly the three arms, plus the structural check:

  ```
  ✖ override: same-line click, lone DOCUMENT_SIZE_CHANGED at 3 ms (v20)
    AssertionError: the state returned carries the clicked point   actual: 1000, expected: 5000
  ✖ override: same-line click, lone INVALIDATE_TILES at 3 ms (F5, v19)   actual: 1000, expected: 5000
  ✖ override: lone size bump, the click is never processed (image-click shape)
    actual: 'engine-acknowledged', expected: 'already-at-target'
  ✖ the override is the subclass's own, and the base is untouched   actual: false, expected: true
  ℹ tests 17  ℹ pass 13  ℹ fail 4
  ```

  The four equal arms (plain, identical point at ~440 ms, selection collapse, off-line) were green before and after; all seven base controls green before and after. With the override: 17/17; ten consecutive runs of the file, 0 failures. `product-page-calls.test.mjs` passes (`has()` walks the prototype chain). The 400 ms grace arms are kept at the default (two per class, ~1.8 s of the file's run) for fidelity with §Q2's table.
- Not measured on WASM whether a lone tile or size callback occurs inside a click's window — as finding 138 and the ruling state; the harness is the evidence.

### 9.4 Checks changed, and what was not done

- Changed because of a ruling (not §34: product code and its unit tests): `page-number.test.mjs:335` (the reversed pin, §9.1); `page-boundary-noop.test.mjs` header gained a paragraph pointing at the new tests and its fixture gained the `noop` switch, move replies and a save counter; `narrow-editor-v2-session.test.mjs` imports `EditorSession` for the seam pin. Assertions of existing tests otherwise untouched.
- Nothing stopped on. No contradiction found between the task and the ruling; the one departure from the README §4 sketch is §9.2's, with its witness.
- Not run here: Python readers, the browser, any `tools/run_*.py`. Nothing in this section has executed in a browser; shell generation v67 is not frozen.
