# Finding 093, phase 3 — a menu of fix shapes, measured against O-FIX

Measured 2026-09-08 by agent, against the oracle registered and committed in
`ORACLE-fix-shape.md` (`8edd7cf8`) **before this probe was written**. Nothing
in the oracle was moved afterwards.

- Instrument: `wasm_sdk_probe/tools/probe_093_fix_shape_oracle.py` — a **new**
  probe, not an extension of phase 2's. Phase 2's answers a different question
  (where the node sits, what scrolling it costs) and is named for it.
- Raw: `phase3-fix-shapes-v12-audible.json`, `phase3-fix-shapes-v8-audible.json`,
  `phase3-fix-shapes-v12-long.json`, `phase3-fix-shapes-v12-audible-s2b.json`,
  `phase3-fix-shapes-v12-long-s2b.json`, `phase3-s2-hit-test.json`
  (the last from `wasm_sdk_probe/tools/probe_093_s2_hit_test.py`)
- Browser: headless Chrome, its own temporary profile, 1920x1080. The owner's
  Chrome was not touched.
- **Nothing was landed.** Every shape was applied to a scratch mirror of
  `dist/` built with `build_mirror`; `web/`, `dist/` and every identity-bound
  path are byte-unchanged. `e2-editor.html` is hashed by nothing (finding 094),
  which is the reason for the mirror rather than a licence to skip it.

**This report does not choose a shape.** The shapes are ranked with reasons at
the end; the choice is the gate owner's.

## The oracle, restated

> When the screen reader is reading paragraph N, paragraph N is visible in the
> viewport.

Machine form (**O-FIX**): after arriving at paragraph N, the band in which the
engine renders paragraph N overlaps `.desk`'s visible band by at least **half a
line**. The band is the caret rectangle at paragraph N, read as
`#sink.offsetTop` / `#sink.offsetHeight` — the values `moveSinkToCaret()`
writes from `editorState.caret` (`web/e2-editor-app.js:722-735`). The page's
own computation, read as a DOM observable.

**Why not the scroll fraction.** Phase 2's positive control collapses the
fraction from 0.9759 to 0.0000, and 0.0000 is a perfect score for a page
showing paragraph 1 while paragraph 8 is read. The fraction is a proxy; O-FIX
is the claim.

## The limitation this phase does not remove

**No screen reader is run.** The link from "Orca moves its browse cursor onto
the projected node" to "the browser scrolls that node into view" is finding
069's precedent and the owner's two walks of 2026-09-08. It was not measured in
phase 2 and it is not measured here. Every verdict below is conditional on it,
and it is the single largest thing still missing.

---

## 1. Feasibility: is per-paragraph geometry obtainable?

**No — not from anything the product is given.** This decides whether candidate
shape S3 exists at all, and it does not.

| Layer | What it carries | Geometry? |
| --- | --- | --- |
| Engine, `src/a11y_tree_probe.cpp:252-345` (`oxsdk_a11y_document_outline`) | queries `XAccessibleContext` (role, state) and `XAccessibleText` (text, numbering attributes); emits `role`, `level`, `focused`, `textLength`, `text` | **none** |
| Worker allowlist, `sdk/sdk-worker.js:393-399` | copies exactly those five fields into `documentOutline.paragraphs[]` | **none** |
| Caret projection, `sdk/sdk-worker.js:336-373` | `fingerprint`, `length`, `offset`, `listPrefixLength`, `text`; `offset` is `value.a11y.position`, a **character** position | **none** |
| Manifest contract, `dist/profiles/e2-editor-v12/sdk-manifest.json` → `editorContract` | declares `caretParagraphText` and `documentOutline` | **no geometry field** |

`grep -rn 'XAccessibleComponent\|getBounds' wasm_sdk_probe/src/` returns
**nothing**: the engine never asks a paragraph for its bounds. The data exists
in UNO — `XAccessibleComponent::getBounds()` is available on the very children
the outline walk already holds — so this is a projection that was never
written, not a capability that is absent. **Adding it is an engine change and a
relink**, i.e. a new artifact identity, which is not available inside a running
gate.

**The only geometry the page ever receives** is:

- `editorState.caret` — one rectangle, the caret (`sdk/sdk-worker.js:302`,
  drawn at `web/e2-editor-app.js:698-719`);
- `editorState.selection.rectangles` — the rectangles of the **current
  selection** (`web/e2-editor-app.js:683-690`).

Both describe where the user is, not where paragraph N is.

**Therefore S3 as specified does not exist.** What *can* be built is **S3'**:
derive the map by putting the caret in each paragraph and reading the rectangle
the engine then reports back. That is what this probe does to obtain its own
ground truth, and it is measured below **under its own name**, with the costs
of the derivation stated rather than hidden.

---

## 2. The two documents, and why there are two

Every fixture this page offers is ten paragraphs or fewer. On `a11y-audible` —
the owner's fixture — the entire document text occupies paper y 100..415 while
`.desk` is 864px tall at 1920x1080, so **the whole document fits on one
screen**. A shape that pins the viewport to the top of the paper therefore
satisfies O-FIX on that fixture no matter what it does to a real document.
Measuring only there would report a property of the fixture as a property of
the shape.

So a second document was used: `dist/a11y-long.odt`, 133 paragraphs, added to
the **mirror's** fixture list by the probe (`install_long_fixture`) and to
nothing else. `dist/` and `web/` are byte-unchanged.

| | `a11y-audible` | `a11y-long` |
| --- | --- | --- |
| paragraphs projected | 10 (`truncated: 0`) | **133** (`truncated: 0`) |
| canvas / paper height | 1153px | **27198px** |
| `.desk` visible height | 864px | 864px |
| document text spans | y 100..415 — **fits** | y 0..27198 — **31 screens** |
| line height | 24px | 22px |
| targets (first / middle / last reached) | paragraph 0 / 5 / 9 | paragraph 11 / 16 / 20 |
| targets at paper y | 100 / 262 / 391 | 2172 / 3085 / 3998 |

The long fixture's targets start at paragraph 11 because the walk's opening
click lands at 9% of a 27198px canvas. That is fine and is stated rather than
tuned away: O-FIX is about an arbitrary paragraph, not specifically the first.

## 3. The results

Each cell is **O-FIX passes / targets measured**, per arm. `browse` = the caret
stays where it was while the reader browses; `focus` = the caret is walked to
the target first.

### `a11y-audible` — the owner's fixture, which fits on one screen

| shape | profile | browse | focus | scroll fraction |
| --- | --- | :---: | :---: | --- |
| **S0** (unfixed) | v12 | **1/3** | **1/3** | 0.9392 |
| **S0** (unfixed) | **v8** | **1/3** | **1/3** | 0.9392 |
| S1 | v12 | 3/3 | 3/3 | 0.0000 |
| S1 | v8 | 3/3 | 3/3 | 0.0000 |
| S2 | v12 | 3/3 | 3/3 | 0.0000 |
| S2b | v12 | 3/3 | 3/3 | 0.0000 |
| S3' | v12 | 3/3 | 3/3 | 0.0000 |

**The control fails on both profiles**, which is the pre-registered stopping
condition and it did not fire: S0 fails paragraph 0 (overlap 0px against an
11-12px threshold) and paragraph 5 (0px), and **passes paragraph 9 by
coincidence** — the desk is scrolled to the bottom of the paper, and the last
paragraph happens to be near where that lands. Reported as measured; a control
that fails 2 of 3 is a failing control, and rounding it to 0/3 would be
tidying.

On v8 a "stop" is a **line**, not a paragraph: the shipping profile projects no
per-paragraph nodes (phase 2: 1 browsable stop against v12's 13), so the only
thing an AT can land on in that region is `#a11y-para`. The band judged is
therefore the caret's own line. The geometry is identical to v12's to the
pixel, which is phase 2's finding arriving again from a different instrument.

### `a11y-long` — 133 paragraphs, v12

| shape | browse | focus | scroll fraction | what the numbers say |
| --- | :---: | :---: | --- | --- |
| **S0** | **0/3** | **0/3** | 0.9992 | viewport at the bottom of a 31-screen paper |
| **S1** | **0/3** | **0/3** | **0.0000** | **a perfect proxy score and nothing visible** |
| **S2** | **0/3** | **0/3** | 0.0504-0.1209 | right region, wrong by one line — see below |
| **S2b** | **1/3** | **3/3** | 0.0511-0.1217 | follows the caret, not the reader |
| **S3'** | **3/3** | **3/3** | 0.0523-0.1228 | the only shape that holds in both arms |

**S1's row is the whole reason this phase exists.** Scroll fraction 0.0000 —
the number phase 2's positive control produced and the number a
fraction-threshold criterion would have called a pass — with **zero of three**
paragraphs visible. The viewport is pinned to the top of a 27198px paper while
the reader is at y 2172, 3085 and 3998.

**S2's 0/3 is two defects, and the second was only visible once the first was
removed.** S2 copies the sink's `left` and `top` and leaves `.a11y-only`'s
`height: 1px`. `scrollIntoView({block: "nearest"})` stops as soon as the
target's **bottom** edge reaches the viewport's bottom edge, so a 1px target
lands the read line entirely below the fold: band top **864** in an **864px**
viewport, overlap 0px, three times, in both arms. `#sink` does not have this
problem because `moveSinkToCaret` already gives it the caret's height
(`web/e2-editor-app.js:730-734`). **S2b** is S2 plus that one line
(`el.a11yDoc.style.height = el.sink.style.height`), and it separates the two
causes: with the height fixed, the focus arm is **3/3** and the browse arm is
**1/3** — passing only for the paragraph the caret happens to be in.

**That 1/3 is the pre-registered S2 divergence, measured rather than assumed.**
The region follows the caret; a screen reader's browse cursor moves without
moving the caret; so browsing to paragraph 16 while the caret sits in 11 scrolls
to 11 and reads 16.

## 4. The S2 hit-test question, measured rather than argued

`#sink` carries `pointer-events: none` and the comment above it says why
(`web/e2-editor.html:92-96`): an element moved over the canvas puts a 1px
transparent target on the drawing surface, and the canvas's own `pointerdown`
is what places the caret. `.a11y-only` has no such declaration
(`web/e2-editor.html:65-70`), so S2 moves a second element there without one.

Measured (`phase3-s2-hit-test.json`, `tools/probe_093_s2_hit_test.py`), with
the caret placed and `#a11y-doc` confirmed riding it (`docOffsetTop` 99 against
`sinkOffsetTop` 100):

| | S0 | S2 |
| --- | --- | --- |
| `#a11y-doc` rides the caret | false | **true** |
| computed `pointer-events` on `#a11y-doc` | `auto` | `auto` |
| computed `clip-path` | `inset(50%)` | `inset(50%)` |
| `elementFromPoint` at the caret | `canvas` | **`canvas`** |
| `elementsFromPoint` stack | canvas, paper, desk, body, html | **identical** |

**The hazard does not fire**: `clip-path: inset(50%)` participates in hit
testing, so the element is not hit-testable even at `pointer-events: auto`.
Recorded because the objection is the obvious one to raise against S2 and it
would otherwise be answered by reasoning.

## 5. The menu

Cost is measured against the shipped files. "Lines" counts changed lines, not
declarations.

### S0 — leave it

- **O-FIX**: 1/3 and 1/3 on a short document, **0/3 and 0/3** on a real one.
- **Cost**: none.
- **What this shape leaves broken**: all of it. Every AT arrival in the region
  drags the desk to the bottom of the paper. On both profiles.

### S1 — `top: 0; left: 0` on `.a11y-only`

- **O-FIX**: 3/3 both arms on `a11y-audible`; **0/3 both arms** on `a11y-long`.
- **Cost**: **1 line**, `web/e2-editor.html:66` (two declarations added to the
  existing `.a11y-only` rule). No JS.
- **What this shape leaves broken**: **every document taller than the
  viewport** — which is most documents; the fixture that passes is 10
  paragraphs of one line each. It replaces "always scrolled to the bottom" with
  "always scrolled to the top", and it scores a perfect 0.0000 scroll fraction
  while doing it, so a criterion written on the fraction would call it fixed.
  Secondarily: it edits a **class** rule, and 069's own lesson is that its fix
  covered an element and not a class — the next `.a11y-only` element would
  silently inherit a position it may not want.

### S2 — S1 plus two lines: `#a11y-doc` takes the sink's left and top

- **O-FIX**: 3/3 both arms on `a11y-audible`; **0/3 both arms** on `a11y-long`.
- **Cost**: **3 lines** (1 HTML + 2 JS in `moveSinkToCaret`,
  `web/e2-editor-app.js:722-735`).
- **What this shape leaves broken**: it lands the read line exactly at the
  bottom edge of the viewport and therefore shows none of it — the 1px height.
  Superseded by S2b; kept in the menu because it is the shape the task named
  and because the failure is instructive: S2 scrolls to the *right place* and
  still fails the oracle.

### S2b — S2 plus one more line: `#a11y-doc` also takes the sink's height

- **O-FIX**: 3/3 both arms on `a11y-audible`; on `a11y-long`, **focus 3/3,
  browse 1/3**.
- **Cost**: **4 lines** (1 HTML + 3 JS), all inside one existing function, no
  new state, no new mechanism.
- **What this shape leaves broken**:
  1. **Browse mode and structural navigation.** Measured 1/3: the region
     follows the caret and a screen reader's browse cursor does not move the
     caret, so it passes only for the paragraph the caret is already in. The
     owner's reported flow (arrow keys) is the one it fixes.
  2. **Range selections.** `paint()` calls `moveSinkToCaret` only when the
     selection is collapsed (`web/e2-editor-app.js:698-713`), so while text is
     selected the region stops following and is left at the last caret. Read
     from source; not measured here.
  3. **Before the first caret exists** (page load, before any click) the region
     is at S1's floor, the top of the paper.
  4. Not broken, checked: the pointer hazard (section 4).

### S3 — each projected node at its own paragraph

**This shape does not exist.** Section 1: no layer the product is given carries
a paragraph rectangle, and the engine never asks for one. It becomes available
with roughly one UNO call added to `oxsdk_a11y_document_outline`
(`src/a11y_tree_probe.cpp:252-345`) — **and an engine change means a relink and
a new artifact identity**, which is not available inside a running gate.

### S3' — the same, from a map derived by walking the caret

- **O-FIX**: **3/3 both arms on both documents.** The only shape that holds in
  the browse arm.
- **Cost**: 1 HTML line, plus per-node positioning (the probe's mutation is 18
  statements), **plus the map — which is the real cost and is not a line
  count**: one engine round trip per paragraph, obtained by *moving the user's
  caret into every paragraph*. 133 of them on `a11y-long`.
- **What this shape leaves broken**:
  1. **The derivation moves the user's caret.** Finding 066 is the record of
     what a stray caret move costs: it discards an armed inline format. Doing
     it once per paragraph at open is that hazard, N times.
  2. **The map goes stale and nothing can tell.** Any edit that rewraps a line
     moves every anchor below it; every `layoutCanvas()` (a window resize
     changes `cssWidth`, `web/e2-editor-app.js:525-539`) moves all of them. A
     stale map points the viewport at the wrong line and looks exactly like a
     correct one — the same shape as the defect being fixed.
  3. The clip has to move from the container to each node, and the container's
     clip is load-bearing (`web/e2-editor.html:231-234`: `display:none` and
     `visibility:hidden` remove the node from the accessibility tree, which
     reads as a broken projection rather than as broken CSS). **The probe's
     mutation did not clip `#a11y-para`**; a product version would have to.
  4. Finding 088's guard reuses nodes when the outline signature is unchanged,
     so positioning must be applied both on rebuild and on reuse.

## 6. Ranking, with reasons — the choice is the owner's

1. **S3'** is the only shape that satisfies the claim in both arms on a real
   document. It is also the most expensive, and the only one whose correctness
   depends on data the product cannot obtain without moving the user's caret
   and cannot keep valid across an edit.
2. **S2b** is the cheapest shape that satisfies the claim on **the flow the
   owner actually reported** (arrow keys), at 4 lines inside one existing
   function. It does not satisfy it for browse mode, and browse mode is how a
   screen reader user reads a document they are not editing.
3. **S1** is one line and satisfies the claim only when the whole document fits
   on one screen. Its 0.0000 scroll fraction against 0/3 visible paragraphs is
   the clearest reason in this file not to accept a proxy.
4. **True S3** (geometry from the engine) removes S3's staleness and caret
   hazards entirely and costs a relink. Named because section 1 found the data
   is one UNO call away, not because this phase recommends it.

**A fifth option nobody has costed**: S2b for the caret flow **plus** a
different answer for browse mode. This phase did not measure any such
combination and does not propose one.

## 7. Incidental, recorded rather than investigated

**A canvas click after the down arrow has been pressed at the last line of the
document places no caret at all.** Measured in all six `a11y-audible` runs
(both profiles, every shape): after the walk reaches the end of the document
and three further `ArrowDown` presses change nothing, the next canvas click
leaves `#s-latency` **empty for 25 seconds** — no success, no
"定位游標 失敗", no toast. On `a11y-long`, where the walk stops after 40
presses without reaching the end, the same click succeeds every time
(882/428/218/222 ms). Raw in every `postWalkClick` field.

This forced the probe to reload the page between arms and is why it does. It is
**not** investigated here and no finding is opened for it; the hypothesis that
fits (a no-op line move at the document end wedges the next placement) is
untested.

## 8. What this phase still does not know

- **Whether Orca's browse cursor is what drives the scroll in practice.**
  Unchanged from phase 2, and it is the single condition every verdict above
  rests on.
- **"Press Tab after the page is at the bottom and see where focus lands"** —
  named as not-done in 093, still not done.
- **The top-boundary focus escape** (`leaving panel`, 3 occurrences). Untouched;
  093 keeps it separate and so does this.
- **Whether any of these shapes survives a screen reader.** No shape here has
  been in front of one.
