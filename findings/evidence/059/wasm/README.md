# Finding 059, the WASM half — core applies the command here too

Measured 2026-08-18, Chrome, shipped v3 artifact `d538ce0b91478426…`, shell v16.
The run is **shimmed** (below), so `servedShell.servedSha256` deliberately does
not equal the declared bundle digest and this report may not be cited as
acceptance evidence.

Reproduce: `tools/run_f059_wasm_predicate.py` (self-test 11/11).
Raw: `collapsed-caret-arms.json`, `range-route-closed.json`.

## The answer

Finding 059 recorded one thing as unestablished and important: whether the WASM
build also *applies* the inline format command it reports as failed. **It does.**

Six arms, each in a page of its own, each opening the fixture through the
product's own file-open path, each placing a collapsed caret and confirming it,
then pressing the toolbar button and inserting a marker through the product's
own insert button, then saving through the product's own save button. The
verdict is the style attached to that marker's run in the saved ODT.

| arm | command result | marker's style in the saved document |
|---|---|---|
| control, no command | — | **unstyled** |
| `set-bold` | `LOK_COMMAND_FAILED` | **bold** |
| `set-italic` | `LOK_COMMAND_FAILED` | **italic** |
| `set-underline` | `LOK_COMMAND_FAILED` | **underlined** |
| `set-strikethrough` | `LOK_COMMAND_FAILED` | **struck through** |

Each arm's marker carries **exactly the slot that was pressed** and no other.
The fixture declares no character styling anywhere (asserted by
`tools/create_f059_predicate_fixture.py --self-test`), and the control arm —
same fixture, same caret, same insert, no command — comes back unstyled. So the
styling is caused by the dispatch, and coincidence is excluded by slot
specificity.

**Consequence.** On the shipped build, pressing B applies bold, and the product
tells the user the action failed and prescribes returning to a checkpoint. It is
asking users to discard work in order to undo a change that succeeded.

## The declared shims, and what they cost

`dist/` is never written; the run serves a symlink mirror.

1. **`editor-shell-v2/paragraph-editor-client.js`** — every *dispatched* failure
   reports `dispatched-unverified` instead of `unknown-rollback`, so the queue
   stays open long enough to insert and save. A refusal that reports it
   dispatched nothing is left alone.
   **Cost**: this run does not measure the product's real disposition, which is
   still `rollback`. Nothing here describes what the product does to a user.
2. **`e2-editor-app.js`** — the page's gesture mask is lifted (range round only).
   **Cost**: the product does not offer these actions on a range; no statement
   about what a user can do may cite that round.

## The range route is closed, and measured closed

The first design used a range selection, so the format would land on existing
text and need no insertion. With the page's mask lifted, all four dispatches
returned **`EDITOR_FORMAT_GESTURE_UNSUPPORTED`**: the mask is enforced in the
engine as well (`editorGesturePermitted`, `src/probe_engine.cpp:4247-4252`), and
the engine's own message says *"nothing was dispatched and the document is
unchanged"*. So those unstyled documents are correct negatives, not nulls.

That also gives relink queue item `p1-2-gesture-mask-inherited` its first
**runtime** witness; it was previously checked only by a static occurrence count.

⇒ On this build the four inline formats can reach core **only** on a collapsed
caret, which is why the marker route is the only one available.

## What is NOT established

* **Why core reports `success: false` for a command it applied.** Not measured,
  not named (040/048 precedent).
* **`insert-path-carries-formatting` did not do its job, and its own result is
  unexplained.** That control opens a fixture whose text is already bold, places
  a caret, and inserts a marker with no command at all; the marker came back
  **unstyled** while the product's own `aria-pressed` reported the caret as bold.
  It was there to make a null in the other arms interpretable, and the other
  arms are positive, so nothing above depends on it — but its null is a loose
  thread. The caret's offset within the bold run was not established, so
  "inserted at the end of the run" is not excluded.
* Anything about Firefox. Only Chrome was run.

## Rounds that measured nothing, and why

Recorded because each produced a readable-looking null for a reason that was not
core, and the guards that now exist are the cost of finding that out.

| round | why nothing was measured | guard added |
|---|---|---|
| range selection | the four formats declare `gestures: ["collapsed"]`, so the page disables those buttons and `click()` on a disabled button fires nothing | each button's `disabled` is recorded; an arm that could not dispatch is not scored |
| fixed sleeps | every arm read `busy` with an empty toast | every sleep replaced by a condition wait |
| collapsed caret | caret placement failed on every arm — the click fell past the end of an eight-character line (finding 052's shape) | padded fixture; caret placement is a proven precondition, tried at several points, and the point that held is recorded |
| two rounds | the product opened an **HTTP 404 page** as the document: `build_mirror` walks the source tree and silently drops an override for a path `dist/` does not contain | fixtures written into the mirror directly; the opened document verified by **bytes** (text unique to the fixture) rather than by the filename label, which is set from the name the page was handed; and a three-second preflight that fetches each fixture and requires `PK\x03\x04` |
| range, shim too narrow | the queue blocked on a code the shim did not cover, the save produced nothing, and the early return discarded the toast that would have named it | the shim covers every dispatched failure; no arm returns early, so a failed arm still reports what it saw |
