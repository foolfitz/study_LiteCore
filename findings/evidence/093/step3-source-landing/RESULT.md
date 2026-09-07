# Finding 093, option B, step 3 — the source landed, and what it does and does not buy

Written 2026-09-08, executing §5 step 3 of
`handoff/RUNBOOK-operator-093-engine-geometry.md` after the owner's ruling of
option **B** and after step 1's calibration (`../step1-native-geometry/`) and
step 2's archive (`../step2-archive-e2-editor-v12.md`).

**Nothing was linked.** No wasm artifact was produced, no profile was
repackaged, `make ALLOW_FROZEN_RELINK=1 …` was not run, and no file under
`dist/profiles/` was touched. Step 4 is the owner's.

**The headline, said before the details:** the acceptance for option B —
`ORACLE-fix-shape.md` at **3/3 on both arms of the 133-paragraph document** —
**cannot be measured yet and was not measured.** No linked engine emits
per-paragraph geometry, so the clause the whole option is being paid for is
inert. What is measured below is that the plumbing is in place, that the page
degrades honestly without it, and that the check landed with it can go red.

---

## The four changes

### 1. `wasm_sdk_probe/src/a11y_tree_probe.cpp` — the engine half

`oxsdk_a11y_document_outline()` now takes the window's `OutputDevice`
alongside the accessible tree it already takes from the same window, queries
each paragraph for `XAccessibleComponent`, calls `getBounds()`, converts, and
emits four more numbers per paragraph: `x`, `y`, `width`, `height`.

**The conversion, and why it carries no DPI.** `getBounds()` returns *output
device pixels* — `SwAccessibleContext::getBoundsImpl` ends in
`GetMap()->CoreToPixel()`, which is `pWin->LogicToPixel(rect, aMapMode)`. Step
1 measured that on native, along with the DPI of the device it measured on
(96) and the fact that the 1/100 mm reading a general UNO convention would
suggest is out by a factor of 26.5.

The conversion here is

```c++
pDev->PixelToLogic(tools::Rectangle(Point(b.X, b.Y), Size(b.Width, b.Height)),
                   MapMode(MapUnit::MapTwip))
```

on **the same `OutputDevice` the bounds came from**. There is no division by
96 and no pixels-per-twip constant anywhere in the change. That is not a
stylistic preference:

* the 96 is a property of *this machine's headless svp device*, measured on
  the *native* build. Carrying it to a wasm artifact is exactly what finding
  036 is about;
* a constant would be **correct on the native build and silently wrong on the
  wasm one**, and nothing downstream could tell — the page would place every
  paragraph at a consistent, plausible, wrong offset;
* `PixelToLogic` asks the device to invert its own transform, so whatever the
  device's resolution turns out to be, the answer is right by construction.

Step 1 also measured that this form (`MapMode(MapUnit::MapTwip)`, a fresh
MapMode) and the exact inverse of `CoreToPixel` (`dev->GetMapMode()`, the
window's own origin and scale) give the **same number on all 114 paragraphs**,
because that device's MapMode is MapTwip at origin (0,0) with scale 1. The
fresh MapMode is the one used, because it depends on no property of the device
except the resolution being inverted.

**Absence is emitted as absence.** A paragraph whose bounds throw, or a view
with no `OutputDevice`, produces no geometry fields — never zeros. A rectangle
at the origin is a place, and a page that believed it would put that paragraph
at the top of the document and look right while being wrong.

**Unmeasured, and named rather than left to be found:** the outline is rebuilt
on every state read, so this adds one `getBounds()` per paragraph per read —
133 on the long fixture. The runbook's §7.3 question about what that costs is
**still open**; step 1 measured coordinates, not time, and this step measured
neither.

### 2. `wasm_sdk_probe/sdk/sdk-worker.js` — the allowlist

Four more fields copied in `productEditorState`'s `documentOutline` projection,
`null` when the engine did not report them rather than 0. This is load-bearing
and not plumbing: the projection is an allowlist, and a field nothing names
there never reaches the product. The file's own comment records the precedent
(`itemCount`, measured natively and reported nowhere for weeks).

### 3. `wasm_sdk_probe/tools/build_e2_editor_v4_profile.py` — the declaration

A new `--document-outline-geometry` flag, off by default, adding
`editorContract.documentOutlineGeometry = "accessible-paragraph-geometry"`.

**Gated, and it is a separate flag from `--document-outline`.** Every profile
linked before 2026-09-08 carries the outline *without* geometry, so a builder
that inferred one from the other would have declared geometry on
`e2-editor-v10`, `v11` and `v12` — three artifacts whose bytes do not have it.
That file's own comment records what unconditional declaration cost on
2026-08-22 ("describes but does not constrain"), and here the two states are
opposite instructions: an undeclared profile degrades honestly, a profile that
declares geometry and delivers none is a **defect the product path now fails
on**.

### 4. `wasm_sdk_probe/web/e2-editor.html` + `web/e2-editor-app.js` — the page

* `#a11y-doc` gets its own rule: `top: 0; left: 0; width: 1px; height: 100%`,
  and it stops clipping (`overflow: visible; clip: auto; clip-path: none`), so
  it becomes the coordinate space the projected nodes live in. `pointer-events:
  none`, because that box now covers the drawing surface.
* The clip it gave up moves to its children: `#a11y-para` by a rule, each
  projected node inline from `positionProjection()`.
* **Fixed on `#a11y-doc`, not on `.a11y-only`.** That is the other half of
  069's lesson. 069 fixed one element and left the class producing the same
  defect for the next user of it — but widening the class rule is the same
  mistake pointed the other way: the census of 2026-09-08 found 28 other rules
  in `web/` that position absolutely and **none** in this shape, so changing
  the class would move 28 elements to fix one. The class comment now names both
  of its instances and says a third would inherit the same trap.
* `positionProjection()` places each node at its own paragraph's twips, scaled
  the way `moveSinkToCaret()` scales (CSS pixels from `clientWidth`/
  `clientHeight`, **not** `paint()`'s backing pixels, which differ by
  devicePixelRatio), and gives it the paragraph's height for the reason
  `moveSinkToCaret` gives the sink the caret's: `scrollIntoView({block:
  "nearest"})` stops at the target's bottom edge, so a 1px target leaves the
  line being read below the fold.

**Geometry does not enter finding 088's `signature`.** The signature is still
`[role, level, text]`. Placement is a **separate pass**, run after the
keep-or-rebuild branch and therefore in both branches, writing `style` in
place. Geometry changes on every relayout; in the signature it would rebuild
the whole projection under a screen reader's feet on every resize, which is
088 exactly — and 088 was found by the owner's ears, not by an instrument.
`layoutCanvas()` also calls the pass, because that is the one place the
twips→CSS scale moves and `projectStructure` runs on state reads, which a
resize is not.

**The page states which of three worlds it is in**, in the DOM, on
`#a11y-structure`:

| `data-geometry` | meaning |
| --- | --- |
| `noProjection` | there is no outline at all — the shipped profile |
| `absent` | the profile does not declare geometry — every artifact linked before 2026-09-08 |
| `present` | declared, and the payload carries it |
| `declared-but-missing` | declared, and **nothing** arrived — a defect |

Per-paragraph misses travel as `data-geometry-carried` / `-placed` and are
deliberately **not** judged: `getBounds()` has branches this tree has never
reached (empty preview pages, a paragraph whose accessible parent is not the
root — both named in step 1 as unvisited), and a threshold on a distribution
nobody has measured would be a number invented ahead of the evidence.

---

## The check, and the red cases that came before it

`the-projection-is-placed-where-the-document-is`, in
`tools/run_e2_c_product_path.py`, with two `MUTATIONS` entries. Its admission
to the gate is registered against AGENTS.md §9's four conditions in
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` (amendment of
2026-09-08), written before the code.

It exists because the census in finding 093 found that **nothing in the net
reads this shape**: the one check that touches this DOM returns text, reason,
offers, deferral and the active descendant, and no geometry. 069 fixed an
element and the net guarded that element; fixing a second element while adding
nothing that watches the shape is how the story runs a third time.

### Red case (b) — declared and not delivered: **red**

`tools/probe_093_placement_red_cases.py`, raw output in `red-cases.json`. It
imports the predicate from the runner rather than restating it, because two
implementations of one rule drift and disagree on the day nobody is checking.

| arm | verdict | `data-geometry` | `#a11y-doc.offsetTop` / canvas |
| --- | --- | --- | --- |
| the page as it ships, shipped profile | **PASS** | `noProjection` | 0 / 929 |
| the page repointed at `e2-editor-v12` | **PASS** | `absent` | 0 / 929 |
| `a11y-projection-at-its-static-position` | **FAIL (C2)** | `absent` | **929 / 929** |
| `geometry-declared-but-not-delivered` | **FAIL (C1)** | `declared-but-missing` | 0 / 929 |

The third arm is finding 093 itself — the `#a11y-doc` rule stripped back to
what it was — and it reproduces phase 2's measurement (`offsetTop` 928 against
a 929px canvas; 929 here rather than 928 because the container no longer
inherits `.a11y-only`'s `margin: -1px`).

The fourth is red case (b) **as the page can see it**. The literal defect
("the engine emits geometry and the worker's allowlist drops it") cannot be
built today: no linked artifact emits geometry, so there is nothing for an
allowlist to drop, and manufacturing one would mean a link. What the mutation
reproduces is the *page-observable state* of that defect — the contract says
the rectangles are there and the payload carries none — which is the only
vantage point the check has. Written down rather than glossed.

### Red case (a) — the engine emits no geometry: **red, and it is today's state**

Measured with the **pinned** instrument against the **pinned** oracle:
`tools/probe_093_fix_shape_oracle.py --profile e2-editor-v12 --fixture
a11y-long --shape S0`, raw output in `oracle-S0-a11y-long.json`. `S0` is "the
page as it ships", so on the landed tree it is the page with this change in it.

**0/3 on both arms**, on the 133-paragraph document:

| target | band in viewport | viewport | overlap | threshold | scroll fraction |
| --- | --- | --- | --- | --- | --- |
| paragraph 11 | 2192 .. 2214 | 864 | **0** | 11.0 | **0.0000** |
| paragraph 14 | 2818 .. 2840 | 864 | **0** | 11.0 | **0.0000** |
| paragraph 16 | 3140 .. 3162 | 864 | **0** | 11.0 | **0.0000** |

identical in the `browse` and `focus` arms.

**This is the S1 signature that phase 3 exists to have named**: a perfect
scroll fraction and nothing visible. The landed page changes *which* wrong
answer an unfixed profile gives — the viewport is pinned to the top of the
paper (`a11yDocOffsetTop` 0, was 27,197 against a 27,198px canvas) instead of
dragged to the bottom — and O-FIX cannot tell the two apart, because both fail
it. **Only the relink can make this 3/3.**

Red case (a) and red case (b) are distinguishable, and the DOM says which is
which without reading any source: (a) reports `data-geometry="absent"` and the
product-path check **passes**; (b) reports `declared-but-missing` and the check
**fails**.

---

## The runbook's §1.2(d) is wrong, and the conclusion it supports survives

The runbook argues that option B's call site "produces no new external symbol
at all". `new-undefined-symbols.txt` in this directory is the measurement:
**43 undefined symbols before the change, 47 after.** The argument covered
`UNO_QUERY` (a header-only path already used for `XAccessibleText`) and
`getBounds()` (a pure virtual call, no symbol) — both hold — and did not cover
the conversion, which is the part option B actually adds:

```
_ZN3vcl6Window9GetOutDevEv
_ZN7MapModeC1E7MapUnit
_ZN7MapModeD1Ev
_ZNK12OutputDevice12PixelToLogicERKN5tools9RectangleERK7MapMode
```

All four are **defined** (`T`) in `libvcllo.a`, and `-lvcllo` is on the link
line, so the runbook's conclusion — no core rebuild, the link will resolve —
is unaffected. The argument is corrected because the next change of this shape
will be argued the same way.

## The translation unit compiles

Compiled **alone**, with the E2_V10/E2_V12 lineage's own flags (`-Oz -pthread
-fwasm-exceptions -sSUPPORT_LONGJMP=wasm -std=c++20 -DLIBO_INTERNAL_ONLY`),
against `../wasm-lite/build-a11y-gate0`'s headers: clean, 1.4 s, and both
`oxsdk_a11y_document_outline` and `oxsdk_a11y_tree_snapshot` are defined in the
object. The object was written to a scratch directory, not into any profile's
build tree. An object file is not a one-way door and mints no identity; a link
is and does, and none was taken.

## What was written outside `web/`, `src/`, `sdk/` and `tools/`

* `wasm_sdk_probe/e2/editor-shell-v2-bundle-v49.json` — the shell generation
  for this page, frozen in the same commit as the change, which is the step
  findings 087, 088 and 090 each skipped and which finding 091 is the record
  of. **A further generation is owed after step 4**, because the relink moves
  `workerUrl` and `PINNED_WASM_SHA256` in the same file; step 5.4 of the
  runbook already says so.
* `wasm_sdk_probe/dist/e2-editor.html` and `dist/e2-editor-app.js` — the two
  `cp` targets of `make e2-c-assets` for the page, and **nothing else under
  `dist/`**. This was not optional: `tools/build_e2_c_shell_bundle.py`'s
  `problems()` refuses to freeze a generation while any served copy differs
  from its source ("dist copy differs from source: … (run `make e2-c-assets`)")
  and `tests/test_product_path_mutations.py` matches every mutation pattern
  against `dist/`, so `make test-e2-c-static` cannot be green without them.
  Both files are git-ignored plain copies of `web/`, carry no identity, and are
  reproducible with `make dist/e2-editor.html dist/e2-editor-app.js`. No
  profile, artifact or `dist/profiles/**` byte was written.

`make test-e2-c-static` exits **0**.

## What remains unmeasurable until the owner links

* **O-FIX at 3/3.** The clause option B is being paid for (C3: the node for the
  paragraph the caret is in is drawn where that paragraph is) has never
  executed, on any run, because no artifact emits the data. The check reports
  `clausesExercised: ["C1", "C2"]` so this cannot be mistaken for coverage.
* **Whether the engine's numbers are right on wasm.** Step 1 measured the
  coordinate space on the native build and deliberately did not carry the DPI
  across. The conversion is DPI-independent by construction, but "the wasm
  device's `PixelToLogic` returns what the caret rectangle is in" is a
  prediction until a linked artifact is asked.
* **The cost of 133 `getBounds()` calls per state read.** Unmeasured, on either
  build.
* **Empty paragraphs, tables, frames, multi-column layout.** Step 1's fixture
  reached neither of `getBoundsImpl`'s two other branches, and neither does
  anything here.
* **Whether a screen reader is what drives the scroll.** Phase 2 and phase 3
  both owe this, and it is not paid here either: every result above models an
  AT arrival as `scrollIntoView({block: "nearest"})`.
