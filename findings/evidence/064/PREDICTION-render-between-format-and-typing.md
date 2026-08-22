# Prediction, written before the measurement (2026-08-21)

Finding 064: **an inline format set through the product never reaches the text
you type next.** All four formats, both directions, eight arms, on artifact
`29ec627b` / shell v25.

The attribution is already done and is **not** what this arm is for: D1's
harness, on the *same* artifact, read by the *same* `inline_styles_of()`, gets
all eight arms right. The engine is fine; the product path is broken. What is
**not** established is the mechanism, and until it is, nobody can say whether
the remedy is a shell change (independent, parallel, no link) or an engine
change (payload item 7, and the link waits).

**This arm names one candidate and measures it. It is not a hunt.**

## The candidate, and why it is the one

`run()` awaits `renderDocument()` after **every** operation
(`web/e2-editor-app.js:377-382`), so the product inserts a `paintTile` +
`getDocumentSize` round trip between the format action and the typing. D1 does
not: it saves there instead (`web/e2-c-d1-app.js:381-382`) and then types.

## Source facts verified before writing this

Each of these was read in the tree at HEAD, not recalled:

1. **There is a second render source, and it is not at the `run()` call site.**
   `onEvent` schedules a repaint whenever the engine reports
   `document-invalidated`: `queueMicrotask(() => void renderDocument())`
   (`web/e2-editor-app.js:768-769`). A diagnostic that removed the `await
   renderDocument()` on line 382 would leave this one running and could report
   "the render is not the mechanism" while a render still happened. **The
   instrument therefore sits inside `renderDocument()` itself**, where every
   caller passes.

2. **`renderDocument()` is the product page's only `paintTile` source.** The
   page never calls `session.render()` or `scheduleViewport()`, and
   `TileScheduler` (`reader-shell/tile-scheduler.js`) has no timer of any kind
   — `invalidateRevision()` only clears its cache. So one counter inside
   `renderDocument()` accounts for every tile request the page can make.

3. **The drain does *not* add a `getState` after a format action.**
   `_drain()` takes `result?.state ||` before falling back to the engine
   (`editor-shell/editor-session.js:301-302`), and
   `NarrowEditorV2Client._validateInherited` rejects any result without `state`
   (`editor-shell-v2/narrow-editor-v2-client.js:117`). So "an extra state read
   between the press and the typing" is **eliminated by source reading, not by
   measurement**, and is recorded that way.

4. **The inline formats do not use the engine's format barrier.** The barrier's
   targets are the list and paragraph-style commands
   (`src/probe_engine.cpp:1224-1241`); the four inline actions take the plain
   `uno-command-result` route. Nothing in the barrier can be interleaved here.

5. **`session.commitText()` and D1's `handle.insertText()` end at the same
   call** (`editor-shell/editor-session.js:511`). The insert itself is not a
   difference between the two paths.

## The remaining differences between the two paths

Listed so the ladder below is finite and so nothing is quietly dropped:

| | product | D1 |
|---|---|---|
| A | `renderDocument()` between the press and the typing | a `save()` there instead |
| B | `insert-paragraph-break` immediately before the press; the caret is in a **fresh empty paragraph** | the caret is inside existing text |
| C | 1.5 s of wall clock between the press and the typing | none |
| D | caret placed by `EditorSession.placeCaret` (click + polled `getState`) | `collapsedAt()` (click + polled `getState`) — same shape |

A is the candidate. B and C are arms only if A does not decide it. D is the same
gesture on both sides and is not an arm.

## What is mirrored (dist/ is never written)

**One file**, in a symlink mirror, `probe.wasm` byte-identical to `29ec627b`:

* `e2-editor-app.js` — a block at the top of `renderDocument()`:

  ```js
  const diag = globalThis.__f064;
  if (diag) {
    if (diag.suppress) { diag.suppressed += 1; return; }
    diag.renders += 1;
  }
  ```

**The mutation is a boolean the probe sets, not a difference between two
files.** Baseline and variant run the *same bytes*; they differ only in whether
`__f064.suppress` was true across the press→commit window. That is what makes
this a single variable — "the mirror changed something else" is not available as
an explanation.

With `globalThis.__f064` absent the block is inert, so the mirrored page is the
shipped page for anything that does not install the hook.

## The instrument's own positive control

**This is the part that must not be skipped.** A suppressed render and a render
that never had a reason to happen look identical from the document side, and
"nothing happened" would come back green either way (`probe-measurement-discipline`,
three separate checks lost to this on 2026-08-21).

So the probe carries **C1**, run before the arms and on the same page:

* with `suppress = false`, commit a marker and confirm the canvas ink **changes**;
* with `suppress = true`, commit a second marker and confirm the canvas ink
  **does not change**, while `__f064.suppressed` advances;
* release `suppress`, force a render, and confirm the ink changes again.

If C1 does not hold, **every arm below reports `NOT_ESTABLISHED`**, not a
result. A run whose instrument cannot be shown to bite measures nothing.

Each arm additionally reports `renders` and `suppressed` sampled *at the press*
and *at the commit*, so the window is quantified rather than assumed, and the
marker's presence in the saved ODT is the arm's own proof that it ran: a marker
that is not `found` makes that arm `NOT_ESTABLISHED`, never `false`.

## The predictions

One format — **italic** — for every arm. `fo:font-style="italic"` is
unambiguous in ODF and does not need the `"none"` reading that underline and
strikethrough do. One arm per fresh engine session, one marker per arm, each in
its own paragraph: six markers at one caret coalesce into a single
`<text:span>` and every later press rewrites the earlier ones (measured
2026-08-21, and it is in the finding).

### P-064-0 — the baseline reproduces (negative control)

With `suppress = false`, the marker typed after a `set-italic` ON press is
`found: true` and carries **no** italic, and `renders` advanced by at least 1
across the press→commit window.

*If the baseline comes back italic*, the defect did not reproduce on the
mirrored page and nothing else in this run may be read. Stop and find out why.

### P-064-1 — suppressing the render makes the format reach the text

With `suppress = true` across press→commit, the marker is `found: true` and
carries **italic**, with `renders` unchanged and `suppressed >= 1`.

*This is the prediction under test.* It is the one that can be wrong.

### P-064-2 — a save in the same slot is harmless (D1's shape, on the product path)

With `suppress = true` but a `session.save()` between the press and the commit,
the marker carries **italic**. This is D1's exact interleave driven through the
product's own session, and it separates "an intervening engine operation" from
"this particular one".

Run whatever P-064-1 says: if P-064-1 holds, P-064-2 confirms the boundary; if
P-064-1 fails, P-064-2 asks whether *anything* on this path can work.

## The ladder if P-064-1 fails

Only then, in this order, one variable each:

* **B** — no `insert-paragraph-break`: place the caret at the end of a line of
  existing text and type there.
* **C** — the 1.5 s wait removed (press → commit as fast as the queue allows),
  with the render left in.

If A, B and C all fail to change the outcome, the product's interleave is not
the mechanism and the difference is somewhere this arm did not look. That is a
result too, and it is the one that puts 064 back on the engine's side of the
line.

## What each outcome does to the link payload

| | |
|---|---|
| **P-064-1 holds** | **Product-side.** The remedy is in the shell: do not repaint between a format action and the next commit (or re-establish the pending format after one). No engine change, **no payload item**, the link proceeds with six and the fix ships in parallel as shell v26 |
| **P-064-1 fails, B or C decides it** | Still product-side; same disposition, different remedy |
| **nothing on the product path changes it** | The attribution stands (D1 works) but the mechanism is not in the interleave. 064 stays `KNOWN_RED`, and whether it becomes **payload item 7** is decided by the next round — **the link does not execute on an unexplained red** |

## Traps

* **Do not read the canvas as the document.** Every verdict here is the saved
  ODT read by `inline_styles_of()`; the canvas is used only by C1, to show the
  instrument bites.
* **Do not read `aria-pressed` as an answer.** It being green while the document
  is untouched *is* finding 064.
* **Do not widen anything.** No manifest, no gesture, no guard is touched by
  this arm.
* **A marker that is not in the saved document is `NOT_ESTABLISHED`.** The
  question "does it carry italic" asked of a marker that is not there must
  return **null**, not `false` — the `fractionNearStart: -0.229` mistake, one
  day old.
* **No rebuild.** `probe.wasm` is byte-identical to `29ec627b` throughout; the
  profile is not touched and `make e2-c-assets` is not run by this probe.
* The report is stamped `evidenceClass: "diagnostic"` and writes nothing into
  `dist/`.
