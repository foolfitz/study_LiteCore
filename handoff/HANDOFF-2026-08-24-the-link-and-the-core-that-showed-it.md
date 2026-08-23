# Handoff: finding 076 shipped and was proved on the core that showed it, and a two-day-old "stall" turned out not to be one

Written 2026-08-24, continuing
[`HANDOFF-2026-08-23d-the-shape-was-never-read.md`](HANDOFF-2026-08-23d-the-shape-was-never-read.md).

## State

**`e2-editor-v8` is the shipped profile** (linked by the user 2026-08-24).
Product path on it: **38 PASS / 2 NOT_ESTABLISHED, `ok: true`** — equal to the
best `e2-editor-v7` ever produced. Shell generation **v41**.

| finding | what | state |
|---|---|---|
| 076 | tile buffer `malloc`'d, uninitialised heap on a canvas the user can screenshot | **closed** — shipped, and measured gone on the core where it was visible |
| 079 | the selection shape was computed from fields that are not on the object | closed (23d) |
| 080 | the abort check blamed the harness for the defect it was checking | re-aimed; `queue-abort-margins-are-unexplained` still open |
| **081** | **the a11y "stall" is a dead session being driven, not a hang** | **new, measured; the first failure's cause is NOT established** |

Profiles now: `e2-editor-v8` ships. `e2-editor-v9` is an **a11y product
candidate, not shipped, nothing points at it**. `a11y-calloc` is diagnostic.

## Finding 076, end to end

### Shipping it proved less than it looked like

The `calloc` fix went out in `e2-editor-v8` and the product core came back
clean — 0 opaque off-page pixels in all three states. **But that core already
read as transparent under `malloc`** (075's own table: 0% opaque). So a clean
canvas there says "no regression", not "cured". The noise the operator saw was
on the **accessibility** core.

Closing a defect on a build where its symptom was never visible is a shape this
tree keeps writing down, so the asymmetry went into the v8 runbook §4 *before*
the measurement, where it could not be quietly dropped afterwards.

### The single-variable experiment

`a11y-calloc` vs `e2-editor-v5` — the artifact the operator actually looked at.
`probe.js`, `sdk-worker.js`, `soffice.data` and its metadata **all byte-identical**;
manifests differ in `profile`, `sdkVersion`, `wasmSha256` and nothing else; and
the wasm difference is **one hunk**, confirmed by preprocessor rather than by
reading commits.

Off-page columns, 26,941 pixels per shot:

| shot | alpha==0 | alpha>128 | ink | distinct | PNG bytes |
|---|---|---|---|---|---|
| v5 at rest | 21,559 | 3 | 0 | 46 | 45,294 |
| v5 after caret | 19,236 | **290** | **30** | **184** | **90,538** |
| v5 after an edit | 19,236 | **1,235** | **853** | 186 | 89,542 |
| a11y-calloc, all three | 21,595 | **0** | **0** | 33 | ~42,6xx |

Two things make this more than a before/after: the post-fix rows **equal the
product core's own** to the pixel (two differently-configured cores now agree
off-page, which they did not before), and the baseline **reproduces** 075's
archived numbers on a different profile of the same core (290/31/184 vs
290/30/184).

**The defect was worse than the finding recorded.** 075 measured at rest and
after a caret only. Driving one format press takes v5 from 290 opaque to
**1,235, of which 853 pass the ink test** — against the 31 the finding was
written from. Nobody had looked.

## Two tools that came out of this, and both exist because a cheap answer was wrong

**`tools/what_the_link_ships.py`** — preprocesses the product's own translation
units with the product's own defines at the shipped commit and at the tree, and
diffs. Answers "what does this link actually ship" by measurement.

* Reading commit messages answers about the repository: 153 engine lines across
  five commits, four of them for a different core.
* Reading the `#ifdef`s misses a hunk — `refreshCaretParagraph()`'s fix is gated
  on a **runtime** flag on purpose.
* **And the tool's own first version missed a third thing**: the builder hashes
  whichever `sdk-worker.js` is in the tree, so a link ships accumulated worker
  changes too. Caught by a dry packaging run showing `workerSha256` move. It now
  covers the worker and separates comment lines from code.

`--variant a11y` handles the other lineage. Both configurations self-assert
against `make -pn` and report `configurationDrift`.

**`--core-data` on the profile builder.** The first `a11y-calloc` packaging
pointed `soffice.data` at the shared **product-core** image, because
`artifactFiles` is inherited from the source manifest — a wasm linked against
one core would have loaded another core's registry and resources. Caught by
diffing the manifest against v5's before measuring anything (`resourcePacks` was
`[]` on one side, a CJK pack on the other). Now a build step rather than a thing
to remember.

## Finding 081: the a11y stall is not a stall

`HANDOFF-2026-08-23c` open item 2 said the format barrier's `stage-deadline`
"possibly [is] the same thing as the product path stalling on that profile", and
asked someone to attach to a stalled run. There was one running, so:

```json
{ "state": "recoverable-error", "checkpoint": "無", "pending": "0",
  "latency": "儲存 失敗", "doc": "format-a-paragraph.odt",
  "toast": "儲存：EDITOR_NOT_READY：… unavailable in recoverable-error" }
```

**`pending: 0`.** Nothing is waiting on the engine. A save failed during
`format-a-paragraph-changes-that-paragraph`, took the session into
`recoverable-error` **with no checkpoint**, and every arm after that burns its
own timeout against a session that refuses everything. That is the 20–50
minutes, and because the report is written only at the end, the run yields
nothing at all.

So both things exist and **they are not the same thing**. Which one caused the
*first* failure is **not established** — `latency` keeps only the last entry, and
in `recoverable-error` even a save is refused, so that entry may be consequence
rather than cause.

The cheap fix is harness-side and is in
`queue-a11y-path-drives-a-dead-session`: check the session state between arms,
stop driving once it is `recoverable-error`, and report naming the arm that
killed it. Same shape as finding 080 — a precondition that can never hold again,
retried arm after arm.

## `e2-editor-v9`: a candidate, and no link was taken for it

The user authorised "the a11y link". **No link was needed.** 076's measurement
already ran on `a11y-calloc`'s wasm `b60cc46f`, which *is* a11y core + `calloc`.
v9 is a **second manifest over that same artifact** — exactly as `e2-editor-v7`
was a second manifest over v4's. One fewer link means one fewer hash and means
076's evidence still describes the candidate itself.

| against | difference |
|---|---|
| `a11y-calloc` | manifest only: v9 carries v8's gestures (078). `a11y-calloc` keeps v5's narrow pre-078 set to stay a one-variable experiment. |
| `e2-editor-v8` | `caretParagraphText`, `documentOutline`, loader and wasm hashes. |

Its Makefile rule reads from the **archive**, not the build tree: adding the rule
made `build/e2/a11y-calloc/probe.js` out of date against the Makefile, so `make`
would have relinked it (finding 042) and left 076's measurement describing an
artifact that no longer existed. A hash-named archive directory says *which*
artifact in a way a build path cannot.

**Nothing points at v9 and its shippability is unmeasured.** v5 was reverted for
three reds; only the band-scan one is addressed here (it was 075). The run that
would answer the rest is the one that died — see 081.

## Open work, in the order I would take it

1. **`queue-a11y-path-drives-a-dead-session`** — harness-side, cheap, and it is
   the thing standing between you and *any* measurement of the a11y lineage.
   Until it lands every a11y run is a coin flip that costs 20–50 minutes.
2. **Then the v9 product path**, which is the real question about a11y as a
   product. Expect `an-inline-format-reaches-a-selection` to be meaningful there
   (v9 has the wide gestures; `a11y-calloc` does not).
3. **`queue-abort-margins-are-unexplained`** — one run each way so far, and this
   check has produced three confident wrong answers on single runs. Start by
   synchronising reads on `revision`/`callbackSequence` rather than wall-clock
   sleeps.
4. The two standing NOT_ESTABLISHED on the product path
   (`notice-action-recovers-the-session`,
   `a-refused-action-is-reported-and-changes-nothing`). Finding 080's lesson is
   that a long-abstaining check is a hypothesis that the thing it measures is
   broken.

## Things a new session should not re-derive

* **A link ships more than the engine.** The builder hashes the tree's worker.
  `what_the_link_ships.py` answers the whole question; use it before deciding.
* **A profile built against a non-product core needs `--core-data`**, or it
  declares the product core's filesystem image.
* **v8's `probe.js` is byte-identical to v4's and v7's.** A page identifying its
  engine by the loader would have seen nothing change across a link. That is the
  argument for pinning the wasm, now demonstrated rather than asserted.
* **Attaching to a live stalled run is cheap** — `curl` the CDP port from
  `--remote-debugging-port`, take the `page` target, `Runtime.evaluate`. It
  answered in one shot a question that had been open for two days.

## The push

`github/main` is at `11c3f58` — the user pushed mid-session, after 079 landed.
Everything from `c41e858` (076's link preparation) onward is committed and not
yet pushed. The remote is `github`, not `origin`.

I nearly wrote "370 commits ahead" here from a number I had read hours earlier.
It was 366 then and is not now, because the remote moved under it. **A count is
a measurement with a timestamp**, and a handoff is exactly where a stale one
gets believed.
