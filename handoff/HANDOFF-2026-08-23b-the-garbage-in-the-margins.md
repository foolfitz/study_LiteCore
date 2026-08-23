# Handoff: the accessibility core paints uninitialised memory beside the page, and 31 of those pixels were eating two paragraphs

Written 2026-08-23, continuing `HANDOFF-2026-08-23-the-projection-reads.md`.

## State

`e2-editor-v4` is still the shipped profile and the page still pins it. `v5` is
minted, archived and NOT shipped. Nothing about that changed today.

What changed is that the reason v5 was reverted is now three separate things
instead of one blur, **two of them were the harness**, and the one that is left
is real.

| the three reasons v5 was reverted | today |
|---|---|
| the band scan saw 7 bands for 9 lines | **closed** — finding 075, root cause found and fixed in the harness |
| bold did not reach the document | **closed** — finding 077, a harness defect. Bold was never broken: 13/13 arms pass on v5 once the arm establishes its starting state |
| the format barrier stopped advancing on a bulleted blank line | **open, and it is the only one left.** Not a band problem and not a harness one |

v5's product path is now **31 PASS / 1 FAIL / 6 NOT_ESTABLISHED**, down from
3 FAIL. v4 is unchanged at **35 PASS / 3 NOT_ESTABLISHED, `ok: true`** — measured
again after every instrument change, which is what caught two of my own
regressions.

## Finding 075 is closed, and the cause was visible

Counting could not tell a focus rectangle from garbage, so the canvas was
photographed (`tools/capture_canvas_edges.py`). Open
`findings/evidence/f075-off-page-garbage/*-top-2x.png` side by side: the shipped
core's surround is flat, the accessibility core's is coloured noise.

The decisive number is alpha. Off-page columns, 26,941 pixels per shot:

* shipped core, either state: **0** pixels with `alpha > 128`. The surround is
  TRANSPARENT, so the ink test never sees it.
* accessibility core after a caret: **290** opaque, **184** distinct alpha
  values against the shipped core's 33, and **31** dark enough to count as ink.

Thirty-one pixels, one to three per row, in the gaps BETWEEN lines at both
margins. They dropped the first gap from 12 rows to 2 so two lines merged, and
they pushed the merged band's extent from 157 columns to 634, which put its
density at 84/634 = 0.133 — under the 0.15 floor. The band was discarded with
two paragraphs in it. The text was on the canvas the whole time.

### The exclusion that was supposed to catch this had never once fired

`INK_ROWS` clips to the page using columns inked DARK down more than 20% of the
canvas. Replayed offline against four canvases, it finds **one** column and
`clipped` is **false** every time, on both cores in both states. The shipped
core was safe for an unrelated reason: its surround is transparent.

### The remedy is opacity, and it cannot move the shipped core

The page is drawn opaque and its surround is not — a property this rendering
HAS in both states on both cores, unlike the drawn border it was looking for.
Clipping to the outermost columns more than 20% opaque:

* all four canvases agree on the same page range;
* page columns are >= 96.9% opaque, off-page columns <= 7.6% even with garbage;
* on the shipped core it drops **0** pixels, which is what "transparent" means;
* bands go 7 -> 9 on the accessibility canvas and stay 9 on the shipped one.

`BAND_MERGE_GAP` and the density floor were NOT touched. Moving either would
have been fitting the instrument to one core's noise.

`INK_ROWS` now returns `pageOpaque`, `pageClipped` and `offPageInk`, and the
product path carries `offPageInk` into its report. That last part is a repair:
the comment claimed the count was "reported rather than silently dropped" while
nothing carried it anywhere.

### What the repeats do and do not show

Five rounds per core, three states each: the accessibility core is 15/15 at 9
bands, and the one anomalous count (10 at rest) belongs to the SHIPPED core.

**`offPageInk` is 0 in all thirty cells.** The garbage did not occur during any
of them, so those runs do not exercise the clip at all. The positive control is
offline, on the canvas that does carry the garbage: clip on -> 9 bands, clip
off -> 7. Do not quote the thirty cells as evidence that the fix works; quote
them for the band count being stable, which is a different claim.

**The garbage is intermittent and its rate is not established.** Present in the
two captures taken for the finding, absent in the ten taken afterwards. Nobody
has looked for what makes the difference.

## Where the garbage comes from — finding 076, and it is ours

Tracing 075's cause to the end reached the engine, three statements in
`src/probe_engine.cpp`:

```cpp
auto *pixels = static_cast<unsigned char *>(std::malloc(byteCount));   // not zeroed
gState.document->pClass->paintTile(gState.document, pixels, ...);      // draws the PAGE
```

and then, in the page, `context.putImageData(strip.image, 0, strip.y)` — replace
semantics **including alpha** — with `layoutCanvas()` scaling the whole canvas
and cropping nothing. So the margins of the tile are whatever `malloc` returned,
and they are displayed.

This is not LOK's defect. Core paints the page it was asked for; allocating the
buffer and handing it on is ours.

**It has always happened and was invisible because a freshly grown WASM heap is
zero.** The project had already measured it, in `tileWasPainted()`'s own
comment: an unpainted buffer is "88 of 2,105,340" non-zero — 0.0042%, and 0%
opaque, which is why the ink test never saw it. On the accessibility core the
same columns come back 1.08% opaque with 184 distinct alpha values. Two hundred
and fifty times as much of the same thing, plausibly because +19.9 MB of code
means the buffer lands on reused memory rather than a fresh page — **inference,
not measured**.

Fixed in source with `calloc`, syntax-checked with em++ under both
configurations, queued as `queue-tile-buffer-is-not-zeroed`. **It does not reach
the product until a link**; `dist/` still carries `malloc`.

The cheap consequence of this defect is a broken band scan. The expensive one is
that a canvas the user can screenshot was displaying fragments of this process's
heap, and this process's heap holds their document.

**The harness-side clip stays anyway.** It guards the class — ink outside the
page — not this one cause. An instrument that is only correct in a world where
the engine is fixed will break silently on the next unexpected off-page
rendering, and silently is how this one behaved for months.

## The barrier failure is NOT a band problem, and its shape is already known

`bulleting-a-blank-line-does-not-demand-a-rollback` FAILs on v5 with
`MUTATION_OUTCOME_UNKNOWN` and the toast "the format barrier stopped advancing
before it could read the paragraph". That sentence has exactly one producer in
the engine: `failFormatBarrierAtDeadline()` (`src/probe_engine.cpp`), which also
sets `failureShape = "stage-deadline:<stage>"`.

Finding 046's remedy is narrow ON PURPOSE — it declines to demand a rollback
only when `dispatched && route == "collapsed" && failureShape ==
"multi-block-readback"`. A stage deadline is not that shape, so the disposition
falls through to "roll back to your checkpoint".

`FormatBarrierStageDeadlineMs` is **5000**, and every stage re-arms it. So this
is a stage that STOPPED, not a core that is slow. **Do not widen the 046 remedy
to cover it.** Widening would turn a stall nobody understands into a green
check. What is needed is why a stage stalls for five seconds on that core.

`failureShape` reaches the page (`paragraph-editor-client.js` reads
`error.details.formatBarrier`) but the product-path report keeps only the toast.
Capturing it there is the cheapest next measurement.

## Bold was never broken — finding 077, and three wrong answers on the way

Three of four bold arms failed on v5 while italic, underline and strikethrough
passed. With the arm fixed, **13 of 13 pass on that core**, and the check goes
FAIL to PASS. Bold reaches the document on the accessibility core. It always did.

What was wrong was the arm. `format_arm` opens each arm with
`insert-paragraph-break`, and a new paragraph INHERITS the caret's formatting —
so every arm started from whatever the rest of the run left behind. The toolbar
is a TOGGLE whose request is derived from the format cache:

```js
? { enabled: formatStateFor(action) !== true }
```

so one wrong starting value makes the press ask for the OPPOSITE of what the arm
wanted, and leaves the next arm inverted in turn. On v5 the very first arm
started at `true` where v4 started at `false`. Everything after that was
deterministic — which is why exactly the bold arms failed and nothing else did.

### The three wrong answers, because the sequence is the lesson

1. **"The press needs longer."** v1 slept 1.5 s. Replaced by a wait on
   `aria-pressed`.
2. **"The cache does not follow on the accessibility core."** v2's wait timed out
   on 8 of 13 arms at 20 s, against 13/13 confirming in ~202 ms on v4. That is a
   clean variation control and it produced a confident, wrong engine finding. The
   wait could never be satisfied: when the request is inverted, the cache moves
   AWAY from the value being waited for. **My own broken wait manufactured the
   evidence for a defect that was not there.**
3. **"The fix is refuted."** After (2) turned v5 from 30/2/6 into 22/5/11 I wrote
   the instrument off. Wrong again — the same harness left v4 at 35 PASS,
   `ok: true`. It was a bad WAIT, not a bad INSTRUMENT, and kept as an
   observation it is what identified the real cause.

The version that stands waits on `#s-latency` (written after the operation
resolves AND `renderDocument()` completes), normalises the starting state with
`清除格式`, turns the format on first for an OFF arm, and **asserts the
precondition from the cache** — reporting `ok: None` with a reason rather than
FAIL when the setup did not take, because `清除格式` is itself NOT_ESTABLISHED on
that profile.

### And the fix had a regression of its own, caught by re-running v4

Normalising EVERY arm took v4 from 35 PASS to 34: the last four arms
**accumulate** on purpose, because `clear-format-removes-every-inline-format`
needs a document with all four formats on at once — clearing an already-clear
document is a no-op any broken button passes. They now normalise ONCE before the
sequence and run with `normalise=False`, and the record carries `normalised` so
that a deliberately inherited arm and a checked one never look alike. v4 is back
to 35 PASS / 3 NOT_ESTABLISHED.

**The rule that caught all of this is the same one each time: re-measure a
changed check on the core it was already green on.**

### Two side results worth keeping

* `清除格式` works on the accessibility profile — thirteen normalisations,
  thirteen successes — while its own check still reports NOT_ESTABLISHED there.
  A check saying "unknown" is not evidence of absence.
* With the page clip reporting its worst scan instead of its last, a run reports
  `pageRange [15, 709]` — the same range the offline replay derived from the
  captured canvases for 075. Two instruments, one number. And `offPageInk` is
  now non-zero in live runs on BOTH cores (v4 worst 1, v5 worst 20), so the clip
  is exercised rather than merely present.

## Also done, and both are retractions of my own text

* `DESIGN-2026-08-22-aria-projection.md` §7 still carried "AA = 68 檢測碼" after
  the roadmap had retracted it. The spec contains neither "68" nor "優先"; the
  68 is the URL path segment `/Accessible/Guide/68`.
* The roadmap asserted "C = 檢測碼, E = 稽核評量碼" in a parenthesis. The spec
  does distinguish those two families but never ties them to the suffix letters;
  the definition is in a tab ("編碼規則及格式說明") that the captured text does
  not cover. Same mistake as the 68, same day: my reading presented as the
  document's.

`DESIGN` §7.4 now maps 1.3.1's eighteen codes onto the projection, and three
things fell out that were not on any plan:

1. **Emphasis is not projected.** The product can apply bold, so it is already
   conveying information through a visual change, and the projection does not
   say so. That is an open gap under a Level A criterion, not a future feature.
2. **Tables are a blank in the projection.** Five table codes read "not
   applicable" only because the projection has no tables; documents can. The
   honest phrasing is "the projection is incomplete for documents with tables",
   and it belongs in the conformance statement.
3. **Five codes are about the SHELL** — toolbar and file input, not the canvas
   — and have never been checked. Separate work item.

## The product path itself stalls, and only on the accessibility profile

Counted over 2026-08-23, same machine, nothing else running, load average under 1:

| profile | runs | stalled |
|---|---|---|
| `e2-editor-v4` | 4 | **0** |
| `e2-editor-v5` | 7 | **3–4** |

A normal run is 11–13 minutes. A stalled one produces **nothing at all** — the
report is written only at the end, so a timeout leaves a 0-byte log — and sits
there: 29 min, 50 min, and one still going at 20 min as this is written. The
browser is alive throughout, the page is loaded, the workers exist, CPU is
low. It stops rather than slows.

**This may be the same thing as the remaining FAIL.** That check dies on
`stage-deadline`, which is a barrier stage that stopped advancing past a 5000 ms
budget that re-arms per stage. Two "stops advancing" symptoms, both only on the
accessibility core. **That is a hypothesis with a shape, not a finding** — nobody
has attached to a stalled run and asked where it is. `/json/list` on the
debugging port is passive and shows the page and workers alive; going further
means evaluating in the page, which perturbs the run being diagnosed.

The cheap next step is a run with per-step progress output, so a stall names its
own step instead of being a silence.

## The two questions only the operator can answer

Run `tools/serve_manual_preview.py --profile e2-editor-v5` (it serves a mirror;
`dist/` is not written) and look at the page. It carries a green banner naming
the profile and the wasm and worker hashes, because on 2026-08-22 the operator
tested half a fix and neither of us could tell.

1. **Does bold work when a human presses it?** The harness path and the user's
   path have disagreed before, and the harness's own stopwatch was wrong here.
2. **Is there coloured noise around the page?** The garbage is in the canvas, so
   it should be visible. Nobody has looked. If it is visible this stops being a
   harness story and becomes a rendering defect on that core — but the core is
   `writer calc` WITH accessibility against a writer-only build WITHOUT it, so
   two differences, one measurement. Calc changing the heap layout is not
   excluded, and accessibility may not be named as the cause on this evidence.

## Commands

```sh
cd wasm_sdk_probe

# the preview for a human
python3 tools/serve_manual_preview.py --profile e2-editor-v5

# the band question, cheap and targeted -- NOT the product path
python3 tools/capture_canvas_edges.py --profile e2-editor-v5 \
    --after-action set-paragraph-heading --out-dir /tmp/bands

# the product path -- nothing else may run alongside it, and it can hang.
# One run hit the 1800 s timeout with a 0-byte log and no report (the report is
# written only at the end, so a timeout leaves nothing); a second was killed at
# 29 min showing the same. An earlier run of the same profile took 11 min. Use
# 3600, and expect to lose the run if it stalls.
python3 tools/run_e2_c_product_path.py --profile e2-editor-v5 --out report.json
```
